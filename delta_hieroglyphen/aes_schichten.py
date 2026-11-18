"""Schritt 1: AES-Korpus auf zwei Schichten reduzieren.

Aufruf: python3 -I aes_schichten.py <aes-json-ordner> <ausgabe.jsonl.gz>

Je Text eine Zeile: Teilkorpus, Text-ID, Bearbeiter, Datierung und die Wortfolge
in Dateireihenfolge. Je Wort: Lemma-ID (Deutungsschicht) und die Zeichenfolge im
Rohformat des Feldes 'hiero' (Schriftschicht; nur bei vollstaendiger Schreibung).
Woerter ohne Lemma-ID (Zerstoerungen, Unlesbares) entfallen.
"""
import collections
import glob
import gzip
import json
import os
import sys

src, out = sys.argv[1], sys.argv[2]
n_text = n_tok = n_hiero = 0
with gzip.open(out, "wt", encoding="utf-8") as fh:
    for f in sorted(glob.glob(os.path.join(src, "_aes_*.json"))):
        korpus = os.path.basename(f)[5:-5]
        data = json.load(open(f, encoding="utf-8"))
        texte = collections.OrderedDict()
        for satz in data.values():
            t = satz["text"]
            e = texte.setdefault(t, {"o": collections.Counter(), "d": collections.Counter(), "tok": []})
            e["o"][satz.get("owner") or "?"] += 1
            e["d"][satz.get("date") or "unknown"] += 1
            for tk in satz.get("token", []):
                lid = tk.get("lemmaID")
                if not lid:
                    continue
                e["tok"].append([lid, tk.get("hiero") or ""])
        for t, e in texte.items():
            if not e["tok"]:
                continue
            fh.write(json.dumps({"c": korpus, "t": t, "o": e["o"].most_common(1)[0][0],
                                 "d": e["d"].most_common(1)[0][0], "tok": e["tok"]}, ensure_ascii=False) + "\n")
            n_text += 1
            n_tok += len(e["tok"])
            n_hiero += sum(1 for x in e["tok"] if x[1])
        del data
print(f"Texte {n_text} | Woerter mit Lemma {n_tok} | davon mit Zeichenfolge {n_hiero}")
