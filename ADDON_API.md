# Add-on-Schnittstelle (HTTP-Contract)

Diese Datei beschreibt die HTTP-Endpunkte, die das **OCR-Add-on** bereitstellen
muss, damit die Integration mehrere Zähler erkennt und ausliest. Sie richtet
sich an Entwickler/Betreiber des Add-ons, nicht an Endnutzer.

Alle Endpunkte laufen unter der Add-on-URL (Standard-Port `5000`).

## `GET /health`

Erreichbarkeitsprüfung. Erwartet:

```json
{ "status": "ok" }
```

## `GET /meters`

Liefert die Liste der verfügbaren Zähler (Discovery). Wird beim Einrichten und
bei jedem Neuladen der Integration abgefragt.

```json
{
  "meters": [
    { "id": "garten",  "name": "Wasser Garten",  "type": "water" },
    { "id": "haus",    "name": "Strom Haus",     "type": "electricity" },
    { "id": "heizung", "name": "Wärme Heizung",  "type": "heat" }
  ]
}
```

- `id` – stabile, eindeutige Kennung des Zählers (wird in `/process` und
  `/set_value` verwendet). **Nicht ändern**, sonst entstehen neue Geräte.
- `name` – Anzeigename (wird zum Gerätenamen in Home Assistant).
- `type` – einer von `water`, `electricity`, `heat`. Wird in HA angezeigt und
  kann dort pro Zähler überschrieben werden. Fehlt der Wert, nimmt HA `water` an.

Eine reine Liste (`[ {…}, {…} ]`) ohne umschließendes `meters`-Objekt wird
ebenfalls akzeptiert.

> Fehlt der Endpunkt komplett, arbeitet die Integration im Kompatibilitätsmodus
> mit einem einzelnen Zähler und spricht `/process` und `/set_value` ohne `id`
> an (Verhalten wie vor Version 1.7.0).

## `GET /process?id=<meter_id>`

Löst für den angegebenen Zähler eine vollständige Ablesung aus (Beleuchtung,
Foto, OCR, Plausibilitätsprüfung) und liefert das Ergebnis. Dieser Aufruf darf
lange dauern; die Integration wartet bis zu 240 Sekunden.

```json
{
  "id": "garten",
  "type": "water",
  "value": 1265.5,
  "rate": 3.2,
  "status": "ok",
  "error": null,
  "error_count": 0,
  "raw_digits": "01265500",
  "plausible": true,
  "last_value": 1265.4,
  "rejected": false,
  "held": false
}
```

| Feld | Pflicht | Bedeutung |
|---|---|---|
| `value` | ja | Zählerstand in der Grundeinheit: **m³** (Wasser) bzw. **kWh** (Strom/Wärme) |
| `rate` | optional | Momentanwert in der Typ-Einheit: **L/min** (Wasser), **W** (Strom), **kW** (Wärme) |
| `status` | ja | `"ok"` oder ein Fehlertext |
| `error` | optional | Fehlerdetails, wenn `status` ≠ `ok` |
| `error_count` | optional | aufeinanderfolgende Fehlversuche |
| `raw_digits` | optional | erkannte Ziffernfolge (Diagnose) |
| `plausible`, `last_value`, `rejected`, `held` | optional | Diagnose-Details, werden als Attribute am Status-Sensor gezeigt |

Für Wasser wird als Momentanwert auch das Legacy-Feld `flow_rate_l_min`
akzeptiert, falls `rate` fehlt.

Auch bei einem unplausiblen/leeren Ergebnis sollte **HTTP 200 mit gültigem JSON**
(passendem `status`/`error`) geliefert werden – so kann HA den Grund anzeigen,
statt nur „nicht erreichbar".

## `POST /set_value`

Überschreibt den gespeicherten Zählerstand eines Zählers manuell.

Request-Body:

```json
{ "id": "garten", "value": 1265.500 }
```

Erfolgsantwort:

```json
{ "ok": true }
```

Fehlerantwort:

```json
{ "ok": false, "error": "Begründung" }
```

Nach dem Setzen sollten Zeitstempel neu gesetzt und der Fehlerzähler
zurückgesetzt werden. Die Integration fragt den Zähler danach sofort neu ab.
