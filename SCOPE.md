# Zielbild / Product scope

Status: confirmed

Am 19.11.2026 wurden SKILL.md und references/ vom Nutzer als Zielbild bestätigt. Die Erweiterung (zwei Hosts,
genau zwei Speicheroptionen, mehrere Bewerber, CV-Import, Stellen-Skills, lokaler Speicherablauf) wurde danach
ausdrücklich freigegeben und hat Vorrang vor früheren Fassungen. Die folgenden Kriterien sind Anforderungen,
keine Behauptung von Umsetzung oder Abnahme. / The extension (two hosts, exactly two storage options, several
candidates, CV import, job skills, local storage flow) was explicitly confirmed afterwards and supersedes earlier
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
oder Marketplace-Kataloge im Plugin-Repository. Kein Git-Speicher, kein Provider-SDK-Adapter und keine
Verwaltung von Git-Zugangsdaten; keine Clone-, Commit-, Push- oder Pull-Funktion für Nutzerdaten.
Keine Legacy-Unterstützung, Aliase, Ersatzpfadsuche oder automatische Migration. „Dateien selbst verwalten“ ist kein
Speichermodus. / No hiring prediction, fabricated experience, background persistence, private plugin data,
plugin-owned marketplace catalog, provider SDK adapter, git credential management, legacy support or migration.

Source/Test sind Belegverweise, keine bestandene Abnahme. Modelltests sind heuristisch; Vertrags-Textprüfungen
beweisen kein Dialogverhalten. Fehlende Verhaltens- oder Host-/Live-Abnahme bleibt offen (siehe docs/acceptance.md).
Source/test pointers are evidence locations, not proof. Model checks are heuristic; text contracts do not establish
actual dialogue behavior.

## R1: Speicherwahl und Zustimmung

Status: confirmed
Acceptance: Beim Erststart genau zwei Speicheroptionen (Lokal, Nicht speichern) vor einer Pfadfrage anbieten; der Projektordner ist höchstens Vorschlag, nie ungefragtes Ziel. Bestehendes Ziel nur bestätigt weiterverwenden oder explizit wechseln (auch Wechsel des Ziels); diese Entscheidung und ungültige vorhandene Konfiguration werden vor jeder Mutation (Verzeichnisse, Workspace-Dateien, Zeiger) geprüft und serialisiert. Setup erhält vorhandene Inhalte und prüft Lese-/Schreibzugriff. „Dateien selbst verwalten“ ist weder Modus noch Fallback.
Source: skills/_shared/references/setup.md
Source: skills/_shared/scripts/interview_workspace.py
Test: tests/integration/workspace/test_projects_candidates.py
Test: tests/behavior/run.py
Fixture: tests/fixtures/behavior/quality-cases.json
Fixture: tests/fixtures/behavior/scenarios/setup_two_options.json

Ergänzung bestätigt am 20.11.2026: Nach „Lokal“ bei bekanntem Projektpfad dessen Unterordner `interview-data`
mit absolutem Pfad und „Ja, hier speichern“ / „Nein, anderen Ordner wählen“ anbieten. „Ja“ bestätigt das Ziel
und die angekündigte Einrichtung ohne erneute Pfadabfrage; „Nein“ führt zur Frage nach einem anderen Pfad,
ohne den Vorschlag anzulegen. Fragen nicht doppelt ausgeben. Ohne bekannten Projektpfad direkt nach dem Ziel
fragen; niemals private Daten im installierten Plugin vorschlagen. Bestehende Format- und Zugriffskontrollen bleiben verbindlich.
Fixture: tests/fixtures/behavior/scenarios/setup_local_accept.json
Fixture: tests/fixtures/behavior/scenarios/setup_two_options.json

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
Acceptance: Bestätigte Bedien- und Interviewsprache getrennt behandeln. Bestätigt am 20.11.2026: Nur die Bediensprache ist projektbezogen und wird im Setup abgefragt. Die Standard-Interviewsprache wird pro Bewerber bestätigt; eine einzelne Stelle kann sie überschreiben, auch unabhängig von anderen Stellen desselben Unternehmens. Ohne Stellenabweichung gilt der Bewerberstandard. Fehlende Bestätigung wird vor Interviewfragen eingeholt. Sprachwahl ist nicht auf Deutsch/Englisch beschränkt. Nicht speichern hält dieselbe Zuordnung nur im Chat. Im Coaching eine Frage pro Turn, Feedback zur tatsächlichen Antwort mit rollenbezogener Gesamtbewertung und Kriterien; im Mock Feedback am Ende. Modi general, targeted, drill, mock, briefing bleiben erhalten. Keine beruflichen Erfahrungen erfinden.
Source: skills/interview-coach/SKILL.md
Source: skills/_shared/references/training.md
Source: skills/_shared/references/evaluation.md
Source: skills/_shared/references/session-control.md
Test: tests/behavior/run.py
Fixture: tests/fixtures/behavior/quality-cases.json
Test: tests/behavior/run_journey.py
Fixture: tests/fixtures/behavior/journeys/teamlead_coaching.json
Test: tests/contracts/test_skill_contract.py

