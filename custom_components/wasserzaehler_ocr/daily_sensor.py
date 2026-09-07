"""Tagesverbrauch-Sensor (typgerecht) fuer einen Zaehler.

Merkt sich den Zaehlerstand zu Tagesbeginn und bildet die Differenz zum
aktuellen Stand. Reset um Mitternacht, uebersteht Neustarts via RestoreEntity.
Wasser wird in Litern ausgegeben (m3 * 1000), Strom/Waerme in kWh.
"""

from __future__ import annotations

import logging

from homeassistant.components.sensor import RestoreSensor, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import HomeAssistant

from .const import DOMAIN, TYPE_CONFIG, meter_device_info, normalize_type
from .coordinator import MeterCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Wird nicht direkt genutzt - MeterDaily wird ueber sensor.py angelegt."""
    return


class MeterDaily(CoordinatorEntity, RestoreSensor):
    """Verbrauch des aktuellen Tages, typgerechte Einheit."""

    _attr_has_entity_name = True
    _attr_name = "Verbrauch heute"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:chart-box-outline"

    def __init__(
        self,
        coordinator: MeterCoordinator,
        entry: ConfigEntry,
        meter_id: str,
        mtype: str,
        name: str,
    ) -> None:
        """Initialisieren."""
        super().__init__(coordinator)
        cfg = TYPE_CONFIG[normalize_type(mtype)]
        self._factor: float = cfg["daily_factor"]
        self._attr_native_unit_of_measurement = cfg["daily_unit"]
        self._attr_device_class = cfg["daily_device_class"]
        self._attr_unique_id = f"{entry.entry_id}_{meter_id}_daily"
        self._attr_device_info = meter_device_info(entry.entry_id, meter_id, mtype, name)
        self._start_of_day: float | None = None  # Basisstand in Grundeinheit
        self._consumption: float = 0.0

    async def async_added_to_hass(self) -> None:
        """Beim Hinzufuegen: gespeicherten Zustand wiederherstellen."""
        await super().async_added_to_hass()

        last_data = await self.async_get_last_sensor_data()
        if last_data is not None and last_data.native_value is not None:
            try:
                self._consumption = float(last_data.native_value)
            except (ValueError, TypeError):
                self._consumption = 0.0

        last_extra = await self.async_get_last_extra_data()
        if last_extra is not None:
            sod = last_extra.as_dict().get("start_of_day")
            if sod is not None:
                try:
                    self._start_of_day = float(sod)
                except (ValueError, TypeError):
                    self._start_of_day = None

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
            self._start_of_day = current
        self._consumption = 0.0
        self.async_write_ha_state()

    def _current_reading(self) -> float | None:
        """Aktuellen Zaehlerstand (Grundeinheit) aus den Coordinator-Daten."""
        if self.coordinator.data is None:
            return None
        val = self.coordinator.data.get("value")
        try:
            return float(val) if val is not None else None
        except (ValueError, TypeError):
            return None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Bei neuen Daten den Tagesverbrauch neu berechnen."""
        current = self._current_reading()
        if current is not None:
            if self._start_of_day is None:
                self._start_of_day = current
            if current < self._start_of_day:
                self._start_of_day = current
            self._consumption = round((current - self._start_of_day) * self._factor, 1)
        super()._handle_coordinator_update()

    @property
    def native_value(self) -> float:
        """Tagesverbrauch."""
        return self._consumption

    @property
    def extra_restore_state_data(self):
        """Zusatzdaten fuer die Wiederherstellung (Tagesbasis)."""
        from homeassistant.helpers.restore_state import RestoredExtraData

        return RestoredExtraData({"start_of_day": self._start_of_day})

    @property
    def extra_state_attributes(self):
        """Tagesbasis als Info anzeigen."""
        return {"start_of_day": self._start_of_day}
