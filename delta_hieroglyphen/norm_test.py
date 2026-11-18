"""Norm-Test: Bleibt der Wortlaut ritueller Texte ueber Epochen stabiler als der anderer Textgruppen?

Aufruf: python3 -I norm_test.py <tokens.jsonl.gz> <ergebnis.json>

Anlass: die Frage, ob Rituale eine Art Norm 'fuer ewig' sind. Pruefbar ist davon der Kern:
Eine Norm wird woertlich weitergegeben und driftet nicht. Vorhersagen, festgelegt vor dem Lauf:
  V1 Wortlaut: Totenbuch-Abschnitte teilen ueber die Grenze NR <-> Spaetzeit mehr Lemma-Fuenfergruppen
     als literarische Abschnitte ueber dieselbe Grenze.
  V2 Drift:    Der Delta-Abstand zwischen den Epochen, geteilt durch den Abstand innerhalb einer Epoche,
     ist beim Totenbuch kleiner als bei der Literatur (gleiches Epochenpaar).
  V3 Pyramidentexte: Ihr Wortlaut steht in spaeten Totentexten haeufiger als in spaeter Literatur.
Gegen die Vorhersage spricht jeweils die umgekehrte Reihenfolge.

Wortebene (Lemmata), Abschnitte zu 1000 Woertern, je Teilkorpus und Epoche getrennt gebildet, damit jeder
Abschnitt genau eine Datierung hat. Datierung = Alter der Handschrift, nicht der Abfassung.
"""
import collections
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import delta_test as dt  # noqa: E402

EP = {"OK & FIP": "AR", "MK & SIP": "MR", "NK": "NR", "TIP - Roman times": "SpZ"}
K, R, B = 10, 20, 1000


