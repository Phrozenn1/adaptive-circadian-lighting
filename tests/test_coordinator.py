"""Tests for AdaptiveCoordinator presence integration and staged dimming."""
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
import tests  # noqa: F401

from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from custom_components.adaptive_circadian_lighting.coordinator import AdaptiveCoordinator
from custom_components.adaptive_circadian_lighting.const import (
    CONF_LIGHTS,
    CONF_PRESENCE_ENABLE,
    CONF_PRESENCE_SENSORS,
    CONF_DIM_BRIGHTNESS,
)


class DummyConfigEntry:
    def __init__(self, entry_id="test_coordinator_entry", data=None, options=None):
        self.entry_id = entry_id
        self.data = data or {}
        self.options = options or {}


class TestCoordinatorPresence(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.hass = MagicMock()
        self.hass.loop = MagicMock()
        self.hass.services = MagicMock()
        self.hass.services.async_call = AsyncMock()

    def test_auto_enable_presence_when_sensors_configured(self):
        # User configured presence sensors but left presence_enable = False
        entry = DummyConfigEntry(data={
            CONF_LIGHTS: ["light.living_room"],
            CONF_PRESENCE_ENABLE: False,
            CONF_PRESENCE_SENSORS: ["binary_sensor.kitchen_motion"],
        })
        coord = AdaptiveCoordinator(self.hass, entry)
        self.assertIsNotNone(coord.presence_mgr)
        self.assertEqual(coord.presence_mgr.sensors, ["binary_sensor.kitchen_motion"])

    def test_presence_manager_none_when_no_sensors(self):
        entry = DummyConfigEntry(data={
            CONF_LIGHTS: ["light.living_room"],
            CONF_PRESENCE_ENABLE: True,
            CONF_PRESENCE_SENSORS: [],
        })
        coord = AdaptiveCoordinator(self.hass, entry)
        self.assertIsNone(coord.presence_mgr)

    async def test_presence_dim_records_sent_state_to_avoid_false_override(self):
        entry = DummyConfigEntry(data={
            CONF_LIGHTS: ["light.living_room"],
            CONF_PRESENCE_ENABLE: True,
            CONF_PRESENCE_SENSORS: ["binary_sensor.kitchen_motion"],
            CONF_DIM_BRIGHTNESS: 15,
        })
        coord = AdaptiveCoordinator(self.hass, entry)

        # Mock light is on
        st = MagicMock()
        st.state = "on"
        self.hass.states.get.return_value = st

        # Mock override manager
        coord.override_mgr = MagicMock()

        await coord._on_presence_dim()

        # Verify turn_on service called
        self.hass.services.async_call.assert_called_once_with(
            LIGHT_DOMAIN,
            "turn_on",
            {"entity_id": "light.living_room", "brightness_pct": 15, "transition": 3.0},
            blocking=False,
        )

        # Crucial check: sent state was recorded in override manager!
        coord.override_mgr.record_sent_state.assert_called_once_with(
            "light.living_room",
            {"entity_id": "light.living_room", "brightness_pct": 15, "transition": 3.0},
        )

    async def test_presence_turn_on_adaptive_resets_override(self):
        entry = DummyConfigEntry(data={
            CONF_LIGHTS: ["light.living_room"],
            CONF_PRESENCE_ENABLE: True,
            CONF_PRESENCE_SENSORS: ["binary_sensor.kitchen_motion"],
        })
        coord = AdaptiveCoordinator(self.hass, entry)

        coord.override_mgr = MagicMock()
        coord._async_apply_to_light = AsyncMock()
        listener = MagicMock()
        coord.register_listener(listener)

        await coord._on_presence_turn_on_adaptive()

        coord.override_mgr.reset_override.assert_called_once_with(
            "light.living_room", notify_callback=False
        )
        coord._async_apply_to_light.assert_called_once_with(
            "light.living_room", custom_transition=1.0, allow_turn_on=True
        )
        listener.assert_called_once()

    def test_on_presence_state_change_notifies_listeners(self):
        entry = DummyConfigEntry(data={
            CONF_LIGHTS: ["light.living_room"],
            CONF_PRESENCE_ENABLE: True,
            CONF_PRESENCE_SENSORS: ["binary_sensor.kitchen_motion"],
        })
        coord = AdaptiveCoordinator(self.hass, entry)

        listener = MagicMock()
        coord.register_listener(listener)

        coord._on_presence_state_change("occupied")
        listener.assert_called_once()

    def test_handle_light_turned_on_updates_room_state_and_notifies(self):
        entry = DummyConfigEntry(data={
            CONF_LIGHTS: ["light.living_room"],
            CONF_PRESENCE_ENABLE: True,
            CONF_PRESENCE_SENSORS: ["binary_sensor.kitchen_motion"],
        })
        coord = AdaptiveCoordinator(self.hass, entry)
        coord.presence_mgr.room_state = "off"

        listener = MagicMock()
        coord.register_listener(listener)

        coord._handle_light_turned_on("light.living_room")
        self.assertEqual(coord.presence_mgr.room_state, "occupied")
        listener.assert_called_once()

    async def test_presence_restore_manual_ensures_nonzero_brightness(self):
        entry = DummyConfigEntry(data={
            CONF_LIGHTS: ["light.living_room"],
            CONF_PRESENCE_ENABLE: True,
            CONF_PRESENCE_SENSORS: ["binary_sensor.kitchen_motion"],
        })
        coord = AdaptiveCoordinator(self.hass, entry)
        coord._calculate_target_values = MagicMock()
        coord.target_brightness = 75
        coord.target_kelvin = 3000

        # Saved state has brightness=0 or None (from light turn-off event)
        saved_states = {
            "light.living_room": {
                "brightness": 0,
                "color_temp_kelvin": 3000,
            }
        }
        await coord._on_presence_restore_manual(saved_states)

        # Service call must have turned on with fallback target brightness (75%)
        self.hass.services.async_call.assert_called_once_with(
            LIGHT_DOMAIN,
            "turn_on",
            {
                "entity_id": "light.living_room",
                "transition": 1.0,
                "brightness_pct": 75,
                "color_temp_kelvin": 3000,
            },
            blocking=False,
        )

    async def test_async_setup_starts_presence_tracking(self):
        entry = DummyConfigEntry(data={
            CONF_LIGHTS: ["light.living_room"],
            CONF_PRESENCE_ENABLE: True,
            CONF_PRESENCE_SENSORS: ["binary_sensor.kitchen_motion", "binary_sensor.ikea_motion"],
        })
        coord = AdaptiveCoordinator(self.hass, entry)
        coord.presence_mgr = MagicMock()

        await coord.async_setup()
        coord.presence_mgr.start_tracking.assert_called_once()

    def test_presence_sensors_attribute_saved(self):
        entry = DummyConfigEntry(data={
            CONF_LIGHTS: ["light.living_room"],
            CONF_PRESENCE_ENABLE: True,
            CONF_PRESENCE_SENSORS: ["binary_sensor.kitchen_motion", "binary_sensor.ikea_motion"],
        })
        coord = AdaptiveCoordinator(self.hass, entry)
        self.assertEqual(coord.presence_sensors, ["binary_sensor.kitchen_motion", "binary_sensor.ikea_motion"])

    def test_anti_glare_payload_records_sent_state(self):
        entry = DummyConfigEntry(data={
            CONF_LIGHTS: ["light.living_room"],
        })
        coord = AdaptiveCoordinator(self.hass, entry)
        coord.override_mgr = MagicMock()

        payload = coord._get_anti_glare_payload("light.living_room")
        coord.override_mgr.record_sent_state.assert_called_once_with("light.living_room", payload)

    async def test_presence_restore_manual_dimmable_only_light(self):
        entry = DummyConfigEntry(data={
            CONF_LIGHTS: ["light.dimmable_bulb"],
            CONF_PRESENCE_ENABLE: True,
            CONF_PRESENCE_SENSORS: ["binary_sensor.kitchen_motion"],
        })
        coord = AdaptiveCoordinator(self.hass, entry)
        coord._calculate_target_values = MagicMock()
        coord.target_brightness = 50

        # Bulb is dimmable only (does not support color_temp)
        st = MagicMock()
        st.attributes = {"supported_color_modes": ["brightness"]}
        self.hass.states.get.return_value = st

        saved_states = {
            "light.dimmable_bulb": {
                "brightness": 128,
            }
        }
        await coord._on_presence_restore_manual(saved_states)

        call_args = self.hass.services.async_call.call_args[0][2]
        self.assertEqual(call_args["brightness"], 128)
        self.assertNotIn("color_temp_kelvin", call_args)

    def test_notify_listeners_handles_exception_safely(self):
        entry = DummyConfigEntry(data={CONF_LIGHTS: ["light.living_room"]})
        coord = AdaptiveCoordinator(self.hass, entry)

        def bad_listener():
            raise RuntimeError("Failing listener")

        good_called = False
        def good_listener():
            nonlocal good_called
            good_called = True

        coord.register_listener(bad_listener)
        coord.register_listener(good_listener)

        # Must not raise exception and good_listener must still be called
        coord._notify_listeners()
        self.assertTrue(good_called)

    async def test_async_apply_to_light_allow_turn_on_resets_override(self):
        entry = DummyConfigEntry(data={CONF_LIGHTS: ["light.living_room"]})
        coord = AdaptiveCoordinator(self.hass, entry)
        coord.override_mgr.set_manual_override("light.living_room", {"brightness": 200})
        self.assertTrue(coord.override_mgr.is_overridden("light.living_room"))

        st = MagicMock()
        st.state = "off"
        st.attributes = {"supported_color_modes": ["brightness"]}
        self.hass.states.get.return_value = st

        await coord._async_apply_to_light("light.living_room", allow_turn_on=True)

        self.assertFalse(coord.override_mgr.is_overridden("light.living_room"))
        self.hass.services.async_call.assert_called_once()
        self.assertEqual(self.hass.services.async_call.call_args[0][1], "turn_on")

    async def test_async_apply_to_light_blocked_by_override_when_allow_turn_on_false(self):
        entry = DummyConfigEntry(data={CONF_LIGHTS: ["light.living_room"]})
        coord = AdaptiveCoordinator(self.hass, entry)
        coord.override_mgr.set_manual_override("light.living_room", {"brightness": 200})

        st = MagicMock()
        st.state = "on"
        st.attributes = {"supported_color_modes": ["brightness"]}
        self.hass.states.get.return_value = st

        await coord._async_apply_to_light("light.living_room", allow_turn_on=False)
        self.hass.services.async_call.assert_not_called()

    async def test_async_apply_to_light_allow_turn_on_ensures_brightness_even_if_adapt_brightness_disabled(self):
        entry = DummyConfigEntry(data={CONF_LIGHTS: ["light.living_room"]})
        coord = AdaptiveCoordinator(self.hass, entry)
        coord.adapt_brightness_enabled = False
        coord.target_brightness = 80

        st = MagicMock()
        st.state = "off"
        st.attributes = {"supported_color_modes": ["brightness"]}
        self.hass.states.get.return_value = st

        await coord._async_apply_to_light("light.living_room", allow_turn_on=True)

        call_args = self.hass.services.async_call.call_args[0][2]
        self.assertEqual(call_args["brightness_pct"], 80)

    async def test_async_apply_to_light_allow_turn_on_zero_brightness_safeguard(self):
        entry = DummyConfigEntry(data={CONF_LIGHTS: ["light.living_room"]})
        coord = AdaptiveCoordinator(self.hass, entry)
        coord.target_brightness = 0  # e.g. uninitialized or 0

        st = MagicMock()
        st.state = "off"
        st.attributes = {"supported_color_modes": ["brightness"]}
        self.hass.states.get.return_value = st

        await coord._async_apply_to_light("light.living_room", allow_turn_on=True)

        call_args = self.hass.services.async_call.call_args[0][2]
        self.assertEqual(call_args["brightness_pct"], 100)

    async def test_periodic_update_checks_continuous_presence(self):
        entry = DummyConfigEntry(data={
            CONF_LIGHTS: ["light.living_room"],
            CONF_PRESENCE_ENABLE: True,
            CONF_PRESENCE_SENSORS: ["binary_sensor.kitchen_motion"],
        })
        coord = AdaptiveCoordinator(self.hass, entry)
        coord.presence_mgr.check_continuous_presence = MagicMock()

        await coord._async_periodic_update()
        coord.presence_mgr.check_continuous_presence.assert_called_once()

    async def test_presence_restore_manual_error_falls_back_to_adaptive(self):
        entry = DummyConfigEntry(data={
            CONF_LIGHTS: ["light.living_room"],
            CONF_PRESENCE_ENABLE: True,
            CONF_PRESENCE_SENSORS: ["binary_sensor.kitchen_motion"],
        })
        coord = AdaptiveCoordinator(self.hass, entry)
        coord._on_presence_turn_on_adaptive = AsyncMock()

        # Cause exception in restore manual by passing invalid structure
        saved_states = {"light.living_room": None}  # None has no .get()
        await coord._on_presence_restore_manual(saved_states)

        coord._on_presence_turn_on_adaptive.assert_called_once()


if __name__ == "__main__":
    unittest.main()
