"""Constants for Cleanergy S012 TCP protocol."""

from typing import Final

DOMAIN = "cleanergy"
DEFAULT_IP = "10.2.0.65"
DEFAULT_PORT = 5555

# Protocol constants
CMD_QUERY = 2
CMD_POWER = 3


# Attribute mappings from Link.java + DeviceDetailFragment.java
# Format: (label, unit, scale) - scale: raw * scale = display value
ATTRIBUTES: Final[dict] = {
    1: ("switch_state", "", 1.0),
    3: ("battery_soc", "%", 1.0),
    4: ("total_output", "W", 1.0),
    5: ("ac_output", "W", 1.0),
    6: ("car_output", "W", 1.0),
    7: ("usb_c_pd_output", "W", 1.0),
    8: ("usb_a_output", "W", 1.0),
    9: ("output_12v", "W", 1.0),
    21: ("total_input", "W", 1.0),
    22: ("ac_grid_input", "W", 1.0),
    23: ("solar_pv_input", "W", 1.0),
    30: ("remaining_time", "min", 1.0),
    32: ("temperature", "°F", 0.1),
    40: ("standby_timeout", "min", 1.0),
    41: ("led_timeout", "min", 1.0),
    49: ("ac_standby_time", "min", 1.0),
    51: ("battery_pack_count", "", 1.0),
    103: ("oil_volume", "", 1.0),
    104: ("generator_output", "W", 1.0),
    105: ("fast_charge_state", "", 1.0),
    110: ("ac_eco_switch", "", 1.0),
    111: ("ac_eco_threshold", "%", 1.0),
    112: ("dc_eco_switch", "", 1.0),
    113: ("dc_eco_threshold", "%", 1.0),
    114: ("dc_standby_time", "min", 1.0),
}

POLL_ATTRS = [1, 3, 4, 5, 21, 22, 23, 30, 32, 105]
CONFIG_ATTRS = [6, 7, 8, 9, 40, 41, 49, 51, 103, 104, 110, 111, 112, 113, 114]
