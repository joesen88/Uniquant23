# Zyklus23 Demonstrator 1.0.0 - verbindlicher Umfang

Stand 04.11.2026. Umsetzung eines eigenständig lokal ausführbaren Demonstrators auf Basis der bereitgestellten `zyklus23(1).py`. Keine neue astronomische Kalibrierung, kein Modelltraining. Der Viewer benötigt ausschließlich Python >=3.10 und einen Browser, keine pip-Pakete und kein Internet. Konzept/Festlegungen: Jörn Christian Anders; mathematische Ausarbeitung/Implementierung des Ausgangsprojekts: Claude (Anthropic); Prüfung, Korrekturen und Demonstrator: ChatGPT (OpenAI).

## PHASENABLAUF

- PHASE=1: `python START.py --phase 1` prüft den mathematischen Demonstratorkern; schreibt `nachweise/lokaler_test.json`.
- PHASE=2: `python START.py` bzw. `python START.py --phase 2` startet den Viewer auf 127.0.0.1 und öffnet den Standardbrowser. Kein Testbericht ist zum normalen Start erforderlich.

## Zuständigkeiten

- `zyklus23.py`: bestehende Formeln, Konstanten und Klassen aus der Projektbasis; einzige mathematische Parameterautorität. Notwendige lokale Korrekturen erfolgen hier, keine zweite Kalenderimplementierung.
- `config.py`: neue Viewer-/Paketparameter VERSION, HOST=127.0.0.1, PORT=0 (freier Port), DEFAULT_GROUP=4, GROUP_OPTIONS=(4,6), MAX_SERIES_POINTS=2000; keine Kopie mathematischer Konstanten.
- `demo.py`: neue Adapterfunktion state(t_q,group), overview(), series(mode,start,count), checks(), date_state(utc,group), jump(t_q,unit,delta,group); verwendet die Klassen aus zyklus23.py. Rechnet Grenzen und Reste mit int/Fraction.
- `START.py`: zentraler CLI- und HTTP-Start (Standardbibliothek), statische Dateien und JSON-Endpunkte. GET /api/overview, /api/state?q=0&group=4, /api/date?utc=2029-07-12T22:00:00Z&group=4, /api/series?mode=year&start=0&count=529, /api/checks, /api/jump?q=0&unit=cycle&delta=1&group=4. Fehler als JSON {error: str} mit HTTP400; unbekannte Pfade404. Keine Schreib-API. Keine Verzeichnislisten. Server nur Loopback.
- `web/index.html`, `web/style.css`, `web/app.js`: deutschsprachiger Viewer, keine externen Ressourcen. Grafiken sind Visualisierungen der gelieferten Daten, keine unabhängigen mathematischen Rechner.
- `tests/test_demo.py`: unabhängige Sollfälle und API-/Grenztests. Kein Training.
- `README.md`, `docs/STAMMBAUM.md`, `docs/STATUS.md`: Anleitung, Herkunft/Erkenntnisse und aktueller Nachweisstand. `MANIFEST.sha256` wird aus den tatsächlichen Paketdateien abgeleitet.

## Geltungsbereich und Einheiten

Zeit t ist eine ganze Zahl in q seit jj=2029-07-12T22:00:00Z. Zulässig ist 0 <= t < VerteilterKalender.grenze(c_max), Horizont 966 Jahre. Werte vor jj oder ab Horizontende erzeugen einen erklärten Eingabefehler. Die Oberfläche startet bei jj, nicht vor der Epoche. UTC-Datumeingaben werden auf das nächste q gerundet und die tatsächlich dargestellte Zeit wird ausgegeben. Keine Schaltsekundenzeichen :60. Jahresindex n=Karte*23+Jahr; Kartenindex j=floor(n/23). Gruppierung (Gruppe, Phase)=divmod(j,m) mit m=4 oder6 läuft unabhängig von Großkarten durch. Weder Anker noch Jahresgrenzen ändern sich beim Wechsel von m.

