# Zielbild / Product scope

Status: confirmed

Am 19.11.2026 wurden SKILL.md und references/ vom Nutzer als Zielbild bestätigt.
Die folgenden Kriterien halten diese Regeln und die drei freigegebenen Review-Korrekturen fest.
Existing skill contracts were confirmed by the user; these are requirements, not claims of implementation or acceptance.

## Zweck / Purpose

Wiederverwendbares, kandidatenunabhängiges Interview-Coaching mit rollenbezogenem Feedback,
Recherche und optionalem privatem Lernstand. / Reusable interview coaching, role-aware feedback,
research and optional private learning state.

## Nicht-Ziele / Non-goals

Keine Einstellungsprognose, erfundenen Erfahrungen, automatischen Hintergrundspeicherungen,
privaten Daten im Plugin oder eingebauten Remote-Storage-Adapter. Kein eigener Marketplace.
No hiring prediction, fabricated experience, background persistence, private plugin data,
built-in remote storage adapter or plugin-owned marketplace.

Source/Test sind Belegverweise, keine bestandene Abnahme. Modelltests sind heuristisch;
Vertrags-Textprüfungen beweisen kein Dialogverhalten. Fehlende Verhaltensabdeckung bleibt offen.
Source/test pointers are evidence locations, not proof. Model checks are heuristic;
text contracts do not establish actual dialogue behavior.

## R1: Speicherwahl und Zustimmung

Status: confirmed
Acceptance: Beim Erststart vier Speicheroptionen vor einer Pfadfrage anbieten. Bestehenden Workspace nur bestätigt weiterverwenden oder wechseln; init erhält vorhandene Inhalte.
Source: skills/interview-coach/references/setup.md
Source: skills/interview-coach/scripts/interview_workspace.py
Test: tests/behavior/run.py
Fixture: tests/fixtures/behavior/quality-cases.json
Test: tests/integration/workspace/test_interview_workspace.py

## R2: Nicht speichern

Status: confirmed
Acceptance: Explizites Nicht speichern verhindert sämtliche skillverwalteten Schreibvorgänge, Exporte und CLI-Aufrufe. Stop liefert nur eine Zusammenfassung im Chat.
Source: skills/interview-coach/SKILL.md
Source: skills/interview-coach/references/storage.md
Source: skills/interview-coach/references/session-control.md
Test: tests/behavior/run.py
Fixture: tests/fixtures/behavior/quality-cases.json
Test: tests/unit/test_run_behavior.py

## R3: Lokale Persistenz und Fehlerberichte

Status: confirmed
Acceptance: Neue Runs sind unveränderlich; State-Hash und kooperative Locks schützen gegen veraltete Schreibzugriffe. Erfolg erst nach Inhaltsprüfung. Fehler unterscheiden fehlendes Journal, ausstehende Wiederherstellung und bereits veröffentlichte Inhalte mit unbestätigter Dauerhaftigkeit; nie pauschal Erfolg behaupten.
Source: skills/interview-coach/scripts/interview_workspace.py
Source: skills/interview-coach/references/storage.md
Test: tests/integration/workspace/test_interview_workspace.py
Test: tests/integration/workspace/test_workspace_lifecycle.py

## R4: Stop Pause und Fortsetzung

Status: confirmed
Acceptance: Stop beendet Fragen ohne zweite Bestätigung. Pausierte Checkpoints werden unter neuer ID fortgesetzt; bekannte Planzahl bleibt erhalten, Zähler sinken nicht. Bereits fortgesetzte Checkpoints nicht erneut verzweigen. Run-Dateien ohne aktuelles Lifecycle-Format blockieren Operationen vor Schreibzugriffen und bleiben unverändert; unsichere Links und korrupte Lifecycle-Metadaten weiterhin ablehnen.
Source: skills/interview-coach/references/session-control.md
Source: skills/interview-coach/scripts/interview_workspace.py
Test: tests/integration/workspace/test_interview_workspace.py
Test: tests/integration/workspace/test_workspace_lifecycle.py
Test: tests/behavior/run.py
Fixture: tests/fixtures/behavior/quality-cases.json

## R5: Sprache und Coaching

Status: confirmed
Acceptance: Bestätigte Bedien- und Interviewsprache getrennt behandeln. Im Coaching eine Frage pro Turn, Feedback zur tatsächlichen Antwort mit rollenbezogener Gesamtbewertung und Kriterien; im Mock Feedback am Ende. Keine beruflichen Erfahrungen erfinden.
Source: skills/interview-coach/SKILL.md
Source: skills/interview-coach/references/training.md
Source: skills/interview-coach/references/evaluation.md
Source: skills/interview-coach/references/session-control.md
Test: tests/behavior/run.py
Fixture: tests/fixtures/behavior/quality-cases.json
Test: tests/behavior/run_journey.py
Fixture: tests/fixtures/behavior/journeys/teamlead_coaching.json
Test: tests/integration/workspace/test_interview_workspace.py

## R6: Evidenzbasierter Fortschritt

Status: confirmed
Acceptance: Nur unabhängige Antworten sind Fortschrittsbelege; improving nach zwei spontanen erfolgreichen Antworten in verschiedenen Szenarien, stable erst nach Bestätigung in späterem Lauf ohne Coaching. Modellantworten sind keine Kandidatenevidenz.
Source: skills/interview-coach/references/evaluation.md
Source: skills/interview-coach/SKILL.md
Test: tests/behavior/run_journey.py
Fixture: tests/fixtures/behavior/journeys/teamlead_coaching.json
Test: tests/unit/test_run_journey.py

## R7: Recherche und private Daten

Status: confirmed
Acceptance: Targeted benötigt CV oder verifiziertes Profil und Stellenquelle. Öffentlich berufliche Recherche mit Quellen und Datum, Fakten von Hypothesen trennen. Vorhandene Job-Vorbereitung wiederverwenden; keine persönlichen Profile oder privaten Daten im Plugin. Remote-Speicherung erfolgt nur über verfügbare autorisierte Connectoren oder Git, nicht durch die lokale CLI.
Source: skills/interview-coach/references/research.md
Source: skills/interview-coach/references/storage.md
Source: skills/interview-coach/SKILL.md
Test: tests/behavior/run.py
Fixture: tests/fixtures/behavior/quality-cases.json
Test: tests/contracts/test_skill_contract.py

## R8: Technische Übungen und Ausführungsgrenzen

Status: confirmed
Acceptance: Aufgabe ohne vorweggenommene Lösung stellen. Kandidatencode nur in autorisierter sicherer Isolation ausführen, andernfalls statisch und als nicht ausgeführt bewerten. Keine unbelegten Test- oder Speichererfolge behaupten.
Source: skills/interview-coach/references/technical-interview.md
Source: skills/interview-coach/SKILL.md
Test: tests/behavior/run_smoke.py
Fixture: tests/fixtures/behavior/behavior-cases.json
Test: tests/contracts/test_skill_contract.py

## R9: Nur aktuelle Formate und Pfade

Status: confirmed
Acceptance: Keine Legacy-Unterstützung, Ersatzpfade oder automatische Migrationen. Nur der aktuelle interview-coach-Konfigurationspfad wird automatisch gelesen; frühere Zeiger bleiben unberührt. Nicht unterstützte Run-Formate vor Schreibzugriffen mit konkreter Diagnose ablehnen.
Source: skills/interview-coach/scripts/interview_workspace.py
Source: skills/interview-coach/references/storage.md
Test: tests/integration/workspace/test_interview_workspace.py
