# Burrows' Delta am ägyptischen Korpus (AES)

Stand: 12.11.2026. Frage: Funktioniert Burrows' Delta auf hieroglyphischen Texten, auch ohne Lesung, und wie stark hängt es vom Vergleichskorpus ab?

Δ(A,B) = (1/n) Σᵢ |zᵢ(A) − zᵢ(B)|, zᵢ(X) = (fᵢ(X) − μᵢ)/σᵢ. Weil sich μᵢ in der Differenz kürzt, gilt Δ(A,B) = (1/n) Σᵢ |fᵢ(A) − fᵢ(B)| / σᵢ. Das Vergleichskorpus wirkt nur über σᵢ und über die Auswahl der n Merkmale.

## Dateien

| Datei | Zweck |
| --- | --- |
| `aes_schichten.py` | reduziert das AES-Korpus je Text auf Lemma-Folge und Zeichenfolge |
| `tokens.jsonl.gz` | Ergebnis davon: 12.959 Texte, 779.011 Wörter mit Lemma, 251.177 davon mit vollständiger Zeichenfolge |
| `delta_test.py` | Haupttest. Das Protokoll steht oben im Skript und wurde festgelegt, bevor die erste Distanz gerechnet war |
| `delta_nachtrag.py` | Auswertungen, die erst nach dem ersten Lauf dazukamen (nicht Teil des Protokolls) |
| `delta_gegenprobe.py` | Kernzahlen mit eigenständig geschriebenem Code nachgerechnet |
| `norm_test.py` | erster Norm-Test über vier grobe Epochenklassen |
| `zeit_metadaten.py` | holt Jahresgrenzen und Handschrift je Text aus der Quelledition AED-TEI |
| `metadaten.jsonl` | Ergebnis davon für alle 12.959 Texte |
| `zeit_schicht.py`, `zeit_schicht.jsonl.gz` | Lemma-Folge je Text mit Ergänzungsmarke, Namensfeld, Handschrift und Jahresgrenzen |
| `halbwertszeit.py` | Halbwertszeit des Wortlauts; Protokoll oben im Skript, festgelegt nach Sichtung der Metadaten und vor der ersten Rechnung gegen die Zeit |
| `halbwertszeit_nachtrag.py` | Auswertungen nach dem Protokoll-Lauf: Sicherheit der Reihenfolge, Namensfeld, Handschriftenpaare |
| `halbwertszeit_gegenprobe.py` | Rückgewinnung bekannter Raten aus künstlichen Daten, Prüfung von Ausrichtung und Überlappung |
| `phasen_test.py` | prüft, ob die Abweichungen zwischen Abschriften einen Takt, eine Lage oder feste Stellen haben |
| `buendel_test.py` | zerlegt die Delta-Struktur in Textgruppe, Zeit und Bearbeiter; Protokoll oben im Skript |
| `buendel_nachtrag.py` | Bereinigung mit Schrumpfung, Zeichenpaare je Bearbeiter, Schriftart als vierter Faktor |
| `merkmal_namen.py`, `merkmal_namen.json` | lesbare Namen: Umschrift der Lemmata, Lautwerte der Zeichen laut JSesh-Zeichenliste |
| `anker_tabelle.tsv` | Ankertabelle: 131 Namensgruppen des Korpus mit fremder Überlieferung, dazu 12 Königsnamen der Königslisten |
| `anker_test.py` | Ankertest: Zeichenwerte nur aus Namen lernen, an zurückgehaltenen Namen, an der Standardliste und an koptischen Wörtern prüfen; Protokoll oben im Skript |
| `anker_nachtrag.py` | Auswertungen nach dem Protokoll-Lauf: vertauschte Anker, gezogene Anker, einzelne Überlieferungen, Zahlwörter |
| `anker_gegenprobe.py` | Rückgewinnung an künstlicher Schrift; zweiter Weg über einfache Zählung |
| `zahlen_anker.py` | Zahlen als Anker: Kalenderstruktur, Strichzählung, Rechenproben |
| `zyklen_test.py` | Königsnamen als Zyklen? Jahreszählung je Thronname, wiederkehrende Namen, Verwandtschaftstitel |
| `zyklen_perioden.py` | Sothis, Mond, Sedfest und Viehzählung gegen die Jahreszählung |
| `sterne_test.py` | Könige als Sterne? Sternnamen im Korpus, Zusammentreffen mit Königsnamen |
| `einheit_test.py` | Was umfasst eine Zählnummer? Lesarten 56 Tage, 56 Wochen, 56 Mondmonate |
| `egyptian_etymologies.tab` | ägyptische Vorgänger koptischer Wörter, unverändert aus dem Coptic Dictionary Online |
| `ausgabe/` | Protokolle und Zahlen aller Läufe |

Aufruf (Python 3 mit NumPy und SciPy):

```
python3 delta_test.py tokens.jsonl.gz ergebnis.json
python3 delta_nachtrag.py tokens.jsonl.gz nachtrag.json
python3 delta_gegenprobe.py tokens.jsonl.gz
```

`aes_schichten.py` braucht den Ordner `files/aes` aus dem AES-Repository.

## Aufbau

- **Einheit:** Abschnitt aus 1.000 aufeinanderfolgenden Wörtern. Lange Texte ergeben reine Abschnitte; Reste und kurze Texte werden je Teilkorpus in Dateireihenfolge aneinandergehängt.
- **Wortebene:** Lemma-IDs, also die Deutungsschicht. 765 Abschnitte aus 12 Teilkorpora.
- **Zeichenebene:** Gardiner-Codes, also die Schriftschicht ohne Lesung. Nur Wörter mit vollständiger Schreibung: 243 Abschnitte aus 7 Teilkorpora, im Mittel 2.943 Zeichen. Codevarianten wie V31A sind auf das Grundzeichen zusammengelegt.
- **Merkmale:** die 150 häufigsten Lemmata bzw. Zeichen.
- **Ausschluss:** Als Nachbar zählt nie ein Abschnitt mit gemeinsamem Text und keiner, der mehr als 5 % der Lemma-Fünfergruppen teilt (Parallelüberlieferung, Formeln).
- **Etikett:** das Teilkorpus der Datenbank. Es bündelt Gattung, Epoche und Bearbeitungsprojekt.

## Ergebnis in der primären Einstellung

| Test: nächster Nachbar … | Wortebene | Zeichenebene |
| --- | --- | --- |
| stammt aus demselben Text | 51,1 % (67 von 131; Zufallsnachbar 0,5 %) | 76,8 % (63 von 82; Zufallsnachbar 1,6 %) |
| hat dasselbe Teilkorpus | 93,2 % (713 von 765; größte Klasse 25,0 %) | 92,2 % (224 von 243; größte Klasse 37,4 %) |
| Nullmodell: alle Wörter gemischt | 12,4 % | 20,9 % |
| dasselbe Teilkorpus, nur fremde Bearbeiter zugelassen | 46,5 % statt 92,0 % (Zufallsnachbar 5,1 %) | 63,8 % statt 94,3 % (Zufallsnachbar 13,8 %) |
| dasselbe Teilkorpus, nur fremde Epoche zugelassen | 67,9 % statt 95,5 % (Zufallsnachbar 8,5 %) | 42,7 % statt 98,5 % (Zufallsnachbar 13,8 %) |

„Statt“ nennt die Quote derselben Anfragen, wenn alle Kandidaten zugelassen sind. In der Epochen-Zeile zählen Abschnitte mit gemischter Datierung mit. Nur eindeutig datierte Abschnitte ergeben 72,7 % (Wort) und 72,2 % (Zeichen); diese Variante ist nachträglich gerechnet.

Die vier vorab gesetzten Kriterien sind erfüllt. K4 (nächster Nachbar wechselt bei mehr als 5 % der Abschnitte) war aber zu lasch gesetzt, siehe unten.

## Was Delta hier erkennt

Ein Merkmal bestimmen, während die anderen festgehalten sind (nachträglich; nur Anfragen, bei denen unter den Kandidaten beide Antworten vorkommen):

| Gesucht, festgehalten | Wortebene | Zeichenebene |
| --- | --- | --- |
| Teilkorpus, gleicher Bearbeiter | 88,1 % (Zufall 58,2 %) | 83,9 % (Zufall 42,3 %) |
| Teilkorpus, gleiche Epoche | 91,7 % (Zufall 33,6 %) | 86,4 % (Zufall 39,8 %) |
| Epoche, gleiches Teilkorpus | 63,8 % (Zufall 41,8 %) | 87,3 % (Zufall 44,1 %) |
| Bearbeiter, gleiches Teilkorpus und gleiche Epoche | 73,1 % (Zufall 53,5 %) | 87,7 % (Zufall 64,6 %) |

