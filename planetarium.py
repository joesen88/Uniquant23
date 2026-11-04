"""Heliozentrisches 3D-Anschauungsmodell ohne externe Laufzeitpakete.

Quelle der Bahnelemente: NASA/JPL Solar System Dynamics,
https://ssd.jpl.nasa.gov/planets/approx_pos.html, Tabellen 2a und 2b,
abgerufen 04.11.2026. Gültigkeit der angepassten Elemente: 3000 v. Chr.
bis 3000 n. Chr.; keine Präzisionsephemeride und keine n-Körper-Integration.

Reihenfolge der Elemente: a [AU], e [dimensionslos], I, L, varpi, Omega
[Grad]. Raten gelten je julianischem Jahrhundert (36525 Tage) ab J2000.
Die JPL-Formel verlangt JDTDB; hier wird ausdrücklich JDTT als Näherung
eingesetzt. Diese Näherung ist für das Anschauungsmodell vorgesehen,
nicht für eine Neudefinition oder Endkalibrierung des Zyklus23-Ankers.
Der Erdmarker ist das Erde-Mond-Baryzentrum. Kein gesondertes Mondmodell.

Autorenbezug: Konzept/Zeitgrundlage Jörn Christian Anders; mathematische
Ausarbeitung des Ausgangsprojekts Claude (Anthropic); dieses neue
3D-Anschauungsmodul und seine Prüfungen ChatGPT (OpenAI).
"""

from __future__ import annotations

import math
from fractions import Fraction

from zyklus23 import (
    DefinierterAnker, EPOCHE_JD_UTC, JAHRE_HORIZONT, SEKUNDEN_PRO_TAG,
    Struktur, VerteilterKalender, jd_tt_aus_systemzeit, jd_zu_text,
)

SOURCE = "https://ssd.jpl.nasa.gov/planets/approx_pos.html"
MODEL = "JPL-Näherungsbahnen, Tabellen 2a/2b (3000 v. Chr. bis 3000 n. Chr.)"
FRAME = "Heliozentrisch; mittlere Ekliptik und Frühlingspunkt J2000; AU"
ORBIT_SEGMENTS = 128

# JPL-Tabelle 2a: Basiswerte und Raten. Diese Tabelle ist die einzige
# Autorität für das neue Planetenmodell; Zyklus23-Zeitkonstanten werden importiert.
ELEMENTS = {
    "mercury": (
        (0.38709843, 0.20563661, 7.00559432, 252.25166724, 77.45771895, 48.33961819),
        (0.0, 0.00002123, -0.00590158, 149472.67486623, 0.15940013, -0.12214182),
    ),
    "venus": (
        (0.72332102, 0.00676399, 3.39777545, 181.97970850, 131.76755713, 76.67261496),
        (-0.00000026, -0.00005107, 0.00043494, 58517.81560260, 0.05679648, -0.27274174),
    ),
    "earth": (
        (1.00000018, 0.01673163, -0.00054346, 100.46691572, 102.93005885, -5.11260389),
        (-0.00000003, -0.00003661, -0.01337178, 35999.37306329, 0.31795260, -0.24123856),
    ),
    "mars": (
        (1.52371243, 0.09336511, 1.85181869, -4.56813164, -23.91744784, 49.71320984),
        (0.00000097, 0.00009149, -0.00724757, 19140.29934243, 0.45223625, -0.26852431),
    ),
    "jupiter": (
        (5.20248019, 0.04853590, 1.29861416, 34.33479152, 14.27495244, 100.29282654),
        (-0.00002864, 0.00018026, -0.00322699, 3034.90371757, 0.18199196, 0.13024619),
    ),
    "saturn": (
        (9.54149883, 0.05550825, 2.49424102, 50.07571329, 92.86136063, 113.63998702),
        (-0.00003065, -0.00032044, 0.00451969, 1222.11494724, 0.54179478, -0.25015002),
    ),
    "uranus": (
        (19.18797948, 0.04685740, 0.77298127, 314.20276625, 172.43404441, 73.96250215),
        (-0.00020455, -0.00001550, -0.00180155, 428.49512595, 0.09266985, 0.05739699),
    ),
    "neptune": (
        (30.06952752, 0.00895439, 1.77005520, 304.22289287, 46.68158724, 131.78635853),
        (0.00006447, 0.00000818, 0.00022400, 218.46515314, 0.01009938, -0.00606302),
    ),
}

