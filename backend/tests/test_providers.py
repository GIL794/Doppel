"""Provider adapters: real request-building code, tested with fake transports -
no network, no credentials. The default local build must stay on the honest
simulated paths; configured paths must call the real provider endpoints."""
import hashlib
import hmac as hmac_mod
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
              "SCRIPT_PROVIDER", "GEMINI_API_KEY", "SMTP_HOST", "STRIPE_WEBHOOK_SECRET"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    db_path = "/tmp/aipromovids-providers-test.db"
    if os.path.exists(db_path):
        os.unlink(db_path)  # deterministic rows per run (fixed stub session ids)
    monkeypatch.setenv("DB_PATH", db_path)
    monkeypatch.setenv("UPLOAD_DIR", "/tmp/aipromovids-providers-uploads")
    if "server" in sys.modules:
        import server
        return importlib.reload(server)
    import server
    return server


# ---------------------------------------------------------------- stripe
def test_stripe_checkout_builds_real_request():
    captured = {}
    def fake_post(url, *, data=None, json_body=None, headers=None, timeout=60):
        captured.update(url=url, data=data, headers=headers)
        return {"id": "cs_test_1", "url": "https://checkout.stripe.com/c/pay/cs_test_1"}
    out = providers.stripe_create_checkout(
        "sk_test_x", order_ref="7", email="a@b.co",
        origin_url="http://localhost:3000", amount_gbp=350, post=fake_post)
    assert captured["url"] == "https://api.stripe.com/v1/checkout/sessions"
    assert captured["headers"]["Authorization"] == "Bearer sk_test_x"
    assert captured["data"]["line_items[0][price_data][unit_amount]"] == "35000"
    assert captured["data"]["line_items[0][price_data][currency]"] == "gbp"
    assert captured["data"]["metadata[order_ref]"] == "7"
    assert "session_id={CHECKOUT_SESSION_ID}" in captured["data"]["success_url"]
    assert out == {"session_id": "cs_test_1", "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_1"}


def _sig(payload: bytes, secret: str, ts: int) -> str:
    v1 = hmac_mod.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={v1}"


def test_webhook_signature_accepts_valid_rejects_forged_and_stale():
    payload = json.dumps({"type": "checkout.session.completed",
                          "data": {"object": {"id": "cs_test_1"}}}).encode()
    ts = int(time.time())
    event = providers.stripe_verify_webhook(payload, _sig(payload, "whsec_x", ts), "whsec_x")
    assert event["type"] == "checkout.session.completed"
    with pytest.raises(ValueError):
        providers.stripe_verify_webhook(payload, _sig(payload, "whsec_OTHER", ts), "whsec_x")
    with pytest.raises(ValueError):
        providers.stripe_verify_webhook(payload, _sig(payload, "whsec_x", ts - 4000), "whsec_x")
    with pytest.raises(ValueError):
        providers.stripe_verify_webhook(payload, "garbage", "whsec_x")


def test_stripe_configured_flow_and_webhook(monkeypatch):
    server = load(monkeypatch, PAYMENT_PROVIDER="stripe", STRIPE_API_KEY="sk_test_x",
                  STRIPE_WEBHOOK_SECRET="whsec_x")
    monkeypatch.setattr(providers, "stripe_create_checkout", lambda *a, **k: {
        "session_id": "cs_test_real", "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_real"})
    client = TestClient(server.app)
    r = client.post("/api/payments/checkout", json={
        "name": "A", "email": "a@b.co", "company": "C", "origin_url": "http://localhost:3000"})
    assert r.status_code == 201
    body = r.json()
    assert body["session_id"] == "cs_test_real"
    assert body["checkout_url"].startswith("https://checkout.stripe.com/")
    status = client.get("/api/payments/status/cs_test_real").json()
    assert status["provider"] == "stripe"
    assert status["payment_status"] == "pending"  # NOT claimed paid before Stripe confirms

    payload = json.dumps({"type": "checkout.session.completed",
                          "data": {"object": {"id": "cs_test_real", "payment_status": "paid",
                                              "amount_total": 35000, "currency": "gbp"}}}).encode()
    bad = client.post("/api/stripe/webhook", content=payload,
                      headers={"stripe-signature": "t=1,v1=bad"})
    assert bad.status_code == 400
    ok = client.post("/api/stripe/webhook", content=payload,
                     headers={"stripe-signature": _sig(payload, "whsec_x", int(time.time()))})
    assert ok.status_code == 200
    status = client.get("/api/payments/status/cs_test_real").json()
    assert status["payment_status"] == "paid"


def test_stripe_session_failure_marks_order_failed(monkeypatch):
    server = load(monkeypatch, PAYMENT_PROVIDER="stripe", STRIPE_API_KEY="sk_test_x")
    def boom(*a, **k):
        raise RuntimeError("stripe down")
    monkeypatch.setattr(providers, "stripe_create_checkout", boom)
    client = TestClient(server.app)
    r = client.post("/api/payments/checkout", json={
        "name": "A", "email": "a@b.co", "company": "C", "origin_url": "http://localhost:3000"})
    assert r.status_code == 502
    detail = r.json()["detail"]
    assert "could not be verified" in detail  # ambiguity preserved
    assert "No charge was made" not in detail  # never claim what we cannot verify


