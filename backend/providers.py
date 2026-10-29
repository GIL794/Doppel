"""Real provider adapters for the DoppelAI rebuild.

Every adapter is OFF unless its env config is present; the default local build
runs fully on the honest simulated paths. Each adapter takes an injectable
`post`/`opener` transport so tests can exercise the real request-building code
without any network or credentials. No credentials are shipped in this repo.
"""
import base64
import hashlib
import hmac
import json
import smtplib
import time
import urllib.parse
import urllib.request


def _http_post(url, *, data=None, json_body=None, headers=None, timeout=60):
    body = None
    hdrs = dict(headers or {})
    if json_body is not None:
        body = json.dumps(json_body).encode()
        hdrs["Content-Type"] = "application/json"
    elif data is not None:
        body = urllib.parse.urlencode(data).encode()
        hdrs["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=body, headers=hdrs, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw or b"{}")


def _http_get(url, *, headers=None, timeout=60):
    req = urllib.request.Request(url, headers=dict(headers or {}))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


# ---------------------------------------------------------------- Stripe
def stripe_create_checkout(api_key, *, order_ref, email, origin_url, amount_gbp, post=_http_post):
    """Create a real Stripe Checkout Session for the £350 promo video.
    Mirrors the original build: one fixed-price digital product, success/cancel
    URLs back to the frontend, order_ref in metadata."""
    origin = origin_url.rstrip("/")
    resp = post(
        "https://api.stripe.com/v1/checkout/sessions",
        data={
            "mode": "payment",
            "customer_email": email,
            "line_items[0][price_data][currency]": "gbp",
            "line_items[0][price_data][unit_amount]": str(int(amount_gbp * 100)),
            "line_items[0][price_data][product_data][name]": "DoppelAI promo video",
            "line_items[0][quantity]": "1",
            "success_url": f"{origin}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{origin}/payment/cancel",
            "metadata[order_ref]": order_ref,
        },
        headers={"Authorization": f"Bearer {api_key}"},
    )
    return {"session_id": resp["id"], "checkout_url": resp["url"]}


def stripe_retrieve_session(api_key, session_id, get=_http_get):
    raw = get(
        f"https://api.stripe.com/v1/checkout/sessions/{urllib.parse.quote(session_id)}",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    return json.loads(raw)


def stripe_verify_webhook(payload: bytes, sig_header: str, secret: str, tolerance=300) -> dict:
    """Manual Stripe webhook signature verification (no stripe SDK dependency)."""
    parts = dict(p.split("=", 1) for p in sig_header.split(",") if "=" in p)
    ts, sig = parts.get("t"), parts.get("v1")
    if not ts or not sig:
        raise ValueError("malformed Stripe-Signature header")
    expected = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise ValueError("bad webhook signature")
    if tolerance and abs(time.time() - int(ts)) > tolerance:
        raise ValueError("stale webhook timestamp")
    return json.loads(payload)


# ---------------------------------------------------------------- Google OAuth
# Standard Google OAuth2 authorization-code flow. Requires an owner-registered
# OAuth client (GOOGLE_CLIENT_ID/SECRET) - the original's Emergent-hosted auth
# is not reusable. Endpoint shapes per Google's published OAuth documentation.
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def google_authorization_url(client_id, redirect_uri, state):
    qs = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    })
    return f"{GOOGLE_AUTH_URL}?{qs}"


def google_exchange_code(client_id, client_secret, code, redirect_uri, post=_http_post):
    return post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
    )


def google_fetch_userinfo(access_token, get=_http_get):
    return json.loads(get(GOOGLE_USERINFO_URL,
                          headers={"Authorization": f"Bearer {access_token}"}))


# ---------------------------------------------------------------- Gemini
# System prompt recovered from the original build's chat export (spec material).
SCRIPT_SYSTEM = (
    "You are a top direct-response copywriter writing scripts for short promo videos "
    "presented by an AI avatar talking straight to camera. Write a 30-second script "
    "(70-85 spoken words) that a business owner's avatar will say. Structure: a scroll-stopping hook "
    "in the first line, the problem or desire, what the business offers, one concrete reason to choose it, "
    "and a clear call to action. Output plain text only in exactly this format:\n"
    "HOOK: <one line>\nSCRIPT: <the spoken script>\nCTA: <one short line>\n"
    "Never invent prices, statistics, awards, reviews or years in business. Write in the requested language."
)


