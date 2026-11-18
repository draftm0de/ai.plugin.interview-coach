# Interview Coach

[![Validate interview coach](https://github.com/draftm0de/ai.plugin.interview-coach/actions/workflows/validate.yml/badge.svg)](https://github.com/draftm0de/ai.plugin.interview-coach/actions/workflows/validate.yml)
[Deutsch](README.md) | [English](README.en.md)

<img src="docs/assets/zyris-icon.png" width="48" alt="ZYRIS-Dokumentationssymbol">

Übe Vorstellungsgespräche mit rollenbezogenen Fragen, konkretem Feedback und einem durch eigene Antworten belegten Lernstand – in Claude, ChatGPT oder Codex.

**[Installation](docs/de/installation.md) · [Nutzung](docs/de/usage.md) · [Beispiele](docs/de/screens.md) · [FAQ](docs/de/faq.md) · [Dokumentation](docs/de/README.md)**

**Installationsvorschau:** [Claude](docs/de/installation.md#claude-desktop) · [Claude Code](docs/de/installation.md#optionale-terminal-installation) · [Codex Desktop](docs/de/installation.md#codex-desktop). Marketplace: `https://github.com/draftm0de/ai.plugins`. Die Veröffentlichung des neuen Eintrags und die GUI-Abnahme stehen noch aus.

## Für wen ist das gedacht?

Für Bewerber, die sich auf eine konkrete Stelle vorbereiten, klarer antworten, ein realistisches Interview proben oder gezielt Schwächen trainieren möchten. Technische Rollen können Coding, Debugging, Code Review und Systemdesign üben.

Fragen und Kriterien richten sich nach Rolle und Erfahrungsniveau. Der Coach trennt eigene Antworten von Formulierungsvorschlägen und erfindet keine Berufserfahrung oder Erfolge.

## So sieht es aus

![Fiktiver Coaching-Ablauf mit erster Antwort, Überarbeitung und Stopp](docs/assets/de/coaching-preview.svg)

*Gerenderte Auszüge eines fiktiven Codex-CLI-Tests, kein Host-Screenshot. Noten bewerten einzelne Antworten und versprechen kein Ergebnis. [Herkunft und vollständiger Ablauf](docs/de/screens.md).*

1. Sprache, Trainingsziel und Speicherwahl festlegen.
2. Im begleiteten Modus jeweils eine Frage beantworten.
3. Gesamtbewertung, relevante Kriterien, Stärken und Verbesserungen erhalten.
4. In eigenen Worten erneut versuchen; eine Überarbeitung belegt noch keine stabile Kompetenz.
5. Mit `stop` jederzeit beenden.

## Funktionen und Modi

| Modus | Zweck | Beispiel |
|---|---|---|
| `general` | Allgemeines Training | „Übe Interviewfragen für eine Senior-Entwicklerrolle.“ |
| `targeted` | Konkrete Stelle und Arbeitgeber | „Nutze meinen Lebenslauf und diese Stellenanzeige.“ |
| `drill` | Einzelne Lernlücke | „Hilf mir, konkreter zu antworten.“ |
| `mock` | Ununterbrochene Simulation | „Gib Feedback erst am Ende.“ |
| `briefing` | Kompakte Vorbereitung | „Fasse die wichtigsten Fakten und Rückfragen zusammen.“ |

Recherche nutzt verfügbare öffentliche berufliche Quellen und kennzeichnet Unsicherheit. Arbeitgeber- und Interviewerrecherche braucht Browserzugriff. [Details](docs/de/usage.md).

## Schnellstart

Öffne die [Installationsanleitung](docs/de/installation.md) und wähle Claude oder Codex. Die öffentliche Katalogadresse ist noch nicht freigegeben; die Anleitung ist eine Vorschau. Nach Installation in einem neuen Chat das Plugin auswählen und die dort genannte erste Anfrage senden. Für diesen Nutzerweg ist kein Quellcheckout erforderlich.

## Nutzung

Nach der Installation:

> Nutze zyris-interview-coach und starte die Einrichtung. Ich möchte für eine Team-Lead-Rolle üben. Verwende Deutsch. Nicht speichern.

Für gezielte Vorbereitung stelle dein bestätigtes Profil und die Stellenanzeige privat bereit. Unbekannte Interviewer verhindern das Training nicht.

| Steuerung | Ergebnis |
|---|---|
| `stop` / `beenden` | Fragen sofort beenden und vorhandene Antworten zusammenfassen |
| `pause` | Fortsetzbaren Checkpoint bei bestätigtem Speicher anfordern |
| `Nicht speichern` | Keine Skill-Dateien, Arbeitsbereiche, Exporte oder gespeicherter Lernstand |

Im Modus `mock` erfolgt Feedback erst am Ende. Chat-Aufbewahrung wird separat vom Host geregelt.

## Speicherung und Datenschutz

Training funktioniert ohne Speicherung. Für Lernen über mehrere Sitzungen nutze einen separaten privaten Arbeitsbereich und einen geprüften Speicherzugang. Cloud-Sandbox oder Anhang garantieren keine Dauerhaftigkeit.

Die lokale CLI unterstützt den Adapter `local` mit `init`, `status`, `finish`, `resume`, `recover`, `validate` und Spracheinstellungen. Sie schützt unveränderliche Berichte, erkennt veraltete Zustände und unterstützt Wiederherstellung nach Teilfehlern. [Speicherung und Grenzen](docs/de/storage.md).

## Projektstatus

MVP mit versionslosen Plugin-Manifesten und Repository-Import über Draftmode AI Plugins. Lizenz: [MIT](LICENSE). Kein Kundenportal, Zahlungssystem oder Lizenzserver; eine Veröffentlichung in einem Plugin-Verzeichnis ist durch das Repository nicht belegt.

Lokale Speicherung und Paketierung besitzen deterministische Tests. CLI-Modellabläufe verwenden fiktive Daten und heuristische Prüfungen. Native Host-Abnahme bleibt separat; erfolgreiche Modelltests belegen weder Oberfläche noch Speicherintegration. Isolierte native CLI-Prüfungen sind im [Release-Nachweis](docs/de/release-evidence.md) dokumentiert; die GUI-Abnahme bleibt offen.

## Entwicklung

Website-Export aus denselben Quellen: `make check-docs-export` und `make export-docs`. Details stehen in der [Entwicklungsdokumentation](docs/de/development.md).

```bash
make test          # Deterministische Unit- und Regressionstests ohne Modellaufrufe
make check-plugin  # Versionslose Host-Manifeste prüfen
```

Alternativ nach Installation von pytest: `python3 -m pytest -q`. Python 3.10+ ist für Paketierung und lokalen Speicherhelfer erforderlich. [Entwicklung und Tests](docs/de/development.md).

Die [kanonische Skill-Quelle](skills/zyris-interview-coach/SKILL.md) definiert das Laufzeitverhalten. Nutzerdokumentation liegt unter [docs/de/](docs/de/README.md) und wird direkt auf GitHub dargestellt.

Herausgeber: **draftmode** · [draftmode.io](https://draftmode.io) · Autor: **Peter Fux**.

Dokumentation erstellt mit ZYRIS Skill Manager.
