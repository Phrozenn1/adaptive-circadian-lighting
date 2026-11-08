"""Tests for manual override manager and power state handling."""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))
import tests  # noqa: F401

from custom_components.adaptive_circadian_lighting.override_manager import OverrideManager


class MockEvent:
    def __init__(self, entity_id, old_state_str, new_state_str):
        self.data = {
            "entity_id": entity_id,
            "old_state": MagicMock(state=old_state_str),
            "new_state": MagicMock(state=new_state_str),
        }


class TestOverrideManager(unittest.TestCase):
    def setUp(self):
        self.hass = MagicMock()
        self.hass.loop = MagicMock()

    def test_turning_off_light_resets_override_silently(self):
        reset_called = False
        def on_reset(entity_id):
            nonlocal reset_called
            reset_called = True

        mgr = OverrideManager(
            self.hass,
            lights=["light.kitchen"],
            timeout_minutes=60,
            on_override_reset_callback=on_reset,
        )

        # Mark light as manually overridden while it is ON
        mgr.overridden_lights["light.kitchen"] = True
        self.assertTrue(mgr.is_overridden("light.kitchen"))

        # User now turns off the light manually
        off_event = MockEvent("light.kitchen", "on", "off")
        mgr._handle_light_change(off_event)

        # Override must be cleared from memory
        self.assertFalse(mgr.is_overridden("light.kitchen"))
        # But reset callback must NOT have been called (so light is never turned back on!)
        self.assertFalse(reset_called)

    def test_timeout_expiration_resets_override_with_callback(self):
        reset_called = False
        def on_reset(entity_id):
            nonlocal reset_called
            reset_called = True

        mgr = OverrideManager(
            self.hass,
            lights=["light.kitchen"],
            timeout_minutes=60,
            on_override_reset_callback=on_reset,
        )

        mgr.overridden_lights["light.kitchen"] = True
        mgr._handle_timeout("light.kitchen")

        self.assertFalse(mgr.is_overridden("light.kitchen"))
        self.assertTrue(reset_called)

    def test_turning_off_light_triggers_on_lights_off_callback(self):
        off_entity_called = None
        def on_off(entity_id):
            nonlocal off_entity_called
            off_entity_called = entity_id

        mgr = OverrideManager(
            self.hass,
            lights=["light.kitchen"],
            on_lights_off_callback=on_off,
        )

        off_event = MockEvent("light.kitchen", "on", "off")
        mgr._handle_light_change(off_event)

        self.assertEqual(off_entity_called, "light.kitchen")

    def test_turning_on_light_triggers_on_lights_on_callback(self):
        on_entity_called = None
        def on_on(entity_id):
            nonlocal on_entity_called
            on_entity_called = entity_id

        mgr = OverrideManager(
            self.hass,
            lights=["light.kitchen"],
            on_lights_on_callback=on_on,
        )

        on_event = MockEvent("light.kitchen", "off", "on")
        mgr._handle_light_change(on_event)

        self.assertEqual(on_entity_called, "light.kitchen")


if __name__ == "__main__":
    unittest.main()
