"""Nachtraege zum Ankertest (nach dem ersten Lauf festgelegt, deshalb getrennt vom Protokoll).

Aufruf: python3 -I anker_nachtrag.py <tokens.jsonl.gz> <anker_tabelle.tsv> <egyptian_etymologies.tab> <ergebnis.json>

N-a  Gewoehnliche Woerter (P4) mit 20 Modellen aus vertauschten Ankern: wie gut waere das Ergebnis ohne echten
     Zusammenhang zwischen Zeichen und fremder Form? (strengerer Massstab als die 50 % des Protokolls)
N-b  Anker mit Zuruecklegen gezogen (20-mal): haengt P4 an einzelnen Eintraegen der von Hand erstellten Tabelle?
N-c  Zahlwoerter in ausgeschriebener Form: Bedeutung durch die Zahl gesichert, Laut aus dem Koptischen bekannt.
N-d  P4 nur fuer Woerter, deren Schreibung kein Zeichen mit weniger als 3 Ankergruppen braucht.
N-e  Anker aus nur einer Ueberlieferung (Griechisch, Keilschrift, Koptisch, Semitisch, Arabisch) -> P4.
N-f  Ortsname Chemenu: mit wie vielen Strichen geschrieben?
N-g  Stichprobe: koptische Formen der Ankertabelle gegen die Tabelle des Coptic Dictionary Online.
"""
import collections
import os
import json
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anker_test as at

tok_pfad, anker_pfad, kop_pfad, ziel = sys.argv[1:5]
rng = np.random.default_rng(20261113)
zeilen = at.lade_anker(anker_pfad)
kop_zeilen = [l.rstrip("\n").split("\t") for l in open(kop_pfad, encoding="utf-8")][1:]
roh = at.lade_schreibungen(tok_pfad, {z["id"] for z in zeilen} | {r[2] for r in kop_zeilen if r[2] != "NA"})
schreib = {z["id"]: at.waehle(roh[z["id"]], 4) for z in zeilen if roh.get(z["id"])}
A = [z for z in zeilen if z["satz"] == "A" and z["id"] in schreib]

anker_ids = {z["id"] for z in zeilen}
paare, alle_kop, kopform = collections.defaultdict(set), set(), collections.defaultdict(list)
for r in kop_zeilen:
    c = at.koptisch(r[1])
    if r[2] != "NA":
        kopform[r[2]].append((r[1], r[3], r[7]))
    if not len(c):
        continue
    alle_kop.add(c)
    if r[2] != "NA" and roh.get(r[2]) and r[2] not in anker_ids:   # Ankernamen selbst werden nicht geprueft
        paare[r[2]].add(c)
kpool = at.Kandidaten(alle_kop)
lem = sorted(paare)
kschreib = {l: at.waehle(roh[l], 3) for l in lem}
Q = [(li, kpool.pos[c]) for li, l in enumerate(lem) for c in sorted(paare[l])]
ql, qt = np.array([q[0] for q in Q]), np.array([q[1] for q in Q])
laenge = kpool.n[qt]


def rangplaetze(punkte):
    o = np.argsort(-punkte, kind="stable")
    rg = np.empty(len(punkte))
    rg[o] = np.arange(len(punkte))
    _, inv, cnt = np.unique(punkte, return_inverse=True, return_counts=True)
    return (np.bincount(inv, weights=rg) / cnt)[inv] / (len(punkte) - 1)


def p4(modell):
    P = np.stack([rangplaetze(kpool.punkte(modell, kschreib[l])) for l in lem])
    pct = P[ql, qt]
    return P, {"rangplatz_prozent": float(100 * pct.mean()), "rang1": float((pct == 0).mean()),
               "unter_ersten_10": float((pct * (len(kpool.folgen) - 1) < 10).mean())}


def vertauscht(zs):
    gs = sorted({z["g"] for z in zs})
    formen = {}
    for z in zs:
        formen.setdefault(z["g"], z["formen"])
    ziel_g = dict(zip(gs, [gs[i] for i in rng.permutation(len(gs))]))
    return [{**z, "formen": formen[ziel_g[z["g"]]]} for z in zs]


E = {}
voll = at.Modell().lerne(at.posten_aus(A, schreib))
P_voll, k_voll = p4(voll)
print(f"P4 mit allen Ankern: Rangplatz {k_voll['rangplatz_prozent']:.1f} % | Rang 1 {100*k_voll['rang1']:.1f} % | unter den ersten 10: {100*k_voll['unter_ersten_10']:.1f} %")
E["voll"] = k_voll

# ---------- N-a ----------
na = [p4(at.Modell().lerne(at.posten_aus(vertauscht(A), schreib)))[1] for _ in range(20)]
for key, name in (("rangplatz_prozent", "Rangplatz %"), ("rang1", "Rang 1"), ("unter_ersten_10", "unter den ersten 10")):
    w = np.array([x[key] for x in na]) * (1 if key == "rangplatz_prozent" else 100)
    print(f"N-a 20 Modelle aus vertauschten Ankern, {name}: Mittel {w.mean():.1f}, Spanne {w.min():.1f} bis {w.max():.1f}")
