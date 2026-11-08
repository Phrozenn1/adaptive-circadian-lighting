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

        # If it was off and just turned on (or discovered during HA startup), let coordinator adapt it
        if old_state is None or old_state.state != "on":
            if self.on_lights_on_callback:
                self.on_lights_on_callback(entity_id)
            return

        new_attrs = getattr(new_state, "attributes", {}) or {}
        old_attrs = getattr(old_state, "attributes", {}) or {}

        new_b = new_attrs.get("brightness") if isinstance(new_attrs.get("brightness"), (int, float)) else None
        old_b = old_attrs.get("brightness") if isinstance(old_attrs.get("brightness"), (int, float)) else None

        new_k = new_attrs.get("color_temp_kelvin") if isinstance(new_attrs.get("color_temp_kelvin"), (int, float)) else None
        old_k = old_attrs.get("color_temp_kelvin") if isinstance(old_attrs.get("color_temp_kelvin"), (int, float)) else None

        new_m = new_attrs.get("color_temp") if isinstance(new_attrs.get("color_temp"), (int, float)) else None
        old_m = old_attrs.get("color_temp") if isinstance(old_attrs.get("color_temp"), (int, float)) else None

        new_rgb = new_attrs.get("rgb_color") if isinstance(new_attrs.get("rgb_color"), (list, tuple)) else None
        old_rgb = old_attrs.get("rgb_color") if isinstance(old_attrs.get("rgb_color"), (list, tuple)) else None

        b_changed_step = (new_b is not None and old_b is not None and new_b != old_b)
        k_changed_step = (new_k is not None and old_k is not None and new_k != old_k)
        m_changed_step = (new_m is not None and old_m is not None and new_m != old_m)
        rgb_changed_step = (new_rgb is not None and old_rgb is not None and new_rgb != old_rgb)

        # 1. Heartbeat / non-lighting attribute check: if no lighting attribute changed, ignore
        if not (b_changed_step or k_changed_step or m_changed_step or rgb_changed_step):
            return

        last_sent = self._last_sent_states.get(entity_id)
        expected_b = last_sent.get("brightness") if last_sent else None
        expected_k = last_sent.get("color_temp_kelvin") if last_sent else None
        expected_m = last_sent.get("color_temp") if last_sent else None
        expected_rgb = last_sent.get("rgb_color") if last_sent else None
        transition = float(last_sent.get("transition", 0.0) or 0.0) if last_sent else 0.0
        time_diff = (datetime.now(timezone.utc) - last_sent["timestamp"]).total_seconds() if last_sent else 999999.0

        # 2. Check if the changes match what coordinator last commanded
        b_matches = (expected_b is not None and new_b is not None and abs(new_b - expected_b) <= 15)

        k_matches = False
        if expected_k is not None:
            if new_k is not None and abs(new_k - expected_k) <= 100:
                k_matches = True
            elif expected_m and new_k and new_k > 0 and abs(round(1000000 / new_k) - expected_m) <= 8:
                k_matches = True
            elif expected_m and new_m and abs(new_m - expected_m) <= 8:
                k_matches = True
        elif expected_m is not None and new_m is not None and abs(new_m - expected_m) <= 8:
            k_matches = True

        rgb_matches = (
            expected_rgb is not None
            and new_rgb is not None
            and len(new_rgb) >= 3
            and len(expected_rgb) >= 3
            and all(abs(a - b) <= 25 for a, b in zip(new_rgb[:3], expected_rgb[:3]))
        )

        b_ok = (not b_changed_step) or b_matches
        k_ok = (not (k_changed_step or m_changed_step)) or k_matches
        rgb_ok = (not rgb_changed_step) or rgb_matches

        if b_ok and k_ok and rgb_ok:
            # All attributes that changed in this event match coordinator commands
            return

        # 3. Check if the change is a legitimate ramp during an active transition
        if transition > 0 and time_diff <= transition + 2.5:
            start_b = last_sent.get("start_brightness") if last_sent else None
            ref_start = start_b if (start_b is not None and isinstance(start_b, (int, float))) else old_b

            b_ramp = True
            if b_changed_step:
                if expected_b is not None and new_b is not None and ref_start is not None:
                    lower_b = min(ref_start, expected_b) - 8
                    upper_b = max(ref_start, expected_b) + 8
                    b_ramp = (lower_b <= new_b <= upper_b)
                else:
                    b_ramp = False

            k_ramp = True
            if k_changed_step or m_changed_step:
                if expected_k is not None and new_k is not None and old_k is not None:
                    lower_k = min(old_k, expected_k) - 60
                    upper_k = max(old_k, expected_k) + 60
                    k_ramp = (lower_k <= new_k <= upper_k)
                else:
                    k_ramp = False

            if b_ramp and k_ramp:
                return

        # 4. Genuine manual override detection (dimmer switches, rotary dials, UI sliders)
        is_already_overridden = self.is_overridden(entity_id)

        b_override = False
        if b_changed_step and new_b is not None:
            if is_already_overridden:
                b_override = True
            elif expected_b is not None:
                # Any departure > 15 from expected target is manual override (handles rotary & step dimming)
                if abs(new_b - expected_b) > 15:
                    b_override = True
            elif old_b is not None and abs(new_b - old_b) > 8:
                b_override = True

        k_override = False
        if (k_changed_step or m_changed_step):
            if is_already_overridden:
                k_override = True
            elif expected_k is not None:
                if new_k is not None and abs(new_k - expected_k) > 100:
                    k_override = True
                elif expected_m and new_m and abs(new_m - expected_m) > 8:
                    k_override = True
            elif (old_k is not None and new_k is not None and abs(new_k - old_k) > 60) or \
                 (old_m is not None and new_m is not None and abs(new_m - old_m) > 4):
                k_override = True

        rgb_override = False
        if rgb_changed_step and new_rgb is not None:
            if is_already_overridden:
                rgb_override = True
            elif expected_rgb is not None:
                if not (len(new_rgb) >= 3 and len(expected_rgb) >= 3 and
                        all(abs(a - b) <= 25 for a, b in zip(new_rgb[:3], expected_rgb[:3]))):
                    rgb_override = True
            elif old_rgb is not None and new_rgb != old_rgb:
                rgb_override = True

        if b_override or k_override or rgb_override:
            self.set_manual_override(entity_id, new_attrs)

