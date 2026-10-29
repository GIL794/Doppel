"""
Aipromovids (Doppel) backend - REBUILT from scratch.

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
- Google sign-in in the original went through Emergent's hosted auth and is
  not available here; email/password auth is fully working.
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
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, EmailStr, Field

# ---------------------------------------------------------------- config
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.environ.get("DB_PATH", str(BASE_DIR / "data" / "app.db"))
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", str(BASE_DIR / "uploads")))
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
PAYMENT_PROVIDER = os.environ.get("PAYMENT_PROVIDER", "mock")  # mock | stripe
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "")
TEASER_PROVIDER = os.environ.get("TEASER_PROVIDER", "none")     # none = no AI provider wired
FREE_TEASERS = int(os.environ.get("FREE_TEASERS", "2"))
ORDER_PRICE_GBP = int(os.environ.get("ORDER_PRICE_GBP", "350"))
ADMIN_EMAILS = {e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()}
ACCESS_TTL = 15 * 60
REFRESH_TTL = 30 * 24 * 3600
RESET_TTL = 3600
MAX_UPLOAD = 10 * 1024 * 1024
ALLOWED_IMAGE = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("aipromovids")

Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()
db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.row_factory = sqlite3.Row
db.executescript(
    """
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'customer',
        created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY, user_id TEXT NOT NULL, kind TEXT NOT NULL,
        expires_at REAL NOT NULL, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS files (
        file_id TEXT PRIMARY KEY, filename TEXT, mime TEXT, kind TEXT,
        path TEXT, size INTEGER, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS orders (
        order_ref INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT UNIQUE, user_id TEXT, name TEXT, email TEXT, company TEXT,
        language TEXT, avatar_style TEXT, brief TEXT,
        photo_file_id TEXT, logo_file_id TEXT,
        amount_gbp INTEGER, payment_status TEXT NOT NULL DEFAULT 'initiated',
        status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL);
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
    """
)
db.commit()


def now():
    return datetime.now(timezone.utc).isoformat()


def q(sql, args=(), one=False, write=False):
    with _lock:
        cur = db.execute(sql, args)
        if write:
            db.commit()
        rows = cur.fetchall()
    if one:
        return rows[0] if rows else None
    return rows


# ---------------------------------------------------------------- auth
def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return f"{salt}${digest}"


def check_password(password, stored):
    salt, digest = stored.split("$", 1)
    return hmac.compare_digest(hash_password(password, salt).split("$", 1)[1], digest)


def new_session(user_id, kind, ttl):
    token = secrets.token_urlsafe(32)
    q("INSERT INTO sessions (token, user_id, kind, expires_at, created_at) VALUES (?,?,?,?,?)",
      (token, user_id, kind, time.time() + ttl, now()), write=True)
    return token


def set_auth_cookies(resp, user_id):
    resp.set_cookie("access_token", new_session(user_id, "access", ACCESS_TTL),
                    httponly=True, samesite="lax", max_age=ACCESS_TTL)
    resp.set_cookie("refresh_token", new_session(user_id, "refresh", REFRESH_TTL),
                    httponly=True, samesite="lax", max_age=REFRESH_TTL)


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


class ScriptIn(BaseModel):
    business: str = Field(min_length=3, max_length=300)
    offer: str | None = Field(default="", max_length=300)
    language: str = "English"
    vibe: str = "Fun & upbeat"


# ---------------------------------------------------------------- app
app = FastAPI(title="Aipromovids API (rebuilt)")
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
        "payments": PAYMENT_PROVIDER,          # "mock" = simulated, no real charge
        "ai_video": TEASER_PROVIDER,           # "none" = not connected
        "email": "not_configured",             # no SMTP in this build
        "google_auth": "unavailable",          # was Emergent-hosted in the original
    }
    demo = (capabilities["payments"] == "mock" or capabilities["ai_video"] == "none"
            or capabilities["email"] == "not_configured" or capabilities["google_auth"] == "unavailable")
    return {"app": "Aipromovids API", "status": "ok", "demo": demo,
            "capabilities": capabilities,
            "note": "rebuilt backend (see docs/RECOVERY.md)"}


# ---------------------------------------------------------------- auth routes
@app.post("/api/auth/register", status_code=201)
def register(body: RegisterIn, response: Response):
    email = body.email.lower()
    if q("SELECT id FROM users WHERE email=?", (email,), one=True):
        raise HTTPException(409, "An account with this email already exists")
    uid = uuid.uuid4().hex
    role = "admin" if email in ADMIN_EMAILS else "customer"
    q("INSERT INTO users (id, name, email, password_hash, role, created_at) VALUES (?,?,?,?,?,?)",
      (uid, body.name.strip(), email, hash_password(body.password), role, now()), write=True)
    user = q("SELECT * FROM users WHERE id=?", (uid,), one=True)
    set_auth_cookies(response, uid)
    return user_public(user)


@app.post("/api/auth/login")
def login(body: LoginIn, response: Response):
    user = q("SELECT * FROM users WHERE email=?", (body.email.lower(),), one=True)
    if not user or not check_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Wrong email or password")
    user = apply_admin_flag(user)
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
    user = apply_admin_flag(user)
    response.set_cookie("access_token", new_session(user["id"], "access", ACCESS_TTL),
                        httponly=True, samesite="lax", max_age=ACCESS_TTL)
    return user_public(user)


@app.post("/api/auth/forgot-password")
def forgot_password(body: ForgotIn):
    user = q("SELECT * FROM users WHERE email=?", (body.email.lower(),), one=True)
    if user:
        token = secrets.token_urlsafe(32)
        q("INSERT INTO password_resets (token, user_id, expires_at, created_at) VALUES (?,?,?,?)",
          (token, user["id"], time.time() + RESET_TTL, now()), write=True)
        origin = (body.origin_url or FRONTEND_ORIGIN).rstrip("/")
        # No SMTP in this local build: the reset link is logged, not emailed.
        log.info("PASSWORD RESET LINK for %s: %s/reset-password?token=%s", user["email"], origin, token)
    return {"ok": True}


@app.post("/api/auth/reset-password")
def reset_password(body: ResetIn):
    row = q("SELECT * FROM password_resets WHERE token=? AND used=0", (body.token,), one=True)
    if not row or row["expires_at"] < time.time():
        raise HTTPException(400, "That reset link is invalid or has expired")
    q("UPDATE users SET password_hash=? WHERE id=?", (hash_password(body.password), row["user_id"]), write=True)
    q("UPDATE password_resets SET used=1 WHERE token=?", (body.token,), write=True)
    return {"ok": True}


@app.post("/api/auth/google/session")
def google_session(body: GoogleSessionIn):
    raise HTTPException(
        501,
        "Google sign-in was provided by Emergent's hosted auth in the original app and is "
        "not available in this local build. Use email and password instead.",
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
    path = UPLOAD_DIR / f"{fid}{ext}"
    path.write_bytes(data)
    q("INSERT INTO files (file_id, filename, mime, kind, path, size, created_at) VALUES (?,?,?,?,?,?,?)",
      (fid, file.filename, file.content_type, kind, str(path), len(data), now()), write=True)
    return {"file_id": fid, "filename": file.filename, "mime": file.content_type, "size": len(data)}


@app.get("/api/files/{file_id}")
def get_file(file_id: str):
    row = q("SELECT * FROM files WHERE file_id=?", (file_id,), one=True)
    if not row or not Path(row["path"]).exists():
        raise HTTPException(404, "File not found")
    return FileResponse(row["path"], media_type=row["mime"])


# ---------------------------------------------------------------- payments & orders
@app.post("/api/payments/checkout", status_code=201)
def checkout(body: CheckoutIn, request: Request):
    if PAYMENT_PROVIDER != "mock" and not STRIPE_API_KEY:
        raise HTTPException(503, "Card payments are not configured in this build (set STRIPE_API_KEY).")
    user = user_from_token(request.cookies.get("access_token"), "access")
    session_id = uuid.uuid4().hex
    origin = (body.origin_url or FRONTEND_ORIGIN).rstrip("/")
    # MOCK payment provider: no real charge. The order is marked paid immediately
    # and the "checkout" redirects straight to the success page, mirroring the
    # original Stripe round-trip. Swap PAYMENT_PROVIDER=stripe + STRIPE_API_KEY
    # for a real integration (not included).
    q("""INSERT INTO orders (session_id, user_id, name, email, company, language, avatar_style,
         brief, photo_file_id, logo_file_id, amount_gbp, payment_status, status, created_at)
         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
      (session_id, user["id"] if user else None, body.name, body.email.lower(), body.company,
       body.language, body.avatar_style, body.brief, body.photo_file_id, body.logo_file_id,
       ORDER_PRICE_GBP, "paid" if PAYMENT_PROVIDER == "mock" else "initiated", "open", now()), write=True)
    return {"checkout_url": f"{origin}/payment/success?session_id={session_id}", "session_id": session_id}


