"""Gegenproben zum Ankertest.

Aufruf: python3 -I anker_gegenprobe.py synth
        python3 -I anker_gegenprobe.py zaehlen <tokens.jsonl.gz> <anker_tabelle.tsv> <signs_description.xml>

synth:   kuenstliche Schrift mit bekannten Zeichenwerten (Einkonsonanten-, Mehrkonsonantenzeichen, stumme Zeichen,
         Lautergaenzungen, vorangestellte Bloecke, Fehler in der fremden Form). Findet das Lernverfahren die Werte wieder?
zaehlen: zweiter Weg ohne das Lernverfahren: fuer jedes Zeichen wird nur gezaehlt, in wie vielen Namensgruppen
         Zeichen und Konsonantenklasse gemeinsam vorkommen (Vierfeldertafel, exakter Test nach Fisher).
"""
import collections
import os
import sys

import numpy as np
from scipy.stats import fisher_exact

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anker_test as at


def synth(seed=1, n_namen=150, fehler=0.10):
    rng = np.random.default_rng(seed)
    K = at.K
    ein = {f"E{i}": (i % K,) for i in range(20)}                      # Einkonsonantenzeichen
    zwei = {f"Z{i}": (int(rng.integers(K)), int(rng.integers(K))) for i in range(15)}
    drei = {f"D{i}": tuple(int(x) for x in rng.integers(K, size=3)) for i in range(5)}
    stumm = [f"S{i}" for i in range(15)]                              # Deutzeichen und schwache Zeichen
    wahr = {**ein, **zwei, **drei, **{s: () for s in stumm}}
    ein_fuer = collections.defaultdict(list)
    for z, v in ein.items():
        ein_fuer[v[0]].append(z)
    laut = list(ein) * 3 + list(zwei) * 2 + list(drei)
    namen = []
    for _ in range(n_namen):
        zeichen, kons = [], []
        bloecke = []
        for _ in range(int(rng.integers(2, 5))):
            z = laut[int(rng.integers(len(laut)))]
            b = [z]
            if len(wahr[z]) >= 2 and rng.random() < 0.5:              # Lautergaenzung: wiederholt den letzten Konsonanten
                b.append(ein_fuer[wahr[z][-1]][int(rng.integers(len(ein_fuer[wahr[z][-1]])))])
            if rng.random() < 0.3:
                b.append(stumm[int(rng.integers(5, 15))])             # schwaches Zeichen im Wort
            bloecke.append((b, list(wahr[z])))
        for b, k in bloecke:
            kons += k
        if rng.random() < 0.15 and len(bloecke) > 1:                   # letzter Block wird vorangestellt geschrieben
            bloecke = [bloecke[-1]] + bloecke[:-1]
        for b, _ in bloecke:
            zeichen += b
        zeichen.append(stumm[int(rng.integers(0, 5))])                # Deutzeichen am Ende
        fremd = []
        for c in kons:
            u = rng.random()
            if u < fehler:
                continue                                              # Konsonant fehlt in der fremden Form
            fremd.append(int(rng.integers(K)) if u < 1.5 * fehler else c)
        if fremd:
            namen.append((tuple(zeichen), tuple(fremd)))
    lern, test = namen[: int(0.85 * len(namen))], namen[int(0.85 * len(namen)):]
    m = at.Modell().lerne([(s, c, 1.0) for s, c in lern])
    vor = collections.Counter(z for s, _ in lern for z in set(s))
    ok = collections.Counter()
    tot = collections.Counter()
    for z, v in wahr.items():
        if vor[z] >= 3:
            art = {0: "stumm", 1: "ein", 2: "zwei", 3: "drei"}[len(v)]
            tot[art] += 1
            ok[art] += m.wert(z)[0] == v
    pool = at.Kandidaten([c for _, c in namen])
    r = [at.rang(pool.punkte(m, [(s, 1.0)]), pool.pos[c]) for s, c in test]
    kz = at.kennzahlen(r)
    print(f"synth seed={seed} Namen={len(namen)} Fehler={fehler}: Werte wiedergefunden " +
          ", ".join(f"{a} {ok[a]}/{tot[a]}" for a in ("ein", "zwei", "drei", "stumm")) +
          f" | zurueckgehaltene Namen: Rang 1 {100*kz['rang1']:.0f} % (Zufall {100*kz['zufall_rang1']:.1f} %), Rangplatz {kz['rangplatz_prozent']:.1f} %"
          f" | Anteile Voranstellung {np.round(m.pi, 2).tolist()}")
    return ok, tot, kz


def zaehlen(tok_pfad, anker_pfad, xml_pfad):
    zeilen = [z for z in at.lade_anker(anker_pfad) if z["satz"] == "A"]
    roh = at.lade_schreibungen(tok_pfad, {z["id"] for z in zeilen})
    hat_z = collections.defaultdict(set)   # Gruppe -> Zeichen (alle gewaehlten Schreibungen)
    hat_k = collections.defaultdict(set)   # Gruppe -> Klassen (alle fremden Formen)
    for z in zeilen:
        if not roh.get(z["id"]):
            continue
        for s, _ in at.waehle(roh[z["id"]], 4):
            hat_z[z["g"]] |= set(s)
        for _, _, c in z["formen"]:
            hat_k[z["g"]] |= set(c)
    gruppen = sorted(hat_z)
    std = at.standardwerte(xml_pfad)
    print(f"zaehlen: {len(gruppen)} Namensgruppen")
    treffer = n = 0
    for code in at.STARK1:
        mit = [g for g in gruppen if code in hat_z[g]]
        if len(mit) < 3:
            print(f"   {code:4s} in {len(mit)} Gruppen: zu selten")
            continue
        best = None
        for k in range(at.K):
            a = sum(k in hat_k[g] for g in mit)
            b = len(mit) - a
            c = sum(k in hat_k[g] for g in gruppen if code not in hat_z[g])
            d = len(gruppen) - len(mit) - c
            p = fisher_exact([[a, b], [c, d]], alternative="greater")[1]
            if best is None or p < best[0]:
                best = (p, k, a, len(mit), c, len(gruppen) - len(mit))
        p, k, a, nm, c, no = best
        passt = (k,) in std.get(code, ([], set()))[1]
        n += 1
        treffer += passt
        print(f"   {code:4s} in {nm:3d} Gruppen | staerkste Bindung an Klasse {at.KLASSEN[k]}: {a}/{nm} mit Zeichen gegen {c}/{no} ohne, "
              f"p = {p:.1e} | Standard {'/'.join(std.get(code, ([], set()))[0])[:14]:14s} | {'passt' if passt else 'passt nicht'}")
    print(f"zaehlen: {treffer} von {n} starken Einkonsonantenzeichen mit passender Klasse")


if __name__ == "__main__":
    if sys.argv[1] == "synth":
        for seed in (1, 2, 3):
            synth(seed)
        synth(4, n_namen=80)
        synth(5, fehler=0.25)
    else:
        zaehlen(*sys.argv[2:5])
