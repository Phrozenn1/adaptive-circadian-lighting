"""Tests for binary sensor platform."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
import tests  # noqa: F401

from custom_components.adaptive_circadian_lighting.binary_sensor import (
    AdaptiveOccupancyBinarySensor,
    async_setup_entry,
)
from custom_components.adaptive_circadian_lighting.const import DOMAIN
from custom_components.adaptive_circadian_lighting.presence_manager import (
    STATE_DIMMED,
    STATE_OCCUPIED,
    STATE_OFF,
)


class DummyConfigEntry:
    def __init__(self, entry_id="test_entry_id", title="Living Room"):
        self.entry_id = entry_id
        self.title = title
        self.data = {}
        self.options = {}


class TestBinarySensor(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.hass = MagicMock()
        self.entry = DummyConfigEntry()
        self.coordinator = MagicMock()
        self.coordinator.name = "Adaptive Circadian Living Room"
        self.hass.data = {DOMAIN: {self.entry.entry_id: self.coordinator}}

    async def test_async_setup_entry_with_presence_manager(self):
        self.coordinator.presence_mgr = MagicMock()
        entities = []
        async_add = lambda ents: entities.extend(ents)

        await async_setup_entry(self.hass, self.entry, async_add)
        self.assertEqual(len(entities), 1)
        self.assertIsInstance(entities[0], AdaptiveOccupancyBinarySensor)

    async def test_async_setup_entry_without_presence_manager(self):
        self.coordinator.presence_mgr = None
        entities = []
        async_add = lambda ents: entities.extend(ents)

        await async_setup_entry(self.hass, self.entry, async_add)
        self.assertEqual(len(entities), 0)

    def test_occupancy_binary_sensor_states(self):
        pm = MagicMock()
        pm.room_state = STATE_OFF
        pm.is_occupied.return_value = False
        pm.sensors = ["binary_sensor.kitchen_motion"]
        pm.last_motion_time = datetime(2026, 11, 8, 8, 30, 0, tzinfo=timezone.utc)
        pm.last_turned_off_time = None
        self.coordinator.presence_mgr = pm

        sensor = AdaptiveOccupancyBinarySensor(self.coordinator, self.entry)
        self.assertEqual(sensor.unique_id, f"{self.entry.entry_id}_occupancy")
        self.assertFalse(sensor.is_on)

        # When room_state is OCCUPIED
        pm.room_state = STATE_OCCUPIED
        self.assertTrue(sensor.is_on)

        # When room_state is DIMMED, but sensor is still reporting triggered
        pm.room_state = STATE_DIMMED
        pm.is_occupied.return_value = True
        self.assertTrue(sensor.is_on)

        # When room_state is DIMMED and sensors are clear
        pm.room_state = STATE_DIMMED
        pm.is_occupied.return_value = False
        self.assertFalse(sensor.is_on)

        # Check extra state attributes
        attrs = sensor.extra_state_attributes
        self.assertEqual(attrs["room_state"], STATE_DIMMED)
        self.assertEqual(attrs["sensors"], ["binary_sensor.kitchen_motion"])
        self.assertIn("2026-11-08", attrs["last_motion"])

    async def test_occupancy_binary_sensor_registration(self):
        sensor = AdaptiveOccupancyBinarySensor(self.coordinator, self.entry)
        self.coordinator.register_listener = MagicMock()
        await sensor.async_added_to_hass()
        self.coordinator.register_listener.assert_called_once_with(sensor.async_write_ha_state)


if __name__ == "__main__":
    unittest.main()
