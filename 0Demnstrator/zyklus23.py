#!/usr/bin/env python3
"""
zyklus23 - Referenzimplementierung: 23-Jahres-Zyklus auf der 1/23-Skala.

Autor:      Joern Christian Anders, B.Sc. Process Technology
            (Konzept, Leitideen und Festlegungen)
Mitwirkung: Claude (Anthropic): mathematische Ausarbeitung, Implementierung, Pruefung
            ChatGPT (OpenAI): zusaetzliche mathematische Pruefung und lokale Korrekturen
Stand:      4. November 2026

Prinzip: Jede ganzzahlige Groesse entsteht durch Runden eines exakten,
kumulierten Sollwerts. Der Fehler bleibt dadurch dauerhaft unter einer
halben Einheit; der Rest wird als Zustand mitgefuehrt (Fehlerrueckfuehrung
erster Ordnung, wie ein Sigma-Delta-Quantisierer mit exakten Integratoren).

Festlegung (Standard)
  jj         Durchgang 00 und Starttag: Freitag, 13. Juli 2029, 00:00:00 MESZ = 12.07.2029,
             22:00:00 UTC. Bis jj wird beobachtet, ab jj gilt die Definition; jede
             Abweichung Natur - Definition beginnt bei 0. Bei jj sind alle Kalenderkoordinaten 0.
  Jules      1 Ju = 69,159 s = 933,18544 q. Systemzeit = UTC + 1 Ju = TT - 25 ms (UTC ab 2027
             ohne Schaltsekunden, 28. CGPM Res. 5; TT = UTC + 69,184 s dauerhaft).
  Laenge     Systemlaenge = tropische Laenge - lambda0, lambda0 = scheinbare Sonnenlaenge bei 00
             (110,82764 Grad, vorlaeufig aus VSOP87). Die Sonne steht bei 00 auf 0 Grad.
  Jahr       Rueckkehr der Sonne auf 0 Grad Systemlaenge, vertreten durch den definierten Anker
             tau(x) = 425 806 080 x + (703 993 x - 11 x^2) / 529 q, x = Jahre ab 00.
             Rest an den Jahresanfaengen periodisch mit 529 Jahren (23 Karten = Grosskarte),
             an jeder Grosskartengrenze exakt 0; Reste der Kartenanfaenge durchlaufen alle k/23 q.
  Zaehlung   verteilt: jeder Zyklus = 66 Ticks + Nulldurchgang von 1 oder 2 q; jede
             Zyklusgrenze liegt hoechstens q/2 neben dem Anker. Kein Jahresblock, kein Randelement.
  Drehung    Delta T ab 00 als festes Polynom (Werte vorlaeufig, am Kalibrierpunkt aus IERS-Daten);
             gemessene Abweichungen als eigene Reihe (drehkorrektur_grad); Delta T in Jules.
  Mond       1 Lunation = 768 x 66 x 23 = 1 165 824 joe (joe : q = Monat : Tag);
             nu(x) = (9 634 217 446 503 x + 32 x^2) / 23^4 q, x = Lunationen ab jj; Phase bei
             jj 65 331 joe nach dem mittleren Neumond (Meeus 49.1).
  Pol        1 Iris (Ir) = 1''/299 (299 = 13 x 23) = 3,3445 mas = 10,33 cm; Pollage als Feld
             (ganzzahlig), Vorhersage als Wahrscheinlichkeit je Feld (IERS 20 C04).
  Delta T    gemessen seit 1972, in Jules ausgedrueckt, in Feldern von 1 q gezaehlt; Vorhersage als
             Wahrscheinlichkeit je Feld.
  Epizykel   die 8 Sonnen- und 8 Mondterme als ganzzahlige Phasenachsen (Platons Kreise).
  Knoten     Finsternisse aus dem Knotenabstand der mittleren Syzygien; ideales S2-Raster = 582 912 q,
             UT1-Modell nicht exakt SI-periodisch; Spring-Nipp = 582 912 joe, M2 aus q- und joe-Raster.
  Platon     Konvergenz der Kreise fuer Sonne, Mond und Mars gegen Kepler-Ellipsen
             (volle Rechnung: python3 zyklus23.py platon, rund 1,5 min).
  Quantische Irrelevanz: jeder Rest ist <= q/2, traegt ueber beliebige Fenster < 1 q bei,
             ist aus dem Anker exakt berechenbar. Der mittlere Dauerfehler pro Einheit
             verschwindet; Jahrespositionsreste haben dagegen Mittel 3/529 q (nicht 0).
  Horizont   42 Karten = 966 Jahre ab 00 (bis Juli 2995).

Herleitung und Referenzen (weiter enthalten)
  anker_herleiten()  Sonnenkreuzungen (PyEphem-Modell) -> Trend + 8 periodische Terme
                    -> beschraenkte Minimax-Naehersuche (kein globaler Optimalitaetsnachweis)
  Fruehlingspunkt    Meeus-Polynom, Aequinoktialgleichung, C1-Spline (Epoche Fruehlingspunkt 2027)
  Kalender           fruehere Tick-/q-Modi mit Jahres-Einfuegung und Randelement

Kalendergrenzen werden in exakter Bruch-/Ganzzahlarithmetik berechnet.
Positionen sind ganze Zahlen in Quanten q, gezaehlt ab der Epoche. Die optionalen
astronomischen Fits und Prognosen enthalten Gleitkommarechnungen und Modellannahmen;
ihre Reproduktion ist kein unabhaengiger Nachweis gegen Naturbeobachtungen.
"""

from __future__ import annotations

__author__ = "Joern Christian Anders"
__credits__ = ["Joern Christian Anders (Konzept)", "Claude, Anthropic (Ausarbeitung und Implementierung)",
               "ChatGPT, OpenAI (zusaetzliche Pruefung und Korrekturen)"]
__date__ = "2026-11-04"

import math
import random
import sys
from bisect import bisect_right
from dataclasses import dataclass
from datetime import date
from fractions import Fraction as F
from typing import Dict, List, Optional, Sequence, Tuple

SEKUNDEN_PRO_TAG = 86400


def runden(x: F) -> int:
    """Naechste ganze Zahl, halbe Werte aufwaerts; exakt."""
    return math.floor(x + F(1, 2))


# ---------------------------------------------------------------------------
# 0. Festlegung: Kalibrierpunkt 00, Systemlaenge, Anker
# ---------------------------------------------------------------------------

JJ = "jj"                                      # Name des Punkts 00 (Durchgang und Starttag)
KALIBRIERPUNKT_TEXT = "Freitag, 13. Juli 2029, 00:00:00 MESZ = 12. Juli 2029, 22:00:00 UTC"
EPOCHE_JD_UTC = F(2462330) + F(5, 12)          # 2029-07-12 22:00:00 UTC
# UTC laeuft ab 20. Mai 2027 ohne Schaltsekunden (28. CGPM, Resolution 5, 15.10.2026); TAI - UTC bleibt 37 s.
TT_MINUS_UTC = F("69.184")                     # 37 s + 32,184 s, dauerhaft fest
JULES_S = F("69.159")                          # 1 Jules (Ju) := 69,159 s = Systemzeit - UTC
SYSTEMZEIT_MINUS_UTC = JULES_S                 # Festlegung: Systemzeit = UTC + 1 Ju
SYSTEMZEIT_MINUS_TT = SYSTEMZEIT_MINUS_UTC - TT_MINUS_UTC      # -0,025 s: Systemzeit laeuft 25 ms hinter TT
EPOCHE_JD_TT = EPOCHE_JD_UTC + TT_MINUS_UTC / SEKUNDEN_PRO_TAG
EPOCHE_JD_SYS = EPOCHE_JD_UTC + SYSTEMZEIT_MINUS_UTC / SEKUNDEN_PRO_TAG   # Ablesung der Systemzeit in 00
LAMBDA0_GRAD = 110.82764018874991              # scheinbare Sonnenlaenge bei 00 (vorlaeufig, VSOP87)
JAHRE_HORIZONT = 23 * 42                       # 966 Jahre ab 00

# Definierter Anker: Parabel mit ganzzahligen Koeffizienten ueber dem Nenner 23^2 = 529
# (hergeleitet aus den wahren Sonnenkreuzungen von lambda0, siehe anker_herleiten()).
ANKER_B, ANKER_G, ANKER_D = 703993, -11, 529


# ---------------------------------------------------------------------------
# 1. Struktur
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Struktur:
    k: int = 23                # Quanten pro Tick
    N: int = 66                # Ticks pro Zyklus
    C: int = 768               # Zyklen pro Tag
    monate: int = 13
    monatstage: int = 28
    nulltage: int = 1
    jahre_pro_karte: int = 23

    @property
    def tage(self) -> int:
        return self.monate * self.monatstage + self.nulltage

    @property
    def tick_s(self) -> F:
        return F(SEKUNDEN_PRO_TAG, self.C * self.N)

    @property
    def q_s(self) -> F:
        return self.tick_s / self.k

    @property
    def zyklus_q(self) -> int:          # 66 Ticks + 1 q Nulldurchgang
        return self.k * self.N + 1

    @property
    def tag_q(self) -> int:
        return self.C * self.zyklus_q

    @property
    def jahr_q(self) -> int:
        return self.tage * self.tag_q

    @property
    def karte_q(self) -> int:           # 23 Jahre ohne Korrektur
        return self.jahre_pro_karte * self.jahr_q

    @property
    def jules_q(self) -> F:             # 1 Ju = 69,159 s = 5 832 409/6 250 q = 933,18544 q
        return JULES_S / self.q_s


# ---------------------------------------------------------------------------
# 2. Modell der Jahreslaenge
# ---------------------------------------------------------------------------

# Mittleres tropisches Jahr nach Laskar (1986) in Tagen zu 86 400 s,
# Argument: julianische Jahrhunderte ab J2000.
LASKAR = (F("365.2421896698"), F("-6.15359e-6"), F("-7.29e-10"), F("2.64e-10"))


@dataclass(frozen=True)
class Modell:
    koeff: Tuple[F, ...] = LASKAR
    bezugsjahr: F = F(2000)

    def _c(self, y) -> F:
        return (F(y) - self.bezugsjahr) / 100

    def T(self, y) -> F:
        """Laenge des Jahres bei Dezimaljahr y, in Tagen."""
        c = self._c(y)
        return sum(a * c ** i for i, a in enumerate(self.koeff))

    def stamm(self, y) -> F:
        """Stammfunktion von T nach y, in Tagen (d/dy stamm = T)."""
        c = self._c(y)
        return 100 * sum(a * c ** (i + 1) / (i + 1) for i, a in enumerate(self.koeff))

    def verstrichen(self, y0, y1) -> F:
        """Verstrichene Zeit in Tagen zwischen den Jahresanfaengen y0 und y1."""
        return self.stamm(y1) - self.stamm(y0)


LaskarModell = Modell

# Mittlere Maerz-Aequinoktien nach Meeus (JDE in Terrestrischer Zeit), Y = (Jahr - 2000) / 1000.
MEEUS_MAERZ = (F("2451623.80984"), F("365242.37404"), F("0.05169"), F("-0.00411"), F("-0.00057"))


@dataclass(frozen=True)
class FruehlingspunktModell:
    """Bezugspunkt Sonne: mittlerer Fruehlingspunkt (Maerz-Aequinoktium).
    Die Position ist direkt das Meeus-Polynom; die Jahreslaenge ist seine Ableitung."""
    koeff: Tuple[F, ...] = MEEUS_MAERZ

    @staticmethod
    def _Y(y) -> F:
        return (F(y) - 2000) / 1000

    def jde(self, y) -> F:
        """Mittleres Maerz-Aequinoktium des (Dezimal-)Jahres y als JDE (TT)."""
        Y = self._Y(y)
        return sum(a * Y ** i for i, a in enumerate(self.koeff))

    def T(self, y) -> F:
        """Laenge des Fruehlingspunktjahres bei y, in Tagen (Ableitung von jde nach y)."""
        Y = self._Y(y)
        return sum(i * a * Y ** (i - 1) for i, a in enumerate(self.koeff) if i > 0) / 1000

    def verstrichen(self, y0, y1) -> F:
        return self.jde(y1) - self.jde(y0)


def jd_zu_text(jd: F) -> str:
    """Julianisches Datum -> 'JJJJ-MM-TT hh:mm:ss' (proleptisch gregorianisch, ohne Zeitskalenwechsel)."""
    jd = F(jd) + F(1, 2)
    Z = math.floor(jd)
    frac = jd - Z
    # Sekunden zuerst runden: ein Mitternachtsuebertrag muss auch das Datum aendern.
    sek = round(frac * SEKUNDEN_PRO_TAG)
    uebertrag, sek = divmod(sek, SEKUNDEN_PRO_TAG)
    Z += uebertrag
    alpha = math.floor((Z - F(186721625, 100)) / F(3652425, 100))
    A = Z + 1 + alpha - alpha // 4
    B = A + 1524
    C = math.floor((B - F(1221, 10)) / F(36525, 100))
    D = math.floor(F(36525, 100) * C)
    E = math.floor((B - D) / F(306001, 10000))
    tag = B - D - math.floor(F(306001, 10000) * E)
    monat = E - 1 if E < 14 else E - 13
    jahr = C - 4716 if monat > 2 else C - 4715
    return f"{jahr:04d}-{monat:02d}-{tag:02d} {sek // 3600:02d}:{sek % 3600 // 60:02d}:{sek % 60:02d}"


# ---------------------------------------------------------------------------
# 3. Anker: Sollposition der Jahresanfaenge in q (n = Jahre ab Epoche)
# ---------------------------------------------------------------------------

class DirekterAnker:
    """Exakter Anker: Integral des Modells, ein Polynom 4. Grades in n."""

    name = "direkt (Laskar-Integral)"

    def __init__(self, s: Struktur, m: Modell, startjahr) -> None:
        self.s, self.m, self.y0 = s, m, F(startjahr)
        self._tage_zu_q = SEKUNDEN_PRO_TAG / s.q_s
        self._cache: Dict[int, F] = {}

    def soll(self, n: int) -> F:
        if n not in self._cache:
            self._cache[n] = self.m.verstrichen(self.y0, self.y0 + n) * self._tage_zu_q
        return self._cache[n]

    def steigung(self, n) -> F:
        """d soll / dn in q pro Jahr."""
        return self.m.T(self.y0 + n) * self._tage_zu_q


@dataclass(frozen=True)
class Segment:
    """Parabelstueck s(n) = a + b x + c x^2 mit x = n - n0, gueltig fuer n0 <= n <= n1."""
    n0: int
    n1: int
    a: F
    b: F
    c: F
    max_abw_q: F               # groesste Abweichung vom Referenzanker an Jahresanfaengen
    durch_horizont: bool       # True: Ende durch den Rechenhorizont, nicht durch die Schwelle

    def wert(self, n) -> F:
        x = n - self.n0
        return self.a + self.b * x + self.c * x * x

    def steigung(self, n) -> F:
        return self.b + 2 * self.c * (n - self.n0)

    def zweite_differenz(self, schritt: int = 23) -> F:
        """Konstante 2. Differenz der Positionen bei Schrittweite 'schritt' Jahre, in q."""
        return 2 * self.c * schritt * schritt


class SplineAnker:
    """C1-Spline aus Parabeln mit ereignisbasierten Knoten.

    Regel: Das laufende Segment wird um ganze 23-Jahres-Karten verlaengert,
    solange seine Abweichung vom Referenzanker an allen Jahresanfaengen
    hoechstens eps betraegt. Wert und Steigung gehen am Knoten stetig ueber,
    die Kruemmung springt (Ebene 3).
    """

    name = "C1-Spline, ereignisbasiert"

    def __init__(self, ref: DirekterAnker, bis_jahr: int, eps_q: F, schritt: int = 23) -> None:
        if not isinstance(bis_jahr, int) or bis_jahr <= 0:
            raise ValueError("Der Spline-Horizont muss eine positive ganze Jahreszahl sein")
        if not isinstance(schritt, int) or schritt <= 0:
            raise ValueError("Die Spline-Schrittweite muss eine positive ganze Zahl sein")
        if F(eps_q) < 0:
            raise ValueError("Die Spline-Fehlerschranke darf nicht negativ sein")
        self.ref, self.eps_q, self.schritt = ref, F(eps_q), schritt
        self.segmente: List[Segment] = []
        n0, a, b = 0, ref.soll(0), ref.steigung(0)
        while n0 < bis_jahr:
            bestes = None
            enden = list(range(n0 + schritt, bis_jahr + 1, schritt))
            if not enden or enden[-1] != bis_jahr:
                enden.append(bis_jahr)  # letztes, ggf. kuerzeres Horizontsegment
            for n1 in enden:
                h = n1 - n0
                c = (ref.soll(n1) - a - b * h) / (h * h)
                abw = max(abs(a + b * x + c * x * x - ref.soll(n0 + x)) for x in range(1, h + 1))
                if abw <= self.eps_q:
                    bestes = (n1, c, abw)
                    continue
                if bestes is None:          # schon eine Karte zu lang: trotzdem nehmen
                    bestes = (n1, c, abw)
                break
            n1, c, abw = bestes
            seg = Segment(n0, n1, a, b, c, abw, durch_horizont=(n1 == bis_jahr))
            self.segmente.append(seg)
            a, b, n0 = seg.wert(n1), seg.steigung(n1), n1
        self._starts = [sg.n0 for sg in self.segmente]

    def segment(self, n: int) -> Segment:
        if n < self.segmente[0].n0 or n > self.segmente[-1].n1:
            raise ValueError(f"Jahr {n} liegt ausserhalb des Splines")
        i = bisect_right(self._starts, n) - 1
        sg = self.segmente[i]
        if n > sg.n1:
            raise ValueError(f"Jahr {n} liegt ausserhalb des Splines")
        return sg

    def soll(self, n: int) -> F:
        return self.segment(n).wert(n)


class DefinierterAnker:
    """Festgelegter Anker tau(x) = Y x + (b x + g x^2) / d in q ab 00, x = Jahre ab 00 (auch gebrochen).

    Er definiert die Kalenderjahresgrenzen. Sonnenkreuzungen lieferten die
    Kalibrierbasis, liegen aber nicht zwingend auf der definierten Jahresgrenze.
    Die Abweichung wird als Natur - Definition beschrieben (bei 00 genau 0).
    Mit d = 23^2 und b, g teilerfremd zu 23 folgt:
      - Rest an den Jahresanfaengen periodisch mit 529 Jahren (Grosskarte = 23 Karten),
        an jeder Grosskartengrenze exakt 0;
      - Reste der Kartenanfaenge durchlaufen in 529 Jahren alle Werte k/23 q, k = -11..11;
      - der ungerundete Jahressprung aendert sich um genau 2g/d q pro Jahr;
        gerundete Spruenge aendern sich nach 529 Jahren um genau 2g q.
    Die 529-Periodizitaet gilt fuer Jahresanfangsreste, nicht fuer alle Zyklusreste.
    Zusatzquanten sind lokal annähernd gleichmaessig verteilt, aber keine globale Sturmian-Folge.
    Herkunft der Zahlen: anker_herleiten()."""

    name = "definiert (Parabel, Nenner 529)"

    def __init__(self, s: Struktur = Struktur(), b: int = ANKER_B, g: int = ANKER_G, d: int = ANKER_D) -> None:
        self.s, self.b, self.g, self.d = s, b, g, d

    def soll(self, x) -> F:
        x = F(x)
        return self.s.jahr_q * x + (self.b * x + self.g * x * x) / self.d

    def steigung(self, x) -> F:
        """d soll / dx in q pro Jahr."""
        return self.s.jahr_q + (self.b + 2 * self.g * F(x)) / self.d

    def sprung(self, n: int) -> F:
        """Exakter Jahressprung des Jahres n (Ueberschuss ueber 365 Nenntage) vor dem Runden."""
        return self.soll(n + 1) - self.soll(n) - self.s.jahr_q

    def runde_bei(self, c: int, teile: int) -> int:
        """runden(soll(c / teile)) in reiner Ganzzahlarithmetik (schnell und exakt)."""
        num = self.s.jahr_q * c * self.d * teile + self.b * c * teile + self.g * c * c
        den = self.d * teile * teile
        return (2 * num + den) // (2 * den)

    def umkehr(self, t) -> float:
        """Naeherung (float): Jahr x mit soll(x) = t; Startwert fuer die exakte Suche."""
        A = self.g / self.d
        B = self.s.jahr_q + self.b / self.d
        t = float(t)
        wurzel = B * B + 4 * A * t
        return 2 * t / (B + math.sqrt(wurzel)) if wurzel > 0 else -B / (2 * A)


def minimax_parabel(e: Sequence[float], nenner: int = ANKER_D) -> Tuple[int, int, float]:
    """Beschraenkte Minimax-Naehersuche fuer ganzzahlige b, g.

    Sucht g nur um den Least-Squares-Startwert (+/-4, mit Floor/Ceil) und b
    innerhalb +/-20000 um den gerundeten Startwert. Fuer festes g ist das
    Maximum in b konvex. Dies garantiert KEIN globales ganzzahliges Optimum.
    Gibt (b, g, groesste Abweichung im untersuchten Suchbereich) zurueck.
    Der historische Funktionsname bleibt fuer bestehende Aufrufer erhalten.
    """
    if len(e) < 3 or nenner <= 0:
        raise ValueError("Mindestens drei Werte und ein positiver Nenner sind erforderlich")
    ns = range(len(e))
    S2, S3, S4 = (sum(n ** p for n in ns) for p in (2, 3, 4))
    T1, T2 = sum(n * e[n] for n in ns), sum(n * n * e[n] for n in ns)
    det = S2 * S4 - S3 * S3
    beta, gamma = (T1 * S4 - T2 * S3) / det, (S2 * T2 - S3 * T1) / det

    def maxabw(b: int, g: int) -> float:
        return max(abs((b * n + g * n * n) / nenner - e[n]) for n in ns)

    bestes = None
    for g in range(math.floor(gamma * nenner) - 4, math.ceil(gamma * nenner) + 5):
        lo, hi = round(beta * nenner) - 20000, round(beta * nenner) + 20000
        while hi - lo > 2:
            m1, m2 = lo + (hi - lo) // 3, hi - (hi - lo) // 3
            if maxabw(m1, g) <= maxabw(m2, g):
                hi = m2
            else:
                lo = m1
        b = min(range(lo, hi + 1), key=lambda bb: maxabw(bb, g))
        w = maxabw(b, g)
        if bestes is None or w < bestes[2]:
            bestes = (b, g, w)
    return bestes


