# Wasserzähler OCR – Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Version](https://img.shields.io/badge/version-1.6.0-blue.svg)](https://github.com/geco1986/watermeter_ocr_integration/releases)

Liest deinen Wasserzähler automatisch aus einem Kamerabild aus und stellt die
Werte als native Home-Assistant-Entitäten bereit: **Zählerstand**,
**Tagesverbrauch**, **Durchflussrate**, **Status** und mehr – inklusive
Eingabefeld zum manuellen Korrigieren. Alles läuft lokal in deinem Netzwerk,
ganz ohne Cloud.

> [!IMPORTANT]
> Diese Integration liest nur die Werte aus. Das eigentliche Auslesen (Foto,
> Bildaufbereitung, Zeichenerkennung) übernimmt das separate
> **Wasserzähler-OCR-Add-on**, das installiert sein und laufen muss. Ohne das
> Add-on hat die Integration keine Datenquelle.

## Was du bekommst

Nach der Einrichtung erscheint ein Gerät **„Wasserzähler OCR"** mit diesen Entitäten:

| Entität | Einheit | Zweck |
|---|---|---|
| Wasserzähler Stand | m³ | aktueller Zählerstand – geeignet fürs Energie-Dashboard |
| Wasserzähler Verbrauch heute | L | Verbrauch des laufenden Tages, Reset um Mitternacht |
| Wasserzähler Durchfluss | L/min | aktuelle Durchflussrate |
| Wasserzähler Stand setzen | m³ | Eingabefeld zur manuellen Korrektur |
| Wasserzähler Status | – | „ok" oder Fehlertext |
| Wasserzähler Problem | on/off | schlägt an, sobald die Ablesung klemmt |
| Wasserzähler Fehlerzähler | – | Anzahl aufeinanderfolgender Fehler |
| Wasserzähler Rohwert | – | zuletzt erkannte Ziffernfolge |

## Voraussetzungen

- Home Assistant **2026.3.0** oder neuer
- [HACS](https://hacs.xyz) installiert
- Das **Wasserzähler-OCR-Add-on** läuft und ist über seine URL erreichbar
  (Standard-Port `5000`, z. B. `http://192.168.3.10:5000`)

## Installation

### 1. Integration über HACS herunterladen

1. In Home Assistant **HACS** öffnen.
2. Oben rechts auf das Drei-Punkte-Menü → **Benutzerdefinierte Repositories**.
3. Repository-URL eintragen:
   `https://github.com/geco1986/watermeter_ocr_integration`
   und als Typ **Integration** wählen, dann **Hinzufügen**.
4. Anschließend „Wasserzähler OCR" in HACS suchen und **Herunterladen**.
5. Home Assistant **neu starten**.

### 2. Integration hinzufügen

1. **Einstellungen → Geräte & Dienste → Integration hinzufügen**.
2. Nach **„Wasserzähler OCR"** suchen und auswählen.
3. Im Dialog eintragen:
   - **Add-on-URL** – die Adresse, unter der das Add-on läuft, z. B.
     `http://192.168.3.10:5000`
   - **Abfrageintervall** in Sekunden (Standard `300`)
4. Fertig – die Entitäten erscheinen automatisch am neuen Gerät.

## Das richtige Abfrageintervall

Jede Abfrage löst im Add-on die **komplette Auslesekette** aus (Beleuchtung an →
kurz warten → Foto → Zeichenerkennung). Je nach Erkennungsverfahren dauert das
einige Sekunden bis Minuten. Wähle das Intervall daher nicht zu kurz –
**300 Sekunden sind ein guter Startwert**. Später anpassbar über
**Konfigurieren** an der Integrationskachel.

## Zählerstand manuell korrigieren

Manchmal blockiert die Plausibilitätsprüfung des Add-ons einen echten großen
Sprung (z. B. nach einem Zählerwechsel). Dann kannst du den Stand von Hand
setzen – auf zwei Wegen:

**Bequem über die Gerätekarte:** die Entität **„Wasserzähler Stand setzen"**
öffnen, den korrekten Wert in m³ eintragen und bestätigen. Zeitstempel und
Fehlerzähler werden dabei zurückgesetzt, die Sensoren aktualisieren sich sofort.

**Per Aktion/Automation:** über den Dienst `wasserzaehler_ocr.set_value`, z. B.
als Dashboard-Knopf:

```yaml
type: button
name: Zählerstand korrigieren
tap_action:
  action: perform-action
  perform_action: wasserzaehler_ocr.set_value
  data:
    value: 1265.500
```

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

## Ins Energie-Dashboard einbinden

Der Sensor **„Wasserzähler Stand"** ist als `total_increasing` in m³ angelegt und
lässt sich direkt als Wasserquelle im **Energie-Dashboard** verwenden
(Einstellungen → Dashboards → Energie → Wasserverbrauch).

## Fehlerbehebung

- **„Add-on nicht erreichbar" bei der Einrichtung:** Prüfe die URL und ob das
  Add-on läuft. Öffne `http://<deine-adresse>:5000/health` im Browser – es sollte
  eine Statusantwort kommen.
- **Werte aktualisieren sich nicht:** Das Intervall greift erst nach Ablauf.
  Für einen sofortigen Test das Intervall kurz verringern oder den Stand einmal
  manuell setzen (löst eine sofortige Abfrage aus).
- **Sensor „Problem" ist an:** Sieh dir „Wasserzähler Status" und den
  „Fehlerzähler" an – dort steht der Grund (z. B. keine Ziffern erkannt,
  unplausibler Sprung).
- **In der HACS-Downloadliste erscheint statt des Icons ein Platzhalter:** Das
  ist ein bekannter Anzeigefehler von HACS. Auf der Integrationsseite und der
  Gerätekarte in Home Assistant wird das Icon korrekt angezeigt.

## Lizenz

MIT – siehe [LICENSE](LICENSE).
