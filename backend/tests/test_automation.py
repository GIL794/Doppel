"""Optional paid-order automation (Gemini script draft, fal.ai render, delivery)
and its restart/admin recovery. Every provider is faked: no network, no
credentials, no spend."""
import importlib
import os
import sys
import time

import pytest
from fastapi.testclient import TestClient

import providers

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
DB = "C:/Users/Gabriele/AppData/Local/Temp/aipromovids-automation-test.db"


def load(monkeypatch, keep_db=False, **env):
    for k in ("PAYMENT_PROVIDER", "STRIPE_API_KEY", "TEASER_PROVIDER", "FAL_KEY", "SCRIPT_PROVIDER",
              "GEMINI_API_KEY", "SMTP_HOST", "ORDER_AUTOMATION", "GEMINI_MODEL", "FAL_MODEL"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("DB_PATH", DB)
    monkeypatch.setenv("UPLOAD_DIR", "C:/Users/Gabriele/AppData/Local/Temp/aipromovids-automation-uploads")
    if "server" in sys.modules:
        import server
        s = importlib.reload(server)
    else:
        import server
        s = server
    if not keep_db:
        for tbl in ("orders", "users", "sessions", "files", "teasers", "password_resets", "script_previews", "oauth_states"):
            try:
                s.q(f"DELETE FROM {tbl}", write=True)
            except Exception:
                pass
    return s


def order_as_customer(server, monkeypatch, real_paid=True):
    captured = []
    monkeypatch.setattr(server, "_spawn", lambda fn, *a: captured.append((fn, a)))
    c = TestClient(server.app)
    c.post("/api/auth/register", json={"name": "C", "email": "c@example.com", "password": "password123"})
    up = c.post("/api/uploads", files={"file": ("me.png", PNG, "image/png")}, data={"kind": "photo"})
    assert up.status_code == 201, up.text
    c.post("/api/payments/checkout", json={"name": "C", "email": "c@example.com", "company": "Bloom",
                                           "brief": "same-day bouquets", "language": "French",
                                           "photo_file_id": up.json()["file_id"], "consent_terms": True, "consent_likeness": True})
    if real_paid:
        # Simulate what the verified Stripe fulfillment path produces and
        # triggers; the mock checkout alone must never qualify for billable
        # automation (and no longer spawns it).
        server.q("UPDATE orders SET provider='stripe'", write=True)
        ref = server.q("SELECT order_ref FROM orders ORDER BY order_ref DESC", one=True)["order_ref"]
        server._auto_draft_script(ref)  # what _mark_order_paid does after a verified payment
    # run anything else that was scheduled, inline and in order
    monkeypatch.setattr(server, "_spawn", lambda fn, *a: fn(*a))
    for fn, a in captured:
        fn(*a)
    return c


def wait_for(predicate, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def make_admin(server, client):
    server.q("UPDATE users SET role='admin'", write=True)
    return client


AUTO = dict(ORDER_AUTOMATION="on", SCRIPT_PROVIDER="gemini", GEMINI_API_KEY="k",
            TEASER_PROVIDER="fal", FAL_KEY="f")

FAKE_JOB = {"request_id": "req1", "status_url": "https://queue.fal.run/x/requests/req1/status",
            "response_url": "https://queue.fal.run/x/requests/req1"}


def fake_fal(monkeypatch, seen, video=b"VIDEO"):
    def fake_submit(key, **k):
        seen["fal_submit"] += 1
        return dict(FAKE_JOB)
    def fake_wait(key, **k):
        seen["fal_wait"] += 1
        return video
    monkeypatch.setattr(providers, "fal_submit_job", fake_submit)
    monkeypatch.setattr(providers, "fal_wait_for_video", fake_wait)


def test_automation_is_off_by_default(monkeypatch):
    server = load(monkeypatch)
    calls = []
    monkeypatch.setattr(providers, "gemini_generate_script", lambda *a, **k: calls.append(1) or "x")
    c = order_as_customer(server, monkeypatch)
    assert calls == []
    assert c.get("/api/orders/mine").json()[0]["production_status"] == "in_production"


def test_default_models_match_verified_provider_docs(monkeypatch):
    server = load(monkeypatch)
    # Owner picked Gemini 3 Flash in the original build chat; ids verified
    # against Google's and fal.ai's official docs on 2026-10-29.
    assert server.GEMINI_MODEL == "gemini-3-flash-preview"
    assert server.FAL_MODEL == "veed/fabric-1.0/text"


def test_full_pipeline_runs_once_and_delivers(monkeypatch):
    server = load(monkeypatch, **AUTO)
    seen = {"gemini": 0, "fal_submit": 0, "fal_wait": 0}
    def fake_gemini(key, **k):
        seen["gemini"] += 1
        assert k["language"] == "French" and k["business"] == "Bloom"
        return "HOOK: Fresh!\nSCRIPT: Bouquets today.\nCTA: Order now."
    monkeypatch.setattr(providers, "gemini_generate_script", fake_gemini)
    fake_fal(monkeypatch, seen)
    c = order_as_customer(server, monkeypatch)
    o = c.get("/api/orders/mine").json()[0]
    # script drafted automatically, but the customer approval gate still applies
    assert o["production_status"] == "script_ready" and seen["fal_submit"] == 0
    ref = o["order_ref"]
    assert c.post(f"/api/orders/{ref}/script/approve").status_code == 200
    o = c.get("/api/orders/mine").json()[0]
    assert o["production_status"] == "delivered" and o["video_job"] == "done" and o["video_file_id"], \
        (o["video_job"], o["video_error"])
    assert o["video_request_id"] == "req1"
    assert seen == {"gemini": 1, "fal_submit": 1, "fal_wait": 1}
    # Duplicate triggers must not pay or deliver again.
    server._auto_render(ref)
    server._finish_render(ref, dict(FAKE_JOB))
    assert seen["fal_submit"] == 1


def test_failed_submit_is_not_retried_and_falls_back_to_manual(monkeypatch):
    server = load(monkeypatch, **AUTO)
    n = {"fal_submit": 0}
    monkeypatch.setattr(providers, "gemini_generate_script", lambda *a, **k: "HOOK: a\nSCRIPT: b\nCTA: c")
    def boom(*a, **k):
        n["fal_submit"] += 1
        raise ConnectionError("network down")
    monkeypatch.setattr(providers, "fal_submit_job", boom)
    c = order_as_customer(server, monkeypatch)
    ref = c.get("/api/orders/mine").json()[0]["order_ref"]
    c.post(f"/api/orders/{ref}/script/approve")
    server._auto_render(ref)
    o = c.get("/api/orders/mine").json()[0]
    assert n["fal_submit"] == 1
    assert o["production_status"] == "script_approved" and o["video_job"] == "failed"
    assert "may or may not have reached the provider or been billed" in o["video_error"]


def test_poll_failure_keeps_job_resumable_without_resubmit(monkeypatch):
    server = load(monkeypatch, **AUTO)
    n = {"fal_submit": 0}
    monkeypatch.setattr(providers, "gemini_generate_script", lambda *a, **k: "HOOK: a\nSCRIPT: b\nCTA: c")
    def submit_ok(key, **k):
        n["fal_submit"] += 1
        return dict(FAKE_JOB)
    monkeypatch.setattr(providers, "fal_submit_job", submit_ok)
    def wait_boom(*a, **k):
        raise TimeoutError("fal generation timed out")
    monkeypatch.setattr(providers, "fal_wait_for_video", wait_boom)
    c = order_as_customer(server, monkeypatch)
    ref = c.get("/api/orders/mine").json()[0]["order_ref"]
    c.post(f"/api/orders/{ref}/script/approve")
    o = c.get("/api/orders/mine").json()[0]
    # request id persisted, still resumable, never resubmitted automatically
    assert o["video_job"] == "submitted" and o["video_request_id"] == "req1"
    assert "still at the provider" in o["video_error"]
    server._auto_render(ref)  # claim only fires from 'none'
    assert n["fal_submit"] == 1


def test_provider_reported_failure_marks_failed(monkeypatch):
    server = load(monkeypatch, **AUTO)
    monkeypatch.setattr(providers, "gemini_generate_script", lambda *a, **k: "HOOK: a\nSCRIPT: b\nCTA: c")
    monkeypatch.setattr(providers, "fal_submit_job", lambda *a, **k: dict(FAKE_JOB))
    def wait_failed(*a, **k):
        raise RuntimeError("fal generation failed")
    monkeypatch.setattr(providers, "fal_wait_for_video", wait_failed)
    c = order_as_customer(server, monkeypatch)
    ref = c.get("/api/orders/mine").json()[0]["order_ref"]
    c.post(f"/api/orders/{ref}/script/approve")
    o = c.get("/api/orders/mine").json()[0]
    assert o["video_job"] == "failed" and "provider reported the video job failed" in o["video_error"]


def test_restart_resumes_submitted_job_without_resubmit(monkeypatch):
    server = load(monkeypatch, **AUTO)
    monkeypatch.setattr(providers, "gemini_generate_script", lambda *a, **k: "HOOK: a\nSCRIPT: b\nCTA: c")
    c = order_as_customer(server, monkeypatch)
    ref = c.get("/api/orders/mine").json()[0]["order_ref"]
    # Simulate a crash mid-poll: job submitted, request id stored, no result yet.
    server.q("""UPDATE orders SET production_status='script_approved', video_job='submitted',
                video_request_id='req1', video_request_model='veed/fabric-1.0/text' WHERE order_ref=?""",
             (ref,), write=True)
    n = {"fal_submit": 0, "fal_wait": 0}
    fake_fal(monkeypatch, n)
    server = load(monkeypatch, keep_db=True, **AUTO)  # "restart"
    # video_job flips to done before the file is stored, so wait for delivery itself.
    assert wait_for(lambda: server.q("SELECT production_status FROM orders WHERE order_ref=?",
                                     (ref,), one=True)["production_status"] == "delivered")
    o = server.q("SELECT * FROM orders WHERE order_ref=?", (ref,), one=True)
    assert o["video_job"] == "done" and o["video_file_id"]
    assert n == {"fal_submit": 0, "fal_wait": 1}  # resumed polling, never resubmitted


def test_restart_mid_submit_without_request_id_marks_failed_not_resubmitted(monkeypatch):
    server = load(monkeypatch, **AUTO)
    monkeypatch.setattr(providers, "gemini_generate_script", lambda *a, **k: "HOOK: a\nSCRIPT: b\nCTA: c")
    c = order_as_customer(server, monkeypatch)
    ref = c.get("/api/orders/mine").json()[0]["order_ref"]
    server.q("""UPDATE orders SET production_status='script_approved', video_job='submitting',
                video_request_id=NULL WHERE order_ref=?""", (ref,), write=True)
    n = {"fal_submit": 0, "fal_wait": 0}
    fake_fal(monkeypatch, n)
    server = load(monkeypatch, keep_db=True, **AUTO)
    assert wait_for(lambda: server.q("SELECT video_job FROM orders WHERE order_ref=?",
                                     (ref,), one=True)["video_job"] == "failed")
    o = server.q("SELECT * FROM orders WHERE order_ref=?", (ref,), one=True)
    assert "may or may not have reached the provider or been billed" in o["video_error"]
    assert n == {"fal_submit": 0, "fal_wait": 0}


def test_restart_resumes_interrupted_script_draft(monkeypatch):
    server = load(monkeypatch, **AUTO)
    monkeypatch.setattr(providers, "gemini_generate_script", lambda *a, **k: "HOOK: a\nSCRIPT: b\nCTA: c")
    c = order_as_customer(server, monkeypatch)
    ref = c.get("/api/orders/mine").json()[0]["order_ref"]
    server.q("UPDATE orders SET production_status='drafting' WHERE order_ref=?", (ref,), write=True)
    server = load(monkeypatch, keep_db=True, **AUTO)
    assert wait_for(lambda: server.q("SELECT production_status FROM orders WHERE order_ref=?",
                                     (ref,), one=True)["production_status"] == "script_ready")


def test_admin_retry_render_reruns_once_after_failure(monkeypatch):
    server = load(monkeypatch, **AUTO)
    monkeypatch.setattr(providers, "gemini_generate_script", lambda *a, **k: "HOOK: a\nSCRIPT: b\nCTA: c")
    monkeypatch.setattr(providers, "fal_submit_job", lambda *a, **k: dict(FAKE_JOB))
    def wait_boom(*a, **k):
        raise RuntimeError("fal generation failed")
    monkeypatch.setattr(providers, "fal_wait_for_video", wait_boom)
    c = order_as_customer(server, monkeypatch)
    ref = c.get("/api/orders/mine").json()[0]["order_ref"]
    assert c.post(f"/api/orders/{ref}/script/approve").status_code == 200
    o = c.get("/api/orders/mine").json()[0]
    ref = o["order_ref"]
    assert o["video_job"] == "failed"
    # a customer cannot retry
    assert c.post(f"/api/admin/orders/{ref}/render/retry").status_code == 403
    # the admin (having checked the provider dashboard) can; the pipeline then
    # runs once more and delivers
    make_admin(server, c)
    monkeypatch.setattr(providers, "fal_wait_for_video", lambda *a, **k: b"VIDEO")
    n = {"fal_submit": 0, "fal_wait": 0}
    fake_fal(monkeypatch, n)
    r = c.post(f"/api/admin/orders/{ref}/render/retry")
    assert r.status_code == 200, r.text
    o = c.get("/api/orders/mine").json()[0]
    assert o["video_job"] == "done" and o["production_status"] == "delivered"
    assert n == {"fal_submit": 1, "fal_wait": 1}


def test_admin_reconcile_finishes_submitted_job(monkeypatch):
    server = load(monkeypatch, **AUTO)
    monkeypatch.setattr(providers, "gemini_generate_script", lambda *a, **k: "HOOK: a\nSCRIPT: b\nCTA: c")
    c = order_as_customer(server, monkeypatch)
    ref = c.get("/api/orders/mine").json()[0]["order_ref"]
    server.q("""UPDATE orders SET production_status='script_approved', video_job='submitted',
                video_request_id='req1', video_request_model='veed/fabric-1.0/text' WHERE order_ref=?""",
             (ref,), write=True)
    n = {"fal_submit": 0, "fal_wait": 0}
    fake_fal(monkeypatch, n)
    make_admin(server, c)
    r = c.post(f"/api/admin/orders/{ref}/render/reconcile")
    assert r.status_code == 200, r.text
    o = c.get("/api/orders/mine").json()[0]
    assert o["video_job"] == "done" and o["production_status"] == "delivered"
    assert n == {"fal_submit": 0, "fal_wait": 1}


def test_failed_script_draft_leaves_order_for_manual_path(monkeypatch):
    server = load(monkeypatch, **AUTO)
    def boom(*a, **k):
        raise RuntimeError("quota")
    monkeypatch.setattr(providers, "gemini_generate_script", boom)
    c = order_as_customer(server, monkeypatch)
    assert c.get("/api/orders/mine").json()[0]["production_status"] == "in_production"


def test_change_request_redrafts_with_the_note(monkeypatch):
    server = load(monkeypatch, **AUTO)
    offers = []
    monkeypatch.setattr(providers, "gemini_generate_script",
                        lambda key, **k: offers.append(k["offer"]) or "HOOK: a\nSCRIPT: b\nCTA: c")
    c = order_as_customer(server, monkeypatch)
    ref = c.get("/api/orders/mine").json()[0]["order_ref"]
    c.post(f"/api/orders/{ref}/script/changes", json={"note": "make it shorter"})
    assert "make it shorter" in offers[-1]
    assert c.get("/api/orders/mine").json()[0]["production_status"] == "script_ready"


def test_mock_paid_order_triggers_zero_provider_calls(monkeypatch):
    """Mock payment + automation ON + keys set: no Gemini, no fal, ever."""
    server = load(monkeypatch, **AUTO)
    n = {"gemini": 0, "fal_submit": 0, "fal_wait": 0}
    monkeypatch.setattr(providers, "gemini_generate_script",
                        lambda *a, **k: n.__setitem__("gemini", n["gemini"] + 1) or "HOOK: a")
    fake_fal(monkeypatch, n)
    c = order_as_customer(server, monkeypatch, real_paid=False)  # stays provider='mock'
    o = c.get("/api/orders/mine").json()[0]
    assert o["production_status"] == "in_production"  # manual path, no auto draft
    ref = o["order_ref"]
    # even after a manual script + customer approval, the mock-paid order must
    # not reach the render provider
    make_admin(server, c)
    assert c.post(f"/api/admin/orders/{ref}/script",
                  json={"script_text": "HOOK: a\nSCRIPT: b\nCTA: c"}).status_code == 200
    assert c.post(f"/api/orders/{ref}/script/approve").status_code == 200
    o = c.get("/api/orders/mine").json()[0]
    assert o["production_status"] == "script_approved" and o["video_job"] == "none"
    assert n == {"gemini": 0, "fal_submit": 0, "fal_wait": 0}
    # and the reviewed retry refuses it explicitly
    server.q("UPDATE orders SET video_job='failed' WHERE order_ref=?", (ref,), write=True)
    r = c.post(f"/api/admin/orders/{ref}/render/retry")
    assert r.status_code == 409 and "verified real payments" in r.json()["detail"]
    assert n == {"gemini": 0, "fal_submit": 0, "fal_wait": 0}


def test_reconcile_allowed_when_automation_off(monkeypatch):
    """Reconcile only polls/downloads the already-submitted job (free), so it
    works with ORDER_AUTOMATION off as long as FAL_KEY is set; it submits
    nothing new."""
    server = load(monkeypatch, FAL_KEY="f")  # automation OFF
    c = order_as_customer(server, monkeypatch, real_paid=False)
    ref = c.get("/api/orders/mine").json()[0]["order_ref"]
    server.q("""UPDATE orders SET production_status='script_approved', video_job='submitted',
                video_request_id='req1', video_request_model='veed/fabric-1.0/text' WHERE order_ref=?""",
             (ref,), write=True)
    n = {"fal_submit": 0, "fal_wait": 0}
    fake_fal(monkeypatch, n)
    make_admin(server, c)
    r = c.post(f"/api/admin/orders/{ref}/render/reconcile")
    assert r.status_code == 200, r.text
    o = c.get("/api/orders/mine").json()[0]
    assert o["video_job"] == "done" and o["production_status"] == "delivered" and o["video_file_id"]
    assert n == {"fal_submit": 0, "fal_wait": 1}  # poll/download only


def test_reconcile_without_fal_key_is_refused(monkeypatch):
    server = load(monkeypatch)  # no FAL_KEY at all
    c = order_as_customer(server, monkeypatch, real_paid=False)
    ref = c.get("/api/orders/mine").json()[0]["order_ref"]
    server.q("""UPDATE orders SET production_status='script_approved', video_job='submitted',
                video_request_id='req1' WHERE order_ref=?""", (ref,), write=True)
    make_admin(server, c)
    r = c.post(f"/api/admin/orders/{ref}/render/reconcile")
    assert r.status_code == 503


def test_restart_resumes_submitted_job_even_when_automation_off(monkeypatch):
    """Boot recovery of an already-submitted job needs only FAL_KEY: turning
    automation off must not strand a job the provider is still holding."""
    server = load(monkeypatch, FAL_KEY="f")
    c = order_as_customer(server, monkeypatch, real_paid=False)
    ref = c.get("/api/orders/mine").json()[0]["order_ref"]
    server.q("""UPDATE orders SET production_status='script_approved', video_job='submitted',
                video_request_id='req1', video_request_model='veed/fabric-1.0/text' WHERE order_ref=?""",
             (ref,), write=True)
    n = {"fal_submit": 0, "fal_wait": 0}
    fake_fal(monkeypatch, n)
    server = load(monkeypatch, keep_db=True, FAL_KEY="f")  # "restart", automation still off
    assert wait_for(lambda: server.q("SELECT video_job FROM orders WHERE order_ref=?",
                                     (ref,), one=True)["video_job"] == "done")
    assert n == {"fal_submit": 0, "fal_wait": 1}


def test_restart_does_not_resume_draft_for_mock_paid_order(monkeypatch):
    server = load(monkeypatch, **AUTO)
    monkeypatch.setattr(providers, "gemini_generate_script", lambda *a, **k: "HOOK: a")
    c = order_as_customer(server, monkeypatch, real_paid=False)
    ref = c.get("/api/orders/mine").json()[0]["order_ref"]
    server.q("UPDATE orders SET production_status='drafting' WHERE order_ref=?", (ref,), write=True)
    server = load(monkeypatch, keep_db=True, **AUTO)
    # give any (buggy) recovery thread a moment, then assert nothing drafted
    assert not wait_for(lambda: server.q("SELECT production_status FROM orders WHERE order_ref=?",
                                         (ref,), one=True)["production_status"] == "script_ready",
                        timeout=1.5)

