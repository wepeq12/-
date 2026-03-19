# -*- coding: utf-8 -*-
"""
🔐 license_window.py — חלון רישיון / קנייה
נפתח אוטומטית כשאין רישיון תקף
"""

import os, json, webbrowser, hashlib, platform, uuid, datetime
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QPushButton, QLineEdit, QStackedWidget, QFrame,
    QScrollArea, QGridLayout, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor, QLinearGradient, QPalette, QPixmap, QIcon

try:
    import requests as _req
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
SERVER_URL   = "https://lucid-strength-production.up.railway.app"
LICENSE_FILE = Path(__file__).parent / "license.key"
CACHE_FILE   = Path(__file__).parent / ".lic_cache"
CACHE_TTL_HOURS = 12

NOWPAYMENTS_STORE_URL = "https://lucid-strength-production.up.railway.app/webhook/nowpayments"  # ← תחליף אחרי שתפתח NOWPayments

PLANS = {
    "starter": {
        "name": "Starter",
        "name_he": "מתחיל",
        "emoji": "🔰",
        "color": "#64748b",
        "sessions": 5,
        "trial": True,
        # מחירי ILS
        "price_1m": 290,  "price_3m": 750,  "price_6m": 1300, "price_1y": 2200,
        # מחירי USD (לעיבוד תשלום)
        "usd_1m": 79,     "usd_3m": 202,    "usd_6m": 351,    "usd_1y": 594,
        "features": [
            "✅ 5 סשנים (חשבונות)",
            "✅ סורק קבוצות בסיסי",
            "✅ גירוד משתמשים",
            "✅ הוספת חברים (Adder)",
            "✅ שליחה המונית בסיסית",
            "✅ Anti-Ban בסיסי",
            "❌ Sniper Mode",
            "❌ AI Control Bot",
            "❌ Multi-Client",
        ],
    },
    "pro": {
        "name": "Pro",
        "name_he": "מקצוען",
        "emoji": "🚀",
        "color": "#22d3b0",
        "sessions": 25,
        "popular": True,
        "price_1m": 590,  "price_3m": 1500, "price_6m": 2700, "price_1y": 4800,
        "usd_1m": 159,    "usd_3m": 405,    "usd_6m": 729,    "usd_1y": 1296,
        "features": [
            "✅ 25 סשנים (חשבונות)",
            "✅ סורק קבוצות מתקדם",
            "✅ תמיכה מלאה ב-Proxy",
            "✅ Device Fingerprint",
            "⚡ Sniper Mode",
            "⚡ AI Control Bot (Gemini)",
            "✅ Group Warmup (SEO)",
            "✅ לולאת 24 שעות",
            "❌ Multi-Client",
        ],
    },
    "agency": {
        "name": "Agency",
        "name_he": "סוכנות",
        "emoji": "💼",
        "color": "#a78bfa",
        "sessions": 50,
        "orig_1m": 1200,
        "price_1m": 790,  "price_3m": 1950, "price_6m": 3600, "price_1y": 6200,
        "usd_1m": 213,    "usd_3m": 527,    "usd_6m": 972,    "usd_1y": 1674,
        "features": [
            "✅ 50 סשנים (חשבונות)",
            "✅ הכל מ-Pro",
            "⚡ Multi-Client Dashboard",
            "✅ בידוד מלא בין לקוחות",
            "✅ Mass Reporting",
            "✅ בוט שליטה לכל לקוח",
            "✅ Number Checker מתקדם",
            "✅ עדיפות בתמיכה",
        ],
    },
    "elite": {
        "name": "Elite",
        "name_he": "עילית",
        "emoji": "👑",
        "color": "#f0c040",
        "sessions": 100,
        "unlimited": True,
        "orig_1m": 2500,
        "price_1m": 1350, "price_3m": 3400, "price_6m": 6200, "price_1y": 10500,
        "usd_1m": 365,    "usd_3m": 918,    "usd_6m": 1674,   "usd_1y": 2835,
        "features": [
            "✅ 100+ סשנים ללא הגבלה",
            "✅ הכל מ-Agency",
            "⚡ AI הכי מתקדם (Gemini Pro)",
            "✅ כל העדכונים העתידיים",
            "✅ תמיכה VIP ישירה",
            "✅ גישה ל-Beta פיצ'רים",
            "✅ SLA 99.9% uptime",
            "✅ Onboarding אישי",
        ],
    },
}

