"""Ankertest: Zeichenwerte nur aus Namen mit fremder Ueberlieferung bestimmen und an Bekanntem pruefen.

Aufruf: python3 -I anker_test.py <tokens.jsonl.gz> <anker_tabelle.tsv> <signs_description.xml>
                                 <egyptian_etymologies.tab> <ergebnis.json> <zeichenwerte.tsv>

Idee: Ein Name ist ausserhalb Aegyptens ueberliefert (Keilschrift, Hebraeisch, Griechisch, Koptisch, heutiges
Arabisch). Seine Konsonanten sind damit ohne jede Hieroglyphenlesung bekannt. Das Modell bekommt nur Paare
(Zeichenfolge, fremde Konsonantenfolge) und lernt, welches Zeichen welche Konsonanten traegt.
Das PROTOKOLL unten wurde festgelegt, bevor das Modell zum ersten Mal auf den Ankern lief.
"""
import collections
import gzip
import hashlib
import itertools
import json
import math
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import delta_test as dt  # nur zeichen(): Feld 'hiero' -> Zeichencodes, Varianten zusammengelegt

PROTOKOLL = {
    "frage": "Lassen sich Zeichenwerte allein aus Namen mit fremder Ueberlieferung bestimmen, und passen die so "
             "bestimmten Werte zu den Standardwerten und zu gewoehnlichen Woertern mit koptischem Nachfolger?",
    "anker": "anker_tabelle.tsv, Satz A: Namen des Korpus mit vollstaendiger Zeichenfolge und fremder Form desselben "
             "Namens in derselben Zusammensetzung (Keilschrift, hebr. Bibel, Aramaeisch/Phoenizisch, Griechisch, "
             "Koptisch, heutiges Arabisch). Satz M (Koenigslisten Manetho/Herodot fuer Koenige vor der Spaetzeit) "
             "geht nicht ins Lernen ein und dient nur als zweiter Pruefsatz.",
    "klassen": "9 Konsonantenklassen der fremden Form: P(p b f) M N R(r l) T(t d) S(s z sch) C(emphatisch/Affrikate) "
               "K(k g q ch) H(h); Vokale, w, y, Aleph, Ajin entfallen",
    "schreibungen": "je Name die bis zu 4 haeufigsten Schreibungen mit Anteil >= 10 % (sonst die haeufigste), "
                    "Gewicht = Anteil; Varianten eines Zeichens zusammengelegt",
    "modell": {"art": "jedes Zeichen erzeugt 0 bis 3 Konsonantenklassen, Zeichen und Konsonanten in gleicher "
                      "Reihenfolge; Summe ueber alle Aufteilungen (EM)",
               "voranstellung": "die ersten k = 0..4 Zeichen duerfen als Block ans Ende rücken (Mischung mit "
                                "gelernten Anteilen); Nebenrechnung ohne diese Freiheit",
               "glaettung": "Wert je Zeichen = (erwartete Zaehlung + alpha * Grundverteilung) / (Summe + alpha), alpha = 2; "
                            "Grundverteilung = Laengenanteile x Klassenhaeufigkeiten, aus allen Zeichen geschaetzt",
               "start": "alle Zeichen gleich: Laengenanteile 0.30/0.50/0.15/0.05, Klassen gleich haeufig, "
                        "Anteile der Voranstellung 0.80/0.05/0.05/0.05/0.05",
               "durchlaeufe": 50},
    "pruefungen": {
        "P1": "zurueckgehaltene Namen: 10 Teile nach Namensgruppe; fuer jeden zurueckgehaltenen Namen Rang der richtigen "
              "fremden Konsonantenfolge unter allen verschiedenen Folgen der Tabelle (andere richtige Folgen desselben "
              "Namens ausgenommen); Kennzahlen Rang 1, mittlerer Kehrwert des Rangs, mittlerer Rangplatz in Prozent",
        "N1": "Gegenprobe: beim Lernen die fremden Formen zwischen den Namensgruppen vertauscht (5 Vertauschungen), "
              "geprueft an den echten zurueckgehaltenen Paaren",
        "P2": "Satz M mit dem Modell aus allen A-Ankern",
        "P3": "gelernter Wert (wahrscheinlichste Klassenfolge) gegen die Lautwerte der JSesh-Zeichenliste, fuer Zeichen "
              "in mindestens 3 Namensgruppen; a) die 20 starken Einkonsonantenzeichen, b) alle Zeichen mit nichtleerem "
              "gelerntem Wert; Zufallsvergleich: Standardwerte unter den geprueften Zeichen vertauscht (10000-mal)",
        "P4": "gewoehnliche Woerter: aegyptische Lemmata mit koptischem Nachfolger (Tabelle des Coptic Dictionary Online), "
              "Schreibungen aus dem Korpus (bis zu 3, Anteil >= 10 %); Rang der richtigen koptischen Konsonantenfolge "
              "unter allen verschiedenen koptischen Folgen der Tabelle; Zufallsvergleich: Partner innerhalb gleicher "
              "Laenge vertauscht (2000-mal); Nebenrechnung mit Ankern ohne koptische Formen",
        "P5": "Obergrenze: dasselbe Modell direkt an den koptischen Paaren gelernt (10 Teile nach Lemma)"},
    "entsprechungen_fuer_P3": "aegyptisch b p f -> P; m -> M; n -> N; r l -> R; t d -> T; s z sch -> S; q k g -> K; "
                              "h -> H; h mit Punkt -> H oder K; ch-Laute -> K, H oder S; tsch dsch -> T, S oder C; "
                              "Aleph, j, y, Ajin, w zaehlen nicht",
    "kriterien": {"K1": "P1: Rang 1 mindestens fuenfmal so oft wie bei Zufall und ueber jeder der 5 Vertauschungen; "
                        "mittlerer Rangplatz unter 25 %",
                  "K2": "P3a: mindestens 75 % der geprueften starken Einkonsonantenzeichen mit passender Klasse",
                  "K3": "P3b: genaue Uebereinstimmung ueber 99,9 % der Vertauschungen",
                  "K4": "P4: mittlerer Rangplatz besser als bei vertauschten Partnern (p < 0,001) und mindestens die "
                        "Haelfte des Abstands zwischen Zufall (50 %) und Obergrenze P5"},
    "seed": 20261112,
}

