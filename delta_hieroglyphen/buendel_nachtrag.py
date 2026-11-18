"""Nachtrag zum Buendel-Test.

Aufruf: python3 -I buendel_nachtrag.py <tokens.jsonl.gz> <zeit_schicht.jsonl.gz> <ergebnis.json>

  A  Bereinigung mit Schrumpfung. Anlass: Die Kontrolle im Protokoll-Lauf zeigte, dass die Bereinigung ohne
     Schrumpfung Rauschen eintraegt (erfundene Bearbeiter ohne Effekt wurden danach besser erkannt als vorher).
     Jetzt wird die Abweichung einer Zelle je Merkmal mit tau2 / (tau2 + se2) gewichtet: tau2 ist die geschaetzte
     Streuung echter Bearbeiterabweichungen, se2 der Schaetzfehler der Zelle bei zufaelligen Handschrifteneffekten.
  B  Austauschbare Zeichenpaare: Welchen Anteil hat je Bearbeiter die eine von zwei Schreibungen?
  C  Schriftart als vierter Faktor (hieratisch, hieroglyphisch, kursivhieroglyphisch). Anlass: Die Zeichenpaare
     aus B trennen vor allem hieratische Papyri von hieroglyphischen Denkmaelern, und Bearbeiter arbeiten meist
     nur an einer Sorte. Wie viel vom eigenen Bearbeiteranteil bleibt, wenn die Schriftart im Modell steht?

Aufruf mit viertem Argument <metadaten.jsonl>, damit C laeuft.
"""
import collections
import hashlib
import json
import os
import sys

import numpy as np
from scipy.spatial.distance import cdist

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import buendel_test as bt  # noqa: E402
import delta_test as dt  # noqa: E402

PAARE = [("Z2", "Z3", "Pluralstriche waagrecht / senkrecht"), ("D40", "A24", "Arm mit Stock / schlagender Mann"),
         ("G43", "Z7", "w als Wachtelkueken / als Schleife"), ("W24", "W22", "Topf / Bierkrug"), ("N35", "D35", "Wasserlinie n / verneinende Arme")]


def schaetze(Z, zelle, XZ, cl):
    """Geschrumpfte Abweichung je Zelle vom Mittel der Bearbeiter derselben Textgruppe."""
    N = len(zelle)
    zl = sorted(set(zelle))
    pos = {z: i for i, z in enumerate(zl)}
    zi = np.array([pos[z] for z in zelle])
    C = np.zeros((N, len(zl)))
    C[np.arange(N), zi] = 1
    X = np.hstack([C, XZ])
    beta = np.linalg.lstsq(X, Z, rcond=None)[0]
    mu, R = beta[:len(zl)], Z - X @ beta
    cc = np.array([f"{c}|{z}" for c, z in zip(cl, zelle)])
    cn, cinv = np.unique(cc, return_inverse=True)
    nc = np.bincount(cinv).astype(float)
    rbar = np.zeros((len(cn), Z.shape[1]))
    np.add.at(rbar, cinv, R)
    rbar /= nc[:, None]
    s_e2 = ((R - rbar[cinv]) ** 2).sum(0) / max(1, N - len(cn))
    frei = max(1, len(cn) - len(zl))
    n0 = (N - (nc ** 2).sum() / N) / frei
    s_u2 = np.clip(((nc[:, None] * rbar ** 2).sum(0) / frei - s_e2) / n0, 0, None)
    zc = np.array([pos[z] for z in (zelle[np.flatnonzero(cinv == k)[0]] for k in range(len(cn)))])
    nA = np.bincount(zi, minlength=len(zl)).astype(float)
    q = np.bincount(zc, weights=nc ** 2, minlength=len(zl))
    se2 = s_u2[None, :] * (q / nA ** 2)[:, None] + s_e2[None, :] / nA[:, None]
    je_g = collections.defaultdict(list)
    for z in zl:
        je_g[z[0]].append(pos[z])
    a = np.zeros_like(mu)
    mehr = np.zeros(len(zl), bool)
    for ids in je_g.values():
        if len(ids) >= 2:
            a[ids] = mu[ids] - mu[ids].mean(0)
            mehr[ids] = True
    if not mehr.any():
        return {}, None
    ng = sum(1 for ids in je_g.values() if len(ids) >= 2)
    tau2 = np.clip((a[mehr] ** 2).sum(0) / max(1, mehr.sum() - ng) - se2[mehr].mean(0), 0, None)
    gewicht = np.divide(tau2[None, :], tau2[None, :] + se2, out=np.zeros_like(se2), where=(tau2[None, :] + se2) > 0)
    return {zl[k]: a[k] * gewicht[k] for k in np.flatnonzero(mehr)}, float(gewicht[mehr].mean())


