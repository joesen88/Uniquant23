"""Buendel auftrennen: Welchen Anteil an der Delta-Struktur haben Textgruppe, Zeit und Bearbeiter?

Aufruf: python3 -I buendel_test.py <tokens.jsonl.gz> <zeit_schicht.jsonl.gz> <ergebnis.json> [merkmal_namen.json]

Das PROTOKOLL wurde vor dem ersten Lauf festgelegt.
"""
import collections
import gzip
import hashlib
import json
import os
import sys

import numpy as np
from scipy.spatial.distance import cdist

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import delta_test as dt  # noqa: E402

PROTOKOLL = {
    "einheit": "Abschnitt aus 1000 Woertern, je Zelle (Textgruppe, Bearbeiter) in Datierungsreihenfolge gebildet; "
               "gemischte Abschnitte, deren Handschriften mehr als 150 Jahre auseinanderliegen, entfallen",
    "aufnahme": "nur Texte mit brauchbarer Datierung; Textgruppen mit mindestens 5 und Bearbeiter mit mindestens 3 Abschnitten",
    "ebenen": {"wort": "Lemma-IDs", "zeichen": "Gardiner-Codes (Varianten zusammengelegt), Woerter mit vollstaendiger Schreibung"},
    "merkmale": "die 150 haeufigsten, z-Werte ueber alle Abschnitte, Burrows' Delta",
    "faktoren": {"G": "Textgruppe (Teilkorpus)", "Z": "Zeit: Datum des Abschnitts, natuerlicher kubischer Spline mit 5 Knoten",
                 "B": "Bearbeiter"},
    "zerlegung": "abstandsbasiert auf der Delta-Matrix (Gower-zentriert, Spur der Hutmatrix); eigene und gemeinsame Anteile "
                 "aus dem korrigierten R2 der sieben Modelle; Gegenrechnung euklidisch auf den z-Werten",
    "test": "eigener Anteil eines Faktors gegen 999 Vertauschungen seiner Werte zwischen Handschriften, jeweils innerhalb der "
            "Schichten der beiden anderen Faktoren (Zeit dafuer in vier Epochen)",
    "bereinigung": "Modell z ~ Zelle(Textgruppe, Bearbeiter) + Spline(Zeit). Abgezogen wird die Abweichung der Zelle vom Mittel "
                   "der Bearbeiter derselben Textgruppe, geschaetzt ohne die Handschriften des jeweiligen Zehntels. "
                   "Textgruppen mit einem einzigen Bearbeiter bleiben unveraendert",
    "pruefgroessen": ["Textgruppe wiedererkannt (alle Kandidaten)", "Textgruppe, nur fremde Bearbeiter zugelassen",
                      "Bearbeiter bei gleicher Textgruppe und Epoche"],
    "vorhersagen": {"V1": "Der gemeinsame, nicht zuordenbare Anteil ist auf beiden Ebenen groesser als jeder eigene Anteil",
                    "V2": "Der eigene Bearbeiteranteil ist auf beiden Ebenen groesser als bei Vertauschung (p < 0.01) und im "
                          "Verhaeltnis zum eigenen Textgruppenanteil auf der Zeichenebene groesser als auf der Wortebene",
                    "V3": "Nach der Bereinigung faellt die Bearbeiter-Erkennung Richtung Zufall, und die Textgruppe wird ueber "
                          "Bearbeitergrenzen besser erkannt",
                    "dagegen": "eigener Bearbeiteranteil nicht von Vertauschungen zu unterscheiden"},
    "seed": 20261114,
}
L, N_MERK, TAU, PERM = 1000, 150, 0.05, 999
NAMEN = {"tb": "Totenbuch", "bbawpyramidentexte": "Pyramidentexte", "sawlit": "Literatur", "sawmedizin": "Medizin",
         "bbawbriefe": "Briefe", "bbawgrabinschriften": "Grabinschriften", "bbawtotenlit": "Spaete Totenliteratur",
         "bbawramessiden": "Ramessidische Inschriften", "bbawamarna": "Amarna", "bbawarchive": "Archive",
         "bbawtempelbib": "Tempelbibliothek", "bbawhistbiospzt": "Hist.-biogr. Spaetzeit"}


