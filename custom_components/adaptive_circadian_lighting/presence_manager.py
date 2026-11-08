"""Presence and occupancy manager with Aqara sensor optimizations, staged dimming and manual state memory."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Callable, Dict, List, Optional

from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant
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
POSITIVE_STATES = {"on", "open", "detected", "active", "occupied", "true", "1"}
OCCUPANCY_ATTRIBUTES = ("occupancy", "presence", "motion", "moving", "has_target", "target")
LUX_ATTRIBUTES = ("illuminance", "lux", "illuminance_lux", "light_level")


class PresenceManager:
    """Manages motion/presence sensors (optimized for Aqara FP1/FP2/P1), staged dimming, and manual override persistence."""

    def __init__(
        self,
        hass: HomeAssistant,
        sensors: List[str],
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
    ) -> None:
        self.hass = hass
        self.sensors = [sensors] if isinstance(sensors, str) else list(sensors or [])
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
        """Start listening to presence/motion sensors."""
        if not self.sensors:
            return

        unsub = async_track_state_change_event(
            self.hass, self.sensors, self._handle_motion_event
        )
        self._unsub_trackers.append(unsub)

        # Evaluate initial state
        self._check_initial_sensor_state()

    def stop_tracking(self) -> None:
        """Stop tracking and cancel active timers."""
        self._cancel_timers()
        for unsub in self._unsub_trackers:
            unsub()
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

    def is_sensor_triggered(self, state_obj: Any) -> bool:
        """Evaluate if an Aqara or standard presence sensor reports occupancy."""
        if not state_obj:
            return False

        # Check primary state
        st = str(state_obj.state).lower()
        if st in POSITIVE_STATES:
            return True

        # Check Aqara specific attributes (FP2 zones, PIR motion flag, etc.)
        attrs = getattr(state_obj, "attributes", {}) or {}
        for key in OCCUPANCY_ATTRIBUTES:
            val = attrs.get(key)
            if val is True or str(val).lower() in ("true", "on", "yes", "1"):
                return True

        return False

    def is_occupied(self) -> bool:
        """Check if any configured presence sensor is currently triggered."""
        for sensor_id in self.sensors:
            st = self.hass.states.get(sensor_id)
            if self.is_sensor_triggered(st):
                return True
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
        self.room_state = STATE_OFF
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

    def _check_initial_sensor_state(self) -> None:
        """Check current sensor state at startup."""
        if self.is_occupied():
            self.room_state = STATE_OCCUPIED
            self.last_motion_time = datetime.now(timezone.utc)
            self._cancel_timers()
            if self.auto_turn_on and self.are_lights_off():
                self._handle_reoccupancy(datetime.now(timezone.utc))
        else:
            self.room_state = STATE_OFF
            self.last_turned_off_time = datetime.now(timezone.utc)
            self._cancel_timers()

    def _handle_motion_event(self, event: Event) -> None:
        """Handle state change from an Aqara or standard motion/presence sensor."""
        new_state = event.data.get("new_state")
        if not new_state:
            return

        is_on = self.is_sensor_triggered(new_state)
        _LOGGER.debug(
            "PresenceManager: sensor %s (Aqara/Presence) state=%s (is_on=%s)",
            event.data.get("entity_id"),
            new_state.state,
            is_on,
        )

        now = datetime.now(timezone.utc)

        if is_on:
            self._cancel_timers()
            self.last_motion_time = now
            lights_off = self.are_lights_off()
            was_empty = (self.room_state in (STATE_DIMMED, STATE_OFF)) or lights_off
            self.room_state = STATE_OCCUPIED

            if was_empty:
                self._handle_reoccupancy(now)
        else:
            # When sensor turns off, check if all sensors are now clear
            if not self.is_occupied():
                if not self.are_lights_off():
                    self._schedule_debounce_or_dim()
                else:
                    self.room_state = STATE_OFF
                    self._cancel_timers()

    def _handle_reoccupancy(self, now: datetime) -> None:
        """Handle person returning to the room."""
        self.room_state = STATE_OCCUPIED

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

        if within_grace and self.has_manual_state():
            _LOGGER.info(
                "PresenceManager: room reoccupied within grace period. Restoring manual kitchen/room settings!"
            )
            if self.on_restore_manual_callback:
                self._dispatch_callback(self.on_restore_manual_callback, self.saved_manual_states)
        elif self.auto_turn_on:
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

        self.room_state = STATE_DIMMED
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

        self.room_state = STATE_OFF
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

    def _dispatch_callback(self, func: Callable[..., Any], *args: Any) -> None:
        """Safely invoke async or sync callback."""
        res = func(*args)
        if asyncio.iscoroutine(res):
            self.hass.async_create_task(res)
