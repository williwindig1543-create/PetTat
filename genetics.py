"""
genetics.py – PatTat · Genetik-Engine
======================================
1000 Ränge · Wild max Rang 100 · Großeltern-Einfluss · Logische Zucht
"""

import random, uuid, math

# ─── 1000-Rang-System ─────────────────────────────────────────────
# Rang   1–100  : In der Wildnis findbar
# Rang 101–1000 : Nur durch Züchten erreichbar

STUFEN = [
    # (min_rang, max_rang, name,            farbe_hex,   basis_preis_pro_rang)
    #  ── Wildränge ──────────────────────────────────────────────────
    (   1,  10, "Gewöhnlich",      "#aaaaaa",     8),
    (  11,  20, "Ungewöhnlich",    "#55dd55",    14),
    (  21,  30, "Selten",          "#4499ff",    22),
    (  31,  40, "Episch",          "#bb44ff",    34),
    (  41,  50, "Legendär",        "#ffaa00",    50),
    (  51,  60, "Mythisch",        "#ff5555",    72),
    (  61,  70, "Antik",           "#00ddff",    98),
    (  71,  80, "Göttlich",        "#ffee22",   130),
    (  81,  90, "Transzendent",    "#ff44ff",   170),
    (  91, 100, "Absolut",         "#ffffff",   220),
    #  ── Zücht-Ränge (nur durch Züchten erreichbar) ─────────────────
    ( 101, 200, "Übernatürlich",   "#ff8833",   380),
    ( 201, 300, "Kosmisch",        "#00ffcc",   600),
    ( 301, 400, "Dimensional",     "#cc44ff",   900),
    ( 401, 500, "Celestiell",      "#4488ff",  1300),
    ( 501, 600, "Uralt",           "#ff3300",  1850),
    ( 601, 700, "Ewig",            "#44ff99",  2600),
    ( 701, 800, "Primordial",      "#ffdd33",  3600),
    ( 801, 900, "Götterkind",      "#ff55ff",  5000),
    ( 901, 999, "Schöpfer",        "#aaddff",  7000),
    (1000,1000, "PatTat",          "#ffd700", 15000),
]

MAX_RANG      = 1000
MAX_WILD_RANG = 100


def rang_zu_stufe(rang: int) -> dict:
    """Gibt Stufen-Info für einen Rang zurück (1–1000)."""
    rang = max(1, min(MAX_RANG, rang))
    for lo, hi, name, farbe, preis_pro in STUFEN:
        if lo <= rang <= hi:
            return {
                "rang":           rang,
                "stufe":          name,
                "farbe":          farbe,
                "basis_preis":    rang * preis_pro,
                "rang_in_stufe":  rang - lo + 1,
                "ist_zucht_rang": rang > MAX_WILD_RANG,
            }
    return {"rang": rang, "stufe": "Gewöhnlich", "farbe": "#aaaaaa",
            "basis_preis": rang * 8, "rang_in_stufe": 1, "ist_zucht_rang": False}


def stufe_zu_rang_bereich(stufe: str) -> tuple:
    for lo, hi, name, _, _ in STUFEN:
        if name == stufe:
            return lo, hi
    return 1, 10


# ─── Spezies ─────────────────────────────────────────────────────

SPECIES = {
    "Koala":  {"emoji": "🐨", "base_size": 1.0,  "base_speed": 0.5},
    "Fuchs":  {"emoji": "🦊", "base_size": 0.85, "base_speed": 1.2},
    "Huhn":   {"emoji": "🐔", "base_size": 0.6,  "base_speed": 0.9},
    "Panda":  {"emoji": "🐼", "base_size": 1.3,  "base_speed": 0.4},
    "Hase":   {"emoji": "🐰", "base_size": 0.55, "base_speed": 1.5},
    "Wolf":   {"emoji": "🐺", "base_size": 1.1,  "base_speed": 1.4},
    "Bär":    {"emoji": "🐻", "base_size": 1.5,  "base_speed": 0.6},
}

