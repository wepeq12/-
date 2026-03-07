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
    QMessageBox, QApplication
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QFont

try:
    import requests as _req
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

# ──────────────────────────────────────────────
SERVER_URL      = "https://lucid-strength-production.up.railway.app"
LICENSE_FILE    = Path(__file__).parent / "license.key"
CACHE_FILE      = Path(__file__).parent / ".lic_cache"
CACHE_TTL_HOURS = 12

PLANS = {
    "trial": {
        "name": "ניסיון חינם",
        "emoji": "🎁",
        "color": "#10b981",
        "price_1m": 0, "price_3m": 0, "price_6m": 0, "price_1y": 0,
        "features": ["✅ גישה מלאה", "✅ כל הפיצ'רים", "✅ 14 ימים בלבד", "❌ לא מתחדש"],
        "trial": True,
    },
    "basic": {
        "name": "Basic",
        "emoji": "🥉",
        "color": "#64748b",
        "price_1m": 15, "price_3m": 40, "price_6m": 70, "price_1y": 120,
        "features": ["✅ לקוח 1", "✅ 2 סשנים", "✅ הוספה & שליחה", "❌ Multi-client", "❌ AI Agent"],
    },
    "pro": {
        "name": "Pro",
        "emoji": "🥈",
        "color": "#3b82f6",
        "price_1m": 35, "price_3m": 90, "price_6m": 160, "price_1y": 280,
        "features": ["✅ 3 לקוחות", "✅ 10 סשנים", "✅ Multi-client", "✅ AI Agent", "✅ בוט"],
        "popular": True,
    },
    "business": {
        "name": "Business",
        "emoji": "🥇",
        "color": "#f59e0b",
        "price_1m": 70, "price_3m": 180, "price_6m": 320, "price_1y": 560,
        "features": ["✅ לקוחות ∞", "✅ סשנים ∞", "✅ כל הפיצ'רים", "✅ תמיכה מהירה", "✅ עדכונים"],
    },
    "ultimate": {
        "name": "Ultimate",
        "emoji": "💎",
        "color": "#a855f7",
        "price_1m": 120, "price_3m": 300, "price_6m": 550, "price_1y": 950,
        "features": ["✅ הכל מ-Business", "✅ תמיכה עדיפות", "✅ הגדרה אישית", "✅ API גישה", "✅ וויטלייבל"],
    },
}

DURATIONS = {
    "1m": ("חודש 1",   1),
    "3m": ("3 חודשים", 3),
    "6m": ("חצי שנה",  6),
    "1y": ("שנה",     12),
}

# ──────────────────────────────────────────────
def get_hwid() -> str:
    parts = [platform.node(), platform.machine(), platform.processor(), str(uuid.getnode())]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]

class LicenseResult:
    def __init__(self, valid=False, plan="", plan_info=None, expires_at="",
                 days_left=0, reason="", features=None,
                 max_clients=1, max_sessions=2, multi_client=False):
        self.valid=valid; self.plan=plan; self.plan_info=plan_info or {}
        self.expires_at=expires_at; self.days_left=days_left; self.reason=reason
        self.features=features or []; self.max_clients=max_clients
        self.max_sessions=max_sessions; self.multi_client=multi_client
    def has_feature(self, f): return "all" in self.features or f in self.features
    def __bool__(self): return self.valid

def _load_cache():
    try:
        if not CACHE_FILE.exists(): return None
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        cached_at = datetime.datetime.fromisoformat(data["cached_at"])
        if (datetime.datetime.utcnow()-cached_at).total_seconds() > CACHE_TTL_HOURS*3600: return None
        return LicenseResult(**{k:v for k,v in data.items() if k!="cached_at"})
    except: return None

def _save_cache(r):
    try:
        data = {k:getattr(r,k) for k in ["valid","plan","plan_info","expires_at","days_left","features","max_clients","max_sessions","multi_client"]}
        data["cached_at"] = datetime.datetime.utcnow().isoformat()
        CACHE_FILE.write_text(json.dumps(data), encoding="utf-8")
    except: pass