Test: tests/integration/workspace/test_languages.py

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
Acceptance: Genau ein aktueller Aufbau (Projekt/Speicherziel → Bewerber → Identität/Profil, CV, Lernstand, Stellen mit Ausschreibung/Recherche/Vorbereitung, Runs mit optionaler Stellenzuordnung) mit versionierten Schemas. Alle privaten Daten liegen außerhalb des installierten Plugins; Pfade sind gegen Traversal und unsichere Symlinks geschützt. Der interne Kontrollordner heißt `.journal` (Format 3) und enthält geschützte Verwaltungs- und Wiederherstellungsdaten, die nicht manuell gelöscht werden sollen. Das frühere Layout mit `.zyris` (Format 2), auch gemischt oder als Datei/Symlink sowie auf Bewerberebene, wird vor jeder Mutation mit konkreter Diagnose abgelehnt und nie migriert, gelesen, verschoben oder gelöscht.
Source: skills/_shared/references/storage.md
Source: skills/_shared/scripts/interview_workspace.py
Source: skills/_shared/scripts/coach_core.py
Test: tests/integration/workspace/test_projects_candidates.py
Test: tests/contracts/test_skill_contract.py

## R19: Git-Speicher entfernt

Status: confirmed
Acceptance: Am 20.11.2026 wurde Git-Speicherung ausdrücklich aus dem Produktumfang entfernt. Angeboten werden nur Lokal und Nicht speichern. Runtime und Skills bieten keine Git-Speicherbefehle, Remote-Parameter, Provider-Anmeldung oder Connector-Speicherung mehr. Bestehende Git-Konfigurationen werden vor Schreibzugriffen konkret abgelehnt und unverändert erhalten; keine automatische Umwandlung in lokalen Speicher, keine Migration und kein Löschen. Git für Repository-Entwicklung und Plugin-Installation ist davon unabhängig.
Source: skills/_shared/scripts/interview_workspace.py
Source: skills/_shared/references/setup.md
Test: tests/integration/workspace/test_storage_modes.py

## R20: Realistischer Nachfrage-Dialog

