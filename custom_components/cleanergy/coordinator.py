"""DataUpdateCoordinator for Cleanergy S012."""

from __future__ import annotations

import asyncio
import json
import logging
import time

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CMD_QUERY,
    CMD_POWER,
    CONFIG_ATTRS,
    DOMAIN,
    POLL_ATTRS,
)

_LOGGER = logging.getLogger(__name__)

BATCH_INITIAL = 10
BATCH_MIN = 1
BATCH_MAX = 25
BATCH_GROW_AFTER = 50
BACKOFF_INITIAL = 0.5
BACKOFF_MAX = 30.0
CONFIG_REFRESH_INTERVAL = 300.0


def _sn() -> str:
    return str(int(time.time() * 1000))


def _frame(cmd: int, msg: dict) -> bytes:
    envelope = {"msg": msg, "pv": 0, "cmd": cmd, "sn": _sn()}
    return (json.dumps(envelope, separators=(",", ":")) + "\r\n").encode()


class CleanergyCoordinator(DataUpdateCoordinator[dict]):
    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        scan_interval: int,
    ) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=None)
        self.host = host
        self.port = port
        self._switch_lock = asyncio.Lock()
        self._poll_lock = asyncio.Lock()

        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

        self._batch_size: int = BATCH_INITIAL
        self._batch_successes: int = 0

        self._config_cache: dict = {}
        self._last_config_fetch: float = 0.0

        self._poll_task: asyncio.Task | None = None

    async def _connect(self) -> None:
        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port), timeout=5.0
        )

    async def _disconnect(self) -> None:
        writer, self._writer = self._writer, None
        self._reader = None
        if writer is not None:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def _ensure_connected(self) -> None:
        if self._writer is None or self._writer.is_closing():
            await self._connect()

    def _record_batch_result(self, requested: list[int], received: dict) -> None:
        if len(received) >= len(requested):
            self._batch_successes += 1
            if (
                self._batch_successes >= BATCH_GROW_AFTER
                and self._batch_size < BATCH_MAX
            ):
                self._batch_size = min(self._batch_size + 1, BATCH_MAX)
                self._batch_successes = 0
                _LOGGER.debug("Batch size → %d", self._batch_size)
        else:
            old = self._batch_size
            self._batch_size = max(self._batch_size - 2, BATCH_MIN)
            self._batch_successes = 0
            if self._batch_size < old:
                _LOGGER.info(
                    "Partial response (%d/%d attrs); batch size %d → %d",
                    len(received),
                    len(requested),
                    old,
                    self._batch_size,
                )

    async def _send_recv(self, attrs: list[int]) -> dict[int, str] | None:
        try:
            await self._ensure_connected()
            self._writer.write(_frame(CMD_QUERY, {"attr": attrs}))
            await self._writer.drain()
            raw = await asyncio.wait_for(self._reader.readuntil(b"\r\n"), timeout=3.0)
            obj = json.loads(raw.decode())
            if obj.get("cmd") != CMD_QUERY:
                _LOGGER.debug("Unexpected cmd %s in query response", obj.get("cmd"))
                return None
            raw_data = obj.get("msg", {}).get("data", {})
            return {int(k): v for k, v in raw_data.items()}
        except asyncio.CancelledError:
            raise
        except ConnectionRefusedError:
            _LOGGER.error("Connection refused to %s:%d", self.host, self.port)
            await self._disconnect()
            return None
        except asyncio.TimeoutError:
            _LOGGER.warning("Query timed out (%s:%d)", self.host, self.port)
            await self._disconnect()
            return None
        except (asyncio.IncompleteReadError, json.JSONDecodeError, OSError) as err:
            _LOGGER.warning("Query error (%s:%d): %s", self.host, self.port, err)
            await self._disconnect()
            return None

    async def _poll_cycle(self) -> dict | None:
        async with self._poll_lock:
            now = time.monotonic()
            include_config = (now - self._last_config_fetch) >= CONFIG_REFRESH_INTERVAL

            remaining = list(POLL_ATTRS) + (
                list(CONFIG_ATTRS) if include_config else []
            )
            data: dict = {}

            while remaining:
                batch = remaining[: self._batch_size]
                remaining = remaining[self._batch_size :]
                result = await self._send_recv(batch)
                if result is None:
                    return None
                self._record_batch_result(batch, result)
                data.update(result)

            if include_config:
                self._config_cache.update(
                    {k: v for k, v in data.items() if k in set(CONFIG_ATTRS)}
                )
                self._last_config_fetch = now

            return {**self._config_cache, **data}

    async def _poll_loop(self) -> None:
        backoff = 0.0
        while True:
            try:
                if backoff:
                    await asyncio.sleep(backoff)
                result = await self._poll_cycle()
                if result is not None:
                    if result != self.data:
                        self.async_set_updated_data(result)
                    backoff = 0.0
                else:
                    backoff = min((backoff or BACKOFF_INITIAL) * 2, BACKOFF_MAX)
                    _LOGGER.debug("Poll failed; backing off %.1fs", backoff)
            except asyncio.CancelledError:
                raise
            except Exception as err:
                _LOGGER.error("Unexpected error in poll loop: %s", err)
                backoff = min((backoff or BACKOFF_INITIAL) * 2, BACKOFF_MAX)

    async def _async_update_data(self) -> dict:
        result = await self._poll_cycle()
        if result is None:
            raise UpdateFailed(f"Could not reach device at {self.host}:{self.port}")
        return result

    async def async_config_entry_first_refresh(self) -> None:
        await super().async_config_entry_first_refresh()
        self._poll_task = self.hass.async_create_task(self._poll_loop())

    async def async_shutdown(self) -> None:
        if self._poll_task is not None:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        await self._disconnect()

    async def async_send_command(self, cmd: int, msg: dict) -> dict | None:
        # Commands use a fresh connection so they don't interfere with the poll loop.
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
            new_value = (current | (1 << bit)) if on else (current & ~(1 << bit))
            await self._send_switch_value(new_value)

    async def async_set_all_outputs(self, on: bool) -> None:
        async with self._switch_lock:
            await self._send_switch_value(3 if on else 0)
