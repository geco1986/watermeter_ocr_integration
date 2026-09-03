"""Config Flow fuer die Wasserzaehler-OCR-Integration."""

from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_URL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_URL,
    DOMAIN,
)


async def _test_connection(hass, base_url: str) -> str | None:
    """Prueft, ob das Add-on erreichbar ist. Gibt Fehlercode oder None zurueck."""
    session = async_get_clientsession(hass)
    url = f"{base_url.rstrip('/')}/health"
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with session.get(url, timeout=timeout) as resp:
            if resp.status != 200:
                return "cannot_connect"
            data = await resp.json(content_type=None)
            if not isinstance(data, dict) or data.get("status") != "ok":
                return "cannot_connect"
    except aiohttp.ClientError:
        return "cannot_connect"
    except Exception:  # noqa: BLE001
        return "unknown"
    return None


class WasserzaehlerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Einrichtungs-Dialog."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Erster (und einziger) Schritt: URL + Intervall."""
        errors: dict[str, str] = {}

        if user_input is not None:
            base_url = user_input[CONF_URL]
            error = await _test_connection(self.hass, base_url)
            if error:
                errors["base"] = error
            else:
                await self.async_set_unique_id(base_url)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Wasserzähler OCR",
                    data={
                        CONF_URL: base_url,
                        CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_URL,
                    default=(user_input or {}).get(CONF_URL, DEFAULT_URL),
                ): str,
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=(user_input or {}).get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=30)),
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        """Optionen-Dialog bereitstellen."""
        return WasserzaehlerOptionsFlow()


class WasserzaehlerOptionsFlow(OptionsFlow):
    """Erlaubt das Anpassen des Abfrageintervalls nach der Einrichtung."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Intervall anpassen."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL, default=current
                ): vol.All(vol.Coerce(int), vol.Range(min=30)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
