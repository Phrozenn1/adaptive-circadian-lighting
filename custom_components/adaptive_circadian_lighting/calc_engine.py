"""Calculation engines for Adaptive Circadian Lighting."""
from __future__ import annotations

from datetime import datetime, time
import math
from typing import Any, List, Tuple

from .const import (
    CALC_MODE_CURVE,
    CALC_MODE_HYBRID,
    CALC_MODE_LUX,
    CALC_MODE_SUN,
    DEFAULT_CURVE_POINTS,
    DEFAULT_MAX_BRIGHTNESS,
    DEFAULT_MAX_COLOR_TEMP,
    DEFAULT_MAX_SUNRISE,
    DEFAULT_MAX_SUNSET,
    DEFAULT_MIN_BRIGHTNESS,
    DEFAULT_MIN_COLOR_TEMP,
    DEFAULT_MIN_SUNRISE,
    DEFAULT_MIN_SUNSET,
)


def cosine_interpolate(y1: float, y2: float, mu: float) -> float:
    """Smooth cosine interpolation between y1 and y2 based on fraction mu (0..1)."""
    mu2 = (1.0 - math.cos(mu * math.pi)) / 2.0
    return y1 * (1.0 - mu2) + y2 * mu2


class SunCalculator:
    """Pure astronomical calculation based on solar elevation."""

    def __init__(
        self,
        min_brightness: int = DEFAULT_MIN_BRIGHTNESS,
        max_brightness: int = DEFAULT_MAX_BRIGHTNESS,
        min_kelvin: int = DEFAULT_MIN_COLOR_TEMP,
        max_kelvin: int = DEFAULT_MAX_COLOR_TEMP,
        sunrise_offset: int = 0,
        sunset_offset: int = 0,
    ) -> None:
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.min_kelvin = min_kelvin
        self.max_kelvin = max_kelvin
        self.sunrise_offset = sunrise_offset
        self.sunset_offset = sunset_offset

    def calculate(self, solar_elevation: float) -> Tuple[int, int, str]:
        """Calculate target brightness, Kelvin and phase name based on sun elevation."""
        # Shift elevation based on offset if applicable (~0.25 degrees elevation per minute)
        offset = self.sunrise_offset if solar_elevation <= 15.0 else self.sunset_offset
        effective_elevation = solar_elevation - (offset * 0.25)

        # Elevation ranges:
        # <= -18: Astronomical night
        # -18 to 0: Twilight / Dawn / Dusk
        # 0 to 60: Day
        if effective_elevation <= -18.0:
            return self.min_brightness, self.min_kelvin, "night"

        if effective_elevation >= 60.0:
            return self.max_brightness, self.max_kelvin, "day"

        # Normalize elevation between -18 (0.0) and 60 (1.0)
        fraction = (effective_elevation + 18.0) / 78.0
        fraction = max(0.0, min(1.0, fraction))

        factor = (1.0 - math.cos(fraction * math.pi)) / 2.0

        brightness = int(round(self.min_brightness + factor * (self.max_brightness - self.min_brightness)))
        kelvin = int(round(self.min_kelvin + factor * (self.max_kelvin - self.min_kelvin)))

        if effective_elevation < 0:
            phase = "twilight"
        elif effective_elevation < 15:
            phase = "golden_hour"
        else:
            phase = "day"

        return brightness, kelvin, phase


