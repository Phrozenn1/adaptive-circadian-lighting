"""Mock Home Assistant modules for standalone unit testing without HA installed."""
import sys
from unittest.mock import MagicMock

# If homeassistant is not installed in the python environment, stub it
if "homeassistant" not in sys.modules:
    ha = MagicMock()
    sys.modules["homeassistant"] = ha
    core_mock = MagicMock()
    core_mock.callback = lambda f: f
    sys.modules["homeassistant.core"] = core_mock
    ha.core = core_mock

    class DummyOptionsFlow:
        def __init__(self, *args, **kwargs):
            pass

    class DummyConfigFlow:
        def __init_subclass__(cls, domain=None, **kwargs):
            super().__init_subclass__(**kwargs)

    ce_mock = MagicMock()
    ce_mock.OptionsFlow = DummyOptionsFlow
    ce_mock.ConfigFlow = DummyConfigFlow
    sys.modules["homeassistant.config_entries"] = ce_mock
    ha.config_entries = ce_mock
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
    bs_mock = MagicMock()
    class DummyBinarySensorEntity:
        _attr_has_entity_name = True
        _attr_device_class = None
        _attr_translation_key = None
        _attr_unique_id = None
        _attr_name = None
        _attr_device_info = None

        @property
        def unique_id(self):
            return self._attr_unique_id

        def async_on_remove(self, func):
            pass

        async def async_write_ha_state(self):
            pass

    class DummyBinarySensorDeviceClass:
        OCCUPANCY = "occupancy"
        MOTION = "motion"
        PRESENCE = "presence"

    bs_mock.BinarySensorEntity = DummyBinarySensorEntity
    bs_mock.BinarySensorDeviceClass = DummyBinarySensorDeviceClass
    sys.modules["homeassistant.components.binary_sensor"] = bs_mock
    ha.components.binary_sensor = bs_mock
    sys.modules["homeassistant.const"] = MagicMock()
    sys.modules["homeassistant.const"].EVENT_CALL_SERVICE = "call_service"
    helpers_mock = MagicMock()
    helpers_mock.__path__ = []
    sys.modules["homeassistant.helpers"] = helpers_mock
    sys.modules["homeassistant.helpers.event"] = MagicMock()
    sys.modules["homeassistant.helpers.selector"] = MagicMock()
    sys.modules["homeassistant.helpers.config_validation"] = MagicMock()
    sys.modules["homeassistant.helpers.entity_platform"] = MagicMock()
    sys.modules["voluptuous"] = MagicMock()
