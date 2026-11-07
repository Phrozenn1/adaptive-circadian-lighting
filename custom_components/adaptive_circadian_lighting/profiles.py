"""Lighting profiles management for Adaptive Circadian Lighting."""
from __future__ import annotations

from datetime import time
from typing import Any, Dict, Optional, Tuple

from .const import (
    DEFAULT_SLEEP_BRIGHTNESS,
    DEFAULT_SLEEP_COLOR_TEMP,
    DEFAULT_SLEEP_END_TIME,
    DEFAULT_SLEEP_RGB,
    DEFAULT_SLEEP_SCHEDULE_ENABLE,
    DEFAULT_SLEEP_START_TIME,
    PROFILE_EVENING,
    PROFILE_FOCUS,
    PROFILE_MORNING,
    PROFILE_NORMAL,
    PROFILE_RELAX,
    PROFILE_SLEEP,
    PROFILES,
)


class ProfileManager:
    """Manages active profiles, sleep schedules, and profile-specific overrides."""

    def __init__(
        self,
        active_profile: str = PROFILE_NORMAL,
        sleep_brightness: int = DEFAULT_SLEEP_BRIGHTNESS,
        sleep_color_temp: int = DEFAULT_SLEEP_COLOR_TEMP,
        sleep_rgb: list[int] | None = None,
        sleep_schedule_enable: bool = DEFAULT_SLEEP_SCHEDULE_ENABLE,
        sleep_start_time: str = DEFAULT_SLEEP_START_TIME,
        sleep_end_time: str = DEFAULT_SLEEP_END_TIME,
    ) -> None:
        self.active_profile = (
            active_profile if active_profile in PROFILES else PROFILE_NORMAL
        )
        self.sleep_brightness = sleep_brightness
        self.sleep_color_temp = sleep_color_temp
        self.sleep_rgb = sleep_rgb or DEFAULT_SLEEP_RGB
        self.sleep_schedule_enable = sleep_schedule_enable
        self.sleep_start_time = sleep_start_time
        self.sleep_end_time = sleep_end_time
        self.sleep_activated_by_schedule = False

    def is_time_in_sleep_window(self, current_time: time) -> bool:
        """Check if a time is within the configured sleep schedule."""
        if not self.sleep_schedule_enable:
            return False

        try:
            start_parts = [int(p) for p in str(self.sleep_start_time).split(":")[:2]]
            end_parts = [int(p) for p in str(self.sleep_end_time).split(":")[:2]]
            start = time(start_parts[0], start_parts[1])
            end = time(end_parts[0], end_parts[1])
        except Exception:
            return False

        if start <= end:
            return start <= current_time < end
        else:
            # Wrap around midnight (e.g. 23:00 to 06:30)
            return current_time >= start or current_time < end

    def evaluate_schedule(self, current_time: time) -> bool:
        """Evaluate schedule and update profile. Returns True if profile changed."""
        if not self.sleep_schedule_enable:
            return False

        in_window = self.is_time_in_sleep_window(current_time)

        if in_window:
            if self.active_profile == PROFILE_NORMAL:
                self.active_profile = PROFILE_SLEEP
                self.sleep_activated_by_schedule = True
                return True
        else:
            if self.active_profile == PROFILE_SLEEP and self.sleep_activated_by_schedule:
                self.active_profile = PROFILE_NORMAL
                self.sleep_activated_by_schedule = False
                return True

        return False

    def set_profile(self, profile: str) -> None:
        """Set the active profile manually."""
        if profile in PROFILES:
            self.active_profile = profile
            self.sleep_activated_by_schedule = False

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
