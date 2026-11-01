"""
DoppelAI backend - REBUILT from scratch (original app "Doppel" on Emergent).

This is NOT the original backend. The original lives in the Emergent workspace
and is not exportable on the free plan. This replacement was written to match
the exact API contract the recovered frontend expects (endpoints, payload
shapes, cookie auth), derived from the recovered frontend source.

Honest scope notes (see docs/RECOVERY.md):
- Auth, uploads/files, orders, admin, mock checkout, script preview and the
  teaser lifecycle all work locally against SQLite.
- Payments run in MOCK mode by default (no real charge, no Stripe calls).
- Teaser avatar videos need an external AI video provider; with none
  configured, teasers fail with an explicit explanation instead of pretending.
- Google sign-in uses standard Google OAuth (authorization-code flow) and is
  OFF unless the owner registers a Google OAuth client and sets
  GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET; the original's Emergent-hosted auth
  is not reusable. Email/password auth works with no external service.
- Paid orders follow the workflow the original site promised ("You approve the
  script before we render"): verified payment -> in production -> script sent
  for approval -> customer approves or requests changes -> delivered. The
  render itself is manual/operator work, as in the original; nothing claims
  automated video delivery.
"""
import hashlib
import hmac
import json
import logging
import os
import secrets
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel, EmailStr, Field

import blobstore
import dbase
import providers

# ---------------------------------------------------------------- config
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.environ.get("DB_PATH", str(BASE_DIR / "data" / "app.db"))
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", str(BASE_DIR / "uploads")))
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
PAYMENT_PROVIDER = os.environ.get("PAYMENT_PROVIDER", "mock")  # mock | stripe
# APP_ENV=production closes the simulated checkout: a public deployment must
# never mark orders "paid" without a real charge. Default stays "development".
APP_ENV = os.environ.get("APP_ENV", "development").strip().lower()
COOKIE_SECURE = APP_ENV == "production"  # HTTPS-only cookies in a real deployment
# Optional: serve the built React app from this same server (one origin, so
# cookies need no cross-site settings). Set FRONTEND_DIST to the build folder.
FRONTEND_DIST = os.environ.get("FRONTEND_DIST", "")
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
SCRIPT_PROVIDER = os.environ.get("SCRIPT_PROVIDER", "template")  # template | gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")  # the owner picked Gemini 3 Flash in the original build chat (2026-10-29);
# model code verified against Google's docs on 2026-10-29:
# https://ai.google.dev/gemini-api/docs/models/gemini-3-flash-preview
TEASER_PROVIDER = os.environ.get("TEASER_PROVIDER", "none")     # none | fal
FAL_KEY = os.environ.get("FAL_KEY", "")
FAL_MODEL = os.environ.get("FAL_MODEL", "veed/fabric-1.0/text")  # text-driven talking-avatar endpoint.
# Verified 2026-10-29 against the official fal.ai docs (schema + pricing):
# https://fal.ai/models/veed/fabric-1.0/text/llms.txt - billed per second of
# video ($0.08/s at 480p, $0.15/s at 720p when checked); each render costs money.
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER)
EMAIL_PROVIDER = "smtp" if SMTP_HOST else "not_configured"
# Paid-order automation (script draft + video render + delivery). OFF by default:
# turning it on lets paid orders trigger Gemini and fal.ai calls that cost money.
ORDER_AUTOMATION = os.environ.get("ORDER_AUTOMATION", "off").lower() == "on"
FREE_TEASERS = int(os.environ.get("FREE_TEASERS", "2"))
ORDER_PRICE_GBP = int(os.environ.get("ORDER_PRICE_GBP", "350"))
ADMIN_EMAILS = {e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()}
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
BACKEND_ORIGIN = os.environ.get("BACKEND_ORIGIN", "http://localhost:8000").rstrip("/")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", f"{BACKEND_ORIGIN}/api/auth/google/callback")
ACCESS_TTL = 15 * 60
REFRESH_TTL = 30 * 24 * 3600
RESET_TTL = 3600
MAX_UPLOAD = 10 * 1024 * 1024
ALLOWED_IMAGE = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("aipromovids")

# DATABASE_URL (postgres://...) switches to PostgreSQL; unset keeps local SQLite.
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

db = dbase.Database(DB_PATH, DATABASE_URL)
store = blobstore.make_store(UPLOAD_DIR, os.environ)
db.script(
    """
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'customer',
        email_verified INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY, user_id TEXT NOT NULL, kind TEXT NOT NULL,
        expires_at REAL NOT NULL, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS files (
        file_id TEXT PRIMARY KEY, filename TEXT, mime TEXT, kind TEXT,
        path TEXT, size INTEGER, owner_user_id TEXT, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS orders (
        order_ref INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT UNIQUE, user_id TEXT, name TEXT, email TEXT, company TEXT,
        language TEXT, avatar_style TEXT, brief TEXT,
        photo_file_id TEXT, logo_file_id TEXT,
        amount_gbp INTEGER, provider TEXT,
        payment_status TEXT NOT NULL DEFAULT 'initiated',
        status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL,
        production_status TEXT NOT NULL DEFAULT 'awaiting_payment',
        script_text TEXT, change_note TEXT, delivered_note TEXT,
        production_updated_at TEXT);
    CREATE TABLE IF NOT EXISTS teasers (
        teaser_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, photo_file_id TEXT,
        text TEXT, voice_description TEXT, status TEXT NOT NULL DEFAULT 'processing',
        video_file_id TEXT, error TEXT, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS password_resets (
        token TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires_at REAL NOT NULL,
        used INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS script_previews (
        id TEXT PRIMARY KEY, business TEXT, offer TEXT, language TEXT, vibe TEXT,
        created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS oauth_states (
        state TEXT PRIMARY KEY, next TEXT NOT NULL DEFAULT '/dashboard',
        expires_at REAL NOT NULL, created_at TEXT NOT NULL);
    """
)


def _ensure_column(table, name, ddl):
    db.ensure_column(table, name, ddl)  # no-op when the column already exists


_ensure_column("users", "email_verified", "INTEGER NOT NULL DEFAULT 0")
_ensure_column("files", "owner_user_id", "TEXT")
_ensure_column("orders", "provider", "TEXT")
_ensure_column("orders", "video_job", "TEXT NOT NULL DEFAULT 'none'")  # none|submitting|done|failed
_ensure_column("orders", "video_file_id", "TEXT")
_ensure_column("orders", "video_error", "TEXT")
_ensure_column("orders", "video_request_id", "TEXT")     # fal queue request id (persisted right after submit)
_ensure_column("orders", "video_request_model", "TEXT")  # fal model the request was submitted to
_ensure_column("orders", "production_status", "TEXT NOT NULL DEFAULT 'awaiting_payment'")
_ensure_column("orders", "script_text", "TEXT")
_ensure_column("orders", "change_note", "TEXT")
_ensure_column("orders", "delivered_note", "TEXT")
_ensure_column("orders", "production_updated_at", "TEXT")
db.run("UPDATE orders SET production_status='in_production' WHERE payment_status='paid' AND production_status='awaiting_payment'", commit=True)


