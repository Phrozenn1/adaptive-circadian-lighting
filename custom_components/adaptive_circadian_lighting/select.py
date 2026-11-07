"""Select entities for Adaptive Circadian Lighting."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CALC_MODES, COLOR_MODES, DOMAIN, PROFILES
from .coordinator import AdaptiveCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select entities."""
    coordinator: AdaptiveCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        AdaptiveProfileSelect(coordinator, entry),
        AdaptiveCalcModeSelect(coordinator, entry),
        AdaptiveColorModeSelect(coordinator, entry),
    ]
    async_add_entities(entities)


class BaseAdaptiveSelect(SelectEntity):
    """Base select entity hooked into coordinator."""

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


class AdaptiveProfileSelect(BaseAdaptiveSelect):
    """Select active lighting profile."""

    _attr_translation_key = "profile"
    _attr_options = PROFILES
    _attr_icon = "mdi:palette-swatch"

    def __init__(self, coordinator: AdaptiveCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_profile"
        self._attr_name = "Profile"

    @property
    def current_option(self) -> str:
        return self.coordinator.profile_mgr.active_profile

    async def async_select_option(self, option: str) -> None:
        self.coordinator.profile_mgr.set_profile(option)
        self.async_write_ha_state()
        await self.coordinator._async_periodic_update()


class AdaptiveCalcModeSelect(BaseAdaptiveSelect):
    """Select calculation model."""

    _attr_translation_key = "calc_mode"
    _attr_options = CALC_MODES
    _attr_icon = "mdi:calculator"

    def __init__(self, coordinator: AdaptiveCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_calc_mode"
        self._attr_name = "Calculation Mode"

    @property
    def current_option(self) -> str:
        return self.coordinator.calc_mode

    async def async_select_option(self, option: str) -> None:
        self.coordinator.calc_mode = option
        self.async_write_ha_state()
        await self.coordinator._async_periodic_update()


class AdaptiveColorModeSelect(BaseAdaptiveSelect):
    """Select color mode (Kelvin, RGB, Auto)."""

    _attr_translation_key = "color_mode"
    _attr_options = COLOR_MODES
    _attr_icon = "mdi:tune"

    def __init__(self, coordinator: AdaptiveCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_color_mode"
        self._attr_name = "Color Mode"

    @property
    def current_option(self) -> str:
        return self.coordinator.color_mode

    async def async_select_option(self, option: str) -> None:
        self.coordinator.color_mode = option
        self.async_write_ha_state()
        await self.coordinator._async_periodic_update()
