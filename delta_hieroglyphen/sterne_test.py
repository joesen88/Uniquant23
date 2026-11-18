"""Sind Koenige Sterne oder Sternbilder? Auszaehlung am AES-Korpus (erkundend).

Aufruf: python3 -I sterne_test.py <aes-json-ordner> <ergebnis.json>

A  Welche Stern- und Sternbildnamen enthaelt das Korpus, und wo?
B  Stehen Koenigsname und Sternwort haeufiger im selben Satz, als bei Unabhaengigkeit zu erwarten waere? (je Teilkorpus)
C  Enthaelt ein Koenigsname einen Sternnamen?
D  Dekanlisten (die aegyptische Sternfolge) im Korpus?   E  '70 Tage' (Unsichtbarkeit des Sirius, Dauer der Balsamierung)
"""
import collections
import glob
import json
import os
import re
import sys

from scipy.stats import fisher_exact

src, ziel = sys.argv[1], sys.argv[2]
RX = re.compile(r"(?<![A-Za-zäöüß])Stern|Morgenstern|Orion|Sothis|Sirius|Zirkumpolar|Großen Bären|Planet")
AUS = re.compile(r"Stern-Jer|Güterverwalter|Priester")
stern, wo, info = collections.Counter(), collections.defaultdict(collections.Counter), {}
n = collections.defaultdict(lambda: [0, 0, 0, 0])          # Korpus -> alle, Koenig, Stern, beide
bsp, koenig_formen, dekan, siebzig = [], set(), collections.Counter(), []
for f in sorted(glob.glob(os.path.join(src, "_aes_*.json"))):
    c = os.path.basename(f)[5:-5]
    for satz in json.load(open(f, encoding="utf-8")).values():
        T = satz["token"]
        st = [t for t in T if t.get("lemmaID") and t.get("pos") != "preposition" and RX.search(t.get("cotext_translation") or "")
              and not AUS.search(t.get("cotext_translation") or "")]
        kn = [t for t in T if t.get("name") == "kings_name" and t.get("lemmaID")]
        for t in kn:
            koenig_formen.add(t.get("lemma_form") or "")
        for t in T:
            if "Dekan" in (t.get("cotext_translation") or ""):
                dekan[(t.get("lemma_form"), (t.get("cotext_translation") or "")[:40])] += 1
        for i, t in enumerate(T[:-1]):
            if (t.get("lemma_form") or "") == "hrw" and (T[i + 1].get("mdc") or "") == "70":
                siebzig.append((c, " ".join((x.get("mdc") or "?") for x in T)[:120], (satz.get("sentence_translation") or "")[:150]))
        n[c][0] += 1
        n[c][1] += bool(kn)
        n[c][2] += bool(st)
        n[c][3] += bool(kn and st)
        for t in st:
            stern[t["lemmaID"]] += 1
            wo[t["lemmaID"]][c] += 1
            info.setdefault(t["lemmaID"], (t.get("lemma_form") or "", (t.get("cotext_translation") or "")[:46]))
        if kn and st and c == "bbawpyramidentexte" and len(bsp) < 400:
            bsp.append((" ".join((t.get("mdc") or "?") for t in T)[:130], (satz.get("sentence_translation") or "")[:170]))
E = {}
print(f"A Stern- und Sternbildnamen: {len(stern)} Lemmata, {sum(stern.values())} Belege; davon in den Pyramidentexten "
      f"{sum(v['bbawpyramidentexte'] for v in wo.values())}, im Totenbuch {sum(v['tb'] for v in wo.values())}")
for k, v in stern.most_common(14):
    print(f"   {v:4d} {info[k][0][:14]:14s} {info[k][1]:46s} {dict(wo[k].most_common(2))}")
E["A"] = {"lemmata": len(stern), "belege": int(sum(stern.values())), "liste": [(info[k][0], info[k][1], int(v)) for k, v in stern.most_common(30)]}
print("\nB Koenigsname und Sternwort im selben Satz")
E["B"] = {}
for c in sorted(n, key=lambda c: -n[c][3]):
    a, k, s, b = n[c]
    if k >= 50:
        odds, p = fisher_exact([[b, k - b], [s - b, a - k - s + b]], alternative="greater")
        print(f"   {c:22s} Saetze {a:6d} | mit Koenig {k:5d} | mit Stern {s:4d} | mit beiden {b:4d} (erwartet {k*s/a:6.1f}) | Verhaeltnis {b/(k*s/a) if s else 0:4.2f} | p = {p:.2g}")
        E["B"][c] = {"saetze": a, "koenig": k, "stern": s, "beide": b, "erwartet": k * s / a, "p": float(p)}
gleich = [x for x in bsp if re.search(r"\b(pw|pj|pi)\b", x[0])]
print(f"   Pyramidentexte: {len(bsp)} Saetze mit Koenig und Stern; Beispiele:")
for x in (gleich[:4] + bsp[:2]):
    print("     ", x[1])
E["B"]["beispiele"] = [x[1] for x in gleich[:6]]
print("\nC Sternname als Bestandteil eines Koenigsnamens")
sternformen = {info[k][0] for k in stern if len(info[k][0]) >= 3}
teile = collections.Counter(t for f in koenig_formen for t in f.split("-"))
treffer = sorted(x for x in sternformen if x in teile)
print(f"   {len(koenig_formen)} Koenigsnamen, {len(sternformen)} Sternnamen; gemeinsame Bestandteile: {treffer or 'keine'}")
E["C"] = treffer
print(f"\nD Lemmata mit 'Dekan' in der Uebersetzung: {dict(dekan) or 'keine'}")
print(f"E 'Tag 70' / '70 Tage': {len(siebzig)} Saetze")
for x in siebzig[:6]:
    print("     ", x)
E["D"], E["E"] = {str(k): v for k, v in dekan.items()}, [list(x) for x in siebzig]
json.dump(E, open(ziel, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
