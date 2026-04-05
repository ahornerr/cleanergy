"""Config flow for Cleanergy S012 integration."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import CMD_QUERY, DEFAULT_IP, DEFAULT_PORT, DOMAIN
from .coordinator import _frame

_LOGGER = logging.getLogger(__name__)


async def _test_connection(host: str, port: int) -> bool:
    writer = None
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=5.0
        )
        writer.write(_frame(CMD_QUERY, {"attr": [3]}))
        await writer.drain()
        raw = await asyncio.wait_for(reader.readuntil(b"\r\n"), timeout=3.0)
        obj = json.loads(raw.decode())
        return bool(obj.get("msg", {}).get("data"))
    except Exception:
        return False
    finally:
        if writer is not None:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("host", default=DEFAULT_IP): str,
        vol.Optional("port", default=DEFAULT_PORT): int,
        vol.Optional("scan_interval", default=10): vol.All(int, vol.Range(min=1)),
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the setup config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                ok = await _test_connection(
                    user_input["host"], user_input.get("port", DEFAULT_PORT)
                )
                if not ok:
                    errors["base"] = "cannot_connect"
                else:
                    return self.async_create_entry(
                        title=f"Cleanergy S012 ({user_input['host']})",
                        data=user_input,
                    )
            except Exception:
                _LOGGER.exception("Unexpected error during connection test")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
