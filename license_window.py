# -*- coding: utf-8 -*-
"""
🔐 license_window.py — Experu TG | License & Purchase Window
גרסה 2.0 — עיצוב SaaS מקצועי, מחירים דינמיים, Webhook לטלגרם
"""

import os, json, webbrowser, hashlib, platform, uuid, datetime, threading
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QPushButton, QLineEdit, QStackedWidget, QFrame,
    QScrollArea, QMessageBox, QApplication, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QSize
from PySide6.QtGui import QFont, QCursor, QIcon

try:
    import requests as _req
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SERVER_URL      = "https://lucid-strength-production.up.railway.app"
SUPPORT_LINK    = "https://t.me/experu_support"
LICENSE_FILE    = Path(__file__).parent / "license.key"
CACHE_FILE      = Path(__file__).parent / ".lic_cache"
CACHE_TTL_HOURS = 12

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PLANS DATA — מחירים אמיתיים ₪ + $ לכל תקופה
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PLANS = {
    "starter": {
        "name":     "Starter",
        "name_he":  "מתחיל",
        "emoji":    "🔰",
        "color":    "#64748b",
        "sessions": 5,
        "trial":    True,
        "prices": {
            "1m":  {"ils": 290,   "usd": 79},
            "3m":  {"ils": 750,   "usd": 202},
            "6m":  {"ils": 1300,  "usd": 351},
            "1y":  {"ils": 2200,  "usd": 594},
        },
        "features": [
            ("✓", "5 סשנים (חשבונות)",      True),
            ("✓", "סורק קבוצות בסיסי",       True),
            ("✓", "גירוד משתמשים (Scraper)",  True),
            ("✓", "הוספת חברים (Adder)",      True),
            ("✓", "שליחה המונית בסיסית",      True),
            ("✓", "Anti-Ban בסיסי",           True),
            ("✗", "Sniper Mode",              False),
            ("✗", "AI Control Bot",           False),
            ("✗", "Multi-Client",             False),
        ],
    },
    "pro": {
        "name":     "Pro",
        "name_he":  "מקצוען",
        "emoji":    "🚀",
        "color":    "#22d3b0",
        "sessions": 25,
        "popular":  True,
        "prices": {
            "1m":  {"ils": 590,   "usd": 159},
            "3m":  {"ils": 1500,  "usd": 405},
            "6m":  {"ils": 2700,  "usd": 729},
            "1y":  {"ils": 4800,  "usd": 1296},
        },
        "features": [
            ("✓", "25 סשנים (חשבונות)",       True),
            ("✓", "סורק קבוצות מתקדם",         True),
            ("✓", "Proxy מלא + Device ID",     True),
            ("✓", "Group Warmup (SEO)",        True),
            ("⚡", "Sniper Mode",              True),
            ("⚡", "AI Control Bot (Gemini)",  True),
            ("✓", "לולאת שליחה 24 שעות",       True),
            ("✗", "Multi-Client",             False),
            ("✗", "Mass Reporting",           False),
        ],
    },
    "agency": {
        "name":     "Agency",
        "name_he":  "סוכנות",
        "emoji":    "💼",
        "color":    "#a78bfa",
        "sessions": 50,
        "orig_ils": 1200,
        "prices": {
            "1m":  {"ils": 790,   "usd": 213},
            "3m":  {"ils": 1950,  "usd": 527},
            "6m":  {"ils": 3600,  "usd": 972},
            "1y":  {"ils": 6200,  "usd": 1674},
        },
        "features": [
            ("✓", "50 סשנים (חשבונות)",        True),
            ("✓", "הכל מ-Pro",                 True),
            ("⚡", "Multi-Client Dashboard",   True),
            ("⚡", "Mass Reporting",           True),
            ("✓", "בידוד מלא בין לקוחות",      True),
            ("✓", "בוט שליטה לכל לקוח",        True),
            ("✓", "Number Checker מתקדם",      True),
            ("✓", "עדיפות בתמיכה",             True),
        ],
    },
    "elite": {
        "name":     "Elite",
        "name_he":  "עילית",
        "emoji":    "👑",
        "color":    "#f0c040",
        "sessions": 100,
        "unlimited": True,
        "orig_ils": 2500,
        "prices": {
            "1m":  {"ils": 1350,  "usd": 365},
            "3m":  {"ils": 3400,  "usd": 918},
            "6m":  {"ils": 6200,  "usd": 1674},
            "1y":  {"ils": 10500, "usd": 2835},
        },
        "features": [
            ("✓", "100+ סשנים ללא הגבלה",      True),
            ("✓", "הכל מ-Agency",              True),
            ("⚡", "AI מתקדם (Gemini Pro)",    True),
            ("⚡", "SLA 99.9% uptime",         True),
            ("✓", "כל עדכונים עתידיים",         True),
            ("✓", "תמיכה VIP ישירה",            True),
            ("✓", "גישה ל-Beta פיצ'רים",        True),
            ("✓", "Onboarding אישי",           True),
        ],
    },
}

