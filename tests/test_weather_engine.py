"""Tests for weather and lux compensation engine."""
import sys
import unittest
from unittest.mock import MagicMock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import tests  # noqa: F401

from custom_components.adaptive_circadian_lighting.weather_engine import WeatherEngine


class MockState:
    def __init__(self, state: str, attributes: dict = None):
        self.state = state
        self.attributes = attributes or {}


class TestWeatherEngine(unittest.TestCase):
    def setUp(self):
        self.hass = MagicMock()

    def test_night_time_no_boost(self):
        engine = WeatherEngine(
            self.hass,
            weather_entity="weather.home",
            cloud_boost_pct=25,
            cloud_boost_kelvin=600,
        )
        b, k, reason = engine.calculate_boost(is_daytime=False)
        self.assertEqual(b, 0)
        self.assertEqual(k, 0)
        self.assertEqual(reason, "night_no_boost")

    def test_weather_cloud_coverage_boost(self):
        # 100% cloud coverage -> full cloud boost
        self.hass.states.get.return_value = MockState(
            "cloudy", attributes={"cloud_coverage": 100}
        )

        engine = WeatherEngine(
            self.hass,
            weather_entity="weather.home",
            cloud_boost_pct=25,
            cloud_boost_kelvin=600,
        )
        b, k, reason = engine.calculate_boost(is_daytime=True)
        self.assertEqual(b, 25)
        self.assertEqual(k, 600)
        self.assertIn("weather_cloudy", reason)

    def test_lux_sensor_priority_over_weather(self):
        # Weather reports sunny (low boost), but lux sensor reports low 1500 lux (stormy/dark)
        def mock_get(entity_id):
            if entity_id == "weather.home":
                return MockState("sunny", {"cloud_coverage": 0})
            if entity_id == "sensor.outdoor_lux":
                return MockState("1500")
            return None

        self.hass.states.get.side_effect = mock_get

        engine = WeatherEngine(
            self.hass,
            weather_entity="weather.home",
            lux_sensor="sensor.outdoor_lux",
            cloud_boost_pct=30,
            cloud_boost_kelvin=500,
            prioritize_lux=True,
        )

        b, k, reason = engine.calculate_boost(is_daytime=True)
        self.assertTrue(b > 20)
        self.assertTrue(k > 300)
        self.assertIn("lux_sensor_1500lx", reason)


if __name__ == "__main__":
    unittest.main()