E["N_a"] = na
null_mittel = float(np.mean([x["rangplatz_prozent"] for x in na]))

# Obergrenze noch einmal (gleiche Aufteilung wie im Hauptlauf ist nicht noetig; eigener Zufallsstrom)
pm = rng.permutation(len(lem))
kteil = {int(li): int(j % 10) for j, li in enumerate(pm)}
pct_ob = np.zeros(len(Q))
for t in range(10):
    post = [(s, c, a) for li, l in enumerate(lem) if kteil[li] != t for c in paare[l] for s, a in kschreib[l]]
    m = at.Modell().lerne(post)
    for qi, (li, ti) in enumerate(Q):
        if kteil[li] == t:
            pct_ob[qi] = rangplaetze(kpool.punkte(m, kschreib[lem[li]]))[ti]
ob = {"rangplatz_prozent": float(100 * pct_ob.mean()), "rang1": float((pct_ob == 0).mean()),
      "unter_ersten_10": float((pct_ob * (len(kpool.folgen) - 1) < 10).mean())}
anteil = (null_mittel - k_voll["rangplatz_prozent"]) / (null_mittel - ob["rangplatz_prozent"])
print(f"Obergrenze (am Koptischen gelernt): Rangplatz {ob['rangplatz_prozent']:.1f} % | Rang 1 {100*ob['rang1']:.1f} % | unter den ersten 10: {100*ob['unter_ersten_10']:.1f} %")
print(f"Anteil des Wegs von 'vertauschte Anker' ({null_mittel:.1f} %) zur Obergrenze ({ob['rangplatz_prozent']:.1f} %), den die echten Anker gehen: {100*anteil:.0f} %")
E["obergrenze"], E["anteil_streng"] = ob, float(anteil)

# ---------- N-b ----------
gruppen = sorted({z["g"] for z in A})
nach_g = collections.defaultdict(list)
for z in A:
    nach_g[z["g"]].append(z)
nb = []
for _ in range(20):
    zug = [z for g in rng.choice(gruppen, len(gruppen)) for z in nach_g[g]]
    nb.append(p4(at.Modell().lerne(at.posten_aus(zug, schreib)))[1])
for key, name in (("rangplatz_prozent", "Rangplatz %"), ("rang1", "Rang 1"), ("unter_ersten_10", "unter den ersten 10")):
    w = np.array([x[key] for x in nb]) * (1 if key == "rangplatz_prozent" else 100)
    print(f"N-b Anker mit Zuruecklegen gezogen (20-mal), {name}: Mittel {w.mean():.1f}, Spanne {w.min():.1f} bis {w.max():.1f}")
E["N_b"] = nb

# ---------- N-c Zahlwoerter ----------
ZAHL = {"136210": "2", "117280": "3", "850571": "4", "177840": "5", "128520": "6", "133760": "7", "117240": "8",
        "62450": "9", "78340": "10", "155320": "100", "113110": "1000", "183450": "10000", "863636": "1/2"}
ZAHLZEICHEN = {"Z1", "Z2", "Z3", "Z4", "Z15", "V20", "V1", "M12", "D50", "I8", "C11"}
print("N-c Zahlwoerter, nur ausgeschriebene Schreibungen (mindestens 2 Zeichen, die keine Zahlzeichen sind):")
nc = []
for lid, zahl in ZAHL.items():
    if lid not in paare:
        print(f"   {zahl:>5s}: kein Paar in der Tabelle oder keine Schreibung im Korpus")
        continue
    aus = [(s, n) for s, n in roh[lid].most_common() if sum(x not in ZAHLZEICHEN for x in s) >= 2]
    if not aus:
        print(f"   {zahl:>5s} {kopform[lid][0][1]:7s}: nur mit Zahlzeichen geschrieben ({sum(roh[lid].values())} Belege)")
        continue
    s = aus[0][0]
    stumm = tuple("?" + x for x in s)                     # alle Zeichen unbekannt: nur Grundverteilung
    for c in sorted(paare[lid]):
        r = 100 * rangplaetze(kpool.punkte(voll, [(s, 1.0)]))[kpool.pos[c]]
        r0 = 100 * rangplaetze(kpool.punkte(voll, [(stumm, 1.0)]))[kpool.pos[c]]
        nc.append({"zahl": zahl, "lemma": kopform[lid][0][1], "schreibung": "-".join(s), "belege": int(aus[0][1]),
                   "koptisch": kopform[lid][0][0], "folge": at.kl_text(c), "rangplatz": float(r), "rangplatz_ohne_werte": float(r0)})
        print(f"   {zahl:>5s} {kopform[lid][0][1]:7s} {'-'.join(s)[:30]:30s} ({aus[0][1]:3d} Belege) -> {kopform[lid][0][0]:7s} {at.kl_text(c):5s} "
              f"Rangplatz {r:5.1f} % (ohne Zeichenwerte {r0:5.1f} %)")
E["N_c"] = nc

# ---------- N-d ----------
zg = collections.defaultdict(set)
for z in A:
    for s, _ in schreib[z["id"]]:
        for x in s:
            zg[x].add(z["g"])
