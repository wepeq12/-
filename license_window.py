# -*- coding: utf-8 -*-
"""
🔐 license_window.py — Experu TG v2.1
תיקונים: מחירים דינמיים, טקסט נראה, ניסיון חינם חד-פעמי, ניווט tabs
"""

import os, json, webbrowser, hashlib, platform, uuid, datetime, threading
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QPushButton, QLineEdit, QStackedWidget, QFrame,
    QMessageBox, QApplication, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QCursor

try:
    import requests as _req
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SERVER_URL      = "https://lucid-strength-production.up.railway.app"
SUPPORT_LINK    = "https://t.me/experu_support"
LICENSE_FILE    = Path(__file__).parent / "license.key"
CACHE_FILE      = Path(__file__).parent / ".lic_cache"
TRIAL_USED_FILE = Path(__file__).parent / ".trial_used"  # גיבוי מקומי בלבד
CACHE_TTL_HOURS = 12

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PLANS DATA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PLANS = {
    "starter": {
        "name": "Starter", "name_he": "מתחיל",
        "emoji": "🔰", "color": "#94a3b8",
        "sessions": 5, "trial": True,
        "prices": {
            "1m": {"ils": 290,   "usd": 79},
            "3m": {"ils": 750,   "usd": 202},
            "6m": {"ils": 1300,  "usd": 351},
            "1y": {"ils": 2200,  "usd": 594},
        },
        "features": [
            ("✓", "5 סשנים (חשבונות)",       True),
            ("✓", "סורק קבוצות בסיסי",        True),
            ("✓", "גירוד משתמשים",             True),
            ("✓", "Adder + Mass Sender",       True),
            ("✓", "Anti-Ban בסיסי",            True),
            ("✗", "Sniper Mode",               False),
            ("✗", "AI Control Bot",            False),
            ("✗", "Multi-Client",              False),
        ],
    },
    "pro": {
        "name": "Pro", "name_he": "מקצוען",
        "emoji": "🚀", "color": "#22d3b0",
        "sessions": 25, "popular": True,
        "prices": {
            "1m": {"ils": 590,   "usd": 159},
            "3m": {"ils": 1500,  "usd": 405},
            "6m": {"ils": 2700,  "usd": 729},
            "1y": {"ils": 4800,  "usd": 1296},
        },
        "features": [
            ("✓", "25 סשנים",                  True),
            ("✓", "Deep Group Scanner",        True),
            ("✓", "Proxy + Device Fingerprint",True),
            ("✓", "Group Warmup (SEO)",        True),
            ("⚡", "Sniper Mode",               True),
            ("⚡", "AI Control Bot (Gemini)",   True),
            ("✓", "לולאת שליחה 24/7",           True),
            ("✗", "Multi-Client",              False),
        ],
    },
    "agency": {
        "name": "Agency", "name_he": "סוכנות",
        "emoji": "💼", "color": "#a78bfa",
        "sessions": 50, "orig_ils": 1200,
        "prices": {
            "1m": {"ils": 790,   "usd": 213},
            "3m": {"ils": 1950,  "usd": 527},
            "6m": {"ils": 3600,  "usd": 972},
            "1y": {"ils": 6200,  "usd": 1674},
        },
        "features": [
            ("✓", "50 סשנים",                  True),
            ("✓", "הכל מ-Pro",                 True),
            ("⚡", "Multi-Client Dashboard",    True),
            ("⚡", "Mass Reporting",            True),
            ("✓", "בידוד לקוחות מלא",           True),
            ("✓", "בוט שליטה לכל לקוח",         True),
            ("✓", "Number Checker",            True),
            ("✓", "עדיפות בתמיכה",              True),
        ],
    },
    "elite": {
        "name": "Elite", "name_he": "עילית",
        "emoji": "👑", "color": "#f0c040",
        "sessions": 100, "unlimited": True, "orig_ils": 2500,
        "prices": {
            "1m": {"ils": 1350,  "usd": 365},
            "3m": {"ils": 3400,  "usd": 918},
            "6m": {"ils": 6200,  "usd": 1674},
            "1y": {"ils": 10500, "usd": 2835},
        },
        "features": [
            ("✓", "100+ סשנים ללא הגבלה",       True),
            ("✓", "הכל מ-Agency",               True),
            ("⚡", "AI Gemini Pro",              True),
            ("⚡", "SLA 99.9% uptime",           True),
            ("✓", "כל עדכונים עתידיים",          True),
            ("✓", "תמיכה VIP ישירה",             True),
            ("✓", "Beta גישה מוקדמת",            True),
            ("✓", "Onboarding אישי",             True),
        ],
    },
}

LIFETIME = {
    "ils": 7000, "usd": 1890, "orig_ils": 14000,
}

DURATIONS = {"1m": "חודש 1", "3m": "3 חודשים", "6m": "חצי שנה", "1y": "שנה"}
SAVINGS   = {"1m": None, "3m": "חיסכון ~14%", "6m": "חיסכון ~25%", "1y": "הכי משתלם 🏆"}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HWID + CACHE + TRIAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_hwid() -> str:
    parts = [platform.node(), platform.machine(), platform.processor(), str(uuid.getnode())]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]

