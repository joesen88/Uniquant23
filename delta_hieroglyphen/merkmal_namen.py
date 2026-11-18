"""Lesbare Namen fuer Merkmale: Lemma-ID -> Umschrift, Zeichencode -> Lautwert laut JSesh-Zeichenliste.

Aufruf: python3 -I merkmal_namen.py <aes-json-ordner> <signs_description.xml> <ausgabe.json>
Die Zeichenliste stammt aus https://github.com/rosmord/jsesh (jsesh/src/main/resources/jsesh/glyphs/resources/).
"""
import collections
import glob
import json
import os
import re
import sys

src, xml, ziel = sys.argv[1], sys.argv[2], sys.argv[3]
lemma, zahl = {}, collections.Counter()
for f in sorted(glob.glob(os.path.join(src, "_aes_*.json"))):
    for satz in json.load(open(f, encoding="utf-8")).values():
        for tk in satz.get("token", []):
            lid = tk.get("lemmaID")
            if lid:
                zahl[lid] += 1
                lemma.setdefault(lid, tk.get("lemma_form") or "")
werte = collections.defaultdict(list)
for sign, tr, typ in re.findall(r'<hasTransliteration sign="([^"]+)" transliteration="([^"]*)" type="([^"]*)"', open(xml, encoding="utf-8").read()):
    if typ == "phonogram" and tr not in werte[sign]:
        werte[sign].append(tr)
json.dump({"lemma": {k: lemma[k] for k, _ in zahl.most_common(4000)},
           "zeichen": {k: v[:3] for k, v in werte.items()}}, open(ziel, "w", encoding="utf-8"), ensure_ascii=False)
print("Lemmata", min(4000, len(lemma)), "| Zeichen mit Lautwert", len(werte))