pct = P_voll[ql, qt]
# Vergleichswert je Abfrage: Rangplatz der Partner gleicher Laenge im Mittel (aus den anderen Abfragen)
mittel_gleiche_laenge = np.zeros(len(Q))
for L in np.unique(laenge):
    ix = np.where(laenge == L)[0]
    M = P_voll[ql[ix]][:, qt[ix]]
    mittel_gleiche_laenge[ix] = (M.sum(axis=1) - np.diag(M)) / max(len(ix) - 1, 1)
bekannt = np.array([all(len(zg.get(x, ())) >= 3 for x in kschreib[lem[li]][0][0]) for li in ql])
nzeichen = np.array([len(kschreib[lem[li]][0][0]) for li in ql])
print(f"N-d Woerter, deren haeufigste Schreibung nur Zeichen aus >= 3 Ankergruppen enthaelt: n={int(bekannt.sum())} | Rangplatz "
      f"{100*pct[bekannt].mean():.1f} % gegen {100*mittel_gleiche_laenge[bekannt].mean():.1f} % bei falschem Partner gleicher Laenge | Rang 1 {100*(pct[bekannt]==0).mean():.1f} %")
print(f"    uebrige Woerter (mindestens ein seltenes oder unbekanntes Zeichen): n={int((~bekannt).sum())} | Rangplatz {100*pct[~bekannt].mean():.1f} % "
      f"gegen {100*mittel_gleiche_laenge[~bekannt].mean():.1f} % | Rang 1 {100*(pct[~bekannt]==0).mean():.1f} %")
E["N_d"] = {"bekannt_n": int(bekannt.sum()), "bekannt_rangplatz": float(100 * pct[bekannt].mean()),
            "bekannt_vergleich": float(100 * mittel_gleiche_laenge[bekannt].mean()), "bekannt_rang1": float((pct[bekannt] == 0).mean()),
            "rest_n": int((~bekannt).sum()), "rest_rangplatz": float(100 * pct[~bekannt].mean()),
            "rest_vergleich": float(100 * mittel_gleiche_laenge[~bekannt].mean()), "rest_rang1": float((pct[~bekannt] == 0).mean())}

# ---------- N-e: Anker aus nur einer Quelle ----------
print("N-e Anker aus nur einer Ueberlieferung -> gewoehnliche Woerter (P4):")
E["N_e"] = {}
for name, behalten in (("Griechisch", {"gr"}), ("Keilschrift", {"akk"}), ("Koptisch", {"kop"}), ("Hebraeisch/Aramaeisch/Phoenizisch", {"heb", "sem"}),
                       ("heutiges Arabisch", {"arab"})):
    ohne = tuple({"gr", "akk", "kop", "heb", "sem", "arab"} - behalten)
    post = at.posten_aus(A, schreib, ohne_sprache=ohne)
    ngr = len({z["g"] for z in A if any(sp in behalten for sp, _, _ in z["formen"])})
    k = p4(at.Modell().lerne(post))[1]
    E["N_e"][name] = {"gruppen": ngr, **k}
    print(f"   {name:34s} {ngr:3d} Namensgruppen | Rangplatz {k['rangplatz_prozent']:5.1f} % | Rang 1 {100*k['rang1']:5.1f} % | unter den ersten 10: {100*k['unter_ersten_10']:5.1f} %")

# ---------- N-f: die Stadt der Acht ----------
STRICH = {"Z1": 1, "Z2": 3, "Z3": 3, "Z4": 2, "Z107": 4}
acht = collections.Counter()
for s, n in roh["117260"].items():
    acht[sum(STRICH.get(x, 0) for x in s)] += n
print(f"N-f Ortsname Chemenu (Lemma 117260; koptisch Schmun = 'acht', arabisch al-Aschmunein): Strichzahl je Beleg {dict(sorted(acht.items()))}")
E["N_f"] = {str(k): int(v) for k, v in acht.items()}

# ---------- N-g: Stichprobe der von Hand erstellten Ankertabelle ----------
gleich = n_vgl = 0
print("N-g Ankernamen, die auch in der koptischen Tabelle stehen: meine koptische Form gegen die Form der Tabelle")
for z in zeilen:
    tab = [r for r in kop_zeilen if r[2] == z["id"]]
    meine = [c for sp, _, c in z["formen"] if sp == "kop"]
    for r in tab:
        c = at.koptisch(r[1])
        if meine:
            n_vgl += 1
            gleich += c in meine
        print(f"   {z['form']:10s} Tabelle {r[1]:9s} {at.kl_text(c):5s} | Ankertabelle koptisch: {', '.join(at.kl_text(x) for x in meine) or '(keine koptische Form eingetragen)'}"
              f" | alle Formen: {', '.join(sorted({at.kl_text(x) for _, _, x in z['formen']}))}")
print(f"   Konsonantenfolge gleich: {gleich} von {n_vgl} vergleichbaren Namen")
E["N_g"] = {"gleich": gleich, "vergleichbar": n_vgl}
json.dump(E, open(ziel, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
