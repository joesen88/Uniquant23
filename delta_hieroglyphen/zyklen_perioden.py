"""Bestimmte Zyklen gegen die Jahreszaehlung: Sothis, Mond, Sedfest, Viehzaehlung.

Aufruf: python3 -I zyklen_perioden.py <aes-json-ordner> <metadaten.jsonl> <ergebnis.json>

Je Zyklus stehen Laenge, Startmarke und Vorhersage vor der Auszaehlung fest (unten in ZYKLEN). Erkundend: welche Belege
das Korpus enthaelt, war aus einer Sichtung bekannt.
Zwei Arten von Vorhersage:
  (a) Der Koenigsname ist der Name des Zyklus  ->  die Zaehlung unter einem Namen endet spaetestens bei der Zykluslaenge.
  (b) Der Zyklus laeuft als eigene Uhr neben der Zaehlung  ->  zwei Marken des Zyklus liegen so weit auseinander, wie
      die Zykluslaenge es verlangt.
Zahlen von aussen (nicht aus dem Korpus) stehen als Konstanten mit Quelle im Abschnitt AUSSEN.
"""
import collections
import glob
import json
import math
import os
import re
import sys

import numpy as np
from scipy.stats import binom

src, meta_pfad, ziel = sys.argv[1:4]
ZYKLEN = {
    "Sothis": {"laenge": "1460 Jahre; der Aufgang des Sirius wandert im Kalender um 1 Tag je 4 Jahre", "start": "Aufgang am Neujahrstag (I Achet 1)",
               "a": "Zaehlung bis 1460", "b": "zwei datierte Aufgaenge: Jahre = 4 x Tage Verschiebung"},
    "Mond": {"laenge": "29,53 Tage; 309 Monate = 25 Kalenderjahre", "start": "Neumond", "a": "Zaehlung bis 25",
             "b": "zwei Neumonde unter einem Namen: Abstand in Tagen = ganze Zahl x 29,53"},
    "Sedfest": {"laenge": "30 Jahre, danach alle 3", "start": "Amtsantritt", "a": "Zaehlung bis 30", "b": "erstes Fest im Jahr 30"},
    "Viehzaehlung": {"laenge": "2 Jahre", "start": "erste Zaehlung", "a": "-", "b": "'Jahr nach dem n-ten Mal' so haeufig wie 'Jahr des n-ten Mals'"},
}
AUSSEN = {
    "c14": {"quelle": "Bronk Ramsey u. a. 2010, Science 328, Tabelle 1 (Amtsantritt, 68 %)", "Sesostris III.": (1884, 1860), "Amenophis I.": (1541, 1527),
            "Ramses I.": (1308, 1297), "Ramses II.": (1292, 1281)},
    "ebers": {"quelle": "Berechnung des Aufgangs fuer Jahr 9 Amenophis' I.: Theben 1517 v. Chr., Memphis 1537 v. Chr."},
    "thutmosis": {"quelle": "Urk. IV 657 und 836: Neumond Jahr 23, I Schemu 21 und Jahr 24, II Peret 30; Amtsantritt I Schemu 4",
                  "t1": (23, 9, 21), "t2": (24, 6, 30), "antritt": (9, 4)},
}
GANZ = re.compile(r"^\d+$")
JAHR, NACH = "850581", ("850582", "850641")
ZEIT = {"216": 0, "856515": 0, "60300": 1, "60290": 1, "154850": 2}
SYN = 29.530589
MONDFEST = {"850569": "Neumondtag (psḏn.tjw)", "99": "zweiter Mondtag (ꜣbd.w)", "852477": "Monatsanfang (tp-ꜣbd)",
            "852387": "15. Mondtag (tp-smd.t)", "450445": "Halbmonatsfest (Tp.j-smd.t)"}


def zahl(t):
    return int(t["mdc"]) if t.get("pos") == "numeral" and GANZ.match(t.get("mdc") or "") else None


def tag_im_jahr(T, i):
    """Monat + Zahl + Jahreszeit + Tag + Zahl ab Position i -> laufender Tag 1..360, sonst None."""
    if i + 4 < len(T) and str(T[i].get("lemmaID")) == "93" and str(T[i + 2].get("lemmaID")) in ZEIT and str(T[i + 3].get("lemmaID")) == "854542":
        m, d = zahl(T[i + 1]), zahl(T[i + 4])
        if m and d:
            return ZEIT[str(T[i + 2].get("lemmaID"))] * 120 + (m - 1) * 30 + d
    return None


