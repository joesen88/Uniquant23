"""Nachtrag zum Delta-Test: Auswertungen, die erst nach dem ersten Lauf dazukamen.

Aufruf: python3 -I delta_nachtrag.py <tokens.jsonl.gz> <ergebnis_nachtrag.json>

Nicht Teil des eingefrorenen Protokolls. Gleiche Abschnitte, gleiche Distanz,
gleiche Ausschlussregel (kein gemeinsamer Text, tau = 0.05).
  A  Gleiche Anfragen mit und ohne Ausschluss des eigenen Bearbeiters bzw. der eigenen Epoche.
  B  Ein Merkmal bestimmen, waehrend die anderen festgehalten sind (nur Anfragen, bei denen
     unter den zulaessigen Kandidaten beide Antworten vorkommen).
  C  Rauschgrenze fuer den Wechsel des Vergleichskorpus: zufaellige Teilmengen gleicher Groesse.
"""
import collections
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import delta_test as dt  # noqa: E402


def boot(treffer, cl, rng, B=2000):
    namen, inv = np.unique(cl, return_inverse=True)
    s = np.bincount(inv, weights=treffer.astype(float), minlength=len(namen))
    z = np.bincount(inv, minlength=len(namen))
    zieh = rng.integers(0, len(namen), (B, len(namen)))
    b = s[zieh].sum(1) / z[zieh].sum(1)
    return [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))]


