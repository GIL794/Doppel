"""Remote file storage (Supabase Storage REST) with a fake transport - no
network, no credentials - plus the database layer's SQL translation."""
import json

import blobstore
import dbase


class FakeHTTP:
    def __init__(self, status=200, body=b""):
        self.calls, self.status, self.body = [], status, body

    def __call__(self, method, url, *, data=None, headers=None, timeout=60):
        self.calls.append((method, url, data, headers))
        return self.status, self.body


def test_supabase_upload_builds_documented_request():
    http = FakeHTTP(200)
    s = blobstore.SupabaseStore("https://x.supabase.co/", "svc-key", "bkt", request=http)
    path = s.put("abc.mp4", b"video", "video/mp4")
    assert path == "sb:abc.mp4"
    method, url, data, h = http.calls[0]
    assert (method, url) == ("POST", "https://x.supabase.co/storage/v1/object/bkt/abc.mp4")
    assert data == b"video" and h["Authorization"] == "Bearer svc-key"
    assert h["Content-Type"] == "video/mp4" and "x-upsert" not in {k.lower() for k in h}


def test_supabase_upload_failure_raises():
    s = blobstore.SupabaseStore("https://x.supabase.co", "k", request=FakeHTTP(400))
    try:
        s.put("a.png", b"x", "image/png")
        raise AssertionError("expected failure")
    except RuntimeError as e:
        assert "400" in str(e)


def test_supabase_signed_url_and_download():
    http = FakeHTTP(200, json.dumps({"signedURL": "/object/sign/bkt/a.mp4?token=t"}).encode())
    s = blobstore.SupabaseStore("https://x.supabase.co", "k", "bkt", request=http)
    assert s.signed_url("sb:a.mp4") == "https://x.supabase.co/storage/v1/object/sign/bkt/a.mp4?token=t"
    assert http.calls[0][0:2] == ("POST", "https://x.supabase.co/storage/v1/object/sign/bkt/a.mp4")
    assert json.loads(http.calls[0][2]) == {"expiresIn": blobstore.SIGNED_URL_SECONDS}
    http2 = FakeHTTP(200, b"bytes")
    s2 = blobstore.SupabaseStore("https://x.supabase.co", "k", "bkt", request=http2)
    assert s2.get("sb:a.mp4") == b"bytes"
    assert http2.calls[0][1].endswith("/object/authenticated/bkt/a.mp4")


def test_local_store_default_and_env_selection(tmp_path):
    assert isinstance(blobstore.make_store(tmp_path, {}), blobstore.LocalStore)
    assert isinstance(blobstore.make_store(tmp_path, {"SUPABASE_URL": "https://x", "SUPABASE_SERVICE_KEY": "k"}),
                      blobstore.SupabaseStore)
    st = blobstore.LocalStore(tmp_path)
    p = st.put("f.png", b"abc", "image/png")
    assert st.get(p) == b"abc" and st.exists(p) and st.signed_url(p) is None


def test_postgres_sql_translation():
    assert dbase.Database._pg_sql("SELECT * FROM t WHERE a=? AND b LIKE '%x'") == \
        "SELECT * FROM t WHERE a=%s AND b LIKE '%%x'"
    ddl = dbase.Database._pg_ddl("order_ref INTEGER PRIMARY KEY AUTOINCREMENT, expires_at REAL NOT NULL, x REAL,")
    assert "SERIAL PRIMARY KEY" in ddl and "AUTOINCREMENT" not in ddl and "DOUBLE PRECISION NOT NULL" in ddl


def test_remote_file_served_by_signed_redirect(monkeypatch, tmp_path):
    import importlib, sys
    from fastapi.testclient import TestClient
    monkeypatch.setenv("DB_PATH", str(tmp_path / "s.db"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "up"))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    import server
    server = importlib.reload(server)
    http = FakeHTTP(200, json.dumps({"signedURL": "/object/sign/bkt/v1.mp4?token=t"}).encode())
    monkeypatch.setattr(server, "store", blobstore.SupabaseStore("https://x.supabase.co", "k", "bkt", request=http))
    server.q("INSERT INTO files (file_id, filename, mime, kind, path, size, created_at) VALUES (?,?,?,?,?,?,?)",
             ("v1", "v.mp4", "video/mp4", "video", "sb:v1.mp4", 5, "now"), write=True)
    r = TestClient(server.app).get("/api/files/v1", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "https://x.supabase.co/storage/v1/object/sign/bkt/v1.mp4?token=t"
    assert TestClient(server.app).get("/api/files/missing").status_code == 404


def test_spa_served_from_same_origin_without_exposing_api_or_parents(monkeypatch, tmp_path):
    import importlib
    from fastapi.testclient import TestClient
    dist = tmp_path / "dist"; (dist / "static").mkdir(parents=True)
    (dist / "index.html").write_text("<html>app</html>")
    (dist / "static" / "a.js").write_text("js")
    (tmp_path / "secret.txt").write_text("nope")
    monkeypatch.setenv("FRONTEND_DIST", str(dist))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "s.db"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "up"))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    import server
    server = importlib.reload(server)
    c = TestClient(server.app)
    assert "app" in c.get("/dashboard").text           # client-side route -> index.html
    assert c.get("/static/a.js").text == "js"
    assert "nope" not in c.get("/../secret.txt").text and "nope" not in c.get("/%2e%2e/secret.txt").text
    r = c.get("/api/nothing")
    assert r.status_code == 404 and r.json()["detail"]  # API misses stay JSON 404
    assert c.post("/dashboard").status_code in (404, 405)
    monkeypatch.delenv("FRONTEND_DIST")


def test_production_cookies_are_secure(monkeypatch, tmp_path):
    import importlib
    from fastapi.testclient import TestClient
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "p.db"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "up"))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    import server
    server = importlib.reload(server)
    r = TestClient(server.app, base_url="https://testserver").post(
        "/api/auth/register", json={"name": "A", "email": "a@example.com", "password": "Passw0rd!long"})
    assert r.status_code in (200, 201), r.text
    assert all("Secure" in h for h in r.headers.get_list("set-cookie")), r.headers.get_list("set-cookie")
    monkeypatch.delenv("APP_ENV")