def check_license(key=None):
    if not key:
        key = LICENSE_FILE.read_text(encoding="utf-8").strip() if LICENSE_FILE.exists() else os.getenv("EXPERU_LICENSE_KEY")
    if not key: return LicenseResult(False, reason="no_key")
    if not REQUESTS_OK:
        c=_load_cache(); return c or LicenseResult(False, reason="no_requests")
    try:
        r = _req.post(f"{SERVER_URL}/verify", json={"license_key":key,"hwid":get_hwid()}, timeout=8)
        d = r.json()
    except:
        c=_load_cache(); return c or LicenseResult(False, reason="no_connection")
    res = LicenseResult(valid=d.get("valid",False),plan=d.get("plan",""),
        plan_info=d.get("plan_info",{}),expires_at=d.get("expires_at",""),
        days_left=d.get("days_left",0),reason=d.get("reason",""),
        features=d.get("features",[]),max_clients=d.get("max_clients",1),
        max_sessions=d.get("max_sessions",2),multi_client=d.get("multi_client",False))
    if res.valid: LICENSE_FILE.write_text(key,encoding="utf-8"); _save_cache(res)
    return res

# ── Workers ──
class LicenseCheckWorker(QThread):
    result = Signal(object)
    def __init__(self, key): super().__init__(); self.key=key
    def run(self): self.result.emit(check_license(self.key))

class _PaymentWorker(QThread):
    result = Signal(dict)
    def __init__(self, plan, duration, contact):
        super().__init__(); self.plan=plan; self.duration=duration; self.contact=contact
    def run(self):
        try:
            r=_req.post(f"{SERVER_URL}/create_payment",
                json={"plan":self.plan,"duration":self.duration,"contact":self.contact},timeout=15)
            self.result.emit(r.json())
        except Exception as e: self.result.emit({"error":str(e)})

class _TrialWorker(QThread):
    result = Signal(dict)
    def __init__(self, contact): super().__init__(); self.contact=contact
    def run(self):
        try:
            r=_req.post(f"{SERVER_URL}/trial",
                json={"contact":self.contact,"hwid":get_hwid()},timeout=10)
            self.result.emit(r.json())
        except Exception as e: self.result.emit({"error":str(e)})

