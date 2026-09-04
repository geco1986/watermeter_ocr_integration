# Wasserzähler OCR – Home-Assistant-Integration (Custom Component)

Diese Integration bindet die Werte des **Wasserzähler-OCR-Add-ons** als native
Home-Assistant-Entitäten ein – ohne REST-Sensoren in der
`configuration.yaml`. Einrichtung per Klick über die HA-Oberfläche.

Voraussetzung: Das Add-on „Wasserzähler Rotate & OCR" läuft bereits und ist
über seine URL (Port 5000) erreichbar.

## Was sie erstellt

Ein Gerät „Wasserzähler OCR" mit diesen Entitäten:

| Entität | Einheit | Zweck |
|---|---|---|
| Wasserzähler Stand | m³ | Zählerstand, `total_increasing` – fürs Energie-Dashboard |
| Wasserzähler Durchfluss | L/min | aktuelle Durchflussrate |
| Wasserzähler Fehlerzähler | – | aufeinanderfolgende Fehler (Diagnose) |
| Wasserzähler Status | – | „ok" oder Fehlertext (Diagnose) |
| Wasserzähler Rohwert | – | erkannte Ziffernfolge (Diagnose) |
| Wasserzähler Problem | on/off | Problem-Melder, sobald Status ≠ ok |

## Installation

1. Ordner `wasserzaehler_ocr` nach `/config/custom_components/` kopieren, also
   `/config/custom_components/wasserzaehler_ocr/…`.
2. Home Assistant neu starten.
3. Einstellungen → Geräte & Dienste → **Integration hinzufügen** → nach
   „Wasserzähler OCR" suchen.
4. Im Dialog die **Add-on-URL** eintragen, z. B. `http://192.168.3.10:5000`
   (die IP deines HA-Hosts, unter der das Add-on läuft) und das
   **Abfrageintervall** wählen (Standard 300 s).

Nach dem Anlegen tauchen die Entitäten automatisch auf. Das Intervall lässt
sich später über „Konfigurieren" bei der Integration anpassen.

## Wichtig zum Intervall

Jede Abfrage löst die **komplette Kette** im Add-on aus (Lampe an → 10 s
warten → Bild → OCR). Auf CPU kann OCR je nach Modell zweistellige Sekunden
bis Minuten dauern. Wähle das Intervall daher nicht zu kurz – 300 s ist ein
guter Startwert. Der Anfrage-Timeout der Integration liegt bei 240 s.

## Verhältnis zu den REST-Sensoren

Diese Integration **ersetzt** die REST-Sensoren aus der Add-on-README. Nutze
entweder die REST-Sensoren *oder* diese Integration, nicht beides parallel für
dieselben Werte (sonst löst du die Ablese-Kette doppelt aus).

## Beispiel-Automation

Benachrichtigung, wenn die Ablesung dauerhaft klemmt:

```yaml
automation:
  - alias: "Wasserzähler Ablesefehler melden"
    trigger:
      - platform: numeric_state
        entity_id: sensor.wasserzahler_fehlerzahler
        above: 3
    action:
      - service: notify.persistent_notification
        data:
          title: "Wasserzähler"
          message: >
            Ablesung klemmt seit {{ states('sensor.wasserzahler_fehlerzahler') }}
            Versuchen. Status: {{ states('sensor.wasserzahler_status') }}
```

## Icon / Logo

Das Wassertropfen-Icon liegt im Ordner `brand/` (icon.png, logo.png und die
@2x-Varianten). Seit Home Assistant 2026.3 werden diese lokalen Bilder
automatisch angezeigt – auf der Integrationsseite und der Gerätekarte, ohne
weitere Konfiguration.

## Dienst: Zählerstand setzen

Die Integration stellt den Dienst `wasserzaehler_ocr.set_value` bereit. Damit
überschreibst du den gespeicherten Zählerstand manuell – nützlich, wenn ein
echter großer Sprung von der Plausibilitätsprüfung blockiert wurde.

Aufruf über Entwicklerwerkzeuge → Aktionen → „Wasserzähler OCR: Zählerstand
setzen", Wert in m³ eingeben. Der Zeitstempel wird auf jetzt gesetzt, der
Fehlerzähler zurückgesetzt, und die Sensoren aktualisieren sich sofort.

Beispiel für einen Dashboard-Knopf:

```yaml
type: button
name: Zählerstand korrigieren
tap_action:
  action: perform-action
  perform_action: wasserzaehler_ocr.set_value
  data:
    value: 1265.500
```

## Änderungen

**1.6.0**

- Marken-Icon und -Logo sind jetzt direkt in der Integration enthalten
  (Ordner `brand/`). Ab Home Assistant 2026.3 werden sie automatisch auf der
  Integrationsseite und der Gerätekarte angezeigt – ohne weitere Einrichtung.

**1.5.0**

- **Wasserzähler Stand setzen** (Number-Eingabefeld) – direkt auf der
  Gerätekarte. Trage den korrekten m³-Wert ein und bestätige; das
  überschreibt den gespeicherten Zählerstand (Zeitstempel neu, Fehlerzähler
  zurückgesetzt). Praktisch, wenn ein legitimer großer Sprung blockiert wurde.
  Das ist der einfachste Weg statt des `set_value`-Dienstes.
- **Wasserzähler Verbrauch heute** (Sensor, Liter) – Wasserverbrauch des
  aktuellen Tages. Setzt sich um Mitternacht automatisch zurück und übersteht
  Neustarts. Als `total_increasing` auch fürs Energie-Dashboard geeignet.