KLASSEN = "PMNRTSCKH"
K = len(KLASSEN)
NCH = 1 + K + K * K + K ** 3
KMAP = {**{c: "P" for c in "pbf"}, "m": "M", "n": "N", "r": "R", "l": "R", "t": "T", "d": "T", "s": "S", "z": "S",
        "S": "S", "c": "C", "k": "K", "g": "K", "q": "K", "x": "K", "h": "H", "H": "H"}
KOPT = {"ⲃ": "P", "ⲡ": "P", "ϥ": "P", "ⲫ": "P", "ⲙ": "M", "ⲛ": "N", "ⲣ": "R", "ⲗ": "R", "ⲧ": "T", "ⲇ": "T", "ϯ": "T",
        "ⲑ": "T", "ⲥ": "S", "ⲍ": "S", "ϣ": "S", "ϫ": "C", "ⲕ": "K", "ⲅ": "K", "ϭ": "K", "ⲭ": "K", "ϧ": "K", "ⳉ": "K",
        "ϩ": "H", "ⲝ": "KS", "ⲯ": "PS"}
KOPT_VOKAL = set("ⲁⲉⲏⲓⲟⲱⲩ")
EG = {"b": "P", "p": "P", "f": "P", "m": "M", "n": "N", "r": "R", "l": "R", "h": "H", "H": "HK", "x": "KHS", "X": "KHS",
      "s": "S", "z": "S", "S": "S", "q": "K", "k": "K", "g": "K", "t": "T", "d": "T", "T": "TSC", "D": "TSC"}
STARK1 = ["D58", "Q3", "I9", "G17", "N35", "D21", "O4", "V28", "Aa1", "F32", "S29", "O34", "N37", "N29", "V31", "W11",
          "X1", "V13", "D46", "I10"]
SCHWACH1 = ["M17", "G1", "D36", "G43", "Z7", "Z4"]
START_LAENGE = np.array([0.30, 0.50, 0.15, 0.05])
ROT = 4


def ch_index(t):
    if len(t) == 0:
        return 0
    if len(t) == 1:
        return 1 + t[0]
    if len(t) == 2:
        return 1 + K + K * t[0] + t[1]
    return 1 + K + K * K + K * K * t[0] + K * t[1] + t[2]


CH_TUP = [()] + [(a,) for a in range(K)] + [(a, b) for a in range(K) for b in range(K)] + \
         [(a, b, c) for a in range(K) for b in range(K) for c in range(K)]
assert all(ch_index(t) == i for i, t in enumerate(CH_TUP))
CH_LEN = np.array([len(t) for t in CH_TUP])
CH_CNT = np.zeros((NCH, K))
for _i, _t in enumerate(CH_TUP):
    for _a in _t:
        CH_CNT[_i, _a] += 1


def kl(kons):
    return tuple(KLASSEN.index(KMAP[c]) for c in kons)


def kl_text(t):
    return "".join(KLASSEN[a] for a in t) if len(t) else "-"


def koptisch(form):
    """Koptische Form -> Klassenfolge; Vokale entfallen, gleiche Nachbarbuchstaben zaehlen einfach."""
    out, vor = [], None
    for ch in form.lower():
        if ch in KOPT:
            if ch != vor:
                out += [KLASSEN.index(x) for x in KOPT[ch]]
        elif ch not in KOPT_VOKAL:
            vor = None
            continue
        vor = ch
    return tuple(out)


_IDX_CACHE = {}


def idx_von(c, n1):
    key = (c, n1)
    if key not in _IDX_CACHE:
        I = np.zeros((n1, 4), dtype=np.int32)
        V = np.zeros((n1, 4))
        for i in range(len(c) + 1):
            for l in range(0, min(3, i) + 1):
                I[i, l] = ch_index(c[i - l:i])
                V[i, l] = 1.0
        _IDX_CACHE[key] = (I, V)
    return _IDX_CACHE[key]


def grundverteilung(lam, q):
    return lam[CH_LEN] * np.prod(q[None, :] ** CH_CNT, axis=1)