# Erweiterte Namenslisten mit PatTat-Charme
FIRST_NAMES = [
    # Klassisch
    "Nova", "Lumi", "Coco", "Sage", "Ash", "River", "Mochi", "Kira", "Boo",
    "Ember", "Dew", "Fern", "Storm", "Dawn", "Pixel", "Echo", "Flint", "Cedar",
    "Wisp", "Blaze", "Frost", "Ivy", "Rune", "Zara", "Quinn", "Onyx", "Pearl",
    # Natürlich
    "Nimbus", "Sable", "Cinder", "Thistle", "Bramble", "Solstice", "Equinox",
    "Vesper", "Zephyr", "Talon", "Cobalt", "Indigo", "Sienna", "Jasper",
    "Flicker", "Drift", "Haze", "Gleam", "Gust", "Helm", "Jolt", "Lynx",
    "Marsh", "Nook", "Pine", "Quill", "Reed", "Sprout", "Wick", "Briar",
    # Kosmisch (für hohe Ränge passend)
    "Stardust", "Moonbeam", "Sunspot", "Raindrop", "Snowfall", "Mistral",
    "Cyclone", "Torrent", "Inferno", "Glacier", "Nebula", "Cosmos", "Solara",
    "Aether", "Vega", "Altair", "Rigel", "Sirius", "Orion", "Lyra",
    # Deutsch-Fantasy
    "Funken", "Glut", "Nebel", "Sturm", "Frost", "Dämmer", "Morgen", "Asche",
    "Stein", "Moos", "Tau", "Gischt", "Schatten", "Licht", "Blitz", "Donner",
]

LAST_NAMES = [
    # Klassisch
    "Paws", "Cloud", "Berry", "Bark", "Leaf", "Mist", "Ridge", "Bloom",
    "Shade", "Thorn", "Vale", "Creek", "Hollow", "Glade", "Crest", "Peak",
    "Glen", "Dusk", "Veil", "Stone", "Rift", "Aura", "Tide", "Glow",
    # Natur
    "Whisker", "Tuft", "Burrow", "Thicket", "Copse", "Heath", "Moor",
    "Knoll", "Bluff", "Crag", "Dell", "Gorge", "Flurry", "Eddy", "Gale",
    "Breeze", "Ember", "Smolder", "Flare", "Ripple", "Surge", "Cascade",
    "Shimmer", "Glimmer", "Twinkle", "Sparkle", "Luster",
    # Episch (häufiger bei hohen Rängen)
    "Starborn", "Voidwalker", "Dreamweaver", "Soulfire", "Cosmosrift",
    "Eternalbark", "Primalroar", "Celestialpad", "Godspawn", "Pattat",
    "Worldender", "Dawnbringer", "Veilpiercer", "Stormcaller", "Ashwalker",
]

EPIC_LAST = [
    "Godspawn", "Pattat", "Primalroar", "Celestialpad", "Voidwalker",
    "Cosmosrift", "Eternalbark", "Soulfire", "Worldender", "Dawnbringer",
    "Stormcaller", "Dreamweaver", "Veilpiercer", "Ashwalker", "Starborn",
]


def random_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def random_name_fuer_rang(rang: int) -> str:
    """Höhere Ränge bekommen häufiger epische Nachnamen."""
    vn = random.choice(FIRST_NAMES)
    if rang >= 900 and random.random() < 0.65:
        nn = random.choice(EPIC_LAST)
    elif rang >= 500 and random.random() < 0.35:
        nn = random.choice(EPIC_LAST)
    else:
        nn = random.choice(LAST_NAMES)
    return f"{vn} {nn}"


# ─── Farb-Helfer ──────────────────────────────────────────────────

def zufalls_farbe():
    return [random.randint(0, 255) for _ in range(3)]


def misch_farbe(c1, c2, c_gross=None, gross_gewicht=0.15, mut=18):
    """Mischt zwei Farben mit optionalem Großeltern-Einfluss."""
    result = []
    for i in range(3):
        basis = (c1[i] + c2[i]) / 2
        if c_gross is not None:
            basis = basis * (1 - gross_gewicht) + c_gross[i] * gross_gewicht
        delta = random.randint(-mut, mut)
        result.append(max(0, min(255, round(basis + delta))))
    return result


