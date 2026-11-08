"""Presence and occupancy manager with Aqara sensor optimizations, staged dimming and manual state memory."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Callable, Dict, List, Optional

from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    DEFAULT_AUTO_TURN_ON,
    DEFAULT_DIM_BRIGHTNESS,
    DEFAULT_DIM_TIMEOUT,
    DEFAULT_GRACE_PERIOD,
    DEFAULT_MOTION_DEBOUNCE,
    DEFAULT_OFF_TIMEOUT,
    DEFAULT_SLEEP_MOTION_BEHAVIOR,
    DEFAULT_TURN_ON_LUX_THRESHOLD,
    SLEEP_MOTION_DND,
)

_LOGGER = logging.getLogger(__name__)

STATE_OCCUPIED = "occupied"
STATE_DIMMED = "dimmed"
STATE_OFF = "off"

# Recognized positive presence states across ZHA, Zigbee2MQTT, DeCONZ, Matter and Aqara Hubs
POSITIVE_STATES = {
    "on",
    "open",
    "opened",
    "opening",
    "detected",
    "active",
    "occupied",
    "true",
    "yes",
    "1",
    "presence",
    "present",
    "motion",
    "moving",
    "movement",
    "move",
    "still",
    "standing",
    "stand",
    "sitting",
    "occupied_standing",
    "occupied_sitting",
    "occupancy",
    "home",
    "enter",
    "entered",
    "enter_left",
    "enter_right",
    "left_enter",
    "right_enter",
    "approach",
    "approaching",
    "someone",
    "somebody",
    "person",
    "fall_detected",
    "trigger",
    "triggered",
    "exist",
    "existence",
    "in_place",
    "in_room",
    "motion_detected",
    "presence_detected",
    "unlocked",
}

NEGATIVE_STATES = {
    "off",
    "closed",
    "clear",
    "standby",
    "idle",
    "none",
    "no_motion",
    "not_home",
    "away",
    "false",
    "no",
    "0",
    "unavailable",
    "unknown",
}

OCCUPANCY_ATTRIBUTES = (
    "occupancy",
    "presence",
    "motion",
    "moving",
    "movement",
    "has_target",
    "target",
    "targets",
    "target_count",
    "targets_detected",
    "number_of_targets",
    "radar_status",
    "motion_state",
    "motion_status",
    "presence_state",
    "presence_status",
    "detection_status",
    "presence_event",
    "detected",
    "motion_detected",
    "person",
    "person_detected",
    "presence_detected",
    "people_count",
    "person_count",
    "exist",
    "existence",
    "in_place",
)
LUX_ATTRIBUTES = ("illuminance", "lux", "illuminance_lux", "light_level")


def _normalize_entity_list(raw_entities: Any) -> List[str]:
    """Normalize a string, list, or comma-separated string of entity IDs into a clean list."""
    if not raw_entities:
        return []
    result: List[str] = []
    if isinstance(raw_entities, str):
        candidates = raw_entities.split(",")
    elif isinstance(raw_entities, (list, tuple, set)):
        candidates = []
        for item in raw_entities:
            if isinstance(item, str):
                candidates.extend(item.split(","))
            elif item:
                candidates.append(str(item))
    else:
        candidates = [str(raw_entities)]

    for c in candidates:
        cleaned = c.strip().strip("'\"[] ")
        if cleaned:
            result.append(cleaned)
    return result


class PresenceManager:
    """Manages motion/presence sensors (optimized for Aqara FP1/FP2/P1 and IKEA Vallhorn/Parasoll/Tradfri), staged dimming, and manual override persistence."""

    def __init__(
        self,
        hass: HomeAssistant,
        sensors: Optional[List[str]] = None,
        motion_sensors: Optional[List[str]] = None,
        presence_sensors: Optional[List[str]] = None,
        dim_timeout: int = DEFAULT_DIM_TIMEOUT,
        off_timeout: int = DEFAULT_OFF_TIMEOUT,
        grace_period: int = DEFAULT_GRACE_PERIOD,
        dim_brightness: int = DEFAULT_DIM_BRIGHTNESS,
        auto_turn_on: bool = DEFAULT_AUTO_TURN_ON,
        turn_on_lux_threshold: int = DEFAULT_TURN_ON_LUX_THRESHOLD,
        motion_debounce: int = DEFAULT_MOTION_DEBOUNCE,
        sleep_motion_behavior: str = DEFAULT_SLEEP_MOTION_BEHAVIOR,
        lux_sensor: Optional[str] = None,
        are_lights_off_callback: Optional[Callable[[], bool]] = None,
        is_sleep_callback: Optional[Callable[[], bool]] = None,
        on_dim_callback: Optional[Callable[[], Any]] = None,
        on_off_callback: Optional[Callable[[], Any]] = None,
        on_restore_manual_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
        on_turn_on_adaptive_callback: Optional[Callable[[], Any]] = None,
        on_state_change_callback: Optional[Callable[[str], Any]] = None,
    ) -> None:
        self.hass = hass
        self.motion_sensors = _normalize_entity_list(motion_sensors)
        self.presence_sensors = _normalize_entity_list(presence_sensors if presence_sensors is not None else sensors)
        # Unified sensor list for backwards compatibility and aggregate status
        combined_sensors: List[str] = []
        for s in self.motion_sensors + self.presence_sensors:
            if s not in combined_sensors:
                combined_sensors.append(s)
        self.sensors = combined_sensors
        self.dim_timeout = dim_timeout
        self.off_timeout = off_timeout
        self.grace_period = grace_period
        self.dim_brightness = dim_brightness
        self.auto_turn_on = auto_turn_on
        self.turn_on_lux_threshold = turn_on_lux_threshold
        self.motion_debounce = motion_debounce
        self.sleep_motion_behavior = sleep_motion_behavior
        self.lux_sensor = lux_sensor
        self.are_lights_off_callback = are_lights_off_callback
        self.is_sleep_callback = is_sleep_callback

        self.on_dim_callback = on_dim_callback
        self.on_off_callback = on_off_callback
        self.on_restore_manual_callback = on_restore_manual_callback
        self.on_turn_on_adaptive_callback = on_turn_on_adaptive_callback
        self.on_state_change_callback = on_state_change_callback

        self.room_state: str = STATE_OFF
        self.last_motion_time: datetime = datetime.now(timezone.utc)
        self.last_turned_off_time: Optional[datetime] = None

        # Saved manual settings: {entity_id: {"brightness": int, "color_temp": int, "rgb_color": list}}
        self.saved_manual_states: Dict[str, Dict[str, Any]] = {}

        self._debounce_timer_handle: Optional[asyncio.TimerHandle] = None
        self._dim_timer_handle: Optional[asyncio.TimerHandle] = None
        self._off_timer_handle: Optional[asyncio.TimerHandle] = None
        self._unsub_trackers: List[CALLBACK_TYPE] = []

    def start_tracking(self) -> None:
        """Start listening to presence/motion sensors via real-time event tracking."""
        if not self.sensors:
            return

        # 1. Track fast motion sensors (PIR / door contacts) with instantaneous turn-on routine
        if self.motion_sensors:
            try:
                unsub = async_track_state_change_event(
                    self.hass, self.motion_sensors, self._handle_motion_event
                )
                if callable(unsub):
                    self._unsub_trackers.append(unsub)
            except Exception as err:
                _LOGGER.error("PresenceManager: error tracking motion sensors %s: %s", self.motion_sensors, err)

        # 2. Track mmWave presence sensors (radar / static occupancy) with continuous hold routine
        if self.presence_sensors:
            try:
                unsub = async_track_state_change_event(
                    self.hass, self.presence_sensors, self._handle_presence_event
                )
                if callable(unsub):
                    self._unsub_trackers.append(unsub)
            except Exception as err:
                _LOGGER.error("PresenceManager: error tracking presence sensors %s: %s", self.presence_sensors, err)

        # 3. Fast watchdog for continuous mmWave presence (checks every 5 seconds)
        try:
            from homeassistant.helpers.event import async_track_time_interval
            from datetime import timedelta
            unsub_interval = async_track_time_interval(
                self.hass, self.check_continuous_presence, timedelta(seconds=5)
            )
            if callable(unsub_interval):
                self._unsub_trackers.append(unsub_interval)
        except Exception as err:
            _LOGGER.error("PresenceManager: error setting up periodic presence check: %s", err)

        # Evaluate initial state
        self._check_initial_sensor_state()

    def stop_tracking(self) -> None:
        """Stop tracking and cancel active timers."""
        self._cancel_timers()
        for unsub in self._unsub_trackers:
            try:
                unsub()
            except Exception:
                pass
        self._unsub_trackers.clear()

    def save_manual_state(self, entity_id: str, attributes: Dict[str, Any]) -> None:
        """Save a user's manual lighting adjustment for restoration."""
        self.saved_manual_states[entity_id] = {
            "brightness": attributes.get("brightness"),
            "color_temp_kelvin": attributes.get("color_temp_kelvin"),
            "rgb_color": attributes.get("rgb_color"),
            "saved_at": datetime.now(timezone.utc),
        }
        _LOGGER.debug(
            "PresenceManager: saved manual state for %s: %s",
            entity_id,
            self.saved_manual_states[entity_id],
        )

    def clear_manual_state(self, entity_id: Optional[str] = None) -> None:
        """Clear saved manual state for one or all entities."""
        if entity_id:
            self.saved_manual_states.pop(entity_id, None)
        else:
            self.saved_manual_states.clear()

    def has_manual_state(self) -> bool:
        """Check if any manual states are saved."""
        return len(self.saved_manual_states) > 0

    def _set_room_state(self, new_state: str) -> None:
        """Update room state and invoke on_state_change_callback if state changed."""
        old_state = self.room_state
        self.room_state = new_state
        if old_state != new_state:
            _LOGGER.debug(
                "PresenceManager: room state changed from %s to %s",
                old_state,
                new_state,
            )
            if self.on_state_change_callback:
                self._dispatch_callback(self.on_state_change_callback, new_state)

    def is_sensor_triggered(self, state_obj: Any) -> bool:
        """Evaluate if an Aqara, mmWave radar, or standard presence sensor reports occupancy."""
        if not state_obj or getattr(state_obj, "state", None) is None:
            return False

        # Check primary state
        st = str(state_obj.state).strip().lower()
        if st in ("unavailable", "unknown"):
            return False

        if st in POSITIVE_STATES:
            return True

        # Check if state itself is a positive numeric count (e.g. radar targets: "1", "2")
        try:
            val_num = float(st)
            if val_num > 0:
                return True
        except (ValueError, TypeError):
            pass

        # Check Aqara/mmWave specific attributes (FP2 zones, PIR motion flag, radar targets, etc.)
        attrs = getattr(state_obj, "attributes", {}) or {}
        # Special check for contact sensors (e.g. IKEA Parasoll): contact=False means open/triggered
        if "contact" in attrs:
            c_val = attrs.get("contact")
            if c_val is False or (isinstance(c_val, str) and c_val.strip().lower() in ("false", "0", "no", "open", "opened")):
                return True

        for key in OCCUPANCY_ATTRIBUTES:
            if key not in attrs:
                continue
            val = attrs.get(key)
            if val is None:
                continue
            if isinstance(val, bool):
                if val:
                    return True
                continue
            if isinstance(val, (int, float)):
                if val > 0:
                    return True
                continue
            if isinstance(val, (list, dict, set)):
                if len(val) > 0:
                    return True
                continue
            val_str = str(val).strip().lower()
            if val_str in POSITIVE_STATES:
                return True
            try:
                if float(val_str) > 0:
                    return True
            except (ValueError, TypeError):
                pass

        return False

    def is_motion_triggered(self) -> bool:
        """Check if any configured fast motion (PIR / door) sensor is currently triggered."""
        for sensor_id in self.motion_sensors:
            try:
                st = self.hass.states.get(sensor_id)
                if self.is_sensor_triggered(st):
                    return True
            except Exception as err:
                _LOGGER.warning("PresenceManager: error evaluating motion sensor %s: %s", sensor_id, err)
        return False

    def is_presence_triggered(self) -> bool:
        """Check if any configured mmWave radar or presence sensor is currently triggered."""
        for sensor_id in self.presence_sensors:
            try:
                st = self.hass.states.get(sensor_id)
                if self.is_sensor_triggered(st):
                    return True
            except Exception as err:
                _LOGGER.warning("PresenceManager: error evaluating presence sensor %s: %s", sensor_id, err)
        return False

    def is_occupied(self) -> bool:
        """Check if any motion or presence sensor reports occupancy."""
        if self.motion_sensors or self.presence_sensors:
            return self.is_motion_triggered() or self.is_presence_triggered()
        for sensor_id in self.sensors:
            try:
                st = self.hass.states.get(sensor_id)
                if self.is_sensor_triggered(st):
                    return True
            except Exception as err:
                _LOGGER.warning("PresenceManager: error evaluating sensor %s: %s", sensor_id, err)
        return False

    def are_lights_off(self) -> bool:
        """Check if target lights are currently off."""
        if self.are_lights_off_callback:
            try:
                return bool(self.are_lights_off_callback())
            except Exception as err:
                _LOGGER.warning("PresenceManager: error checking if lights are off: %s", err)
        return self.room_state == STATE_OFF

    def on_lights_turned_off(self) -> None:
        """Handle when all lights in the room are turned off."""
        self._cancel_timers()
        self._set_room_state(STATE_OFF)
        self.last_turned_off_time = datetime.now(timezone.utc)
        _LOGGER.debug("PresenceManager: lights turned off; room state set to OFF.")

    def get_ambient_lux(self) -> Optional[float]:
        """Extract ambient illuminance from dedicated lux sensor or Aqara presence sensor attributes."""
        if self.lux_sensor:
            st = self.hass.states.get(self.lux_sensor)
            if st and st.state not in ("unavailable", "unknown"):
                try:
                    return float(st.state)
                except (ValueError, TypeError):
                    pass

        for sensor_id in self.sensors:
            st = self.hass.states.get(sensor_id)
            if not st or not getattr(st, "attributes", None):
                continue
            attrs = st.attributes
            for key in LUX_ATTRIBUTES:
                val = attrs.get(key)
                if val is not None:
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        pass
        return None

    @callback
    def check_continuous_presence(self, _now: Optional[datetime] = None) -> None:
        """Periodic watchdog check for mmWave / continuous presence sensors.

        If sensor reports presence while lights are off, turn them on (with 15s cooldown after manual turn-off).
        If room was dimmed while presence is detected, immediately restore full occupancy.
        """
        if not self.auto_turn_on:
            return

        has_presence = self.is_presence_triggered()
        if not has_presence and not self.presence_sensors and self.is_occupied():
            # If user configured only generic sensors list, check aggregate occupancy
            has_presence = True

        if has_presence:
            now = datetime.now(timezone.utc)
            self.last_motion_time = now

            if self.are_lights_off():
                # Allow a brief 15s cooldown if user just manually turned lights off
                if self.last_turned_off_time is not None:
                    elapsed = (now - self.last_turned_off_time).total_seconds()
                    if elapsed < 15.0:
                        _LOGGER.debug(
                            "PresenceManager [mmWave]: continuous presence detected but lights turned off %.1fs ago (<15s cooldown).",
                            elapsed,
                        )
                        return

                _LOGGER.debug(
                    "PresenceManager [mmWave]: continuous presence detected while lights are off. Triggering reoccupancy."
                )
                self._cancel_timers()
                self._handle_reoccupancy(now)
            elif self.room_state == STATE_DIMMED:
                _LOGGER.debug(
                    "PresenceManager [mmWave]: continuous presence detected while room was dimmed. Restoring full occupancy."
                )
                self._cancel_timers()
                self._set_room_state(STATE_OCCUPIED)
                if self.on_turn_on_adaptive_callback:
                    self._dispatch_callback(self.on_turn_on_adaptive_callback)

    def _check_initial_sensor_state(self) -> None:
        """Check current sensor state at startup."""
        if self.is_occupied():
            self._set_room_state(STATE_OCCUPIED)
            self.last_motion_time = datetime.now(timezone.utc)
            self._cancel_timers()
            if self.auto_turn_on and self.are_lights_off():
                self._handle_reoccupancy(datetime.now(timezone.utc))
        else:
            self._set_room_state(STATE_OFF)
            self.last_turned_off_time = datetime.now(timezone.utc)
            self._cancel_timers()

    @callback
    def _handle_motion_event(self, event: Event) -> None:
        """Handle fast movement events (PIR / door contact sensors)."""
        if hasattr(event, "data"):
            new_state = event.data.get("new_state")
            entity_id = event.data.get("entity_id")
        elif isinstance(event, dict):
            new_state = event.get("new_state")
            entity_id = event.get("entity_id")
        else:
            return

        if not new_state:
            return

        is_on = self.is_sensor_triggered(new_state)
        _LOGGER.debug(
            "PresenceManager [PIR]: motion sensor %s state=%s (is_on=%s)",
            entity_id,
            getattr(new_state, "state", None),
            is_on,
        )

        now = datetime.now(timezone.utc)

        if is_on:
            # Instant PIR edge trigger: cancel timers, set occupied, turn lights on immediately
            self._cancel_timers()
            self.last_motion_time = now
            lights_off = self.are_lights_off()
            was_empty = self.room_state in (STATE_DIMMED, STATE_OFF)
            self._set_room_state(STATE_OCCUPIED)

            if lights_off or was_empty:
                self._handle_reoccupancy(now)
        else:
            # Motion sensor cleared.
            # Sensor Fusion: Only start dimming if no other motion sensor AND no presence sensor is active!
            if not self.is_occupied():
                if not self.are_lights_off():
                    self._schedule_debounce_or_dim()
                else:
                    self._set_room_state(STATE_OFF)
                    self._cancel_timers()
            else:
                _LOGGER.debug(
                    "PresenceManager [PIR]: motion sensor cleared but mmWave/presence still active. Holding occupancy."
                )

        if self.on_state_change_callback:
            self._dispatch_callback(self.on_state_change_callback, self.room_state)

    @callback
    def _handle_presence_event(self, event: Event) -> None:
        """Handle mmWave radar / static presence events."""
        if hasattr(event, "data"):
            new_state = event.data.get("new_state")
            entity_id = event.data.get("entity_id")
        elif isinstance(event, dict):
            new_state = event.get("new_state")
            entity_id = event.get("entity_id")
        else:
            return

        if not new_state:
            return

        is_on = self.is_sensor_triggered(new_state)
        _LOGGER.debug(
            "PresenceManager [mmWave]: presence sensor %s state=%s (is_on=%s)",
            entity_id,
            getattr(new_state, "state", None),
            is_on,
        )

        now = datetime.now(timezone.utc)

        if is_on:
            # mmWave occupancy detected: cancel timers, set occupied, turn lights on
            self._cancel_timers()
            self.last_motion_time = now
            lights_off = self.are_lights_off()
            was_empty = self.room_state in (STATE_DIMMED, STATE_OFF)
            self._set_room_state(STATE_OCCUPIED)

            if lights_off or was_empty:
                self._handle_reoccupancy(now)
        else:
            # mmWave presence cleared
            if not self.is_occupied():
                if not self.are_lights_off():
                    self._schedule_debounce_or_dim()
                else:
                    self._set_room_state(STATE_OFF)
                    self._cancel_timers()

        if self.on_state_change_callback:
            self._dispatch_callback(self.on_state_change_callback, self.room_state)

    def _handle_reoccupancy(self, now: datetime) -> None:
        """Handle person returning to the room."""
        self._set_room_state(STATE_OCCUPIED)

        if not self.auto_turn_on:
            _LOGGER.debug(
                "PresenceManager: motion detected but auto_turn_on is disabled. Skipping turn-on."
            )
            return

        # Check if room is in Sleep Mode and DND is active (ignore motion)
        if self.is_sleep_callback and self.is_sleep_callback():
            if self.sleep_motion_behavior == SLEEP_MOTION_DND:
                _LOGGER.info(
                    "PresenceManager: motion detected but Sleep Mode DND is active. Ignoring motion turn-on."
                )
                return

        within_grace = False
        if self.last_turned_off_time is not None:
            elapsed = (now - self.last_turned_off_time).total_seconds()
            within_grace = elapsed <= self.grace_period
        else:
            # If room was only dimmed but not completely off, user is definitely within grace
            within_grace = True

        # Check if ambient lux is above threshold (e.g. bright sunny kitchen)
        if self.turn_on_lux_threshold > 0:
            lux = self.get_ambient_lux()
            if lux is not None and lux >= self.turn_on_lux_threshold:
                _LOGGER.info(
                    "PresenceManager: motion detected but ambient lux (%s) >= threshold (%s). Keeping lights off.",
                    lux,
                    self.turn_on_lux_threshold,
                )
                return

        # Validate saved manual states: ensure valid brightness > 0
        has_valid_manual = False
        if within_grace and self.has_manual_state():
            for ent_id, st in self.saved_manual_states.items():
                b = st.get("brightness")
                if b is not None and b > 0:
                    has_valid_manual = True
                    break

        restored = False
        if within_grace and has_valid_manual and self.on_restore_manual_callback:
            _LOGGER.info(
                "PresenceManager: room reoccupied within grace period. Restoring manual kitchen/room settings!"
            )
            restored = self._dispatch_callback(
                self.on_restore_manual_callback, self.saved_manual_states
            )

        if not restored and self.auto_turn_on:
            _LOGGER.info(
                "PresenceManager: room reoccupied. Applying adaptive circadian lighting."
            )
            self.clear_manual_state()
            if self.on_turn_on_adaptive_callback:
                self._dispatch_callback(self.on_turn_on_adaptive_callback)

    def _schedule_debounce_or_dim(self) -> None:
        """Schedule debounce delay to compensate for Aqara PIR blind time before starting dim."""
        self._cancel_timers()
        loop = self.hass.loop

        if self.motion_debounce > 0:
            _LOGGER.debug(
                "PresenceManager: sensor went off. Waiting debounce buffer of %ss (Aqara blind-time protection).",
                self.motion_debounce,
            )
            self._debounce_timer_handle = loop.call_later(
                self.motion_debounce, self._schedule_dim
            )
        else:
            self._schedule_dim()

    def _schedule_dim(self) -> None:
        """Schedule staged dimming when room remains clear after debounce."""
        if self.is_occupied():
            return

        self._cancel_timers()
        loop = self.hass.loop
        self._dim_timer_handle = loop.call_later(self.dim_timeout, self._trigger_dim)
        _LOGGER.debug(
            "PresenceManager: room confirmed empty. Scheduled dim in %s seconds.",
            self.dim_timeout,
        )

    def _trigger_dim(self) -> None:
        """Execute dim phase."""
        if self.is_occupied():
            return

        self._set_room_state(STATE_DIMMED)
        _LOGGER.info(
            "PresenceManager: room empty for %ss. Dimming lights to %s%%.",
            self.dim_timeout,
            self.dim_brightness,
        )
        if self.on_dim_callback:
            self._dispatch_callback(self.on_dim_callback)

        # Schedule complete turn off
        loop = self.hass.loop
        self._off_timer_handle = loop.call_later(self.off_timeout, self._trigger_off)

    def _trigger_off(self) -> None:
        """Execute complete turn off."""
        if self.is_occupied():
            return

        self._set_room_state(STATE_OFF)
        self.last_turned_off_time = datetime.now(timezone.utc)
        _LOGGER.info(
            "PresenceManager: room still empty after %ss. Turning off lights completely.",
            self.off_timeout,
        )
        if self.on_off_callback:
            self._dispatch_callback(self.on_off_callback)

    def _cancel_timers(self) -> None:
        """Cancel all pending timers."""
        if self._debounce_timer_handle:
            self._debounce_timer_handle.cancel()
            self._debounce_timer_handle = None
        if self._dim_timer_handle:
            self._dim_timer_handle.cancel()
            self._dim_timer_handle = None
        if self._off_timer_handle:
            self._off_timer_handle.cancel()
            self._off_timer_handle = None

    def _dispatch_callback(self, func: Callable[..., Any], *args: Any) -> bool:
        """Safely invoke async or sync callback with exception handling. Returns True if succeeded."""
        try:
            res = func(*args)
            if asyncio.iscoroutine(res):
                try:
                    self.hass.async_create_task(res)
                except RuntimeError:
                    asyncio.run_coroutine_threadsafe(res, self.hass.loop)
            return True
        except Exception as err:
            _LOGGER.error("PresenceManager: error executing callback %s: %s", func, err)
            return False
