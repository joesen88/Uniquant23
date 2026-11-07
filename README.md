# Zyklus23 · Demonstrator 1.0.0

Lokaler interaktiver Viewer der Zyklus23-Zählung und eines 3D-Sonnensystems.

## Start

1. ZIP vollständig entpacken.
2. Den entpackten Ordner öffnen.
3. `START.py` in PyCharm ausführen oder im Terminal starten:

```bash
python3 START.py
```

Der Standardbrowser öffnet sich mit dem Viewer. Benötigt werden Python **3.10 oder neuer** und ein aktueller Browser. **Keine pip-Installation und keine Internetverbindung nötig.** Auf Ubuntu ist auch `bash START.sh` möglich. Im Terminal steht die lokale Adresse; falls sich kein Browser öffnet, diese Adresse manuell öffnen. Zum Beenden im Terminal `Strg+C` drücken.

Optional:

```bash
python3 START.py --no-browser
python3 START.py --port 8765
python3 START.py --phase 1
```

`--phase 1` führt die mitgelieferten Tests aus und schreibt `nachweise/lokaler_test.json`. Der normale Viewerstart verlangt keinen vorherigen Testlauf. Ein belegter Port erzeugt einen Startfehler; ohne `--port` wird ein freier Port gewählt.

## Was sich ansehen und bedienen lässt

- **Überblick:** Kalenderkoordinaten, Nulltag, ein oder zwei q lange Nulldurchgänge, mittlere Mondphase und definierte Drehachse.
- **Hierarchie:** Großkarte, unabhängige Zwischenzyklus-Gruppierung, Karte, Jahr, Monat, Tag, Zyklus und Tick. Eine Ebene lässt sich zur Navigation auswählen.
- **4 × 23 und 6 × 23:** Umschalten zwischen 92- und 138-Jahresgruppen. Die zusätzliche Gruppierung verändert die Kalenderzählung und den Anker nicht.
- **Rundungsreste:** Jahres-, Karten- und Zyklusgrenzen als Diagramm mit exakten Brüchen, Fehlergrenze und Mittelwert. Die Jahresreste haben über 529 Jahre Mittelwert **3/529 q**; die 23 Kartenreste Mittelwert null.
- **3D-Sonnensystem:** Sonne und acht Planeten, Bahnen im räumlichen J2000-System, Maus-/Touchrotation und Zoom. Mit gemeinsamer Zeitnavigation und Zeitraffer; Planetenklick zeigt Bahndaten.
- **Daten:** UTC-Datum oder ganze q eingeben, vordefinierte Grenzen anspringen, Zustandsdaten als JSON und Diagrammdaten als CSV herunterladen.
- **Definitionen:** Formeln, Bedeutung der Achsen, Quellen, Autorenbezug und lokale Prüfungen.

## Zeit und mathematische Bedeutung

- Ursprung **jj = 12. Juli 2029, 22:00:00 UTC** = 13. Juli 2029, 00:00 MESZ.
- Die q-Koordinate zählt seit diesem Ereignis, alle Kalenderindizes beginnen bei null.
- **1 q = 75/1012 SI-Sekunden**, ein Tick = 23 q.
- Eingabebereich: **0 bis 966 definierte Jahre nach jj**, obere Grenze ausgeschlossen. Zeitpunkte vor jj werden erklärt abgewiesen. Der Viewer startet deshalb bei jj und nicht bei der heutigen Uhrzeit.
- UTC-Daten werden auf das nächste q gerundet; angezeigt wird der tatsächlich verwendete Zeitpunkt. Rundung direkt am oberen Horizont kann außerhalb des zulässigen q-Bereichs enden und wird dann abgewiesen.
- Der Systemtag ist eine eigene Zähleinheit und länger als der 86.400-Sekunden-Tag.
- Positiver Rest bedeutet **Sollgrenze liegt nach der gerundeten Zählgrenze**.
- Bei Kalender-Nulldurchgängen werden −2 und −1 bzw. nur −1 angezeigt. Der Nulltag nach 13 × 28 Tagen ist ein eigener Tag, kein 14. Monat.

Der Positionsrundungsfehler zum definierten Anker beträgt höchstens q/2; der Dauerfehler zwischen zwei Grenzen bleibt kleiner als q. Diese Eigenschaft beschränkt nicht die Abweichung der tatsächlichen Sonne oder des tatsächlichen Mondes von den definierten Modellen. Keine globale Sturmian-Eigenschaft und kein verschwindendes Jahrespositionsrestmittel werden behauptet.

## Bedeutung des 3D-Modells

