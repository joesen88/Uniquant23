"""Sind Koenigsnamen Namen von Zyklen? Auszaehlung am AES-Korpus.

Aufruf: python3 -I zyklen_test.py <aes-json-ordner> <ergebnis.json>

Erkundend: Die Regeln wurden nach einer ersten Sichtung der Jahresangaben festgelegt, nicht vorab eingefroren.
Zwei Lesarten und was sie vorhersagen:
  Zaehlperiode  Der Name bezeichnet den Zeitraum, in dem unter ihm Jahre gezaehlt werden. Das gilt per Bauart der
                Datumsformel; zu pruefen ist nur, ob die Zaehlung am Namen oder an der Person haengt.
  Zyklus        Der Name bezeichnet eine wiederkehrende Periode fester Laenge. Vorhersage: gleiche Hoechstzahl bei allen
                Namen, Jahreszahlen gleichmaessig ueber die Periode verteilt, derselbe Name kehrt wieder.
  Regierung     Der Name bezeichnet die Amtszeit eines Menschen. Vorhersage: Laengen unregelmaessig und nie ueber einem
                Menschenleben, kleine Jahreszahlen ueberwiegen, die Zaehlung laeuft weiter, wenn der Name wechselt.
A Titulatur   B Jahreszaehlung je Thronname   C Formel 'Beginn der Ewigkeit'   D welche Namen wiederkehren   E Verwandtschaft
"""
import collections
import glob
import json
import os
import re
import sys

import numpy as np

src, ziel = sys.argv[1], sys.argv[2]
GANZ = re.compile(r"^\d+$")
JAHR = "850581"            # rnp.t-zp, Regierungsjahr
VERWANDT = {"zꜣ-nswt": "Königssohn", "zꜣ-nswt-n-ẖ.t=f": "leiblicher Königssohn", "zꜣ.t-nswt": "Königstochter",
            "zꜣ.t-nswt-n.t-ẖ.t=f": "leibliche Königstochter", "ḥm.t-nswt": "Königsgemahlin",
            "ḥm.t-nswt-wr.t": "große Königsgemahlin", "mw.t-nswt": "Königsmutter", "sn-nswt": "Königsbruder",
            "sn.t-nswt": "Königsschwester"}

info, tokens_je_name = {}, collections.Counter()
jahre_alle = []                                   # (text, jahr)
verknuepft = []                                   # (text, jahr, [koenigs-lemmata], art)
paar_tg = collections.Counter()                   # (thron, geburt) im Titel 'nswt-bjtj X zꜣ-Rꜥw Y'
verwandt = collections.Counter()
sed = []
beispiele = {}
for f in sorted(glob.glob(os.path.join(src, "_aes_*.json"))):
    korpus = os.path.basename(f)[5:-5]
    offen = None                                  # Jahresangabe des vorigen Satzes ohne Koenigsnamen
    for satz in json.load(open(f, encoding="utf-8")).values():
        T = satz["token"]
        text = satz["text"]
        kn = [(i, t["lemmaID"]) for i, t in enumerate(T) if t.get("name") == "kings_name" and t.get("lemmaID")]
        for i, k in kn:
            tokens_je_name[k] += 1
            info.setdefault(k, (T[i].get("lemma_form") or "", (T[i].get("cotext_translation") or "")))
        lf = [(t.get("lemma_form") or "") for t in T]
        for x in lf:
            if x in VERWANDT:
                verwandt[x] += 1
        jz = [(i, int(T[i + 1]["mdc"])) for i, t in enumerate(T) if str(t.get("lemmaID")) == JAHR and i + 1 < len(T)
              and T[i + 1].get("pos") == "numeral" and GANZ.match(T[i + 1].get("mdc") or "")]
        # Jahresangabe aus dem Satz davor: der Koenigsname steht am Anfang dieses Satzes
        if offen and offen[0] == text and kn and kn[0][0] < 20 and not (jz and jz[0][0] < kn[0][0]):
            grenze = jz[0][0] if jz else len(T)
            verknuepft.append((text, offen[1], [k for i, k in kn if i < min(grenze, kn[0][0] + 25)], "Folgesatz", korpus))
        offen = None
        for n, (i, y) in enumerate(jz):
            jahre_alle.append((text, y))
            ende = jz[n + 1][0] if n + 1 < len(jz) else len(T)
            ks = [k for j, k in kn if i < j < min(ende, i + 25)]
            if ks:
                verknuepft.append((text, y, ks, "selber Satz", korpus))
            elif n == len(jz) - 1:
                offen = (text, y)
            if any("HAb-sd" in (t.get("mdc") or "") for t in T[i:i + 14]) and "nḥḥ" in lf[i:i + 8]:
                sed.append((korpus, y, " ".join((t.get("mdc") or "?") for t in T)[:140], (satz.get("sentence_translation") or "")[:160]))
        if len(jz) >= 2 and "xft" in [t.get("mdc") for t in T] and "beni" not in beispiele and jz[0][1] == 43:
            beispiele["doppeldatum"] = (" ".join((t.get("mdc") or "?") for t in T)[:330], (satz.get("sentence_translation") or "")[:420])
        if jz and jz[0][1] == 1 and "nḥḥ" in lf and "ḏ.t" in lf and "jahr1" not in beispiele:
            beispiele["jahr1"] = (" ".join((t.get("mdc") or "?") for t in T)[:200], (satz.get("sentence_translation") or "")[:260])
        # Titel: Thronname ... zꜣ-Rꜥw ... Geburtsname
        for a in range(len(kn)):
            for b in range(a + 1, len(kn)):
                if kn[b][0] - kn[a][0] <= 6 and "zꜣ-Rꜥw" in lf[kn[a][0] + 1:kn[b][0]]:
                    paar_tg[(kn[a][1], kn[b][1])] += 1


