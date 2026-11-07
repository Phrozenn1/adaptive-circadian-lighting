"""Tests for options flow robust entry resolution and initialization."""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
import tests  # noqa: F401

from custom_components.adaptive_circadian_lighting.config_flow import (
    AdaptiveCircadianConfigFlow,
    AdaptiveCircadianOptionsFlow,
)
from custom_components.adaptive_circadian_lighting.const import (
    CONF_LIGHTS,
    CONF_CALC_MODE,
    CONF_COLOR_MODE,
    CONF_MIN_BRIGHTNESS,
    CONF_MAX_BRIGHTNESS,
    CONF_SLEEP_RGB,
    DOMAIN,
)


class DummyConfigEntry:
    def __init__(self, entry_id="test_entry_id", data=None, options=None):
        self.entry_id = entry_id
        self.data = data or {
            CONF_LIGHTS: ["light.ceiling"],
            CONF_CALC_MODE: "hybrid",
            CONF_COLOR_MODE: "auto",
            CONF_MIN_BRIGHTNESS: 5,
            CONF_MAX_BRIGHTNESS: 95,
            CONF_SLEEP_RGB: [255, 60, 0],
        }
        self.options = options or {}


class TestOptionsFlow(unittest.IsolatedAsyncioTestCase):
    async def test_options_flow_creation_and_entry_resolution(self):
        entry = DummyConfigEntry()
        flow = AdaptiveCircadianConfigFlow.async_get_options_flow(entry)
        self.assertIsInstance(flow, AdaptiveCircadianOptionsFlow)
        self.assertEqual(flow._entry, entry)

    async def test_options_flow_fallback_to_handler(self):
        entry = DummyConfigEntry(entry_id="abc123")
        flow = AdaptiveCircadianOptionsFlow()
        flow.handler = "abc123"
        flow.hass = MagicMock()
        flow.hass.config_entries.async_get_entry.return_value = entry

        self.assertEqual(flow._entry, entry)

    async def test_options_flow_step_init_form_generation(self):
        entry = DummyConfigEntry()
        flow = AdaptiveCircadianConfigFlow.async_get_options_flow(entry)
        flow.hass = MagicMock()
        flow.async_show_form = MagicMock(return_value={"type": "form", "step_id": "init"})

        result = await flow.async_step_init(user_input=None)
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "init")
        flow.async_show_form.assert_called_once()
        kwargs = flow.async_show_form.call_args.kwargs
        self.assertEqual(kwargs["step_id"], "init")
        self.assertIsNotNone(kwargs["data_schema"])

    async def test_options_flow_with_empty_or_none_fields(self):
        # Config entry created before sleep_rgb or with None optional fields
        sparse_data = {
            CONF_LIGHTS: None,
            "weather_entity": None,
            "lux_sensor": None,
        }
        entry = DummyConfigEntry(data=sparse_data)
        flow = AdaptiveCircadianConfigFlow.async_get_options_flow(entry)
        flow.hass = MagicMock()
        flow.async_show_form = MagicMock(return_value={"type": "form", "step_id": "init"})

        result = await flow.async_step_init(user_input=None)
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "init")
        flow.async_show_form.assert_called_once()

    async def test_options_flow_step_init_submission(self):
        entry = DummyConfigEntry()
        flow = AdaptiveCircadianConfigFlow.async_get_options_flow(entry)
        flow.hass = MagicMock()
        flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})

        user_input = {
            CONF_MIN_BRIGHTNESS: 15,
            CONF_MAX_BRIGHTNESS: 85,
            CONF_SLEEP_RGB: [255, 40, 0],
        }
        result = await flow.async_step_init(user_input=user_input)
        self.assertEqual(result["type"], "create_entry")
        flow.hass.config_entries.async_update_entry.assert_called_once()


if __name__ == "__main__":
    unittest.main()