LIFETIME = {
    "name":     "Lifetime ♾️",
    "name_he":  "לנצח",
    "color":    "#f0c040",
    "ils":      7000,
    "usd":      1890,
    "orig_ils": 14000,
}

DURATIONS = {
    "1m": "חודש 1",
    "3m": "3 חודשים",
    "6m": "חצי שנה",
    "1y": "שנה",
}

DURATION_SAVINGS = {
    "1m": None,
    "3m": "חיסכון ~14%",
    "6m": "חיסכון ~25%",
    "1y": "הכי משתלם",
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HWID + CACHE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_hwid() -> str:
    parts = [platform.node(), platform.machine(), platform.processor(), str(uuid.getnode())]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]


class LicenseResult:
    def __init__(self, valid=False, plan="", plan_info=None, expires_at="",
                 days_left=0, reason="", features=None,
                 max_clients=1, max_sessions=5, multi_client=False):
        self.valid        = valid
        self.plan         = plan
        self.plan_info    = plan_info or {}
        self.expires_at   = expires_at
        self.days_left    = days_left
        self.reason       = reason
        self.features     = features or []
        self.max_clients  = max_clients
        self.max_sessions = max_sessions
        self.multi_client = multi_client

    def has_feature(self, f):
        return "all" in self.features or f in self.features

    def __bool__(self):
        return self.valid


def _load_cache() -> Optional[LicenseResult]:
    try:
        if not CACHE_FILE.exists():
            return None
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        cached_at = datetime.datetime.fromisoformat(data["cached_at"])
        if (datetime.datetime.utcnow() - cached_at).total_seconds() > CACHE_TTL_HOURS * 3600:
            return None
        return LicenseResult(**{k: v for k, v in data.items() if k != "cached_at"})
    except Exception:
        return None


def _save_cache(r: LicenseResult):
    try:
        data = {k: getattr(r, k) for k in ["valid", "plan", "plan_info", "expires_at",
                                             "days_left", "features", "max_clients",
                                             "max_sessions", "multi_client"]}
        data["cached_at"] = datetime.datetime.utcnow().isoformat()
        CACHE_FILE.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass


def check_license(key: str = None) -> LicenseResult:
    if not key:
        key = LICENSE_FILE.read_text(encoding="utf-8").strip() if LICENSE_FILE.exists() else os.getenv("EXPERU_LICENSE_KEY")
    if not key:
        return LicenseResult(False, reason="no_key")
    hwid = get_hwid()
    if not REQUESTS_OK:
        c = _load_cache()
        return c or LicenseResult(False, reason="no_requests")
    try:
        r = _req.post(f"{SERVER_URL}/verify", json={"license_key": key, "hwid": hwid}, timeout=8)
        d = r.json()
    except Exception:
        c = _load_cache()
        return c or LicenseResult(False, reason="no_connection")
    res = LicenseResult(
        valid        = d.get("valid", False),
        plan         = d.get("plan", ""),
        plan_info    = d.get("plan_info", {}),
        expires_at   = d.get("expires_at", ""),
        days_left    = d.get("days_left", 0),
        reason       = d.get("reason", ""),
        features     = d.get("features", []),
        max_clients  = d.get("max_clients", 1),
        max_sessions = d.get("max_sessions", 5),
        multi_client = d.get("multi_client", False),
    )
    if res.valid:
        LICENSE_FILE.write_text(key, encoding="utf-8")
        _save_cache(res)
    return res


