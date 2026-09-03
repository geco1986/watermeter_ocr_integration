# Wasserzähler OCR – Home-Assistant-Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

Custom Integration, die die Werte des **Wasserzähler-OCR-Add-ons** als native
Home-Assistant-Entitäten bereitstellt: Zählerstand, Durchflussrate,
Tagesverbrauch, Fehlerzähler, Status – plus ein Eingabefeld zum manuellen
Korrigieren des Zählerstands.

> **Wichtig:** Das zugehörige **Add-on** muss separat installiert sein und
> laufen (eigenes Repository / Add-on-Store). Diese Integration liest nur
> dessen Werte aus.

## Vor dem Hochladen zu GitHub

Ersetze in `custom_components/wasserzaehler_ocr/manifest.json` den Platzhalter
`DEIN-USER` durch deinen echten GitHub-Benutzernamen (in `documentation`,
`issue_tracker` und `codeowners`).

## Installation über HACS

1. Dieses Repository zu GitHub hochladen (siehe unten).
2. In Home Assistant: HACS öffnen → oben rechts die drei Punkte →
   **Benutzerdefiniertes Repository hinzufügen**.
3. Die GitHub-URL deines Repos eintragen, als Kategorie **Integration** wählen.
4. Das Repo erscheint in HACS → **Herunterladen**.
5. Home Assistant neu starten.
6. Einstellungen → Geräte & Dienste → **Integration hinzufügen** →
   „Wasserzähler OCR" → die Add-on-URL (z. B. `http://192.168.3.10:5000`)
   und das Abfrageintervall eingeben.

> HACS zeigt benutzerdefinierte Repositories am besthbaren, wenn mindestens
> ein **Release/Tag** existiert. Nach dem Hochladen also in GitHub unter
> „Releases" ein Tag wie `v1.5.0` anlegen.

## Repository zu GitHub hochladen

```bash
cd wasserzaehler_ocr_integration_repo
git init
git add .
git commit -m "Initial commit: Wasserzähler OCR Integration v1.5.0"
git branch -M main
git remote add origin https://github.com/DEIN-USER/wasserzaehler_ocr.git
git push -u origin main
# danach in GitHub ein Release mit Tag v1.5.0 anlegen
```

## Entitäten

| Entität | Einheit | Zweck |
|---|---|---|
| Wasserzähler Stand | m³ | Zählerstand (`total_increasing`) |
| Wasserzähler Verbrauch heute | L | Tagesverbrauch, Reset um Mitternacht |
| Wasserzähler Durchfluss | L/min | aktuelle Durchflussrate |
| Wasserzähler Fehlerzähler | – | aufeinanderfolgende Fehler |
| Wasserzähler Status | – | „ok" oder Fehlertext |
| Wasserzähler Rohwert | – | erkannte Ziffernfolge |
| Wasserzähler Problem | on/off | Problem-Melder |
| Wasserzähler Stand setzen | m³ | Eingabefeld zur manuellen Korrektur |

Details zu Konfiguration und Diensten in
`custom_components/wasserzaehler_ocr/README.md`.

## Lizenz

MIT – siehe LICENSE.
