# Zielbild / Product scope

Status: confirmed

Am 19.11.2026 wurden SKILL.md und references/ vom Nutzer als Zielbild bestätigt. Die Erweiterung (zwei Hosts,
genau drei Speicheroptionen, mehrere Bewerber, CV-Import, Stellen-Skills, funktionaler Git-Ablauf) wurde danach
ausdrücklich freigegeben und hat Vorrang vor früheren Fassungen. Die folgenden Kriterien sind Anforderungen,
keine Behauptung von Umsetzung oder Abnahme. / The extension (two hosts, exactly three storage options, several
candidates, CV import, job skills, functional Git flow) was explicitly confirmed afterwards and supersedes earlier
versions. The criteria below are requirements, not claims of implementation or acceptance.

## Zweck / Purpose

Wiederverwendbares Interview-Coaching für **Claude Code und Codex** mit lokalen Projektordnern. Ein Projekt verwaltet
mehrere Bewerber; jeder hat getrennte Identität/Profil, CV-Quellen und Markdown, Stellenvorbereitungen, Trainingsläufe
und evidenzbasierten Lernstand. / Reusable interview coaching for Claude Code and Codex. One project manages several
candidates, each with separate identity/profile, CV sources and Markdown, job preparations, runs and learning state.

Öffentliche Skills / public skills: `interview-coach` (Einstieg, Setup), `candidate-create`, `candidate-training`,
`job-create`, `job-training`. Natürliche Sprache funktioniert zusätzlich zu den dokumentierten Host-Aufrufen; ein
nativer Befehl `:job-create` wird nicht behauptet. Setup erfolgt bei Erstverwendung oder explizitem `setup`; eine
automatische Aktivierung beim Öffnen eines Projekts wird nicht behauptet.

## Nicht-Ziele / Non-goals

Keine Einstellungsprognose, erfundenen Erfahrungen, automatischen Hintergrundspeicherungen, privaten Daten im Plugin
oder Marketplace-Kataloge im Plugin-Repository. Kein Provider-SDK-Adapter und keine eigene Verwaltung von
Git-Zugangsdaten (Tokens/Passwörter werden weder erfragt noch gespeichert); Remote-Speicherung koordiniert die
Runtime über externes `git` (Sichtbarkeitsprüfung über `gh`/`glab` oder ausdrückliche Connector-Bestätigung).
Keine Legacy-Unterstützung, Aliase, Ersatzpfadsuche oder automatische Migration. „Dateien selbst verwalten“ ist kein
Speichermodus. / No hiring prediction, fabricated experience, background persistence, private plugin data,
plugin-owned marketplace catalog, provider SDK adapter, git credential management, legacy support or migration.

Source/Test sind Belegverweise, keine bestandene Abnahme. Modelltests sind heuristisch; Vertrags-Textprüfungen
beweisen kein Dialogverhalten. Fehlende Verhaltens- oder Host-/Live-Abnahme bleibt offen (siehe docs/acceptance.md).
Source/test pointers are evidence locations, not proof. Model checks are heuristic; text contracts do not establish
actual dialogue behavior.

## R1: Speicherwahl und Zustimmung

Status: confirmed
Acceptance: Beim Erststart genau drei Speicheroptionen (Lokal, Git, Nicht speichern) vor einer Pfad- bzw. Repository-Frage anbieten; der Projektordner ist höchstens Vorschlag, nie ungefragtes Ziel. Bestehendes Ziel nur bestätigt weiterverwenden oder explizit wechseln (auch Wechsel der Speicherart oder des Repositorys am selben Pfad); diese Entscheidung und ungültige vorhandene Konfiguration werden vor jeder Mutation (Verzeichnisse, Klone, Workspace-Dateien, Zeiger, Remote-Schreibaktionen) geprüft und serialisiert. Setup erhält vorhandene Inhalte und prüft Lese-/Schreibzugriff. „Dateien selbst verwalten“ ist weder Modus noch Fallback.
Source: skills/_shared/references/setup.md
Source: skills/_shared/scripts/interview_workspace.py
Test: tests/integration/workspace/test_projects_candidates.py
Test: tests/behavior/run.py
Fixture: tests/fixtures/behavior/quality-cases.json
Fixture: tests/fixtures/behavior/scenarios/setup_three_options.json

