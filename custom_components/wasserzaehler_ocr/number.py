"""Number-Entitaet zum manuellen Setzen des Zaehlerstands.

Erscheint als Eingabefeld direkt auf der Geraetekarte. Beim Setzen wird der
/set_value-Endpunkt des Add-ons aufgerufen (Zeitstempel neu, Fehlerzaehler 0).
"""

from __future__ import annotations

import aiohttp
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WasserzaehlerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Number-Entitaet einrichten."""
    coordinator: WasserzaehlerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WasserzaehlerSetValue(coordinator, entry)])


class WasserzaehlerSetValue(CoordinatorEntity, NumberEntity):
    """Eingabefeld: Zaehlerstand manuell setzen."""

    _attr_name = "Wasserzähler Stand setzen"
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    _attr_native_min_value = 0
    _attr_native_max_value = 999999
    _attr_native_step = 0.001
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:pencil"

    def __init__(
        self,
        coordinator: WasserzaehlerCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialisieren."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_set_value"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Wasserzähler OCR",
            manufacturer="Eigenbau",
            model="ESP32-CAM + Ollama",
        )

    @property
    def native_value(self) -> float | None:
        """Zeigt den aktuellen Zaehlerstand an (zur Orientierung)."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("value")

    async def async_set_native_value(self, value: float) -> None:
        """Neuen Zaehlerstand ans Add-on schicken."""
        base_url = self._entry.data[CONF_URL].rstrip("/")
        session = async_get_clientsession(self.hass)
        url = f"{base_url}/set_value"
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with session.post(
                url, json={"value": value}, timeout=timeout
            ) as resp:
                data = await resp.json(content_type=None)
                if resp.status != 200 or not data.get("ok"):
                    raise HomeAssistantError(
                        f"Add-on lehnte den Wert ab: {data.get('error', resp.status)}"
                    )
        except aiohttp.ClientError as err:
            raise HomeAssistantError(f"Add-on nicht erreichbar: {err}") from err

        # Sofort neu abfragen, damit alle Sensoren den neuen Wert zeigen
        await self.coordinator.async_request_refresh()
