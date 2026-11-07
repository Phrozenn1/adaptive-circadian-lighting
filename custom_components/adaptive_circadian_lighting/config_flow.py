"""Config and Options Flow for Adaptive Circadian Lighting."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CALC_MODES,
    COLOR_MODES,
    CONF_ADAPT_ONLY_ON_BARE_TURN_ON,
    CONF_ANTI_GLARE,
    CONF_AUTO_TURN_ON,
    CONF_CALC_MODE,
    CONF_CLOUD_BOOST_KELVIN,
    CONF_CLOUD_BOOST_PCT,
    CONF_COLOR_MODE,
    CONF_DIM_BRIGHTNESS,
    CONF_DIM_TIMEOUT,
    CONF_EVENING_MAX_BRIGHTNESS,
    CONF_GRACE_PERIOD,
    CONF_INITIAL_ADAPT_BRIGHTNESS,
    CONF_INITIAL_ADAPT_COLOR,
    CONF_INTERVAL,
    CONF_LIGHTS,
    CONF_LUX_SENSOR,
    CONF_MAX_BRIGHTNESS,
    CONF_MAX_COLOR_TEMP,
    CONF_MIN_BRIGHTNESS,
    CONF_MIN_COLOR_TEMP,
    CONF_MOTION_DEBOUNCE,
    CONF_NAME,
    CONF_OFF_TIMEOUT,
    CONF_OVERRIDE_TIMEOUT,
    CONF_PRESENCE_ENABLE,
    CONF_PRESENCE_SENSORS,
    CONF_PRIORITIZE_LUX,
    CONF_SLEEP_BRIGHTNESS,
    CONF_SLEEP_COLOR_TEMP,
    CONF_SLEEP_END_TIME,
    CONF_SLEEP_ENTITY,
    CONF_SLEEP_MOTION_BEHAVIOR,
    CONF_SLEEP_SCHEDULE_ENABLE,
    CONF_SLEEP_START_TIME,
    CONF_SLEEP_WEEKEND_ENABLE,
    CONF_SLEEP_WEEKEND_END_TIME,
    CONF_SLEEP_WEEKEND_START_TIME,
    CONF_SUNRISE_OFFSET,
    CONF_SUNSET_OFFSET,
    CONF_TRANSITION,
    CONF_TURN_ON_LUX_THRESHOLD,
    CONF_WEATHER_ENTITY,
    DEFAULT_ADAPT_ONLY_ON_BARE_TURN_ON,
    DEFAULT_AUTO_TURN_ON,
    DEFAULT_CALC_MODE,
    DEFAULT_CLOUD_BOOST_KELVIN,
    DEFAULT_CLOUD_BOOST_PCT,
    DEFAULT_COLOR_MODE,
    DEFAULT_DIM_BRIGHTNESS,
    DEFAULT_DIM_TIMEOUT,
    DEFAULT_EVENING_MAX_BRIGHTNESS,
    DEFAULT_GRACE_PERIOD,
    DEFAULT_INITIAL_ADAPT_BRIGHTNESS,
    DEFAULT_INITIAL_ADAPT_COLOR,
    DEFAULT_INTERVAL,
    DEFAULT_MAX_BRIGHTNESS,
    DEFAULT_MAX_COLOR_TEMP,
    DEFAULT_MIN_BRIGHTNESS,
    DEFAULT_MIN_COLOR_TEMP,
    DEFAULT_MOTION_DEBOUNCE,
    DEFAULT_NAME,
    DEFAULT_OFF_TIMEOUT,
    DEFAULT_OVERRIDE_TIMEOUT,
    DEFAULT_PRIORITIZE_LUX,
    DEFAULT_SLEEP_BRIGHTNESS,
    DEFAULT_SLEEP_COLOR_TEMP,
    DEFAULT_SLEEP_END_TIME,
    DEFAULT_SLEEP_MOTION_BEHAVIOR,
    DEFAULT_SLEEP_SCHEDULE_ENABLE,
    DEFAULT_SLEEP_START_TIME,
    DEFAULT_SLEEP_WEEKEND_ENABLE,
    DEFAULT_SLEEP_WEEKEND_END_TIME,
    DEFAULT_SLEEP_WEEKEND_START_TIME,
    DEFAULT_SUNRISE_OFFSET,
    DEFAULT_SUNSET_OFFSET,
    DEFAULT_TRANSITION,
    DEFAULT_TURN_ON_LUX_THRESHOLD,
    DOMAIN,
    SLEEP_MOTION_BEHAVIORS,
)


class AdaptiveCircadianConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Adaptive Circadian Lighting."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict = {}

    async def async_step_user(self, user_input=None):
        """Step 1: Room name and light selection."""
        errors = {}
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_modes()

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_LIGHTS): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="light", multiple=True)
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_modes(self, user_input=None):
        """Step 2: Choose Calculation Mode and Color Mode."""
        errors = {}
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_weather()

        schema = vol.Schema(
            {
                vol.Required(CONF_CALC_MODE, default=DEFAULT_CALC_MODE): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=CALC_MODES,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        translation_key="calc_modes",
                    )
                ),
                vol.Required(CONF_COLOR_MODE, default=DEFAULT_COLOR_MODE): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=COLOR_MODES,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        translation_key="color_modes",
                    )
                ),
                vol.Required(CONF_ADAPT_ONLY_ON_BARE_TURN_ON, default=DEFAULT_ADAPT_ONLY_ON_BARE_TURN_ON): bool,
                vol.Required(CONF_SUNRISE_OFFSET, default=DEFAULT_SUNRISE_OFFSET): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=-120, max=120, step=5, unit_of_measurement="min")
                ),
                vol.Required(CONF_SUNSET_OFFSET, default=DEFAULT_SUNSET_OFFSET): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=-120, max=120, step=5, unit_of_measurement="min")
                ),
            }
        )
        return self.async_show_form(step_id="modes", data_schema=schema, errors=errors)

    async def async_step_weather(self, user_input=None):
        """Step 3: Weather, Clouds and Lux priority."""
        errors = {}
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_presence()

        schema = vol.Schema(
            {
                vol.Optional(CONF_WEATHER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="weather")
                ),
                vol.Optional(CONF_LUX_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="illuminance")
                ),
                vol.Required(CONF_PRIORITIZE_LUX, default=DEFAULT_PRIORITIZE_LUX): bool,
                vol.Required(CONF_CLOUD_BOOST_PCT, default=DEFAULT_CLOUD_BOOST_PCT): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=50, step=5, unit_of_measurement="%")
                ),
                vol.Required(CONF_CLOUD_BOOST_KELVIN, default=DEFAULT_CLOUD_BOOST_KELVIN): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=1500, step=100, unit_of_measurement="K")
                ),
            }
        )
        return self.async_show_form(step_id="weather", data_schema=schema, errors=errors)

    async def async_step_presence(self, user_input=None):
        """Step 4: Motion/Presence sensors, Aqara blind-time debounce, and memory timeouts."""
        errors = {}
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_limits()

        schema = vol.Schema(
            {
                vol.Required(CONF_PRESENCE_ENABLE, default=False): bool,
                vol.Optional(CONF_PRESENCE_SENSORS): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor", multiple=True)
                ),
                vol.Required(CONF_AUTO_TURN_ON, default=DEFAULT_AUTO_TURN_ON): bool,
                vol.Required(CONF_SLEEP_MOTION_BEHAVIOR, default=DEFAULT_SLEEP_MOTION_BEHAVIOR): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=SLEEP_MOTION_BEHAVIORS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        translation_key="sleep_motion_behaviors",
                    )
                ),
                vol.Required(CONF_MOTION_DEBOUNCE, default=DEFAULT_MOTION_DEBOUNCE): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=180, step=5, unit_of_measurement="s")
                ),
                vol.Required(CONF_TURN_ON_LUX_THRESHOLD, default=DEFAULT_TURN_ON_LUX_THRESHOLD): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=1000, step=25, unit_of_measurement="lx")
                ),
                vol.Required(CONF_DIM_TIMEOUT, default=DEFAULT_DIM_TIMEOUT): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=10, max=1800, step=10, unit_of_measurement="s")
                ),
                vol.Required(CONF_OFF_TIMEOUT, default=DEFAULT_OFF_TIMEOUT): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=10, max=1800, step=10, unit_of_measurement="s")
                ),
                vol.Required(CONF_GRACE_PERIOD, default=DEFAULT_GRACE_PERIOD): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=60, max=3600, step=60, unit_of_measurement="s")
                ),
                vol.Required(CONF_DIM_BRIGHTNESS, default=DEFAULT_DIM_BRIGHTNESS): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=30, step=1, unit_of_measurement="%")
                ),
            }
        )
        return self.async_show_form(step_id="presence", data_schema=schema, errors=errors)

    async def async_step_limits(self, user_input=None):
        """Step 5: Limits, transitions, intervals, and sleep schedules."""
        errors = {}
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title=self._data[CONF_NAME], data=self._data)

        schema = vol.Schema(
            {
                vol.Required(CONF_MIN_BRIGHTNESS, default=DEFAULT_MIN_BRIGHTNESS): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=100, step=1, unit_of_measurement="%")
                ),
                vol.Required(CONF_MAX_BRIGHTNESS, default=DEFAULT_MAX_BRIGHTNESS): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=100, step=1, unit_of_measurement="%")
                ),
                vol.Required(CONF_EVENING_MAX_BRIGHTNESS, default=DEFAULT_EVENING_MAX_BRIGHTNESS): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=100, step=5, unit_of_measurement="%")
                ),
                vol.Required(CONF_MIN_COLOR_TEMP, default=DEFAULT_MIN_COLOR_TEMP): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1000, max=4000, step=100, unit_of_measurement="K")
                ),
                vol.Required(CONF_MAX_COLOR_TEMP, default=DEFAULT_MAX_COLOR_TEMP): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=3000, max=10000, step=100, unit_of_measurement="K")
                ),
                vol.Required(CONF_INTERVAL, default=DEFAULT_INTERVAL): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=10, max=300, step=5, unit_of_measurement="s")
                ),
                vol.Required(CONF_TRANSITION, default=DEFAULT_TRANSITION): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0.5, max=60, step=0.5, unit_of_measurement="s")
                ),
                vol.Required(CONF_OVERRIDE_TIMEOUT, default=DEFAULT_OVERRIDE_TIMEOUT): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=480, step=5, unit_of_measurement="min")
                ),
                vol.Required(CONF_ANTI_GLARE, default=True): bool,
                vol.Required(CONF_SLEEP_SCHEDULE_ENABLE, default=DEFAULT_SLEEP_SCHEDULE_ENABLE): bool,
                vol.Required(CONF_SLEEP_START_TIME, default=DEFAULT_SLEEP_START_TIME): selector.TimeSelector(),
                vol.Required(CONF_SLEEP_END_TIME, default=DEFAULT_SLEEP_END_TIME): selector.TimeSelector(),
                vol.Required(CONF_SLEEP_BRIGHTNESS, default=DEFAULT_SLEEP_BRIGHTNESS): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=100, step=1, unit_of_measurement="%")
                ),
                vol.Required(CONF_SLEEP_COLOR_TEMP, default=DEFAULT_SLEEP_COLOR_TEMP): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1000, max=4000, step=100, unit_of_measurement="K")
                ),
                vol.Required(CONF_SLEEP_WEEKEND_ENABLE, default=DEFAULT_SLEEP_WEEKEND_ENABLE): bool,
                vol.Required(CONF_SLEEP_WEEKEND_START_TIME, default=DEFAULT_SLEEP_WEEKEND_START_TIME): selector.TimeSelector(),
                vol.Required(CONF_SLEEP_WEEKEND_END_TIME, default=DEFAULT_SLEEP_WEEKEND_END_TIME): selector.TimeSelector(),
                vol.Optional(CONF_SLEEP_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["input_boolean", "binary_sensor"])
                ),
            }
        )
        return self.async_show_form(step_id="limits", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return AdaptiveCircadianOptionsFlow()


class AdaptiveCircadianOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Adaptive Circadian Lighting."""

    def __init__(self, config_entry: config_entries.ConfigEntry | None = None) -> None:
        """Initialize options flow supporting both new and legacy HA core."""
        if config_entry is not None:
            self._custom_entry = config_entry

    @property
    def _entry(self) -> config_entries.ConfigEntry:
        """Get config entry supporting both new and older HA core."""
        try:
            return self.config_entry
        except (AttributeError, KeyError):
            return getattr(self, "_custom_entry", None)

    async def async_step_init(self, user_input=None):
        """Manage the options menu."""
        entry = self._entry
        if user_input is not None:
            # Update config entry data directly so coordinator gets new settings
            new_data = {**entry.data, **user_input}
            self.hass.config_entries.async_update_entry(entry, data=new_data)
            return self.async_create_entry(title="", data=user_input)

        current = {**entry.data, **entry.options}
        schema_dict = {
            vol.Required(CONF_LIGHTS, default=current.get(CONF_LIGHTS, [])): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="light", multiple=True)
            ),
            vol.Required(CONF_CALC_MODE, default=current.get(CONF_CALC_MODE, DEFAULT_CALC_MODE)): selector.SelectSelector(
                selector.SelectSelectorConfig(options=CALC_MODES, mode=selector.SelectSelectorMode.DROPDOWN)
            ),
            vol.Required(CONF_COLOR_MODE, default=current.get(CONF_COLOR_MODE, DEFAULT_COLOR_MODE)): selector.SelectSelector(
                selector.SelectSelectorConfig(options=COLOR_MODES, mode=selector.SelectSelectorMode.DROPDOWN)
            ),
            vol.Required(CONF_ADAPT_ONLY_ON_BARE_TURN_ON, default=current.get(CONF_ADAPT_ONLY_ON_BARE_TURN_ON, DEFAULT_ADAPT_ONLY_ON_BARE_TURN_ON)): bool,
            vol.Required(CONF_SUNRISE_OFFSET, default=current.get(CONF_SUNRISE_OFFSET, DEFAULT_SUNRISE_OFFSET)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=-120, max=120, step=5, unit_of_measurement="min")
            ),
            vol.Required(CONF_SUNSET_OFFSET, default=current.get(CONF_SUNSET_OFFSET, DEFAULT_SUNSET_OFFSET)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=-120, max=120, step=5, unit_of_measurement="min")
            ),
            vol.Optional(CONF_WEATHER_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="weather")
            ),
            vol.Optional(CONF_LUX_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="illuminance")
            ),
            vol.Required(CONF_MIN_BRIGHTNESS, default=current.get(CONF_MIN_BRIGHTNESS, DEFAULT_MIN_BRIGHTNESS)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=100, step=1, unit_of_measurement="%")
            ),
            vol.Required(CONF_MAX_BRIGHTNESS, default=current.get(CONF_MAX_BRIGHTNESS, DEFAULT_MAX_BRIGHTNESS)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=100, step=1, unit_of_measurement="%")
            ),
            vol.Required(CONF_EVENING_MAX_BRIGHTNESS, default=current.get(CONF_EVENING_MAX_BRIGHTNESS, DEFAULT_EVENING_MAX_BRIGHTNESS)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=5, unit_of_measurement="%")
            ),
            vol.Required(CONF_MIN_COLOR_TEMP, default=current.get(CONF_MIN_COLOR_TEMP, DEFAULT_MIN_COLOR_TEMP)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1000, max=4000, step=100, unit_of_measurement="K")
            ),
            vol.Required(CONF_MAX_COLOR_TEMP, default=current.get(CONF_MAX_COLOR_TEMP, DEFAULT_MAX_COLOR_TEMP)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=3000, max=10000, step=100, unit_of_measurement="K")
            ),
            vol.Required(CONF_INTERVAL, default=current.get(CONF_INTERVAL, DEFAULT_INTERVAL)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=10, max=300, step=5, unit_of_measurement="s")
            ),
            vol.Required(CONF_OVERRIDE_TIMEOUT, default=current.get(CONF_OVERRIDE_TIMEOUT, DEFAULT_OVERRIDE_TIMEOUT)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=480, step=5, unit_of_measurement="min")
            ),
            vol.Required(CONF_ANTI_GLARE, default=current.get(CONF_ANTI_GLARE, True)): bool,
            vol.Required(CONF_PRESENCE_ENABLE, default=current.get(CONF_PRESENCE_ENABLE, False)): bool,
            vol.Optional(CONF_PRESENCE_SENSORS): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor", multiple=True)
            ),
            vol.Required(CONF_AUTO_TURN_ON, default=current.get(CONF_AUTO_TURN_ON, DEFAULT_AUTO_TURN_ON)): bool,
            vol.Required(CONF_SLEEP_MOTION_BEHAVIOR, default=current.get(CONF_SLEEP_MOTION_BEHAVIOR, DEFAULT_SLEEP_MOTION_BEHAVIOR)): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=SLEEP_MOTION_BEHAVIORS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="sleep_motion_behaviors",
                )
            ),
            vol.Required(CONF_MOTION_DEBOUNCE, default=current.get(CONF_MOTION_DEBOUNCE, DEFAULT_MOTION_DEBOUNCE)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=180, step=5, unit_of_measurement="s")
            ),
            vol.Required(CONF_TURN_ON_LUX_THRESHOLD, default=current.get(CONF_TURN_ON_LUX_THRESHOLD, DEFAULT_TURN_ON_LUX_THRESHOLD)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=1000, step=25, unit_of_measurement="lx")
            ),
            vol.Required(CONF_DIM_TIMEOUT, default=current.get(CONF_DIM_TIMEOUT, DEFAULT_DIM_TIMEOUT)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=10, max=1800, step=10, unit_of_measurement="s")
            ),
            vol.Required(CONF_OFF_TIMEOUT, default=current.get(CONF_OFF_TIMEOUT, DEFAULT_OFF_TIMEOUT)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=10, max=1800, step=10, unit_of_measurement="s")
            ),
            vol.Required(CONF_GRACE_PERIOD, default=current.get(CONF_GRACE_PERIOD, DEFAULT_GRACE_PERIOD)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=60, max=3600, step=60, unit_of_measurement="s")
            ),
            vol.Required(CONF_DIM_BRIGHTNESS, default=current.get(CONF_DIM_BRIGHTNESS, DEFAULT_DIM_BRIGHTNESS)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=30, step=1, unit_of_measurement="%")
            ),
            vol.Required(CONF_SLEEP_SCHEDULE_ENABLE, default=current.get(CONF_SLEEP_SCHEDULE_ENABLE, DEFAULT_SLEEP_SCHEDULE_ENABLE)): bool,
            vol.Required(CONF_SLEEP_START_TIME, default=current.get(CONF_SLEEP_START_TIME, DEFAULT_SLEEP_START_TIME)): selector.TimeSelector(),
            vol.Required(CONF_SLEEP_END_TIME, default=current.get(CONF_SLEEP_END_TIME, DEFAULT_SLEEP_END_TIME)): selector.TimeSelector(),
            vol.Required(CONF_SLEEP_BRIGHTNESS, default=current.get(CONF_SLEEP_BRIGHTNESS, DEFAULT_SLEEP_BRIGHTNESS)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=100, step=1, unit_of_measurement="%")
            ),
            vol.Required(CONF_SLEEP_COLOR_TEMP, default=current.get(CONF_SLEEP_COLOR_TEMP, DEFAULT_SLEEP_COLOR_TEMP)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1000, max=4000, step=100, unit_of_measurement="K")
            ),
            vol.Required(CONF_SLEEP_WEEKEND_ENABLE, default=current.get(CONF_SLEEP_WEEKEND_ENABLE, DEFAULT_SLEEP_WEEKEND_ENABLE)): bool,
            vol.Required(CONF_SLEEP_WEEKEND_START_TIME, default=current.get(CONF_SLEEP_WEEKEND_START_TIME, DEFAULT_SLEEP_WEEKEND_START_TIME)): selector.TimeSelector(),
            vol.Required(CONF_SLEEP_WEEKEND_END_TIME, default=current.get(CONF_SLEEP_WEEKEND_END_TIME, DEFAULT_SLEEP_WEEKEND_END_TIME)): selector.TimeSelector(),
            vol.Optional(CONF_SLEEP_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["input_boolean", "binary_sensor"])
            ),
        }

        base_schema = vol.Schema(schema_dict)
        try:
            schema = self.add_suggested_values_to_schema(base_schema, current)
        except Exception:
            schema = base_schema

        return self.async_show_form(step_id="init", data_schema=schema)