def main():
    pfad, ziel = sys.argv[1], sys.argv[2]
    P = dt.PROTOKOLL["primaer"]
    rng = np.random.default_rng(dt.PROTOKOLL["seed"] + 2)
    texte = []
    for t in dt.lade(pfad):
        if t["d"] in EP:
            u = dict(t)
            u["c"] = t["c"] + "|" + EP[t["d"]]
            texte.append(u)
    ch = dt.abschnitte(texte, P["L"], False)
    N = len(ch)
    zelle = np.array([c["c"] for c in ch])
    cl = np.array([c["cluster"] for c in ch])
    folgen = [[x[0] for x in c["tok"]] for c in ch]
    F, _ = dt.haeufigkeiten(folgen)
    D, _ = dt.distanz(F, P["n"], "burrows")
    T, S = dt.teilt(ch, "texte"), dt.ueberlappung(ch)
    gram = [{tuple(f[j:j + 5]) for j in range(len(f) - 4)} for f in folgen]
    idx = {z: np.flatnonzero(zelle == z) for z in sorted(set(zelle.tolist()))}
    print(f"{N} Abschnitte; Zellen (Teilkorpus|Epoche) mit mindestens {K} Abschnitten:")
    print("  ", {z: len(i) for z, i in idx.items() if len(i) >= K})
    out = {"zellen": {z: int(len(i)) for z, i in idx.items()}}

    def zieh(i):
        namen, inv = np.unique(cl[i], return_inverse=True)
        return np.concatenate([i[inv == p] for p in rng.integers(0, len(namen), len(namen))])

    def mittel(i, j, ok):
        m = ok[np.ix_(i, j)]
        return D[np.ix_(i, j)][m].mean() if m.any() else np.nan

    def drift(ia, ib, ok):
        return mittel(ia, ib, ok) / (0.5 * (mittel(ia, ia, ok) + mittel(ib, ib, ok)))

    def reuse(src, tgt):
        """Je Quellabschnitt: Anteil seiner Fuenfergruppen, die in K zufaelligen Zielabschnitten stehen."""
        w = np.full(len(src), np.nan)
        for a, i in enumerate(src):
            kand = tgt[~T[i, tgt]]
            if len(kand) < K:
                continue
            v = []
            for _ in range(R):
                U = set().union(*(gram[j] for j in rng.choice(kand, K, replace=False)))
                v.append(len(gram[i] & U) / len(gram[i]))
            w[a] = np.mean(v)
        return w

    def mit_ki(w, src):
        ok = ~np.isnan(w)
        w, c = w[ok], cl[src][ok]
        namen, inv = np.unique(c, return_inverse=True)
        s, z = np.bincount(inv, weights=w), np.bincount(inv)
        pick = rng.integers(0, len(namen), (B, len(namen)))
        b = s[pick].sum(1) / z[pick].sum(1)
        return float(w.mean()), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))

    # V1 und V2: gleiche Textgruppe, zwei Epochen
    print("\nV1/V2  gleiche Textgruppe ueber eine Epochengrenze")
    print(f"   {'Textgruppe':12s} {'Epochen':8s} {'n':>9s} | Wortlaut geteilt: ueber die Grenze | innerhalb | fremde Gruppe"
          f" | Drift B/W alle Paare [95%-KI] | ohne Parallelen | Epoche erkannt (Zufall)")
    out["paare"] = {}
    gruppen = sorted({z.split("|")[0] for z in idx})
    for g in gruppen:
        eps = [e for e in ("AR", "MR", "NR", "SpZ") if len(idx.get(f"{g}|{e}", [])) >= K]
        for x in range(len(eps)):
            for y in range(x + 1, len(eps)):
                a, b = idx[f"{g}|{eps[x]}"], idx[f"{g}|{eps[y]}"]
                fremd_b = np.concatenate([i for z, i in idx.items() if z.endswith("|" + eps[y]) and not z.startswith(g + "|")])
                fremd_a = np.concatenate([i for z, i in idx.items() if z.endswith("|" + eps[x]) and not z.startswith(g + "|")])
                quer = np.concatenate([reuse(a, b), reuse(b, a)])
                innen = np.concatenate([reuse(a, a), reuse(b, b)])
                fremd = np.concatenate([reuse(a, fremd_b), reuse(b, fremd_a)])
                beide = np.concatenate([a, b])
                rq, ri, rf = mit_ki(quer, beide), mit_ki(innen, beide), mit_ki(fremd, beide)
                ok_alle, ok_str = ~T, ~T & (S <= P["tau"])
                d0, d1 = drift(a, b, ok_alle), drift(a, b, ok_str)
                bs = [drift(zieh(a), zieh(b), ok_alle) for _ in range(B)]
                # Epoche innerhalb der Textgruppe per naechstem Nachbarn (anderer Text)
                E = np.zeros((N, N), bool)
                E[np.ix_(beide, beide)] = True
                E &= ~T
                nn = np.where(E, D, np.inf).argmin(1)[beide]
                ep = np.array([z.split("|")[1] for z in zelle])
                tr = (ep[nn] == ep[beide]).mean()
                zuf = np.mean([(E[i] & (ep == ep[i])).sum() / E[i].sum() for i in beide])
                r = {"n": [int(len(a)), int(len(b))], "wortlaut_quer": rq, "wortlaut_innen": ri, "wortlaut_fremd": rf,
                     "drift": float(d0), "drift_ki": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                     "drift_ohne_parallelen": float(d1), "epoche_erkannt": float(tr), "epoche_zufall": float(zuf)}
                out["paare"][f"{g}|{eps[x]}-{eps[y]}"] = r
                print(f"   {g[:12]:12s} {eps[x] + '-' + eps[y]:8s} {len(a):4d}/{len(b):<4d} | {rq[0]:6.1%} [{rq[1]:.1%}, {rq[2]:.1%}] "
                      f"| {ri[0]:6.1%} | {rf[0]:5.1%} | {d0:.3f} [{r['drift_ki'][0]:.3f}, {r['drift_ki'][1]:.3f}] | {d1:.3f} "
                      f"| {tr:.1%} ({zuf:.1%})")

    # V3: Wortlaut der Pyramidentexte in anderen Zellen
    print("\nV3  Wortlaut der Pyramidentexte (AR) in anderen Textgruppen: Anteil der Fuenfergruppen, die in 10 Zielabschnitten stehen")
    pt = idx["bbawpyramidentexte|AR"]
    out["pyramidentexte"] = {}
    for z, i in sorted(idx.items(), key=lambda kv: kv[0]):
        if len(i) < K:
            continue
        r = mit_ki(reuse(pt, i), pt)
        out["pyramidentexte"][z] = r
        print(f"   -> {z:28s} ({len(i):3d}): {r[0]:6.2%} [{r[1]:.2%}, {r[2]:.2%}]")
    # Gegenrichtung: wie viel eines spaeten Abschnitts steht schon in den Pyramidentexten?
    print("   Gegenrichtung: Anteil der Fuenfergruppen eines Abschnitts, die in 10 Pyramidentext-Abschnitten stehen")
    out["aus_pyramidentexten"] = {}
    for z, i in sorted(idx.items(), key=lambda kv: kv[0]):
        if len(i) < K or z == "bbawpyramidentexte|AR":
            continue
        r = mit_ki(reuse(i, pt), i)
        out["aus_pyramidentexten"][z] = r
        print(f"   <- {z:28s} ({len(i):3d}): {r[0]:6.2%} [{r[1]:.2%}, {r[2]:.2%}]")

    json.dump(out, open(ziel, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\ngeschrieben:", ziel)


if __name__ == "__main__":
    main()