def lauf(name, chunks, ebene, rng):
    P = dt.PROTOKOLL["primaer"]
    N = len(chunks)
    cl = np.array([ch["cluster"] for ch in chunks])
    y = np.array([ch["c"] for ch in chunks])
    folgen = [[x[0] for x in ch["tok"]] if ebene == "lem" else [s for x in ch["tok"] for s in x[1]] for ch in chunks]
    F, _ = dt.haeufigkeiten(folgen)
    T, S = dt.teilt(chunks, "texte"), dt.ueberlappung(chunks)
    ich = np.eye(N, dtype=bool)
    E = ~T & ~ich & (S <= P["tau"])
    D, merk = dt.distanz(F, P["n"], P["distanz"])
    yb = np.array([sorted(ch["bearb"])[0] for ch in chunks])
    yd = np.array([sorted(ch["datum"])[0] for ch in chunks])
    eb = np.array([len(ch["bearb"]) == 1 for ch in chunks])
    ed = np.array([len(ch["datum"]) == 1 and "unknown" not in ch["datum"] for ch in chunks])
    Gg = y[None, :] == y[:, None]
    Gb = (yb[None, :] == yb[:, None])
    Gd = (yd[None, :] == yd[:, None])
    Bm, Dm = dt.teilt(chunks, "bearb"), dt.teilt(chunks, "datum")
    idx = np.arange(N)
    out = {"abschnitte": N}
    print(f"\n=== {name}: {N} Abschnitte ===")

    def nachbar(El):
        return np.where(El, D, np.inf).argmin(1)

    # A: gleiche Anfragen
    unb = np.array(["unknown" in ch["datum"] for ch in chunks])
    for titel, El, gueltig in (("fremder Bearbeiter", E & ~Bm, np.ones(N, bool)),
                               ("fremde Epoche (Protokoll)", E & ~Dm & ~unb[None, :], ~unb),
                               ("fremde Epoche (eindeutig datiert)", E & ~Dm & ed[None, :], ed)):
        q = (Gg & El).any(1) & gueltig
        mit, ohne = Gg[idx, nachbar(E)], Gg[idx, nachbar(El)]
        out["A " + titel] = {"anfragen": int(q.sum()), "alle_kandidaten": float(mit[q].mean()), "ki_alle": boot(mit[q], cl[q], rng),
                             "mit_ausschluss": float(ohne[q].mean()), "ki_ausschluss": boot(ohne[q], cl[q], rng),
                             "zufall_ausschluss": float(((Gg & El).sum(1) / np.maximum(El.sum(1), 1))[q].mean())}
        r = out["A " + titel]
        print(f"   A {titel:34s} n={r['anfragen']:4d}: alle Kandidaten {r['alle_kandidaten']:.1%} "
              f"[{r['ki_alle'][0]:.1%}, {r['ki_alle'][1]:.1%}] -> mit Ausschluss {r['mit_ausschluss']:.1%} "
              f"[{r['ki_ausschluss'][0]:.1%}, {r['ki_ausschluss'][1]:.1%}] (Zufallsnachbar {r['zufall_ausschluss']:.1%})")

    # B: ein Merkmal bei festgehaltenen anderen
    def test(titel, ziel, halte, gueltig):
        El = E & gueltig[None, :]
        for M in halte:
            El = El & M
        zahl = El.sum(1)
        p = np.divide((ziel & El).sum(1), zahl, out=np.zeros(N), where=zahl > 0)
        q = gueltig & (p > 0) & (p < 1)
        if q.sum() < 10:
            print(f"   B {titel:44s} zu wenige Anfragen ({int(q.sum())})")
            out["B " + titel] = {"anfragen": int(q.sum())}
            return
        tr = ziel[idx, nachbar(El)]
        kl = collections.Counter()
        r = {"anfragen": int(q.sum()), "cluster": int(len(set(cl[q]))), "treffer": float(tr[q].mean()),
             "ki": boot(tr[q], cl[q], rng), "zufallsnachbar": float(p[q].mean())}
        sim = (rng.random((2000, int(q.sum()))) < p[q]).mean(1)
        r["p"] = float((1 + (sim >= r["treffer"]).sum()) / 2001)
        out["B " + titel] = r
        print(f"   B {titel:44s} n={r['anfragen']:4d} ({r['cluster']:3d} Cluster): Treffer {r['treffer']:.1%} "
              f"[{r['ki'][0]:.1%}, {r['ki'][1]:.1%}] | Zufallsnachbar {r['zufallsnachbar']:.1%} | p {r['p']:.4f}")

    test("Gattung | gleicher Bearbeiter", Gg, [Gb & eb[None, :]], eb)
    test("Gattung | gleiche Epoche", Gg, [Gd & ed[None, :]], ed)
    test("Gattung | gleicher Bearbeiter und Epoche", Gg, [Gb & eb[None, :], Gd & ed[None, :]], eb & ed)
    test("Epoche | gleiche Gattung", Gd, [Gg], ed)
    test("Epoche | gleiche Gattung und Bearbeiter", Gd, [Gg, Gb & eb[None, :]], eb & ed)
    test("Bearbeiter | gleiche Gattung", Gb, [Gg], eb)
    test("Bearbeiter | gleiche Gattung und Epoche", Gb, [Gg, Gd & ed[None, :]], eb & ed)

    # C: Rauschgrenze Vergleichskorpus
    nn0 = nachbar(E)
    q = (Gg & E).any(1)
    out["C"] = {}
    for g, k in collections.Counter(y.tolist()).most_common():
        if k < 30:
            continue
        ref = np.flatnonzero(y == g)
        Dg, mg = dt.distanz(F, P["n"], P["distanz"], ref=ref)
        nng = np.where(E, Dg, np.inf).argmin(1)
        echt = {"nachbar": float((nng[q] != nn0[q]).mean()), "antwort": float((y[nng[q]] != y[nn0[q]]).mean()),
                "treffer": float((y[nng[q]] == y[q]).mean())}
        zn, za, zt, zm = [], [], [], []
        for _ in range(20):
            r = rng.choice(N, k, replace=False)
            Dr, mr = dt.distanz(F, P["n"], P["distanz"], ref=r)
            nnr = np.where(E, Dr, np.inf).argmin(1)
            zn.append((nnr[q] != nn0[q]).mean())
            za.append((y[nnr[q]] != y[nn0[q]]).mean())
            zt.append((y[nnr[q]] == y[q]).mean())
            zm.append(len(set(mr.tolist()) & set(merk.tolist())))
        out["C"][g] = {"groesse": int(k), "teilkorpus": echt,
                       "zufallsauswahl": {"nachbar": float(np.mean(zn)), "antwort": float(np.mean(za)),
                                          "treffer": float(np.mean(zt)), "gemeinsame_merkmale": float(np.mean(zm))}}
        z = out["C"][g]["zufallsauswahl"]
        print(f"   C {g:20s} ({k:3d}): Nachbar wechselt {echt['nachbar']:.1%} (Zufallsauswahl gleicher Groesse {z['nachbar']:.1%}) | "
              f"Antwort wechselt {echt['antwort']:.1%} ({z['antwort']:.1%}) | Treffer {echt['treffer']:.1%} ({z['treffer']:.1%})")
    return out


def main():
    pfad, ziel = sys.argv[1], sys.argv[2]
    P = dt.PROTOKOLL["primaer"]
    texte = dt.lade(pfad)
    rng = np.random.default_rng(dt.PROTOKOLL["seed"] + 1)
    mini = dt.PROTOKOLL["min_abschnitte_je_teilkorpus"]
    W = dt.filtere(dt.abschnitte(texte, P["L"], False), mini)
    Z = dt.filtere(dt.abschnitte(texte, P["L"], True, True), mini)
    erg = {"wort": lauf("WORTEBENE", W, "lem", rng), "zeichen": lauf("ZEICHENEBENE", Z, "sig", rng),
           "wort_gepaart": lauf("WORTEBENE gepaart", Z, "lem", rng)}
    json.dump(erg, open(ziel, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\ngeschrieben:", ziel)


if __name__ == "__main__":
    main()