def misch_wert(a, b, lo, hi, gross=None, gross_w=0.12, mut_staerke=0.1):
    """Mischt zwei Zahlenwerte mit optionalem Großeltern-Einfluss."""
    basis = (a + b) / 2
    if gross is not None and isinstance(gross, (int, float)):
        basis = basis * (1 - gross_w) + gross * gross_w
    spanne = (hi - lo) * mut_staerke
    return round(max(lo, min(hi, basis + random.uniform(-spanne, spanne))), 3)


# ─── Rang-Berechnung (1–1000) ────────────────────────────────────

MUTATIONS_CHANCE  = 0.05   # 5 %  → Rang-Sprung
SUPER_MUTATION_CH = 0.01   # 1 %  → extreme Eigenschaft


def berechne_kind_rang(r1: int, r2: int) -> int:
    """
    Rang des Kindes aus zwei Elternteilen.
    Normal:    Schnitt ± Gauss(0,3), max +12 / -5
    Mutation:  5 % Chance auf ±25 Sprung
    Deckel:    max. Rang 1000
    """
    schnitt   = (r1 + r2) / 2
    variation = random.gauss(0, 3)
    kind_rang = schnitt + variation

    untergrenze = min(r1, r2) - 5
    obergrenze  = max(r1, r2) + 12
    kind_rang   = max(untergrenze, min(obergrenze, kind_rang))

    if random.random() < MUTATIONS_CHANCE:
        sprung    = random.choice([-25, -18, -12, 12, 18, 25, 30])
        kind_rang = kind_rang + sprung

    return max(1, min(MAX_RANG, round(kind_rang)))


# ─── Haupt-Zucht-Funktion ─────────────────────────────────────────

