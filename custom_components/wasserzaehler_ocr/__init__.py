"""Zaehler OCR - Home-Assistant-Integration (Wasser / Strom / Waerme).

Bindet die Werte des OCR-Add-ons als native Entitaeten ein. Ein Add-on kann
mehrere Zaehler bereitstellen (Discovery ueber /meters); je Zaehler entsteht
ein eigenes Geraet mit typgerechten Entitaeten und einem eigenen Poll-Zyklus.
"""

from __future__ import annotations

import logging

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry as dr

from .const import (
    CONF_SCAN_INTERVAL,
    CONF_TYPE_OVERRIDES,
    CONF_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    HEALTH_PATH,
    METER_WATER,
    METERS_PATH,
    QUICK_TIMEOUT,
    SET_VALUE_PATH,
    normalize_type,
)
from .coordinator import MeterCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
]

SERVICE_SET_VALUE = "set_value"
SET_VALUE_SCHEMA = vol.Schema(
    {
        vol.Required("value"): vol.Coerce(float),
        vol.Optional("meter_id"): str,
    }
)


def _normalize_meter(raw, index: int) -> dict:
    """Bringt einen Discovery-Eintrag in die Form {id, name, type}."""
    if isinstance(raw, str):
        return {"id": raw, "name": raw, "type": METER_WATER}
    if not isinstance(raw, dict):
        return {"id": f"meter_{index}", "name": f"Zähler {index + 1}", "type": METER_WATER}
    mid = str(raw.get("id") or raw.get("meter_id") or f"meter_{index}")
    name = str(raw.get("name") or raw.get("title") or mid)
    mtype = normalize_type(raw.get("type") or raw.get("meter_type"))
    return {"id": mid, "name": name, "type": mtype}


async def _discover_meters(hass: HomeAssistant, base_url: str) -> list[dict]:
    """Zaehler vom Add-on abfragen. Faellt auf einen Standardzaehler zurueck."""
    session = async_get_clientsession(hass)
    url = f"{base_url.rstrip('/')}{METERS_PATH}"
    try:
        timeout = aiohttp.ClientTimeout(total=QUICK_TIMEOUT)
        async with session.get(url, timeout=timeout) as resp:
            if resp.status == 200:
                data = await resp.json(content_type=None)
                meters = data.get("meters") if isinstance(data, dict) else data
                if isinstance(meters, list) and meters:
                    return [_normalize_meter(m, i) for i, m in enumerate(meters)]
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Kein /meters-Endpunkt - nutze Legacy-Einzelzaehler")
    # Legacy-Add-on: ein einzelner Zaehler ohne ID (spricht /process direkt an).
    return [{"id": "", "name": "Zähler", "type": METER_WATER}]


