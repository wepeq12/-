# -*- coding: utf-8 -*-
"""
🔐 Experu TG — License Server
FastAPI + SQLite | Deploy on Railway.app (free)

Endpoints:
  POST /verify          — תוכנה בודקת רישיון בהפעלה
  POST /activate        — webhook מ-Stripe / NOWPayments
  POST /admin/grant     — מנהל נותן רישיון ידנית
  POST /admin/revoke    — מנהל מבטל רישיון
  GET  /admin/licenses  — רשימת כל הרישיונות
  GET  /admin/stats     — סטטיסטיקות
"""

import os, uuid, hashlib, hmac, json, datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Header, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
from pathlib import Path

# ──────────────────────────────────────────────
# CONFIG — שנה את הערכים האלה!
# ──────────────────────────────────────────────
ADMIN_SECRET      = os.getenv("ADMIN_SECRET",   "CHANGE_ME_ADMIN_SECRET")
STRIPE_SECRET     = os.getenv("STRIPE_SECRET",   "")          # מ-Stripe Dashboard
NOWPAY_IPN_SECRET = os.getenv("NOWPAY_IPN_SECRET", "")        # מ-NOWPayments
TELEGRAM_BOT_TOKEN= os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_TELEGRAM_ID  = os.getenv("ADMIN_TELEGRAM_ID",  "")      # ה-chat_id שלך
APP_SECRET        = os.getenv("APP_SECRET",      "experu_tg_secret_2025")  # סוד פנימי

DB_PATH = Path(os.getenv("DB_PATH", "licenses.db"))

# ──────────────────────────────────────────────
# תוכניות
# ──────────────────────────────────────────────
PLANS = {
    "basic": {
        "name": "Basic",
        "max_clients": 1,
        "max_sessions": 2,
        "multi_client": False,
        "features": ["adder", "sender", "warmup"],
        "price_monthly": 15,
    },
    "pro": {
        "name": "Pro",
        "max_clients": 3,
        "max_sessions": 10,
        "multi_client": True,
        "features": ["adder", "sender", "warmup", "scanner", "bot", "ai"],
        "price_monthly": 35,
    },
    "business": {
        "name": "Business",
        "max_clients": 999,
        "max_sessions": 999,
        "multi_client": True,
        "features": ["all"],
        "price_monthly": 70,
    },
    "ultimate": {
        "name": "Ultimate",
        "max_clients": 999,
        "max_sessions": 999,
        "multi_client": True,
        "features": ["all"],
        "price_monthly": 120,
        "priority_support": True,
    },
}

DURATIONS = {
    "1m":  30,
    "3m":  90,
    "6m":  180,
    "1y":  365,
}

