"""Nachtrag zur Halbwertszeit: Auswertungen, die erst nach dem Protokoll-Lauf dazukamen.

Aufruf: python3 -I halbwertszeit_nachtrag.py <zeit_schicht.jsonl.gz> <ergebnis.json>

  A  Wie sicher ist die vorhergesagte Reihenfolge? Anteil der Ziehungen, in denen sie gilt.
  B  Abschreibtreue (M2) mit Namensfeld: Namen von Personen und Koenigen zaehlen als ein Platzhalter.
     Anlass: Pyramidentexte tragen in jedem Grab einen anderen Koenigsnamen.
  C  Handschriftenpaare des Totenbuchs einzeln: Zeitabstand und Uebereinstimmung.
"""
import collections
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import halbwertszeit as hw  # noqa: E402

B = 1000


def m1_ziehungen(texte, gruppen, rng):
    ch, datum = hw.abschnitte(texte, 1000, False)
    ch = [c for c in ch if c["spanne"] <= 150 and len(c["gram"]) >= 100]
    N = len(ch)
    S = hw.ueberlappung(ch)
    grp = np.array([c["c"] for c in ch])
    cl = np.array([c["cluster"] for c in ch])
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
    bg = float(S[grp[:, None] != grp[None, :]].mean())
    out = {}
    for g in gruppen:
        ii = np.flatnonzero(grp == g)
        namen = sorted(set(cl[ii].tolist()))
        glied = [np.flatnonzero(cl[ii] == n) for n in namen]
        hg = np.flatnonzero((W[ii] > 0).any(0))
        lb = []
        for _ in range(B):
            jj = np.concatenate([glied[p] for p in rng.integers(0, len(namen), len(namen))])
            zug = mitte.copy()
            zug[hg] = rng.uniform(nb[hg], na[hg])
            dd = (W[ii] @ zug)[jj]
            ju = np.triu_indices(len(jj), 1)
            ok = ~teilt[np.ix_(ii[jj], ii[jj])][ju]
            lb.append(hw.anpassen(np.abs(dd[:, None] - dd[None, :])[ju][ok], S[np.ix_(ii[jj], ii[jj])][ju][ok], b=bg)[0])
        out[g] = np.array(lb)
    return out


def paare_mit_namensfeld(texte, namensfeld):
    """Wie hw.m2_paare, aber Namen von Personen und Koenigen als ein gemeinsamer Platzhalter."""
    code, zaehler = {}, [0]
    NAME = 10 ** 9

    def folge(t):
        out = []
        for (lid, e), art in zip(t["tok"], t["art"]):
            if e not in (0, 1):
                zaehler[0] -= 1
                out.append(zaehler[0])
            elif namensfeld and art == 1:
                if not out or out[-1] != NAME:
                    out.append(NAME)
            else:
                out.append(code.setdefault(lid, len(code) + 1))
        return out

    werke = collections.defaultdict(list)
    for t in texte:
        if t["c"] in ("tb", "bbawpyramidentexte", "sawlit"):
            werke[(t["c"], hw.titel(t["titel"]))].append(t)
    paare = []
    for (c, w), ts in werke.items():
        if len({t["hs"] for t in ts}) < 2:
            continue
        fs = [folge(t) for t in ts]
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                if ts[i]["hs"] == ts[j]["hs"]:
                    continue
                r = hw.ausrichten(fs[i], fs[j])
                if r is None or r[0] < 15 or sum(r) < 30:
                    continue
                paare.append({"c": c, "werk": w, "a": ts[i]["hs"], "b": ts[j]["hs"], "M": r[0], "D": r[1]})
    return paare


def m2_auswerten(paare, texte, rng, g):
    datum = {}
    for t in texte:
        e = datum.setdefault(t["hs"], [t["nb"], t["na"]])
        e[0], e[1] = min(e[0], t["nb"]), max(e[1], t["na"])
    P = [p for p in paare if p["c"] == g]
    hs = sorted({p["a"] for p in P} | {p["b"] for p in P})
    pos = {h: i for i, h in enumerate(hs)}
    ia, ib = np.array([pos[p["a"]] for p in P]), np.array([pos[p["b"]] for p in P])
    nb, na = np.array([datum[h][0] for h in hs], float), np.array([datum[h][1] for h in hs], float)
    mitte = (nb + na) / 2
    w = np.array([p["M"] + p["D"] for p in P], float)
    y = np.array([p["M"] for p in P], float) / w
    x = np.abs(mitte[ia] - mitte[ib])
    lam, A = hw.anpassen(x, y, w)
    werk = np.array([p["werk"] for p in P])
    namen, inv = np.unique(werk, return_inverse=True)
    glied = [np.flatnonzero(inv == k) for k in range(len(namen))]
    lb = []
    for _ in range(B):
        jj = np.concatenate([glied[p] for p in rng.integers(0, len(namen), len(namen))])
        zug = rng.uniform(nb, na)
        lb.append(hw.anpassen(np.abs(zug[ia[jj]] - zug[ib[jj]]), y[jj], w[jj])[0])
    return {"paare": len(P), "gleichzeitig": A, "gesamt": float((w * y).sum() / w.sum()), **hw.kennzahlen(lam),
            "klassen": hw.klassen(x, y, w)}, np.array(lb), (P, hs, mitte, ia, ib, w, y, x)