# JPL-Tabelle 2b: M-Zusätze b*T² + c*cos(f*T) + s*sin(f*T),
# alle Winkel in Grad; f ist Grad pro julianischem Jahrhundert.
EXTRA = {
    "jupiter": (-0.00012452, 0.06064060, -0.35635438, 38.35125000),
    "saturn": (0.00025899, -0.13434469, 0.87320147, 38.35125000),
    "uranus": (0.00058331, -0.97731848, 0.17689245, 7.67025000),
    "neptune": (-0.00041348, 0.68346318, -0.10162547, 7.67025000),
}

# Nur Darstellung; symbol_size ist eine Zeichenhilfe, kein physischer Radius.
DISPLAY = {
    "sun": ("Sonne", "#ffcb65", 13),
    "mercury": ("Merkur", "#a9a39c", 4),
    "venus": ("Venus", "#e3c28b", 6),
    "earth": ("Erde", "#62b5f2", 6),
    "mars": ("Mars", "#ef8c69", 5),
    "jupiter": ("Jupiter", "#d5af88", 10),
    "saturn": ("Saturn", "#ead3a1", 9),
    "uranus": ("Uranus", "#9bdfde", 7),
    "neptune": ("Neptun", "#7a98ed", 7),
}


def kepler_eccentric_anomaly(mean_anomaly: float, eccentricity: float) -> float:
    """Löse E - e sin(E) = M in Radiant; elliptischer Fall 0 <= e < 1.

    Newton mit bewachtem Intervall und Bisektionsrückfall. Der Rückgabewert
    gehört zum modulo 2π auf [-π,π] reduzierten Eingangswinkel.
    """
    if not math.isfinite(mean_anomaly) or not math.isfinite(eccentricity):
        raise ValueError("Kepler-Eingaben müssen endlich sein")
    if not 0 <= eccentricity < 1:
        raise ValueError("Für elliptische Bahnen muss 0 <= e < 1 gelten")
    m = math.remainder(mean_anomaly, math.tau)
    if eccentricity == 0 or m == 0:
        return m
    lo, hi = -math.pi, math.pi
    e_anomaly = m + eccentricity * math.sin(m)
    for _ in range(80):
        residual = e_anomaly - eccentricity * math.sin(e_anomaly) - m
        if abs(residual) <= 2e-14:
            return e_anomaly
        if residual > 0:
            hi = e_anomaly
        else:
            lo = e_anomaly
        candidate = e_anomaly - residual / (1 - eccentricity * math.cos(e_anomaly))
        e_anomaly = candidate if lo < candidate < hi else (lo + hi) / 2
    raise ArithmeticError("Kepler-Iteration konvergierte nicht")


def orbital_elements(body_id: str, centuries: float) -> dict:
    """Momentane angepasste JPL-Elemente einschließlich äußerer M-Terme."""
    base, rate = ELEMENTS[body_id]
    a, e, inc, longitude, perihelion, node = (
        value + drift * centuries for value, drift in zip(base, rate)
    )
    b, c, s, f = EXTRA.get(body_id, (0.0, 0.0, 0.0, 0.0))
    phase = math.radians(f * centuries)
    correction = b * centuries * centuries + c * math.cos(phase) + s * math.sin(phase)
    # dM/dT in Grad/Jahrhundert; die Kreisstudie ist keine Naturperiodenmessung.
    motion = rate[3] - rate[4] + 2 * b * centuries + math.radians(f) * (-c * math.sin(phase) + s * math.cos(phase))
    return {
        "a": a, "e": e, "inclination": inc, "node": node,
        "argument_perihelion": perihelion - node,
        "mean_anomaly": longitude - perihelion + correction,
        "motion": motion,
    }


