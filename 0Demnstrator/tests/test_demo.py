"""Sollbeispiele und angeschlossene HTTP-Wege des Demonstrators."""
import json
import threading
import unittest
from fractions import Fraction as F
from urllib.error import HTTPError
from urllib.request import urlopen

import demo
from START import Handler, ThreadingHTTPServer


class DemoTests(unittest.TestCase):
    def test_known_calendar_boundaries(self):
        first = demo.state(0)
        self.assertEqual(first["calendar"]["year_index"], 0)
        self.assertEqual(first["calendar"]["cycle"], 0)
        self.assertEqual(first["utc"], "2029-07-12T22:00:00.000000Z")
        self.assertEqual(first["system_time"], "2029-07-12T22:01:09.159000Z")
        self.assertEqual(demo.state(1518)["calendar"]["countdown"], -1)
        self.assertEqual(demo.state(1519)["calendar"]["cycle"], 1)
        self.assertEqual(demo.state(425807411)["calendar"]["year_index"], 1)

    def test_two_quantum_zero_crossing(self):
        c = next(c for c in range(1000) if demo.CALENDAR.grenze(c + 1) - demo.CALENDAR.grenze(c) == 1520)
        end = demo.CALENDAR.grenze(c + 1)
        self.assertEqual(demo.state(end - 2)["calendar"]["countdown"], -2)
        self.assertEqual(demo.state(end - 1)["calendar"]["countdown"], -1)
        self.assertEqual(demo.state(end)["calendar"]["quant"], 0)
        self.assertEqual(demo.state(end - 2)["cycle"]["zero_length_q"], "2")

    def test_groups_are_independent_of_count(self):
        q = demo.CALENDAR.jahresanfang(92)
        a, b = demo.state(q, 4), demo.state(q, 6)
        self.assertEqual(a["calendar"], b["calendar"])
        self.assertEqual(a["residual"], b["residual"])
        self.assertEqual((a["group"]["index"], a["group"]["phase"]), (1, 0))
        self.assertEqual((b["group"]["index"], b["group"]["phase"]), (0, 4))
        q = demo.CALENDAR.jahresanfang(529)
        self.assertEqual(demo.state(q, 4)["group"]["phase"], 3)
        self.assertEqual(demo.state(q, 6)["group"]["phase"], 5)

    def test_null_day_and_progress_bounds(self):
        q = demo.CALENDAR.grenze(364 * demo.STRUCTURE.C)
        out = demo.state(q)
        self.assertIsNone(out["calendar"]["month"])
        self.assertIsNone(out["calendar"]["day"])
        self.assertEqual(out["calendar"]["day_of_year"], 364)
        for q in (0, 1518, 1519, q, demo.END_Q - 1):
            for level in demo.state(q)["levels"]:
                self.assertLessEqual(int(level["start_q"]), q)
                self.assertLess(q, int(level["end_q"]))
                self.assertGreaterEqual(level["progress"], 0)
                self.assertLess(level["progress"], 1)

    def test_date_conversion_rounding_and_offsets(self):
        self.assertEqual(demo.date_state("2029-07-13T00:00:00+02:00")["q"], "0")
        self.assertEqual(demo.date_state("2029-07-12T22:00:00.074111Z")["q"], "1")
        self.assertEqual(demo.date_state("2029-07-12T22:00:00.010000Z")["q"], "0")
        for q in (0, 1, 1518, 425807411, demo.END_Q - 1):
            self.assertEqual(demo.date_state(demo.utc_text(q))["q"], str(q))

    def test_exact_year_mean_and_chart_classes(self):
        data = demo.series("year", 0, 529)
        self.assertEqual(data["summary"]["mean_exact_q"], "3/529")
        chart = demo.series("chart", 0, 23)
        self.assertEqual(chart["summary"]["mean_exact_q"], "0")
        self.assertEqual(sorted(F(p["exact_q"]) for p in chart["points"]), [F(k, 23) for k in range(-11, 12)])

    def test_jumps_use_actual_boundaries(self):
        self.assertEqual(demo.jump(1518, "cycle", 1)["q"], "1519")
        self.assertEqual(demo.jump(1518, "year", 1)["q"], "425807411")
        self.assertEqual(demo.jump(0, "quantum", 1)["q"], "1")

    def test_horizon_and_input_errors(self):
        for q in (-1, demo.END_Q, True, 1.5):
            with self.assertRaises(ValueError):
                demo.state(q)
        for g in (0, 5, 4.0, True):
            with self.assertRaises(ValueError):
                demo.state(0, g)
        for args in (("year", 0, 0), ("year", 0, 2001), ("year", 966, 2), ("chart", 42, 2), ("bad", 0, 1)):
            with self.assertRaises(ValueError):
                demo.series(*args)
        for text in ("", "jetzt", "2026-11-04T00:00:00Z", "2029-07-12T21:59:59.999999Z", "2029-07-12T22:00:60Z"):
            with self.assertRaises(ValueError):
                demo.date_state(text)

    def test_visible_checks(self):
        result = demo.checks()
        self.assertTrue(result["passed"])
        self.assertEqual(len(result["checks"]), 10)


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def get(self, path):
        with urlopen(self.url + path, timeout=10) as r:
            return json.load(r)

    def test_public_api_chain(self):
        meta = self.get("/api/overview")
        self.assertEqual(meta["q_seconds"]["exact"], "75/1012")
        self.assertEqual(self.get("/api/state?q=425807411&group=6")["calendar"]["year_index"], 1)
        self.assertEqual(self.get("/api/date?utc=2029-07-12T22:00:00Z")["q"], "0")
        self.assertEqual(self.get("/api/jump?q=0&unit=cycle&delta=1")["q"], "1519")
        self.assertEqual(self.get("/api/series?mode=year&start=0&count=529")["summary"]["mean_exact_q"], "3/529")
        self.assertTrue(self.get("/api/checks")["passed"])
        planets = self.get("/api/planets?q=0")
        self.assertEqual(len(planets["bodies"]), 9)
        self.assertTrue(all(len(b["orbit_au"]) == 129 for b in planets["bodies"] if b["id"] != "sun"))

    def test_api_input_and_path_rejection(self):
        for path, status in (("/api/state?q=-1", 400), ("/api/state?q=abc", 400),
                             ("/api/state?group=5", 400), ("/api/planets?q=-1", 400),
                             ("/api/series?count=3000", 400), ("/../zyklus23.py", 404)):
            with self.assertRaises(HTTPError) as ctx:
                self.get(path)
            self.assertEqual(ctx.exception.code, status)
            self.assertIn("error", json.load(ctx.exception))


if __name__ == "__main__":
    unittest.main()