def sonnenlaenge_scheinbar(jd_tt: float) -> float:
    """Scheinbare geozentrische Sonnenlaenge in Grad (wahres Aequinoktium des Datums):
    geometrisch aus VSOP87 (PyEphem) + Nutation in Laenge + Aberration (-20,4898''/R). Benoetigt PyEphem."""
    import ephem
    dublin = 2415020.0
    d = ephem.Date(jd_tt - dublin)
    for _ in range(2):                           # TT -> UT ueber das Delta T von PyEphem
        d = ephem.Date(jd_tt - ephem.delta_t(d) / SEKUNDEN_PRO_TAG - dublin)
    sonne = ephem.Sun()
    sonne.compute(d, epoch=d)
    lam = math.degrees(sonne.hlon) + 180.0
    lam += nutation(jd_tt)[0] / 3600.0 - 20.4898 / sonne.earth_distance / 3600.0
    return lam % 360.0


def systemlaenge(tropisch_grad: float) -> float:
    """Systemlaenge = tropische Laenge - lambda0 (die Sonne steht bei 00 auf 0 Grad)."""
    return (tropisch_grad - LAMBDA0_GRAD) % 360.0


def sonnenkreuzungen(jahre: int = JAHRE_HORIZONT) -> List[float]:
    """JD (TT) der Zeitpunkte, zu denen die wahre Sonne 0 Grad Systemlaenge erreicht, n = 0..jahre.
    n = 0 ist der Kalibrierpunkt selbst. Benoetigt PyEphem."""
    aus, jd = [], float(EPOCHE_JD_TT)
    for n in range(jahre + 1):
        if n:
            jd += 365.2416
        for _ in range(30):
            l1 = sonnenlaenge_scheinbar(jd)
            dl = ((LAMBDA0_GRAD - l1 + 180.0) % 360.0) - 180.0
            if abs(dl) < 1e-10:
                break
            rate = ((((sonnenlaenge_scheinbar(jd + 0.01) - l1) + 180.0) % 360.0) - 180.0) / 0.01
            jd += dl / rate
        aus.append(jd)
    return aus


def anker_herleiten(jahre: int = JAHRE_HORIZONT, s: Struktur = Struktur()) -> Optional[Dict[str, object]]:
    """Wie die Festlegung entsteht (Kalibrierung):
    1. wahre Sonnenkreuzungen von lambda0 fuer n = 0..jahre (PyEphem; endgueltig mit DE440),
    2. Zerlegung in kubischen Trend + 8 periodische Terme fester Herkunft (kleinste Quadrate),
    3. Trend durch 00 verschoben, darauf beschraenkte Minimax-Naehersuche mit Nenner 529.
    Gibt b, g, Abweichungen und Kennzahlen zurueck; None ohne PyEphem/NumPy."""
    try:
        import numpy as np
        kr = sonnenkreuzungen(jahre)
    except ImportError:
        return None
    n = np.arange(jahre + 1, dtype=float)
    e = np.array([float((F(x) - EPOCHE_JD_TT) * SEKUNDEN_PRO_TAG / s.q_s) for x in kr]) - s.jahr_q * n
    jahr_tage = (kr[-1] - kr[0]) / jahre
    x = n / 1000.0
    spalten = [np.ones_like(x), x, x ** 2, x ** 3]
    terme = []
    for name, P, harmonische in SCHWANKUNGSQUELLEN:
        for h in harmonische:
            fa = h * jahr_tage / P - round(h * jahr_tage / P)
            spalten += [np.cos(2 * np.pi * fa * n), np.sin(2 * np.pi * fa * n)]
            terme.append((name, h, 1.0 / abs(fa)))
    A = np.vstack(spalten).T
    k, *_ = np.linalg.lstsq(A, e, rcond=None)
    trend = A[:, :4] @ k[:4]
    periodisch = A[:, 4:] @ k[4:]
    glatt = trend - trend[0]
    b, g, w = minimax_parabel(list(glatt), ANKER_D)
    tau = (b * n + g * n * n) / ANKER_D
    natur = e - tau                                  # Natur - Definition in q
    q = float(s.q_s)
    amp = sorted(((float(np.hypot(k[4 + 2 * i], k[5 + 2 * i])) * q / 60, t) for i, t in enumerate(terme)),
                 reverse=True)
    koeff_terme = []
    for i, (name, h_, periode) in enumerate(terme):
        P = next(PP for nn, PP, _ in SCHWANKUNGSQUELLEN if nn == name)
        f_wahr = h_ * jahr_tage / P                      # Umlaeufe pro Jahr (physikalisch)
        koeff_terme.append((name, h_, f_wahr, float(k[4 + 2 * i]), float(k[5 + 2 * i])))
    return {"b": b, "g": g, "max_abw_trend_s": w * q, "jahr_tage": jahr_tage,
            "natur_q": natur, "glatt_minus_anker_q": trend - tau, "koeff_terme": koeff_terme,
            "natur_min": (natur * q / 60), "streuung_vorher_min": float(np.std(e - trend)) * q / 60,
            "streuung_rest_min": float(np.std(e - trend - periodisch)) * q / 60,
            "groesster_rest_min": float(np.max(np.abs(e - trend - periodisch))) * q / 60,
            "mittel_natur_min": float(trend[0]) * q / 60, "terme": amp}


# ---------------------------------------------------------------------------
# 4. Karten (23-Jahres-Zyklen)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Karte:
    j: int
    P: int                     # Kartenanfang (q ab Epoche)
    P_naechste: int
    R: int                     # Gesamtkorrektur in q: P_naechste - P - 23 Y
    einheit_q: int             # 23 (Tick-Modus) oder 1 (q-Modus)
    C: Tuple[int, ...]         # kumulierte Einfuegungen nach Jahr 1..23 in Einheiten, C[0] = 0
    r: int                     # Randelement in q: > 0 Luecke, < 0 Ueberlappung
    starts: Tuple[int, ...]    # relative Jahresanfaenge m = 0..23 (m = 23: Inhaltsende)

    @property
    def inhalt_ende(self) -> int:
        """Absolutes Ende des gezaehlten Inhalts (inkl. Jahres-Einfuegungen)."""
        return self.P + self.starts[23]

    def einfuegungen(self) -> List[int]:
        """Einfuegung am Ende von Jahr m (m = 0..22), in Einheiten."""
        return [self.C[m + 1] - self.C[m] for m in range(23)]


@dataclass(frozen=True)
class Koordinate:
    karte: int
    art: str                   # normal | nd_zyklus | nd_jahr | luecke
    jahr: Optional[int] = None     # 0..22
    tag: Optional[int] = None      # 0..364, 364 = Nulltag
    zyklus: Optional[int] = None   # 0..767
    tick: Optional[int] = None     # 0..65
    quant: Optional[int] = None    # 0..22
    index: Optional[int] = None    # Lage innerhalb eines Nulldurchgangs (q)
    fold: int = 0                  # 0/1, nur in einer Ueberlappung von Bedeutung

    def text(self) -> str:
        """Alle Stellen 0-basiert (00 = Karte 0, Jahr 0, Monat 0, Tag 0, Zyklus 0, Tick 0, q 0)."""
        if self.art == "uebergang":
            return f"Karte {self.karte}, Jahr {self.jahr}, Uebergang {self.index} q (Countdown)"
        if self.art == "luecke":
            return f"Karte {self.karte}, Randluecke +{self.index} q"
        if self.art == "nd_jahr":
            return f"Karte {self.karte}, Jahr {self.jahr}, Jahres-Nulldurchgang +{self.index} q (fold={self.fold})"
        tagtext = "Nulltag" if self.tag == 364 else f"Monat {self.tag // 28}, Tag {self.tag % 28}"
        if self.art == "nd_zyklus":
            idx = "" if self.index is None else f" {self.index} q"
            return f"Karte {self.karte}, Jahr {self.jahr}, {tagtext}, Zyklus {self.zyklus}, Zyklus-Nulldurchgang{idx}"
        return (f"Karte {self.karte}, Jahr {self.jahr}, {tagtext}, Zyklus {self.zyklus}, "
                f"Tick {self.tick}, q {self.quant}")


class Kalender:
    """Baut Karten aus einem Anker und bildet Zeitpunkte auf Koordinaten ab."""

    def __init__(self, s: Struktur, anker, karten: int, modus: str = "tick",
                 rand: str = "signiert") -> None:
        if modus not in ("tick", "q") or rand not in ("signiert", "luecke"):
            raise ValueError("modus: tick|q, rand: signiert|luecke")
        self.s, self.anker, self.modus, self.rand = s, anker, modus, rand
        Y, J = s.jahr_q, s.jahre_pro_karte
        u = s.k if modus == "tick" else 1
        self.P = [runden(anker.soll(J * j)) for j in range(karten + 1)]
        self.karten: List[Karte] = []
        for j in range(karten):
            P, Pn = self.P[j], self.P[j + 1]
            R = Pn - P - J * Y
            if modus == "q":
                K, r = R, 0
            else:
                K = runden(F(R, u)) if rand == "signiert" else R // u
                r = R - u * K
            C = [0]
            for m in range(1, J):
                C.append(runden((anker.soll(J * j + m) - P - m * Y) / u))
            C.append(K)
            starts = tuple(m * Y + u * C[m] for m in range(J + 1))
            self.karten.append(Karte(j, P, Pn, R, u, tuple(C), r, starts))

    # --- Fehler ---------------------------------------------------------------

    def jahresfehler(self, j: int, gegen=None) -> List[F]:
        """Fehler der Jahresanfaenge m = 0..22 von Karte j (q), gegen Anker oder Referenz."""
        ziel = gegen if gegen is not None else self.anker
        k = self.karten[j]
        return [k.P + k.starts[m] - ziel.soll(23 * j + m) for m in range(23)]

    # --- Koordinaten ------------------------------------------------------------

    def _lokal(self, k: Karte, t: int, fold: int) -> Koordinate:
        s, Y = self.s, self.s.jahr_q
        x = t - k.P
        m = bisect_right(k.starts, x) - 1
        if m >= 23:
            return Koordinate(k.j, "luecke", index=x - k.starts[23])
        off = x - k.starts[m]
        if off >= Y:
            return Koordinate(k.j, "nd_jahr", jahr=m, index=off - Y, fold=fold)
        tag, rest = divmod(off, s.tag_q)
        zyk, rest2 = divmod(rest, s.zyklus_q)
        if rest2 >= s.k * s.N:
            return Koordinate(k.j, "nd_zyklus", jahr=m, tag=tag, zyklus=zyk, fold=fold)
        tick, quant = divmod(rest2, s.k)
        return Koordinate(k.j, "normal", jahr=m, tag=tag, zyklus=zyk, tick=tick, quant=quant, fold=fold)

    def ueberlappung(self, t: int) -> bool:
        j = bisect_right(self.P, t) - 1
        return j > 0 and self.karten[j - 1].r < 0 and t < self.karten[j - 1].inhalt_ende

    def koordinaten(self, t: int, fold: int = 0) -> Koordinate:
        j = bisect_right(self.P, t) - 1
        if not 0 <= j < len(self.karten):
            raise ValueError("Zeitpunkt ausserhalb der berechneten Karten")
        if self.ueberlappung(t):
            if fold == 0:
                return self._lokal(self.karten[j - 1], t, 0)
            return self._lokal(self.karten[j], t, 1)
        return self._lokal(self.karten[j], t, 0)

    # --- Countdown-Konvention: Uebergaenge zaehlen -n ... -1 bis zur naechsten Null ---

    def koordinaten_countdown(self, t: int) -> Koordinate:
        """Wie koordinaten(), aber jeder Uebergang zwischen zwei Jahren (Jahres-Nulldurchgang,
        an Kartengrenzen samt Randelement) wird rueckwaerts auf den naechsten Jahresanfang
        gezaehlt: Index -n ... -1, die 0 ist eindeutig der Anfang der neuen Einheit.
        Eine Ueberlappung verkuerzt nur den letzten Uebergang; ein fold-Flag ist unnoetig."""
        Y = self.s.jahr_q
        j = bisect_right(self.P, t) - 1
        if not 0 <= j < len(self.karten):
            raise ValueError("Zeitpunkt ausserhalb der berechneten Karten")
        k = self.karten[j]
        x = t - k.P
        m = min(bisect_right(k.starts, x) - 1, 22)
        if x - k.starts[m] < Y:
            return self._lokal(k, t, 0)
        if m < 22:
            return Koordinate(j, "uebergang", jahr=m + 1, index=x - k.starts[m + 1])
        return Koordinate(j + 1, "uebergang", jahr=0, index=t - k.P_naechste)

    def zeitpunkt_countdown(self, c: Koordinate) -> int:
        if c.art == "uebergang":
            ziel = self.P[c.karte] if c.jahr == 0 else self.karten[c.karte].P + self.karten[c.karte].starts[c.jahr]
            return ziel + c.index
        return self.zeitpunkt(c)

    def zeitpunkt(self, c: Koordinate) -> int:
        s = self.s
        k = self.karten[c.karte]
        if c.art == "luecke":
            return k.P + k.starts[23] + c.index
        basis = k.P + k.starts[c.jahr]
        if c.art == "nd_jahr":
            return basis + s.jahr_q + c.index
        basis += c.tag * s.tag_q + c.zyklus * s.zyklus_q
        if c.art == "nd_zyklus":
            return basis + s.k * s.N
        return basis + c.tick * s.k + c.quant


class VerteilterKalender:
    """Standard-Zaehlung: der gesamte Rest sitzt in den Zyklus-Nulldurchgaengen (1 oder 2 q).

    Zyklusgrenze c (Zyklen ab Epoche): B(c) = runden(anker.soll(c / Z)), Z = 365 x 768 = 280 320.
    Jede Zyklusgrenze liegt hoechstens q/2 neben dem Anker; Jahres- und Kartenanfaenge sind
    gewoehnliche Zyklusgrenzen. Ein Jahr hat genau 280 320 Zyklen, davon J(n) mit 2-q-Nulldurchgang,
    J(n) = Jahressprung. Den Nulldurchgang zaehlt die Koordinate rueckwaerts (-2, -1 bzw. -1):
    vor jeder Null steht -1, ein fold-Flag ist unnoetig."""

    def __init__(self, s: Struktur, anker, jahre: int = 23 * 42) -> None:
        self.s, self.anker, self.jahre = s, anker, jahre
        self.Z = s.tage * s.C
        self.c_max = self.Z * jahre

    def grenze(self, c: int) -> int:
        if hasattr(self.anker, "runde_bei"):
            return self.anker.runde_bei(c, self.Z)
        return runden(self.anker.soll(F(c, self.Z)))

    def jahresanfang(self, n: int) -> int:
        return self.grenze(n * self.Z)

    def sprung(self, n: int) -> int:
        """Jahressprung J(n) in q = Anzahl der 2-q-Nulldurchgaenge im Jahr n."""
        return self.jahresanfang(n + 1) - self.jahresanfang(n) - self.s.jahr_q

    def zyklus_von(self, t: int) -> int:
        """Groesstes c mit B(c) <= t."""
        if hasattr(self.anker, "umkehr"):
            c = math.floor(self.anker.umkehr(t + 0.5) * self.Z)
            while self.grenze(c + 1) <= t:
                c += 1
            while self.grenze(c) > t:
                c -= 1
            return c
        lo, hi = 0, self.c_max
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.grenze(mid) <= t:
                lo = mid
            else:
                hi = mid
        return lo

    def koordinaten(self, t: int) -> Koordinate:
        s = self.s
        if not self.grenze(0) <= t < self.grenze(self.c_max):
            raise ValueError("Zeitpunkt ausserhalb des Horizonts")
        c = self.zyklus_von(t)
        b0 = self.grenze(c)
        o = t - b0
        n, w = divmod(c, self.Z)
        karte, jahr = divmod(n, s.jahre_pro_karte)
        tag, zyk = divmod(w, s.C)
        if o < s.k * s.N:
            tick, quant = divmod(o, s.k)
            return Koordinate(karte, "normal", jahr, tag, zyk, tick, quant)
        return Koordinate(karte, "nd_zyklus", jahr, tag, zyk, index=t - self.grenze(c + 1))

    def zeitpunkt(self, k: Koordinate) -> int:
        s = self.s
        c = ((k.karte * s.jahre_pro_karte + k.jahr) * s.tage + k.tag) * s.C + k.zyklus
        if k.art == "nd_zyklus":
            return self.grenze(c + 1) + k.index
        return self.grenze(c) + k.tick * s.k + k.quant

    def jahr_analyse(self, n: int) -> Dict[str, object]:
        """Ein ganzes Jahr: Zykluslaengen, Abstaende der 2-q-Nulldurchgaenge, 2-q je Tag,
        groesste Abweichung der Zyklusgrenzen vom Anker (exakt)."""
        s, Z = self.s, self.Z
        c0 = n * Z
        B = [self.grenze(c) for c in range(c0, c0 + Z + 1)]
        L = [B[i + 1] - B[i] for i in range(Z)]
        lang = [i for i in range(Z) if L[i] == s.zyklus_q + 1]
        abstaende = sorted(set(b - a for a, b in zip(lang, lang[1:])))
        je_tag = sorted(set(sum(1 for i in range(d * s.C, (d + 1) * s.C) if L[i] == s.zyklus_q + 1)
                            for d in range(s.tage)))
        abw = max(abs(B[i] - self.anker.soll(F(c0 + i, Z))) for i in range(0, Z + 1, 97))
        return {"laengen": sorted(set(L)), "zwei_q": len(lang), "abstaende": abstaende,
                "je_tag": je_tag, "max_abw_q": abw}


# ---------------------------------------------------------------------------
# 5. Differenzenschema und Zustand
# ---------------------------------------------------------------------------

def differenzmaschine(startwerte: Sequence[F], schritte: int) -> List[F]:
    """Werte eines Polynoms vom Grad d aus seinen ersten d+1 Werten,
    weitergerechnet nur mit Additionen (Newtonsches Differenzenschema)."""
    zeile, tabelle = list(startwerte), []
    while zeile:
        tabelle.append(zeile[0])
        zeile = [zeile[i + 1] - zeile[i] for i in range(len(zeile) - 1)]
    aus, cur = [], tabelle[:]
    for _ in range(schritte):
        aus.append(cur[0])
        for i in range(len(cur) - 1):
            cur[i] += cur[i + 1]
    return aus


def zustandsperiode(D: F, S0: F, Y: int, max_periode: int = 1000) -> Optional[int]:
    """Periode des Zustands (Nachkommateile von Position und Zuwachs) bei konstanter
    2. Differenz D. Endlich, sobald D und S0 rational sind."""
    A, s, folge = F(0), S0, []
    for _ in range(3 * max_periode):
        folge.append((A - math.floor(A), s - math.floor(s)))
        A, s = A + 23 * Y + s, s + D
    for p in range(1, max_periode + 1):
        if all(folge[i] == folge[i + p] for i in range(len(folge) - p)):
            return p
    return None


# ---------------------------------------------------------------------------
# 6. Drehachse: Erdrotation, Sternzeit, Aszendent und Haeuser
# ---------------------------------------------------------------------------
#
# Zweite Zaehlachse neben der Jahresachse. Beide beziehen sich auf den Fruehlingspunkt:
# die Jahresachse auf die Sonne im Fruehlingspunkt, die Drehachse auf den Fruehlingspunkt
# im Meridian (Sternzeit). Kopplung an die SI-Zeit ueber Delta T = TT - UT1 (gemessen,
# fuer die Zukunft extrapoliert). Drei Bewegungen der Erdachse:
#   Drehung   Erdrotationswinkel ERA (IAU 2000), linear in UT1
#   Kegel     Praezession: Polynom zwischen ERA (Sternbezug) und GMST (Fruehlingspunktbezug)
#   Pendeln   Nutation: periodische Terme (Hauptterm 18,6 Jahre), fuer scheinbare Sternzeit
# Die Polbewegung (Bruchteile einer Bogensekunde) wird nicht modelliert.

DREH_Q_PRO_UMLAUF = 768 * 66 * 23          # 1 165 824 Dreh-Quanten pro Sternumlauf (Raster wie der Tag)
TT_MINUS_UTC_S = float(TT_MINUS_UTC)       # TAI-UTC = 37 s (seit 2017, ab 2027 dauerhaft) + 32,184 s

# Delta T in Sekunden (gerundet; 2000 und 2020 laut Wikipedia/IERS, uebrige nach Espenak/Meeus).
DELTA_T_STUETZWERTE = ((1950, 29.15), (1955, 31.07), (1960, 33.15), (1965, 35.73), (1970, 40.18),
                       (1975, 45.48), (1980, 50.54), (1985, 54.34), (1990, 56.86), (1995, 60.78),
                       (2000, 63.83), (2005, 64.69), (2010, 66.07), (2015, 67.64), (2020, 69.36),
                       (2027, 69.2))


DELTA_T_RATE = 0.28          # s/Jahr, mittlerer Anstieg 2000-2020
DELTA_T_BESCHL = 0.0064      # s/Jahr^2, zweite Ableitung der Langzeitparabel -20 + 32 u^2 (Gezeitenbremsung)


