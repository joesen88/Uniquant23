# Zyklus23 · Versions- und Erkenntnisverlauf

Stand 04.11.2026. Aktueller Umsetzungs- und Nachweisstand: [STATUS.md](STATUS.md). Definitionen und Schnittstellen: [VERTRAG.md](VERTRAG.md).

## V-BASIS-20261104 · Bereitgestelltes Projekt

- Stand der bereitgestellten Python-Datei: 04.11.2026; keine eigenständige Paketversion angegeben.
- Konzept und Festlegungen: Jörn Christian Anders.
- Mathematische Ausarbeitung und ursprüngliche Implementierung: Claude (Anthropic).
- Kopie: `../referenz/zyklus23_ausgangsbasis.py`.
- SHA256: `f17c784dde59df699ea8d8c80b5d9006b1c5a5be0776bff99931629a07d60d54`.
- Zugehöriges PDF: `../referenz/Integer_Time_Counting_1-23_Scale-3.pdf`, SHA256 `192a430f47fc26ad2baa4f6d987150cd7c4b58d2ce15e9c5d2ac1b63d4005fc9`.

## E-01 · Rundung und Restmittel

04.11.2026: Der Positionsrundungsfehler ist durch q/2 beschränkt, Intervallfehler sind kleiner als q. Die stärkere ursprüngliche Nullmittelbehauptung für alle Reste ist widerlegt: Jahrespositionsreste besitzen über529 Jahre das Mittel3/529 q. Kartenanfangsreste besitzen über23 Karten Mittelnull.

Beleg: Prüfbericht `../referenz/ZYKLUS23_MATHEMATISCHE_PRUEFUNG_2026-11-04.pdf`; ausführbare Sollfälle `../tests/test_core.py`, `../tests/test_demo.py`. Entscheidung: Anker und Zählung erhalten; Begriff und Anzeige berichtigen.

## E-02 · Perioden und Zusatzquanten

04.11.2026: Die kleinste Jahresrestperiode beträgt529 Jahre. Diese Periode gilt nicht für alle Zyklusreste; Jahreslängen selbst wiederholen sich ebenfalls nicht. Die globale Sturmian-Bezeichnung ist durch Jahresblöcke mit1331 bzw1290 Zusatzquanten widerlegt.

Entscheidung: präzise Jahresrestperiode anzeigen, keine globale Wiederkehr aller Natur- oder Kalenderzustände behaupten.

## E-03 · Statistik und beschränkte Minimax-Suche

04.11.2026: Die ursprünglichen98,7% sind eine feldzentrierte Modellrechnung. Die nachgeprüfte eintägige Polfeldtrefferquote auf demselben Rückrechnungsdatensatz ist303/407=74,45%. Dies ist keine neue unabhängige Kalibrierung. Die vorhandene Minimax-Suche garantiert kein globales Optimum.

Entscheidung: statistische Interpretation und beschränkte Suche im Projekttext präzisieren. Keine neue Polprognose oder globale Optimierung im Demonstrator.

## D-01 · Unabhängige Zwischenzyklus-Gruppierung

04.11.2026: Nutzer fragt nach4×23 und6×23 als zusätzlicher Ebene. Beide Varianten teilen die529-Jahres-Großkarte nicht vollständig.

Entscheidung: beide auswählbar, Standard4; Gruppierung läuft unabhängig vom Großkartenwechsel durch. Kalender und Anker unverändert. Kein behaupteter astronomischer Genauigkeitsgewinn.

## V-DEMO-1.0.0 · Lokaler Viewer und3D

- Datum04.11.2026, direkt aus V-BASIS-20261104 abgeleitet.
- Neues Verhalten: Browser-Viewer, exakte Anzeigeadapter, Restdiagramme, beide Zwischenzyklus-Gruppierungen und3D-Sonnensystem.
- Zusätzliche Mathematikquelle: NASA/JPL-Elementtabellen2a/2b; neue Zuständigkeit `planetarium.py`, ohne Neuanpassung des Zeitankers.
- Lokale Korrekturen: Datumsübertrag, Spline-Teilintervalle, historische UTC-Konvertierung und oben genannte Anspruchspräzisierungen.
- Belegumfang: Standardbibliotheks-Tests, HTTP-Schnittstelle, anschließend Browser- und entpackter Paketstart. Tatsächliche Resultate ausschließlich in [STATUS.md](STATUS.md) und `../nachweise/`.
- Inhaltliche Identität der Lieferung: `../MANIFEST.sha256`.
- Implementierung und zusätzliche Prüfung: ChatGPT (OpenAI); ursprüngliche Beiträge von Jörn und Claude bleiben ausgewiesen.

## Offene fachliche Folgefragen

- Unabhängiger Vergleich mit einer Präzisionsephemeride über den gesamtenHorizont; kein Ersatz durch bloße Reproduktion derselben Näherungsformeln.
- Ausgetrennte Kalibrierung der Polfeldwahrscheinlichkeiten.
- Falls gewünscht: zertifizierte globale ganzzahlige Minimax-Suche.
- Konkreter Erkenntniszweck der Vierer- oder Sechsergruppierung; ein Nutzen ist noch nicht experimentell nachgewiesen.