Reste ρ=Soll−gerundete Grenze, positiv bedeutet Soll liegt nach der gezählten Grenze. Float-Werte dienen nur der Anzeige; alle q-Grenzen werden als dezimale Strings übergeben. Gruppennummern und Phasen sind nullbasiert. Mittel über529 Jahresanfangsreste ist3/529 q. Es wird keine globale Restnullmittel-Eigenschaft und keine Sturmian-Eigenschaft behauptet. Astronomische Anzeige ist definiertes Modell, keine unabhängige Naturmessung.

## API-Antworten (verbindlich für Frontend/Backend)

overview(): {version, credits:[{name,role}], epoch_utc, q_seconds:{exact,value}, horizon:{years,end_q,end_utc}, presets:[{label,q}], math:{Y,b,g,d,Z}, group_options:[4,6],default_group:4}.

state(): {q, utc, system_time, coordinate_text, calendar:{chart,year,year_index,month,day,day_of_year,cycle,cycle_index,tick,quant,kind,countdown}, group:{size,index,phase,start_year,end_year,start_q,end_q}, moon:{lunation,cycle,tick,joe,quant,phase,phase_degrees,mean_period_seconds}, rotation:{turn,cycle,tick,quant,residual}, levels:[{key,label,index,start_q,end_q,offset_q,total_q,progress}], residual:{cycle:{exact_q,q,seconds},year:{exact_q,q,seconds},chart:{exact_q,q,seconds}}, cycle:{length_q,zero_length_q,is_zero,offset_q,next_q}, year:{extra_q,length_q,length_seconds}}.

`q`, alle `*_q`-Grenzen/Längen/Offsets in levels/group/cycle/year und cycle_index sind Strings; `extra_q`, residual.q, residual.seconds, Phasen und übrige Indizes sind Numbers. `exact_q` enthält einen Fraction-String. calendar.kind = normal oder nd_zyklus. Während Nulldurchgang: tick=null,quant=null,countdown=-1 oder-2. Nulltag: month=null,day=null,day_of_year=364. moon.quant ist q seit Joe-Beginn. Die Levels umfassen Großkarte, Gruppierung, Karte, Jahr, Monat/Nulltag, Tag, Zyklus und Tick/Nulldurchgang; korrekte tatsächliche Grenzlängen aus dem bestehenden Anker.

series(): {mode,xlabel,ylabel,points:[{x,exact_q,q,seconds,extra_q}],summary:{count,mean_exact_q,mean_q,min_q,max_q,max_abs_q}}. mode=year (n=0..966),chart (j=0..42) oder cycle (c=0..c_max). count<=2000; Bereichsüberschreitung ist Fehler, kein stiller Clamp. points.extra_q ist beiyear ein Number, sonst null. Bei Jahrespunkt966 ist extra_q=null, da er den Endpunkt bezeichnet. /api/checks liefert {passed,checks:[{name,passed,detail}]}; meaningful checks prüfen feste Sollbeispiele, 529-Periodizität der Jahresreste, Mittel3/529 und Roundtrips.

jump(): unit=quantum (t+delta),cycle (Beginn Zyklus c+delta),year (Beginn Jahr n+delta),chart (Beginn Karte j+delta), delta ganz -1000..1000. Ergebnis ist state(). Datum- und Sprungfehler verändern den aktuellen Viewer-Zustand nicht.

## Abnahmekriterien vor Umsetzung