## R2: Nicht speichern

Status: confirmed
Acceptance: Explizites Nicht speichern verhindert sämtliche skillverwalteten Schreibvorgänge, Konfigurationszeiger, Locks, Journale, Exporte und Runtime-Aufrufe; Bewerberkontexte und Stellen bleiben im Chat unterscheidbar, ohne Wiederverfügbarkeit zu behaupten. Stop liefert nur eine Zusammenfassung im Chat.
Source: skills/interview-coach/SKILL.md
Source: skills/_shared/references/storage.md
Source: skills/_shared/scripts/interview_workspace.py
Test: tests/integration/workspace/test_projects_candidates.py
Test: tests/behavior/run.py
Fixture: tests/fixtures/behavior/quality-cases.json
Fixture: tests/fixtures/behavior/scenarios/no_storage_no_writes.json

## R3: Lokale Persistenz und Fehlerberichte

Status: confirmed
Acceptance: Neue Runs sind unveränderlich; State-Hash und kooperative Locks schützen pro Bewerber gegen veraltete und konkurrierende Schreibzugriffe. Erfolg erst nach Inhaltsprüfung. Fehler unterscheiden fehlendes Journal, ausstehende Wiederherstellung und bereits veröffentlichte Inhalte mit unbestätigter Dauerhaftigkeit; nie pauschal Erfolg behaupten. Fehlende Berechtigungen und I/O-Fehler führen zu Fehlern ohne Teilerfolgsmeldung.
Source: skills/_shared/scripts/interview_workspace.py
Source: skills/_shared/references/storage.md
Test: tests/integration/workspace/test_jobs_runs.py

## R4: Stop Pause und Fortsetzung

Status: confirmed
Acceptance: Stop beendet Fragen ohne zweite Bestätigung. Pausierte Checkpoints werden unter neuer Run-ID fortgesetzt, nur beim selben Bewerber und derselben Stelle; bekannte Planzahl bleibt erhalten, Zähler sinken nicht. Bereits fortgesetzte Checkpoints nicht erneut verzweigen. Run-Dateien ohne aktuelles Format oder mit fremder Zuordnung blockieren Operationen vor Schreibzugriffen und bleiben unverändert.
Source: skills/_shared/references/session-control.md
Source: skills/_shared/scripts/interview_workspace.py
Test: tests/integration/workspace/test_jobs_runs.py
Test: tests/behavior/run.py
Fixture: tests/fixtures/behavior/quality-cases.json
Fixture: tests/fixtures/behavior/scenarios/stop_pause_resume.json

## R5: Sprache und Coaching

Status: confirmed
Acceptance: Bestätigte Bedien- und Interviewsprache getrennt behandeln. Im Coaching eine Frage pro Turn, Feedback zur tatsächlichen Antwort mit rollenbezogener Gesamtbewertung und Kriterien; im Mock Feedback am Ende. Modi general, targeted, drill, mock, briefing bleiben erhalten. Keine beruflichen Erfahrungen erfinden.
Source: skills/interview-coach/SKILL.md
Source: skills/_shared/references/training.md
Source: skills/_shared/references/evaluation.md
Source: skills/_shared/references/session-control.md
Test: tests/behavior/run.py
Fixture: tests/fixtures/behavior/quality-cases.json
Test: tests/behavior/run_journey.py
Fixture: tests/fixtures/behavior/journeys/teamlead_coaching.json
Test: tests/contracts/test_skill_contract.py

## R6: Evidenzbasierter Fortschritt

Status: confirmed
Acceptance: Nur unabhängige Antworten sind Fortschrittsbelege; improving nach zwei spontanen erfolgreichen Antworten in verschiedenen Szenarien, stable erst nach Bestätigung in späterem Lauf ohne Coaching. Modellantworten sind keine Kompetenznachweise. Lernstand ist pro Bewerber getrennt; stellenspezifische Passungslücken stehen nicht im bewerberübergreifenden Lernstand.
Source: skills/_shared/references/evaluation.md
Source: skills/interview-coach/SKILL.md
Source: skills/job-training/SKILL.md
Test: tests/behavior/run_journey.py
Fixture: tests/fixtures/behavior/journeys/teamlead_coaching.json
Test: tests/unit/test_run_journey.py
Test: tests/integration/workspace/test_projects_candidates.py

