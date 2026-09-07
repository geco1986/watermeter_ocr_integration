"""Binary-Sensor (Problem-Melder) pro Zaehler.

Schlaegt an, sobald der Status des letzten Ablesevorgangs nicht 'ok' ist -
ideal fuer Benachrichtigungs-Automationen.
"""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, meter_device_info
from .coordinator import MeterCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Fuer jeden Zaehler einen Problem-Melder anlegen."""
    store = hass.data[DOMAIN][entry.entry_id]
    entities = [
        MeterProblem(
            info["coordinator"],
            entry,
            mid,
            info["type"],
            info["meter"].get("name") or mid,
        )
        for mid, info in store["meters"].items()
    ]
    async_add_entities(entities)


class MeterProblem(CoordinatorEntity, BinarySensorEntity):
    """Meldet ein Problem, wenn der letzte Ablesevorgang nicht ok war."""

    _attr_has_entity_name = True
    _attr_name = "Problem"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

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
        self._attr_unique_id = f"{entry.entry_id}_{meter_id}_problem"
        self._attr_device_info = meter_device_info(entry.entry_id, meter_id, mtype, name)

    @property
    def is_on(self) -> bool | None:
        """True = Problem. Status ungleich 'ok' gilt als Problem."""
        data = self.coordinator.data
        if data is None:
            return None
        return data.get("status") != "ok"

    @property
    def extra_state_attributes(self):
        """Fehlergrund und Fehlerzaehler als Zusatzinfo."""
        data = self.coordinator.data or {}
        return {
            "status": data.get("status"),
            "error": data.get("error"),
            "error_count": data.get("error_count"),
        }