def delta_t(jahr: float) -> float:
    """TT - UT1 in Sekunden. 1950-2027 aus Stuetzwerten interpoliert. Ab 2027 Extrapolation:
    69,2 s + 0,28 s/J * (J - 2027) + 0,0032 s/J^2 * (J - 2027)^2, also heutiger Anstieg plus
    Gezeitenbeschleunigung. Vor 1950 grob ueber die Langzeitparabel. Die Zukunft ist unsicher und
    wird mit Messungen (IERS Bulletin A) neu verankert: Delta T ist der beobachtete Rest der Drehachse."""
    pts = DELTA_T_STUETZWERTE
    if jahr < pts[0][0]:
        parabel = lambda y: -20 + 32 * ((y - 1820) / 100) ** 2
        return parabel(jahr) - (parabel(pts[0][0]) - pts[0][1])
    for (y0, d0), (y1, d1) in zip(pts, pts[1:]):
        if jahr <= y1:
            return d0 + (d1 - d0) * (jahr - y0) / (y1 - y0)
    y_end, d_end = pts[-1]
    dy = jahr - y_end
    return d_end + DELTA_T_RATE * dy + 0.5 * DELTA_T_BESCHL * dy * dy


def jd_tt_aus_systemzeit(t_q, s: Struktur = Struktur()) -> float:
    """System-Zeitpunkt (q ab Kalibrierpunkt 00) -> Julianisches Datum TT."""
    return float(EPOCHE_JD_TT + F(t_q) * s.q_s / SEKUNDEN_PRO_TAG)


def systemzeit_aus_jd_tt(jd_tt: float, s: Struktur = Struktur()) -> int:
    """Julianisches Datum TT -> naechster System-Zeitpunkt in q ab 00."""
    return runden((F(jd_tt) - EPOCHE_JD_TT) * SEKUNDEN_PRO_TAG / s.q_s)


def drehkorrektur_grad(delta_t_gemessen_s: float, jahr: float) -> float:
    """Definierte Drehung: ab 00 gilt Delta T per Definition (delta_t). Weicht der gemessene Wert ab,
    liegt der wahre Meridian um diesen Winkel versetzt (in Grad, auf die definierte Sternzeit zu addieren):
    -(Delta T gemessen - Delta T definiert) * 1,0027379 * 360 / 86400."""
    return -(delta_t_gemessen_s - delta_t(jahr)) * 1.00273781191135448 * 360.0 / SEKUNDEN_PRO_TAG


# TAI-UTC ab 1972, jeweils wirksam am angegebenen UTC-Tagesanfang.
# Historische Spruenge gemaess IERS/SOFA; ab 2017 37 s. Im Zukunftsbereich
# dieses Projekts gilt der festgelegte Stand (CGPM-Resolution 5, 2026).
_TAI_MINUS_UTC_AB = (
    (1972, 1, 1, 10), (1972, 7, 1, 11), (1973, 1, 1, 12),
    (1974, 1, 1, 13), (1975, 1, 1, 14), (1976, 1, 1, 15),
    (1977, 1, 1, 16), (1978, 1, 1, 17), (1979, 1, 1, 18),
    (1980, 1, 1, 19), (1981, 7, 1, 20), (1982, 7, 1, 21),
    (1983, 7, 1, 22), (1985, 7, 1, 23), (1988, 1, 1, 24),
    (1990, 1, 1, 25), (1991, 1, 1, 26), (1992, 7, 1, 27),
    (1993, 7, 1, 28), (1994, 7, 1, 29), (1996, 1, 1, 30),
    (1997, 7, 1, 31), (1999, 1, 1, 32), (2006, 1, 1, 33),
    (2009, 1, 1, 34), (2012, 7, 1, 35), (2015, 7, 1, 36),
    (2017, 1, 1, 37),
)


def _tt_minus_utc_s(jahr: int, monat: int, tag: int) -> float:
    """TT(TAI)-UTC fuer gueltige gregorianische Daten ab 1972, ohne :60-Eingabe."""
    datum = date(jahr, monat, tag)  # prueft auch ungueltige Monat-/Tagkombinationen
    if datum < date(1972, 1, 1):
        raise ValueError("UTC vor 1972 wird nicht unterstuetzt (historische Frequenzkorrekturen)")
    return 32.184 + next(s for y, m, d, s in reversed(_TAI_MINUS_UTC_AB)
                         if (jahr, monat, tag) >= (y, m, d))


def jd_tt_aus_utc(jahr: int, monat: int, tag: int, stunde: int = 0, minute: int = 0, sekunde: float = 0.0) -> float:
    """Buergerliche Zeit UTC -> JD TT(TAI), ab 1972 mit historischer Schaltsekundentabelle.

    Ab 2017 ist TT(TAI)-UTC 69,184 s; fuer die Projektzukunft bleibt dieser
    Tabellenstand gemaess CGPM-Resolution 5 (2026) bestehen. Eingaben einer
    Schaltsekunde (:60) und Daten vor 1972 sind ausdruecklich nicht unterstuetzt.
    """
    versatz = _tt_minus_utc_s(jahr, monat, tag)
    if (not isinstance(stunde, int) or not 0 <= stunde < 24
            or not isinstance(minute, int) or not 0 <= minute < 60
            or not math.isfinite(sekunde) or not 0 <= sekunde < 60):
        raise ValueError("Uhrzeit ungueltig: 00:00:00 bis vor 24:00:00, keine :60-Eingabe")
    if monat <= 2:
        jahr, monat = jahr - 1, monat + 12
    a = jahr // 100
    b = 2 - a + a // 4
    jd = math.floor(365.25 * (jahr + 4716)) + math.floor(30.6001 * (monat + 1)) + tag + b - 1524.5
    return jd + (stunde + minute / 60 + sekunde / 3600) / 24 + versatz / SEKUNDEN_PRO_TAG


def jd_ut1_aus_tt(jd_tt: float) -> float:
    jahr = 2000 + (jd_tt - 2451545.0) / 365.25
    return jd_tt - delta_t(jahr) / SEKUNDEN_PRO_TAG


def erdrotationswinkel(jd_ut1: float) -> float:
    """ERA in Umlaeufen, aufsummiert (nicht modulo 1), IAU 2000."""
    du = jd_ut1 - 2451545.0
    return 0.7790572732640 + 1.00273781191135448 * du


def praezession_ra(jd_tt: float) -> float:
    """Kegel: aufgelaufene Praezession in Rektaszension, in Umlaeufen (GMST - ERA, IAU 2006)."""
    t = (jd_tt - 2451545.0) / 36525.0
    bogensek = 0.014506 + t * (4612.156534 + t * (1.3915817 + t * (-0.00000044 + t * (-0.000029956 - 0.0000000368 * t))))
    return bogensek / 1296000.0


def nutation(jd_tt: float) -> Tuple[float, float]:
    """Pendeln: Nutation in Laenge und Schiefe in Bogensekunden (Kurzreihe nach Meeus, ~0,5'')."""
    t = (jd_tt - 2451545.0) / 36525.0
    om = math.radians(125.04452 - 1934.136261 * t)
    l_s = math.radians(280.4665 + 36000.7698 * t)
    l_m = math.radians(218.3165 + 481267.8813 * t)
    dpsi = -17.20 * math.sin(om) - 1.32 * math.sin(2 * l_s) - 0.23 * math.sin(2 * l_m) + 0.21 * math.sin(2 * om)
    deps = 9.20 * math.cos(om) + 0.57 * math.cos(2 * l_s) + 0.10 * math.cos(2 * l_m) - 0.09 * math.cos(2 * om)
    return dpsi, deps


def schiefe_mittel(jd_tt: float) -> float:
    """Mittlere Schiefe der Ekliptik in Grad (IAU 2006): halber Oeffnungswinkel des Praezessionskegels."""
    t = (jd_tt - 2451545.0) / 36525.0
    bogensek = 84381.406 + t * (-46.836769 + t * (-0.0001831 + t * (0.00200340 + t * (-0.000000576 - 0.0000000434 * t))))
    return bogensek / 3600.0


def jd_ut1_aus_utc(jahr: int, monat: int, tag: int, stunde: int = 0, minute: int = 0, sekunde: float = 0.0,
                   dut1_s: Optional[float] = None) -> float:
    """Buergerliche Zeit UTC -> JD UT1. Ab 2027 waechst UT1 - UTC ohne Schaltsekunden (bis 3600 s
    zulaessig). dut1_s = gemessenes UT1 - UTC (IERS Bulletin A); ohne Angabe gilt die definierte
    Drehung: UT1 = TT - Delta T (delta_t). TT-UTC wird datumsabhaengig
    aus derselben historischen Tabelle wie jd_tt_aus_utc berechnet."""
    jd_tt = jd_tt_aus_utc(jahr, monat, tag, stunde, minute, sekunde)
    if dut1_s is None:
        return jd_ut1_aus_tt(jd_tt)
    return jd_tt - (_tt_minus_utc_s(jahr, monat, tag) - dut1_s) / SEKUNDEN_PRO_TAG


def sternzeit(jd_tt: float, scheinbar: bool = True, jd_ut1: Optional[float] = None) -> float:
    """Greenwich-Sternzeit in Umlaeufen, aufsummiert: Drehung + Kegel (+ Pendeln).
    jd_ut1 optional; sonst aus jd_tt ueber Delta T."""
    jd_u = jd_ut1_aus_tt(jd_tt) if jd_ut1 is None else jd_ut1
    st = erdrotationswinkel(jd_u) + praezession_ra(jd_tt)
    if scheinbar:
        dpsi, deps = nutation(jd_tt)
        eps = math.radians(schiefe_mittel(jd_tt) + deps / 3600.0)
        st += dpsi * math.cos(eps) / 1296000.0
    return st


@dataclass(frozen=True)
class Drehkoordinate:
    umlauf: int        # Sternumlaeufe (Sterntage) seit JD 2451545 UT1, ganzzahlig
    zyklus: int        # 0..767
    tick: int          # 0..65
    quant: int         # 0..22
    rest: float        # Rest in Dreh-Quanten, |rest| <= 1/2


def drehkoordinate(t_q: int, laenge_grad: float = 0.0, scheinbar: bool = True) -> Drehkoordinate:
    """Ortssternzeit eines System-Zeitpunkts auf dem Raster 768 x 66 x 23 pro Umlauf;
    gerundet wird die aufsummierte Sternzeit, der Rest bleibt als Zustand erhalten."""
    st = sternzeit(jd_tt_aus_systemzeit(t_q), scheinbar) + laenge_grad / 360.0
    umlauf = math.floor(st)
    x = (st - umlauf) * DREH_Q_PRO_UMLAUF
    k = math.floor(x + 0.5)
    rest = x - k
    if k == DREH_Q_PRO_UMLAUF:
        umlauf, k = umlauf + 1, 0
    zyklus, r = divmod(k, 66 * 23)
    tick, quant = divmod(r, 23)
    return Drehkoordinate(umlauf, zyklus, tick, quant, rest)


HAUSSYSTEME = ("placidus", "porphyrius", "gleich", "ganzzeichen")


def haeuser(jd_tt: float, breite_grad: float, laenge_grad: float, system: str = "placidus",
            scheinbar: bool = True, jd_ut1: Optional[float] = None) -> Dict[str, object]:
    """Aszendent, MC und die 12 Haeuserspitzen (tropische ekliptikale Laenge in Grad).
    breite/laenge geografisch, Ost positiv. jd_ut1 optional (sonst aus jd_tt ueber Delta T)."""
    if system not in HAUSSYSTEME:
        raise ValueError(f"Haussystem: {HAUSSYSTEME}")
    eps_g = schiefe_mittel(jd_tt)
    if scheinbar:
        eps_g += nutation(jd_tt)[1] / 3600.0
    eps, phi = math.radians(eps_g), math.radians(breite_grad)
    ramc = math.radians((sternzeit(jd_tt, scheinbar, jd_ut1) * 360.0 + laenge_grad) % 360.0)
    norm = lambda g: g % 360.0
    mc = norm(math.degrees(math.atan2(math.sin(ramc), math.cos(ramc) * math.cos(eps))))
    asc = norm(math.degrees(math.atan2(math.cos(ramc), -(math.sin(ramc) * math.cos(eps) + math.tan(phi) * math.sin(eps)))))
    ic = norm(mc + 180.0)
    spitzen = [0.0] * 13                      # Index 1..12
    if system == "gleich":
        for i in range(1, 13):
            spitzen[i] = norm(asc + 30.0 * (i - 1))
    elif system == "ganzzeichen":
        for i in range(1, 13):
            spitzen[i] = norm(30.0 * math.floor(asc / 30.0) + 30.0 * (i - 1))
    else:
        spitzen[1], spitzen[10], spitzen[4], spitzen[7] = asc, mc, ic, norm(asc + 180.0)
        if system == "porphyrius":
            ost = norm(asc - mc)                 # Bogen MC -> ASC
            unten = norm(ic - asc)               # Bogen ASC -> IC
            spitzen[11], spitzen[12] = norm(mc + ost / 3), norm(mc + 2 * ost / 3)
            spitzen[2], spitzen[3] = norm(asc + unten / 3), norm(asc + 2 * unten / 3)
        else:                                    # Placidus: Zeitdrittelung der Halbboegen
            def spitze(anteil: float, oben: bool, start: float) -> float:
                lam = math.radians(start)
                for _ in range(100):
                    dek = math.asin(math.sin(eps) * math.sin(lam))
                    x = math.tan(phi) * math.tan(dek)
                    if abs(x) >= 1.0:
                        raise ValueError("Placidus ist jenseits der Polarkreise nicht definiert")
                    ad = math.asin(x)                          # Aszensionaldifferenz
                    dsa = math.pi / 2 + ad                     # Tag-Halbbogen
                    nsa = math.pi - dsa                        # Nacht-Halbbogen
                    ra = ramc + anteil * dsa if oben else ramc + math.pi - anteil * nsa
                    neu = math.atan2(math.sin(ra), math.cos(ra) * math.cos(eps))
                    if abs(math.remainder(neu - lam, 2 * math.pi)) < 1e-12:
                        lam = neu
                        break
                    lam = neu
                return norm(math.degrees(lam))
            ost, unten = norm(asc - mc), norm(ic - asc)
            spitzen[11] = spitze(1 / 3, True, mc + ost / 3)
            spitzen[12] = spitze(2 / 3, True, mc + 2 * ost / 3)
            spitzen[2] = spitze(2 / 3, False, asc + unten / 3)
            spitzen[3] = spitze(1 / 3, False, asc + 2 * unten / 3)
        for i, j in ((5, 11), (6, 12), (8, 2), (9, 3)):
            spitzen[i] = norm(spitzen[j] + 180.0)
    return {"asc": asc, "mc": mc, "ramc": math.degrees(ramc), "schiefe": eps_g, "spitzen": spitzen[1:]}


def haeuser_utc(jahr: int, monat: int, tag: int, stunde: int, minute: int, sekunde: float,
                breite_grad: float, laenge_grad: float, system: str = "placidus",
                dut1_s: Optional[float] = None) -> Dict[str, object]:
    """Haeuser fuer eine buergerliche Zeit (UTC): TT aus historischer UTC-Tabelle fuer die langsamen Groessen,
    UT1 aus gemessenem dut1_s oder, ohne Angabe, aus der definierten Drehung."""
    jd_tt = jd_tt_aus_utc(jahr, monat, tag, stunde, minute, sekunde)
    jd_u = jd_ut1_aus_utc(jahr, monat, tag, stunde, minute, sekunde, dut1_s)
    return haeuser(jd_tt, breite_grad, laenge_grad, system, True, jd_u)


def jules(sekunden: float) -> float:
    """Sekunden -> Jules (1 Ju = 69,159 s)."""
    return sekunden / float(JULES_S)