## R7: Recherche und private Daten

Status: confirmed
Acceptance: Gezielte Vorbereitung benötigt ein bestätigtes Profil und die Stellenquelle. Ein unbestätigtes Profil darf als Entwurf gespeichert und angezeigt werden, gilt aber nicht als verlässliche Bewerberevidenz; die Kennzeichnung „unbestätigt“ ersetzt die Bestätigung nicht. Stellenaufnahme und allgemeine Unternehmensrecherche bleiben unabhängig davon möglich; ein personenbezogener Abgleich und Training, das Profilangaben als Fakten verwendet, setzen die Bestätigung voraus. Allgemeines Training bleibt im Rahmen belegter Angaben möglich. Öffentlich berufliche Recherche mit Quellen und Abrufdatum; Fakten, Schlussfolgerungen und Unbekanntes getrennt; Namensgleichheiten vor Zuordnung klären; keine psychologischen Profile. Vorhandene Stellenvorbereitung wiederverwenden. Keine privaten Daten im Plugin.
Source: skills/_shared/references/research.md
Source: skills/_shared/references/job-preparation.md
Source: skills/_shared/references/storage.md
Source: skills/job-create/SKILL.md
Test: tests/behavior/run.py
Fixture: tests/fixtures/behavior/quality-cases.json
Test: tests/contracts/test_skill_contract.py

## R8: Technische Übungen und Ausführungsgrenzen

Status: confirmed
Acceptance: Aufgabe ohne vorweggenommene Lösung stellen. Kandidatencode nur in autorisierter sicherer Isolation ausführen, andernfalls statisch und als nicht ausgeführt bewerten. Keine unbelegten Test-, Recherche- oder Speichererfolge behaupten.
Source: skills/_shared/references/technical-interview.md
Source: skills/interview-coach/SKILL.md
Test: tests/behavior/run_smoke.py
Fixture: tests/fixtures/behavior/behavior-cases.json
Test: tests/contracts/test_skill_contract.py

## R9: Nur aktuelle Formate und Pfade

Status: confirmed
Acceptance: Keine Legacy-Unterstützung, Ersatzpfade oder automatische Migrationen. Die Auflösung erfolgt ausschließlich über den projektbezogenen Zeiger des aktuellen Formats; alte Zeiger werden nie gesucht. Nicht unterstützte Workspace-, Bewerber-, Run- und Artefaktformate werden vor Schreibzugriffen mit konkreter Diagnose abgelehnt und bleiben unverändert.
Source: skills/_shared/scripts/interview_workspace.py
Source: skills/_shared/references/storage.md
Test: tests/integration/workspace/test_projects_candidates.py
Test: tests/integration/workspace/test_jobs_runs.py

## R10: Zwei Hosts

Status: confirmed
Acceptance: Claude Code und Codex erhalten dokumentierte, funktionierende Einstiegspunkte für alle fünf Skills aus demselben verteilten Payload; fachliche Abläufe sind gleichwertig, Aufrufsyntax darf abweichen. Keine behauptete automatische Aktivierung beim Projektöffnen und kein behaupteter nativer Befehl `:job-create`.
Source: skills/interview-coach/SKILL.md
Source: scripts/plugin.py
Test: tests/contracts/test_distribution_contract.py
Test: tests/contracts/test_install.py

## R11: Projektbezogene Auflösung und mehrere Bewerber

Status: confirmed
Acceptance: Der Speicherzeiger gilt pro Projektordner; zwei Projekte schalten einander nicht um. Ein Projekt verwaltet mehrere Bewerber mit stabilen IDs; gleiche Namen sind zulässig, Namen erzeugen keine Pfade. Eindeutige Auswahl wird wiederverwendet, Mehrdeutigkeit führt zur Nachfrage. Bewerber teilen weder Lernstand noch Profil, CV, Stellen oder Runs.
Source: skills/_shared/scripts/interview_workspace.py
Source: skills/_shared/references/candidate-selection.md
Test: tests/integration/workspace/test_projects_candidates.py
Test: tests/integration/workspace/test_jobs_runs.py
Fixture: tests/fixtures/behavior/scenarios/same_name_selection.json

