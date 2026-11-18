"""Was umfasst eine Zaehlnummer? Pruefung der Lesarten 56 Tage, 56 Wochen, 56 Mondmonate (erkundend).

Aufruf: python3 -I einheit_test.py <aes-json-ordner> <metadaten.jsonl> <ergebnis.json>

E1  Daten mit derselben Zaehlnummer unter demselben Koenig (Datierung der Edition): wie viele Tage liegen sie auseinander?
    Waere die Einheit 56 Tage lang, duerften es nie mehr als 56 sein.
E2  Laenge der Einheit aus zwei Neumonden (Thutmosis III., von aussen): Abstand = 2 L - 81 Tage muss ein Vielfaches des
    Mondmonats sein.
E3  27,32 + 29,53 Tage; Schwebung der beiden Mondmonate; 56 Mondmonate, 56 Wochen, drei Knotenumlaeufe.
"""
import collections
import glob
import json
import os
import re
import sys

src, meta_pfad, ziel = sys.argv[1:4]
GANZ = re.compile(r"^\d+$")
ZEIT = {"216": 0, "856515": 0, "60300": 1, "60290": 1, "154850": 2}
ERSTER = {"550180", "171460", "171450", "171470", "171480"}
SYN, SID = 29.530589, 27.321661
meta = {json.loads(l)["t"]: json.loads(l) for l in open(meta_pfad, encoding="utf-8")}


def zahl(t):
    return int(t["mdc"]) if t.get("pos") == "numeral" and GANZ.match(t.get("mdc") or "") else None


def tag_im_jahr(T, j):
    m = None
    if j + 1 < len(T) and str(T[j].get("lemmaID")) == "93":
        m, j = zahl(T[j + 1]), j + 2
    elif j < len(T) and str(T[j].get("lemmaID")) in ERSTER:
        m, j = 1, j + 1
    if m is None or j >= len(T) or str(T[j].get("lemmaID")) not in ZEIT:
        return None
    z, j = ZEIT[str(T[j].get("lemmaID"))], j + 1
    if j < len(T) and str(T[j].get("lemmaID")) == "854542":
        j += 1
    d = zahl(T[j]) if j < len(T) else None
    return z * 120 + (m - 1) * 30 + d if d and 1 <= m <= 4 and 1 <= d <= 30 else None


grp = collections.defaultdict(set)
for f in sorted(glob.glob(os.path.join(src, "_aes_*.json"))):
    for satz in json.load(open(f, encoding="utf-8")).values():
        T, m = satz["token"], meta.get(satz["text"], {})
        lab = (m.get("datierung") or ["?"])[0]
        if re.search(r"Dyn|Reich|Zeit|Jhdt|\?|Makedonen", lab) or lab == "Sethos II.":   # nur Datierung auf einen Koenig; bei Sethos II.
            continue                                                                       # tragen Abschriften aelterer Texte das Etikett
        for i, t in enumerate(T):
            if str(t.get("lemmaID")) == "850581" and i + 1 < len(T) and zahl(T[i + 1]):
                tg = tag_im_jahr(T, i + 2)
                if tg:
                    grp[(lab, zahl(T[i + 1]))].add(tg)
E = {"E1": []}
print("E1 Gleiche Zaehlnummer, gleicher Koenig: Spanne der Tage im Jahr")
for (lab, y), tage in sorted(grp.items(), key=lambda kv: -(max(kv[1]) - min(kv[1]))):
    if len(tage) >= 2:
        sp = max(tage) - min(tage)
        E["E1"].append({"koenig": lab, "jahr": y, "tage": sorted(tage), "spanne": sp})
        print(f"   {lab:26s} Jahr {y:2d}: Tage {sorted(tage)} -> Spanne {sp}")
n = len(E["E1"])
print(f"   {n} Faelle; Spanne ueber 56 Tage: {sum(e['spanne'] > 56 for e in E['E1'])}, ueber 30 Tage: {sum(e['spanne'] > 30 for e in E['E1'])}, groesste {max(e['spanne'] for e in E['E1'])}")
print("\nE2 Laenge der Zaehleinheit aus zwei Neumonden (Jahr 23 Tag 261, Jahr 24 Tag 180, Jahreswechsel am Tag 244)")
E["E2"] = {}
for name, L in (("365 Tage", 365.0), ("360 Tage", 360.0), ("12 Mondmonate", 12 * SYN), ("56 Wochen", 392.0), ("56 Mondmonate", 56 * SYN)):
    a = 2 * L - 81
    k = a / SYN
    E["E2"][name] = {"abstand": a, "monate": k, "fehler_tage": (k - round(k)) * SYN}
    print(f"   Einheit {name:14s}: Abstand {a:7.1f} Tage = {k:6.2f} Mondmonate, {abs(k - round(k)) * SYN:4.1f} Tage neben dem naechsten Neumond")
print("   Einheit 56 Tage: Tag 261 und Tag 180 gaebe es in ihr nicht")
print("\nE3 Mondzahlen")
schweb = 1 / (1 / SID - 1 / SYN)
print(f"   siderischer + synodischer Monat = {SID + SYN:.2f} Tage | Schwebung 1/(1/{SID:.2f} - 1/{SYN:.2f}) = {schweb:.2f} Tage | "
      f"56 synodische Monate = {56*SYN:.0f} Tage = {56*SYN/365.2422:.2f} Jahre | 56 Wochen = 392 Tage | 3 x 18,61 Jahre = {3*18.61:.2f} Jahre")
E["E3"] = {"summe": SID + SYN, "schwebung": schweb, "56_monate_jahre": 56 * SYN / 365.2422, "drei_knoten": 3 * 18.61}
json.dump(E, open(ziel, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
