"""Schritt 2: Burrows' Delta am AES-Korpus testen.

Aufruf: python3 -I delta_test.py <tokens.jsonl.gz> <ergebnis.json>

Das PROTOKOLL unten wurde festgelegt, bevor die erste Distanz gerechnet war.
Delta(A,B) = (1/n) * Summe_i |z_i(A) - z_i(B)|,  z_i(X) = (f_i(X) - mu_i) / sigma_i,
mu_i und sigma_i ueber die Abschnitte des Vergleichskorpus.
"""
import collections
import gzip
import hashlib
import json
import re
import statistics
import sys

import numpy as np
from scipy.spatial.distance import cdist
from scipy.stats import spearmanr

PROTOKOLL = {
    "einheit": "Abschnitt aus L aufeinanderfolgenden Woertern; lange Texte ergeben reine Abschnitte, "
               "Reste und kurze Texte werden je Teilkorpus in Dateireihenfolge aneinandergehaengt",
    "ebenen": {"wort": "Lemma-IDs (Deutungsschicht), alle Teilkorpora",
               "zeichen": "Gardiner-Codes (Schriftschicht, ohne Lesung), nur Woerter mit vollstaendiger Schreibung",
               "wort_gepaart": "Lemma-IDs derselben Woerter wie auf der Zeichenebene"},
    "primaer": {"L": 1000, "n": 150, "distanz": "burrows", "zeichen": "zusammengelegt", "tau": 0.05},
    "robustheit": {"n": [30, 50, 100, 150, 300, 500], "distanz": ["burrows", "cosinus", "roh_l1"],
                   "L": [500, 1000, 2000], "tau": [0.01, 0.05, 0.20, None], "zeichen": ["zusammengelegt", "roh"]},
    "ausschluss": "Kandidaten mit gemeinsamem Text immer; streng zusaetzlich Kandidaten, die mehr als tau der "
                  "Lemma-5-Gramme teilen (Parallelueberlieferung, Formeln)",
    "min_abschnitte_je_teilkorpus": 5,
    "tests": {"T_text": "naechster Nachbar stammt aus demselben Text (bekannte Antwort)",
              "T_gattung": "naechster Nachbar (streng) hat dasselbe Teilkorpus",
              "T_fremdbearbeiter": "wie T_gattung, Kandidaten desselben Bearbeiters ausgeschlossen",
              "T_fremdepoche": "wie T_gattung, Kandidaten derselben Datierungsklasse ausgeschlossen",
              "N_zufallsnachbar": "Trefferquote bei zufaelligem zulaessigem Nachbarn",
              "N_wortmischung": "alle Woerter ueber alle Abschnitte gemischt, Etiketten bleiben"},
    "kriterien": {"K1": "T_text mindestens das Zehnfache des Zufallsnachbarn",
                  "K2": "T_gattung ueber Mehrheitsklasse und Zufallsnachbar, p < 0.001",
                  "K3": "N_wortmischung nicht ueber der Mehrheitsklasse",
                  "K4": "anderes Vergleichskorpus aendert bei mehr als 5 % der Abschnitte den naechsten Nachbarn"},
    "auswahlkontrolle": "beste Kombination aus n x Distanz auf Haelfte A der Texte bestimmt, auf Haelfte B berichtet",
    "seed": 20261112,
}

G = re.compile(r"^((?:Aa|Ff|NL|NU|[A-Z])\d+)([A-Za-z]*)$")
US = re.compile(r"^US\d+((?:Aa|[A-Z])\d+)[A-Za-z]*$")