def trial_used() -> bool:
    """בודק ע"פ HWID מהשרת — לא קובץ מקומי. אם השרת לא זמין — גיבוי מקומי."""
    hwid = get_hwid()
    if REQUESTS_OK:
        try:
            r = _req.post(f"{SERVER_URL}/trial/check",
                json={"hwid": hwid}, timeout=6)
            data = r.json()
            used = data.get("used", False)
            # עדכן גיבוי מקומי
            if used:
                if not TRIAL_USED_FILE.exists():
                    TRIAL_USED_FILE.write_text("server_confirmed")
            else:
                # אם השרת אומר לא שומש — מחק קובץ מקומי ישן
                if TRIAL_USED_FILE.exists():
                    TRIAL_USED_FILE.unlink()
            return used
        except Exception:
            pass  # fallback למקומי
    return TRIAL_USED_FILE.exists()

def mark_trial_used(tg_username: str):
    """שומר גיבוי מקומי בלבד — הרשומה האמיתית נשמרת בשרת"""
    try:
        TRIAL_USED_FILE.write_text(json.dumps({
            "tg": tg_username,
            "hwid": get_hwid(),
            "at": datetime.datetime.utcnow().isoformat()
        }))
    except Exception:
        pass

class LicenseResult:
    def __init__(self, valid=False, plan="", plan_info=None, expires_at="",
                 days_left=0, reason="", features=None,
                 max_clients=1, max_sessions=5, multi_client=False):
        self.valid = valid; self.plan = plan; self.plan_info = plan_info or {}
        self.expires_at = expires_at; self.days_left = days_left
        self.reason = reason; self.features = features or []
        self.max_clients = max_clients; self.max_sessions = max_sessions
        self.multi_client = multi_client
    def has_feature(self, f): return "all" in self.features or f in self.features
    def __bool__(self): return self.valid

def _load_cache():
    try:
        if not CACHE_FILE.exists(): return None
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        cached_at = datetime.datetime.fromisoformat(data["cached_at"])
        if (datetime.datetime.utcnow() - cached_at).total_seconds() > CACHE_TTL_HOURS * 3600:
            return None
        return LicenseResult(**{k: v for k, v in data.items() if k != "cached_at"})
    except Exception: return None

def _save_cache(r: LicenseResult):
    try:
        data = {k: getattr(r, k) for k in ["valid","plan","plan_info","expires_at","days_left","features","max_clients","max_sessions","multi_client"]}
        data["cached_at"] = datetime.datetime.utcnow().isoformat()
        CACHE_FILE.write_text(json.dumps(data), encoding="utf-8")
    except Exception: pass

def check_license(key=None) -> LicenseResult:
    if not key:
        key = LICENSE_FILE.read_text(encoding="utf-8").strip() if LICENSE_FILE.exists() else os.getenv("EXPERU_LICENSE_KEY")
    if not key: return LicenseResult(False, reason="no_key")
    if not REQUESTS_OK:
        c = _load_cache(); return c or LicenseResult(False, reason="no_requests")
    try:
        r = _req.post(f"{SERVER_URL}/verify", json={"license_key": key, "hwid": get_hwid()}, timeout=8)
        d = r.json()
    except Exception:
        c = _load_cache(); return c or LicenseResult(False, reason="no_connection")
    res = LicenseResult(
        valid=d.get("valid",False), plan=d.get("plan",""), plan_info=d.get("plan_info",{}),
        expires_at=d.get("expires_at",""), days_left=d.get("days_left",0),
        reason=d.get("reason",""), features=d.get("features",[]),
        max_clients=d.get("max_clients",1), max_sessions=d.get("max_sessions",5),
        multi_client=d.get("multi_client",False)
    )
    if res.valid: LICENSE_FILE.write_text(key, encoding="utf-8"); _save_cache(res)
    return res

def send_welcome_webhook(result: LicenseResult, contact=""):
    def _go():
        try:
            plan_name = PLANS.get(result.plan, {}).get("name", result.plan)
            _req.post(f"{SERVER_URL}/webhook/welcome", json={
                "message": f"🎉 *ברוך הבא ל-Experu TG!*\n✅ תוכנית: *{plan_name}*\n📅 תוקף: *{result.days_left} ימים*\n📞 תמיכה: @experu\\_support",
                "contact": contact, "plan": result.plan
            }, timeout=8)
        except Exception: pass
    threading.Thread(target=_go, daemon=True).start()

BOT_TOKEN = "8605591762:AAEpvopxifsmtvFatvdSo8hddf0GJG-eoEM"
ADMIN_TG_ID = "8525975054"

def request_trial(tg_username: str):
    """שולח בקשת ניסיון: מודיע לאדמין + מנסה דרך השרת"""
    def _go():
        # 1. שלח הודעה לאדמין דרך הבוט
        try:
            msg = (
                f"🎁 *בקשת ניסיון חינם חדשה!*\n\n"
                f"👤 יוזר: @{tg_username}\n"
                f"💻 HWID: `{get_hwid()[:16]}...`\n"
                f"📅 {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
                f"הפק רישיון: /grant starter 3d {tg_username}"
            )
            _req.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": ADMIN_TG_ID, "text": msg, "parse_mode": "Markdown"},
                timeout=8
            )
        except Exception: pass
        # 2. נסה גם דרך השרת
        try:
            _req.post(f"{SERVER_URL}/trial",
                json={"tg": tg_username, "hwid": get_hwid()}, timeout=8)
        except Exception: pass
    threading.Thread(target=_go, daemon=True).start()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# THREADS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class LicenseCheckWorker(QThread):
    result = Signal(object)
    def __init__(self, key): super().__init__(); self.key = key
    def run(self): self.result.emit(check_license(self.key))

