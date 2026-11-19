# Installation und Aktualisierung

[Deutsch](./installation.md) | [English](../en/installation.md)

[Start](../../README.md) · [Dokumentation](README.md) · [Installation](installation.md) · [Nutzung](usage.md) · [Beispiele](screens.md) · [FAQ](faq.md) · [Speicherung](storage.md) · [Entwicklung](development.md)

## Plattform auswählen

Dieses Repository enthält **Interview Coach** (`interview-coach`), keinen eigenen Marketplace. Die enthaltene Skill-Kennung lautet ebenfalls `interview-coach`. Installationsquelle ist **Draftmode AI Plugins** (`draftmode-ai-plugins`): `https://github.com/draftm0de/ai.plugins`.

Laut Nutzer sind beide Plugins im veröffentlichten Marketplace vorhanden. Die lokale Umbenennung des Skills zu `interview-coach` ist noch nicht veröffentlicht; ein Repository-Import liefert den veröffentlichten Stand. Die GUI-Abnahme der aktuellen Änderungen bleibt separat. Dein Account benötigt Zugriff auf beide Repositories.

## Installieren

### Claude Desktop

1. Öffne **Einstellungen → Anpassungen → Plugins**.
2. Wähle **+ Hinzufügen → Marketplace hinzufügen → Aus einem Repository hinzufügen**.
3. Gib `https://github.com/draftm0de/ai.plugins` ein und klicke **Synchronisieren**.
4. Wähle **Interview Coach** und installiere das Plugin.

### Codex Desktop

1. Öffne **User Icon → Settings → Integration → Plugins**.
2. Wähle **+ Add → A Marketplace**.
3. Gib `https://github.com/draftm0de/ai.plugins` ein und synchronisiere den Marketplace.
4. Wähle **Interview Coach** und installiere das Plugin.

### Optionale Terminal-Installation

In einer Claude-Code-Terminal-Sitzung, nicht im Eingabefeld des Desktop-Code-Reiters:

```text
/plugin marketplace add https://github.com/draftm0de/ai.plugins
/plugin install interview-coach@draftmode-ai-plugins
```

Für Codex CLI:

```sh
codex plugin marketplace add https://github.com/draftm0de/ai.plugins
codex plugin add interview-coach@draftmode-ai-plugins
```

Die technische Plugin-Kennung ist `interview-coach`; angezeigt wird **Interview Coach**. Kein ZIP, Tag oder eigener Katalog ist erforderlich. ChatGPT-Kontoimporte und Organisationsfreigaben sind separat zu prüfen.

## Aktualisieren

Synchronisiere den gemeinsamen Marketplace in der Plugin-Verwaltung und öffne eine neue Sitzung. Die Manifeste enthalten keine Versionsbindung. Ein Push allein belegt keine erfolgreiche Aktualisierung beim Nutzer.

## Entfernen

Entferne **Interview Coach** in der Plugin-Verwaltung. Private Trainingsdaten außerhalb der Installation bleiben erhalten. Entferne nicht den gesamten Marketplace, wenn du den Plugin Manager weiter nutzen möchtest.

## Erste Nutzung prüfen

Öffne einen neuen Chat und sende **„Start interview coach setup“**. Wähle Deutsch und **Nicht speichern**, übe mit einer fiktiven Frage und beende mit `stop`. Dauerhafte Speicherung benötigt einen freigegebenen privaten Arbeitsbereich und eine passende Python-Laufzeit im Host; siehe [Speicherung](storage.md). Internetrecherche benötigt Internetzugang.

Prüfe beim Marketplace-Test, dass **Plugin Manager** und **Interview Coach** angeboten werden. [Entwicklung](development.md) · [Prüfstand](release-evidence.md).

Die Menüpunkte beruhen auf vorhandenen Nutzerangaben und Aufnahmen, nicht auf einer neuen GUI-Abnahme. CLI-Befehle wurden mit der lokalen Hilfe abgeglichen. [Claude-Code-Anleitung](https://code.claude.com/docs/en/discover-plugins) · [OpenAI-Plugin-Dokumentation](https://developers.openai.com/plugins/build/plugins).