class Modell:
    """Zeichen -> Verteilung ueber Klassenfolgen der Laenge 0..3; Lernen mit EM ueber alle Aufteilungen."""

    def __init__(self, alpha=2.0, rot=ROT, durchlaeufe=50):
        self.alpha, self.rot, self.durchlaeufe = alpha, rot, durchlaeufe

    def lerne(self, posten):
        """posten: Liste (Zeichenfolge als Tupel, Klassenfolge als Tupel, Gewicht)."""
        codes = sorted({z for s, _, _ in posten for z in s})
        self.z = {c: i for i, c in enumerate(codes)}
        S = len(codes)
        self.PAD, self.UNK = S, S + 1
        reihen = []
        for it, (s, c, w) in enumerate(posten):
            for k in range(self.rot + 1):
                if k == 0 or len(s) > k:
                    reihen.append((it, k, s[k:] + s[:k], c, w))
        R = len(reihen)
        M = max(len(r[2]) for r in reihen)
        N1 = max(len(r[3]) for r in reihen) + 1
        Sg = np.full((R, M), self.PAD, dtype=np.int64)
        IDX = np.zeros((R, N1, 4), dtype=np.int64)
        VAL = np.zeros((R, N1, 4))
        nlen = np.zeros(R, dtype=np.int64)
        item = np.zeros(R, dtype=np.int64)
        kk = np.zeros(R, dtype=np.int64)
        w = np.zeros(R)
        for r, (it, k, s, c, wt) in enumerate(reihen):
            Sg[r, :len(s)] = [self.z[x] for x in s]
            IDX[r], VAL[r] = idx_von(c, N1)
            nlen[r], item[r], kk[r], w[r] = len(c), it, k, wt
        lam, q = START_LAENGE.copy(), np.full(K, 1.0 / K)
        th0 = grundverteilung(lam, q)
        Theta = np.tile(th0, (S + 2, 1))
        Theta[self.PAD] = 0.0
        Theta[self.PAD, 0] = 1.0
        pi = np.array([0.80] + [0.20 / self.rot] * self.rot) if self.rot else np.array([1.0])
        ar = np.arange(R)
        n_it = len(posten)
        self.verlauf = []
        for _ in range(self.durchlaeufe):
            f = np.zeros((R, N1))
            f[:, 0] = 1.0
            Fs, Ts = [], []
            for j in range(M):
                T = Theta[Sg[:, j][:, None, None], IDX] * VAL
                fp = np.concatenate([np.zeros((R, 3)), f], axis=1)
                Fsh = np.stack([fp[:, 3 - l:3 - l + N1] for l in range(4)], axis=2)
                Fs.append(Fsh)
                Ts.append(T)
                f = (Fsh * T).sum(axis=2)
            F = f[ar, nlen]
            Lk = np.maximum(np.bincount(item, weights=pi[kk] * F, minlength=n_it), 1e-300)
            norm = np.bincount(item, weights=pi[kk], minlength=n_it)
            wi = np.bincount(item, weights=w, minlength=n_it) / np.maximum(np.bincount(item, minlength=n_it), 1)
            self.verlauf.append(float((wi * np.log(Lk / norm)).sum()))
            rw = w * pi[kk] / Lk[item]
            b = np.zeros((R, N1))
            b[ar, nlen] = 1.0
            zaehl = np.zeros((S + 2) * NCH)
            for j in range(M - 1, -1, -1):
                T, Fsh = Ts[j], Fs[j]
                G = Fsh * T * b[:, :, None] * rw[:, None, None]
                lin = Sg[:, j][:, None, None] * NCH + IDX
                zaehl += np.bincount(lin.ravel(), weights=G.ravel(), minlength=(S + 2) * NCH)
                bn = np.zeros((R, N1))
                for l in range(4):
                    bn[:, :N1 - l] += b[:, l:] * T[:, l:, l]
                b = bn
            n = zaehl.reshape(S + 2, NCH)[:S]
            lz = np.array([n[:, CH_LEN == L].sum() for L in range(4)]) + 1.0
            lam = lz / lz.sum()
            qc = (n.sum(axis=0)[:, None] * CH_CNT).sum(axis=0) + 1.0
            q = qc / qc.sum()
            th0 = grundverteilung(lam, q)
            Theta = np.zeros((S + 2, NCH))
            Theta[:S] = (n + self.alpha * th0) / (n.sum(axis=1, keepdims=True) + self.alpha)
            Theta[self.PAD, 0] = 1.0
            Theta[self.UNK] = th0
            if self.rot:
                pk = np.bincount(kk, weights=w * pi[kk] * F / Lk[item], minlength=self.rot + 1) + 0.5
                pi = pk / pk.sum()
        self.Theta, self.pi, self.n, self.lam, self.q = Theta, pi, n, lam, q
        return self

    def logp(self, s, IDXc, VALc, nc):
        """log P(Kandidat | Zeichenfolge) fuer alle Kandidaten zugleich."""
        si = [self.z.get(x, self.UNK) for x in s]
        Nc, N1, _ = IDXc.shape
        ar = np.arange(Nc)
        tot, norm = np.zeros(Nc), 0.0
        for k in range(self.rot + 1):
            if k and len(si) <= k:
                continue
            f = np.zeros((Nc, N1))
            f[:, 0] = 1.0
            for sg in si[k:] + si[:k]:
                T = self.Theta[sg][IDXc] * VALc
                fp = np.concatenate([np.zeros((Nc, 3)), f], axis=1)
                f = sum(fp[:, 3 - l:3 - l + N1] * T[:, :, l] for l in range(4))
            tot += self.pi[k] * f[ar, nc]
            norm += self.pi[k]
        return np.log(np.maximum(tot / norm, 1e-300))

    def wert(self, code):
        """wahrscheinlichste Klassenfolge eines Zeichens, ihre Wahrscheinlichkeit, Wahrscheinlichkeit fuer 'kein Laut'."""
        if code not in self.z:
            return None
        th = self.Theta[self.z[code]]
        i = int(th.argmax())
        return CH_TUP[i], float(th[i]), float(th[0]), float(self.n[self.z[code]].sum())