Alle drei Größen sind einzeln nachweisbar. „Bearbeiter“ lässt sich nicht von „Handschriften, die dieser Bearbeiter ediert hat“ trennen.

## Vergleichskorpus

Nimmt man statt aller Abschnitte nur ein Teilkorpus als Vergleichskorpus:

| | Wortebene | Zeichenebene |
| --- | --- | --- |
| nächster Nachbar wechselt | 61–82 % | 34–49 % |
| … bei Zufallsauswahl gleicher Größe | 38–51 % | 22–28 % |
| Antwort (Teilkorpus) wechselt | 8–16 % | 3–9 % |
| … bei Zufallsauswahl gleicher Größe | 4–6 % | 3–4 % |
| Trefferquote | 84–94 % | 89–92 % |

Der nächste Nachbar wechselt also schon durch Stichprobenrauschen oft. Systematisch ist der Unterschied bei der Antwort und bei der Trefferquote, am stärksten auf der Wortebene.

## Robustheit und Prüfung

- **n und Distanz:** 18 Kombinationen (n = 30 bis 500; Burrows, Cosinus-Delta, L1 ohne σ) ergeben 76,7–94,8 % (Wort) und 84,4–94,2 % (Zeichen).
- **Ohne σ:** L1 auf rohen Häufigkeiten erreicht 91,9 % und 90,5 %.
- **Abschnittslänge:** 500, 1.000, 2.000 Wörter ergeben 86,9 / 93,2 / 94,7 % (Wort) und 88,8 / 92,2 / 93,9 % (Zeichen).
- **Parallelstellen-Schwelle:** von 1 % bis ohne Schwelle 89,1–95,4 % (Wort) und 90,1–93,0 % (Zeichen).
- **Codes unverändert:** 91,8 %.
- **Ebenenvergleich** auf denselben Wörtern: Zeichen 92,2 %, Lemmata 90,5 %; die Distanzmatrizen korrelieren mit ρ = 0,65 (29.022 Paare), die Antwort stimmt bei 90,1 % der Abschnitte überein.
- **Gegenprobe:** Der zweite Code liefert dieselben Trefferzahlen (67/131, 713/765, 139/299; 63/82, 224/243, 111/174). Ordnet man die Zeichen nach Gesamtzahl statt nach mittlerem Anteil, werden daraus 225/243 und 115/174.

## Grenzen

- Delta vergleicht Häufigkeitsprofile im selben Merkmalsraum. Ägyptisch gegen Griechisch oder Latein lässt sich damit nicht messen.
- Delta prüft nicht, ob die Lesung stimmt: Die Lemma-Schicht ist aus den Zeichen abgeleitet.
- Teilkorpus, Epoche und Bearbeiter fallen im Korpus weitgehend zusammen. Die Pyramidentexte haben einen einzigen Bearbeiter, eine Epoche und fast keine Zeichencodierung; ihre Sonderstellung (99,1 % auf der Wortebene) lässt sich deshalb nicht zuordnen.
- Zufallsraten und p-Werte behandeln Anfragen als unabhängig; die Konfidenzintervalle in den Protokollen ziehen ganze Texte.

# Halbwertszeit des Wortlauts

Frage: Wie schnell zerfällt gemeinsamer Wortlaut mit dem Zeitabstand, und ist ein Ritualtext darin eine Norm?

```
python3 zeit_metadaten.py <aed-tei-klon> tokens.jsonl.gz metadaten.jsonl
python3 zeit_schicht.py <aes/files/aes> metadaten.jsonl zeit_schicht.jsonl.gz
python3 halbwertszeit.py zeit_schicht.jsonl.gz ergebnis.json
python3 halbwertszeit_nachtrag.py zeit_schicht.jsonl.gz nachtrag.json
python3 halbwertszeit_gegenprobe.py zeit_schicht.jsonl.gz
```

Die ersten beiden Schritte sind schon gelaufen; ihre Ergebnisse liegen bei.

## Aufbau

- **Zeit:** Jede Handschrift hat in der Quelledition Jahresgrenzen. Datum ist die Mitte; die Unsicherheit wird mitgezogen, indem jede Wiederholung das Datum neu zwischen den Grenzen wählt. Texte ohne Datierung und Datierungen, die mehr als 450 Jahre offen lassen, entfallen. Es bleiben 12.494 Texte mit 744.191 Wörtern.
- **Handschrift:** Inventarnummer, sonst Name, Ort und Datierung. Bei Pyramidentexten und Grabinschriften nennt die Quelle nur die Wand; dort gilt Ort plus Datierung. Bei den Pyramidentexten ist das die Pyramide, bei Grabinschriften eine Gruppe gleich datierter Gräber eines Ortes.
- **Ergänzungen:** Vom Bearbeiter ganz ergänzte Wörter (5,2 % aller Wörter, bei den Pyramidentexten 10,8 %) und zerstörte Stellen zählen nie als Übereinstimmung.
- **M1, gemeinsamer Wortlaut:** Abschnitte zu 1.000 Wörtern, je Textgruppe in Datierungsreihenfolge gebildet. Maß ist der Anteil gemeinsamer Lemma-Fünfergruppen zwischen zwei Abschnitten verschiedener Handschriften. Modell: Hintergrund + A · exp(−λ · Zeitabstand).
- **M2, Abschreibtreue:** derselbe Spruch oder dasselbe Werk (gleicher Titel) in zwei Handschriften. Nach Ausrichtung der Lemma-Folgen: gleiche Stellen geteilt durch gleiche plus abweichende Stellen im gemeinsamen Bereich. Abweichend sind Ersetzungen, Zusätze und Auslassungen. Modell: a₀ · exp(−μ · Zeitabstand).
- **Kennzahlen:** Normtreue je Jahrhundert = exp(−100 · Rate), Halbwertszeit = ln 2 / Rate.
- **Unsicherheit:** 1.000 Wiederholungen, in denen Handschriften (M1) oder Werke (M2) mit Zurücklegen gezogen werden. Nullmodell: Datierungen zwischen den Handschriften vertauscht.

## M1: gemeinsamer Wortlaut zwischen Abschnitten verschiedener Handschriften

| Textgruppe | Abschnitte, Handschriften | Normtreue je Jahrhundert (95 %) | Halbwertszeit | p (Nullmodell) |
| --- | --- | --- | --- | --- |
| Briefe | 44, 312 | 29,9 % (14,5–48,0) | 57 Jahre (36–94) | 0,001 |
| Literatur | 175, 515 | 57,7 % (27,2–77,3) | 126 Jahre (53–269) | 0,001 |
| Grabinschriften | 92, 62 | 82,8 % (62,8–106,9) | 367 Jahre (ab 149) | 0,033 |
| Totenbuch | 108, 16 | 95,6 % (69,3–122,1) | 1.554 Jahre (ab 189) | 0,298 |
| Pyramidentexte | 98, 5 | nicht bestimmbar | – | 0,353 |
| Medizin | 51, 25 | nicht bestimmbar | – | 0,341 |
| Späte Totenliteratur | 36, 7 | nicht bestimmbar | – | 0,266 |

„Nicht bestimmbar“ heißt: Das Intervall reicht von der unteren bis zur oberen Suchgrenze. Bei den Pyramidentexten liegen nur fünf Pyramiden über 108 Jahre vor.

Beobachtete Mittel je Zeitabstand (Anteil gemeinsamer Fünfergruppen, in Klammern Zahl der Paare):

| Zeitabstand | Briefe | Literatur | Grabinschriften | Totenbuch |
| --- | --- | --- | --- | --- |
| unter 50 Jahre | 2,52 % (156) | 0,54 % (2.342) | 7,05 % (1.340) | 1,01 % (1.042) |
| 50–150 | 1,29 % (174) | 0,31 % (2.313) | 7,65 % (1.983) | 0,03 % (23) |
| 150–300 | 0,50 % (161) | 0,21 % (2.087) | 3,71 % (528) | 0,27 % (51) |
| 300–600 | 0,26 % (81) | 0,05 % (3.006) | 3,34 % (22) | 0,73 % (662) |
| 600–1.000 | 0,10 % (300) | 0,05 % (4.583) | – | 0,77 % (480) |
| über 1.000 | 0,06 % (33) | 0,002 % (637) | – | 0,56 % (2.240) |

Der Hintergrund zwischen verschiedenen Textgruppen liegt bei 0,012 %. Die beiden dünn besetzten Totenbuch-Klassen stammen aus wenigen kleinen Handschriften.