def tierkreis_text(laenge_grad: float) -> str:
    zeichen = ("Widder", "Stier", "Zwillinge", "Krebs", "Loewe", "Jungfrau",
               "Waage", "Skorpion", "Schuetze", "Steinbock", "Wassermann", "Fische")
    g = laenge_grad % 360.0
    i = int(g // 30)
    rest = g - 30 * i
    gr = int(rest)
    mi = (rest - gr) * 60
    return f"{gr:2d}°{mi:05.2f}' {zeichen[i]}"


# ---------------------------------------------------------------------------
# 6b. Mondachse: joe, definierte mittlere Lunation, Mondkoordinate
# ---------------------------------------------------------------------------
#
# Dritte Zaehlachse neben Jahres- und Drehachse. Die Lunation wird geteilt wie der reine Tag
# und wie der Sternumlauf: 1 Lunation = 768 Mondzyklen x 66 Mondticks x 23 joe.
# 1 joe = 1/1 165 824 der mittleren Elongation Mond - Sonne (360 Grad), also 1,11166''.
# Seine mittlere Dauer in q ist die Laenge des synodischen Monats in Tagen (29,530589 q):
# joe : q = synodischer Monat : Tag.
# Geglaetteter Verlauf (Natur): mittlere Mondphasen nach Meeus (1998), Gl. 49.1 (JDE in TT).
# Bis jj beobachtet, ab jj definiert:
#   Phase bei jj   MOND_PHI0 ganze joe nach dem mittleren Neumond
#   Zeit            nu(x) = (MOND_A x + MOND_G x^2) / 23^4 q, x = Lunationen ab jj
#   Grenzen         joe m (ab jj) beginnt bei round(nu(m / 1 165 824)); Lunation k beginnt
#                   bei m = k * 1 165 824 - MOND_PHI0. Jede Grenze liegt hoechstens q/2 neben nu.
# Phase 0 ist der mittlere Neumond (nicht jj): so bleiben Phasen und Finsternisbezuege ganzzahlig
# (Viertel 291 456, Vollmond 582 912, letztes Viertel 874 368 joe).

JOE_PRO_LUNATION = 768 * 66 * 23          # 1 165 824 joe pro Lunation
MOND_D = 23 ** 4                             # 279 841
MOND_A, MOND_G, MOND_PHI0 = 9634217446503, 32, 65331
MEEUS_PHASEN = (2451550.09766, 29.530588861, 0.00015437, -0.000000150, 0.00000000073)
MEEUS_K_PRO_JH = 1236.85                     # Lunationen pro julianischem Jahrhundert (Meeus 49)
# Mittlere Monatslaengen J2000 in Tagen (Meeus 1998, nach Chapront ELP-2000/82)
MONAT_SYNODISCH, MONAT_DRAKONITISCH, MONAT_ANOMALISTISCH = 29.530588861, 27.212220817, 27.554549878
JAHR_ANOMALISTISCH = 365.259636
# Periodische Terme der wahren Neumonde, Argumente als ganzzahlige Kombination (M', M, F)
MONDTERME = (("Mondanomalie M'", 1, 0, 0), ("Sonnenanomalie M", 0, 1, 0), ("2 M'", 2, 0, 0),
             ("2 F (Knotenabstand)", 0, 0, 2), ("M' - M (Apsidenumlauf)", 1, -1, 0),
             ("M' + M", 1, 1, 0), ("2 M", 0, 2, 0), ("3 M'", 3, 0, 0))
FINSTERNISZYKLEN = (("Tritos", 135), ("Saros", 223), ("Meton", 235), ("Inex", 358), ("Exeligmos", 669))


def mittlere_mondphase_jde(k: float) -> float:
    """JDE (TT) der mittleren Mondphase k nach Meeus Gl. 49.1; k ganz = Neumond, k + 1/2 = Vollmond,
    k = 0 ist der Neumond vom 6. Januar 2000."""
    c0, c1, c2, c3, c4 = MEEUS_PHASEN
    t = k / MEEUS_K_PRO_JH
    return c0 + c1 * k + t * t * (c2 + t * (c3 + t * c4))


def mondphase_k(jd_tt: float) -> float:
    """Umkehrung von mittlere_mondphase_jde: mittlere Phase k (Lunationen seit 6. Januar 2000)."""
    c0, c1, c2, c3, c4 = MEEUS_PHASEN
    k = (jd_tt - c0) / c1
    for _ in range(8):
        t = k / MEEUS_K_PRO_JH
        k -= (mittlere_mondphase_jde(k) - jd_tt) / (c1 + t * (2 * c2 + t * (3 * c3 + 4 * c4 * t)) / MEEUS_K_PRO_JH)
    return k


@dataclass(frozen=True)
class Mondkoordinate:
    lunation: int      # 0 = Lunation, in der jj liegt (beginnt mit dem definierten mittleren Neumond)
    zyklus: int        # Mondzyklus 0..767
    tick: int          # Mondtick 0..65
    joe: int           # joe 0..22 (1 joe = 1/1 165 824 Lunation)
    q: int             # q seit Beginn des joe (0..29)

    @property
    def phase(self) -> int:
        """joe seit dem mittleren Neumond, 0..1 165 823."""
        return (self.zyklus * 66 + self.tick) * 23 + self.joe

    def text(self) -> str:
        return (f"Lunation {self.lunation}, Mondzyklus {self.zyklus}, Mondtick {self.tick}, "
                f"joe {self.joe}, q {self.q}")


class Mondachse:
    """Definierte Mondachse ab jj (siehe Abschnittskopf). Alle Grenzen exakt ganzzahlig."""

    def __init__(self, s: Struktur = Struktur(), a: int = MOND_A, g: int = MOND_G,
                 phi0: int = MOND_PHI0, d: int = MOND_D) -> None:
        self.s, self.a, self.g, self.phi0, self.d = s, a, g, phi0, d
        self.L = JOE_PRO_LUNATION

    def soll(self, x) -> F:
        """Exakter Zeitpunkt (q ab jj) der Phase PHI0 + 1 165 824 x joe."""
        x = F(x)
        return (self.a * x + self.g * x * x) / self.d

    def lunation_q(self, x) -> F:
        """Momentane mittlere Lunation in q (Ableitung von nu) bei x Lunationen ab jj."""
        return (self.a + 2 * self.g * F(x)) / self.d

    def grenze(self, m: int) -> int:
        """Beginn des joe m (gezaehlt ab jj, m = 0 bei jj) in ganzen q, exakt gerundet."""
        num = self.a * m * self.L + self.g * m * m
        den = self.d * self.L * self.L
        return (2 * num + den) // (2 * den)

    def neumond(self, k: int) -> int:
        """Beginn der Lunation k (definierter mittlerer Neumond) in q ab jj."""
        return self.grenze(k * self.L - self.phi0)

    def lunationslaenge(self, k: int) -> int:
        return self.neumond(k + 1) - self.neumond(k)

    def _x(self, t: float) -> float:
        a, g, d = self.a, self.g, self.d
        return (2.0 * t * d / a) / (1.0 + math.sqrt(1.0 + 4.0 * g * t * d / (a * a)))   # stabile Wurzel

    def joe_von(self, t: int) -> int:
        """Index m des joe, in dem der Zeitpunkt t (q ab jj) liegt."""
        m = math.floor(self._x(t) * self.L)
        while self.grenze(m) > t:
            m -= 1
        while self.grenze(m + 1) <= t:
            m += 1
        return m

    def koordinate(self, t: int) -> Mondkoordinate:
        m = self.joe_von(t)
        lun, p = divmod(m + self.phi0, self.L)
        zyklus, r = divmod(p, 66 * 23)
        tick, joe = divmod(r, 23)
        return Mondkoordinate(lun, zyklus, tick, joe, t - self.grenze(m))

    def zeitpunkt(self, mk: Mondkoordinate) -> int:
        return self.grenze(mk.lunation * self.L + mk.phase - self.phi0) + mk.q

    def elongation_grad(self, t: float) -> float:
        """Definierte mittlere Elongation in Grad (0 = mittlerer Neumond) zum Zeitpunkt t (q ab jj)."""
        return ((self.phi0 / self.L + self._x(t)) * 360.0) % 360.0


def mond_herleiten(jahre: int = JAHRE_HORIZONT, s: Struktur = Struktur()) -> Optional[Dict[str, object]]:
    """Herleitung der Mondachse aus Meeus Gl. 49.1:
    1. mittlere Phase bei jj auf ganze joe runden (PHI0),
    2. Verlauf der Phasenzeiten ueber den Horizont, durch jj verschoben,
    3. Beschraenkte Minimax-Naehersuche fuer nu(x) = (A x + G x^2) / 23^4
       mit ganzen A, G; kein globaler ganzzahliger Optimalitaetsnachweis.
    None ohne NumPy."""
    try:
        import numpy as np
    except ImportError:
        return None
    L, d, qs = JOE_PRO_LUNATION, MOND_D, float(s.q_s)
    jd0 = float(EPOCHE_JD_TT)
    k0 = mondphase_k(jd0)
    K0 = math.floor(k0)
    phi0 = round((k0 - K0) * L)
    basis = K0 + phi0 / L
    t_ref0 = (mittlere_mondphase_jde(basis) - jd0) * SEKUNDEN_PRO_TAG / qs      # eingefrorener Versatz
    n = math.ceil(jahre * 12.3683) + 2
    xs = np.unique(np.concatenate([np.arange(1, n + 1) - phi0 / L, np.linspace(0.0, n, 20001)[1:]]))
    tr = np.array([(mittlere_mondphase_jde(basis + x) - jd0) * SEKUNDEN_PRO_TAG / qs for x in xs]) - t_ref0
    alpha, gamma = np.linalg.lstsq(np.vstack([xs, xs * xs]).T, tr, rcond=None)[0]

    def maxabw(a: int, g: int) -> float:
        return float(np.max(np.abs((a * xs + g * xs * xs) / d - tr)))

    ergebnisse = []
    for g in range(math.floor(gamma * d) - 3, math.ceil(gamma * d) + 4):
        lo, hi = round(alpha * d) - 400000, round(alpha * d) + 400000
        while hi - lo > 2:
            m1, m2 = lo + (hi - lo) // 3, hi - (hi - lo) // 3
            if maxabw(m1, g) <= maxabw(m2, g):
                hi = m2
            else:
                lo = m1
        a = min(range(lo, hi + 1), key=lambda aa: maxabw(aa, g))
        ergebnisse.append((maxabw(a, g), a, g))
    w, a, g = min(ergebnisse)
    return {"k0": k0, "K0": K0, "phi0": phi0, "a": a, "g": g, "max_abw_s": w * qs,
            "versatz_s": t_ref0 * qs, "lunationen": n}


def neumonde_natur(anzahl: int, achse: Optional["Mondachse"] = None) -> Optional[List[float]]:
    """Wahre Neumonde (PyEphem: scheinbare Konjunktion in Laenge) der Lunationen 0..anzahl-1,
    in q ab jj. Gesucht wird je ab 2 Tage vor dem definierten Neumond (Abstand stets < 15 h)."""
    try:
        import ephem
    except ImportError:
        return None
    achse = achse or Mondachse()
    qs = float(achse.s.q_s)
    dublin = 2415020.0
    jd0_tt, jd0_utc = float(EPOCHE_JD_TT), float(EPOCHE_JD_UTC)
    aus = []
    for k in range(anzahl):
        start = jd0_utc + achse.neumond(k) * qs / SEKUNDEN_PRO_TAG - 2.0
        d = ephem.next_new_moon(ephem.Date(start - dublin))
        jd_tt = float(d) + dublin + ephem.delta_t(d) / SEKUNDEN_PRO_TAG
        aus.append((jd_tt - jd0_tt) * SEKUNDEN_PRO_TAG / qs)
    return aus


def mond_natur_minus_definition(jahre: int = JAHRE_HORIZONT, achse: Optional["Mondachse"] = None
                                ) -> Optional[Dict[str, object]]:
    """Natur - Definition an den Neumonden: wahre Neumonde minus nu, Zerlegung in die MONDTERME
    (Frequenzen je Lunation; die Abtastung einmal pro Lunation faltet M' auf 411,78 Tage)."""
    try:
        import numpy as np
    except ImportError:
        return None
    achse = achse or Mondachse()
    n = math.ceil(jahre * 12.3683)
    nat = neumonde_natur(n, achse)
    if nat is None:
        return None
    qs = float(achse.s.q_s)
    k = np.arange(n, dtype=float)
    soll = np.array([float(achse.soll(F(int(i) * achse.L - achse.phi0, achse.L))) for i in range(n)])
    r = (np.array(nat) - soll) * qs / 3600.0                       # Stunden
    f = {"M1": MONAT_SYNODISCH / MONAT_ANOMALISTISCH - 1.0, "M": MONAT_SYNODISCH / JAHR_ANOMALISTISCH,
         "F": MONAT_SYNODISCH / MONAT_DRAKONITISCH - 1.0}
    spalten, terme = [np.ones(n), k / n], []
    for name, a1, a2, a3 in MONDTERME:
        fr = a1 * f["M1"] + a2 * f["M"] + a3 * f["F"]
        spalten += [np.sin(2 * np.pi * fr * k), np.cos(2 * np.pi * fr * k)]
        terme.append((name, MONAT_SYNODISCH / abs(fr)))
    X = np.vstack(spalten).T
    c, *_ = np.linalg.lstsq(X, r, rcond=None)
    rest = r - X @ c
    amp = [(name, periode, float(np.hypot(c[2 + 2 * i], c[3 + 2 * i]))) for i, (name, periode) in enumerate(terme)]
    koeff_terme = []
    for i, (name, a1, a2, a3) in enumerate(MONDTERME):
        f_wahr = a1 * MONAT_SYNODISCH / MONAT_ANOMALISTISCH + a2 * f["M"] + a3 * MONAT_SYNODISCH / MONAT_DRAKONITISCH
        koeff_terme.append((name, f_wahr, float(c[3 + 2 * i]), float(c[2 + 2 * i])))   # (cos, sin)
    return {"r_h": r, "lunation0_h": float(r[0]), "mittel_min": float(r.mean()) * 60,
            "min_h": float(r.min()), "max_h": float(r.max()), "rms_h": float(np.sqrt(np.mean(r * r))),
            "terme": amp, "rest_rms_min": float(rest.std()) * 60, "rest_max_min": float(np.abs(rest).max()) * 60,
            "trend_min": float(c[1]) * 60, "anzahl": n, "koeff_terme": koeff_terme,
            "konst_h": float(c[0]), "trend_h": float(c[1])}


def neumonde_je_jahr(achse: "Mondachse", anker: "DefinierterAnker", jahre: int = JAHRE_HORIZONT) -> List[int]:
    """Anzahl definierter Neumonde in jedem Systemjahr n (Jahresanfaenge aus dem Sonnenanker)."""
    starts = [anker.runde_bei(n, 1) for n in range(jahre + 1)]
    kmax = math.ceil(jahre * 12.3683) + 2
    nm = [achse.neumond(k) for k in range(1, kmax + 1)]
    return [bisect_right(nm, starts[n + 1] - 1) - bisect_right(nm, starts[n] - 1) for n in range(jahre)]


def kettenbruch(x: F, glieder: int = 10) -> List[int]:
    cf = []
    for _ in range(glieder):
        a = math.floor(x)
        cf.append(a)
        if x == a:
            break
        x = 1 / (x - a)
    return cf


def naeherungsbrueche(cf: Sequence[int]) -> List[F]:
    p0, p1, q0, q1 = 1, cf[0], 0, 1
    aus = [F(p1, q1)]
    for a in cf[1:]:
        p0, p1 = p1, a * p1 + p0
        q0, q1 = q1, a * q1 + q0
        aus.append(F(p1, q1))
    return aus


def finsterniszyklen(jahr_tage: float) -> List[Tuple[str, int, float, float, float, float]]:
    """Bekannte Finsterniszyklen: (Name, Lunationen, Tage, Systemjahre, Knotenversatz in Grad,
    Anomalieversatz in Grad). Knotenversatz: Abstand von F zum naechsten Vielfachen von 180 Grad."""
    aus = []
    for name, n in FINSTERNISZYKLEN:
        tage = n * MONAT_SYNODISCH
        dra, ano = tage / MONAT_DRAKONITISCH, tage / MONAT_ANOMALISTISCH
        knoten = (2 * dra - round(2 * dra)) * 180.0
        anomalie = (ano - round(ano)) * 360.0
        aus.append((name, n, tage, tage / jahr_tage, knoten, anomalie))
    return aus


# ---------------------------------------------------------------------------
# 6c. Polachse: Iris (Ir)
# ---------------------------------------------------------------------------
#
# Vierte Achse: der Pol der Erdachse auf der Erdkruste (Polbewegung). Der IERS gibt x_p, y_p in
# Bogensekunden; komplex m = x_p - i y_p. Klassenraster 1 Iris (Ir) = 1''/299 mit 299 = 13 x 23,
# also 3,3445 mas oder 10,33 cm am Boden. Die Klasse eines Pols ist das Feld (round(299 x), round(299 y)),
# eine Gausssche ganze Zahl. Die Polbewegung ist nicht definierbar (Anregung durch Atmosphaere, Ozean
# und Wasserhaushalt): sie wird gemessen und als Wahrscheinlichkeit je Feld vorhergesagt.
# Vorhersagemodell (einfach): mittlerer Pol linear ueber 10 Jahre, Jahres- und Halbjahresellipse und
# Chandler-Kreise (433 d) ueber die letzten 3 Jahre; der aktuelle Rest klingt mit 120 d ab. Die Streuung
# je Horizont stammt aus Rueckrechnungen 2010-2026 mit der Reihe IERS 20 C04.

IRIS_PRO_BOGENSEKUNDE = 13 * 23            # 299 Ir pro Bogensekunde
POL_FENSTER_TAGE = 1096                    # Anpassung ueber 3 Jahre
POL_DRIFT_TAGE = 3652                      # mittlerer Pol ueber 10 Jahre
POL_CHANDLER_TAGE = 433.0
POL_REST_TAU_TAGE = 120.0
POL_HORIZONTE = (1, 7, 30, 90, 180, 365, 1000)
MJD_JJ = float(EPOCHE_JD_UTC) - 2400000.5  # jj als MJD (UTC)


def iris_mas() -> float:
    """1 Ir in Millibogensekunden."""
    return 1000.0 / IRIS_PRO_BOGENSEKUNDE


def iris_cm() -> float:
    """1 Ir als Strecke am Erdboden (mittlerer Radius 6 371 km) in cm."""
    return 6371000.0 * math.pi / 648000.0 / IRIS_PRO_BOGENSEKUNDE * 100.0


def pol_feld(x_bogensek: float, y_bogensek: float) -> Tuple[int, int]:
    """Iris-Feld (Klasse) eines Pols: ganzzahlige Koordinaten in Ir."""
    return (math.floor(x_bogensek * IRIS_PRO_BOGENSEKUNDE + 0.5),
            math.floor(y_bogensek * IRIS_PRO_BOGENSEKUNDE + 0.5))


def pol_daten():
    """IERS 20 C04 (taeglich, 0h UTC) aus dem Paket astropy-iers-data: (mjd, x, y) mit x, y in
    Bogensekunden. None, wenn NumPy oder das Paket fehlt (pip install astropy-iers-data)."""
    try:
        import numpy as np
        import astropy_iers_data as aid
    except ImportError:
        return None
    d = np.loadtxt(aid.IERS_B_FILE, comments="#", usecols=(4, 5, 6))
    return d[:, 0], d[:, 1], d[:, 2]


def _pol_kreise(np, tt):
    spalten = []
    for periode in (365.2422, 182.6211, POL_CHANDLER_TAGE):
        w = 2 * np.pi * tt / periode
        spalten += [np.exp(1j * w), np.exp(-1j * w)]          # je ein Kreis vorwaerts und rueckwaerts
    return np.vstack(spalten).T


def pol_vorhersage(daten, i0: int, mjd_ziel):
    """Mittlere Vorhersage des Pols (komplex m = x - i y in Bogensekunden) ab Tag i0 fuer mjd_ziel:
    1. mittlerer Pol linear ueber 10 Jahre (zusammen mit den Kreisen angepasst),
    2. Jahres-, Halbjahres- und Chandler-Kreise neu ueber die letzten 3 Jahre,
    3. der Rest am Tag i0 klingt mit 120 Tagen ab."""
    import numpy as np
    t, x, y = daten
    m = x - 1j * y
    s = slice(max(0, i0 - POL_DRIFT_TAGE), i0 + 1)
    u = (t[s] - t[i0]) / 365.25
    A = np.hstack([np.vstack([np.ones_like(u), u]).T, _pol_kreise(np, t[s])])
    c, *_ = np.linalg.lstsq(A, m[s], rcond=None)

    def drift(tt):
        return c[0] + c[1] * (tt - t[i0]) / 365.25

    s2 = slice(max(0, i0 - POL_FENSTER_TAGE), i0 + 1)
    B = np.hstack([np.ones((s2.stop - s2.start, 1)), _pol_kreise(np, t[s2])])
    c2, *_ = np.linalg.lstsq(B, m[s2] - drift(t[s2]), rcond=None)

    def modell(tt):
        return drift(tt) + np.hstack([np.ones((len(tt), 1)), _pol_kreise(np, tt)]) @ c2

    r0 = m[i0] - modell(t[i0:i0 + 1])[0]
    ziel = np.atleast_1d(np.asarray(mjd_ziel, dtype=float))
    return modell(ziel) + r0 * np.exp(-(ziel - t[i0]) / POL_REST_TAU_TAGE)


def pol_rueckrechnung(daten, ab_jahr: int = 2010, schritt: int = 15) -> Dict[int, Tuple[float, float, int]]:
    """Rueckrechnung: je Horizont h (Tage) die Streuung sigma_x, sigma_y des Vorhersagefehlers in Ir
    und die Zahl der Faelle. Startpunkte ab ab_jahr alle schritt Tage."""
    import numpy as np
    t, x, y = daten
    m = x - 1j * y
    fehler: Dict[int, List[complex]] = {h: [] for h in POL_HORIZONTE}
    for i0 in range(POL_DRIFT_TAGE, len(t) - 1, schritt):
        if t[i0] < 37665 + 365.25 * (ab_jahr - 1962):
            continue
        hs = [h for h in POL_HORIZONTE if i0 + h < len(t)]
        if not hs:
            break
        vorh = pol_vorhersage(daten, i0, [t[i0 + h] for h in hs])
        for h, v in zip(hs, vorh):
            fehler[h].append(m[i0 + h] - v)
    aus = {}
    for h, e in fehler.items():
        e = np.array(e) * IRIS_PRO_BOGENSEKUNDE
        aus[h] = (float(np.sqrt(np.mean(e.real ** 2))), float(np.sqrt(np.mean(e.imag ** 2))), len(e))
    return aus


def feld_wahrscheinlichkeit(mx: float, my: float, sx: float, sy: float, X: int, Y: int) -> float:
    """Wahrscheinlichkeit des Iris-Felds (X, Y) bei Normalverteilung um (mx, my) mit sx, sy (alles in Ir)."""
    def anteil(mu: float, s: float, k: int) -> float:
        a, b = (k - 0.5 - mu) / (s * math.sqrt(2.0)), (k + 0.5 - mu) / (s * math.sqrt(2.0))
        return 0.5 * (math.erf(b) - math.erf(a))
    return anteil(mx, sx, X) * anteil(my, sy, Y)


def pol_radius(sx: float, sy: float, anteil: float) -> float:
    """Radius in Ir, der den Anteil der Wahrscheinlichkeit enthaelt (isotrope Naeherung)."""
    s = math.sqrt((sx * sx + sy * sy) / 2.0)
    return s * math.sqrt(-2.0 * math.log(1.0 - anteil))


# ---------------------------------------------------------------------------
# 6d. Delta-T-Achse in Jules
# ---------------------------------------------------------------------------
#
# Gemessenes Delta T = TT - UT1 = 32,184 s + (TAI - UTC) - (UT1 - UTC), taeglich ab 1972
# (IERS 20 C04 und Schaltsekundentabelle). Ausgedrueckt in Jules (1 Ju = 69,159 s), gezaehlt in
# Feldern von 1 q. Delta T ist nicht definierbar (Kern, Mantel, Atmosphaere, Gezeiten): gemessen und
# als Wahrscheinlichkeit je Feld vorhergesagt. Modell: Steigung und Jahres-, Halbjahres-, Monats- und
# Halbmonatsterm aus dem letzten Jahr, fortgeschrieben ab dem letzten Messwert.

DT_FENSTER_TAGE = 365
DT_PERIODEN = (365.2422, 182.6211, 27.5545, 13.6608)       # Tage


def dt_daten():
    """(mjd, delta_t in s) taeglich ab 1972-01-01; None ohne NumPy oder astropy-iers-data."""
    try:
        import os
        import numpy as np
        import astropy_iers_data as aid
    except ImportError:
        return None
    tab = [z.split() for z in open(os.path.join(os.path.dirname(aid.IERS_B_FILE), "Leap_Second.dat"))
           if z.strip() and not z.startswith("#")]
    sprung = np.array([[float(a[0]), float(a[4])] for a in tab])          # MJD, TAI - UTC
    d = np.loadtxt(aid.IERS_B_FILE, comments="#", usecols=(4, 7))
    t, dut1 = d[:, 0], d[:, 1]
    s = t >= 41317.0
    t, dut1 = t[s], dut1[s]
    tai_utc = sprung[np.searchsorted(sprung[:, 0], t, side="right") - 1, 1]
    return t, 32.184 + tai_utc - dut1


def dt_feld(dt_s: float, s: Struktur = Struktur()) -> int:
    """Feld von Delta T in ganzen q."""
    return runden(F(dt_s) / s.q_s)


def _dt_matrix(np, tt, t0):
    u = (tt - t0) / 365.25
    spalten = [np.ones_like(tt), u]
    for periode in DT_PERIODEN:
        w = 2 * np.pi * tt / periode
        spalten += [np.cos(w), np.sin(w)]
    return np.vstack(spalten).T


def dt_vorhersage(daten, i0: int, mjd_ziel):
    """Delta T (s) ab Tag i0 fuer mjd_ziel: Modell aus dem letzten Jahr, durch den letzten Messwert."""
    import numpy as np
    t, dt = daten
    s = slice(max(0, i0 - DT_FENSTER_TAGE), i0 + 1)
    A = _dt_matrix(np, t[s], t[i0])
    c, *_ = np.linalg.lstsq(A, dt[s], rcond=None)
    r0 = dt[i0] - A[-1] @ c
    ziel = np.atleast_1d(np.asarray(mjd_ziel, dtype=float))
    return _dt_matrix(np, ziel, t[i0]) @ c + r0


def dt_rueckrechnung(daten, ab_jahr: int = 2010, schritt: int = 15) -> Dict[int, Tuple[float, int]]:
    """Rueckrechnung: je Horizont die Streuung des Vorhersagefehlers in s und die Zahl der Faelle."""
    import numpy as np
    t, dt = daten
    fehler: Dict[int, List[float]] = {h: [] for h in POL_HORIZONTE}
    for i0 in range(DT_FENSTER_TAGE, len(t) - 1, schritt):
        if t[i0] < 51544.5 + (ab_jahr - 2000) * 365.25:
            continue
        hs = [h for h in POL_HORIZONTE if i0 + h < len(t)]
        if not hs:
            break
        v = dt_vorhersage(daten, i0, [t[i0 + h] for h in hs])
        for h, x in zip(hs, v):
            fehler[h].append(dt[i0 + h] - x)
    return {h: (float(np.sqrt(np.mean(np.square(e)))), len(e)) for h, e in fehler.items()}


def dt_feld_wahrscheinlichkeit(mu_s: float, sigma_s: float, k: int, s: Struktur = Struktur()) -> float:
    """Wahrscheinlichkeit, dass Delta T im Feld k (ganze q) liegt, bei Normalverteilung N(mu, sigma)."""
    q = float(s.q_s)
    a, b = ((k - 0.5) * q - mu_s) / (sigma_s * math.sqrt(2.0)), ((k + 0.5) * q - mu_s) / (sigma_s * math.sqrt(2.0))
    return 0.5 * (math.erf(b) - math.erf(a))


# ---------------------------------------------------------------------------
# 6e. Epizykel-Achsen: Platons Kreise als ganzzahlige Zaehler
# ---------------------------------------------------------------------------
#
# Jeder periodische Term von Natur - Definition ist eine gleichfoermige Kreisbewegung. Seine Phase
# wird wie jede Achse auf dem Raster 1 165 824 pro Umlauf gezaehlt, durch kumuliertes Runden:
#   p(n) = round(L * (phi0 + f * n)),  Rest <= 1/2 Rasterpunkt (quantisch irrelevant),
# mit der physikalischen Frequenz f (Umlaeufe pro Jahr bzw. pro Lunation). Der Beitrag ist
# A * cos(2 pi p(n) / L). Sonne: 8 Terme an den Durchgaengen von lambda0; Mond: 8 Terme an den Neumonden.

EPIZYKEL_L = 768 * 66 * 23


@dataclass(frozen=True)
class Epizykel:
    name: str
    f: F                # Umlaeufe pro Schritt (Jahr bzw. Lunation), exakt als Bruch
    phi0: F             # Anfangsphase in Umlaeufen
    amplitude: float    # in der Einheit der Reihe (q bei der Sonne, Stunden beim Mond)

    def phase(self, n: int) -> int:
        """Ganzzahlige Phase auf dem Raster, kumuliert gerundet."""
        return runden(EPIZYKEL_L * (self.phi0 + self.f * n)) % EPIZYKEL_L

    def wert(self, n: int) -> float:
        return self.amplitude * math.cos(2 * math.pi * self.phase(n) / EPIZYKEL_L)


def _epizykel(name: str, f_wahr: float, a_cos: float, b_sin: float) -> Epizykel:
    amp = math.hypot(a_cos, b_sin)
    phi = -math.atan2(b_sin, a_cos) / (2 * math.pi)            # a cos x + b sin x = A cos(x - atan2(b, a))
    return Epizykel(name, F(f_wahr).limit_denominator(10 ** 12), F(phi).limit_denominator(10 ** 12), amp)


def epizykel_sonne() -> Optional[Dict[str, object]]:
    """Die 8 Sonnenterme als Epizykel-Achsen und der Vergleich an den 967 Durchgaengen von lambda0."""
    h = herleitung()
    if h is None:
        return None
    import numpy as np
    achsen = [_epizykel(f"{name} h={hh}", fw, a, b) for name, hh, fw, a, b in h["koeff_terme"]]
    natur, glatt = np.asarray(h["natur_q"]), np.asarray(h["glatt_minus_anker_q"])
    q = float(Struktur().q_s)
    summe = np.array([sum(e.wert(n) for e in achsen) for n in range(len(natur))])
    rest = (natur - glatt - summe) * q / 60
    ohne = (natur - glatt) * q / 60
    return {"achsen": achsen, "rest_rms_min": float(np.sqrt(np.mean((rest - rest.mean()) ** 2))),
            "rest_max_min": float(np.max(np.abs(rest - rest.mean()))), "ohne_rms_min": float(np.std(ohne)),
            "anzahl": len(natur)}


def epizykel_mond() -> Optional[Dict[str, object]]:
    """Die 8 Mondterme als Epizykel-Achsen und der Vergleich an den wahren Neumonden."""
    nd = mond_natur()
    if nd is None:
        return None
    import numpy as np
    achsen = [_epizykel(name, fw, a, b) for name, fw, a, b in nd["koeff_terme"]]
    r = np.asarray(nd["r_h"])
    n = len(r)
    k = np.arange(n)
    summe = np.array([sum(e.wert(int(i)) for e in achsen) for i in range(n)])
    rest = (r - nd["konst_h"] - nd["trend_h"] * k / n - summe) * 60
    return {"achsen": achsen, "rest_rms_min": float(np.std(rest)), "rest_max_min": float(np.max(np.abs(rest))),
            "ohne_rms_min": float(np.sqrt(np.mean(r * r))) * 60, "anzahl": n}


# ---------------------------------------------------------------------------
# 6f. Finsternisse (Knotenachse) und Gezeiten
# ---------------------------------------------------------------------------
#
# Knotenachse: Argument der Breite F des Mondes bei den mittleren Syzygien (Meeus 49), auf dem Raster
# 1 165 824 pro Umlauf gezaehlt. Eine Finsternis ist nur moeglich, wenn F nahe 0 oder 180 Grad liegt;
# die Schwellen werden an den wahren Syzygien (PyEphem, Breite des Mondes, Parallaxe, Radien) bestimmt.
# Gezeiten: Im idealen SI-Tagesraster ist S2 = 582 912 q. gezeiten() koppelt S2
# jedoch an UT1 aus dem Delta-T-Modell und ist deshalb nicht exakt SI-periodisch.
# Spring-Nipp-Zyklus = halbe definierte Lunation = 582 912 joe; ideales M2 ist
# die doppelte Schwebung von q- und joe-Raster: f_M2 = (2/L) (1/q - 1/joe).

MEEUS_F = (160.7108, 390.67050284, -0.0016118, -0.00000227, 0.000000011)


def knoten_f_grad(k_meeus: float) -> float:
    """Argument der Breite F (Grad) bei der mittleren Phase k nach Meeus Gl. 49."""
    c0, c1, c2, c3, c4 = MEEUS_F
    t = k_meeus / MEEUS_K_PRO_JH
    return (c0 + c1 * k_meeus + t * t * (c2 + t * (c3 + t * c4))) % 360.0


def knoten_index(k_meeus: float) -> int:
    """F auf dem Raster 1 165 824 pro Umlauf (gerundet)."""
    return runden(F(knoten_f_grad(k_meeus)).limit_denominator(10 ** 9) * EPIZYKEL_L / 360) % EPIZYKEL_L


def knotenabstand_grad(k_meeus: float) -> float:
    """Abstand von F zum naechsten Knoten (0 oder 180 Grad)."""
    f = knoten_f_grad(k_meeus) % 180.0
    return min(f, 180.0 - f)


def finsternisse_natur(jahre: int = 200) -> Optional[List[Tuple[float, str, float, bool, bool]]]:
    """Wahre Syzygien ab Lunation 0 ueber 'jahre' Jahre (PyEphem): (k_meeus, Art, Knotenabstand der
    mittleren Phase, Finsternis ja/nein, zentral/Kernschatten ja/nein)."""
    try:
        import ephem
    except ImportError:
        return None
    ma = Mondachse()
    qs = float(ma.s.q_s)
    dublin = 2415020.0
    erdradius_ae = 6378.137 / 149597870.7
    aus = []
    for k in range(math.ceil(jahre * 12.3683)):
        for art, halb in (("Sonne", 0.0), ("Mond", 0.5)):
            mitte = float(EPOCHE_JD_UTC) + (ma.neumond(k) + halb * float(ma.lunation_q(k))) * qs / SEKUNDEN_PRO_TAG
            such = ephem.next_new_moon if art == "Sonne" else ephem.next_full_moon
            d = such(ephem.Date(mitte - dublin - 2.0))
            mond, sonne = ephem.Moon(d), ephem.Sun(d)
            beta = abs(float(ephem.Ecliptic(mond, epoch=d).lat))
            pi_m, pi_s = math.asin(erdradius_ae / mond.earth_distance), math.asin(erdradius_ae / sonne.earth_distance)
            s_m, s_s = float(mond.radius), float(sonne.radius)
            if art == "Sonne":
                ja = beta < pi_m - pi_s + s_m + s_s
                kern = beta < pi_m - pi_s                                           # Schattenachse trifft die Erde
            else:
                ja = beta < 1.02 * (pi_m + pi_s + s_s) + s_m                       # Halbschatten
                kern = beta < 1.02 * (pi_m + pi_s - s_s) + s_m                      # Kernschatten
            km = MOND_K0 + k + halb
            aus.append((km, art, knotenabstand_grad(km), ja, kern))
    return aus


MOND_K0 = 365                                   # Lunation 0 = Meeus-Lunation 365


def gezeiten(t_q: int, s: Struktur = Struktur()) -> Dict[str, int]:
    """Gezeitenphasen auf dem Raster L zum Zeitpunkt t_q (q ab jj), bezogen auf Greenwich-Mittagszeit:
    S2 = 2 x Sonnenstundenwinkel (UT1 aus dem definierten Delta T), Spring-Nipp = 2 x Elongation,
    M2 = S2 - Spring-Nipp. Spring bei 0, Nipp bei L/2 der Spring-Nipp-Phase.
    Die UT1-S2-Phase hat keine exakt konstante Periode in SI-Sekunden/q."""
    L = EPIZYKEL_L
    jd_tt = jd_tt_aus_systemzeit(t_q, s)
    jd_ut1 = jd_ut1_aus_tt(jd_tt)
    stundenwinkel = jd_ut1 % 1.0                                 # Umlaeufe ab Mittag Greenwich (JD beginnt 12 h)
    s2 = runden(F(2 * stundenwinkel).limit_denominator(10 ** 12) * L) % L
    ma = Mondachse(s)
    sn = (2 * ma.koordinate(t_q).phase) % L
    return {"S2": s2, "spring_nipp": sn, "M2": (s2 - sn) % L}


# ---------------------------------------------------------------------------
# 6g. Platons Frage: Konvergenz der Kreise, Kepler-Ellipsen zum Vergleich
# ---------------------------------------------------------------------------
#
# Platons Frage numerisch: Wie viele gleichfoermige Kreise braucht eine Laenge am Himmel fuer eine
# gegebene Genauigkeit? Grundbewegung = quadratisches Polynom (wie der Anker), dazu K Kreise mit je
# Frequenz, Amplitude und Phase (3 Zahlen je Kreis). Die Frequenzen werden ohne Vorwissen nacheinander
# aus dem Spektrum des Rests gesucht (Hann-Fenster, verfeinert), danach werden alle Kreise gemeinsam
# angepasst (Frequenzanalyse nach Laskar). Vergleich: Kepler-Ellipsen mit linear veraenderlichen
# Elementen (11 Zahlen je Ellipse) an die Orte angepasst, und Ellipse + Kreise fuer den Rest.
# Daten: PyEphem, mittlere Ekliptik und mittleres Aequinoktium des Datums, geometrisch (ohne Aberration
# und Nutation). Aufruf der vollen Rechnung (rund 1,5 min): python3 zyklus23.py platon

PLATON_KOERPER = {"Sonne": (200, 2.0), "Mond": (100, 1.0), "Mars": (200, 2.0)}   # Jahre ab jj, Schritt in Tagen
PLATON_K = 150                                  # Kreise je Kurve
PLATON_GRENZEN = ((3600.0, "1 Grad"), (60.0, "1'"), (10.0, "10\""), (1.0, "1\""))   # RMS in Bogensekunden

KEPLER_START = {   # (a [AE], e, de, I, dI, Knoten, dKnoten, Perihel, dPerihel, L, n) in Grad je julian. Jahrhundert,
    # mittleres Aequinoktium des Datums (Meeus, Tafel 31.A; Mond: Kap. 47)
    "Erde": [1.000001, 0.0167086, -0.000042, 0.0, 0.0, 0.0, 0.0, 102.937348, 1.7195366, 100.466457, 36000.7698278],
    "Mars": [1.523679, 0.0934007, 0.000090, 1.849726, -0.0006011, 49.558093, 0.7720959, 336.060234, 1.8410449,
             355.433000, 19141.6964471],
    "Mond": [0.0025696, 0.0549, 0.0, 5.145, 0.0, 125.0445479, -1934.1362891, 83.3530513, 4069.0137287,
             218.3164477, 481267.8812342]}


def platon_orte(koerper: str, jahre: float, schritt: float):
    """Zeiten t (Tage ab jj) und ekliptikale xy-Orte in AE: 'Sonne' -> Erde heliozentrisch, 'Mars' -> Erde
    und Mars heliozentrisch, 'Mond' -> Mond geozentrisch."""
    import numpy as np
    import ephem
    dublin, jd0 = 2415020.0, float(EPOCHE_JD_UTC)
    t = np.arange(int(jahre * 365.25 / schritt)) * schritt
    namen = {"Sonne": ("Erde",), "Mars": ("Erde", "Mars"), "Mond": ("Mond",)}[koerper]
    orte = {n: np.empty((len(t), 2)) for n in namen}
    sonne, mars, mond = ephem.Sun(), ephem.Mars(), ephem.Moon()
    for i, x in enumerate(t):
        d = ephem.Date(jd0 + x - dublin)
        if "Erde" in orte:
            sonne.compute(d)
            r, b, l = sonne.earth_distance, float(sonne.hlat), float(sonne.hlon)
            orte["Erde"][i] = (r * math.cos(b) * math.cos(l), r * math.cos(b) * math.sin(l))
        if "Mars" in orte:
            mars.compute(d)
            r, b, l = mars.sun_distance, float(mars.hlat), float(mars.hlon)
            orte["Mars"][i] = (r * math.cos(b) * math.cos(l), r * math.cos(b) * math.sin(l))
        if "Mond" in orte:
            mond.compute(d, epoch=d)
            e = ephem.Ecliptic(mond, epoch=d)
            r, b, l = mond.earth_distance, float(e.lat), float(e.lon)
            orte["Mond"][i] = (r * math.cos(b) * math.cos(l), r * math.cos(b) * math.sin(l))
    return t, orte


def platon_laenge(koerper: str, orte):
    """Geozentrische Laenge in Grad, stetig fortgesetzt."""
    import numpy as np
    if koerper == "Sonne":
        x, y = -orte["Erde"][:, 0], -orte["Erde"][:, 1]
    elif koerper == "Mars":
        x, y = orte["Mars"][:, 0] - orte["Erde"][:, 0], orte["Mars"][:, 1] - orte["Erde"][:, 1]
    else:
        x, y = orte["Mond"][:, 0], orte["Mond"][:, 1]
    return np.degrees(np.unwrap(np.arctan2(y, x)))


def platon_konvergenz(t, lam, k_max: int, polster: int = 4, grad: int = 2) -> Dict[str, list]:
    """Kreise nacheinander aus dem Rest. 'tabelle': [(K, RMS ", Maximum ", Periode des K-ten Kreises in Tagen)],
    'kreise': [(Periode in Tagen, Amplitude ")] der Endanpassung in der Reihenfolge des Findens.
    Die gemeinsame Anpassung laeuft als fortgesetzte Orthogonalisierung (Gram-Schmidt, zweifach)."""
    import numpy as np
    n = len(t)
    u = (t - t.mean()) / (t.max() - t.mean())
    grund = np.vstack([u ** j for j in range(grad + 1)]).T
    hann = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(n) / (n - 1))
    nfft = 1 << int(math.ceil(math.log2(n * polster)))
    fgitter = np.fft.rfftfreq(nfft, t[1] - t[0])
    Q = np.empty((n, grad + 1 + 2 * k_max))
    Q[:, :grad + 1] = np.linalg.qr(grund)[0]
    p = grad + 1
    r = lam - Q[:, :p] @ (Q[:, :p].T @ lam)
    aus = [(0, float(np.sqrt(np.mean(r * r))) * 3600, float(np.max(np.abs(r))) * 3600, None)]
    freq: List[float] = []
    g = (math.sqrt(5.0) - 1.0) / 2.0
    for k in range(1, k_max + 1):
        spek = np.abs(np.fft.rfft(r * hann, nfft))
        spek[fgitter < 1.0 / (t.max() - t.min())] = 0.0
        j = int(np.argmax(spek))
        rh = r * hann

        def minus_amp(f):
            return -abs(np.dot(rh, np.exp(-2j * np.pi * f * t)))

        a, b = fgitter[max(j - 1, 0)], fgitter[min(j + 1, len(fgitter) - 1)]
        x1, x2 = b - g * (b - a), a + g * (b - a)
        f1, f2 = minus_amp(x1), minus_amp(x2)
        for _ in range(36):                                   # goldener Schnitt auf dem Spektralgipfel
            if f1 < f2:
                b, x2, f2 = x2, x1, f1
                x1 = b - g * (b - a)
                f1 = minus_amp(x1)
            else:
                a, x1, f1 = x1, x2, f2
                x2 = a + g * (b - a)
                f2 = minus_amp(x2)
        f = (a + b) / 2.0
        freq.append(f)
        B = np.vstack([np.cos(2 * np.pi * f * t), np.sin(2 * np.pi * f * t)]).T
        for _ in range(2):                                    # gegen alle bisherigen Kreise orthogonalisieren
            B -= Q[:, :p] @ (Q[:, :p].T @ B)
        qb, rb = np.linalg.qr(B)
        qb = qb[:, np.abs(np.diag(rb)) > 1e-9 * math.sqrt(n)]
        Q[:, p:p + qb.shape[1]] = qb
        p += qb.shape[1]
        r = r - qb @ (qb.T @ r)
        aus.append((k, float(np.sqrt(np.mean(r * r))) * 3600, float(np.max(np.abs(r))) * 3600, 1.0 / f))
    A = np.hstack([grund] + [np.vstack([np.cos(2 * np.pi * f * t), np.sin(2 * np.pi * f * t)]).T for f in freq])
    c = np.linalg.lstsq(A, lam, rcond=None)[0]
    kreise = [(1.0 / f, float(math.hypot(c[grad + 1 + 2 * i], c[grad + 2 + 2 * i])) * 3600) for i, f in enumerate(freq)]
    return {"tabelle": aus, "kreise": kreise}