class HybridCalculator:
    """Hybrid model clamping solar progression with fixed time anchors."""

    def __init__(
        self,
        min_brightness: int = DEFAULT_MIN_BRIGHTNESS,
        max_brightness: int = DEFAULT_MAX_BRIGHTNESS,
        min_kelvin: int = DEFAULT_MIN_COLOR_TEMP,
        max_kelvin: int = DEFAULT_MAX_COLOR_TEMP,
        min_sunrise: str = DEFAULT_MIN_SUNRISE,
        max_sunrise: str = DEFAULT_MAX_SUNRISE,
        min_sunset: str = DEFAULT_MIN_SUNSET,
        max_sunset: str = DEFAULT_MAX_SUNSET,
        sunrise_offset: int = 0,
        sunset_offset: int = 0,
    ) -> None:
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.min_kelvin = min_kelvin
        self.max_kelvin = max_kelvin
        self.sunrise_offset = sunrise_offset
        self.sunset_offset = sunset_offset
        self.min_sunrise = self._parse_time(min_sunrise)
        self.max_sunrise = self._parse_time(max_sunrise)
        self.min_sunset = self._parse_time(min_sunset)
        self.max_sunset = self._parse_time(max_sunset)

    @staticmethod
    def _parse_time(t_str: str) -> float:
        parts = [int(p) for p in t_str.split(":")[:2]]
        return parts[0] + parts[1] / 60.0

    def calculate(
        self, now: datetime, solar_elevation: float | None = None
    ) -> Tuple[int, int, str]:
        """Calculate values clamping astronomical position between target bounds."""
        current_time = now.hour + now.minute / 60.0 + now.second / 3600.0

        # Anchor times adjusted for sunrise and sunset offsets in minutes:
        offset_sunrise_h = self.sunrise_offset / 60.0
        offset_sunset_h = self.sunset_offset / 60.0

        t_wake_start = self.min_sunrise + offset_sunrise_h
        t_day_full = self.max_sunrise + offset_sunrise_h
        t_evening_start = self.min_sunset + offset_sunset_h
        t_night_full = self.max_sunset + offset_sunset_h

        # Night phase
        if current_time < t_wake_start or current_time >= t_night_full:
            return self.min_brightness, self.min_kelvin, "night"

        # Morning ramp-up
        if t_wake_start <= current_time < t_day_full:
            duration = t_day_full - t_wake_start
            fraction = (current_time - t_wake_start) / max(0.01, duration)
            factor = (1.0 - math.cos(fraction * math.pi)) / 2.0
            brightness = int(round(self.min_brightness + factor * (self.max_brightness - self.min_brightness)))
            kelvin = int(round(self.min_kelvin + factor * (self.max_kelvin - self.min_kelvin)))
            return brightness, kelvin, "morning_ramp"

        # Daytime full
        if t_day_full <= current_time < t_evening_start:
            # If solar elevation is available, adjust subtle peak at noon
            factor = 1.0
            if solar_elevation is not None and solar_elevation < 10:
                factor = 0.85 + 0.15 * max(0.0, solar_elevation / 10.0)
            brightness = int(round(self.max_brightness * factor))
            kelvin = int(round(self.max_kelvin * factor))
            return max(self.min_brightness, brightness), max(self.min_kelvin, kelvin), "day"

        # Evening wind-down
        if t_evening_start <= current_time < t_night_full:
            duration = t_night_full - t_evening_start
            fraction = (current_time - t_evening_start) / max(0.01, duration)
            factor = (1.0 + math.cos(fraction * math.pi)) / 2.0
            brightness = int(round(self.min_brightness + factor * (self.max_brightness - self.min_brightness)))
            kelvin = int(round(self.min_kelvin + factor * (self.max_kelvin - self.min_kelvin)))
            return brightness, kelvin, "evening_ramp"

        return self.min_brightness, self.min_kelvin, "night"


class CurveCalculator:
    """24-hour custom curve piecewise-interpolator."""

    def __init__(self, curve_points: List[List[float | int]] | None = None) -> None:
        self.points = sorted(
            curve_points or DEFAULT_CURVE_POINTS, key=lambda p: float(p[0])
        )

    def calculate(self, now: datetime) -> Tuple[int, int, str]:
        """Interpolate brightness and Kelvin at the current time."""
        current_hour = now.hour + now.minute / 60.0 + now.second / 3600.0

        if not self.points:
            return DEFAULT_MIN_BRIGHTNESS, DEFAULT_MIN_COLOR_TEMP, "night"

        # Wrap around if before first point or after last point
        first_pt = self.points[0]
        last_pt = self.points[-1]

        if current_hour <= float(first_pt[0]) or current_hour >= float(last_pt[0]):
            # Wrap around between last_pt and first_pt across midnight (24h)
            p1 = last_pt
            p2 = first_pt
            h1 = float(p1[0])
            h2 = float(p2[0]) + 24.0
            cur = current_hour if current_hour >= float(last_pt[0]) else current_hour + 24.0
            mu = (cur - h1) / max(0.001, (h2 - h1))
            brightness = int(round(cosine_interpolate(float(p1[1]), float(p2[1]), mu)))
            kelvin = int(round(cosine_interpolate(float(p1[2]), float(p2[2]), mu)))
            return max(1, min(100, brightness)), max(1000, kelvin), "night"

        # Find enclosing interval
        for i in range(len(self.points) - 1):
            p1 = self.points[i]
            p2 = self.points[i + 1]
            h1 = float(p1[0])
            h2 = float(p2[0])
            if h1 <= current_hour <= h2:
                mu = (current_hour - h1) / max(0.001, (h2 - h1))
                brightness = int(round(cosine_interpolate(float(p1[1]), float(p2[1]), mu)))
                kelvin = int(round(cosine_interpolate(float(p1[2]), float(p2[2]), mu)))
                phase = "day" if 8.0 <= current_hour <= 18.0 else "transition"
                return max(1, min(100, brightness)), max(1000, kelvin), phase

        return int(self.points[0][1]), int(self.points[0][2]), "curve"