# ---------------------------------------------------------------- gemini
def test_gemini_adapter_builds_prompt_and_parses():
    captured = {}
    def fake_post(url, *, data=None, json_body=None, headers=None, timeout=60):
        captured.update(url=url, json_body=json_body, headers=headers)
        return {"candidates": [{"content": {"parts": [{"text": "HOOK: Hi\nSCRIPT: Words\nCTA: Go"}]}}]}
    text = providers.gemini_generate_script(
        "gem-key", model="gemini-2.0-flash", business="Bakery", offer="sourdough",
        language="English", vibe="Fun & upbeat", post=fake_post)
    assert "gemini-2.0-flash:generateContent" in captured["url"]
    assert captured["headers"]["x-goog-api-key"] == "gem-key"
    assert "Bakery" in captured["json_body"]["contents"][0]["parts"][0]["text"]
    assert "HOOK:" in captured["json_body"]["system_instruction"]["parts"][0]["text"]
    assert text.startswith("HOOK:")


def test_script_preview_uses_gemini_when_configured(monkeypatch):
    server = load(monkeypatch, SCRIPT_PROVIDER="gemini", GEMINI_API_KEY="gem-key")
    monkeypatch.setattr(providers, "gemini_generate_script",
                        lambda *a, **k: "HOOK: Real AI\nSCRIPT: Generated words\nCTA: Buy")
    assert TestClient(server.app).get("/api").json()["capabilities"]["ai_script"] == "configured"
    r = TestClient(server.app).post("/api/script/preview", json={"business": "Bakery in Leeds"})
    assert r.status_code == 200
    assert "Real AI" in r.text


def test_script_preview_defaults_to_template_and_says_so(monkeypatch):
    server = load(monkeypatch)
    assert TestClient(server.app).get("/api").json()["capabilities"]["ai_script"] == "template"
    r = TestClient(server.app).post("/api/script/preview", json={"business": "Bakery in Leeds"})
    assert r.status_code == 200
    assert "HOOK:" in r.text


# ---------------------------------------------------------------- fal.ai
def test_fal_adapter_polls_and_downloads():
    calls = []
    def fake_post(url, *, data=None, json_body=None, headers=None, timeout=60):
        calls.append(("post", url))
        assert json_body["image_url"].startswith("data:image/png;base64,")
        assert headers["Authorization"] == "Key fal-key"
        return {"request_id": "req1", "status_url": "https://queue.fal.run/x/status/req1",
                "response_url": "https://queue.fal.run/x/requests/req1"}
    def fake_get(url, *, headers=None, timeout=60):
        calls.append(("get", url))
        if url.endswith("/status/req1"):
            return json.dumps({"status": "COMPLETED"}).encode()
        if url.endswith("/requests/req1"):
            return json.dumps({"video": {"url": "https://cdn.fal/v.mp4"}}).encode()
        return b"VIDEOBYTES"
    video = providers.fal_generate_talking_avatar(
        "fal-key", model="veed/fabric-1.0", image_bytes=b"PNG", image_mime="image/png",
        text="Hi there", post=fake_post, get=fake_get, sleep=lambda s: None)
    assert video == b"VIDEOBYTES"


def test_fal_adapter_raises_on_failure():
    def fake_post(url, *, data=None, json_body=None, headers=None, timeout=60):
        return {"request_id": "req1", "status_url": "s", "response_url": "r"}
    def fake_get(url, *, headers=None, timeout=60):
        return json.dumps({"status": "FAILED"}).encode()
    with pytest.raises(RuntimeError):
        providers.fal_generate_talking_avatar(
            "k", model="m", image_bytes=b"x", image_mime="image/png",
            text="t", post=fake_post, get=fake_get, sleep=lambda s: None)


def test_teaser_fails_loudly_without_provider(monkeypatch):
    server = load(monkeypatch)
    assert TestClient(server.app).get("/api").json()["capabilities"]["ai_video"] == "none"


# ---------------------------------------------------------------- email
def test_email_noop_without_smtp():
    assert providers.send_order_email({"host": ""}, to_email="a@b.co", order_ref="1",
                                      amount_gbp=350) is False


def test_email_sends_with_smtp():
    sent = {}
    class FakeMailer:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def login(self, u, p): sent["login"] = (u, p)
        def sendmail(self, frm, to, body): sent["mail"] = (frm, to, body)
    ok = providers.send_order_email(
        {"host": "smtp.example.com", "port": 465, "user": "u", "password": "p",
         "from": "hello@doppelai.example"},
        to_email="a@b.co", order_ref="7", amount_gbp=350, mailer=FakeMailer())
    assert ok is True
    assert sent["login"] == ("u", "p")
    assert sent["mail"][1] == ["a@b.co"]
    assert b"#7" in sent["mail"][2]


