"""The /api capability flags drive the frontend's honesty labels, so each
combination must report exactly what is connected - never claim real from
absence, never clear unrelated labels."""
import importlib
import os
import sys

import pytest
from fastapi.testclient import TestClient


def load(monkeypatch, **env):
    for k in ("PAYMENT_PROVIDER", "STRIPE_API_KEY", "TEASER_PROVIDER"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("DB_PATH", "/tmp/aipromovids-flags-test.db")
    monkeypatch.setenv("UPLOAD_DIR", "/tmp/aipromovids-flags-uploads")
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
        "payments": "mock", "ai_video": "none",
        "email": "not_configured", "google_auth": "unavailable"}


def test_real_payments_do_not_clear_other_demo_flags(monkeypatch):
    server = load(monkeypatch, PAYMENT_PROVIDER="stripe", STRIPE_API_KEY="sk_test_x")
    d = flags(server)
    c = d["capabilities"]
    assert c["payments"] == "stripe"
    assert c["ai_video"] == "none"
    assert c["email"] == "not_configured"
    assert c["google_auth"] == "unavailable"
    assert d["demo"] is True  # still demo overall


def test_status_endpoint_reports_order_provider(monkeypatch):
    server = load(monkeypatch)
    client = TestClient(server.app)
    r = client.post("/api/payments/checkout", json={
        "name": "A", "email": "a@b.co", "company": "C", "origin_url": "http://localhost:3000"})
    sid = r.json()["session_id"]
    status = client.get(f"/api/payments/status/{sid}").json()
    assert status["provider"] == "mock"
    assert status["payment_status"] == "paid"
