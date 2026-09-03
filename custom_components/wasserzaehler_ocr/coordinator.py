"""DataUpdateCoordinator fuer die Wasserzaehler-OCR-Integration.

Ruft periodisch den /process-Endpunkt des Add-ons auf. Dieser Aufruf loest
die komplette Kette aus (Lampe an, warten, Bild holen, rotieren, OCR,
Plausibilitaet) und liefert ein JSON mit allen Werten.
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


class WasserzaehlerCoordinator(DataUpdateCoordinator):
    """Holt die Wasserzaehler-Daten vom Add-on."""

    def __init__(
        self,
        hass: HomeAssistant,
        base_url: str,
        scan_interval: int,
    ) -> None:
        """Initialisieren."""
        super().__init__(
            hass,
            _LOGGER,
            name="Wasserzähler OCR",
            update_interval=timedelta(seconds=scan_interval),
        )
        self._base_url = base_url.rstrip("/")
        self._session = async_get_clientsession(hass)

    async def _async_update_data(self) -> dict:
        """Einen Ablesevorgang ausloesen und das JSON zurueckgeben."""
        url = f"{self._base_url}{PROCESS_PATH}"
        try:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            async with self._session.get(url, timeout=timeout) as resp:
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