Status: confirmed
Acceptance: Bestätigt am 20.11.2026. Nach einer Antwort prüft der Interviewer zuerst, ob eine wesentliche, tatsächlich gestellte Anforderung der Hauptfrage offen, mehrdeutig oder widersprüchlich ist. Wenn ja: genau eine konkrete Nachfrage pro Turn, bei der aktuellen Hauptfrage; davor keine Musterantwort, kein Lösungshinweis, keine ausführliche Bewertung, keine Verbesserungsliste; Abwarten der eigenständigen Antwort; kein Wechsel zur nächsten Hauptfrage allein wegen einer eingegangenen Antwort. Eine Nachfrage ist kein vollständiger Wiederholungsversuch. Bei genügend Evidenz, fehlender sinnvoller Klärung oder Nichtwissen wird der Frageblock beendet: in Coaching-Modi erst jetzt (nie nach jeder Einzelantwort) Erstantwort und Ergänzungen getrennt bewerten, dann Coaching anbieten oder zur nächsten Hauptfrage; keine endlose Schleife, keine starre Quote, keine künstliche Nachfrage bei guter vollständiger Antwort. Mock erlaubt natürliche Nachfragen, Bewertung/Hinweise/Musterantworten erst am Ende; Briefing bleibt ohne Antwortbewertung. STOP hat immer Vorrang (keine weitere Frage, keine zweite Bestätigung).
Arten: clarification (neutral), completion (wesentliche Anforderung fehlt), deepening (zusätzliche Dimension, kein Fehler der Erstantwort). Die Anzahl der Nachfragen erzeugt keinen pauschalen Abzug; bewertet wird, was spontan beantwortet, was nach einer Nachfrage selbstständig konkretisiert wurde, was offen blieb und wo Hinweise/Coaching nötig waren. Eine Antwort nach neutraler Nachfrage ist eigene Evidenz, aber keine spontan vollständige Erstantwort; nach inhaltlichen Hilfen ist sie unterstützt; Musterantworten sind keine Bewerberevidenz; improving/stable bleiben unverändert und Nachfragen täuschen keine zusätzlichen Szenarien vor. Nur ausdrücklich verlangte oder wesentliche Aspekte werden bewertet; ein „wenn möglich“ erbetenes reales Beispiel ist keine Voraussetzung für eine gute Antwort auf ein hypothetisches Szenario und wird später im Block nicht verpflichtend.
Rollenpassung: mehrdeutige Motivationsaussagen werden vor jeder Schwächenableitung geklärt; eine bestätigte Präferenz für technische Umsetzung kann gegen eine Product-Rolle sprechen, ist aber eine stellenspezifische Passungsfrage (match/preparation), keine allgemeine Kommunikationsschwäche und nicht Teil des Bewerber-Lernstands; Ausschreibungen werden nicht überzeichnet (Ausschreibungsfakten und Interpretation getrennt).
Persistenz (Run-Format 4, nur aktuelles Format): je Hauptfrage stabile Zuordnung `q-N`, Hauptfrage und ursprüngliche Antwort, Nachfragen (`q-N-fM`) mit Originalwortlaut, Art, konkretem Anlass, Antwort, Hinweis-Flag, geschlossene/offene Lücken und getrennter Einordnung von Erstantwort und Frageblock. Hauptfragen, Nachfragen und Wiederholungsversuche werden getrennt gezählt; eine Nachfrage erhöht `answered_count` nicht; eine unbeantwortete Nachfrage bei STOP ist weder Antwort noch fehlgeschlagene Antwort. Immutable Runs, stopped_early, Pause/Fortsetzung (neue Run-ID, gleiche Zuordnung, unveränderte Planzahl, beantwortete Inhalte unverändert und nicht wiederholt; ein dokumentierter Hinweis `hints_before` wird nie entfernt; dokumentierte offene Lücken verschwinden nur mit neuer Evidenz) bleiben erhalten. Runs im Format 3 (ohne Dialogdaten) werden vor Schreibzugriffen konkret abgelehnt und unverändert gelassen; keine Aliase, Fallbacks oder Migration. Nicht speichern: dieselbe Gesprächslogik nur im Chat ohne Runtime-Aufrufe oder Dateien.
Source: skills/_shared/references/followup.md
Source: skills/_shared/references/evaluation.md
Source: skills/_shared/references/session-control.md
Source: skills/_shared/references/runtime.md
Source: skills/_shared/references/storage.md
Source: skills/_shared/scripts/interview_workspace.py
Test: tests/integration/workspace/test_followups.py
Test: tests/behavior/run_scenarios.py
Test: tests/unit/test_run_scenarios.py
Test: tests/native/run_host_dialogue.py
Test: tests/unit/test_host_dialogue.py
Fixture: tests/fixtures/behavior/judge_cases/final10_B_role_fit_penalty.json
Fixture: tests/fixtures/behavior/judge_cases/final10_host_claude_false_missing.json
Fixture: tests/fixtures/behavior/scenarios/followup_adr_deadline.json
Fixture: tests/fixtures/behavior/scenarios/followup_motivation_role_fit.json
Fixture: tests/fixtures/behavior/scenarios/followup_complete_answer.json
Fixture: tests/fixtures/behavior/scenarios/followup_gap_stays_open.json
Fixture: tests/fixtures/behavior/scenarios/followup_optional_example.json
Fixture: tests/fixtures/behavior/scenarios/followup_stop_open.json
Fixture: tests/fixtures/behavior/scenarios/followup_mock.json
Fixture: tests/fixtures/behavior/scenarios/followup_pause_resume.json
Fixture: tests/fixtures/behavior/scenarios/followup_no_storage.json
