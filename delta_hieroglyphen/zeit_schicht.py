"""Schicht fuer die Zeitanalyse: Lemma-Folge je Text mit Ergaenzungsmarke, Handschrift und Jahresgrenzen.

Aufruf: python3 -I zeit_schicht.py <aes-json-ordner> <metadaten.jsonl> <ausgabe.jsonl.gz>

Je Wort [Lemma-ID, e]:  e = 0 erhalten, 1 teilweise ergaenzt, 2 ganz ergaenzt (alle Buchstaben stehen in
eckigen Klammern, das Wort ist also vom Bearbeiter eingesetzt, meist nach einer Parallele).
Zerstoerte oder unlesbare Stellen stehen als [null, 9]; mehrere hintereinander zaehlen als eine.
Die Liste 'art' laeuft parallel dazu: 1 = Name einer Person oder eines Koenigs, sonst 0.

Handschrift ('hs'): Inventarnummer, sonst Name, Ort und Datierung. Bei Pyramidentexten und Grabinschriften
nennt die Quelle nur die Wand; dort gilt Ort plus Datierung, bei den Pyramidentexten ist das die Pyramide.
"""
import collections
import glob
import gzip
import json
import os
import re
import sys

src, meta_pfad, ziel = sys.argv[1], sys.argv[2], sys.argv[3]
meta = {}
for z in open(meta_pfad, encoding="utf-8"):
    m = json.loads(z)
    meta[m["t"]] = m

LEER = {"", "unbekannt", "[ohne inventarnummer]", "-"}
WAND = {"bbawpyramidentexte", "bbawgrabinschriften", "bbawfelsinschriften", "bbawgraeberspzt"}


def handschrift(m):
    c = m["c"]
    if c in WAND:
        return f"{c}|{m['ort']}|{m['nb']}|{m['na']}"
    inv = re.sub(r"\s+", " ", m["inv"]).strip().lower()
    if inv not in LEER and len(inv) >= 2:
        return f"{c}|inv:{inv}"
    return f"{c}|{m['hs']}|{m['ort']}|{m['nb']}|{m['na']}"


def ergaenzt(mdc):
    if "[" not in mdc:
        return 0
    return 1 if re.search(r"[A-Za-z]", re.sub(r"\[[^\]]*\]", "", mdc)) else 2


n = collections.Counter()
with gzip.open(ziel, "wt", encoding="utf-8") as fh:
    for f in sorted(glob.glob(os.path.join(src, "_aes_*.json"))):
        korpus = os.path.basename(f)[5:-5]
        data = json.load(open(f, encoding="utf-8"))
        texte = collections.OrderedDict()
        arten = {}
        for satz in data.values():
            tok = texte.setdefault(satz["text"], [])
            art = arten.setdefault(satz["text"], [])
            for tk in satz.get("token", []):
                lid = tk.get("lemmaID")
                if not lid:
                    if not tok or tok[-1][1] != 9:
                        tok.append([None, 9])
                        art.append(0)
                    continue
                tok.append([lid, ergaenzt(tk.get("mdc") or "")])
                # 1 = Name einer Person oder eines Koenigs (das "Namensfeld" eines Spruchs)
                art.append(1 if tk.get("pos") == "entity_name" and tk.get("name") in ("person_name", "kings_name") else 0)
        for t, tok in texte.items():
            m = meta.get(t)
            if m is None or not any(x[0] for x in tok):
                continue
            fh.write(json.dumps({"c": korpus, "t": t, "o": m["o"], "titel": m["titel"], "hs": handschrift(m),
                                 "hsname": m["hs"], "nb": m["nb"], "na": m["na"],
                                 "label": m["datierung"][0] if m["datierung"] else "", "tok": tok,
                                 "art": arten[t]}, ensure_ascii=False) + "\n")
            n["texte"] += 1
            for lid, e in tok:
                n[f"e{e}"] += 1
        del data
print(dict(n))