# ──────────────────────────────────────────────
# DB
# ──────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            key         TEXT PRIMARY KEY,
            plan        TEXT NOT NULL,
            email       TEXT,
            telegram_id TEXT,
            hwid        TEXT,
            created_at  TEXT NOT NULL,
            expires_at  TEXT NOT NULL,
            active      INTEGER DEFAULT 1,
            duration    TEXT DEFAULT '1m',
            note        TEXT DEFAULT ''
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS activations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            key         TEXT NOT NULL,
            hwid        TEXT,
            ip          TEXT,
            activated_at TEXT NOT NULL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            provider     TEXT,
            payment_id   TEXT,
            email        TEXT,
            plan         TEXT,
            duration     TEXT,
            amount       REAL,
            currency     TEXT,
            status       TEXT,
            created_at   TEXT,
            license_key  TEXT
        )
    """)
    db.commit()
    db.close()

def generate_key() -> str:
    raw = uuid.uuid4().hex.upper()
    return f"EXPERU-{raw[:6]}-{raw[6:12]}-{raw[12:18]}-{raw[18:24]}"

def now_str() -> str:
    return datetime.datetime.utcnow().isoformat()

def expiry_str(days: int) -> str:
    exp = datetime.datetime.utcnow() + datetime.timedelta(days=days)
    return exp.isoformat()

# ──────────────────────────────────────────────
# TELEGRAM NOTIFY
# ──────────────────────────────────────────────
async def notify_admin(msg: str):
    if not TELEGRAM_BOT_TOKEN or not ADMIN_TELEGRAM_ID:
        return
    try:
        import httpx
        async with httpx.AsyncClient() as c:
            await c.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": ADMIN_TELEGRAM_ID, "text": msg, "parse_mode": "HTML"},
                timeout=5
            )
    except Exception:
        pass

async def notify_customer(telegram_id: str, msg: str):
    if not TELEGRAM_BOT_TOKEN or not telegram_id:
        return
    try:
        import httpx
        async with httpx.AsyncClient() as c:
            await c.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": telegram_id, "text": msg, "parse_mode": "HTML"},
                timeout=5
            )
    except Exception:
        pass

# ──────────────────────────────────────────────
# APP
# ──────────────────────────────────────────────
app = FastAPI(title="Experu TG License Server", docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    init_db()

# ──────────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────────
def require_admin(x_admin_secret: str = Header(...)):
    if x_admin_secret != ADMIN_SECRET:
        raise HTTPException(403, "Unauthorized")

# ──────────────────────────────────────────────
# MODELS
# ──────────────────────────────────────────────
class VerifyRequest(BaseModel):
    license_key: str
    hwid: str

class GrantRequest(BaseModel):
    plan: str
    duration: str = "1m"
    email: Optional[str] = None
    telegram_id: Optional[str] = None
    note: Optional[str] = ""

class RevokeRequest(BaseModel):
    license_key: str

class StripeWebhook(BaseModel):
    pass

# ──────────────────────────────────────────────
# ENDPOINTS
# ──────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "service": "Experu TG License Server"}

@app.get("/health")
def health():
    return {"status": "ok", "time": now_str()}

# ── חיפוש חשבון קיים (לדף login) ───────────
@app.post("/lookup")
async def lookup_account(request: Request):
    data = await request.json()
    identifier = data.get("identifier", "").strip().lstrip("@").lower()
    if not identifier:
        return {"found": False}
    db = get_db()
    # חיפוש לפי telegram_id או email
    row = db.execute(
        "SELECT key, plan, expires_at, active FROM licenses WHERE (LOWER(telegram_id)=? OR LOWER(email)=?) AND active=1 ORDER BY expires_at DESC LIMIT 1",
        (identifier, identifier)
    ).fetchone()
    db.close()
    if not row:
        return {"found": False}
    expires = datetime.datetime.fromisoformat(row["expires_at"])
    days_left = max(0, (expires - datetime.datetime.utcnow()).days)
    return {
        "found": True,
        "plan": row["plan"],
        "days_left": days_left,
        "key_hint": row["key"][:14] + "...",  # רמז בלבד — לא המפתח המלא
    }

# ── אימות רישיון (קריאה מהתוכנה) ──────────────
@app.post("/verify")
async def verify_license(req: VerifyRequest, request: Request):
    db = get_db()
    row = db.execute(
        "SELECT * FROM licenses WHERE key=?", (req.license_key,)
    ).fetchone()

    if not row:
        db.close()
        return {"valid": False, "reason": "key_not_found"}

    if not row["active"]:
        db.close()
        return {"valid": False, "reason": "key_revoked"}

    # בדיקת תפוגה
    expires = datetime.datetime.fromisoformat(row["expires_at"])
    if datetime.datetime.utcnow() > expires:
        db.close()
        return {"valid": False, "reason": "expired", "expired_at": row["expires_at"]}

    # נעילת HWID — בפעם הראשונה נועלים
    if not row["hwid"]:
        db.execute("UPDATE licenses SET hwid=? WHERE key=?", (req.hwid, req.license_key))
        db.commit()
    elif row["hwid"] != req.hwid:
        db.close()
        return {"valid": False, "reason": "hwid_mismatch"}

    # רישום activation
    ip = request.client.host if request.client else "unknown"
    db.execute(
        "INSERT INTO activations (key, hwid, ip, activated_at) VALUES (?,?,?,?)",
        (req.license_key, req.hwid, ip, now_str())
    )
    db.commit()

    plan_info = PLANS.get(row["plan"], {})
    db.close()

    days_left = (expires - datetime.datetime.utcnow()).days

    return {
        "valid": True,
        "plan": row["plan"],
        "plan_info": plan_info,
        "expires_at": row["expires_at"],
        "days_left": days_left,
        "features": plan_info.get("features", []),
        "max_clients": plan_info.get("max_clients", 1),
        "max_sessions": plan_info.get("max_sessions", 2),
        "multi_client": plan_info.get("multi_client", False),
    }

# ── מנהל: הענקת רישיון ידנית ──────────────────
@app.post("/admin/grant", dependencies=[Depends(require_admin)])
async def admin_grant(req: GrantRequest):
    if req.plan not in PLANS:
        raise HTTPException(400, f"Plan must be one of: {list(PLANS.keys())}")
    if req.duration not in DURATIONS:
        raise HTTPException(400, f"Duration must be one of: {list(DURATIONS.keys())}")

    days = DURATIONS[req.duration]
    key = generate_key()
    db = get_db()
    db.execute(
        "INSERT INTO licenses (key,plan,email,telegram_id,created_at,expires_at,duration,note) VALUES (?,?,?,?,?,?,?,?)",
        (key, req.plan, req.email or "", req.telegram_id or "", now_str(), expiry_str(days), req.duration, req.note or "")
    )
    db.commit()
    db.close()

    plan_info = PLANS[req.plan]
    msg = (
        f"🔑 <b>רישיון חדש הופק</b>\n\n"
        f"📦 תוכנית: <b>{plan_info['name']}</b>\n"
        f"⏱ תקופה: {req.duration}\n"
        f"📅 תפוגה: {expiry_str(days)[:10]}\n\n"
        f"🔐 <b>License Key:</b>\n<code>{key}</code>\n\n"
        f"📥 הורד את התוכנה והזן את המפתח בהגדרות."
    )

    # שלח ללקוח
    if req.telegram_id:
        await notify_customer(req.telegram_id, msg)

    # הודע למנהל
    await notify_admin(
        f"✅ רישיון חדש הופק\nתוכנית: {req.plan} | {req.duration}\nEmail: {req.email}\nKey: {key}"
    )

    return {"success": True, "license_key": key, "plan": req.plan, "expires_at": expiry_str(days)}

# ── מנהל: ביטול רישיון ────────────────────────
@app.post("/admin/revoke", dependencies=[Depends(require_admin)])
async def admin_revoke(req: RevokeRequest):
    db = get_db()
    db.execute("UPDATE licenses SET active=0 WHERE key=?", (req.license_key,))
    db.commit()
    db.close()
    await notify_admin(f"🚫 רישיון בוטל: {req.license_key}")
    return {"success": True}

# ── מנהל: אפס HWID (למקרה שהלקוח החליף מחשב) ──
@app.post("/admin/reset_hwid", dependencies=[Depends(require_admin)])
async def admin_reset_hwid(req: RevokeRequest):
    db = get_db()
    db.execute("UPDATE licenses SET hwid='' WHERE key=?", (req.license_key,))
    db.commit()
    db.close()
    return {"success": True, "msg": "HWID reset — next activation will lock to new machine"}

# ── מנהל: רשימת רישיונות ──────────────────────
@app.get("/admin/licenses", dependencies=[Depends(require_admin)])
def admin_licenses():
    db = get_db()
    rows = db.execute("SELECT * FROM licenses ORDER BY created_at DESC").fetchall()
    db.close()
    now = datetime.datetime.utcnow()
    result = []
    for r in rows:
        exp = datetime.datetime.fromisoformat(r["expires_at"])
        result.append({
            "key": r["key"],
            "plan": r["plan"],
            "email": r["email"],
            "telegram_id": r["telegram_id"],
            "active": bool(r["active"]),
            "hwid_locked": bool(r["hwid"]),
            "expires_at": r["expires_at"],
            "days_left": max(0, (exp - now).days),
            "note": r["note"],
        })
    return result

# ── מנהל: סטטיסטיקות ──────────────────────────
@app.get("/admin/stats", dependencies=[Depends(require_admin)])
def admin_stats():
    db = get_db()
    total  = db.execute("SELECT COUNT(*) FROM licenses").fetchone()[0]
    active = db.execute("SELECT COUNT(*) FROM licenses WHERE active=1").fetchone()[0]
    now = datetime.datetime.utcnow().isoformat()
    valid  = db.execute("SELECT COUNT(*) FROM licenses WHERE active=1 AND expires_at > ?", (now,)).fetchone()[0]
    expired= db.execute("SELECT COUNT(*) FROM licenses WHERE expires_at <= ?", (now,)).fetchone()[0]
    plans  = db.execute("SELECT plan, COUNT(*) as cnt FROM licenses WHERE active=1 GROUP BY plan").fetchall()
    activations = db.execute("SELECT COUNT(*) FROM activations").fetchone()[0]
    db.close()
    return {
        "total_licenses": total,
        "active_licenses": active,
        "valid_licenses": valid,
        "expired_licenses": expired,
        "total_activations": activations,
        "by_plan": {r["plan"]: r["cnt"] for r in plans},
    }

# ── Stripe Webhook ─────────────────────────────
@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    # אימות חתימה
    if STRIPE_SECRET:
        try:
            import stripe
            event = stripe.Webhook.construct_event(payload, sig, STRIPE_SECRET)
        except Exception as e:
            raise HTTPException(400, str(e))
    else:
        event = json.loads(payload)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        meta    = session.get("metadata", {})
        plan    = meta.get("plan", "basic")
        duration= meta.get("duration", "1m")
        email   = session.get("customer_email", "")
        tg_id   = meta.get("telegram_id", "")
        amount  = session.get("amount_total", 0) / 100
        currency= session.get("currency", "usd").upper()

        days = DURATIONS.get(duration, 30)
        key  = generate_key()
        db   = get_db()
        db.execute(
            "INSERT INTO licenses (key,plan,email,telegram_id,created_at,expires_at,duration,note) VALUES (?,?,?,?,?,?,?,?)",
            (key, plan, email, tg_id, now_str(), expiry_str(days), duration, f"Stripe payment {amount}{currency}")
        )
        db.execute(
            "INSERT INTO payments (provider,payment_id,email,plan,duration,amount,currency,status,created_at,license_key) VALUES (?,?,?,?,?,?,?,?,?,?)",
            ("stripe", session.get("id",""), email, plan, duration, amount, currency, "completed", now_str(), key)
        )
        db.commit()
        db.close()

        plan_name = PLANS.get(plan, {}).get("name", plan)
        msg = (
            f"🎉 <b>תשלום התקבל!</b>\n\n"
            f"📦 תוכנית: <b>{plan_name}</b> ({duration})\n"
            f"💰 {amount} {currency}\n\n"
            f"🔐 <b>License Key שלך:</b>\n<code>{key}</code>\n\n"
            f"📥 הזן את המפתח בתוכנה תחת 'הגדרות → License'."
        )
        if tg_id:
            await notify_customer(tg_id, msg)
        await notify_admin(f"💰 תשלום Stripe\n{email} | {plan} | {duration}\n{amount}{currency}\nKey: {key}")

    return {"received": True}

# ── NOWPayments Webhook (קריפטו) ───────────────
@app.post("/webhook/nowpayments")
async def nowpayments_webhook(request: Request):
    payload = await request.body()
    data    = json.loads(payload)

    # אימות חתימה
    if NOWPAY_IPN_SECRET:
        sig = request.headers.get("x-nowpayments-sig", "")
        expected = hmac.new(NOWPAY_IPN_SECRET.encode(), payload, hashlib.sha512).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise HTTPException(400, "Invalid signature")

    if data.get("payment_status") in ("finished", "confirmed"):
        meta     = data.get("order_description", "").split("|")
        plan     = meta[0] if len(meta) > 0 else "basic"
        duration = meta[1] if len(meta) > 1 else "1m"
        tg_id    = meta[2] if len(meta) > 2 else ""
        email    = data.get("payer_email", "")
        amount   = data.get("actually_paid", 0)
        currency = data.get("pay_currency", "USDT").upper()

        days = DURATIONS.get(duration, 30)
        key  = generate_key()
        db   = get_db()
        db.execute(
            "INSERT INTO licenses (key,plan,email,telegram_id,created_at,expires_at,duration,note) VALUES (?,?,?,?,?,?,?,?)",
            (key, plan, email, tg_id, now_str(), expiry_str(days), duration, f"Crypto {amount}{currency}")
        )
        db.execute(
            "INSERT INTO payments (provider,payment_id,email,plan,duration,amount,currency,status,created_at,license_key) VALUES (?,?,?,?,?,?,?,?,?,?)",
            ("nowpayments", str(data.get("payment_id","")), email, plan, duration, float(amount), currency, "completed", now_str(), key)
        )
        db.commit()
        db.close()

        plan_name = PLANS.get(plan, {}).get("name", plan)
        msg = (
            f"🎉 <b>תשלום קריפטו אושר!</b>\n\n"
            f"📦 תוכנית: <b>{plan_name}</b> ({duration})\n"
            f"💎 {amount} {currency}\n\n"
            f"🔐 <b>License Key שלך:</b>\n<code>{key}</code>\n\n"
            f"📥 הזן את המפתח בתוכנה."
        )
        if tg_id:
            await notify_customer(tg_id, msg)
        await notify_admin(f"💎 תשלום קריפטו\n{email} | {plan} | {duration}\n{amount} {currency}\nKey: {key}")

    return {"received": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("license_server:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=False)
