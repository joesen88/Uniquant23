"""Phasen-Test: Hat die Abweichung zwischen Abschriften desselben Spruchs eine Phasen- oder Taktstruktur?

Aufruf: python3 -I phasen_test.py <zeit_schicht.jsonl.gz> <ergebnis.json>

Anlass: Zwei gleichzeitige Totenbuch-Abschriften weichen an rund einem Viertel der Stellen ab.
Vier pruefbare Lesarten von "phasenmaessig", festgelegt vor dem ersten Lauf:
  H1 scharfes Viertel:  Der Anteil liegt bei allen Paaren eng um 25 % (Streuung unter 3 Punkten).
  H2 Takt:              Abweichungen kehren im festen Abstand wieder (Periode 2 bis 64 Woerter, insbesondere 4).
                        Massstab: Spektrum gegen Ersatzfolgen, in denen dieselben Laeufe in anderer Reihenfolge stehen.
  H3 Lage im Spruch:    Die Abweichungsrate haengt von der relativen Position im Spruch ab (Anfang, Mitte, Ende).
  H4 feste Stellen:     Die Abweichungen verschiedener Handschriften fallen auf dieselben Stellen (Geruest und
                        veraenderliche Stellen). Massstab: jede Handschrift fuer sich kreisfoermig verschoben.
Erwartung ohne Phasenstruktur: H1 und H2 treffen nicht zu; Abweichungen kommen in Bloecken (Zusaetze, Auslassungen).

Nach dem ersten Lauf geaendert oder ergaenzt:
  H3  Der gemeinsame Bereich beginnt und endet per Definition mit mindestens vier gleichen Woertern. Das drueckt die
      Rate an den Raendern kuenstlich. Massstab sind deshalb Ersatzfolgen mit denselben Randbloecken und vertauschten
      inneren Laeufen.
  H4  Zusatz: Teilen die abweichenden Handschriften dieselbe Lesart? (Ob die Zeit sie trennt, liess sich nicht
      auswerten: Im Totenbuch hat nur eine spaete Handschrift genug Parallelen.)
  H5  Zwei Zustaende statt Zerfall (nur Totenbuch): Handschriften vor und nach 700 v. Chr. als zwei Fassungen.
      Bleibt die Uebereinstimmung innerhalb einer Fassung ueber die Zeit gleich und faellt nur ueber die Grenze?
"""
import collections
import difflib
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import halbwertszeit as hw  # noqa: E402

FENSTER, ERSATZ, GRENZE = 64, 400, -700
LUECKE = 0


def folgen(texte, gruppe):
    code, z, out = {}, 0, []
    for t in texte:
        if t["c"] != gruppe:
            continue
        f = []
        for lid, e in t["tok"]:
            if e in (0, 1):
                f.append(code.setdefault(lid, len(code) + 1))
            else:
                z -= 1
                f.append(z)
        out.append((t, f))
    return out


def kern(a, b):
    ops = difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
    anker = [k for k, o in enumerate(ops) if o[0] == "equal" and o[2] - o[1] >= 4]
    return ops[anker[0]:anker[-1] + 1] if anker else None


def abfolge(a, b):
    """0 = gleich, 1 = abweichend, None = nicht pruefbar (Luecke oder Ergaenzung)."""
    ops = kern(a, b)
    if ops is None:
        return None
    seq = []
    for tag, i1, i2, j1, j2 in ops:
        if tag == "equal":
            seq += [0] * (i2 - i1)
        elif all(v > 0 for v in a[i1:i2]) and all(v > 0 for v in b[j1:j2]):
            seq += [1] * max(i2 - i1, j2 - j1)
        else:
            seq += [None] * max(i2 - i1, j2 - j1)
    return seq


def laeufe(x):
    out, n = [], 1
    for u, v in zip(x, x[1:]):
        if u == v:
            n += 1
        else:
            out.append((u, n))
            n = 1
    out.append((x[-1], n))
    return out


def mische_laeufe(x, rng):
    r = laeufe(x)
    nullen = [n for v, n in r if v == 0]
    einsen = [n for v, n in r if v == 1]
    rng.shuffle(nullen)
    rng.shuffle(einsen)
    out, v = [], r[0][0]
    while nullen or einsen:
        quelle = nullen if v == 0 else einsen
        if quelle:
            out += [v] * quelle.pop()
        v = 1 - v
    return out