def epoche(d):
    return "AR" if d <= -2050 else "MR" if d <= -1550 else "NR" if d <= -1070 else "SpZ"


def lade(tok_pfad, zeit_pfad):
    meta = {}
    for z in gzip.open(zeit_pfad, "rt", encoding="utf-8"):
        t = json.loads(z)
        if t["nb"] is None or (t["nb"] == 1 and t["na"] == 1) or t["na"] - t["nb"] > 450:
            continue
        meta[t["t"]] = (t["o"], t["hs"], t["nb"], t["na"])
    out = []
    for z in gzip.open(tok_pfad, "rt", encoding="utf-8"):
        t = json.loads(z)
        if t["t"] in meta:
            o, hs, nb, na = meta[t["t"]]
            out.append({"c": t["c"], "o": o, "hs": hs, "d": (nb + na) / 2, "tok": t["tok"]})
    return out


def abschnitte(texte, ebene):
    zellen = collections.OrderedDict()
    for t in texte:
        if ebene == "zeichen":
            tok = [(lid, s) for lid, s in ((lid, dt.zeichen(h, True) if h else []) for lid, h in t["tok"]) if s]
        else:
            tok = [(lid, None) for lid, _ in t["tok"]]
        e = zellen.setdefault((t["c"], t["o"]), collections.OrderedDict()).setdefault(t["hs"], {"d": t["d"], "tok": []})
        e["tok"].extend(tok)
    out = []
    for (c, o), hss in zellen.items():
        pool = []
        for hs in sorted(hss, key=lambda h: (hss[h]["d"], h)):
            tok = hss[hs]["tok"]
            k = len(tok) // L
            for i in range(k):
                out.append({"c": c, "o": o, "hs": {hs: L}, "cluster": "H:" + hs, "d": hss[hs]["d"], "spanne": 0.0, "tok": tok[i * L:(i + 1) * L]})
            pool.extend((hs, x) for x in tok[k * L:])
        for i in range(len(pool) // L):
            teil = pool[i * L:(i + 1) * L]
            gew = collections.Counter(h for h, _ in teil)
            tage = [hss[h]["d"] for h in gew]
            out.append({"c": c, "o": o, "hs": dict(gew), "cluster": f"P:{c}:{o}:{i}", "spanne": max(tage) - min(tage),
                        "d": sum(hss[h]["d"] * n for h, n in gew.items()) / L, "tok": [x for _, x in teil]})
    out = [a for a in out if a["spanne"] <= 150]
    for _ in range(3):
        ng, nb = collections.Counter(a["c"] for a in out), collections.Counter(a["o"] for a in out)
        out = [a for a in out if ng[a["c"]] >= 5 and nb[a["o"]] >= 3]
    return out


def klassen(labels):
    namen = sorted(set(labels))
    X = np.zeros((len(labels), len(namen)))
    X[np.arange(len(labels)), [namen.index(v) for v in labels]] = 1
    return X[:, 1:]


def spline(x, kn):
    x = np.asarray(x, float)

    def d(k):
        return (np.clip(x - kn[k], 0, None) ** 3 - np.clip(x - kn[-1], 0, None) ** 3) / (kn[-1] - kn[k])

    X = np.column_stack([x] + [d(k) - d(len(kn) - 2) for k in range(len(kn) - 2)])
    return (X - X.mean(0)) / X.std(0)


def basis(teile):
    X = np.hstack(teile)
    X = X - X.mean(0)
    U, s, _ = np.linalg.svd(X, full_matrices=False)
    return U[:, s > 1e-9 * s[0]]


def zerlege(XG, XZ, XB, Gm):
    sst, N = float(np.trace(Gm)), Gm.shape[0]
    R = {}
    for name, teile in (("G", [XG]), ("Z", [XZ]), ("B", [XB]), ("GZ", [XG, XZ]), ("GB", [XG, XB]), ("ZB", [XZ, XB]), ("GZB", [XG, XZ, XB])):
        U = basis(teile)
        r = float(np.sum(U * (Gm @ U)) / sst)
        R[name] = (r, 1 - (1 - r) * (N - 1) / (N - U.shape[1] - 1), int(U.shape[1]))
    a = {k: v[1] for k, v in R.items()}
    T = a["GZB"]
    f = {"G": T - a["ZB"], "Z": T - a["GB"], "B": T - a["GZ"],
         "G+Z": a["GB"] + a["ZB"] - a["B"] - T, "G+B": a["GZ"] + a["ZB"] - a["Z"] - T, "Z+B": a["GZ"] + a["GB"] - a["G"] - T}
    f["G+Z+B"] = T - sum(f.values())
    f["rest"] = 1 - T
    roh = {"G": R["GZB"][0] - R["ZB"][0], "Z": R["GZB"][0] - R["GB"][0], "B": R["GZB"][0] - R["GZ"][0]}
    return f, R, roh


def nachbar_tests(D, E, g, b, ep):
    """Trefferquoten des naechsten Nachbarn fuer die drei Pruefgroessen; liefert auch die Einzeltreffer."""
    N = len(g)
    idx = np.arange(N)
    gl_g, gl_b, gl_e = g[:, None] == g[None, :], b[:, None] == b[None, :], ep[:, None] == ep[None, :]
    out = {}
    for name, El, ziel, informativ in (("textgruppe", E, gl_g, False), ("textgruppe_fremde_bearbeiter", E & ~gl_b, gl_g, False),
                                       ("bearbeiter_gleiche_gruppe_epoche", E & gl_g & gl_e, gl_b, True),
                                       ("textgruppe_gleicher_bearbeiter", E & gl_b, gl_g, True)):
        zahl = El.sum(1)
        p = np.divide((ziel & El).sum(1), zahl, out=np.zeros(N), where=zahl > 0)
        q = (zahl > 0) & (p > 0) & ((p < 1) if informativ else True)
        nn = np.where(El, D, np.inf).argmin(1)
        out[name] = {"q": q, "treffer": ziel[idx, nn], "zufall": float(p[q].mean()) if q.any() else None}
    return out


def bereinige(Z, zelle, XZ, cluster, falten=10):
    N = len(zelle)
    zellen = sorted(set(zelle))
    pos = {z: i for i, z in enumerate(zellen)}
    C = np.zeros((N, len(zellen)))
    C[np.arange(N), [pos[z] for z in zelle]] = 1
    falte = np.array([int(hashlib.sha1(c.encode()).hexdigest(), 16) % falten for c in cluster])
    Zb, unveraendert = Z.copy(), 0
    for f in range(falten):
        tr, te = falte != f, np.flatnonzero(falte == f)
        gesehen = np.flatnonzero(C[tr].sum(0) > 0)
        beta = np.linalg.lstsq(np.hstack([C[tr][:, gesehen], XZ[tr]]), Z[tr], rcond=None)[0]
        mu = {zellen[k]: beta[j] for j, k in enumerate(gesehen)}
        je_g = collections.defaultdict(list)
        for z, m in mu.items():
            je_g[z[0]].append(m)
        for i in te:
            z = zelle[i]
            if z in mu and len(je_g[z[0]]) >= 2:
                Zb[i] = Z[i] - (mu[z] - np.mean(je_g[z[0]], 0))
            else:
                unveraendert += 1
    return Zb, unveraendert


def untersuche(name, texte, ebene, rng, namen=None, kontrolle=False):
    ch = abschnitte(texte, ebene)
    N = len(ch)
    g = np.array([a["c"] for a in ch])
    b = np.array([a["o"] for a in ch])
    d = np.array([a["d"] for a in ch])
    cl = np.array([a["cluster"] for a in ch])
    ep = np.array([epoche(v) for v in d])
    folgen = [[x[0] for x in a["tok"]] if ebene == "wort" else [s for x in a["tok"] for s in x[1]] for a in ch]
    F, vok = dt.haeufigkeiten(folgen)
    order = np.argsort(-F.sum(0), kind="stable")[:N_MERK]
    X = F[:, order]
    Z = (X - X.mean(0)) / X.std(0, ddof=1)
    D = cdist(Z, Z, "cityblock") / N_MERK
    hs_all = sorted({h for a in ch for h in a["hs"]})
    pos = {h: i for i, h in enumerate(hs_all)}
    W = np.zeros((N, len(hs_all)))
    for i, a in enumerate(ch):
        for h in a["hs"]:
            W[i, pos[h]] = 1
    E = ~((W @ W.T) > 0) & (dt.ueberlappung(ch) <= TAU)
    out = {"abschnitte": N, "textgruppen": dict(collections.Counter(g.tolist())), "bearbeiter": dict(collections.Counter(b.tolist())),
           "cluster": int(len(set(cl.tolist()))), "zellen": len({(x, y) for x, y in zip(g, b)})}
    print(f"\n=== {name}: {N} Abschnitte, {len(set(g))} Textgruppen, {len(set(b))} Bearbeiter, {out['zellen']} Zellen, {out['cluster']} Cluster ===")
    print("   Textgruppen:", {NAMEN.get(k, k): v for k, v in collections.Counter(g.tolist()).most_common()})
    print("   Bearbeiter :", dict(collections.Counter(b.tolist()).most_common()))

    kn = np.unique(np.percentile(d, [5, 27.5, 50, 72.5, 95]))
    out["knoten"] = [float(v) for v in kn]
    XG, XB, XZ = klassen(g.tolist()), klassen(b.tolist()), spline(d, kn)
    J = np.eye(N) - 1 / N
    Gm = -0.5 * J @ (D ** 2) @ J
    f, R, roh = zerlege(XG, XZ, XB, Gm)
    Zc = Z - Z.mean(0)
    fe, _, _ = zerlege(XG, XZ, XB, Zc @ Zc.T)
    out["zerlegung"] = f
    out["zerlegung_euklidisch"] = fe
    out["modelle"] = {k: {"r2": v[0], "r2_korrigiert": v[1], "parameter": v[2]} for k, v in R.items()}
    print("   Zerlegung der Delta-Struktur (korrigierte Anteile; in Klammern euklidische Gegenrechnung):")
    for k, titel in (("G", "nur Textgruppe"), ("Z", "nur Zeit"), ("B", "nur Bearbeiter"), ("G+Z", "Textgruppe und Zeit gemeinsam"),
                     ("G+B", "Textgruppe und Bearbeiter gemeinsam"), ("Z+B", "Zeit und Bearbeiter gemeinsam"),
                     ("G+Z+B", "alle drei gemeinsam"), ("rest", "nicht erklaert")):
        print(f"      {titel:36s} {f[k]:6.1%}  ({fe[k]:6.1%})")
    print(f"      erklaert insgesamt {1 - f['rest']:.1%}; Modelle einzeln: Textgruppe {R['G'][1]:.1%}, Zeit {R['Z'][1]:.1%}, Bearbeiter {R['B'][1]:.1%}")

    # Vertauschungstests auf Handschriftenebene
    cnamen, erst = np.unique(cl, return_index=True)
    cinv = np.searchsorted(cnamen, cl)
    cg, cb, cd, ce = g[erst], b[erst], np.array([d[cl == c].mean() for c in cnamen]), ep[erst]

    def vertausche(werte, schicht):
        neu = werte.copy()
        for s in set(schicht):
            ii = np.flatnonzero(np.array(schicht) == s)
            if len(ii) > 1:
                neu[ii] = werte[ii][rng.permutation(len(ii))]
        return neu

    U_ZB, U_GB, U_GZ = basis([XZ, XB]), basis([XG, XB]), basis([XG, XZ])
    sst = float(np.trace(Gm))
    r_ohne = {"G": float(np.sum(U_ZB * (Gm @ U_ZB)) / sst), "Z": float(np.sum(U_GB * (Gm @ U_GB)) / sst), "B": float(np.sum(U_GZ * (Gm @ U_GZ)) / sst)}
    out["test"] = {}
    for fak in ("G", "Z", "B"):
        null = []
        schicht = {"G": [f"{x}|{y}" for x, y in zip(cb, ce)], "Z": [f"{x}|{y}" for x, y in zip(cg, cb)], "B": [f"{x}|{y}" for x, y in zip(cg, ce)]}[fak]
        beweglich = sum(1 for s in set(schicht) if len({(cg, cd, cb)[("G", "Z", "B").index(fak)][i] for i in np.flatnonzero(np.array(schicht) == s)}) > 1)
        for _ in range(PERM):
            if fak == "G":
                U = basis([klassen(vertausche(cg, schicht)[cinv].tolist()), XZ, XB])
            elif fak == "Z":
                U = basis([XG, spline(vertausche(cd, schicht)[cinv], kn), XB])
            else:
                U = basis([XG, XZ, klassen(vertausche(cb, schicht)[cinv].tolist())])
            null.append(float(np.sum(U * (Gm @ U)) / sst) - r_ohne[fak])
        null = np.array(null)
        out["test"][fak] = {"eigener_anteil_roh": roh[fak], "vertauscht_mittel": float(null.mean()), "vertauscht_95": float(np.percentile(null, 95)),
                            "p": float((1 + (null >= roh[fak]).sum()) / (PERM + 1)), "schichten_mit_auswahl": int(beweglich)}
        t = out["test"][fak]
        print(f"   Test eigener Anteil {dict(G='Textgruppe', Z='Zeit', B='Bearbeiter')[fak]:11s}: {roh[fak]:.2%} gegen Vertauschung {t['vertauscht_mittel']:.2%} "
              f"(95 %: {t['vertauscht_95']:.2%}), p = {t['p']:.3f}; Schichten mit Auswahl: {beweglich}")

    # Bereinigter Abstand
    zelle = list(zip(g.tolist(), b.tolist()))
    Zb, unv = bereinige(Z, zelle, XZ, cl.tolist())
    Db = cdist(Zb, Zb, "cityblock") / N_MERK
    vor, nach = nachbar_tests(D, E, g, b, ep), nachbar_tests(Db, E, g, b, ep)
    out["bereinigung"] = {"unveraendert": int(unv)}
    print(f"   Bereinigung: {N - unv} von {N} Abschnitten angepasst (die uebrigen liegen in Textgruppen mit einem Bearbeiter oder in neuen Zellen)")
    for k, titel in (("textgruppe", "Textgruppe wiedererkannt"), ("textgruppe_fremde_bearbeiter", "Textgruppe, nur fremde Bearbeiter"),
                     ("bearbeiter_gleiche_gruppe_epoche", "Bearbeiter bei gleicher Gruppe und Epoche"),
                     ("textgruppe_gleicher_bearbeiter", "Textgruppe bei gleichem Bearbeiter")):
        q = vor[k]["q"] & nach[k]["q"]
        if q.sum() < 10:
            continue
        a, c_ = vor[k]["treffer"][q].astype(float), nach[k]["treffer"][q].astype(float)
        namen_c, inv = np.unique(cl[q], return_inverse=True)
        zieh = rng.integers(0, len(namen_c), (1000, len(namen_c)))
        zahl = np.bincount(inv, minlength=len(namen_c))
        diff = (np.bincount(inv, weights=c_ - a, minlength=len(namen_c))[zieh].sum(1)) / zahl[zieh].sum(1)
        out["bereinigung"][k] = {"anfragen": int(q.sum()), "vorher": float(a.mean()), "nachher": float(c_.mean()), "zufall": vor[k]["zufall"],
                                 "aenderung_95": [float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5))]}
        r = out["bereinigung"][k]
        print(f"      {titel:42s} n={r['anfragen']:4d}: vorher {r['vorher']:.1%} -> nachher {r['nachher']:.1%} "
              f"(Aenderung [{r['aenderung_95'][0]:+.1%}, {r['aenderung_95'][1]:+.1%}]; Zufallsnachbar {r['zufall']:.1%})")

    # Merkmale mit dem groessten eigenen Anteil je Faktor (einzeln, euklidisch)
    def anteil(teile):
        U = basis(teile)
        r = ((U.T @ Zc) ** 2).sum(0) / (Zc ** 2).sum(0)
        return 1 - (1 - r) * (N - 1) / (N - U.shape[1] - 1)

    voll = anteil([XG, XZ, XB])
    eigen = {"B": voll - anteil([XG, XZ]), "Z": voll - anteil([XG, XB]), "G": voll - anteil([XZ, XB])}
    art = "lemma" if ebene == "wort" else "zeichen"
    out["merkmale"] = {}
    for fak, titel in (("B", "Bearbeiter"), ("Z", "Zeit"), ("G", "Textgruppe")):
        top = np.argsort(-eigen[fak])[:12]
        out["merkmale"][fak] = [{"merkmal": vok[order[j]], "name": (namen or {}).get(art, {}).get(vok[order[j]]), "eigener_anteil": float(eigen[fak][j]),
                                 "rang": int(j) + 1} for j in top]
        print(f"   groesster eigener Anteil {titel}: " + ", ".join(
            f"{vok[order[j]]}" + (f" ({'/'.join(n_) if isinstance(n_, list) else n_})" if (n_ := (namen or {}).get(art, {}).get(vok[order[j]])) else "")
            + f" {eigen[fak][j]:.0%}" for j in top[:10]))
    out["merkmale_mittel"] = {k: float(v.mean()) for k, v in eigen.items()}

    if kontrolle:
        # Kontrolle: erfundene Bearbeiter (zufaellig je Handschrift innerhalb der Textgruppe), erst ohne, dann mit kuenstlichem Effekt
        print("   Kontrolle mit erfundenen Bearbeitern (je Handschrift zufaellig A oder B innerhalb der Textgruppe):")
        fb = np.array([f"{x}:{'AB'[int(rng.integers(0, 2))]}" for x in cg])[cinv]
        XF = klassen(fb.tolist())
        for staerke in (0.0, 0.5):
            Zk = Z.copy()
            richtung = np.zeros(N_MERK)
            richtung[rng.choice(N_MERK, 30, replace=False)] = staerke
            Zk[np.char.endswith(fb, ":A")] += richtung
            Dk = cdist(Zk, Zk, "cityblock") / N_MERK
            Gk = -0.5 * J @ (Dk ** 2) @ J
            fk, _, rohk = zerlege(XG, XZ, XF, Gk)
            Zkb, _ = bereinige(Zk, list(zip(g.tolist(), fb.tolist())), XZ, cl.tolist())
            v_, n_ = nachbar_tests(Dk, E, g, fb, ep), nachbar_tests(cdist(Zkb, Zkb, "cityblock") / N_MERK, E, g, fb, ep)
            q = v_["bearbeiter_gleiche_gruppe_epoche"]["q"] & n_["bearbeiter_gleiche_gruppe_epoche"]["q"]
            out.setdefault("kontrolle", {})[str(staerke)] = {"eigener_anteil": fk["B"], "vorher": float(v_["bearbeiter_gleiche_gruppe_epoche"]["treffer"][q].mean()),
                                                           "nachher": float(n_["bearbeiter_gleiche_gruppe_epoche"]["treffer"][q].mean()),
                                                           "zufall": v_["bearbeiter_gleiche_gruppe_epoche"]["zufall"]}
            k = out["kontrolle"][str(staerke)]
            print(f"      Effekt {staerke:.1f} Standardabweichungen auf 30 Merkmalen: eigener Anteil {fk['B']:+.2%}; erfundener Bearbeiter erkannt "
                  f"vorher {k['vorher']:.1%}, nachher {k['nachher']:.1%} (Zufallsnachbar {k['zufall']:.1%})")
    return out


def main():
    tok_pfad, zeit_pfad, ziel = sys.argv[1], sys.argv[2], sys.argv[3]
    namen = json.load(open(sys.argv[4], encoding="utf-8")) if len(sys.argv) > 4 else None
    print("PROTOKOLL sha256:", hashlib.sha256(json.dumps(PROTOKOLL, sort_keys=True).encode()).hexdigest()[:16])
    texte = lade(tok_pfad, zeit_pfad)
    rng = np.random.default_rng(PROTOKOLL["seed"])
    erg = {"protokoll": PROTOKOLL,
           "wort": untersuche("WORTEBENE", texte, "wort", rng, namen, kontrolle=True),
           "zeichen": untersuche("ZEICHENEBENE", texte, "zeichen", rng, namen, kontrolle=True)}
    json.dump(erg, open(ziel, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("\ngeschrieben:", ziel)


if __name__ == "__main__":
    main()
