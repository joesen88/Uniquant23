"""Unabhängige Sollfälle des aus dem Ausgangsprojekt übernommenen Rechenkerns.

Ausführung im Paketverzeichnis: python -m unittest discover -s tests -p test_core.py -v
Nur Standardbibliothek; keine Ephemeriden-/IERS-Downloads.
"""

from datetime import datetime
from fractions import Fraction as F
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import zyklus23 as z


class RoundingTests(unittest.TestCase):
    def test_ties_round_toward_positive_infinity(self):
        for value, expected in [
            (F(-3, 2), -1), (F(-1, 2), 0), (F(1, 2), 1), (F(3, 2), 2),
            (F(49, 100), 0), (F(-51, 100), -1),
        ]:
            with self.subTest(value=value):
                self.assertEqual(z.runden(value), expected)

    def test_quantum_has_independently_derived_si_length(self):
        self.assertEqual(z.Struktur().q_s, F(75, 1012))
        self.assertEqual(z.Struktur().tick_s, F(75, 44))


class DefinedCalendarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.structure = z.Struktur()
        cls.anchor = z.DefinierterAnker(cls.structure)
        cls.calendar = z.VerteilterKalender(cls.structure, cls.anchor)

    def test_known_boundaries(self):
        expected = [
            (0, "normal", 0, 0, 0, 0, 0, 0, None),
            (1518, "nd_zyklus", 0, 0, 0, 0, None, None, -1),
            (1519, "normal", 0, 0, 0, 1, 0, 0, None),
            (425807411, "normal", 0, 1, 0, 0, 0, 0, None),
        ]
        for t, kind, chart, year, day, cycle, tick, quant, countdown in expected:
            with self.subTest(t=t):
                c = self.calendar.koordinaten(t)
                self.assertEqual(
                    (c.art, c.karte, c.jahr, c.tag, c.zyklus, c.tick, c.quant, c.index),
                    (kind, chart, year, day, cycle, tick, quant, countdown),
                )
                self.assertEqual(self.calendar.zeitpunkt(c), t)

    def test_year_residual_period_and_nonzero_mean(self):
        residuals = [self.anchor.soll(n) - self.calendar.jahresanfang(n) for n in range(529)]
        self.assertEqual(sum(residuals), F(3))
        self.assertEqual(sum(residuals) / 529, F(3, 529))
        for n, residual in enumerate(residuals):
            with self.subTest(n=n):
                self.assertEqual(residual, self.anchor.soll(n + 529) - self.calendar.jahresanfang(n + 529))
                self.assertLessEqual(abs(residual), F(1, 2))

    def test_chart_residues_form_all_23_classes(self):
        residuals = [self.anchor.soll(23 * j) - self.calendar.jahresanfang(23 * j) for j in range(23)]
        self.assertEqual(sorted(residuals), [F(k, 23) for k in range(-11, 12)])
        self.assertEqual(sum(residuals), F(0))

    def test_epoch_and_horizon_are_checked(self):
        with self.assertRaises(ValueError):
            self.calendar.koordinaten(-1)
        end = self.calendar.grenze(self.calendar.c_max)
        with self.assertRaises(ValueError):
            self.calendar.koordinaten(end)
        final = self.calendar.koordinaten(end - 1)
        self.assertEqual(self.calendar.zeitpunkt(final), end - 1)


class JulianDateFormattingTests(unittest.TestCase):
    @staticmethod
    def julian_datetime(value):
        delta = value - datetime(2000, 1, 1, 12)
        return F(2451545) + F(delta.days * 86400 + delta.seconds, 86400) + F(delta.microseconds, 86400000000)

    def test_j2000_noon(self):
        self.assertEqual(z.jd_zu_text(F(2451545)), "2000-01-01 12:00:00")

    def test_rounded_midnight_carries_date(self):
        cases = [
            (datetime(1999, 12, 31, 23, 59, 59, 900000), "2000-01-01 00:00:00"),
            (datetime(2000, 1, 1, 23, 59, 59, 900000), "2000-01-02 00:00:00"),
            (datetime(2000, 1, 31, 23, 59, 59, 900000), "2000-02-01 00:00:00"),
            (datetime(2000, 2, 29, 23, 59, 59, 900000), "2000-03-01 00:00:00"),
            (datetime(2000, 12, 31, 23, 59, 59, 900000), "2001-01-01 00:00:00"),
        ]
        for date, expected in cases:
            with self.subTest(date=date):
                self.assertEqual(z.jd_zu_text(self.julian_datetime(date)), expected)


class SplineTests(unittest.TestCase):
    def test_short_and_partial_card_horizons(self):
        reference = z.DirekterAnker(z.Struktur(), z.Modell(), 2000)
        for horizon in (1, 22, 24, 25):
            with self.subTest(horizon=horizon):
                spline = z.SplineAnker(reference, horizon, F(1, 2))
                self.assertTrue(spline.segmente)
                self.assertEqual(spline.segmente[0].n0, 0)
                self.assertEqual(spline.segmente[-1].n1, horizon)
                self.assertEqual(spline.soll(0), reference.soll(0))
                self.assertEqual(spline.soll(horizon), reference.soll(horizon))
                for left, right in zip(spline.segmente, spline.segmente[1:]):
                    self.assertEqual(left.n1, right.n0)
                    self.assertEqual(left.wert(left.n1), right.wert(right.n0))
                    self.assertEqual(left.steigung(left.n1), right.steigung(right.n0))
                with self.assertRaises(ValueError):
                    spline.soll(-1)
                with self.assertRaises(ValueError):
                    spline.soll(horizon + 1)


class UtcConversionTests(unittest.TestCase):
    def test_historical_tai_offsets(self):
        # Sollwerte: TAI−UTC=10,11,32,34,37 s; TT(TAI)−TAI=32,184 s.
        for date, expected in [
            (datetime(1972, 1, 1), 42.184),
            (datetime(1972, 7, 1), 43.184),
            (datetime(2000, 1, 1), 64.184),
            (datetime(2010, 1, 1), 66.184),
            (datetime(2017, 1, 1), 69.184),
        ]:
            with self.subTest(date=date):
                utc_jd = JulianDateFormattingTests.julian_datetime(date)
                tt_jd = z.jd_tt_aus_utc(date.year, date.month, date.day)
                # Float-JD-Auflösung bei heutigen Epochen etwa40µs.
                actual_seconds = float(F(tt_jd) - utc_jd) * 86400
                self.assertAlmostEqual(actual_seconds, expected, delta=0.0001)

    def test_unsupported_or_invalid_utc_is_rejected(self):
        for args in [(1971, 12, 31), (2000, 2, 30), (2000, 13, 1), (2000, 1, 1, 0, 0, 60)]:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    z.jd_tt_aus_utc(*args)

    def test_measured_dut1_uses_the_historical_offset(self):
        # Bei J2000-Mittag ist JD(UTC)=2451545; gemessenes UT1−UTC=+0,2s.
        expected = 2451545.0 + 0.2 / 86400
        self.assertAlmostEqual(
            z.jd_ut1_aus_utc(2000, 1, 1, 12, 0, 0, dut1_s=0.2), expected,
            delta=1e-9,
        )


if __name__ == "__main__":
    unittest.main()
