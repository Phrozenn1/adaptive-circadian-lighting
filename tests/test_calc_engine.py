"""Tests for calculation engines (Sun, Hybrid, Curve)."""
import sys
import unittest
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
import tests  # noqa: F401

from custom_components.adaptive_circadian_lighting.calc_engine import (
    CurveCalculator,
    HybridCalculator,
    SunCalculator,
)


class TestCalcEngine(unittest.TestCase):
    def test_sun_calculator_night_and_day(self):
        calc = SunCalculator(
            min_brightness=1,
            max_brightness=100,
            min_kelvin=2000,
            max_kelvin=6000,
        )

        # Deep astronomical night (elevation <= -18)
        b, k, phase = calc.calculate(-20.0)
        self.assertEqual(b, 1)
        self.assertEqual(k, 2000)
        self.assertEqual(phase, "night")

        # Full day (elevation >= 60)
        b, k, phase = calc.calculate(65.0)
        self.assertEqual(b, 100)
        self.assertEqual(k, 6000)
        self.assertEqual(phase, "day")

        # Twilight
        b, k, phase = calc.calculate(-5.0)
        self.assertTrue(1 < b < 100)
        self.assertTrue(2000 < k < 6000)
        self.assertEqual(phase, "twilight")

    def test_hybrid_calculator_anchors(self):
        calc = HybridCalculator(
            min_brightness=1,
            max_brightness=100,
            min_kelvin=2200,
            max_kelvin=5500,
            min_sunrise="06:30",
            max_sunrise="08:30",
            min_sunset="17:00",
            max_sunset="21:30",
        )

        # 04:00 -> Night
        dt_night = datetime(2026, 11, 7, 4, 0, 0)
        b, k, phase = calc.calculate(dt_night)
        self.assertEqual(b, 1)
        self.assertEqual(k, 2200)
        self.assertEqual(phase, "night")

        # 07:30 -> Morning ramp
        dt_ramp = datetime(2026, 11, 7, 7, 30, 0)
        b, k, phase = calc.calculate(dt_ramp)
        self.assertTrue(1 < b < 100)
        self.assertTrue(2200 < k < 5500)
        self.assertEqual(phase, "morning_ramp")

        # 12:00 -> Midday full
        dt_noon = datetime(2026, 11, 7, 12, 0, 0)
        b, k, phase = calc.calculate(dt_noon, solar_elevation=25.0)
        self.assertEqual(b, 100)
        self.assertEqual(k, 5500)
        self.assertEqual(phase, "day")

        # 19:00 -> Evening ramp
        dt_eve = datetime(2026, 11, 7, 19, 0, 0)
        b, k, phase = calc.calculate(dt_eve)
        self.assertTrue(1 < b < 100)
        self.assertEqual(phase, "evening_ramp")

        # 22:30 -> Night
        dt_late = datetime(2026, 11, 7, 22, 30, 0)
        b, k, phase = calc.calculate(dt_late)
        self.assertEqual(b, 1)
        self.assertEqual(k, 2200)
        self.assertEqual(phase, "night")

    def test_curve_calculator_spline(self):
        points = [
            [0.0, 1, 1800],
            [6.0, 10, 2200],
            [12.0, 100, 5500],
            [18.0, 80, 4000],
            [23.0, 1, 1800],
        ]
        calc = CurveCalculator(points)

        # At exact midday
        b, k, _ = calc.calculate(datetime(2026, 11, 7, 12, 0, 0))
        self.assertEqual(b, 100)
        self.assertEqual(k, 5500)

        # Mid-morning (09:00) between 6.0 and 12.0
        b, k, _ = calc.calculate(datetime(2026, 11, 7, 9, 0, 0))
        self.assertTrue(10 < b < 100)
        self.assertTrue(2200 < k < 5500)


if __name__ == "__main__":
    unittest.main()
