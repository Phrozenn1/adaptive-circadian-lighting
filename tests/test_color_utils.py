"""Tests for color conversion and light service data preparation."""
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
import tests  # noqa: F401

from custom_components.adaptive_circadian_lighting.color_utils import (
    kelvin_to_rgb,
    rgb_to_kelvin,
    prepare_light_service_data,
)
from custom_components.adaptive_circadian_lighting.const import (
    COLOR_MODE_AUTO,
    COLOR_MODE_KELVIN,
    COLOR_MODE_RGB,
)


class TestColorUtils(unittest.TestCase):
    def test_kelvin_to_rgb_ranges(self):
        # 1800K (warm candle / night light): should be high red, moderate green, low blue
        r, g, b = kelvin_to_rgb(1800)
        self.assertEqual(r, 255)
        self.assertTrue(g < 150)
        self.assertTrue(b < 50)

        # 6500K (cool daylight): balanced blue/green
        r, g, b = kelvin_to_rgb(6500)
        self.assertTrue(r > 200)
        self.assertTrue(g > 200)
        self.assertTrue(b > 200)

    def test_rgb_to_kelvin_approximation(self):
        k = rgb_to_kelvin(255, 147, 41)  # approx 2100-2700K warm white
        self.assertTrue(1800 <= k <= 3200)

    def test_prepare_light_service_data_kelvin_mode(self):
        payload = prepare_light_service_data(
            supported_modes=["color_temp"],
            min_kelvin=2200,
            max_kelvin=6500,
            brightness_pct=75,
            target_kelvin=4000,
            mode_pref=COLOR_MODE_KELVIN,
        )
        self.assertEqual(payload["brightness_pct"], 75)
        self.assertEqual(payload["color_temp_kelvin"], 4000)
        self.assertNotIn("rgb_color", payload)

    def test_prepare_light_service_data_rgb_mode(self):
        payload = prepare_light_service_data(
            supported_modes=["rgb"],
            min_kelvin=2200,
            max_kelvin=6500,
            brightness_pct=50,
            target_kelvin=2700,
            mode_pref=COLOR_MODE_RGB,
        )
        self.assertEqual(payload["brightness_pct"], 50)
        self.assertIn("rgb_color", payload)
        self.assertEqual(len(payload["rgb_color"]), 3)

    def test_prepare_light_service_data_auto_mode_deep_night_switch(self):
        # Bulb supports both Kelvin (min 2200K) and RGB.
        # Requested temperature is 1800K (lower than hardware min white 2200K).
        # In AUTO mode, it should switch to RGB to produce deep warm amber!
        payload = prepare_light_service_data(
            supported_modes=["color_temp", "rgb"],
            min_kelvin=2200,
            max_kelvin=6500,
            brightness_pct=1,
            target_kelvin=1800,
            mode_pref=COLOR_MODE_AUTO,
        )
        self.assertIn("rgb_color", payload)
        self.assertNotIn("color_temp_kelvin", payload)

    def test_prepare_light_service_data_auto_mode_daytime_kelvin(self):
        # Daytime 4500K is within 2200K-6500K -> use native color_temp_kelvin
        payload = prepare_light_service_data(
            supported_modes=["color_temp", "rgb"],
            min_kelvin=2200,
            max_kelvin=6500,
            brightness_pct=90,
            target_kelvin=4500,
            mode_pref=COLOR_MODE_AUTO,
        )
        self.assertEqual(payload["color_temp_kelvin"], 4500)
        self.assertNotIn("rgb_color", payload)

    def test_rgb_override_takes_precedence(self):
        payload = prepare_light_service_data(
            supported_modes=["color_temp", "rgb"],
            min_kelvin=2200,
            max_kelvin=6500,
            brightness_pct=5,
            target_kelvin=3000,
            mode_pref=COLOR_MODE_AUTO,
            rgb_override=(255, 50, 0),
        )
        self.assertEqual(payload["rgb_color"], [255, 50, 0])

    def test_prepare_light_service_data_onoff_light(self):
        payload = prepare_light_service_data(
            supported_modes=["onoff"],
            min_kelvin=None,
            max_kelvin=None,
            brightness_pct=80,
            target_kelvin=4000,
        )
        self.assertEqual(payload, {})


if __name__ == "__main__":
    unittest.main()
