"""Binary sensor platform for Adaptive Circadian Lighting."""
from __future__ import annotations

from typing import Any, Mapping

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AdaptiveCoordinator
from .presence_manager import STATE_OCCUPIED


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities."""
    coordinator: AdaptiveCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[BinarySensorEntity] = []
    if coordinator.presence_mgr:
        entities.append(AdaptiveOccupancyBinarySensor(coordinator, entry))

    async_add_entities(entities)


class AdaptiveOccupancyBinarySensor(BinarySensorEntity):
    """Room occupancy binary sensor reflecting real-time presence."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY
    _attr_translation_key = "occupancy"

    def __init__(self, coordinator: AdaptiveCoordinator, entry: ConfigEntry) -> None:
        self.coordinator = coordinator
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_occupancy"
        self._attr_name = "Occupancy"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": coordinator.name,
            "manufacturer": "Adaptive Circadian",
            "model": "Circadian Controller",
        }

    async def async_added_to_hass(self) -> None:
        """Register listener on coordinator updates."""
        self.async_on_remove(self.coordinator.register_listener(self.async_write_ha_state))

    @property
    def is_on(self) -> bool:
        """Return true if the room is occupied."""
        if self.coordinator.presence_mgr:
            return (
                self.coordinator.presence_mgr.room_state == STATE_OCCUPIED
                or self.coordinator.presence_mgr.is_occupied()
            )
        return False

    @property
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.presence_mgr:
            return {}
        pm = self.coordinator.presence_mgr
        return {
            "room_state": pm.room_state,
            "sensors": pm.sensors,
            "last_motion": pm.last_motion_time.isoformat() if pm.last_motion_time else None,
            "last_turned_off": pm.last_turned_off_time.isoformat() if pm.last_turned_off_time else None,
        }