def zeichen(h, zusammengelegt):
    """Feld 'hiero' -> Liste von Zeichencodes. Ziffern sind Zahlzeichen (Einer Z1, Zehner V20, Hunderter V1)."""
    out = []
    for x in h.split("-"):
        x = x.strip("_")
        if not x:
            continue
        if x.isdigit():
            v = int(x)
            if 1 <= v <= 9:
                out += ["Z1"] * v
            elif 10 <= v <= 90 and v % 10 == 0:
                out += ["V20"] * (v // 10)
            elif 100 <= v <= 900 and v % 100 == 0:
                out += ["V1"] * (v // 100)
            continue
        m = US.match(x) or G.match(x)
        if m:
            out.append(m.group(1) if zusammengelegt else x)
    return out


def lade(pfad):
    return [json.loads(z) for z in gzip.open(pfad, "rt", encoding="utf-8")]


def abschnitte(texte, L, nur_mit_zeichen, zusammengelegt=True):
    """Liefert Abschnitte: dict(c, texte, bearb, datum, rein, cluster, lem, sig)."""
    out = []
    je_korpus = collections.OrderedDict()
    for t in texte:
        je_korpus.setdefault(t["c"], []).append(t)
    for c, ts in je_korpus.items():
        pool = []
        for t in ts:
            if nur_mit_zeichen:
                tok = []
                for lid, h in t["tok"]:
                    s = zeichen(h, zusammengelegt) if h else []
                    if s:
                        tok.append((lid, s))
            else:
                tok = [(lid, None) for lid, _ in t["tok"]]
            k = len(tok) // L
            for i in range(k):
                out.append({"c": c, "texte": {t["t"]}, "bearb": {t["o"]}, "datum": {t["d"]}, "rein": True,
                            "cluster": "T:" + t["t"], "tok": tok[i * L:(i + 1) * L]})
            for x in tok[k * L:]:
                pool.append((t, x))
        for i in range(len(pool) // L):
            teil = pool[i * L:(i + 1) * L]
            out.append({"c": c, "texte": {t["t"] for t, _ in teil}, "bearb": {t["o"] for t, _ in teil},
                        "datum": {t["d"] for t, _ in teil}, "rein": False, "cluster": f"P:{c}:{i}",
                        "tok": [x for _, x in teil]})
    return out


def filtere(chunks, minimum):
    n = collections.Counter(ch["c"] for ch in chunks)
    return [ch for ch in chunks if n[ch["c"]] >= minimum]


def haeufigkeiten(folgen, v_max=3000):
    """Relative Haeufigkeiten je Abschnitt fuer die v_max insgesamt haeufigsten Merkmale."""
    gesamt = collections.Counter()
    je = [collections.Counter(f) for f in folgen]
    for c in je:
        gesamt.update(c)
    vok = [w for w, _ in gesamt.most_common(v_max)]
    idx = {w: i for i, w in enumerate(vok)}
    F = np.zeros((len(folgen), len(vok)))
    for r, (c, f) in enumerate(zip(je, folgen)):
        for w, k in c.items():
            i = idx.get(w)
            if i is not None:
                F[r, i] = k / len(f)
    return F, vok


def distanz(F, n, art, ref=None, merkmale=None):
    """Distanzmatrix. ref = Zeilenindex des Vergleichskorpus (None = alle Abschnitte)."""
    R = F if ref is None else F[ref]
    order = np.argsort(-R.sum(0), kind="stable")[:n] if merkmale is None else np.asarray(merkmale)
    X, Rr = F[:, order], R[:, order]
    if art == "roh_l1":
        return cdist(X, X, "cityblock") / len(order), order
    mu, sd = Rr.mean(0), Rr.std(0, ddof=1)
    ok = sd > 0
    Z = (X[:, ok] - mu[ok]) / sd[ok]
    if art == "burrows":
        return cdist(Z, Z, "cityblock") / ok.sum(), order[ok]
    if art == "cosinus":
        return cdist(Z, Z, "cosine"), order[ok]
    raise ValueError(art)


def teilt(chunks, feld):
    """Boolesche Matrix: Abschnitte i und j teilen einen Wert im Mengenfeld."""
    N = len(chunks)
    inv = collections.defaultdict(list)
    for i, ch in enumerate(chunks):
        for v in ch[feld]:
            inv[v].append(i)
    M = np.zeros((N, N), bool)
    for ids in inv.values():
        a = np.asarray(ids)
        M[np.ix_(a, a)] = True
    return M


def ueberlappung(chunks, k=5):
    """Anteil gemeinsamer Lemma-k-Gramme, bezogen auf den kleineren Abschnitt."""
    N = len(chunks)
    inv = collections.defaultdict(set)
    groesse = np.zeros(N)
    for i, ch in enumerate(chunks):
        lem = [x[0] for x in ch["tok"]]
        g = {tuple(lem[j:j + k]) for j in range(len(lem) - k + 1)}
        groesse[i] = len(g)
        for x in g:
            inv[x].add(i)
    S = np.zeros((N, N))
    for ids in inv.values():
        if len(ids) > 1:
            a = np.fromiter(ids, int)
            S[np.ix_(a, a)] += 1
    np.fill_diagonal(S, 0)
    return S / np.minimum.outer(groesse, groesse)


def werte(D, E, y, gleich=None, anfragen=None, cluster=None, rng=None, B=2000):
    """Naechster zulaessiger Nachbar je Anfrage; Treffer, wenn 'gleich' (Standard: gleiches Etikett)."""
    N = len(y)
    if gleich is None:
        gleich = y[None, :] == y[:, None]
    ziel = gleich & E
    q = E.any(1) & ziel.any(1)
    if anfragen is not None:
        q &= anfragen
    nn = np.where(E, D, np.inf).argmin(1)
    treffer = gleich[np.arange(N), nn]
    p_zufall = np.divide(ziel.sum(1), E.sum(1), out=np.zeros(N), where=E.sum(1) > 0)
    qi = np.flatnonzero(q)
    res = {"anfragen": int(q.sum()), "treffer": float(treffer[q].mean()) if qi.size else None,
           "zufallsnachbar": float(p_zufall[q].mean()) if qi.size else None}
    if qi.size == 0:
        return res, nn, q, treffer
    klassen = collections.Counter(y[q].tolist())
    res["mehrheitsklasse"] = max(klassen.values()) / q.sum()
    res["klassen"] = len(klassen)
    rec = [treffer[q & (y == k)].mean() for k in klassen]
    res["ausgewogen"] = float(np.mean(rec))
    if rng is not None:
        sim = (rng.random((B, qi.size)) < p_zufall[qi]).mean(1)
        res["p_zufall"] = float((1 + (sim >= res["treffer"]).sum()) / (B + 1))
        if cluster is not None:
            cl = np.asarray(cluster)[qi]
            namen, inv = np.unique(cl, return_inverse=True)
            summe = np.bincount(inv, weights=treffer[qi].astype(float), minlength=len(namen))
            zahl = np.bincount(inv, minlength=len(namen))
            zieh = rng.integers(0, len(namen), (B, len(namen)))
            boot = summe[zieh].sum(1) / zahl[zieh].sum(1)
            res["ki95"] = [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]
            res["cluster"] = int(len(namen))
    return res, nn, q, treffer


def kurz(r):
    if r.get("treffer") is None:
        return "keine auswertbaren Anfragen"
    s = f"Treffer {r['treffer']:.1%} (n={r['anfragen']}"
    if "ki95" in r:
        s += f", 95%-KI {r['ki95'][0]:.1%}-{r['ki95'][1]:.1%}, {r['cluster']} Cluster"
    s += f") | Zufallsnachbar {r['zufallsnachbar']:.1%}"
    if "mehrheitsklasse" in r:
        s += f" | Mehrheitsklasse {r['mehrheitsklasse']:.1%} | ausgewogen {r['ausgewogen']:.1%} bei {r['klassen']} Klassen"
    if "p_zufall" in r:
        s += f" | p {r['p_zufall']:.4f}"
    return s


def haelfte(cluster):
    return np.array([int(hashlib.sha1(c.encode()).hexdigest(), 16) % 2 == 0 for c in cluster])


def untersuche(name, chunks, ebene, rng, voll=True):
    """Alle Tests fuer einen Datensatz und eine Merkmalsebene ('lem' oder 'sig')."""
    P = PROTOKOLL["primaer"]
    N = len(chunks)
    y = np.array([ch["c"] for ch in chunks])
    cluster = [ch["cluster"] for ch in chunks]
    if ebene == "lem":
        folgen = [[x[0] for x in ch["tok"]] for ch in chunks]
    else:
        folgen = [[s for x in ch["tok"] for s in x[1]] for ch in chunks]
    F, vok = haeufigkeiten(folgen)
    T = teilt(chunks, "texte")
    S = ueberlappung(chunks)
    ich = np.eye(N, dtype=bool)

    def zulaessig(tau):
        E = ~T & ~ich
        if tau is not None:
            E &= S <= tau
        return E

    E = zulaessig(P["tau"])
    out = {"abschnitte": N, "merkmale_gesamt": len(vok),
           "je_teilkorpus": dict(collections.Counter(y.tolist())),
           "mittlere_laenge": float(np.mean([len(f) for f in folgen]))}
    print(f"\n=== {name}: {N} Abschnitte, {len(vok)} Merkmale, mittlere Laenge {out['mittlere_laenge']:.0f} ===")
    print("   je Teilkorpus:", dict(sorted(out["je_teilkorpus"].items(), key=lambda kv: -kv[1])))
    D, merk = distanz(F, P["n"], P["distanz"])
    out["top_merkmale"] = [vok[i] for i in merk[:25]]
    print("   haeufigste Merkmale:", " ".join(out["top_merkmale"][:20]))

    # T_text: bekannte Antwort
    rein = np.array([ch["rein"] for ch in chunks])
    zahl = collections.Counter(c for c, r in zip(cluster, rein) if r)
    mehrfach = np.array([r and zahl[c] >= 2 for c, r in zip(cluster, rein)])
    r, *_ = werte(D, ~ich, y, gleich=T & ~ich, anfragen=mehrfach, cluster=cluster, rng=rng)
    out["T_text"] = r
    print("   T_text      ", kurz(r))

    # T_gattung: streng und nur ohne gemeinsamen Text
    r, nn, q, treffer = werte(D, E, y, cluster=cluster, rng=rng)
    out["T_gattung"] = r
    print("   T_gattung   ", kurz(r))
    r2, *_ = werte(D, zulaessig(None), y, cluster=cluster, rng=rng)
    out["T_gattung_nur_textausschluss"] = r2
    print("   ..ohne tau  ", kurz(r2))
    je = {}
    for k in sorted(set(y.tolist())):
        m = q & (y == k)
        if m.any():
            ziel = collections.Counter(y[nn[m]].tolist())
            je[k] = {"anfragen": int(m.sum()), "treffer": float(treffer[m].mean()),
                     "haeufigste_antworten": ziel.most_common(3)}
    out["je_klasse"] = je
    for k, v in sorted(je.items(), key=lambda kv: -kv[1]["anfragen"]):
        print(f"      {k:22s} n={v['anfragen']:4d} Treffer {v['treffer']:6.1%}  -> {v['haeufigste_antworten']}")
    nicht = {k: int(((y == k) & ~q).sum()) for k in set(y.tolist()) if ((y == k) & ~q).any()}
    out["nicht_auswertbar"] = nicht
    print("      nicht auswertbar (kein zulaessiger Kandidat der eigenen Klasse):", nicht)

    # Bearbeiter- und Epochengrenze
    Bm = teilt(chunks, "bearb")
    Dm = teilt(chunks, "datum")
    unbekannt = np.array(["unknown" in ch["datum"] for ch in chunks])
    r, *_ = werte(D, E & ~Bm, y, cluster=cluster, rng=rng)
    out["T_fremdbearbeiter"] = r
    print("   T_fremdbearb", kurz(r))
    Ed = E & ~Dm & ~unbekannt[None, :]
    r, *_ = werte(D, Ed, y, anfragen=~unbekannt, cluster=cluster, rng=rng)
    out["T_fremdepoche"] = r
    print("   T_fremdepoch", kurz(r))
    # Gegenprobe: erkennt Delta den Bearbeiter, wenn die eigene Gattung ausgeschlossen ist?
    einzel = np.array([len(ch["bearb"]) == 1 for ch in chunks])
    yb = np.array([sorted(ch["bearb"])[0] for ch in chunks])
    gl = y[None, :] == y[:, None]
    r, *_ = werte(D, E & ~gl & einzel[None, :], yb, anfragen=einzel, cluster=cluster, rng=rng)
    out["T_bearbeiter_fremde_gattung"] = r
    print("   Bearbeiter ueber Gattungsgrenze", kurz(r))
    yd = np.array([sorted(ch["datum"])[0] for ch in chunks])
    eind = np.array([len(ch["datum"]) == 1 and "unknown" not in ch["datum"] for ch in chunks])
    r, *_ = werte(D, E & eind[None, :], yd, anfragen=eind, cluster=cluster, rng=rng)
    out["T_epoche"] = r
    print("   Epoche (alle Kandidaten)", kurz(r))
    r, *_ = werte(D, E & ~gl & eind[None, :], yd, anfragen=eind, cluster=cluster, rng=rng)
    out["T_epoche_fremde_gattung"] = r
    print("   Epoche ueber Gattungsgrenze", kurz(r))

    if not voll:
        return out, D, E, y, T

    # Robustheit: n x Distanz, tau
    gitter = {}
    for art in PROTOKOLL["robustheit"]["distanz"]:
        for n in PROTOKOLL["robustheit"]["n"]:
            Dg, _ = distanz(F, n, art)
            rg, _, _, tg = werte(Dg, E, y)
            rt, *_ = werte(Dg, ~ich, y, gleich=T & ~ich, anfragen=mehrfach)
            gitter[f"{art}|{n}"] = {"T_gattung": rg["treffer"], "ausgewogen": rg["ausgewogen"], "T_text": rt["treffer"],
                                    "_t": tg}
    out["gitter"] = {k: {a: b for a, b in v.items() if a != "_t"} for k, v in gitter.items()}
    print("   n x Distanz (T_gattung streng / ausgewogen / T_text):")
    for art in PROTOKOLL["robustheit"]["distanz"]:
        print(f"      {art:8s} " + "  ".join(
            f"n={n}: {gitter[f'{art}|{n}']['T_gattung']:.1%}/{gitter[f'{art}|{n}']['ausgewogen']:.1%}/"
            f"{gitter[f'{art}|{n}']['T_text']:.1%}" for n in PROTOKOLL["robustheit"]["n"]))
    A = haelfte(cluster)
    bester = max(gitter, key=lambda k: gitter[k]["_t"][q & A].mean())
    out["auswahlkontrolle"] = {"beste_auf_A": bester, "A": float(gitter[bester]["_t"][q & A].mean()),
                               "B": float(gitter[bester]["_t"][q & ~A].mean()),
                               "primaer_A": float(treffer[q & A].mean()), "primaer_B": float(treffer[q & ~A].mean()),
                               "anfragen_A": int((q & A).sum()), "anfragen_B": int((q & ~A).sum())}
    print("   Auswahlkontrolle:", out["auswahlkontrolle"])
    out["tau"] = {}
    for tau in PROTOKOLL["robustheit"]["tau"]:
        rg, *_ = werte(D, zulaessig(tau), y)
        out["tau"][str(tau)] = {k: rg.get(k) for k in ("anfragen", "treffer", "ausgewogen", "zufallsnachbar", "mehrheitsklasse")}
    print("   tau:", {k: (v["anfragen"], round(v["treffer"], 3), round(v["ausgewogen"], 3)) for k, v in out["tau"].items()})

    # Nullmodell Wortmischung
    alle = [x for ch in chunks for x in ch["tok"]]
    misch = []
    for _ in range(20):
        perm = rng.permutation(len(alle))
        pos, neu = 0, []
        for ch in chunks:
            teil = [alle[i] for i in perm[pos:pos + len(ch["tok"])]]
            pos += len(ch["tok"])
            neu.append([x[0] for x in teil] if ebene == "lem" else [s for x in teil for s in x[1]])
        Fm, _ = haeufigkeiten(neu)
        Dn, _ = distanz(Fm, P["n"], P["distanz"])
        misch.append(werte(Dn, E, y)[0]["treffer"])
    out["N_wortmischung"] = {"mittel": float(np.mean(misch)), "max": float(np.max(misch)), "laeufe": len(misch)}
    print("   N_wortmischung", out["N_wortmischung"])

    # Vergleichskorpus: mu kuerzt sich, sigma und Merkmalsauswahl wirken
    mu, sd = F[:, merk].mean(0), F[:, merk].std(0, ddof=1)
    ohne_mu = cdist(F[:, merk] / sd, F[:, merk] / sd, "cityblock") / len(merk)
    out["mu_kuerzt_sich_max_abweichung"] = float(np.abs(ohne_mu - D).max())
    print(f"   mu kuerzt sich: groesste Abweichung {out['mu_kuerzt_sich_max_abweichung']:.2e}")
    pred = y[nn]
    out["vergleichskorpus"] = {}
    for g, k in sorted(out["je_teilkorpus"].items(), key=lambda kv: -kv[1]):
        if k < 30:
            continue
        ref = np.flatnonzero(y == g)
        Dg, mg = distanz(F, P["n"], P["distanz"], ref=ref)
        rg, nng, _, _ = werte(Dg, E, y)
        _, sg = F[np.ix_(ref, merk)].mean(0), F[np.ix_(ref, merk)].std(0, ddof=1)
        ok = sg > 0
        Ds = cdist(F[:, merk][:, ok] / sg[ok], F[:, merk][:, ok] / sg[ok], "cityblock") / ok.sum()
        rs, nns, _, _ = werte(Ds, E, y)
        out["vergleichskorpus"][g] = {
            "abschnitte": int(k), "gemeinsame_merkmale": int(len(set(mg.tolist()) & set(merk.tolist()))),
            "T_gattung": rg["treffer"], "ausgewogen": rg["ausgewogen"],
            "nachbar_geaendert": float((nng[q] != nn[q]).mean()), "antwort_geaendert": float((y[nng[q]] != pred[q]).mean()),
            "nur_sigma": {"merkmale_mit_sigma_null": int((~ok).sum()), "T_gattung": rs["treffer"],
                          "nachbar_geaendert": float((nns[q] != nn[q]).mean()),
                          "antwort_geaendert": float((y[nns[q]] != pred[q]).mean())}}
        v = out["vergleichskorpus"][g]
        print(f"   Vergleichskorpus {g:20s} ({k:3d}): gemeinsame Merkmale {v['gemeinsame_merkmale']}/{P['n']}, "
              f"T_gattung {v['T_gattung']:.1%}, Nachbar geaendert {v['nachbar_geaendert']:.1%}, "
              f"Antwort geaendert {v['antwort_geaendert']:.1%} | nur sigma: sigma=0 bei {v['nur_sigma']['merkmale_mit_sigma_null']}, "
              f"T_gattung {v['nur_sigma']['T_gattung']:.1%}, Nachbar {v['nur_sigma']['nachbar_geaendert']:.1%}, "
              f"Antwort {v['nur_sigma']['antwort_geaendert']:.1%}")

    # Abstaende zwischen Teilkorpora (Mittel ueber zulaessige Paare)
    kl = sorted(set(y.tolist()))
    M = np.full((len(kl), len(kl)), np.nan)
    for a, ka in enumerate(kl):
        for b, kb in enumerate(kl):
            m = E & (y[:, None] == ka) & (y[None, :] == kb)
            if m.any():
                M[a, b] = D[m].mean()
    out["abstand_teilkorpora"] = {"klassen": kl, "matrix": [[None if np.isnan(x) else round(float(x), 4) for x in row] for row in M]}
    for a, ka in enumerate(kl):
        z = M[a].copy()
        innen = z[a]
        z[a] = np.inf
        z = np.where(np.isnan(z), np.inf, z)
        b = int(z.argmin())
        print(f"      {ka:22s} innen {innen:.3f} | naechstes Teilkorpus {kl[b]:20s} {z[b]:.3f}")

    # Unabhaengige Nachrechnung einzelner Paare direkt aus den Wortlisten
    namen = [vok[i] for i in merk]
    zaehl = [collections.Counter(f) for f in folgen]
    rel = [[zaehl[i][w] / len(folgen[i]) for w in namen] for i in range(N)]
    sdp = [statistics.stdev(col) for col in zip(*rel)]
    abw = 0.0
    for _ in range(300):
        i, j = (int(v) for v in rng.integers(0, N, 2))
        d = sum(abs(a - b) / s for a, b, s in zip(rel[i], rel[j], sdp)) / len(namen)
        abw = max(abw, abs(d - D[i, j]))
    out["nachrechnung_max_abweichung"] = abw
    print(f"   Nachrechnung von 300 Paaren ohne NumPy: groesste Abweichung {abw:.2e}")
    return out, D, E, y, T


def main():
    pfad, ziel = sys.argv[1], sys.argv[2]
    P, R = PROTOKOLL["primaer"], PROTOKOLL["robustheit"]
    print("PROTOKOLL sha256:", hashlib.sha256(json.dumps(PROTOKOLL, sort_keys=True).encode()).hexdigest()[:16])
    texte = lade(pfad)
    erg = {"protokoll": PROTOKOLL}
    rng = np.random.default_rng(PROTOKOLL["seed"])
    mini = PROTOKOLL["min_abschnitte_je_teilkorpus"]

    # Wortebene, alle Teilkorpora
    W = filtere(abschnitte(texte, P["L"], False), mini)
    erg["wort"], *_ = untersuche("WORTEBENE (Lemmata), alle Teilkorpora", W, "lem", rng)

    # Zeichenebene und dieselben Woerter auf Wortebene
    Z = filtere(abschnitte(texte, P["L"], True, True), mini)
    erg["zeichen"], Dz, Ez, yz, Tz = untersuche("ZEICHENEBENE (Gardiner-Codes, zusammengelegt)", Z, "sig", rng)
    erg["wort_gepaart"], Dl, El, yl, _ = untersuche("WORTEBENE, dieselben Woerter wie Zeichenebene", Z, "lem", rng)

    # Uebereinstimmung der beiden Ebenen
    iu = np.triu_indices(len(Z), 1)
    frei = ~Tz[iu]
    rho = spearmanr(Dz[iu][frei], Dl[iu][frei]).statistic
    nnz = np.where(Ez, Dz, np.inf).argmin(1)
    nnl = np.where(El, Dl, np.inf).argmin(1)
    perm = []
    for _ in range(999):
        p = rng.permutation(len(Z))
        perm.append(spearmanr(Dz[iu][frei], Dl[np.ix_(p, p)][iu][frei]).statistic)
    erg["ebenen"] = {"spearman": float(rho), "p_mantel": float((1 + (np.array(perm) >= rho).sum()) / 1000),
                     "perm_max": float(np.max(perm)),
                     "gleicher_nachbar": float((nnz == nnl).mean()), "gleiche_antwort": float((yz[nnz] == yl[nnl]).mean()),
                     "paare": int(frei.sum())}
    print("\n=== EBENENVERGLEICH ===\n  ", erg["ebenen"])

    # Robustheit: L und Zeichencodierung (jeweils sonst primaer)
    erg["L"] = {}
    for L in R["L"]:
        for nm, ebene, mit in (("wort", "lem", False), ("zeichen", "sig", True)):
            ch = filtere(abschnitte(texte, L, mit, True), mini)
            o, *_ = untersuche(f"L={L} {nm}", ch, ebene, rng, voll=False)
            erg["L"][f"{nm}|{L}"] = o
    Zr = filtere(abschnitte(texte, P["L"], True, False), mini)
    erg["zeichen_roh"], *_ = untersuche("ZEICHENEBENE, Codes unveraendert", Zr, "sig", rng, voll=False)

    json.dump(erg, open(ziel, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("\ngeschrieben:", ziel)


if __name__ == "__main__":
    main()