def now():
    return datetime.now(timezone.utc).isoformat()


def q(sql, args=(), one=False, write=False):
    rows, _ = db.run(sql, args, commit=write)
    if one:
        return rows[0] if rows else None
    return rows


# ---------------------------------------------------------------- auth
def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return f"{salt}${digest}"


def check_password(password, stored):
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False  # passwordless account (e.g. created via Google OAuth)
    return hmac.compare_digest(hash_password(password, salt).split("$", 1)[1], digest)


def new_session(user_id, kind, ttl):
    token = secrets.token_urlsafe(32)
    q("INSERT INTO sessions (token, user_id, kind, expires_at, created_at) VALUES (?,?,?,?,?)",
      (token, user_id, kind, time.time() + ttl, now()), write=True)
    return token


def set_auth_cookies(resp, user_id):
    resp.set_cookie("access_token", new_session(user_id, "access", ACCESS_TTL),
                    httponly=True, samesite="lax", secure=COOKIE_SECURE, max_age=ACCESS_TTL)
    resp.set_cookie("refresh_token", new_session(user_id, "refresh", REFRESH_TTL),
                    httponly=True, samesite="lax", secure=COOKIE_SECURE, max_age=REFRESH_TTL)


def user_public(row):
    return {"id": row["id"], "name": row["name"], "email": row["email"],
            "role": row["role"], "created_at": row["created_at"]}


def user_from_token(token, kind):
    if not token:
        return None
    row = q("SELECT * FROM sessions WHERE token=? AND kind=?", (token, kind), one=True)
    if not row or row["expires_at"] < time.time():
        return None
    return q("SELECT * FROM users WHERE id=?", (row["user_id"],), one=True)


def current_user(request: Request):
    user = user_from_token(request.cookies.get("access_token"), "access")
    if not user:
        raise HTTPException(401, "Not signed in")
    return user


