# Installation und Aktualisierung

[Deutsch](./installation.md) | [English](../en/installation.md)

[Start](../../README.md) · [Dokumentation](README.md) · [Installation](installation.md) · [Nutzung](usage.md) · [Beispiele](screens.md) · [FAQ](faq.md) · [Speicherung](storage.md) · [Entwicklung](development.md)

## Plattform auswählen

Du brauchst Python 3.10+, Bash und optional Make. Für native Installation muss die CLI des gewählten Hosts verfügbar sein. Führe Befehle im Repository-Stamm aus. Das Plugin bündelt den Coaching-Skill; es ist keine eigene Chat-Anwendung.

Offizielle Host-Anleitungen, geprüft am 18.11.2026: [Claude Code](https://code.claude.com/docs/en/plugins/install), [ChatGPT-Upload und Zugang](https://help.openai.com/en/articles/20001256-plugins-in-chatgpt), [OpenAI-Plugins](https://learn.chatgpt.com/docs/plugins). Verfügbarkeit und Berechtigungen hängen vom Konto ab. Diese Quellen belegen keine Abnahme dieses konkreten Pakets.

## Installieren

```bash
git clone https://github.com/draftm0de/zyris.skill.interview-coach.git
cd zyris.skill.interview-coach
```

| Aktion | Make | Gleichwertiger Bash-Befehl |
|---|---|---|
| Drei ZIPs und lokale Kataloge bauen | `make package` | `bash install.sh build` |
| Codex installieren | `make install TARGET=codex` | `bash install.sh install --target codex` |
| Claude Code installieren | `make install TARGET=claude` | `bash install.sh install --target claude` |
| Claude-Installation vorbereiten | `make install TARGET=claude DRY_RUN=1` | `bash install.sh install --target claude --dry-run` |
| ChatGPT-Upload vorbereiten | `make install TARGET=chatgpt` | `bash install.sh install --target chatgpt` |

Ein Dry Run baut Dateien und zeigt Befehle, ruft aber den Host nicht auf. ChatGPT-Befehle bauen immer nur; sie laden nichts hoch.

### Codex

Der Installer verwendet `codex plugin marketplace add` und `codex plugin add`. Der generierte Katalog liegt in `dist/codex-marketplace`, das Host-Manifest im Paket unter `.codex-plugin/plugin.json`. Öffne danach einen neuen Chat; starte Codex gegebenenfalls neu. Das Repository muss für spätere Updates verfügbar bleiben. Frühere Dokumentation nennt einen Test mit Codex CLI 0.165.0; dieser native Test wurde bei dieser Aktualisierung nicht wiederholt. Andere Plugins und private Arbeitsbereiche werden nicht entfernt.

### Claude Code

Der Helfer baut und registriert `dist/claude-marketplace` und installiert über die native Plugin-Verwaltung. Starte Claude Code neu und fordere die Einrichtung an. Bewahre den Checkout für Updates auf. Checkout und Host-Pakete verwenden denselben neutralen Laufzeitpfad `skills/zyris-interview-coach`. Die Host-Manifeste entstehen beim Build. Teste das installierte Plugin aus einem anderen Projekt, um das installierte Paket unabhängig vom Quellcheckout zu prüfen.

### Frühere Einzelinstallationen

`claude-chat`, `claude-plugin`, `all` und `--yes` sind eingestellt und liefern Migrationshinweise. `bash install.sh claude` installiert nun das Plugin, `bash install.sh chatgpt` bereitet den Upload vor, `bash install.sh codex` installiert nativ. Alte Skill-Kopien bleiben erhalten. Prüfe sie nach erfolgreicher Plugin-Installation auf Dopplungen und entferne sie bei Bedarf gesondert. Eine Installation gilt nur für den gewählten Host.

### ChatGPT

Lade `dist/zyris-interview-coach-chatgpt-plugin.zip` über die für dein Konto verfügbare Plugin-Verwaltung hoch und aktiviere das Plugin. Das Paket enthält den Skill und den Python-Helfer, keinen entfernten MCP-Speicherdienst. Ein gebautes ZIP belegt weder Host-Abnahme noch Speicherung über Chat-Grenzen hinweg.

## Aktualisieren

Erhalte lokale Änderungen, bevor du deinen Checkout aktualisierst. Wähle danach deinen Host:

| Host | Make | Bash |
|---|---|---|
| Codex | `make update TARGET=codex` | `bash install.sh update --target codex` |
| Claude Code | `make update TARGET=claude` | `bash install.sh update --target claude` |
| ChatGPT | `make update TARGET=chatgpt` | `bash install.sh update --target chatgpt` |

Codex baut und installiert die neue Inhaltsversion erneut. Claude benötigt eine vorherige Installation des lokalen Katalogs. Bei ChatGPT lädst du das neue ZIP manuell hoch. Prüfe Einrichtung und privaten Speicher in einer neuen Sitzung.

`plugin.json` enthält die Basisversion; Paketversionen erhalten einen deterministischen Inhaltshash. Die Befehle erstellen keinen Commit, pushen und veröffentlichen nichts. Automatische Marketplace-Updates werden durch dieses MVP nicht konfiguriert.

## Entfernen

Deaktiviere oder entferne das Plugin über die Plugin-Verwaltung des Hosts. Frühere Einzelkopien und die Projektquelle sind davon getrennt. Private Trainingsdaten und der lokale Konfigurationszeiger werden nicht gelöscht.

## Erste Nutzung prüfen

Starte die Einrichtung, bestätige deine Sprache und wähle **Nicht speichern**. Beantworte eine fiktive Frage, prüfe rollenbezogenes Feedback und beende mit `stop`. Siehe [Nutzung](usage.md) und [Beispiele](screens.md). Native Installation und vollständiger Host-Ablauf bleiben gesonderte Abnahmeprüfungen.
