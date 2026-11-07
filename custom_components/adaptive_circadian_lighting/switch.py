"""Switch entities for Adaptive Circadian Lighting."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, PROFILE_NORMAL, PROFILE_SLEEP
from .coordinator import AdaptiveCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch entities."""
    coordinator: AdaptiveCoordinator = hass.data[DOMAIN][entry.entry_id]

    switches = [
        AdaptiveMasterSwitch(coordinator, entry),
        AdaptiveBrightnessSwitch(coordinator, entry),
        AdaptiveColorSwitch(coordinator, entry),
        AdaptiveSleepSwitch(coordinator, entry),
    ]
    async_add_entities(switches)


class BaseAdaptiveEntity(SwitchEntity):
    """Base entity hooked into coordinator."""

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


class AdaptiveMasterSwitch(BaseAdaptiveEntity):
    """Master switch to enable/disable all adaptation for this room."""

    _attr_translation_key = "adaptation"

    def __init__(self, coordinator: AdaptiveCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_adaptation"
        self._attr_name = "Adaptation"
        self._attr_icon = "mdi:theme-light-dark"

    @property
    def is_on(self) -> bool:
        return self.coordinator.adaptation_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.coordinator.adaptation_enabled = True
        self.async_write_ha_state()
        await self.coordinator._async_periodic_update()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.coordinator.adaptation_enabled = False
        self.async_write_ha_state()


class AdaptiveBrightnessSwitch(BaseAdaptiveEntity):
    """Toggle brightness adaptation."""

    _attr_translation_key = "adapt_brightness"

    def __init__(self, coordinator: AdaptiveCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_adapt_brightness"
        self._attr_name = "Adapt Brightness"
        self._attr_icon = "mdi:brightness-6"

    @property
    def is_on(self) -> bool:
        return self.coordinator.adapt_brightness_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.coordinator.adapt_brightness_enabled = True
        self.async_write_ha_state()
        await self.coordinator._async_periodic_update()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.coordinator.adapt_brightness_enabled = False
        self.async_write_ha_state()


class AdaptiveColorSwitch(BaseAdaptiveEntity):
    """Toggle color / color temperature adaptation."""

    _attr_translation_key = "adapt_color"

    def __init__(self, coordinator: AdaptiveCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_adapt_color"
        self._attr_name = "Adapt Color"
        self._attr_icon = "mdi:palette"

    @property
    def is_on(self) -> bool:
        return self.coordinator.adapt_color_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.coordinator.adapt_color_enabled = True
        self.async_write_ha_state()
        await self.coordinator._async_periodic_update()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.coordinator.adapt_color_enabled = False
        self.async_write_ha_state()


class AdaptiveSleepSwitch(BaseAdaptiveEntity):
    """Sleep mode toggle."""

    _attr_translation_key = "sleep_mode"

    def __init__(self, coordinator: AdaptiveCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_sleep_mode"
        self._attr_name = "Sleep Mode"
        self._attr_icon = "mdi:bed"

    @property
    def is_on(self) -> bool:
        return self.coordinator.profile_mgr.is_sleep()

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.coordinator.profile_mgr.set_profile(PROFILE_SLEEP)
        self.async_write_ha_state()
        await self.coordinator._async_periodic_update()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.coordinator.profile_mgr.set_profile(PROFILE_NORMAL)
        self.async_write_ha_state()
        await self.coordinator._async_periodic_update()