## R12: Bewerber anlegen

Status: confirmed
Acceptance: candidate-create fragt den Namen, vergibt eine eindeutige stabile ID, fragt nach einem CV, importiert ihn oder erarbeitet ein Profil und zeigt Ergebnis, offene Punkte und tatsächlichen Speicherort. Unterbrochene Anlage erzeugt keinen scheinbar fertigen Datensatz, sondern einen nicht nutzbaren Entwurf (creating), der ohne Überschreiben abgeschlossen werden kann.
Source: skills/candidate-create/SKILL.md
Source: skills/_shared/scripts/interview_workspace.py
Test: tests/integration/workspace/test_projects_candidates.py
Fixture: tests/fixtures/behavior/scenarios/candidate_create_with_cv.json

## R13: CV-Import

Status: confirmed
Acceptance: PDF, DOCX und Markdown werden über nachvollziehbare Extraktionswege übernommen; Originaldatei bytegetreu (SHA-256), Markdown bildet den Inhalt ab, Herkunft und Zusammenhang Original/Extraktion/Profil sind festgehalten. Unlesbare Stellen und Lücken werden offengelegt und der Import dann als partial markiert; fehlende Fähigkeiten werden konkret gemeldet, nichts wird installiert oder erfunden. Wiederholung und Kollision erhalten vorhandene Quellen.
Source: skills/_shared/scripts/coach_extract.py
Source: skills/_shared/scripts/interview_workspace.py
Source: skills/_shared/references/cv-profile.md
Test: tests/integration/workspace/test_cv_profile.py

## R14: Profil ohne CV

Status: confirmed
Acceptance: Ohne CV werden Erfahrung, Ausbildung, Fähigkeiten, Projekte und Ziele mit je einer Frage erarbeitet, nichts erfunden; ein gekennzeichneter CV-Entwurf und ein Profil entstehen als Entwurf. Fachliche Angaben gelten erst nach Bestätigung als verifizierte Grundlage für gezielte Vorbereitung; ein Entwurf wird nie still zu „bestätigt“ hochgestuft; Original, Nutzerangaben und Modellformulierungen bleiben unterscheidbar.
Source: skills/_shared/references/cv-profile.md
Source: skills/candidate-create/SKILL.md
Source: skills/_shared/scripts/interview_workspace.py
Test: tests/integration/workspace/test_cv_profile.py
Fixture: tests/fixtures/behavior/scenarios/candidate_create_without_cv.json

## R15: Allgemeines Training

Status: confirmed
Acceptance: candidate-training bestimmt den Bewerber eindeutig, lädt Profil, Lernstand und frühere Runs, richtet Fragen an Fähigkeiten, Erfahrung, Rolle und Zielen aus, stellt je eine Frage, bewertet die tatsächliche Antwort, leitet bessere Formulierungen nur aus belegten Angaben ab, speichert jeden Durchlauf als eigenen Run und aktualisiert nur den Lernstand des richtigen Bewerbers.
Source: skills/candidate-training/SKILL.md
Source: skills/_shared/references/training.md
Source: skills/_shared/scripts/interview_workspace.py
Test: tests/integration/workspace/test_jobs_runs.py
Fixture: tests/fixtures/behavior/scenarios/general_training_answer.json

## R16: Stelle vorbereiten

Status: confirmed
Acceptance: job-create bestimmt den Bewerber, sichert Ausschreibung und Herkunft (Link mit Abrufdatum oder Upload mit Originalbytes), fragt fehlendes Unternehmen und Interviewteilnehmer (Unbekannt blockiert nicht), recherchiert öffentlich-beruflich mit Quellen und Abrufdatum, klärt Namensgleichheit vor Zuordnung, gleicht Anforderungen mit Bewerberbelegen ab und speichert Inhalt, Recherche, Abgleich und Vorbereitung als unveränderliche Snapshots. Eine Stelle gehört genau einem Bewerber; Aktualisierungen entfernen keine Evidenz.
Source: skills/job-create/SKILL.md
Source: skills/_shared/references/job-preparation.md
Source: skills/_shared/scripts/interview_workspace.py
Test: tests/integration/workspace/test_jobs_runs.py
Fixture: tests/fixtures/behavior/scenarios/job_create_missing_company.json
Fixture: tests/fixtures/behavior/scenarios/job_create_unknown_participants.json
Fixture: tests/fixtures/behavior/scenarios/job_create_ambiguous_person.json