Vorhersage V1 (Totenbuch > Literatur > Briefe) gilt in 94 % der Ziehungen; Totenbuch über Literatur in 98 %. Dass das Totenbuch überhaupt zerfällt, gilt nur in 80 %.

Robustheit: Mit Abschnitten zu 500 Wörtern 27,0 / 55,7 / 84,7 / 96,0 %, nur mit ganz erhaltenen Wörtern 31,4 / 60,9 / 83,0 / 95,7 % (Briefe / Literatur / Grabinschriften / Totenbuch).

## M2: derselbe Spruch oder dasselbe Werk in zwei Handschriften

| Textgruppe | Paare, Werke, Handschriften | gleichzeitige Abschriften | Normtreue je Jahrhundert | Halbwertszeit | p (Nullmodell) |
| --- | --- | --- | --- | --- | --- |
| Totenbuch | 273, 116, 11 | 75,1 % | 99,06 % (über Werke 98,4–99,4; über Handschriften 77,8–122,1) | 7.357 Jahre | 0,243 |
| Literatur | 46, 17, 56 | 89,2 % | 97,34 % (über Werke 91,8–99,5; über Handschriften 89,5–100,8) | 2.574 Jahre | 0,047 |
| Pyramidentexte | 383, 191, 5 | 84,6 %, mit Namensfeld 89,1 % | kein Verlust in 108 Jahren messbar | – | 0,911 |

- **Totenbuch je Zeitabstand:** unter 50 Jahre 74,7 % (59 Paare, Median 78,5 %, Quartile 71,8–84,3 %), 300–1.000 Jahre 71,6 % (85 Paare), über 1.000 Jahre 66,9 % (128 Paare, Median 68,5 %).
- **Handschriftenpaare des Totenbuchs:** pMaiherperi gegen pNu (gleichzeitig) 71,9 %; pNu gegen pJuja (43 Jahre) 78,3 %; pNu gegen pBM 10793 (444 Jahre) 74,6 %; pBM 10793 gegen pTurin 1791 (788 Jahre) 68,3 %; pNu gegen pTurin 1791 (1.232 Jahre, 86 Sprüche) 67,7 %.
- **Namensfeld (nachträglich):** Zählen Namen von Personen und Königen als ein Platzhalter, steigt die Übereinstimmung der Pyramidentexte von 86,4 % auf 90,3 % (alle Paare). Im Totenbuch ändert sich nichts, dort ist der Name des Besitzers nicht als Personenname erfasst.
- **Vorhersage V2** (Totenbuch treuer als Literatur) gilt in 97 % der Ziehungen, V3 (Halbwertszeit über 1.000 Jahre) für den Schätzwert und beim Ziehen über Werke, nicht beim Ziehen über die elf Handschriften.

## Prüfung

- **Rückgewinnung:** Aus künstlichen Überlieferungen mit bekannter Verlustrate findet M2 die Rate wieder, leicht zu niedrig: wahr 0,0005 je Jahr, geschätzt 0,00046; wahr 0,002, geschätzt 0,00185. Ohne Verlust ergibt sich 0.
- **M1 mit vielen Nullen:** wahr 0,0005 / 0,005 / 0,012, geschätzt 0,0005 / 0,0058 / 0,0090. Schnelle Zerfälle sind also nur auf etwa ein Viertel genau.
- **Ausrichtung:** Das verwendete Verfahren findet 97,6 % der gleichen Stellen, die die bestmögliche Ausrichtung (längste gemeinsame Teilfolge) findet, geprüft an 150 Totenbuch-Paaren.
- **Überlappung:** Matrix und direkter Mengenschnitt stimmen an 300 Zufallspaaren exakt überein.

## Grenzen

- Das Totenbuch stützt sich auf 16 Handschriften in drei Zeitgruppen (18. Dynastie, 21. Dynastie, ptolemäisch); M2 auf 11. Beim Ziehen über Handschriften ist sein Zerfall nicht von null zu unterscheiden.
- M1 misst Wortlaut und Repertoire zusammen: Sinkt der Wert, kann der Text anders lauten oder ein anderer Text in Gebrauch sein. M2 misst nur den Wortlaut desselben Spruchs.
- Datiert ist die Handschrift, nicht die Abfassung. Eine späte Handschrift muss nicht von einer frühen des Korpus abstammen.
- Bei Grabinschriften ist das einzelne Grab nicht identifizierbar.
- Literatur in M2 beruht auf 46 Paaren; verschiedene Bearbeiter können dort die Übereinstimmung senken.

# Phasen-Test

Frage: Hat die Abweichung zwischen Abschriften desselben Spruchs eine Phasen- oder Taktstruktur? Aufruf: `python3 phasen_test.py zeit_schicht.jsonl.gz ergebnis.json`. Vier Lesarten standen vor dem ersten Lauf fest; die Randkontrolle bei der Lage und der Abschnitt „zwei Zustände“ kamen danach dazu.

| Lesart | Totenbuch (273 Spruchpaare) | Pyramidentexte (383 Spruchpaare) |
| --- | --- | --- |
| scharfes Viertel | nein: gleichzeitige Paare Median 21,5 %, Quartile 15,7–28,2 %, Spanne 4,3–69,3 % | nein: Median 10,9 %, Quartile 2,5–23,5 % |
| Takt, Periode 2 bis 64 Wörter | nein: p = 0,28; bei Periode 4 das 0,98-Fache der Ersatzfolgen | kein Takt; nur eine grobe Ungleichverteilung über das ganze Fenster (p = 0,005 bei Periode 64) |
| Blöcke | 56 % der abweichenden Stellen in Läufen ab 3 Wörtern, mittlerer Lauf 2,29 Wörter | 42 %, mittlerer Lauf 2,09 Wörter |
| Lage im Spruch | Anfang wie Kontrolle (13,4 % zu 13,9 %), Ende höher (17,3 % zu 13,7 %) | Anfang 6,1 % zu 5,3 %, Ende 8,3 % zu 6,1 % |
| feste Stellen | schwach: mehrere Handschriften weichen an 10,4 % der Stellen ab, bei verschobenen Handschriften 7,1 % (5,9–8,4) | 2,1 % statt 0,6 % (0,2–1,2) |

Kontrolle bei „Lage“: Der gemeinsame Bereich beginnt und endet per Definition mit vier gleichen Wörtern; verglichen wird deshalb mit Folgen, in denen dieselben Randblöcke stehen und die inneren Läufe vertauscht sind.

## Zwei Zustände statt Zerfall (Totenbuch)

| Paare | Zahl | gleich |
| --- | --- | --- |
| beide Handschriften vor 700 v. Chr., Abstand unter 50 Jahre | 59 | 74,7 % |
| beide vor 700 v. Chr., Abstand 300–600 Jahre | 49 | 74,1 % |
| eine vor, eine nach 700 v. Chr. | 164 | 67,1 % |

- Innerhalb der zehn frühen Handschriften (18. bis 21. Dynastie, bis 444 Jahre Abstand) ist kein Verlust messbar: Normtreue 99,89 % je Jahrhundert (97,81–101,39).
- Der ganze Verlust steckt im Vergleich mit der einen späten Handschrift, die Parallelen hat (pTurin 1791). pLeiden T 31 enthält nur Sprüche ohne Parallele.
- Stetiger Zerfall und zwei Zustände erklären die Unterschiede zwischen den Paaren gleich gut (13,1 % und 13,8 %). Der Sprung beträgt 7,4 Punkte, beim Ziehen über Handschriften −0,8 bis +28,6.
- Die Angabe „0,9 % Verlust je Jahrhundert“ aus M2 ist deshalb nur eine von zwei gleich guten Beschreibungen.

# Bündel auftrennen: Textgruppe, Zeit, Bearbeiter

Frage: Welchen Anteil an der Delta-Struktur haben Textgruppe, Zeit und Bearbeiter je für sich, und was bleibt unzuordenbar?

```
python3 buendel_test.py tokens.jsonl.gz zeit_schicht.jsonl.gz ergebnis.json merkmal_namen.json
python3 buendel_nachtrag.py tokens.jsonl.gz zeit_schicht.jsonl.gz nachtrag.json metadaten.jsonl
```

## Aufbau