def mische_innen(s, rng):
    """Randbloecke bleiben, die inneren Laeufe (gleich, abweichend, nicht pruefbar) wechseln die Reihenfolge."""
    r = laeufe(s)
    if len(r) < 4:
        return s
    innen = r[1:-1]
    out = [r[0][0]] * r[0][1]
    for k in rng.permutation(len(innen)):
        out += [innen[k][0]] * innen[k][1]
    return out + [r[-1][0]] * r[-1][1]


def spektrum(fenster):
    X = np.asarray(fenster, float)
    X = X - X.mean(1, keepdims=True)
    return (np.abs(np.fft.rfft(X, axis=1)) ** 2)[:, 1:].mean(0) / X.shape[1]


def lage(folgen_):
    """Abweichungsrate je Zehntel sowie in den ersten 10, den letzten 10 und den uebrigen Woertern."""
    zeh, zn, rand = np.zeros(10), np.zeros(10), np.zeros(6)
    for s in folgen_:
        L = len(s)
        for k, v in enumerate(s):
            if v is None:
                continue
            d = min(9, int(10 * k / L))
            zeh[d] += v
            zn[d] += 1
            o = 0 if k < 10 else (2 if k >= L - 10 else 1)
            rand[2 * o] += v
            rand[2 * o + 1] += 1
    return zeh / zn, np.array([rand[0] / rand[1], rand[2] / rand[3], rand[4] / rand[5]])


