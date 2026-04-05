"""Switch entities for Cleanergy S012 power control.

switch_state bit encoding (attr 1):
  bit 0 = AC output   (value 1)
  bit 1 = DC output   (value 2)

Confirmed values:
  0 = all off
  1 = AC only
  2 = DC only
  3 = both on
"""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import CleanergyCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# bit 0 = AC, bit 1 = DC
_AC_BIT = 0
_DC_BIT = 1


class CleanergyOutputSwitch(CoordinatorEntity[CleanergyCoordinator], SwitchEntity):
    """Controls one output (AC or DC) while preserving the other."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CleanergyCoordinator,
        bit: int,
        name: str,
    ) -> None:
        super().__init__(coordinator)
        self._bit = bit
        self._attr_name = name
        self._attr_unique_id = f"cleanergy_{coordinator.host}_{name.lower()}_switch"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.host)},
            name="Cleanergy S012",
            model="S012",
            manufacturer="Cleanergy",
        )

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if not data:
            return None
        raw = data.get(1)
        if raw is None:
            return None
        try:
            return bool(int(raw) & (1 << self._bit))
        except (ValueError, TypeError):
            return None

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_switch_bit(self._bit, True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_switch_bit(self._bit, False)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: CleanergyCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            CleanergyOutputSwitch(coordinator, _AC_BIT, "AC Output"),
            CleanergyOutputSwitch(coordinator, _DC_BIT, "DC Output"),
        ]
    )
