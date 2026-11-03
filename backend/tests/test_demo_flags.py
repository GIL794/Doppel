"""The /api capability flags drive the frontend's honesty labels, so each
combination must report exactly what is connected - never claim real from
absence, never clear unrelated labels."""
import importlib
import os
import sys

import pytest
from fastapi.testclient import TestClient


def load(monkeypatch, **env):
    for k in ("PAYMENT_PROVIDER", "STRIPE_API_KEY", "TEASER_PROVIDER", "FAL_KEY",
              "SCRIPT_PROVIDER", "GEMINI_API_KEY", "SMTP_HOST", "STRIPE_WEBHOOK_SECRET"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("DB_PATH", "C:/Users/Gabriele/AppData/Local/Temp/aipromovids-flags-test.db")
    monkeypatch.setenv("UPLOAD_DIR", "C:/Users/Gabriele/AppData/Local/Temp/aipromovids-flags-uploads")
    if "server" in sys.modules:
        import server
        return importlib.reload(server)
    import server
    return server


def flags(server):
    return TestClient(server.app).get("/api").json()


def test_default_build_reports_everything_not_connected(monkeypatch):
    server = load(monkeypatch)
    d = flags(server)
    assert d["demo"] is True
    assert d["capabilities"] == {
        "payments": "mock", "ai_video": "none", "ai_script": "template",
        "email": "not_configured", "google_auth": "not_configured",
        "order_automation": "off"}


def test_real_payments_do_not_clear_other_demo_flags(monkeypatch):
    server = load(monkeypatch, PAYMENT_PROVIDER="stripe", STRIPE_API_KEY="sk_test_x")
    d = flags(server)
    c = d["capabilities"]
    assert c["payments"] == "stripe"
    assert c["ai_video"] == "none"
    assert c["email"] == "not_configured"
    assert c["google_auth"] == "not_configured"
    assert d["demo"] is True  # still demo overall


def test_status_endpoint_reports_order_provider(monkeypatch):
    server = load(monkeypatch)
    client = TestClient(server.app)
    r = client.post("/api/payments/checkout", json={
        "name": "A", "email": "a@b.co", "company": "C", "origin_url": "http://localhost:3000", "consent_terms": True, "consent_likeness": True})
    sid = r.json()["session_id"]
    status = client.get(f"/api/payments/status/{sid}").json()
    assert status["provider"] == "mock"
    assert status["payment_status"] == "paid"


def test_provider_persisted_per_order_survives_config_change(monkeypatch):
    """An order created under mock must still say mock after the server is
    restarted with a live provider configured - config never relabels history."""
    server = load(monkeypatch)
    client = TestClient(server.app)
    r = client.post("/api/payments/checkout", json={
        "name": "A", "email": "a@b.co", "company": "C", "origin_url": "http://localhost:3000", "consent_terms": True, "consent_likeness": True})
    sid = r.json()["session_id"]
    assert client.get(f"/api/payments/status/{sid}").json()["provider"] == "mock"

    server2 = load(monkeypatch, PAYMENT_PROVIDER="stripe", STRIPE_API_KEY="sk_test_x")
    client2 = TestClient(server2.app)
    status = client2.get(f"/api/payments/status/{sid}").json()
    assert status["provider"] == "mock"  # unchanged


def test_order_without_provider_reports_null_not_current_config(monkeypatch):
    """Orders predating the provider column (or otherwise unknown) report
    provider null; the frontend must treat that as unverified."""
    server = load(monkeypatch)
    import uuid
    from server import q, now
    sid = uuid.uuid4().hex
    q("""INSERT INTO orders (session_id, name, email, company, amount_gbp, provider,
         payment_status, status, created_at) VALUES (?,?,?,?,?,?,?,?,?)""",
      (sid, "Old", "old@b.co", "OldCo", 350, None, "paid", "open", now()), write=True)
    status = TestClient(server.app).get(f"/api/payments/status/{sid}").json()
    assert status["provider"] is None
    assert status["payment_status"] == "paid"



def test_production_env_refuses_mock_checkout(monkeypatch):
    """A public deployment must never mark orders paid without a real charge."""
    monkeypatch.setenv("APP_ENV", "production")
    server = load(monkeypatch)
    c = TestClient(server.app)
    r = c.post("/api/payments/checkout", json={
        "name": "A", "email": "a@example.com", "company": "Co", "language": "en",
        "avatar_style": "professional", "brief": "x" * 40, "consent_terms": True, "consent_likeness": True})
    assert r.status_code == 503
    assert "not open" in r.json()["detail"].lower()
    assert c.get("/api").json()["capabilities"]["payments"] == "closed"
    monkeypatch.delenv("APP_ENV", raising=False)
