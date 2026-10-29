"""Full-scope local functionality: standard Google OAuth, SMTP password reset,
and the paid-order script-approval workflow. All external services are faked -
no network, no credentials."""
import importlib
import json
import os
import sys
import time

import pytest
from fastapi.testclient import TestClient

import providers


def load(monkeypatch, **env):
    for k in ("PAYMENT_PROVIDER", "STRIPE_API_KEY", "TEASER_PROVIDER", "FAL_KEY",
              "SCRIPT_PROVIDER", "GEMINI_API_KEY", "SMTP_HOST", "STRIPE_WEBHOOK_SECRET",
              "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "ADMIN_EMAILS"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    db_path = "/tmp/aipromovids-fullscope-test.db"
    if os.path.exists(db_path):
        os.unlink(db_path)
    monkeypatch.setenv("DB_PATH", db_path)
    monkeypatch.setenv("UPLOAD_DIR", "/tmp/aipromovids-fullscope-uploads")
    if "server" in sys.modules:
        import server
        return importlib.reload(server)
    import server
    return server


# ------------------------------------------------------------- google oauth
def _google_client(monkeypatch, verified=True, email="g@example.com"):
    server = load(monkeypatch, GOOGLE_CLIENT_ID="cid", GOOGLE_CLIENT_SECRET="csec")
    monkeypatch.setattr(providers, "google_exchange_code",
                        lambda *a, **k: {"access_token": "tok"})
    monkeypatch.setattr(providers, "google_fetch_userinfo",
                        lambda *a, **k: {"email": email, "email_verified": verified,
                                         "name": "G User", "sub": "g1"})
    return server, TestClient(server.app)


def _login_state(client):
    r = client.get("/api/auth/google/login", follow_redirects=False)
    assert r.status_code == 302
    loc = r.headers["location"]
    assert loc.startswith(providers.GOOGLE_AUTH_URL)
    assert "client_id=cid" in loc and "response_type=code" in loc
    assert "scope=openid+email+profile" in loc
    from urllib.parse import urlparse, parse_qs
    return parse_qs(urlparse(loc).query)["state"][0]


def test_google_login_redirects_to_google_when_configured(monkeypatch):
    server, client = _google_client(monkeypatch)
    _login_state(client)


def test_google_login_bounces_back_when_unconfigured(monkeypatch):
    server = load(monkeypatch)
    client = TestClient(server.app)
    r = client.get("/api/auth/google/login", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"].endswith("/login?google=unavailable")
    assert client.get("/api").json()["capabilities"]["google_auth"] == "not_configured"


def test_google_callback_creates_user_and_session(monkeypatch):
    server, client = _google_client(monkeypatch)
    state = _login_state(client)
    r = client.get(f"/api/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"].endswith("/dashboard")
    me = client.get("/api/auth/me")
    assert me.status_code == 200 and me.json()["email"] == "g@example.com"


def test_google_callback_existing_user_signs_in(monkeypatch):
    server, client = _google_client(monkeypatch)
    client.post("/api/auth/register", json={"name": "G", "email": "g@example.com", "password": "password123"})
    client.post("/api/auth/logout")
    state = _login_state(client)
    client.get(f"/api/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    assert client.get("/api/auth/me").json()["email"] == "g@example.com"


def test_google_callback_rejects_bad_state_and_unverified_email(monkeypatch):
    server, client = _google_client(monkeypatch)
    r = client.get("/api/auth/google/callback?code=abc&state=wrong", follow_redirects=False)
    assert r.headers["location"].endswith("/login?google=failed")
    state = _login_state(client)
    monkeypatch.setattr(providers, "google_fetch_userinfo",
                        lambda *a, **k: {"email": "g@example.com", "email_verified": False})
    r = client.get(f"/api/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    assert r.headers["location"].endswith("/login?google=failed")
    assert client.get("/api/auth/me").status_code == 401


def test_google_state_is_single_use(monkeypatch):
    server, client = _google_client(monkeypatch)
    state = _login_state(client)
    client.get(f"/api/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    client.post("/api/auth/logout")
    r = client.get(f"/api/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    assert r.headers["location"].endswith("/login?google=failed")


# ---------------------------------------------------------- password reset
def test_reset_email_sent_when_smtp_configured(monkeypatch):
    server = load(monkeypatch, SMTP_HOST="smtp.example.com")
    sent = []
    monkeypatch.setattr(providers, "send_password_reset_email",
                        lambda cfg, *, to_email, reset_link, **k: sent.append((to_email, reset_link)) or True)
    client = TestClient(server.app)
    client.post("/api/auth/register", json={"name": "R", "email": "r@example.com", "password": "password123"})
    r = client.post("/api/auth/forgot-password", json={"email": "r@example.com"})
    assert r.status_code == 200
    assert len(sent) == 1 and sent[0][0] == "r@example.com"
    token = sent[0][1].split("token=")[1]
    r = client.post("/api/auth/reset-password", json={"token": token, "password": "newpassword123"})
    assert r.status_code == 200
    assert client.post("/api/auth/login", json={"email": "r@example.com", "password": "newpassword123"}).status_code == 200


def test_reset_without_smtp_stays_generic_and_sends_nothing(monkeypatch):
    server = load(monkeypatch)
    calls = []
    monkeypatch.setattr(providers, "send_password_reset_email", lambda *a, **k: calls.append(1))
    client = TestClient(server.app)
    client.post("/api/auth/register", json={"name": "R", "email": "r@example.com", "password": "password123"})
    assert client.post("/api/auth/forgot-password", json={"email": "r@example.com"}).json() == {"ok": True}
    assert calls == []


# ------------------------------------------------- fulfillment fail-closed
def _stripe_client(monkeypatch):
    server = load(monkeypatch, PAYMENT_PROVIDER="stripe", STRIPE_API_KEY="sk_test_x",
                  STRIPE_WEBHOOK_SECRET="whsec_x")
    monkeypatch.setattr(providers, "stripe_create_checkout",
                        lambda *a, **k: {"session_id": "cs_test_real", "checkout_url": "https://checkout.stripe.com/pay/cs_test_real"})
    client = TestClient(server.app)
    client.post("/api/payments/checkout", json={"name": "A", "email": "a@b.co", "company": "C"})
    return server, client


def _fire(client, event_type, obj):
    import hashlib, hmac as hmac_mod
    payload = json.dumps({"type": event_type, "data": {"object": obj}}).encode()
    ts = int(time.time())
    sig = hmac_mod.new(b"whsec_x", f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    return client.post("/api/stripe/webhook", content=payload,
                       headers={"stripe-signature": f"t={ts},v1={sig}"})


def test_fulfillment_fails_closed_when_amount_or_currency_absent(monkeypatch):
    server, client = _stripe_client(monkeypatch)
    _fire(client, "checkout.session.completed", {"id": "cs_test_real", "payment_status": "paid", "currency": "gbp"})
    assert client.get("/api/payments/status/cs_test_real").json()["payment_status"] == "pending"
    _fire(client, "checkout.session.completed", {"id": "cs_test_real", "payment_status": "paid", "amount_total": 35000})
    assert client.get("/api/payments/status/cs_test_real").json()["payment_status"] == "pending"
    _fire(client, "checkout.session.completed",
          {"id": "cs_test_real", "payment_status": "paid", "amount_total": 35000, "currency": "gbp"})
    assert client.get("/api/payments/status/cs_test_real").json()["payment_status"] == "paid"


# ------------------------------------------- paid-order script-approval loop
@pytest.fixture
def workflow(monkeypatch):
    server = load(monkeypatch, SMTP_HOST="smtp.example.com", ADMIN_EMAILS="boss@example.com")
    emails = []
    monkeypatch.setattr(providers, "send_script_ready_email",
                        lambda cfg, *, to_email, order_ref, dashboard_url, **k: emails.append(("script", to_email, order_ref)) or True)
    monkeypatch.setattr(providers, "send_delivery_email",
                        lambda cfg, *, to_email, order_ref, note, **k: emails.append(("delivered", to_email, order_ref)) or True)
    customer = TestClient(server.app)
    customer.post("/api/auth/register", json={"name": "C", "email": "c@example.com", "password": "password123"})
    customer.post("/api/payments/checkout", json={"name": "C", "email": "c@example.com", "company": "Co"})
    admin = TestClient(server.app)
    admin.post("/api/auth/register", json={"name": "B", "email": "boss@example.com", "password": "password123"})
    # Out-of-band promotion: password registration must never grant admin.
    server.q("UPDATE users SET role='admin' WHERE email='boss@example.com'", write=True)
    return server, customer, admin, emails


def test_paid_order_workflow_end_to_end(workflow):
    server, customer, admin, emails = workflow
    mine = customer.get("/api/orders/mine").json()
    assert mine[0]["production_status"] == "in_production"
    ref = mine[0]["order_ref"]

    r = admin.post(f"/api/admin/orders/{ref}/script", json={"script_text": "HOOK: hi\nSCRIPT: body here\nCTA: buy"})
    assert r.json() == {"ok": True, "production_status": "script_ready", "email_sent": True}
    mine = customer.get("/api/orders/mine").json()
    assert mine[0]["production_status"] == "script_ready" and "HOOK" in mine[0]["script_text"]

    r = customer.post(f"/api/orders/{ref}/script/changes", json={"note": "shorter please"})
    assert r.json()["production_status"] == "changes_requested"

    r = admin.post(f"/api/admin/orders/{ref}/script", json={"script_text": "HOOK: hi\nSCRIPT: short now\nCTA: buy"})
    assert r.json()["production_status"] == "script_ready"
    r = customer.post(f"/api/orders/{ref}/script/approve")
    assert r.json()["production_status"] == "script_approved"

    r = admin.post(f"/api/admin/orders/{ref}/deliver", json={"note": "Your video is attached to your studio"})
    assert r.json() == {"ok": True, "production_status": "delivered", "email_sent": True}
    mine = customer.get("/api/orders/mine").json()
    assert mine[0]["production_status"] == "delivered"
    assert mine[0]["delivered_note"] == "Your video is attached to your studio"
    assert [e[0] for e in emails] == ["script", "script", "delivered"]


def test_workflow_rejects_bad_transitions(workflow):
    server, customer, admin, emails = workflow
    ref = customer.get("/api/orders/mine").json()[0]["order_ref"]
    assert customer.post(f"/api/orders/{ref}/script/approve").status_code == 409
    assert admin.post(f"/api/admin/orders/{ref}/deliver", json={"note": "x"}).status_code == 409
    admin.post(f"/api/admin/orders/{ref}/script", json={"script_text": "HOOK: h\nSCRIPT: b\nCTA: c"})
    assert admin.post(f"/api/admin/orders/{ref}/script", json={"script_text": "HOOK: h\nSCRIPT: b\nCTA: c"}).status_code == 409
    customer.post(f"/api/orders/{ref}/script/approve")
    assert customer.post(f"/api/orders/{ref}/script/changes", json={"note": "more"}).status_code == 409


def test_workflow_rejects_non_owner(workflow):
    server, customer, admin, emails = workflow
    ref = customer.get("/api/orders/mine").json()[0]["order_ref"]
    admin.post(f"/api/admin/orders/{ref}/script", json={"script_text": "HOOK: h\nSCRIPT: b\nCTA: c"})
    other = TestClient(server.app)
    other.post("/api/auth/register", json={"name": "O", "email": "o@example.com", "password": "password123"})
    assert other.post(f"/api/orders/{ref}/script/approve").status_code == 403
    assert other.post(f"/api/orders/{ref}/script/changes", json={"note": "more"}).status_code == 403
    assert other.post(f"/api/admin/orders/{ref}/deliver", json={"note": "x"}).status_code == 403


def test_admin_sees_production_status(workflow):
    server, customer, admin, emails = workflow
    rows = admin.get("/api/admin/orders").json()
    assert rows[0]["production_status"] == "in_production"


# ============================================== review-fix regression tests
def test_reset_link_ignores_client_origin(monkeypatch):
    server = load(monkeypatch, SMTP_HOST="smtp.example.com")
    sent = []
    monkeypatch.setattr(providers, "send_password_reset_email",
                        lambda cfg, *, to_email, reset_link, **k: sent.append(reset_link) or True)
    client = TestClient(server.app)
    client.post("/api/auth/register", json={"name": "V", "email": "v@example.com", "password": "password123"})
    client.post("/api/auth/forgot-password",
                json={"email": "v@example.com", "origin_url": "https://attacker.example"})
    assert len(sent) == 1
    assert sent[0].startswith("http://localhost:3000/reset-password?token=")
    assert "attacker" not in sent[0]


def test_password_registration_never_grants_admin(monkeypatch):
    server = load(monkeypatch, ADMIN_EMAILS="boss@example.com")
    client = TestClient(server.app)
    r = client.post("/api/auth/register", json={"name": "X", "email": "boss@example.com", "password": "password123"})
    assert r.json()["role"] == "customer"
    assert client.get("/api/admin/overview").status_code == 403
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"email": "boss@example.com", "password": "password123"})
    assert client.get("/api/admin/overview").status_code == 403  # no promotion at login either


def test_google_login_promotes_admin_with_verified_email(monkeypatch):
    server, client = _google_client(monkeypatch)
    server.ADMIN_EMAILS.add("g@example.com")
    state = _login_state(client)
    client.get(f"/api/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    assert client.get("/api/auth/me").json()["role"] == "admin"
    assert client.get("/api/admin/overview").status_code == 200


def test_oauth_account_password_login_returns_401_not_500(monkeypatch):
    server, client = _google_client(monkeypatch)
    state = _login_state(client)
    client.get(f"/api/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    client.post("/api/auth/logout")
    r = client.post("/api/auth/login", json={"email": "g@example.com", "password": "whatever123"})
    assert r.status_code == 401


def test_google_callback_requires_browser_bound_state(monkeypatch):
    server, client1 = _google_client(monkeypatch)
    state = _login_state(client1)  # sets the gstate cookie in client1 only
    other_browser = TestClient(server.app)
    r = other_browser.get(f"/api/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    assert r.headers["location"].endswith("/login?google=failed")
    assert other_browser.get("/api/auth/me").status_code == 401
    # the legitimate browser still completes with the same state
    r = client1.get(f"/api/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    assert r.headers["location"].endswith("/dashboard")


def test_guest_order_hidden_until_email_verified(monkeypatch):
    server = load(monkeypatch)
    guest = TestClient(server.app)
    guest.post("/api/payments/checkout", json={"name": "G", "email": "v@example.com", "company": "Co"})
    # password account with the same email string: NO access to the guest order
    pw = TestClient(server.app)
    pw.post("/api/auth/register", json={"name": "V", "email": "v@example.com", "password": "password123"})
    assert pw.get("/api/orders/mine").json() == []
    assert pw.post("/api/orders/1/script/approve").status_code == 403
    # a Google-verified account with the same email DOES inherit the guest order
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "csec")
    import importlib as il
    server = il.reload(server)
    monkeypatch.setattr(providers, "google_exchange_code", lambda *a, **k: {"access_token": "t"})
    monkeypatch.setattr(providers, "google_fetch_userinfo",
                        lambda *a, **k: {"email": "v@example.com", "email_verified": True, "name": "V", "sub": "s"})
    g = TestClient(server.app)
    r = g.get("/api/auth/google/login", follow_redirects=False)
    from urllib.parse import urlparse, parse_qs
    st = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
    g.get(f"/api/auth/google/callback?code=x&state={st}", follow_redirects=False)
    mine = g.get("/api/orders/mine").json()
    assert len(mine) == 1 and mine[0]["email"] == "v@example.com"


def test_teaser_photo_must_belong_to_requester(monkeypatch):
    server = load(monkeypatch)
    import io
    PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32
    a = TestClient(server.app)
    a.post("/api/auth/register", json={"name": "A", "email": "a@example.com", "password": "password123"})
    fid = a.post("/api/uploads", files={"file": ("p.png", io.BytesIO(PNG), "image/png")},
                 data={"kind": "photo"}).json()["file_id"]
    b = TestClient(server.app)
    b.post("/api/auth/register", json={"name": "B", "email": "b@example.com", "password": "password123"})
    r = b.post("/api/teasers", json={"photo_file_id": fid, "text": "hello there world"})
    assert r.status_code == 400


def test_payment_status_surfaces_expired(monkeypatch):
    server, client = _stripe_client(monkeypatch)
    _fire(client, "checkout.session.expired", {"id": "cs_test_real"})
    body = client.get("/api/payments/status/cs_test_real").json()
    assert body["payment_status"] == "expired" and body["status"] == "expired"


def test_checkout_redirects_use_server_origin_only(monkeypatch):
    server = load(monkeypatch)
    client = TestClient(server.app)
    r = client.post("/api/payments/checkout", json={
        "name": "A", "email": "a@b.co", "company": "C", "origin_url": "https://evil.example"})
    assert r.json()["checkout_url"].startswith("http://localhost:3000/")
    server2 = load(monkeypatch, PAYMENT_PROVIDER="stripe", STRIPE_API_KEY="sk_test_x")
    captured = {}
    monkeypatch.setattr(providers, "stripe_create_checkout",
                        lambda *a, **k: captured.update(k) or {"session_id": "cs_1", "checkout_url": "u"})
    client2 = TestClient(server2.app)
    client2.post("/api/payments/checkout", json={
        "name": "A", "email": "a@b.co", "company": "C", "origin_url": "https://evil.example"})
    assert captured["origin_url"] == "http://localhost:3000"


def test_stripe_without_key_reports_misconfigured_not_real(monkeypatch):
    server = load(monkeypatch, PAYMENT_PROVIDER="stripe")
    body = server.app and TestClient(server.app).get("/api").json()
    assert body["capabilities"]["payments"] == "misconfigured"
    assert body["demo"] is True