def lookup_account(identifier: str) -> dict:
    try:
        r = _req.post(f"{SERVER_URL}/lookup", json={"identifier": identifier}, timeout=8)
        return r.json()
    except Exception:
        return {"found": False, "error": "no_connection"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TELEGRAM WEBHOOK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def send_welcome_webhook(result: LicenseResult, contact: str = ""):
    """שולח הודעת ברוך הבא לבוט הטלגרם אחרי הפעלת רישיון"""
    def _send():
        try:
            plan_name = PLANS.get(result.plan, {}).get("name", result.plan)
            msg = (
                f"🎉 *ברוך הבא ל-Experu TG!*\n\n"
                f"✅ הרישיון שלך הופעל בהצלחה\n"
                f"📦 תוכנית: *{plan_name}*\n"
                f"📅 תוקף: *{result.days_left} ימים* (עד {result.expires_at[:10] if result.expires_at else '—'})\n\n"
                f"🚀 *התחלת עבודה:*\n"
                f"1. פתח את Experu TG\n"
                f"2. הגדר את הסשנים שלך\n"
                f"3. בחר כלי ותתחיל\n\n"
                f"📞 תמיכה: @experu\\_support\n"
                f"_מחשב: {get_hwid()[:8]}..._"
            )
            _req.post(
                f"{SERVER_URL}/webhook/welcome",
                json={"message": msg, "contact": contact, "plan": result.plan},
                timeout=8
            )
        except Exception:
            pass
    threading.Thread(target=_send, daemon=True).start()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WORKER THREADS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class LicenseCheckWorker(QThread):
    result = Signal(object)

    def __init__(self, key):
        super().__init__()
        self.key = key

    def run(self):
        self.result.emit(check_license(self.key))


class PaymentWorker(QThread):
    result = Signal(dict)

    def __init__(self, plan, duration, contact, ils_amount, usd_amount):
        super().__init__()
        self.plan = plan
        self.duration = duration
        self.contact = contact
        self.ils_amount = ils_amount
        self.usd_amount = usd_amount

    def run(self):
        try:
            r = _req.post(
                f"{SERVER_URL}/create_payment",
                json={
                    "plan": self.plan,
                    "duration": self.duration,
                    "contact": self.contact,
                    "ils_amount": self.ils_amount,
                    "usd_amount": self.usd_amount,
                },
                timeout=15
            )
            self.result.emit(r.json())
        except Exception as e:
            self.result.emit({"error": str(e)})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STYLE HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BASE_STYLE = """
QDialog, QWidget {
    background: #07090F;
    color: #EEF2FF;
    font-family: 'Segoe UI', 'Arial', sans-serif;
}
QLabel {
    color: #EEF2FF;
    border: none;
    background: transparent;
}
QLineEdit {
    background: #0D1117;
    color: #EEF2FF;
    border: 1px solid #1E2D3D;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    selection-background-color: #22d3b0;
}
QLineEdit:focus {
    border: 1px solid #22d3b0;
}
QScrollArea {
    border: none;
    background: transparent;
}
QScrollBar:vertical {
    width: 6px;
    background: #0D1117;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #1E2D3D;
    border-radius: 3px;
}
"""


def btn_style(bg="#22d3b0", fg="#07090F", hover="#16a085", radius=10, fs=14, fw=700, pad="14px"):
    return f"""
        QPushButton {{
            background: {bg}; color: {fg};
            font-size: {fs}px; font-weight: {fw};
            border-radius: {radius}px; padding: {pad};
            border: none;
        }}
        QPushButton:hover {{ background: {hover}; }}
        QPushButton:disabled {{ background: #1E2330; color: #374151; }}
    """


def card_style(border_color="#1E2D3D", bg="#0D1117", radius=12):
    return f"QFrame {{ background: {bg}; border: 1px solid {border_color}; border-radius: {radius}px; }}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PLAN CARD WIDGET
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class PlanCard(QFrame):
    clicked = Signal(str)

    def __init__(self, plan_key: str, plan: dict, parent=None):
        super().__init__(parent)
        self.plan_key = plan_key
        self.plan     = plan
        self.selected = False
        self._duration = "1m"
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedWidth(200)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self._build()
        self._apply_style(False)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(6)

        # כותרת + badge
        top = QHBoxLayout()
        name_lbl = QLabel(f"{self.plan['emoji']} {self.plan['name']}")
        name_lbl.setStyleSheet(f"color: {self.plan['color']}; font-size: 14px; font-weight: 900;")
        top.addWidget(name_lbl)
        top.addStretch()
        if self.plan.get("popular"):
            badge = QLabel("🔥")
            badge.setToolTip("הנמכרת ביותר")
            badge.setStyleSheet("font-size: 14px;")
            top.addWidget(badge)
        if self.plan.get("trial"):
            trial = QLabel("✨ ניסיון")
            trial.setStyleSheet(
                "color: #4ade80; font-size: 9px; font-weight: 700;"
                "background: rgba(74,222,128,0.12); border-radius: 4px; padding: 2px 5px;"
            )
            top.addWidget(trial)
        layout.addLayout(top)

        # מחיר
        self._price_lbl = QLabel()
        self._price_lbl.setStyleSheet(f"color: {self.plan['color']}; font-size: 20px; font-weight: 900; letter-spacing: -1px;")
        layout.addWidget(self._price_lbl)

        self._usd_lbl = QLabel()
        self._usd_lbl.setStyleSheet("color: #4A5568; font-size: 10px;")
        layout.addWidget(self._usd_lbl)

        # מחיר מקורי אם קיים
        if self.plan.get("orig_ils"):
            orig = QLabel(f"₪{self.plan['orig_ils']:,}")
            orig.setStyleSheet("color: #374151; font-size: 10px; text-decoration: line-through;")
            layout.addWidget(orig)

        # סשנים
        sess = "∞" if self.plan.get("unlimited") else str(self.plan.get("sessions", 0))
        sess_lbl = QLabel(f"💻 {sess} סשנים")
        sess_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600; margin-top: 2px;")
        layout.addWidget(sess_lbl)

        # קו הפרדה
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background: #1E2D3D; border: none;")
        layout.addWidget(line)

        # פיצ'רים
        for icon, feat_name, included in self.plan["features"]:
            row = QHBoxLayout()
            row.setSpacing(5)
            if icon == "⚡":
                icon_color = "#f0c040"
            elif included:
                icon_color = "#4ade80"
            else:
                icon_color = "#374151"
            icon_lbl = QLabel(icon)
            icon_lbl.setStyleSheet(f"color: {icon_color}; font-size: 11px; font-weight: 900;")
            icon_lbl.setFixedWidth(14)
            feat_lbl = QLabel(feat_name)
            feat_lbl.setStyleSheet(f"color: {'#CBD5E1' if included else '#374151'}; font-size: 10px;")
            feat_lbl.setWordWrap(True)
            row.addWidget(icon_lbl)
            row.addWidget(feat_lbl, 1)
            layout.addLayout(row)

        layout.addStretch()
        self._update_price("1m")

    def _update_price(self, duration: str):
        self._duration = duration
        p = self.plan["prices"][duration]
        self._price_lbl.setText(f"₪{p['ils']:,}")
        self._usd_lbl.setText(f"~${p['usd']:,} | {DURATIONS[duration]}")

    def set_duration(self, duration: str):
        self._update_price(duration)

    def get_price(self) -> dict:
        return self.plan["prices"][self._duration]

    def set_selected(self, sel: bool):
        self.selected = sel
        self._apply_style(sel)

    def _apply_style(self, selected: bool):
        color = self.plan["color"]
        if selected:
            self.setStyleSheet(
                f"QFrame {{ background: #0D1117; border: 2px solid {color};"
                f"border-radius: 12px; }}"
            )
        else:
            self.setStyleSheet(card_style())

    def mousePressEvent(self, event):
        self.clicked.emit(self.plan_key)


class LifetimeCard(QFrame):
    clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedWidth(200)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self._build()
        self.setStyleSheet(card_style("#2a2010"))

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(6)

        top = QHBoxLayout()
        name = QLabel(f"♾️ Lifetime")
        name.setStyleSheet(f"color: {LIFETIME['color']}; font-size: 14px; font-weight: 900;")
        top.addWidget(name)
        top.addStretch()
        launch = QLabel("🔥")
        launch.setToolTip("מחיר השקה")
        top.addWidget(launch)
        layout.addLayout(top)

        orig = QLabel(f"₪{LIFETIME['orig_ils']:,}")
        orig.setStyleSheet("color: #374151; font-size: 10px; text-decoration: line-through;")
        layout.addWidget(orig)

        price = QLabel(f"₪{LIFETIME['ils']:,}")
        price.setStyleSheet(f"color: {LIFETIME['color']}; font-size: 20px; font-weight: 900; letter-spacing: -1px;")
        layout.addWidget(price)

        once = QLabel("💡 חד-פעמי לנצח")
        once.setStyleSheet("color: #4ade80; font-size: 10px; font-weight: 700;")
        layout.addWidget(once)

        sess = QLabel("💻 ∞ סשנים לנצח")
        sess.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600; margin-top: 2px;")
        layout.addWidget(sess)

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background: #2a2010; border: none;")
        layout.addWidget(line)

        feats = [
            ("⚡", "כל הפיצ'רים לנצח"),
            ("⚡", "כל עדכונים עתידיים"),
            ("✓",  "תמיכה VIP ישירה"),
            ("✓",  "Beta גישה מוקדמת"),
            ("✓",  "Onboarding אישי"),
            ("✓",  "ללא תשלום חוזר"),
        ]
        for icon, txt in feats:
            row = QHBoxLayout()
            row.setSpacing(5)
            ic = QLabel(icon)
            ic.setStyleSheet(f"color: {'#f0c040' if icon == '⚡' else '#4ade80'}; font-size: 11px; font-weight: 900;")
            ic.setFixedWidth(14)
            tl = QLabel(txt)
            tl.setStyleSheet("color: #CBD5E1; font-size: 10px;")
            row.addWidget(ic)
            row.addWidget(tl, 1)
            layout.addLayout(row)

        layout.addStretch()

    def set_selected(self, sel: bool):
        if sel:
            self.setStyleSheet(f"QFrame {{ background: #0D1117; border: 2px solid {LIFETIME['color']}; border-radius: 12px; }}")
        else:
            self.setStyleSheet(card_style("#2a2010"))

    def set_duration(self, _):
        pass  # Lifetime לא תלוי תקופה

    def get_price(self) -> dict:
        return {"ils": LIFETIME["ils"], "usd": LIFETIME["usd"]}

    def mousePressEvent(self, event):
        self.clicked.emit("lifetime")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN DIALOG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class LicenseDialog(QDialog):
    license_accepted = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚡ Experu TG — רישיון")
        self.setFixedSize(1100, 750)
        self.setStyleSheet(BASE_STYLE)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)

        self._selected_plan     = "pro"
        self._selected_duration = "1m"
        self._plan_cards: dict[str, QFrame] = {}
        self._dur_btns: dict[str, QPushButton] = {}
        self._worker = None
        self._pay_worker = None

        self._build_ui()

    # ─────────────────────────────────────────────
    # BUILD UI
    # ─────────────────────────────────────────────
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

    # ─────────────────────────────────────────────
    # SIDEBAR
    # ─────────────────────────────────────────────
    def _build_sidebar(self):
        sb = QWidget()
        sb.setFixedWidth(210)
        sb.setStyleSheet("background: #0D1117; border-left: 1px solid #1E2D3D;")
        lay = QVBoxLayout(sb)
        lay.setContentsMargins(16, 28, 16, 24)
        lay.setSpacing(6)

        # Logo
        logo = QLabel("⚡ Experu TG")
        logo.setStyleSheet("color: #22d3b0; font-size: 17px; font-weight: 900; padding-bottom: 4px;")
        lay.addWidget(logo)

        ver = QLabel("v2.0")
        ver.setStyleSheet("color: #374151; font-size: 10px;")
        lay.addWidget(ver)

        lay.addSpacing(20)

        sep = QLabel("ניווט")
        sep.setStyleSheet("color: #374151; font-size: 10px; font-weight: 700; letter-spacing: 1px;")
        lay.addWidget(sep)

        self._nav_btns = {}
        nav_items = [
            ("buy",      "🛒  רכישת תוכנית"),
            ("activate", "🔑  יש לי מפתח"),
        ]
        for key, label in nav_items:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(40)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent; color: #6B7280;
                    text-align: right; padding: 10px 12px;
                    border-radius: 8px; font-size: 13px;
                    border: none;
                }
                QPushButton:checked {
                    background: #0D2420; color: #22d3b0; font-weight: 700;
                }
                QPushButton:hover:!checked {
                    background: #111827; color: #E2E8F0;
                }
            """)
            btn.clicked.connect(lambda _, k=key: self._switch_page(k))
            self._nav_btns[key] = btn
            lay.addWidget(btn)

        lay.addStretch()

        # מידע תחתון
        info_box = QFrame()
        info_box.setStyleSheet("QFrame { background: #111827; border-radius: 8px; border: none; }")
        info_lay = QVBoxLayout(info_box)
        info_lay.setContentsMargins(12, 12, 12, 12)
        info_lay.setSpacing(4)

        info_title = QLabel("💡 ניסיון חינם")
        info_title.setStyleSheet("color: #4ade80; font-size: 11px; font-weight: 700;")
        info_lay.addWidget(info_title)

        info_txt = QLabel("Starter כולל 3 ימי ניסיון ללא תשלום")
        info_txt.setStyleSheet("color: #6B7280; font-size: 10px;")
        info_txt.setWordWrap(True)
        info_lay.addWidget(info_txt)

        lay.addWidget(info_box)
        lay.addSpacing(12)

        # כפתור תמיכה
        support_btn = QPushButton("📞  תמיכה")
        support_btn.setFixedHeight(38)
        support_btn.setStyleSheet("""
            QPushButton {
                background: #111827; color: #6B7280;
                border-radius: 8px; font-size: 12px; font-weight: 600;
                border: 1px solid #1E2D3D; text-align: center;
            }
            QPushButton:hover { color: #22d3b0; border-color: #22d3b0; }
        """)
        support_btn.clicked.connect(lambda _: webbrowser.open(SUPPORT_LINK))
        lay.addWidget(support_btn)

        return sb

    def _switch_page(self, key):
        pages = {"buy": 0, "activate": 1}
        for k, btn in self._nav_btns.items():
            btn.setChecked(k == key)
        self._stack.setCurrentIndex(pages[key])

    # ─────────────────────────────────────────────
    # BUY PAGE
    # ─────────────────────────────────────────────
    def _build_buy_page(self):
        page = QWidget()
        page.setStyleSheet("background: #07090F;")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(32, 28, 32, 24)
        outer.setSpacing(0)

        # כותרת
        title = QLabel("בחר תוכנית")
        title.setStyleSheet("font-size: 22px; font-weight: 900; color: #F8FAFC; letter-spacing: -0.5px;")
        outer.addWidget(title)

        sub = QLabel("שלם בקריפטו (USDT/BTC) — מפתח מגיע מיד לטלגרם שלך")
        sub.setStyleSheet("color: #6B7280; font-size: 12px; margin-top: 4px;")
        outer.addWidget(sub)

        outer.addSpacing(20)

        # ── בחירת תקופה ──
        dur_wrap = QFrame()
        dur_wrap.setStyleSheet("QFrame { background: #0D1117; border-radius: 10px; border: none; }")
        dur_lay = QHBoxLayout(dur_wrap)
        dur_lay.setContentsMargins(8, 8, 8, 8)
        dur_lay.setSpacing(6)

        self._dur_btns = {}
        for dur_key, dur_label in DURATIONS.items():
            btn = QPushButton(dur_label)
            btn.setFixedHeight(36)
            btn.setCheckable(True)
            btn.setChecked(dur_key == "1m")
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent; color: #6B7280;
                    border: none; border-radius: 7px;
                    padding: 6px 18px; font-size: 12px; font-weight: 600;
                }
                QPushButton:checked {
                    background: #0D2420; color: #22d3b0;
                    border: 1px solid #22d3b0;
                }
                QPushButton:hover:!checked { color: #E2E8F0; }
            """)
            saving = DURATION_SAVINGS.get(dur_key)
            if saving:
                btn.setToolTip(saving)
            btn.clicked.connect(lambda _, k=dur_key: self._select_duration(k))
            self._dur_btns[dur_key] = btn
            dur_lay.addWidget(btn)

        dur_lay.addStretch()

        self._saving_lbl = QLabel("")
        self._saving_lbl.setStyleSheet("color: #4ade80; font-size: 11px; font-weight: 700;")
        dur_lay.addWidget(self._saving_lbl)

        outer.addWidget(dur_wrap)
        outer.addSpacing(18)

        # ── כרטיסי תוכניות ──
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        cards_row.setContentsMargins(0, 0, 0, 0)

        self._plan_cards = {}

        for plan_key, plan_data in PLANS.items():
            card = PlanCard(plan_key, plan_data)
            card.clicked.connect(self._select_plan)
            self._plan_cards[plan_key] = card
            cards_row.addWidget(card)

        lt_card = LifetimeCard()
        lt_card.clicked.connect(self._select_plan)
        self._plan_cards["lifetime"] = lt_card
        cards_row.addWidget(lt_card)

        outer.addLayout(cards_row, 1)
        outer.addSpacing(18)

        # ── פרטי שליחת מפתח ──
        details = QFrame()
        details.setStyleSheet("QFrame { background: #0D1117; border: 1px solid #1E2D3D; border-radius: 10px; }")
        det_lay = QVBoxLayout(details)
        det_lay.setContentsMargins(16, 14, 16, 14)
        det_lay.setSpacing(10)

        det_title = QLabel("📬  לאן לשלוח את מפתח הגישה?")
        det_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #94A3B8;")
        det_lay.addWidget(det_title)

        fields_row = QHBoxLayout()
        fields_row.setSpacing(12)

        tg_col = QVBoxLayout()
        tg_col.setSpacing(4)
        tg_lbl = QLabel("📱 שם משתמש טלגרם")
        tg_lbl.setStyleSheet("font-size: 11px; color: #6B7280;")
        self._tg_input = QLineEdit()
        self._tg_input.setPlaceholderText("@username")
        self._tg_input.setFixedHeight(40)
        tg_col.addWidget(tg_lbl)
        tg_col.addWidget(self._tg_input)

        or_lbl = QLabel("או")
        or_lbl.setStyleSheet("color: #374151; font-size: 12px;")
        or_lbl.setAlignment(Qt.AlignCenter)

        gmail_col = QVBoxLayout()
        gmail_col.setSpacing(4)
        gmail_lbl = QLabel("📧 כתובת Gmail")
        gmail_lbl.setStyleSheet("font-size: 11px; color: #6B7280;")
        self._gmail_input = QLineEdit()
        self._gmail_input.setPlaceholderText("your@gmail.com")
        self._gmail_input.setFixedHeight(40)
        gmail_col.addWidget(gmail_lbl)
        gmail_col.addWidget(self._gmail_input)

        fields_row.addLayout(tg_col, 2)
        fields_row.addWidget(or_lbl)
        fields_row.addLayout(gmail_col, 2)
        det_lay.addLayout(fields_row)

        outer.addWidget(details)
        outer.addSpacing(14)

        # ── כפתור קנה + תווית מחיר ──
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(14)

        self._price_summary = QLabel("")
        self._price_summary.setStyleSheet("color: #22d3b0; font-size: 13px; font-weight: 700;")
        self._price_summary.setAlignment(Qt.AlignVCenter)
        bottom_row.addWidget(self._price_summary, 1)

        self._buy_btn = QPushButton("💎  קנה עכשיו — שלם בקריפטו")
        self._buy_btn.setFixedHeight(50)
        self._buy_btn.setFixedWidth(300)
        self._buy_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #22d3b0,stop:1 #a78bfa);
                color: #07090F; font-size: 14px; font-weight: 900;
                border-radius: 12px; border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #16a085,stop:1 #7c3aed);
            }
            QPushButton:disabled { background: #1E2330; color: #374151; }
        """)
        self._buy_btn.clicked.connect(self._do_buy)
        bottom_row.addWidget(self._buy_btn)

        outer.addLayout(bottom_row)

        # בחר Pro כברירת מחדל
        self._select_plan("pro")
        return page

    # ─────────────────────────────────────────────
    # ACTIVATE PAGE
    # ─────────────────────────────────────────────
    def _build_activate_page(self):
        page = QWidget()
        page.setStyleSheet("background: #07090F;")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(80, 80, 80, 60)
        lay.setSpacing(16)
        lay.addStretch()

        title = QLabel("🔑 הזן מפתח גישה")
        title.setStyleSheet("font-size: 24px; font-weight: 900; color: #F8FAFC; letter-spacing: -0.5px;")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        sub = QLabel("הכנס את המפתח שקיבלת לאחר הרכישה")
        sub.setStyleSheet("color: #6B7280; font-size: 13px;")
        sub.setAlignment(Qt.AlignCenter)
        lay.addWidget(sub)

        lay.addSpacing(24)

        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText("EXPERU-XXXXXX-XXXXXX-XXXXXX-XXXXXX")
        self._key_input.setAlignment(Qt.AlignCenter)
        self._key_input.setFixedHeight(54)
        self._key_input.setStyleSheet("""
            QLineEdit {
                background: #0D1117; color: #22d3b0;
                border: 2px solid #1E2D3D; border-radius: 12px;
                padding: 10px 18px; font-size: 16px;
                font-family: 'Consolas', 'Courier New', monospace;
                letter-spacing: 1px;
            }
            QLineEdit:focus { border-color: #22d3b0; }
        """)
        self._key_input.returnPressed.connect(self._do_activate)
        lay.addWidget(self._key_input)

        self._activate_btn = QPushButton("✅  הפעל רישיון")
        self._activate_btn.setFixedHeight(52)
        self._activate_btn.setStyleSheet(btn_style(bg="#22d3b0", fg="#07090F", hover="#16a085", fs=15))
        self._activate_btn.clicked.connect(self._do_activate)
        lay.addWidget(self._activate_btn)

        self._activate_status = QLabel("")
        self._activate_status.setAlignment(Qt.AlignCenter)
        self._activate_status.setWordWrap(True)
        self._activate_status.setStyleSheet("font-size: 13px;")
        lay.addWidget(self._activate_status)

        lay.addSpacing(32)

        # קופון / הערה
        hint = QFrame()
        hint.setStyleSheet("QFrame { background: #0D1117; border-radius: 10px; border: 1px solid #1E2D3D; }")
        hint_lay = QVBoxLayout(hint)
        hint_lay.setContentsMargins(20, 14, 20, 14)

        h1 = QLabel("💡 המפתח נשלח לטלגרם/Gmail שלך מיד אחרי אישור התשלום")
        h1.setStyleSheet("color: #94A3B8; font-size: 12px;")
        h1.setAlignment(Qt.AlignCenter)
        hint_lay.addWidget(h1)

        h2 = QLabel("🔒 המפתח נעול למחשב שממנו הופעל בפעם הראשונה")
        h2.setStyleSheet("color: #4A5568; font-size: 11px;")
        h2.setAlignment(Qt.AlignCenter)
        hint_lay.addWidget(h2)

        lay.addWidget(hint)
        lay.addStretch()

        go_buy = QPushButton("← חזרה לרכישה")
        go_buy.setStyleSheet(btn_style(bg="#0D1117", fg="#6B7280", hover="#111827", fs=12, pad="10px"))
        go_buy.clicked.connect(lambda _: self._switch_page("buy"))
        lay.addWidget(go_buy)

        return page

    # ─────────────────────────────────────────────
    # LOGIC
    # ─────────────────────────────────────────────
    def _select_plan(self, plan_key: str):
        self._selected_plan = plan_key
        for k, card in self._plan_cards.items():
            card.set_selected(k == plan_key)
        self._refresh_price_summary()

    def _select_duration(self, dur_key: str):
        self._selected_duration = dur_key
        for k, btn in self._dur_btns.items():
            btn.setChecked(k == dur_key)
        # עדכן מחירים בכל הכרטיסים
        for card in self._plan_cards.values():
            card.set_duration(dur_key)
        # תווית חיסכון
        saving = DURATION_SAVINGS.get(dur_key)
        self._saving_lbl.setText(f"✓ {saving}" if saving else "")
        self._refresh_price_summary()

    def _refresh_price_summary(self):
        card = self._plan_cards.get(self._selected_plan)
        if not card:
            return
        p = card.get_price()
        if self._selected_plan == "lifetime":
            self._price_summary.setText(f"♾️ Lifetime | ₪{p['ils']:,} (~${p['usd']:,}) | חד-פעמי לנצח")
        else:
            plan = PLANS[self._selected_plan]
            dur_label = DURATIONS[self._selected_duration]
            self._price_summary.setText(
                f"{plan['emoji']} {plan['name']} | {dur_label} | ₪{p['ils']:,} (~${p['usd']:,} USDT)"
            )

    def _do_buy(self, _checked=False):
        tg    = self._tg_input.text().strip().lstrip("@")
        gmail = self._gmail_input.text().strip()
        if not tg and not gmail:
            QMessageBox.warning(self, "⚠️", "הכנס שם משתמש טלגרם או כתובת Gmail")
            return
        contact = tg or gmail
        card = self._plan_cards[self._selected_plan]
        p = card.get_price()

        if self._selected_plan == "lifetime":
            plan_name = "Lifetime ♾️"
            dur_label = "לנצח"
            dur_key   = "lifetime"
        else:
            plan_name = PLANS[self._selected_plan]["name"]
            dur_label = DURATIONS[self._selected_duration]
            dur_key   = self._selected_duration

        self._buy_btn.setEnabled(False)
        self._buy_btn.setText("⏳  יוצר קישור תשלום...")

        self._pay_worker = PaymentWorker(
            self._selected_plan, dur_key, contact, p["ils"], p["usd"]
        )
        self._pay_worker.result.connect(
            lambda res: self._on_payment_created(res, plan_name, dur_label, p)
        )
        self._pay_worker.start()

    def _on_payment_created(self, result: dict, plan_name: str, dur_label: str, p: dict):
        self._buy_btn.setEnabled(True)
        self._buy_btn.setText("💎  קנה עכשיו — שלם בקריפטו")
        if result.get("success"):
            webbrowser.open(result["payment_url"])
            QMessageBox.information(
                self, "💳 תשלום קריפטו",
                f"נפתח דף תשלום ייחודי שלך בדפדפן!\n\n"
                f"📦 תוכנית: {plan_name} | {dur_label}\n"
                f"💰 סכום: ₪{p['ils']:,} (~${p['usd']:,} USDT)\n\n"
                f"⚡ אחרי אישור התשלום תקבל מפתח לטלגרם/Gmail.\n"
                f"לאחר מכן לחץ 'יש לי מפתח' בסרגל הצדי."
            )
            self._switch_page("activate")
        else:
            QMessageBox.critical(
                self, "❌ שגיאה",
                f"לא ניתן ליצור קישור תשלום:\n{result.get('error', '')}\n\nצור קשר: @experu_support"
            )

    def _do_activate(self, _checked=False):
        key = self._key_input.text().strip()
        if not key:
            self._activate_status.setText("⚠️ הכנס מפתח")
            self._activate_status.setStyleSheet("color: #f59e0b; font-size: 13px;")
            return
        self._activate_btn.setEnabled(False)
        self._activate_btn.setText("⏳  בודק...")
        self._activate_status.setText("")
        self._worker = LicenseCheckWorker(key)
        self._worker.result.connect(self._on_activate_result)
        self._worker.start()

    def _on_activate_result(self, result: LicenseResult):
        self._activate_btn.setEnabled(True)
        self._activate_btn.setText("✅  הפעל רישיון")
        if result.valid:
            plan_name = PLANS.get(result.plan, {}).get("name", result.plan)
            self._activate_status.setText(
                f"🎉 רישיון תקף! | {plan_name} | עוד {result.days_left} ימים"
            )
            self._activate_status.setStyleSheet("color: #4ade80; font-size: 13px; font-weight: 700;")
            # שלח Webhook ברוך הבא
            contact = self._tg_input.text().strip() or self._gmail_input.text().strip() if hasattr(self, "_tg_input") else ""
            send_welcome_webhook(result, contact)
            QTimer.singleShot(1400, lambda: self.license_accepted.emit(result))
        else:
            msgs = {
                "key_not_found": "❌ מפתח לא נמצא במערכת",
                "key_revoked":   "🚫 מפתח זה בוטל",
                "expired":       "⏰ הרישיון פג — חדש את המנוי",
                "hwid_mismatch": "💻 המפתח נעול למחשב אחר\n(צור קשר: @experu_support לאיפוס)",
                "no_connection": "🌐 אין חיבור לשרת — בדוק אינטרנט",
            }
            self._activate_status.setText(msgs.get(result.reason, f"❌ שגיאה: {result.reason}"))
            self._activate_status.setStyleSheet("color: #ef4444; font-size: 12px;")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PUBLIC API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def check_and_show_license(app: QApplication) -> Optional[LicenseResult]:
    """
    בודק רישיון קיים. אם תקף — מחזיר LicenseResult.
    אם לא — מציג חלון רישיון ומחכה להפעלה.
    מחזיר None אם המשתמש סגר בלי לרשום.
    """
    lic = check_license()
    if lic.valid:
        return lic

    result_holder = [None]
    dialog = LicenseDialog()

    def on_accepted(lic_result):
        result_holder[0] = lic_result
        dialog.accept()

    dialog.license_accepted.connect(on_accepted)
    dialog.exec()
    return result_holder[0]
