"""Constants for Adaptive Circadian Lighting."""
from __future__ import annotations

DOMAIN = "adaptive_circadian_lighting"

# Configuration and options keys
CONF_NAME = "name"
CONF_LIGHTS = "lights"
CONF_CALC_MODE = "calc_mode"
CONF_COLOR_MODE = "color_mode"
CONF_MIN_BRIGHTNESS = "min_brightness"
CONF_MAX_BRIGHTNESS = "max_brightness"
CONF_MIN_COLOR_TEMP = "min_color_temp"
CONF_MAX_COLOR_TEMP = "max_color_temp"
CONF_INTERVAL = "interval"
CONF_TRANSITION = "transition"
CONF_OVERRIDE_TIMEOUT = "override_timeout"
CONF_ANTI_GLARE = "anti_glare"

# Calculation Modes
CALC_MODE_SUN = "sun"
CALC_MODE_HYBRID = "hybrid"
CALC_MODE_CURVE = "curve"
CALC_MODE_LUX = "lux"
CALC_MODES = [CALC_MODE_SUN, CALC_MODE_HYBRID, CALC_MODE_CURVE, CALC_MODE_LUX]

# Color Modes
COLOR_MODE_KELVIN = "kelvin"
COLOR_MODE_RGB = "rgb"
COLOR_MODE_AUTO = "auto"
COLOR_MODES = [COLOR_MODE_KELVIN, COLOR_MODE_RGB, COLOR_MODE_AUTO]

# Profiles
PROFILE_NORMAL = "normal"
PROFILE_SLEEP = "sleep"
PROFILE_MORNING = "morning"
PROFILE_EVENING = "evening"
PROFILE_FOCUS = "focus"
PROFILE_RELAX = "relax"
PROFILES = [
    PROFILE_NORMAL,
    PROFILE_SLEEP,
    PROFILE_MORNING,
    PROFILE_EVENING,
    PROFILE_FOCUS,
    PROFILE_RELAX,
]

# Weather & Lux Settings
CONF_WEATHER_ENTITY = "weather_entity"
CONF_LUX_SENSOR = "lux_sensor"
CONF_CLOUD_BOOST_PCT = "cloud_boost_pct"
CONF_CLOUD_BOOST_KELVIN = "cloud_boost_kelvin"
CONF_PRIORITIZE_LUX = "prioritize_lux"

# Presence & Motion Settings
CONF_PRESENCE_ENABLE = "presence_enable"
CONF_PRESENCE_SENSORS = "presence_sensors"
CONF_AUTO_TURN_ON = "auto_turn_on"
CONF_TURN_ON_LUX_THRESHOLD = "turn_on_lux_threshold"
CONF_MOTION_DEBOUNCE = "motion_debounce"
CONF_DIM_TIMEOUT = "dim_timeout"        # seconds after motion stops to dim
CONF_OFF_TIMEOUT = "off_timeout"        # seconds after dimming to turn off
CONF_GRACE_PERIOD = "grace_period"      # seconds to remember manual settings
CONF_DIM_BRIGHTNESS = "dim_brightness"  # brightness % during dim phase

# Sleep Schedule Settings
CONF_SLEEP_SCHEDULE_ENABLE = "sleep_schedule_enable"
CONF_SLEEP_START_TIME = "sleep_start_time"
CONF_SLEEP_END_TIME = "sleep_end_time"
CONF_SLEEP_ENTITY = "sleep_entity"

# Hybrid Anchors
CONF_MIN_SUNRISE_TIME = "min_sunrise_time"
CONF_MAX_SUNRISE_TIME = "max_sunrise_time"
CONF_MIN_SUNSET_TIME = "min_sunset_time"
CONF_MAX_SUNSET_TIME = "max_sunset_time"

# Custom Curve Points: list of [hour_float, brightness_pct, kelvin]
CONF_CURVE_POINTS = "curve_points"

DEFAULT_SLEEP_SCHEDULE_ENABLE = False
DEFAULT_SLEEP_START_TIME = "23:00:00"
DEFAULT_SLEEP_END_TIME = "06:30:00"

# Defaults
DEFAULT_NAME = "Living Room"
DEFAULT_CALC_MODE = CALC_MODE_HYBRID
DEFAULT_COLOR_MODE = COLOR_MODE_AUTO
DEFAULT_MIN_BRIGHTNESS = 1
DEFAULT_MAX_BRIGHTNESS = 100
DEFAULT_MIN_COLOR_TEMP = 2200
DEFAULT_MAX_COLOR_TEMP = 5500
DEFAULT_SLEEP_BRIGHTNESS = 1
DEFAULT_SLEEP_COLOR_TEMP = 1800
DEFAULT_SLEEP_RGB = [255, 55, 0]
DEFAULT_TRANSITION = 3
DEFAULT_INTERVAL = 60
DEFAULT_OVERRIDE_TIMEOUT = 60  # minutes

DEFAULT_CLOUD_BOOST_PCT = 25
DEFAULT_CLOUD_BOOST_KELVIN = 600
DEFAULT_PRIORITIZE_LUX = True

DEFAULT_PRESENCE_ENABLE = False
DEFAULT_AUTO_TURN_ON = True
DEFAULT_TURN_ON_LUX_THRESHOLD = 0       # 0 = always turn on, >0 = only when lux is below threshold
DEFAULT_MOTION_DEBOUNCE = 30            # 30s buffer for Aqara PIR / mmWave micro-fluctuations
DEFAULT_DIM_TIMEOUT = 180               # 3 minutes
DEFAULT_OFF_TIMEOUT = 120       # 2 minutes
DEFAULT_GRACE_PERIOD = 900      # 15 minutes
DEFAULT_DIM_BRIGHTNESS = 10     # 10%

DEFAULT_MIN_SUNRISE = "06:30:00"
DEFAULT_MAX_SUNRISE = "08:30:00"
DEFAULT_MIN_SUNSET = "17:00:00"
DEFAULT_MAX_SUNSET = "21:30:00"

# Default 24h curve: [hour, brightness, kelvin]
DEFAULT_CURVE_POINTS = [
    [0.0, 1, 1800],
    [5.0, 1, 1800],
    [6.5, 30, 2500],
    [8.0, 80, 4000],
    [12.0, 100, 5500],
    [17.0, 85, 4500],
    [20.0, 50, 3000],
    [22.0, 20, 2200],
    [23.5, 1, 1800],
]

# Frontend Paths
FRONTEND_URL = "/adaptive_circadian_frontend"
CARD_FILENAME = "adaptive-circadian-card.js"
PANEL_FILENAME = "adaptive-circadian-panel.js"
