"""Zahlen als Anker: Pruefungen, die keine Sprache brauchen.

Aufruf: python3 -I zahlen_anker.py <aes-json-ordner> <ergebnis.json>

Z1 Kalender: Aus griechischer Ueberlieferung (Herodot II 4) und aus dem bis heute gebrauchten koptischen Kalender ist
   bekannt: 12 Monate zu 30 Tagen und 5 Zusatztage. Die aegyptische Datumsformel nennt Jahr, Monat (innerhalb einer von
   drei Jahreszeiten) und Tag. Vorhersage: Monatszahl 1..4, Tageszahl 1..30, genau drei Jahreszeiten, Zusatztage 5.
   Vergleich: die Jahreszahl derselben Formel (nicht durch den Kalender begrenzt) und alle uebrigen Zahlen im Korpus.
Z2 dasselbe auf der Zeichenebene: gezaehlt werden nur gezeichnete Striche (Einer) und Buegel (Zehner).
Z3 Rechenproben: Summenzeilen. Regeln vor dem Auszaehlen festgelegt:
   S1  dmd + genau drei unbeschaedigte ganze Zahlen a b c  ->  a = b + c  (Soll = Ist + Fehlbestand)
   S2  erste Zahl T nach dmd; Summanden = alle Zahlen desselben Satzes davor (ab dem vorigen dmd), mindestens zwei,
       alle unbeschaedigt und ganz  ->  T = Summe
   Zufallsvergleich S2: die Summen T zwischen den Faellen vertauscht.
Zahlenwerte stammen aus der Umschrift der Bearbeiter (Feld mdc); Z2 nutzt nur die Zeichenfolge.
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
SLOT = {"93": "monat", "854542": "tag", "850581": "jahr"}
ZEIT = {"216": "Achet (Ueberschwemmung)", "60300": "Peret (Aussaat)", "154850": "Schemu (Ernte)"}
STRICH = {"Z1": 1, "Z1A": 1, "Z2": 3, "Z2A": 3, "Z3": 3, "Z3A": 3, "Z4": 2, "Z4A": 2, "Z4B": 2, "Z107": 4}
ZEHNER = {"V20", "V20H", "V20h"}


def striche(h):
    """Zeichenfolge einer Zahl -> (Einer, Zehner) nur aus gezeichneten Strichen und Buegeln; None, wenn anderes vorkommt."""
    e = z = 0
    for x in h.split("-"):
        if x.isdigit():
            v = int(x)
            if v < 10:
                e += v
            elif v % 10 == 0 and v < 100:
                z += v // 10
            else:
                return None
        elif x in STRICH:
            e += STRICH[x]
        elif x in ZEHNER:
            z += 1
        else:
            return None
    return e, z


werte = collections.defaultdict(collections.Counter)
werte_datum = collections.Counter()
zeichen = collections.defaultdict(list)
jahreszeit = collections.Counter()
alle = collections.Counter()
ausnahmen = []
epag = collections.Counter()
s1, s2, tagmonat = [], [], []
n_dat = 0
for f in sorted(glob.glob(os.path.join(src, "_aes_*.json"))):
    korpus = os.path.basename(f)[5:-5]
    for satz in json.load(open(f, encoding="utf-8")).values():
        T = satz["token"]
        im_slot = set()
        for i, t in enumerate(T):
            sl = SLOT.get(str(t.get("lemmaID")))
            if sl and i + 1 < len(T) and T[i + 1].get("pos") == "numeral":
                n = T[i + 1]
                im_slot.add(i + 1)
                m = n.get("mdc") or ""
                datum = sl != "monat" or (i + 2 < len(T) and str(T[i + 2].get("lemmaID")) in ZEIT)
                if GANZ.match(m):
                    v = int(m)
                    werte[sl][v] += 1
                    if sl == "monat" and datum:
                        werte_datum[v] += 1
                        jahreszeit[ZEIT[str(T[i + 2].get("lemmaID"))]] += 1
                    if (sl == "monat" and v > 4) or (sl == "tag" and v > 30):
                        ausnahmen.append((korpus, sl, v, "Datum" if datum else "kein Datum (Dauer)",
                                          " ".join((x.get("mdc") or "?") for x in T[max(0, i - 3):i + 5]),
                                          (satz.get("sentence_translation") or "")[:140]))
                    if n.get("hiero") and (sl != "monat" or datum):
                        st = striche(n["hiero"])
                        if st is not None:
                            zeichen[sl].append((st, v, n["hiero"]))
            if (t.get("lemma_form") or "") == "ḥr.jw-rnp.t":
                for x in T[max(0, i - 1):i + 2]:
                    if x.get("pos") == "numeral":
                        epag[re.sub(r"[^\d]", "", x.get("mdc") or "") or "?"] += 1
        for i, t in enumerate(T):
            if t.get("pos") == "numeral" and i not in im_slot and GANZ.match(t.get("mdc") or ""):
                alle[int(t["mdc"])] += 1
        # ----- Summen -----
        lf = [(t.get("lemma_form") or "") for t in T]
        dm = [i for i, x in enumerate(lf) if x.startswith("dmḏ")]
        text = " ".join((t.get("mdc") or "?") for t in T)
        for di, i in enumerate(dm):
            nach = []
            j = i + 1
            while j < len(T) and T[j].get("pos") == "numeral":
                nach.append(T[j].get("mdc") or "")
                j += 1
            if len(nach) == 3 and all(GANZ.match(x) for x in nach):
                a, b, c = map(int, nach)
                s1.append((korpus, a, b, c, a == b + c, text[:150]))
            # S2
            k = i + 1
            while k < len(T) and k <= i + 3 and T[k].get("pos") != "numeral":
                k += 1
            if k < len(T) and k <= i + 3 and T[k].get("pos") == "numeral" and GANZ.match(T[k].get("mdc") or ""):
                start = dm[di - 1] + 1 if di else 0
                summ = [T[x].get("mdc") or "" for x in range(start, i) if T[x].get("pos") == "numeral"]
                if len(summ) >= 2 and all(GANZ.match(x) for x in summ):
                    s2.append((korpus, [int(x) for x in summ], int(T[k]["mdc"]), text[:170], (satz.get("sentence_translation") or "")[:150]))
        if "ẖr.t-hrw" in lf and "ẖr.t-ꜣbd" in lf:
            tagmonat.append((korpus, text[:200], (satz.get("sentence_translation") or "")[:200]))

E = {}
print("Z1 Kalender (Zahlen laut Umschrift, nur unbeschaedigte ganze Zahlen)")
jahr = werte["jahr"]
nj = sum(jahr.values())
nm, nmd, nt = sum(werte["monat"].values()), sum(werte_datum.values()), sum(werte["tag"].values())
na = sum(alle.values())
print(f"   Jahreszahlen:  n={nj}, Spanne {min(jahr)}..{max(jahr)}, davon <= 4: {100*sum(v for k, v in jahr.items() if k <= 4)/nj:.0f} %, <= 30: {100*sum(v for k, v in jahr.items() if k <= 30)/nj:.0f} %")
print(f"   Monatszahlen in Datumsformeln (Monat + Zahl + Jahreszeit): n={nmd}, Verteilung {sorted(werte_datum.items())}")
print(f"   Monatszahlen insgesamt (auch 'x Monate' als Dauer): n={nm}, Verteilung {sorted(werte['monat'].items())}")
print(f"   Tageszahlen:   n={nt}, Spanne {min(werte['tag'])}..{max(werte['tag'])}, ueber 30: {sum(v for k, v in werte['tag'].items() if k > 30)}")
print(f"   Jahreszeiten nach Monat + Zahl: {dict(jahreszeit)}")
print(f"   Zusatztage (hr.jw-rnp.t) mit Zahl: {dict(epag)}")
a4 = sum(v for k, v in alle.items() if k <= 4) / na
a30 = sum(v for k, v in alle.items() if k <= 30) / na
j4 = sum(v for k, v in jahr.items() if k <= 4) / nj
j30 = sum(v for k, v in jahr.items() if k <= 30) / nj
print(f"   Vergleich: uebrige Zahlen im Korpus n={na}: <= 4: {100*a4:.0f} %, <= 30: {100*a30:.0f} %")
print(f"   Waeren Monatszahlen verteilt wie Jahreszahlen, laegen alle {nmd} mit Wahrscheinlichkeit 10^{nmd*np.log10(j4):.0f} bei <= 4; "
      f"wie die uebrigen Zahlen: 10^{nmd*np.log10(a4):.0f}")
print(f"   Waeren Tageszahlen verteilt wie Jahreszahlen, laegen alle {nt} mit Wahrscheinlichkeit 10^{nt*np.log10(j30):.0f} bei <= 30; "
      f"wie die uebrigen Zahlen: 10^{nt*np.log10(a30):.0f}")
for a in ausnahmen:
    print("   Ausnahme:", a)
E["Z1"] = {"jahr": dict(sorted(jahr.items())), "monat_datum": dict(sorted(werte_datum.items())), "monat_alle": dict(sorted(werte["monat"].items())),
           "tag": dict(sorted(werte["tag"].items())), "jahreszeiten": dict(jahreszeit), "zusatztage": dict(epag),
           "uebrige_n": na, "uebrige_le4": a4, "uebrige_le30": a30, "jahr_le4": j4, "jahr_le30": j30,
           "ausnahmen": ausnahmen}

print("\nZ2 Kalender auf der Zeichenebene (nur Striche und Buegel gezaehlt)")
for sl, name, grenze in (("monat", "Monat", "hoechstens 4 Striche, kein Buegel"), ("tag", "Tag", "hoechstens 3 Buegel; bei 3 Buegeln kein Strich"),
                         ("jahr", "Jahr", "keine Grenze erwartet")):
    L = zeichen[sl]
    if not L:
        continue
    ein = collections.Counter(e for (e, z), _, _ in L)
    zeh = collections.Counter(z for (e, z), _, _ in L)
    gleich = sum(e + 10 * z == v for (e, z), v, _ in L)
    if sl == "monat":
        verst = [(h, v) for (e, z), v, h in L if e > 4 or z > 0]
    elif sl == "tag":
        verst = [(h, v) for (e, z), v, h in L if z > 3 or (z == 3 and e > 0) or e > 9]
    else:
        verst = []
    print(f"   {name}: n={len(L)} | Striche {sorted(ein.items())} | Buegel {sorted(zeh.items())} | Strichzahl = Zahl der Umschrift: {gleich}/{len(L)} | "
          f"Vorhersage ({grenze}) verletzt: {len(verst)} {verst[:5]}")
    E.setdefault("Z2", {})[sl] = {"n": len(L), "striche": dict(sorted(ein.items())), "buegel": dict(sorted(zeh.items())), "gleich": gleich, "verletzt": verst}

print("\nZ3 Rechenproben")
ok1 = sum(x[4] for x in s1)
print(f"   S1 Soll = Ist + Fehlbestand: {ok1} von {len(s1)} Faellen stimmen")
for x in s1:
    print(f"      {x[0]:18s} {x[1]} = {x[2]} + {x[3]}  {'stimmt' if x[4] else 'stimmt nicht'}   | {x[5]}")
ok2 = sum(sum(x[1]) == x[2] for x in s2)
rng = np.random.default_rng(20261113)
tot = np.array([x[2] for x in s2])
sm = np.array([sum(x[1]) for x in s2])
null = [int((sm == tot[rng.permutation(len(tot))]).sum()) for _ in range(5000)] if len(s2) else [0]
print(f"   S2 Summe der Posten = Summenzeile: {ok2} von {len(s2)} Faellen stimmen | bei vertauschten Summen im Mittel {np.mean(null):.2f}, hoechstens {max(null)}")
for x in s2:
    print(f"      {x[0]:18s} {' + '.join(map(str, x[1]))} = {sum(x[1])} ; Summenzeile {x[2]}  {'stimmt' if sum(x[1]) == x[2] else 'stimmt nicht'}\n         | {x[3]}\n         | {x[4]}")
print(f"   Tagesbedarf und Monatsbedarf im selben Satz: {len(tagmonat)}")
for x in tagmonat:
    print("     ", x)
E["Z3"] = {"S1": [list(x) for x in s1], "S1_stimmt": int(ok1), "S2": [list(x) for x in s2], "S2_stimmt": int(ok2),
           "S2_null_mittel": float(np.mean(null)), "S2_null_max": int(max(null)), "tag_monat": [list(x) for x in tagmonat]}
json.dump(E, open(ziel, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
