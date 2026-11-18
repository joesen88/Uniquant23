"""Halbwertszeit des Wortlauts: Wie schnell zerfaellt gemeinsamer Wortlaut mit dem Zeitabstand?

Aufruf: python3 -I halbwertszeit.py <zeit_schicht.jsonl.gz> <ergebnis.json>

Das PROTOKOLL wurde festgelegt, nachdem nur die Metadaten (Datierungen, Handschriften, Titel)
gesichtet waren, und bevor ein Zusammenhang zwischen Wortlaut und Zeit gerechnet war.
"""
import collections
import difflib
import gzip
import hashlib
import json
import math
import re
import sys

import numpy as np
from scipy.optimize import minimize_scalar

PROTOKOLL = {
    "daten": "AES-Lemmata; Jahresgrenzen und Handschrift aus AED-TEI. Ausgeschlossen: undatierte Texte "
             "(auch Platzhalter 1..1) und Datierungen, die mehr als 450 Jahre offen lassen",
    "zeit": "Datum einer Handschrift = Mitte ihrer Jahresgrenzen; Unsicherheit gleichverteilt zwischen den Grenzen",
    "ergaenzungen": "ganz ergaenzte Woerter und zerstoerte Stellen zaehlen nie als Uebereinstimmung; "
                    "Sensitivitaet: auch teilweise ergaenzte Woerter ausschliessen",
    "M1": {"name": "gemeinsamer Wortlaut zwischen Abschnitten verschiedener Handschriften",
           "einheit": "Abschnitt aus L = 1000 nutzbaren Woertern, je Textgruppe in Datierungsreihenfolge gebildet; "
                      "gemischte Abschnitte, deren Handschriften mehr als 150 Jahre auseinanderliegen, entfallen, "
                      "ebenso Abschnitte mit weniger als 100 lueckenlosen Fuenfergruppen",
           "mass": "Anteil gemeinsamer Lemma-Fuenfergruppen, bezogen auf den kleineren Abschnitt",
           "hintergrund": "Mittel desselben Masses ueber Abschnittspaare aus verschiedenen Textgruppen",
           "modell": "E[s] = b + A * exp(-lambda * dt), kleinste Quadrate ueber alle Paare ohne gemeinsame Handschrift",
           "aufnahme": "mindestens 12 Abschnitte, 6 Cluster und 100 Jahre Spanne"},
    "M2": {"name": "derselbe Spruch oder dasselbe Werk in zwei Handschriften (Abschreibtreue)",
           "werke": "gleicher Titel in Totenbuch, Pyramidentexten und Literatur",
           "mass": "nach Ausrichtung der Lemma-Folgen: gleiche Stellen / (gleiche + abweichende Stellen) im gemeinsamen "
                   "Bereich; Bloecke, die eine Luecke oder Ergaenzung beruehren, zaehlen nicht mit",
           "bedingung": "Ankerblock von mindestens 4 gleichen Woertern, mindestens 15 gleiche und 30 vergleichbare Stellen",
           "modell": "E[a] = a0 * exp(-mu * dt), gewichtet mit der Zahl vergleichbarer Stellen"},
    "kennzahlen": "Normtreue je Jahrhundert = exp(-100 * Rate); Halbwertszeit = ln 2 / Rate",
    "unsicherheit": "1000 Wiederholungen: Handschriften (M1) bzw. Werke (M2) mit Zuruecklegen gezogen, "
                    "dazu jede Datierung neu zwischen ihren Grenzen gezogen",
    "nullmodell": "Datierungen innerhalb der Textgruppe zwischen den Handschriften vertauscht (1000-mal)",
    "vorhersagen": {"V1": "M1: Normtreue Totenbuch > Literatur > Briefe",
                    "V2": "M2: Normtreue Totenbuch > Literatur",
                    "V3": "M2: Halbwertszeit des Totenbuchs ueber 1000 Jahre",
                    "offen": "Pyramidentexte: nur fuenf Pyramiden ueber 108 Jahre, keine Vorhersage",
                    "dagegen": "Totenbuch nicht ueber der Literatur"},
    "robustheit": {"L": [500, 1000], "nur_ganz_erhaltene_woerter": True, "literatur_gleicher_bearbeiter": True},
    "grenzen_rate": [-0.002, 0.05], "klassen": [0, 50, 150, 300, 600, 1000],
    "seed": 20261113,
}
LAM_MIN, LAM_MAX = PROTOKOLL["grenzen_rate"]
KANTEN = PROTOKOLL["klassen"]
B = 1000
NAMEN = {"tb": "Totenbuch", "bbawpyramidentexte": "Pyramidentexte", "sawlit": "Literatur", "sawmedizin": "Medizin",
         "bbawbriefe": "Briefe", "bbawgrabinschriften": "Grabinschriften", "bbawtotenlit": "Spaete Totenliteratur"}