## R17: Stellenbezogenes Training

Status: confirmed
Acceptance: job-training bestimmt Bewerber und Stelle, lädt Profil, Vorbereitung und Lernstand, verwendet vorhandene Recherche wieder und aktualisiert zeitabhängige Fakten, richtet Fragen an Anforderungen, Seniorität, Recherche und Lücken aus, speichert jeden Durchlauf als eigenen unveränderlichen Run mit maschinenprüfbarer Bewerber-/Stellenzuordnung und trennt bewerberübergreifenden Lernstand von stellenspezifischen Passungslücken.
Source: skills/job-training/SKILL.md
Source: skills/_shared/scripts/interview_workspace.py
Test: tests/integration/workspace/test_jobs_runs.py
Fixture: tests/fixtures/behavior/scenarios/job_training_reuse_second_run.json

## R18: Kanonische Datenhierarchie

Status: confirmed
Acceptance: Genau ein aktueller Aufbau (Projekt/Speicherziel → Bewerber → Identität/Profil, CV, Lernstand, Stellen mit Ausschreibung/Recherche/Vorbereitung, Runs mit optionaler Stellenzuordnung) mit versionierten Schemas. Alle privaten Daten liegen außerhalb des installierten Plugins; Pfade sind gegen Traversal und unsichere Symlinks geschützt. Der interne Kontrollordner heißt `.journal` (Format 3) und enthält geschützte Verwaltungs- und Wiederherstellungsdaten, die nicht manuell gelöscht werden sollen. Das frühere Layout mit `.zyris` (Format 2), auch gemischt oder als Datei/Symlink sowie auf Bewerberebene, wird vor jeder Mutation mit konkreter Diagnose abgelehnt und nie migriert, gelesen, verschoben oder gelöscht; der Schutz vor Veröffentlichung von Kontrolldateien erfasst `.journal` und `.zyris` als vollständige Pfadsegmente.
Source: skills/_shared/references/storage.md
Source: skills/_shared/scripts/interview_workspace.py
Source: skills/_shared/scripts/coach_core.py
Test: tests/integration/workspace/test_projects_candidates.py
Test: tests/contracts/test_skill_contract.py

## R19: Git-Speicherablauf

Status: confirmed
Acceptance: Ausschließlich private GitHub-/GitLab-Repositories mit explizitem Ziel; vor Einrichtung werden authentifizierter Zugriff, privater Status und Schreibrecht bestätigt (Provider-CLI oder ausdrücklich aufgezeichnete Connector-Bestätigung), ohne Testcommit und ohne Tokenabfrage. Remote-gespeichert wird erst nach bestätigtem Remote-Head gemeldet; lokale Änderung ist kein Remote-Erfolg. Konflikte, abgelehnte oder unterbrochene Pushes, fehlende Rechte und unbestätigter Remote-Erfolg enden in Fehlern ohne Force-Push und ohne Verlust fremder Änderungen. Vor jeder Veröffentlichung wird das tatsächliche Fetch- und Push-Ziel (origin, pushurl, mehrere Ziele, URL-Rewriting) gegen das autorisierte private Repository geprüft; Privatheits- und Rechtenachweis gelten für genau dieses Ziel und werden aktuell erhoben (eine gespeicherte Connector-Bestätigung ist kein Dauerbeweis), die abschließende Verifikation liest das beschriebene Ziel. Veröffentlicht werden nur Änderungen des autorisierten Speichervorgangs: gestagte, geänderte oder fremde Dateien (auch in verwalteten Verzeichnissen) brechen ab und bleiben unangetastet; es gibt keine automatischen Resets, Stashes oder Bereinigungen.
Source: skills/_shared/scripts/coach_git.py
Source: skills/_shared/references/storage.md
Test: tests/integration/git/test_git_storage.py
Fixture: tests/fixtures/behavior/scenarios/storage_failure_no_false_success.json
