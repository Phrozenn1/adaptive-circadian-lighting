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

    def test_no_false_override_during_transition_window(self):
        mgr = OverrideManager(self.hass, lights=["light.living_room"])
        # Coordinator commanded a 5-second transition to 70% brightness (179)
        mgr.record_sent_state("light.living_room", {
            "brightness_pct": 70,
            "color_temp_kelvin": 3000,
            "transition": 5.0,
        })

        # Halfway through the transition (2 seconds later), light reports ramp state
        event = MagicMock()
        event.data = {
            "entity_id": "light.living_room",
            "old_state": MagicMock(state="on", attributes={"brightness": 100, "color_temp_kelvin": 2700}),
            "new_state": MagicMock(state="on", attributes={"brightness": 140, "color_temp_kelvin": 2850}),
        }
        mgr._handle_light_change(event)

        self.assertFalse(mgr.is_overridden("light.living_room"))

    def test_no_false_override_on_brightness_pct_scaling(self):
        mgr = OverrideManager(self.hass, lights=["light.living_room"])
        # Coordinator sent brightness_pct: 50 -> 128 (in 0-255 scale)
        mgr.record_sent_state("light.living_room", {
            "brightness_pct": 50,
            "color_temp_kelvin": 3500,
            "transition": 0.0,
        })
        # Simulate elapsed time beyond transition window
        from datetime import datetime, timezone, timedelta
        mgr._last_sent_states["light.living_room"]["timestamp"] = datetime.now(timezone.utc) - timedelta(seconds=10)

        # Light reports 127 in 0-255 scale (due to integer rounding in Zigbee bulb)
        event = MagicMock()
        event.data = {
            "entity_id": "light.living_room",
            "old_state": MagicMock(state="on", attributes={"brightness": 255, "color_temp_kelvin": 3500}),
            "new_state": MagicMock(state="on", attributes={"brightness": 127, "color_temp_kelvin": 3500}),
        }
        mgr._handle_light_change(event)

        self.assertFalse(mgr.is_overridden("light.living_room"))

    def test_no_false_override_on_kelvin_mireds_rounding(self):
        mgr = OverrideManager(self.hass, lights=["light.living_room"])
        # Coordinator commanded 3000K (which is 333.33 mireds)
        mgr.record_sent_state("light.living_room", {
            "brightness_pct": 80,
            "color_temp_kelvin": 3000,
            "transition": 0.0,
        })
        from datetime import datetime, timezone, timedelta
        mgr._last_sent_states["light.living_room"]["timestamp"] = datetime.now(timezone.utc) - timedelta(seconds=10)

        # Light reports 3003K because Zigbee hardware stored 333 mireds (1000000 / 333 = 3003)
        event = MagicMock()
        event.data = {
            "entity_id": "light.living_room",
            "old_state": MagicMock(state="on", attributes={"brightness": 204, "color_temp_kelvin": 4000}),
            "new_state": MagicMock(state="on", attributes={"brightness": 204, "color_temp_kelvin": 3003}),
        }
        mgr._handle_light_change(event)

        self.assertFalse(mgr.is_overridden("light.living_room"))

    def test_real_manual_change_triggers_override(self):
        mgr = OverrideManager(self.hass, lights=["light.living_room"])
        mgr.record_sent_state("light.living_room", {
            "brightness_pct": 50,
            "color_temp_kelvin": 3000,
            "transition": 0.0,
        })
        from datetime import datetime, timezone, timedelta
        mgr._last_sent_states["light.living_room"]["timestamp"] = datetime.now(timezone.utc) - timedelta(seconds=10)

        # User drags dimmer slider to 100% (255) and 5500K
        event = MagicMock()
        event.data = {
            "entity_id": "light.living_room",
            "old_state": MagicMock(state="on", attributes={"brightness": 128, "color_temp_kelvin": 3000}),
            "new_state": MagicMock(state="on", attributes={"brightness": 255, "color_temp_kelvin": 5500}),
        }
        mgr._handle_light_change(event)

        self.assertTrue(mgr.is_overridden("light.living_room"))

    def test_old_state_none_does_not_trigger_override(self):
        # On HA startup or initial entity discovery, old_state is None
        mgr = OverrideManager(self.hass, lights=["light.living_room"])
        event = MagicMock()
        event.data = {
            "entity_id": "light.living_room",
            "old_state": None,
            "new_state": MagicMock(state="on", attributes={"brightness": 255, "color_temp_kelvin": 3000}),
        }
        mgr._handle_light_change(event)
        self.assertFalse(mgr.is_overridden("light.living_room"))

    def test_none_attributes_do_not_crash_or_override(self):
        # Attributes can contain None for brightness or color_temp_kelvin (e.g. RGB or transitioning lights)
        mgr = OverrideManager(self.hass, lights=["light.living_room"])
        event = MagicMock()
        event.data = {
            "entity_id": "light.living_room",
            "old_state": MagicMock(state="on", attributes={"brightness": None, "color_temp_kelvin": None}),
            "new_state": MagicMock(state="on", attributes={"brightness": None, "color_temp_kelvin": None}),
        }
        # Must not raise TypeError
        mgr._handle_light_change(event)
        self.assertFalse(mgr.is_overridden("light.living_room"))

    def test_callback_decorator_present(self):
        mgr = OverrideManager(self.hass, lights=["light.living_room"])
        self.assertTrue(getattr(mgr._handle_light_change, "_hass_callback", False))

    def test_no_false_override_when_bulb_omits_color_attributes(self):
        # Many Zigbee bulbs (e.g. Ikea / Hue) report brightness updates without color_temp_kelvin
        mgr = OverrideManager(self.hass, lights=["light.living_room"])
        mgr.record_sent_state("light.living_room", {
            "brightness_pct": 80,
            "color_temp_kelvin": 3200,
            "transition": 0.0,
        })
        from datetime import datetime, timezone, timedelta
        mgr._last_sent_states["light.living_room"]["timestamp"] = datetime.now(timezone.utc) - timedelta(seconds=10)

        # Light reports 204 brightness (80%), but color_temp_kelvin is None in this state report
        event = MagicMock()
        event.data = {
            "entity_id": "light.living_room",
            "old_state": MagicMock(state="on", attributes={"brightness": 100, "color_temp_kelvin": 2700}),
            "new_state": MagicMock(state="on", attributes={"brightness": 204, "color_temp_kelvin": None}),
        }
        mgr._handle_light_change(event)
        self.assertFalse(mgr.is_overridden("light.living_room"))

    def test_no_false_override_when_brightness_matches_expected_even_if_old_different(self):
        # Light transitioned from 100 to 255 because of coordinator command
        mgr = OverrideManager(self.hass, lights=["light.living_room"])
        mgr.record_sent_state("light.living_room", {
            "brightness_pct": 100,  # 255
            "color_temp_kelvin": 4000,
            "transition": 0.0,
        })
        from datetime import datetime, timezone, timedelta
        mgr._last_sent_states["light.living_room"]["timestamp"] = datetime.now(timezone.utc) - timedelta(seconds=10)

        # Bulb reports 254 (Ikea/Hue max is 254)
        event = MagicMock()
        event.data = {
            "entity_id": "light.living_room",
            "old_state": MagicMock(state="on", attributes={"brightness": 100, "color_temp_kelvin": 4000}),
            "new_state": MagicMock(state="on", attributes={"brightness": 254, "color_temp_kelvin": 4000}),
        }
        mgr._handle_light_change(event)
        self.assertFalse(mgr.is_overridden("light.living_room"))

    def test_gradual_rotary_dimming_detected_as_override(self):
        # User dims kitchen light gradually using a rotary dimmer (steps of <= 8 units)
        mgr = OverrideManager(self.hass, lights=["light.kitchen"])
        mgr.record_sent_state("light.kitchen", {
            "brightness_pct": 100,  # 255
            "color_temp_kelvin": 4000,
            "transition": 0.0,
        })
        from datetime import datetime, timezone, timedelta
        mgr._last_sent_states["light.kitchen"]["timestamp"] = datetime.now(timezone.utc) - timedelta(seconds=10)

        # Step 1: 255 -> 250 (diff 5 <= 15)
        e1 = MagicMock()
        e1.data = {
            "entity_id": "light.kitchen",
            "old_state": MagicMock(state="on", attributes={"brightness": 255, "color_temp_kelvin": 4000}),
            "new_state": MagicMock(state="on", attributes={"brightness": 250, "color_temp_kelvin": 4000}),
        }
        mgr._handle_light_change(e1)
        self.assertFalse(mgr.is_overridden("light.kitchen"))

        # Step 2: 250 -> 244 (diff 6 <= 8, but total departure from 255 is 11 <= 15)
        e2 = MagicMock()
        e2.data = {
            "entity_id": "light.kitchen",
            "old_state": MagicMock(state="on", attributes={"brightness": 250, "color_temp_kelvin": 4000}),
            "new_state": MagicMock(state="on", attributes={"brightness": 244, "color_temp_kelvin": 4000}),
        }
        mgr._handle_light_change(e2)
        self.assertFalse(mgr.is_overridden("light.kitchen"))

        # Step 3: 244 -> 235 (diff 9, total departure from 255 is 20 > 15)
        e3 = MagicMock()
        e3.data = {
            "entity_id": "light.kitchen",
            "old_state": MagicMock(state="on", attributes={"brightness": 244, "color_temp_kelvin": 4000}),
            "new_state": MagicMock(state="on", attributes={"brightness": 235, "color_temp_kelvin": 4000}),
        }
        mgr._handle_light_change(e3)
        self.assertTrue(mgr.is_overridden("light.kitchen"))

        # Step 4: 235 -> 230 (further dimming while already overridden updates override state)
        e4 = MagicMock()
        e4.data = {
            "entity_id": "light.kitchen",
            "old_state": MagicMock(state="on", attributes={"brightness": 235, "color_temp_kelvin": 4000}),
            "new_state": MagicMock(state="on", attributes={"brightness": 230, "color_temp_kelvin": 4000}),
        }
        mgr._handle_light_change(e4)
        self.assertTrue(mgr.is_overridden("light.kitchen"))

    def test_dimmer_adjustment_during_transition_outside_ramp_detected(self):
        mgr = OverrideManager(self.hass, lights=["light.kitchen"])
        mgr.record_sent_state("light.kitchen", {
            "brightness_pct": 70,  # 179
            "color_temp_kelvin": 4000,
            "transition": 5.0,
        })
        # Coordinator is ramping from 100 to 179 over 5 seconds.
        # User suddenly turns dimmer down to 40 (outside ramp [95, 184])
        event = MagicMock()
        event.data = {
            "entity_id": "light.kitchen",
            "old_state": MagicMock(state="on", attributes={"brightness": 100, "color_temp_kelvin": 4000}),
            "new_state": MagicMock(state="on", attributes={"brightness": 40, "color_temp_kelvin": 4000}),
        }
        mgr._handle_light_change(event)
        self.assertTrue(mgr.is_overridden("light.kitchen"))

    def test_light_turned_on_from_off_does_not_trigger_override(self):
        mgr = OverrideManager(self.hass, lights=["light.kitchen"])
        mgr.record_sent_state("light.kitchen", {
            "brightness_pct": 100,  # 255
            "color_temp_kelvin": 4000,
            "transition": 0.0,
        })
        # Light was OFF and turned ON (e.g. motion sensor or wall toggle)
        # It must NOT be marked as an override so coordinator can adapt it smoothly!
        event = MagicMock()
        event.data = {
            "entity_id": "light.kitchen",
            "old_state": MagicMock(state="off"),
            "new_state": MagicMock(state="on", attributes={"brightness": 60, "color_temp_kelvin": 2700}),
        }
        mgr._handle_light_change(event)
        self.assertFalse(mgr.is_overridden("light.kitchen"))

    def test_heartbeat_or_ping_does_not_trigger_override(self):
        # When a Zigbee bulb reports a state heartbeat where no lighting attributes changed
        mgr = OverrideManager(self.hass, lights=["light.kitchen"])
        mgr.record_sent_state("light.kitchen", {
            "brightness_pct": 100,  # 255
            "color_temp_kelvin": 4000,
            "transition": 0.0,
        })
        from datetime import datetime, timezone, timedelta
        mgr._last_sent_states["light.kitchen"]["timestamp"] = datetime.now(timezone.utc) - timedelta(seconds=30)

        # Light is at 200, 3000K. State event arrives where brightness and color did NOT change
        event = MagicMock()
        event.data = {
            "entity_id": "light.kitchen",
            "old_state": MagicMock(state="on", attributes={"brightness": 200, "color_temp_kelvin": 3000}),
            "new_state": MagicMock(state="on", attributes={"brightness": 200, "color_temp_kelvin": 3000}),
        }
        mgr._handle_light_change(event)
        self.assertFalse(mgr.is_overridden("light.kitchen"))

    def test_multipacket_zigbee_update_does_not_trigger_override(self):
        # Coordinator sent brightness 200 and kelvin 4000
        mgr = OverrideManager(self.hass, lights=["light.kitchen"])
        mgr.record_sent_state("light.kitchen", {
            "brightness": 200,
            "color_temp_kelvin": 4000,
            "transition": 0.0,
        })

        # Packet 1: brightness reached 200, but kelvin packet hasn't arrived yet (still 2700)
        e1 = MagicMock()
        e1.data = {
            "entity_id": "light.kitchen",
            "old_state": MagicMock(state="on", attributes={"brightness": 100, "color_temp_kelvin": 2700}),
            "new_state": MagicMock(state="on", attributes={"brightness": 200, "color_temp_kelvin": 2700}),
        }
        mgr._handle_light_change(e1)
        self.assertFalse(mgr.is_overridden("light.kitchen"))

        # Packet 2: kelvin reached 4000, brightness is 200
        e2 = MagicMock()
        e2.data = {
            "entity_id": "light.kitchen",
            "old_state": MagicMock(state="on", attributes={"brightness": 200, "color_temp_kelvin": 2700}),
            "new_state": MagicMock(state="on", attributes={"brightness": 200, "color_temp_kelvin": 4000}),
        }
        mgr._handle_light_change(e2)
        self.assertFalse(mgr.is_overridden("light.kitchen"))

    def test_dimmable_only_bulb_does_not_trigger_override(self):
        # Dimmable bulb without color temp support
        mgr = OverrideManager(self.hass, lights=["light.dimmable"])
        mgr.record_sent_state("light.dimmable", {
            "brightness": 180,
            "color_temp_kelvin": None,
            "transition": 0.0,
        })

        # State updates to 180 (no kelvin reported)
        e = MagicMock()
        e.data = {
            "entity_id": "light.dimmable",
            "old_state": MagicMock(state="on", attributes={"brightness": 100}),
            "new_state": MagicMock(state="on", attributes={"brightness": 180}),
        }
        mgr._handle_light_change(e)
        self.assertFalse(mgr.is_overridden("light.dimmable"))


if __name__ == "__main__":
    unittest.main()
