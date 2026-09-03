"""Sensor-Entitaeten fuer die Wasserzaehler-OCR-Integration."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfVolume, UnitOfVolumeFlowRate
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WasserzaehlerCoordinator


@dataclass(frozen=True, kw_only=True)
class WzSensorDescription(SensorEntityDescription):
    """Beschreibung eines Sensors inkl. Wie-hole-ich-den-Wert-Funktion."""

    value_fn: Callable[[dict], object]


SENSORS: tuple[WzSensorDescription, ...] = (
    WzSensorDescription(
        key="value",
        translation_key="value",
        name="Wasserzähler Stand",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.get("value"),
    ),
    WzSensorDescription(
        key="flow_rate_l_min",
        translation_key="flow_rate_l_min",
        name="Wasserzähler Durchfluss",
        native_unit_of_measurement=UnitOfVolumeFlowRate.LITERS_PER_MINUTE,
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:water-pump",
        value_fn=lambda d: d.get("flow_rate_l_min"),
    ),
    WzSensorDescription(
        key="error_count",
        translation_key="error_count",
        name="Wasserzähler Fehlerzähler",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert-circle-outline",
        value_fn=lambda d: d.get("error_count"),
    ),
    WzSensorDescription(
        key="status",
        translation_key="status",
        name="Wasserzähler Status",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:information-outline",
        value_fn=lambda d: d.get("status"),
    ),
    WzSensorDescription(
        key="raw_digits",
        translation_key="raw_digits",
        name="Wasserzähler Rohwert",
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
    """Sensoren einrichten."""
    from .daily_sensor import WasserzaehlerDaily

    coordinator: WasserzaehlerCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list = [
        WasserzaehlerSensor(coordinator, entry, desc) for desc in SENSORS
    ]
    entities.append(WasserzaehlerDaily(coordinator, entry))
    async_add_entities(entities)


class WasserzaehlerSensor(CoordinatorEntity, SensorEntity):
    """Ein einzelner Wert aus der Add-on-Antwort."""

    entity_description: WzSensorDescription
    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: WasserzaehlerCoordinator,
        entry: ConfigEntry,
        description: WzSensorDescription,
    ) -> None:
        """Initialisieren."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Wasserzähler OCR",
            manufacturer="Eigenbau",
            model="ESP32-CAM + Ollama",
        )

    @property
    def native_value(self):
        """Aktuellen Wert aus den Coordinator-Daten holen."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self):
        """Zusatzinfos (Fehlergrund, letzter Wert, Plausibilitaet)."""
        data = self.coordinator.data or {}
        # Nur beim Status-Sensor die Details anhaengen - dort ist es nuetzlich
        if self.entity_description.key == "status":
            return {
                "error": data.get("error"),
                "plausible": data.get("plausible"),
                "last_value": data.get("last_value"),
                "rejected": data.get("rejected"),
                "held": data.get("held"),
            }
        return None