def art(k):
    ueb = info[k][1]
    if ueb.startswith("[Thron"):
        return "thron"
    if re.match(r"\[(Horus|Nebti|Gold)", ueb):
        return "horus_nebti_gold"
    return "geburt"


E = {}
arten = collections.Counter(art(k) for k in info)
thron_re = sum("Rꜥw" in info[k][0] for k in info if art(k) == "thron")
wh = [(info[k][0], info[k][1][:50], tokens_je_name[k]) for k in info if info[k][0].startswith("Wḥm-msw.t")]
print("A Titulatur")
print(f"   Koenigsnamen im Korpus: {len(info)} Lemmata, {sum(tokens_je_name.values())} Belege | Thronnamen {arten['thron']}, Horus-, Nebti- und Goldnamen "
      f"{arten['horus_nebti_gold']}, Geburtsnamen und Namen ohne Angabe {arten['geburt']}")
print(f"   Thronnamen mit dem Sonnengott Re im Namen: {thron_re} von {arten['thron']}")
print(f"   Namen 'Wiederholung der Geburten' (Wḥm-msw.t): {wh}")
print(f"   Datumsformel 'Jahr 1, Beginn der Ewigkeit': {beispiele.get('jahr1')}")
E["A"] = {"lemmata": len(info), "belege": int(sum(tokens_je_name.values())), "arten": dict(arten), "thron_mit_re": thron_re, "wiederholung": wh,
          "jahr1": beispiele.get("jahr1")}

print("\nB Jahreszaehlung")
einmal = sorted(set(jahre_alle))
y = np.array([j for _, j in einmal])
print(f"   Jahresangaben mit unbeschaedigter Zahl: {len(jahre_alle)}, je Text und Jahr einmal gezaehlt: {len(y)} | hoechste Zahl {y.max()} | "
      f"Median {np.median(y):.0f} | bis 10: {100*(y <= 10).mean():.0f} %, 11 bis 30: {100*((y > 10) & (y <= 30)).mean():.0f} %, ueber 30: {100*(y > 30).mean():.0f} %")
gl = np.array([(y <= g).mean() for g in range(1, y.max() + 1)])
print(f"   bei gleichmaessiger Verteilung ueber 1..{y.max()} laegen {100*10/y.max():.0f} % bis 10; groesste Abweichung der Summenkurve von der Gleichverteilung: "
      f"{np.abs(gl - np.arange(1, y.max() + 1) / y.max()).max():.2f}")
aera = collections.defaultdict(set)               # Thronname -> {(text, jahr)}
namen_im_jahr = collections.defaultdict(lambda: collections.defaultdict(set))
ohne_thron = 0
for text, jahr, ks, wie, korpus in verknuepft:
    th = [k for k in ks if art(k) == "thron"]
    if not th:
        ohne_thron += 1
        continue
    aera[th[0]].add((text, jahr))
    for k in ks:
        if art(k) == "geburt":
            namen_im_jahr[th[0]][k].add(jahr)
print(f"   mit Koenigsnamen verknuepft: {len(verknuepft)} Angaben ({sum(v[3] == 'Folgesatz' for v in verknuepft)} ueber den Folgesatz), "
      f"davon {len(verknuepft) - ohne_thron} mit Thronnamen; {len(aera)} verschiedene Thronnamen")
