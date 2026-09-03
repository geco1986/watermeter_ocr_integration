"""Tagesverbrauch-Sensor fuer die Wasserzaehler-OCR-Integration.

Zeigt den Wasserverbrauch des aktuellen Tages in Litern. Merkt sich den
Zaehlerstand zu Tagesbeginn und bildet die Differenz zum aktuellen Stand.
Reset um Mitternacht. Uebersteht Neustarts via RestoreEntity.
"""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import WasserzaehlerCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Tagesverbrauch-Sensor einrichten."""
    coordinator: WasserzaehlerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WasserzaehlerDaily(coordinator, entry)])


class WasserzaehlerDaily(CoordinatorEntity, RestoreSensor):
    """Wasserverbrauch des aktuellen Tages in Litern."""

    _attr_name = "Wasserzähler Verbrauch heute"
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:water"

    def __init__(
        self,
        coordinator: WasserzaehlerCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialisieren."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_daily"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Wasserzähler OCR",
            manufacturer="Eigenbau",
            model="ESP32-CAM + Ollama",
        )
        # Zaehlerstand (m3) zu Tagesbeginn - Basis fuer die Differenz
        self._start_of_day_m3: float | None = None
        self._consumption_l: float = 0.0

    async def async_added_to_hass(self) -> None:
        """Beim Hinzufuegen: gespeicherten Zustand wiederherstellen."""
        await super().async_added_to_hass()

        # Letzten Zustand wiederherstellen (Verbrauch + Tagesbasis)
        last_data = await self.async_get_last_sensor_data()
        if last_data is not None and last_data.native_value is not None:
            try:
                self._consumption_l = float(last_data.native_value)
            except (ValueError, TypeError):
                self._consumption_l = 0.0

        last_extra = await self.async_get_last_extra_data()
        if last_extra is not None:
            data = last_extra.as_dict()
            sod = data.get("start_of_day_m3")
            if sod is not None:
                try:
                    self._start_of_day_m3 = float(sod)
                except (ValueError, TypeError):
                    self._start_of_day_m3 = None

        # Taeglicher Reset um Mitternacht
        self.async_on_remove(
            async_track_time_change(
                self.hass, self._handle_midnight, hour=0, minute=0, second=0
            )
        )

    @callback
    def _handle_midnight(self, now) -> None:
        """Um Mitternacht: aktuellen Stand als neue Tagesbasis setzen."""
        current = self._current_reading()
        if current is not None:
            self._start_of_day_m3 = current
        self._consumption_l = 0.0
        self.async_write_ha_state()

    def _current_reading(self) -> float | None:
        """Aktuellen Zaehlerstand (m3) aus den Coordinator-Daten."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("value")

    @callback
    def _handle_coordinator_update(self) -> None:
        """Bei neuen Daten den Tagesverbrauch neu berechnen."""
        current = self._current_reading()
        if current is not None:
            # Erste Messung ueberhaupt -> Tagesbasis initialisieren
            if self._start_of_day_m3 is None:
                self._start_of_day_m3 = current
            # Falls der Zaehler unter die Tagesbasis faellt (z. B. manuelle
            # Korrektur nach unten), Basis nachziehen, um negative Werte zu
            # vermeiden.
            if current < self._start_of_day_m3:
                self._start_of_day_m3 = current
            # Verbrauch in Litern (1 m3 = 1000 L)
            self._consumption_l = round(
                (current - self._start_of_day_m3) * 1000.0, 1
            )
        super()._handle_coordinator_update()

    @property
    def native_value(self) -> float:
        """Tagesverbrauch in Litern."""
        return self._consumption_l

    @property
    def extra_restore_state_data(self):
        """Zusatzdaten fuer die Wiederherstellung (Tagesbasis)."""
        from homeassistant.helpers.restore_state import RestoredExtraData

        return RestoredExtraData({"start_of_day_m3": self._start_of_day_m3})

    @property
    def extra_state_attributes(self):
        """Tagesbasis als Info anzeigen."""
        return {"start_of_day_m3": self._start_of_day_m3}