class PaymentWorker(QThread):
    result = Signal(dict)
    def __init__(self, plan, dur, contact, ils, usd):
        super().__init__(); self.plan=plan; self.dur=dur; self.contact=contact; self.ils=ils; self.usd=usd
    def run(self):
        try:
            r = _req.post(f"{SERVER_URL}/create_payment", json={
                "plan": self.plan, "duration": self.dur,
                "contact": self.contact, "ils_amount": self.ils, "usd_amount": self.usd
            }, timeout=15)
            self.result.emit(r.json())
        except Exception as e: self.result.emit({"error": str(e)})

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PLAN CARD — תיקון: כל label מקבל צבע מפורש
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class PlanCard(QFrame):
    clicked = Signal(str)

    def __init__(self, plan_key: str, plan: dict, parent=None):
        super().__init__(parent)
        self.plan_key = plan_key
        self.plan = plan
        self._cur_dur = "1m"
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedWidth(175)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self._build()
        self._set_border(False)

    def _lbl(self, text, color, size, weight=400, extra=""):
        """יוצר QLabel עם style מפורש שלא מושפע מ-QFrame"""
        l = QLabel(text)
        l.setStyleSheet(
            f"color: {color}; font-size: {size}px; font-weight: {weight};"
            f" background: transparent; border: none; {extra}"
        )
        return l

    def _build(self):
        ly = QVBoxLayout(self)
        ly.setContentsMargins(12, 14, 12, 12)
        ly.setSpacing(5)

        # ── שורת כותרת ──
        top = QHBoxLayout()
        top.setSpacing(4)
        name = self._lbl(f"{self.plan['emoji']} {self.plan['name']}", self.plan['color'], 14, 900)
        top.addWidget(name)
        top.addStretch()
        if self.plan.get("popular"):
            b = self._lbl("🔥 HOT", "#f0c040", 9, 700, "background: rgba(240,192,64,0.12); border-radius: 4px; padding: 2px 5px;")
            top.addWidget(b)
        if self.plan.get("trial"):
            t = self._lbl("✨ Trial", "#4ade80", 9, 700, "background: rgba(74,222,128,0.1); border-radius: 4px; padding: 2px 5px;")
            top.addWidget(t)
        ly.addLayout(top)

        # ── מחיר מקורי ──
        if self.plan.get("orig_ils"):
            ly.addWidget(self._lbl(f"₪{self.plan['orig_ils']:,}", "#374151", 10, 400, "text-decoration: line-through;"))

        # ── מחיר עיקרי (דינמי) ──
        self._price_lbl = self._lbl("", self.plan['color'], 22, 900)
        ly.addWidget(self._price_lbl)

        # ── תקופה + USD ──
        self._dur_lbl = self._lbl("", "#6B7280", 10)
        ly.addWidget(self._dur_lbl)

        # ── סשנים ──
        sess = "∞" if self.plan.get("unlimited") else str(self.plan.get("sessions", 0))
        ly.addWidget(self._lbl(f"💻 {sess} סשנים", "#94a3b8", 11, 600))

        # ── קו ──
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #1E2D3D; border: none;")
        ly.addWidget(sep)

        # ── פיצ'רים ──
        for icon, feat_name, included in self.plan["features"]:
            row = QHBoxLayout()
            row.setSpacing(5)
            row.setContentsMargins(0, 0, 0, 0)
            if icon == "⚡":
                ic_color, txt_color = "#f0c040", "#F0E68C"
            elif included:
                ic_color, txt_color = "#4ade80", "#CBD5E1"
            else:
                ic_color, txt_color = "#374151", "#374151"
            ic = self._lbl(icon, ic_color, 11, 900)
            ic.setFixedWidth(14)
            tx = self._lbl(feat_name, txt_color, 10)
            tx.setWordWrap(True)
            row.addWidget(ic)
            row.addWidget(tx, 1)
            ly.addLayout(row)

        ly.addStretch()
        self._refresh("1m")

    def _refresh(self, dur: str):
        self._cur_dur = dur
        p = self.plan["prices"][dur]
        self._price_lbl.setText(f"₪{p['ils']:,}")
        self._dur_lbl.setText(f"~${p['usd']:,}  |  {DURATIONS[dur]}")

    def set_duration(self, dur: str):
        self._refresh(dur)

    def get_price(self) -> dict:
        return self.plan["prices"][self._cur_dur]

    def set_selected(self, sel: bool):
        self._set_border(sel)

    def _set_border(self, sel: bool):
        c = self.plan["color"]
        if sel:
            self.setStyleSheet(f"QFrame {{ background: #0D1117; border: 2px solid {c}; border-radius: 12px; }}")
        else:
            self.setStyleSheet("QFrame { background: #0D1117; border: 1px solid #1E2D3D; border-radius: 12px; }")

    def mousePressEvent(self, e):
        self.clicked.emit(self.plan_key)


