"""Konstanten fuer die Wasserzaehler-OCR-Integration."""

DOMAIN = "wasserzaehler_ocr"

# Konfigurationsschluessel
CONF_URL = "url"
CONF_SCAN_INTERVAL = "scan_interval"

# Standardwerte
DEFAULT_URL = "http://homeassistant.local:5000"
DEFAULT_SCAN_INTERVAL = 300  # Sekunden; grosszuegig wegen langsamer CPU-OCR

# Der Endpunkt des Add-ons, der die ganze Kette ausloest
PROCESS_PATH = "/process"

# Timeout fuer eine Anfrage - muss laenger sein als die gesamte Kette
# (Lampe an + 10s warten + Bild + OCR). Auf CPU kann OCR lange dauern.
REQUEST_TIMEOUT = 240