- **Einheit:** Abschnitte zu 1.000 Wörtern, je Zelle aus Textgruppe und Bearbeiter in Datierungsreihenfolge gebildet. Wortebene 694 Abschnitte (12 Textgruppen, 17 Bearbeiter, 316 Handschriften-Cluster), Zeichenebene 209 Abschnitte (7 Textgruppen, 12 Bearbeiter, 109 Cluster).
- **Faktoren:** Textgruppe und Bearbeiter als Klassen, Zeit als glatte Kurve über das Datum des Abschnitts (natürlicher kubischer Spline, 5 Knoten).
- **Zerlegung:** auf der Delta-Matrix selbst (Gower-zentriert, Spur der Hutmatrix), Anteile aus dem korrigierten R² der sieben Modelle. Eine euklidische Gegenrechnung auf den z-Werten liefert dasselbe Muster.
- **Test:** eigener Anteil eines Faktors gegen 999 Vertauschungen seiner Werte zwischen Handschriften, innerhalb der Schichten der beiden anderen Faktoren.

## Anteile an der Delta-Struktur

| Anteil | Wortebene | Zeichenebene |
| --- | --- | --- |
| nur Textgruppe | 4,7 % | 5,1 % |
| nur Zeit | 2,0 % | 2,6 % |
| nur Bearbeiter | 3,5 % | 7,3 % |
| Textgruppe und Bearbeiter gemeinsam | 22,1 % | 14,3 % |
| alle drei gemeinsam | 11,0 % | 15,9 % |
| Textgruppe und Zeit, Zeit und Bearbeiter gemeinsam | 2,0 % | 7,8 % |
| nicht erklärt | 54,7 % | 47,0 % |

- **Vertauschungstest:** Alle eigenen Anteile liegen über der Vertauschung. Wortebene: Textgruppe 5,20 % gegen 1,76 %, Zeit 2,28 % gegen 0,66 %, Bearbeiter 4,42 % gegen 2,06 % (rohe Anteile, je p = 0,001). Zeichenebene: Textgruppe 5,60 % gegen 3,63 % (p = 0,010), Zeit 3,31 % gegen 2,18 %, Bearbeiter 9,01 % gegen 4,94 % (je p = 0,001).
- **Kontrolle:** Erfundene Bearbeiter, je Handschrift zufällig vergeben, kommen auf einen eigenen Anteil von 0,8 % (Wort) und 1,1 % (Zeichen). Die eigenen Anteile der Tabelle sind also um etwa einen Punkt zu hoch, weil Abschnitte derselben Handschrift zusammenhängen.
- **Schriftart als vierter Faktor (nachträglich):** Steht die Schriftart (hieratisch, hieroglyphisch, kursivhieroglyphisch) im Modell, sinkt der eigene Bearbeiteranteil von 3,5 % auf 2,7 % (Wort) und von 7,3 % auf 5,1 % (Zeichen); er bleibt über der Vertauschung (p = 0,001).

## Was die Faktoren tragen

- **Zeit, Wortebene:** die Kennzeichen des Neuägyptischen: =w, mtw=, nꜣy=, pꜣy=, nꜣ, pꜣ.
- **Textgruppe, Zeichenebene:** A1 (sitzender Mann) und Deutzeichen der Medizin: Aa2, N33, F51.
- **Bearbeiter, Zeichenebene:** T14, W22, G37, Z3, A24, A2, D40, D35, N26, Z2. Darunter Paare, die beim Umsetzen hieratischer Schrift austauschbar sind. Anteil der zweiten Schreibung je Zelle:

| Paar | hieroglyphische Denkmäler | hieratische Papyri |
| --- | --- | --- |
| D40 / A24 (Arm mit Stock / schlagender Mann) | Amarna 3 %, hist.-biogr. Spätzeit 3 %, Stelen des Mittleren Reichs 70 % | 50–93 % je Zelle |
| G43 / Z7 (w als Wachtelküken / als Schleife) | Grabinschriften 0 %, Stelen des Mittleren Reichs 0 %, Amarna 10 % | Literatur des Neuen Reichs 90–99 % je Bearbeiter |
| Z2 / Z3 (Pluralstriche waagrecht / senkrecht) | Amarna 5 % | Medizin: Papyrus Ebers 4 %, Papyri bei Brose 60 %, bei Dils 20 % |

- **Bearbeiter, Wortebene:** Wörter des jeweiligen Stoffs, etwa das verneinende m der Lehren und Formeln der Grabinschriften.

„Bearbeiter“ steht damit für ein Arbeitspaket: Schriftart, Untergattung und Handschriftenfamilie des Materials, das eine Person ediert hat. Persönliche Umschriftgewohnheiten lassen sich davon mit diesem Korpus nicht trennen.

## Bereinigter Abstand

Abgezogen wird je Merkmal die Abweichung einer Zelle vom Mittel der Bearbeiter derselben Textgruppe, geschätzt ohne die Handschriften des jeweiligen Zehntels.

| Prüfgröße | Wortebene | Zeichenebene |
| --- | --- | --- |
| Textgruppe erkannt, nur fremde Bearbeiter zugelassen | 76,2 % → 86,2 % (Änderung +5,1 bis +15,6) | 73,0 % → 87,4 % (+1,1 bis +30,6) |
| Bearbeiter erkannt bei gleicher Textgruppe und Epoche | 76,0 % → 69,3 % (Zufall 55,6 %) | 87,2 % → 65,0 % (Zufall 55,7 %) |
| Textgruppe erkannt, alle Kandidaten | 90,5 % → 93,9 % | 86,5 % → 86,5 % |

- Die Tabelle zeigt die Fassung mit Schrumpfung aus dem Nachtrag. Die Fassung des Protokolls trug Rauschen ein: In der Kontrolle wurden erfundene Bearbeiter ohne Effekt danach besser erkannt als vorher (Wortebene 53,7 % → 62,9 %). Mit Schrumpfung bleibt die Kontrolle beim Zufall (46,4 % → 46,2 %), und ein künstlicher Effekt wird entfernt (77,9 % → 54,2 %, Zufall 45,9 %).
- Angepasst werden nur Textgruppen mit mehreren Bearbeitern: 357 von 694 Abschnitten (Wort), 126 von 209 (Zeichen).

## Grenzen

- Totenbuch, Pyramidentexte und Briefe haben je einen Bearbeiter. Ihre Eigenart steckt im gemeinsamen Anteil von Textgruppe und Bearbeiter und lässt sich nicht zuordnen.
- Einige Zellen bestehen aus einer einzigen Handschrift (Papyrus Ebers bei Popko). Dort ist „Bearbeiter“ dasselbe wie „Handschrift“.
- Die Zerlegung ist additiv. Wechselwirkungen, etwa ein Sprachwandel, der nur eine Textgruppe erfasst, landen im Rest.

# Anker-Test: Namen und Zahlen

Stand: 13.11.2026. Frage: Lassen sich Zeichenwerte allein aus Ankern bestimmen, die ohne Hieroglyphenlesung bekannt sind, und passen die so bestimmten Werte zu komplexeren Verbindungen, also zu gewöhnlichen Wörtern einer verstandenen Sprache? Zwei Ankerfamilien: Namen (geben den Laut) und Zahlen (geben Bedeutung und Struktur).

```
python3 anker_test.py tokens.jsonl.gz anker_tabelle.tsv signs_description.xml egyptian_etymologies.tab ergebnis.json zeichenwerte.tsv
python3 anker_nachtrag.py tokens.jsonl.gz anker_tabelle.tsv egyptian_etymologies.tab nachtrag.json
python3 anker_gegenprobe.py synth
python3 anker_gegenprobe.py zaehlen tokens.jsonl.gz anker_tabelle.tsv signs_description.xml
python3 zahlen_anker.py <aes-json-ordner> ergebnis.json
```

`signs_description.xml` ist die Zeichenliste aus dem JSesh-Repository (`jsesh/src/main/resources/jsesh/glyphs/resources/`).

## Welche Anker das Korpus hergibt

- **Namen mit Zeichenfolge:** 2.596 verschiedene, davon 768 Götter-, 374 Orts-, 112 Königs- und 965 Personennamen.
- **Mit fremder Überlieferung** (`anker_tabelle.tsv`, von Hand zusammengestellt): 131 Namensgruppen mit 245 fremden Formen. Griechisch 86, Keilschrift (Amarna, Hattuša, Assyrien) 56, Koptisch 48, hebräische Bibel 24, heutige arabische Ortsnamen 24, Aramäisch/Phönizisch 7. Dazu 12 Königsnamen der Königslisten (Manetho, Herodot) als getrennter Prüfsatz, der nicht ins Lernen eingeht.
- **Was fehlt:** Die klassischen Anker der Entzifferung (Ptolemaios, Kleopatra, Berenike) stehen nicht im zeichencodierten Teil des Korpus; Alexander hat 2 Belege. Chinesisch liefert keinen Anker, weil es keinen gemeinsamen Namen und keinen gemeinsamen Text gibt.
- **Aufnahmeregel:** Die fremde Form gibt denselben Namen in derselben Zusammensetzung wieder. Wie gut ihre Konsonanten zur Zeichenfolge passen, war kein Kriterium.
- **Vergleichsebene:** 9 Konsonantenklassen der fremden Form: P (p b f), M, N, R (r l), T (t d), S (s z sch), C (emphatische Laute und Affrikaten), K (k g q ch), H. Vokale, w, y, Aleph und Ajin entfallen.

