"""Manual control detection and timeout management."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Callable, Dict, List, Optional

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from .const import DEFAULT_OVERRIDE_TIMEOUT

_LOGGER = logging.getLogger(__name__)


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


class OverrideManager:
    """Detects and manages manual overrides of lights."""

    def __init__(
        self,
        hass: HomeAssistant,
        lights: list[str],
        timeout_minutes: int = DEFAULT_OVERRIDE_TIMEOUT,
        on_override_reset_callback: Optional[Callable[[str], Any]] = None,
        on_manual_change_callback: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
        on_lights_off_callback: Optional[Callable[[str], Any]] = None,
        on_lights_on_callback: Optional[Callable[[str], Any]] = None,
    ) -> None:
        self.hass = hass
        self.lights = _normalize_entity_list(lights)
        self.timeout_minutes = timeout_minutes
        self.on_override_reset_callback = on_override_reset_callback
        self.on_manual_change_callback = on_manual_change_callback
        self.on_lights_off_callback = on_lights_off_callback
        self.on_lights_on_callback = on_lights_on_callback

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
        brightness_pct = state_data.get("brightness_pct")
        brightness = state_data.get("brightness")
        if brightness is None and brightness_pct is not None:
            brightness = round(brightness_pct * 255 / 100)
        elif brightness_pct is None and brightness is not None:
            brightness_pct = round(brightness * 100 / 255)

        kelvin = state_data.get("color_temp_kelvin")
        mireds = state_data.get("color_temp")
        if kelvin is None and mireds is not None and mireds > 0:
            kelvin = round(1000000 / mireds)
        elif mireds is None and kelvin is not None and kelvin > 0:
            mireds = round(1000000 / kelvin)

        transition = float(state_data.get("transition", 0.0) or 0.0)

        self._last_sent_states[entity_id] = {
            "brightness_pct": brightness_pct,
            "brightness": brightness,
            "color_temp_kelvin": kelvin,
            "color_temp": mireds,
            "rgb_color": state_data.get("rgb_color"),
            "transition": transition,
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

    def reset_override(self, entity_id: Optional[str] = None, notify_callback: bool = True) -> None:
        """Reset manual override for a specific entity or all entities."""
        if entity_id:
            if entity_id in self.overridden_lights:
                self.overridden_lights.pop(entity_id, None)
                handle = self._timer_handles.pop(entity_id, None)
                if handle:
                    handle.cancel()
                _LOGGER.info("OverrideManager: reset override for %s", entity_id)
                if notify_callback and self.on_override_reset_callback:
                    self.on_override_reset_callback(entity_id)
        else:
            for ent_id in list(self.overridden_lights.keys()):
                self.reset_override(ent_id, notify_callback=notify_callback)

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
        self.reset_override(entity_id, notify_callback=True)

    @callback
    def _handle_light_change(self, event: Event) -> None:
        """Evaluate whether a state change was manual or automated."""
        if hasattr(event, "data"):
            entity_id = event.data.get("entity_id")
            old_state = event.data.get("old_state")
            new_state = event.data.get("new_state")
        elif isinstance(event, dict):
            entity_id = event.get("entity_id")
            old_state = event.get("old_state")
            new_state = event.get("new_state")
        else:
            return

        if not new_state or new_state.state != "on":
            # If light turned off, clear override silently so it re-adapts next time it turns on
            if old_state and old_state.state == "on" and new_state and new_state.state == "off":
                self.reset_override(entity_id, notify_callback=False)
            if self.on_lights_off_callback and (not new_state or new_state.state == "off"):
                self.on_lights_off_callback(entity_id)
            return

        # If it was off and just turned on (or first seen), notify callback and let anti-glare / coordinator adapt it
        if old_state is None or old_state.state != "on":
            if self.on_lights_on_callback:
                self.on_lights_on_callback(entity_id)
            return

        # 1. Compare new state against last sent coordinator state
        last_sent = self._last_sent_states.get(entity_id)
        if last_sent:
            time_diff = (datetime.now(timezone.utc) - last_sent["timestamp"]).total_seconds()
            transition = float(last_sent.get("transition", 0.0) or 0.0)

            # During coordinator transition (plus safety buffer for HA / Zigbee latency), ignore updates
            transition_window = max(5.0, transition + 3.0)
            if time_diff < transition_window:
                return

        new_attrs = getattr(new_state, "attributes", {}) or {}
        old_attrs = getattr(old_state, "attributes", {}) or {}

        # 2. Check if the reported state matches what coordinator last commanded
        if last_sent:
            matches_sent = True

            # Brightness check (handling 0-255 vs 0-100% scaling and rounding)
            expected_b = last_sent.get("brightness")
            actual_b = new_attrs.get("brightness")
            if expected_b is not None and actual_b is not None:
                # 8 units out of 255 is ~3% tolerance for dimmer rounding/quantization
                if abs(actual_b - expected_b) > 8:
                    matches_sent = False

            # Color temperature check (handling Kelvin vs Mireds conversion rounding)
            expected_k = last_sent.get("color_temp_kelvin")
            expected_m = last_sent.get("color_temp")
            actual_k = new_attrs.get("color_temp_kelvin")
            actual_m = new_attrs.get("color_temp")
            if expected_k is not None:
                ct_ok = False
                if actual_k is not None:
                    # Zigbee mired rounding error at high Kelvin can be up to 60K
                    if abs(actual_k - expected_k) <= 60:
                        ct_ok = True
                    elif expected_m and actual_k > 0:
                        act_m = round(1000000 / actual_k)
                        if abs(act_m - expected_m) <= 4:
                            ct_ok = True
                elif actual_m is not None and expected_m is not None:
                    if abs(actual_m - expected_m) <= 4:
                        ct_ok = True
                if not ct_ok:
                    matches_sent = False

            # RGB color check
            expected_rgb = last_sent.get("rgb_color")
            actual_rgb = new_attrs.get("rgb_color")
            if expected_rgb is not None and actual_rgb is not None:
                if not (len(actual_rgb) >= 3 and len(expected_rgb) >= 3 and
                        all(abs(a - b) <= 15 for a, b in zip(actual_rgb[:3], expected_rgb[:3]))):
                    matches_sent = False

            if matches_sent:
                # The state matches coordinator command; NOT a manual override!
                return

        # 3. Detect actual manual changes
        new_b = new_attrs.get("brightness")
        old_b = old_attrs.get("brightness")
        b_changed = (
            new_b is not None
            and old_b is not None
            and abs(new_b - old_b) > 8
        )

        new_k = new_attrs.get("color_temp_kelvin")
        old_k = old_attrs.get("color_temp_kelvin")
        new_m = new_attrs.get("color_temp")
        old_m = old_attrs.get("color_temp")
        ct_changed = False
        if new_k is not None and old_k is not None:
            ct_changed = abs(new_k - old_k) > 60
        elif new_m is not None and old_m is not None:
            ct_changed = abs(new_m - old_m) > 4

        new_rgb = new_attrs.get("rgb_color")
        old_rgb = old_attrs.get("rgb_color")
        rgb_changed = (
            new_rgb is not None
            and old_rgb is not None
            and new_rgb != old_rgb
        )

        if b_changed or ct_changed or rgb_changed:
            self.set_manual_override(entity_id, new_attrs)

