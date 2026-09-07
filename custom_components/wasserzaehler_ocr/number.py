"""Number-Entitaet zum manuellen Setzen des Zaehlerstands (pro Zaehler)."""

from __future__ import annotations

import aiohttp
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    QUICK_TIMEOUT,
    SET_VALUE_PATH,
    TYPE_CONFIG,
    meter_device_info,
    normalize_type,
)
from .coordinator import MeterCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Fuer jeden Zaehler ein Eingabefeld anlegen."""
    store = hass.data[DOMAIN][entry.entry_id]
    entities = [
        MeterSetValue(
            info["coordinator"],
            entry,
            mid,
            info["type"],
            info["meter"].get("name") or mid,
            store["base_url"],
        )
        for mid, info in store["meters"].items()
    ]
    async_add_entities(entities)


class MeterSetValue(CoordinatorEntity, NumberEntity):
    """Eingabefeld: Zaehlerstand manuell setzen."""

    _attr_has_entity_name = True
    _attr_name = "Stand setzen"
    _attr_native_min_value = 0
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:pencil"

    def __init__(
        self,
        coordinator: MeterCoordinator,
        entry: ConfigEntry,
        meter_id: str,
        mtype: str,
        name: str,
        base_url: str,
    ) -> None:
        """Initialisieren."""
        super().__init__(coordinator)
        cfg = TYPE_CONFIG[normalize_type(mtype)]
        self._meter_id = meter_id
        self._base_url = base_url.rstrip("/")
        self._attr_native_unit_of_measurement = cfg["total_unit"]
        self._attr_native_step = cfg["set_step"]
        self._attr_native_max_value = cfg["set_max"]
        self._attr_unique_id = f"{entry.entry_id}_{meter_id}_set_value"
        self._attr_device_info = meter_device_info(entry.entry_id, meter_id, mtype, name)

    @property
    def native_value(self) -> float | None:
        """Zeigt den aktuellen Zaehlerstand an (zur Orientierung)."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("value")

    async def async_set_native_value(self, value: float) -> None:
        """Neuen Zaehlerstand ans Add-on schicken."""
        session = async_get_clientsession(self.hass)
        url = f"{self._base_url}{SET_VALUE_PATH}"
        payload = {"value": value}
        if self._meter_id:
            payload["id"] = self._meter_id
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

        await self.coordinator.async_request_refresh()