def lade(pfad):
    out = []
    for z in gzip.open(pfad, "rt", encoding="utf-8"):
        t = json.loads(z)
        if t["nb"] is None or (t["nb"] == 1 and t["na"] == 1) or t["na"] - t["nb"] > 450:
            continue
        out.append(t)
    return out


def anpassen(x, y, w=None, b=0.0):
    """y ~ b + A * exp(-lam * x). A >= 0 in geschlossener Form, lam per Gitter und Feinsuche."""
    x = np.asarray(x, float)
    y = np.asarray(y, float) - b
    w = np.ones_like(x) if w is None else np.asarray(w, float)

    def teile(lam):
        e = np.exp(-lam * x)
        A = max(0.0, float((w * y * e).sum() / (w * e * e).sum()))
        return float((w * (y - A * e) ** 2).sum()), A

    gitter = np.concatenate([np.linspace(LAM_MIN, 0, 9)[:-1], [0.0], np.geomspace(1e-5, LAM_MAX, 40)])
    werte = [teile(l)[0] for l in gitter]
    k = int(np.argmin(werte))
    lo, hi = gitter[max(k - 1, 0)], gitter[min(k + 1, len(gitter) - 1)]
    r = minimize_scalar(lambda l: teile(l)[0], bounds=(lo, hi), method="bounded", options={"xatol": 1e-8})
    lam = float(r.x) if r.fun <= werte[k] else float(gitter[k])
    return lam, teile(lam)[1]


def kennzahlen(lam):
    return {"rate_je_jahr": lam, "normtreue_je_jahrhundert": math.exp(-100 * lam),
            "halbwertszeit": (math.log(2) / lam) if lam > 0 else None}


def klassen(x, y, w=None):
    x, y = np.asarray(x, float), np.asarray(y, float)
    w = np.ones_like(x) if w is None else np.asarray(w, float)
    out = []
    for a, b in zip(KANTEN, KANTEN[1:] + [float("inf")]):
        m = (x >= a) & (x < b)
        out.append({"von": a, "bis": None if b == float("inf") else b, "paare": int(m.sum()),
                    "mittel": float((w[m] * y[m]).sum() / w[m].sum()) if m.any() else None,
                    "dt_mittel": float(x[m].mean()) if m.any() else None})
    return out


def quantile(v):
    v = np.asarray(v, float)
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]


# ---------------------------------------------------------------- M1
def abschnitte(texte, L, streng):
    nutz = (0,) if streng else (0, 1)
    gruppen = collections.OrderedDict()
    for t in texte:
        gruppen.setdefault(t["c"], collections.OrderedDict()).setdefault(t["hs"], []).append(t)
    out, datum = [], {}
    for c, hss in gruppen.items():
        strom = {}
        for hs, ts in hss.items():
            datum[hs] = (min(t["nb"] for t in ts), max(t["na"] for t in ts))
            s = []
            for t in ts:
                s.extend((lid if e in nutz else None) for lid, e in t["tok"])
                s.append(None)
            strom[hs] = s
        pool = []
        for hs in sorted(strom, key=lambda h: (sum(datum[h]) / 2, h)):
            akt, n = [], 0
            for x in strom[hs]:
                akt.append(x)
                if x is not None:
                    n += 1
                    if n == L:
                        out.append({"c": c, "hs": {hs: L}, "cluster": "H:" + hs, "strom": akt})
                        akt, n = [], 0
            pool.extend((hs, x) for x in akt)
        akt, n, k = [], 0, 0
        for hs, x in pool:
            akt.append((hs, x))
            if x is not None:
                n += 1
                if n == L:
                    out.append({"c": c, "hs": dict(collections.Counter(h for h, v in akt if v is not None)),
                                "cluster": f"P:{c}:{k}", "strom": [v for _, v in akt]})
                    akt, n, k = [], 0, k + 1
    for ch in out:
        s = ch.pop("strom")
        ch["gram"] = {tuple(s[j:j + 5]) for j in range(len(s) - 4) if None not in s[j:j + 5]}
        mitten = [sum(datum[h]) / 2 for h in ch["hs"]]
        ch["spanne"] = max(mitten) - min(mitten)
    return out, datum


