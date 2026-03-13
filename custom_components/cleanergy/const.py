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
    4: ("total_dc_output", "W", 1.0),
    5: ("ac_output", "W", 1.0),
    6: ("car_output", "W", 1.0),
    7: ("usb_c_pd_output", "W", 1.0),
    8: ("usb_a_output", "W", 1.0),
    9: ("output_12v", "W", 1.0),
    21: ("total_input", "W", 1.0),
    22: ("ac_grid_input", "W", 1.0),
    23: ("solar_pv_input", "W", 1.0),
    30: ("remaining_time", "min", 1.0),
    31: ("total_input_alt", "W", 1.0),
    32: ("temperature", "°F", 0.1),
    40: ("standby_timeout", "min", 1.0),
    41: ("led_timeout", "min", 1.0),
    42: ("temperature_42", "°F", 0.1),
    47: ("temperature_47", "°F", 0.1),
    49: ("ac_standby_time", "min", 1.0),
    51: ("battery_pack_count", "", 1.0),
    52: ("temperature_52", "°F", 0.1),
    77: ("temperature_77", "°F", 0.1),
    82: ("temperature_82", "°F", 0.1),
    103: ("oil_volume", "", 1.0),
    104: ("generator_output", "W", 1.0),
    105: ("fast_charge_state", "", 1.0),
    110: ("ac_eco_switch", "", 1.0),
    111: ("ac_eco_threshold", "%", 1.0),
    112: ("dc_eco_switch", "", 1.0),
    113: ("dc_eco_threshold", "%", 1.0),
    114: ("dc_standby_time", "min", 1.0),
    201: ("charge_mode", "", 1.0),
    202: ("dfc_start_work", "", 1.0),
    203: ("dfc_charge_voltage", "mV", 1.0),
    204: ("dfc_charge_power", "W", 1.0),
    205: ("battery_pack_soc", "%", 1.0),
    206: ("battery_pack_temp", "°F", 0.1),
    207: ("battery_rem_time", "min", 1.0),
    208: ("battery_out_power", "W", 1.0),
    209: ("battery_start_volt", "mV", 1.0),
    210: ("battery_fw_version", "", 1.0),
    211: ("current_electric", "mA", 1.0),
    212: ("error_code", "", 1.0),
    213: ("device_flag", "", 1.0),
    214: ("battery_voltage", "mV", 1.0),
    215: ("dfc_temp", "°F", 0.1),
    216: ("battery_full", "", 1.0),
    217: ("dfc_full", "", 1.0),
    218: ("dfc_charge_timeout", "min", 1.0),
    219: ("dfc_discharge_tout", "min", 1.0),
    220: ("dfc_save_timeout", "min", 1.0),
}

# Fast mode attributes (high-frequency polling)
FAST_ATTRS = [1, 3, 4, 5, 21, 22, 23, 30, 32, 105]

# Slow mode attributes — polled every SLOW_POLL_EVERY fast cycles (~100 s at default 10 s interval)
# All non-fast sensor attrs except attr 1 (switch_state, covered by switch entities)
SLOW_ATTRS = [6, 7, 8, 9, 40, 41, 49, 51, 103, 104, 110, 111, 112, 113, 114]
SLOW_POLL_EVERY = 10