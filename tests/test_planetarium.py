"""Unabhängige geometrische Sollfälle des neuen 3D-Modells (Standardbibliothek)."""
import json
import math
import unittest

from planetarium import (
    EXTRA, ELEMENTS, kepler_eccentric_anomaly, orbital_elements,
    orbital_position, planet_state,
)
from zyklus23 import DefinierterAnker, Struktur, VerteilterKalender


class KeplerTests(unittest.TestCase):
    def test_circle_and_apsides(self):
        self.assertEqual(kepler_eccentric_anomaly(0, 0.7), 0)
        self.assertAlmostEqual(kepler_eccentric_anomaly(0.7, 0), 0.7, places=14)
        self.assertAlmostEqual(kepler_eccentric_anomaly(math.pi, 0.7), math.pi, places=13)
        self.assertAlmostEqual(kepler_eccentric_anomaly(-math.pi, 0.7), -math.pi, places=13)

    def test_known_anomaly(self):
        # E=pi/2, e=1/2 gives M=pi/2-1/2 independently of the solver.
        self.assertAlmostEqual(kepler_eccentric_anomaly(math.pi / 2 - 0.5, 0.5), math.pi / 2, places=12)

    def test_equation_including_high_eccentricity(self):
        for eccentricity in (0.0, 0.2, 0.8, 0.999):
            for mean in (-17, -math.pi, -0.001, 0, 0.001, 0.6, math.pi, 100):
                value = kepler_eccentric_anomaly(mean, eccentricity)
                self.assertLess(abs(value - eccentricity * math.sin(value) - math.remainder(mean, math.tau)), 3e-13)

    def test_invalid_eccentricity(self):
        for eccentricity in (-1, 1, float("nan")):
            with self.assertRaises(ValueError):
                kepler_eccentric_anomaly(0.2, eccentricity)


class OrbitTests(unittest.TestCase):
    def test_perihelion_and_aphelion(self):
        # Focus-centred ellipse a=2, e=1/4 -> peri=1.5 and aphelion=2.5.
        self.assertEqual(orbital_position(2, 0.25, 0, 0, 0, 0), [1.5, 0.0, 0.0])
        aphelion = orbital_position(2, 0.25, 0, 0, 0, math.pi)
        self.assertAlmostEqual(aphelion[0], -2.5, places=13)
        self.assertAlmostEqual(aphelion[1], 0, places=13)

    def test_inclination_rotates_into_z(self):
        # Circular orbit, 90° inclination: quarter orbit sits on the z-axis.
        point = orbital_position(2, 0, 90, 0, 0, math.pi / 2)
        for actual, expected in zip(point, (0, 0, 2)):
            self.assertAlmostEqual(actual, expected, places=13)

    def test_node_rotation(self):
        point = orbital_position(2, 0, 0, 90, 0, 0)
        for actual, expected in zip(point, (0, 2, 0)):
            self.assertAlmostEqual(actual, expected, places=13)

    def test_rotation_preserves_focus_distance(self):
        a, e, E = 2.3, 0.22, 0.9
        point = orbital_position(a, e, 37, 29, 72, E)
        self.assertAlmostEqual(math.sqrt(sum(x * x for x in point)), a * (1 - e * math.cos(E)), places=13)

    def test_outer_planet_correction_present(self):
        # At T=0, the cosine coefficient c survives; all other extra terms vanish.
        for name in EXTRA:
            base, _ = ELEMENTS[name]
            self.assertAlmostEqual(orbital_elements(name, 0)["mean_anomaly"], base[3] - base[4] + EXTRA[name][1], places=12)


class ResponseTests(unittest.TestCase):
    def test_sun_eight_planets_and_closed_orbits(self):
        result = planet_state(0)
        self.assertEqual(result["utc"], "2029-07-12T22:00:00Z")
        self.assertEqual(result["q"], "0")
        self.assertEqual([b["id"] for b in result["bodies"]], ["sun", "mercury", "venus", "earth", "mars", "jupiter", "saturn", "uranus", "neptune"])
        self.assertEqual(result["bodies"][0]["position_au"], [0, 0, 0])
        self.assertEqual(result["bodies"][0]["orbit_au"], [])
        for body in result["bodies"][1:]:
            self.assertEqual(len(body["orbit_au"]), 129)
            self.assertEqual(body["orbit_au"][0], body["orbit_au"][-1])
            for point in body["orbit_au"]:
                radius = math.sqrt(sum(x * x for x in point))
                self.assertGreaterEqual(radius + 1e-12, body["a_au"] * (1 - body["eccentricity"]))
                self.assertLessEqual(radius - 1e-12, body["a_au"] * (1 + body["eccentricity"]))
                self.assertTrue(all(math.isfinite(x) for x in point))
        json.dumps(result, allow_nan=False)

    def test_time_change_and_horizon_end(self):
        calendar = VerteilterKalender(Struktur(), DefinierterAnker())
        end_q = calendar.grenze(calendar.c_max)
        initial = planet_state(0)
        after = planet_state(calendar.jahresanfang(1))
        self.assertNotEqual(initial["bodies"][1]["position_au"], after["bodies"][1]["position_au"])
        self.assertEqual(len(planet_state(end_q - 1)["bodies"]), 9)
        for invalid in (-1, end_q, True, 0.5):
            with self.assertRaises(ValueError):
                planet_state(invalid)


if __name__ == "__main__":
    unittest.main(verbosity=2)
