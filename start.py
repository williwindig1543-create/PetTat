"""
start.py – PatTat  ·  Multiplayer Edition  ·  v6
=================================================
Neu in v6:
  - Umbenennung: BioBreeder → PatTat
  - Zücht-Bug behoben (gr_wert in genetics.py)
  - Ränge 1–1000 (Wild max 100, Zucht bis 1000)
  - Bot mit echtem Coin-Haushalt (kauft/verkauft realistisch)
  - Chat-System (Nachrichten, Freunde, Blockieren)
  - Persistenter Secret-Key (übersteht Neustarts auf Uberspace)

Sicherheits-Features:
  - Rate-Limiting (pro IP + pro Endpunkt, Sliding-Window)
  - Brute-Force-Schutz (Login-Sperre: 5 Versuche / 10 Min)
  - Sichere Session-Cookies (HttpOnly, SameSite=Lax, 8h-Timeout)
  - Input-Sanitisierung & Validierung auf allen Eingaben
  - DSGVO Art.17: Recht auf Löschung (/api/account/loeschen)
"""

from flask import Flask, render_template, jsonify, request, session, g
from werkzeug.security import generate_password_hash, check_password_hash
import json, os, random, tempfile, threading, uuid, secrets, time, re, math
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import genetics

# ================================================================
#  KONFIGURATION
# ================================================================

app = Flask(__name__)

DATA     = os.path.join(os.path.dirname(__file__), "data")
BOT_NAME = "MarktBot"

# ── Persistenter Secret Key (übersteht Neustarts) ────────────────
def _lade_oder_erzeuge_secret() -> str:
    """Liest den Secret Key aus einer Datei oder erzeugt ihn einmalig."""
    env_key = os.environ.get("PATTAT_SECRET") or os.environ.get("BIOBREEDER_SECRET")
    if env_key:
        return env_key
    os.makedirs(DATA, exist_ok=True)
    keyfile = os.path.join(DATA, ".secret_key")
    if os.path.exists(keyfile):
        with open(keyfile, "r") as f:
            key = f.read().strip()
        if len(key) >= 32:
            return key
    key = secrets.token_hex(32)
    with open(keyfile, "w") as f:
        f.write(key)
    return key

app.config.update(
    SECRET_KEY               = _lade_oder_erzeuge_secret(),
    SESSION_COOKIE_HTTPONLY  = True,
    SESSION_COOKIE_SAMESITE  = "Lax",
    SESSION_COOKIE_SECURE    = False,        # True wenn HTTPS aktiv
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8),
    MAX_CONTENT_LENGTH       = 64 * 1024,
)

_lock          = threading.Lock()
ONLINE_TIMEOUT = 30
MAX_NACHRICHTEN = 10000  # max. gespeicherte Chat-Nachrichten

# ── Bot-Budget ────────────────────────────────────────────────────
BOT_START_COINS   = 3000    # Startkapital
BOT_START_BLAETTER = 50
BOT_MAX_COINS     = 50000   # Deckel damit Bot nicht unendlich reich wird

# ================================================================
#  SICHERHEITS-SYSTEM
# ================================================================

class _RateLimiter:
    def __init__(self):
        self._hits = defaultdict(list)
        self._lock = threading.Lock()

    def allow(self, key: str, max_calls: int, window: int) -> bool:
        now = time.monotonic()
        with self._lock:
            lst = [t for t in self._hits[key] if now - t < window]
            self._hits[key] = lst
            if len(lst) >= max_calls:
                return False
            lst.append(now)
            return True

    def cleanup(self):
        now = time.monotonic()
        with self._lock:
            stale = [k for k, v in self._hits.items()
                     if not v or (now - max(v)) > 3600]
            for k in stale:
                del self._hits[k]


class _LoginProtection:
    MAX_ATTEMPTS    = 5
    LOCKOUT_SECONDS = 600

    def __init__(self):
        self._attempts = defaultdict(list)
        self._lock     = threading.Lock()

    def record_fail(self, name: str):
        with self._lock:
            self._attempts[name].append(time.monotonic())

    def is_locked(self, name: str) -> bool:
        now = time.monotonic()
        with self._lock:
            lst = [t for t in self._attempts.get(name, [])
                   if now - t < self.LOCKOUT_SECONDS]
            self._attempts[name] = lst
            return len(lst) >= self.MAX_ATTEMPTS

    def remaining(self, name: str) -> int:
        now = time.monotonic()
        with self._lock:
            lst = self._attempts.get(name, [])
            if not lst: return 0
            return max(0, int(self.LOCKOUT_SECONDS - (now - min(lst))))

    def reset(self, name: str):
        with self._lock:
            self._attempts.pop(name, None)


_rate       = _RateLimiter()
_bruteforce = _LoginProtection()


def sanitize(s, max_len=200, allow_spaces=True):
    if not isinstance(s, str): return ""
    s = s.strip()[:max_len]
    s = s.replace("<", "").replace(">", "").replace(chr(34), "").replace("'", "")
    if not allow_spaces:
        s = s.replace(" ", "")
    return s

def validate_name(name):
    if len(name) < 3:  return False, "Name mind. 3 Zeichen"
    if len(name) > 30: return False, "Name max. 30 Zeichen"
    if not re.match(r"^[A-Za-z0-9_\-äöüÄÖÜß ]+$", name):
        return False, "Name enthält ungültige Zeichen"
    return True, ""

def validate_password(pw):
    if len(pw) < 8:   return False, "Passwort mind. 8 Zeichen"
    if len(pw) > 128: return False, "Passwort zu lang"
    if not re.search(r"\d", pw): return False, "Passwort muss mind. eine Zahl enthalten"
    return True, ""

def anon_ip():
    raw = request.remote_addr or "0.0.0.0"
    parts = raw.split(".")
    if len(parts) == 4: parts[-1] = "0"
    return ".".join(parts)


@app.before_request
def security_checks():
    session.permanent = True
    if not _rate.allow(f"global:{anon_ip()}", 120, 60):
        return jsonify({"ok": False, "fehler": "Zu viele Anfragen – bitte warte kurz."}), 429
    if "spieler" in session:
        ua_hash = hash(request.user_agent.string or "")
        if "ua_hash" not in session:
            session["ua_hash"] = ua_hash
        elif session.get("ua_hash") != ua_hash:
            session.clear()
            return jsonify({"ok": False, "fehler": "Session ungültig – bitte neu einloggen"}), 401
    if random.random() < 0.02:
        _rate.cleanup()


def auth_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "spieler" not in session:
            return jsonify({"ok": False, "fehler": "Nicht eingeloggt"}), 401
        sp     = session["spieler"]
        nutzer = lade("users")
        if sp not in nutzer:
            session.clear()
            return jsonify({"ok": False, "fehler": "Session abgelaufen – bitte neu einloggen"}), 401
        g.sp     = sp
        g.nutzer = nutzer
        return fn(*args, **kwargs)
    return wrapper