- A1: Entpacktes Paket startet mit `python START.py --no-browser`, liefert die lokalen Dateien und alle angeschlossenen API-Wege ohne pip-Abhängigkeiten.
- A2: t=0 ergibt alle Kalenderkoordinaten0; t=1518 ergibt Nulldurchgang-1; t=1519 beginnt Zyklus1; t=425807411 beginnt Jahr1; exakter Hin-/Rückweg an geprüften Grenzen. Mittel3/529 und 529-Jahresrestperiode stimmen.
- A3: Wechsel4/6 ändert nur Gruppierung. Zwei lange/kurze Nulldurchgänge und Nulltag werden gültig dargestellt. Eingabegrenzen erzeugen verständliche Fehler.
- A4: Viewer bedienbar mit UTC/q-Eingabe, Navigation, Gruppenauswahl, Ebenenverlauf, Restdiagrammen, Definitionen und JSON/CSV-Download. Offline, auch bei kleinerem Bildschirm ohne abgeschnittene Hauptbedienung. Browserprüfung wird tatsächlich ausgeführt und dokumentiert.
- A5: Bekanntes Minimax-Gegenbeispiel wird korrekt behandelt oder die Funktion wird zutreffend als beschränkte Näherung benannt. Datumsübertrag und Spline-Horizonte korrigiert. UTC-Konvertierung historisch korrekt im erklärten Bereich. S2-Anzeige behauptet keine exakte SI-Periodizität des UT1-Modells.
- A6: Vollständiges ZIP mit Start, Anleitung, Belegen, Autorenbezug, Herkunft und SHA256-Manifest; Starttest aus isoliert entpacktem finalem Paket. GPU nicht erforderlich.

## Ergänzung: 3D-Sonnensystem (Nutzerauftrag 04.11.2026)

Zusätzlicher Viewer-Tab mit Sonne und acht Planeten, frei mit Maus/Touch drehbar und per Mausrad/Bedienknöpfen zoombar. Derselbe q-Zeitpunkt wie im Kalender; Wiedergabe verändert diesen Zeitpunkt und alle Anzeigen gemeinsam. Geschwindigkeiten 1,10,100 Tage pro Sekunde, zusätzlich frei bedienbare Navigation. Ekliptikale J2000-Koordinaten, heliozentrisch, Entfernungen in AU. Erdmarker bezeichnet das Erde-Mond-Baryzentrum als Erdnäherung. Kugelgrößen nur symbolisch; Abstandsdarstellung proportional oder ausdrücklich komprimiert. Keine Behauptung eines DE440-Präzisionsmodells.

Neue Zuständigkeit `planetarium.py`: JPL-Elemente Tabellen2a/2b, inklusive b,c,s,f-Zusatztermen für äußere Planeten, Gültigkeit3000v.Chr.-3000n.Chr.; dies deckt den Viewerhorizont2029-2995. Quelle https://ssd.jpl.nasa.gov/planets/approx_pos.html, abgerufen04.11.2026. Veröffentliche im Modul keine zweite Zeitepoche: importiere jd_tt_aus_systemzeit aus zyklus23. Für diese Näherung wird TT als TDB-Näherung verwendet, ausdrücklich dokumentiert. Neue Felder und Modelle sind vollständig auf diese neue Zuständigkeit begrenzt.

GET /api/planets?q=0: {q,utc,frame,model,source,bodies:[{id,name,color,symbol_size,position_au:[x,y,z],distance_au,a_au,eccentricity,inclination_deg,period_days,orbit_au:[[x,y,z],...]}],notes:[str]}. `q` String. IDs sun,mercury,venus,earth,mars,jupiter,saturn,uranus,neptune. Sonne:Position[0,0,0],orbit_au=[],period_days=null,a_au=0. Orbits sind geschlossene128-Punkte-Polygone mit am Schluss wiederholtem Startpunkt, sonstkeine Veränderung von Achsen. `period_days` aus momentaner mittlerer Bewegung als demonstrative Näherung, nicht neu gemessener Naturwert. Symbolgrößen und Farbfelder sind Darstellungsdaten im Backend; keine wissenschaftlichen Radienbehauptungen.

- A7: 3D-Tab zeigt neun Körper samt Bahnen, Kamera verändert Ansicht tatsächlich, q-Wechsel verändert Positionen; Kreis-/Kepler-Randfall und gültige Orbitgeometrie werden unabhängig geprüft. Animation an Ende des erlaubten Horizonts stoppt. Keine Netzwerkzugriffe zur Laufzeit.
