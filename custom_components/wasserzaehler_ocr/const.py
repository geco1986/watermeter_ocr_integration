"""Konstanten und Typ-Definitionen fuer die Zaehler-OCR-Integration.

Die Integration unterstuetzt mehrere Zaehler pro Add-on und drei Zaehlertypen:
Wasser, Strom und Waerme. Einheiten und Geraeteklassen richten sich nach dem
Typ und werden hier zentral definiert.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfPower,
    UnitOfVolume,
    UnitOfVolumeFlowRate,
)
from homeassistant.helpers.device_registry import DeviceInfo

DOMAIN = "wasserzaehler_ocr"

# Konfigurationsschluessel
CONF_URL = "url"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_TYPE_OVERRIDES = "type_overrides"  # {meter_id: type}

# Standardwerte
DEFAULT_URL = "http://homeassistant.local:5000"
DEFAULT_SCAN_INTERVAL = 300  # Sekunden; grosszuegig wegen langsamer CPU-OCR

# Add-on-Endpunkte
HEALTH_PATH = "/health"
METERS_PATH = "/meters"      # Liste aller Zaehler (Discovery)
PROCESS_PATH = "/process"    # ?id=<meter_id> loest eine Ablesung aus
SET_VALUE_PATH = "/set_value"  # POST {id, value}

# Timeouts
REQUEST_TIMEOUT = 240  # ganze OCR-Kette kann auf CPU lange dauern
QUICK_TIMEOUT = 15     # health / meters / set_value

# --- Zaehlertypen -----------------------------------------------------------

METER_WATER = "water"
METER_ELECTRICITY = "electricity"
METER_HEAT = "heat"
METER_TYPES = [METER_WATER, METER_ELECTRICITY, METER_HEAT]

# Pro Typ: Einheiten, Geraeteklassen, Anzeigenamen, Icons.
TYPE_CONFIG: dict[str, dict] = {
    METER_WATER: {
        "label": "Wasser",
        "total_unit": UnitOfVolume.CUBIC_METERS,
        "total_device_class": SensorDeviceClass.WATER,
        "total_icon": "mdi:water",
        "rate_unit": UnitOfVolumeFlowRate.LITERS_PER_MINUTE,
        "rate_device_class": SensorDeviceClass.VOLUME_FLOW_RATE,
        "rate_name": "Durchfluss",
        "rate_icon": "mdi:water-pump",
        "daily_unit": UnitOfVolume.LITERS,
        "daily_device_class": SensorDeviceClass.WATER,
        "daily_factor": 1000.0,   # m3 -> L
        "set_step": 0.001,
        "set_max": 999999,
        "device_icon": "mdi:water",
    },
    METER_ELECTRICITY: {
        "label": "Strom",
        "total_unit": UnitOfEnergy.KILO_WATT_HOUR,
        "total_device_class": SensorDeviceClass.ENERGY,
        "total_icon": "mdi:transmission-tower",
        "rate_unit": UnitOfPower.WATT,
        "rate_device_class": SensorDeviceClass.POWER,
        "rate_name": "Leistung",
        "rate_icon": "mdi:flash",
        "daily_unit": UnitOfEnergy.KILO_WATT_HOUR,
        "daily_device_class": SensorDeviceClass.ENERGY,
        "daily_factor": 1.0,
        "set_step": 0.001,
        "set_max": 9999999,
        "device_icon": "mdi:flash",
    },
    METER_HEAT: {
        "label": "Wärme",
        "total_unit": UnitOfEnergy.KILO_WATT_HOUR,
        "total_device_class": SensorDeviceClass.ENERGY,
        "total_icon": "mdi:radiator",
        "rate_unit": UnitOfPower.KILO_WATT,
        "rate_device_class": SensorDeviceClass.POWER,
        "rate_name": "Leistung",
        "rate_icon": "mdi:heat-wave",
        "daily_unit": UnitOfEnergy.KILO_WATT_HOUR,
        "daily_device_class": SensorDeviceClass.ENERGY,
        "daily_factor": 1.0,
        "set_step": 0.001,
        "set_max": 9999999,
        "device_icon": "mdi:radiator",
    },
}


def normalize_type(value: str | None) -> str:
    """Gibt einen gueltigen Typ zurueck (Fallback: Wasser)."""
    if value in TYPE_CONFIG:
        return value  # type: ignore[return-value]
    return METER_WATER


def meter_device_info(entry_id: str, meter_id: str, mtype: str, name: str) -> DeviceInfo:
    """Einheitliche Geraeteinfo fuer alle Entitaeten eines Zaehlers."""
    cfg = TYPE_CONFIG[normalize_type(mtype)]
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry_id}_{meter_id}")},
        name=name,
        manufacturer="OCR",
        model=f"{cfg['label']}-Zähler (OCR)",
    )
