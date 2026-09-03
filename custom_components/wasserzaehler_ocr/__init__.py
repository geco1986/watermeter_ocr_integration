"""Wasserzähler OCR - Home-Assistant-Integration.

Bindet die Werte des Wasserzaehler-OCR-Add-ons (Zaehlerstand, Durchflussrate,
Fehlerzaehler, Status) als native Entitaeten ein und stellt einen Dienst zum
manuellen Setzen des Zaehlerstands bereit.
"""

from __future__ import annotations

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import WasserzaehlerCoordinator

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
]

SERVICE_SET_VALUE = "set_value"
SET_VALUE_SCHEMA = vol.Schema(
    {vol.Required("value"): vol.Coerce(float)}
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Integration aus einem Config-Entry einrichten."""
    base_url = entry.data[CONF_URL]
    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )

    coordinator = WasserzaehlerCoordinator(hass, base_url, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _async_register_services(hass)

    return True


def _async_register_services(hass: HomeAssistant) -> None:
    """Den set_value-Dienst registrieren (einmalig)."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_VALUE):
        return

    async def _handle_set_value(call: ServiceCall) -> None:
        """Ruft den /set_value-Endpunkt des Add-ons auf."""
        value = call.data["value"]

        # Basis-URL des ersten konfigurierten Eintrags nutzen
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            raise HomeAssistantError("Keine Wasserzähler-OCR-Integration eingerichtet.")
        base_url = entries[0].data[CONF_URL].rstrip("/")

        session = async_get_clientsession(hass)
        url = f"{base_url}/set_value"
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with session.post(url, json={"value": value}, timeout=timeout) as resp:
                data = await resp.json(content_type=None)
                if resp.status != 200 or not data.get("ok"):
                    raise HomeAssistantError(
                        f"Add-on lehnte den Wert ab: {data.get('error', resp.status)}"
                    )
        except aiohttp.ClientError as err:
            raise HomeAssistantError(f"Add-on nicht erreichbar: {err}") from err

        # Danach sofort neu abfragen, damit die Sensoren den neuen Wert zeigen
        for coordinator in hass.data.get(DOMAIN, {}).values():
            await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN, SERVICE_SET_VALUE, _handle_set_value, schema=SET_VALUE_SCHEMA
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Integration entladen."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        # Dienst entfernen, wenn keine Eintraege mehr da sind
        if not hass.config_entries.async_entries(DOMAIN):
            hass.services.async_remove(DOMAIN, SERVICE_SET_VALUE)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Config-Entry neu laden, wenn die Optionen geaendert wurden."""
    await hass.config_entries.async_reload(entry.entry_id)
