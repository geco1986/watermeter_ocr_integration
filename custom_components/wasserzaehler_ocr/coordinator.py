"""DataUpdateCoordinator fuer einen einzelnen Zaehler.

Jeder Zaehler bekommt einen eigenen Coordinator, der periodisch
GET /process?id=<meter_id> aufruft. Dieser Aufruf loest im Add-on die
komplette Kette aus (Beleuchtung, Bild, OCR, Plausibilitaet) und liefert
ein JSON mit den Werten dieses Zaehlers.
"""

from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import PROCESS_PATH, REQUEST_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class MeterCoordinator(DataUpdateCoordinator):
    """Holt die Daten eines Zaehlers vom Add-on."""

    def __init__(
        self,
        hass: HomeAssistant,
        base_url: str,
        meter_id: str,
        name: str,
        scan_interval: int,
    ) -> None:
        """Initialisieren."""
        super().__init__(
            hass,
            _LOGGER,
            name=name,
            update_interval=timedelta(seconds=scan_interval),
        )
        self._base_url = base_url.rstrip("/")
        self._meter_id = meter_id
        self._session = async_get_clientsession(hass)

    async def _async_update_data(self) -> dict:
        """Einen Ablesevorgang ausloesen und das JSON zurueckgeben."""
        url = f"{self._base_url}{PROCESS_PATH}"
        # Leere meter_id => Legacy-Add-on ohne Mehr-Zaehler-Unterstuetzung.
        params = {"id": self._meter_id} if self._meter_id else None
        try:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            async with self._session.get(url, params=params, timeout=timeout) as resp:
                # Auch bei HTTP 422 (unplausibel/keine Ziffern) liefert das
                # Add-on ein gueltiges JSON mit status/error - das wollen wir.
                data = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Add-on nicht erreichbar: {err}") from err
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Fehler beim Abruf: {err}") from err

        if not isinstance(data, dict):
            raise UpdateFailed("Unerwartete Antwort vom Add-on (kein JSON-Objekt)")

        return data
