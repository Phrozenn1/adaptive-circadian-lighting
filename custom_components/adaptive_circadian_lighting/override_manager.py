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
        get_expected_state_callback: Optional[Callable[[str], Dict[str, Any]]] = None,
    ) -> None:
        self.hass = hass
        self.lights = _normalize_entity_list(lights)
        self.timeout_minutes = timeout_minutes
        self.on_override_reset_callback = on_override_reset_callback
        self.on_manual_change_callback = on_manual_change_callback
        self.on_lights_off_callback = on_lights_off_callback
        self.on_lights_on_callback = on_lights_on_callback
        self.get_expected_state_callback = get_expected_state_callback

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

        current_b = None
        if hasattr(self, "hass") and self.hass and hasattr(self.hass, "states"):
            try:
                st = self.hass.states.get(entity_id)
                if st and hasattr(st, "attributes") and isinstance(st.attributes, dict):
                    raw_b = st.attributes.get("brightness")
                    if isinstance(raw_b, (int, float)):
                        current_b = round(raw_b)
            except Exception:
                pass

        self._last_sent_states[entity_id] = {
            "brightness_pct": brightness_pct,
            "brightness": brightness,
            "start_brightness": current_b,
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

        new_attrs = getattr(new_state, "attributes", {}) or {}
        old_attrs = getattr(old_state, "attributes", {}) or {}
        last_sent = self._last_sent_states.get(entity_id)

        # Fallback expected values if last_sent is missing
        expected_fallback = (
            self.get_expected_state_callback(entity_id)
            if self.get_expected_state_callback
            else None
        )

        expected_b = (
            last_sent.get("brightness")
            if last_sent and last_sent.get("brightness") is not None
            else (expected_fallback.get("brightness") if expected_fallback else None)
        )
        expected_k = (
            last_sent.get("color_temp_kelvin")
            if last_sent and last_sent.get("color_temp_kelvin") is not None
            else (expected_fallback.get("color_temp_kelvin") if expected_fallback else None)
        )
        expected_m = last_sent.get("color_temp") if last_sent else None
        expected_rgb = (
            last_sent.get("rgb_color")
            if last_sent and last_sent.get("rgb_color") is not None
            else (expected_fallback.get("rgb_color") if expected_fallback else None)
        )

        actual_b = new_attrs.get("brightness")
        actual_k = new_attrs.get("color_temp_kelvin")
        actual_m = new_attrs.get("color_temp")
        actual_rgb = new_attrs.get("rgb_color")

        # If it was off and just turned on (or first seen), notify callback and check for explicit manual turn-on values
        if old_state is None or old_state.state != "on":
            if self.on_lights_on_callback:
                self.on_lights_on_callback(entity_id)
            # If it was turned on with a specific manual brightness that differs from circadian target
            if expected_b is not None and actual_b is not None and abs(actual_b - expected_b) > 15:
                self.set_manual_override(entity_id, new_attrs)
            elif expected_k is not None and actual_k is not None and abs(actual_k - expected_k) > 100:
                self.set_manual_override(entity_id, new_attrs)
            return

        # 1. Check if the reported state matches what coordinator last commanded
        matches_sent = True
        has_comparison = False

        if expected_b is not None and actual_b is not None:
            has_comparison = True
            # 15 units out of 255 (~6%) accommodates Zigbee 254-max caps and dimmer rounding
            if abs(actual_b - expected_b) > 15:
                matches_sent = False

        if expected_k is not None:
            if actual_k is not None or actual_m is not None:
                has_comparison = True
                ct_ok = False
                if actual_k is not None:
                    # Zigbee mired rounding error at high Kelvin can be up to 100K
                    if abs(actual_k - expected_k) <= 100:
                        ct_ok = True
                    elif expected_m and actual_k > 0:
                        act_m = round(1000000 / actual_k)
                        if abs(act_m - expected_m) <= 8:
                            ct_ok = True
                elif actual_m is not None and expected_m is not None:
                    if abs(actual_m - expected_m) <= 8:
                        ct_ok = True
                if not ct_ok:
                    matches_sent = False

        if expected_rgb is not None and actual_rgb is not None:
            has_comparison = True
            if not (len(actual_rgb) >= 3 and len(expected_rgb) >= 3 and
                    all(abs(a - b) <= 25 for a, b in zip(actual_rgb[:3], expected_rgb[:3]))):
                matches_sent = False

        if has_comparison and matches_sent:
            # The state matches coordinator command; NOT a manual override!
            return

        # 2. Check if the bulb is currently ramping towards coordinator's target
        if last_sent:
            time_diff = (datetime.now(timezone.utc) - last_sent["timestamp"]).total_seconds()
            transition = float(last_sent.get("transition", 0.0) or 0.0)

            if transition > 0 and time_diff <= transition + 1.5:
                # We are within active transition duration.
                # Check if this change is an intermediate ramp towards expected target:
                start_b = last_sent.get("start_brightness")
                old_b_raw = old_attrs.get("brightness")
                old_b = old_b_raw if isinstance(old_b_raw, (int, float)) else None
                ref_start = start_b if (start_b is not None and isinstance(start_b, (int, float))) else old_b

                if expected_b is not None and actual_b is not None and ref_start is not None:
                    lower = min(ref_start, expected_b) - 5
                    upper = max(ref_start, expected_b) + 5
                    if lower <= actual_b <= upper:
                        # Bulb is legitimately ramping between start and target
                        return

        # 3. Detect actual manual changes (rotary dimming, dimmer switches, app sliders)
        old_b = old_attrs.get("brightness") if isinstance(old_attrs.get("brightness"), (int, float)) else None
        b_changed = False
        if actual_b is not None:
            if expected_b is not None:
                # Any departure > 15 from expected target is manual override, even if done in small increments
                if abs(actual_b - expected_b) > 15:
                    b_changed = True
            elif old_b is not None and abs(actual_b - old_b) > 8:
                b_changed = True

            # If already overridden, any further dimmer movement updates override state and timer
            if self.is_overridden(entity_id) and old_b is not None and actual_b != old_b:
                b_changed = True

        old_k = old_attrs.get("color_temp_kelvin") if isinstance(old_attrs.get("color_temp_kelvin"), (int, float)) else None
        old_m = old_attrs.get("color_temp") if isinstance(old_attrs.get("color_temp"), (int, float)) else None
        ct_changed = False
        if actual_k is not None:
            if expected_k is not None:
                if abs(actual_k - expected_k) > 100:
                    ct_changed = True
            elif old_k is not None and abs(actual_k - old_k) > 60:
                ct_changed = True
        elif actual_m is not None:
            if expected_m is not None:
                if abs(actual_m - expected_m) > 8:
                    ct_changed = True
            elif old_m is not None and abs(actual_m - old_m) > 4:
                ct_changed = True

        if self.is_overridden(entity_id):
            if actual_k is not None and old_k is not None and actual_k != old_k:
                ct_changed = True
            elif actual_m is not None and old_m is not None and actual_m != old_m:
                ct_changed = True

        old_rgb = old_attrs.get("rgb_color")
        rgb_changed = False
        if actual_rgb is not None:
            if expected_rgb is not None:
                if not (len(actual_rgb) >= 3 and len(expected_rgb) >= 3 and
                        all(abs(a - b) <= 25 for a, b in zip(actual_rgb[:3], expected_rgb[:3]))):
                    rgb_changed = True
            elif old_rgb is not None and actual_rgb != old_rgb:
                rgb_changed = True

        if self.is_overridden(entity_id) and actual_rgb is not None and old_rgb is not None and actual_rgb != old_rgb:
            rgb_changed = True

        if b_changed or ct_changed or rgb_changed:
            self.set_manual_override(entity_id, new_attrs)