def gemini_generate_script(api_key, *, model, business, offer, language, vibe, post=_http_post):
    prompt = (
        f"Business: {business}\n"
        f"What they want to promote: {offer or 'their business in general'}\n"
        f"Language: {language}\nVibe: {vibe}"
    )
    resp = post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        json_body={
            "system_instruction": {"parts": [{"text": SCRIPT_SYSTEM}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        },
        headers={"x-goog-api-key": api_key},
    )
    return resp["candidates"][0]["content"]["parts"][0]["text"]


# ---------------------------------------------------------------- fal.ai
def fal_generate_talking_avatar(api_key, *, model, image_bytes, image_mime, text, post=_http_post,
                                get=_http_get, sleep=time.sleep, max_wait=300):
    """Queue a talking-avatar video on fal.ai (same model family the original
    build used) and return the finished video bytes. Accepts the photo as a
    data URI so locally stored uploads work."""
    data_uri = "data:" + image_mime + ";base64," + base64.b64encode(image_bytes).decode()
    submit = post(
        f"https://queue.fal.run/{model}",
        json_body={"image_url": data_uri, "text": text, "resolution": "480p"},
        headers={"Authorization": f"Key {api_key}"},
    )
    status_url = submit.get("status_url") or f"https://queue.fal.run/{model}/requests/{submit['request_id']}/status"
    response_url = submit.get("response_url") or f"https://queue.fal.run/{model}/requests/{submit['request_id']}"
    waited = 0
    while waited < max_wait:
        status = json.loads(get(status_url, headers={"Authorization": f"Key {api_key}"}))
        state = status.get("status")
        if state == "COMPLETED":
            break
        if state in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"fal generation {state.lower()}")
        sleep(3)
        waited += 3
    else:
        raise TimeoutError("fal generation timed out")
    result = json.loads(get(response_url, headers={"Authorization": f"Key {api_key}"}))
    video_url = (result.get("video") or {}).get("url") or result.get("video_url")
    if not video_url:
        raise RuntimeError("fal result had no video url")
    return get(video_url)


# ---------------------------------------------------------------- email
def _send(cfg, *, to_email, subject, text, mailer=None):
    """Plain-SMTP send. Returns False only when unconfigured; raises on real
    send failure so callers can log it (never reported as delivered)."""
    if not cfg.get("host"):
        return False
    body = (
        f"Subject: {subject}\r\n"
        f"To: {to_email}\r\n"
        f"From: {cfg['from']}\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n\r\n"
        f"{text}"
    )
    if mailer is None:
        mailer = smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=30)
    with mailer as m:
        if cfg.get("user"):
            m.login(cfg["user"], cfg["password"])
        m.sendmail(cfg["from"], [to_email], body.encode())
    return True


def send_order_email(cfg, *, to_email, order_ref, amount_gbp, mailer=None):
    return _send(
        cfg, to_email=to_email, mailer=mailer,
        subject=f"Your DoppelAI order #{order_ref}",
        text=(f"Thanks for your order (#{order_ref}, GBP {amount_gbp}).\n"
              f"We'll be in touch with a script for you to approve before we render.\n"))


def send_password_reset_email(cfg, *, to_email, reset_link, mailer=None):
    return _send(
        cfg, to_email=to_email, mailer=mailer,
        subject="Reset your DoppelAI password",
        text=(f"A password reset was requested for this account.\n"
              f"Open this link within the hour to choose a new password:\n{reset_link}\n"
              f"If you didn't ask for this, you can ignore this email.\n"))


def send_script_ready_email(cfg, *, to_email, order_ref, dashboard_url, mailer=None):
    return _send(
        cfg, to_email=to_email, mailer=mailer,
        subject=f"Your script is ready to approve - order #{order_ref}",
        text=(f"Your script for order #{order_ref} is ready.\n"
              f"Review and approve it (or request changes) in your studio:\n{dashboard_url}\n"
              f"We only render once you've approved the script.\n"))


def send_delivery_email(cfg, *, to_email, order_ref, note, mailer=None):
    extra = f"\nNote from the studio: {note}\n" if note else "\n"
    return _send(
        cfg, to_email=to_email, mailer=mailer,
        subject=f"Your video is ready - order #{order_ref}",
        text=f"Your video for order #{order_ref} has been delivered.{extra}")
