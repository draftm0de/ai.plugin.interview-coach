# Teststruktur / Test structure

Tests sind zuerst nach Testart, darunter bei Bedarf nach Skill oder Komponente geordnet. Python-Namen verwenden Unterstriche (`plugin_create`). Nur benötigte Verzeichnisse werden angelegt.

Tests are organized by test type first, then by skill or component where useful. Python names use underscores (`plugin_create`). Only needed directories are created.

| Bereich / Layer | Aufgabe / Purpose |
| --- | --- |
| `unit/` | Einzelne Funktionen ohne Host oder Modell / Individual functions without host or model |
| `integration/` | Zusammenspiel von Werkzeugen, Dateien und temporären Repositories / Tools, files and temporary repositories working together |
| `contracts/` | Skill-, Manifest-, Katalog- und Paketverträge / Skill, manifest, catalog and package contracts |
| `behavior/` | Ausdrücklich gestartete Modelltests / Explicit model behavior tests |
| `native/` | Echte Host-CLIs mit isolierten Profilen / Real host CLIs with isolated profiles |
| `fixtures/` | Fiktive Testdaten / Fictional test data |
| `support/` | Gemeinsame Testhelfer ohne eigene Tests / Shared test helpers without tests |

Judge-Kalibrierung: `fixtures/behavior/judge_cases/` (gespeicherte fiktive Antworten mit bekanntem Urteil, u. a. übersehene Fachfehler); `python3 tests/behavior/run_scenarios.py --cli claude --judge-calibration` fragt den echten Judge. Modellläufe bewahren die gespeicherten Run-/State-/Match-Artefakte unter `<output>/artifacts/`. / Judge calibration with stored replies of known verdict; model runs keep the stored artifacts.

Nachfrage-Dialog: Runtime-Format in `integration/workspace/test_followups.py`, Modellszenarien `fixtures/behavior/scenarios/followup_*.json`, Einzelturn-Host `run_native.py --only …,followup_adr_deadline` (heuristisch bzw. beobachtet, nicht deterministisch). / Follow-up dialogue: runtime format in `test_followups.py`, model scenarios `followup_*.json`, single-turn host phase `followup_adr_deadline`.

Im jeweiligen Repository / From the relevant repository:

```sh
make test                    # unit + integration + contracts
make test-unit
make test-integration
make test-contracts
make test-native             # explicit, isolated hosts only
make test-behavior           # explicit model calls, when configured
make test-scenarios          # explicit multi-step model scenarios (heuristic)
make test-host CLI=claude|codex      # native host acceptance (its check logic is covered by deterministic unit tests; the runner itself needs a signed-in host) in a temporary project (tests/native/run_native.py)
make test-research CLI=claude|codex  # live-web research acceptance with a real public posting
python3 -B scripts/run_tests.py --kind deterministic --list
```

`make test` führt auch bei gesetzten Umgebungsvariablen keine nativen Tests aus. Ein nicht vorhandener Bereich meldet ausdrücklich `NOT RUN`; das ist keine bestandene Prüfung. Ein unbekannter `TEST_GROUP` oder Importfehler führt zum Fehlerstatus. Es werden keine Werkzeuge automatisch installiert.

`make test` never runs native tests, regardless of environment flags. An absent layer reports `NOT RUN`, which is not a passed test. Unknown `TEST_GROUP` values or import errors fail. Tools are never installed automatically.

Im Manager kann `make test TEST_GROUP=publish` oder `make test-integration TEST_GROUP=plugin-create` eine Komponente auswählen. `make test-native` im ai.plugins-Stamm führt die Marketplace- und Manager-Hosttests aus. Native Tests verändern keine persönlichen Installationen. Der Coach hat derzeit keine eigene native Suite; seine Host-Abnahme bleibt separat (`NOT RUN`, siehe `docs/acceptance.md`). `make test-host`/`make test-research` (`tests/native/run_native.py`) laufen mit der angemeldeten Host-CLI in einem temporären Projekt (Claude Code: `--plugin-dir` auf eine Payload-Kopie; Codex: Payload-Skills als projektlokale `.agents/skills`, keine Marketplace-Installation). `make test-scenarios` führt mehrstufige Modellszenarien mit Rubrik-Judge (zweiter Modellaufruf, heuristisch) mit eingeschränktem Tool-Kanal aus (heuristisch, kein Hostlauf). Manager und Coach besitzen Modelltests. Im Manager: `make test-behavior CLI=claude|codex`; im Coach etwa `make test-behavior CLI=codex` und `make test-journey CLI=claude`. Modelltests können Credits verbrauchen; sie werden nicht mit dem normalen Testlauf gestartet.

In the Manager, `make test TEST_GROUP=publish` or `make test-integration TEST_GROUP=plugin-create` selects a component. Root `make test-native` in ai.plugins runs marketplace and Manager host tests. Native tests never change personal installations. The Coach currently has no dedicated native suite; host acceptance remains separate (`NOT RUN`, see `docs/acceptance.md`). `make test-host`/`make test-research` (`tests/native/run_native.py`) run the signed-in host CLI in a temporary project (Claude Code: `--plugin-dir` on a payload copy; Codex: payload skills as project-scoped `.agents/skills`, no marketplace installation). `make test-scenarios` runs multi-step model scenarios with a rubric judge (a second model call, heuristic) with a restricted tool channel (heuristic, not a host run). Both Manager and Coach have model tests: `make test-behavior CLI=claude|codex` in the Manager; in the Coach, for example `make test-behavior CLI=codex` and `make test-journey CLI=claude`. Model tests may consume credits and never run with the default suite.

Regressionen gehören zur jeweiligen Testart, nicht in einen eigenen regression-Ordner. CI verwendet weiterhin `make test`. Testdaten bleiben fiktiv; Modellartefakte liegen ignoriert unter `.tmp/tests/`. Erfolgreiche lokale Tests ersetzen keine veröffentlichte GitHub-/GUI-Abnahme.

Regressions belong to their test type rather than a separate regression directory. CI continues to use `make test`. Fixtures remain fictional; model artifacts stay ignored under `.tmp/tests/`. Local success does not certify published GitHub/GUI acceptance.

Native selection uses only `--kind native` / `make test-native`; the runner sets `AI_PLUGIN_TEST_NATIVE`. Previous native gate names are not consumed.

`tests/native/run_host_acceptance.py` ist der gestufte, gezielte Hosttest (Stufen `prepare`, `evidence`, `ask`, `check-answer`, `answer`, `status`, je eigener Aufruf, gemeinsame Deadline). Er trennt automatische Prüfungen und fachliches Review; PASS braucht beides, Exitcode 0 nur dann. Seine Logik ist in `tests/unit/test_host_acceptance.py` mit gemocktem Host abgedeckt. / Staged targeted host test; automatic checks and domain review are separate verdicts, exit code 0 only for a verified PASS.