# ──────────────────────────────────────────────
# DIALOG
# ──────────────────────────────────────────────
class LicenseDialog(QDialog):
    license_accepted = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔐 Experu TG — רישיון")
        self.setFixedSize(880, 640)
        self.setStyleSheet("""
            QDialog{background:#080b12;color:#e2e8f0;}
            QLabel{color:#e2e8f0;border:none;background:transparent;}
            QLineEdit{background:#111827;color:#e2e8f0;border:1px solid #1e2d45;
                border-radius:8px;padding:10px 14px;font-size:13px;}
            QLineEdit:focus{border:1px solid #3b82f6;}
            QPushButton{border-radius:8px;padding:10px 20px;font-size:13px;font-weight:700;}
        """)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        self._selected_plan="pro"; self._selected_duration="1m"
        self._build_ui()

    def _lbl(self, text, style=""):
        l=QLabel(text); l.setStyleSheet(style); return l

    def _build_ui(self):
        main=QHBoxLayout(self); main.setContentsMargins(0,0,0,0); main.setSpacing(0)

        # תוכן
        self._stack=QStackedWidget()
        self._stack.setStyleSheet("background:#080b12;")
        self._stack.addWidget(self._build_buy_page())
        self._stack.addWidget(self._build_activate_page())
        self._stack.addWidget(self._build_login_page())
        main.addWidget(self._stack, 1)

        # סרגל ניווט
        sidebar=QWidget(); sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("background:#0d1117;border-left:1px solid #1e2330;")
        sb=QVBoxLayout(sidebar); sb.setContentsMargins(16,24,16,24); sb.setSpacing(8)

        logo=self._lbl("⚡ Experu TG","color:#3b82f6;font-size:16px;font-weight:900;padding-bottom:16px;")
        logo.setAlignment(Qt.AlignCenter); sb.addWidget(logo)

        self._nav_btns={}
        for key,label in [("buy","🛒 קנה רישיון"),("activate","🔑 יש לי מפתח"),("login","👤 חשבון קיים")]:
            btn=QPushButton(label); btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton{background:transparent;color:#6b7280;text-align:center;
                    padding:10px 12px;border-radius:8px;font-size:12px;border:none;}
                QPushButton:checked{background:#1e2d45;color:#3b82f6;font-weight:700;}
                QPushButton:hover:!checked{background:#111827;color:#e2e8f0;}
            """)
            btn.clicked.connect(lambda _,k=key: self._switch_page(k))
            self._nav_btns[key]=btn; sb.addWidget(btn)

        sb.addStretch()
        sup=self._lbl("📞 @experu_support","color:#374151;font-size:10px;")
        sup.setAlignment(Qt.AlignCenter); sb.addWidget(sup)
        main.addWidget(sidebar)
        self._switch_page("buy")

    def _switch_page(self, key):
        for k,btn in self._nav_btns.items(): btn.setChecked(k==key)
        self._stack.setCurrentIndex({"buy":0,"activate":1,"login":2}[key])

    # ══ דף קנייה ══
    def _build_buy_page(self):
        page=QWidget(); layout=QVBoxLayout(page)
        layout.setContentsMargins(24,18,24,18); layout.setSpacing(10)

        layout.addWidget(self._lbl("🛒 בחר תוכנית","font-size:20px;font-weight:900;color:#f8fafc;"))
        layout.addWidget(self._lbl("שלם בקריפטו (USDT) — מפתח מגיע מיד לטלגרם / Gmail שלך","color:#6b7280;font-size:12px;"))

        # תקופה
        dur_row=QHBoxLayout()
        dur_row.addWidget(self._lbl("⏱ תקופה:","font-size:12px;color:#94a3b8;"))
        self._dur_btns={}
        for dk,(dl,_) in DURATIONS.items():
            btn=QPushButton(dl); btn.setCheckable(True); btn.setChecked(dk=="1m")
            btn.setFixedHeight(30)
            btn.setStyleSheet("""
                QPushButton{background:#111827;color:#94a3b8;border:1px solid #1e2330;
                    border-radius:6px;padding:4px 12px;font-size:11px;font-weight:600;}
                QPushButton:checked{background:#1e2d45;color:#3b82f6;border-color:#3b82f6;}
                QPushButton:hover:!checked{background:#1a2236;color:#e2e8f0;}
            """)
            btn.clicked.connect(lambda _,k=dk: self._select_duration(k))
            self._dur_btns[dk]=btn; dur_row.addWidget(btn)
        dur_row.addStretch(); layout.addLayout(dur_row)

        # כרטיסים
        plans_row=QHBoxLayout(); plans_row.setSpacing(7)
        self._plan_cards={}; self._plan_price_labels={}
        for pk,plan in PLANS.items():
            card,plbl=self._make_plan_card(pk,plan)
            self._plan_cards[pk]=card; self._plan_price_labels[pk]=plbl
            plans_row.addWidget(card)
        layout.addLayout(plans_row)

        # פרטי לקוח
        det=QFrame(); det.setStyleSheet("QFrame{background:#0d1117;border:1px solid #1e2330;border-radius:10px;}")
        dl=QVBoxLayout(det); dl.setContentsMargins(14,10,14,10); dl.setSpacing(7)
        dl.addWidget(self._lbl("📬 לאן לשלוח את מפתח הגישה?","font-size:12px;font-weight:700;color:#94a3b8;"))
        fr=QHBoxLayout()
        tc=QVBoxLayout(); tc.addWidget(self._lbl("📱 שם משתמש טלגרם","font-size:11px;color:#6b7280;"))
        self._tg_input=QLineEdit(); self._tg_input.setPlaceholderText("@username"); self._tg_input.setFixedHeight(36)
        tc.addWidget(self._tg_input)
        ol=self._lbl("  או  ","color:#374151;font-size:12px;"); ol.setAlignment(Qt.AlignCenter)
        gc=QVBoxLayout(); gc.addWidget(self._lbl("📧 כתובת Gmail","font-size:11px;color:#6b7280;"))
        self._gmail_input=QLineEdit(); self._gmail_input.setPlaceholderText("your@gmail.com"); self._gmail_input.setFixedHeight(36)
        gc.addWidget(self._gmail_input)
        fr.addLayout(tc); fr.addWidget(ol); fr.addLayout(gc)
        dl.addLayout(fr); layout.addWidget(det)

        # כפתורים
        br=QHBoxLayout()
        self._trial_btn=QPushButton("🎁 ניסיון חינם 14 יום")
        self._trial_btn.setFixedHeight(46)
        self._trial_btn.setStyleSheet("""
            QPushButton{background:#064e3b;color:#10b981;font-size:13px;font-weight:900;
                border-radius:10px;border:2px solid #10b981;}
            QPushButton:hover{background:#065f46;}
            QPushButton:disabled{background:#1e2330;color:#374151;border-color:#1e2330;}
        """)
        self._trial_btn.clicked.connect(self._do_trial)

        self._buy_btn=QPushButton("💎 קנה עכשיו — שלם בקריפטו")
        self._buy_btn.setFixedHeight(46)
        self._buy_btn.setStyleSheet("""
            QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #3b82f6,stop:1 #8b5cf6);
                color:white;font-size:14px;font-weight:900;border-radius:10px;}
            QPushButton:hover{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #2563eb,stop:1 #7c3aed);}
            QPushButton:disabled{background:#1e2330;color:#374151;}
        """)
        self._buy_btn.clicked.connect(self._do_buy)
        br.addWidget(self._trial_btn,1); br.addWidget(self._buy_btn,2)
        layout.addLayout(br)

        self._price_label=QLabel("")
        self._price_label.setStyleSheet("color:#3b82f6;font-size:12px;font-weight:700;")
        self._price_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._price_label)
        self._update_price_label()
        return page

    def _make_plan_card(self, pk, plan):
        card=QFrame(); card.setFixedHeight(172); card.setCursor(Qt.PointingHandCursor)
        self._style_plan_card(card, pk, pk=="pro")
        cl=QVBoxLayout(card); cl.setContentsMargins(10,10,10,10); cl.setSpacing(3)
        cl.addWidget(self._lbl(f"{plan['emoji']} {plan['name']}",f"color:{plan['color']};font-size:13px;font-weight:900;"))
        if plan.get("trial"): ptxt="חינם! 14 יום"
        else: ptxt=f"${plan['price_1m']}/חודש"
        plbl=QLabel(ptxt); plbl.setStyleSheet("color:#f8fafc;font-size:12px;font-weight:700;")
        cl.addWidget(plbl)
        for feat in plan["features"][:4]:
            f=QLabel(feat); f.setStyleSheet("font-size:10px;color:#94a3b8;"); cl.addWidget(f)
        if plan.get("popular"):
            cl.addWidget(self._lbl(f"⭐ הכי פופולרי",f"color:{plan['color']};font-size:9px;font-weight:700;"))
        card.mousePressEvent=lambda e,k=pk: self._select_plan(k)
        return card, plbl

    def _style_plan_card(self, card, pk, selected):
        color=PLANS[pk]["color"]
        if selected: card.setStyleSheet(f"QFrame{{background:#0d1117;border:2px solid {color};border-radius:10px;}}")
        else: card.setStyleSheet("QFrame{background:#0d1117;border:1px solid #1e2330;border-radius:10px;}")

    def _select_plan(self, pk):
        self._selected_plan=pk
        for k,c in self._plan_cards.items(): self._style_plan_card(c,k,k==pk)
        self._update_price_label()

    def _select_duration(self, dk):
        self._selected_duration=dk
        for k,btn in self._dur_btns.items(): btn.setChecked(k==dk)
        # עדכן מחירים בכרטיסים
        for pk,plan in PLANS.items():
            lbl=self._plan_price_labels.get(pk)
            if not lbl: continue
            if plan.get("trial"): lbl.setText("חינם! 14 יום")
            else:
                price=plan[f"price_{dk}"]
                lbl.setText(f"${price} / {DURATIONS[dk][0]}")
        self._update_price_label()

    def _update_price_label(self):
        plan=PLANS[self._selected_plan]
        if plan.get("trial"): self._price_label.setText("🎁 ניסיון חינם — גישה מלאה ל-14 ימים")
        else:
            price=plan[f"price_{self._selected_duration}"]
            self._price_label.setText(f"💰 {plan['name']} | {DURATIONS[self._selected_duration][0]} | ${price} USDT")

    def _do_buy(self):
        if PLANS[self._selected_plan].get("trial"): self._do_trial(); return
        tg=self._tg_input.text().strip().lstrip("@")
        gmail=self._gmail_input.text().strip()
        if not tg and not gmail:
            QMessageBox.warning(self,"⚠️","הכנס שם משתמש טלגרם או כתובת Gmail"); return
        self._buy_btn.setEnabled(False); self._buy_btn.setText("⏳ יוצר קישור...")
        self._pay_worker=_PaymentWorker(self._selected_plan, self._selected_duration, tg or gmail)
        self._pay_worker.result.connect(self._on_payment_created); self._pay_worker.start()

    def _on_payment_created(self, result):
        self._buy_btn.setEnabled(True); self._buy_btn.setText("💎 קנה עכשיו — שלם בקריפטו")
        if result.get("success"):
            webbrowser.open(result["payment_url"])
            plan=PLANS[self._selected_plan]
            price=plan[f"price_{self._selected_duration}"]
            QMessageBox.information(self,"💳 תשלום קריפטו",
                f"נפתח דף תשלום אישי!\n\n"
                f"📦 {plan['name']} | {DURATIONS[self._selected_duration][0]}\n"
                f"💰 סכום מדויק: ${price} USDT\n\n"
                f"⚠️ שלם בדיוק ${price} USDT — סכום שונה לא יאושר!\n\n"
                f"⚡ אחרי תשלום — מפתח יגיע לטלגרם/Gmail.\n"
                f"לחץ 'יש לי מפתח' בתפריט.")
            self._switch_page("activate")
        else:
            QMessageBox.critical(self,"❌ שגיאה",f"שגיאה ביצירת תשלום:\n{result.get('error','')}\n\nצור קשר: @experu_support")

    def _do_trial(self):
        tg=self._tg_input.text().strip().lstrip("@")
        gmail=self._gmail_input.text().strip()
        if not tg and not gmail:
            QMessageBox.warning(self,"⚠️","הכנס שם משתמש טלגרם או Gmail לקבלת מפתח הניסיון"); return
        self._trial_btn.setEnabled(False); self._trial_btn.setText("⏳ יוצר ניסיון...")
        self._trial_worker=_TrialWorker(tg or gmail)
        self._trial_worker.result.connect(self._on_trial_created); self._trial_worker.start()

    def _on_trial_created(self, result):
        self._trial_btn.setEnabled(True); self._trial_btn.setText("🎁 ניסיון חינם 14 יום")
        if result.get("success"):
            key=result.get("license_key","")
            QMessageBox.information(self,"🎁 ניסיון חינם!",
                f"מפתח הניסיון שלך:\n\n{key}\n\nגישה מלאה ל-14 ימים!\nהמפתח הוכנס אוטומטית — לחץ 'הפעל רישיון'.")
            self._key_input.setText(key); self._switch_page("activate")
        else:
            err=result.get("error","")
            if "already_used" in err: QMessageBox.warning(self,"⚠️","כבר השתמשת בניסיון חינם עם פרטים אלה.")
            else: QMessageBox.critical(self,"❌ שגיאה",f"לא ניתן ליצור ניסיון:\n{err}")

    # ══ דף הפעלת מפתח ══
    def _build_activate_page(self):
        page=QWidget(); layout=QVBoxLayout(page)
        layout.setContentsMargins(60,70,60,40); layout.setSpacing(16)

        t=self._lbl("🔑 הזן מפתח גישה","font-size:22px;font-weight:900;color:#f8fafc;")
        t.setAlignment(Qt.AlignCenter); layout.addWidget(t)
        s=self._lbl("הכנס את המפתח שקיבלת אחרי הרכישה / ניסיון","color:#6b7280;font-size:13px;")
        s.setAlignment(Qt.AlignCenter); layout.addWidget(s)
        layout.addSpacing(10)

        self._key_input=QLineEdit()
        self._key_input.setPlaceholderText("EXPERU-XXXXXX-XXXXXX-XXXXXX-XXXXXX")
        self._key_input.setAlignment(Qt.AlignCenter); self._key_input.setFixedHeight(50)
        self._key_input.setStyleSheet("""
            QLineEdit{background:#0d1117;color:#e2e8f0;border:2px solid #1e2d45;
                border-radius:10px;padding:10px 18px;font-size:14px;
                font-family:Consolas,monospace;letter-spacing:1px;}
            QLineEdit:focus{border-color:#3b82f6;}
        """)
        layout.addWidget(self._key_input)

        self._activate_btn=QPushButton("✅ הפעל רישיון"); self._activate_btn.setFixedHeight(48)
        self._activate_btn.setStyleSheet("""
            QPushButton{background:#10b981;color:white;font-size:15px;font-weight:900;border-radius:10px;}
            QPushButton:hover{background:#059669;}
            QPushButton:disabled{background:#1e2330;color:#374151;}
        """)
        self._activate_btn.clicked.connect(self._do_activate); layout.addWidget(self._activate_btn)

        self._activate_status=QLabel("")
        self._activate_status.setAlignment(Qt.AlignCenter)
        self._activate_status.setStyleSheet("font-size:12px;"); self._activate_status.setWordWrap(True)
        layout.addWidget(self._activate_status); layout.addStretch()

        h=self._lbl("עדיין לא קנית? לחץ 'קנה רישיון' • ניסיון חינם זמין!","color:#374151;font-size:11px;")
        h.setAlignment(Qt.AlignCenter); layout.addWidget(h)
        return page

    def _do_activate(self):
        key=self._key_input.text().strip()
        if not key:
            self._activate_status.setText("⚠️ הכנס מפתח")
            self._activate_status.setStyleSheet("color:#f59e0b;font-size:12px;"); return
        self._activate_btn.setEnabled(False); self._activate_btn.setText("⏳ בודק...")
        self._activate_status.setText("")
        self._worker=LicenseCheckWorker(key)
        self._worker.result.connect(self._on_activate_result); self._worker.start()

    def _on_activate_result(self, result):
        self._activate_btn.setEnabled(True); self._activate_btn.setText("✅ הפעל רישיון")
        if result.valid:
            pname=PLANS.get(result.plan,{}).get("name",result.plan)
            self._activate_status.setText(f"🎉 רישיון תקף! {pname} | עוד {result.days_left} ימים")
            self._activate_status.setStyleSheet("color:#10b981;font-size:13px;font-weight:700;")
            QTimer.singleShot(1200, lambda: self.license_accepted.emit(result))
        else:
            msgs={"key_not_found":"❌ מפתח לא נמצא","key_revoked":"🚫 מפתח בוטל",
                "expired":"⏰ רישיון פג — חדש מנוי","trial_expired":"⏰ ניסיון הסתיים — רכוש מנוי!",
                "hwid_mismatch":"💻 נעול למחשב אחר\nצור קשר: @experu_support",
                "no_connection":"🌐 אין חיבור לשרת"}
            self._activate_status.setText(msgs.get(result.reason,f"❌ {result.reason}"))
            self._activate_status.setStyleSheet("color:#ef4444;font-size:12px;")

    # ══ דף חשבון קיים ══
    def _build_login_page(self):
        page=QWidget(); layout=QVBoxLayout(page)
        layout.setContentsMargins(60,50,60,40); layout.setSpacing(14)

        t=self._lbl("👤 כניסה — חשבון קיים","font-size:22px;font-weight:900;color:#f8fafc;")
        t.setAlignment(Qt.AlignCenter); layout.addWidget(t)
        s=self._lbl("החלפת מחשב? הכנס פרטים ומפתח גישה","color:#6b7280;font-size:12px;")
        s.setAlignment(Qt.AlignCenter); layout.addWidget(s)
        layout.addSpacing(10)

        layout.addWidget(self._lbl("📬 שם משתמש טלגרם או Gmail","font-size:12px;color:#94a3b8;"))
        self._login_id_input=QLineEdit()
        self._login_id_input.setPlaceholderText("@username  או  email@gmail.com")
        self._login_id_input.setFixedHeight(44); layout.addWidget(self._login_id_input)

        layout.addWidget(self._lbl("🔐 מפתח גישה (חובה)","font-size:12px;color:#94a3b8;"))
        self._login_key_input=QLineEdit()
        self._login_key_input.setPlaceholderText("EXPERU-XXXXXX-XXXXXX-XXXXXX-XXXXXX")
        self._login_key_input.setFixedHeight(44)
        self._login_key_input.setStyleSheet("""
            QLineEdit{background:#0d1117;color:#e2e8f0;border:1px solid #1e2d45;
                border-radius:8px;padding:10px 14px;font-family:Consolas,monospace;font-size:13px;}
            QLineEdit:focus{border-color:#f59e0b;}
        """)
        layout.addWidget(self._login_key_input)
        layout.addWidget(self._lbl("💡 המפתח נשלח אליך בטלגרם/Gmail בזמן הרכישה","color:#374151;font-size:10px;"))

        self._login_btn=QPushButton("🔓 כנס למערכת"); self._login_btn.setFixedHeight(48)
        self._login_btn.setStyleSheet("""
            QPushButton{background:#f59e0b;color:#080b12;font-size:15px;font-weight:900;border-radius:10px;}
            QPushButton:hover{background:#d97706;}
            QPushButton:disabled{background:#1e2330;color:#374151;}
        """)
        self._login_btn.clicked.connect(self._do_login); layout.addWidget(self._login_btn)

        self._login_status=QLabel(""); self._login_status.setAlignment(Qt.AlignCenter)
        self._login_status.setStyleSheet("font-size:12px;"); self._login_status.setWordWrap(True)
        layout.addWidget(self._login_status); layout.addStretch()

        n=self._lbl("🔒 המפתח נעול למחשב הראשון שהפעיל אותו.\nלהחלפת מחשב: @experu_support","color:#374151;font-size:10px;")
        n.setAlignment(Qt.AlignCenter); n.setWordWrap(True); layout.addWidget(n)
        return page

    def _do_login(self):
        identifier=self._login_id_input.text().strip()
        key=self._login_key_input.text().strip()
        if not identifier:
            self._login_status.setText("⚠️ הכנס שם משתמש טלגרם או Gmail")
            self._login_status.setStyleSheet("color:#f59e0b;font-size:12px;"); return
        if not key:
            self._login_status.setText("⚠️ המפתח חובה — בדוק בטלגרם/Gmail שלך")
            self._login_status.setStyleSheet("color:#f59e0b;font-size:12px;"); return
        self._login_btn.setEnabled(False); self._login_btn.setText("⏳ מאמת...")
        self._login_status.setText("")
        self._login_worker=LicenseCheckWorker(key)
        self._login_worker.result.connect(self._on_login_result); self._login_worker.start()

    def _on_login_result(self, result):
        self._login_btn.setEnabled(True); self._login_btn.setText("🔓 כנס למערכת")
        if result.valid:
            self._login_status.setText(f"✅ ברוך הבא! {result.plan} | עוד {result.days_left} ימים")
            self._login_status.setStyleSheet("color:#10b981;font-size:13px;font-weight:700;")
            QTimer.singleShot(1000, lambda: self.license_accepted.emit(result))
        else:
            msgs={"key_not_found":"❌ מפתח לא נמצא","key_revoked":"🚫 מפתח בוטל",
                "expired":"⏰ רישיון פג","hwid_mismatch":"💻 נעול למחשב אחר — @experu_support",
                "no_connection":"🌐 אין חיבור לשרת"}
            self._login_status.setText(msgs.get(result.reason,f"❌ {result.reason}"))
            self._login_status.setStyleSheet("color:#ef4444;font-size:12px;")


# ──────────────────────────────────────────────
def check_and_show_license(app: QApplication) -> Optional[LicenseResult]:
    lic=check_license()
    if lic.valid: return lic
    holder=[None]
    dlg=LicenseDialog()
    def on_acc(r): holder[0]=r; dlg.accept()
    dlg.license_accepted.connect(on_acc); dlg.exec()
    return holder[0]
