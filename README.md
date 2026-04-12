# 🐾 PatTat

Ein 3D-Browser-Spiel mit prozedualer Welt, Genetik-System und Züchtungs-Engine.

---

## 🚀 Schnellstart

### 1. Python & Flask installieren
```bash
pip install flask
```
oder mit der requirements.txt:
```bash
pip install -r requirements.txt
```

### 2. Server starten
```bash
python app.py
```

### 3. Spiel öffnen
Browser öffnen → **http://localhost:5000**

---

## 📁 Projektstruktur

```
BioBreeder3D/
│
├── app.py              ← Python-Server (Flask) – alle API-Routen
├── genetics.py         ← Züchtungs-Algorithmus (DNA, Mutation, Hybride)
├── requirements.txt    ← Python-Abhängigkeiten
│
├── data/
│   ├── animals.json    ← Alle existierenden Tiere (persistent)
│   └── users.json      ← Spieler-Daten (Coins, Blätter, Inventar)
│
├── static/
│   ├── js/
│   │   ├── main.js     ← Three.js 3D-Welt + Game Loop + Touch-Steuerung
│   │   └── api.js      ← Alle fetch()-Aufrufe zur Flask-API
│   └── css/
│       └── style.css   ← Komplettes Spiel-UI
│
└── templates/
    └── index.html      ← Haupt-HTML (wird von Flask gerendert)
```

---

## 🎮 Spielanleitung

| Aktion | Tastatur | Touch |
|--------|----------|-------|
| Laufen | WASD / Pfeiltasten | Linker Joystick |
| Umsehen | Maus (nach Klick) | Rechte Bildschirmhälfte ziehen |
| Springen | Leertaste | ⬆️ Button |
| Aktion (Sammeln/Zähmen) | E | ✋ Button |
| Sprint | Shift | 🏃 Button halten |
| Zücht-Panel | TAB | 🧬 Button |

### Blätter sammeln
- Laufe zu den **leuchtend grünen Kugeln** in der Welt
- Drücke **E** oder **✋** wenn du nah genug bist
- +1 Blatt, +2 Coins

### Tier zähmen
- Laufe zu einem **wilden Tier** (sie wandern durch die Welt)
- Du brauchst **3 Blätter**
- Drücke **E** oder **✋**

### Züchten
- Öffne das **🧬 Züchten-Panel**
- Klicke auf **zwei verschiedene Tiere**
- Klicke **Züchten!**
- Kostet **3 Blätter**

---

## 🧬 Genetik-System

### Farbmischung
```
C_kind = (C_vater + C_mutter) / 2 + Zufallsabweichung(±25)
```
- Blau + Rot = Lila (mit leichter Variation)
- Lila + Grün = Neues Mischfarbe
- Jede Kombination ist einzigartig

### Mutations-Chancen
| Typ | Wahrscheinlichkeit | Effekt |
|-----|--------------------|--------|
| Normal-Mutation | 5% | Komplett neue Zufallsfarbe |
| Super-Mutation | 1% | Extreme Eigenschafts-Veränderung |

### Seltenheits-Stufen
| Stufe | Basis-Chance |
|-------|-------------|
| Gewöhnlich | 55% |
| Ungewöhnlich | 25% |
| Selten | 12% |
| Episch | 6% |
| Legendär | 2% |

> Höhere Eltern-Seltenheit erhöht die Chance auf seltene Kinder!

### Hybride
- Kreuzung verschiedener Arten = **Hybrid**
- Beispiel: Koala + Fuchs = **Fuchs-Koala-Hybrid**
- Hybride haben einzigartige Körperformen
- Unendlich viele Kombinationen möglich

---

## 🌐 API-Übersicht

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/` | GET | Spiel-HTML |
| `/api/tiere` | GET | Alle Tiere laden |
| `/api/tier/<id>` | GET | Einzelnes Tier |
| `/api/zuechten` | POST | Baby züchten |
| `/api/blatt_sammeln` | POST | Blatt +1 |
| `/api/zaehmen` | POST | Wildtier zähmen |
| `/api/markt` | GET | Marktplatz-Angebote |
| `/api/markt/einstellen` | POST | Tier verkaufen |
| `/api/markt/kaufen` | POST | Tier kaufen |
| `/api/stammbaum/<id>` | GET | Stammbaum |
| `/api/wildtier` | POST | Neues Wildtier generieren |

---

## 🔧 Erweiterungen (Ideen)

- **Mehr Spezies** → In `genetics.py` bei `SPECIES` eintragen
- **Biome** → `terrainH()` in `main.js` anpassen
- **Multiplayer** → Flask-SocketIO hinzufügen
- **3D-Modelle** → Three.js GLTFLoader + eigene Assets
- **Speicherung online** → SQLite statt JSON

---

## 📝 Technologie-Stack

- **Python 3.8+** + **Flask** → Server & Genetik-Engine
- **Three.js r128** → 3D-Welt im Browser
- **Vanilla JS** → Game-Loop, Touch-Steuerung, API
- **CSS3** → UI mit Safe-Area-Support für iPhone/Android
- **JSON** → Persistente Datenspeicherung