def test_email_capability_reports_configuration(monkeypatch):
    server = load(monkeypatch)
    assert TestClient(server.app).get("/api").json()["capabilities"]["email"] == "not_configured"
    server = load(monkeypatch, SMTP_HOST="smtp.example.com")
    assert TestClient(server.app).get("/api").json()["capabilities"]["email"] == "configured"


def _stripe_client(monkeypatch, **env):
    server = load(monkeypatch, PAYMENT_PROVIDER="stripe", STRIPE_API_KEY="sk_test_x",
                  STRIPE_WEBHOOK_SECRET="whsec_x", **env)
    monkeypatch.setattr(providers, "stripe_create_checkout", lambda *a, **k: {
        "session_id": "cs_test_real", "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_real"})
    client = TestClient(server.app)
    client.post("/api/payments/checkout", json={
        "name": "A", "email": "a@b.co", "company": "C", "origin_url": "http://localhost:3000"})
    return server, client


def _fire(client, event_type, obj):
    payload = json.dumps({"type": event_type, "data": {"object": obj}}).encode()
    return client.post("/api/stripe/webhook", content=payload,
                       headers={"stripe-signature": _sig(payload, "whsec_x", int(time.time()))})


def test_unpaid_completed_does_not_mark_paid(monkeypatch):
    server, client = _stripe_client(monkeypatch)
    # delayed-notification methods complete UNPAID - not proof of payment
    r = _fire(client, "checkout.session.completed",
              {"id": "cs_test_real", "payment_status": "unpaid", "amount_total": 35000, "currency": "gbp"})
    assert r.status_code == 200
    assert client.get("/api/payments/status/cs_test_real").json()["payment_status"] == "pending"


def test_async_payment_succeeded_marks_paid(monkeypatch):
    server, client = _stripe_client(monkeypatch)
    _fire(client, "checkout.session.async_payment_succeeded",
          {"id": "cs_test_real", "amount_total": 35000, "currency": "gbp"})
    assert client.get("/api/payments/status/cs_test_real").json()["payment_status"] == "paid"


def test_duplicate_webhook_sends_exactly_one_email(monkeypatch):
    server, client = _stripe_client(monkeypatch, SMTP_HOST="smtp.example.com")
    calls = []
    monkeypatch.setattr(providers, "send_order_email", lambda *a, **k: calls.append(1) or True)
    obj = {"id": "cs_test_real", "payment_status": "paid", "amount_total": 35000, "currency": "gbp"}
    _fire(client, "checkout.session.completed", obj)
    _fire(client, "checkout.session.completed", obj)  # duplicate delivery
    assert client.get("/api/payments/status/cs_test_real").json()["payment_status"] == "paid"
    assert len(calls) == 1


def test_late_expiry_does_not_downgrade_paid_order(monkeypatch):
    server, client = _stripe_client(monkeypatch)
    _fire(client, "checkout.session.completed",
          {"id": "cs_test_real", "payment_status": "paid", "amount_total": 35000, "currency": "gbp"})
    _fire(client, "checkout.session.expired", {"id": "cs_test_real"})
    assert client.get("/api/payments/status/cs_test_real").json()["payment_status"] == "paid"


def test_amount_or_currency_mismatch_rejected(monkeypatch):
    server, client = _stripe_client(monkeypatch)
    _fire(client, "checkout.session.completed",
          {"id": "cs_test_real", "payment_status": "paid", "amount_total": 100, "currency": "gbp"})
    assert client.get("/api/payments/status/cs_test_real").json()["payment_status"] == "pending"
    _fire(client, "checkout.session.completed",
          {"id": "cs_test_real", "payment_status": "paid", "amount_total": 35000, "currency": "usd"})
    assert client.get("/api/payments/status/cs_test_real").json()["payment_status"] == "pending"


def test_status_liecheck_requires_paid_not_complete(monkeypatch):
    server, client = _stripe_client(monkeypatch)
    monkeypatch.setattr(providers, "stripe_retrieve_session", lambda *a, **k: {
        "payment_status": "unpaid", "status": "complete", "amount_total": 35000, "currency": "gbp"})
    assert client.get("/api/payments/status/cs_test_real").json()["payment_status"] == "pending"
    monkeypatch.setattr(providers, "stripe_retrieve_session", lambda *a, **k: {
        "payment_status": "paid", "status": "complete", "amount_total": 35000, "currency": "gbp"})
    assert client.get("/api/payments/status/cs_test_real").json()["payment_status"] == "paid"


def test_mock_checkout_never_sends_real_email_even_with_smtp(monkeypatch):
    server = load(monkeypatch, SMTP_HOST="smtp.example.com")
    calls = []
    monkeypatch.setattr(providers, "send_order_email", lambda *a, **k: calls.append(1) or True)
    client = TestClient(server.app)
    r = client.post("/api/payments/checkout", json={
        "name": "A", "email": "a@b.co", "company": "C", "origin_url": "http://localhost:3000"})
    assert r.status_code == 201
    assert r.json()["checkout_url"].startswith("http://localhost:3000/payment/success")
    assert calls == []  # simulated payment -> no real email, ever
