"""Config- und Options-Flow fuer die Zaehler-OCR-Integration."""

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
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_SCAN_INTERVAL,
    CONF_TYPE_OVERRIDES,
    CONF_URL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_URL,
    DOMAIN,
    HEALTH_PATH,
    QUICK_TIMEOUT,
    TYPE_CONFIG,
    normalize_type,
)


async def _test_connection(hass, base_url: str) -> str | None:
    """Prueft das Add-on. Gibt einen Fehlercode oder None (=ok) zurueck."""
    session = async_get_clientsession(hass)
    url = f"{base_url.rstrip('/')}{HEALTH_PATH}"
    try:
        timeout = aiohttp.ClientTimeout(total=QUICK_TIMEOUT)
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


def _type_selector() -> SelectSelector:
    """Auswahlfeld fuer den Zaehlertyp."""
    return SelectSelector(
        SelectSelectorConfig(
            options=[
                SelectOptionDict(value=key, label=cfg["label"])
                for key, cfg in TYPE_CONFIG.items()
            ],
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


class ZaehlerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Einrichtungs-Dialog: nur die Add-on-URL + Standardintervall."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Erster Schritt: URL + Intervall."""
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
                    title=base_url,
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
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        """Optionen-Dialog bereitstellen."""
        return ZaehlerOptionsFlow()


class ZaehlerOptionsFlow(OptionsFlow):
    """Intervall global anpassen und Zaehlertyp pro Zaehler ueberschreiben."""

    def __init__(self) -> None:
        """Mapping von Schema-Schluessel -> meter_id fuer die Auswertung."""
        self._key_to_id: dict[str, str] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Optionen anzeigen und speichern."""
        options = self.config_entry.options
        current_interval = options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        current_overrides: dict = dict(options.get(CONF_TYPE_OVERRIDES, {}))

        if user_input is not None:
            new_overrides = dict(current_overrides)
            for key, meter_id in self._key_to_id.items():
                if key in user_input:
                    new_overrides[meter_id] = user_input[key]
            return self.async_create_entry(
                title="",
                data={
                    CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                    CONF_TYPE_OVERRIDES: new_overrides,
                },
            )

        # Zaehler aus dem laufenden Setup lesen (falls vorhanden), sonst leer.
        store = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        schema_dict: dict = {
            vol.Required(
                CONF_SCAN_INTERVAL, default=current_interval
            ): vol.All(vol.Coerce(int), vol.Range(min=30)),
        }
        self._key_to_id = {}
        if store:
            for mid, info in store["meters"].items():
                name = info["meter"].get("name") or mid or "Zähler"
                key = f"Typ – {name}"
                self._key_to_id[key] = mid
                default_type = normalize_type(
                    current_overrides.get(mid) or info.get("type")
                )
                schema_dict[vol.Required(key, default=default_type)] = _type_selector()

        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(schema_dict)
        )