def orbital_position(a: float, eccentricity: float, inclination_deg: float,
                     node_deg: float, argument_perihelion_deg: float,
                     eccentric_anomaly: float) -> list[float]:
    """Ellipsenpunkt im ekliptikalen J2000-System; E in Radiant, Winkel in Grad."""
    if a <= 0 or not 0 <= eccentricity < 1:
        raise ValueError("a muss positiv sein und e im Bereich [0,1) liegen")
    inc, node, omega = map(math.radians, (inclination_deg, node_deg, argument_perihelion_deg))
    xp = a * (math.cos(eccentric_anomaly) - eccentricity)
    yp = a * math.sqrt(1 - eccentricity * eccentricity) * math.sin(eccentric_anomaly)
    co, so, cnode, snode, ci, si = (
        math.cos(omega), math.sin(omega), math.cos(node), math.sin(node), math.cos(inc), math.sin(inc)
    )
    return [
        (co * cnode - so * snode * ci) * xp + (-so * cnode - co * snode * ci) * yp,
        (co * snode + so * cnode * ci) * xp + (-so * snode + co * cnode * ci) * yp,
        so * si * xp + co * si * yp,
    ]


def planet_state(t_q: int) -> dict:
    """Sonne und acht Planeten zum vorhandenen Zyklus23-Zeitpunkt.

    Alle Bahnen zeigen die am betrachteten Zeitpunkt gültigen Elemente und
    sind keine Planetenspuren über ein Zeitfenster. Die letzte Orbitposition
    ist eine exakte Kopie der ersten, damit die gezeichnete Kurve geschlossen ist.
    """
    if isinstance(t_q, bool) or not isinstance(t_q, int):
        raise ValueError("q muss eine ganze Zahl sein")
    structure = Struktur()
    calendar = VerteilterKalender(structure, DefinierterAnker(structure))
    if not 0 <= t_q < calendar.grenze(calendar.c_max):
        raise ValueError(f"Zeitpunkt außerhalb des Viewerhorizonts von {JAHRE_HORIZONT} Jahren ab jj")
    centuries = (jd_tt_aus_systemzeit(t_q) - 2451545.0) / 36525.0
    # 2029..2995 ist innerhalb des Gültigkeitsbereichs von Tabelle 2a/2b.
    name, color, size = DISPLAY["sun"]
    bodies = [{
        "id": "sun", "name": name, "color": color, "symbol_size": size,
        "position_au": [0.0, 0.0, 0.0], "distance_au": 0.0,
        "a_au": 0.0, "eccentricity": 0.0, "inclination_deg": 0.0,
        "period_days": None, "orbit_au": [],
    }]
    for body_id in ELEMENTS:
        elements = orbital_elements(body_id, centuries)
        a, e, inc = elements["a"], elements["e"], elements["inclination"]
        node, omega = elements["node"], elements["argument_perihelion"]
        eccentric_anomaly = kepler_eccentric_anomaly(math.radians(elements["mean_anomaly"]), e)
        position = orbital_position(a, e, inc, node, omega, eccentric_anomaly)
        orbit = [orbital_position(a, e, inc, node, omega, math.tau * j / ORBIT_SEGMENTS)
                 for j in range(ORBIT_SEGMENTS)]
        orbit.append(orbit[0].copy())
        name, color, size = DISPLAY[body_id]
        bodies.append({
            "id": body_id, "name": name, "color": color, "symbol_size": size,
            "position_au": position, "distance_au": math.sqrt(sum(x * x for x in position)),
            "a_au": a, "eccentricity": e, "inclination_deg": inc,
            "period_days": 360.0 * 36525.0 / abs(elements["motion"]),
            "orbit_au": orbit,
        })
    utc = jd_zu_text(EPOCHE_JD_UTC + Fraction(t_q) * structure.q_s / SEKUNDEN_PRO_TAG).replace(" ", "T") + "Z"
    return {
        "q": str(t_q), "utc": utc, "frame": FRAME, "model": MODEL, "source": SOURCE,
        "bodies": bodies,
        "notes": [
            "JPL-Näherung der Bahnen; keine DE440-Präzisionsephemeride und keine n-Körper-Simulation.",
            "TT wird als Näherung des von JPL vorgesehenen TDB-Zeitarguments verwendet.",
            "Der Erdmarker stellt näherungsweise das Erde-Mond-Baryzentrum dar.",
            "Kugelgrößen sind symbolisch; eine komprimierte Abstandsskala verändert nur die Darstellung.",
            "Bahnen zeigen die am gewählten Zeitpunkt gültigen Elemente; die angezeigte Umlaufdauer ist eine Näherung.",
        ],
    }