def bereinige(Z, zelle, XZ, cluster, falten=10):
    falte = np.array([int(hashlib.sha1(c.encode()).hexdigest(), 16) % falten for c in cluster])
    zelle = list(zelle)
    Zb, n, gew = Z.copy(), 0, []
    for f in range(falten):
        tr, te = np.flatnonzero(falte != f), np.flatnonzero(falte == f)
        ab, g_ = schaetze(Z[tr], [zelle[i] for i in tr], XZ[tr], [cluster[i] for i in tr])
        if g_ is not None:
            gew.append(g_)
        for i in te:
            if zelle[i] in ab:
                Zb[i] = Z[i] - ab[zelle[i]]
                n += 1
    return Zb, n, float(np.mean(gew)) if gew else None


def schriftarten(meta_pfad, zeit_pfad):
    """Vorherrschende Schriftart je Handschrift nach Wortzahl."""
    import gzip
    art = {}
    for z in open(meta_pfad, encoding="utf-8"):
        m = json.loads(z)
        s = m["schrift"]
        art[m["t"]] = ("hieratisch" if "ieratisch" in s else "kursivhieroglyphisch" if "ursivhieroglyph" in s
                       else "hieroglyphisch" if "ieroglyph" in s else "unbekannt")
    je = collections.defaultdict(collections.Counter)
    for z in gzip.open(zeit_pfad, "rt", encoding="utf-8"):
        t = json.loads(z)
        je[t["hs"]][art.get(t["t"], "unbekannt")] += sum(1 for x in t["tok"] if x[0])
    return {h: c.most_common(1)[0][0] for h, c in je.items()}