class Kandidaten:
    def __init__(self, folgen):
        self.folgen = sorted(set(folgen))
        self.pos = {c: i for i, c in enumerate(self.folgen)}
        N1 = max(len(c) for c in self.folgen) + 1
        self.IDX = np.stack([idx_von(c, N1)[0] for c in self.folgen]).astype(np.int64)
        self.VAL = np.stack([idx_von(c, N1)[1] for c in self.folgen])
        self.n = np.array([len(c) for c in self.folgen], dtype=np.int64)

    def punkte(self, modell, schreibungen):
        """gewichtetes Mittel der log-Wahrscheinlichkeiten ueber die Schreibungen eines Namens oder Lemmas."""
        return sum(a * modell.logp(list(s), self.IDX, self.VAL, self.n) for s, a in schreibungen)


def rang(punkte, wahr, aus=()):
    m = np.ones(len(punkte), dtype=bool)
    m[list(aus)] = False
    m[wahr] = False
    andere = punkte[m]
    return 1.0 + float((andere > punkte[wahr]).sum()) + 0.5 * float((andere == punkte[wahr]).sum()), int(m.sum()) + 1


def kennzahlen(raenge):
    r = np.array([x[0] for x in raenge])
    n = np.array([x[1] for x in raenge])
    return {"n": int(len(r)), "rang1": float((r < 1.5).mean()), "kehrwert": float((1 / r).mean()),
            "rangplatz_prozent": float(100 * ((r - 1) / (n - 1)).mean()),
            "zufall_rang1": float((1 / n).mean()),
            "zufall_kehrwert": float(np.mean([sum(1 / i for i in range(1, int(x) + 1)) / x for x in n]))}


def lade_anker(pfad):
    zeilen = []
    for l in open(pfad, encoding="utf-8"):
        if not l.strip() or l.startswith("#"):
            continue
        g, lid, form, satz, formen = l.rstrip("\n").split("\t")
        fl = []
        for f in formen.split(" ; "):
            sp, name, kons = f.split(":")
            fl.append((sp, name, kl(kons)))
        zeilen.append({"g": g, "id": lid, "form": form, "satz": satz, "formen": fl})
    return zeilen


def lade_schreibungen(tok_pfad, ids):
    z = collections.defaultdict(collections.Counter)
    for l in gzip.open(tok_pfad, "rt", encoding="utf-8"):
        for lid, h in json.loads(l)["tok"]:
            lid = str(lid)
            if h and lid in ids:
                s = tuple(dt.zeichen(h, True))
                if 1 <= len(s) <= 24:
                    z[lid][s] += 1
    return z


def waehle(counter, hoechstens, anteil=0.10):
    tot = sum(counter.values())
    top = [(s, c / tot) for s, c in counter.most_common(hoechstens) if c / tot >= anteil] or \
          [(counter.most_common(1)[0][0], 1.0)]
    summe = sum(a for _, a in top)
    return [(s, a / summe) for s, a in top]


def posten_aus(zeilen, schreib, ohne_sprache=()):
    P = []
    for z in zeilen:
        for sp, _, c in z["formen"]:
            if sp in ohne_sprache:
                continue
            for s, a in schreib[z["id"]]:
                P.append((s, c, a))
    return P


def standardwerte(xml_pfad):
    """JSesh: Zeichencode (Varianten zusammengelegt) -> Menge moeglicher Klassenfolgen laut Lautwertliste."""
    roh = collections.defaultdict(set)
    for sign, tr in re.findall(r'<hasTransliteration sign="([^"]+)" transliteration="([^"]*)"', open(xml_pfad, encoding="utf-8").read()):
        m = dt.US.match(sign) or dt.G.match(sign)
        if m:
            roh[m.group(1)].add(tr)
    out = {}
    for code, werte in roh.items():
        menge = set()
        for tr in werte:
            opt = [EG[ch] for ch in tr if ch in EG]
            if len(opt) > 6:
                continue
            for kombi in itertools.product(*opt):
                menge.add(tuple(KLASSEN.index(x) for x in kombi))
        out[code] = (sorted(werte), menge)
    return out


def urteil(gelernt, menge):
    if gelernt in menge:
        return "genau"
    if len(gelernt):
        for m in menge:
            if len(m) and len(m) != len(gelernt):
                a, b = (gelernt, m) if len(gelernt) < len(m) else (m, gelernt)
                if b[:len(a)] == a or b[-len(a):] == a:
                    return "teil"
    return "nein"


