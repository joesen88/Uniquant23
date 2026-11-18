"""Gegenprobe zur Halbwertszeit.

Aufruf: python3 -I halbwertszeit_gegenprobe.py <zeit_schicht.jsonl.gz>

  1  Rueckgewinnung M2: kuenstliche Ueberlieferung mit bekannter Verlustrate; findet das Verfahren sie wieder?
  2  Rueckgewinnung M1: kuenstliche Paare mit bekanntem Zerfall und vielen Nullen.
  3  Ausrichtung: difflib-Mass gegen die laengste gemeinsame Teilfolge (obere Schranke) an echten Totenbuch-Paaren.
  4  Ueberlappung: Matrix gegen direkten Mengenschnitt an 300 Zufallspaaren.
  5  Verteilung der Uebereinstimmung im Totenbuch: gewichtetes Mittel, Median, Quartile.
"""
import collections
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import halbwertszeit as hw  # noqa: E402

rng = np.random.default_rng(424242)

print("1  Rueckgewinnung M2 (Abschreibtreue), 150 Werke, 12 Handschriften, 12 % unabhaengige Abweichung je Abschrift")
daten = np.array([-1413.0] * 4 + [-1393.0] * 2 + [-1370.0] * 2 + [-969.0] * 2 + [-182.0] * 2)
p_vok = 1 / np.arange(1, 2001)
p_vok /= p_vok.sum()
for nu in (0.0, 0.0001, 0.0005, 0.002):
    X, Y, Wt = [], [], []
    for _ in range(150):
        n = int(rng.integers(80, 400))
        stand = rng.choice(2000, n, p=p_vok) + 1
        zuletzt, zeugen = daten[0], []
        for h in np.argsort(daten, kind="stable"):
            aendern = rng.random(n) < 1 - math.exp(-nu * (daten[h] - zuletzt))
            stand = np.where(aendern, rng.choice(2000, n, p=p_vok) + 1, stand)
            zuletzt = daten[h]
            if rng.random() < 0.5:
                kopie = np.where(rng.random(n) < 0.12, rng.choice(2000, n, p=p_vok) + 1, stand).tolist()
                for k in np.flatnonzero(rng.random(n) < 0.03):
                    kopie[k] = -int(rng.integers(1, 10 ** 9))
                zeugen.append((h, kopie))
        for i in range(len(zeugen)):
            for j in range(i + 1, len(zeugen)):
                r = hw.ausrichten(zeugen[i][1], zeugen[j][1])
                if r is None or r[0] < 15 or sum(r) < 30:
                    continue
                X.append(abs(daten[zeugen[i][0]] - daten[zeugen[j][0]]))
                Y.append(r[0] / sum(r))
                Wt.append(sum(r))
    lam, A = hw.anpassen(X, Y, Wt)
    print(f"   wahre Rate {nu:.4f}/Jahr (Normtreue {math.exp(-100 * nu):.2%}) -> geschaetzt {lam:.5f} ({math.exp(-100 * lam):.2%}), "
          f"gleichzeitig {A:.1%} (erwartet etwa {0.88 ** 2:.1%}), Paare {len(X)}")

print("\n2  Rueckgewinnung M1 (Zerfall mit Hintergrund, 90 % Nullen), 10000 Paare")
for lam0 in (0.0005, 0.005, 0.012):
    x = np.concatenate([rng.uniform(0, 60, 3000), rng.uniform(300, 1300, 7000)])
    mittel = 0.0001 + 0.01 * np.exp(-lam0 * x)
    y = (rng.random(len(x)) < 0.1) * rng.exponential(mittel / 0.1)
    lam, A = hw.anpassen(x, y, b=0.0001)
    print(f"   wahre Rate {lam0:.4f} -> geschaetzt {lam:.4f}; Niveau {A + 0.0001:.4%} (wahr 1.0100%)")

texte = hw.lade(sys.argv[1])

print("\n3  Ausrichtung an echten Totenbuch-Paaren (Sprueche bis 800 Woerter)")


def lcs(a, b):
    vor = [0] * (len(b) + 1)
    for x in a:
        akt = [0]
        for j, y in enumerate(b):
            akt.append(vor[j] + 1 if x == y else max(vor[j + 1], akt[j]))
        vor = akt
    return vor[-1]


import difflib  # noqa: E402

werke = collections.defaultdict(list)
for t in texte:
    if t["c"] == "tb" and 30 <= len(t["tok"]) <= 800:
        werke[hw.titel(t["titel"])].append(t)
code, zaehler, gefunden, optimal = {}, 0, [], []
for w, ts in sorted(werke.items()):
    for i in range(len(ts)):
        for j in range(i + 1, len(ts)):
            if ts[i]["hs"] == ts[j]["hs"] or len(gefunden) >= 150:
                continue
            folgen = []
            for t in (ts[i], ts[j]):
                f = []
                for l, e in t["tok"]:
                    if e in (0, 1):
                        f.append(code.setdefault(l, len(code) + 1))
                    else:
                        zaehler -= 1
                        f.append(zaehler)
                folgen.append(f)
            a, b = folgen
            m = sum(o[2] - o[1] for o in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if o[0] == "equal")
            gefunden.append(m)
            optimal.append(lcs(a, b))
gefunden, optimal = np.array(gefunden, float), np.array(optimal, float)
print(f"   Paare {len(gefunden)}: difflib findet {gefunden.sum() / optimal.sum():.1%} der gleichen Stellen, die die laengste "
      f"gemeinsame Teilfolge (bestmoegliche Ausrichtung) findet; je Paar mindestens {(gefunden / optimal).min():.1%}")

print("\n4  Ueberlappung gegen direkten Mengenschnitt")
ch, _ = hw.abschnitte(texte, 1000, False)
S = hw.ueberlappung(ch)
abw = 0.0
for _ in range(300):
    i, j = (int(v) for v in rng.integers(0, len(ch), 2))
    if i == j:
        continue
    d = len(ch[i]["gram"] & ch[j]["gram"]) / max(1, min(len(ch[i]["gram"]), len(ch[j]["gram"])))
    abw = max(abw, abs(d - S[i, j]))
print(f"   groesste Abweichung {abw:.2e} bei {len(ch)} Abschnitten")

print("\n5  Totenbuch: Verteilung der Uebereinstimmung je Spruchpaar")
P = [p for p in hw.m2_paare(texte, False) if p["c"] == "tb"]
datum = {}
for t in texte:
    e = datum.setdefault(t["hs"], [t["nb"], t["na"]])
    e[0], e[1] = min(e[0], t["nb"]), max(e[1], t["na"])
for name, lo, hi in (("0-50 Jahre", 0, 50), ("300-1000 Jahre", 300, 1000), ("ueber 1000 Jahre", 1000, 1e9)):
    sel = [p for p in P if lo <= abs(sum(datum[p["a"]]) / 2 - sum(datum[p["b"]]) / 2) < hi]
    a = np.array([p["M"] / (p["M"] + p["D"]) for p in sel])
    w = np.array([p["M"] + p["D"] for p in sel], float)
    print(f"   {name:17s} Paare {len(sel):3d} | gewichtetes Mittel {(a * w).sum() / w.sum():.1%} | Median {np.median(a):.1%} | "
          f"Quartile {np.percentile(a, 25):.1%}-{np.percentile(a, 75):.1%} | Anteil der Paare ueber 90 %: {(a > 0.9).mean():.0%}")