LIFETIME = {
    "name": "Lifetime",
    "name_he": "לנצח",
    "emoji": "♾️",
    "color": "#f0c040",
    "price_ils": 7000,
    "price_usd": 1890,
    "orig_ils": 14000,
    "features": [
        "⚡ כל הפיצ'רים לנצח",
        "⚡ סשנים ללא הגבלה",
        "✅ כל העדכונים לעולם",
        "✅ תמיכה VIP ישירה",
        "✅ Beta גישה מוקדמת",
        "✅ Onboarding אישי",
    ],
}

DURATIONS = {
    "1m":  ("חודש 1",     1),
    "3m":  ("3 חודשים",   3),
    "6m":  ("חצי שנה",    6),
    "1y":  ("שנה",       12),
}

# ──────────────────────────────────────────────
# HWID
# ──────────────────────────────────────────────
def get_hwid() -> str:
    parts = [platform.node(), platform.machine(), platform.processor(), str(uuid.getnode())]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]

# ──────────────────────────────────────────────
# LICENSE CHECK
# ──────────────────────────────────────────────
class LicenseResult:
    def __init__(self, valid=False, plan="", plan_info=None, expires_at="",
                 days_left=0, reason="", features=None,
                 max_clients=1, max_sessions=2, multi_client=False):
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

    def has_feature(self, f): return "all" in self.features or f in self.features
    def __bool__(self): return self.valid

def _load_cache() -> Optional[LicenseResult]:
    try:
        if not CACHE_FILE.exists(): return None
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        cached_at = datetime.datetime.fromisoformat(data["cached_at"])
        if (datetime.datetime.utcnow() - cached_at).total_seconds() > CACHE_TTL_HOURS * 3600:
            return None
        return LicenseResult(**{k: v for k, v in data.items() if k != "cached_at"})
    except Exception:
        return None

def _save_cache(r: LicenseResult):
    try:
        data = {k: getattr(r, k) for k in ["valid","plan","plan_info","expires_at","days_left","features","max_clients","max_sessions","multi_client"]}
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
    res = LicenseResult(**{k: d.get(k, LicenseResult.__init__.__defaults__[i]) for i, k in enumerate(["valid","plan","plan_info","expires_at","days_left","reason","features","max_clients","max_sessions","multi_client"])})
    if res.valid:
        LICENSE_FILE.write_text(key, encoding="utf-8")
        _save_cache(res)
    return res

def lookup_account(identifier: str) -> dict:
    """מחפש חשבון קיים לפי שם משתמש טלגרם או Gmail"""
    try:
        r = _req.post(f"{SERVER_URL}/lookup", json={"identifier": identifier}, timeout=8)
        return r.json()
    except Exception:
        return {"found": False, "error": "no_connection"}

# ──────────────────────────────────────────────
# WORKER THREAD
# ──────────────────────────────────────────────
class LicenseCheckWorker(QThread):
    result = Signal(object)
    def __init__(self, key):
        super().__init__()
        self.key = key
    def run(self):
        self.result.emit(check_license(self.key))

class LookupWorker(QThread):
    result = Signal(dict)
    def __init__(self, identifier):
        super().__init__()
        self.identifier = identifier
    def run(self):
        self.result.emit(lookup_account(self.identifier))

class _PaymentWorker(QThread):
    result = Signal(dict)
    def __init__(self, plan, duration, contact):
        super().__init__()
        self.plan = plan
        self.duration = duration
        self.contact = contact
    def run(self):
        try:
            r = _req.post(
                f"{SERVER_URL}/create_payment",
                json={"plan": self.plan, "duration": self.duration, "contact": self.contact},
                timeout=15
            )
            self.result.emit(r.json())
        except Exception as e:
            self.result.emit({"error": str(e)})