def main():
    pfad, ziel = sys.argv[1], sys.argv[2]
    texte = hw.lade(pfad)
    rng = np.random.default_rng(hw.PROTOKOLL["seed"] + 7)
    erg = {}

    print("A  Reihenfolge der Vorhersagen (Anteil der 1000 Ziehungen)")
    z1 = m1_ziehungen(texte, ["tb", "sawlit", "bbawbriefe", "bbawgrabinschriften", "bbawpyramidentexte", "sawmedizin"], rng)
    erg["A"] = {"V1_tb_ueber_literatur": float((z1["tb"] < z1["sawlit"]).mean()),
                "V1_literatur_ueber_briefen": float((z1["sawlit"] < z1["bbawbriefe"]).mean()),
                "V1_ganz": float(((z1["tb"] < z1["sawlit"]) & (z1["sawlit"] < z1["bbawbriefe"])).mean()),
                "tb_ueber_briefen": float((z1["tb"] < z1["bbawbriefe"]).mean()),
                "tb_ueber_grabinschriften": float((z1["tb"] < z1["bbawgrabinschriften"]).mean()),
                "tb_zerfall_groesser_null": float((z1["tb"] > 0).mean())}
    print("   M1:", {k: round(v, 3) for k, v in erg["A"].items()})
    for g, v in z1.items():
        print(f"      {hw.NAMEN.get(g, g):18s} Normtreue/Jh. Median {np.exp(-100 * np.median(v)):.1%}, "
              f"Anteil der Ziehungen an der Suchgrenze {((v <= hw.LAM_MIN + 1e-6) | (v >= hw.LAM_MAX - 1e-6)).mean():.1%}")

    print("\nB  Abschreibtreue ohne und mit Namensfeld")
    erg["B"] = {}
    zb = {}
    for feld in (False, True):
        paare = paare_mit_namensfeld(texte, feld)
        for g in ("tb", "bbawpyramidentexte", "sawlit"):
            r, lb, roh = m2_auswerten(paare, texte, rng, g)
            r["normtreue_ki"] = sorted(float(np.exp(-100 * q)) for q in np.percentile(lb, [2.5, 97.5]))
            erg["B"][f"{g}|{'mit' if feld else 'ohne'}"] = r
            zb[(g, feld)] = (lb, roh)
            k0 = r["klassen"][0]
            print(f"   {hw.NAMEN[g]:16s} {'mit Namensfeld ' if feld else 'ohne Namensfeld'}: Paare {r['paare']:4d} | gleichzeitig (Modell) {r['gleichzeitig']:.1%} | "
                  f"0-50 Jahre {k0['mittel']:.1%} | alle Paare {r['gesamt']:.1%} | Normtreue/Jh. {r['normtreue_je_jahrhundert']:.2%} "
                  f"[{r['normtreue_ki'][0]:.2%}, {r['normtreue_ki'][1]:.2%}]")
    erg["A"]["V2_tb_ueber_literatur"] = float((zb[("tb", False)][0] < zb[("sawlit", False)][0]).mean())
    print("   V2 (Totenbuch treuer als Literatur), Anteil der Ziehungen:", round(erg["A"]["V2_tb_ueber_literatur"], 3))

    print("\nC  Totenbuch: Handschriftenpaare mit mindestens 1000 vergleichbaren Stellen")
    P, hs, mitte, ia, ib, w, y, x = zb[("tb", False)][1]
    agg = collections.defaultdict(lambda: [0.0, 0.0, 0])
    for k in range(len(P)):
        e = agg[tuple(sorted((hs[ia[k]], hs[ib[k]]), key=lambda h: (mitte[hs.index(h)], h)))]
        e[0] += w[k] * y[k]
        e[1] += w[k]
        e[2] += 1
    erg["C"] = []
    for (a, b), e in sorted(agg.items(), key=lambda kv: abs(mitte[hs.index(kv[0][0])] - mitte[hs.index(kv[0][1])])):
        if e[1] < 1000:
            continue
        dt = abs(mitte[hs.index(a)] - mitte[hs.index(b)])
        erg["C"].append({"a": a, "b": b, "dt": float(dt), "stellen": int(e[1]), "sprueche": e[2], "uebereinstimmung": e[0] / e[1]})
        print(f"   {a.split('|', 1)[1][:22]:22s} ({mitte[hs.index(a)]:6.0f}) - {b.split('|', 1)[1][:22]:22s} ({mitte[hs.index(b)]:6.0f}): "
              f"{dt:5.0f} Jahre | {e[2]:3d} Sprueche, {int(e[1]):6d} Stellen | gleich {e[0] / e[1]:.1%}")
    json.dump(erg, open(ziel, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\ngeschrieben:", ziel)


if __name__ == "__main__":
    main()
