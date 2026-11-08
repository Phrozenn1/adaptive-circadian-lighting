"""Tests for AntiGlareInterceptor and dimmer switch interaction."""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))
import tests  # noqa: F401

from custom_components.adaptive_circadian_lighting.anti_glare import AntiGlareInterceptor


class MockServiceEvent:
    def __init__(self, domain: str, service: str, service_data: dict, target: dict = None):
        self.data = {
            "domain": domain,
            "service": service,
            "service_data": service_data,
            "target": target or {},
        }


class TestAntiGlare(unittest.TestCase):
    def setUp(self):
        self.hass = MagicMock()
        self.hass.bus = MagicMock()
        self.hass.states = MagicMock()

    def test_anti_glare_ignores_already_on_lights(self):
        # When kitchen light is ON and user turns the dimmer knob
        st = MagicMock()
        st.state = "on"
        self.hass.states.get.return_value = st

        target_payload = {"brightness_pct": 100, "color_temp_kelvin": 4000}
        cb = MagicMock(return_value=target_payload)

        ag = AntiGlareInterceptor(
            self.hass,
            target_lights=["light.kitchen"],
            get_target_payload_callback=cb,
            enabled=True,
        )

        service_data = {"entity_id": "light.kitchen", "brightness": 120}
        event = MockServiceEvent("light", "turn_on", service_data)
        ag._handle_service_call(event)

        # Anti-glare must NOT modify service data or call callback for already ON lights
        cb.assert_not_called()
        self.assertEqual(service_data, {"entity_id": "light.kitchen", "brightness": 120})

    def test_anti_glare_respects_brightness_step_dimmer_commands(self):
        # Dimmer switches often send brightness_step or brightness_step_pct
        st = MagicMock()
        st.state = "off"
        self.hass.states.get.return_value = st

        target_payload = {"brightness_pct": 100, "color_temp_kelvin": 3000}
        cb = MagicMock(return_value=target_payload)

        ag = AntiGlareInterceptor(
            self.hass,
            target_lights=["light.kitchen"],
            get_target_payload_callback=cb,
            enabled=True,
        )

        service_data = {"entity_id": "light.kitchen", "brightness_step": -25}
        event = MockServiceEvent("light", "turn_on", service_data)
        ag._handle_service_call(event)

        # Anti-glare must NOT inject brightness_pct when brightness_step is present!
        self.assertNotIn("brightness_pct", service_data)
        self.assertEqual(service_data["brightness_step"], -25)
        # But can inject missing color_temp_kelvin
        self.assertEqual(service_data["color_temp_kelvin"], 3000)

    def test_anti_glare_injects_both_when_turned_on_bare_from_off(self):
        st = MagicMock()
        st.state = "off"
        self.hass.states.get.return_value = st

        target_payload = {"brightness_pct": 10, "color_temp_kelvin": 2200}
        cb = MagicMock(return_value=target_payload)

        ag = AntiGlareInterceptor(
            self.hass,
            target_lights=["light.kitchen"],
            get_target_payload_callback=cb,
            enabled=True,
        )

        service_data = {"entity_id": "light.kitchen"}
        event = MockServiceEvent("light", "turn_on", service_data)
        ag._handle_service_call(event)

        self.assertEqual(service_data["brightness_pct"], 10)
        self.assertEqual(service_data["color_temp_kelvin"], 2200)


if __name__ == "__main__":
    unittest.main()