# ──────────────────────────────────────────────
# MAIN LICENSE DIALOG
# ──────────────────────────────────────────────
class LicenseDialog(QDialog):
    license_accepted = Signal(object)  # LicenseResult

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔐 Experu TG — רישיון")
        self.setFixedSize(820, 620)
        self.setStyleSheet("""
            QDialog { background: #080b12; color: #e2e8f0; }
            QLabel  { color: #e2e8f0; border: none; background: transparent; }
            QLineEdit {
                background: #111827; color: #e2e8f0;
                border: 1px solid #1e2d45; border-radius: 8px;
                padding: 10px 14px; font-size: 13px;
            }
            QLineEdit:focus { border: 1px solid #3b82f6; }
            QPushButton {
                border-radius: 8px; padding: 10px 20px;
                font-size: 13px; font-weight: 700;
            }
        """)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        self._selected_plan = "starter"
        self._selected_duration = "1m"
        self._build_ui()

    def _build_ui(self):
        main = QHBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # ── סרגל שמאלי ──
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("background: #0d1117; border-right: 1px solid #1e2330;")
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(16, 24, 16, 24)
        sb_layout.setSpacing(8)

        logo = QLabel("⚡ Experu TG")
        logo.setStyleSheet("color: #22d3b0; font-size: 16px; font-weight: 900; padding-bottom: 16px;")
        sb_layout.addWidget(logo)

        self._nav_btns = {}
        nav_items = [
            ("buy",     "🛒 קנה רישיון"),
            ("activate","🔑 יש לי מפתח"),
            ("login",   "👤 חשבון קיים"),
        ]
        for key, label in nav_items:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton { background: transparent; color: #6b7280; text-align: right;
                    padding: 10px 12px; border-radius: 8px; font-size: 12px; }
                QPushButton:checked { background: #0d2420; color: #22d3b0; font-weight: 700; }
                QPushButton:hover:!checked { background: #111827; color: #e2e8f0; }
            """)
            btn.clicked.connect(lambda _, k=key: self._switch_page(k))
            self._nav_btns[key] = btn
            sb_layout.addWidget(btn)

        sb_layout.addStretch()

        support_lbl = QLabel("📞 תמיכה\n@experu_support")
        support_lbl.setStyleSheet("color: #374151; font-size: 10px; text-align: center;")
        support_lbl.setAlignment(Qt.AlignCenter)
        sb_layout.addWidget(support_lbl)

        main.addWidget(sidebar)

        # ── תוכן ראשי ──
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: #080b12;")
        self._stack.addWidget(self._build_buy_page())      # 0
        self._stack.addWidget(self._build_activate_page()) # 1
        self._stack.addWidget(self._build_login_page())    # 2
        main.addWidget(self._stack)

        self._switch_page("buy")

    def _switch_page(self, key):
        pages = {"buy": 0, "activate": 1, "login": 2}
        for k, btn in self._nav_btns.items():
            btn.setChecked(k == key)
        self._stack.setCurrentIndex(pages[key])

    # ═══════════════════════════════════════════
    # דף קנייה
    # ═══════════════════════════════════════════
    def _build_buy_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("🛒 בחר תוכנית")
        title.setStyleSheet("font-size: 20px; font-weight: 900; color: #f8fafc;")
        layout.addWidget(title)

        sub = QLabel("שלם בקריפטו (USDT/BTC) — מפתח מגיע מיד לטלגרם שלך | מחירים ב-₪ / $")
        sub.setStyleSheet("color: #6b7280; font-size: 12px;")
        layout.addWidget(sub)

        # ── בחירת תקופה ──
        dur_row = QHBoxLayout()
        dur_row.addWidget(QLabel("⏱ תקופה:"))
        self._dur_btns = {}
        for dur_key, (dur_label, _) in DURATIONS.items():
            btn = QPushButton(dur_label)
            btn.setCheckable(True)
            btn.setChecked(dur_key == "1m")
            btn.setStyleSheet("""
                QPushButton { background: #111827; color: #94a3b8; border: 1px solid #1e2330;
                    border-radius: 6px; padding: 6px 14px; font-size: 11px; font-weight: 600; }
                QPushButton:checked { background: #0d2420; color: #22d3b0; border-color: #22d3b0; }
            """)
            btn.clicked.connect(lambda _, k=dur_key: self._select_duration(k))
            self._dur_btns[dur_key] = btn
            dur_row.addWidget(btn)
        dur_row.addStretch()
        layout.addLayout(dur_row)

        # ── כרטיסי תוכניות ──
        plans_row = QHBoxLayout()
        plans_row.setSpacing(10)
        self._plan_cards = {}
        for plan_key, plan in PLANS.items():
            card = self._make_plan_card(plan_key, plan)
            self._plan_cards[plan_key] = card
            plans_row.addWidget(card)
        # כרטיס Lifetime
        lt_card = self._make_lifetime_card()
        self._plan_cards["lifetime"] = lt_card
        plans_row.addWidget(lt_card)
        layout.addLayout(plans_row)

        # ── שדות פרטים ──
        details_frame = QFrame()
        details_frame.setStyleSheet("background: #0d1117; border: 1px solid #1e2330; border-radius: 10px;")
        details_layout = QVBoxLayout(details_frame)
        details_layout.setContentsMargins(16, 14, 16, 14)
        details_layout.setSpacing(10)

        details_lbl = QLabel("📬 לאן לשלוח את מפתח הגישה?")
        details_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #94a3b8;")
        details_layout.addWidget(details_lbl)

        row = QHBoxLayout()

        tg_col = QVBoxLayout()
        tg_lbl = QLabel("📱 שם משתמש טלגרם")
        tg_lbl.setStyleSheet("font-size: 11px; color: #6b7280;")
        self._tg_input = QLineEdit()
        self._tg_input.setPlaceholderText("@username")
        tg_col.addWidget(tg_lbl)
        tg_col.addWidget(self._tg_input)

        or_lbl = QLabel("  או  ")
        or_lbl.setStyleSheet("color: #374151; font-size: 12px;")
        or_lbl.setAlignment(Qt.AlignCenter)

        gmail_col = QVBoxLayout()
        gmail_lbl = QLabel("📧 כתובת Gmail")
        gmail_lbl.setStyleSheet("font-size: 11px; color: #6b7280;")
        self._gmail_input = QLineEdit()
        self._gmail_input.setPlaceholderText("your@gmail.com")
        gmail_col.addWidget(gmail_lbl)
        gmail_col.addWidget(self._gmail_input)

        row.addLayout(tg_col)
        row.addWidget(or_lbl)
        row.addLayout(gmail_col)
        details_layout.addLayout(row)
        layout.addWidget(details_frame)

        # ── כפתור קנה ──
        self._buy_btn = QPushButton("💎 קנה עכשיו — שלם בקריפטו")
        self._buy_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #3b82f6,stop:1 #8b5cf6);
                color: white; font-size: 14px; font-weight: 900;
                border-radius: 10px; padding: 14px;
            }
            QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #2563eb,stop:1 #7c3aed); }
        """)
        self._buy_btn.clicked.connect(self._do_buy)
        layout.addWidget(self._buy_btn)

        self._price_label = QLabel("")
        self._price_label.setStyleSheet("color: #3b82f6; font-size: 12px; font-weight: 700;")
        self._price_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._price_label)
        self._update_price_label()

        return page

    def _make_plan_card(self, plan_key, plan):
        card = QFrame()
        card.setFixedHeight(200)
        card.setCursor(Qt.PointingHandCursor)
        self._style_plan_card(card, plan_key, False)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(3)

        # שורת כותרת
        header_row = QHBoxLayout()
        name_lbl = QLabel(f"{plan['emoji']} {plan['name']}")
        name_lbl.setStyleSheet(f"color: {plan['color']}; font-size: 13px; font-weight: 900;")
        header_row.addWidget(name_lbl)
        if plan.get("trial"):
            trial_lbl = QLabel("✨ ניסיון חינם")
            trial_lbl.setStyleSheet("color: #4ade80; font-size: 9px; font-weight: 700; background: rgba(74,222,128,0.1); border-radius: 4px; padding: 2px 5px;")
            header_row.addWidget(trial_lbl)
        header_row.addStretch()
        layout.addLayout(header_row)

        # מחיר
        ils_price = plan['price_1m']
        orig = plan.get('orig_1m')
        if orig:
            orig_lbl = QLabel(f"₪{orig:,}")
            orig_lbl.setStyleSheet("color: #4a5568; font-size: 10px; text-decoration: line-through;")
            layout.addWidget(orig_lbl)
        price_lbl = QLabel(f"₪{ils_price:,}/חודש")
        price_lbl.setObjectName("price_lbl")
        price_lbl.setStyleSheet(f"color: {plan['color']}; font-size: 14px; font-weight: 900;")
        layout.addWidget(price_lbl)

        # סשנים
        sessions = plan.get("sessions", 0)
        sessions_str = "∞" if plan.get("unlimited") else str(sessions)
        sess_lbl = QLabel(f"💻 {sessions_str} סשנים")
        sess_lbl.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 600;")
        layout.addWidget(sess_lbl)

        layout.addSpacing(4)

        for feat in plan["features"][:4]:
            color = "#f0c040" if feat.startswith("⚡") else ("#4ade80" if feat.startswith("✅") else "#4a5568")
            f = QLabel(feat)
            f.setStyleSheet(f"font-size: 10px; color: {color};")
            layout.addWidget(f)

        if plan.get("popular"):
            pop = QLabel("🔥 הנמכרת ביותר")
            pop.setStyleSheet(f"color: {plan['color']}; font-size: 9px; font-weight: 700;")
            layout.addWidget(pop)

        card.mousePressEvent = lambda e, k=plan_key: self._select_plan(k)
        return card

    def _make_lifetime_card(self):
        lt = LIFETIME
        card = QFrame()
        card.setFixedHeight(200)
        card.setCursor(Qt.PointingHandCursor)
        card.setStyleSheet(f"QFrame {{ background: #0d1117; border: 1px solid #2a2010; border-radius: 10px; }}")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(3)

        header = QLabel(f"{lt['emoji']} {lt['name']}")
        header.setStyleSheet(f"color: {lt['color']}; font-size: 13px; font-weight: 900;")
        layout.addWidget(header)

        orig_lbl = QLabel(f"₪{lt['orig_ils']:,}")
        orig_lbl.setStyleSheet("color: #4a5568; font-size: 10px; text-decoration: line-through;")
        layout.addWidget(orig_lbl)

        price_lbl = QLabel(f"₪{lt['price_ils']:,}")
        price_lbl.setObjectName("lt_price_lbl")
        price_lbl.setStyleSheet(f"color: {lt['color']}; font-size: 14px; font-weight: 900;")
        layout.addWidget(price_lbl)

        once_lbl = QLabel("💡 חד-פעמי לנצח")
        once_lbl.setStyleSheet("color: #4ade80; font-size: 9px; font-weight: 700;")
        layout.addWidget(once_lbl)

        layout.addSpacing(4)

        for feat in lt["features"][:4]:
            color = "#f0c040" if feat.startswith("⚡") else "#4ade80"
            f = QLabel(feat)
            f.setStyleSheet(f"font-size: 10px; color: {color};")
            layout.addWidget(f)

        launch = QLabel("🔥 מחיר השקה")
        launch.setStyleSheet(f"color: {lt['color']}; font-size: 9px; font-weight: 700;")
        layout.addWidget(launch)

        card.mousePressEvent = lambda e: self._select_plan("lifetime")
        return card

    def _style_plan_card(self, card, plan_key, selected):
        if plan_key == "lifetime":
            color = LIFETIME["color"]
        else:
            color = PLANS[plan_key]["color"]
        if selected:
            card.setStyleSheet(f"QFrame {{ background: #0d1117; border: 2px solid {color}; border-radius: 10px; }}")
        else:
            card.setStyleSheet("QFrame { background: #0d1117; border: 1px solid #1e2330; border-radius: 10px; }")

    def _select_plan(self, plan_key):
        self._selected_plan = plan_key
        for k, card in self._plan_cards.items():
            self._style_plan_card(card, k, k == plan_key)
        self._update_price_label()

    def _select_duration(self, dur_key):
        self._selected_duration = dur_key
        for k, btn in self._dur_btns.items():
            btn.setChecked(k == dur_key)
        for plan_key, card in self._plan_cards.items():
            if plan_key == "lifetime":
                continue  # Lifetime לא משתנה לפי תקופה
            p = PLANS[plan_key][f"price_{dur_key}"]
            lbl = card.findChild(QLabel, "price_lbl")
            if lbl:
                dur_label = DURATIONS[dur_key][0]
                lbl.setText(f"₪{p:,} / {dur_label}")
        self._update_price_label()

    def _update_price_label(self):
        if self._selected_plan == "lifetime":
            ils = LIFETIME["price_ils"]
            usd = LIFETIME["price_usd"]
            self._price_label.setText(f"♾️ Lifetime | ₪{ils:,} (~${usd:,}) | חד-פעמי לנצח 🔥")
        else:
            plan = PLANS[self._selected_plan]
            ils = plan[f"price_{self._selected_duration}"]
            usd = plan[f"usd_{self._selected_duration}"]
            dur_label = DURATIONS[self._selected_duration][0]
            self._price_label.setText(f"💰 {plan['name']} | {dur_label} | ₪{ils:,} (~${usd:,} USDT)")

    def _do_buy(self):
        tg    = self._tg_input.text().strip().lstrip("@")
        gmail = self._gmail_input.text().strip()
        if not tg and not gmail:
            QMessageBox.warning(self, "⚠️", "הכנס שם משתמש טלגרם או כתובת Gmail")
            return
        contact = tg or gmail
        plan    = self._selected_plan
        dur     = self._selected_duration

        if plan == "lifetime":
            usd_price = LIFETIME["price_usd"]
            ils_price = LIFETIME["price_ils"]
            plan_name = "Lifetime"
        else:
            usd_price = PLANS[plan][f"usd_{dur}"]
            ils_price = PLANS[plan][f"price_{dur}"]
            plan_name = PLANS[plan]["name"]

        self._buy_btn.setEnabled(False)
        self._buy_btn.setText("⏳ יוצר קישור תשלום...")

        self._pay_worker = _PaymentWorker(plan, dur, contact)
        self._pay_worker.result.connect(self._on_payment_created)
        self._pay_worker.start()

    def _on_payment_created(self, result: dict):
        self._buy_btn.setEnabled(True)
        self._buy_btn.setText("💎 קנה עכשיו — שלם בקריפטו")
        if result.get("success"):
            url = result["payment_url"]
            webbrowser.open(url)
            plan = self._selected_plan
            dur  = self._selected_duration
            if plan == "lifetime":
                plan_name = "Lifetime ♾️"
                ils = LIFETIME["price_ils"]
                usd = LIFETIME["price_usd"]
                dur_str = "לנצח"
            else:
                plan_name = PLANS[plan]["name"]
                ils = PLANS[plan][f"price_{dur}"]
                usd = PLANS[plan][f"usd_{dur}"]
                dur_str = DURATIONS[dur][0]
            QMessageBox.information(self, "💳 תשלום קריפטו",
                f"נפתח דף תשלום ייחודי שלך בדפדפן!\n\n"
                f"📦 תוכנית: {plan_name} | {dur_str}\n"
                f"💰 סכום: ₪{ils:,} (~${usd:,} USDT)\n\n"
                f"⚡ אחרי אישור התשלום תקבל מפתח לטלגרם/Gmail שלך.\n"
                f"לאחר מכן לחץ 'יש לי מפתח' בצד שמאל."
            )
            self._switch_page("activate")
        else:
            QMessageBox.critical(self, "❌ שגיאה", f"לא ניתן ליצור קישור תשלום:\n{result.get('error','')}\n\nצור קשר: @experu_support")

    # ═══════════════════════════════════════════
    # דף הפעלת מפתח
    # ═══════════════════════════════════════════
    def _build_activate_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 60, 40, 40)
        layout.setSpacing(16)

        title = QLabel("🔑 הזן מפתח גישה")
        title.setStyleSheet("font-size: 22px; font-weight: 900; color: #f8fafc;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        sub = QLabel("הכנס את המפתח שקיבלת לאחר הרכישה")
        sub.setStyleSheet("color: #6b7280; font-size: 13px;")
        sub.setAlignment(Qt.AlignCenter)
        layout.addWidget(sub)

        layout.addSpacing(20)

        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText("EXPERU-XXXXXX-XXXXXX-XXXXXX-XXXXXX")
        self._key_input.setAlignment(Qt.AlignCenter)
        self._key_input.setFixedHeight(50)
        self._key_input.setStyleSheet("""
            QLineEdit {
                background: #0d1117; color: #e2e8f0;
                border: 2px solid #1e2d45; border-radius: 10px;
                padding: 10px 18px; font-size: 15px;
                font-family: Consolas, monospace; letter-spacing: 1px;
            }
            QLineEdit:focus { border-color: #22d3b0; }
        """)
        layout.addWidget(self._key_input)

        self._activate_btn = QPushButton("✅ הפעל רישיון")
        self._activate_btn.setFixedHeight(48)
        self._activate_btn.setStyleSheet("""
            QPushButton {
                background: #22d3b0; color: #080b12;
                font-size: 15px; font-weight: 900; border-radius: 10px;
            }
            QPushButton:hover { background: #16a085; }
            QPushButton:disabled { background: #1e2330; color: #374151; }
        """)
        self._activate_btn.clicked.connect(self._do_activate)
        layout.addWidget(self._activate_btn)

        self._activate_status = QLabel("")
        self._activate_status.setAlignment(Qt.AlignCenter)
        self._activate_status.setStyleSheet("font-size: 12px;")
        self._activate_status.setWordWrap(True)
        layout.addWidget(self._activate_status)

        layout.addStretch()

        hint = QLabel("עדיין לא קנית? לחץ על 'קנה רישיון' בתפריט")
        hint.setStyleSheet("color: #374151; font-size: 11px;")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        return page

    def _do_activate(self):
        key = self._key_input.text().strip()
        if not key:
            self._activate_status.setText("⚠️ הכנס מפתח")
            self._activate_status.setStyleSheet("color: #f59e0b; font-size: 12px;")
            return
        self._activate_btn.setEnabled(False)
        self._activate_btn.setText("⏳ בודק...")
        self._activate_status.setText("")
        self._worker = LicenseCheckWorker(key)
        self._worker.result.connect(self._on_activate_result)
        self._worker.start()

    def _on_activate_result(self, result: LicenseResult):
        self._activate_btn.setEnabled(True)
        self._activate_btn.setText("✅ הפעל רישיון")
        if result.valid:
            self._activate_status.setText(
                f"🎉 רישיון תקף!\n{PLANS.get(result.plan, LIFETIME if result.plan == 'lifetime' else {}).get('name', result.plan)} | "
                f"עוד {result.days_left} ימים"
            )
            self._activate_status.setStyleSheet("color: #10b981; font-size: 13px; font-weight: 700;")
            QTimer.singleShot(1200, lambda: self.license_accepted.emit(result))
        else:
            reasons = {
                "key_not_found": "❌ מפתח לא נמצא במערכת",
                "key_revoked":   "🚫 מפתח זה בוטל",
                "expired":       "⏰ הרישיון פג — חדש את המנוי",
                "hwid_mismatch": "💻 המפתח נעול למחשב אחר\n(צור קשר עם התמיכה לאיפוס)",
                "no_connection": "🌐 אין חיבור לשרת — בדוק אינטרנט",
            }
            msg = reasons.get(result.reason, f"❌ שגיאה: {result.reason}")
            self._activate_status.setText(msg)
            self._activate_status.setStyleSheet("color: #ef4444; font-size: 12px;")

    # ═══════════════════════════════════════════
    # דף כניסה — חשבון קיים
    # ═══════════════════════════════════════════
    def _build_login_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 50, 40, 40)
        layout.setSpacing(14)

        title = QLabel("👤 כניסה — חשבון קיים")
        title.setStyleSheet("font-size: 22px; font-weight: 900; color: #f8fafc;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        sub = QLabel("החלפת מחשב? הכנס את הפרטים שלך ומפתח הגישה")
        sub.setStyleSheet("color: #6b7280; font-size: 12px;")
        sub.setAlignment(Qt.AlignCenter)
        layout.addWidget(sub)

        layout.addSpacing(10)

        # זיהוי — טלגרם או Gmail
        id_lbl = QLabel("📬 שם משתמש טלגרם או Gmail")
        id_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(id_lbl)

        self._login_id_input = QLineEdit()
        self._login_id_input.setPlaceholderText("@username  או  email@gmail.com")
        self._login_id_input.setFixedHeight(44)
        layout.addWidget(self._login_id_input)

        # מפתח גישה — חובה
        key_lbl = QLabel("🔐 מפתח גישה (חובה)")
        key_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(key_lbl)

        self._login_key_input = QLineEdit()
        self._login_key_input.setPlaceholderText("EXPERU-XXXXXX-XXXXXX-XXXXXX-XXXXXX")
        self._login_key_input.setFixedHeight(44)
        self._login_key_input.setStyleSheet("""
            QLineEdit {
                background: #0d1117; color: #e2e8f0;
                border: 1px solid #1e2d45; border-radius: 8px;
                padding: 10px 14px; font-family: Consolas, monospace;
                font-size: 13px;
            }
            QLineEdit:focus { border-color: #f59e0b; }
        """)
        layout.addWidget(self._login_key_input)

        hint = QLabel("💡 המפתח נשלח אליך בטלגרם / Gmail בזמן הרכישה")
        hint.setStyleSheet("color: #374151; font-size: 10px;")
        layout.addWidget(hint)

        self._login_btn = QPushButton("🔓 כנס למערכת")
        self._login_btn.setFixedHeight(48)
        self._login_btn.setStyleSheet("""
            QPushButton {
                background: #f59e0b; color: #080b12;
                font-size: 15px; font-weight: 900; border-radius: 10px;
            }
            QPushButton:hover { background: #d97706; }
            QPushButton:disabled { background: #1e2330; color: #374151; }
        """)
        self._login_btn.clicked.connect(self._do_login)
        layout.addWidget(self._login_btn)

        self._login_status = QLabel("")
        self._login_status.setAlignment(Qt.AlignCenter)
        self._login_status.setStyleSheet("font-size: 12px;")
        self._login_status.setWordWrap(True)
        layout.addWidget(self._login_status)

        layout.addStretch()

        note = QLabel("🔒 המפתח נעול למחשב שממנו הופעל בפעם הראשונה.\n"
                      "להחלפת מחשב צור קשר: @experu_support")
        note.setStyleSheet("color: #374151; font-size: 10px;")
        note.setAlignment(Qt.AlignCenter)
        note.setWordWrap(True)
        layout.addWidget(note)

        return page

    def _do_login(self):
        identifier = self._login_id_input.text().strip()
        key        = self._login_key_input.text().strip()
        if not identifier:
            self._login_status.setText("⚠️ הכנס שם משתמש טלגרם או Gmail")
            self._login_status.setStyleSheet("color: #f59e0b; font-size: 12px;")
            return
        if not key:
            self._login_status.setText("⚠️ המפתח חובה — בדוק בטלגרם / Gmail שלך")
            self._login_status.setStyleSheet("color: #f59e0b; font-size: 12px;")
            return
        self._login_btn.setEnabled(False)
        self._login_btn.setText("⏳ מאמת...")
        self._login_status.setText("")
        # בדוק ישירות את המפתח (הזיהוי הוא רק לנוחות)
        self._worker = LicenseCheckWorker(key)
        self._worker.result.connect(self._on_login_result)
        self._worker.start()

    def _on_login_result(self, result: LicenseResult):
        self._login_btn.setEnabled(True)
        self._login_btn.setText("🔓 כנס למערכת")
        if result.valid:
            self._login_status.setText(f"✅ ברוך הבא! תוכנית {result.plan} | עוד {result.days_left} ימים")
            self._login_status.setStyleSheet("color: #10b981; font-size: 13px; font-weight: 700;")
            QTimer.singleShot(1000, lambda: self.license_accepted.emit(result))
        else:
            reasons = {
                "key_not_found": "❌ מפתח לא נמצא",
                "key_revoked":   "🚫 מפתח בוטל",
                "expired":       "⏰ רישיון פג",
                "hwid_mismatch": "💻 המפתח נעול למחשב אחר — @experu_support",
                "no_connection": "🌐 אין חיבור לשרת",
            }
            self._login_status.setText(reasons.get(result.reason, f"❌ {result.reason}"))
            self._login_status.setStyleSheet("color: #ef4444; font-size: 12px;")


# ──────────────────────────────────────────────
# פונקציה ראשית — קרא מה-main של התוכנה
# ──────────────────────────────────────────────
def check_and_show_license(app: QApplication) -> Optional[LicenseResult]:
    """
    בודק רישיון קיים. אם תקף — מחזיר LicenseResult.
    אם לא — מציג חלון רישיון ומחכה להפעלה.
    מחזיר None אם המשתמש סגר בלי לרשום.
    """
    # בדוק קאש קודם
    lic = check_license()
    if lic.valid:
        return lic

    # הצג חלון רישיון
    result_holder = [None]
    dialog = LicenseDialog()

    def on_accepted(lic_result):
        result_holder[0] = lic_result
        dialog.accept()

    dialog.license_accepted.connect(on_accepted)
    dialog.exec()
    return result_holder[0]