class LifetimeCard(QFrame):
    clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedWidth(175)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self._build()
        self.setStyleSheet("QFrame { background: #0D1117; border: 1px solid #2a2010; border-radius: 12px; }")

    def _lbl(self, text, color, size, weight=400, extra=""):
        l = QLabel(text)
        l.setStyleSheet(f"color: {color}; font-size: {size}px; font-weight: {weight}; background: transparent; border: none; {extra}")
        return l

    def _build(self):
        ly = QVBoxLayout(self)
        ly.setContentsMargins(12, 14, 12, 12)
        ly.setSpacing(5)

        top = QHBoxLayout()
        top.addWidget(self._lbl("♾️ Lifetime", "#f0c040", 14, 900))
        top.addStretch()
        top.addWidget(self._lbl("🔥", "#f0c040", 14))
        ly.addLayout(top)

        ly.addWidget(self._lbl(f"₪{LIFETIME['orig_ils']:,}", "#374151", 10, 400, "text-decoration: line-through;"))
        ly.addWidget(self._lbl(f"₪{LIFETIME['ils']:,}", "#f0c040", 22, 900))
        ly.addWidget(self._lbl(f"~${LIFETIME['usd']:,}  |  חד-פעמי לנצח", "#6B7280", 10))
        ly.addWidget(self._lbl("∞ סשנים לנצח", "#94a3b8", 11, 600))

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #2a2010; border: none;")
        ly.addWidget(sep)

        feats = [
            ("⚡", "כל הפיצ'רים לנצח",    "#F0E68C"),
            ("⚡", "כל עדכונים עתידיים",   "#F0E68C"),
            ("✓",  "תמיכה VIP ישירה",      "#CBD5E1"),
            ("✓",  "Beta גישה מוקדמת",     "#CBD5E1"),
            ("✓",  "Onboarding אישי",       "#CBD5E1"),
            ("✓",  "ללא תשלום חוזר לעולם", "#CBD5E1"),
        ]
        for icon, txt, col in feats:
            row = QHBoxLayout()
            row.setSpacing(5); row.setContentsMargins(0, 0, 0, 0)
            ic_col = "#f0c040" if icon == "⚡" else "#4ade80"
            ic = self._lbl(icon, ic_col, 11, 900)
            ic.setFixedWidth(14)
            tx = self._lbl(txt, col, 10)
            row.addWidget(ic); row.addWidget(tx, 1)
            ly.addLayout(row)

        ly.addStretch()

    def set_duration(self, _): pass
    def get_price(self): return {"ils": LIFETIME["ils"], "usd": LIFETIME["usd"]}
    def set_selected(self, sel: bool):
        if sel:
            self.setStyleSheet("QFrame { background: #0D1117; border: 2px solid #f0c040; border-radius: 12px; }")
        else:
            self.setStyleSheet("QFrame { background: #0D1117; border: 1px solid #2a2010; border-radius: 12px; }")
    def mousePressEvent(self, e): self.clicked.emit("lifetime")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRIAL DIALOG — חלונית ניסיון חינם
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class TrialDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("✨ ניסיון חינם — Experu TG")
        self.setFixedSize(400, 280)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog { background: #0D1117; color: #EEF2FF; }
            QLabel  { color: #EEF2FF; background: transparent; border: none; }
            QLineEdit {
                background: #07090F; color: #22d3b0;
                border: 1px solid #1E2D3D; border-radius: 8px;
                padding: 10px 14px; font-size: 14px;
            }
            QLineEdit:focus { border-color: #22d3b0; }
        """)
        self._build()

    def _build(self):
        ly = QVBoxLayout(self)
        ly.setContentsMargins(28, 28, 28, 24)
        ly.setSpacing(14)

        title = QLabel("✨ 3 ימי ניסיון חינם")
        title.setStyleSheet("color: #4ade80; font-size: 18px; font-weight: 900;")
        title.setAlignment(Qt.AlignCenter)
        ly.addWidget(title)

        sub = QLabel("הכנס שם המשתמש שלך בטלגרם\nמפתח ניסיון ישלח אליך מיד")
        sub.setStyleSheet("color: #6B7280; font-size: 12px;")
        sub.setAlignment(Qt.AlignCenter)
        sub.setWordWrap(True)
        ly.addWidget(sub)

        self._input = QLineEdit()
        self._input.setPlaceholderText("@username")
        self._input.setFixedHeight(44)
        self._input.returnPressed.connect(self._submit)
        ly.addWidget(self._input)

        self._status = QLabel("")
        self._status.setStyleSheet("font-size: 12px; color: #6B7280;")
        self._status.setAlignment(Qt.AlignCenter)
        ly.addWidget(self._status)

        btn = QPushButton("✅  שלח מפתח ניסיון")
        btn.setFixedHeight(46)
        btn.setStyleSheet("""
            QPushButton {
                background: #4ade80; color: #07090F;
                font-size: 14px; font-weight: 900;
                border-radius: 10px; border: none;
            }
            QPushButton:hover { background: #22c55e; }
        """)
        btn.clicked.connect(self._submit)
        ly.addWidget(btn)

        note = QLabel("⚠️ ניסיון חד-פעמי — לא ניתן לחזור על זה")
        note.setStyleSheet("color: #374151; font-size: 10px;")
        note.setAlignment(Qt.AlignCenter)
        ly.addWidget(note)

    def _submit(self):
        tg = self._input.text().strip().lstrip("@")
        if not tg:
            self._status.setText("⚠️ הכנס שם משתמש טלגרם")
            self._status.setStyleSheet("color: #f59e0b; font-size: 12px;")
            return
        mark_trial_used(tg)
        request_trial(tg)
        self._status.setText(f"🎉 הבקשה נשלחה לאדמין! תקבל מפתח ל-@{tg} תוך כמה דקות")
        self._status.setStyleSheet("color: #4ade80; font-size: 12px; font-weight: 700;")
        QTimer.singleShot(2500, self.accept)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN DIALOG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class LicenseDialog(QDialog):
    license_accepted = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚡ Experu TG — רישיון")
        self.setFixedSize(1100, 750)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        self.setStyleSheet("QDialog { background: #07090F; color: #EEF2FF; }")

        self._selected_plan     = "pro"
        self._selected_duration = "1m"
        self._plan_cards: dict  = {}
        self._dur_btns: dict    = {}
        self._worker            = None
        self._pay_worker        = None

        self._build_ui()

    # ────────────────────────────────────────
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: #07090F;")
        self._stack.addWidget(self._build_buy_page())      # 0
        self._stack.addWidget(self._build_activate_page()) # 1
        root.addWidget(self._stack, 1)
        self._switch_page("buy")

    # ────────────────────────────────────────
    # SIDEBAR
    # ────────────────────────────────────────
    def _build_sidebar(self):
        sb = QWidget()
        sb.setFixedWidth(210)
        sb.setStyleSheet("QWidget { background: #0D1117; border-left: 1px solid #1E2D3D; }")
        ly = QVBoxLayout(sb)
        ly.setContentsMargins(16, 28, 16, 24)
        ly.setSpacing(6)

        logo = QLabel("⚡ Experu TG")
        logo.setStyleSheet("color: #22d3b0; font-size: 17px; font-weight: 900; background: transparent; border: none;")
        ly.addWidget(logo)
        ver = QLabel("v2.1")
        ver.setStyleSheet("color: #374151; font-size: 10px; background: transparent; border: none;")
        ly.addWidget(ver)
        ly.addSpacing(16)

        sep = QLabel("ניווט")
        sep.setStyleSheet("color: #374151; font-size: 10px; font-weight: 700; letter-spacing: 1px; background: transparent; border: none;")
        ly.addWidget(sep)

        self._nav_btns = {}
        for key, label in [("buy", "🛒  רכישת תוכנית"), ("activate", "🔑  יש לי מפתח גישה")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(42)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent; color: #6B7280;
                    text-align: right; padding: 10px 12px;
                    border-radius: 8px; font-size: 13px; border: none;
                }
                QPushButton:checked { background: #0D2420; color: #22d3b0; font-weight: 700; }
                QPushButton:hover:!checked { background: #111827; color: #E2E8F0; }
            """)
            btn.pressed.connect(lambda k=key: self._switch_page(k))
            self._nav_btns[key] = btn
            ly.addWidget(btn)

        ly.addStretch()

        # ── ניסיון חינם ──
        if not trial_used():
            trial_box = QFrame()
            trial_box.setStyleSheet("QFrame { background: #111827; border-radius: 10px; border: 1px solid #1E2D3D; }")
            tb_ly = QVBoxLayout(trial_box)
            tb_ly.setContentsMargins(12, 12, 12, 12)
            tb_ly.setSpacing(6)

            tl = QLabel("✨ ניסיון חינם")
            tl.setStyleSheet("color: #4ade80; font-size: 12px; font-weight: 700; background: transparent; border: none;")
            tb_ly.addWidget(tl)

            ts = QLabel("3 ימים ללא תשלום")
            ts.setStyleSheet("color: #6B7280; font-size: 10px; background: transparent; border: none;")
            ts.setWordWrap(True)
            tb_ly.addWidget(ts)

            trial_btn = QPushButton("קבל ניסיון חינם →")
            trial_btn.setFixedHeight(34)
            trial_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(74,222,128,0.12); color: #4ade80;
                    border: 1px solid rgba(74,222,128,0.3);
                    border-radius: 7px; font-size: 11px; font-weight: 700;
                }
                QPushButton:hover { background: rgba(74,222,128,0.22); }
            """)
            trial_btn.clicked.connect(self._open_trial)
            tb_ly.addWidget(trial_btn)
            ly.addWidget(trial_box)
            ly.addSpacing(10)
        else:
            used = QLabel("✓ ניסיון חינם שומש")
            used.setStyleSheet("color: #374151; font-size: 10px; text-align: center; background: transparent; border: none;")
            used.setAlignment(Qt.AlignCenter)
            ly.addWidget(used)
            ly.addSpacing(10)

        support_btn = QPushButton("📞  תמיכה")
        support_btn.setFixedHeight(38)
        support_btn.setStyleSheet("""
            QPushButton {
                background: #111827; color: #6B7280;
                border-radius: 8px; font-size: 12px; font-weight: 600;
                border: 1px solid #1E2D3D;
            }
            QPushButton:hover { color: #22d3b0; border-color: #22d3b0; background: #0D2420; }
        """)
        support_btn.clicked.connect(lambda _: webbrowser.open(SUPPORT_LINK))
        ly.addWidget(support_btn)
        return sb

    def _open_trial(self):
        dlg = TrialDialog(self)
        dlg.exec()
        # אחרי שימוש — הסתר את הכפתור (reload sidebar)
        # בפועל הסימון נשמר ב-TRIAL_USED_FILE

    def _switch_page(self, key):
        pages = {"buy": 0, "activate": 1}
        active_style = """
            QPushButton {
                background: #0D2420; color: #22d3b0; font-weight: 700;
                text-align: right; padding: 10px 12px;
                border-radius: 8px; font-size: 13px; border: none;
            }"""
        inactive_style = """
            QPushButton {
                background: transparent; color: #6B7280;
                text-align: right; padding: 10px 12px;
                border-radius: 8px; font-size: 13px; border: none;
            }
            QPushButton:hover { background: #111827; color: #E2E8F0; }"""
        for k, btn in self._nav_btns.items():
            btn.setStyleSheet(active_style if k == key else inactive_style)
        self._stack.setCurrentIndex(pages[key])

    # ────────────────────────────────────────
    # BUY PAGE
    # ────────────────────────────────────────
    def _dur_btn_style(self, active: bool) -> str:
        if active:
            return (
                "QPushButton { background: #0D2420; color: #22d3b0;"
                " border: 1px solid #22d3b0; border-radius: 7px;"
                " padding: 6px 20px; font-size: 12px; font-weight: 700; }"
                " QPushButton:hover { background: #0D2420; }"
            )
        return (
            "QPushButton { background: transparent; color: #6B7280;"
            " border: none; border-radius: 7px;"
            " padding: 6px 20px; font-size: 12px; font-weight: 600; }"
            " QPushButton:hover { color: #E2E8F0; background: #111827; }"
        )

    def _build_buy_page(self):
        page = QWidget()
        page.setStyleSheet("QWidget { background: #07090F; }")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(28, 24, 28, 20)
        outer.setSpacing(0)

        # כותרת
        h = QLabel("בחר תוכנית")
        h.setStyleSheet("color: #F8FAFC; font-size: 22px; font-weight: 900; background: transparent; border: none;")
        outer.addWidget(h)
        sub = QLabel("שלם בקריפטו (USDT/BTC) — מפתח מגיע מיד לטלגרם שלך")
        sub.setStyleSheet("color: #6B7280; font-size: 12px; margin-top: 3px; background: transparent; border: none;")
        outer.addWidget(sub)
        outer.addSpacing(16)

        # ── בחירת תקופה ── (THE KEY FIX)
        dur_wrap = QFrame()
        dur_wrap.setStyleSheet("QFrame { background: #0D1117; border-radius: 10px; border: none; }")
        dur_lay = QHBoxLayout(dur_wrap)
        dur_lay.setContentsMargins(8, 8, 8, 8)
        dur_lay.setSpacing(6)

        self._dur_btns = {}
        for dk, dl in DURATIONS.items():
            btn = QPushButton(dl)
            btn.setFixedHeight(36)
            saving = SAVINGS.get(dk)
            if saving:
                btn.setToolTip(saving)
            is_active = (dk == "1m")
            btn.setStyleSheet(self._dur_btn_style(is_active))
            btn.pressed.connect(lambda k=dk: self._on_duration(k))
            self._dur_btns[dk] = btn
            dur_lay.addWidget(btn)

        dur_lay.addStretch()
        self._saving_lbl = QLabel("")
        self._saving_lbl.setStyleSheet("color: #4ade80; font-size: 11px; font-weight: 700; background: transparent; border: none;")
        dur_lay.addWidget(self._saving_lbl)

        outer.addWidget(dur_wrap)
        outer.addSpacing(16)

        # ── כרטיסי תוכניות (בתוך scroll אופקי) ──
        cards_container = QWidget()
        cards_container.setStyleSheet("QWidget { background: transparent; }")
        cards_row = QHBoxLayout(cards_container)
        cards_row.setSpacing(10)
        cards_row.setContentsMargins(4, 4, 4, 4)

        self._plan_cards = {}
        for pk, pd in PLANS.items():
            card = PlanCard(pk, pd)
            card.clicked.connect(self._on_plan)
            self._plan_cards[pk] = card
            cards_row.addWidget(card)

        lt = LifetimeCard()
        lt.clicked.connect(self._on_plan)
        self._plan_cards["lifetime"] = lt
        cards_row.addWidget(lt)
        cards_row.addStretch()

        from PySide6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidget(cards_container)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumHeight(400)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:horizontal {
                height: 6px; background: #0D1117; border-radius: 3px;
            }
            QScrollBar::handle:horizontal {
                background: #22d3b0; border-radius: 3px; min-width: 40px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
        """)

        outer.addWidget(scroll, 1)
        outer.addSpacing(16)

        # ── פרטי משלוח ──
        details = QFrame()
        details.setStyleSheet("QFrame { background: #0D1117; border: 1px solid #1E2D3D; border-radius: 10px; }")
        det = QVBoxLayout(details)
        det.setContentsMargins(16, 12, 16, 12)
        det.setSpacing(8)

        dl = QLabel("📬  לאן לשלוח את מפתח הגישה?")
        dl.setStyleSheet("font-size: 12px; font-weight: 700; color: #94A3B8; background: transparent; border: none;")
        det.addWidget(dl)

        row = QHBoxLayout(); row.setSpacing(12)

        tg_col = QVBoxLayout(); tg_col.setSpacing(3)
        tg_col.addWidget(self._small_lbl("📱 שם משתמש טלגרם"))
        self._tg_input = QLineEdit(); self._tg_input.setPlaceholderText("@username"); self._tg_input.setFixedHeight(40)
        self._tg_input.setStyleSheet("QLineEdit { background: #07090F; color: #EEF2FF; border: 1px solid #1E2D3D; border-radius: 8px; padding: 8px 12px; font-size: 13px; } QLineEdit:focus { border-color: #22d3b0; }")
        tg_col.addWidget(self._tg_input)

        or_lbl = QLabel("או"); or_lbl.setStyleSheet("color: #374151; font-size: 12px; background: transparent; border: none;")
        or_lbl.setAlignment(Qt.AlignCenter)

        gm_col = QVBoxLayout(); gm_col.setSpacing(3)
        gm_col.addWidget(self._small_lbl("📧 כתובת Gmail"))
        self._gmail_input = QLineEdit(); self._gmail_input.setPlaceholderText("your@gmail.com"); self._gmail_input.setFixedHeight(40)
        self._gmail_input.setStyleSheet("QLineEdit { background: #07090F; color: #EEF2FF; border: 1px solid #1E2D3D; border-radius: 8px; padding: 8px 12px; font-size: 13px; } QLineEdit:focus { border-color: #22d3b0; }")
        gm_col.addWidget(self._gmail_input)

        row.addLayout(tg_col, 2); row.addWidget(or_lbl); row.addLayout(gm_col, 2)
        det.addLayout(row)
        outer.addWidget(details)
        outer.addSpacing(12)

        # ── תחתית ──
        bot = QHBoxLayout(); bot.setSpacing(14)
        self._price_summary = QLabel("")
        self._price_summary.setStyleSheet("color: #22d3b0; font-size: 13px; font-weight: 700; background: transparent; border: none;")
        self._price_summary.setAlignment(Qt.AlignVCenter)
        bot.addWidget(self._price_summary, 1)

        self._buy_btn = QPushButton("💎  קנה עכשיו — שלם בקריפטו")
        self._buy_btn.setFixedHeight(50); self._buy_btn.setFixedWidth(300)
        self._buy_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #22d3b0,stop:1 #a78bfa);
                color: #07090F; font-size: 14px; font-weight: 900;
                border-radius: 12px; border: none;
            }
            QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #16a085,stop:1 #7c3aed); }
            QPushButton:disabled { background: #1E2330; color: #374151; }
        """)
        self._buy_btn.clicked.connect(self._do_buy)
        bot.addWidget(self._buy_btn)
        outer.addLayout(bot)

        self._on_plan("pro")
        return page

    def _small_lbl(self, txt):
        l = QLabel(txt)
        l.setStyleSheet("font-size: 11px; color: #6B7280; background: transparent; border: none;")
        return l

    # ────────────────────────────────────────
    # ACTIVATE PAGE
    # ────────────────────────────────────────
    def _build_activate_page(self):
        page = QWidget()
        page.setStyleSheet("QWidget { background: #07090F; }")
        ly = QVBoxLayout(page)
        ly.setContentsMargins(80, 0, 80, 60)
        ly.addStretch()

        title = QLabel("🔑 יש לי מפתח גישה")
        title.setStyleSheet("color: #F8FAFC; font-size: 24px; font-weight: 900; background: transparent; border: none;")
        title.setAlignment(Qt.AlignCenter)
        ly.addWidget(title)

        sub = QLabel("הכנס את המפתח שקיבלת לאחר הרכישה")
        sub.setStyleSheet("color: #6B7280; font-size: 13px; background: transparent; border: none;")
        sub.setAlignment(Qt.AlignCenter)
        ly.addWidget(sub)
        ly.addSpacing(28)

        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText("EXPERU-XXXXXX-XXXXXX-XXXXXX-XXXXXX")
        self._key_input.setAlignment(Qt.AlignCenter)
        self._key_input.setFixedHeight(54)
        self._key_input.setStyleSheet("""
            QLineEdit {
                background: #0D1117; color: #22d3b0;
                border: 2px solid #1E2D3D; border-radius: 12px;
                padding: 10px 18px; font-size: 16px;
                font-family: 'Consolas', monospace; letter-spacing: 1px;
            }
            QLineEdit:focus { border-color: #22d3b0; }
        """)
        self._key_input.returnPressed.connect(self._do_activate)
        ly.addWidget(self._key_input)
        ly.addSpacing(12)

        self._activate_btn = QPushButton("✅  הפעל רישיון")
        self._activate_btn.setFixedHeight(52)
        self._activate_btn.setStyleSheet("""
            QPushButton {
                background: #22d3b0; color: #07090F;
                font-size: 15px; font-weight: 900;
                border-radius: 12px; border: none;
            }
            QPushButton:hover { background: #16a085; }
            QPushButton:disabled { background: #1E2330; color: #374151; }
        """)
        self._activate_btn.clicked.connect(self._do_activate)
        ly.addWidget(self._activate_btn)

        self._activate_status = QLabel("")
        self._activate_status.setAlignment(Qt.AlignCenter)
        self._activate_status.setWordWrap(True)
        self._activate_status.setStyleSheet("font-size: 13px; background: transparent; border: none;")
        ly.addWidget(self._activate_status)

        ly.addSpacing(28)

        hint = QFrame()
        hint.setStyleSheet("QFrame { background: #0D1117; border-radius: 10px; border: 1px solid #1E2D3D; }")
        hl = QVBoxLayout(hint); hl.setContentsMargins(20, 14, 20, 14); hl.setSpacing(5)
        for txt, col in [
            ("💡 המפתח נשלח לטלגרם/Gmail שלך מיד אחרי אישור התשלום", "#94A3B8"),
            ("🔒 המפתח נעול למחשב שממנו הופעל בפעם הראשונה", "#4A5568"),
            ("📞 בעיה? צור קשר: @experu_support", "#374151"),
        ]:
            l = QLabel(txt)
            l.setStyleSheet(f"color: {col}; font-size: 11px; background: transparent; border: none;")
            l.setAlignment(Qt.AlignCenter)
            hl.addWidget(l)
        ly.addWidget(hint)
        ly.addStretch()

        back = QPushButton("← חזרה לרכישה")
        back.setFixedHeight(36)
        back.setStyleSheet("""
            QPushButton {
                background: #0D1117; color: #6B7280;
                border: 1px solid #1E2D3D; border-radius: 8px;
                font-size: 12px;
            }
            QPushButton:hover { color: #22d3b0; border-color: #22d3b0; }
        """)
        back.clicked.connect(lambda _: self._switch_page("buy"))
        ly.addWidget(back)
        return page

    # ────────────────────────────────────────
    # LOGIC
    # ────────────────────────────────────────
    def _on_plan(self, plan_key: str):
        self._selected_plan = plan_key
        for k, c in self._plan_cards.items():
            c.set_selected(k == plan_key)
        self._refresh_summary()

    def _on_duration(self, dur: str):
        """מעדכן תקופה + מחירים בכל הכרטיסים"""
        self._selected_duration = dur
        # עדכן style כפתורים ידנית
        for k, btn in self._dur_btns.items():
            btn.setStyleSheet(self._dur_btn_style(k == dur))
        # עדכן מחיר בכל כרטיס — זה העיקר
        for card in self._plan_cards.values():
            card.set_duration(dur)
        # תווית חיסכון
        s = SAVINGS.get(dur)
        self._saving_lbl.setText(f"✓ {s}" if s else "")
        self._refresh_summary()

    def _refresh_summary(self):
        card = self._plan_cards.get(self._selected_plan)
        if not card: return
        p = card.get_price()
        if self._selected_plan == "lifetime":
            self._price_summary.setText(f"♾️ Lifetime | ₪{p['ils']:,} (~${p['usd']:,}) | חד-פעמי לנצח")
        else:
            plan = PLANS[self._selected_plan]
            dl   = DURATIONS[self._selected_duration]
            self._price_summary.setText(f"{plan['emoji']} {plan['name']} | {dl} | ₪{p['ils']:,} (~${p['usd']:,} USDT)")

    def _do_buy(self, _=False):
        tg    = self._tg_input.text().strip().lstrip("@")
        gmail = self._gmail_input.text().strip()
        if not tg and not gmail:
            QMessageBox.warning(self, "⚠️", "הכנס שם משתמש טלגרם או כתובת Gmail")
            return
        contact = tg or gmail
        card    = self._plan_cards[self._selected_plan]
        p       = card.get_price()

        if self._selected_plan == "lifetime":
            plan_name, dur_label, dur_key = "Lifetime ♾️", "לנצח", "lifetime"
        else:
            plan_name = PLANS[self._selected_plan]["name"]
            dur_label = DURATIONS[self._selected_duration]
            dur_key   = self._selected_duration

        self._buy_btn.setEnabled(False)
        self._buy_btn.setText("⏳  יוצר קישור תשלום...")
        self._pay_worker = PaymentWorker(self._selected_plan, dur_key, contact, p["ils"], p["usd"])
        self._pay_worker.result.connect(lambda res: self._on_paid(res, plan_name, dur_label, p))
        self._pay_worker.start()

    def _on_paid(self, result, plan_name, dur_label, p):
        self._buy_btn.setEnabled(True)
        self._buy_btn.setText("💎  קנה עכשיו — שלם בקריפטו")
        if result.get("success"):
            webbrowser.open(result["payment_url"])
            QMessageBox.information(self, "💳 תשלום קריפטו",
                f"נפתח דף תשלום ייחודי שלך בדפדפן!\n\n"
                f"📦 תוכנית: {plan_name} | {dur_label}\n"
                f"💰 סכום: ₪{p['ils']:,} (~${p['usd']:,} USDT)\n\n"
                f"⚡ אחרי אישור התשלום תקבל מפתח לטלגרם/Gmail שלך.\n"
                f"לחץ 'יש לי מפתח גישה' בסרגל הצדי."
            )
            self._switch_page("activate")
        else:
            QMessageBox.critical(self, "❌ שגיאה",
                f"לא ניתן ליצור קישור תשלום:\n{result.get('error','')}\n\nצור קשר: @experu_support")

    def _do_activate(self, _=False):
        key = self._key_input.text().strip()
        if not key:
            self._activate_status.setText("⚠️ הכנס מפתח")
            self._activate_status.setStyleSheet("color: #f59e0b; font-size: 13px; background: transparent; border: none;")
            return
        self._activate_btn.setEnabled(False)
        self._activate_btn.setText("⏳  בודק...")
        self._activate_status.setText("")
        self._worker = LicenseCheckWorker(key)
        self._worker.result.connect(self._on_activated)
        self._worker.start()

    def _on_activated(self, result: LicenseResult):
        self._activate_btn.setEnabled(True)
        self._activate_btn.setText("✅  הפעל רישיון")
        if result.valid:
            plan_name = PLANS.get(result.plan, {}).get("name", result.plan)
            self._activate_status.setText(f"🎉 רישיון תקף! | {plan_name} | עוד {result.days_left} ימים")
            self._activate_status.setStyleSheet("color: #4ade80; font-size: 13px; font-weight: 700; background: transparent; border: none;")
            contact = getattr(self, "_tg_input", None) and self._tg_input.text().strip() or ""
            send_welcome_webhook(result, contact)
            QTimer.singleShot(1400, lambda: self.license_accepted.emit(result))
        else:
            msgs = {
                "key_not_found": "❌ מפתח לא נמצא במערכת",
                "key_revoked":   "🚫 מפתח זה בוטל",
                "expired":       "⏰ הרישיון פג — חדש את המנוי",
                "hwid_mismatch": "💻 המפתח נעול למחשב אחר\n(צור קשר: @experu_support)",
                "no_connection": "🌐 אין חיבור לשרת",
            }
            self._activate_status.setText(msgs.get(result.reason, f"❌ {result.reason}"))
            self._activate_status.setStyleSheet("color: #ef4444; font-size: 12px; background: transparent; border: none;")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PUBLIC API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def check_and_show_license(app: QApplication) -> Optional[LicenseResult]:
    lic = check_license()
    if lic.valid:
        return lic
    result_holder = [None]
    dialog = LicenseDialog()
    def on_accepted(r): result_holder[0] = r; dialog.accept()
    dialog.license_accepted.connect(on_accepted)
    dialog.exec()
    return result_holder[0]
