# Entwicklung und Prüfung

[Deutsch](./development.md) | [English](../en/development.md)

[Start](../../README.md) · [Dokumentation](README.md) · [Installation](installation.md) · [Nutzung](usage.md) · [Beispiele](screens.md) · [FAQ](faq.md) · [Speicherung](storage.md) · [Entwicklung](development.md)

## Kanonische Quelle

`skills/zyris-interview-coach/` enthält unverändert die Coaching-Laufzeit. `plugin.json` definiert das Plugin `interview-coach` mit Anzeigename **Interview Coach**. `make sync-plugin` leitet `.claude-plugin/plugin.json` und `.codex-plugin/plugin.json` ab; `make check-plugin` prüft Drift. Alle Manifeste bleiben versionslos. Der gemeinsame Marketplace liegt im separaten Repository `ai.plugins`; hier gibt es keinen eigenen Katalog.

## Prüfungen

Führe im Repository-Stamm aus:

```bash
make test
make test-unit
make test-regression
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Diese Prüfungen verwenden keine Modelle. Alternativ nach Installation von pytest: `python3 -m pytest -q`. Quellbezogene Unit-Tests stehen in `tests/unit/`, Vertrags- und Ablaufregressionen in `tests/regression/`.

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

## Paketierung

Repository-Import benötigt keine Plugin-ZIPs. `plugin.mk`, die alten Installationsskripte und die Tag-/Release-Werkzeuge sind entfernt. Tests prüfen die versionierten Manifeste und die unabhängig kopierte Coaching-Laufzeit. Lokale Entwicklung verwendet den gemeinsamen Marketplace `draftmode-ai-plugins-dev`.

## CI und Releases

Die [CI](../../.github/workflows/validate.yml) führt `make test`, `make check-plugin` und die Website-Exportprüfung aus. Modelltests bleiben optional. Veröffentliche zuerst dieses Plugin-Repository und anschließend den neuen Eintrag in `ai.plugins`. Tags oder GitHub Releases sind dafür nicht erforderlich. [Ablauf](release-operations.md) · [Prüfstand](release-evidence.md).

## Dokumentation pflegen

### Export für die Website

`make check-docs-export` prüft den Vertrag; `make export-docs` erzeugt `dist/<plugin-name>-documentation.zip` mit `index.json`, unveränderten Markdown-Seiten und ausgewählten Assets. Die Konfiguration `export` in `docs/documentation.json` enthält ausschließlich Seiten- und Asset-Verweise. Produktmetadaten kommen aus `plugin.json`, Sprachen aus der bestehenden Dokumentationskonfiguration. Der Index ergänzt Linkzuordnungen, Prüfsummen und Git-Herkunft; lokale Änderungen werden kenntlich gemacht. Die Website übernimmt Routing und sichere Darstellung. Es wird nichts veröffentlicht.

Deutsch: `README.md` und `docs/de/`; vollständiges Englisch: `README.en.md` und `docs/en/`. Beide Sprachfassungen beschreiben dieselben Befehle, Grenzen und Fakten. Gegenstücklinks, vorgegebene Überschriften und Medienherkunft erhalten. GitHub rendert Markdown direkt; keine zusätzliche Website, kein Wiki- oder Pages-Deployment nötig.

`docs/documentation.json` enthält Quellenzeiger und die Dokumentationssprachen dieses Repositories (`documentation.languages`: `de`, `en`; `default_language`: `de`). Produktfakten bleiben ausschließlich in ihren kanonischen Quellen. Quellen bei jeder Aktualisierung neu lesen. Die installierte ZYRIS-Dokumentationsaktion aktualisiert Dokumentation; Plugin-Updates erfolgen über den gemeinsamen Marketplace. Anschließend Dokumentationsvalidierung und Verify ausführen. Screenshots erst nach Prüfung auf private Inhalte ergänzen; siehe [Aufnahmecheckliste](screens.md).

Dokumentation erstellt mit ZYRIS Skill Manager.

### Lokal über den gemeinsamen Marketplace

Die Zuordnung auf diesem Rechner steht bereits in der Git-ignorierten `.local/marketplace.json`. Für einen neuen Rechner `local-marketplace.example.json` dorthin kopieren und den Pfad zu `ai.plugins` anpassen. Dort muss `.local/marketplace.json` unter `sources.interview-coach` auf diesen Checkout zeigen. Alternativ lässt sich der Marketplace-Pfad mit `MARKETPLACE=/pfad/zu/ai.plugins` übergeben.

```sh
make install-local TARGET=claude
# oder TARGET=codex
make update-local TARGET=claude
```

Beide Befehle delegieren an `ai.plugins` und umfassen Manager und Coach im selben Entwicklungs-Katalog. Kein eigener Katalog und kein ZIP wird hier erstellt. `DRY_RUN=1` erstellt die gemeinsamen Snapshots ohne Host-Aufruf. Neue lokale Sitzung öffnen und nur die gewünschte Entwicklungskopie aktivieren. Die Prüfung erfolgt im Manager mit `plugin-verify` auf diesen Repository-Pfad; sie verändert keine Dateien.
