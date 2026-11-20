# Zyklus23 Demonstrator 1.0.0 · Übergabestand

Stand 04.11.2026. Vertrag: [VERTRAG.md](VERTRAG.md); Herkunft und datierte Erkenntnisse: [STAMMBAUM.md](STAMMBAUM.md).

## Ausgewählter Lieferumfang

Vollständiges ausführbares Demonstrationspaket: Kalenderzählung und Rundungsreste ansehen,4×23/6×23-Gruppierung umschalten und ein3D-Sonnensystem mit gemeinsamem Zeitpunkt bedienen. Keine neue astronomische Kalibrierung, kein Training, keineGPU nötig.

## Arbeitsaufträge und Zuständigkeiten

| Auftrag | Ergebnis | Dateien | Abnahme / Übergabe |
|---|---|---|---|
| DEMO-01 | Projektkern übernehmen und lokale belegte Fehler korrigieren | zyklus23.py, tests/test_core.py | A2,A5; Verbraucher demo.py |
| DEMO-02 | Bestehenden Kern an neue Anzeige-API und lokalen Start anbinden | config.py,demo.py,START.py,tests/test_demo.py | A1,A2,A3; Verbraucher web/ |
| DEMO-03 | Neue3D-Näherungsbahnen aus veröffentlichter Quelle berechnen | planetarium.py,tests/test_planetarium.py | A7; Verbraucher web/ |
| DEMO-04 | Interaktive lokale Oberfläche einschließlich3D | web/index.html,web/style.css,web/app.js | A4,A7; Browserprüfung |
| DEMO-05 | Vollständige Lieferung mit Belegen und Herkunft | README.md,docs/,referenz/,nachweise/,MANIFEST.sha256 | A6; isoliert entpackter Start |

## Ausgeführte und noch ausstehende Nachweise

| Kriterium | Status | Beleg und Gültigkeitsbereich |
|---|---|---|
| A2,A3 | PASS |34 Python-Testmethoden einschließlich API, UTC/q-Rückweg, ein-/zwei-q-Nulldurchgänge, Nulltag,4/6-Unabhängigkeit und529-Jahres-Grenzen; `nachweise/lokaler_test.json` |
| A5 | PASS | Datumsübertrag, Teilhorizonte und historische UTC-Kopplung gezielt geprüft. Minimax ist zutreffend als beschränkte Näherung dokumentiert; keine globale Optimierung behauptet. |
| A7 numerisch | PASS | Keplergleichung, Kreis/Apsiden/Neigung/Knoten, geschlossene3D-Bahnen, neun Körper und gültige Horizontenden geprüft. |
| A1 | PASS | Produktiver Start aus isoliert entpacktem ZIP und fremdem Arbeitsverzeichnis mit python -S; statische Dateien und alle benötigten API-Wege HTTP200. `nachweise/entpackt_test.json` |
| A4,A7 Bedienung | PASS |15 tatsächliche Browser-Prüfgruppen in Chromium140, Desktop1440×1000 und schmale Ansicht390×844. Kamera verändert Bild; Animation synchronisiert Zeit und Planeten; JSON/CSV-Downloads geprüft; keine externen Laufzeitanfragen oder JavaScript-Ausnahmen. `nachweise/browser_test.json` |
| A6 | PASS | ZIP-Integrität, Pflichtdateien und sämtliche Manifest-Prüfsummen nach Entpacken geprüft; Code-Identität mit Python- und Browserbelegen abgeglichen. `nachweise/entpackt_test.json` und `MANIFEST.sha256` |

Die Tests liefen mit `python -S START.py --phase 1`: Zusatzpakete sind dabei nicht auf dem Importsuchpfad. Der normale Start benötigt ebenfalls ausschließlich die Python-Standardbibliothek. Der Nachweis erfordert keine optionalen astronomischen Bibliotheken.

Browserprüfung: Chromium140.0.7339.16 / Playwright1.55 nur in der Entwicklungsumgebung; der Benutzer benötigt diese Testwerkzeuge nicht. Die mitgelieferten Testbelege enthalten die SHA256-Werte der jeweils geprüften produktiven Dateien. Ein dabei aufgedeckter Slider-/Navigationskonflikt wurde vor der abschließenden Browserprüfung behoben.

## Bewusst begrenzte Aussagen

- Jahresanfangsreste sind529-periodisch; vollständige Zykluszustände und Naturbewegungen sind es nicht.
- Mittel über529 Jahresanfangsreste3/529 q; Mittel der23 Kartenrestklassennull.
- q/2 begrenzt den Rundungsfehler gegenüber der Definition, keinen Naturfehler.
- Minimax ist eine beschränkte Suche. Keine neue globale Garantie im Paket.
- 3D-Modell ist JPL-Näherung, kein unabhängiger Präzisionsnachweis des Kalenderankers.
- Die ursprüngliche Natur-/Kreisstudie wurde im vorangegangenen Prüfauftrag reproduziert. Dieser historische Beleg wird nicht als neue Ausführung des Demonstrators gezählt.
- Quelltexte können später weiterentwickelt werden; dann müssen die konkret betroffenen Nachweise erneut geprüft werden.


## Abschluss

Alle für diesen Demonstrator verpflichtenden Kriterien A1-A7 sind im genannten Gültigkeitsbereich bestanden. Keine offenen Laufzeitvoraussetzungen für den Viewer. Die separat benannten wissenschaftlichen Folgefragen bleiben offen; die Lieferung ist kein Nachweis einer neuen Naturgenauigkeit. Nächster nutzbarer Schritt: ZIP entpacken und START.py starten.