def admin_user(user=Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(403, "Admins only")
    return user


def apply_admin_flag(user):
    if user["email"].lower() in ADMIN_EMAILS and user["role"] != "admin":
        q("UPDATE users SET role='admin' WHERE id=?", (user["id"],), write=True)
        user = q("SELECT * FROM users WHERE id=?", (user["id"],), one=True)
    return user


# ---------------------------------------------------------------- schemas
class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ForgotIn(BaseModel):
    email: EmailStr
    origin_url: str | None = None


class ResetIn(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=200)


class GoogleSessionIn(BaseModel):
    session_id: str | None = None


class CheckoutIn(BaseModel):
    name: str
    email: EmailStr
    company: str
    language: str = "English"
    avatar_style: str = "Looks like me"
    brief: str | None = ""
    photo_file_id: str | None = None
    logo_file_id: str | None = None
    origin_url: str | None = None


class TeaserIn(BaseModel):
    photo_file_id: str
    text: str = Field(min_length=5, max_length=180)
    voice_description: str | None = Field(default=None, max_length=120)


class ScriptSubmitIn(BaseModel):
    script_text: str = Field(min_length=10, max_length=5000)


class ChangeRequestIn(BaseModel):
    note: str = Field(min_length=3, max_length=1000)


class DeliverIn(BaseModel):
    note: str = Field(default="", max_length=1000)


class ScriptIn(BaseModel):
    business: str = Field(min_length=3, max_length=300)
    offer: str | None = Field(default="", max_length=300)
    language: str = "English"
    vibe: str = "Fun & upbeat"


# ---------------------------------------------------------------- app
app = FastAPI(title="DoppelAI API (rebuilt)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in FRONTEND_ORIGIN.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api")
def root():
    # Per-capability honesty flags: the frontend labels itself from these, so a
    # capability only stops being called "demo" when it is genuinely connected.
    capabilities = {
        "payments": (("stripe" if STRIPE_API_KEY else "misconfigured")
                     if PAYMENT_PROVIDER == "stripe"
                     else "closed" if (APP_ENV == "production" and PAYMENT_PROVIDER == "mock")
                     else PAYMENT_PROVIDER),
        "ai_video": "configured" if (TEASER_PROVIDER == "fal" and FAL_KEY) else "none",
        "order_automation": "on" if (_automation_script_ready() or _automation_video_ready()) else "off",
        "ai_script": "configured" if (SCRIPT_PROVIDER == "gemini" and GEMINI_API_KEY) else "template",
        "email": "configured" if EMAIL_PROVIDER == "smtp" else "not_configured",
        "google_auth": "configured" if (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET) else "not_configured",
    }
    demo = any(v in ("mock", "none", "template", "not_configured", "misconfigured", "closed")
               for v in capabilities.values())
    return {"app": "DoppelAI API", "status": "ok", "demo": demo,
            "capabilities": capabilities,
            "note": "rebuilt backend (see docs/RECOVERY.md)"}


# ---------------------------------------------------------------- auth routes
@app.post("/api/auth/register", status_code=201)
def register(body: RegisterIn, response: Response):
    email = body.email.lower()
    if q("SELECT id FROM users WHERE email=?", (email,), one=True):
        raise HTTPException(409, "An account with this email already exists")
    uid = uuid.uuid4().hex
    # Password registration proves no email ownership, so it can never grant
    # admin - ADMIN_EMAILS promotion happens only on a verified-email path
    # (Google OAuth) or out-of-band (existing admin / direct DB change).
    q("INSERT INTO users (id, name, email, password_hash, role, email_verified, created_at) VALUES (?,?,?,?,?,0,?)",
      (uid, body.name.strip(), email, hash_password(body.password), "customer", now()), write=True)
    user = q("SELECT * FROM users WHERE id=?", (uid,), one=True)
    set_auth_cookies(response, uid)
    return user_public(user)


@app.post("/api/auth/login")
def login(body: LoginIn, response: Response):
    user = q("SELECT * FROM users WHERE email=?", (body.email.lower(),), one=True)
    if not user or not check_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Wrong email or password")
    set_auth_cookies(response, user["id"])
    return user_public(user)


@app.post("/api/auth/logout")
def logout(request: Request, response: Response):
    for name, kind in (("access_token", "access"), ("refresh_token", "refresh")):
        token = request.cookies.get(name)
        if token:
            q("DELETE FROM sessions WHERE token=?", (token,), write=True)
        response.delete_cookie(name)
    return {"ok": True}


@app.get("/api/auth/me")
def me(user=Depends(current_user)):
    return user_public(user)


@app.post("/api/auth/refresh")
def refresh(request: Request, response: Response):
    user = user_from_token(request.cookies.get("refresh_token"), "refresh")
    if not user:
        raise HTTPException(401, "Session expired")
    response.set_cookie("access_token", new_session(user["id"], "access", ACCESS_TTL),
                        httponly=True, samesite="lax", secure=COOKIE_SECURE, max_age=ACCESS_TTL)
    return user_public(user)


@app.post("/api/auth/forgot-password")
def forgot_password(body: ForgotIn):
    user = q("SELECT * FROM users WHERE email=?", (body.email.lower(),), one=True)
    if user:
        token = secrets.token_urlsafe(32)
        q("INSERT INTO password_resets (token, user_id, expires_at, created_at) VALUES (?,?,?,?)",
          (token, user["id"], time.time() + RESET_TTL, now()), write=True)
        # Always the server-configured origin: a client-supplied origin_url
        # would let anyone email a victim a genuine token on an attacker host.
        link = f"{FRONTEND_ORIGIN}/reset-password?token={token}"
        if EMAIL_PROVIDER == "smtp":
            try:
                providers.send_password_reset_email(_smtp_cfg(), to_email=user["email"], reset_link=link)
            except Exception:
                log.exception("password reset email failed")
        else:
            # No SMTP configured: the reset link is logged, not emailed.
            log.info("PASSWORD RESET LINK for %s: %s", user["email"], link)
    return {"ok": True}


@app.post("/api/auth/reset-password")
def reset_password(body: ResetIn):
    row = q("SELECT * FROM password_resets WHERE token=? AND used=0", (body.token,), one=True)
    if not row or row["expires_at"] < time.time():
        raise HTTPException(400, "That reset link is invalid or has expired")
    q("UPDATE users SET password_hash=? WHERE id=?", (hash_password(body.password), row["user_id"]), write=True)
    q("UPDATE password_resets SET used=1 WHERE token=?", (body.token,), write=True)
    return {"ok": True}


@app.get("/api/auth/google/login")
def google_login(next: str = "/dashboard"):
    """Standard Google OAuth2 authorization-code flow (off unless the owner
    registers a Google OAuth client and sets GOOGLE_CLIENT_ID/SECRET)."""
    if not (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET):
        return RedirectResponse(f"{FRONTEND_ORIGIN}/login?google=unavailable", status_code=302)
    if not next.startswith("/") or next.startswith("//"):
        next = "/dashboard"
    state = secrets.token_urlsafe(24)
    q("INSERT INTO oauth_states (state, next, expires_at, created_at) VALUES (?,?,?,?)",
      (state, next, time.time() + 600, now()), write=True)
    resp = RedirectResponse(
        providers.google_authorization_url(GOOGLE_CLIENT_ID, GOOGLE_REDIRECT_URI, state),
        status_code=302)
    # Bind the state to this browser so a captured callback URL cannot log a
    # victim into the attacker's account.
    resp.set_cookie("gstate", state, httponly=True, samesite="lax", secure=COOKIE_SECURE, max_age=600)
    return resp


@app.get("/api/auth/google/callback")
def google_callback(request: Request, code: str = "", state: str = ""):
    fail = RedirectResponse(f"{FRONTEND_ORIGIN}/login?google=failed", status_code=302)
    fail.delete_cookie("gstate")
    cookie = request.cookies.get("gstate", "")
    if not cookie or not hmac.compare_digest(cookie, state):
        return fail  # state not bound to this browser
    row = q("SELECT * FROM oauth_states WHERE state=?", (state,), one=True)
    if not row or row["expires_at"] < time.time() or not code:
        return fail
    q("DELETE FROM oauth_states WHERE state=?", (state,), write=True)
    try:
        tokens = providers.google_exchange_code(
            GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, code, GOOGLE_REDIRECT_URI)
        info = providers.google_fetch_userinfo(tokens["access_token"])
    except Exception:
        log.exception("google oauth exchange failed")
        return fail
    email = (info.get("email") or "").lower()
    if not email or info.get("email_verified") not in (True, "true"):
        log.warning("google oauth: unverified or missing email")
        return fail
    # Google verified this email ownership, so the account is marked verified
    # and ADMIN_EMAILS promotion is safe to apply on this path only.
    user = q("SELECT * FROM users WHERE email=?", (email,), one=True)
    if not user:
        uid = uuid.uuid4().hex
        q("INSERT INTO users (id, name, email, password_hash, role, email_verified, created_at) VALUES (?,?,?,?,?,1,?)",
          (uid, (info.get("name") or email.split("@")[0])[:120], email,
           "!google-oauth", "customer", now()), write=True)
        user = q("SELECT * FROM users WHERE id=?", (uid,), one=True)
    elif not user["email_verified"]:
        # Linking moment: Google just proved ownership of an email whose
        # password account anyone could have registered (squatting). Revoke
        # every pre-verification credential - password, live sessions, and
        # outstanding reset tokens - so only this Google session survives.
        # If the owner wants a password afterwards, the reset flow now reaches
        # the verified inbox.
        q("UPDATE users SET email_verified=1, password_hash='!google-oauth' WHERE id=?",
          (user["id"],), write=True)
        q("DELETE FROM sessions WHERE user_id=?", (user["id"],), write=True)
        q("UPDATE password_resets SET used=1 WHERE user_id=?", (user["id"],), write=True)
        user = q("SELECT * FROM users WHERE id=?", (user["id"],), one=True)
    user = apply_admin_flag(user)
    resp = RedirectResponse(f"{FRONTEND_ORIGIN}{row['next']}", status_code=302)
    resp.delete_cookie("gstate")
    set_auth_cookies(resp, user["id"])
    return resp


@app.post("/api/auth/google/session")
def google_session(body: GoogleSessionIn):
    raise HTTPException(
        501,
        "This endpoint belonged to Emergent's hosted auth in the original app. "
        "This build uses standard Google OAuth via /api/auth/google/login "
        "(off until the owner configures a Google OAuth client), or email and password.",
    )


# ---------------------------------------------------------------- files
@app.post("/api/uploads", status_code=201)
def upload(file: UploadFile = File(...), kind: str = Form("photo"), user=Depends(current_user)):
    if file.content_type not in ALLOWED_IMAGE:
        raise HTTPException(400, "Please choose a JPG, PNG or WEBP image")
    data = file.file.read()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(400, "Image must be under 10 MB")
    fid = uuid.uuid4().hex
    ext = ALLOWED_IMAGE[file.content_type]
    try:
        path = store.put(f"{fid}{ext}", data, file.content_type)
    except Exception:
        log.exception("upload storage failed")
        raise HTTPException(503, "Could not store the file right now. Please try again.")
    q("INSERT INTO files (file_id, filename, mime, kind, path, size, owner_user_id, created_at) VALUES (?,?,?,?,?,?,?,?)",
      (fid, file.filename, file.content_type, kind, path, len(data), user["id"], now()), write=True)
    return {"file_id": fid, "filename": file.filename, "mime": file.content_type, "size": len(data)}


@app.get("/api/files/{file_id}")
def get_file(file_id: str):
    row = q("SELECT * FROM files WHERE file_id=?", (file_id,), one=True)
    if not row:
        raise HTTPException(404, "File not found")
    if row["path"].startswith(blobstore.REMOTE_PREFIX):
        # Remote object: redirect to a short-lived signed URL (Range/seek handled there).
        if not store.remote:
            raise HTTPException(404, "File not found")
        try:
            return RedirectResponse(store.signed_url(row["path"]), status_code=302)
        except Exception:
            log.exception("signing storage url failed")
            raise HTTPException(404, "File not found")
    if not Path(row["path"]).exists():
        raise HTTPException(404, "File not found")
    return FileResponse(row["path"], media_type=row["mime"])


def _read_file_bytes(row):
    """Bytes of a stored file, whether it lives on local disk or in remote storage."""
    if row["path"].startswith(blobstore.REMOTE_PREFIX):
        return store.get(row["path"])
    return Path(row["path"]).read_bytes()


# ---------------------------------------------------------------- payments & orders
# ------------------------------------------------- optional order automation
# Pipeline design chosen by the builder (not a detailed owner spec): paid order ->
# Gemini drafts the script -> customer approves it (still required) -> fal.ai renders
# the avatar video -> file stored -> order marked delivered and emailed.
# Safety rules: off unless ORDER_AUTOMATION=on and keys exist; automatic
# drafting/rendering only touches orders with a VERIFIED real (Stripe) payment,
# never a mock-paid order; each paid step is claimed atomically so it runs at
# most once; the fal request id is persisted immediately after submit so
# restarts resume polling the SAME job (polling is free) instead of paying
# twice; a failed or ambiguous provider call is NEVER retried automatically -
# the order falls back to the manual admin path with the error recorded, and
# only an explicit admin action re-runs it. Reconciling an already-submitted
# job (poll/download only) stays available with just FAL_KEY.
# video_job states: none -> submitting -> submitted -> done | failed.
def _claim(sql, args):
    _, n = db.run(sql, args, commit=True)
    return n == 1


def _spawn(fn, *args):
    threading.Thread(target=fn, args=args, daemon=True).start()


def _automation_script_ready():
    return ORDER_AUTOMATION and SCRIPT_PROVIDER == "gemini" and bool(GEMINI_API_KEY)


def _automation_video_ready():
    return ORDER_AUTOMATION and TEASER_PROVIDER == "fal" and bool(FAL_KEY)


def _real_paid(order):
    """A paid order is only automation-eligible when the payment was VERIFIED
    real money: the Stripe fulfillment path is the only one that sets
    payment_status='paid' on a provider='stripe' order. A mock order
    (provider='mock', marked paid without charging) must never trigger a
    billable Gemini/fal call, even with automation on and keys set."""
    return bool(order) and order["payment_status"] == "paid" and order["provider"] == "stripe"


def _auto_draft_script(order_ref):
    if not _automation_script_ready():
        return
    order = q("SELECT * FROM orders WHERE order_ref=?", (order_ref,), one=True)
    prev = order["production_status"] if order else None
    if prev not in ("in_production", "changes_requested") or not _real_paid(order):
        return
    if not _claim("UPDATE orders SET production_status='drafting', production_updated_at=? "
                  "WHERE order_ref=? AND production_status=?", (now(), order_ref, prev)):
        return  # someone else is already drafting
    try:
        offer = order["brief"] or ""
        if prev == "changes_requested" and order["change_note"]:
            offer += f"\nCustomer requested these changes to the previous script: {order['change_note']}"
        text = providers.gemini_generate_script(
            GEMINI_API_KEY, model=GEMINI_MODEL, business=order["company"] or order["name"],
            offer=offer, language=order["language"] or "English", vibe=order["avatar_style"] or "")
        q("UPDATE orders SET script_text=?, production_status='script_ready', production_updated_at=? "
          "WHERE order_ref=?", (text.strip(), now(), order_ref), write=True)
        _maybe_send(providers.send_script_ready_email, to_email=order["email"],
                    order_ref=order_ref, dashboard_url=f"{FRONTEND_ORIGIN}/dashboard")
    except Exception:
        log.exception("automatic script draft failed for order %s; back to manual", order_ref)
        q("UPDATE orders SET production_status=?, production_updated_at=? WHERE order_ref=?",
          (prev, now(), order_ref), write=True)


def _spoken_text(script):
    lines = []
    for part in (script or "").splitlines():
        part = part.strip()
        for label in ("HOOK:", "SCRIPT:", "CTA:"):
            if part.upper().startswith(label):
                part = part[len(label):].strip()
        if part:
            lines.append(part)
    return " ".join(lines)


def _auto_render(order_ref):
    """Submit the paid render exactly once, persist the provider request id,
    then finish. Split so a restart never resubmits a billed job."""
    if not _automation_video_ready():
        return
    order = q("SELECT * FROM orders WHERE order_ref=?", (order_ref,), one=True)
    if not order or order["production_status"] != "script_approved" or not order["photo_file_id"]:
        return
    if not _real_paid(order):
        return  # never spend provider money on a simulated payment
    if not _claim("UPDATE orders SET video_job='submitting', video_error=NULL "
                  "WHERE order_ref=? AND video_job='none'", (order_ref,)):
        return  # already submitted once: never submit (and pay) twice
    f = q("SELECT * FROM files WHERE file_id=?", (order["photo_file_id"],), one=True)
    try:
        image = _read_file_bytes(f)
        image_mime = f["mime"]
    except Exception:
        log.exception("photo for order %s unreadable; back to manual", order_ref)
        q("UPDATE orders SET video_job='failed', video_error=? WHERE order_ref=?",
          ("The uploaded photo could not be read, so no video job was submitted "
           "(nothing was billed).", order_ref), write=True)
        return
    try:
        job = providers.fal_submit_job(
            FAL_KEY, model=FAL_MODEL, image_bytes=image,
            image_mime=image_mime, text=_spoken_text(order["script_text"]))
    except Exception as e:
        # Ambiguous: the submit may or may not have reached fal and been billed.
        log.exception("automatic render submit failed for order %s", order_ref)
        q("UPDATE orders SET video_job='failed', video_error=? WHERE order_ref=?",
          (f"Automatic video submit failed ({type(e).__name__}); it may or may not have "
           "reached the provider or been billed. Check the provider dashboard before any "
           "manual retry.", order_ref), write=True)
        return
    # The request id is durably stored BEFORE any polling, so a restart resumes
    # this exact job instead of paying for a new one.
    q("UPDATE orders SET video_job='submitted', video_request_id=?, video_request_model=? "
      "WHERE order_ref=?", (job["request_id"], FAL_MODEL, order_ref), write=True)
    _finish_render(order_ref, job)


def _finish_render(order_ref, job):
    """Poll an already-submitted (already billed) job and deliver the video.
    Polling and downloading are free, so this may safely run again after a
    restart or an admin reconcile - it never submits a new job."""
    try:
        video = providers.fal_wait_for_video(
            FAL_KEY, status_url=job["status_url"], response_url=job["response_url"])
    except RuntimeError as e:
        # The provider itself reported the job failed/cancelled - NOT ambiguous.
        log.exception("provider reported render failure for order %s", order_ref)
        q("UPDATE orders SET video_job='failed', video_error=? WHERE order_ref=?",
          (f"The provider reported the video job failed ({e}). Check the provider "
           "dashboard; if it was not billed, use the admin render retry.", order_ref), write=True)
        return
    except Exception as e:
        # Lost contact while polling (network, timeout, or a restart killed the
        # thread). The job exists and its request id is stored - keep it
        # 'submitted' and resume later; do NOT resubmit (that would bill twice).
        log.exception("lost contact with render for order %s; stays resumable", order_ref)
        q("UPDATE orders SET video_error=? WHERE order_ref=?",
          (f"Lost contact with the submitted video job ({type(e).__name__}). The job is still "
           "at the provider; polling resumes on restart or via admin reconcile. No new job "
           "was submitted.", order_ref), write=True)
        return
    # Exactly one finisher wins this claim, so duplicate resumes cannot store
    # the file twice, deliver twice, or email twice.
    if not _claim("UPDATE orders SET video_job='done', video_error=NULL "
                  "WHERE order_ref=? AND video_job='submitted' AND production_status='script_approved'",
                  (order_ref,)):
        return
    try:
        order = q("SELECT * FROM orders WHERE order_ref=?", (order_ref,), one=True)
        vid = uuid.uuid4().hex
        vpath = store.put(f"{vid}.mp4", video, "video/mp4")
        q("""INSERT INTO files (file_id, filename, mime, kind, path, size, owner_user_id, created_at)
             VALUES (?,?,?,?,?,?,?,?)""",
          (vid, f"promo-{order_ref}.mp4", "video/mp4", "video", vpath,
           len(video), order["user_id"], now()), write=True)
        note = "Your video is ready in your studio."
        q("""UPDATE orders SET video_file_id=?, production_status='delivered',
             delivered_note=?, production_updated_at=? WHERE order_ref=?""",
          (vid, note, now(), order_ref), write=True)
        _maybe_send(providers.send_delivery_email, to_email=order["email"], order_ref=order_ref, note=note)
    except Exception:
        # Local storage failed after the video rendered. Roll back to
        # 'submitted' so a reconcile re-downloads the finished video (free)
        # instead of resubmitting a paid job.
        log.exception("storing finished video failed for order %s", order_ref)
        q("UPDATE orders SET video_job='submitted', video_error=? WHERE order_ref=?",
          ("The video rendered at the provider but storing it locally failed. Re-fetching "
           "the finished file is free; use admin reconcile to finish delivery.", order_ref),
          write=True)


def _recover_interrupted_work():
    """Restart recovery for the paid pipeline. Safe cases only:
    - video_job 'submitted' (request id stored): resume polling the SAME job
      (polling is free, no new charge).
    - video_job 'submitting' (died before/at the submit, no request id): the
      submit may or may not have reached the provider - mark failed for MANUAL
      review. Never auto-resubmit a possibly-billed job.
    - production_status 'drafting' (died mid-draft): the draft never reached
      the customer, so reset to in_production and draft again (one extra
      Gemini call; the customer approval gate still applies)."""
    # Resuming/flagging existing jobs is free (polling only, or a status
    # change), so it runs whenever the provider key exists - even if the owner
    # turned ORDER_AUTOMATION off after the job was submitted. Only NEW paid
    # submits are gated on the automation flag.
    if FAL_KEY:
        for row in q("SELECT order_ref, video_request_id, video_request_model FROM orders "
                     "WHERE video_job IN ('submitting','submitted')"):
            if row["video_request_id"]:
                model = row["video_request_model"] or FAL_MODEL
                rid = row["video_request_id"]
                job = {"request_id": rid,
                       "status_url": f"https://queue.fal.run/{model}/requests/{rid}/status",
                       "response_url": f"https://queue.fal.run/{model}/requests/{rid}"}
                log.info("restart: resuming polling of submitted video job for order %s",
                         row["order_ref"])
                _spawn(_finish_render, row["order_ref"], job)
            else:
                q("UPDATE orders SET video_job='failed', video_error=? WHERE order_ref=?",
                  ("The server stopped while the video job was being submitted; it may or may "
                   "not have reached the provider or been billed. Check the provider dashboard; "
                   "if it was not billed, use the admin render retry.", row["order_ref"]),
                  write=True)
                log.warning("restart: order %s died mid-submit; marked failed for manual review",
                            row["order_ref"])
    if _automation_script_ready():
        stuck = q("SELECT order_ref FROM orders WHERE production_status='drafting' "
                  "AND payment_status='paid' AND provider='stripe'")
        for row in stuck:
            if _claim("UPDATE orders SET production_status='in_production', production_updated_at=? "
                      "WHERE order_ref=? AND production_status='drafting'", (now(), row["order_ref"])):
                log.info("restart: resuming interrupted script draft for order %s", row["order_ref"])
                _spawn(_auto_draft_script, row["order_ref"])


_spawn(_recover_interrupted_work)


@app.post("/api/payments/checkout", status_code=201)
def checkout(body: CheckoutIn, request: Request):
    if APP_ENV == "production" and PAYMENT_PROVIDER == "mock":
        raise HTTPException(503, "Ordering is not open yet.")
    if PAYMENT_PROVIDER != "mock" and not STRIPE_API_KEY:
        raise HTTPException(503, "Card payments are not configured in this build (set STRIPE_API_KEY).")
    user = user_from_token(request.cookies.get("access_token"), "access")
    session_id = uuid.uuid4().hex
    # Redirect targets are always the server-configured origin, never a
    # client-supplied one (a payment URL must not bounce through attacker hosts).
    origin = FRONTEND_ORIGIN
    checkout_url = None
    # MOCK payment provider: no real charge. The order is marked paid immediately
    # and the "checkout" redirects straight to the success page, mirroring the
    # original Stripe round-trip. A real Stripe adapter is included and
    # activates with PAYMENT_PROVIDER=stripe + owner-supplied keys.
    q("""INSERT INTO orders (session_id, user_id, name, email, company, language, avatar_style,
         brief, photo_file_id, logo_file_id, amount_gbp, provider, payment_status, status, created_at)
         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
      (session_id, user["id"] if user else None, body.name, body.email.lower(), body.company,
       body.language, body.avatar_style, body.brief, body.photo_file_id, body.logo_file_id,
       ORDER_PRICE_GBP, PAYMENT_PROVIDER, "paid" if PAYMENT_PROVIDER == "mock" else "pending",
       "open", now()), write=True)
    order_ref = str(q("SELECT order_ref FROM orders WHERE session_id=?", (session_id,), one=True)["order_ref"])
    if PAYMENT_PROVIDER == "stripe":
        # REAL charge path - only when explicitly configured with a key the
        # owner supplied. Never exercised in the default local build.
        try:
            sess = providers.stripe_create_checkout(
                STRIPE_API_KEY, order_ref=order_ref, email=body.email.lower(),
                origin_url=origin, amount_gbp=ORDER_PRICE_GBP)
        except Exception:
            # Ambiguous outcome: the request may or may not have reached Stripe.
            # Never claim "no charge was made" - we cannot verify that here.
            # A Checkout Session can only collect payment if the customer
            # completes it, and this customer never received a URL, but the
            # order is still preserved for reconciliation instead of retried
            # blindly (each retry creates a NEW session; no auto-retry).
            q("UPDATE orders SET status='failed', payment_status='unknown' WHERE session_id=?",
              (session_id,), write=True)
            log.exception("stripe checkout session creation failed")
            raise HTTPException(
                502,
                "Could not reach the payment provider, so checkout did not start. "
                "Whether a checkout session was created could not be verified; "
                "no payment page was shown. Please contact us before retrying.")
        session_id = sess["session_id"]
        checkout_url = sess["checkout_url"]
        q("UPDATE orders SET session_id=? WHERE order_ref=?", (session_id, order_ref), write=True)
    if PAYMENT_PROVIDER == "mock":
        # Simulated path: marked paid immediately, no charge. NEVER sends a
        # real confirmation email - a simulated payment must not trigger real
        # email even when SMTP is configured.
        q("UPDATE orders SET production_status='in_production', production_updated_at=? WHERE session_id=?",
          (now(), session_id), write=True)
        checkout_url = f"{origin}/payment/success?session_id={session_id}"
        # No automation spawn here: a mock payment is not real money, and
        # _auto_draft_script refuses non-verified payments anyway.
    return {"checkout_url": checkout_url, "session_id": session_id}


def _smtp_cfg():
    return {"host": SMTP_HOST, "port": SMTP_PORT, "user": SMTP_USER,
            "password": SMTP_PASSWORD, "from": SMTP_FROM}


def _maybe_send(fn, **kwargs):
    """Send a transactional email through the configured adapter. No-op when
    SMTP is not configured; failures are logged, never hidden as success."""
    if EMAIL_PROVIDER != "smtp":
        return False
    try:
        return fn(_smtp_cfg(), **kwargs)
    except Exception:
        log.exception("transactional email failed")
        return False


def _maybe_send_order_email(to_email, order_ref):
    return _maybe_send(providers.send_order_email, to_email=to_email,
                       order_ref=order_ref, amount_gbp=ORDER_PRICE_GBP)


def _mark_order_paid(session_id, amount_total=None, currency=None):
    """Idempotent fulfillment: only a verified paid Stripe session for THIS
    stripe order, at the expected amount and currency, transitions the order -
    and only that transition sends the confirmation email. Duplicate webhook
    deliveries do nothing. Returns True only when the order moved to paid."""
    order = q("SELECT * FROM orders WHERE session_id=?", (session_id,), one=True)
    if not order or order["provider"] != "stripe":
        log.warning("paid-event for unknown/non-stripe session %s", session_id)
        return False
    # Fail closed: the event must carry the expected amount and currency -
    # a missing field is treated as a mismatch, never waved through.
    if amount_total != ORDER_PRICE_GBP * 100:
        log.error("amount mismatch for %s: %r != %s", session_id, amount_total, ORDER_PRICE_GBP * 100)
        return False
    if str(currency or "").lower() != "gbp":
        log.error("currency mismatch for %s: %r", session_id, currency)
        return False
    if order["payment_status"] == "paid":
        return False  # duplicate delivery: no re-update, no second email
    q("""UPDATE orders SET payment_status='paid', status='complete',
         production_status='in_production', production_updated_at=?
         WHERE session_id=? AND payment_status!='paid'""", (now(), session_id), write=True)
    _maybe_send_order_email(order["email"], order["order_ref"])
    if _automation_script_ready():
        _spawn(_auto_draft_script, order["order_ref"])
    return True


@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(503, "Stripe webhook not configured")
    payload = await request.body()
    try:
        event = providers.stripe_verify_webhook(
            payload, request.headers.get("stripe-signature", ""), STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(400, "Invalid webhook signature")
    obj, t = event.get("data", {}).get("object", {}), event.get("type")
    sid = obj.get("id", "")
    # checkout.session.completed can be UNPAID for delayed-notification payment
    # methods (per Stripe's fulfillment docs) - it is not proof of payment.
    if t == "checkout.session.completed":
        if obj.get("payment_status") == "paid":
            _mark_order_paid(sid, obj.get("amount_total"), obj.get("currency"))
    elif t == "checkout.session.async_payment_succeeded":
        _mark_order_paid(sid, obj.get("amount_total"), obj.get("currency"))
    elif t == "checkout.session.async_payment_failed":
        q("""UPDATE orders SET payment_status='failed', status='failed'
             WHERE session_id=? AND payment_status NOT IN ('paid')""", (sid,), write=True)
    elif t == "checkout.session.expired":
        # a late expiry event must never downgrade an already-paid order
        q("""UPDATE orders SET payment_status='expired', status='expired'
             WHERE session_id=? AND payment_status NOT IN ('paid')""", (sid,), write=True)
    return {"status": "ok"}


@app.get("/api/payments/status/{session_id}")
def payment_status(session_id: str):
    order = q("SELECT * FROM orders WHERE session_id=?", (session_id,), one=True)
    if not order:
        raise HTTPException(404, "Unknown checkout session")
    if order["provider"] == "stripe" and order["payment_status"] == "pending" and STRIPE_API_KEY:
        # live-check Stripe for a session whose webhook has not arrived yet.
        # "complete" is NOT proof of payment (delayed methods complete unpaid) -
        # only payment_status == "paid" with the expected amount/currency is.
        try:
            sess = providers.stripe_retrieve_session(STRIPE_API_KEY, session_id)
            if sess.get("payment_status") == "paid":
                _mark_order_paid(session_id, sess.get("amount_total"), sess.get("currency"))
                order = q("SELECT * FROM orders WHERE session_id=?", (session_id,), one=True)
        except Exception:
            log.exception("stripe session retrieve failed")
    # provider is what this order was actually created with (None = unknown,
    # e.g. orders predating the column); the frontend must not relabel it from
    # current config.
    status_map = {"paid": "complete", "expired": "expired", "failed": "failed"}
    return {"session_id": session_id, "payment_status": order["payment_status"],
            "status": status_map.get(order["payment_status"], "open"),
            "order_ref": order["order_ref"], "provider": order["provider"]}


@app.get("/api/orders/mine")
def my_orders(user=Depends(current_user)):
    # Guest orders attach to an account by email ONLY when that email's
    # ownership was verified (Google path) - a matching string alone proves
    # nothing on the password path.
    if user["email_verified"]:
        rows = q("""SELECT * FROM orders WHERE payment_status='paid' AND (user_id=? OR email=?)
                    ORDER BY order_ref DESC""", (user["id"], user["email"]))
    else:
        rows = q("SELECT * FROM orders WHERE payment_status='paid' AND user_id=? ORDER BY order_ref DESC",
                 (user["id"],))
    return [dict(r) for r in rows]


# ------------------------------------------------- paid-order production loop
# The original site promised: "You approve the script before we render." The
# render itself was manual operator work (the original app tracked only
# payment status and hardcoded "In production"). This workflow makes the
# promised approval loop real; it never claims automated video delivery.
PRODUCTION_FLOW = ("awaiting_payment", "in_production", "script_ready",
                   "changes_requested", "script_approved", "delivered")


def _order_or_404(order_ref):
    order = q("SELECT * FROM orders WHERE order_ref=?", (order_ref,), one=True)
    if not order:
        raise HTTPException(404, "Unknown order")
    return order


def _own_order(order, user):
    if order["user_id"] == user["id"]:
        return
    if user["email_verified"] and order["email"].lower() == user["email"].lower():
        return
    raise HTTPException(403, "That order belongs to a different account")


@app.post("/api/admin/orders/{order_ref}/script")
def admin_submit_script(order_ref: int, body: ScriptSubmitIn, user=Depends(admin_user)):
    order = _order_or_404(order_ref)
    if order["payment_status"] != "paid":
        raise HTTPException(409, "Scripts can only be sent for paid orders")
    if order["production_status"] not in ("in_production", "changes_requested"):
        raise HTTPException(409, f"Order is not awaiting a script (status: {order['production_status']})")
    q("""UPDATE orders SET script_text=?, production_status='script_ready',
         production_updated_at=? WHERE order_ref=?""",
      (body.script_text.strip(), now(), order_ref), write=True)
    email_sent = _maybe_send(providers.send_script_ready_email, to_email=order["email"],
                             order_ref=order_ref, dashboard_url=f"{FRONTEND_ORIGIN}/dashboard")
    return {"ok": True, "production_status": "script_ready", "email_sent": bool(email_sent)}


@app.post("/api/orders/{order_ref}/script/approve")
def approve_script(order_ref: int, user=Depends(current_user)):
    order = _order_or_404(order_ref)
    _own_order(order, user)
    if order["production_status"] != "script_ready":
        raise HTTPException(409, "There is no script awaiting your approval on this order")
    q("""UPDATE orders SET production_status='script_approved',
         production_updated_at=? WHERE order_ref=?""", (now(), order_ref), write=True)
    if _automation_video_ready():
        _spawn(_auto_render, order_ref)
    return {"ok": True, "production_status": "script_approved"}


@app.post("/api/orders/{order_ref}/script/changes")
def request_script_changes(order_ref: int, body: ChangeRequestIn, user=Depends(current_user)):
    order = _order_or_404(order_ref)
    _own_order(order, user)
    if order["production_status"] != "script_ready":
        raise HTTPException(409, "There is no script awaiting your review on this order")
    q("""UPDATE orders SET production_status='changes_requested', change_note=?,
         production_updated_at=? WHERE order_ref=?""",
      (body.note.strip(), now(), order_ref), write=True)
    if _automation_script_ready():
        _spawn(_auto_draft_script, order_ref)
    return {"ok": True, "production_status": "changes_requested"}


@app.post("/api/admin/orders/{order_ref}/deliver")
def admin_deliver_order(order_ref: int, body: DeliverIn, user=Depends(admin_user)):
    order = _order_or_404(order_ref)
    if order["production_status"] != "script_approved":
        raise HTTPException(409, "Only orders with an approved script can be marked delivered")
    q("""UPDATE orders SET production_status='delivered', delivered_note=?,
         production_updated_at=? WHERE order_ref=?""",
      (body.note.strip(), now(), order_ref), write=True)
    email_sent = _maybe_send(providers.send_delivery_email, to_email=order["email"],
                             order_ref=order_ref, note=body.note.strip())
    return {"ok": True, "production_status": "delivered", "email_sent": bool(email_sent)}


@app.post("/api/admin/orders/{order_ref}/render/retry")
def admin_retry_render(order_ref: int, user=Depends(admin_user)):
    """Reviewed manual recovery for a FAILED render. Only run this after
    checking the provider dashboard and confirming the failed job was not
    billed: it resets the job state so the normal single-submit automation
    runs once more (a new, separately billed job)."""
    order = _order_or_404(order_ref)
    if not _real_paid(order):
        raise HTTPException(409, "Automatic rendering only runs for verified real payments")
    if order["production_status"] != "script_approved":
        raise HTTPException(409, "Only orders with an approved script can be re-rendered")
    if order["video_job"] != "failed":
        raise HTTPException(409, f"Retry only applies to a failed video job (state: {order['video_job']})")
    if not _automation_video_ready():
        raise HTTPException(503, "Automatic rendering is not configured")
    q("""UPDATE orders SET video_job='none', video_error=NULL, video_request_id=NULL,
         video_request_model=NULL WHERE order_ref=?""", (order_ref,), write=True)
    log.info("admin %s approved a render retry for order %s", user["email"], order_ref)
    _spawn(_auto_render, order_ref)
    return {"ok": True, "video_job": "none"}


@app.post("/api/admin/orders/{order_ref}/render/reconcile")
def admin_reconcile_render(order_ref: int, user=Depends(admin_user)):
    """Re-check a SUBMITTED render with the provider now. Polling and
    downloading the finished video are free; this never submits a new job."""
    order = _order_or_404(order_ref)
    if order["video_job"] != "submitted" or not order["video_request_id"]:
        raise HTTPException(409, "This order has no submitted video job to reconcile")
    # Reconcile only polls/downloads the already-submitted job (free, no new
    # paid submit), so it stays available when ORDER_AUTOMATION is off - it is
    # the manual completion path for a job that automation already started.
    if not FAL_KEY:
        raise HTTPException(503, "Reconciling needs FAL_KEY to query the provider")
    model = order["video_request_model"] or FAL_MODEL
    rid = order["video_request_id"]
    job = {"request_id": rid,
           "status_url": f"https://queue.fal.run/{model}/requests/{rid}/status",
           "response_url": f"https://queue.fal.run/{model}/requests/{rid}"}
    log.info("admin %s reconciled the submitted render for order %s", user["email"], order_ref)
    _spawn(_finish_render, order_ref, job)
    return {"ok": True, "video_job": "submitted"}


# ---------------------------------------------------------------- teasers
def _finish_teaser(teaser_id):
    if TEASER_PROVIDER == "fal" and FAL_KEY:
        # Real generation path - only when the owner supplies a fal.ai key.
        try:
            t = q("SELECT * FROM teasers WHERE teaser_id=?", (teaser_id,), one=True)
            f = q("SELECT * FROM files WHERE file_id=?", (t["photo_file_id"],), one=True)
            data = _read_file_bytes(f)
            video = providers.fal_generate_talking_avatar(
                FAL_KEY, model=FAL_MODEL, image_bytes=data,
                image_mime=f["mime"], text=t["text"])
            vid = uuid.uuid4().hex
            vpath = store.put(f"{vid}.mp4", video, "video/mp4")
            q("""INSERT INTO files (file_id, filename, mime, kind, path, size, created_at)
                 VALUES (?,?,?,?,?,?,?)""",
              (vid, "teaser.mp4", "video/mp4", "video", vpath, len(video), now()), write=True)
            q("UPDATE teasers SET status='done', video_file_id=? WHERE teaser_id=?",
              (vid, teaser_id), write=True)
            return
        except Exception as e:
            q("UPDATE teasers SET status='failed', error=? WHERE teaser_id=?",
              (f"Video generation failed: {e}", teaser_id), write=True)
            return
    time.sleep(6)
    # No AI video provider is wired in this build: fail loudly instead of
    # pretending a video was generated.
    q("UPDATE teasers SET status='failed', error=? WHERE teaser_id=? AND status='processing'",
      ("Avatar video generation needs an external AI provider, which is not configured in this local build.",
       teaser_id), write=True)


@app.get("/api/teasers")
def list_teasers(user=Depends(current_user)):
    rows = q("SELECT * FROM teasers WHERE user_id=? ORDER BY created_at DESC", (user["id"],))
    remaining = max(0, FREE_TEASERS - len(rows))
    return {"items": [dict(r) for r in rows], "remaining": remaining}


@app.post("/api/teasers", status_code=201)
def create_teaser(body: TeaserIn, user=Depends(current_user)):
    count = len(q("SELECT teaser_id FROM teasers WHERE user_id=?", (user["id"],)))
    if count >= FREE_TEASERS:
        raise HTTPException(400, "You've used your free teasers. Order a full video to keep going.")
    photo = q("SELECT file_id, owner_user_id FROM files WHERE file_id=?", (body.photo_file_id,), one=True)
    if not photo or photo["owner_user_id"] != user["id"]:
        raise HTTPException(400, "Upload a clear, front-facing photo first")
    tid = uuid.uuid4().hex
    q("""INSERT INTO teasers (teaser_id, user_id, photo_file_id, text, voice_description, status, created_at)
         VALUES (?,?,?,?,?,'processing',?)""",
      (tid, user["id"], body.photo_file_id, body.text, body.voice_description, now()), write=True)
    threading.Thread(target=_finish_teaser, args=(tid,), daemon=True).start()
    return {"teaser_id": tid, "status": "processing"}


# ---------------------------------------------------------------- script preview (SSE)
SCRIPT_TEMPLATE = (
    "HOOK: Meet {business} - the easiest way to {offer_line}without the hassle.\n"
    "SCRIPT: Running {business} keeps you busy. You want customers to see what makes you special, "
    "but filming yourself feels awkward and hiring a crew costs a fortune. So we built a shortcut: "
    "a friendly presenter who introduces your business, {vibe_line}. {offer_sentence}"
    "Short, sharp, and ready to share anywhere your customers are.\n"
    "CTA: Ready to put a face to {business}? Order your promo video today."
)


@app.post("/api/script/preview")
def script_preview(body: ScriptIn):
    q("INSERT INTO script_previews (id, business, offer, language, vibe, created_at) VALUES (?,?,?,?,?,?)",
      (uuid.uuid4().hex, body.business, body.offer, body.language, body.vibe, now()), write=True)
    offer = (body.offer or "").strip()
    if SCRIPT_PROVIDER == "gemini" and GEMINI_API_KEY:
        # Real AI path - only when the owner supplies a Gemini key.
        try:
            text = providers.gemini_generate_script(
                GEMINI_API_KEY, model=GEMINI_MODEL, business=body.business.strip(),
                offer=offer, language=body.language, vibe=body.vibe)
            return _script_sse(text)
        except Exception:
            log.exception("gemini script generation failed; falling back to template")
    text = SCRIPT_TEMPLATE.format(
        business=body.business.strip(),
        offer_line=f"share \"{offer}\" " if offer else "stand out ",
        vibe_line=f"in a {body.vibe.lower()} style" if body.vibe else "",
        offer_sentence=f"Right now: {offer}." if offer else "",
    )
    if body.language != "English":
        text += f"\n\n(Preview generated in English; the finished video is delivered in {body.language}.)"

    return _script_sse(text)


def _script_sse(text):
    def stream():
        # Streams any script text (templated stand-in or Gemini output) in the
        # HOOK / SCRIPT / CTA format the recovered frontend parses.
        for i in range(0, len(text), 24):
            yield f"data: {json.dumps({'delta': text[i:i + 24]})}\n\n"
            time.sleep(0.02)
        yield "data: {\"done\": true}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


# ---------------------------------------------------------------- admin
@app.get("/api/admin/overview")
def admin_overview(user=Depends(admin_user)):
    paid = q("SELECT COUNT(*) c, COALESCE(SUM(amount_gbp),0) rev FROM orders WHERE payment_status='paid'", one=True)
    return {
        "revenue_gbp": paid["rev"],
        "paid_orders": paid["c"],
        "started_checkouts": q("SELECT COUNT(*) c FROM orders", one=True)["c"],
        "customers": q("SELECT COUNT(*) c FROM users", one=True)["c"],
        "teasers": q("SELECT COUNT(*) c FROM teasers", one=True)["c"],
        "scripts": q("SELECT COUNT(*) c FROM script_previews", one=True)["c"],
    }


@app.get("/api/admin/orders")
def admin_orders(user=Depends(admin_user)):
    rows = q("SELECT * FROM orders ORDER BY order_ref DESC")
    return [dict(r) for r in rows]


@app.exception_handler(404)
async def not_found(request, exc):
    if FRONTEND_DIST and request.method == "GET" and not request.url.path.startswith("/api"):
        root = Path(FRONTEND_DIST).resolve()
        rel = request.url.path.lstrip("/")
        target = (root / rel).resolve()
        if rel and root in target.parents and target.is_file():
            return FileResponse(target)
        index = root / "index.html"
        if index.is_file():
            return FileResponse(index)  # single-page app: client router handles the path
    return JSONResponse({"detail": getattr(exc, "detail", "Not found")}, status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))

