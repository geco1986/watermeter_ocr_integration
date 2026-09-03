"""Binary-Sensor fuer die Wasserzaehler-OCR-Integration.

Ein 'Problem'-Melder, der anschlaegt, sobald der Status nicht 'ok' ist -
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
    """Binary-Sensor einrichten."""
    coordinator: WasserzaehlerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WasserzaehlerProblem(coordinator, entry)])


class WasserzaehlerProblem(CoordinatorEntity, BinarySensorEntity):
    """Meldet ein Problem, wenn der letzte Ablesevorgang nicht ok war."""

    _attr_name = "Wasserzähler Problem"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: WasserzaehlerCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialisieren."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_problem"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Wasserzähler OCR",
            manufacturer="Eigenbau",
            model="ESP32-CAM + Ollama",
        )

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