def platon_schwellen(tabelle, grenzen=PLATON_GRENZEN) -> List[Optional[int]]:
    """Kleinste Kreiszahl K, deren RMS-Rest die Grenze erreicht (None: nicht erreicht)."""
    return [next((k for k, rms, _, _ in tabelle if rms <= g), None) for g, _ in grenzen]


def _kepler_xyz(np, p, T):
    """Ekliptikale x, y einer Kepler-Ellipse mit linear veraenderlichen Elementen (T in julian. Jahrhunderten)."""
    a, e0, e1, i0, i1, o0, o1, w0, w1, l0, n = p
    e = e0 + e1 * T
    inkl, knoten, peri = np.radians(i0 + i1 * T), np.radians(o0 + o1 * T), np.radians(w0 + w1 * T)
    M = np.mod(np.radians(l0 + n * T) - peri + np.pi, 2 * np.pi) - np.pi
    E = M + e * np.sin(M)
    for _ in range(12):                                       # Kepler-Gleichung E - e sin E = M (Newton)
        E -= (E - e * np.sin(E) - M) / (1 - e * np.cos(E))
    xp, yp = a * (np.cos(E) - e), a * np.sqrt(1 - e * e) * np.sin(E)
    om = peri - knoten
    co, so, cO, sO, cI = np.cos(om), np.sin(om), np.cos(knoten), np.sin(knoten), np.cos(inkl)
    x = (co * cO - so * sO * cI) * xp + (-so * cO - co * sO * cI) * yp
    y = (co * sO + so * cO * cI) * xp + (-so * sO + co * cO * cI) * yp
    return x, y


def kepler_anpassen(t, orte) -> Dict[str, object]:
    """Je Ort eine Kepler-Ellipse (11 Parameter) nach kleinsten Quadraten; Rueckgabe Modellorte wie 'orte'."""
    import numpy as np
    from scipy.optimize import least_squares
    T = (float(EPOCHE_JD_UTC) + t - 2451545.0) / 36525.0
    modell = {}
    for key, X in orte.items():
        def fehler(p, X=X):
            x, y = _kepler_xyz(np, p, T)
            return np.concatenate([x - X[:, 0], y - X[:, 1]])

        p = least_squares(fehler, KEPLER_START[key], x_scale="jac", max_nfev=400).x
        modell[key] = np.vstack(_kepler_xyz(np, p, T)).T
    return modell


# ---------------------------------------------------------------------------
# 7. Pruefungen und Bericht
# ---------------------------------------------------------------------------

def aufbauen(startjahr=2027, karten: int = 42, eps_q: Optional[F] = None, modell=None):
    """Standard: Bezugspunkt Sonne (mittlerer Fruehlingspunkt nach Meeus), 42 Karten = 2027-2992."""
    s = Struktur()
    m = FruehlingspunktModell() if modell is None else modell
    ref = DirekterAnker(s, m, startjahr)
    eps = F(1, 2) if eps_q is None else eps_q
    spline = SplineAnker(ref, bis_jahr=23 * karten, eps_q=eps)
    return s, m, ref, spline