meta = {}
for l in open(meta_pfad, encoding="utf-8"):
    m = json.loads(l)
    meta[m["t"]] = m
jahre = {}                                # (titel, jahr, tag) -> (jahr, koenig, korpus)
thron_jahr = collections.defaultdict(set)
sothis, ewig, sed_texte, zaehl = [], [], collections.defaultdict(lambda: {"sed": [], "jahre": []}), []
mondfeste = collections.Counter()
info = {}
for f in sorted(glob.glob(os.path.join(src, "_aes_*.json"))):
    korpus = os.path.basename(f)[5:-5]
    for satz in json.load(open(f, encoding="utf-8")).values():
        T, text = satz["token"], satz["text"]
        m = meta.get(text, {})
        lf = [(t.get("lemma_form") or "") for t in T]
        for t in T:
            if t.get("name") == "kings_name" and t.get("lemmaID"):
                info.setdefault(t["lemmaID"], (t.get("lemma_form") or "", t.get("cotext_translation") or ""))
            if str(t.get("lemmaID")) in MONDFEST:
                mondfeste[MONDFEST[str(t.get("lemmaID"))]] += 1
        for i, t in enumerate(T):
            lid = str(t.get("lemmaID"))
            if lid == JAHR or lid in NACH:
                y = zahl(T[i + 1]) if i + 1 < len(T) else None
                alt = m.get("nb") is not None and m["nb"] < -2100
                if alt:
                    zaehl.append((korpus, "nach" if lid in NACH else "mal", y, text))
                sed_texte[text]["jahre"].append(("nach " if lid in NACH else "") + str(y))
                if lid == JAHR and y:
                    tg = tag_im_jahr(T, i + 2)
                    kn = [x["lemmaID"] for x in T[i:i + 25] if x.get("name") == "kings_name" and x.get("lemmaID")]
                    th = [k for k in kn if (info.get(k) or ("", ""))[1].startswith("[Thron")]
                    koenig = (m.get("datierung") or [None])[0]
                    jahre.setdefault((m.get("titel") or text, y, tg), (y, koenig, korpus, th[0] if th else None))
                    md = [x.get("mdc") for x in T[i:i + 8]]
                    if "HA,t" in md and "nHH" in md:
                        ewig.append((korpus, y, koenig, " ".join((x.get("mdc") or "?") for x in T[i:i + 9])))
            if lf[i] in ("pr.t-spd.t", "Spd.t") and any(str(x.get("lemmaID")) == "93" for x in T):
                for j in range(len(T)):
                    tg = tag_im_jahr(T, j)
                    if tg:
                        sothis.append({"korpus": korpus, "titel": m.get("titel"), "hs": m.get("hs"), "nb": m.get("nb"), "na": m.get("na"),
                                       "tag": tg, "satz": " ".join((x.get("mdc") or "?") for x in T)[:160], "text": text})
        ms = " ".join((t.get("mdc") or "?") for t in T)
        if "HAb-sd" in ms and re.search(r"zp[ -]tp", ms):
            sed_texte[text]["sed"].append(ms[:60])
for s in sothis:
    s["jahre_im_text"] = sed_texte[s["text"]]["jahre"]

E = {"zyklen": ZYKLEN, "aussen": AUSSEN}
# ---------- 1 Obergrenzen ----------
J = sorted(jahre.values(), key=lambda j: (j[0], str(j[1])))
y = np.array([j[0] for j in J])
print(f"1 Jahreszahlen, je Werk und Datum einmal gezaehlt: {len(y)} | hoechste {y.max()} | Mittel {y.mean():.1f} | Median {np.median(y):.0f}")
E["jahre"] = {"n": int(len(y)), "max": int(y.max()), "mittel": float(y.mean()), "grenzen": {}}
for name, L in (("Sothis-Vierjahr", 4), ("Mond (25 Jahre)", 25), ("Sedfest (30 Jahre)", 30), ("Sothis (1460 Jahre)", 1460)):
    ueber = [j for j in J if j[0] > L]
    koenige = sorted({str(j[1]) for j in ueber if j[1]})
    print(f"   Obergrenze {name:20s}: {len(ueber):3d} Angaben darueber ({100*len(ueber)/len(y):.0f} %)")
    E["jahre"]["grenzen"][name] = {"L": L, "darueber": len(ueber), "koenige": koenige, "jahre": sorted(j[0] for j in ueber)[:60]}
