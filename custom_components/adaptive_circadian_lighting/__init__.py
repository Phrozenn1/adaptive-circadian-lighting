"""Adaptive Circadian Lighting custom component."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import (
    CARD_FILENAME,
    DOMAIN,
    FRONTEND_URL,
    PANEL_FILENAME,
    PROFILE_NORMAL,
    PROFILE_SLEEP,
    PROFILES,
)
from .coordinator import AdaptiveCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["switch", "select", "sensor"]

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Adaptive Circadian Lighting integration."""
    hass.data.setdefault(DOMAIN, {})

    # 1. Expose the frontend folder over HTTP
    frontend_dir = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                url_path=FRONTEND_URL,
                path=str(frontend_dir),
                cache_headers=False,
            )
        ]
    )

    # 2. Automatically register the Lovelace resource
    await _async_register_lovelace_card(hass)

    # 3. Register the Custom Sidebar Panel
    _async_register_panel(hass)

    # 4. Register global services
    _register_services(hass)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up an instance from a config entry."""
    coordinator = AdaptiveCoordinator(hass, entry)
    await coordinator.async_setup()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: AdaptiveCoordinator = hass.data[DOMAIN].get(entry.entry_id)
    if coordinator:
        await coordinator.async_unload()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def _async_register_lovelace_card(hass: HomeAssistant) -> None:
    """Automatically register the Lovelace card resource in Home Assistant."""
    if "lovelace" not in hass.data:
        return

    try:
        resources = hass.data["lovelace"].resources
        if not resources.loaded:
            await resources.async_load()

        card_url = f"{FRONTEND_URL}/{CARD_FILENAME}"
        exists = any(r.get("url") == card_url for r in resources.async_items())
        if not exists:
            await resources.async_create_item({
                "res_type": "module",
                "url": card_url,
            })
            _LOGGER.info("Registered Lovelace card resource: %s", card_url)
    except Exception as err:
        _LOGGER.warning("Could not automatically register Lovelace resource: %s", err)


def _async_register_panel(hass: HomeAssistant) -> None:
    """Register custom sidebar panel in Home Assistant."""
    try:
        if hasattr(hass.components.frontend, "async_register_built_in_panel"):
            hass.components.frontend.async_register_built_in_panel(
                component_name="custom",
                sidebar_title="Adaptive Light",
                sidebar_icon="mdi:sun-clock",
                frontend_url_path="adaptive-circadian",
                config={
                    "_panel_custom": {
                        "name": "adaptive-circadian-panel",
                        "module_url": f"{FRONTEND_URL}/{PANEL_FILENAME}",
                    }
                },
                require_admin=False,
            )
            _LOGGER.info("Registered Adaptive Circadian sidebar panel.")
    except Exception as err:
        _LOGGER.debug("Note: Could not register sidebar panel (optional): %s", err)


def _register_services(hass: HomeAssistant) -> None:
    """Register component services."""
    async def handle_apply_now(call: ServiceCall) -> None:
        entity_id = call.data.get("entity_id")
        for coord in hass.data[DOMAIN].values():
            if not isinstance(coord, AdaptiveCoordinator):
                continue
            if entity_id:
                if entity_id in coord.lights:
                    await coord._async_apply_to_light(entity_id)
            else:
                await coord._async_periodic_update()

    async def handle_reset_override(call: ServiceCall) -> None:
        entity_id = call.data.get("entity_id")
        for coord in hass.data[DOMAIN].values():
            if not isinstance(coord, AdaptiveCoordinator):
                continue
            coord.override_mgr.reset_override(entity_id)

    async def handle_set_profile(call: ServiceCall) -> None:
        profile = call.data.get("profile", PROFILE_NORMAL)
        if profile in PROFILES:
            for coord in hass.data[DOMAIN].values():
                if isinstance(coord, AdaptiveCoordinator):
                    coord.profile_mgr.set_profile(profile)
                    await coord._async_periodic_update()

    async def handle_toggle_sleep(call: ServiceCall) -> None:
        for coord in hass.data[DOMAIN].values():
            if isinstance(coord, AdaptiveCoordinator):
                new_p = PROFILE_NORMAL if coord.profile_mgr.is_sleep() else PROFILE_SLEEP
                coord.profile_mgr.set_profile(new_p)
                await coord._async_periodic_update()

    hass.services.async_register(DOMAIN, "apply_now", handle_apply_now)
    hass.services.async_register(DOMAIN, "reset_manual_override", handle_reset_override)
    hass.services.async_register(DOMAIN, "set_profile", handle_set_profile)
    hass.services.async_register(DOMAIN, "toggle_sleep_mode", handle_toggle_sleep)