## Aufbau

- **Modell:** Jedes Zeichen erzeugt 0 bis 3 Konsonantenklassen; Zeichen und Konsonanten stehen in gleicher Reihenfolge. Gelernt wird mit dem EM-Verfahren über alle möglichen Aufteilungen (Vorwärts-Rückwärts-Rechnung). Das Modell bekommt nur Paare aus Zeichenfolge und fremder Konsonantenfolge, keine ägyptologische Lesung.
- **Glättung:** Wert je Zeichen = (erwartete Zählung + 2 × Grundverteilung) / (Summe + 2). Seltene Zeichen fallen damit auf die Grundverteilung zurück.
- **Voranstellung:** Die ersten bis zu vier Zeichen dürfen als Block ans Ende rücken (Gottesname im Königsnamen). Das Modell nutzt diese Freiheit praktisch nicht (Anteil 2 %); ohne sie ist das Ergebnis gleich.
- **Protokoll:** steht oben in `anker_test.py` (sha256 21587b85a6db8c48), festgelegt vor dem ersten Lauf auf den Ankern. Vorher lief nur die Rückgewinnung an künstlichen Daten.

## Ergebnis

| Prüfung | mit echten Ankern | Vergleich |
| --- | --- | --- |
| P1 zurückgehaltene Namen: richtige fremde Form unter 138 Kandidaten auf Rang 1 | 14,4 % (9,4–20,1) | Anker vertauscht: 0 bis 1,7 %; Zufall 0,7 % |
| P1 mittlerer Rangplatz der richtigen Form | 23,1 % (18,3–28,1) | Anker vertauscht: 43,5 bis 45,0 % |
| P2 Königslisten, 16 Abfragen | Rang 1 bei 2, Rang 2 bei 4; mittlerer Rangplatz 31,8 % | Zufall 0,7 % und 50 % |
| P3a starke Einkonsonantenzeichen, 16 prüfbar | 13 mit passender Klasse; Zählverfahren 16 von 16 | – |
| P3b Zeichen mit gelerntem Lautwert, 24 | 20 genau wie die Standardliste, 3 teilweise, 1 falsch | Standardwerte vertauscht: im Mittel 3,7, höchstens 10; p = 0,0001 |
| P4 gewöhnliche Wörter: koptischer Nachfolger unter 462 Kandidaten auf Rang 1 | 25,0 % | Anker vertauscht (20 Läufe): 2,2 % (1,0–4,2) |
| P4 unter den ersten 10 | 55,3 % | 21,4 % (18,8–23,7) |
| P4 mittlerer Rangplatz | 6,7 % | 18,2 % (17,4–18,8) |
| P5 Obergrenze: dasselbe Modell am Koptischen selbst gelernt | Rang 1 51,5 %; erste 10: 83,6 %; Rangplatz 2,4 % | – |

Alle vier vorab festgelegten Kriterien sind erfüllt. Zwei Einschränkungen dazu: Bei K1 lag die Grenze für den mittleren Rangplatz bei 25 %, das Intervall reicht bis 28,1 %. Bei K4 rechnete das Protokoll den Zufall mit 50 %; richtig ist der Wert bei vertauschten Ankern (18,2 %). Damit gehen die Ankerwerte rund 72 % des Wegs zur Obergrenze, nicht 91 %.

### P1 nach Überlieferung und Länge

| Fremde Form bezeugt in | Abfragen | Rang 1 | mittlerer Rangplatz |
| --- | --- | --- | --- |
| Griechisch | 86 | 22,1 % | 13,3 % |
| Koptisch | 48 | 12,5 % | 17,8 % |
| Aramäisch/Phönizisch | 7 | 57,1 % | 9,3 % |
| Arabisch | 24 | 4,2 % | 26,9 % |
| Hebräisch | 24 | 16,7 % | 28,9 % |
| Keilschrift | 56 | 12,5 % | 33,2 % |

- **Länge:** 1 Konsonant 55,6 % auf Rang 1, 2 Konsonanten 10,5 %, 3 Konsonanten 12,5 %, ab 4 Konsonanten 6,1 % bei einem mittleren Rangplatz von 44,3 %. Lange Formen erkennt das Verfahren nicht.
- **Richtig gelesen, ohne den Namen gesehen zu haben:** Psammetich (PSMTK), Astarte (STRT), Reschef (RSP), Nikkal (NKR), Sokar (SKR), Petamun (PTMN), Sochotes (SKT), Mendes (MNT), Amenhotep (MNT), Amun, Sobek, Bes, Baal, Kusch und weitere; 25 von 131 Namensgruppen mit einer Form auf Rang 1, 52 unter den ersten 5.
- **Am schlechtesten:** die keilschriftlich überlieferten Thronnamen (Wašmuaria Šatepnaria auf Rang 138 von 138, Riamašeša 137, Nibmuaria 108). Sie sind mit Wortzeichen geschrieben, die in zu wenigen Ankern vorkommen, und der Gottesname steht voran.

### Gelernte Zeichenwerte (P3)

Die vollständige Liste für alle 192 Zeichen steht in `ausgabe/anker_zeichenwerte.tsv`.

| Zeichen | gelernt | Standard | Urteil |
| --- | --- | --- | --- |
| D58, Q3, I9 | P | b, p, f | passt |
| G17 | M | m | passt |
| D21 | R | r | passt |
| V28 | H | ḥ | passt |
| S29, O34, N37 | S | s, z, š | passt |
| V31 | K | k | passt |
| V13, D46 | T | ṯ, d | passt |
| I10 | C | ḏ | passt |
| N35, X1, Aa1 | kein Laut | n, t, ḫ | passt nicht |
| M17, G1, D36, G43, Z7, Z4 | kein Laut | j, ꜣ, ꜥ, w, w, y | wie erwartet, diese Laute fehlen in den fremden Formen |
| Y5 | MN | mn | genau |
| L1 | KPR | ḫpr | genau |
| U15 | TM | tm | genau |
| W24, U33, Q1, D37 | N, T, S, T | nw, tj, ꜣs/st, dj | genau |
| C10, G5 | M, R | mꜣꜥt, ḥr | teilweise |
| R4 | T | ḥtp | falsch |

- **N35 und X1** tragen in der einfachen Zählung sehr wohl ihren Laut (N35 mit Klasse N in 35 von 40 Gruppen gegen 19 von 91 ohne das Zeichen, p = 5·10⁻¹³; X1 mit T in 38 von 56 gegen 19 von 75). Das Lernverfahren legt den Laut auf das Nachbarzeichen, weil beide meist als Lautergänzung (Y5 + N35 für mn) oder als nicht mehr gesprochene Femininendung stehen. Die Beschreibungen „Y5 = mn, N35 stumm“ und „Y5 = m, N35 = n“ sind aus den Daten nicht unterscheidbar.
- **Aa1** kommt in 4 Gruppen vor, und die fremden Formen geben ḫ uneinheitlich wieder (griechisch ch, koptisch sch).
- **A40** (sitzender Gott, ein Deutzeichen) erhielt den Wert R und zählt nach der Regel als „teilweise“, weil die Standardliste dafür nṯr nennt. Inhaltlich ist das ein Fehler: Das Zeichen steht hinter Namen, die auf r enden.

### Gewöhnliche Wörter (P4)

Grundlage: 1.159 ägyptische Lemmata, die im Korpus mit Zeichenfolge belegt sind und laut der Tabelle des Coptic Dictionary Online einen koptischen Nachfolger haben (1.194 Paare). 18 weitere Lemmata der Tabelle sind selbst Ankernamen (Amun, Osiris, Horus und andere) und bleiben draußen. Im ersten Lauf waren sie versehentlich mitgeprüft; mit ihnen lauteten die Hauptzahlen 25,4 % und 55,8 %. Gefragt ist, ob die aus Namen gelernten Werte den koptischen Nachfolger unter allen 462 verschiedenen koptischen Konsonantenfolgen nach vorn bringen.