def ueberlappung(chunks):
    N = len(chunks)
    inv = collections.defaultdict(list)
    g = np.array([len(c["gram"]) for c in chunks], float)
    for i, c in enumerate(chunks):
        for x in c["gram"]:
            inv[x].append(i)
    S = np.zeros((N, N))
    for ids in inv.values():
        if len(ids) > 1:
            a = np.asarray(ids)
            S[np.ix_(a, a)] += 1
    np.fill_diagonal(S, 0)
    return S / np.minimum.outer(np.maximum(g, 1), np.maximum(g, 1))


def m1(texte, L, streng, rng, voll=True):
    ch, datum = abschnitte(texte, L, streng)
    ch = [c for c in ch if c["spanne"] <= 150 and len(c["gram"]) >= 100]
    N = len(ch)
    S = ueberlappung(ch)
    grp = np.array([c["c"] for c in ch])
    hs_all = sorted({h for c in ch for h in c["hs"]})
    pos = {h: i for i, h in enumerate(hs_all)}
    W = np.zeros((N, len(hs_all)))
    for i, c in enumerate(ch):
        for h, n in c["hs"].items():
            W[i, pos[h]] = n
    teilt = (W @ W.T) > 0
    W = W / W.sum(1, keepdims=True)
    nb = np.array([datum[h][0] for h in hs_all], float)
    na = np.array([datum[h][1] for h in hs_all], float)
    mitte = (nb + na) / 2
    fremd = grp[:, None] != grp[None, :]
    bg = float(S[fremd].mean())
    out = {"abschnitte": N, "hintergrund": bg, "gruppen": {}}
    print(f"   Abschnitte {N}, Hintergrund zwischen Textgruppen {bg:.5%}")
    cl = np.array([c["cluster"] for c in ch])
    for g in sorted(set(grp.tolist()), key=lambda k: -int((grp == k).sum())):
        ii = np.flatnonzero(grp == g)
        d = W[ii] @ mitte
        namen = sorted(set(cl[ii].tolist()))
        if len(ii) < 12 or len(namen) < 6 or d.max() - d.min() < 100:
            continue
        iu = np.triu_indices(len(ii), 1)
        ok = ~teilt[np.ix_(ii, ii)][iu]
        y = S[np.ix_(ii, ii)][iu][ok]
        x = np.abs(d[:, None] - d[None, :])[iu][ok]
        lam, A = anpassen(x, y, b=bg)
        r = {"abschnitte": int(len(ii)), "cluster": len(namen), "paare": int(ok.sum()),
             "handschriften": int((W[ii] > 0).any(0).sum()), "spanne_jahre": float(d.max() - d.min()),
             "niveau_gleichzeitig": A + bg, **kennzahlen(lam), "klassen": klassen(x, y)}
        if voll:
            hg = np.flatnonzero((W[ii] > 0).any(0))
            glied = [np.flatnonzero(cl[ii] == n) for n in namen]
            lb = []
            for _ in range(B):
                jj = np.concatenate([glied[p] for p in rng.integers(0, len(namen), len(namen))])
                zug = mitte.copy()
                zug[hg] = rng.uniform(nb[hg], na[hg])
                dd = (W[ii] @ zug)[jj]
                ju = np.triu_indices(len(jj), 1)
                okb = ~teilt[np.ix_(ii[jj], ii[jj])][ju]
                lb.append(anpassen(np.abs(dd[:, None] - dd[None, :])[ju][okb], S[np.ix_(ii[jj], ii[jj])][ju][okb], b=bg)[0])
            lb = np.array(lb)
            r["rate_ki"] = quantile(lb)
            r["normtreue_ki"] = sorted(float(math.exp(-100 * v)) for v in r["rate_ki"])
            r["halbwertszeit_ki"] = [(math.log(2) / v) if v > 0 else None for v in r["rate_ki"]][::-1]
            null = []
            for _ in range(B):
                zug = mitte.copy()
                zug[hg] = mitte[hg][rng.permutation(len(hg))]
                dd = W[ii] @ zug
                null.append(anpassen(np.abs(dd[:, None] - dd[None, :])[iu][ok], y, b=bg)[0])
            r["p_null"] = float((1 + (np.array(null) >= lam).sum()) / (B + 1))
        out["gruppen"][g] = r
        ki = f" [{r['normtreue_ki'][0]:.1%}, {r['normtreue_ki'][1]:.1%}] p={r['p_null']:.3f}" if voll else ""
        hz = f"{r['halbwertszeit']:.0f} J" if r["halbwertszeit"] else "kein Zerfall"
        print(f"   {NAMEN.get(g, g):22s} Abschn. {len(ii):3d} Hss {r['handschriften']:3d} Spanne {r['spanne_jahre']:5.0f} J | "
              f"gleichzeitig {r['niveau_gleichzeitig']:.3%} | Normtreue/Jh. {r['normtreue_je_jahrhundert']:.1%}{ki} | Halbwertszeit {hz}")
        print("        Klassen: " + "  ".join(f"{k['von']}-{k['bis'] or ''}: {k['mittel']:.3%} ({k['paare']})"
                                              for k in r["klassen"] if k["paare"]))
    return out