async def _check_health(hass: HomeAssistant, base_url: str) -> bool:
    """Prueft, ob das Add-on grundsaetzlich erreichbar ist."""
    session = async_get_clientsession(hass)
    url = f"{base_url.rstrip('/')}{HEALTH_PATH}"
    try:
        timeout = aiohttp.ClientTimeout(total=QUICK_TIMEOUT)
        async with session.get(url, timeout=timeout) as resp:
            if resp.status != 200:
                return False
            data = await resp.json(content_type=None)
            return isinstance(data, dict) and data.get("status") == "ok"
    except Exception:  # noqa: BLE001
        return False


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Integration aus einem Config-Entry einrichten."""
    base_url = entry.data[CONF_URL]

    if not await _check_health(hass, base_url):
        raise ConfigEntryNotReady(f"Add-on unter {base_url} nicht erreichbar")

    default_interval = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )
    type_overrides: dict = entry.options.get(CONF_TYPE_OVERRIDES, {})

    meters = await _discover_meters(hass, base_url)

    coordinators: dict[str, dict] = {}
    for meter in meters:
        mid = meter["id"]
        mtype = normalize_type(type_overrides.get(mid) or meter.get("type"))
        coordinator = MeterCoordinator(
            hass, base_url, mid, meter["name"], default_interval
        )
        coordinators[mid] = {
            "coordinator": coordinator,
            "meter": meter,
            "type": mtype,
        }
        # Erste Ablesung im Hintergrund anstossen - blockiert das Setup nicht,
        # da die OCR-Kette pro Zaehler lange dauern kann.
        entry.async_create_background_task(
            hass, coordinator.async_refresh(), name=f"{DOMAIN}_init_{mid}"
        )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "base_url": base_url,
        "meters": coordinators,
    }

    # Veraltete Geraete aufraeumen: Alles, was diesem Eintrag zugeordnet ist,
    # aber keinem aktuell gemeldeten Zaehler mehr entspricht (z. B. das alte
    # Einzel-Geraet frueherer Versionen), wird aus dem Register entfernt.
    _cleanup_stale_devices(hass, entry, coordinators)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    _async_register_services(hass)
    return True


def _valid_identifiers(entry_id: str, meter_ids) -> set:
    """Gueltige Geraete-Identifier fuer die aktuell gemeldeten Zaehler."""
    return {(DOMAIN, f"{entry_id}_{mid}") for mid in meter_ids}


def _cleanup_stale_devices(hass: HomeAssistant, entry: ConfigEntry, coordinators: dict) -> None:
    """Entfernt Geraete dieses Eintrags, die zu keinem aktuellen Zaehler passen."""
    dev_reg = dr.async_get(hass)
    valid = _valid_identifiers(entry.entry_id, coordinators.keys())
    for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        if not any(ident in valid for ident in device.identifiers):
            _LOGGER.info("Entferne veraltetes Geraet '%s'", device.name_by_user or device.name)
            dev_reg.async_update_device(device.id, remove_config_entry_id=entry.entry_id)


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: ConfigEntry, device
) -> bool:
    """Erlaubt das manuelle Loeschen eines Geraets in der HA-Oberflaeche.

    Zugelassen wird nur, was keinem aktuell gemeldeten Zaehler entspricht -
    aktive Zaehler-Geraete lassen sich so nicht versehentlich entfernen.
    """
    store = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    valid = _valid_identifiers(entry.entry_id, store["meters"].keys()) if store else set()
    return not any(ident in valid for ident in device.identifiers)


def _async_register_services(hass: HomeAssistant) -> None:
    """Den set_value-Dienst registrieren (einmalig)."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_VALUE):
        return

    async def _handle_set_value(call: ServiceCall) -> None:
        """Ruft /set_value fuer einen bestimmten Zaehler auf."""
        value = call.data["value"]
        meter_id = call.data.get("meter_id")

        # Passenden Zaehler ueber alle Eintraege finden.
        target = None
        all_meters: list[tuple[str, dict]] = []
        for store in hass.data.get(DOMAIN, {}).values():
            for mid, info in store["meters"].items():
                all_meters.append((store["base_url"], info))
                if meter_id is not None and mid == meter_id:
                    target = (store["base_url"], info)

        if meter_id is None:
            if len(all_meters) == 1:
                target = all_meters[0]
            else:
                raise HomeAssistantError(
                    "Mehrere Zähler vorhanden - bitte meter_id angeben."
                )
        if target is None:
            raise HomeAssistantError(f"Kein Zähler mit ID '{meter_id}' gefunden.")

        base_url, info = target
        coordinator: MeterCoordinator = info["coordinator"]
        payload = {"value": value}
        mid = info["meter"]["id"]
        if mid:
            payload["id"] = mid

        session = async_get_clientsession(hass)
        url = f"{base_url.rstrip('/')}{SET_VALUE_PATH}"
        try:
            timeout = aiohttp.ClientTimeout(total=QUICK_TIMEOUT)
            async with session.post(url, json=payload, timeout=timeout) as resp:
                data = await resp.json(content_type=None)
                if resp.status != 200 or not data.get("ok"):
                    raise HomeAssistantError(
                        f"Add-on lehnte den Wert ab: {data.get('error', resp.status)}"
                    )
        except aiohttp.ClientError as err:
            raise HomeAssistantError(f"Add-on nicht erreichbar: {err}") from err

        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN, SERVICE_SET_VALUE, _handle_set_value, schema=SET_VALUE_SCHEMA
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Integration entladen."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.config_entries.async_entries(DOMAIN):
            hass.services.async_remove(DOMAIN, SERVICE_SET_VALUE)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Config-Entry neu laden, wenn Optionen geaendert wurden."""
    await hass.config_entries.async_reload(entry.entry_id)