| Anker | Namensgruppen | Rang 1 | unter den ersten 10 | mittlerer Rangplatz |
| --- | --- | --- | --- | --- |
| alle | 131 | 25,0 % | 55,3 % | 6,7 % |
| ohne koptische Formen | – | 22,0 % | 51,8 % | 8,0 % |
| nur Keilschrift, Hebräisch, Aramäisch/Phönizisch | – | 14,4 % | 41,8 % | 10,4 % |
| nur Griechisch | 80 | 11,8 % | 40,2 % | 14,7 % |
| nur Hebräisch, Aramäisch/Phönizisch | 30 | 10,0 % | 35,5 % | 12,0 % |
| nur Keilschrift | 52 | 9,5 % | 32,1 % | 18,3 % |
| nur Koptisch | 45 | 8,1 % | 32,7 % | 13,3 % |
| nur heutiges Arabisch | 23 | 5,7 % | 29,2 % | 17,0 % |
| vertauscht (20 Läufe) | 131 | 2,2 % (1,0–4,2) | 21,4 % (18,8–23,7) | 18,2 % (17,4–18,8) |

- **Anker mit Zurücklegen gezogen (20-mal):** Rang 1 im Mittel 19,0 % (14,7–26,8), unter den ersten 10: 48,8 % (39,9–54,7). Das Ergebnis hängt nicht an einzelnen Zeilen der Tabelle.
- **Wörter nur aus gut belegten Zeichen** (jedes Zeichen in mindestens 3 Namensgruppen, 196 Paare): Rang 1 bei 33,7 %, Rangplatz 5,0 % gegen 15,8 % für einen falschen Partner gleicher Länge. Übrige Wörter: 23,2 % und 7,0 % gegen 20,2 %.
- **Ab 4 koptischen Konsonanten** (40 Paare) liegt der Rangplatz bei 39,0 %: Auch hier scheitert das Verfahren an langen Formen.
- **Zahlwörter:** stehen im Korpus fast immer als Zahlzeichen. Ausgeschrieben gibt es je einen Beleg für 2, 3 und 4. „Vier“ (M17-I9-D46 und vier Striche) führt auf koptisch ϥⲧⲟⲟⲩ, Rangplatz 0,2 % statt 4,2 % ohne Zeichenwerte; „zwei“ und „drei“ enthalten Zeichen, die in keinem Anker vorkommen.

## Zahlen als Anker

Zahlen brauchen keine Sprache. Aus griechischer Überlieferung (Herodot II 4) und aus dem bis heute gebrauchten koptischen Kalender ist bekannt: 12 Monate zu 30 Tagen und 5 Zusatztage. Die ägyptische Datumsformel nennt Jahr, Monat innerhalb einer Jahreszeit und Tag.

| Stelle der Formel | Belege | Werte |
| --- | --- | --- |
| Jahr | 218 | 1 bis 56; 36 % bis 4, 91 % bis 30 |
| Monat (Monat + Zahl + Jahreszeit) | 332 | nur 1, 2, 3, 4 (67 / 77 / 99 / 89) |
| Tag | 344 | 1 bis 30, kein Wert darüber |
| Jahreszeit | 332 | genau drei Wörter (98 / 103 / 131) |
| Zusatztage | 12 | immer 5 |

- **Monatszahlen über 4** gibt es dreimal (5, 7, 9). Alle drei stehen außerhalb der Datumsformel und geben eine Dauer an („ein Jahr und fünf Monate“).
- **Gegenrechnung:** Wären Monatszahlen verteilt wie die Jahreszahlen derselben Formel, lägen alle 332 mit einer Wahrscheinlichkeit von 10⁻¹⁴⁶ bei höchstens 4; für die Tage 10⁻¹⁴. Gegen die übrigen 14.625 Zahlen des Korpus: 10⁻²⁵ und 10⁻¹⁰.
- **Zeichenebene** (nur gezeichnete Striche und Bügel gezählt, keine Lesung): Monat 97 Belege mit 1 bis 4 Strichen und nie einem Bügel; Tag 74 Belege mit höchstens 2 Bügeln und 9 Strichen; Jahr 73 Belege mit bis zu 4 Bügeln. Die Strichzahl stimmt in 239 von 244 Fällen mit der Zahl der Bearbeiter überein.
- **Rechenproben:** „Soll = Ist + Fehlbestand“ stimmt in 2 von 2 Fällen (15 = 13 + 2; 225 = 200 + 25). „Summe der Posten = Summenzeile“ stimmt nach der mechanischen Regel in 7 von 12 Fällen (3+1 = 4; 3+2 = 5; 5+5 = 10; 5+11 = 16; 7+4+4+6 = 21; 200+300 = 500; 87+64+27 = 178); bei vertauschten Summen im Mittel 0,84. Die 5 übrigen Fälle mischen Stückzahl und Wert oder setzen eine Liste aus dem Satz davor fort. Einer davon geht auf, wenn 1 Deben = 12 Schenati gilt: 16 Schenati + 1 Deben = 2 Deben 4 Schenati.
- **Tagesbedarf 100, Monatsbedarf 3.000** im selben Satz (ein Beleg): Faktor 30.
- **Stadt der Acht:** Der Ortsname Chemenu ist in 11 von 13 Belegen mit acht Zählstrichen geschrieben. Koptisch heißt die Stadt Schmun und „acht“ ϣⲙⲟⲩⲛ, arabisch heißt der Ort bis heute al-Aschmunein, assyrisch Ḫimuni. Hier treffen Zahl, Name und heutige Sprache an einer Zeichenfolge zusammen.

## Prüfung

- **Rückgewinnung an künstlicher Schrift** (20 Einkonsonantenzeichen, 15 Zwei-, 5 Dreikonsonantenzeichen, 15 stumme Zeichen, Lautergänzungen, vorangestellte Blöcke): Bei 150 Namen und 10 % Fehlern in der fremden Form findet das Verfahren 16 bis 20 der 20 Einkonsonantenwerte, 9 bis 13 der 15 Zweikonsonantenwerte und alle stummen Zeichen; zurückgehaltene Namen stehen zu 43 bis 57 % auf Rang 1. Bei 80 Namen 18 von 20 und 33 %. Bei 25 % Fehlern bricht es ein: 13 von 20, kein Mehrkonsonantenzeichen, 0 % auf Rang 1.
- **Zweiter Weg ohne das Lernverfahren:** Für jedes Zeichen wird nur gezählt, in wie vielen Namensgruppen Zeichen und Klasse gemeinsam vorkommen (Vierfeldertafel, exakter Test). Alle 16 prüfbaren starken Einkonsonantenzeichen binden am stärksten an die passende Klasse.
- **Vertauschte Anker** laufen durch denselben Code und landen beim Zufall.
- **Stichprobe der Ankertabelle:** Für 12 Ankernamen steht die koptische Form auch in der Tabelle des Coptic Dictionary Online. Alle 12 Konsonantenfolgen stimmen mit den von Hand eingetragenen überein.

## Grenzen

- Die Ankertabelle stammt aus Handbuchwissen, nicht aus einer Datenbank. Einzelne Formen wurden online nachgeschlagen (Tarqû, Mempi, Niʾ, Saya, Binṭiṭi, Ṣaʾnu, Wašmuaria Šatepnaria, Mayati); unsichere Gleichsetzungen blieben draußen. Die Datei lässt sich ändern und neu rechnen.
- Welche Zeichengruppe welcher Name ist, kommt aus der Auszeichnung der Bearbeiter. Blind müsste man die Namen erst finden, historisch über Kartuschen und zweisprachige Texte.
- Die Paare ägyptisch–koptisch stammen aus der ägyptologischen Etymologie. P4 zeigt deshalb, dass sich Namen, Zeichenwerte und Koptisch gegenseitig stützen; ein von der Ägyptologie unabhängiger Beweis der Wortbedeutungen ist es nicht.
- Verglichen werden Konsonantenklassen. b und p oder t und d unterscheidet der Test nicht.
- Lange Formen, Wortzeichen in wenigen Ankern und vorangestellte Gottesnamen bleiben ungelesen.
- Zahlenwerte in Z1 und Z3 stammen aus der Umschrift der Bearbeiter; nur die Strichzählung nutzt allein die Zeichen. Die Rechenproben beruhen auf wenigen Sätzen.

# Königsnamen als Namen von Zyklen?

Stand: 13.11.2026. Aufruf: `python3 zyklen_test.py <aes-json-ordner> ergebnis.json`. Erkundend: Die Regeln standen erst nach einer Sichtung der Jahresangaben fest.

