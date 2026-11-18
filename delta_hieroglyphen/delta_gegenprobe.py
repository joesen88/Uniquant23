"""Gegenprobe: Kernzahlen des Delta-Tests mit eigenstaendigem Code nachrechnen.

Aufruf: python3 -I delta_gegenprobe.py <tokens.jsonl.gz>

Nutzt nichts aus delta_test.py. Abschnittsbildung, Zeichenzerlegung, 5-Gramm-
Ueberlappung (direkter Mengenschnitt je Paar) und Distanz (Schleife ueber Zeilen)
sind neu geschrieben. Erwartet werden dieselben Trefferzahlen.
"""
import gzip
import json
import math
import re
import sys
from collections import Counter, defaultdict

import numpy as np

L, N_MERK, TAU, MINI = 1000, 150, 0.05, 5
CODE = re.compile(r"(?:Aa|Ff|NL|NU|[A-Z])[0-9]+")


def zerlege(h):
    res = []
    for teil in h.split("-"):
        teil = teil.replace("_", "")
        if teil == "":
            continue
        if re.fullmatch(r"[0-9]+", teil):
            v = int(teil)
            if v < 10:
                res.extend(["Z1"] * v)
            elif v < 100 and v % 10 == 0:
                res.extend(["V20"] * (v // 10))
            elif v < 1000 and v % 100 == 0:
                res.extend(["V1"] * (v // 100))
            continue
        m = re.fullmatch(r"US[0-9]+(" + CODE.pattern + r")[A-Za-z]*", teil)
        if m:
            res.append(m.group(1))
            continue
        m = re.fullmatch(r"(" + CODE.pattern + r")[A-Za-z]*", teil)
        if m:
            res.append(m.group(1))
    return res


def baue(pfad, mit_zeichen):
    stuecke, rest = [], defaultdict(list)
    for zeile in gzip.open(pfad, "rt", encoding="utf-8"):
        t = json.loads(zeile)
        woerter = []
        for lid, h in t["tok"]:
            if mit_zeichen:
                z = zerlege(h) if h else []
                if not z:
                    continue
                woerter.append((lid, z))
            else:
                woerter.append((lid, []))
        voll = len(woerter) // L
        for i in range(voll):
            stuecke.append({"k": t["c"], "t": {t["t"]}, "b": {t["o"]}, "w": woerter[i * L:i * L + L], "rein": t["t"]})
        for w in woerter[voll * L:]:
            rest[t["c"]].append((t["t"], t["o"], w))
    for k, liste in rest.items():
        for i in range(0, len(liste) - L + 1, L):
            teil = liste[i:i + L]
            stuecke.append({"k": k, "t": {a for a, _, _ in teil}, "b": {b for _, b, _ in teil},
                            "w": [w for _, _, w in teil], "rein": None})
    zahl = Counter(s["k"] for s in stuecke)
    return [s for s in stuecke if zahl[s["k"]] >= MINI]


def pruefe(name, stuecke, ebene):
    n = len(stuecke)
    folgen = [[w[0] for w in s["w"]] if ebene == "wort" else [z for w in s["w"] for z in w[1]] for s in stuecke]
    gesamt, anteil = Counter(), Counter()
    for f in folgen:
        gesamt.update(f)
        for m, c in Counter(f).items():
            anteil[m] += c / len(f)
    # Rangfolge der Merkmale: 'anteil' = Summe der relativen Haeufigkeiten je Abschnitt (wie delta_test.py),
    # 'anzahl' = Gesamtzahl im Korpus. Bei gleich langen Abschnitten (Wortebene) ist beides dasselbe.
    rang = anteil if RANG == "anteil" else gesamt
    erste = {m: i for i, (m, _) in enumerate(gesamt.most_common())}
    merk = sorted(rang, key=lambda m: (-rang[m], erste[m]))[:N_MERK]
    X = np.array([[Counter(f)[m] / len(f) for m in merk] for f in folgen])
    mittel = X.sum(axis=0) / n
    streu = np.sqrt(((X - mittel) ** 2).sum(axis=0) / (n - 1))
    Zs = (X - mittel) / streu
    gramme = []
    for s in stuecke:
        lem = [w[0] for w in s["w"]]
        gramme.append({tuple(lem[i:i + 5]) for i in range(len(lem) - 4)})
    t_gatt = t_text = t_fremd = n_text = n_fremd = n_gatt = 0
    reine = Counter(s["rein"] for s in stuecke if s["rein"])
    for i, s in enumerate(stuecke):
        d = np.abs(Zs - Zs[i]).sum(axis=1) / len(merk)
        d[i] = math.inf
        # bekannte Antwort: derselbe Text
        if s["rein"] and reine[s["rein"]] >= 2:
            n_text += 1
            t_text += bool(stuecke[int(d.argmin())]["t"] & s["t"])
        ok = np.array([j != i and not (stuecke[j]["t"] & s["t"])
                       and len(gramme[i] & gramme[j]) / min(len(gramme[i]), len(gramme[j])) <= TAU for j in range(n)])
        gleich = np.array([stuecke[j]["k"] == s["k"] for j in range(n)])
        if (ok & gleich).any():
            n_gatt += 1
            j = int(np.where(ok, d, math.inf).argmin())
            t_gatt += stuecke[j]["k"] == s["k"]
        fremd = ok & np.array([not (stuecke[j]["b"] & s["b"]) for j in range(n)])
        if (fremd & gleich).any():
            n_fremd += 1
            j = int(np.where(fremd, d, math.inf).argmin())
            t_fremd += stuecke[j]["k"] == s["k"]
    print(f"{name}: {n} Abschnitte | gleicher Text {t_text}/{n_text} = {t_text / n_text:.1%} | "
          f"Teilkorpus streng {t_gatt}/{n_gatt} = {t_gatt / n_gatt:.1%} | fremde Bearbeiter {t_fremd}/{n_fremd} = {t_fremd / n_fremd:.1%}")


pfad = sys.argv[1]
RANG = sys.argv[2] if len(sys.argv) > 2 else "anteil"
print("Rangfolge der Merkmale nach:", RANG)
pruefe("Wortebene", baue(pfad, False), "wort")
z = baue(pfad, True)
pruefe("Zeichenebene", z, "zeichen")
pruefe("Wortebene gepaart", z, "wort")
