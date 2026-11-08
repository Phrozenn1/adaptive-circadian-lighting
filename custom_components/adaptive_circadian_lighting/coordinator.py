"""Central coordinator for Adaptive Circadian Lighting."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.light import ATTR_MAX_COLOR_TEMP_KELVIN, ATTR_MIN_COLOR_TEMP_KELVIN, ATTR_SUPPORTED_COLOR_MODES, DOMAIN as LIGHT_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .anti_glare import AntiGlareInterceptor
from .calc_engine import CurveCalculator, HybridCalculator, SunCalculator
from .color_utils import kelvin_to_rgb, prepare_light_service_data
from .const import (
    CALC_MODE_CURVE,
    CALC_MODE_HYBRID,
    CALC_MODE_LUX,
    CALC_MODE_SUN,
    COLOR_MODE_AUTO,
    CONF_ANTI_GLARE,
    CONF_AUTO_TURN_ON,
    CONF_CALC_MODE,
    CONF_CLOUD_BOOST_KELVIN,
    CONF_CLOUD_BOOST_PCT,
    CONF_COLOR_MODE,
    CONF_CURVE_POINTS,
    CONF_DIM_BRIGHTNESS,
    CONF_DIM_TIMEOUT,
    CONF_GRACE_PERIOD,
    CONF_INTERVAL,
    CONF_LIGHTS,
    CONF_LUX_SENSOR,
    CONF_MAX_BRIGHTNESS,
    CONF_MAX_COLOR_TEMP,
    CONF_MAX_SUNRISE_TIME,
    CONF_MAX_SUNSET_TIME,
    CONF_MIN_BRIGHTNESS,
    CONF_MIN_COLOR_TEMP,
    CONF_MIN_SUNRISE_TIME,
    CONF_MIN_SUNSET_TIME,
    CONF_MOTION_DEBOUNCE,
    CONF_NAME,
    CONF_OFF_TIMEOUT,
    CONF_OVERRIDE_TIMEOUT,
    CONF_PRESENCE_ENABLE,
    CONF_PRESENCE_SENSORS,
    CONF_PRIORITIZE_LUX,
    CONF_SLEEP_END_TIME,
    CONF_SLEEP_ENTITY,
    CONF_SLEEP_SCHEDULE_ENABLE,
    CONF_SLEEP_START_TIME,
    CONF_TRANSITION,
    CONF_TURN_ON_LUX_THRESHOLD,
    CONF_WEATHER_ENTITY,
    CONF_ADAPT_ONLY_ON_BARE_TURN_ON,
    CONF_EVENING_MAX_BRIGHTNESS,
    CONF_INITIAL_ADAPT_BRIGHTNESS,
    CONF_INITIAL_ADAPT_COLOR,
    CONF_SLEEP_BRIGHTNESS,
    CONF_SLEEP_COLOR_TEMP,
    CONF_SLEEP_MOTION_BEHAVIOR,
    CONF_SLEEP_RGB,
    CONF_SLEEP_WEEKEND_ENABLE,
    CONF_SLEEP_WEEKEND_END_TIME,
    CONF_SLEEP_WEEKEND_START_TIME,
    CONF_SUNRISE_OFFSET,
    CONF_SUNSET_OFFSET,
    DEFAULT_ADAPT_ONLY_ON_BARE_TURN_ON,
    DEFAULT_AUTO_TURN_ON,
    DEFAULT_CALC_MODE,
    DEFAULT_COLOR_MODE,
    DEFAULT_DIM_BRIGHTNESS,
    DEFAULT_DIM_TIMEOUT,
    DEFAULT_EVENING_MAX_BRIGHTNESS,
    DEFAULT_GRACE_PERIOD,
    DEFAULT_INITIAL_ADAPT_BRIGHTNESS,
    DEFAULT_INITIAL_ADAPT_COLOR,
    DEFAULT_INTERVAL,
    DEFAULT_MAX_BRIGHTNESS,
    DEFAULT_MAX_COLOR_TEMP,
    DEFAULT_MAX_SUNRISE,
    DEFAULT_MAX_SUNSET,
    DEFAULT_MIN_BRIGHTNESS,
    DEFAULT_MIN_COLOR_TEMP,
    DEFAULT_MIN_SUNRISE,
    DEFAULT_MIN_SUNSET,
    DEFAULT_MOTION_DEBOUNCE,
    DEFAULT_OFF_TIMEOUT,
    DEFAULT_OVERRIDE_TIMEOUT,
    DEFAULT_SLEEP_BRIGHTNESS,
    DEFAULT_SLEEP_COLOR_TEMP,
    DEFAULT_SLEEP_END_TIME,
    DEFAULT_SLEEP_MOTION_BEHAVIOR,
    DEFAULT_SLEEP_RGB,
    DEFAULT_SLEEP_SCHEDULE_ENABLE,
    DEFAULT_SLEEP_START_TIME,
    DEFAULT_SLEEP_WEEKEND_ENABLE,
    DEFAULT_SLEEP_WEEKEND_END_TIME,
    DEFAULT_SLEEP_WEEKEND_START_TIME,
    DEFAULT_SUNRISE_OFFSET,
    DEFAULT_SUNSET_OFFSET,
    DEFAULT_TRANSITION,
    DEFAULT_TURN_ON_LUX_THRESHOLD,
    PROFILE_EVENING,
    PROFILE_NORMAL,
    PROFILE_SLEEP,
)
from .override_manager import OverrideManager
from .presence_manager import PresenceManager
from .profiles import ProfileManager
from .weather_engine import WeatherEngine

_LOGGER = logging.getLogger(__name__)


class AdaptiveCoordinator:
    """Coordinates calculation, presence, weather, profiles, and light adjustments."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry

        config = {**(entry.data or {}), **(entry.options or {})}

        # Config properties
        self.name: str = config.get(CONF_NAME, "Adaptive Lighting")
        lights_raw = config.get(CONF_LIGHTS, [])
        self.lights: List[str] = [lights_raw] if isinstance(lights_raw, str) else list(lights_raw or [])
        self.calc_mode: str = config.get(CONF_CALC_MODE, DEFAULT_CALC_MODE)
        self.color_mode: str = config.get(CONF_COLOR_MODE, DEFAULT_COLOR_MODE)
        self.min_brightness: int = config.get(CONF_MIN_BRIGHTNESS, DEFAULT_MIN_BRIGHTNESS)
        self.max_brightness: int = config.get(CONF_MAX_BRIGHTNESS, DEFAULT_MAX_BRIGHTNESS)
        self.min_kelvin: int = config.get(CONF_MIN_COLOR_TEMP, DEFAULT_MIN_COLOR_TEMP)
        self.max_kelvin: int = config.get(CONF_MAX_COLOR_TEMP, DEFAULT_MAX_COLOR_TEMP)
        self.interval: int = config.get(CONF_INTERVAL, DEFAULT_INTERVAL)
        self.transition: float = float(config.get(CONF_TRANSITION, DEFAULT_TRANSITION))
        self.sunrise_offset: int = config.get(CONF_SUNRISE_OFFSET, DEFAULT_SUNRISE_OFFSET)
        self.sunset_offset: int = config.get(CONF_SUNSET_OFFSET, DEFAULT_SUNSET_OFFSET)
        self.adapt_only_on_turn_on: bool = config.get(CONF_ADAPT_ONLY_ON_BARE_TURN_ON, DEFAULT_ADAPT_ONLY_ON_BARE_TURN_ON)
        self.evening_max_brightness: int = config.get(CONF_EVENING_MAX_BRIGHTNESS, DEFAULT_EVENING_MAX_BRIGHTNESS)
        self._already_adapted_lights: set[str] = set()

        # Toggles
        self.adaptation_enabled: bool = True
        self.adapt_brightness_enabled: bool = config.get(CONF_INITIAL_ADAPT_BRIGHTNESS, DEFAULT_INITIAL_ADAPT_BRIGHTNESS)
        self.adapt_color_enabled: bool = config.get(CONF_INITIAL_ADAPT_COLOR, DEFAULT_INITIAL_ADAPT_COLOR)

        # State outputs
        self.target_brightness: int = 100
        self.target_kelvin: int = 4000
        self.target_rgb: List[int] = [255, 180, 100]
        self.phase: str = "day"
        self.weather_boost_desc: str = "none"

        # Engines
        self.sun_calc = SunCalculator(
            self.min_brightness,
            self.max_brightness,
            self.min_kelvin,
            self.max_kelvin,
            sunrise_offset=self.sunrise_offset,
            sunset_offset=self.sunset_offset,
        )
        self.hybrid_calc = HybridCalculator(
            self.min_brightness,
            self.max_brightness,
            self.min_kelvin,
            self.max_kelvin,
            min_sunrise=config.get(CONF_MIN_SUNRISE_TIME, DEFAULT_MIN_SUNRISE),
            max_sunrise=config.get(CONF_MAX_SUNRISE_TIME, DEFAULT_MAX_SUNRISE),
            min_sunset=config.get(CONF_MIN_SUNSET_TIME, DEFAULT_MIN_SUNSET),
            max_sunset=config.get(CONF_MAX_SUNSET_TIME, DEFAULT_MAX_SUNSET),
            sunrise_offset=self.sunrise_offset,
            sunset_offset=self.sunset_offset,
        )
        self.curve_calc = CurveCalculator(config.get(CONF_CURVE_POINTS))

        presence_enabled = config.get(CONF_PRESENCE_ENABLE, False)
        presence_sensors_raw = config.get(CONF_PRESENCE_SENSORS, [])
        presence_sensors: List[str] = [presence_sensors_raw] if isinstance(presence_sensors_raw, str) else list(presence_sensors_raw or [])
        self.presence_mgr: Optional[PresenceManager] = None
        if presence_enabled and presence_sensors:
            self.presence_mgr = PresenceManager(
                hass,
                sensors=presence_sensors,
                dim_timeout=config.get(CONF_DIM_TIMEOUT, DEFAULT_DIM_TIMEOUT),
                off_timeout=config.get(CONF_OFF_TIMEOUT, DEFAULT_OFF_TIMEOUT),
                grace_period=config.get(CONF_GRACE_PERIOD, DEFAULT_GRACE_PERIOD),
                dim_brightness=config.get(CONF_DIM_BRIGHTNESS, DEFAULT_DIM_BRIGHTNESS),
                auto_turn_on=config.get(CONF_AUTO_TURN_ON, DEFAULT_AUTO_TURN_ON),
                turn_on_lux_threshold=config.get(CONF_TURN_ON_LUX_THRESHOLD, DEFAULT_TURN_ON_LUX_THRESHOLD),
                motion_debounce=config.get(CONF_MOTION_DEBOUNCE, DEFAULT_MOTION_DEBOUNCE),
                sleep_motion_behavior=config.get(CONF_SLEEP_MOTION_BEHAVIOR, DEFAULT_SLEEP_MOTION_BEHAVIOR),
                lux_sensor=config.get(CONF_LUX_SENSOR),
                are_lights_off_callback=self._are_all_lights_off,
                is_sleep_callback=lambda: self.profile_mgr.is_sleep(),
                on_dim_callback=self._on_presence_dim,
                on_off_callback=self._on_presence_off,
                on_restore_manual_callback=self._on_presence_restore_manual,
                on_turn_on_adaptive_callback=self._on_presence_turn_on_adaptive,
            )

        self.weather_engine = WeatherEngine(
            hass,
            weather_entity=config.get(CONF_WEATHER_ENTITY),
            lux_sensor=config.get(CONF_LUX_SENSOR),
            cloud_boost_pct=config.get(CONF_CLOUD_BOOST_PCT, 25),
            cloud_boost_kelvin=config.get(CONF_CLOUD_BOOST_KELVIN, 600),
            prioritize_lux=config.get(CONF_PRIORITIZE_LUX, True),
            get_presence_lux_callback=lambda: self.presence_mgr.get_ambient_lux() if self.presence_mgr else None,
        )

        self.profile_mgr = ProfileManager(
            sleep_brightness=config.get(CONF_SLEEP_BRIGHTNESS, DEFAULT_SLEEP_BRIGHTNESS),
            sleep_color_temp=config.get(CONF_SLEEP_COLOR_TEMP, DEFAULT_SLEEP_COLOR_TEMP),
            sleep_rgb=config.get(CONF_SLEEP_RGB, DEFAULT_SLEEP_RGB),
            sleep_schedule_enable=config.get(CONF_SLEEP_SCHEDULE_ENABLE, DEFAULT_SLEEP_SCHEDULE_ENABLE),
            sleep_start_time=config.get(CONF_SLEEP_START_TIME, DEFAULT_SLEEP_START_TIME),
            sleep_end_time=config.get(CONF_SLEEP_END_TIME, DEFAULT_SLEEP_END_TIME),
            sleep_weekend_enable=config.get(CONF_SLEEP_WEEKEND_ENABLE, DEFAULT_SLEEP_WEEKEND_ENABLE),
            sleep_weekend_start_time=config.get(CONF_SLEEP_WEEKEND_START_TIME, DEFAULT_SLEEP_WEEKEND_START_TIME),
            sleep_weekend_end_time=config.get(CONF_SLEEP_WEEKEND_END_TIME, DEFAULT_SLEEP_WEEKEND_END_TIME),
        )
        self.sleep_entity: Optional[str] = config.get(CONF_SLEEP_ENTITY)
        self._unsub_sleep_entity: Optional[Callable[[], None]] = None

        self.override_mgr = OverrideManager(
            hass,
            lights=self.lights,
            timeout_minutes=config.get(CONF_OVERRIDE_TIMEOUT, DEFAULT_OVERRIDE_TIMEOUT),
            on_override_reset_callback=self._on_override_reset,
            on_manual_change_callback=self._on_manual_change,
            on_lights_off_callback=self._handle_light_turned_off,
        )

        anti_glare_on = config.get(CONF_ANTI_GLARE, True)
        self.anti_glare = AntiGlareInterceptor(
            hass,
            target_lights=self.lights,
            get_target_payload_callback=self._get_anti_glare_payload,
            enabled=anti_glare_on,
        )

        self._unsub_interval: Optional[Callable[[], None]] = None
        self._listeners: List[Callable[[], None]] = []

    async def async_setup(self) -> None:
        """Start tracking and scheduled intervals."""
        self.override_mgr.start_tracking()
        if self.presence_mgr:
            self.presence_mgr.start_tracking()
        self.anti_glare.start()

        if self.sleep_entity:
            from homeassistant.helpers.event import async_track_state_change_event
            self._unsub_sleep_entity = async_track_state_change_event(
                self.hass, [self.sleep_entity], self._handle_sleep_entity_change
            )

        # Initial calculation
        self._calculate_target_values()

        # Start periodic update
        from datetime import timedelta
        self._unsub_interval = async_track_time_interval(
            self.hass, self._async_periodic_update, timedelta(seconds=self.interval)
        )

    async def async_unload(self) -> None:
        """Tear down listeners and timers."""
        if self._unsub_interval:
            self._unsub_interval()
            self._unsub_interval = None
        if self._unsub_sleep_entity:
            self._unsub_sleep_entity()
            self._unsub_sleep_entity = None
        self.override_mgr.stop_tracking()
        if self.presence_mgr:
            self.presence_mgr.stop_tracking()
        self.anti_glare.stop()

    def register_listener(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Register entity update listener."""
        self._listeners.append(callback)
        def unsub():
            if callback in self._listeners:
                self._listeners.remove(callback)
        return unsub

    def _notify_listeners(self) -> None:
        """Notify entity observers."""
        for cb in self._listeners:
            cb()

    def _get_solar_elevation(self) -> Optional[float]:
        """Fetch solar elevation from sun.sun entity if available."""
        sun_state = self.hass.states.get("sun.sun")
        if sun_state and "elevation" in sun_state.attributes:
            try:
                return float(sun_state.attributes["elevation"])
            except (ValueError, TypeError):
                return None
        return None

    def _handle_sleep_entity_change(self, event: Any) -> None:
        """Handle state change of external sleep entity."""
        new_state = event.data.get("new_state")
        if not new_state:
            return
        is_sleep = new_state.state in ("on", "true", "True", "detected", "active", "sleeping", "home")
        if is_sleep:
            self.profile_mgr.set_profile(PROFILE_SLEEP)
        else:
            if self.profile_mgr.is_sleep():
                self.profile_mgr.set_profile(PROFILE_NORMAL)
        self._calculate_target_values()
        self._notify_listeners()

    def _calculate_target_values(self) -> None:
        """Calculate desired brightness and Kelvin based on mode, weather, schedule and profiles."""
        now = datetime.now()
        elevation = self._get_solar_elevation()

        # Evaluate automatic sleep schedule (passes full datetime to support weekend schedule)
        if self.profile_mgr.evaluate_schedule(now):
            _LOGGER.debug(
                "AdaptiveCoordinator: sleep schedule switched profile to %s",
                self.profile_mgr.active_profile,
            )

        # 1. Profile override check
        profile_override = self.profile_mgr.get_profile_override()
        if profile_override is not None:
            self.target_brightness, self.target_kelvin, rgb_ov = profile_override
            self.phase = f"profile_{self.profile_mgr.active_profile}"
            if self.evening_max_brightness > 0 and self.profile_mgr.active_profile == PROFILE_EVENING:
                self.target_brightness = min(self.target_brightness, self.evening_max_brightness)
            if rgb_ov is not None:
                self.target_rgb = list(rgb_ov)
            else:
                self.target_rgb = list(kelvin_to_rgb(self.target_kelvin))
            return

        # 2. Base Calculation Mode
        if self.calc_mode == CALC_MODE_SUN:
            elev = elevation if elevation is not None else 10.0
            bright, kelvin, phase = self.sun_calc.calculate(elev)
        elif self.calc_mode == CALC_MODE_CURVE:
            bright, kelvin, phase = self.curve_calc.calculate(now)
        elif self.calc_mode in (CALC_MODE_HYBRID, CALC_MODE_LUX):
            bright, kelvin, phase = self.hybrid_calc.calculate(now, elevation)
        else:
            bright, kelvin, phase = self.hybrid_calc.calculate(now, elevation)

        # 3. Weather / Lux Boost
        is_day = phase in ("day", "morning_ramp", "golden_hour")
        boost_b, boost_k, reason = self.weather_engine.calculate_boost(is_day)
        self.weather_boost_desc = reason

        self.target_brightness = max(1, min(100, bright + boost_b))
        self.target_kelvin = max(1000, min(10000, kelvin + boost_k))
        self.phase = phase

        # 4. Evening Brightness Cap
        if self.evening_max_brightness > 0:
            is_evening_or_night = phase in ("evening_ramp", "night", "twilight")
            if is_evening_or_night:
                self.target_brightness = min(self.target_brightness, self.evening_max_brightness)

        # 5. Live target RGB
        if self.profile_mgr.is_sleep() and self.profile_mgr.sleep_rgb:
            self.target_rgb = list(self.profile_mgr.sleep_rgb)
        else:
            self.target_rgb = list(kelvin_to_rgb(self.target_kelvin))

    def _get_anti_glare_payload(self, entity_id: str) -> Dict[str, Any]:
        """Return target payload for intercepted light.turn_on."""
        self._calculate_target_values()
        self._already_adapted_lights.add(entity_id)
        st = self.hass.states.get(entity_id)
        modes = st.attributes.get(ATTR_SUPPORTED_COLOR_MODES) if st else []
        min_k = st.attributes.get(ATTR_MIN_COLOR_TEMP_KELVIN) if st else None
        max_k = st.attributes.get(ATTR_MAX_COLOR_TEMP_KELVIN) if st else None

        rgb_override = (
            tuple(self.profile_mgr.sleep_rgb)
            if self.profile_mgr.is_sleep()
            else None
        )

        return prepare_light_service_data(
            modes,
            min_k,
            max_k,
            self.target_brightness,
            self.target_kelvin,
            mode_pref=self.color_mode,
            rgb_override=rgb_override,
            transition=0.5,
        )

    async def _async_periodic_update(self, _now: Any = None) -> None:
        """Periodic loop to adapt lights."""
        if not self.adaptation_enabled:
            return

        self._calculate_target_values()
        self._notify_listeners()

        # Update lights that are ON and NOT manually overridden
        for light_id in self.lights:
            if self.override_mgr.is_overridden(light_id):
                continue

            st = self.hass.states.get(light_id)
            if not st or st.state != "on":
                self._already_adapted_lights.discard(light_id)
                continue

            # If adapt_only_on_turn_on is active, do not adapt again while already on
            if self.adapt_only_on_turn_on and light_id in self._already_adapted_lights:
                continue

            await self._async_apply_to_light(light_id)
            self._already_adapted_lights.add(light_id)

    async def _async_apply_to_light(
        self,
        light_id: str,
        custom_transition: Optional[float] = None,
        allow_turn_on: bool = False,
    ) -> None:
        """Send adapted brightness and color to a single light."""
        st = self.hass.states.get(light_id)
        if not st:
            return

        # Never send turn_on commands to lights that are currently off unless explicitly permitted
        if st.state != "on" and not allow_turn_on:
            return

        modes = st.attributes.get(ATTR_SUPPORTED_COLOR_MODES)
        min_k = st.attributes.get(ATTR_MIN_COLOR_TEMP_KELVIN)
        max_k = st.attributes.get(ATTR_MAX_COLOR_TEMP_KELVIN)

        rgb_override = (
            tuple(self.profile_mgr.sleep_rgb)
            if self.profile_mgr.is_sleep()
            else None
        )

        payload = prepare_light_service_data(
            modes,
            min_k,
            max_k,
            self.target_brightness,
            self.target_kelvin,
            mode_pref=self.color_mode,
            rgb_override=rgb_override,
            transition=custom_transition or self.transition,
        )

        # Filter out brightness or color if their respective adapt switches are off
        if not self.adapt_brightness_enabled:
            payload.pop("brightness_pct", None)
        if not self.adapt_color_enabled:
            payload.pop("color_temp_kelvin", None)
            payload.pop("rgb_color", None)

        payload["entity_id"] = light_id

        # Record this outgoing command in override manager so we don't trigger false manual override
        self.override_mgr.record_sent_state(light_id, payload)

        await self.hass.services.async_call(
            LIGHT_DOMAIN, "turn_on", payload, blocking=False
        )

    # --- Presence Callbacks ---
    async def _on_presence_dim(self) -> None:
        """Dim active lights when room has been empty for dim_timeout."""
        dim_pct = self.presence_mgr.dim_brightness if self.presence_mgr else 10
        for light_id in self.lights:
            st = self.hass.states.get(light_id)
            if st and st.state == "on":
                await self.hass.services.async_call(
                    LIGHT_DOMAIN,
                    "turn_on",
                    {"entity_id": light_id, "brightness_pct": dim_pct, "transition": 3.0},
                    blocking=False,
                )

    async def _on_presence_off(self) -> None:
        """Turn off lights when room has been empty for off_timeout."""
        for light_id in self.lights:
            st = self.hass.states.get(light_id)
            if st and st.state == "on":
                await self.hass.services.async_call(
                    LIGHT_DOMAIN,
                    "turn_off",
                    {"entity_id": light_id, "transition": 2.0},
                    blocking=False,
                )

    def _are_all_lights_off(self) -> bool:
        """Check if all managed lights are off."""
        if not self.lights:
            return True
        for light_id in self.lights:
            st = self.hass.states.get(light_id)
            if st and st.state == "on":
                return False
        return True

    def _handle_light_turned_off(self, entity_id: str) -> None:
        """Handle when a light is turned off."""
        self._already_adapted_lights.discard(entity_id)
        if self._are_all_lights_off():
            if self.presence_mgr:
                self.presence_mgr.on_lights_turned_off()
            self._notify_listeners()

    async def _on_presence_restore_manual(self, saved_states: Dict[str, Dict[str, Any]]) -> None:
        """Restore manual adjustments when reoccupied within grace period."""
        self._calculate_target_values()
        for light_id in self.lights:
            if light_id in saved_states:
                attrs = saved_states[light_id]
                payload: Dict[str, Any] = {"entity_id": light_id, "transition": 1.0}
                if attrs.get("brightness") is not None:
                    payload["brightness"] = attrs["brightness"]
                if attrs.get("color_temp_kelvin") is not None:
                    payload["color_temp_kelvin"] = attrs["color_temp_kelvin"]
                elif attrs.get("rgb_color") is not None:
                    payload["rgb_color"] = attrs["rgb_color"]

                self.override_mgr.record_sent_state(light_id, payload)
                self.override_mgr.set_manual_override(light_id, attrs)
                await self.hass.services.async_call(LIGHT_DOMAIN, "turn_on", payload, blocking=False)
            else:
                await self._async_apply_to_light(light_id, custom_transition=1.0, allow_turn_on=True)
            self._already_adapted_lights.add(light_id)

    async def _on_presence_turn_on_adaptive(self) -> None:
        """Turn on lights with fresh adaptive settings when room reoccupied."""
        self._calculate_target_values()
        for light_id in self.lights:
            await self._async_apply_to_light(light_id, custom_transition=1.0, allow_turn_on=True)
            self._already_adapted_lights.add(light_id)

    # --- Override Callbacks ---
    def _on_manual_change(self, entity_id: str, attributes: Dict[str, Any]) -> None:
        """Save manual adjustment into presence manager memory."""
        if self.presence_mgr:
            self.presence_mgr.save_manual_state(entity_id, attributes)
        self._notify_listeners()

    def _on_override_reset(self, entity_id: str) -> None:
        """Re-apply adaptive settings when override expires (only if light is currently ON)."""
        st = self.hass.states.get(entity_id)
        if st and st.state == "on":
            self.hass.async_create_task(self._async_apply_to_light(entity_id))
        self._notify_listeners()