Drei Lesarten: Der Name bezeichnet (1) den Zeitraum, in dem unter ihm Jahre gezählt werden, (2) eine wiederkehrende Periode fester Länge, (3) die Amtszeit eines Menschen. Lesart 1 gilt per Bauart der Datumsformel. Lesart 2 sagt gleiche Höchstzahlen, gleichmäßig verteilte Jahreszahlen und wiederkehrende Namen vorher; Lesart 3 unregelmäßige Längen unter einem Menschenleben, überwiegend kleine Jahreszahlen und eine Zählung, die weiterläuft, wenn der Name wechselt.

| Befund | Zahl |
| --- | --- |
| Königsnamen im Korpus | 257 Lemmata, 9.339 Belege; 64 Thronnamen, 85 Horus-, Nebti- und Goldnamen, 108 Geburtsnamen oder ohne Angabe |
| Thronnamen mit Re im Namen | 62 von 64 |
| Name „Wiederholung der Geburten“ (Wḥm-msw.t) | Amenemhet I. (5 Belege), Sethos I. (8 Belege) |
| Jahresangaben, je Text und Jahr einmal | 197; Median 8; bis Jahr 10: 63 %; über 30: 10 %; höchste Zahl 56 |
| bei gleichmäßiger Verteilung über 1 bis 56 | 18 % bis Jahr 10 |
| mit Thronnamen verknüpft | 60 Angaben, 19 Thronnamen |
| höchstes Jahr je Thronname | Ramses II. 56 (11 Angaben), Sesostris I. 43 (11), Amenophis III. 33 (2), Amenemhet II. 13 (6), Sethos I. 11 (7), Echnaton 8 (3), Sesostris III. 8 (3), Sesostris II. 6 (3) |
| fester Zyklus von 56 Jahren, Angaben gleichmäßig verteilt | Wahrscheinlichkeit für so niedrige Angaben bei sechs Namen zusammen 10⁻¹⁸; einzeln Amenemhet II. 0,00016, Sethos I. 0,00001 |
| Verwandtschaftstitel am König | 920 Belege: Königssohn 273, Königstochter 250, Königsgemahlin 356, Königsmutter 37, Geschwister 4 |

- **Zählung über einen Namenswechsel hinweg:** Unter dem Thronnamen Nfr-ḫpr.w-Rꜥw-wꜥ-n-Rꜥw stehen Jahr 3 und Jahr 4 mit dem Geburtsnamen Amenhotep, Jahr 8 mit Echnaton. Die Zählung hängt an der Person, nicht am Namen.
- **Zwei Zählungen nebeneinander:** „Jahr 43 unter der Majestät des Horus Anch-mesut, König Cheper-ka-Re … entsprechend Jahr 25 im Gazellengau des Fürsten Ameni“ (sawlit). Auch ein Gaufürst zählt seine Amtsjahre.
- **Was wiederkehrt:** Der Geburtsname Sesostris steht bei drei verschiedenen Thronnamen, Amenemhet bei zwei. Von 22 Thronnamen mit belegtem Geburtsnamen gehören 20 zu genau einem; die beiden übrigen sind eine Schreibvariante (Sethos I.) und eine Umbenennung (Echnaton).
- **Erklärter Neubeginn:** Sethos I. eröffnet sein Jahr 1 mit „Beginn der Neheh-Ewigkeit, Anfang der Djet-Ewigkeit, Millionen von Sedfesten“. „Erstes Sedfest im Jahr 30“ kommt im Korpus nicht vor.
- **Mehrere Könige gleichzeitig:** Die Pije-Stele (bbawhistbiospzt) zählt König Nimlot, König Juput und weitere Fürsten nebeneinander auf, mit Söhnen und Heeren.

Grenzen: Nur 73 Jahresangaben stehen bei einem Königsnamen, 60 bei einem Thronnamen. Die Rechnung zum festen Zyklus setzt gleichmäßig verteilte Angaben voraus. Welche Zeichengruppe ein Königsname ist und welcher Art, kommt aus der Auszeichnung der Bearbeiter. Ein Zyklus mit unregelmäßiger Länge im Maß eines Menschenlebens ist durch Zählen allein nicht von einer Regierung zu unterscheiden.

# Bestimmte Zyklen gegen die Jahreszählung

Stand: 13.11.2026. Aufruf: `python3 zyklen_perioden.py <aes-json-ordner> metadaten.jsonl ergebnis.json`. Länge, Startmarke und Vorhersage je Zyklus stehen oben im Skript. Erkundend: Welche Belege das Korpus enthält, war aus einer Sichtung bekannt. Zahlen von außen stehen als Konstanten mit Quelle im Skript.

Zwei Arten von Vorhersage: (a) Der Königsname ist der Name des Zyklus, dann endet die Zählung spätestens bei der Zykluslänge. (b) Der Zyklus läuft als eigene Uhr neben der Zählung, dann liegen zwei seiner Marken so weit auseinander, wie die Länge es verlangt.

Grundlage für (a): 196 Jahresangaben, je Werk und Datum einmal gezählt. Mittel 11,5, Median 7, höchste Zahl 56. Je Fünfjahresklasse: 85 / 39 / 18 / 14 / 13 / 8 / 9 / 5 / 3 / 1 / 1 (Jahre 1–5 bis 51–56). Ein Zerfall mit konstanter Endrate (Halbwertszeit 7,6 Jahre) beschreibt die Verteilung um 123 log-Likelihood-Einheiten besser als eine Gleichverteilung über 1 bis 56.

| Zyklus | Länge und Startmarke | (a) als Name der Zählung | (b) als eigene Uhr |
| --- | --- | --- | --- |
| Sothis | 1.460 Jahre; der Aufgang wandert 1 Tag je 4 Jahre; Start: Aufgang am Neujahrstag | nein: höchste Zahl 56. Auch das Vierjahr scheidet aus: 63 % der Angaben liegen über 4 | ja: zwei datierte Aufgänge im Korpus, 83 Tage auseinander, also 332 Jahre (329–335), mit dem Ortsunterschied Illahun–Theben 346. Radiokarbon für dieselbe Spanne: 340 ± 14 |
| Mond | 29,53 Tage; 309 Monate = 25 Kalenderjahre; Start: Neumond | nein: 27 Angaben (14 %) über 25, bei mindestens acht Königen | im Korpus keine datierte Mondbeobachtung. Von außen (Thutmosis III.): zwei Neumonde 649 Tage auseinander = 21,98 Monate |
| Sedfest | 30 Jahre, danach alle 3; Start: Amtsantritt | nein: 19 Angaben (10 %) über 30, bei mindestens sechs Königen | das einzige datierte „erste Mal des Sedfestes“ (Pepi I., zwei Felsinschriften) steht im „Jahr nach dem 18. Mal“, nicht im Jahr 30 |
| Viehzählung | 2 Jahre; Start: erste Zählung | ist im Alten Reich die Zähleinheit selbst („Jahr des n-ten Mals“) | nicht streng zweijährig: 12 von 61 Angaben sind „Jahr nach dem n-ten Mal“ (20 %), erwartet wären 50 %; p = 10⁻⁶ |

## Sothis

- **Belege:** Brief pBerlin 10012 (Illahun, Edition 1872–1854 v. Chr.): „Der Aufgang der Sothis wird im 4. Monat der Peret-Zeit, Tag 16, stattfinden“ (Tag 226 des Jahres). Papyrus Ebers, Kalender der Rückseite: „Jahr 9 unter der Majestät des Königs Djeserkare“ und „3. Monat der Schemu-Zeit, Tag 9: Aufgang der Sothis“ (Tag 309).
- **Abstand:** 83 Tage Verschiebung ergeben 332 Jahre bei gleichem Beobachtungsort. Der Aufgang ist je Breitengrad nach Süden rund einen Tag früher zu sehen; zwischen Illahun (29,2° N) und Theben (25,7° N) sind das etwa 3,5 Tage, also 346 Jahre.
- **Unabhängige Uhr:** Radiokarbon (Bronk Ramsey u. a. 2010, Tabelle 1, 68 %): Amtsantritt Sesostris III. 1884–1860, Amenophis I. 1541–1527 v. Chr. Von Jahr 7 des einen bis Jahr 9 des anderen sind das 340 ± 14 Jahre. Mittleres und Neues Reich sind dort getrennt modelliert.
- **Startmarke:** Vom Ebers-Datum bis zum Aufgang am Neujahrstag fehlen 57 Tage, also 228 Jahre (225–231) nach Jahr 9, das sind 236 Jahre nach dem Amtsantritt Amenophis' I. Mit Radiokarbon liegt die Marke bei 1305–1291 v. Chr.; Ramses I. tritt dort 1308–1297 an, Ramses II. 1292–1281, Sethos I. regiert dazwischen. Mit der Chronologie der Edition (Jahr 9 = 1517 v. Chr., Beobachtung in Theben) liegt sie bei 1289 v. Chr.; Sethos I. regiert dort 1290–1280. Bei Beobachtung in Memphis (1537 v. Chr.) läge sie bei 1309 v. Chr., unter Haremhab.
- **Im Korpus dazu:** Die Eröffnung „Beginn der Ewigkeit“ steht bei genau zwei Jahresangaben, Jahr 1 und Jahr 4, beide von Sethos I. Sein Nebti-Name ist „Wiederholung der Geburten“.
- **Einordnung:** Den Beginn dieser Sothis-Periode nennt die spätantike Überlieferung „Ära des Menophres“ (1322/1321 v. Chr., gerechnet für den Norden). Dass damit Sethos I. gemeint sei, ist eine alte und umstrittene These.

