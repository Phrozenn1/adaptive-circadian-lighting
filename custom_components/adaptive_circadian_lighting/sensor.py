"""Sensor entities for Adaptive Circadian Lighting."""
from __future__ import annotations

from typing import Any, Mapping

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AdaptiveCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor entities."""
    coordinator: AdaptiveCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        AdaptiveBrightnessSensor(coordinator, entry),
        AdaptiveKelvinSensor(coordinator, entry),
        AdaptivePhaseSensor(coordinator, entry),
        AdaptiveWeatherBoostSensor(coordinator, entry),
        AdaptiveOverridesSensor(coordinator, entry),
    ]

    if coordinator.presence_mgr:
        entities.append(AdaptivePresenceStateSensor(coordinator, entry))

    async_add_entities(entities)


class BaseAdaptiveSensor(SensorEntity):
    """Base sensor hooked into coordinator."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AdaptiveCoordinator, entry: ConfigEntry) -> None:
        self.coordinator = coordinator
        self.entry = entry
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": coordinator.name,
            "manufacturer": "Adaptive Circadian",
            "model": "Circadian Controller",
        }

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.coordinator.register_listener(self.async_write_ha_state))


class AdaptiveBrightnessSensor(BaseAdaptiveSensor):
    """Current target brightness."""

    _attr_translation_key = "target_brightness"
    _attr_native_unit_of_measurement = "%"
    _attr_icon = "mdi:brightness-percent"

    def __init__(self, coordinator: AdaptiveCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_target_brightness"
        self._attr_name = "Target Brightness"

    @property
    def native_value(self) -> int:
        return self.coordinator.target_brightness


class AdaptiveKelvinSensor(BaseAdaptiveSensor):
    """Current target color temperature in Kelvin."""

    _attr_translation_key = "target_color_temp"
    _attr_native_unit_of_measurement = "K"
    _attr_icon = "mdi:sun-thermometer"

    def __init__(self, coordinator: AdaptiveCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_target_color_temp"
        self._attr_name = "Target Color Temp"

    @property
    def native_value(self) -> int:
        return self.coordinator.target_kelvin


class AdaptivePhaseSensor(BaseAdaptiveSensor):
    """Current daylight/circadian phase."""

    _attr_translation_key = "phase"
    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator: AdaptiveCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_phase"
        self._attr_name = "Phase"

    @property
    def native_value(self) -> str:
        return self.coordinator.phase


class AdaptiveWeatherBoostSensor(BaseAdaptiveSensor):
    """Current weather or lux boost information."""

    _attr_translation_key = "weather_boost"
    _attr_icon = "mdi:weather-partly-cloudy"

    def __init__(self, coordinator: AdaptiveCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_weather_boost"
        self._attr_name = "Weather Boost"

    @property
    def native_value(self) -> str:
        return self.coordinator.weather_boost_desc


class AdaptiveOverridesSensor(BaseAdaptiveSensor):
    """Count and list of lights currently under manual override."""

    _attr_translation_key = "manual_overrides"
    _attr_icon = "mdi:hand-back-right-off"

    def __init__(self, coordinator: AdaptiveCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_manual_overrides"
        self._attr_name = "Manual Overrides"

    @property
    def native_value(self) -> int:
        return len(self.coordinator.override_mgr.overridden_lights)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any]:
        return {
            "overridden_entities": list(self.coordinator.override_mgr.overridden_lights.keys())
        }


class AdaptivePresenceStateSensor(BaseAdaptiveSensor):
    """Room presence state (occupied, dimmed, off)."""

    _attr_translation_key = "presence_state"
    _attr_icon = "mdi:motion-sensor"

    def __init__(self, coordinator: AdaptiveCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_presence_state"
        self._attr_name = "Presence State"

    @property
    def native_value(self) -> str:
        if self.coordinator.presence_mgr:
            return self.coordinator.presence_mgr.room_state
        return "unknown"