def lauf(name, texte, ebene, rng, schrift=None):
    ch = bt.abschnitte(texte, ebene)
    N = len(ch)
    g, b = np.array([a["c"] for a in ch]), np.array([a["o"] for a in ch])
    d, cl = np.array([a["d"] for a in ch]), [a["cluster"] for a in ch]
    ep = np.array([bt.epoche(v) for v in d])
    folgen = [[x[0] for x in a["tok"]] if ebene == "wort" else [s for x in a["tok"] for s in x[1]] for a in ch]
    F, vok = dt.haeufigkeiten(folgen)
    order = np.argsort(-F.sum(0), kind="stable")[:bt.N_MERK]
    X = F[:, order]
    Z = (X - X.mean(0)) / X.std(0, ddof=1)
    hs_all = sorted({h for a in ch for h in a["hs"]})
    pos = {h: i for i, h in enumerate(hs_all)}
    W = np.zeros((N, len(hs_all)))
    for i, a in enumerate(ch):
        for h in a["hs"]:
            W[i, pos[h]] = 1
    E = ~((W @ W.T) > 0) & (dt.ueberlappung(ch) <= bt.TAU)
    XZ = bt.spline(d, np.unique(np.percentile(d, [5, 27.5, 50, 72.5, 95])))
    out = {}
    print(f"\n=== {name}: {N} Abschnitte ===")

    def vergleich(Zv, labels, titel):
        Zb, n, gew = bereinige(Zv, list(zip(g.tolist(), labels.tolist())), XZ, cl)
        vor = bt.nachbar_tests(cdist(Zv, Zv, "cityblock") / bt.N_MERK, E, g, labels, ep)
        nach = bt.nachbar_tests(cdist(Zb, Zb, "cityblock") / bt.N_MERK, E, g, labels, ep)
        res = {"angepasst": n, "mittleres_gewicht": gew}
        print(f"   {titel}: {n} Abschnitte angepasst, mittleres Gewicht der Abweichungen {gew:.2f}" if gew is not None else f"   {titel}: nichts anzupassen")
        cla = np.array(cl)
        for k, t in (("textgruppe", "Textgruppe wiedererkannt"), ("textgruppe_fremde_bearbeiter", "Textgruppe, nur fremde Bearbeiter"),
                     ("bearbeiter_gleiche_gruppe_epoche", "Bearbeiter bei gleicher Gruppe und Epoche")):
            q = vor[k]["q"] & nach[k]["q"]
            if q.sum() < 10:
                continue
            a_, c_ = vor[k]["treffer"][q].astype(float), nach[k]["treffer"][q].astype(float)
            namen_c, inv = np.unique(cla[q], return_inverse=True)
            zieh = rng.integers(0, len(namen_c), (1000, len(namen_c)))
            diff = np.bincount(inv, weights=c_ - a_, minlength=len(namen_c))[zieh].sum(1) / np.bincount(inv, minlength=len(namen_c))[zieh].sum(1)
            res[k] = {"anfragen": int(q.sum()), "vorher": float(a_.mean()), "nachher": float(c_.mean()), "zufall": vor[k]["zufall"],
                      "aenderung_95": [float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5))]}
            r = res[k]
            print(f"      {t:42s} n={r['anfragen']:4d}: vorher {r['vorher']:.1%} -> nachher {r['nachher']:.1%} "
                  f"(Aenderung [{r['aenderung_95'][0]:+.1%}, {r['aenderung_95'][1]:+.1%}]; Zufallsnachbar {r['zufall']:.1%})")
        return res

    out["echt"] = vergleich(Z, b, "A  echte Bearbeiter")
    cnamen, erst = np.unique(np.array(cl), return_index=True)
    cinv = np.searchsorted(cnamen, np.array(cl))
    fb = np.array([f"{x}:{'AB'[int(rng.integers(0, 2))]}" for x in g[erst]])[cinv]
    for staerke in (0.0, 0.5):
        Zk = Z.copy()
        richtung = np.zeros(bt.N_MERK)
        richtung[rng.choice(bt.N_MERK, 30, replace=False)] = staerke
        Zk[np.char.endswith(fb, ":A")] += richtung
        out[f"kontrolle_{staerke}"] = vergleich(Zk, fb, f"   Kontrolle, erfundene Bearbeiter, Effekt {staerke:.1f}")

    if ebene == "zeichen":
        print("   B  Austauschbare Zeichenpaare: Anteil der zweiten Schreibung je Bearbeiter (Zellen mit mindestens 5 Abschnitten)")
        zaehl = collections.defaultdict(collections.Counter)
        for a, f in zip(ch, folgen):
            zaehl[(a["c"], a["o"])].update(f)
        nsek = collections.Counter((a["c"], a["o"]) for a in ch)
        out["paare"] = {}
        for s1, s2, titel in PAARE:
            zeile = {}
            for z, c in sorted(zaehl.items()):
                if nsek[z] >= 5 and c[s1] + c[s2] >= 30:
                    zeile[f"{bt.NAMEN.get(z[0], z[0])} / {z[1]}"] = {"anteil_zweite": c[s2] / (c[s1] + c[s2]), "n": c[s1] + c[s2]}
            out["paare"][f"{s1}/{s2}"] = zeile
            print(f"      {s1}/{s2} ({titel}): " + "; ".join(f"{k.split(' / ')[0][:10]} [{k.split(' / ')[1][-22:]}] {v['anteil_zweite']:.0%} (n={v['n']})" for k, v in zeile.items()))

    if schrift:
        s = []
        for a in ch:
            c = collections.Counter()
            for h, n in a["hs"].items():
                c[schrift.get(h, "unbekannt")] += n
            s.append(c.most_common(1)[0][0])
        s = np.array(s)
        D = cdist(Z, Z, "cityblock") / bt.N_MERK
        J = np.eye(N) - 1 / N
        Gm = -0.5 * J @ (D ** 2) @ J
        sst = float(np.trace(Gm))
        XG, XB, XS = bt.klassen(g.tolist()), bt.klassen(b.tolist()), bt.klassen(s.tolist())

        def r2(teile):
            U = bt.basis(teile)
            r = float(np.sum(U * (Gm @ U)) / sst)
            return r, 1 - (1 - r) * (N - 1) / (N - U.shape[1] - 1)

        m = {k: r2(t) for k, t in (("S", [XS]), ("GZ", [XG, XZ]), ("GZB", [XG, XZ, XB]), ("GZS", [XG, XZ, XS]), ("GZBS", [XG, XZ, XB, XS]))}
        cla = np.array(cl)
        cnamen, erst = np.unique(cla, return_index=True)
        cinv = np.searchsorted(cnamen, cla)
        cb = b[erst]
        schicht = np.array([f"{x}|{y}|{w}" for x, y, w in zip(g[erst], ep[erst], s[erst])])
        null = []
        for _ in range(bt.PERM):
            neu = cb.copy()
            for sc in set(schicht.tolist()):
                ii = np.flatnonzero(schicht == sc)
                if len(ii) > 1:
                    neu[ii] = cb[ii][rng.permutation(len(ii))]
            null.append(r2([XG, XZ, bt.klassen(neu[cinv].tolist()), XS])[0] - m["GZS"][0])
        null = np.array(null)
        roh = m["GZBS"][0] - m["GZS"][0]
        out["schriftart"] = {"abschnitte_je_schriftart": dict(collections.Counter(s.tolist())), "schriftart_allein": m["S"][1],
                             "bearbeiter_eigen_ohne_schriftart": m["GZB"][1] - m["GZ"][1], "bearbeiter_eigen_mit_schriftart": m["GZBS"][1] - m["GZS"][1],
                             "schriftart_eigen": m["GZBS"][1] - m["GZB"][1], "schriftart_neben_gruppe_und_zeit": m["GZS"][1] - m["GZ"][1],
                             "test_bearbeiter": {"roh": roh, "vertauscht_mittel": float(null.mean()), "p": float((1 + (null >= roh).sum()) / (bt.PERM + 1))}}
        r = out["schriftart"]
        print(f"   C  Schriftart: Abschnitte {r['abschnitte_je_schriftart']}; Schriftart allein erklaert {r['schriftart_allein']:.1%}")
        print(f"      eigener Bearbeiteranteil ohne Schriftart im Modell {r['bearbeiter_eigen_ohne_schriftart']:.1%}, mit Schriftart {r['bearbeiter_eigen_mit_schriftart']:.1%} "
              f"(roh {roh:.2%} gegen Vertauschung {null.mean():.2%}, p = {r['test_bearbeiter']['p']:.3f})")
        print(f"      Schriftart zusaetzlich zu Textgruppe und Zeit {r['schriftart_neben_gruppe_und_zeit']:.1%}, zusaetzlich auch zum Bearbeiter {r['schriftart_eigen']:.1%}")
    return out


def main():
    texte = bt.lade(sys.argv[1], sys.argv[2])
    rng = np.random.default_rng(bt.PROTOKOLL["seed"] + 5)
    schrift = schriftarten(sys.argv[4], sys.argv[2]) if len(sys.argv) > 4 else None
    erg = {"wort": lauf("WORTEBENE", texte, "wort", rng, schrift), "zeichen": lauf("ZEICHENEBENE", texte, "zeichen", rng, schrift)}
    json.dump(erg, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("\ngeschrieben:", sys.argv[3])


if __name__ == "__main__":
    main()