Die Planetenpositionen stammen aus den **JPL-Näherungsbahnen, Tabellen 2a und 2b**. Ihr veröffentlichter Bereich 3000 v. Chr. bis 3000 n. Chr. umfasst den Demonstrationshorizont. Die äußeren Planeten enthalten die erforderlichen zusätzlichen Anomalieterme. Verwendet werden heliozentrische Koordinaten in AU relativ zur mittleren Ekliptik und zum Frühlingspunkt J2000.

- Das ist ein anschauliches Keplermodell, **keine vollständige gravitative N-Körper-Simulation und keine Präzisionsephemeride**.
- Die JPL-Formel verlangt TDB. Im Anschauungsmodell dient TT als Näherung des Zeitarguments.
- Der Erdmarker bezeichnet näherungsweise das **Erde-Mond-Baryzentrum**. Ein eigener Mond ist in der 3D-Ansicht nicht enthalten; die Kalenderseite zeigt separat die definierte mittlere Mondphase.
- Kugelgrößen sind symbolisch. Die umschaltbare komprimierte Abstandsskala verändert ausschließlich die Darstellung.
- Bahnlinien zeigen Ellipsen mit den am gewählten Zeitpunkt gültigen Elementen; sie sind keine gemessenen Trajektorien.
- Der Kalender-Anker wird nicht aus dem neuen 3D-Modell neu kalibriert. Die vereinfachte heliocentrische J2000-Bahn und der ursprüngliche scheinbare tropische Sonnenbezug sind unterschiedliche Modelle und Bezugssysteme.

Quelle: [NASA/JPL · Approximate Positions of the Planets](https://ssd.jpl.nasa.gov/planets/approx_pos.html), abgerufen am 04.11.2026.

## Autoren und Herkunft

- **Jörn Christian Anders:** Konzept, Leitideen und Festlegungen des Zyklus23-Projekts.
- **Claude (Anthropic):** mathematische Ausarbeitung, ursprüngliche Implementierung und Erstprüfung.
- **ChatGPT (OpenAI):** zusätzliche mathematische Prüfung, dokumentierte Korrekturen und dieses Demonstrationspaket einschließlich Viewer und 3D-Modell.

`referenz/` enthält die unveränderten bereitgestellten Ausgangsdateien und den Prüfbericht. Dieser Bericht untersucht die Ausgangsbasis; welche Punkte im Demonstrator korrigiert wurden, steht in `docs/STATUS.md`. Der ursprüngliche Referenztext bleibt als historische Quelle erhalten.

## Codeaufbau

| Datei | Aufgabe |
|---|---|
| `START.py` | Zentraler Start, Tests und lokaler HTTP-Server |
| `config.py` | Viewerparameter und Paketversion |
| `zyklus23.py` | Bestehender Kalender-/Mond-/Drehkern mit dokumentierten Korrekturen |
| `demo.py` | Exakte Anzeigeadapter, Diagrammreihen und Navigation |
| `planetarium.py` | Neue 3D-JPL-Näherungsbahnen |
| `web/` | Vollständige lokale Browseroberfläche |
| `tests/` | Unabhängige Sollfälle und angeschlossene API-Tests |
| `docs/VERTRAG.md` | Formeln, Schnittstellen und Abnahmekriterien |
| `docs/STATUS.md` | Aktueller Umsetzungs- und Nachweisstand |
| `docs/STAMMBAUM.md` | Basis, Version und datierte Erkenntnisse |
| `nachweise/` | Tatsächlich ausgeführte Prüfungen |
| `MANIFEST.sha256` | SHA256-Prüfsummen der ausgelieferten Dateien |

Der alleinige Start von `zyklus23.py` führt die älteren umfassenden Studien aus und kann dafür optionale Fachbibliotheken voraussetzen. Für den Demonstrator ist ausschließlich `START.py` vorgesehen. Astronomische Vollstudien, echte Polprognose-Kalibrierung und eine zertifizierte globale Minimax-Suche sind keine Funktionen dieses Viewers. Die vorhandene Minimax-Suche ist im Code ausdrücklich als begrenzte Näherung dokumentiert.

## Start in PyCharm

Den entpackten Ordner als Projekt öffnen, einen vorhandenen Python-Interpreter ab Version 3.10 auswählen und **START.py** starten. Ein GPU-Interpreter ist nicht erforderlich; ein bestehendes venv kann unverändert verwendet werden. Der Arbeitsordner darf vom Projektordner abweichen, da Ressourcen relativ zu START.py aufgelöst werden.

https://claude.ai/artifact/XWvNyZnRUALWByiC9KBuYT#c5e44717-6e8a
