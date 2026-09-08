# Zähler OCR – Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Version](https://img.shields.io/badge/version-1.7.1-blue.svg)](https://github.com/geco1986/watermeter_ocr_integration/releases)

Liest deine Zähler automatisch aus einem Kamerabild aus und stellt die Werte als
native Home-Assistant-Entitäten bereit. Unterstützt **mehrere Zähler
gleichzeitig** und vier Zählertypen – **Wasser, Strom, Wärme und Gas** – jeweils mit
den passenden Einheiten. Alles läuft lokal in deinem Netzwerk, ganz ohne Cloud.

> [!IMPORTANT]
> Diese Integration liest nur die Werte aus. Das eigentliche Auslesen (Foto,
> Bildaufbereitung, Zeichenerkennung) übernimmt das separate **OCR-Add-on**,
> das installiert sein und laufen muss. Ein Add-on kann mehrere Zähler
> bedienen; die Integration erkennt sie automatisch.

## Unterstützte Zählertypen

| Typ | Zählerstand | Momentanwert | Tagesverbrauch |
|---|---|---|---|
| **Wasser** | m³ | Durchfluss in L/min | Liter |
| **Strom** | kWh | Leistung in W | kWh |
| **Wärme** | kWh | Leistung in kW | kWh |
| **Gas** | m³ | Durchfluss in m³/h | m³ |

Der Typ wird vom Add-on gemeldet und kann in Home Assistant pro Zähler
überschrieben werden, falls er einmal nicht passt.

## Was du je Zähler bekommst

Für jeden erkannten Zähler entsteht ein eigenes **Gerät** mit diesen Entitäten:

| Entität | Zweck |
|---|---|
| Zählerstand | aktueller Stand (`total_increasing`) – geeignet fürs Energie-Dashboard |
| Verbrauch heute | Verbrauch des laufenden Tages, Reset um Mitternacht |
| Durchfluss / Leistung | aktueller Momentanwert (je nach Typ) |
| Stand setzen | Eingabefeld zur manuellen Korrektur |
| Status | „ok" oder Fehlertext |
| Problem | schlägt an, sobald die Ablesung klemmt |
| Fehlerzähler | Anzahl aufeinanderfolgender Fehler |
| Rohwert | zuletzt erkannte Ziffernfolge |

## Voraussetzungen

- Home Assistant **2026.3.0** oder neuer
- [HACS](https://hacs.xyz) installiert
- Das **OCR-Add-on** läuft und ist über seine URL erreichbar
  (Standard-Port `5000`, z. B. `http://192.168.3.10:5000`)

## Installation

### 1. Integration über HACS herunterladen

1. In Home Assistant **HACS** öffnen.
2. Oben rechts auf das Drei-Punkte-Menü → **Benutzerdefinierte Repositories**.
3. Repository-URL eintragen:
   `https://github.com/geco1986/watermeter_ocr_integration`
   und als Typ **Integration** wählen, dann **Hinzufügen**.
4. Anschließend „Zähler OCR" in HACS suchen und **Herunterladen**.
5. Home Assistant **neu starten**.

### 2. Integration hinzufügen

1. **Einstellungen → Geräte & Dienste → Integration hinzufügen**.
2. Nach **„Zähler OCR"** suchen und auswählen.
3. Im Dialog die **Add-on-URL** (z. B. `http://192.168.3.10:5000`) und das
   **Abfrageintervall** eintragen (Standard `300` s, gilt pro Zähler).
4. Fertig – alle Zähler des Add-ons werden automatisch erkannt und als eigene
   Geräte angelegt.

Läuft dein Add-on auf mehreren Adressen (z. B. an verschiedenen Standorten),
kannst du die Integration einfach **mehrfach** mit unterschiedlichen URLs
hinzufügen.

## Zählertyp oder Intervall nachträglich ändern

Über **Konfigurieren** an der Integrationskachel lässt sich das Abfrageintervall
anpassen und für jeden Zähler der Typ (Wasser/Strom/Wärme) überschreiben.

## Das richtige Abfrageintervall

Jede Abfrage löst im Add-on die **komplette Auslesekette** aus (Beleuchtung an →
kurz warten → Foto → Zeichenerkennung) – und zwar pro Zähler. Wähle das Intervall
daher nicht zu kurz; **300 Sekunden sind ein guter Startwert**. Jeder Zähler wird
unabhängig abgefragt, sodass ein langsamer Zähler die anderen nicht ausbremst.

## Zählerstand manuell korrigieren

Blockiert die Plausibilitätsprüfung des Add-ons einen echten großen Sprung
(z. B. nach einem Zählerwechsel), kannst du den Stand von Hand setzen:

**Über die Gerätekarte:** die Entität **„Stand setzen"** des jeweiligen Zählers
öffnen, den korrekten Wert eintragen und bestätigen.

**Per Aktion/Automation:** über den Dienst `wasserzaehler_ocr.set_value`. Bei
mehreren Zählern die `meter_id` mit angeben:

```yaml
type: button
name: Zählerstand Garten korrigieren
tap_action:
  action: perform-action
  perform_action: wasserzaehler_ocr.set_value
  data:
    meter_id: garten
    value: 1265.500
```

## Beispiel-Automation

Benachrichtigung, wenn ein Zähler dauerhaft klemmt:

```yaml
automation:
  - alias: "Zähler Ablesefehler melden"
    trigger:
      - platform: state
        entity_id: binary_sensor.strom_haus_problem
        to: "on"
        for: "00:30:00"
    action:
      - service: notify.persistent_notification
        data:
          title: "Zähler"
          message: >
            Ablesung klemmt. Status:
            {{ state_attr('binary_sensor.strom_haus_problem', 'status') }}
```

## Ins Energie-Dashboard einbinden

Der Sensor **„Zählerstand"** ist `total_increasing` mit passender Geräteklasse
(Wasser bzw. Energie) und lässt sich direkt im **Energie-Dashboard** als Quelle
verwenden (Wasserverbrauch bzw. Stromnetz/Wärme).

## Fehlerbehebung

- **„Add-on nicht erreichbar" bei der Einrichtung:** URL prüfen und ob das Add-on
  läuft. Rufe `http://<deine-adresse>:5000/health` im Browser auf – es sollte eine
  Statusantwort kommen.
- **Es wird nur ein Zähler angelegt, obwohl mehrere vorhanden sind:** Dann liefert
  dein Add-on (noch) keine Zählerliste. Details zur erwarteten Schnittstelle
  stehen in [`ADDON_API.md`](ADDON_API.md).
- **Falscher Typ/Einheit bei einem Zähler:** unter *Konfigurieren* den Typ dieses
  Zählers überschreiben.
- **Werte aktualisieren sich nicht:** Das Intervall greift erst nach Ablauf. Zum
  Testen das Intervall kurz verringern oder den Stand einmal manuell setzen.
- **In der HACS-Downloadliste erscheint statt des Icons ein Platzhalter:** bekannter
  Anzeigefehler von HACS. In Home Assistant selbst wird das Icon korrekt angezeigt.

## Lizenz

MIT – siehe [LICENSE](LICENSE).
