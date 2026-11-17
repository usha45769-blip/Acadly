"""Run with:  python -m unittest core.tests   (no database needed)"""
import random
import unittest

from core.services.attendance import attendance_stats
from core.services.gpa import cgpa, sgpa
from core.services.ml import predict_attendance
from core.services.ocr import match_code


class AttendanceTests(unittest.TestCase):
    def test_percentage_and_status(self):
        self.assertEqual(attendance_stats(40, 38)["status"], "safe")
        self.assertEqual(attendance_stats(20, 17)["status"], "borderline")   # exactly 85%
        self.assertEqual(attendance_stats(30, 20)["status"], "short")
        self.assertEqual(attendance_stats(0, 0)["status"], "no-data")

    def test_classes_needed_really_reach_threshold(self):
        for held, att in [(30, 20), (50, 30), (12, 5)]:
            n = attendance_stats(held, att)["need_to_attend"]
            self.assertGreaterEqual((att + n) * 100 / (held + n), 85)
            self.assertLess((att + n - 1) * 100 / (held + n - 1), 85)

    def test_can_miss_stays_above_threshold(self):
        s = attendance_stats(40, 38)
        self.assertGreaterEqual(38 * 100 / (40 + s["can_miss"]), 85)
        self.assertLess(38 * 100 / (40 + s["can_miss"] + 1), 85)


class GpaTests(unittest.TestCase):
    def test_sgpa(self):
        self.assertEqual(sgpa([("O", 4), ("A", 3), ("B+", 3)]), 8.5)

    def test_cgpa_is_credit_weighted(self):
        self.assertEqual(cgpa([(8.5, 22), (7.9, 24)]), 8.19)
        self.assertEqual(cgpa([]), 0.0)


class MlTests(unittest.TestCase):
    def test_falls_back_with_little_data(self):
        r = predict_attendance([], 10, 8, [{"weekday": 0, "hour": 9}] * 10)
        self.assertEqual(r["model"], "current-rate")
        self.assertAlmostEqual(r["projected_pct"], 80.0, places=1)

    def test_uses_model_with_enough_data(self):
        random.seed(2)
        hist = [{"date": f"2026-09-{7 + i % 20:02d}", "hour": 9 + i % 6, "present": int(random.random() < .7)}
                for i in range(30)]
        r = predict_attendance(hist, 5, 4, [{"weekday": i % 6, "hour": 9 + i % 6} for i in range(30)])
        self.assertEqual(r["model"], "logistic-regression")
        self.assertTrue(0 <= r["projected_pct"] <= 100)

    def test_all_present_does_not_crash(self):
        hist = [{"date": f"2026-09-{7 + i:02d}", "hour": 9, "present": 1} for i in range(15)]
        r = predict_attendance(hist, 0, 0, [{"weekday": 0, "hour": 9}] * 5)
        self.assertEqual(r["projected_pct"], 100.0)


class OcrMatchTests(unittest.TestCase):
    AL = {"CN": "CN", "PE": "PE", "RM": "RM", "TOC": "TOC", "DEPARTMENT ACTIVITIES": "act:Dept"}

    def test_short_codes_do_not_match_inside_words(self):
        self.assertEqual(match_code("Department Activities", self.AL), "act:Dept")

    def test_bracketed_tutorial_marker(self):
        self.assertEqual(match_code("RM[T]", self.AL), "RM")
        self.assertEqual(match_code("TOC|T]", self.AL), "TOC")

    def test_noise_returns_none(self):
        self.assertIsNone(match_code("~ . :", self.AL))


if __name__ == "__main__":
    unittest.main()