# ---------------------------------------------------------------- M2
def titel(s):
    return re.sub(r"\s+", " ", re.sub(r"[〈〉\[\]]", "", s)).strip()


def ausrichten(a, b):
    ops = difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
    anker = [k for k, o in enumerate(ops) if o[0] == "equal" and o[2] - o[1] >= 4]
    if not anker:
        return None
    M = D = 0
    for tag, i1, i2, j1, j2 in ops[anker[0]:anker[-1] + 1]:
        if tag == "equal":
            M += i2 - i1
        elif all(v > 0 for v in a[i1:i2]) and all(v > 0 for v in b[j1:j2]):
            D += max(i2 - i1, j2 - j1)
    return M, D


def m2_paare(texte, streng):
    nutz = (0,) if streng else (0, 1)
    code, zaehler = {}, [0]

    def folge(t):
        out = []
        for lid, e in t["tok"]:
            if e in nutz:
                out.append(code.setdefault(lid, len(code) + 1))
            else:
                zaehler[0] -= 1
                out.append(zaehler[0])
        return out

    werke = collections.defaultdict(list)
    for t in texte:
        if t["c"] in ("tb", "bbawpyramidentexte", "sawlit"):
            werke[(t["c"], titel(t["titel"]))].append(t)
    paare = []
    for (c, w), ts in werke.items():
        if len({t["hs"] for t in ts}) < 2:
            continue
        fs = [folge(t) for t in ts]
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                if ts[i]["hs"] == ts[j]["hs"]:
                    continue
                r = ausrichten(fs[i], fs[j])
                if r is None or r[0] < 15 or sum(r) < 30:
                    continue
                paare.append({"c": c, "werk": w, "a": ts[i]["hs"], "b": ts[j]["hs"], "M": r[0], "D": r[1],
                              "gleicher_bearbeiter": ts[i]["o"] == ts[j]["o"]})
    return paare


