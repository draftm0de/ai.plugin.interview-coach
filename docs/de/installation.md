# Installation und Aktualisierung

[Deutsch](./installation.md) | [English](../en/installation.md)

[Start](../../README.md) · [Dokumentation](README.md) · [Installation](installation.md) · [Nutzung](usage.md) · [Beispiele](screens.md) · [FAQ](faq.md) · [Speicherung](storage.md) · [Entwicklung](development.md)

## Plattform auswählen

Dieses Repository enthält **Interview Coach** (`interview-coach`) mit fünf Skills (`interview-coach`, `candidate-create`, `candidate-training`, `job-create`, `job-training`) und gemeinsamer Runtime unter `skills/_shared/`; es besitzt keinen eigenen Marketplace. Unterstützte Hosts: **Claude Code** und **Codex**. Installationsquelle ist **Draftmode AI Plugins** (`draftmode-ai-plugins`): `https://github.com/draftm0de/ai.plugins`. Ob die aktuelle Erweiterung dort veröffentlicht ist, ist nicht belegt; ein Repository-Import liefert den veröffentlichten Stand.

Voraussetzungen: Python 3.10+ für die Runtime; Git nur für den Git-Speicher (optional `gh`/`glab` zur Sichtbarkeitsprüfung); für PDF-Import `pdftotext`, `mutool` oder Python-`pypdf`. **Es wird nichts automatisch installiert**; fehlt etwas, nennt der Coach genau, was fehlt.

## Installieren

### Claude Code

In einer Claude-Code-Sitzung:

```text
/plugin marketplace add https://github.com/draftm0de/ai.plugins
/plugin install interview-coach@draftmode-ai-plugins
```

Danach neue Sitzung öffnen. Einstieg: `/interview-coach:interview-coach setup` oder natürliche Sprache. Die weiteren Skills heißen `/interview-coach:candidate-create`, `…:candidate-training`, `…:job-create`, `…:job-training`. Claude Code findet sie als Verzeichnisse `skills/*/SKILL.md` im Plugin; `skills/_shared/` enthält keinen Skill. Der Claude-Desktop-Dialog (Einstellungen → Anpassungen → Plugins → Marketplace aus Repository hinzufügen) führt zum selben Marketplace; seine Abnahme ist nur teilweise belegt ([Beispiele](screens.md)).

### Codex

```sh
codex plugin marketplace add https://github.com/draftm0de/ai.plugins
codex plugin add interview-coach@draftmode-ai-plugins
```

In Codex Desktop: Settings → Plugins → Marketplace hinzufügen → Interview Coach installieren. Das Manifest verweist auf `./skills/`; Einstieg per Skill-Erwähnung `$interview-coach` (Skills: `$candidate-create`, `$candidate-training`, `$job-create`, `$job-training`) oder natürliche Sprache.

Die genauen Aufrufschreibweisen richten sich nach der jeweiligen Host-Version und sind in diesem Repository nicht durch einen isolierten Host-Lauf belegt ([Abnahme](../acceptance.md)). Kein ZIP, Tag oder eigener Katalog ist erforderlich.

## Aktualisieren

Synchronisiere den gemeinsamen Marketplace in der Plugin-Verwaltung und öffne eine neue Sitzung. Die Manifeste enthalten keine Versionsbindung. Ein Push allein belegt keine erfolgreiche Aktualisierung beim Nutzer.

## Entfernen

Entferne **Interview Coach** in der Plugin-Verwaltung. Private Trainingsdaten außerhalb der Installation bleiben erhalten. Entferne nicht den gesamten Marketplace, wenn du den Plugin Manager weiter nutzen möchtest.

## Erste Nutzung prüfen

Öffne eine neue Sitzung und sende **„Starte die Einrichtung von interview-coach“**. Wähle Deutsch und **Nicht speichern**, übe mit einer fiktiven Frage und beende mit `stop`. Dauerhafte Speicherung (Lokal oder privates Git) benötigt ein Ziel, das du ausdrücklich bestätigst; siehe [Speicherung](storage.md). Internetrecherche benötigt Internetzugang.

Prüfe beim Marketplace-Test, dass **Plugin Manager** und **Interview Coach** angeboten werden. [Entwicklung](development.md) · [Prüfstand](release-evidence.md).

Die Menüpunkte beruhen auf vorhandenen Nutzerangaben und Aufnahmen, nicht auf einer neuen GUI-Abnahme. CLI-Befehle wurden mit der lokalen Hilfe abgeglichen. [Claude-Code-Anleitung](https://code.claude.com/docs/en/discover-plugins) · [OpenAI-Plugin-Dokumentation](https://developers.openai.com/plugins/build/plugins).