@app.get("/api/payments/status/{session_id}")
def payment_status(session_id: str):
    order = q("SELECT * FROM orders WHERE session_id=?", (session_id,), one=True)
    if not order:
        raise HTTPException(404, "Unknown checkout session")
    return {"session_id": session_id, "payment_status": order["payment_status"],
            "status": "complete" if order["payment_status"] == "paid" else "open",
            "order_ref": order["order_ref"], "provider": PAYMENT_PROVIDER}


@app.get("/api/orders/mine")
def my_orders(user=Depends(current_user)):
    rows = q("SELECT * FROM orders WHERE payment_status='paid' AND (user_id=? OR email=?) ORDER BY order_ref DESC",
             (user["id"], user["email"]))
    return [dict(r) for r in rows]


# ---------------------------------------------------------------- teasers
def _finish_teaser(teaser_id):
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
    if not q("SELECT file_id FROM files WHERE file_id=?", (body.photo_file_id,), one=True):
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
    text = SCRIPT_TEMPLATE.format(
        business=body.business.strip(),
        offer_line=f"share \"{offer}\" " if offer else "",
        vibe_line=f"in a {body.vibe.lower()} style" if body.vibe else "",
        offer_sentence=f"Right now: {offer}." if offer else "",
    )
    if body.language != "English":
        text += f"\n\n(Preview generated in English; the finished video is delivered in {body.language}.)"

    def stream():
        # Templated stand-in for the original AI-generated script. No AI model
        # is called; the format (HOOK / SCRIPT / CTA) matches what the
        # recovered frontend parses.
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
    return JSONResponse({"detail": getattr(exc, "detail", "Not found")}, status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