def m2(texte, streng, rng, voll=True, nur_gleicher_bearbeiter=False):
    paare = m2_paare(texte, streng)
    datum = {}
    for t in texte:
        e = datum.setdefault(t["hs"], [t["nb"], t["na"]])
        e[0], e[1] = min(e[0], t["nb"]), max(e[1], t["na"])
    out = {}
    for g in ("tb", "bbawpyramidentexte", "sawlit"):
        P = [p for p in paare if p["c"] == g and (p["gleicher_bearbeiter"] or not nur_gleicher_bearbeiter)]
        if len(P) < 20:
            continue
        hs = sorted({p["a"] for p in P} | {p["b"] for p in P})
        pos = {h: i for i, h in enumerate(hs)}
        ia, ib = np.array([pos[p["a"]] for p in P]), np.array([pos[p["b"]] for p in P])
        nb, na = np.array([datum[h][0] for h in hs], float), np.array([datum[h][1] for h in hs], float)
        mitte = (nb + na) / 2
        w = np.array([p["M"] + p["D"] for p in P], float)
        y = np.array([p["M"] for p in P], float) / w
        x = np.abs(mitte[ia] - mitte[ib])
        lam, A = anpassen(x, y, w)
        werk = np.array([p["werk"] for p in P])
        r = {"paare": len(P), "werke": len(set(werk.tolist())), "handschriften": len(hs),
             "vergleichbare_stellen": int(w.sum()), "spanne_jahre": float(x.max()),
             "uebereinstimmung_gleichzeitig": A, **kennzahlen(lam), "klassen": klassen(x, y, w)}
        if voll:
            namen, inv = np.unique(werk, return_inverse=True)
            glied = [np.flatnonzero(inv == k) for k in range(len(namen))]
            lb, lh = [], []
            for _ in range(B):
                jj = np.concatenate([glied[p] for p in rng.integers(0, len(namen), len(namen))])
                zug = rng.uniform(nb, na)
                lb.append(anpassen(np.abs(zug[ia[jj]] - zug[ib[jj]]), y[jj], w[jj])[0])
                mult = np.bincount(rng.integers(0, len(hs), len(hs)), minlength=len(hs)).astype(float)
                wh = w * mult[ia] * mult[ib]
                if (wh > 0).sum() >= 10:
                    lh.append(anpassen(np.abs(zug[ia] - zug[ib])[wh > 0], y[wh > 0], wh[wh > 0])[0])
            r["rate_ki"] = quantile(lb)
            r["normtreue_ki"] = sorted(float(math.exp(-100 * v)) for v in r["rate_ki"])
            r["halbwertszeit_ki"] = [(math.log(2) / v) if v > 0 else None for v in r["rate_ki"]][::-1]
            r["normtreue_ki_handschriften"] = sorted(float(math.exp(-100 * v)) for v in quantile(lh))
            null = []
            for _ in range(B):
                zug = mitte[rng.permutation(len(hs))]
                null.append(anpassen(np.abs(zug[ia] - zug[ib]), y, w)[0])
            r["p_null"] = float((1 + (np.array(null) >= lam).sum()) / (B + 1))
        out[g] = r
        ki = (f" [{r['normtreue_ki'][0]:.1%}, {r['normtreue_ki'][1]:.1%}] (ueber Handschriften gezogen: "
              f"[{r['normtreue_ki_handschriften'][0]:.1%}, {r['normtreue_ki_handschriften'][1]:.1%}]) p={r['p_null']:.3f}") if voll else ""
        hz = f"{r['halbwertszeit']:.0f} J" if r["halbwertszeit"] else "kein Zerfall"
        print(f"   {NAMEN.get(g, g):16s} Paare {len(P):4d} Werke {r['werke']:3d} Hss {len(hs):3d} Stellen {int(w.sum()):6d} | "
              f"gleichzeitig {A:.1%} | Normtreue/Jh. {r['normtreue_je_jahrhundert']:.2%}{ki} | Halbwertszeit {hz}")
        print("        Klassen: " + "  ".join(f"{k['von']}-{k['bis'] or ''}: {k['mittel']:.1%} ({k['paare']})"
                                              for k in r["klassen"] if k["paare"]))
    return out


def main():
    pfad, ziel = sys.argv[1], sys.argv[2]
    print("PROTOKOLL sha256:", hashlib.sha256(json.dumps(PROTOKOLL, sort_keys=True).encode()).hexdigest()[:16])
    texte = lade(pfad)
    rng = np.random.default_rng(PROTOKOLL["seed"])
    print(f"Texte mit brauchbarer Datierung: {len(texte)}, Woerter {sum(1 for t in texte for x in t['tok'] if x[0])}")
    erg = {"protokoll": PROTOKOLL}
    print("\nM1  gemeinsamer Wortlaut zwischen Abschnitten verschiedener Handschriften (L = 1000)")
    erg["M1"] = m1(texte, 1000, False, rng)
    print("\nM2  derselbe Spruch / dasselbe Werk in zwei Handschriften")
    erg["M2"] = m2(texte, False, rng)
    print("\nRobustheit")
    print(" M1 mit L = 500")
    erg["M1_L500"] = m1(texte, 500, False, rng, voll=False)
    print(" M1 nur ganz erhaltene Woerter")
    erg["M1_streng"] = m1(texte, 1000, True, rng, voll=False)
    print(" M2 nur ganz erhaltene Woerter")
    erg["M2_streng"] = m2(texte, True, rng, voll=False)
    print(" M2 nur Paare mit gleichem Bearbeiter")
    erg["M2_gleicher_bearbeiter"] = m2(texte, False, rng, voll=False, nur_gleicher_bearbeiter=True)
    json.dump(erg, open(ziel, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\ngeschrieben:", ziel)


if __name__ == "__main__":
    main()
