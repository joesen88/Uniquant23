"""Datierung und Handschrift je Text aus der Quelledition AED-TEI holen.

Aufruf: python3 -I zeit_metadaten.py <aed-tei-klon> <tokens.jsonl.gz> <ausgabe.jsonl>

<aed-tei-klon> ist ein Klon von https://github.com/simondschweitzer/aed-tei (auch ohne Dateiinhalte,
also mit --filter=blob:none --no-checkout; die noetigen Dateien werden dann in einem Zug nachgeladen).
Gelesen wird nur der Kopf jeder Datei: Titel, Handschrift, Schrift, Objekt, Herkunft und die
Jahresgrenzen der Datierung (notBefore, notAfter).
"""
import gzip
import html
import json
import re
import subprocess
import sys

repo, tokens, ziel = sys.argv[1], sys.argv[2], sys.argv[3]
git = ["git", "-C", repo]

texte = [json.loads(z) for z in gzip.open(tokens, "rt", encoding="utf-8")]
sha = {}
for zeile in subprocess.run(git + ["ls-tree", "-r", "HEAD"], capture_output=True, text=True, check=True).stdout.splitlines():
    kopf, pfad = zeile.split("\t", 1)
    if pfad.startswith("files/") and pfad.endswith(".xml"):
        sha[pfad[6:-4]] = kopf.split()[2]
brauche = [sha[t["t"]] for t in texte if t["t"] in sha]
print(f"Texte {len(texte)}, mit Datei {len(brauche)}")

# fehlende Dateiinhalte in einem Zug nachladen (wie Git es bei Teilklonen intern tut)
fehlt = subprocess.run(git + ["cat-file", "--batch-check", "--batch-all-objects"], capture_output=True, text=True).stdout
vorhanden = {z.split()[0] for z in fehlt.splitlines() if " blob " in z}
holen = [s for s in brauche if s not in vorhanden]
if holen:
    print(f"lade {len(holen)} Dateien nach ...")
    subprocess.run(git + ["-c", "fetch.negotiationAlgorithm=noop", "fetch", "origin", "--no-tags", "--no-write-fetch-head",
                          "--recurse-submodules=no", "--filter=blob:none", "--stdin"],
                   input="\n".join(holen) + "\n", text=True, check=True, capture_output=True)

TAG = re.compile(r"<[^>]+>")


def rein(s):
    return re.sub(r"\s+", " ", html.unescape(TAG.sub(" ", s or ""))).strip()


def eins(muster, s):
    m = re.search(muster, s, re.S)
    return rein(m.group(1)) if m else ""


p = subprocess.Popen(git + ["cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
n = 0
with open(ziel, "w", encoding="utf-8") as out:
    for t in texte:
        s = sha.get(t["t"])
        if not s:
            continue
        p.stdin.write((s + "\n").encode())
        p.stdin.flush()
        kopfzeile = p.stdout.readline().split()
        groesse = int(kopfzeile[2])
        daten = p.stdout.read(groesse + 1)[:-1].decode("utf-8", "replace")
        kopf = daten.split("</teiHeader>")[0]
        od = re.search(r"<origDate>(.*?)</origDate>", kopf, re.S)
        od = od.group(1) if od else ""
        nb = [int(x) for x in re.findall(r'notBefore="(-?\d+)"', od)]
        na = [int(x) for x in re.findall(r'notAfter="(-?\d+)"', od)]
        ident = re.search(r"<msIdentifier>(.*?)</msIdentifier>", kopf, re.S)
        ident = ident.group(1) if ident else ""
        out.write(json.dumps({
            "t": t["t"], "c": t["c"], "o": t["o"], "d": t["d"], "n": len(t["tok"]),
            "titel": eins(r"<titleStmt>\s*<title>(.*?)</title>", kopf),
            "hs": eins(r"<msName>(.*?)</msName>", ident), "inv": eins(r"<idno>(.*?)</idno>", ident),
            "sammlung": eins(r"<repository[^>]*>(.*?)</repository>", ident),
            "schrift": eins(r"<textLang[^>]*>(.*?)</textLang>", kopf), "sprache": eins(r'<textLang mainLang="([^"]*)"', kopf),
            "objekt": eins(r"<objectType[^>]*>(.*?)</objectType>", kopf),
            "ort": eins(r"<origPlace[^>]*>(.*?)</origPlace>", kopf),
            "nb": min(nb) if nb else None, "na": max(na) if na else None,
            "datierung": [rein(x) for x in re.findall(r"<date [^>]*>(.*?)</date>", od, re.S)],
        }, ensure_ascii=False) + "\n")
        n += 1
p.stdin.close()
p.wait()
print("geschrieben:", ziel, n)