def breed(p1: dict, p2: dict) -> dict:
    """
    Erzeugt Kind aus zwei Eltern. Nutzt Großeltern-Daten wenn vorhanden.
    Kind-Rang kann bis 1000 gehen (Wildtiere max 100).
    """
    g1 = p1["genetik"]
    g2 = p2["genetik"]

    # ── Großeltern-Farben ──────────────────────────────────────
    def gross_farbe(g, key):
        gf = g.get("grosseltern_farben") or {}
        return gf.get(key)

    gk1 = gross_farbe(g1, "koerper") or g1["koerper_farbe"]
    gk2 = gross_farbe(g2, "koerper") or g2["koerper_farbe"]
    gross_koerper = [(a + b) // 2 for a, b in zip(gk1, gk2)]

    gb1 = gross_farbe(g1, "bauch") or g1["bauch_farbe"]
    gb2 = gross_farbe(g2, "bauch") or g2["bauch_farbe"]
    gross_bauch = [(a + b) // 2 for a, b in zip(gb1, gb2)]

    go1 = gross_farbe(g1, "ohr") or g1["ohr_farbe"]
    go2 = gross_farbe(g2, "ohr") or g2["ohr_farbe"]
    gross_ohr = [(a + b) // 2 for a, b in zip(go1, go2)]

    # ── Farben mischen ─────────────────────────────────────────
    if random.random() < MUTATIONS_CHANCE:
        koerper_farbe = zufalls_farbe()
        mutation_flag = True
    else:
        koerper_farbe = misch_farbe(g1["koerper_farbe"], g2["koerper_farbe"], gross_koerper, mut=14)
        mutation_flag = False

    bauch_farbe = misch_farbe(g1["bauch_farbe"], g2["bauch_farbe"], gross_bauch, mut=12)
    ohr_farbe   = misch_farbe(g1["ohr_farbe"],   g2["ohr_farbe"],   gross_ohr,   mut=12)

    # ── Rang berechnen ─────────────────────────────────────────
    r1 = g1.get("rang", 5)
    r2 = g2.get("rang", 5)
    gr_schnitt = (g1.get("grosseltern_rang", r1) + g2.get("grosseltern_rang", r2)) / 2
    basis_rang = berechne_kind_rang(r1, r2)
    kind_rang  = round(basis_rang * 0.9 + gr_schnitt * 0.1)
    kind_rang  = max(1, min(MAX_RANG, kind_rang))
    rang_info  = rang_zu_stufe(kind_rang)

    # ── Eigenschaften mischen ──────────────────────────────────
    # BUG-FIX: war vorher:  g.get(...) or {} or {} or {} or {}.get(key)
    # Korrekt:              (g.get(...) or {}).get(key)
    def gr_wert(g, key):
        return (g.get("grosseltern_werte") or {}).get(key)

    groesse    = misch_wert(g1["groesse"],     g2["groesse"],     0.4,  2.2, gr_wert(g1, "groesse"))
    speed      = misch_wert(g1["speed"],       g2["speed"],       0.15, 2.0, gr_wert(g1, "speed"))
    ear_size   = misch_wert(g1["ohr_groesse"], g2["ohr_groesse"], 0.25, 1.0)
    roundness  = misch_wert(g1["rundheit"],    g2["rundheit"],    0.5,  1.5)
    fluffiness = misch_wert(g1["flauschig"],   g2["flauschig"],   0.3,  1.5)

    # Super-Mutation (1 %)
    super_mut = False
    if random.random() < SUPER_MUTATION_CH:
        super_mut = True
        trait = random.choice(["groesse", "speed", "flauschig"])
        if trait == "groesse":   groesse    = round(random.uniform(0.4, 2.2), 3)
        elif trait == "speed":   speed      = round(random.uniform(0.15, 2.0), 3)
        else:                    fluffiness = round(random.uniform(0.3, 1.5), 3)

    # ── Art & Hybrid ───────────────────────────────────────────
    if p1["art"] == p2["art"]:
        art = p1["art"]
    else:
        teile  = sorted([p1["art"].replace("-Hybrid", ""), p2["art"].replace("-Hybrid", "")])
        unique = list(dict.fromkeys(t for s in teile for t in s.split("-") if t))
        art    = "-".join(unique[:2]) + "-Hybrid"

    emoji      = _hybrid_emoji(art)
    generation = max(p1.get("generation", 0), p2.get("generation", 0)) + 1
    basis_preis = rang_info["basis_preis"]
    name        = random_name_fuer_rang(kind_rang)

    child = {
        "id":         str(uuid.uuid4())[:8].upper(),
        "name":       name,
        "art":        art,
        "emoji":      emoji,
        "besitzer":   p1.get("besitzer", "spieler"),
        "generation": generation,
        "genetik": {
            "koerper_farbe":  koerper_farbe,
            "bauch_farbe":    bauch_farbe,
            "ohr_farbe":      ohr_farbe,
            "groesse":        groesse,
            "speed":          speed,
            "ohr_groesse":    ear_size,
            "rundheit":       roundness,
            "flauschig":      fluffiness,
            "rang":           kind_rang,
            "stufe":          rang_info["stufe"],
            "rang_farbe":     rang_info["farbe"],
            "ist_zucht_rang": kind_rang > MAX_WILD_RANG,
            "grosseltern_farben": {
                "koerper": [(a + b) // 2 for a, b in zip(g1["koerper_farbe"], g2["koerper_farbe"])],
                "bauch":   [(a + b) // 2 for a, b in zip(g1["bauch_farbe"],   g2["bauch_farbe"])],
                "ohr":     [(a + b) // 2 for a, b in zip(g1["ohr_farbe"],     g2["ohr_farbe"])],
            },
            "grosseltern_rang":   (r1 + r2) // 2,
            "grosseltern_werte": {
                "groesse": (g1["groesse"] + g2["groesse"]) / 2,
                "speed":   (g1["speed"]   + g2["speed"])   / 2,
            },
        },
        "stammbaum": {
            "vater_id":    p1["id"],
            "mutter_id":   p2["id"],
            "vater_name":  p1.get("name", "?"),
            "mutter_name": p2.get("name", "?"),
        },
        "markt_preis": None,
        "markt_von":   None,
        "basis_preis": basis_preis,
        "meta": {
            "mutation":       mutation_flag,
            "super_mutation": super_mut,
            "ist_neue_art":   "-Hybrid" in art and art not in (p1["art"], p2["art"]),
            "zucht_nummer":   None,
        },
    }
    return child


# ─── Wildtier generieren (max Rang 100) ──────────────────────────

def generiere_wildtier(art=None, ziel_rang=None) -> dict:
    """
    Wildtier mit zufälligem oder gewünschtem Rang.
    Wildtiere sind IMMER maximal Rang 100.
    """
    if art is None:
        art = random.choice(list(SPECIES.keys()))
    sp = SPECIES.get(art, SPECIES["Koala"])

    if ziel_rang is None:
        ziel_rang = random.choices(
            range(1, 101),
            weights=[max(1, 30 - abs(r - 10)) for r in range(1, 101)]
        )[0]

    ziel_rang = max(1, min(MAX_WILD_RANG, ziel_rang))
    rang_info = rang_zu_stufe(ziel_rang)

    g = {
        "koerper_farbe":   zufalls_farbe(),
        "bauch_farbe":     zufalls_farbe(),
        "ohr_farbe":       zufalls_farbe(),
        "groesse":         round(sp["base_size"]  * random.uniform(0.75, 1.3), 3),
        "speed":           round(sp["base_speed"] * random.uniform(0.75, 1.3), 3),
        "ohr_groesse":     round(random.uniform(0.25, 1.0), 3),
        "rundheit":        round(random.uniform(0.5,  1.5), 3),
        "flauschig":       round(random.uniform(0.3,  1.5), 3),
        "rang":            ziel_rang,
        "stufe":           rang_info["stufe"],
        "rang_farbe":      rang_info["farbe"],
        "ist_zucht_rang":  False,
        "grosseltern_farben": None,
        "grosseltern_rang":   ziel_rang,
        "grosseltern_werte":  None,
    }

    return {
        "id":          str(uuid.uuid4())[:8].upper(),
        "name":        random_name(),
        "art":         art,
        "emoji":       sp["emoji"],
        "besitzer":    None,
        "generation":  0,
        "genetik":     g,
        "stammbaum":   {"vater_id": None, "mutter_id": None,
                        "vater_name": None, "mutter_name": None},
        "markt_preis": None,
        "markt_von":   None,
        "basis_preis": rang_info["basis_preis"],
        "meta": {"mutation": False, "super_mutation": False,
                 "ist_neue_art": False, "zucht_nummer": None},
    }


# ─── Hilfsfunktionen ─────────────────────────────────────────────

def _hybrid_emoji(art: str) -> str:
    if "-Hybrid" not in art:
        return SPECIES.get(art, {}).get("emoji", "❓")
    teile = art.replace("-Hybrid", "").split("-")
    return "".join(SPECIES.get(t, {}).get("emoji", "❓") for t in teile[:2])


def bot_preis_fuer(tier: dict) -> int:
    """Bot-Kaufpreis basierend auf Rang (1–1000)."""
    rang  = tier.get("genetik", {}).get("rang", 5)
    info  = rang_zu_stufe(rang)
    basis = info["basis_preis"]
    return max(10, round(basis * random.uniform(0.88, 1.12)))


def zucht_kosten(r1: int, r2: int) -> int:
    """Blätter-Kosten für eine Züchtung, abhängig von den Elternrängen."""
    schnitt = (r1 + r2) / 2
    if schnitt <= 100:
        return max(1, min(10, math.ceil(schnitt / 20)))
    elif schnitt <= 300:
        return max(10, math.ceil(schnitt / 25))
    elif schnitt <= 600:
        return max(20, math.ceil(schnitt / 20))
    else:
        return max(40, math.ceil(schnitt / 15))