## Mond

- **Im Korpus:** keine datierte Mondbeobachtung unter einem Königsnamen. Der Mond gliedert den Kult: 83 Belege für Mondtage in Fest- und Opferlisten (Halbmonatsfest 45, 15. Mondtag 14, zweiter Mondtag 9, Monatsanfang 8, Neumondtag 7).
- **Von außen:** Thutmosis III., Neumond im Jahr 23, I Schemu 21, und im Jahr 24, II Peret 30; Amtsantritt I Schemu 4. Wechselt die Jahreszahl am Antrittstag, liegen die Daten 649 Tage auseinander, das sind 21,98 Mondmonate. Wechselte sie am Neujahrstag, wären es 284 Tage und 9,62 Monate. Die Zählung beginnt demnach am Antrittstag der Person.

## Sedfest und Viehzählung

- **Über 30 hinaus** zählen Sesostris I. (33, 34, 39, 43, 44), Amenemhet III. (36 bis 38), Amenophis III. (33), Ramses II. (33, 34, 56), Mentuhotep II. (46) und Pepi II. (31). Über 25 kommen Amenemhet I. (30) und Ramses III. (26) dazu.
- **Pepi I.:** „Jahr nach dem 18. Mal“ wäre bei jährlicher Zählung Jahr 19, bei zweijähriger Jahr 36 oder 37. Jahr 30 passt zu keiner der beiden. Mindestens einer der beiden Zyklen lief nicht regelmäßig.
- **Viehzählung:** 49 Angaben „Jahr des n-ten Mals“, 12 „Jahr nach dem n-ten Mal“ in Texten vor 2100 v. Chr.; höchste Zahl 31.

## Grenzen

- Die Sothis-Rechnung setzt voraus, dass beide Notizen echte Beobachtungen sind und dass ein Tag Verschiebung vier Jahren entspricht. Ob die Ebers-Notiz eine Beobachtung ist und wo beobachtet wurde, ist umstritten; der Ort verschiebt die Marke um rund 20 Jahre.
- Das Jahr 7 Sesostris' III. für den Illahun-Brief steht nicht im Brief selbst, sondern stammt aus der Literatur.
- Die absoluten Jahreszahlen der Edition beruhen selbst auf diesen Sothis-Daten. Unabhängig davon sind Radiokarbon und die Monddaten.
- Der Mondtest und die Radiokarbonwerte kommen von außerhalb des Korpus.
- Welcher König hinter einer Jahreszahl steht, ist bei 27 hohen Angaben von Hand aus Formel und Editionsdatierung bestimmt.

# Könige als Sterne oder Sternbilder?

Stand: 13.11.2026. Aufruf: `python3 sterne_test.py <aes-json-ordner> ergebnis.json`. Erkundend.

| Frage | Befund |
| --- | --- |
| Stern- und Sternbildnamen im Korpus | 40 Lemmata, 633 Belege; 422 in den Pyramidentexten, 131 im Totenbuch. Häufigste: Nicht-Untergehender (Zirkumpolarstern) 158, Stern 152, Sothis und Sirius 79, Orion 59, Morgenstern 44 |
| Königsname und Sternwort im selben Satz, Pyramidentexte | 123 Sätze, bei Unabhängigkeit 107 erwartet (Verhältnis 1,15; p = 0,036) |
| dasselbe in Inschriften lebender Könige (Ramessiden, Amarna, Fels- und Grabinschriften, Spätzeit, Briefe) | 0 von 999 Sätzen mit Königsname; Sternwörter stehen dort insgesamt nur in 10 Sätzen |
| Sternname als Bestandteil eines Königsnamens | bei 257 Königsnamen und 34 Sternnamen nur ḫpš; das Wort heißt „Schenkel, starker Arm“ und bezeichnet auch den Großen Wagen |
| Dekanlisten (die ägyptische Sternfolge) | keine; 5 einzelne Dekannamen mit zusammen 12 Belegen |

- **Was die Texte sagen:** Der tote König wird zum Stern. Beispiele aus den Pyramidentexten: „Du hast dir diesen Pepi als Nicht-Untergehenden platziert“; „Die Schwester des Pepi ist Sothis, der Abkömmling dieses Pepi ist der Morgenstern“; „wie er zum Himmel emporsteigt unter den Sternen“.
- **Grenzen:** Die Sternfolge selbst (36 Dekane in fester Reihenfolge) lässt sich am Korpus nicht prüfen. Das Zusammentreffen im Satz ist ein grobes Maß; in den Pyramidentexten steht der Königsname in 30 % aller Sätze.

# Was umfasst eine Zählnummer? (56 Tage, 56 Wochen, 56 Mondmonate)

Stand: 13.11.2026. Aufruf: `python3 einheit_test.py <aes-json-ordner> metadaten.jsonl ergebnis.json`. Erkundend.

| Lesart | Vorhersage | Befund |
| --- | --- | --- |
| Einheit = 56 Tage (27 + 29) | Daten mit derselben Zählnummer liegen höchstens 56 Tage auseinander | 10 Fälle mit mehreren Daten je König und Zählnummer; in 5 liegt die Spanne über 56 Tagen, größte 329 (Sethos I., Jahr 1) |
| Einheit = 56 Wochen (392 Tage) | zwei Neumonde im Abstand 2 L − 81 = 703 Tage | 23,81 Mondmonate, 5,7 Tage neben einem Neumond |
| Einheit = 56 Mondmonate | Abstand 3.226 Tage | 109,26 Mondmonate, 7,6 Tage daneben |
| Einheit = 365 Tage | Abstand 649 Tage | 21,98 Mondmonate, 0,7 Tage daneben |
| 56 als Länge eines Zyklus | jede Zählung läuft bis 56 | 1 von 196 Angaben nennt 56; andere Zählungen enden im Korpus bei 46, 44, 38, 33, 31 |

- Die Mondprobe nutzt die beiden Neumonde Thutmosis' III. (Jahr 23, I Schemu 21; Jahr 24, II Peret 30; Jahreswechsel am Antrittstag I Schemu 4) und kommt von außerhalb des Korpus.
- Siderischer und synodischer Monat ergeben zusammen 56,85 Tage. Ihre Schwebung, 1/(1/27,32 − 1/29,53), ist 365,26 Tage, also das Jahr.
- 56 synodische Monate sind 4,53 Jahre, 56 Wochen 392 Tage, drei Umläufe der Mondknoten 55,83 Jahre.
- Die Datumsformel selbst zählt unter jeder Nummer 3 Jahreszeiten zu 4 Monaten zu 30 Tagen und 5 Zusatztage (Abschnitt „Zahlen als Anker“).

# Quelle der Daten

AES – Ancient Egyptian Sentences, Simon D. Schweitzer, https://github.com/simondschweitzer/aes, und AED-TEI, https://github.com/simondschweitzer/aed-tei, beide Lizenz CC BY-SA 4.0. `tokens.jsonl.gz`, `metadaten.jsonl` und `zeit_schicht.jsonl.gz` sind daraus abgeleitet und stehen unter derselben Lizenz.

Coptic Dictionary Online mit dem Comprehensive Coptic Lexicon (BBAW, DDGLC, KELLIA), https://github.com/KELLIA/dictionary, Lexikondaten unter CC BY-SA 4.0; `egyptian_etymologies.tab` ist die Datei `data/egyptian_etymologies.tab` von dort (Stand 26.08.2026). Die Zeichenliste mit Lautwerten stammt aus JSesh, https://github.com/rosmord/jsesh, und liegt dem Paket nicht bei.
