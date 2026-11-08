"""Tests for presence manager, staged dimming and manual override memory."""
import sys
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import tests  # noqa: F401

from custom_components.adaptive_circadian_lighting.presence_manager import (
    PresenceManager,
    STATE_DIMMED,
    STATE_OCCUPIED,
    STATE_OFF,
)


class MockState:
    def __init__(self, state: str, attributes: dict = None):
        self.state = state
        self.attributes = attributes or {}


class TestPresenceManager(unittest.TestCase):
    def setUp(self):
        self.hass = MagicMock()
        self.hass.loop = MagicMock()

    def test_save_and_clear_manual_state(self):
        pm = PresenceManager(self.hass, sensors=["binary_sensor.motion"])
        self.assertFalse(pm.has_manual_state())

        pm.save_manual_state("light.desk", {"brightness": 255, "color_temp_kelvin": 5000})
        self.assertTrue(pm.has_manual_state())
        self.assertEqual(pm.saved_manual_states["light.desk"]["brightness"], 255)

        pm.clear_manual_state("light.desk")
        self.assertFalse(pm.has_manual_state())

    def test_is_occupied_detection(self):
        pm = PresenceManager(self.hass, sensors=["binary_sensor.motion_1", "binary_sensor.motion_2"])

        def get_state(entity_id):
            if entity_id == "binary_sensor.motion_1":
                return MockState("off")
            if entity_id == "binary_sensor.motion_2":
                return MockState("on")
            return None

        self.hass.states.get.side_effect = get_state
        self.assertTrue(pm.is_occupied())

    def test_reoccupancy_within_grace_restores_manual(self):
        restore_cb = MagicMock()
        turn_on_adaptive_cb = MagicMock()

        pm = PresenceManager(
            self.hass,
            sensors=["binary_sensor.motion"],
            grace_period=900,
            on_restore_manual_callback=restore_cb,
            on_turn_on_adaptive_callback=turn_on_adaptive_cb,
        )
        pm.save_manual_state("light.kitchen", {"brightness": 200, "color_temp_kelvin": 4000})
        pm.room_state = STATE_OFF
        # Lights turned off 3 minutes ago (well within 15 minute grace period)
        pm.last_turned_off_time = datetime.now(timezone.utc) - timedelta(minutes=3)

        pm._handle_reoccupancy(datetime.now(timezone.utc))

        self.assertEqual(pm.room_state, STATE_OCCUPIED)
        restore_cb.assert_called_once_with(pm.saved_manual_states)

    def test_reoccupancy_beyond_grace_clears_manual(self):
        restore_cb = MagicMock()
        turn_on_adaptive_cb = MagicMock()

        pm = PresenceManager(
            self.hass,
            sensors=["binary_sensor.motion"],
            grace_period=900,  # 15 min
            on_restore_manual_callback=restore_cb,
            on_turn_on_adaptive_callback=turn_on_adaptive_cb,
        )
        pm.save_manual_state("light.kitchen", {"brightness": 200, "color_temp_kelvin": 4000})
        pm.room_state = STATE_OFF
        # Turned off 30 minutes ago (beyond 15 min grace period)
        pm.last_turned_off_time = datetime.now(timezone.utc) - timedelta(minutes=30)

        pm._handle_reoccupancy(datetime.now(timezone.utc))

        # Manual state should have been wiped
        self.assertFalse(pm.has_manual_state())

    def test_aqara_presence_attributes_detection(self):
        # Aqara FP2 / ZHA sensor that has presence or has_target attribute
        pm = PresenceManager(self.hass, sensors=["binary_sensor.aqara_kitchen"])

        # State is 'off' but FP2 detected presence in attributes
        mock_fp2 = MockState("off", {"presence": True, "has_target": True})
        self.hass.states.get.return_value = mock_fp2
        self.assertTrue(pm.is_occupied())

    def test_aqara_illuminance_extraction(self):
        # Aqara P1 / FP2 reporting illuminance in attributes
        pm = PresenceManager(self.hass, sensors=["binary_sensor.aqara_kitchen"])
        mock_aqara = MockState("on", {"illuminance": 85, "occupancy": True})
        self.hass.states.get.return_value = mock_aqara
        self.assertEqual(pm.get_ambient_lux(), 85.0)

    def test_aqara_motion_debounce_schedule(self):
        pm = PresenceManager(self.hass, sensors=["binary_sensor.aqara_kitchen"], motion_debounce=45)
        self.hass.states.get.return_value = MockState("off")
        pm._schedule_debounce_or_dim()
        self.hass.loop.call_later.assert_called_with(45, pm._schedule_dim)

    def test_sleep_motion_dnd_behavior(self):
        turn_on_called = False
        def turn_on_cb():
            nonlocal turn_on_called
            turn_on_called = True

        from custom_components.adaptive_circadian_lighting.const import SLEEP_MOTION_DND
        pm = PresenceManager(
            self.hass,
            sensors=["binary_sensor.bedroom_motion"],
            auto_turn_on=True,
            sleep_motion_behavior=SLEEP_MOTION_DND,
            is_sleep_callback=lambda: True,
            on_turn_on_adaptive_callback=turn_on_cb,
        )
        pm.room_state = STATE_OFF
        pm._handle_reoccupancy(datetime.now(timezone.utc))

        # Because DND is active during sleep, motion should NOT have turned on lights
        self.assertFalse(turn_on_called)

    def test_initial_state_empty_sets_room_off(self):
        self.hass.states.get.return_value = MockState("off")
        pm = PresenceManager(self.hass, sensors=["binary_sensor.motion"])
        pm._check_initial_sensor_state()
        self.assertEqual(pm.room_state, STATE_OFF)
        self.assertIsNotNone(pm.last_turned_off_time)
        self.hass.loop.call_later.assert_not_called()

    def test_motion_event_turns_on_lights(self):
        turn_on_called = False
        def turn_on_cb():
            nonlocal turn_on_called
            turn_on_called = True

        pm = PresenceManager(
            self.hass,
            sensors=["binary_sensor.motion"],
            auto_turn_on=True,
            on_turn_on_adaptive_callback=turn_on_cb,
        )
        pm.room_state = STATE_OFF

        event = MagicMock()
        event.data = {
            "entity_id": "binary_sensor.motion",
            "new_state": MockState("on"),
        }
        pm._handle_motion_event(event)

        self.assertTrue(turn_on_called)
        self.assertEqual(pm.room_state, STATE_OCCUPIED)

    def test_motion_turns_on_when_lights_off_callback_true(self):
        turn_on_called = False
        def turn_on_cb():
            nonlocal turn_on_called
            turn_on_called = True

        pm = PresenceManager(
            self.hass,
            sensors=["binary_sensor.motion"],
            auto_turn_on=True,
            are_lights_off_callback=lambda: True,
            on_turn_on_adaptive_callback=turn_on_cb,
        )
        # Even if room_state was temporarily occupied due to recent debounce
        pm.room_state = STATE_OCCUPIED

        event = MagicMock()
        event.data = {
            "entity_id": "binary_sensor.motion",
            "new_state": MockState("on"),
        }
        pm._handle_motion_event(event)

        self.assertTrue(turn_on_called)

    def test_on_lights_turned_off_transitions_to_off(self):
        pm = PresenceManager(self.hass, sensors=["binary_sensor.motion"])
        pm.room_state = STATE_OCCUPIED
        pm._dim_timer_handle = MagicMock()

        pm.on_lights_turned_off()

        self.assertEqual(pm.room_state, STATE_OFF)
        self.assertIsNotNone(pm.last_turned_off_time)
        self.assertIsNone(pm._dim_timer_handle)

    def test_sensor_clears_when_lights_already_off_no_dim(self):
        pm = PresenceManager(
            self.hass,
            sensors=["binary_sensor.motion"],
            are_lights_off_callback=lambda: True,
        )
        pm.room_state = STATE_OFF
        self.hass.states.get.return_value = MockState("off")

        event = MagicMock()
        event.data = {
            "entity_id": "binary_sensor.motion",
            "new_state": MockState("off"),
        }
        pm._handle_motion_event(event)

        self.assertEqual(pm.room_state, STATE_OFF)
        self.hass.loop.call_later.assert_not_called()

    def test_lux_sensor_entity_threshold(self):
        pm = PresenceManager(
            self.hass,
            sensors=["binary_sensor.motion"],
            lux_sensor="sensor.kitchen_lux",
            turn_on_lux_threshold=200,
        )
        self.hass.states.get.side_effect = lambda eid: MockState("350.0") if eid == "sensor.kitchen_lux" else MockState("off")
        self.assertEqual(pm.get_ambient_lux(), 350.0)


if __name__ == "__main__":
    unittest.main()
