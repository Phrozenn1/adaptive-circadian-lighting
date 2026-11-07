"""Mock Home Assistant modules for standalone unit testing without HA installed."""
import sys
from unittest.mock import MagicMock

# If homeassistant is not installed in the python environment, stub it
if "homeassistant" not in sys.modules:
    ha = MagicMock()
    sys.modules["homeassistant"] = ha
    sys.modules["homeassistant.core"] = MagicMock()
    sys.modules["homeassistant.config_entries"] = MagicMock()
    sys.modules["homeassistant.components"] = MagicMock()
    sys.modules["homeassistant.components.http"] = MagicMock()
    sys.modules["homeassistant.components.light"] = MagicMock()
    sys.modules["homeassistant.components.light"].DOMAIN = "light"
    sys.modules["homeassistant.components.light"].ATTR_SUPPORTED_COLOR_MODES = "supported_color_modes"
    sys.modules["homeassistant.components.light"].ATTR_MIN_COLOR_TEMP_KELVIN = "min_color_temp_kelvin"
    sys.modules["homeassistant.components.light"].ATTR_MAX_COLOR_TEMP_KELVIN = "max_color_temp_kelvin"
    sys.modules["homeassistant.components.switch"] = MagicMock()
    sys.modules["homeassistant.components.select"] = MagicMock()
    sys.modules["homeassistant.components.sensor"] = MagicMock()
    sys.modules["homeassistant.const"] = MagicMock()
    sys.modules["homeassistant.const"].EVENT_CALL_SERVICE = "call_service"
    sys.modules["homeassistant.helpers"] = MagicMock()
    sys.modules["homeassistant.helpers.event"] = MagicMock()
    sys.modules["homeassistant.helpers.selector"] = MagicMock()
    sys.modules["homeassistant.helpers.config_validation"] = MagicMock()
    sys.modules["voluptuous"] = MagicMock()
