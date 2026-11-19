# Entwicklung und Prüfung

[Deutsch](./development.md) | [English](../en/development.md)

[Start](../../README.md) · [Dokumentation](README.md) · [Installation](installation.md) · [Nutzung](usage.md) · [Beispiele](screens.md) · [FAQ](faq.md) · [Speicherung](storage.md) · [Entwicklung](development.md)

## Kanonische Quelle

`skills/interview-coach/` enthält die Coaching-Laufzeit; Ordner und Skill-Kennung heißen jetzt `interview-coach`. `plugin.json` definiert das Plugin `interview-coach` mit Anzeigename **Interview Coach**. `make sync-plugin` leitet `.claude-plugin/plugin.json` und `.codex-plugin/plugin.json` ab; `make check-plugin` prüft Drift. Alle Manifeste bleiben versionslos. Der gemeinsame Marketplace liegt im separaten Repository `ai.plugins`; hier gibt es keinen eigenen Katalog.

Git und Python 3.10+ sind für Verwaltungswerkzeuge erforderlich; Make ist ein optionaler Komfortzugang. Keine zusätzlichen Python-Pakete. Die Host-CLI wird nur für automatische lokale Installation/Updates sowie ausdrücklich gewählte Modelltests benötigt. Der Speicherhelfer selbst benötigt Python 3.10+, aber kein Git. Fehlende Werkzeuge werden nicht automatisch installiert.

## Prüfungen

Die gemeinsame [Teststruktur](../../tests/README.md) ordnet zuerst nach Testart: `unit/`, `integration/`, `contracts/`, optional `behavior/` und `native/`. Skills oder Komponenten werden darunter eingeordnet; Daten und Helfer stehen unter `fixtures/` beziehungsweise `support/`.

`make test` führt nur Unit-, Integrations- und Vertragstests aus. Einzelbereiche: `make test-unit`, `make test-integration`, `make test-contracts`. `make test-native` und `make test-behavior` werden separat angefordert. Nicht vorhandene Suiten melden ausdrücklich `NOT RUN`; alte Native-Flags erweitern den normalen Testlauf nicht.

Führe im Repository-Stamm aus:

```bash
make test
make test-unit
make test-integration
make test-contracts
python3 -B scripts/run_tests.py --kind deterministic
```

Diese Prüfungen verwenden keine Modelle. Isolierte Funktionen stehen in `tests/unit/`, Dateisystem- und Ablaufprüfungen in `tests/integration/`, Skill- und Paketverträge in `tests/contracts/`.

### Optionale Modelltests

Mit authentifizierter Codex- oder Claude-Code-CLI und ausdrücklicher Auswahl:

```bash
make help
make test-list
make test-behavior CLI=codex
make test-behavior CLI=claude CASE=lead_feedback
make test-smoke CLI=codex
make test-journey CLI=codex
make test-journey CLI=claude
python3 tests/behavior/run.py --list
python3 tests/behavior/run.py --cli codex --output-dir .tmp/tests/behavior/codex
python3 tests/behavior/run.py --cli claude --output-dir .tmp/tests/behavior/claude
```

Diese Tests senden Skill-Text und fiktive Prompts an Modelle und können Credits verbrauchen. Sie prüfen Rollenbewertung, Feedback, Stopp ohne Speicherung und unbekannte Interviewer heuristisch. Ergebnisse müssen manuell geprüft werden. Sie lesen keine privaten Kandidaten-Arbeitsbereiche. Alle drei Runner trennen Modellantworten auf stdout von stderr-Diagnosen.

`teamlead_coaching` umfasst drei Szenarioantworten, eine eigene überarbeitete Antwort und `stop` ohne Speicherung. Jeder Schritt startet einen neuen Modellaufruf und spielt den bisherigen Dialog erneut ein: fünf Aufrufe, keine native Sitzungskontinuität und kein echter Persistenztest. Markdown wird für Prüfungen normalisiert; deutsche Textheuristiken können gültige alternative Formulierungen übersehen. Fehler zuerst als Produkt-, Runner- oder Szenarioproblem einordnen.

Ausgaben liegen ignoriert unter `.tmp/tests/behavior/<cli>/`, `.tmp/tests/smoke/<cli>/` und `.tmp/tests/journey/<cli>/<journey>/`. Journey-Artefakte enthalten Antwort, Diagnose pro Schritt und `result.json`. `OUT=.tmp/tests/behavior/custom` ändert den Behavior-Ausgabeort; deterministische Tests verwenden temporäre Verzeichnisse.


Native Abnahme bleibt separat: Installation, Auswahl, Berechtigungen, gespeicherte Stellenrecherche, Speichern am Ende und Wiederaufnahme im neuen Chat mit einem Wegwerf-Arbeitsbereich prüfen. CLI-Modelltests belegen diese Host-Funktionen nicht.

### Lokal über den gemeinsamen Marketplace

