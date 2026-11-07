"""Presence and occupancy manager with manual state memory and staged dimming."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Callable, Dict, List, Optional

from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    DEFAULT_DIM_BRIGHTNESS,
    DEFAULT_DIM_TIMEOUT,
    DEFAULT_GRACE_PERIOD,
    DEFAULT_OFF_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)

STATE_OCCUPIED = "occupied"
STATE_DIMMED = "dimmed"
STATE_OFF = "off"


class PresenceManager:
    """Manages motion/presence sensors, staged dimming, and manual override persistence."""

    def __init__(
        self,
        hass: HomeAssistant,
        sensors: List[str],
        dim_timeout: int = DEFAULT_DIM_TIMEOUT,
        off_timeout: int = DEFAULT_OFF_TIMEOUT,
        grace_period: int = DEFAULT_GRACE_PERIOD,
        dim_brightness: int = DEFAULT_DIM_BRIGHTNESS,
        on_dim_callback: Optional[Callable[[], Any]] = None,
        on_off_callback: Optional[Callable[[], Any]] = None,
        on_restore_manual_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
        on_turn_on_adaptive_callback: Optional[Callable[[], Any]] = None,
    ) -> None:
        self.hass = hass
        self.sensors = sensors
        self.dim_timeout = dim_timeout
        self.off_timeout = off_timeout
        self.grace_period = grace_period
        self.dim_brightness = dim_brightness

        self.on_dim_callback = on_dim_callback
        self.on_off_callback = on_off_callback
        self.on_restore_manual_callback = on_restore_manual_callback
        self.on_turn_on_adaptive_callback = on_turn_on_adaptive_callback

        self.room_state: str = STATE_OCCUPIED
        self.last_motion_time: datetime = datetime.now(timezone.utc)
        self.last_turned_off_time: Optional[datetime] = None

        # Saved manual settings: {entity_id: {"brightness": int, "color_temp": int, "rgb_color": list}}
        self.saved_manual_states: Dict[str, Dict[str, Any]] = {}

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

    def is_occupied(self) -> bool:
        """Check if any configured presence sensor is currently reporting 'on'."""
        for sensor_id in self.sensors:
            st = self.hass.states.get(sensor_id)
            if st and st.state in ("on", "open", "detected", "active"):
                return True
        return False

    def _check_initial_sensor_state(self) -> None:
        """Check current sensor state at startup."""
        if self.is_occupied():
            self.room_state = STATE_OCCUPIED
            self.last_motion_time = datetime.now(timezone.utc)
            self._cancel_timers()
        else:
            self.room_state = STATE_OCCUPIED
            self._schedule_dim()

    def _handle_motion_event(self, event: Event) -> None:
        """Handle state change from a motion/presence sensor."""
        new_state = event.data.get("new_state")
        if not new_state:
            return

        is_on = new_state.state in ("on", "open", "detected", "active")
        _LOGGER.debug(
            "PresenceManager: sensor %s changed to %s (is_on=%s)",
            event.data.get("entity_id"),
            new_state.state,
            is_on,
        )

        now = datetime.now(timezone.utc)

        if is_on:
            self._cancel_timers()
            self.last_motion_time = now
            was_empty = self.room_state in (STATE_DIMMED, STATE_OFF)
            self.room_state = STATE_OCCUPIED

            if was_empty:
                self._handle_reoccupancy(now)
        else:
            # Check if all sensors are now off
            if not self.is_occupied():
                self._schedule_dim()

    def _handle_reoccupancy(self, now: datetime) -> None:
        """Handle person returning to the room."""
        self.room_state = STATE_OCCUPIED
        within_grace = False
        if self.last_turned_off_time is not None:
            elapsed = (now - self.last_turned_off_time).total_seconds()
            within_grace = elapsed <= self.grace_period
        else:
            # If room was only dimmed but not completely off, user is definitely within grace
            within_grace = True

        if within_grace and self.has_manual_state():
            _LOGGER.info(
                "PresenceManager: room reoccupied within grace period. Restoring manual settings!"
            )
            if self.on_restore_manual_callback:
                self._dispatch_callback(self.on_restore_manual_callback, self.saved_manual_states)
        else:
            # Beyond grace period or no manual setting: wipe previous manual memory
            _LOGGER.info(
                "PresenceManager: room reoccupied. Applying adaptive circadian lighting."
            )
            self.clear_manual_state()
            if self.on_turn_on_adaptive_callback:
                self._dispatch_callback(self.on_turn_on_adaptive_callback)

    def _schedule_dim(self) -> None:
        """Schedule staged dimming when room becomes empty."""
        self._cancel_timers()
        loop = self.hass.loop
        self._dim_timer_handle = loop.call_later(self.dim_timeout, self._trigger_dim)
        _LOGGER.debug(
            "PresenceManager: room empty. Scheduled dim in %s seconds.",
            self.dim_timeout,
        )

    def _trigger_dim(self) -> None:
        """Execute dim phase."""
        if self.is_occupied():
            return

        self.room_state = STATE_DIMMED
        _LOGGER.info(
            "PresenceManager: room has been empty for %ss. Dimming lights to %s%%.",
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
        """Cancel dim and off timers."""
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