def untersuche(name, texte, gruppe, rng, stufe=False):
    F = folgen(texte, gruppe)
    werke = collections.defaultdict(list)
    for t, f in F:
        werke[hw.titel(t["titel"])].append((t, f))
    mitte = lambda t: (t["nb"] + t["na"]) / 2  # noqa: E731
    paare = []
    for w, ts in werke.items():
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                if ts[i][0]["hs"] == ts[j][0]["hs"]:
                    continue
                s = abfolge(ts[i][1], ts[j][1])
                if s is None or s.count(0) < 15 or s.count(0) + s.count(1) < 30:
                    continue
                paare.append({"werk": w, "a": ts[i][0]["hs"], "b": ts[j][0]["hs"], "da": mitte(ts[i][0]), "db": mitte(ts[j][0]), "s": s})
    out = {"paare": len(paare)}
    print(f"\n=== {name}: {len(paare)} Spruchpaare, {sum(p['s'].count(0) + p['s'].count(1) for p in paare)} pruefbare Stellen ===")

    # H1: wie scharf ist das Viertel?
    ant = np.array([p["s"].count(1) / (p["s"].count(0) + p["s"].count(1)) for p in paare])
    gew = np.array([p["s"].count(0) + p["s"].count(1) for p in paare], float)
    dt = np.array([abs(p["da"] - p["db"]) for p in paare])
    out["H1"] = {}
    for titel, m in (("gleichzeitig (unter 50 Jahre)", dt < 50), ("alle Paare", np.ones(len(paare), bool))):
        a = ant[m]
        r = {"paare": int(m.sum()), "mittel_gewichtet": float((ant[m] * gew[m]).sum() / gew[m].sum()), "median": float(np.median(a)),
             "quartile": [float(np.percentile(a, 25)), float(np.percentile(a, 75))], "streuung": float(a.std(ddof=1)),
             "spanne": [float(a.min()), float(a.max())], "anteil_23_bis_27": float(((a >= 0.23) & (a <= 0.27)).mean())}
        out["H1"][titel] = r
        print(f"   H1 {titel:30s} n={r['paare']:3d}: Mittel {r['mittel_gewichtet']:.1%}, Median {r['median']:.1%}, Quartile "
              f"{r['quartile'][0]:.1%}-{r['quartile'][1]:.1%}, Streuung {r['streuung']:.1%}, Spanne {r['spanne'][0]:.1%}-{r['spanne'][1]:.1%}, "
              f"zwischen 23 und 27 %: {r['anteil_23_bis_27']:.0%} der Paare")

    # Bloecke: Lauflaengen
    stuecke = []
    for p in paare:
        akt = []
        for v in p["s"] + [None]:
            if v is None:
                if len(akt) >= 2:
                    stuecke.append(akt)
                akt = []
            else:
                akt.append(v)
    alle = [r for st in stuecke for r in laeufe(st)]
    einsen = np.array([n for v, n in alle if v == 1])
    pr = sum(sum(st) for st in stuecke) / sum(len(st) for st in stuecke)
    x0 = np.concatenate([np.asarray(st[:-1], float) for st in stuecke])
    x1 = np.concatenate([np.asarray(st[1:], float) for st in stuecke])
    out["bloecke"] = {"rate": pr, "mittlere_lauflaenge": float(einsen.mean()), "erwartet_unabhaengig": 1 / (1 - pr),
                      "anteil_stellen_in_laeufen_ab_3": float(einsen[einsen >= 3].sum() / einsen.sum()),
                      "laengster_lauf": int(einsen.max()), "autokorrelation_1": float(np.corrcoef(x0, x1)[0, 1])}
    b = out["bloecke"]
    print(f"   Bloecke: mittlere Laenge eines Abweichungslaufs {b['mittlere_lauflaenge']:.2f} Woerter (bei unabhaengigen Stellen "
          f"{b['erwartet_unabhaengig']:.2f}); {b['anteil_stellen_in_laeufen_ab_3']:.0%} der abweichenden Stellen liegen in Laeufen ab 3 Woertern; "
          f"laengster Lauf {b['laengster_lauf']}; Autokorrelation zum Nachbarwort {b['autokorrelation_1']:.2f}")

    # H2: Takt
    fenster = [st[k:k + FENSTER] for st in stuecke for k in range(0, len(st) - FENSTER + 1, FENSTER)]
    fenster = [f for f in fenster if 0 < sum(f) < FENSTER]
    beob = spektrum(fenster)
    null = np.array([spektrum([mische_laeufe(f, rng) for f in fenster]) for _ in range(ERSATZ)])
    mu, sd = null.mean(0), null.std(0, ddof=1)
    z = (beob - mu) / sd
    zmax_null = ((null - mu) / sd).max(1)
    perioden = FENSTER / np.arange(1, FENSTER // 2 + 1)
    k4 = FENSTER // 4 - 1
    out["H2"] = {"fenster": len(fenster), "z_max": float(z.max()), "periode_bei_z_max": float(perioden[int(z.argmax())]),
                 "p_gesamt": float((1 + (zmax_null >= z.max()).sum()) / (ERSATZ + 1)), "z_periode_4": float(z[k4]),
                 "leistung_periode_4_relativ": float(beob[k4] / mu[k4]),
                 "z_je_periode": {f"{perioden[k]:.1f}": round(float(z[k]), 2) for k in range(len(z))}}
    h = out["H2"]
    print(f"   H2 Takt: {h['fenster']} Fenster zu {FENSTER} Woertern; groesster Ausschlag z = {h['z_max']:.2f} bei Periode {h['periode_bei_z_max']:.1f} Woerter, "
          f"p ueber alle Perioden {h['p_gesamt']:.3f}; Periode 4: z = {h['z_periode_4']:.2f}, Leistung {h['leistung_periode_4_relativ']:.2f}-fach der Ersatzfolgen")

    # H3: Lage im Spruch, gegen Ersatzfolgen mit denselben Randbloecken
    seqs = [p["s"] for p in paare]
    zb, rb = lage(seqs)
    zn_, rn_ = zip(*[lage([mische_innen(s, rng) for s in seqs]) for _ in range(ERSATZ)])
    zn_, rn_ = np.array(zn_), np.array(rn_)
    out["H3"] = {"zehntel": [float(v) for v in zb], "zehntel_ersatz": [float(v) for v in zn_.mean(0)],
                 "zehntel_ersatz_95": [[float(np.percentile(zn_[:, d], 2.5)), float(np.percentile(zn_[:, d], 97.5))] for d in range(10)],
                 "erste10_mitte_letzte10": [float(v) for v in rb], "ersatz": [float(v) for v in rn_.mean(0)],
                 "ersatz_95": [[float(np.percentile(rn_[:, d], 2.5)), float(np.percentile(rn_[:, d], 97.5))] for d in range(3)]}
    h = out["H3"]
    print("   H3 Lage: Abweichungsrate je Zehntel, beobachtet:   " + " ".join(f"{v:5.1%}" for v in zb))
    print("            bei vertauschten inneren Laeufen:        " + " ".join(f"{v:5.1%}" for v in zn_.mean(0)))
    print(f"      erste 10 Woerter {rb[0]:.1%} (Ersatz {rn_[:, 0].mean():.1%} [{h['ersatz_95'][0][0]:.1%}, {h['ersatz_95'][0][1]:.1%}]), "
          f"Mitte {rb[1]:.1%} (Ersatz {rn_[:, 1].mean():.1%}), letzte 10 Woerter {rb[2]:.1%} (Ersatz {rn_[:, 2].mean():.1%} "
          f"[{h['ersatz_95'][2][0]:.1%}, {h['ersatz_95'][2][1]:.1%}])")

    # H4: feste Stellen (Sternausrichtung auf den laengsten Zeugen, Mehrheitslesart je Stelle)
    spalten, varianten = [], collections.Counter()
    for w, ts in werke.items():
        je_hs = {}
        for t, f in ts:
            if t["hs"] not in je_hs or len(f) > len(je_hs[t["hs"]][1]):
                je_hs[t["hs"]] = (mitte(t), f)
        if len(je_hs) < 4:
            continue
        zeugen = sorted(je_hs.values(), key=lambda v: len(v[1]), reverse=True)
        A = zeugen[0][1]
        tage = np.array([d for d, _ in zeugen])
        les = [[v if v > 0 else None for v in A]]
        for _, Bf in zeugen[1:]:
            R = [None] * len(A)
            for tag, i1, i2, j1, j2 in kern(A, Bf) or []:
                if tag == "equal":
                    R[i1:i2] = A[i1:i2]
                elif tag != "insert" and all(v > 0 for v in A[i1:i2]) and all(v > 0 for v in Bf[j1:j2]):
                    for u in range(i2 - i1):
                        R[i1 + u] = Bf[j1 + u] if u < j2 - j1 else LUECKE
            les.append(R)
        X = np.full((len(les), len(A)), np.nan)
        for k in range(len(A)):
            bekannt = [(q, r[k]) for q, r in enumerate(les) if r[k] is not None]
            if len(bekannt) < 4:
                continue
            c = collections.Counter(v for _, v in bekannt).most_common(2)
            if len(c) > 1 and c[0][1] == c[1][1]:
                varianten["ohne_mehrheit"] += 1
                continue
            ab = [(q, v) for q, v in bekannt if v != c[0][0]]
            for q, v in bekannt:
                X[q, k] = float(v != c[0][0])
            if len(ab) >= 2:
                varianten["mehrfach"] += 1
                if len({v for _, v in ab}) == 1:
                    varianten["gemeinsame_lesart"] += 1
                    qa = [q for q, _ in ab]
                    qm = [q for q, v in bekannt if v == c[0][0]]
                    spaet = tage > GRENZE
                    if spaet[[q for q, _ in bekannt]].any() and (~spaet[[q for q, _ in bekannt]]).any():
                        varianten["beide_fassungen_belegt"] += 1
                        getrennt = (spaet[qa].all() and not spaet[qm].any()) or (not spaet[qa].any() and spaet[qm].all())
                        varianten["zeitlich_getrennt"] += int(getrennt)
                        alle_q = np.array([q for q, _ in bekannt])
                        treffer = 0
                        for _ in range(200):
                            zug = rng.permutation(alle_q)
                            sa, sm = spaet[zug[:len(qa)]], spaet[zug[len(qa):]]
                            treffer += (sa.all() and not sm.any()) or (not sa.any() and sm.all())
                        varianten["zeitlich_getrennt_zufall_x200"] += treffer
        X = X[:, ~np.isnan(X).all(0)]
        if X.shape[1] >= 20:
            spalten.append(X)

    def kennzahlen(mats):
        N = np.concatenate([np.nansum(X, 0) for X in mats])
        n = np.concatenate([(~np.isnan(X)).sum(0) for X in mats])
        return float((N == 0).mean()), float((N >= 2).mean()), float((N / n).var())

    if spalten:
        beob = kennzahlen(spalten)
        nullw = []
        for _ in range(ERSATZ):
            neu = []
            for X in spalten:
                Y = X.copy()
                for q in range(X.shape[0]):
                    ok = np.flatnonzero(~np.isnan(X[q]))
                    if len(ok) > 1:
                        Y[q, ok] = np.roll(X[q, ok], int(rng.integers(1, len(ok))))
                neu.append(Y)
            nullw.append(kennzahlen(neu))
        nullw = np.array(nullw)
        out["H4"] = {"sprueche": len(spalten), "stellen": int(sum(X.shape[1] for X in spalten)),
                     "zeugen_im_mittel": float(np.mean([(~np.isnan(X)).sum(0).mean() for X in spalten])),
                     "fest_beobachtet": beob[0], "fest_null": [float(nullw[:, 0].mean()), float(np.percentile(nullw[:, 0], 2.5)), float(np.percentile(nullw[:, 0], 97.5))],
                     "mehrfach_beobachtet": beob[1], "mehrfach_null": [float(nullw[:, 1].mean()), float(np.percentile(nullw[:, 1], 2.5)), float(np.percentile(nullw[:, 1], 97.5))],
                     "streuung_verhaeltnis": beob[2] / float(nullw[:, 2].mean()),
                     "varianten": {k: int(v) for k, v in varianten.items()}}
        h = out["H4"]
        print(f"   H4 feste Stellen: {h['sprueche']} Sprueche mit mindestens 4 Handschriften, {h['stellen']} Stellen, im Mittel {h['zeugen_im_mittel']:.1f} Zeugen je Stelle")
        print(f"      Stellen ohne jede Abweichung: beobachtet {h['fest_beobachtet']:.1%}, bei verschobenen Handschriften {h['fest_null'][0]:.1%} "
              f"[{h['fest_null'][1]:.1%}, {h['fest_null'][2]:.1%}]")
        print(f"      Stellen, an denen mindestens 2 Handschriften abweichen: beobachtet {h['mehrfach_beobachtet']:.1%}, verschoben {h['mehrfach_null'][0]:.1%} "
              f"[{h['mehrfach_null'][1]:.1%}, {h['mehrfach_null'][2]:.1%}]; Streuung je Stelle {h['streuung_verhaeltnis']:.2f}-fach")
        v = varianten
        if v["mehrfach"]:
            print(f"      Zusatz: an {v['mehrfach']} Stellen weichen mehrere ab, davon {v['gemeinsame_lesart']} mit derselben Lesart; "
                  f"ohne Mehrheit {v['ohne_mehrheit']} Stellen. Die zeitliche Trennung ist nicht auswertbar, wenn nur eine "
                  f"spaete Handschrift Parallelen hat.")

    # H5: zwei Zustaende statt Zerfall
    if stufe:
        y = 1 - ant
        fa = np.array([p["da"] > GRENZE for p in paare])
        fb = np.array([p["db"] > GRENZE for p in paare])
        kl = np.where(fa & fb, "spaet-spaet", np.where(~fa & ~fb, "frueh-frueh", "frueh-spaet"))
        hs = sorted({p["a"] for p in paare} | {p["b"] for p in paare})
        pos = {h_: i for i, h_ in enumerate(hs)}
        ia, ib = np.array([pos[p["a"]] for p in paare]), np.array([pos[p["b"]] for p in paare])
        out["H5"] = {"klassen": {}}
        print(f"   H5 zwei Fassungen (Grenze {GRENZE}): Handschriften frueh {len({p[k] for p in paare for k, d in (('a', 'da'), ('b', 'db')) if p[d] <= GRENZE})}, "
              f"spaet {len({p[k] for p in paare for k, d in (('a', 'da'), ('b', 'db')) if p[d] > GRENZE})}")
        for k in ("frueh-frueh", "frueh-spaet", "spaet-spaet"):
            m = kl == k
            if m.any():
                out["H5"]["klassen"][k] = {"paare": int(m.sum()), "stellen": int(gew[m].sum()), "uebereinstimmung": float((y[m] * gew[m]).sum() / gew[m].sum())}
                print(f"      {k:12s} Paare {int(m.sum()):3d}, Stellen {int(gew[m].sum()):6d}: gleich {out['H5']['klassen'][k]['uebereinstimmung']:.1%}")
        ff = kl == "frueh-frueh"
        for a_, b_ in ((0, 50), (50, 300), (300, 600)):
            m = ff & (dt >= a_) & (dt < b_)
            if m.any():
                print(f"         frueh-frueh, {a_}-{b_} Jahre: Paare {int(m.sum()):3d}, gleich {(y[m] * gew[m]).sum() / gew[m].sum():.1%}")
        lam_ff, a_ff = hw.anpassen(dt[ff], y[ff], gew[ff])
        werk = np.array([p["werk"] for p in paare])
        namen, inv = np.unique(werk[ff], return_inverse=True)
        glied = [np.flatnonzero(ff)[inv == k] for k in range(len(namen))]
        lb, sprung = [], []
        fs = kl == "frueh-spaet"
        for _ in range(1000):
            jj = np.concatenate([glied[q] for q in rng.integers(0, len(namen), len(namen))])
            lb.append(hw.anpassen(dt[jj], y[jj], gew[jj])[0])
            mult = np.bincount(rng.integers(0, len(hs), len(hs)), minlength=len(hs)).astype(float)
            wh = gew * mult[ia] * mult[ib]
            if wh[ff].sum() > 0 and wh[fs].sum() > 0:
                sprung.append((y[ff] * wh[ff]).sum() / wh[ff].sum() - (y[fs] * wh[fs]).sum() / wh[fs].sum())
        res = {}
        for titel, vorhersage in (("konstant", np.full(len(y), (y * gew).sum() / gew.sum())),
                                  ("zerfall", None), ("zwei_fassungen", None)):
            if titel == "zerfall":
                l_, a_ = hw.anpassen(dt, y, gew)
                vorhersage = a_ * np.exp(-l_ * dt)
            elif titel == "zwei_fassungen":
                vorhersage = np.zeros(len(y))
                for k in set(kl.tolist()):
                    m = kl == k
                    vorhersage[m] = (y[m] * gew[m]).sum() / gew[m].sum()
            res[titel] = float((gew * (y - vorhersage) ** 2).sum())
        out["H5"].update({"normtreue_innerhalb_frueh": float(np.exp(-100 * lam_ff)),
                          "normtreue_innerhalb_frueh_ki": sorted(float(np.exp(-100 * q)) for q in np.percentile(lb, [2.5, 97.5])),
                          "sprung_frueh_zu_spaet": float(np.mean(sprung)) if sprung else None,
                          "sprung_ki_handschriften": [float(np.percentile(sprung, 2.5)), float(np.percentile(sprung, 97.5))],
                          "restquadrate": res,
                          "erklaert_zerfall": 1 - res["zerfall"] / res["konstant"], "erklaert_zwei_fassungen": 1 - res["zwei_fassungen"] / res["konstant"]})
        h = out["H5"]
        print(f"      Innerhalb der fruehen Fassung (bis 444 Jahre Abstand): Normtreue je Jahrhundert {h['normtreue_innerhalb_frueh']:.2%} "
              f"[{h['normtreue_innerhalb_frueh_ki'][0]:.2%}, {h['normtreue_innerhalb_frueh_ki'][1]:.2%}]")
        print(f"      Sprung frueh-frueh minus frueh-spaet: {h['sprung_frueh_zu_spaet']:+.1%} "
              f"[{h['sprung_ki_handschriften'][0]:+.1%}, {h['sprung_ki_handschriften'][1]:+.1%}] (ueber Handschriften gezogen)")
        print(f"      erklaerter Anteil der Unterschiede zwischen Paaren: Zerfall {h['erklaert_zerfall']:.1%}, zwei Fassungen {h['erklaert_zwei_fassungen']:.1%}")
    return out


def main():
    texte = hw.lade(sys.argv[1])
    rng = np.random.default_rng(hw.PROTOKOLL["seed"] + 11)
    erg = {"totenbuch": untersuche("TOTENBUCH", texte, "tb", rng, stufe=True),
           "pyramidentexte": untersuche("PYRAMIDENTEXTE", texte, "bbawpyramidentexte", rng)}
    json.dump(erg, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\ngeschrieben:", sys.argv[2])


if __name__ == "__main__":
    main()
