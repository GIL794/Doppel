import io
import os
import re
import time

os.environ["DB_PATH"] = "/tmp/aipromovids-test.db"
os.environ["UPLOAD_DIR"] = "/tmp/aipromovids-test-uploads"
os.environ["ADMIN_EMAILS"] = "admin@example.com"

for p in ("/tmp/aipromovids-test.db",):
    if os.path.exists(p):
        os.remove(p)

from fastapi.testclient import TestClient  # noqa: E402
import server  # noqa: E402

client = TestClient(server.app)
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c626001000000ffff030000060005"
    "57bfabd40000000049454e44ae426082"
)


def test_register_login_me_refresh_logout():
    r = client.post("/api/auth/register", json={"name": "Ada", "email": "ada@example.com", "password": "password123"})
    assert r.status_code == 201, r.text
    assert r.json()["role"] == "customer"
    assert "access_token" in r.cookies and "refresh_token" in r.cookies

    assert client.get("/api/auth/me").json()["email"] == "ada@example.com"

    # refresh works even with an invalid access cookie
    client.cookies.set("access_token", "bogus")
    r = client.post("/api/auth/refresh")
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Ada"

    r = client.post("/api/auth/logout")
    assert r.status_code == 200
    assert client.get("/api/auth/me").status_code == 401

    r = client.post("/api/auth/login", json={"email": "ada@example.com", "password": "password123"})
    assert r.status_code == 200
    r = client.post("/api/auth/login", json={"email": "ada@example.com", "password": "wrong"})
    assert r.status_code == 401


def test_upload_and_file_serving():
    client.post("/api/auth/login", json={"email": "ada@example.com", "password": "password123"})
    r = client.post("/api/uploads", files={"file": ("p.png", io.BytesIO(PNG), "image/png")}, data={"kind": "photo"})
    assert r.status_code == 201, r.text
    fid = r.json()["file_id"]
    r = client.get(f"/api/files/{fid}")
    assert r.status_code == 200 and r.content == PNG
    r = client.post("/api/uploads", files={"file": ("x.txt", io.BytesIO(b"hi"), "text/plain")}, data={"kind": "photo"})
    assert r.status_code == 400


def test_mock_checkout_status_and_my_orders():
    client.post("/api/auth/login", json={"email": "ada@example.com", "password": "password123"})
    r = client.post("/api/payments/checkout", json={
        "name": "Ada", "email": "ada@example.com", "company": "Bloom Florist",
        "language": "English", "avatar_style": "Looks like me", "brief": "Say hi",
        "origin_url": "http://localhost:3000"})
    assert r.status_code == 201, r.text
    url = r.json()["checkout_url"]
    sid = re.search(r"session_id=([0-9a-f]+)", url).group(1)
    assert url.startswith("http://localhost:3000/payment/success")

    r = client.get(f"/api/payments/status/{sid}")
    assert r.json()["payment_status"] == "paid"
    ref = r.json()["order_ref"]

    mine = client.get("/api/orders/mine").json()
    assert any(o["order_ref"] == ref and o["company"] == "Bloom Florist" for o in mine)
    assert client.get("/api/payments/status/nope").status_code == 404


def test_teasers_lifecycle_and_limit():
    client.post("/api/auth/login", json={"email": "ada@example.com", "password": "password123"})
    fid = client.post("/api/uploads", files={"file": ("p.png", io.BytesIO(PNG), "image/png")},
                      data={"kind": "photo"}).json()["file_id"]
    r = client.post("/api/teasers", json={"photo_file_id": fid, "text": "Hello from my shop!"})
    assert r.status_code == 201, r.text
    tid = r.json()["teaser_id"]
    data = client.get("/api/teasers").json()
    assert data["remaining"] == 1 and data["items"][0]["status"] == "processing"
    deadline = time.time() + 15
    while time.time() < deadline:
        item = [t for t in client.get("/api/teasers").json()["items"] if t["teaser_id"] == tid][0]
        if item["status"] != "processing":
            break
        time.sleep(1)
    assert item["status"] == "failed"
    assert "not configured" in item["error"]  # honest failure, no fake video

    client.post("/api/teasers", json={"photo_file_id": fid, "text": "Second teaser"})
    r = client.post("/api/teasers", json={"photo_file_id": fid, "text": "Third teaser"})
    assert r.status_code == 400  # free limit enforced
    assert client.get("/api/teasers").json()["remaining"] == 0


def test_script_preview_sse():
    r = client.post("/api/script/preview", json={
        "business": "Bloom Florist", "offer": "free delivery this week",
        "language": "English", "vibe": "Warm & friendly"})
    assert r.status_code == 200, r.text
    text = ""
    for line in r.text.splitlines():
        if line.startswith("data: "):
            import json
            ev = json.loads(line[6:])
            text += ev.get("delta", "")
    assert "HOOK:" in text and "SCRIPT:" in text and "CTA:" in text
    assert "Bloom Florist" in text and "free delivery this week" in text


def test_admin_overview_and_orders():
    r = client.post("/api/auth/register", json={"name": "Boss", "email": "admin@example.com", "password": "password123"})
    assert r.json()["role"] == "customer"  # password registration never grants admin
    # Out-of-band promotion (what a real deployment does for the owner):
    server.q("UPDATE users SET role='admin' WHERE email='admin@example.com'", write=True)
    overview = client.get("/api/admin/overview").json()
    assert overview["paid_orders"] == 1 and overview["revenue_gbp"] == 350
    assert overview["customers"] == 2 and overview["teasers"] == 2 and overview["scripts"] == 1
    orders = client.get("/api/admin/orders").json()
    assert orders[0]["company"] == "Bloom Florist" and orders[0]["payment_status"] == "paid"

    client.post("/api/auth/login", json={"email": "ada@example.com", "password": "password123"})
    assert client.get("/api/admin/overview").status_code == 403


def test_password_reset_flow():
    client.post("/api/auth/forgot-password", json={"email": "ada@example.com", "origin_url": "http://localhost:3000"})
    row = server.q("SELECT token FROM password_resets ORDER BY created_at DESC", one=True)
    r = client.post("/api/auth/reset-password", json={"token": row["token"], "password": "newpassword1"})
    assert r.status_code == 200, r.text
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={"email": "ada@example.com", "password": "newpassword1"}).status_code == 200
    # token can't be reused
    assert client.post("/api/auth/reset-password", json={"token": row["token"], "password": "anotherone1"}).status_code == 400


def test_google_session_honest_501():
    r = client.post("/api/auth/google/session", json={"session_id": "x"})
    assert r.status_code == 501 and "/api/auth/google/login" in r.json()["detail"]
