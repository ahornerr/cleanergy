# Cleanergy S012 Home Assistant Custom Integration

A local_polling Home Assistant integration for Cleanergy S012 power stations.

## Features

- **22 sensor entities** tracking device attributes (power in/out, battery status, temperature, etc.)
- **1 switch entity** for power control (on/off both AC and DC outputs)
- **TCP communication** with device at configurable host/port
- **Fast polling** (10 attributes every ~3 seconds) for responsive updates
- **Connection recovery** - automatic retry on failures

## Installation

1. Copy this directory to your Home Assistant custom components:
   ```bash
   mkdir -p ~/.homeassistant/custom_components/cleanergy
   cp -r /path/to/cleanergy/* ~/.homeassistant/custom_components/cleanergy/
   ```

2. Restart Home Assistant:
   - Via UI: Settings → System → YAML Configuration → Server Controls → Restart
   - Via SSH: `ha core restart`

3. Add the integration:
   - Settings → Devices & Services → Add Integration → Cleanergy S012
   - Configure: Host (e.g., `10.2.0.65`), Port (default: 5555), Scan interval (default: 10s)

## Entities

### Sensors

| Entity | Description | Unit |
|--------|-------------|------|
| sensor.cleanergy_{host}_battery_soc | Battery state of charge | % |
| sensor.cleanergy_{host}_total_dc_output | Total DC output power | W |
| sensor.cleanergy_{host}_ac_output | AC output power | W |
| sensor.cleanergy_{host}_car_output | Car/12V output power | W |
| sensor.cleanergy_{host}_usb_c_pd_output | USB-C PD output | W |
| sensor.cleanergy_{host}_usb_a_output | USB-A output | W |
| sensor.cleanergy_{host}_output_12v | 12V DC output | W |
| sensor.cleanergy_{host}_total_input | Total input power | W |
| sensor.cleanergy_{host}_ac_grid_input | Grid/AC input | W |
| sensor.cleanergy_{host}_solar_pv_input | Solar panel input | W |
| sensor.cleanergy_{host}_remaining_time | Estimated runtime remaining | min |
| sensor.cleanergy_{host}_temperature | Device temperature | °F |
| sensor.cleanergy_{host}_standby_timeout | Standby timeout setting | min |
| sensor.cleanergy_{host}_led_timeout | LED timeout setting | min |
| sensor.cleanergy_{host}_ac_standby_time | AC standby setting | min |
| sensor.cleanergy_{host}_battery_pack_count | Battery pack count | |
| sensor.cleanergy_{host}_oil_volume | Generator oil volume | |
| sensor.cleanergy_{host}_generator_output | Generator output | W |
| sensor.cleanergy_{host}_fast_charge_state | Fast charge mode | |

### Switch

| Entity | Description |
|--------|-------------|
| switch.cleanergy_{host}_power_switch | Power on/off (both AC+DC) |

## Services

| Service | Description |
|---------|-------------|
| cleanergy.turn_on | Turn on all outputs |
| cleanergy.turn_off | Turn off all outputs |
| cleanergy.set_power_ac | Set AC output state (boolean) |
| cleanergy.set_power_dc | Set DC output state (boolean) |

## Configuration

| Field | Description | Default |
|-------|-------------|---------|
| host | Device IP address | `10.2.0.65` |
| port | TCP port | `5555` |
| scan_interval | Poll interval (seconds) | `10` |

## Notes

- The integration polls 10 "fast" attributes at ~3 second intervals (2 batches of 5 attrs + 1s delay)
- Other attributes are only queried during full device discovery
- Switch controls both AC and DC outputs simultaneously (bit0 | bit1 = both on)
- All sensors use proper HA device classes (battery, power, temperature, duration, voltage, current)
- Connection uses fresh TCP socket per batch pattern to avoid device rate limiting

## Troubleshooting

If sensors show `unavailable`:
1. Verify device is powered on and reachable from HA host
2. Check IP address matches device's current LAN IP
3. Check firewall isn't blocking TCP port 5555
4. Check Home Assistant logs for connection errors

## Development

Integration follows Home Assistant best practices:
- Uses `DataUpdateCoordinator` for coordinated polling
- Implements `CoordinatorEntity` for sensors/switch
- Fresh TCP connections per batch to avoid device overloading
- Proper unit/device class mapping for automatic entity categorization
- Connection test during config flow for immediate feedback

Based on TCP LAN protocol analysis from decompiled Cleanergy Android app.
