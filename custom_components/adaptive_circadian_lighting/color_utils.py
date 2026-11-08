"""Color conversion and mode decision utilities."""
from __future__ import annotations

import math
from typing import Any, Tuple

from .const import COLOR_MODE_AUTO, COLOR_MODE_KELVIN, COLOR_MODE_RGB


def kelvin_to_rgb(kelvin: int | float) -> Tuple[int, int, int]:
    """Convert a color temperature in Kelvin to an (R, G, B) tuple.
    
    Based on Tanner Helland's Planckian Blackbody algorithm, calibrated
    for smart lighting LEDs.
    """
    temp = max(1000.0, min(40000.0, float(kelvin))) / 100.0

    # Calculate Red
    if temp <= 66:
        r = 255.0
    else:
        r = temp - 60
        r = 329.698727446 * (r ** -0.1332047592)
        r = max(0.0, min(255.0, r))

    # Calculate Green
    if temp <= 66:
        g = temp
        g = 99.4708025861 * math.log(g) - 161.1195681661
        g = max(0.0, min(255.0, g))
    else:
        g = temp - 60
        g = 288.1221695283 * (g ** -0.0755148492)
        g = max(0.0, min(255.0, g))

    # Calculate Blue
    if temp >= 66:
        b = 255.0
    elif temp <= 19:
        b = 0.0
    else:
        b = temp - 10
        b = 138.5177312231 * math.log(b) - 305.0447927307
        b = max(0.0, min(255.0, b))

    return int(round(r)), int(round(g)), int(round(b))


def rgb_to_kelvin(r: int, g: int, b: int) -> int:
    """Approximate color temperature in Kelvin from an RGB value using McCamy's formula."""
    # Convert sRGB to linear RGB
    def to_linear(c: float) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r_lin = to_linear(r)
    g_lin = to_linear(g)
    b_lin = to_linear(b)

    # sRGB to XYZ matrix
    x_val = r_lin * 0.4124 + g_lin * 0.3576 + b_lin * 0.1805
    y_val = r_lin * 0.2126 + g_lin * 0.7152 + b_lin * 0.0722
    z_val = r_lin * 0.0193 + g_lin * 0.1192 + b_lin * 0.9505

    sum_xyz = x_val + y_val + z_val
    if sum_xyz == 0:
        return 2700

    x = x_val / sum_xyz
    y = y_val / sum_xyz

    # McCamy formula
    denom = 0.1858 - y
    if denom == 0:
        return 2700
    n = (x - 0.3320) / denom
    cct = 449.0 * (n ** 3) + 3525.0 * (n ** 2) + 6823.3 * n + 5520.33

    return int(max(1000, min(15000, round(cct))))


def prepare_light_service_data(
    supported_modes: list[str] | set[str] | None,
    min_kelvin: int | None,
    max_kelvin: int | None,
    brightness_pct: int,
    target_kelvin: int,
    mode_pref: str = COLOR_MODE_AUTO,
    rgb_override: tuple[int, int, int] | None = None,
    transition: float | None = None,
) -> dict[str, Any]:
    """Determine the exact service payload for light.turn_on."""
    modes = set(supported_modes or [])
    if modes == {"onoff"}:
        return {}

    service_data: dict[str, Any] = {
        "brightness_pct": max(1, min(100, int(brightness_pct)))
    }
    if transition is not None:
        service_data["transition"] = float(transition)
    supports_kelvin = "color_temp" in modes or "color_temp_kelvin" in modes
    supports_rgb = bool({"rgb", "rgbw", "rgbww", "xy", "hs"} & modes)

    bulb_min_k = min_kelvin or 2200
    bulb_max_k = max_kelvin or 6500

    # 1. Explicit RGB override (e.g. from Sleep profile or manual RGB)
    if rgb_override is not None:
        if supports_rgb or not supports_kelvin:
            service_data["rgb_color"] = list(rgb_override)
            return service_data

    # 2. RGB Mode Preferred
    if mode_pref == COLOR_MODE_RGB:
        if supports_rgb:
            service_data["rgb_color"] = list(kelvin_to_rgb(target_kelvin))
            return service_data
        elif supports_kelvin:
            clamped_k = max(bulb_min_k, min(bulb_max_k, target_kelvin))
            service_data["color_temp_kelvin"] = clamped_k
            return service_data

    # 3. Auto / Hybrid Mode
    if mode_pref == COLOR_MODE_AUTO:
        # If target temperature is lower than what the bulb's white diodes can output,
        # and bulb supports RGB, use rich amber/red RGB!
        if supports_rgb and (target_kelvin < bulb_min_k):
            service_data["rgb_color"] = list(kelvin_to_rgb(target_kelvin))
            return service_data

        if supports_kelvin:
            clamped_k = max(bulb_min_k, min(bulb_max_k, target_kelvin))
            service_data["color_temp_kelvin"] = clamped_k
            return service_data
        elif supports_rgb:
            service_data["rgb_color"] = list(kelvin_to_rgb(target_kelvin))
            return service_data

    # 4. Kelvin Mode Preferred
    if supports_kelvin:
        clamped_k = max(bulb_min_k, min(bulb_max_k, target_kelvin))
        service_data["color_temp_kelvin"] = clamped_k
    elif supports_rgb:
        service_data["rgb_color"] = list(kelvin_to_rgb(target_kelvin))

    return service_data
