"""DataUpdateCoordinator for Cleanergy S012."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CMD_QUERY,
    CMD_POWER,
    DOMAIN,
    FAST_ATTRS,
    SLOW_ATTRS,
    SLOW_POLL_EVERY,
)

_LOGGER = logging.getLogger(__name__)

BATCH_SIZE = 5
BATCH_RETRIES = 1
BATCH_DELAY = 0.5  # seconds between batches (device rate-limit guard)


def _sn() -> str:
    return str(int(time.time() * 1000))


def _frame(cmd: int, msg: dict) -> bytes:
    envelope = {"msg": msg, "pv": 0, "cmd": cmd, "sn": _sn()}
    return (json.dumps(envelope, separators=(",", ":")) + "\r\n").encode()


async def _query_batch(host: str, port: int, batch: list[int]) -> dict[int, str]:
    for attempt in range(BATCH_RETRIES + 1):
        writer = None
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=5.0
            )
            writer.write(_frame(CMD_QUERY, {"attr": batch}))
            await writer.drain()
            raw = await asyncio.wait_for(reader.readuntil(b"\r\n"), timeout=3.0)
            obj = json.loads(raw.decode())
            if obj.get("cmd") != CMD_QUERY:
                _LOGGER.debug("Unexpected cmd %s in query response", obj.get("cmd"))
                return {}
            raw_data = obj.get("msg", {}).get("data", {})
            return {int(k): v for k, v in raw_data.items()}
        except ConnectionRefusedError:
            _LOGGER.error(
                "Connection refused to %s:%d — is the device powered on?", host, port
            )
            return {}
        except asyncio.TimeoutError:
            _LOGGER.warning(
                "Batch %s timed out (%s:%d, attempt %d/%d)",
                batch,
                host,
                port,
                attempt + 1,
                BATCH_RETRIES + 1,
            )
        except (asyncio.IncompleteReadError, asyncio.LimitOverrunError) as err:
            _LOGGER.warning("Incomplete response for batch %s: %s", batch, err)
        except json.JSONDecodeError as err:
            _LOGGER.warning("Invalid JSON from device for batch %s: %s", batch, err)
        except OSError as err:
            _LOGGER.warning(
                "Network error for batch %s (%s:%d, attempt %d/%d): %s",
                batch,
                host,
                port,
                attempt + 1,
                BATCH_RETRIES + 1,
                err,
            )
        finally:
            if writer is not None:
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass
        if attempt < BATCH_RETRIES:
            await asyncio.sleep(0.3)
    return {}


class CleanergyCoordinator(DataUpdateCoordinator[dict]):
    """Coordinator that polls the S012 device over TCP."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.host = host
        self.port = port
        self._slow_counter = SLOW_POLL_EVERY  # trigger slow poll on first update
        self._slow_cache: dict = {}
        self._switch_lock = asyncio.Lock()

    async def _async_update_data(self) -> dict:
        try:
            data = await self._poll(FAST_ATTRS)

            # Slow attrs: refresh every SLOW_POLL_EVERY cycles
            self._slow_counter -= 1
            if self._slow_counter <= 0:
                slow_data = await self._poll(SLOW_ATTRS)
                data.update(slow_data)
                self._slow_cache.update(slow_data)
                self._slow_counter = SLOW_POLL_EVERY
            else:
                # Merge cached slow attrs into each update
                data.update(self._slow_cache)

            return data
        except Exception as err:
            raise UpdateFailed(f"Error polling Cleanergy device: {err}") from err

    async def _poll(self, attrs: list[int]) -> dict:
        data: dict = {}
        batches = [attrs[i : i + BATCH_SIZE] for i in range(0, len(attrs), BATCH_SIZE)]
        for i, batch in enumerate(batches):
            batch_data = await _query_batch(self.host, self.port, batch)
            data.update(batch_data)
            if i < len(batches) - 1:
                await asyncio.sleep(BATCH_DELAY)
        return data

    async def async_send_command(self, cmd: int, msg: dict) -> dict | None:
        writer = None
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=5.0
            )
            writer.write(_frame(cmd, msg))
            await writer.drain()
            raw = await asyncio.wait_for(reader.readuntil(b"\r\n"), timeout=3.0)
            obj = json.loads(raw.decode())
            if obj.get("cmd") != cmd:
                _LOGGER.warning(
                    "Unexpected response cmd=%s for sent cmd=%d", obj.get("cmd"), cmd
                )
            return obj.get("msg", {}).get("data")
        except Exception as err:
            _LOGGER.error(
                "Command cmd=%d to %s:%d failed: %s", cmd, self.host, self.port, err
            )
            return None
        finally:
            if writer is not None:
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass

    async def _send_switch_value(self, new_value: int) -> None:
        result = await self.async_send_command(
            CMD_POWER, {"data": {"1": new_value}, "attr": [1]}
        )
        if result is not None and self.data is not None:
            self.data[1] = str(new_value)

    async def async_set_switch_bit(self, bit: int, on: bool) -> None:
        # bit 0 = AC, bit 1 = DC
        # Lock serializes concurrent toggles so the second reads the first's result.
        async with self._switch_lock:
            current = 0
            if self.data:
                try:
                    current = int(self.data.get(1, 0))
                except (ValueError, TypeError):
                    pass
            if on:
                new_value = current | (1 << bit)
            else:
                new_value = current & ~(1 << bit)
            await self._send_switch_value(new_value)

    async def async_set_all_outputs(self, on: bool) -> None:
        async with self._switch_lock:
            await self._send_switch_value(3 if on else 0)
