"""Sensor-Entitaeten fuer die Zaehler-OCR-Integration.

Baut je Zaehler einen Satz Sensoren auf; Einheiten und Geraeteklassen
richten sich nach dem Zaehlertyp (Wasser / Strom / Waerme).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, TYPE_CONFIG, meter_device_info, normalize_type
from .coordinator import MeterCoordinator
from .daily_sensor import MeterDaily


def _rate(data: dict):
    """Momentanwert: generisches 'rate', sonst Wasser-Legacy 'flow_rate_l_min'."""
    if "rate" in data and data.get("rate") is not None:
        return data.get("rate")
    return data.get("flow_rate_l_min")


@dataclass(frozen=True, kw_only=True)
class MeterSensorDescription(SensorEntityDescription):
    """Sensorbeschreibung inkl. Wertfunktion."""

    value_fn: Callable[[dict], object]


def _build_descriptions(mtype: str) -> tuple[MeterSensorDescription, ...]:
    """Erzeugt die typgerechten Sensorbeschreibungen fuer einen Zaehler."""
    cfg = TYPE_CONFIG[normalize_type(mtype)]
    return (
        MeterSensorDescription(
            key="value",
            name="Zählerstand",
            native_unit_of_measurement=cfg["total_unit"],
            device_class=cfg["total_device_class"],
            state_class=SensorStateClass.TOTAL_INCREASING,
            icon=cfg["total_icon"],
            value_fn=lambda d: d.get("value"),
        ),
        MeterSensorDescription(
            key="rate",
            name=cfg["rate_name"],
            native_unit_of_measurement=cfg["rate_unit"],
            device_class=cfg["rate_device_class"],
            state_class=SensorStateClass.MEASUREMENT,
            icon=cfg["rate_icon"],
            value_fn=_rate,
        ),
        MeterSensorDescription(
            key="status",
            name="Status",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:information-outline",
            value_fn=lambda d: d.get("status"),
        ),
        MeterSensorDescription(
            key="error_count",
            name="Fehlerzähler",
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:alert-circle-outline",
            value_fn=lambda d: d.get("error_count"),
        ),
        MeterSensorDescription(
            key="raw_digits",
            name="Rohwert",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:numeric",
            value_fn=lambda d: d.get("raw_digits"),
        ),
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Sensoren fuer alle Zaehler des Eintrags einrichten."""
    store = hass.data[DOMAIN][entry.entry_id]
    entities: list = []
    for mid, info in store["meters"].items():
        coordinator: MeterCoordinator = info["coordinator"]
        mtype = info["type"]
        name = info["meter"].get("name") or mid
        for desc in _build_descriptions(mtype):
            entities.append(
                MeterSensor(coordinator, entry, mid, mtype, name, desc)
            )
        entities.append(MeterDaily(coordinator, entry, mid, mtype, name))
    async_add_entities(entities)


class MeterSensor(CoordinatorEntity, SensorEntity):
    """Ein einzelner Wert aus der Add-on-Antwort eines Zaehlers."""

    entity_description: MeterSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MeterCoordinator,
        entry: ConfigEntry,
        meter_id: str,
        mtype: str,
        name: str,
        description: MeterSensorDescription,
    ) -> None:
        """Initialisieren."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{meter_id}_{description.key}"
        self._attr_device_info = meter_device_info(entry.entry_id, meter_id, mtype, name)

    @property
    def native_value(self):
        """Aktuellen Wert aus den Coordinator-Daten holen."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self):
        """Beim Status-Sensor die Plausibilitaets-Details anhaengen."""
        data = self.coordinator.data or {}
        if self.entity_description.key == "status":
            return {
                "error": data.get("error"),
                "plausible": data.get("plausible"),
                "last_value": data.get("last_value"),
                "rejected": data.get("rejected"),
                "held": data.get("held"),
            }
        return None
