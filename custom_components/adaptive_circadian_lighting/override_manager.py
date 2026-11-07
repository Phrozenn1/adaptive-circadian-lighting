"""Manual control detection and timeout management."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Callable, Dict, Optional, Set

from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event

from .const import DEFAULT_OVERRIDE_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class OverrideManager:
    """Detects and manages manual overrides of lights."""

    def __init__(
        self,
        hass: HomeAssistant,
        lights: list[str],
        timeout_minutes: int = DEFAULT_OVERRIDE_TIMEOUT,
        on_override_reset_callback: Optional[Callable[[str], Any]] = None,
        on_manual_change_callback: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
    ) -> None:
        self.hass = hass
        self.lights = lights
        self.timeout_minutes = timeout_minutes
        self.on_override_reset_callback = on_override_reset_callback
        self.on_manual_change_callback = on_manual_change_callback

        # Track what our integration last sent so we don't trigger ourselves
        self._last_sent_states: Dict[str, Dict[str, Any]] = {}

        # Set of lights currently in manual override
        self.overridden_lights: Dict[str, datetime] = {}
        self._timer_handles: Dict[str, asyncio.TimerHandle] = {}
        self._unsub: Optional[Callable[[], None]] = None

    def start_tracking(self) -> None:
        """Listen to state changes on target lights."""
        if not self.lights:
            return

        self._unsub = async_track_state_change_event(
            self.hass, self.lights, self._handle_light_change
        )

    def stop_tracking(self) -> None:
        """Stop listening and cancel timers."""
        if self._unsub:
            self._unsub()
            self._unsub = None
        for handle in self._timer_handles.values():
            handle.cancel()
        self._timer_handles.clear()

    def record_sent_state(self, entity_id: str, state_data: Dict[str, Any]) -> None:
        """Record that our coordinator made this change to prevent false manual detection."""
        self._last_sent_states[entity_id] = {
            "brightness_pct": state_data.get("brightness_pct"),
            "color_temp_kelvin": state_data.get("color_temp_kelvin"),
            "rgb_color": state_data.get("rgb_color"),
            "timestamp": datetime.now(timezone.utc),
        }

    def is_overridden(self, entity_id: str) -> bool:
        """Check if an entity is currently manually overridden."""
        return entity_id in self.overridden_lights

    def set_manual_override(self, entity_id: str, attributes: Dict[str, Any]) -> None:
        """Mark an entity as manually overridden and start timeout."""
        self.overridden_lights[entity_id] = datetime.now(timezone.utc)
        _LOGGER.info(
            "OverrideManager: manual control detected for %s. Pausing adaptive updates.",
            entity_id,
        )

        if self.on_manual_change_callback:
            self.on_manual_change_callback(entity_id, attributes)

        self._schedule_timeout(entity_id)

    def reset_override(self, entity_id: Optional[str] = None) -> None:
        """Reset manual override for a specific entity or all entities."""
        if entity_id:
            if entity_id in self.overridden_lights:
                self.overridden_lights.pop(entity_id, None)
                handle = self._timer_handles.pop(entity_id, None)
                if handle:
                    handle.cancel()
                _LOGGER.info("OverrideManager: reset override for %s", entity_id)
                if self.on_override_reset_callback:
                    self.on_override_reset_callback(entity_id)
        else:
            for ent_id in list(self.overridden_lights.keys()):
                self.reset_override(ent_id)

    def _schedule_timeout(self, entity_id: str) -> None:
        """Schedule automatic timeout reset."""
        # Cancel previous handle if any
        handle = self._timer_handles.pop(entity_id, None)
        if handle:
            handle.cancel()

        if self.timeout_minutes <= 0:
            return  # Infinite override until manual reset or power toggle

        timeout_sec = self.timeout_minutes * 60
        loop = self.hass.loop
        self._timer_handles[entity_id] = loop.call_later(
            timeout_sec, self._handle_timeout, entity_id
        )

    def _handle_timeout(self, entity_id: str) -> None:
        """Handle timeout expiration."""
        _LOGGER.info(
            "OverrideManager: override timeout expired for %s. Resuming adaptive control.",
            entity_id,
        )
        self.reset_override(entity_id)

    def _handle_light_change(self, event: Event) -> None:
        """Evaluate whether a state change was manual or automated."""
        entity_id = event.data.get("entity_id")
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")

        if not new_state or new_state.state != "on":
            # If light turned off, clear override so it re-adapts next time it turns on
            if old_state and old_state.state == "on" and new_state and new_state.state == "off":
                self.reset_override(entity_id)
            return

        # If it was off and just turned on, let anti-glare / coordinator adapt it
        if old_state and old_state.state != "on":
            return

        # Compare new state against last sent coordinator state
        last_sent = self._last_sent_states.get(entity_id)
        if last_sent:
            time_diff = (datetime.now(timezone.utc) - last_sent["timestamp"]).total_seconds()
            if time_diff < 4.0:
                # Within recent command window, ignore to prevent self-triggering
                return

        new_attrs = new_state.attributes
        old_attrs = old_state.attributes if old_state else {}

        # Check if brightness, color temp or rgb actually changed
        b_changed = (
            "brightness" in new_attrs
            and abs(new_attrs.get("brightness", 0) - old_attrs.get("brightness", 0)) > 6
        )
        ct_changed = (
            "color_temp_kelvin" in new_attrs
            and abs(new_attrs.get("color_temp_kelvin", 0) - old_attrs.get("color_temp_kelvin", 0)) > 50
        )
        rgb_changed = (
            "rgb_color" in new_attrs
            and new_attrs.get("rgb_color") != old_attrs.get("rgb_color")
        )

        if b_changed or ct_changed or rgb_changed:
            self.set_manual_override(entity_id, new_attrs)
