"""Lighting profiles management for Adaptive Circadian Lighting."""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .const import (
    DEFAULT_SLEEP_BRIGHTNESS,
    DEFAULT_SLEEP_COLOR_TEMP,
    DEFAULT_SLEEP_RGB,
    PROFILE_EVENING,
    PROFILE_FOCUS,
    PROFILE_MORNING,
    PROFILE_NORMAL,
    PROFILE_RELAX,
    PROFILE_SLEEP,
    PROFILES,
)


class ProfileManager:
    """Manages active profiles and profile-specific overrides."""

    def __init__(
        self,
        active_profile: str = PROFILE_NORMAL,
        sleep_brightness: int = DEFAULT_SLEEP_BRIGHTNESS,
        sleep_color_temp: int = DEFAULT_SLEEP_COLOR_TEMP,
        sleep_rgb: list[int] | None = None,
    ) -> None:
        self.active_profile = (
            active_profile if active_profile in PROFILES else PROFILE_NORMAL
        )
        self.sleep_brightness = sleep_brightness
        self.sleep_color_temp = sleep_color_temp
        self.sleep_rgb = sleep_rgb or DEFAULT_SLEEP_RGB

    def set_profile(self, profile: str) -> None:
        """Set the active profile."""
        if profile in PROFILES:
            self.active_profile = profile

    def is_sleep(self) -> bool:
        """Check if sleep mode is active."""
        return self.active_profile == PROFILE_SLEEP

    def get_profile_override(
        self,
    ) -> Optional[Tuple[int, int, Optional[Tuple[int, int, int]]]]:
        """Get static brightness, kelvin, and optional RGB override for the active profile.
        
        Returns:
            Tuple of (brightness_pct, kelvin, rgb_tuple) or None if Normal profile.
        """
        if self.active_profile == PROFILE_NORMAL:
            return None

        if self.active_profile == PROFILE_SLEEP:
            rgb = tuple(self.sleep_rgb) if self.sleep_rgb else (255, 55, 0)
            return self.sleep_brightness, self.sleep_color_temp, rgb

        if self.active_profile == PROFILE_MORNING:
            return 50, 3500, None

        if self.active_profile == PROFILE_EVENING:
            return 30, 2200, None

        if self.active_profile == PROFILE_FOCUS:
            return 100, 5800, None

        if self.active_profile == PROFILE_RELAX:
            return 20, 2200, None

        return None
