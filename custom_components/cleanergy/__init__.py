"""Home Assistant custom integration for Cleanergy S012 devices."""

from __future__ import annotations

import logging
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DEFAULT_PORT, DOMAIN
from .coordinator import CleanergyCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: Final = [Platform.SENSOR, Platform.SWITCH]

_SERVICES = ("turn_on", "turn_off", "set_power_ac", "set_power_dc")


def _get_coordinators(hass: HomeAssistant) -> list[CleanergyCoordinator]:
    return [
        v
        for v in hass.data.get(DOMAIN, {}).values()
        if isinstance(v, CleanergyCoordinator)
    ]


def _register_services(hass: HomeAssistant) -> None:
    async def handle_turn_on(call: ServiceCall) -> None:
        for coord in _get_coordinators(hass):
            await coord.async_set_all_outputs(True)
            await coord.async_request_refresh()

    async def handle_turn_off(call: ServiceCall) -> None:
        for coord in _get_coordinators(hass):
            await coord.async_set_all_outputs(False)
            await coord.async_request_refresh()

    async def handle_set_power_ac(call: ServiceCall) -> None:
        for coord in _get_coordinators(hass):
            await coord.async_set_switch_bit(0, bool(call.data.get("state", True)))
            await coord.async_request_refresh()

    async def handle_set_power_dc(call: ServiceCall) -> None:
        for coord in _get_coordinators(hass):
            await coord.async_set_switch_bit(1, bool(call.data.get("state", True)))
            await coord.async_request_refresh()

    hass.services.async_register(DOMAIN, "turn_on", handle_turn_on)
    hass.services.async_register(DOMAIN, "turn_off", handle_turn_off)
    hass.services.async_register(DOMAIN, "set_power_ac", handle_set_power_ac)
    hass.services.async_register(DOMAIN, "set_power_dc", handle_set_power_dc)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Create coordinator, first refresh, then set up platforms."""
    host = entry.data["host"]
    port = entry.data.get("port", DEFAULT_PORT)
    scan_interval = entry.data.get("scan_interval", 10)

    coordinator = CleanergyCoordinator(hass, host, port, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    if not hass.services.has_service(DOMAIN, "turn_on"):
        _register_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload platforms and remove coordinator."""
    coordinator: CleanergyCoordinator = hass.data[DOMAIN].get(entry.entry_id)
    if coordinator:
        await coordinator.async_shutdown()

    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        if not _get_coordinators(hass):
            for service in _SERVICES:
                hass.services.async_remove(DOMAIN, service)
    return unloaded
