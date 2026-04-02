"""
fix_json.py – Repariert kaputte animals.json
Einfach ausführen: python fix_json.py
"""
import json, os

DATA = os.path.join(os.path.dirname(__file__), "data")
PFAD = os.path.join(DATA, "animals.json")

print("🔧 Lese animals.json ...")

with open(PFAD, "r", encoding="utf-8") as f:
    raw = f.read().strip()

# Manchmal werden zwei JSON-Arrays hintereinander: [...][...]
# Wir parsen alle gültigen Objekte nacheinander raus
tiere = []
decoder = json.JSONDecoder()
pos = 0
while pos < len(raw):
    try:
        obj, end_idx = decoder.raw_decode(raw, pos)
        if isinstance(obj, list):
            tiere.extend(obj)
        elif isinstance(obj, dict):
            tiere.append(obj)
        pos += end_idx
        # Whitespace überspringen
        while pos < len(raw) and raw[pos] in ' \t\r\n':
            pos += 1
    except json.JSONDecodeError:
        break

# Duplikate nach ID entfernen
seen = {}
for t in tiere:
    if isinstance(t, dict) and "id" in t:
        seen[t["id"]] = t
sauber = list(seen.values())

print(f"✅ {len(sauber)} Tiere gefunden und dedupliziert")

# Backup anlegen
backup = PFAD + ".backup"
with open(backup, "w", encoding="utf-8") as f:
    f.write(raw)
print(f"💾 Backup gespeichert als: animals.json.backup")

# Sauber zurückschreiben
with open(PFAD, "w", encoding="utf-8") as f:
    json.dump(sauber, f, indent=2, ensure_ascii=False)

print(f"✅ Fertig! animals.json repariert.")
print("👉 Jetzt: python app.py")
