"""Weather and Lux compensation engine for Adaptive Circadian Lighting."""
from __future__ import annotations

import logging
from typing import Any, Tuple

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Weather conditions representing overcast/dark conditions
DARK_CONDITIONS = {
    "cloudy": 0.8,
    "overcast": 1.0,
    "rainy": 0.9,
    "pouring": 1.0,
    "lightning-rainy": 1.0,
    "snowy": 0.7,
    "snowy-rainy": 0.9,
    "fog": 0.8,
    "partlycloudy": 0.35,
    "windy": 0.2,
    "hail": 0.9,
}


class WeatherEngine:
    """Calculates adaptive brightness and kelvin boosts based on weather and lux sensors."""

    def __init__(
        self,
        hass: HomeAssistant,
        weather_entity: str | None = None,
        lux_sensor: str | None = None,
        cloud_boost_pct: int = 25,
        cloud_boost_kelvin: int = 600,
        prioritize_lux: bool = True,
    ) -> None:
        self.hass = hass
        self.weather_entity = weather_entity
        self.lux_sensor = lux_sensor
        self.cloud_boost_pct = cloud_boost_pct
        self.cloud_boost_kelvin = cloud_boost_kelvin
        self.prioritize_lux = prioritize_lux

    def get_weather_data(self) -> Tuple[str | None, float | None]:
        """Fetch condition and cloud coverage from the weather entity."""
        if not self.weather_entity:
            return None, None

        state = self.hass.states.get(self.weather_entity)
        if not state or state.state in ("unknown", "unavailable"):
            return None, None

        condition = state.state.lower()
        cloud_cov = state.attributes.get("cloud_coverage")
        cloud_coverage_val = float(cloud_cov) if cloud_cov is not None else None

        return condition, cloud_coverage_val

    def get_lux_reading(self) -> float | None:
        """Fetch illuminance reading in lux from the lux sensor."""
        if not self.lux_sensor:
            return None

        state = self.hass.states.get(self.lux_sensor)
        if not state or state.state in ("unknown", "unavailable"):
            return None

        try:
            return float(state.state)
        except (ValueError, TypeError):
            return None

    def calculate_boost(
        self, is_daytime: bool
    ) -> Tuple[int, int, str]:
        """Calculate additional brightness percentage and Kelvin boost.
        
        Returns:
            Tuple of (extra_brightness_pct, extra_kelvin, reason_string)
        """
        # We only boost during daytime/twilight hours to avoid ruining night mode
        if not is_daytime:
            return 0, 0, "night_no_boost"

        # 1. Highest Priority: Physical Lux Sensor
        if self.prioritize_lux and self.lux_sensor:
            lux = self.get_lux_reading()
            if lux is not None:
                # Outdoor day lux benchmark: 10,000+ lux is bright daylight.
                # Under 2,500 lux on daytime indicates heavy cloud cover or storm.
                if lux < 10000.0:
                    deficit_ratio = max(0.0, min(1.0, (10000.0 - lux) / 9500.0))
                    extra_bright = int(round(self.cloud_boost_pct * deficit_ratio))
                    extra_k = int(round(self.cloud_boost_kelvin * deficit_ratio))
                    return extra_bright, extra_k, f"lux_sensor_{int(lux)}lx"

        # 2. Priority: Weather Entity (Cloud coverage / Condition)
        condition, cloud_coverage = self.get_weather_data()
        if condition or cloud_coverage is not None:
            factor = 0.0

            if cloud_coverage is not None:
                # Cloud coverage 0..100%
                if cloud_coverage > 40:
                    factor = (cloud_coverage - 40.0) / 60.0  # 0.0 to 1.0
            elif condition in DARK_CONDITIONS:
                factor = DARK_CONDITIONS[condition]

            if factor > 0.05:
                extra_bright = int(round(self.cloud_boost_pct * factor))
                extra_k = int(round(self.cloud_boost_kelvin * factor))
                desc = f"weather_{condition or 'clouds'}_{int(factor*100)}%"
                return extra_bright, extra_k, desc

        return 0, 0, "clear_sky"
