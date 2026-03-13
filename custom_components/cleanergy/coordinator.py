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


def _sn() -> str:
    return str(int(time.time() * 1000))


def _frame(cmd: int, msg: dict) -> bytes:
    msg_str = json.dumps(msg, separators=(",", ":"))
    packet = f'{{"msg":{msg_str},"pv":0,"cmd":{cmd},"sn":"{_sn()}"}}\r\n'
    return packet.encode()


async def _query_batch(host: str, port: int, batch: list[int]) -> dict:
    """Open a fresh TCP connection, query one batch of attrs, close."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=5.0
        )
        writer.write(_frame(CMD_QUERY, {"attr": batch}))
        await writer.drain()
        raw = await asyncio.wait_for(reader.read(4096), timeout=3.0)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass

        for line in raw.decode(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if obj.get("cmd") == CMD_QUERY:
                    return obj.get("msg", {}).get("data", {})
            except json.JSONDecodeError:
                pass
    except Exception as err:
        _LOGGER.debug("Batch query %s failed: %s", batch, err)
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
                await asyncio.sleep(1.0)
        return data

    async def async_send_command(self, cmd: int, msg: dict) -> None:
        """Send a control command (e.g. cmd=3 power on/off)."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=5.0
            )
            writer.write(_frame(cmd, msg))
            await writer.drain()
            await asyncio.wait_for(reader.read(4096), timeout=3.0)
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
        except Exception as err:
            _LOGGER.error("Command cmd=%d failed: %s", cmd, err)

    async def async_set_switch_bit(self, bit: int, on: bool) -> None:
        """Toggle one output bit while preserving the other.

        bit 0 = AC, bit 1 = DC
        Reads current switch_state from coordinator cache, flips the bit, sends.
        """
        current = 0
        if self.data:
            try:
                current = int(self.data.get("1", 0))
            except (ValueError, TypeError):
                pass
        if on:
            new_value = current | (1 << bit)
        else:
            new_value = current & ~(1 << bit)
        await self.async_send_command(
            CMD_POWER, {"data": {"1": new_value}, "attr": [1]}
        )
