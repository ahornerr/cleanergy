"""Home Assistant sensors for Cleanergy S012."""
from __future__ import annotations

import logging
from typing import Final

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTES, DOMAIN
from .coordinator import CleanergyCoordinator

_LOGGER = logging.getLogger(__name__)

# Map unit strings from const.py → HA unit constants
_UNIT_MAP: Final = {
    "W":   UnitOfPower.WATT,
    "mV":  UnitOfElectricPotential.MILLIVOLT,
    "mA":  UnitOfElectricCurrent.MILLIAMPERE,
    "%":   PERCENTAGE,
    "min": UnitOfTime.MINUTES,
    "°F":  UnitOfTemperature.FAHRENHEIT,
    "°C":  UnitOfTemperature.CELSIUS,
}

# Map attr names → SensorDeviceClass
_DEVICE_CLASS_MAP: Final = {
    "battery_soc":       SensorDeviceClass.BATTERY,
    "battery_pack_soc":  SensorDeviceClass.BATTERY,
    "total_dc_output":   SensorDeviceClass.POWER,
    "ac_output":         SensorDeviceClass.POWER,
    "car_output":        SensorDeviceClass.POWER,
    "usb_c_pd_output":   SensorDeviceClass.POWER,
    "usb_a_output":      SensorDeviceClass.POWER,
    "output_12v":        SensorDeviceClass.POWER,
    "total_input":       SensorDeviceClass.POWER,
    "total_input_alt":   SensorDeviceClass.POWER,
    "ac_grid_input":     SensorDeviceClass.POWER,
    "solar_pv_input":    SensorDeviceClass.POWER,
    "generator_output":  SensorDeviceClass.POWER,
    "dfc_charge_power":  SensorDeviceClass.POWER,
    "battery_out_power":  SensorDeviceClass.POWER,
    "temperature":       SensorDeviceClass.TEMPERATURE,
    "temperature_42":    SensorDeviceClass.TEMPERATURE,
    "temperature_47":    SensorDeviceClass.TEMPERATURE,
    "temperature_52":    SensorDeviceClass.TEMPERATURE,
    "temperature_77":    SensorDeviceClass.TEMPERATURE,
    "temperature_82":    SensorDeviceClass.TEMPERATURE,
    "battery_pack_temp": SensorDeviceClass.TEMPERATURE,
    "dfc_temp":          SensorDeviceClass.TEMPERATURE,
    "remaining_time":    SensorDeviceClass.DURATION,
    "standby_timeout":   SensorDeviceClass.DURATION,
    "led_timeout":       SensorDeviceClass.DURATION,
    "ac_standby_time":   SensorDeviceClass.DURATION,
    "dc_standby_time":   SensorDeviceClass.DURATION,
    "battery_rem_time":  SensorDeviceClass.DURATION,
    "battery_voltage":   SensorDeviceClass.VOLTAGE,
    "battery_start_volt": SensorDeviceClass.VOLTAGE,
    "dfc_charge_voltage": SensorDeviceClass.VOLTAGE,
    "current_electric":  SensorDeviceClass.CURRENT,
}

# Attrs to expose as HA sensors (skip low-value zeros and temp duplicates)
SENSOR_ATTR_IDS: Final = [
    1,   # switch_state
    3,   # battery_soc
    4,   # total_dc_output
    5,   # ac_output
    6,   # car_output
    7,   # usb_c_pd_output
    8,   # usb_a_output
    9,   # output_12v
    21,  # total_input
    22,  # ac_grid_input
    23,  # solar_pv_input
    30,  # remaining_time
    32,  # temperature
    40,  # standby_timeout
    41,  # led_timeout
    49,  # ac_standby_time
    51,  # battery_pack_count
    103, # oil_volume
    104, # generator_output
    105, # fast_charge_state
    110, # ac_eco_switch
    111, # ac_eco_threshold
    112, # dc_eco_switch
    113, # dc_eco_threshold
    114, # dc_standby_time
]


class CleanergySensor(CoordinatorEntity[CleanergyCoordinator], SensorEntity):
    """A sensor entity that reflects one Cleanergy S012 attribute."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CleanergyCoordinator, attr_id: int) -> None:
        super().__init__(coordinator)
        label, unit_str, scale = ATTRIBUTES[attr_id]
        self._attr_id = attr_id
        self._scale = scale
        self._attr_unique_id = f"cleanergy_{coordinator.host}_{attr_id}"
        self._attr_name = label.replace("_", " ").title()
        self._attr_native_unit_of_measurement = _UNIT_MAP.get(unit_str)
        self._attr_device_class = _DEVICE_CLASS_MAP.get(label)
        self._attr_state_class = SensorStateClass.MEASUREMENT if unit_str else None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.host)},
            name="Cleanergy S012",
            model="S012",
            manufacturer="Cleanergy",
        )

    @property
    def native_value(self) -> int | float | None:
        data = self.coordinator.data
        if not data:
            return None
        raw = data.get(str(self._attr_id))
        if raw is None:
            return None
        try:
            val = float(raw) * self._scale
            return int(val) if val == int(val) else round(val, 1)
        except (ValueError, TypeError):
            return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: CleanergyCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        CleanergySensor(coordinator, attr_id) for attr_id in SENSOR_ATTR_IDS
    )