Verwende regulär die Manager-Aktion `configure` mit diesem Plugin-Checkout und dem gewählten Marketplace. Sie erhält andere Zuordnungen, setzt den lokalen Standard und prüft wirksame Ignore-Regeln vor dem Schreiben. `local-marketplace.example.json` ist nur eine optionale manuelle Kopiervorlage. Zur Laufzeit wird ausschließlich die Git-ignorierte `.local/marketplace.json` gelesen; lokale Zuordnungen niemals committen. `MARKETPLACE=/pfad/zu/ai.plugins` überschreibt den Standard für einen Aufruf.

Im Coach-Repository:

```sh
make install-local TARGET=claude
make update-local TARGET=codex
# Ohne Make:
python3 -B scripts/local_marketplace.py update-local --target codex
```

Beide Befehle delegieren an den konfigurierten Marketplace und erfassen alle zugeordneten lokalen Plugins im gemeinsamen Entwicklungskatalog `draftmode-ai-plugins-dev`. Fehlende benötigte Checkouts stoppen vor Host-Änderungen. `DRY_RUN=1` erstellt Snapshots ohne Host-Aufruf.

Snapshots verwenden den aktuellen Checkout einschließlich uncommitteter Änderungen, unabhängig vom Branch. Nach Änderungen oder Branchwechsel `update-local` ausführen und eine neue Host-Sitzung öffnen. Kein Commit, Push oder PR ist für lokale Tests erforderlich; keine zusätzlichen Marketplaces pro Branch.

`plugin-verify` im Manager prüft dieses Repository nur lesend. Eine gültige veröffentlichbare Struktur ist unabhängig von vollständiger lokaler Entwicklungskonfiguration: Fehlende Checkouts oder `.local`-Dateien sind auf einem frischen Clone erwartbar und werden als nicht verfügbare lokale Prüfung gemeldet.

## Paketierung

Repository-Import benötigt keine Plugin-ZIPs. `plugin.mk`, die alten Installationsskripte und die Tag-/Release-Werkzeuge sind entfernt. Tests prüfen die versionierten Manifeste und die unabhängig kopierte Coaching-Laufzeit. Lokale Entwicklung verwendet den gemeinsamen Marketplace `draftmode-ai-plugins-dev`.

## CI und Releases

Die [CI](../../.github/workflows/validate.yml) führt `make test` und `make check-plugin` aus. Modelltests bleiben optional. Bei neuen Katalogeinträgen zuerst dieses Plugin-Repository und anschließend den Eintrag in `ai.plugins` veröffentlichen. Bestehende Einträge benötigen bei einer reinen Plugin-Änderung keinen künstlichen Katalog-Commit. Tags oder GitHub Releases sind dafür nicht erforderlich. [Ablauf](release-operations.md) · [Prüfstand](release-evidence.md).

## Dokumentation pflegen

Deutsch: `README.md` und `docs/de/`; vollständiges Englisch: `README.en.md` und `docs/en/`. Beide Sprachfassungen beschreiben dieselben Befehle, Grenzen und Fakten. Gegenstücklinks, vorgegebene Überschriften und Medienherkunft erhalten. GitHub rendert Markdown direkt; keine zusätzliche Website, kein Wiki- oder Pages-Deployment nötig.

`docs/documentation.json` enthält Quellenzeiger und die Dokumentationssprachen dieses Repositories (`documentation.languages`: `de`, `en`; `default_language`: `de`). Produktfakten bleiben ausschließlich in ihren kanonischen Quellen. Quellen bei jeder Aktualisierung neu lesen. Die Aktion `update` (Plugin Manager) liest die Quellen erneut und aktualisiert README und Anleitungen; `update-local` aktualisiert dagegen lokale Plugin-Snapshots. Anschließend Dokumentationsvalidierung und Verify ausführen. Screenshots erst nach Prüfung auf private Inhalte ergänzen; siehe [Aufnahmecheckliste](screens.md).

Dokumentation erstellt mit Plugin Manager.


README und Anleitungen sind gepflegtes Markdown, keine bei jedem Build neu erzeugten Dateien. `update` (Plugin Manager) nutzt Quellen, Sprachkonfiguration und Vorlagen; der Agent formuliert die Inhalte. Die Strukturprüfung ersetzt keine inhaltliche Prüfung.

### Zielbild und Entwicklung

Das bestätigte Zielbild steht in [SCOPE.md](../../SCOPE.md), gemeinsame Entwicklungsregeln
in [AGENTS.md](../../AGENTS.md) und [Architektur](../architecture.md). CLAUDE.md verweist
auf dieselben Regeln. Source-/Testverweise sind keine Abnahme; Modellprüfungen bleiben
heuristisch. Der lesende Review führt weder Source noch Tests aus.

Runs ohne aktuelles Lifecycle-Format werden vor Schreibzugriffen abgelehnt und
bleiben unverändert. Bei Speicherfehlern die konkrete Diagnose beachten: Journal vorhanden →
recover; kein Auftrag aufgezeichnet → Schreibfehler beheben und gleiche Run-ID mit
ursprünglichem State-Hash erneut versuchen; Inhalte vorhanden ohne bestätigte finale
Dauerhaftigkeit → vorhandene Inhalte prüfen, nicht überschreiben.