def pruefe(karten: int = 42, stichproben: int = 20000, seed: int = 1) -> List[str]:
    s, m, ref, spline = aufbauen(karten=karten)
    ok: List[str] = []
    assert jd_zu_text(F(2451545)) == "2000-01-01 12:00:00"
    assert FruehlingspunktModell().T(2000) == F("365.24237404")

    # Struktur
    assert (s.zyklus_q, s.tag_q, s.jahr_q) == (1519, 1166592, 425806080)
    assert s.tick_s == F(75, 44) and s.q_s == F(75, 1012)
    assert (s.tag_q % 23, s.jahr_q % 23, (23 * s.jahr_q) % 23) == (9, 19, 0)
    ok.append("Struktur: 1519 / 1 166 592 / 425 806 080 q, Phasen 9, 19, 0")

    # Modell: Stammfunktion
    for mod in (m, LaskarModell()):
        for y in (2027, 2500, 2900):
            mittel = mod.verstrichen(y, y + 1)
            assert abs(mittel - mod.T(F(y) + F(1, 2))) < F(1, 10 ** 9)
    ok.append("Modelle (Fruehlingspunkt, Laskar): Position und Jahreslaenge konsistent (< 1e-9 d)")

    # Spline: Knoten interpolieren exakt, C1-stetig, Abweichung <= eps (ausser Horizont)
    for a, b in zip(spline.segmente, spline.segmente[1:]):
        assert a.wert(a.n1) == b.a == ref.soll(a.n1)
        assert a.steigung(a.n1) == b.b
    for sg in spline.segmente:
        assert sg.max_abw_q <= spline.eps_q
    ok.append(f"Spline: {len(spline.segmente)} Segmente, Knoten exakt, C1-stetig, Abweichung <= {spline.eps_q} q")

    rnd = random.Random(seed)
    for modus in ("tick", "q"):
        for rand in ("signiert", "luecke"):
            kal = Kalender(s, spline, karten, modus, rand)
            u = s.k if modus == "tick" else 1
            schranke = F(u, 2)
            for k in kal.karten:
                assert abs(k.P - spline.soll(23 * k.j)) <= F(1, 2)
                assert k.R == u * k.C[23] + k.r
                assert all(e >= 0 for e in k.einfuegungen())
                if modus == "q":
                    assert k.r == 0
                elif rand == "signiert":
                    assert -(u // 2) <= k.r <= u // 2
                else:
                    assert 0 <= k.r < u
                for e in kal.jahresfehler(k.j):
                    assert abs(e) <= schranke
            # Koordinaten: Hin- und Rueckweg
            t0, t1 = kal.P[0], kal.P[-1]
            punkte = [rnd.randrange(t0, t1) for _ in range(stichproben)]
            for k in kal.karten:                          # Raender gezielt
                punkte += [k.P, k.P_naechste - 1, k.inhalt_ende - 1, k.inhalt_ende]
                punkte += [k.P + k.starts[mm] + d for mm in range(23) for d in (-1, 0, 1)]
            punkte = [p for p in punkte if t0 <= p < t1]
            for p in punkte:
                for f in (0, 1):
                    c = kal.koordinaten(p, f)
                    assert kal.zeitpunkt(c) == p
                    assert kal.koordinaten(kal.zeitpunkt(c), c.fold) == c
                c = kal.koordinaten_countdown(p)          # bijektiv ohne fold
                assert kal.zeitpunkt_countdown(c) == p
                assert kal.koordinaten_countdown(kal.zeitpunkt_countdown(c)) == c
            # vor jeder Null (Jahres- und Kartenanfang) existiert der Index -1
            for k in kal.karten[1:]:
                for mm in range(23):
                    c = kal.koordinaten_countdown(k.P + k.starts[mm] - 1)
                    assert c.art == "uebergang" and c.index == -1 and c.jahr == mm and c.karte == k.j
            ok.append(f"Kalender {modus}/{rand}: Schranken eingehalten, {len(punkte)} Punkte Hin- und Rueckweg "
                      f"(fold und Countdown), -1 vor jeder Null")

    # Differenzenschema = geschlossene Form
    werte = [ref.soll(23 * j) for j in range(5)]
    dm = differenzmaschine(werte, 60)
    assert all(dm[j] == ref.soll(23 * j) for j in range(60))
    sg = spline.segmente[0]
    n_seg = (sg.n1 - sg.n0) // 23
    dm2 = differenzmaschine([sg.wert(23 * j) for j in range(3)], n_seg + 1)
    assert all(dm2[j] == sg.wert(23 * j) for j in range(n_seg + 1))
    ok.append("Differenzenschema: Grad 4 (direkt) und Grad 2 (Spline) exakt gleich der geschlossenen Form")

    # Zustandsperiode bei rationaler Kruemmung
    assert zustandsperiode(F(-797, 21), F(46638 * 21 + 14, 21), s.jahr_q) == 21
    ok.append("Zustand: Periode 21 Karten bei D = -797/21 q")

    # Drehachse und Haeuser
    assert abs(delta_t(2027) - 69.2) < 1e-9
    orte = ((52.52, 13.40), (48.14, 11.58), (-33.87, 151.21), (40.71, -74.01), (0.0, 0.0), (60.17, 24.94))
    for t in (0, kal_t := 123456789012, 4 * 10 ** 11):
        dk = drehkoordinate(t, 13.40)
        assert abs(dk.rest) <= 0.5 and 0 <= dk.zyklus < 768 and 0 <= dk.tick < 66 and 0 <= dk.quant < 23
        k = (dk.zyklus * 66 + dk.tick) * 23 + dk.quant
        st = sternzeit(jd_tt_aus_systemzeit(t)) + 13.40 / 360
        assert abs(dk.umlauf + (k + dk.rest) / DREH_Q_PRO_UMLAUF - st) < 1e-9
    for (br, la) in orte:
        for t in (0, 10 ** 11, 3 * 10 ** 11):
            jd = jd_tt_aus_systemzeit(t)
            for sysname in HAUSSYSTEME:
                h = haeuser(jd, br, la, sysname)
                sp = h["spitzen"]
                schritte = [(sp[(i + 1) % 12] - sp[i]) % 360 for i in range(12)]
                assert all(0 < x < 180 for x in schritte) and abs(sum(schritte) - 360) < 1e-6
                if sysname in ("placidus", "porphyrius"):
                    assert abs(sp[0] - h["asc"]) < 1e-9 and abs(sp[9] - h["mc"]) < 1e-9
                if sysname == "gleich":
                    assert all(abs(x - 30) < 1e-9 for x in schritte)
    meldung = "Drehachse: Raster 1 165 824 q je Umlauf, Rest <= 1/2; Haeuser in vier Systemen konsistent"
    try:
        import swisseph as swe
        groesste = 0.0
        codes = {"placidus": b"P", "porphyrius": b"O", "gleich": b"E", "ganzzeichen": b"W"}
        for (br, la) in orte:
            for t in (0, 10 ** 10, 5 * 10 ** 10, 10 ** 11):      # 2029 bis 2264; danach weichen
                jd = jd_tt_aus_systemzeit(t)                     # die Praezessionsmodelle ab
                ju = jd_ut1_aus_tt(jd)
                for sysname, code in codes.items():
                    h = haeuser(jd, br, la, sysname)
                    cusps, ascmc = swe.houses_ex(ju, br, la, code)
                    werte = list(zip(h["spitzen"], cusps[:12])) + [(h["asc"], ascmc[0]), (h["mc"], ascmc[1])]
                    for a, b in werte:
                        groesste = max(groesste, abs(((a - b + 180) % 360) - 180) * 3600)
        assert groesste < 5.0
        meldung += f"; gegen Swiss Ephemeris 2029-2264 hoechstens {groesste:.1f}''"
    except ImportError:
        meldung += " (Swiss Ephemeris nicht installiert, Vergleich uebersprungen)"
    ok.append(meldung)
    return ok


def segmentstudie(nenner: Sequence[int] = (2, 8, 32, 128, 512), karten: int = 42,
                  schritte: Sequence[int] = (23, 1)) -> None:
    """Grenzuebergang: Schwelle eps = q/nenner verkleinern, Segmentlaengen beobachten.
    schritt = 23: Knoten nur an Kartengrenzen; schritt = 1: Knoten an jedem Jahresanfang."""
    s, m = Struktur(), FruehlingspunktModell()
    ref = DirekterAnker(s, m, 2027)
    print("\nSEGMENTSTUDIE (eps -> 0)")
    for schritt in schritte:
        for n in nenner:
            sp = SplineAnker(ref, 23 * karten, F(1, n), schritt=schritt)
            L = [g.n1 - g.n0 for g in sp.segmente if not g.durch_horizont]
            dirP = [runden(ref.soll(23 * j)) for j in range(karten + 1)]
            flips = sum(1 for j in range(karten + 1) if runden(sp.soll(23 * j)) != dirP[j])
            print(f"  Knotenraster {schritt:2d} J, eps = q/{n:<3d}: {len(sp.segmente):3d} Segmente, "
                  f"erstes {L[0]} J, kuerzestes {min(L)} J, Karten mit anderem P als direkt: {flips}")


def _s(x_q: F, s: Struktur, stellen: int = 3) -> str:
    return f"{float(x_q * s.q_s):+.{stellen}f} s"


def aequinoktialgleichung(von: int = 2027, bis: int = 2992):
    """Wahres minus mittleres Maerz-Aequinoktium in Minuten je Jahr (benoetigt PyEphem).
    Gibt None zurueck, wenn PyEphem nicht installiert ist."""
    try:
        import ephem
    except ImportError:
        return None
    m = FruehlingspunktModell()
    aus = []
    for y in range(von, bis + 1):
        d = ephem.next_vernal_equinox(ephem.Date(f"{y}/1/1"))
        jd_tt = float(d) + 2415020.0 + ephem.delta_t(d) / 86400.0
        aus.append((y, (jd_tt - float(m.jde(y))) * 1440.0))
    return aus


# Quellen der Schwankung: Periode in Tagen und verwendete Harmonische.
# Bei Abtastung einmal pro Jahr erscheint eine Frequenz f (Zyklen/Jahr) als Alias f - round(f).
SCHWANKUNGSQUELLEN = (
    ("Mondknoten (Nutation)", 6798.38, (1,)),
    ("Mondmonat (synodisch)", 29.530589, (1,)),
    ("Venus (synodisch)", 583.924, (1, 2, 3)),
    ("Mars (synodisch)", 779.94, (2,)),
    ("Jupiter (synodisch)", 398.88, (1, 2)),
)


def aequinoktialgleichung_reihe(von: int = 2027, bis: int = 2992, jahr_tage: float = 365.2424):
    """Beschreibt wahr minus mittel als Konstante + Trend + periodische Terme fester Herkunft
    (Kleinste Quadrate). Gibt (Terme, Streuung vorher, Reststreuung, groesster Rest) zurueck;
    Terme = Liste (Quelle, Harmonische, scheinbare Periode in Jahren, Amplitude in min).
    Benoetigt PyEphem und NumPy; sonst None."""
    daten = aequinoktialgleichung(von, bis)
    try:
        import numpy as np
    except ImportError:
        return None
    if daten is None:
        return None
    t = np.array([y for y, _ in daten], float)
    v = np.array([w for _, w in daten], float)
    x = t - t.mean()
    spalten, terme = [np.ones_like(x), x / 1000.0], []
    for name, P, harmonische in SCHWANKUNGSQUELLEN:
        for h in harmonische:
            f = h * jahr_tage / P
            fa = f - round(f)
            spalten += [np.cos(2 * np.pi * fa * x), np.sin(2 * np.pi * fa * x)]
            terme.append((name, h, 1.0 / abs(fa)))
    A = np.vstack(spalten).T
    koeff, *_ = np.linalg.lstsq(A, v, rcond=None)
    rest = v - A @ koeff
    aus = []
    for i, (name, h, periode) in enumerate(terme):
        c, s = koeff[2 + 2 * i], koeff[3 + 2 * i]
        aus.append((name, h, periode, float(np.hypot(c, s))))
    aus.sort(key=lambda z: -z[3])
    return aus, float(v.std()), float(rest.std()), float(np.abs(rest).max())


def bericht(karten: int = 42, tabelle_karten: int = 21) -> None:
    s, m, ref, spline = aufbauen(karten=karten)
    if isinstance(m, FruehlingspunktModell):
        jde0 = m.jde(2027)
        print("EPOCHE (mittlerer Fruehlingspunkt 2027)")
        print(f"  JDE = {float(jde0):.5f}, TT {jd_zu_text(jde0)}, "
              f"UTC {jd_zu_text(jde0 - TT_MINUS_UTC / SEKUNDEN_PRO_TAG)}")
        ag = aequinoktialgleichung(2027, 2027 + 23 * karten - 1)
        if ag:
            werte = [v for _, v in ag]
            mittel = sum(werte) / len(werte)
            sd = math.sqrt(sum((v - mittel) ** 2 for v in werte) / len(werte))
            reihe = aequinoktialgleichung_reihe(2027, 2027 + 23 * karten - 1)
            if reihe:
                terme, vorher, nachher, maxrest = reihe
                print(f"  Reihe aus {len(terme)} Termen + Trend: Streuung {vorher:.2f} -> {nachher:.2f} min, "
                      f"groesster Rest {maxrest:.2f} min")
                for name, h, periode, amp in terme:
                    print(f"    {name:24s} h={h}  Periode {periode:6.2f} J  Amplitude {amp:.2f} min")
            print(f"  wahr - mittel: 2027 {ag[0][1]:+.2f} min; {ag[0][0]}-{ag[-1][0]}: Mittel {mittel:+.2f}, "
                  f"Streuung {sd:.2f}, Spanne {min(werte):+.2f} bis {max(werte):+.2f} min")
    print("STRUKTUR")
    print(f"  q = {s.q_s} s = {float(s.q_s):.7f} s, Tick = {s.tick_s} s = {float(s.tick_s):.7f} s")
    print(f"  Zyklus {s.zyklus_q} q, Tag {s.tag_q} q = {float(s.tag_q * s.q_s):.3f} s, "
          f"Jahr {s.jahr_q} q = {float(s.jahr_q * s.q_s):.3f} s")
    T0 = m.T(2027)
    defizit_q = T0 * SEKUNDEN_PRO_TAG / s.q_s - s.jahr_q
    print(f"  T(2027) = {float(T0):.10f} d, Defizit/Jahr = {float(defizit_q * s.q_s):.3f} s "
          f"= {float(defizit_q):.1f} q = {float(defizit_q / 23):.2f} Ticks")
    beitrag0 = s.tage * s.C            # q pro Jahr aus Zyklus-Nulldurchgaengen
    print(f"  Ebene 0 traegt {beitrag0} q/Jahr = {float(beitrag0 * s.q_s):.1f} s/Jahr bei")

    print("\nSPLINE (eps = q/2)")
    vorher = None
    for sg in spline.segmente:
        D = sg.zweite_differenz()
        sprung = "" if vorher is None else f", Sprung {float(D - vorher):+.3f} q"
        print(f"  {2027 + sg.n0}-{2027 + sg.n1 - 1}: {(sg.n1 - sg.n0) // 23:2d} Karten, "
              f"max Abw. {_s(sg.max_abw_q, s, 4)}, D = {float(D):.3f} q/Karte^2{sprung}"
              f"{' (Horizont)' if sg.durch_horizont else ''}")
        vorher = D

    kal = Kalender(s, spline, karten, "tick", "signiert")
    kalq = Kalender(s, spline, karten, "q", "signiert")
    dirP = [runden(ref.soll(23 * j)) for j in range(karten + 1)]
    diff = [kal.P[j] - dirP[j] for j in range(karten + 1)]
    print(f"\nAnker Spline vs direkt: max |Delta P| = {max(abs(d) for d in diff)} q, "
          f"Karten mit Abweichung: {sum(1 for d in diff if d)} von {karten + 1}")

    print("\nKARTEN (Tick-Modus, Randelement signiert)")
    print("  Karte | Jahre | R (q) | Ticks K + r | Randelement | Jahres-Einfuegungen | max|e| Anker | max|e| Referenz | q-Modus max|e| Referenz")
    for k in kal.karten[:tabelle_karten]:
        e_a = max(abs(x) for x in kal.jahresfehler(k.j))
        e_l = max(abs(x) for x in kal.jahresfehler(k.j, ref))
        e_q = max(abs(x) for x in kalq.jahresfehler(k.j, ref))
        ins = k.einfuegungen()
        zusammensetzung = ", ".join(f"{v}x{ins.count(v)}" for v in sorted(set(ins)))
        art = "Luecke" if k.r > 0 else ("Ueberlappung" if k.r < 0 else "-")
        print(f"  {k.j:2d} | {2027 + 23 * k.j}-{2027 + 23 * k.j + 22} | {k.R} | {k.C[23]} {k.r:+d} | "
              f"{art} {float(abs(k.r) * s.q_s):.3f} s | {zusammensetzung} | "
              f"{float(e_a * s.q_s):.3f} s | {float(e_l * s.q_s):.3f} s | {float(e_q * s.q_s):.3f} s")

    print("\nZUSTAND an den Kartenwechseln (Spline-Anker)")
    for j in range(6):
        sg = spline.segment(23 * j)
        e = kal.P[j] - spline.soll(23 * j)
        print(f"  Karte {j}: Rest e = {float(e):+.4f} q, Steigung = {float(sg.steigung(23 * j)):.4f} q/Jahr, "
              f"D = {float(sg.zweite_differenz()):.4f} q/Karte^2")

    k0 = kal.karten[0]
    print("\nBEISPIELKOORDINATEN Karte 0")
    for t in (k0.P, k0.P + s.zyklus_q - 1, k0.P + s.jahr_q, k0.inhalt_ende - 1):
        print(f"  t = {t}: {kal.koordinaten(t).text()}")
    for k in kal.karten[:30]:
        if k.r < 0:
            t = k.P_naechste
            print(f"  Ueberlappung nach Karte {k.j}, t = {t}: fold=0 -> {kal.koordinaten(t, 0).text()}")
            print(f"  {'':>33} fold=1 -> {kal.koordinaten(t, 1).text()}")
            for dt in (-2, -1, 0, 1):
                print(f"  Countdown t{dt:+d}: {kal.koordinaten_countdown(t + dt)}")
            break
    laengen = [23 * k.einfuegungen()[22] + k.r for k in kal.karten]
    print(f"  Uebergang am Kartenende (Countdown-Laenge): {min(laengen)} bis {max(laengen)} q")


def bericht_drehachse(breite: float = 52.52, laenge: float = 13.40, ort: str = "Berlin") -> None:
    print("\nDREHACHSE")
    stellartag = 86400 / 1.00273781191135448
    rate_gmst = 1.00273781191135448 + 4612.156534 / 1296000 / 36525
    print(f"  Sterntag bezogen auf die Sterne (ERA): {stellartag:.4f} s; auf den Fruehlingspunkt (GMST): "
          f"{86400 / rate_gmst:.4f} s; Differenz {stellartag - 86400 / rate_gmst:.4f} s pro Tag (Kegel)")
    print(f"  Kegel: Praezession {4612.156534 / 100:.2f}'' pro Jahr in Rektaszension, "
          f"{23 * 50.29 / 3600:.3f} Grad pro Karte in Laenge; halber Oeffnungswinkel = Schiefe "
          f"{schiefe_mittel(jd_tt_aus_systemzeit(0)):.4f} Grad")
    dpsi, deps = nutation(jd_tt_aus_systemzeit(0))
    print(f"  Pendeln bei 00: Nutation in Laenge {dpsi:+.2f}'', in Schiefe {deps:+.2f}'' "
          f"(Hauptterm 18,6 Jahre, 17,2'' / 9,2'')")
    j00 = 2000 + (float(EPOCHE_JD_TT) - 2451545.0) / 365.25
    print(f"  Definierte Drehung: Delta T bei {JJ} = {delta_t(j00):.2f} s = {jules(delta_t(j00)):.4f} Ju "
          f"(vorlaeufig; bei {JJ} aus IERS-Daten); "
          + ", ".join(f"{y}: {delta_t(y):.1f} s = {jules(delta_t(y)):.3f} Ju" for y in (2050, 2100, 2300)))
    print(f"  UT1 - UTC (definiert) bei {JJ}: {TT_MINUS_UTC_S - delta_t(j00):+.3f} s; 2050: "
          f"{TT_MINUS_UTC_S - delta_t(2050):+.2f} s; 2100: {TT_MINUS_UTC_S - delta_t(2100):+.2f} s (ohne Schaltsekunden)")
    print(f"  Eine Messabweichung von +1 s versetzt den wahren Meridian um {drehkorrektur_grad(delta_t(j00) + 1, j00) * 3600:+.2f}'', "
          f"von +1 Ju um {drehkorrektur_grad(delta_t(j00) + float(JULES_S), j00) * 60:+.3f}'")
    dk = drehkoordinate(0, laenge)
    print(f"  {JJ} in {ort}: Sternumlauf {dk.umlauf}, Zyklus {dk.zyklus}, "
          f"Tick {dk.tick}, q {dk.quant}, Rest {dk.rest:+.3f} q")
    h = haeuser(jd_tt_aus_systemzeit(0), breite, laenge, "placidus")
    print(f"  Aszendent {tierkreis_text(h['asc'])} (Systemlaenge {systemlaenge(h['asc']):.4f} Grad), "
          f"MC {tierkreis_text(h['mc'])} (Systemlaenge {systemlaenge(h['mc']):.4f} Grad), Schiefe {h['schiefe']:.4f} Grad")
    print("  Placidus: " + "; ".join(f"{i + 1}: {tierkreis_text(x)}" for i, x in enumerate(h["spitzen"])))


_MOND: Dict[str, Optional[Dict[str, object]]] = {}


def mond_herleitung() -> Optional[Dict[str, object]]:
    """mond_herleiten() mit Zwischenspeicher."""
    if "herleitung" not in _MOND:
        _MOND["herleitung"] = mond_herleiten()
    return _MOND["herleitung"]


def mond_natur() -> Optional[Dict[str, object]]:
    """mond_natur_minus_definition() mit Zwischenspeicher (PyEphem-Rechnung nur einmal)."""
    if "natur" not in _MOND:
        _MOND["natur"] = mond_natur_minus_definition()
    return _MOND["natur"]


def pruefe_mond(stichproben: int = 20000, seed: int = 3) -> List[str]:
    """Pruefungen der Mondachse: Raster, Grenzen (quantische Irrelevanz), Koordinaten,
    Herleitung, Natur - Definition, Neumonde je Jahr."""
    s, ok = Struktur(), []
    L = JOE_PRO_LUNATION
    assert L == 768 * 66 * 23 == 2 ** 9 * 3 ** 2 * 11 * 23
    assert all(L % n == 0 for n in (2, 3, 4, 8, 9, 11, 12, 16, 23, 24, 32, 66, 768)) and L % 5 and L % 30
    ma = Mondachse(s)
    n_lun = math.ceil(JAHRE_HORIZONT * 12.3683)
    assert ma.soll(0) == 0 and ma.grenze(0) == 0
    k0 = ma.koordinate(0)
    assert (k0.lunation, k0.phase, k0.q) == (0, MOND_PHI0, 0) and ma.neumond(0) < 0 < ma.neumond(1)
    rnd = random.Random(seed)
    ms = [rnd.randrange(-MOND_PHI0, n_lun * L) for _ in range(stichproben)]
    ms += [k * L - MOND_PHI0 + j for k in (0, 1, n_lun // 2, n_lun - 1) for j in range(-3, 4)]
    for m in ms:
        b0 = ma.grenze(m)
        assert ma.grenze(m + 1) - b0 in (29, 30) and abs(ma.soll(F(m, L)) - b0) <= F(1, 2)
    rho = [float(ma.soll(F(k * L - MOND_PHI0, L)) - ma.neumond(k)) for k in range(n_lun + 1)]
    assert max(abs(r) for r in rho) <= 0.5 and max(rho) - min(rho) < 1
    laengen = [ma.lunationslaenge(k) for k in range(n_lun)]
    nenn = MOND_A // MOND_D
    assert min(laengen) >= nenn and max(laengen) - min(laengen) <= 4
    pts = [rnd.randrange(ma.neumond(0), ma.neumond(n_lun)) for _ in range(stichproben)]
    pts += [ma.neumond(k) + j for k in (1, 2, n_lun - 1) for j in (-1, 0, 1)]
    for t in pts:
        mk = ma.koordinate(t)
        assert ma.zeitpunkt(mk) == t and 0 <= mk.q < 30 and ma.koordinate(ma.zeitpunkt(mk)) == mk
    for k in (1, 100, n_lun - 1):
        assert ma.koordinate(ma.neumond(k)).phase == 0
        assert ma.koordinate(ma.grenze(k * L - MOND_PHI0 + L // 2)).phase == L // 2      # Vollmond
    ok.append(f"Mondachse: 1 Lunation = 768 x 66 x 23 = {L} joe, joe 29/30 q, Neumonde <= q/2 "
              f"(Fenster {max(rho) - min(rho):.4f} q < 1), Lunationen {nenn} + {min(laengen) - nenn}..{max(laengen) - nenn} q, "
              f"{len(pts)} Punkte Hin- und Rueckweg, {JJ} = Lunation 0, Phase {MOND_PHI0}")

    h = mond_herleitung()
    if h is None:
        ok.append("Mond-Herleitung uebersprungen (NumPy fehlt)")
    else:
        assert h["phi0"] == MOND_PHI0 and h["g"] == MOND_G and abs(h["a"] - MOND_A) <= 100
        ok.append(f"Mond-Herleitung (Meeus 49.1) reproduziert PHI0 = {h['phi0']}, A = {h['a']}, G = {h['g']}; "
                  f"Abweichung vom geglaetteten Verlauf <= {h['max_abw_s']:.1f} s")
    nd = mond_natur()
    if nd is None:
        ok.append("Mond Natur - Definition uebersprungen (PyEphem/NumPy fehlt)")
    else:
        assert abs(nd["mittel_min"]) < 5 and -15 < nd["min_h"] and nd["max_h"] < 15 and nd["rest_rms_min"] < 10
        ok.append(f"Mond Natur - Definition ({nd['anzahl']} Neumonde): Mittel {nd['mittel_min']:+.2f} min, "
                  f"Spanne {nd['min_h']:+.2f} bis {nd['max_h']:+.2f} h, nach 8 Termen {nd['rest_rms_min']:.1f} min RMS")
    nj = neumonde_je_jahr(ma, DefinierterAnker(s))
    assert set(nj) == {12, 13} and sum(nj) == bisect_right([ma.neumond(k) for k in range(1, n_lun + 3)],
                                                             DefinierterAnker(s).runde_bei(JAHRE_HORIZONT, 1) - 1)
    ok.append(f"Neumonde je Systemjahr: 12 ({nj.count(12)} J) oder 13 ({nj.count(13)} J)")
    assert s.jules_q == F(5832409, 6250) and SYSTEMZEIT_MINUS_TT == F("-0.025")
    ok.append(f"Jules: 1 Ju = 69,159 s = {s.jules_q} q = {float(s.jules_q):.5f} q; Systemzeit = UTC + 1 Ju = TT - 25 ms")
    return ok


def bericht_mond() -> None:
    s = Struktur()
    q, L = float(s.q_s), JOE_PRO_LUNATION
    ma, anker = Mondachse(s), DefinierterAnker(s)
    n_lun = math.ceil(JAHRE_HORIZONT * 12.3683)
    print("\nMONDACHSE")
    mq = float(ma.lunation_q(0)) / L
    print(f"  joe: 1 Lunation = 768 x 66 x 23 = {L} joe; 1 joe = {1296000 / L:.5f}'' Elongation, "
          f"bei {JJ} {mq:.6f} q = {mq * q:.5f} s (joe : q = synodischer Monat : Tag)")
    print(f"  Mondzyklus = 1518 joe = {360 / 768:.5f} Grad, Mondtick = 23 joe = {1296000 / L * 23:.2f}''; "
          f"Viertel {L // 4}, Vollmond {L // 2}, letztes Viertel {3 * L // 4}")
    n0 = ma.neumond(0)
    print(f"  {JJ}: {ma.koordinate(0).text()}, Phase {MOND_PHI0} joe = {MOND_PHI0 * 360 / L:.4f} Grad; "
          f"Lunation 0 begann {jd_zu_text(EPOCHE_JD_UTC + F(n0) * s.q_s / SEKUNDEN_PRO_TAG)} UTC, "
          f"Lunation 1 beginnt {jd_zu_text(EPOCHE_JD_UTC + F(ma.neumond(1)) * s.q_s / SEKUNDEN_PRO_TAG)} UTC")
    print(f"  Definition: nu(x) = ({MOND_A} x + {MOND_G} x^2) / {MOND_D} q, x = Lunationen ab {JJ}")
    print(f"  mittlere Lunation bei {JJ} {float(ma.lunation_q(0)):.4f} q = {float(ma.lunation_q(0)) * q / 86400:.10f} d, "
          f"am Horizont {float(ma.lunation_q(n_lun)):.4f} q = {float(ma.lunation_q(n_lun)) * q / 86400:.10f} d")
    laengen = [ma.lunationslaenge(k) for k in range(n_lun)]
    nenn = MOND_A // MOND_D
    lang = [x - 29 * L for x in laengen]
    print(f"  Lunationslaengen {nenn} + {min(laengen) - nenn}..{max(laengen) - nenn} q (Lunationssprung); "
          f"joe 29 oder 30 q, davon {min(lang)} bis {max(lang)} je Lunation mit 30 q")
    h = mond_herleitung()
    if h:
        print(f"  Herleitung (Meeus 49.1): k bei {JJ} = {h['k0']:.6f} (Lunation 0 = Meeus-Lunation {h['K0']}); "
              f"Abweichung vom geglaetteten Verlauf <= {h['max_abw_s']:.1f} s; eingefrorener Versatz {h['versatz_s']:+.2f} s")
    nd = mond_natur()
    if nd:
        print(f"  Natur - Definition (wahre Neumonde, PyEphem, {nd['anzahl']} Lunationen): Lunation 0 {nd['lunation0_h']:+.2f} h, "
              f"Mittel {nd['mittel_min']:+.2f} min, Spanne {nd['min_h']:+.2f} bis {nd['max_h']:+.2f} h, RMS {nd['rms_h']:.2f} h; "
              f"nach 8 Termen Rest {nd['rest_rms_min']:.1f} min RMS (max {nd['rest_max_min']:.1f} min)")
        for name, periode, amp in nd["terme"]:
            print(f"    {name:26s} Periode {periode:8.2f} d   Amplitude {amp:6.3f} h = {amp * 60:6.1f} min")
    nj = neumonde_je_jahr(ma, anker)
    je_karte = [sum(1 for c in nj[23 * j:23 * j + 23] if c == 13) for j in range(JAHRE_HORIZONT // 23)]
    print(f"  Neumonde je Systemjahr: 12 in {nj.count(12)} Jahren, 13 in {nj.count(13)}; Karte 0: "
          f"{' '.join(str(c) for c in nj[:23])}; Jahre mit 13 je Karte: {min(je_karte)} oder {max(je_karte)}")
    R = F(s.jahr_q * ANKER_D + ANKER_B, ANKER_D) / F(MOND_A, MOND_D)
    cf = kettenbruch(R, 9)
    nb = naeherungsbrueche(cf)
    print(f"  Lunationen je Systemjahr bei {JJ}: {float(R):.7f} = [{cf[0]}; {', '.join(map(str, cf[1:]))}]; "
          f"Naeherungen " + ", ".join(f"{x.numerator}/{x.denominator}" for x in nb[1:8]))
    for x in nb[3:8]:
        fehler_h = (x.numerator / x.denominator - float(R)) * x.denominator * float(ma.lunation_q(0)) * q / 3600
        print(f"    {x.numerator:6d} Lunationen ~ {x.denominator:5d} Systemjahre, Fehler {fehler_h:+9.2f} h")
    print(f"  je Karte {23 * float(R):.3f} Lunationen, je Grosskarte {529 * float(R):.2f}")
    jt = float(anker.steigung(0)) * q / SEKUNDEN_PRO_TAG
    for name, n, tage, jahre, knoten, anomalie in finsterniszyklen(jt):
        print(f"    {name:10s} {n:4d} Lunationen = {tage:9.3f} d = {jahre:7.3f} Systemjahre; "
              f"Knotenversatz {knoten:+7.3f} Grad, Anomalieversatz {anomalie:+7.2f} Grad")


_POL: Dict[str, object] = {}


def pol_stand() -> Optional[Dict[str, object]]:
    """Daten, Rueckrechnung und Vorhersage fuer jj, einmal berechnet."""
    if "stand" not in _POL:
        daten = pol_daten()
        if daten is None:
            _POL["stand"] = None
        else:
            t, x, y = daten
            rueck = pol_rueckrechnung(daten)
            i0 = len(t) - 1
            v = complex(pol_vorhersage(daten, i0, MJD_JJ)[0])
            h = MJD_JJ - t[i0]
            sx, sy, _ = rueck[min(POL_HORIZONTE, key=lambda k: abs(k - h))]
            mx, my = v.real * IRIS_PRO_BOGENSEKUNDE, -v.imag * IRIS_PRO_BOGENSEKUNDE
            _POL["stand"] = {"daten": daten, "rueck": rueck, "jj": (mx, my, sx, sy, h)}
    return _POL["stand"]  # type: ignore[return-value]


def pruefe_pol() -> List[str]:
    """Pruefungen der Polachse: Raster, Felder, Wahrscheinlichkeiten, Rueckrechnung."""
    ok = []
    assert IRIS_PRO_BOGENSEKUNDE == 299 == 13 * 23
    assert abs(iris_mas() - 3.3444816) < 1e-6 and abs(iris_cm() - 10.330) < 0.001
    assert pol_feld(0.0, 0.0) == (0, 0) and pol_feld(1.0, -1.0) == (299, -299)
    assert abs(sum(feld_wahrscheinlichkeit(0.3, -1.7, 2.0, 3.0, X, Y)
                   for X in range(-30, 31) for Y in range(-35, 32)) - 1.0) < 1e-9
    st = pol_stand()
    if st is None:
        ok.append("Polachse: IERS-Daten fehlen (pip install astropy-iers-data), Pruefung nur des Rasters")
        return ok
    import numpy as np
    t, x, y = st["daten"]
    assert np.all(np.diff(t) == 1.0)                       # lueckenlos taeglich
    rueck = st["rueck"]
    s1 = math.hypot(rueck[1][0], rueck[1][1])
    assert s1 < 1.0 and all(math.hypot(*rueck[a][:2]) < math.hypot(*rueck[b][:2])
                            for a, b in zip(POL_HORIZONTE[:4], POL_HORIZONTE[1:5]))
    ok.append(f"Polachse: 1 Ir = 1''/299 = {iris_mas():.4f} mas = {iris_cm():.2f} cm, Felder ganzzahlig, "
              f"Wahrscheinlichkeiten summieren zu 1; IERS 20 C04 {len(t)} Tage lueckenlos; "
              f"Vorhersagefehler 1 Tag {s1:.2f} Ir, steigend mit dem Horizont")
    return ok


def bericht_pol() -> None:
    print("\nPOLACHSE (IRIS)")
    print(f"  1 Iris (Ir) = 1''/299 = {iris_mas():.4f} mas = {iris_cm():.2f} cm am Boden; Feld = (round(299 x), round(299 y))")
    st = pol_stand()
    if st is None:
        print("  IERS-Daten fehlen (pip install astropy-iers-data)")
        return
    import numpy as np
    t, x, y = st["daten"]
    X, Y = x * IRIS_PRO_BOGENSEKUNDE, y * IRIS_PRO_BOGENSEKUNDE
    print(f"  IERS 20 C04: MJD {t[0]:.0f}-{t[-1]:.0f}; letzter Tag Feld {pol_feld(x[-1], y[-1])} Ir")
    for a, b in ((1962, 2027), (2016, 2027)):
        s = (t >= 37665 + 365.25 * (a - 1962)) & (t < 37665 + 365.25 * (b - 1962))
        schritt = np.hypot(np.diff(X[s]), np.diff(Y[s]))
        print(f"  {a}-{b - 1}: x {X[s].min():.0f} bis {X[s].max():.0f} Ir, y {Y[s].min():.0f} bis {Y[s].max():.0f} Ir; "
              f"Tagesschritt Median {np.median(schritt):.2f} Ir, hoechstens {schritt.max():.2f} Ir")
    print("  Rueckrechnung ab 2010 (Horizont: RMSE_x, RMSE_y; Gaußmodell-Radius 68 % / 95 %; P bei Zellmitte):")
    for h in POL_HORIZONTE:
        sx, sy, n = st["rueck"][h]
        p = feld_wahrscheinlichkeit(0.0, 0.0, sx, sy, 0, 0)
        print(f"    {h:5d} d: {sx:5.2f} / {sy:5.2f} Ir; {pol_radius(sx, sy, 0.68):5.1f} / {pol_radius(sx, sy, 0.95):5.1f} Ir; "
              f"P(Zellmitte) {p:6.1%}  (n = {n}; keine gemessene Feldtrefferquote)")
    mx, my, sx, sy, h = st["jj"]
    X0, Y0 = round(mx), round(my)
    print(f"  Vorhersage fuer {JJ} ({h:.0f} Tage voraus): Mitte ({mx:.1f}, {my:.1f}) Ir, wahrscheinlichstes Feld "
          f"({X0}, {Y0}) mit P = {feld_wahrscheinlichkeit(mx, my, sx, sy, X0, Y0):.2%}; 68 % im Radius "
          f"{pol_radius(sx, sy, 0.68):.0f} Ir, 95 % im Radius {pol_radius(sx, sy, 0.95):.0f} Ir")


_DT: Dict[str, object] = {}


def dt_stand() -> Optional[Dict[str, object]]:
    """Gemessenes Delta T, Rueckrechnung und Vorhersage fuer jj, einmal berechnet."""
    if "stand" not in _DT:
        daten = dt_daten()
        if daten is None:
            _DT["stand"] = None
        else:
            import numpy as np
            t, dt = daten
            rueck = dt_rueckrechnung(daten)
            i0 = len(t) - 1
            mu = float(dt_vorhersage(daten, i0, MJD_JJ)[0])
            h = MJD_JJ - t[i0]
            sigma = rueck[min(POL_HORIZONTE, key=lambda k: abs(k - h))][0]
            kreuz = [float(t[i]) for i in np.where(np.diff(np.sign(dt - float(JULES_S))))[0]]
            _DT["stand"] = {"daten": daten, "rueck": rueck, "jj": (mu, sigma, h), "kreuzungen": kreuz}
    return _DT["stand"]  # type: ignore[return-value]


def _jahr_aus_mjd(mjd: float) -> float:
    return 2000.0 + (mjd - 51544.5) / 365.25


def pruefe_dt() -> List[str]:
    s, ok = Struktur(), []
    assert dt_feld(69.159) == 933 and dt_feld(float(JULES_S)) == runden(s.jules_q)
    assert abs(sum(dt_feld_wahrscheinlichkeit(69.2, 0.3, k) for k in range(900, 970)) - 1.0) < 1e-9
    st = dt_stand()
    if st is None:
        return ["Delta-T-Achse: IERS-Daten fehlen (pip install astropy-iers-data)"]
    import numpy as np
    t, dt = st["daten"]
    assert np.all(np.diff(t) == 1.0) and np.max(np.abs(np.diff(dt))) < 0.01          # stetig, keine Spruenge
    for jahr in (1980, 1990, 2000, 2010, 2020):
        i = int(np.searchsorted(t, 51544.5 + (jahr - 2000) * 365.25))
        assert abs(dt[i] - delta_t(jahr)) < 0.01                                  # gegen die Stuetzwerte
    r1 = st["rueck"][1][0]
    assert r1 < 0.001
    ok.append(f"Delta-T-Achse: {len(t)} Tage seit 1972 stetig, Stuetzwerte 1980-2020 auf 10 ms getroffen; "
              f"Felder in q, Wahrscheinlichkeiten summieren zu 1; Vorhersagefehler 1 Tag {r1 * 1000:.2f} ms")
    return ok


def bericht_dt() -> None:
    s = Struktur()
    q = float(s.q_s)
    print("\nDELTA-T-ACHSE (JULES)")
    st = dt_stand()
    if st is None:
        print("  IERS-Daten fehlen (pip install astropy-iers-data)")
        return
    t, dt = st["daten"]
    print(f"  gemessen (IERS 20 C04): {_jahr_aus_mjd(t[0]):.1f} {dt[0]:.3f} s ... {_jahr_aus_mjd(t[-1]):.3f} "
          f"{dt[-1]:.4f} s = {jules(dt[-1]):.5f} Ju = Feld {dt_feld(dt[-1])} q")
    print("  Delta T kreuzte 1 Ju = 69,159 s: " + ", ".join(
        jd_zu_text(F(x) + F(4800001, 2))[:10] for x in st["kreuzungen"]))
    print(f"  definiert (delta_t) am letzten Messtag: {delta_t(_jahr_aus_mjd(t[-1])):.4f} s; "
          f"gemessen - definiert {dt[-1] - delta_t(_jahr_aus_mjd(t[-1])):+.4f} s")
    print("  Rueckrechnung 2010-2026 (Horizont: sigma; P(wahrscheinlichstes Feld)):")
    for h in POL_HORIZONTE:
        sg, n = st["rueck"][h]
        print(f"    {h:5d} d: {sg * 1000:7.1f} ms = {sg / q:5.2f} q; P {dt_feld_wahrscheinlichkeit(0.0, sg, 0):6.1%}  (n = {n})")
    mu, sg, h = st["jj"]
    k = dt_feld(mu)
    dd = delta_t(_jahr_aus_mjd(MJD_JJ))
    print(f"  Vorhersage fuer {JJ} ({h:.0f} Tage voraus): {mu:.3f} s = {jules(mu):.5f} Ju, sigma {sg:.3f} s; Feld {k} q mit "
          f"P = {dt_feld_wahrscheinlichkeit(mu, sg, k):.1%}; Delta T_def({JJ}) = {dd:.3f} s liegt {(dd - mu) / sg:+.1f} sigma daneben")


_EPI: Dict[str, object] = {}


def epizykel_stand() -> Dict[str, object]:
    if "s" not in _EPI:
        _EPI["s"], _EPI["m"] = epizykel_sonne(), epizykel_mond()
    return _EPI


def pruefe_epizykel() -> List[str]:
    ok = []
    e = Epizykel("Test", F(1, 3), F(0), 1.0)
    assert [e.phase(n) for n in range(4)] == [0, EPIZYKEL_L // 3, 2 * EPIZYKEL_L // 3, 0]
    st = epizykel_stand()
    if st["s"] is None or st["m"] is None:
        return ["Epizykel-Achsen: PyEphem/NumPy fehlen, uebersprungen"]
    es, em = st["s"], st["m"]
    h, nd = herleitung(), mond_natur()
    assert abs(es["rest_rms_min"] - h["streuung_rest_min"]) < 0.01 and abs(em["rest_rms_min"] - nd["rest_rms_min"]) < 0.01
    ok.append(f"Epizykel-Achsen: 8 Sonnen- und 8 Mondkreise ganzzahlig gezaehlt (Rest <= 1/2 Rasterpunkt); "
              f"Sonne {es['ohne_rms_min']:.2f} -> {es['rest_rms_min']:.2f} min, Mond {em['ohne_rms_min']:.0f} -> "
              f"{em['rest_rms_min']:.1f} min, gleich der Gleitkomma-Zerlegung")
    return ok


def bericht_epizykel() -> None:
    print("\nEPIZYKEL-ACHSEN")
    st = epizykel_stand()
    if st["s"] is None or st["m"] is None:
        print("  PyEphem/NumPy fehlen")
        return
    for titel, e, einheit, fakt in (("Sonne (Durchgaenge von lambda0, je Jahr)", st["s"], "min", float(Struktur().q_s) / 60),
                                    ("Mond (Neumonde, je Lunation)", st["m"], "h", 1.0)):
        print(f"  {titel}: ohne Kreise {e['ohne_rms_min']:.2f} min RMS, mit 8 Kreisen {e['rest_rms_min']:.2f} min "
              f"(max {e['rest_max_min']:.2f} min) ueber {e['anzahl']} Schritte")
        for a in e["achsen"]:
            print(f"    {a.name:28s} f = {float(a.f):10.6f} Umlaeufe/Schritt, Amplitude {a.amplitude * fakt:7.3f} {einheit}, "
                  f"Phase bei {JJ} {a.phase(0):7d} von {EPIZYKEL_L}")


_FINS: Dict[str, object] = {}


def finsternis_stand(jahre: int = 200) -> Optional[Dict[str, object]]:
    if "s" not in _FINS:
        liste = finsternisse_natur(jahre)
        if liste is None:
            _FINS["s"] = None
        else:
            aus: Dict[str, object] = {"liste": liste, "jahre": jahre}
            for art, idx in (("Sonne", 3), ("Mond", 3), ("Mond_kern", 4), ("Sonne_zentral", 4)):
                a = art.split("_")[0]
                ja = [x[2] for x in liste if x[1] == a and x[idx]]
                nein = [x[2] for x in liste if x[1] == a and not x[idx]]
                aus[art] = (len(ja), len([x for x in liste if x[1] == a]), max(ja), min(nein))
            _FINS["s"] = aus
    return _FINS["s"]  # type: ignore[return-value]


def pruefe_finsternis_gezeiten() -> List[str]:
    ok, s = [], Struktur()
    L = EPIZYKEL_L
    ma = Mondachse(s)
    assert s.tag_q != L and L // 2 == 582912                             # ideales SI-Tagesraster, nicht exakte UT1-Periode
    for k in (1, 50, 500):
        assert gezeiten(ma.neumond(k))["spring_nipp"] == 0                 # Springtide bei Neumond
        assert gezeiten(ma.grenze(k * L - MOND_PHI0 + L // 2))["spring_nipp"] == 0      # und Vollmond
        assert gezeiten(ma.grenze(k * L - MOND_PHI0 + L // 4))["spring_nipp"] == L // 2  # Nipptide
    p_m2_h = 1.0 / (2.0 / 24.0 - 2.0 / (MONAT_SYNODISCH * 24.0))
    assert abs(p_m2_h - 12.4206012) < 1e-4
    t0 = 10 ** 9
    d = (gezeiten(t0 + 582912)["S2"] - gezeiten(t0)["S2"]) % L
    assert min(d, L - d) <= 2                                              # lokale Naeherung an ideale S2-Periode
    ok.append(f"Gezeiten: ideales S2-Raster 582 912 q (UT1-Modell nicht exakt SI-periodisch), Spring-Nipp = 582 912 joe (Spring bei Neu- und Vollmond, Nipp bei den Vierteln), "
              f"M2 = {p_m2_h:.5f} h aus q- und joe-Raster")
    st = finsternis_stand()
    if st is None:
        ok.append("Finsternisse: PyEphem fehlt, uebersprungen")
        return ok
    erste = [x for x in st["liste"] if x[3]][:3]
    assert erste[0][1] == "Sonne" and erste[0][0] == MOND_K0                 # 11. Juli 2029: Sonnenfinsternis
    for art in ("Sonne", "Mond"):
        n_ja, n, max_ja, min_nein = st[art]
        assert max_ja < 25.0 and min_nein > 5.0
    ok.append(f"Finsternisse {st['jahre']} Jahre ab {JJ}: Knotenachse trennt Finsternis und keine Finsternis; "
              f"Lunation 0 beginnt mit der Sonnenfinsternis vom 11. Juli 2029")
    return ok


def bericht_finsternis_gezeiten() -> None:
    L = EPIZYKEL_L
    print("\nFINSTERNISSE (KNOTENACHSE) UND GEZEITEN")
    p_m2_h = 1.0 / (2.0 / 24.0 - 2.0 / (MONAT_SYNODISCH * 24.0))
    print(f"  Ideales SI-Tagesraster S2 = {L // 2} q; UT1-S2 nicht exakt SI-periodisch; Spring-Nipp-Zyklus = halbe definierte Lunation = {L // 2} joe genau "
          f"({MONAT_SYNODISCH / 2:.4f} d); M2 = {p_m2_h:.6f} h, f_M2 = (2/L)(1/q - 1/joe)")
    g = gezeiten(0)
    print(f"  bei {JJ}: S2-Phase {g['S2']}, Spring-Nipp-Phase {g['spring_nipp']} (0 = Spring, {L // 2} = Nipp), M2-Phase {g['M2']}")
    print(f"  Knotenachse: F bei Lunation 0 (Neumond) {knoten_f_grad(MOND_K0):.2f} Grad = Index {knoten_index(MOND_K0)}, "
          f"Abstand zum Knoten {knotenabstand_grad(MOND_K0):.2f} Grad; F waechst je Lunation um {MEEUS_F[1] - 360:.4f} Grad")
    st = finsternis_stand()
    if st is None:
        print("  PyEphem fehlt")
        return
    for art, text in (("Sonne", "Sonnenfinsternisse (irgendwo auf der Erde)"), ("Sonne_zentral", "  davon zentral"),
                      ("Mond", "Mondfinsternisse (Halbschatten)"), ("Mond_kern", "  davon Kernschatten")):
        n_ja, n, max_ja, min_nein = st[art]
        print(f"  {text}: {n_ja} von {n} Syzygien in {st['jahre']} Jahren ({n_ja / st['jahre']:.2f} je Jahr); Knotenabstand "
              f"aller Finsternisse <= {max_ja:.2f} Grad, aller Nicht-Finsternisse >= {min_nein:.2f} Grad")
    ma = Mondachse()
    q = float(ma.s.q_s)
    zeilen = []
    for km, art, ab, ja, kern in [x for x in st["liste"] if x[3]][:6]:
        k = int(km - MOND_K0)
        halb = km - MOND_K0 - k
        t = ma.neumond(k) + halb * float(ma.lunation_q(k))
        zeilen.append(f"{jd_zu_text(EPOCHE_JD_UTC + F(t * q / SEKUNDEN_PRO_TAG).limit_denominator(10 ** 9))[:10]} {art}"
                      f"{' (zentral)' if art == 'Sonne' and kern else ' (Kernschatten)' if art == 'Mond' and kern else ''}, "
                      f"Knotenabstand {ab:.1f} Grad")
    print("  erste Finsternisse ab jj (mittlere Syzygie): " + "; ".join(zeilen))


_PLATON: Dict[int, Optional[Dict[str, object]]] = {}


def platon_stand(k_max: int = PLATON_K) -> Optional[Dict[str, object]]:
    """Volle Rechnung zu Platons Frage: je Koerper Kreise allein, Kepler-Ellipse(n), Ellipse + Kreise.
    None ohne NumPy, PyEphem oder SciPy."""
    if k_max not in _PLATON:
        try:
            import numpy as np
            import ephem  # noqa: F401
            import scipy.optimize  # noqa: F401
        except ImportError:
            _PLATON[k_max] = None
            return None
        aus: Dict[str, object] = {}
        for koerper, (jahre, schritt) in PLATON_KOERPER.items():
            t, orte = platon_orte(koerper, jahre, schritt)
            lam = platon_laenge(koerper, orte)
            kreise = platon_konvergenz(t, lam, k_max)
            rest = lam - platon_laenge(koerper, kepler_anpassen(t, orte))
            rest -= np.round(np.mean(rest) / 360.0) * 360.0
            kep = {"rms": float(np.sqrt(np.mean(rest * rest))) * 3600, "max": float(np.max(np.abs(rest))) * 3600,
                   "parameter": 11 * len(orte)}
            aus[koerper] = {"jahre": jahre, "schritt": schritt, "n": len(t), "kreise": kreise, "kepler": kep,
                            "hybrid": platon_konvergenz(t, rest, k_max),
                            "aequivalent": next((k for k, rms, _, _ in kreise["tabelle"] if rms <= kep["rms"]), None)}
        _PLATON[k_max] = aus
    return _PLATON[k_max]


def pruefe_platon() -> List[str]:
    try:
        import numpy as np
    except ImportError:
        return ["Platons Frage: NumPy fehlt, uebersprungen"]
    ok = []
    t = np.arange(0.0, 20000.0, 2.0)                                   # 1) bekannte Kreise wiederfinden
    u = (t - t.mean()) / (t.max() - t.mean())
    perioden, amp = (365.25, 27.55, 433.0), (3.0, 0.4, 0.05)
    lam = 1 + 0.5 * u + 0.1 * u * u + sum(a * np.cos(2 * np.pi * t / p + 0.3 * i)
                                          for i, (p, a) in enumerate(zip(perioden, amp)))
    k = platon_konvergenz(t, lam, 3)
    assert all(abs(g / p - 1) < 1e-6 for g, p in zip(sorted(x for x, _ in k["kreise"]), sorted(perioden)))
    assert all(abs(g / a - 1) < 1e-4 for (_, g), a in zip(k["kreise"], [x * 3600 for x in amp]))
    assert k["tabelle"][3][1] < 1e-5 * k["tabelle"][0][1]
    e = 0.0934                                                         # 2) Kepler-Gleichung gegen die Reihe
    M = np.linspace(-np.pi, np.pi, 2001)
    x, y = _kepler_xyz(np, [1.0, e, 0, 0, 0, 0, 0, 0, 0, 0, 1.0], np.degrees(M))
    reihe = (M + (2 * e - e ** 3 / 4) * np.sin(M) + 1.25 * e * e * np.sin(2 * M) + 13 / 12 * e ** 3 * np.sin(3 * M)
             + (103 / 96 * np.sin(4 * M) - 11 / 24 * np.sin(2 * M)) * e ** 4)
    assert np.max(np.abs(np.angle(np.exp(1j * (np.arctan2(y, x) - reihe))))) < 2 * e ** 5
    x, y = _kepler_xyz(np, [2.0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.0], np.degrees(M))
    assert np.max(np.hypot(x - 2 * np.cos(M), y - 2 * np.sin(M))) < 1e-12           # e = 0: der Kreis
    ok.append("Platons Frage: drei bekannte Kreise wiedergefunden (Periode < 1e-6, Amplitude < 1e-4, Rest < 1e-5); "
              "Kepler-Gleichung gegen die Reihe bis e^4, e = 0 ergibt den Kreis")
    try:
        import ephem  # noqa: F401
    except ImportError:
        return ok + ["Platons Frage, Sonne: PyEphem fehlt, uebersprungen"]
    t, orte = platon_orte("Sonne", 30, 5.0)                             # 3) Sonne, 30 Jahre ab jj
    k = platon_konvergenz(t, platon_laenge("Sonne", orte), 2)
    (p1, a1), (p2, a2) = k["kreise"]
    assert abs(p1 - JAHR_ANOMALISTISCH) < 0.01 and abs(p2 - JAHR_ANOMALISTISCH / 2) < 0.01
    assert k["tabelle"][1][1] < k["tabelle"][0][1] / 50
    ok.append(f"Platons Frage, Sonne 30 Jahre: erster Kreis = anomalistisches Jahr ({p1:.3f} d, {a1 / 3600:.3f} Grad), "
              f"zweiter = halbes ({p2:.3f} d); Rest {k['tabelle'][0][1]:.0f}\" -> {k['tabelle'][1][1]:.0f}\" -> "
              f"{k['tabelle'][2][1]:.0f}\" (volle Rechnung: python3 zyklus23.py platon)")
    return ok


def bericht_platon(k_max: int = PLATON_K) -> None:
    print("\nPLATONS FRAGE: WIE VIELE KREISE FUER WELCHE GENAUIGKEIT?")
    print("  Laenge (mittlere Ekliptik des Datums, geometrisch, PyEphem) = quadratische Grundbewegung + K Kreise;")
    print("  Zahlen = freie Parameter (Polynom 3, je Kreis 3, je Kepler-Ellipse 11). RMS und Maximum in Bogensekunden.")
    st = platon_stand(k_max)
    if st is None:
        print("  NumPy/PyEphem/SciPy fehlen")
        return
    zeigen = (0, 1, 2, 3, 4, 5, 6, 8, 10, 15, 20, 30, 40, 60, 80, 100, 120, 150, 200)
    for koerper, e in st.items():
        kep = e["kepler"]
        print(f"\n  {koerper}: {e['jahre']} Jahre ab {JJ}, Schritt {e['schritt']:g} d ({e['n']} Orte)")
        print(f"    {'K':>4s} {'Zahlen':>7s} {'Kreise RMS':>12s} {'max':>10s}   {'Periode K':>11s}   "
              f"{'Ellipse+K RMS':>14s} {'max':>9s}")
        for (k, rms, mx, per), (_, hr, hm, _) in zip(e["kreise"]["tabelle"], e["hybrid"]["tabelle"]):
            if k in zeigen:
                print(f"    {k:4d} {3 + 3 * k:7d} {rms:12.2f} {mx:10.2f}   {'' if per is None else f'{per:9.3f} d':>11s}   "
                      f"{hr:14.3f} {hm:9.2f}")
        print("    erste Kreise (Periode, Amplitude): "
              + "; ".join(f"{p:.3f} d {a:.0f}\"" for p, a in e["kreise"]["kreise"][:8]))
        sk, sh = platon_schwellen(e["kreise"]["tabelle"]), platon_schwellen(e["hybrid"]["tabelle"])
        print("    Kreise fuer RMS " + ", ".join(f"{n}: {k if k is not None else f'> {k_max}'}"
                                               for (_, n), k in zip(PLATON_GRENZEN, sk))
              + "  |  Ellipse + Kreise: " + ", ".join(f"{n}: {k if k is not None else f'> {k_max}'}"
                                                       for (_, n), k in zip(PLATON_GRENZEN, sh)))
        print(f"    Kepler: {kep['parameter']} Zahlen, RMS {kep['rms']:.2f}\", max {kep['max']:.2f}\"; "
              f"erst {e['aequivalent']} Kreise ({3 + 3 * e['aequivalent']} Zahlen) sind genauer")


_HERLEITUNG: Dict[int, Optional[Dict[str, object]]] = {}


def herleitung(jahre: int = JAHRE_HORIZONT) -> Optional[Dict[str, object]]:
    """anker_herleiten() mit Zwischenspeicher (PyEphem-Rechnung nur einmal)."""
    if jahre not in _HERLEITUNG:
        _HERLEITUNG[jahre] = anker_herleiten(jahre)
    return _HERLEITUNG[jahre]


def pruefe_festlegung(stichproben: int = 20000, seed: int = 2) -> List[str]:
    """Pruefungen der Festlegung: Kalibrierpunkt, definierter Anker, quantische Irrelevanz,
    verteilte Zaehlung, Koordinaten, Herleitung."""
    import datetime
    s, ok = Struktur(), []
    assert jd_zu_text(EPOCHE_JD_UTC) == "2029-07-12 22:00:00"
    assert jd_zu_text(EPOCHE_JD_UTC + F(2, 24)) == "2029-07-13 00:00:00"      # MESZ = UTC + 2 h
    assert datetime.date(2029, 7, 13).weekday() == 4                          # Freitag
    assert EPOCHE_JD_SYS - EPOCHE_JD_UTC == JULES_S / SEKUNDEN_PRO_TAG
    ok.append(f"{JJ} (Kalibrierpunkt 00): {KALIBRIERPUNKT_TEXT}, JD TT {float(EPOCHE_JD_TT):.6f}")

    anker = DefinierterAnker(s)
    assert anker.b % 23 and anker.g % 23 and anker.d == 23 ** 2
    A = [anker.runde_bei(n, 1) for n in range(2 * 529 + 1)]
    rho = [anker.soll(n) - A[n] for n in range(2 * 529 + 1)]
    assert all(rho[n] == rho[n + 529] for n in range(529 + 1))
    assert rho[0] == rho[529] == rho[1058] == 0
    J = [A[n + 1] - A[n] - s.jahr_q for n in range(2 * 529)]
    assert all(J[n + 529] - J[n] == 2 * anker.g for n in range(529))
    assert sorted(int(rho[23 * j] * 23) for j in range(23)) == list(range(-11, 12))
    ok.append(f"Anker {anker.b}/{anker.d}, {anker.g}/{anker.d}: Jahresanfangsrest periodisch 529 J, 0 an jeder Grosskartengrenze, "
              f"Kartenanfaenge durchlaufen alle k/23 q, Sprung aendert sich um {2 * anker.g} q je 529 J")

    rh = [float(anker.soll(n) - anker.runde_bei(n, 1)) for n in range(JAHRE_HORIZONT + 1)]
    assert max(abs(r) for r in rh) <= 0.5 and max(rh) - min(rh) < 1
    mittel = sum(rh) / len(rh)
    rms = math.sqrt(sum(r * r for r in rh) / len(rh))
    ok.append(f"Quantische Irrelevanz ({JAHRE_HORIZONT} J): max |Rest| {max(abs(r) for r in rh):.3f} q, "
              f"Fenster {max(rh) - min(rh):.3f} q < 1, Mittel {mittel:+.4f} q, RMS {rms:.3f} q")

    kal = VerteilterKalender(s, anker)
    for n in (0, JAHRE_HORIZONT - 1):
        a = kal.jahr_analyse(n)
        assert a["laengen"] == [s.zyklus_q, s.zyklus_q + 1] and a["zwei_q"] == kal.sprung(n)
        assert len(a["abstaende"]) == 2 and a["abstaende"][1] - a["abstaende"][0] == 1
        assert len(a["je_tag"]) <= 2 and a["je_tag"][-1] - a["je_tag"][0] <= 1
        assert a["max_abw_q"] <= F(1, 2)
    k0 = kal.koordinaten(0)
    assert (k0.art, k0.karte, k0.jahr, k0.tag, k0.zyklus, k0.tick, k0.quant) == ("normal", 0, 0, 0, 0, 0, 0)
    rnd = random.Random(seed)
    t_ende = kal.grenze(kal.c_max)
    punkte = [rnd.randrange(0, t_ende) for _ in range(stichproben)]
    grenzen = [rnd.randrange(1, kal.c_max) for _ in range(3000)] + [n * kal.Z for n in range(1, JAHRE_HORIZONT)]
    for c in grenzen:
        b0 = kal.grenze(c)
        punkte += [b0 - 2, b0 - 1, b0, b0 + 1, b0 + s.k * s.N - 1]
        vor = kal.koordinaten(b0 - 1)
        assert vor.art == "nd_zyklus" and vor.index == -1
        assert kal.grenze(c) - kal.grenze(c - 1) in (s.zyklus_q, s.zyklus_q + 1)
    for p in punkte:
        k = kal.koordinaten(p)
        assert kal.zeitpunkt(k) == p and kal.koordinaten(kal.zeitpunkt(k)) == k
    for n in range(0, JAHRE_HORIZONT + 1, 7):
        assert kal.jahresanfang(n) == runden(anker.soll(n))
    ok.append(f"Verteilte Zaehlung: Zyklen 1519/1520 q, 2-q-Nulldurchgaenge = Jahressprung, Zyklusgrenzen <= q/2, "
                      f"{len(punkte)} Punkte Hin- und Rueckweg, -1 vor jeder Null, 00 = alle Kalenderkoordinaten 0")

    h = herleitung()
    if h is None:
        ok.append("Herleitung uebersprungen (PyEphem/NumPy fehlt)")
    else:
        assert abs(h["b"] - ANKER_B) <= 3 and h["g"] == ANKER_G
        lam = sonnenlaenge_scheinbar(float(EPOCHE_JD_TT))
        assert abs(((systemlaenge(lam) + 180) % 360) - 180) < 1e-6
        ok.append(f"Herleitung reproduziert b = {h['b']}, g = {h['g']}; Abweichung vom geglaetteten Verlauf "
                  f"<= {h['max_abw_trend_s']:.1f} s; Sonne bei 00 auf 0 Grad Systemlaenge")
    return ok


def bericht_standard() -> None:
    s = Struktur()
    q = float(s.q_s)
    anker = DefinierterAnker(s)
    kal = VerteilterKalender(s, anker)
    print("FESTLEGUNG")
    print(f"  {JJ} (Durchgang 00, Starttag): {KALIBRIERPUNKT_TEXT}; TT {jd_zu_text(EPOCHE_JD_TT)}")
    print(f"  Systemzeit = UTC + 1 Ju, 1 Jules = {float(JULES_S):.3f} s = {float(s.jules_q):.5f} q; "
          f"Systemzeit - TT = {float(SYSTEMZEIT_MINUS_TT) * 1000:+.0f} ms; Ablesung bei {JJ}: {jd_zu_text(EPOCHE_JD_SYS)}")
    print(f"  lambda0 = {LAMBDA0_GRAD:.5f} Grad = {tierkreis_text(LAMBDA0_GRAD)}; Systemlaenge = tropisch - lambda0")
    print(f"  Anker: tau(x) = {s.jahr_q} x + ({anker.b} x {'-' if anker.g < 0 else '+'} {abs(anker.g)} x^2) / {anker.d} q")
    Js = [kal.sprung(n) for n in range(JAHRE_HORIZONT)]
    print(f"  Jahressprung J: {Js[0]} q im ersten Jahr ({float(anker.sprung(0)) * q:.2f} s), "
          f"{min(Js)} bis {max(Js)} q ueber {JAHRE_HORIZONT} Jahre")
    ks = [str(anker.soll(23 * j) - anker.runde_bei(23 * j, 1)) for j in range(6)]
    print(f"  Rest der Kartenanfaenge (Karte 0-5): {', '.join(ks)} q ...")
    for n in (0, 483, JAHRE_HORIZONT - 1):
        a = kal.jahr_analyse(n)
        print(f"  Jahr {n} (ab 00): Zykluslaengen {a['laengen']}, 2-q-Nulldurchgaenge {a['zwei_q']}, "
              f"Abstand {a['abstaende']} Zyklen, je Tag {a['je_tag']}")
    for t in (0, s.k * s.N, s.zyklus_q, kal.grenze(kal.Z) - 1, kal.grenze(kal.Z)):
        print(f"  t = {t}: {kal.koordinaten(t).text()}")
    h = herleitung()
    if h:
        nat = h["natur_min"]
        print(f"  Herleitung: wahres Sonnenjahr bei lambda0 im Mittel {h['jahr_tage']:.6f} d; "
              f"Streuung um den Trend {h['streuung_vorher_min']:.2f} min, nach 8 Termen {h['streuung_rest_min']:.2f} min")
        print(f"  Natur - Definition: bei 00 {nat[0]:+.3f} min, Mittel {nat.mean():+.2f} min "
              f"(bei 00 eingefrorener Versatz {h['mittel_natur_min']:+.2f} min), Spanne {nat.min():+.2f} bis "
              f"{nat.max():+.2f} min; Anker gegen geglaetteten Verlauf <= {h['max_abw_trend_s']:.1f} s")
        for amp, (name, hh, periode) in h["terme"]:
            print(f"    {name:24s} h={hh}  Periode {periode:6.2f} J  Amplitude {amp:.2f} min")
    print()


if __name__ == "__main__":
    if "platon" in sys.argv[1:]:
        bericht_platon()
        sys.exit(0)
    for zeile in (pruefe_festlegung() + pruefe_mond() + pruefe_pol() + pruefe_dt() + pruefe_epizykel()
                  + pruefe_finsternis_gezeiten() + pruefe_platon() + pruefe()):
        print("OK  ", zeile)
    print()
    bericht_standard()
    print("REFERENZ: Fruehlingspunkt-Variante (Epoche mittlerer Fruehlingspunkt 2027, Tick-/q-Modus)")
    bericht()
    segmentstudie()
    bericht_drehachse()
    bericht_mond()
    bericht_pol()
    bericht_dt()
    bericht_epizykel()
    bericht_finsternis_gezeiten()

# (c) 2026 Joern Christian Anders - erarbeitet mit Unterstuetzung von Claude (Anthropic)
# Zusaetzliche mathematische Pruefung und Demonstrator-Korrekturen: ChatGPT (OpenAI), 04.11.2026.