# Zerfall gegen Gleichverteilung
q = 1 - 1 / y.mean()
ll_zerfall = float(np.sum(np.log(1 - q) + (y - 1) * np.log(q)))
ll_gleich = float(-len(y) * np.log(y.max()))
print(f"   Verteilung: gleichmaessig ueber 1..{y.max()} (ein fester Zyklus) log-Likelihood {ll_gleich:.0f}; Zerfall mit konstanter Endrate "
      f"(geometrisch, mittlere Dauer {y.mean():.1f} Jahre, Halbwertszeit {math.log(2)/-math.log(q):.1f} Jahre) {ll_zerfall:.0f}; Unterschied {ll_zerfall-ll_gleich:.0f}")
klassen = [(1, 5), (6, 10), (11, 15), (16, 20), (21, 25), (26, 30), (31, 35), (36, 40), (41, 45), (46, 50), (51, 56)]
kz = [int(((y >= a) & (y <= b)).sum()) for a, b in klassen]
print("   Angaben je Fuenfjahresklasse: " + ", ".join(f"{a}-{b}: {n}" for (a, b), n in zip(klassen, kz)))
E["jahre"]["klassen"] = {f"{a}-{b}": n for (a, b), n in zip(klassen, kz)}
print("   Anteil der Angaben mit Jahr >= x: " + ", ".join(f"{x}: {100*(y >= x).mean():.0f} %" for x in (1, 5, 10, 20, 30, 40, 50)))
E["jahre"].update({"ll_gleich": ll_gleich, "ll_zerfall": ll_zerfall, "halbwertszeit": math.log(2) / -math.log(q),
                   "ueberleben": {x: float((y >= x).mean()) for x in (1, 5, 10, 20, 30, 40, 50)}})

# ---------- 2 Sothis ----------
print("\n2 Sothis")
sd = {}
for s in sothis:
    sd.setdefault(s["hs"], s)
for s in sd.values():
    print(f"   Aufgang am Tag {s['tag']} des Jahres | {s['hs']} ({s['korpus']}), Edition {s['nb']}..{s['na']} | Jahresangaben im Text: {s['jahre_im_text']} | {s['satz'][:110]}")
tage = sorted(s["tag"] for s in sd.values())
if len(tage) == 2:
    dv = tage[1] - tage[0]
    bis_neujahr = 366 - tage[1]
    c = AUSSEN["c14"]
    mitte = lambda r: (r[0] + r[1]) / 2
    halb = lambda r: (r[0] - r[1]) / 2
    c14 = (mitte(c["Sesostris III."]) - 6) - (mitte(c["Amenophis I."]) - 8)
    c14_s = math.hypot(halb(c["Sesostris III."]), halb(c["Amenophis I."]))
    print(f"   Verschiebung {dv} Tage -> {4*dv} Jahre (gleicher Beobachtungsort; {4*dv-3} bis {4*dv+3}); mit rund 3,5 Tagen Unterschied zwischen "
          f"Illahun und Theben {4*(dv+3.5):.0f} Jahre")
    print(f"   Radiokarbon, unabhaengig von beiden Daten: Jahr 7 Sesostris' III. bis Jahr 9 Amenophis' I. = {c14:.0f} Jahre, +/- {c14_s:.0f}")
    print(f"   Startmarke: vom Ebers-Datum bis zum Aufgang am Neujahrstag fehlen {bis_neujahr} Tage -> {4*bis_neujahr} Jahre nach Jahr 9 "
          f"({4*bis_neujahr-3} bis {4*bis_neujahr+3}), also {4*bis_neujahr+8} Jahre nach dem Amtsantritt Amenophis' I.")
    a1 = c["Amenophis I."]
    print(f"      Radiokarbon: Amtsantritt Amenophis I. {a1[0]}-{a1[1]} -> Marke {a1[0]-4*bis_neujahr-8} bis {a1[1]-4*bis_neujahr-8} v. Chr.; "
          f"Amtsantritt Ramses I. {c['Ramses I.'][0]}-{c['Ramses I.'][1]}, Ramses II. {c['Ramses II.'][0]}-{c['Ramses II.'][1]} (Sethos I. dazwischen)")
    print(f"      Chronologie der Edition: Jahr 9 = 1517 v. Chr. (Theben) -> Marke {1517-4*bis_neujahr} v. Chr.; Sethos I. laut Edition 1290-1280; "
          f"bei Beobachtung in Memphis (1537) -> {1537-4*bis_neujahr} v. Chr., unter Haremhab (1319-1293)")
    E["sothis"] = {"belege": list(sd.values()), "verschiebung_tage": dv, "jahre": 4 * dv, "jahre_ortsunterschied": 4 * (dv + 3.5), "c14": c14, "c14_s": c14_s,
                   "bis_neujahr_tage": bis_neujahr, "marke_jahre_nach_jahr9": 4 * bis_neujahr}
