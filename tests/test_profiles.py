"""Tests for profile manager."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import tests  # noqa: F401

from datetime import time
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

    def test_sleep_schedule_window_and_transitions(self):
        # Schedule from 23:00 to 06:30
        pm = ProfileManager(
            active_profile=PROFILE_NORMAL,
            sleep_schedule_enable=True,
            sleep_start_time="23:00:00",
            sleep_end_time="06:30:00",
        )

        # Check window calculation across midnight
        self.assertTrue(pm.is_time_in_sleep_window(time(23, 15)))
        self.assertTrue(pm.is_time_in_sleep_window(time(2, 0)))
        self.assertTrue(pm.is_time_in_sleep_window(time(6, 29)))
        self.assertFalse(pm.is_time_in_sleep_window(time(6, 31)))
        self.assertFalse(pm.is_time_in_sleep_window(time(14, 0)))

        # Evaluate schedule: entering sleep window switches profile to sleep
        changed = pm.evaluate_schedule(time(23, 30))
        self.assertTrue(changed)
        self.assertEqual(pm.active_profile, PROFILE_SLEEP)
        self.assertTrue(pm.sleep_activated_by_schedule)

        # Evaluate schedule: leaving sleep window reverts profile to normal
        changed = pm.evaluate_schedule(time(7, 0))
        self.assertTrue(changed)
        self.assertEqual(pm.active_profile, PROFILE_NORMAL)
        self.assertFalse(pm.sleep_activated_by_schedule)


if __name__ == "__main__":
    unittest.main()
