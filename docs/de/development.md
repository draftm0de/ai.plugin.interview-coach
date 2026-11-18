# Entwicklung und Prüfung

[Deutsch](./development.md) | [English](../en/development.md)

[Start](../../README.md) · [Dokumentation](README.md) · [Installation](installation.md) · [Nutzung](usage.md) · [Beispiele](screens.md) · [FAQ](faq.md) · [Speicherung](storage.md) · [Entwicklung](development.md)

## Kanonische Quelle

Die [kanonische Quelle](../../skills/zyris-interview-coach/SKILL.md) liegt unter `skills/zyris-interview-coach/`, einschließlich Referenzen und `scripts/interview_workspace.py`. Nur diese Laufzeit wird ausgeliefert. Root-`scripts/` enthält den Build-Helfer `plugin.py`; Tests und Dokumentation sind Entwicklungsdateien.

`plugin.json` legt Identität, Basisversion, MIT-Lizenz und Distribution fest. `Makefile` bindet `plugin.mk` ein; dieses und `install.sh` delegieren an den gemeinsamen Helfer. Die drei Installer-Dateien sind abgeleitete Kopien der ZYRIS-Dokumentationsvorlagen. Änderungen zuerst an den Vorlagen vornehmen und geprüft übertragen; Verify erkennt Abweichungen.

Gemeinsame Ablageregeln: `.tmp/` entsteht erst für lokale Arbeitsdateien oder Diagnoseausgaben; `dist/` enthält erzeugte Pakete. `.DS_Store`, `.idea/`, Caches, Bytecode und Abhängigkeitsumgebungen werden ignoriert. Projektspezifische Ignore-Regeln und Diagnosen bleiben erhalten. Entwicklungswerkzeuge liegen in Root-`scripts/`, Laufzeit-Scripts beim jeweiligen Skill. Lokale Python-Imports sollen keinen Bytecode erzeugen; entpackte Pakete werden unabhängig vom Checkout getestet. Verify des Dokumentationsplugins prüft wirksame Ignore-Regeln, versionierte Ausgabedateien und statisch Python-Syntax/Imports im Paket; es führt keinen Zielcode aus und ersetzt keine Host-Abnahme.

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

`ZYRIS_TEST_CODEX_NATIVE=1 make test` aktiviert optional den echten Codex-Installations-, Wiederinstallations- und Update-Test in einem isolierten temporären Profil. Er wurde bei dieser Dokumentationsaktualisierung nicht ausgeführt.

Native Abnahme bleibt separat: Installation, Auswahl, Berechtigungen, gespeicherte Stellenrecherche, Speichern am Ende und Wiederaufnahme im neuen Chat mit einem Wegwerf-Arbeitsbereich prüfen. CLI-Modelltests belegen diese Host-Funktionen nicht.

## Paketierung

```bash
make check-plugin
make package
```

Es entstehen drei Plugin-ZIPs für ChatGPT, Claude und Codex sowie `dist/claude-marketplace` und `dist/codex-marketplace`. `package-chatgpt`, `package-claude-plugin` und `package-all` delegieren an denselben Builder; `package-claude-chat` endet mit einem Migrationshinweis. Die ältere Make-Hilfe „both“ ist überholt: Es werden drei ZIPs erzeugt.

Host-Manifeste und Paketversionen mit Inhaltshash werden abgeleitet. Keine separat gepflegten Host-Manifeste im Checkout. `LICENSE` wird mitgeliefert; Dokumentation und Tests werden nicht paketiert.

## CI und Releases

[GitHub Actions](../../.github/workflows/validate.yml) führt deterministische Tests, Manifestprüfung und Paketierung aus. Modelltests bleiben optional. Die Pfadfilter berücksichtigen auch Dokumentation, README-Dateien, Lizenz und Export-Makefile; die CI prüft und baut den Dokumentationsexport.

Ein lokaler Katalog oder ein ZIP veröffentlicht weder einen Verzeichniseintrag noch einen GitHub Release. Vor einer öffentlichen Einreichung sind tatsächliche Publisher-/Datenschutz-/Nutzungsmetadaten und Host-Abnahme erforderlich. Keine erfundenen rechtlichen URLs oder Veröffentlichungsbehauptungen.

## Dokumentation pflegen

### Export für die Website

`make check-docs-export` prüft den Vertrag; `make export-docs` erzeugt `dist/<plugin-name>-documentation.zip` mit `index.json`, unveränderten Markdown-Seiten und ausgewählten Assets. Die Konfiguration `export` in `docs/documentation.json` enthält ausschließlich Seiten- und Asset-Verweise. Produktmetadaten kommen aus `plugin.json`, Sprachen aus der bestehenden Dokumentationskonfiguration. Der Index ergänzt Linkzuordnungen, Prüfsummen und Git-Herkunft; lokale Änderungen werden kenntlich gemacht. Die Website übernimmt Routing und sichere Darstellung. Es wird nichts veröffentlicht.

Deutsch: `README.md` und `docs/de/`; vollständiges Englisch: `README.en.md` und `docs/en/`. Beide Sprachfassungen beschreiben dieselben Befehle, Grenzen und Fakten. Gegenstücklinks, vorgegebene Überschriften und Medienherkunft erhalten. GitHub rendert Markdown direkt; keine zusätzliche Website, kein Wiki- oder Pages-Deployment nötig.

`docs/documentation.json` enthält Quellenzeiger und die Dokumentationssprachen dieses Repositories (`documentation.languages`: `de`, `en`; `default_language`: `de`). Produktfakten bleiben ausschließlich in ihren kanonischen Quellen. Quellen bei jeder Aktualisierung neu lesen. Die installierte ZYRIS-Dokumentationsaktion aktualisiert Dokumentation; `make update` aktualisiert dagegen das installierte Coaching-Plugin. Anschließend Dokumentationsvalidierung und Verify ausführen. Screenshots erst nach Prüfung auf private Inhalte ergänzen; siehe [Aufnahmecheckliste](screens.md).

Dokumentation erstellt mit ZYRIS Skill Documentation.