def main():
    tok_pfad, anker_pfad, xml_pfad, kop_pfad, ziel, ziel_tsv = sys.argv[1:7]
    sha = hashlib.sha256(json.dumps(PROTOKOLL, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    print(f"Protokoll sha256 {sha}")
    rng = np.random.default_rng(PROTOKOLL["seed"])
    E = {"protokoll": PROTOKOLL, "sha": sha}

    # ---------- Anker ----------
    zeilen = lade_anker(anker_pfad)
    kop_zeilen = [l.rstrip("\n").split("\t") for l in open(kop_pfad, encoding="utf-8")][1:]
    kop_ids = {r[2] for r in kop_zeilen if r[2] != "NA"}
    roh = lade_schreibungen(tok_pfad, {z["id"] for z in zeilen} | kop_ids)
    schreib = {z["id"]: waehle(roh[z["id"]], 4) for z in zeilen if roh.get(z["id"])}
    fehlend = [z["id"] for z in zeilen if z["id"] not in schreib]
    zeilen = [z for z in zeilen if z["id"] in schreib]
    A = [z for z in zeilen if z["satz"] == "A"]
    Mz = [z for z in zeilen if z["satz"] == "M"]
    gruppen = sorted({z["g"] for z in A})
    spr = collections.Counter(sp for z in A for sp, _, _ in z["formen"])
    pool = Kandidaten([c for z in zeilen for _, _, c in z["formen"]])
    zeichen_in_gruppen = collections.defaultdict(set)
    for z in A:
        for s, _ in schreib[z["id"]]:
            for x in s:
                zeichen_in_gruppen[x].add(z["g"])
    print(f"Anker: {len(gruppen)} Namensgruppen (Satz A), {len(A)} Lemmata, {sum(len(z['formen']) for z in A)} fremde Formen "
          f"{dict(spr)}; Satz M: {len({z['g'] for z in Mz})} Gruppen; ohne Schreibung im Korpus: {fehlend}")
    print(f"verschiedene Zeichen in den Ankern: {len(zeichen_in_gruppen)}, davon in >= 3 Gruppen: "
          f"{sum(len(v) >= 3 for v in zeichen_in_gruppen.values())}; verschiedene Konsonantenfolgen (Kandidaten): {len(pool.folgen)}")
    E["anker"] = {"gruppen_A": len(gruppen), "lemmata_A": len(A), "formen_A": int(sum(len(z["formen"]) for z in A)),
                  "sprachen": dict(spr), "gruppen_M": len({z["g"] for z in Mz}), "zeichen": len(zeichen_in_gruppen),
                  "zeichen_ab3": int(sum(len(v) >= 3 for v in zeichen_in_gruppen.values())), "kandidaten": len(pool.folgen)}

    def abfragen(zs):
        """je Lemma und verschiedener Klassenfolge eine Abfrage; Sprachen, die diese Folge bezeugen, werden notiert."""
        Q = []
        for z in zs:
            folgen = collections.defaultdict(set)
            for sp, _, c in z["formen"]:
                folgen[c].add(sp)
            for c, sps in folgen.items():
                Q.append({"g": z["g"], "id": z["id"], "c": c, "spr": sorted(sps), "aus": [pool.pos[x] for x in folgen if x != c]})
        return Q

    def pruefe(modell, zs):
        out = []
        cache = {}
        for q in abfragen(zs):
            if q["id"] not in cache:
                cache[q["id"]] = pool.punkte(modell, schreib[q["id"]])
            r, n = rang(cache[q["id"]], pool.pos[q["c"]], q["aus"])
            out.append({**{k: q[k] for k in ("g", "id", "spr")}, "c": kl_text(q["c"]), "rang": r, "n": n})
        return out

    # ---------- P1: zurueckgehaltene Namen ----------
    perm = rng.permutation(len(gruppen))
    teil = {gruppen[i]: int(j % 10) for j, i in enumerate(perm)}

    def kreuz(zs_lernen_fn, rot=ROT):
        erg = []
        for t in range(10):
            lern = [z for z in A if teil[z["g"]] != t]
            test = [z for z in A if teil[z["g"]] == t]
            m = Modell(rot=rot).lerne(posten_aus(zs_lernen_fn(lern), schreib))
            erg += pruefe(m, test)
        return erg

    p1 = kreuz(lambda zs: zs)
    k1 = kennzahlen([(x["rang"], x["n"]) for x in p1])
    # Streuung: Namensgruppen mit Zuruecklegen gezogen
    nach_g = collections.defaultdict(list)
    for x in p1:
        nach_g[x["g"]].append(x)
    gl = sorted(nach_g)
    bs = []
    for _ in range(2000):
        zug = [y for g in rng.choice(gl, len(gl)) for y in nach_g[g]]
        kz = kennzahlen([(y["rang"], y["n"]) for y in zug])
        bs.append((kz["rang1"], kz["rangplatz_prozent"], kz["kehrwert"]))
    bs = np.array(bs)
    k1["rang1_ki"] = [float(np.percentile(bs[:, 0], 2.5)), float(np.percentile(bs[:, 0], 97.5))]
    k1["rangplatz_ki"] = [float(np.percentile(bs[:, 1], 2.5)), float(np.percentile(bs[:, 1], 97.5))]
    print(f"\nP1 zurueckgehaltene Namen: {k1['n']} Abfragen | Rang 1: {100*k1['rang1']:.1f} % "
          f"[{100*k1['rang1_ki'][0]:.1f}; {100*k1['rang1_ki'][1]:.1f}] (Zufall {100*k1['zufall_rang1']:.2f} %) | "
          f"Kehrwert {k1['kehrwert']:.3f} (Zufall {k1['zufall_kehrwert']:.3f}) | mittlerer Rangplatz {k1['rangplatz_prozent']:.1f} % "
          f"[{k1['rangplatz_ki'][0]:.1f}; {k1['rangplatz_ki'][1]:.1f}] (Zufall 50 %)")
    nach_spr = {}
    for sp in sorted(spr):
        sub = [(x["rang"], x["n"]) for x in p1 if sp in x["spr"]]
        if sub:
            nach_spr[sp] = kennzahlen(sub)
            print(f"   Form bezeugt in {sp:5s}: n={nach_spr[sp]['n']:3d} | Rang 1 {100*nach_spr[sp]['rang1']:5.1f} % | "
                  f"Rangplatz {nach_spr[sp]['rangplatz_prozent']:5.1f} %")
    nach_laenge = {}
    for L in (1, 2, 3, 4):
        sub = [(x["rang"], x["n"]) for x in p1 if (len(x["c"]) == L if L < 4 else len(x["c"]) >= 4)]
        if sub:
            nach_laenge[L] = kennzahlen(sub)
            print(f"   Folgen mit {L}{'+' if L == 4 else ''} Konsonanten: n={nach_laenge[L]['n']:3d} | Rang 1 "
                  f"{100*nach_laenge[L]['rang1']:5.1f} % | Rangplatz {nach_laenge[L]['rangplatz_prozent']:5.1f} %")
    p1o = kreuz(lambda zs: zs, rot=0)
    k1o = kennzahlen([(x["rang"], x["n"]) for x in p1o])
    print(f"   Nebenrechnung ohne Voranstellung: Rang 1 {100*k1o['rang1']:.1f} % | Rangplatz {k1o['rangplatz_prozent']:.1f} %")
    E["P1"] = {"gesamt": k1, "nach_sprache": nach_spr, "nach_laenge": nach_laenge, "ohne_voranstellung": k1o, "abfragen": p1}

    # ---------- N1: vertauschte Paare ----------
    def vertauscht(zs):
        gs = sorted({z["g"] for z in zs})
        formen = {}
        for z in zs:
            formen.setdefault(z["g"], z["formen"])
        ziel_g = dict(zip(gs, [gs[i] for i in rng.permutation(len(gs))]))
        return [{**z, "formen": formen[ziel_g[z["g"]]]} for z in zs]

    n1 = []
    for v in range(5):
        kz = kennzahlen([(x["rang"], x["n"]) for x in kreuz(vertauscht)])
        n1.append(kz)
        print(f"N1 Vertauschung {v+1}: Rang 1 {100*kz['rang1']:.1f} % | Kehrwert {kz['kehrwert']:.3f} | Rangplatz {kz['rangplatz_prozent']:.1f} %")
    E["N1"] = n1

    # ---------- Modell aus allen A-Ankern ----------
    voll = Modell().lerne(posten_aus(A, schreib))
    print(f"\nModell aus allen A-Ankern: Anteile der Voranstellung k=0..4: {np.round(voll.pi, 3).tolist()} | "
          f"Laengenanteile 0..3: {np.round(voll.lam, 3).tolist()} | log-Likelihood Start {voll.verlauf[0]:.1f} -> Ende {voll.verlauf[-1]:.1f}")
    E["modell"] = {"pi": voll.pi.tolist(), "lam": voll.lam.tolist(), "verlauf": [voll.verlauf[0], voll.verlauf[-1]]}

    # ---------- P2: Satz M ----------
    p2 = pruefe(voll, Mz)
    k2 = kennzahlen([(x["rang"], x["n"]) for x in p2])
    print(f"P2 Koenigslisten (Satz M): {k2['n']} Abfragen | Rang 1 {100*k2['rang1']:.1f} % (Zufall {100*k2['zufall_rang1']:.2f} %) | "
          f"Rangplatz {k2['rangplatz_prozent']:.1f} %")
    for x in p2:
        print(f"   {x['g']:15s} {x['c']:6s} Rang {x['rang']:.1f} von {x['n']}")
    E["P2"] = {"gesamt": k2, "abfragen": p2}

    # ---------- P3: Standardwerte ----------
    std = standardwerte(xml_pfad)
    geprueft = sorted(c for c, v in zeichen_in_gruppen.items() if len(v) >= 3)
    tab = []
    for c in sorted(zeichen_in_gruppen, key=lambda c: -len(zeichen_in_gruppen[c])):
        wt, p, p0, n = voll.wert(c)
        werte, menge = std.get(c, ([], set()))
        tab.append({"zeichen": c, "gruppen": len(zeichen_in_gruppen[c]), "gelernt": kl_text(wt), "p": p, "p_leer": p0, "zaehlung": n,
                    "standard": werte, "urteil": urteil(wt, menge) if c in geprueft else "", "_w": wt, "_m": menge})
    with open(ziel_tsv, "w", encoding="utf-8") as fh:
        fh.write("zeichen\tnamensgruppen\tgelernter_wert\twahrscheinlichkeit\tw_kein_laut\tstandardwerte_jsesh\turteil\n")
        for t in tab:
            fh.write(f"{t['zeichen']}\t{t['gruppen']}\t{t['gelernt']}\t{t['p']:.2f}\t{t['p_leer']:.2f}\t{' '.join(t['standard'])}\t{t['urteil']}\n")
    T = {t["zeichen"]: t for t in tab}
    stark = [c for c in STARK1 if c in geprueft]
    stark_ok = [c for c in stark if len(T[c]["_w"]) == 1 and T[c]["_w"] in T[c]["_m"]]
    schwach = [c for c in SCHWACH1 if c in geprueft]
    schwach_ok = [c for c in schwach if len(T[c]["_w"]) == 0]
    print(f"\nP3a starke Einkonsonantenzeichen: {len(stark)} von 20 kommen in >= 3 Namensgruppen vor, davon {len(stark_ok)} mit passender Klasse")
    for c in STARK1:
        if c in T:
            t = T[c]
            print(f"   {c:4s} Gruppen {t['gruppen']:3d} | gelernt {t['gelernt']:4s} (p={t['p']:.2f}, kein Laut {t['p_leer']:.2f}) | "
                  f"Standard {'/'.join(t['standard'])[:18]:18s} | {'passt' if c in stark_ok else ('zu selten' if c not in geprueft else 'passt nicht')}")
        else:
            print(f"   {c:4s} kommt in den Ankern nicht vor")
    print(f"   schwache Zeichen (Aleph, j, y, Ajin, w): {len(schwach_ok)} von {len(schwach)} ohne Lautwert gelernt: "
          + ", ".join(f"{c}={T[c]['gelernt']}" for c in schwach))
    nl = [t for t in tab if t["zeichen"] in geprueft and len(t["_w"])]
    genau = sum(t["urteil"] == "genau" for t in nl)
    teilw = sum(t["urteil"] == "teil" for t in nl)
    null_g, null_t = [], []
    mengen = [t["_m"] for t in nl]
    for _ in range(10000):
        pm = rng.permutation(len(nl))
        u = [urteil(nl[i]["_w"], mengen[pm[i]]) for i in range(len(nl))]
        null_g.append(sum(x == "genau" for x in u))
        null_t.append(sum(x != "nein" for x in u))
    null_g, null_t = np.array(null_g), np.array(null_t)
    print(f"P3b Zeichen mit nichtleerem gelerntem Wert (in >= 3 Gruppen): {len(nl)} | genau {genau} ({100*genau/len(nl):.0f} %), "
          f"teilweise {teilw}, nein {len(nl)-genau-teilw} | bei vertauschten Standardwerten genau im Mittel {null_g.mean():.1f} "
          f"(hoechstens {null_g.max()}), p = {(1+(null_g >= genau).sum())/10001:.4f}; genau oder teilweise {genau+teilw} gegen {null_t.mean():.1f}, "
          f"p = {(1+(null_t >= genau+teilw).sum())/10001:.4f}")
    for t in nl:
        print(f"   {t['zeichen']:5s} Gruppen {t['gruppen']:3d} | gelernt {t['gelernt']:4s} (p={t['p']:.2f}) | Standard {'/'.join(t['standard'])[:28]:28s} | {t['urteil']}")
    leer = [t for t in tab if t["zeichen"] in geprueft and not len(t["_w"])]
    print(f"   ohne Lautwert gelernt: {len(leer)} Zeichen: " + " ".join(t["zeichen"] for t in leer))
    E["P3"] = {"stark_geprueft": stark, "stark_passt": stark_ok, "schwach_geprueft": schwach, "schwach_leer": schwach_ok,
               "nichtleer": len(nl), "genau": int(genau), "teil": int(teilw), "null_genau_mittel": float(null_g.mean()),
               "null_genau_max": int(null_g.max()), "p_genau": float((1 + (null_g >= genau).sum()) / 10001),
               "null_teil_mittel": float(null_t.mean()), "p_teil": float((1 + (null_t >= genau + teilw).sum()) / 10001),
               "tabelle": [{k: v for k, v in t.items() if not k.startswith("_")} for t in tab]}

    # ---------- P4: gewoehnliche Woerter gegen Koptisch ----------
    # Korrektur nach dem ersten Lauf (13.11.2026): 18 Lemmata der koptischen Tabelle sind selbst Ankernamen (Amun, Osiris,
    # Horus ...). Sie waren im ersten Lauf Teil von P4, obwohl das Modell an ihnen gelernt hatte, und sind jetzt ausgenommen.
    anker_ids = {z["id"] for z in lade_anker(anker_pfad)}
    doppelt = sorted({r[2] for r in kop_zeilen if r[2] in anker_ids})
    print(f"\nKorrektur: {len(doppelt)} Lemmata der koptischen Tabelle sind selbst Anker und werden in P4 und P5 nicht geprueft")
    paare = collections.defaultdict(set)
    alle_kop = set()
    for r in kop_zeilen:
        c = koptisch(r[1])
        if not len(c):
            continue
        alle_kop.add(c)
        if r[2] != "NA" and roh.get(r[2]) and r[2] not in anker_ids:
            paare[r[2]].add(c)
    kpool = Kandidaten(alle_kop)
    lem = sorted(paare)
    kschreib = {l: waehle(roh[l], 3) for l in lem}
    Q = [(li, kpool.pos[c]) for li, l in enumerate(lem) for c in sorted(paare[l])]
    ql = np.array([q[0] for q in Q])
    qt = np.array([q[1] for q in Q])
    laenge = kpool.n[qt]
    print(f"P4 gewoehnliche Woerter: {len(lem)} aegyptische Lemmata mit Zeichenfolge und koptischem Nachfolger, {len(Q)} Paare, "
          f"{len(kpool.folgen)} verschiedene koptische Konsonantenfolgen als Kandidaten")

    def rangplatz_matrix(modell, auswahl=None):
        P = np.zeros((len(lem), len(kpool.folgen)))
        for li, l in enumerate(lem):
            if auswahl is None or li in auswahl:
                sc = kpool.punkte(modell, kschreib[l])
                o = np.argsort(-sc, kind="stable")
                rg = np.empty(len(sc))
                rg[o] = np.arange(len(sc))
                # gleiche Punktzahlen: mittlerer Rang
                _, inv, cnt = np.unique(sc, return_inverse=True, return_counts=True)
                summe = np.bincount(inv, weights=rg)
                P[li] = (summe / cnt)[inv] / (len(sc) - 1)
        return P

    def p4_kennzahlen(P, name):
        pct = P[ql, qt]
        beob = float(100 * pct.mean())
        null = []
        for _ in range(2000):
            neu = qt.copy()
            for L in np.unique(laenge):
                ix = np.where(laenge == L)[0]
                neu[ix] = qt[ix][rng.permutation(len(ix))]
            null.append(100 * P[ql, neu].mean())
        null = np.array(null)
        rang1 = float((pct == 0).mean())
        top10 = float((pct * (len(kpool.folgen) - 1) < 10).mean())
        out = {"rangplatz_prozent": beob, "median_prozent": float(100 * np.median(pct)), "rang1": rang1, "unter_ersten_10": top10,
               "null_mittel": float(null.mean()), "null_min": float(null.min()), "p": float((1 + (null <= beob).sum()) / 2001)}
        print(f"   {name}: mittlerer Rangplatz {beob:.1f} % (Median {out['median_prozent']:.1f} %) | Rang 1 {100*rang1:.1f} % | "
              f"unter den ersten 10: {100*top10:.1f} % | vertauschte Partner {null.mean():.1f} % (kleinster Wert {null.min():.1f} %), p = {out['p']:.4f}")
        return out

    E["P4"] = {"lemmata": len(lem), "paare": len(Q), "kandidaten": len(kpool.folgen)}
    P_voll = rangplatz_matrix(voll)
    E["P4"]["anker"] = p4_kennzahlen(P_voll, "Werte aus allen Ankern        ")
    ohne_kop = Modell().lerne(posten_aus(A, schreib, ohne_sprache=("kop",)))
    E["P4"]["anker_ohne_koptisch"] = p4_kennzahlen(rangplatz_matrix(ohne_kop), "Anker ohne koptische Formen   ")
    nur_alt = Modell().lerne(posten_aus(A, schreib, ohne_sprache=("kop", "arab", "gr")))
    E["P4"]["anker_nur_keilschrift_semitisch"] = p4_kennzahlen(rangplatz_matrix(nur_alt), "nur Keilschrift und Semitisch ")
    vz = vertauscht(A)
    E["P4"]["vertauschte_anker"] = p4_kennzahlen(rangplatz_matrix(Modell().lerne(posten_aus(vz, schreib))), "vertauschte Anker (Gegenprobe)")
    # nach Laenge der koptischen Folge
    nl4 = {}
    for L in (1, 2, 3, 4):
        ix = (laenge == L) if L < 4 else (laenge >= 4)
        nl4[L] = {"n": int(ix.sum()), "rangplatz_prozent": float(100 * P_voll[ql[ix], qt[ix]].mean())}
        print(f"      koptische Folge mit {L}{'+' if L == 4 else ''} Konsonanten: n={nl4[L]['n']:4d} | Rangplatz {nl4[L]['rangplatz_prozent']:.1f} %")
    E["P4"]["nach_laenge"] = nl4

    # ---------- P5: Obergrenze, am Koptischen selbst gelernt ----------
    pm = rng.permutation(len(lem))
    kteil = {int(li): int(j % 10) for j, li in enumerate(pm)}
    P_ob = np.zeros_like(P_voll)
    for t in range(10):
        post = [(s, c, a) for li, l in enumerate(lem) if kteil[li] != t for c in paare[l] for s, a in kschreib[l]]
        m = Modell().lerne(post)
        test = {li for li in range(len(lem)) if kteil[li] == t}
        Pt = rangplatz_matrix(m, test)
        for li in test:
            P_ob[li] = Pt[li]
    E["P5"] = p4_kennzahlen(P_ob, "Obergrenze (am Koptischen gelernt)")
    anteil = (50 - E["P4"]["anker"]["rangplatz_prozent"]) / (50 - E["P5"]["rangplatz_prozent"])
    print(f"   Anteil des Abstands Zufall -> Obergrenze, den die Ankerwerte erreichen: {100*anteil:.0f} %")
    E["P4"]["anteil_obergrenze"] = float(anteil)

    # Beispiele: beste und schlechteste Paare, Zahlwoerter
    zahl_ids = {"136210": "2", "117280": "3", "850571": "4", "177840": "5", "128520": "6", "133760": "7", "117240": "8",
                "62450": "9", "78340": "10", "155320": "100", "113110": "1000", "183450": "10000", "863636": "1/2"}
    kopform = collections.defaultdict(list)
    for r in kop_zeilen:
        if r[2] != "NA":
            kopform[r[2]].append((r[1], r[3], r[7]))
    print("   Zahlwoerter (Bedeutung durch Rechnen gesichert):")
    zw = []
    for li, l in enumerate(lem):
        if l in zahl_ids:
            for c in sorted(paare[l]):
                pr = 100 * P_voll[li, kpool.pos[c]]
                zw.append({"zahl": zahl_ids[l], "lemma": kopform[l][0][1], "koptisch": kopform[l][0][0], "folge": kl_text(c),
                           "schreibung": "-".join(kschreib[l][0][0]), "rangplatz_prozent": float(pr)})
                print(f"      {zahl_ids[l]:>5s} {kopform[l][0][1]:8s} {'-'.join(kschreib[l][0][0])[:26]:26s} -> {kopform[l][0][0]:8s} {kl_text(c):5s} Rangplatz {pr:.1f} %")
    E["P4"]["zahlwoerter"] = zw
    bsp = []
    for li, l in enumerate(lem):
        for c in sorted(paare[l]):
            bsp.append((P_voll[li, kpool.pos[c]], l, c))
    bsp.sort()
    print("   Beispiele vom oberen Ende, aus der Mitte und vom unteren Ende (Lemma, Schreibung, koptisch, Rangplatz):")
    for sel in (bsp[:8], bsp[len(bsp) // 2 - 4:len(bsp) // 2 + 4], bsp[-8:]):
        for p, l, c in sel:
            print(f"      {kopform[l][0][1][:10]:10s} {'-'.join(kschreib[l][0][0])[:24]:24s} -> {kopform[l][0][0][:10]:10s} {kl_text(c):6s} {100*p:5.1f} %  ({kopform[l][0][2][:24]})")
        print("      ...")

    # ---------- Kriterien ----------
    kr = {"K1": bool(k1["rang1"] >= 5 * k1["zufall_rang1"] and all(k1["rang1"] > x["rang1"] for x in n1) and k1["rangplatz_prozent"] < 25),
          "K2": bool(len(stark) > 0 and len(stark_ok) / len(stark) >= 0.75),
          "K3": bool(E["P3"]["p_genau"] < 0.001),
          "K4": bool(E["P4"]["anker"]["p"] < 0.001 and anteil >= 0.5)}
    print("\nKriterien:", kr)
    E["kriterien"] = kr
    json.dump(E, open(ziel, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