print(f"   Jahresangaben, eroeffnet mit 'Beginn der Ewigkeit': {[(e[1], e[2]) for e in ewig]}")
E.setdefault("sothis", {})["beginn_der_ewigkeit"] = [list(e) for e in ewig]

# ---------- 3 Mond ----------
print("\n3 Mond")
print(f"   datierte Mondbeobachtungen unter einem Koenigsnamen im Korpus: keine | Mondfeste in Fest- und Opferlisten: "
      + ", ".join(f"{k} {v}" for k, v in mondfeste.most_common()) + f" (zusammen {sum(mondfeste.values())})")
t = AUSSEN["thutmosis"]
tag = lambda mo, d: (mo - 1) * 30 + d
d1, d2, an = tag(*t["t1"][1:]), tag(*t["t2"][1:]), tag(*t["antritt"])
ziv = lambda j, tg: (j - 1) + (1 if tg < an else 0)           # Kalenderjahr-Index, wenn das Zaehljahr am Antrittstag wechselt
abst_antritt = (ziv(t["t2"][0], d2) - ziv(t["t1"][0], d1)) * 365 + d2 - d1
abst_neujahr = (t["t2"][0] - t["t1"][0]) * 365 + d2 - d1
print(f"   von aussen (Thutmosis III.): zwei Neumonde, Jahr 23 Tag {d1} und Jahr 24 Tag {d2}")
print(f"      Jahreswechsel am Antrittstag (Tag {an}): Abstand {abst_antritt} Tage = {abst_antritt/SYN:.2f} Mondmonate")
print(f"      Jahreswechsel am Neujahrstag:           Abstand {abst_neujahr} Tage = {abst_neujahr/SYN:.2f} Mondmonate")
E["mond"] = {"mondfeste": {k: int(v) for k, v in mondfeste.items()}, "abstand_antritt": abst_antritt, "monate_antritt": abst_antritt / SYN,
             "abstand_neujahr": abst_neujahr, "monate_neujahr": abst_neujahr / SYN}

# ---------- 4 Sedfest ----------
print("\n4 Sedfest")
erst = [(meta.get(tx, {}).get("titel"), meta.get(tx, {}).get("nb"), (meta.get(tx, {}).get("datierung") or [None])[0], v["jahre"], v["sed"][0])
        for tx, v in sed_texte.items() if v["sed"]]
for e in erst:
    print(f"   'erstes Mal des Sedfestes': {str(e[0])[:26]:26s} {e[1]} {str(e[2])[:14]:14s} Jahresangabe im Text: {e[3]}")
print("   Angaben ueber Jahr 25 (Jahr | Werk | Datierung der Handschrift laut Edition | Thronname in der Formel):")
hoch = []
for (titel, jahr, tg), j in sorted(jahre.items(), key=lambda kv: kv[1][0]):
    if jahr > 25:
        hoch.append({"jahr": jahr, "werk": str(titel)[:60], "edition": j[1], "thronname": info[j[3]][0] if j[3] else None})
        print(f"      {jahr:2d} | {str(titel)[:50]:50s} | {str(j[1])[:26]:26s} | {info[j[3]][0] if j[3] else '-'}")
E["sed"] = {"erstes_mal": [list(e) for e in erst], "ueber25": hoch}

# ---------- 5 Viehzaehlung ----------
print("\n5 Viehzaehlung (Texte vor 2100 v. Chr.)")
n_mal = sum(z[1] == "mal" for z in zaehl)
n_nach = sum(z[1] == "nach" for z in zaehl)
p = float(binom.cdf(n_nach, n_mal + n_nach, 0.5))
hoch = sorted({z[2] for z in zaehl if z[2]}, reverse=True)[:6]
print(f"   'Jahr des n-ten Mals': {n_mal} | 'Jahr nach dem n-ten Mal': {n_nach} ({100*n_nach/(n_mal+n_nach):.0f} %) | bei strenger Zweijahreszaehlung "
      f"waeren 50 % zu erwarten, p = {p:.1e} | hoechste Zahlen: {hoch}")
E["viehzaehlung"] = {"mal": n_mal, "nach": n_nach, "p": p, "hoechste": hoch}
json.dump(E, open(ziel, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
