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


if __name__ == "__main__":
    unittest.main()