L = max(max(j for _, j in v) for v in aera.values())
tab = []
for k, v in sorted(aera.items(), key=lambda kv: -max(j for _, j in kv[1])):
    js = sorted(j for _, j in v)
    p = (max(js) / L) ** len(js)
    tab.append({"thronname": info[k][0], "koenig": info[k][1][:40], "angaben": len(js), "jahre": js, "hoechstes": max(js), "p_fester_zyklus": p})
    print(f"   {info[k][0][:26]:26s} {info[k][1][:34]:34s} {len(js):2d} Angaben | hoechstes Jahr {max(js):2d} | Jahre {js}"[:200])
mehr = [t for t in tab if t["angaben"] >= 3 and t["hoechstes"] < L]
print(f"   Fester Zyklus der Laenge {L} mit gleichmaessig verteilten Angaben: Wahrscheinlichkeit, dass alle Angaben eines Namens so niedrig liegen wie beobachtet:")
for t in mehr:
    print(f"      {t['thronname'][:24]:24s} {t['angaben']} Angaben, alle bis {t['hoechstes']:2d}: {t['p_fester_zyklus']:.1e}")
print(f"      alle {len(mehr)} Namen zusammen: 10^{sum(np.log10(t['p_fester_zyklus']) for t in mehr):.0f}")
print("   Wechsel des Geburtsnamens innerhalb einer Zaehlung:")
wechsel = []
for th, d in namen_im_jahr.items():
    if len(d) >= 2:
        z = {info[k][0]: sorted(v) for k, v in d.items()}
        wechsel.append({"thronname": info[th][0], "geburtsnamen": z})
        print(f"      {info[th][0]}: {z}")
print(f"   Doppeldatum: {beispiele.get('doppeldatum')}")
E["B"] = {"angaben": len(jahre_alle), "einmal": int(len(y)), "hoechste": int(y.max()), "median": float(np.median(y)), "bis10": float((y <= 10).mean()),
          "ueber30": float((y > 30).mean()), "verteilung": {int(k): int(v) for k, v in sorted(collections.Counter(y.tolist()).items())},
          "verknuepft": len(verknuepft), "tabelle": tab, "wechsel": wechsel, "doppeldatum": beispiele.get("doppeldatum")}

print("\nC Jahresangabe, eroeffnet mit 'Beginn der Ewigkeit ... Millionen von Sedfesten' (Erneuerungsfest)")
sj = sorted({(k, j) for k, j, _, _ in sed})
print(f"   {len(sed)} Saetze | Jahre: {sorted(j for _, j in sj)} | 'erstes Sedfest im Jahr 30' kommt im Korpus nicht vor")
for s in sed[:14]:
    print("     ", s)
E["C"] = {"jahre": sorted(j for _, j in sj), "saetze": [list(s) for s in sed]}

print("\nD Welche Namen kehren wieder? (Titel 'Koenig X, Sohn des Re Y', mindestens 2 Belege je Paar)")
g2t, t2g = collections.defaultdict(dict), collections.defaultdict(dict)
for (a, b), n in paar_tg.items():
    if n >= 2 and art(a) == "thron" and art(b) == "geburt":
        g2t[b][a] = n
        t2g[a][b] = n
vg = collections.Counter(len(v) for v in g2t.values())
vt = collections.Counter(len(v) for v in t2g.values())
print(f"   Geburtsnamen nach Zahl verschiedener Thronnamen: {sorted(vg.items())} | Thronnamen nach Zahl verschiedener Geburtsnamen: {sorted(vt.items())}")
for b, d in sorted(g2t.items(), key=lambda kv: -len(kv[1])):
    if len(d) >= 2:
        print(f"   Geburtsname {info[b][0]} ({info[b][1][:24]}) steht bei: " + ", ".join(f"{info[a][0]} ({n})" for a, n in d.items()))
for a, d in sorted(t2g.items(), key=lambda kv: -len(kv[1])):
    if len(d) >= 2:
        print(f"   Thronname {info[a][0]} ({info[a][1][:30]}) steht bei: " + ", ".join(f"{info[b][0]} ({n})" for b, n in d.items()))
E["D"] = {"geburt_nach_thronzahl": dict(vg), "thron_nach_geburtszahl": dict(vt),
          "geburt": {info[b][0]: {info[a][0]: n for a, n in d.items()} for b, d in g2t.items() if len(d) >= 2},
          "thron": {info[a][0]: {info[b][0]: n for b, n in d.items()} for a, d in t2g.items() if len(d) >= 2}}

print("\nE Verwandtschaftstitel am Koenig")
for k, n in verwandt.most_common():
    print(f"   {VERWANDT[k]:26s} {k:22s} {n}")
print(f"   zusammen {sum(verwandt.values())}")
E["E"] = {VERWANDT[k]: int(n) for k, n in verwandt.items()}
json.dump(E, open(ziel, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