@app.errorhandler(Exception)
def handle_exception(e):
    import traceback; traceback.print_exc()
    return jsonify({"ok": False, "fehler": "Interner Serverfehler"}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({"ok": False, "fehler": "Anfrage zu groß"}), 413


# ================================================================
#  DATEI-HELFER
# ================================================================

def lade(name):
    with open(os.path.join(DATA, f"{name}.json"), "r", encoding="utf-8") as f:
        return json.load(f)

def speichere(name, inhalt):
    ziel = os.path.join(DATA, f"{name}.json")
    fd, tmp = tempfile.mkstemp(dir=DATA, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(inhalt, f, indent=2, ensure_ascii=False)
        os.replace(tmp, ziel)
    except Exception:
        try: os.unlink(tmp)
        except: pass
        raise

def naechste_nr(tiere):
    nrs = [t.get("meta", {}).get("zucht_nummer") or 0 for t in tiere]
    return max((n for n in nrs if isinstance(n, int)), default=0) + 1

def jetzt_iso():
    return datetime.now(timezone.utc).isoformat()

def sekunden_seit(iso_str):
    if not iso_str: return 9999
    try:
        t = datetime.fromisoformat(iso_str)
        if t.tzinfo is None: t = t.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - t).total_seconds()
    except: return 9999

def _pub(u):
    """Gibt nur öffentliche Felder zurück – niemals Passwort."""
    return {
        "name":            u["name"],
        "coins":           u["coins"],
        "blaetter":        u["blaetter"],
        "inventar":        u["inventar"],
        "entdeckte_arten": u.get("entdeckte_arten", []),
        "zucht_zaehler":   u.get("zucht_zaehler", 0),
        "einstellungen":   u.get("einstellungen", {}),
        "freunde":         u.get("freunde", []),
        "blockiert":       u.get("blockiert", []),
    }


# ================================================================
#  BOT-LOGIK  (realistischer Coin-Haushalt)
# ================================================================

def bot_starte():
    """Initialisiert den MarktBot beim ersten Start."""
    with _lock:
        nutzer = lade("users"); tiere = lade("animals")
        if BOT_NAME not in nutzer:
            nutzer[BOT_NAME] = {
                "name": BOT_NAME, "passwort": "BOT",
                "coins": BOT_START_COINS, "blaetter": BOT_START_BLAETTER,
                "inventar": [],
                "entdeckte_arten": list(genetics.SPECIES.keys()),
                "zucht_zaehler": 0, "ist_bot": True,
                "letzte_aktivitaet": jetzt_iso(),
                "freunde": [], "blockiert": [],
            }
        bot = nutzer[BOT_NAME]
        # Starte-Inventar: 6 Tiere (Rang 5–40), kostenlos weil Bot
        if len(bot["inventar"]) < 6:
            for art in list(genetics.SPECIES.keys()) * 2:
                t = genetics.generiere_wildtier(art, ziel_rang=random.randint(5, 40))
                t["besitzer"] = BOT_NAME
                t["meta"]["zucht_nummer"] = naechste_nr(tiere)
                tiere.append(t)
                bot["inventar"].append(t["id"])
            nutzer[BOT_NAME] = bot
            speichere("animals", tiere)
            speichere("users", nutzer)


def bot_tick():
    """
    Bot-KI: kauft günstige Tiere von Spielern, verkauft eigene.
    Geld fließt realistisch: Bot gibt Coins aus und bekommt sie zurück.
    """
    with _lock:
        nutzer = lade("users"); tiere = lade("animals")
        bot = nutzer.get(BOT_NAME)
        if not bot: return

        changed = False
        bot_listings = [t for t in tiere
                        if t.get("besitzer") == "Markt" and t.get("markt_von") == BOT_NAME]

        # ── Bot stellt eigene Tiere ein ──────────────────────────
        inv = list(bot.get("inventar", []))
        while len(bot_listings) < 4 and inv:
            tid  = random.choice(inv)
            tier = next((t for t in tiere if t["id"] == tid), None)
            if tier and tier.get("besitzer") == BOT_NAME:
                preis = genetics.bot_preis_fuer(tier)
                tier["besitzer"]    = "Markt"
                tier["markt_preis"] = preis
                tier["markt_von"]   = BOT_NAME
                bot["inventar"]     = [i for i in bot["inventar"] if i != tid]
                bot_listings.append(tier)
                changed = True
            inv = [i for i in inv if i != tid]

        # ── Bot kauft günstige Spieler-Tiere ────────────────────
        # Nur kaufen wenn Bot es sich leisten kann
        for t in list(tiere):
            if (t.get("besitzer") != "Markt"
                    or t.get("markt_von") in (BOT_NAME, None)
                    or not t.get("markt_preis")):
                continue
            fair_preis = genetics.bot_preis_fuer(t)
            angebots_preis = t.get("markt_preis", 9999)
            # Bot kauft nur wenn Preis gut (< 70 % des fairen Wertes)
            if (angebots_preis < fair_preis * 0.70
                    and random.random() < 0.5
                    and bot.get("coins", 0) >= angebots_preis):
                verk = t.get("markt_von")
                # Coins fließen: Bot zahlt, Verkäufer bekommt Geld
                bot["coins"] = min(BOT_MAX_COINS, bot.get("coins", 0) - angebots_preis)
                if verk and verk in nutzer and not nutzer[verk].get("ist_bot"):
                    nutzer[verk]["coins"] = nutzer[verk].get("coins", 0) + angebots_preis
                    _push_notif(nutzer, verk,
                                f"🤖 {BOT_NAME} hat dein Tier für {angebots_preis} 💰 gekauft!")
                t["besitzer"]    = BOT_NAME
                t["markt_preis"] = None
                t["markt_von"]   = None
                bot["inventar"].append(t["id"])
                changed = True

        # ── Bot generiert neue Tiere wenn Inventar leer ──────────
        if len(bot["inventar"]) < 3:
            for _ in range(3):
                t = genetics.generiere_wildtier(ziel_rang=random.randint(5, 55))
                t["besitzer"] = BOT_NAME
                t["meta"]["zucht_nummer"] = naechste_nr(tiere)
                tiere.append(t)
                bot["inventar"].append(t["id"])
                changed = True

        if changed:
            nutzer[BOT_NAME] = bot
            speichere("animals", tiere)
            speichere("users", nutzer)


# ================================================================
#  BENACHRICHTIGUNGEN
# ================================================================

def _push_notif(nutzer, name, nachricht):
    if name not in nutzer or nutzer[name].get("ist_bot"): return
    nutzer[name].setdefault("benachrichtigungen", []).append({
        "id": str(uuid.uuid4())[:8], "text": str(nachricht)[:500],
        "zeit": jetzt_iso(), "gelesen": False,
    })
    nutzer[name]["benachrichtigungen"] = nutzer[name]["benachrichtigungen"][-50:]


# ================================================================
#  AUTH-ROUTES
# ================================================================

@app.route("/")
def index(): return render_template("index.html")

@app.route("/api/ich")
def ich():
    if "spieler" not in session:
        return jsonify({"ok": False, "eingeloggt": False})
    nutzer = lade("users")
    user   = nutzer.get(session["spieler"])
    if not user: session.clear(); return jsonify({"ok": False, "eingeloggt": False})
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return jsonify({"ok": True, "eingeloggt": True, "user": _pub(user),
                    "csrf_token": session["csrf_token"]})

@app.route("/api/login", methods=["POST"])
def login():
    if not _rate.allow(f"login:{anon_ip()}", 10, 60):
        return jsonify({"ok": False, "fehler": "Zu viele Login-Versuche. 1 Minute warten."}), 429
    d    = request.get_json() or {}
    name = sanitize(d.get("name") or "", max_len=30, allow_spaces=False)
    pw   = (d.get("passwort") or "")[:128]
    if not name or not pw:
        return jsonify({"ok": False, "fehler": "Name und Passwort erforderlich"}), 400
    if _bruteforce.is_locked(name):
        sek = _bruteforce.remaining(name)
        return jsonify({"ok": False, "fehler": f"Konto gesperrt, noch {sek // 60 + 1} Min."}), 429
    nutzer = lade("users"); user = nutzer.get(name)
    if not user:
        _bruteforce.record_fail(name)
        return jsonify({"ok": False, "fehler": "Konto nicht gefunden"}), 404
    if user.get("ist_bot"):
        return jsonify({"ok": False, "fehler": "Login nicht möglich"}), 403
    if not check_password_hash(user["passwort"], pw):
        _bruteforce.record_fail(name)
        return jsonify({"ok": False, "fehler": "Falsches Passwort"}), 401
    _bruteforce.reset(name)
    session.clear()
    session["spieler"]    = name
    session["ua_hash"]    = hash(request.user_agent.string or "")
    session["csrf_token"] = secrets.token_hex(16)
    return jsonify({"ok": True, "user": _pub(user), "csrf_token": session["csrf_token"]})

@app.route("/api/register", methods=["POST"])
def register():
    if not _rate.allow(f"register:{anon_ip()}", 3, 3600):
        return jsonify({"ok": False, "fehler": "Zu viele Registrierungen. Später versuchen."}), 429
    d    = request.get_json() or {}
    name = sanitize(d.get("name") or "", max_len=30, allow_spaces=True)
    pw   = (d.get("passwort") or "")[:128]
    ok_n, err_n = validate_name(name)
    if not ok_n: return jsonify({"ok": False, "fehler": err_n}), 400
    ok_p, err_p = validate_password(pw)
    if not ok_p: return jsonify({"ok": False, "fehler": err_p}), 400
    if name == BOT_NAME: return jsonify({"ok": False, "fehler": "Name nicht erlaubt"}), 400
    nutzer = lade("users")
    if name in nutzer: return jsonify({"ok": False, "fehler": "Name bereits vergeben"}), 409
    nutzer[name] = {
        "name": name, "passwort": generate_password_hash(pw, method="scrypt"),
        "coins": 300, "blaetter": 6, "inventar": [],
        "entdeckte_arten": [], "zucht_zaehler": 0,
        "ist_bot": False, "letzte_aktivitaet": jetzt_iso(),
        "benachrichtigungen": [], "einstellungen": {},
        "registriert_am": jetzt_iso(),
        "freunde": [], "blockiert": [],
    }
    speichere("users", nutzer)
    session.clear()
    session["spieler"]    = name
    session["ua_hash"]    = hash(request.user_agent.string or "")
    session["csrf_token"] = secrets.token_hex(16)
    return jsonify({"ok": True, "user": _pub(nutzer[name]), "csrf_token": session["csrf_token"]})

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear(); return jsonify({"ok": True})


# ================================================================
#  DSGVO – RECHT AUF LÖSCHUNG (Art. 17 DSGVO)
# ================================================================

@app.route("/api/account/loeschen", methods=["POST"])
@auth_required
def account_loeschen():
    d  = request.get_json() or {}
    pw = (d.get("passwort") or "")[:128]
    sp = g.sp
    with _lock:
        nutzer = lade("users"); user = nutzer.get(sp)
        if not user: return jsonify({"ok": False, "fehler": "Nicht gefunden"}), 404
        if not check_password_hash(user["passwort"], pw):
            return jsonify({"ok": False, "fehler": "Falsches Passwort"}), 401
        tiere = lade("animals")
        for t in tiere:
            if t.get("markt_von") == sp or t.get("besitzer") == sp:
                t["besitzer"]    = BOT_NAME
                t["markt_preis"] = None; t["markt_von"] = None
        trades = lade("trades")
        for tr in trades:
            if tr.get("von") == sp or tr.get("an") == sp:
                tr["status"] = "geloescht"
        del nutzer[sp]
        speichere("users", nutzer); speichere("animals", tiere); speichere("trades", trades)
    session.clear()
    return jsonify({"ok": True, "nachricht": "Account vollständig gelöscht."})


# ================================================================
#  ONLINE-STATUS
# ================================================================

@app.route("/api/heartbeat", methods=["POST"])
@auth_required
def heartbeat():
    sp = g.sp
    with _lock:
        nutzer = lade("users")
        if sp in nutzer:
            nutzer[sp]["letzte_aktivitaet"] = jetzt_iso()
            speichere("users", nutzer)
    return jsonify({"ok": True})

@app.route("/api/spieler/online")
@auth_required
def spieler_online():
    nutzer = g.nutzer
    online = [{"name": n} for n, u in nutzer.items()
              if sekunden_seit(u.get("letzte_aktivitaet")) < ONLINE_TIMEOUT
              and not u.get("ist_bot") and not u.get("geloescht") and n != g.sp]
    return jsonify({"ok": True, "online": online})


# ================================================================
#  BENACHRICHTIGUNGEN
# ================================================================

@app.route("/api/benachrichtigungen")
@auth_required
def benachrichtigungen():
    sp = g.sp
    with _lock:
        nutzer = lade("users"); user = nutzer.get(sp)
        if not user: return jsonify({"ok": True, "benachrichtigungen": []})
        notifs    = user.get("benachrichtigungen", [])
        ungelesen = [n for n in notifs if not n.get("gelesen")]
        for n in notifs: n["gelesen"] = True
        nutzer[sp]["benachrichtigungen"] = notifs
        speichere("users", nutzer)
    return jsonify({"ok": True, "benachrichtigungen": ungelesen})


# ================================================================
#  KERN-SPIEL-API
# ================================================================

@app.route("/api/tiere")
@auth_required
def get_tiere(): return jsonify({"ok": True, "tiere": lade("animals")})

@app.route("/api/tier/<tid>")
@auth_required
def get_tier(tid):
    tid = sanitize(tid, max_len=20)
    t = next((t for t in lade("animals") if t["id"] == tid), None)
    if not t: return jsonify({"ok": False, "fehler": "Nicht gefunden"}), 404
    return jsonify({"ok": True, "tier": t})

@app.route("/api/zuechten", methods=["POST"])
@auth_required
def zuechten():
    d  = request.get_json() or {}
    sp = g.sp
    with _lock:
        tiere = lade("animals"); nutzer = lade("users"); user = nutzer.get(sp)
        if not user: session.clear(); return jsonify({"ok": False, "fehler": "Session abgelaufen"}), 401
        v_id = sanitize(d.get("vater_id")  or "", max_len=20)
        m_id = sanitize(d.get("mutter_id") or "", max_len=20)
        p1 = next((t for t in tiere if t["id"] == v_id), None)
        p2 = next((t for t in tiere if t["id"] == m_id), None)
        if not p1 or not p2:
            return jsonify({"ok": False, "fehler": "Elterntier nicht gefunden"}), 404
        if p1.get("besitzer") != sp:
            return jsonify({"ok": False, "fehler": "Tier gehört dir nicht"}), 403
        if p2.get("besitzer") != sp:
            return jsonify({"ok": False, "fehler": "Tier gehört dir nicht"}), 403
        if p1["id"] == p2["id"]:
            return jsonify({"ok": False, "fehler": "Gleiche Eltern"}), 400
        r1 = p1.get("genetik", {}).get("rang", 5)
        r2 = p2.get("genetik", {}).get("rang", 5)
        kosten = genetics.zucht_kosten(r1, r2)
        if user["blaetter"] < kosten:
            return jsonify({"ok": False,
                            "fehler": f"Nicht genug Blätter ({kosten} benötigt, du hast {user['blaetter']})"}), 400
        try:
            baby = genetics.breed(p1, p2)
        except Exception as e:
            return jsonify({"ok": False, "fehler": f"Züchtungsfehler: {str(e)}"}), 500
        baby["besitzer"] = sp
        baby["meta"]["zucht_nummer"] = naechste_nr(tiere)
        user.setdefault("entdeckte_arten", [])
        neue_art = baby["art"] not in user["entdeckte_arten"]
        if neue_art: user["entdeckte_arten"].append(baby["art"])
        user["blaetter"]      -= kosten
        user["zucht_zaehler"] += 1
        user["coins"]         += 10
        user["inventar"].append(baby["id"])
        tiere.append(baby)
        nutzer[sp] = user
        speichere("animals", tiere); speichere("users", nutzer)
    return jsonify({"ok": True, "baby": baby, "neue_art": neue_art, "kosten": kosten,
                    "user": {"coins": user["coins"], "blaetter": user["blaetter"]}})

@app.route("/api/blatt_sammeln", methods=["POST"])
@auth_required
def blatt():
    sp = g.sp
    if not _rate.allow(f"blatt:{sp}", 30, 60):
        return jsonify({"ok": False, "fehler": "Zu schnell! Warte kurz."}), 429
    with _lock:
        nutzer = lade("users"); user = nutzer.get(sp)
        if not user: return jsonify({"ok": False, "fehler": "Fehler"}), 500
        user["blaetter"] += 1; user["coins"] += 2
        nutzer[sp] = user; speichere("users", nutzer)
    return jsonify({"ok": True, "blaetter": user["blaetter"], "coins": user["coins"]})

@app.route("/api/zaehmen", methods=["POST"])
@auth_required
def zaehmen():
    d  = request.get_json() or {}
    sp = g.sp
    with _lock:
        tiere = lade("animals"); nutzer = lade("users"); user = nutzer.get(sp)
        if not user: return jsonify({"ok": False, "fehler": "Fehler"}), 500
        if user["blaetter"] < 3: return jsonify({"ok": False, "fehler": "3 Blätter benötigt"}), 400
        tid  = sanitize(d.get("tier_id") or "", max_len=20)
        tier = next((t for t in tiere if t["id"] == tid), None)
        if not tier: return jsonify({"ok": False, "fehler": "Tier nicht gefunden"}), 404
        if tier.get("besitzer"): return jsonify({"ok": False, "fehler": "Tier bereits gezähmt"}), 400
        tier["besitzer"] = sp; user["blaetter"] -= 3; user["inventar"].append(tier["id"])
        user.setdefault("entdeckte_arten", [])
        if tier["art"] not in user["entdeckte_arten"]: user["entdeckte_arten"].append(tier["art"])
        nutzer[sp] = user; speichere("animals", tiere); speichere("users", nutzer)
    return jsonify({"ok": True, "tier": tier,
                    "user": {"coins": user["coins"], "blaetter": user["blaetter"]}})

@app.route("/api/wildtier", methods=["POST"])
@auth_required
def wildtier():
    d = request.get_json() or {}
    rang = d.get("rang")
    if rang is not None:
        rang = max(1, min(genetics.MAX_WILD_RANG, int(rang)))
    t = genetics.generiere_wildtier(d.get("art"), rang)
    with _lock:
        tiere = lade("animals"); t["meta"]["zucht_nummer"] = naechste_nr(tiere)
        tiere.append(t); speichere("animals", tiere)
    return jsonify({"ok": True, "tier": t})

@app.route("/api/user/ich")
@auth_required
def user_ich():
    return jsonify({"ok": True, "user": _pub(g.nutzer[g.sp])})


# ================================================================
#  MARKTPLATZ
# ================================================================

@app.route("/api/markt")
@auth_required
def markt():
    bot_tick()
    return jsonify({"ok": True, "angebote": [
        t for t in lade("animals") if t.get("besitzer") == "Markt" and t.get("markt_preis")
    ]})

@app.route("/api/markt/einstellen", methods=["POST"])
@auth_required
def einstellen():
    d = request.get_json() or {}; sp = g.sp
    with _lock:
        tiere = lade("animals"); nutzer = lade("users"); user = nutzer.get(sp)
        if not user: return jsonify({"ok": False, "fehler": "Fehler"}), 500
        tid  = sanitize(d.get("tier_id") or "", max_len=20)
        tier = next((t for t in tiere if t["id"] == tid), None)
        if not tier or tier.get("besitzer") != sp:
            return jsonify({"ok": False, "fehler": "Kein Zugriff"}), 403
        preis = max(1, min(9999999, int(d.get("preis", tier.get("basis_preis", 50)) or 50)))
        tier["besitzer"]    = "Markt"
        tier["markt_preis"] = preis
        tier["markt_von"]   = sp
        user["inventar"] = [i for i in user["inventar"] if i != tier["id"]]
        nutzer[sp] = user; speichere("animals", tiere); speichere("users", nutzer)
    return jsonify({"ok": True, "tier": tier})

@app.route("/api/markt/kaufen", methods=["POST"])
@auth_required
def kaufen():
    d = request.get_json() or {}; sp = g.sp
    with _lock:
        tiere = lade("animals"); nutzer = lade("users"); user = nutzer.get(sp)
        if not user: return jsonify({"ok": False, "fehler": "Fehler"}), 500
        tid  = sanitize(d.get("tier_id") or "", max_len=20)
        tier = next((t for t in tiere if t["id"] == tid and t.get("besitzer") == "Markt"), None)
        if not tier: return jsonify({"ok": False, "fehler": "Nicht verfügbar"}), 404
        preis = tier.get("markt_preis", 50)
        if user["coins"] < preis:
            return jsonify({"ok": False, "fehler": f"Nicht genug Coins ({preis} benötigt)"}), 400
        user["coins"] -= preis
        user["inventar"].append(tier["id"])
        verk = tier.get("markt_von")
        if verk and verk in nutzer:
            # Coins gehen an Verkäufer (Spieler oder Bot)
            if nutzer[verk].get("ist_bot"):
                nutzer[verk]["coins"] = min(BOT_MAX_COINS,
                                            nutzer[verk].get("coins", 0) + preis)
            else:
                nutzer[verk]["coins"] = nutzer[verk].get("coins", 0) + preis
                _push_notif(nutzer, verk,
                            f"🛍️ {sp} hat dein {tier.get('emoji','?')} {tier['name']} für {preis} 💰 gekauft!")
        user.setdefault("entdeckte_arten", [])
        if tier["art"] not in user["entdeckte_arten"]:
            user["entdeckte_arten"].append(tier["art"])
        tier["besitzer"]    = sp
        tier["markt_preis"] = None
        tier["markt_von"]   = None
        nutzer[sp] = user; speichere("animals", tiere); speichere("users", nutzer)
    return jsonify({"ok": True, "tier": tier,
                    "user": {"coins": user["coins"], "blaetter": user["blaetter"]}})

@app.route("/api/markt/zurueckziehen", methods=["POST"])
@auth_required
def zurueckziehen():
    d = request.get_json() or {}; sp = g.sp
    with _lock:
        tiere = lade("animals"); nutzer = lade("users"); user = nutzer.get(sp)
        if not user: return jsonify({"ok": False, "fehler": "Fehler"}), 500
        tid  = sanitize(d.get("tier_id") or "", max_len=20)
        tier = next((t for t in tiere if t["id"] == tid
                     and t.get("besitzer") == "Markt" and t.get("markt_von") == sp), None)
        if not tier: return jsonify({"ok": False, "fehler": "Nicht gefunden"}), 404
        tier["besitzer"]    = sp
        tier["markt_preis"] = None
        tier["markt_von"]   = None
        user["inventar"].append(tier["id"])
        nutzer[sp] = user; speichere("animals", tiere); speichere("users", nutzer)
    return jsonify({"ok": True})


# ================================================================
#  TAUSCH-SYSTEM
# ================================================================

@app.route("/api/trades/meine")
@auth_required
def trades_meine():
    sp = g.sp; trades = lade("trades")
    meine = [t for t in trades if (t["von"] == sp or t["an"] == sp) and t["status"] == "offen"]
    tiere = {t["id"]: t for t in lade("animals")}
    for tr in meine:
        tr["biete_tier"]    = tiere.get(tr.get("biete_tier_id"))
        tr["wuensche_tier"] = tiere.get(tr.get("wuensche_tier_id"))
    return jsonify({"ok": True, "trades": meine})

@app.route("/api/trade/anbieten", methods=["POST"])
@auth_required
def trade_anbieten():
    d = request.get_json() or {}; sp = g.sp
    an          = sanitize(d.get("an") or "", max_len=30)
    biete_id    = sanitize(d.get("biete_tier_id")    or "", max_len=20) or None
    wuensche_id = sanitize(d.get("wuensche_tier_id") or "", max_len=20)
    gebot_coins = max(0, min(9999999, int(d.get("gebot_coins", 0) or 0)))
    if not an or not wuensche_id:
        return jsonify({"ok": False, "fehler": "Fehlende Parameter"}), 400
    if an == sp:
        return jsonify({"ok": False, "fehler": "Kein Trade mit dir selbst"}), 400
    nutzer = lade("users")
    if an not in nutzer:
        return jsonify({"ok": False, "fehler": "Spieler nicht gefunden"}), 404
    biete_tier = None
    if biete_id:
        tiere = lade("animals")
        biete_tier = next((t for t in tiere if t["id"] == biete_id and t["besitzer"] == sp), None)
        if not biete_tier:
            return jsonify({"ok": False, "fehler": "Tier gehört dir nicht"}), 403
    trade = {
        "id": str(uuid.uuid4())[:8].upper(), "von": sp, "an": an,
        "biete_tier_id": biete_id, "wuensche_tier_id": wuensche_id,
        "gebot_coins": gebot_coins, "status": "offen", "zeitstempel": jetzt_iso(),
    }
    with _lock:
        trades = lade("trades"); trades.append(trade); speichere("trades", trades)
        n2 = lade("users")
        if biete_tier:
            _push_notif(n2, an, f"🔁 {sp} möchte {biete_tier.get('emoji','?')} {biete_tier['name']} tauschen! [#{trade['id']}]")
        else:
            _push_notif(n2, an, f"💬 {sp} bietet {gebot_coins} 💰 für dein Tier! [#{trade['id']}]")
        speichere("users", n2)
    return jsonify({"ok": True, "trade": trade})

@app.route("/api/trade/annehmen/<trade_id>", methods=["POST"])
@auth_required
def trade_annehmen(trade_id):
    trade_id = sanitize(trade_id, max_len=20); sp = g.sp
    with _lock:
        trades = lade("trades"); nutzer = lade("users"); tiere = lade("animals")
        trade  = next((t for t in trades if t["id"] == trade_id
                       and t["an"] == sp and t["status"] == "offen"), None)
        if not trade: return jsonify({"ok": False, "fehler": "Trade nicht gefunden"}), 404
        von = trade["von"]; wuensche_id = trade["wuensche_tier_id"]
        biete_id = trade.get("biete_tier_id"); gebot_coins = trade.get("gebot_coins", 0)
        wuensche_tier = next((t for t in tiere if t["id"] == wuensche_id), None)
        if not wuensche_tier:
            return jsonify({"ok": False, "fehler": "Tier nicht mehr vorhanden"}), 400
        besitzer_ok = (wuensche_tier["besitzer"] == sp or
                       (wuensche_tier["besitzer"] == "Markt" and wuensche_tier.get("markt_von") == sp))
        if not besitzer_ok:
            return jsonify({"ok": False, "fehler": "Tier nicht mehr verfügbar"}), 400
        user_von = nutzer.get(von); user_an = nutzer.get(sp)
        if not user_von or not user_an:
            return jsonify({"ok": False, "fehler": "Spieler nicht gefunden"}), 404
        if biete_id:
            biete_tier = next((t for t in tiere if t["id"] == biete_id and t["besitzer"] == von), None)
            if not biete_tier:
                return jsonify({"ok": False, "fehler": "Angebotenes Tier nicht mehr da"}), 400
            biete_tier["besitzer"] = sp; wuensche_tier["besitzer"] = von
            wuensche_tier["markt_preis"] = None; wuensche_tier["markt_von"] = None
            user_von["inventar"] = [i for i in user_von.get("inventar", []) if i != biete_id]
            user_von["inventar"].append(wuensche_id)
            user_an["inventar"]  = [i for i in user_an.get("inventar", []) if i != wuensche_id]
            user_an["inventar"].append(biete_id)
            _push_notif(nutzer, von, f"✅ Tausch bestätigt! Du erhältst {wuensche_tier.get('emoji','?')} {wuensche_tier['name']}.")
        else:
            if user_von.get("coins", 0) < gebot_coins:
                return jsonify({"ok": False, "fehler": "Anbieter hat nicht genug Coins"}), 400
            user_von["coins"] -= gebot_coins
            user_an["coins"]   = user_an.get("coins", 0) + gebot_coins
            wuensche_tier["besitzer"] = von
            wuensche_tier["markt_preis"] = None; wuensche_tier["markt_von"] = None
            user_von["inventar"] = list(user_von.get("inventar", [])); user_von["inventar"].append(wuensche_id)
            user_an["inventar"]  = [i for i in user_an.get("inventar", []) if i != wuensche_id]
            _push_notif(nutzer, von, f"✅ Coin-Trade erfolgreich! {gebot_coins} 💰 gezahlt, du erhältst {wuensche_tier.get('emoji','?')} {wuensche_tier['name']}.")
        trade["status"] = "angenommen"
        nutzer[von] = user_von; nutzer[sp] = user_an
        speichere("trades", trades); speichere("animals", tiere); speichere("users", nutzer)
    return jsonify({"ok": True, "user": _pub(nutzer[sp])})

@app.route("/api/trade/ablehnen/<trade_id>", methods=["POST"])
@auth_required
def trade_ablehnen(trade_id):
    trade_id = sanitize(trade_id, max_len=20); sp = g.sp
    with _lock:
        trades = lade("trades"); nutzer = lade("users")
        trade  = next((t for t in trades if t["id"] == trade_id
                       and t["an"] == sp and t["status"] == "offen"), None)
        if not trade: return jsonify({"ok": False, "fehler": "Trade nicht gefunden"}), 404
        trade["status"] = "abgelehnt"
        _push_notif(nutzer, trade["von"], f"❌ {sp} hat dein Trade-Angebot abgelehnt. [#{trade_id}]")
        speichere("trades", trades); speichere("users", nutzer)
    return jsonify({"ok": True})


# ================================================================
#  PREISVERHANDLUNG
# ================================================================

@app.route("/api/user/einstellungen", methods=["POST"])
@auth_required
def einstellungen_speichern():
    d = request.get_json() or {}; sp = g.sp
    erlaubt = {"auto_verhandlung"}
    with _lock:
        nutzer = lade("users"); user = nutzer.get(sp)
        if not user: return jsonify({"ok": False, "fehler": "Fehler"}), 500
        for k, v in d.items():
            if k in erlaubt:
                user.setdefault("einstellungen", {})[k] = sanitize(str(v), max_len=50)
        nutzer[sp] = user; speichere("users", nutzer)
    return jsonify({"ok": True})

@app.route("/api/user/einstellungen")
@auth_required
def einstellungen_lesen():
    return jsonify({"ok": True, "einstellungen": g.nutzer.get(g.sp, {}).get("einstellungen", {})})


_verhandlungs_sessions = {}

def _cleanup_verhandlungen():
    jetzt = time.monotonic()
    stale = [k for k, v in _verhandlungs_sessions.items() if jetzt - v.get("t", 0) > 1800]
    for k in stale: del _verhandlungs_sessions[k]

@app.route("/api/verhandlung/starten", methods=["POST"])
@auth_required
def verhandlung_starten():
    d = request.get_json() or {}; sp = g.sp
    tid   = sanitize(d.get("tier_id") or "", max_len=20)
    tiere = lade("animals")
    tier  = next((t for t in tiere if t["id"] == tid and t.get("besitzer") == "Markt"), None)
    if not tier: return jsonify({"ok": False, "fehler": "Nicht verfügbar"}), 404
    preis = tier["markt_preis"]
    _verhandlungs_sessions[(sp, tid)] = {
        "runde": 0, "listenpreis": preis, "min_preis": round(preis * 0.68),
        "gegenangebot": None, "t": time.monotonic(),
    }
    if random.random() < 0.05: _cleanup_verhandlungen()
    return jsonify({"ok": True, "listenpreis": preis, "min_preis_hint": round(preis * 0.85)})

@app.route("/api/verhandlung/angebot", methods=["POST"])
@auth_required
def verhandlung_angebot():
    d     = request.get_json() or {}; sp = g.sp
    tid   = sanitize(d.get("tier_id") or "", max_len=20)
    gebot = max(0, min(99999999, int(d.get("gebot", 0) or 0)))
    tiere  = lade("animals")
    tier   = next((t for t in tiere if t["id"] == tid and t.get("besitzer") == "Markt"), None)
    if not tier: return jsonify({"ok": False, "fehler": "Nicht mehr verfügbar"}), 404
    preis   = tier["markt_preis"]
    verk    = tier.get("markt_von")
    ist_bot = (verk == BOT_NAME)
    nutzer  = lade("users")

    verk_e      = (nutzer.get(verk) or {}).get("einstellungen", {})
    verk_online = bool(verk and sekunden_seit((nutzer.get(verk) or {}).get("letzte_aktivitaet")) < ONLINE_TIMEOUT)
    auto_vhd    = verk_e.get("auto_verhandlung", "selbst")

    if auto_vhd == "selbst" and not ist_bot:
        if not verk_online:
            return jsonify({"ok": True, "ergebnis": "offline",
                            "nachricht": f"⏳ {verk} verhandelt selbst und ist gerade offline. Kaufe zum Listenpreis oder komm später."})
        return jsonify({"ok": True, "ergebnis": "warte_auf_spieler",
                        "nachricht": f"📨 Angebot gesendet. {verk} wird benachrichtigt."})

    benutze_bot = ist_bot or (auto_vhd == "immer_bot") or (auto_vhd == "bot_wenn_offline" and not verk_online)

    key = (sp, tid)
    if key not in _verhandlungs_sessions:
        _verhandlungs_sessions[key] = {
            "runde": 0, "listenpreis": preis,
            "min_preis": round(preis * 0.68), "gegenangebot": None, "t": time.monotonic(),
        }
    sess = _verhandlungs_sessions[key]
    sess["runde"] += 1
    runde = sess["runde"]; min_preis = sess["min_preis"]

    if gebot >= preis:
        del _verhandlungs_sessions[key]
        return jsonify({"ok": True, "ergebnis": "angenommen", "endpreis": preis,
                        "nachricht": "💰 Listenpreis akzeptiert – Deal!"})

    if gebot < min_preis:
        if runde >= 2:
            del _verhandlungs_sessions[key]
            msg = random.choice([
                f"🤖 Nein. Mein Mindestpreis ist {min_preis} – kein Cent weniger.",
                f"🤖 Verhandlung beendet. Unter {min_preis} gehe ich nicht.",
            ]) if benutze_bot else f"❌ Unter {min_preis} 💰 geht es wirklich nicht."
            return jsonify({"ok": True, "ergebnis": "abgebrochen", "nachricht": msg})
        ga = round(min_preis * random.uniform(1.0, 1.08))
        sess["gegenangebot"] = ga
        msg = random.choice([
            f"🤖 Zu wenig! Gegenangebot: {ga} 💰.",
            f"🤖 Für diesen Rang? Unmöglich. Ich gehe auf {ga}.",
        ]) if benutze_bot else f"Zu wenig. Ich schlage {ga} 💰 vor."
        return jsonify({"ok": True, "ergebnis": "gegenangebot", "gegenangebot": ga,
                        "min_preis": min_preis, "nachricht": msg, "runde": runde})

    prozent = gebot / preis

    if prozent >= 0.88:
        del _verhandlungs_sessions[key]
        msg = random.choice([f"🤖 Deal! {gebot} 💰 – einverstanden. 🤝",
                              f"🤖 Gut verhandelt! {gebot} akzeptiert.",
                             ]) if benutze_bot else f"✅ Einverstanden! {gebot} 💰 – Deal! 🤝"
        return jsonify({"ok": True, "ergebnis": "angenommen", "endpreis": gebot, "nachricht": msg})

    if prozent >= 0.78:
        if runde >= 3:
            if random.random() < 0.6:
                del _verhandlungs_sessions[key]
                msg = "🤖 Ok, ich nehme es an." if benutze_bot else f"✅ Na gut, {gebot} 💰. Abgemacht."
                return jsonify({"ok": True, "ergebnis": "angenommen", "endpreis": gebot, "nachricht": msg})
            ga = round(min_preis * 1.02); del _verhandlungs_sessions[key]
            msg = f"🤖 Letztes Wort: {ga} 💰. Ja oder nein?" if benutze_bot else f"Letztes Angebot: {ga} 💰."
            return jsonify({"ok": True, "ergebnis": "letztes_angebot", "gegenangebot": ga,
                            "min_preis": min_preis, "nachricht": msg, "runde": runde})
        ga = max(min_preis, round((gebot + preis * 0.9) / 2))
        sess["gegenangebot"] = ga
        msg = random.choice([f"🤖 Wie wäre es mit {ga}? Mein Kompromiss.",
                              f"🤖 Ich treffe dich in der Mitte: {ga} 💰.",
                             ]) if benutze_bot else f"Ich treffe dich in der Mitte: {ga} 💰?"
        return jsonify({"ok": True, "ergebnis": "gegenangebot", "gegenangebot": ga,
                        "min_preis": min_preis, "nachricht": msg, "runde": runde})

    ga = round(min_preis * random.uniform(1.01, 1.06))
    sess["gegenangebot"] = ga
    msg = random.choice([f"🤖 Unter {ga} gehe ich nicht – letztes Angebot.",
                          f"🤖 {ga} 💰 – mein finales Angebot.",
                         ]) if benutze_bot else f"Unterste Grenze: {ga} 💰. Mehr geht nicht."
    return jsonify({"ok": True, "ergebnis": "letztes_angebot", "gegenangebot": ga,
                    "min_preis": min_preis, "nachricht": msg, "runde": runde})

@app.route("/api/verhandlung/abschluss", methods=["POST"])
@auth_required
def verhandlung_abschluss():
    d = request.get_json() or {}; sp = g.sp
    tid   = sanitize(d.get("tier_id") or "", max_len=20)
    preis = max(0, int(d.get("endpreis", 0) or 0))
    with _lock:
        tiere = lade("animals"); nutzer = lade("users"); user = nutzer.get(sp)
        if not user: return jsonify({"ok": False, "fehler": "Fehler"}), 500
        tier  = next((t for t in tiere if t["id"] == tid and t.get("besitzer") == "Markt"), None)
        if not tier: return jsonify({"ok": False, "fehler": "Nicht mehr verfügbar"}), 404
        min_preis = round(tier["markt_preis"] * 0.68)
        if preis < min_preis: return jsonify({"ok": False, "fehler": "Preis zu niedrig"}), 400
        if user["coins"] < preis: return jsonify({"ok": False, "fehler": "Nicht genug Coins"}), 400
        user["coins"] -= preis; user["inventar"].append(tier["id"])
        verk = tier.get("markt_von")
        if verk and verk in nutzer:
            if nutzer[verk].get("ist_bot"):
                nutzer[verk]["coins"] = min(BOT_MAX_COINS, nutzer[verk].get("coins", 0) + preis)
            else:
                nutzer[verk]["coins"] = nutzer[verk].get("coins", 0) + preis
                _push_notif(nutzer, verk, f"🤝 {sp} hat dein {tier.get('emoji','?')} {tier['name']} für {preis} 💰 ausgehandelt!")
        tier["besitzer"] = sp; tier["markt_preis"] = None; tier["markt_von"] = None
        user.setdefault("entdeckte_arten", [])
        if tier["art"] not in user["entdeckte_arten"]: user["entdeckte_arten"].append(tier["art"])
        nutzer[sp] = user; speichere("animals", tiere); speichere("users", nutzer)
    return jsonify({"ok": True, "tier": tier,
                    "user": {"coins": user["coins"], "blaetter": user["blaetter"]}})


# ================================================================
#  STAMMBAUM / SONSTIGES
# ================================================================

@app.route("/api/stammbaum/<tid>")
@auth_required
def stammbaum(tid):
    tid = sanitize(tid, max_len=20)
    tmap = {t["id"]: t for t in lade("animals")}
    def baum(i, d=0):
        if not i or d > 5: return None
        t = tmap.get(i); gn = (t or {}).get("genetik", {})
        if not t: return None
        return {"id": t["id"], "name": t["name"], "art": t["art"],
                "emoji": t.get("emoji", "?"),
                "farbe": gn.get("koerper_farbe", [150, 150, 150]),
                "rang": gn.get("rang", 1), "stufe": gn.get("stufe", "?"),
                "rang_farbe": gn.get("rang_farbe", "#aaa"), "gen": t.get("generation", 0),
                "vater": baum(t["stammbaum"].get("vater_id"), d + 1),
                "mutter": baum(t["stammbaum"].get("mutter_id"), d + 1)}
    b = baum(tid)
    if not b: return jsonify({"ok": False, "fehler": "Nicht gefunden"}), 404
    return jsonify({"ok": True, "stammbaum": b})

@app.route("/api/rang_info")
def rang_info():
    # Alle Stufen zurückgeben (repräsentative Ränge)
    raenge = []
    for lo, hi, name, farbe, _ in genetics.STUFEN:
        raenge.append(genetics.rang_zu_stufe(lo))
    return jsonify({"ok": True, "raenge": raenge})


# ================================================================
#  CHAT-SYSTEM
# ================================================================

@app.route("/api/nachricht/senden", methods=["POST"])
@auth_required
def nachricht_senden():
    d  = request.get_json() or {}
    sp = g.sp
    if not _rate.allow(f"msg:{sp}", 20, 60):
        return jsonify({"ok": False, "fehler": "Zu viele Nachrichten – kurz warten"}), 429
    an   = sanitize(d.get("an")   or "", max_len=30)
    text = sanitize(d.get("text") or "", max_len=500, allow_spaces=True)
    if not an or not text:
        return jsonify({"ok": False, "fehler": "Empfänger und Text erforderlich"}), 400
    if an == sp:
        return jsonify({"ok": False, "fehler": "Du kannst dir nicht selbst schreiben"}), 400
    if an == BOT_NAME:
        return jsonify({"ok": False, "fehler": "MarktBot antwortet leider nicht 🤖"}), 400
        
    nutzer = lade("users")
    if an != "__alle__":
        if an not in nutzer:
            return jsonify({"ok": False, "fehler": "Spieler nicht gefunden"}), 404
        empf = nutzer[an]
        if sp in empf.get("blockiert", []):
            return jsonify({"ok": False, "fehler": "Nachricht konnte nicht gesendet werden"}), 403
    msg = {
        "id":      str(uuid.uuid4())[:8].upper(),
        "von":     sp, "an": an,
        "text":    text,
        "zeit":    jetzt_iso(),
        "gelesen": False,
    }
    with _lock:
        nachrichten = lade("nachrichten")
        nachrichten.append(msg)
        if len(nachrichten) > MAX_NACHRICHTEN:
            nachrichten = nachrichten[-MAX_NACHRICHTEN:]
        speichere("nachrichten", nachrichten)
    return jsonify({"ok": True, "nachricht": msg})

@app.route("/api/nachrichten/postfach")
@auth_required
def postfach():
    sp = g.sp
    nachrichten = lade("nachrichten")
    konvs = {}
    for m in nachrichten:
        if m["von"] == sp:   partner = m["an"]
        elif m["an"] == sp:  partner = m["von"]
        else:                continue
        if partner not in konvs:
            konvs[partner] = {"partner": partner, "letzte": m, "ungelesen": 0}
        else:
            konvs[partner]["letzte"] = m
        if m["an"] == sp and not m.get("gelesen"):
            konvs[partner]["ungelesen"] += 1
    result = sorted(konvs.values(), key=lambda k: k["letzte"]["zeit"], reverse=True)
    return jsonify({"ok": True, "konversationen": result})

@app.route("/api/nachrichten/verlauf/<partner>")
@auth_required
def nachrichten_verlauf(partner):
    sp      = g.sp
    partner = sanitize(partner, max_len=30)
    nachrichten = lade("nachrichten")
    
    if partner == "__alle__":
        verlauf = [m for m in nachrichten if m["an"] == "__alle__"]
    else:
        verlauf = [m for m in nachrichten
                   if (m["von"] == sp and m["an"] == partner)
                   or (m["von"] == partner and m["an"] == sp)]
    with _lock:
        alle = lade("nachrichten"); changed = False
        for m in alle:
            if m["an"] == sp and m["von"] == partner and not m.get("gelesen"):
                m["gelesen"] = True; changed = True
        if changed:
            speichere("nachrichten", alle)
    return jsonify({"ok": True, "verlauf": verlauf[-100:]})

@app.route("/api/nachrichten/ungelesen_anzahl")
@auth_required
def ungelesen_anzahl():
    sp = g.sp
    nachrichten = lade("nachrichten")
    count = sum(1 for m in nachrichten if m["an"] == sp and not m.get("gelesen"))
    return jsonify({"ok": True, "anzahl": count})


# ================================================================
#  SOZIALES SYSTEM (Freunde + Blockieren)
# ================================================================

@app.route("/api/sozialdaten")
@auth_required
def sozialdaten():
    user = g.nutzer.get(g.sp, {})
    return jsonify({
        "ok":        True,
        "freunde":   user.get("freunde",   []),
        "blockiert": user.get("blockiert", []),
    })

@app.route("/api/freunde/hinzufuegen", methods=["POST"])
@auth_required
def freund_hinzufuegen():
    d = request.get_json() or {}; sp = g.sp
    name = sanitize(d.get("name") or "", max_len=30)
    if not name or name == sp:
        return jsonify({"ok": False, "fehler": "Ungültiger Name"}), 400
    with _lock:
        nutzer = lade("users")
        if name not in nutzer:
            return jsonify({"ok": False, "fehler": "Spieler nicht gefunden"}), 404
        user = nutzer[sp]
        user.setdefault("freunde", [])
        if name not in user["freunde"]:
            user["freunde"].append(name)
        nutzer[sp] = user; speichere("users", nutzer)
    return jsonify({"ok": True})

@app.route("/api/freunde/entfernen", methods=["POST"])
@auth_required
def freund_entfernen():
    d = request.get_json() or {}; sp = g.sp
    name = sanitize(d.get("name") or "", max_len=30)
    with _lock:
        nutzer = lade("users"); user = nutzer.get(sp, {})
        user["freunde"] = [f for f in user.get("freunde", []) if f != name]
        nutzer[sp] = user; speichere("users", nutzer)
    return jsonify({"ok": True})

@app.route("/api/blockieren", methods=["POST"])
@auth_required
def blockieren():
    d = request.get_json() or {}; sp = g.sp
    name = sanitize(d.get("name") or "", max_len=30)
    if not name or name == sp:
        return jsonify({"ok": False, "fehler": "Ungültiger Name"}), 400
    with _lock:
        nutzer = lade("users"); user = nutzer.get(sp, {})
        user.setdefault("blockiert", [])
        if name not in user["blockiert"]:
            user["blockiert"].append(name)
        user["freunde"] = [f for f in user.get("freunde", []) if f != name]
        nutzer[sp] = user; speichere("users", nutzer)
    return jsonify({"ok": True})

@app.route("/api/entblockieren", methods=["POST"])
@auth_required
def entblockieren():
    d = request.get_json() or {}; sp = g.sp
    name = sanitize(d.get("name") or "", max_len=30)
    with _lock:
        nutzer = lade("users"); user = nutzer.get(sp, {})
        user["blockiert"] = [b for b in user.get("blockiert", []) if b != name]
        nutzer[sp] = user; speichere("users", nutzer)
    return jsonify({"ok": True})


# ================================================================
#  START
# ================================================================

if __name__ == "__main__":
    os.makedirs(DATA, exist_ok=True)
    for fname, default in [("animals", []), ("users", {}), ("trades", []), ("nachrichten", [])]:
        p = os.path.join(DATA, f"{fname}.json")
        if not os.path.exists(p):
            with open(p, "w") as fh: json.dump(default, fh)
    bot_starte()
    print("=" * 60)
    print("  PatTat  ·  Multiplayer  ·  v6")
    print("  http://localhost:5000")
    print("  Tipp: Setze PATTAT_SECRET=<32-Zeichen-Schlüssel>")
    print("=" * 60)
    app.run(debug=False, port=5000, host="0.0.0.0")
