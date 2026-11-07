"""Tests for profile manager."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import tests  # noqa: F401

from custom_components.adaptive_circadian_lighting.profiles import ProfileManager
from custom_components.adaptive_circadian_lighting.const import (
    PROFILE_FOCUS,
    PROFILE_MORNING,
    PROFILE_NORMAL,
    PROFILE_SLEEP,
)


class TestProfiles(unittest.TestCase):
    def test_normal_profile_has_no_override(self):
        pm = ProfileManager(active_profile=PROFILE_NORMAL)
        self.assertIsNone(pm.get_profile_override())
        self.assertFalse(pm.is_sleep())

    def test_sleep_profile_override(self):
        pm = ProfileManager(
            active_profile=PROFILE_SLEEP,
            sleep_brightness=1,
            sleep_color_temp=1800,
            sleep_rgb=[255, 45, 0],
        )
        self.assertTrue(pm.is_sleep())
        b, k, rgb = pm.get_profile_override()
        self.assertEqual(b, 1)
        self.assertEqual(k, 1800)
        self.assertEqual(rgb, (255, 45, 0))

    def test_focus_profile_override(self):
        pm = ProfileManager(active_profile=PROFILE_FOCUS)
        b, k, rgb = pm.get_profile_override()
        self.assertEqual(b, 100)
        self.assertTrue(k >= 5500)
        self.assertIsNone(rgb)


if __name__ == "__main__":
    unittest.main()
