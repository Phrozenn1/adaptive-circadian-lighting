"""Anti-glare service call interceptor to prevent nighttime light blinding."""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from homeassistant.const import EVENT_CALL_SERVICE
from homeassistant.core import Event, HomeAssistant

_LOGGER = logging.getLogger(__name__)


class AntiGlareInterceptor:
    """Intercepts light.turn_on service calls to inject calculated target brightness and color."""

    def __init__(
        self,
        hass: HomeAssistant,
        target_lights: List[str],
        get_target_payload_callback: Callable[[str], Dict[str, Any]],
        enabled: bool = True,
    ) -> None:
        self.hass = hass
        self.target_lights = set(target_lights)
        self.get_target_payload_callback = get_target_payload_callback
        self.enabled = enabled
        self._unsub: Optional[Callable[[], None]] = None

    def start(self) -> None:
        """Start listening to call_service events."""
        if not self.target_lights or not self.enabled:
            return

        self._unsub = self.hass.bus.async_listen(
            EVENT_CALL_SERVICE, self._handle_service_call
        )

    def stop(self) -> None:
        """Stop listening to call_service events."""
        if self._unsub:
            self._unsub()
            self._unsub = None

    def update_targets(self, lights: List[str], enabled: bool) -> None:
        """Update member lights and active state."""
        self.target_lights = set(lights)
        self.enabled = enabled
        if not enabled and self._unsub:
            self.stop()
        elif enabled and not self._unsub:
            self.start()

    def _handle_service_call(self, event: Event) -> None:
        """Intercept light.turn_on and inject parameters if missing."""
        if not self.enabled:
            return

        data = event.data
        if data.get("domain") != "light" or data.get("service") != "turn_on":
            return

        service_data = data.get("service_data")
        if not isinstance(service_data, dict):
            return

        # Check entity IDs targeted by this call
        entity_ids: List[str] = []
        raw_ent = service_data.get("entity_id")
        if isinstance(raw_ent, str):
            entity_ids.append(raw_ent)
        elif isinstance(raw_ent, list):
            entity_ids.extend(raw_ent)

        target_data = data.get("target", {})
        target_ents = target_data.get("entity_id", [])
        if isinstance(target_ents, str):
            entity_ids.append(target_ents)
        elif isinstance(target_ents, list):
            entity_ids.extend(target_ents)

        matched = set(entity_ids) & self.target_lights
        if not matched:
            return

        # If call already specified brightness or color, user/automation explicitly asked for it
        has_bright = "brightness" in service_data or "brightness_pct" in service_data
        has_color = (
            "color_temp" in service_data
            or "color_temp_kelvin" in service_data
            or "rgb_color" in service_data
            or "xy_color" in service_data
            or "hs_color" in service_data
        )

        if has_bright and has_color:
            return

        # Inject missing parameters for each matched light
        for light_id in matched:
            payload = self.get_target_payload_callback(light_id)
            if not has_bright and "brightness_pct" in payload:
                service_data["brightness_pct"] = payload["brightness_pct"]
            if not has_color:
                if "color_temp_kelvin" in payload:
                    service_data["color_temp_kelvin"] = payload["color_temp_kelvin"]
                elif "rgb_color" in payload:
                    service_data["rgb_color"] = payload["rgb_color"]

            _LOGGER.debug(
                "AntiGlare: injected target values into turn_on for %s: %s",
                light_id,
                service_data,
            )
