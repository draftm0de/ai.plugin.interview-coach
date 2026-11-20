# Abnahmematrix / Acceptance matrix

Stand: 2026-11-19, uncommitteter Arbeitsbaum auf `47f45f2`. Quelle der Anforderungen: [SCOPE.md](../SCOPE.md).
Ein Source-Verweis oder ein bestandener Text-Vertragstest beweist keinen fachlich korrekten Ablauf. Modelltests sind heuristisch.

**Keine vollständige Abnahme.** Unten stehen getrennt: deterministisch geprüft · modellbasiert geprüft · nativ im Host beobachtet ·
live beim Provider geprüft (nicht erfolgt) · nicht implementiert · noch nicht geprüft.

## Nachtrag 2026-11-19 17:25 — Unit- und Vertragstests auf aktuellem Stand (nur deterministisch)

Gilt nur für den unten fingerprinteten, uncommitteten Arbeitsbaum auf `47f45f2`; **darunter alles historisch**. Keine Code- oder Testkorrektur war nötig.

**Statische Vorprüfung:** `scripts/run_tests.py --kind unit|contracts` lädt nur `tests/unit` bzw. `tests/contracts`. Die Tests nutzen keine Modelle, Host-CLIs oder Netzwerke: Subprozesse sind die eigene Runtime (`--config-dir` im Temp-Verzeichnis, `HOME` überschrieben), `scripts/plugin.py check` und der Live-Git-Runner ausschließlich im `--dry-run`/Ablehnungsmodus (Tests prüfen Exitcode 2/„NOT RUN“ ohne Freigabephrase); Native-/Behavior-Runner werden nur über Stubs und `CompletedProcess`-Attrappen geprüft.

**Ausgeführte Kommandos** (2 von höchstens 3; Limit je 60 s; Runner `run_logged.py` im Protokollordner, Vordergrund, Exitcode vom Prozess; Fingerprints vor jedem Lauf)

| Bereich | Argumentliste | Dauer | Exitcode | Tests |
|---|---|---|---|---|
| Unit | `python3 -B scripts/run_tests.py --kind unit` | 0,7 s | 0 | 85, OK |
| Verträge | `python3 -B scripts/run_tests.py --kind contracts` | 0,3 s | 0 | 28, OK |

Keine Timeouts, keine übersprungenen Tests (`skip` in keinem Log). Protokolle (roh): `.tmp/tests/2026-11-19-unit-contracts-check/cmd{1-unit,2-contracts}.{stdout.log,stderr.log,record.json,fingerprints.json}`; dort liegen die Fingerprints von 60 Runtime-, Skill-, Manifest-, Skript- und Testdateien.

| Datei (Auszug) | SHA-256 |
|---|---|
| `skills/_shared/scripts/interview_workspace.py` | `5fe457c7ab6158ad950136b4c3f689d509dd0b8a116f6b24df0be852405dcc73` |
| `skills/_shared/scripts/coach_core.py` | `9c538e94a9b7c7f1a465392b2a543271d0fdb0a4a541431f6fd2ee60378cc43c` |
| `skills/_shared/scripts/coach_git.py` | `9fd07ef5e54aacee3c925317bc0c770bc0c72a92f8fb48b2def5042c6b077e8b` |
| `skills/interview-coach/SKILL.md` | `9df9796e2b569d926f5abce547ba322104b8d943f9101f5f29027a74bf82ce59` |
| `plugin.json` | `e526cd95a1e58701958853942f01b31db65651dd43914dd46be9bed2b4a304b9` |
| `tests/contracts/test_skill_contract.py` | `be0fab6c4c08b0310bbcfd03adca12e297826ce01885c349e576f1811a392e29` |
| `tests/unit/test_live_and_native.py` | `acbe4954dc909fd63b48920bdc074ddc80300a6c46443068a549a16cc6d2152a` |

**Nicht ausgeführt:** Integrationstests (die gespeicherten 41 Tests des Nachtrags 17:14 bleiben historisch und decken nur deren Fingerprints ab), `make test`, Szenarien, Journey, Smoke, Modell-, Host-, Recherche-, Installations- und Live-Git-Läufe. **Offene Fehler:** keine in diesen beiden Bereichen. Grenze: bestandene Struktur-/Text-Verträge und Unit-Tests sind kein Modell-, Host- oder Live-Nachweis und keine vollständige Produktabnahme; Codex-Hostlauf, Claude-Hostwiederholung, Recherche, Marketplace-Installation und Live-Git bleiben offen.

---

# Historisch: Stand vor diesem Nachtrag

## Nachtrag 2026-11-19 17:14 — Formatprüfung nach dem Klonen, Symlinks in Bewerberverzeichnissen (nur deterministisch)

Gilt nur für den unten fingerprinteten Stand; **darunter alles historisch**.

**Korrekturen**
1. `setup_project`: nach `prepare_clone` und **vor** Git-Guard, Sperre, Journal, Commit, Push und Zeiger prüft `check_workspace_target` den geklonten Inhalt ausschließlich lesend (alte/unsichere Layouts, Formatversion, fremde Dateien via `require_workspace`). Format 2 ohne `.zyris`-Marker wird damit abgelehnt; ein tatsächlich leeres Repository bleibt initialisierbar, ein gültiges Format 3 wird wiederverwendet. Der Klon selbst ist die einzige vorherige (unvermeidliche) Schreibaktion und bleibt unverändert erhalten; nichts wird bereinigt oder migriert.
2. `legacy_markers` ersetzt durch `scan_layout`/`layout_refusal`: Typen werden ohne Folgen von Links bestimmt (`DirEntry.is_symlink`, `is_dir(follow_symlinks=False)`, `os.path.lexists`). Ein symlinkter `candidates`-Ordner oder Bewerbereintrag (auch hängend) wird als „Unsafe layout“ abgelehnt, ohne darunter zu suchen; alte `.zyris`-Marker (Datei/Ordner/Symlink) auf Workspace- und echter Bewerberebene werden weiter erkannt. Nicht inspizierbare Verzeichnisse führen zu einem Fehler statt „kein Marker“.
3. Doku: `docs/de/storage.md` und `docs/en/storage.md` nannten noch `.zyris/pending.json` → `.journal/pending.json`; übrige aktuelle Speicheranleitungen und Referenzen nennen `.zyris` nur noch in Ablehnungs-/Schutzregeln.

**Tatsächlich gestartetes Testkommando** (1 von höchstens 2; Limit 60 s; Protokolle roh und ungefiltert, Exitcode vom Prozess, Fingerprints vor dem Lauf: `.tmp/tests/2026-11-19-format-check-symlinks/`)

| Kommando (Argumentliste in `cmd1-new-and-layout.record.json`) | Start–Ende, Dauer | Exitcode | Tests |
|---|---|---|---|
| `python3 -B -m unittest -v tests.integration.workspace.test_projects_candidates.SymlinkedCandidateDirectories tests.integration.workspace.test_projects_candidates.JournalFolderAndLegacyLayout tests.integration.git.test_git_storage.FormatCheckAfterClone tests.integration.git.test_git_storage.JournalFolderGit tests.integration.git.test_git_storage.SetupOrdering tests.integration.git.test_git_storage.Connect` | 17:14:06–17:14:32, 25,8 s | 0 | 41, OK |

Dateien: `cmd1-new-and-layout.{stdout.log,stderr.log,record.json,fingerprints.json}`. Belege: Nicht-Verfolgen per Instrumentierung (`os.path.lexists` gespiegelt: kein Pfad unter dem Link oder im externen Ziel wurde geprüft), externe Testdaten und Workspace unverändert; Format-2-Klon ohne Marker: kein `.journal`, Inhalt unverändert, `git status` sauber, kein `commit`/`add`/`push` nach dem Klon, Remote-Head und Zeiger unverändert; leeres Repository und Format 3: Einrichtung bzw. Wiederverwendung funktionieren; der bestehende Alt-Marker-Test läuft mit.

**Fingerprints (SHA-256 vor dem Lauf; danach nur Dokumentation geändert)**

| Datei | SHA-256 |
|---|---|
| `skills/_shared/scripts/interview_workspace.py` | `5fe457c7ab6158ad950136b4c3f689d509dd0b8a116f6b24df0be852405dcc73` |
| `skills/_shared/scripts/coach_core.py` | `9c538e94a9b7c7f1a465392b2a543271d0fdb0a4a541431f6fd2ee60378cc43c` |
| `skills/_shared/scripts/coach_git.py` | `9fd07ef5e54aacee3c925317bc0c770bc0c72a92f8fb48b2def5042c6b077e8b` |
| `tests/integration/workspace/test_projects_candidates.py` | `f5d7f355f1639a8f8b58ba759ad02e15875478111b6acb38c85075ff736aec7f` |
| `tests/integration/git/test_git_storage.py` | `8820e32610a1938c5bacfab1f5bef740fd644f3b0dd51fd8f3cad14a054a01d8` |
| `tests/support/coach.py` | `6df0379e046d400ae15c77159acc45d92a49bc3a3cbcacbbc428be21665af71b` |

**Nicht ausgeführt:** alle übrigen Tests (Vertragstests, übrige Workspace-/Git-Klassen wie `Publishing`, `ControlFilesAndPull`, `OwnChanges`, native Prüflogik, Szenario-Harness), alle Modell-, Host-, Recherche- und Live-Git-Läufe. Die Läufe des vorigen Nachtrags decken den geänderten Quellstand (`interview_workspace.py`) nicht mehr ab. **Keine vollständige Produkt- oder Host-Abnahme.** Offen bleiben unverändert Live-Git, Codex-Hostlauf, Recherche-Abnahme, nativer Claude-Wiederholungslauf, vollständige Suite. Grenze: das Layout wird nur auf Workspace- und Bewerberebene geprüft (nicht tiefer); der Klon bleibt nach einer Ablehnung bestehen.

---

# Historisch: Stand vor diesem Nachtrag

## Nachtrag 2026-11-19 17:00 — Kontrollordner `.journal` statt `.zyris` (Format 3, nur deterministisch)

Gilt nur für den unten fingerprinteten Stand; **alle Abschnitte darunter sind historisch** (sie nennen `.zyris` und Format 2 für den damaligen Stand und werden nicht umgeschrieben).

**Format-/Pfadänderung:** Der interne Kontrollordner heißt `.journal` (eine kanonische Konstante `CONTROL` in `coach_core.py`; Git-Schutz über `CONTROL_SEGMENTS`). Betroffen: Workspace- und Bewerber-Locks, Git-Sperre `.journal/git.lock`, `pending.json`, `interrupted.json`, Import-Staging, temporäre Dateipräfixe (`.journal-tmp-`), `.gitignore` (`.journal/`). `SCHEMA` ist jetzt 3 (Workspace, Bewerber, Stellen, Artefakte, Runs, Präferenzen, Projektzeiger, Journale): ein Format-2-Workspace wird deshalb auch dann nicht still akzeptiert, wenn sein `.zyris`-Ordner fehlt. `.journal` ist geschützte Verwaltungs-/Wiederherstellungsdaten (können Trainingsantworten/CV-Text enthalten), kein Cache.

**Alte Daten (keine Migration):** `legacy_markers`/`reject_legacy_layout` erkennen `.zyris` (Ordner, Datei, Symlink — auch hängend, ohne Folgen) auf Workspace- und Bewerberebene, auch gemischt mit `.journal`, ausschließlich zur Ablehnung. Prüfung vor jeder Mutation (Setup-Vorprüfung, `workspace_problems`/`require_workspace`, `require_workspace_shallow`, nach dem Klonen vor Sperre/Journal/Guard); nichts wird gelesen, umbenannt, kopiert, verschoben oder gelöscht. Diagnose: altes, nicht unterstütztes Layout, Daten unverändert, neuer leerer Speicherort erforderlich. Der Veröffentlichungsschutz behandelt `.journal` und das historische `.zyris` als vollständige Pfadsegmente (Wurzel/verschachtelt, auch Zwischencommits); ähnliche Namen bleiben frei.

**Tatsächlich gestartete Testkommandos** (2 von höchstens 3; Protokolle roh, ungefiltert; Exitcode vom Prozess; Fingerprints vor dem Lauf: `.tmp/tests/2026-11-19-journal-rename/`)

| # | Kommando (Argumentliste in `*.record.json`) | Start–Ende, Dauer | Exitcode | Tests |
|---|---|---|---|---|
| 1 | `python3 -B -m unittest -v tests.integration.workspace.test_projects_candidates tests.integration.git.test_git_storage.JournalFolderGit tests.integration.git.test_git_storage.ControlFilesAndPull tests.integration.git.test_git_storage.OwnChanges` | 17:01:35–17:02:11, 35,8 s | 0 | 63, OK |
| 2 | `python3 -B -m unittest -v tests.integration.workspace.test_jobs_runs tests.integration.workspace.test_cv_profile tests.integration.git.test_git_storage.Publishing tests.integration.git.test_git_storage.SetupOrdering tests.integration.git.test_git_storage.Connect` | 17:02:20–17:03:12, 51,1 s | 0 | 93, OK |

Kein Timeout/Abbruch; kumuliert ca. 87 s. Dateien je Lauf: `cmd1-new-and-journal.*`, `cmd2-adapted-existing.*` (`stdout.log`, `stderr.log`, `record.json`, `fingerprints.json`). Abgedeckt u. a.: neuer Workspace nur mit `.journal` und Schema 3; Bewerber, Speichern, Pause/Fortsetzung und Recovery über die angepassten Bestandstests (`pending.json`, `stage-*`); gemeinsame `.journal/git.lock` für Speichern, Pull, Status und Publish; gestagte und unveröffentlicht committete `.journal`-Dateien auf Workspace- und Bewerberebene; historische `.zyris`-Dateien werden nicht gepusht; alter/gemischter/Marker-als-Datei/Symlink/Format-2-ohne-Marker/Bewerber-Marker-Workspace und Klon mit alten Kontrolldateien werden vor Mutationen abgelehnt (Inhalt, Konfiguration, Remote unverändert); Nicht speichern erzeugt keine Kontrollordner.

**Fingerprints (SHA-256, identisch mit dem Stand vor Lauf 1; danach nur Dokumentation geändert)**

| Datei | SHA-256 |
|---|---|
| `skills/_shared/scripts/coach_core.py` | `9c538e94a9b7c7f1a465392b2a543271d0fdb0a4a541431f6fd2ee60378cc43c` |
| `skills/_shared/scripts/coach_git.py` | `9fd07ef5e54aacee3c925317bc0c770bc0c72a92f8fb48b2def5042c6b077e8b` |
| `skills/_shared/scripts/interview_workspace.py` | `da621b6bef4ca979884420ddb8d9d7211a2377a1726fbd85d6349adcca657d97` |
| `tests/support/coach.py` | `6df0379e046d400ae15c77159acc45d92a49bc3a3cbcacbbc428be21665af71b` |
| `tests/integration/workspace/test_projects_candidates.py` | `390947f151d63f28365626d7da4eb5844a71752662a66212b9224a31683270c3` |
| `tests/integration/workspace/test_jobs_runs.py` | `c1a0ddddd42e7714302d1b4567b83fcfc26aa12a5d2841d0cd580ff08b73f024` |
| `tests/integration/workspace/test_cv_profile.py` | `344f872ae2fc09e182119fba8f2a5ce3a82ab5bf007d3e8ecd83ab0439846401` |
| `tests/integration/git/test_git_storage.py` | `21b7f4502ab614a0c7d52ce79ad619ee86c8fec8ba9febf750762dfd7ae3489c` |

**Nicht ausgeführt:** Vertragstests, übrige Unit-Tests (inkl. native Prüflogik und Szenario-Harness), Workspace-Tests außerhalb der zwei Läufe, alle Modell-, Host-, Recherche- und Live-Git-Läufe, vollständige Suite. **Kein neuer Host-Nachweis, keine vollständige Produktabnahme.** Alle früheren offenen Abnahmen (Live-Git, Codex-Hostlauf, Recherche, nativer Claude-Wiederholungslauf, Claude-Szenario-Gesamtlauf) bleiben offen.
**Grenzen:** Ältere Modell-/Host-Läufe und Ergebnisse beziehen sich auf Format 2 und `.zyris`; die Skill-Texte (`storage.md`) wurden angepasst, aber Modellverhalten damit nicht erneut geprüft. Persönliche Altdaten im alten Layout müssen vom Nutzer selbst in ein neues Ziel übertragen werden (kein Werkzeug dafür). Kooperative Sperren gelten nicht gegen Programme, die sie ignorieren.

---

# Historisch: Stand vor diesem Nachtrag

## Nachtrag 2026-11-19 16:50 — letzte Lücke in `training_question` (nur deterministisch)

**Korrektur:** In `tests/native/run_native.py` entfällt `forced`. Überschriften/Nummerierungen werden entfernt (bei Überschrift in derselben Zeile zählt nur der Rest); der verbleibende Inhalt muss selbst mit `?` enden oder wie eine Aufgabe beginnen (erweiterte `IMPERATIVE`-Liste: erzähl, beschreib, nenn, stell, erkläre, erläuter, schilder, berichte, skizzier, zeig, gib, Fragewörter, kannst/könntest du). Beliebiger Folgetext („Einen Moment bitte.“), auch gleichzeilig oder hinter einer Nummerierung, zählt nicht mehr; Auswahl-/Bestätigungs-/Vorbereitungsklärungen bleiben abgelehnt; echte Fragen mit getrennter oder gleichzeiliger Überschrift bleiben akzeptiert. Neuer Test: `HeadingsAreNotQuestions.test_a_heading_does_not_turn_arbitrary_following_text_into_a_question` und `…test_clarifications_after_headings_stay_rejected_and_real_questions_stay_accepted`. Grenze: Heuristik erkennt nur die gelisteten Überschrift- und Aufgabenformen; ein ungewöhnlich formulierter Aufgabensatz ohne `?` und ohne gelistetes Verb wird abgelehnt (strengere, nicht schwächere Prüfung).

**Test (1 Kommando, Limit 30 s):** `python3 -B -m unittest -v tests.unit.test_live_and_native` — 16:50:33, 0,4 s, Exitcode 0, 44 Tests OK, kein Timeout. Protokolle ungefiltert samt Record und Fingerprints vor dem Lauf: `.tmp/tests/2026-11-19-last-gap/` (`cmd1-training-question.{stdout.log,stderr.log,record.json,fingerprints.json}`). Nicht gelaufen: alle übrigen Tests (auch Git-Integration; Git-, Runtime- und Architekturcode unverändert, daher decken die Ergebnisse der vorigen Nachträge ihren Stand weiter nur für die dort genannten Fingerprints ab).

| Datei | SHA-256 (nach der Änderung, vor dem Lauf) |
|---|---|
| `tests/native/run_native.py` | `b95c282e76fde08cb0e33b9e695ca26986c97adf846f7cb00d9b81afe12818d1` |
| `tests/unit/test_live_and_native.py` | `acbe4954dc909fd63b48920bdc074ddc80300a6c46443068a549a16cc6d2152a` |

**Status:** Prüflogik deterministisch geprüft; **kein neuer nativer Host-Nachweis**, Runner nicht ausgeführt; keine vollständige Produktabnahme. Offen bleiben unverändert Live-Git, Codex-Hostlauf, Recherche-Abnahme, nativer Claude-Wiederholungslauf, vollständige Suite und Claude-Szenario-Gesamtlauf.

---

# Historisch: Stand vor diesem Nachtrag

## Nachtrag 2026-11-19 16:32–16:40 — drei Restbefunde (nur deterministisch)

Gilt nur für den unten fingerprinteten Stand. **Alle Abschnitte darunter sind historisch** und werden nicht als aktuelle Ergebnisse ausgegeben; die Ergebnisse des vorigen Nachtrags (36 und 76 Tests) decken diesen Stand nicht ab.

**Restbefunde und Korrekturen**
1. Kontrolldateien in unveröffentlichten Commits: `coach_git.is_control_path` erkennt `.zyris` als **vollständiges Pfadsegment** (Wurzel und verschachtelt, z. B. `candidates/<id>/.zyris/…`; `.zyris-notes/`, `my.zyris/`, `zyris/` nicht). `control_files_in_unpublished_commits` prüft jeden zu veröffentlichenden Commit einzeln (`rev-list` + `diff-tree -z`, also auch Zwischencommits, die die Datei wieder entfernt haben, ohne newline-basierte Pfadzerlegung). Fehlgeschlagene Git-Abfragen (`rev-parse`-Probe außer Exit 0/1, `rev-list`, `diff-tree`) brechen vor dem Push ab; ein noch nicht vorhandener Remote-Branch (Probe-Exit 1) prüft alle Commits ab HEAD. Kein Push, kein Umschreiben, kein Löschen/Unstagen. `_status_entries` verwendet dieselbe Segmentregel für ungestagte/ignorierte Einträge; gestagte bleiben sichtbar (unverändert).
2. `tests/native/run_native.py` `training_question`: eigenständige Überschriften/Nummerierungen (`**Erste Frage:**`, `Frage 2 von 4:`, `1.`) zählen nicht als Frage; die folgende Zeile/der folgende Satz wird als Frage-/Aufgabenkandidat gewertet und bei Auswahl-, Bestätigungs- oder Vorbereitungsklärung abgelehnt; Text nach der Überschrift in derselben Zeile wird ebenso bewertet. Grenzen: nur gelistete Überschriftformen, keine Bedeutungsanalyse, Stellenbezug am Gesamttext.
3. `Host.parse`: Tool-Ergebnisse werden pro Tool-ID gesammelt; abweichende Ergebnisse derselben ID (Fehler→Erfolg, Erfolg→Fehler, mit späterem Erfolg) ergeben `conflict` und `exit: None`; identische Wiederholungen gelten als konsistent (dokumentierte Regel); Ergebnisse ohne verwertbare ID markieren keinen Aufruf; fehlende Ergebnisse bleiben unbekannt; doppelte Tool-IDs über mehrere Aufrufe sind `ambiguous`. Bei Claude ist `exit` **abgeleitet** (`exit_source: derived-from-is_error`), bei Codex vom Host gemeldet (`host-exit_code`). `successful_calls`/`subcommands(ok_only)` lehnen `conflict`/`ambiguous` ab; Einzelaufruf- sowie Projekt-/Bewerber-/Job-ID-Prüfung bleiben.

**Tatsächlich gestartete Testkommandos** (2 von höchstens 3, kumuliert ca. 67 s; Protokolle roh und ungefiltert, Exitcode vom Prozess selbst, Fingerprints vor dem Lauf: `.tmp/tests/2026-11-19-review3-rest/`)

| # | Kommando (vollständige Argumentliste in `*.record.json`) | Start–Ende, Dauer | Exitcode | Tests | Dateien |
|---|---|---|---|---|---|
| 1 | `python3 -B -m unittest -v tests.integration.git.test_git_storage.ControlFilesAndPull tests.unit.test_live_and_native` | 16:35:58–16:36:18, 20,5 s | 0 | 60, OK | `cmd1-new-regressions.{stdout.log,stderr.log,record.json,fingerprints.json}` |
| 2 | `python3 -B -m unittest -v tests.integration.git.test_git_storage.Publishing tests.integration.git.test_git_storage.OwnChanges tests.integration.git.test_git_storage.SetupOrdering tests.integration.git.test_git_storage.Connect tests.unit.test_run_scenarios tests.unit.test_run_behavior` | 16:36:28–16:37:15, 46,9 s | 0 | 76, OK (u. a. `Publishing.test_conflicting_change_to_same_file_is_never_overwritten_and_not_reported_saved`) | `cmd2-existing-git-and-harness.*` |

Kein Timeout, kein Abbruch, kein dritter Lauf, keine Änderung an Code oder Tests nach den Läufen (nur Dokumentation). Der Fingerprint beider Läufe ist identisch. Nicht ausgeführt: `ControlFilesAndPull` ist neu (18 Tests inkl. der Regressionen oben); nicht gelaufen sind Vertragstests, Workspace-Integration (`test_cv_profile`, `test_projects_candidates`, `test_jobs_runs`), übrige Unit-Tests, Szenarien sowie alle nativen, Modell-, Recherche- und Live-Läufe.

**Fingerprints (SHA-256 vor beiden Läufen)**

| Datei | SHA-256 |
|---|---|
| `skills/_shared/scripts/coach_git.py` | `e34b2f9ff59ef676637573ce817e9153b9762834c7706e9181b4884094b29ac5` |
| `skills/_shared/scripts/coach_core.py` | `775bfa0807d5ad541db534a3af3319d2cf35036a0f6c13821ba60cd15e746b69` |
| `skills/_shared/scripts/interview_workspace.py` | `ac92cb242620a53aaa70dd2369ea5199feaeada590bcf1b2d535f681e7ea3526` |
| `tests/native/run_native.py` | `f1373fb304e12e504c17453572b8c302a87ed5672305af98690fd285e2c48d68` |
| `tests/integration/git/test_git_storage.py` | `23bfe10b4dc1ea85efd3a07018484b3ba26895de2fee8fb4497fd53b8f92e8ae` |
| `tests/unit/test_live_and_native.py` | `7631f993e9bd54aadeac82d91cb42905cb3cd133a1e0ba41aca6b9716fabc50c` |
| `tests/support/coach.py` | `6810f0e9968e2cb92c5020f39ea8679879256279fd8e1623e0c28d254b6a4281` |

**Status:** Prüflogik des nativen Runners deterministisch geprüft — **kein neuer nativer Host-Nachweis**, Runner nicht ausgeführt. Git-Verhalten nur gegen lokale Bare-Repositories mit Fake-`gh` und Identitäts-Testdouble, **keine Live-Abnahme**. Unverändert offen: Live-GitHub/GitLab, Codex-Hostlauf, Recherche-Abnahme mit echter Anzeige, nativer Claude-Wiederholungslauf, vollständige deterministische Suite, Claude-Szenario-Gesamtlauf. Keine vollständige Produktabnahme. Restgrenzen: kooperative Sperren gelten nicht gegen Programme, die sie ignorieren; die beiden nativen Heuristiken (`training_question`, `parse_runtime_call`) sind begrenzt; Claude-Erfolgsstatus ist abgeleitet.

---

# Historisch: Stand vor diesem Nachtrag

## Nachtrag 2026-11-19 16:20–16:26 — vier Review-Befunde (nur deterministisch)

Gilt nur für den unten fingerprinteten Stand. **Alle Abschnitte darunter sind historisch.** Insbesondere ist der Satz im vorigen Nachtrag, der Konflikttest sei „nicht erneut ausgeführt“, durch Lauf 2 unten überholt; der vorherige Lauf 3 deckt den jetzigen Stand nicht ab.

**Befunde und Korrekturen**
1. Gestagte Kontrolldateien: `coach_git._status_entries` blendet nur noch ungestagte/ignorierte `.zyris/`-Einträge aus; neue `staged_paths` (`git diff --cached`, alle Änderungsarten) wird in `baseline`, `commit_own` und `publish` verwendet → Abbruch mit Pfaden, nichts wird entstagt/gelöscht/zurückgesetzt. `control_files_in_unpublished_commits` verweigert den Push lokaler Commits mit `.zyris/`-Dateien (Schutzgrenze für bereits vorhandene Commits).
2. `git-pull`/`git-status`: neue `interview_workspace.git_pull`/`git_status` laufen unter `git_lock`; Zielauflösung, ausstehende Recovery und Pull-Zustand werden nach Erwerb der Sperre geprüft; der CLI-Zweig ruft sie auf.
3. `tests/native/run_native.py` `training_question`: Fragewörter wie „welche/zwei/korrekt“ gelten nur mit Meta-Objekt (Kandidat/Profil/Angaben/Vorbereitung …) oder Meta-Phrase („meinst du“, „soll ich“) als Klärung. Begrenzte Heuristik, Grenzen im Docstring und in der Entwicklerdoku.
4. Gleiche Datei, `parse_runtime_call`/`successful_calls`: nur ein einzelner, per shlex nachweisbarer Runtime-Aufruf (optional ein `sh -c`-Wrapper) mit eigenem Exitcode 0 zählt; zusammengesetzte Kommandos, Pipes, `|| true`, Variablen-Präfixe, unbekannter Status und `$VAR`-Werte zählen nicht; `job_training` verlangt passende Projekt-, Bewerber- und Job-ID.

**Tatsächlich gestartete Testkommandos** (2 von höchstens 3; Protokolle roh, ungefiltert, mit Exitcode, Fingerprints: `.tmp/tests/2026-11-19-review4/`)

| # | Kommando | Start–Ende, Dauer | Exitcode | Tests | Protokolle |
|---|---|---|---|---|---|
| 1 | `python3 -B -m unittest -v tests.integration.git.test_git_storage.ControlFilesAndPull tests.unit.test_live_and_native` | 16:23:05–16:23:20, 15,1 s | 0 | 36, OK | `cmd1-new-regressions.{stdout.log,stderr.log,record.json,fingerprints.json}` |
| 2 | `python3 -B -m unittest -v tests.integration.git.test_git_storage.Connect tests.integration.git.test_git_storage.SetupOrdering tests.integration.git.test_git_storage.Publishing tests.integration.git.test_git_storage.OwnChanges tests.unit.test_run_scenarios tests.unit.test_run_behavior` | 16:23:33–16:24:25, 52,3 s | 0 | 76, OK (enthält `Publishing.test_conflicting_change_to_same_file_is_never_overwritten_and_not_reported_saved`) | `cmd2-existing-git-and-harness.*` |

Kein Timeout, kein Abbruch; kumulierte Laufzeit ca. 67 s. Ausführung über `run_logged.py` (gleiche Datei im Ergebnisverzeichnis, Hard-Timeout 90 s, nur eigene Prozessgruppe). Mehr wurde nicht ausgeführt: nicht gelaufen sind Vertragstests, `test_cv_profile`, Workspace-Integration, übrige Unit-Tests, Szenarien, native und Live-Läufe.

**Fingerprints (SHA-256, identisch vor beiden Läufen; danach nur Dokumentation geändert)**

| Datei | SHA-256 |
|---|---|
| `skills/_shared/scripts/coach_git.py` | `4a0a3cd2d844171324b1b21792819992224afe4115c15983d79391297fe7bfae` |
| `skills/_shared/scripts/coach_core.py` | `775bfa0807d5ad541db534a3af3319d2cf35036a0f6c13821ba60cd15e746b69` |
| `skills/_shared/scripts/interview_workspace.py` | `ac92cb242620a53aaa70dd2369ea5199feaeada590bcf1b2d535f681e7ea3526` |
| `tests/native/run_native.py` | `65fc05efb60efa8040b8530b4fc67cf92926500883d2653126f75ee6f299a945` |
| `tests/integration/git/test_git_storage.py` | `fa4b8fd446f2937eef89c0129c2d23ca1fac40498be3f52e13143a163179cbc4` |
| `tests/unit/test_live_and_native.py` | `a85632723addd36e1df077fa4d5b351c03e85e3398a4844aff92387ba31a4a6e` |
| `tests/support/coach.py` | `6810f0e9968e2cb92c5020f39ea8679879256279fd8e1623e0c28d254b6a4281` |

**Status**
- Nativer Runner: **Prüflogik deterministisch geprüft** (Unit-Tests mit fiktiven Host-Ereignissen bestanden). **Kein neuer nativer Host-Nachweis**; der Runner wurde nicht ausgeführt. Folge: ein echter Lauf kann strenger scheitern, weil zusammengesetzte Shell-Kommandos nicht als Beleg gelten.
- Git-Befunde: gegen lokale Bare-Repositories mit Fake-`gh` und Identitäts-Testdouble geprüft — **keine Live-Abnahme** bei GitHub/GitLab.
- Weiterhin offen: Live-Git, Codex-Hostlauf, Recherche-Abnahme mit echter Anzeige, nativer Claude-Wiederholungslauf, vollständige deterministische Suite und Claude-Szenario-Gesamtlauf. Keine vollständige Produktabnahme.
- Restgrenzen: kooperative Sperren gelten nicht gegen Programme, die sie ignorieren; `training_question` und `parse_runtime_call` sind begrenzte Heuristiken; Identität der Git-Ziele beruht auf URL-Normalisierung.

---

# Historisch: Stand vor diesem Nachtrag

## Nachtrag 2026-11-19 15:30–15:36 — Git-Nachbesserung und nativer Testkorrektur (begrenzter Auftrag)

Dieser Nachtrag betrifft nur den unten genannten Quellstand. **Alle späteren Abschnitte dieser Datei sind historisch** für den Stand davor (insbesondere Zeilen zu B/C und `--allow-url-rewrite`, die nicht mehr existieren) und werden nicht als aktuelle Ergebnisse ausgegeben.

**Behoben (Quelle, nicht vollständig durch Tests belegt):**
1. Push-Verifikation: `publish` liest nach dem Push `targets["push"]` (nicht mehr das Fetch-Ziel), `coach_git.py` Abschnitt `publish`.
2. URL-Rewriting: `identity_of`/`check_rewrite`/`resolve_targets` verlangen für Roh- und effektive Fetch-/Push-URLs eine beweisbare Identität des autorisierten Repositorys; lokale Pfade/andere Hosts sind unbeweisbar → Ablehnung vor jeder Schreibaktion; `--allow-url-rewrite` entfernt. Tests ersetzen die Identität nur über ein Testdouble (`tests/support/coach.py`), kein Bypass im Produktivcode.
3. Eigene Änderungen: `commit_own` stagt ausdrücklich nur aufgezeichnete Pfade (`git add -- <Pfade>`, `GIT_LITERAL_PATHSPECS`), kein `git add -A`; Aufzeichnung über `coach_core.recording/touch`; Journal v2 mit SHA-256 (`interrupted.json`), geänderte Reste oder unbekannte Formate werden nie fortgesetzt; neue fremde Dateien nach der Vorprüfung brechen den Commit ab.
4. Eine gemeinsame kooperative Git-Workspace-Sperre (`.zyris/git.lock`) für Speichern und Veröffentlichen; Reihenfolge: Projektzeiger-Sperre → Git-Sperre → Workspace-/Kandidatensperren.
5. `tests/native/run_native.py` korrigiert: Erikas Profil wird vor dem Training bestätigt, Namensvetter wird zuletzt angelegt, Claude-Tool-Ergebnisse liefern Exitstatus, `job_training` verlangt erfolgreiches `job-show` und eine stellenbezogene Interviewfrage (deterministisch, kein Judge). **Korrigiert, nativ nicht erneut geprüft.**

**Tatsächlich ausgeführte Tests** (3 von 3 erlaubten Kommandos, kumuliert ca. 66 s):

| # | Kommando (Kurzform) | Start | Dauer | Ergebnis |
|---|---|---|---|---|
| 1 | `timeout 90 python3 -B -m unittest tests.integration.git.test_git_storage.OwnChanges …Connect` | 15:32:20 | ca. 8 s | 18 Tests, 11 Fehler (Ursache: `.zyris` zählte beim Setup als fremder Inhalt; behoben) |
| 2 | dasselbe | 15:32:35 | ca. 9 s | 18 Tests, 1 Fehler (veraltete Testannahme `rewritten`; behoben) |
| 3 | `timeout 90 python3 -B -m unittest tests.unit.test_live_and_native tests.integration.git.test_git_storage tests.integration.workspace.test_projects_candidates tests.integration.workspace.test_jobs_runs` | 15:34:16 | 49 s | **111 Tests, 110 OK, 1 Fehler** (Exitstatus nicht erfasst, wegen FAILED ≠ 0) |

Der eine Fehler in Lauf 3 (`Publishing.test_conflicting_change_to_same_file_…`) war ein Testkonstruktionsfehler: die lokale Änderung wurde mit `write_text` statt über einen verwalteten Schreibweg erzeugt und daher zu Recht nicht als eigene Änderung attribuiert. Der Test wurde danach auf `iw.write_atomic` umgestellt (**nicht erneut ausgeführt**; Budget der Testkommandos erschöpft). Nicht ausgeführt: Vertragstests, übrige Unit-Tests, `test_cv_profile`, Szenarien, native Läufe.

**Quellstand (SHA-256 nach den Änderungen):**

| Datei | SHA-256 |
|---|---|
| `skills/_shared/scripts/coach_git.py` | `ee83e825e6f3d257f2d34ebc3becbe61c4ca6ebc05c08afedb9a70f1bbb40a8d` |
| `skills/_shared/scripts/coach_core.py` | `775bfa0807d5ad541db534a3af3319d2cf35036a0f6c13821ba60cd15e746b69` |
| `skills/_shared/scripts/interview_workspace.py` | `5dcb56b66ae71bda1e09aed5a1e4675cba6291c600ce3e76a6c13e6e6dcfd698` |
| `tests/native/run_native.py` | `94387b8f5c11b2e41dd8b240604d039484275e7d044945559aa7aa932c7773ef` |
| `tests/integration/git/test_git_storage.py` (nach der Testkorrektur) | `d9378cff8ad0b2a3449eee327c384c618928cd45cc2a3a35add687492994b1b8` |
| `tests/support/coach.py` | `6810f0e9968e2cb92c5020f39ea8679879256279fd8e1623e0c28d254b6a4281` |
| `tests/unit/test_live_and_native.py` | `1623b748043c36db2d285b13806e00992e30e016a7c2c768ee3bc3e5ecabb69a` |

Die Hashes beziehen sich auf die Dateien nach der Testkorrektur; Lauf 3 sah `test_git_storage.py` davor. Die neuen nativen Unit-Tests (`NativeJobTrainingCheck`) liefen in Lauf 3 mit und waren grün.

**Weiterhin offen (unverändert):** Live-GitHub/GitLab, Codex-Hostlauf, Recherche-Abnahme mit echter Anzeige, nativer Claude-Wiederholungslauf nach der Korrektur, vollständige deterministische Suite, Claude-Szenario-Gesamtlauf. Verbleibende technische Grenzen: kooperative Sperren schützen nicht gegen Programme, die sie ignorieren; Identitätsprüfung der Push-/Fetch-Ziele beruht auf URL-Normalisierung (kein Provider-Aufruf je Ziel); Connector-Bestätigung bleibt weitergereichte Nutzerangabe.

---

# Historisch: Stand vor der Git-Nachbesserung

## Quellstand (Fingerprints, SHA-256 gekürzt)

| Datei / Baum | Fingerprint |
|---|---|
| `skills/_shared/scripts/interview_workspace.py` | `77d01e7d…` |
| `skills/_shared/scripts/coach_git.py` / `coach_core.py` / `coach_extract.py` | `4965b5d1…` / `2bf5e0cc…` / `802e2342…` |
| `SCOPE.md` | `af6e7b9b…` |
| Baum `skills/` / Baum `tests/` | `b343a751…` / `17ccaee5…` |

Werkzeuge: Python 3.15.0, git 2.54.0, Claude Code 2.1.319, codex-cli 0.165.0. Kein `pdftotext`, `mutool`, `pypdf`, `glab`; PDF läuft über macOS PDFKit/`swift`.
Nach den letzten Doku-/Harness-Änderungen wurde **die vollständige deterministische Suite nicht erneut ausgeführt** (Testlaufverbot der laufenden Sitzung).

## 1. Deterministisch geprüft (tatsächlich ausgeführt)

| Lauf | Kommando | Ergebnis |
|---|---|---|
| Gesamtsuite (vor den letzten Änderungen) | `python3 -B scripts/run_tests.py --kind deterministic` | 184 Tests, OK, 1 übersprungen (damals echte PDF-Extraktion) |
| Integration inkl. Git, Workspace, CV (danach) | `--kind integration` | 111 Tests OK, 1 übersprungen → danach PDF-Tests ergänzt: `--group workspace` 75 Tests OK, 0 übersprungen |
| Unit (zuletzt) | `--kind unit` | 46 Tests OK |
| Verträge | `--kind contracts` | zuletzt in der 184er-Gesamtsuite OK; **nach den Doku-Änderungen nicht neu gelaufen** |
| Manifeste | `scripts/plugin.py check` | gültig (vor den Änderungen) |
| Statischer Scope-Check | `verify.py --source . --review` | siehe Abschnitt 6 |

Git-Tests (`tests/integration/git`, 41 Tests, zuletzt grün) laufen gegen lokale Bare-Repositories, Fake-`gh`, protokollierenden `git`-Wrapper:
**keine** Live-Abnahme von GitHub/GitLab. Echte PDF-Extraktion ist auf macOS über PDFKit geprüft (Original-Bytes, Text, Herkunft, Textebene fehlt → `partial`, leere Seite → Warnung, defektes PDF → abgelehnt); auf Hosts ohne Werkzeug bleibt sie NOT RUN.

## 2. Befunde A–D

| Befund | Behebung | Nachweis |
|---|---|---|
| A Speicherwechsel zu spät | `setup_project`: schreibgeschützte Vorprüfung (Wechsel von Ziel/Speicherart/Repository, ungültiger Zeiger, fremder Inhalt) vor Verzeichnis-, Klon-, Config-, Remote-Aktion; Wiederholung unter Projekt-Sperre | `SetupOrdering`, `ProjectResolution` (grün) |
| B Zielbindung Git | `resolve_targets`, `verify_target`, `publish(targets)`: Fetch/Push-URL (origin, pushurl, mehrere Ziele, Rewriting) an autorisiertes Repo gebunden und gepinnt; aktuelle Privatheits-/Rechteprüfung je Publish; Connector-Bestätigung nennt Repo, trägt Nutzerbestätigung, wird nie als Beweis gespeichert; Verifikation liest Push-Ziel | `Publishing`-Tests origin/pushurl/mehrere Ziele/Rewriting/public/Rechte/Attest (grün) |
| C `git add -A` | `publish` stagt nie; Speicherbefehle verlangen sauberen Baum (`baseline`) und committen nur eigene Änderungen (`commit_own`); Reste fehlgeschlagener Speicherung via `.zyris/interrupted.json` | Tests fremde/gestagte/verwaltete Dateien, Adoption, Publish ohne Staging (grün) |
| D Profilbestätigung | SCOPE R7/R14, `cv-profile.md`, `research.md`, `candidate-selection.md`, Skills, Doku bereinigt; Runtime lehnt `match` ohne `confirmed` ab; `profile_reliable` im Status | `ProfileReliability` (grün) |

Grenzen: Eigene-Änderungen-Zuordnung setzt voraus, dass während eines Speichervorgangs niemand im Arbeitsbaum schreibt. Connector-Bestätigungen sind weitergereichte Nutzerangaben, kein unabhängiger Beweis.

## 3. Modellbasierte Szenarien (heuristisch; angemeldete CLI, Host-Tools aus, temporäres Projekt)

Ergebnisdateien unter `.tmp/tests/scenarios/run-2026-11-19{a,b,c,d,e}-<cli>/` (lokal, ignoriert, unverändert erhalten; frühere Fehlversuche nicht umgeschrieben).

| Lauf | Harness-Stand | Claude | Codex |
|---|---|---|---|
| a (erste Läufe; Codex-Ordner `codex-all`) | Wortlisten | 13/13 *erst nach Nachbesserung von 4 Szenarien*; Erstlauf 9/13 | 8/13 |
| b | + Struktur/Judge | 9/15 | 7/15 |
| c | Rubrikwortlaut präzisiert, Antworten generisch | 12/15 | 8/15 |
| d | Judge-Zitatprüfung, Einzel-Rückfrage-Rubrik | 14/16 (Lauf vollständig) | 10/16 |
| e | Codex `workspace-write` statt `read-only` | nur `research_fixture_namesake` PASS (1/1) | **15/16** (Lauf vollständig) |

Einordnung der fünf ursprünglichen Codex-Fehler (Lauf a/`codex-all`):
1. `candidate_create_without_cv` – Antwort las Angaben zurück und fragte „vollständig und korrekt?“: **Produkt ok, Testfehler** (Wortanker „Entwurf/bestätig“).
2. `general_training_answer` – Gesamtbewertung, Einzelkriterien, konkrete Hinweise vorhanden, nur „verbessern/Verbesserung“ fehlte: **Testfehler**.
3. `job_create_missing_company` – Unternehmen gespeichert, Teilnehmer erfragt: **Testfehler** (Wortanker „Interview“).
4. `job_training_reuse_second_run`, 5. `stop_pause_resume` – Rückfrage statt Note bei unpassender/zu unkonkreter Antwort: **teils Testfehler** (skriptierte Antwort passte nicht zur vom Modell gewählten Frage; berechtigte Rückfrage laut evaluation.md). Daraus: getrennte Szenarien für bewertbare vs. unzureichende Antworten.

Weitere Befunde der Läufe: (a) Codex unter `--sandbox read-only` meldet „kein Schreibzugriff“ und umgeht den Tool-Kanal – Harness-Störfaktor, deshalb Lauf e; (b) Claude gab eine Formulierung mit nicht genannten Angaben („stabile Produktionssysteme“) – **echte Abweichung**, `evaluation.md` nun explizit (`[ergänzen: …]`); (c) Rubrik-Judge ist ein Modell und irrt (Fehlurteile bei `no_attribution`, `no_invention`, `one_question` beobachtet; Zitatprüfung/Rubrikpräzisierung als Gegenmaßnahme); (d) Claude `stop_pause_resume` (Lauf d): Fortsetzungs-Artefakte korrekt (Vorgänger, Zähler, unveränderter Checkpoint), aber Judge meldete zwei Fragen in einem Turn und `no_invention` – nicht abschließend bewertet.
Offen in Lauf e (Codex): `job_training_reuse_second_run` FAIL `reuses_research` (die Antwort nannte die Ausschreibung, nicht die gespeicherte Recherche).
**Kein vollständiger Claude-Lauf nach der letzten Rubrik-/Harness-Änderung** (nur 1 Szenario in e); Lauf d für Claude entstand mit dem Vorstand der Rubrik.

## 4. Bestehende Modellsuiten (`make test-behavior|test-smoke|test-journey`; Prompts mit gehärtetem `run()`: leeres Temp-Verzeichnis, Tools aus)

| Suite | Claude | Codex |
|---|---|---|
| behavior | 4/5 (FAIL `stop_without_storage`, Wortanker „eine Frage“) | 5/5 |
| smoke (erster Lauf) | FAIL `coding` – Prompt verwies auf `tests/fixtures`, die das Modell nach der Härtung nicht lesen konnte (Harness-Regression durch mich) | FAIL `coding`, `no_invention` (gleiche Ursache) |
| smoke (nach Fixture-Inlining, Lauf `legacy-2026-11-19b`) | 3/3 | 3/3 |
| journey | 4/5 (FAIL `revision`: Warnregex; Antwort enthält die Vorsicht sinngemäß) | 3/5 (FAIL `revision`, `stop`; Wortregex) |

Die alten Journey-/Behavior-Heuristiken wurden **nicht** an die Ausgaben angepasst; die Fehlschläge bleiben stehen.

## 5. Nativ im Host beobachtet

| Host | Was | Ergebnis |
|---|---|---|
| Claude Code 2.1.319 | `claude plugin validate` auf Payload-Kopie | bestanden mit Warnungen (Version fehlt bewusst; README fehlte in der Kopie) |
| Claude Code | `tests/native/run_native.py --host claude` (`--plugin-dir` auf Payload-Kopie, neue Chats je Phase, isoliertes Temp-Projekt, angemeldete CLI) | **10/12 Phasen**: Skill-Erkennung (alle fünf `interview-coach:*`), drei Optionen, Setup, Bewerber mit CV (Original byte-gleich), ohne CV unbestätigt, Bestätigung im neuen Chat, gleichnamige Auswahl, Speichern + Wiederaufnahme im neuen Chat, Nicht speichern ohne Schreibaktion: PASS. `job_create`, `job_training`: FAIL – **Runner-Reihenfolgefehler**: die Phase `same_name_selection` legte einen zweiten „Erika Beispiel“ an, das Modell fragte korrekt nach; Profil zudem nur Entwurf. Nicht wiederholt |
| Claude Code | Research mit echter Anzeige (`--research`) | **abgebrochen/NOT RUN**: Lauf wurde auf Anweisung gezielt beendet, keine Ergebnisse |
| Codex 0.165.0 | Skill-Erkennung über projektlokale `.agents/skills` (Probe, manuell) | Skills erkannt, Runtime aus Payload-Layout ausgeführt; **nur eine Einzelprobe, kein Phasenlauf** |
| Codex | `run_native.py --host codex`, Research, Plugin-Installation über Marketplace | **NOT RUN** |

Isolierte Profile ohne Anmeldung können kein Modell aufrufen (`Not logged in`). Alle Läufe nutzen die vorhandene Anmeldung der Host-CLI (keine Credentials gelesen/kopiert).

## 6. Statischer Review

Getrennt von allen Testläufen, nur lesend (`verify.py --source . --review`, kein Zielcode ausgeführt): `structure_valid: true`, `ready_for_source_review`, keine Evidenzbefunde — das bedeutet nur, dass die Evidenzdateien lesbar sind.
Agentenseitige statische Durchsicht (ohne Ausführung) der Korrekturen: Runtime, Skill-Anweisungen (`setup.md`, `storage.md`, `runtime.md`, `cv-profile.md`, `job-create`, `job-training`, `candidate-training`), SCOPE R1/R7/R14/R19 und Doku widersprechen sich nach Textsuche nicht (Vertragsphrasen aus `test_skill_contract.py` sind noch vorhanden; die Tests selbst wurden danach **nicht** ausgeführt). Nicht per Review belegbar: Modellverhalten, Host-Verhalten, Live-Provider.
Nach dem Hostlauf wurde `tests/native/run_native.py` korrigiert (Phase `same_name_selection` jetzt nach den Stellenphasen) — **ungetestet, nicht erneut gelaufen**.

## 7. Offen / NOT RUN

- Codex nativer Phasenlauf, Codex-Research, Claude-Research mit echter Anzeige (Rechercheabnahme E), Wiederholung der zwei fehlgeschlagenen Claude-Phasen nach Runner-Korrektur.
- Live-GitHub/GitLab (`tests/live/run_live_git.py`, nur Trockenlauf-Test): braucht Freigabe eines privaten Test-Repositories, Testbranch, Schreibaktionen.
- Erneute vollständige deterministische Suite nach den letzten Änderungen; Claude-Szenario-Gesamtlauf mit finalem Harness.
- Nicht belegt: Aufrufsyntax `$skill` in Codex als Plugin (nur projektlokale Skills probiert); Marketplace-Installation beider Hosts.
- Nicht erzwungen durch Runtime: „Nicht speichern“ ohne Runtime-Aufruf, Trennung state/match (Skill-Text + Szenarien).

## 8. Nachtrag: begrenzte lokale Claude-Code-Hostabnahme (2026-11-19, einmalig, 10-Minuten-Budget)

Quellstand: HEAD `47f45f2` plus umfangreiche uncommittete Änderungen. Claude Code 2.1.319, angemeldete CLI. Ladeverfahren: `claude -p /interview-coach:<skill> --plugin-dir <Payload-Kopie> --setting-sources project --tools Skill,Bash,Read,Write --disallowedTools WebFetch WebSearch --strict-mcp-config --no-session-persistence`, temporäres Projekt, fiktive Daten, keine Installation, keine Web-/Git-Aktion. Eigener Wrapper (nicht der bestehende `run_native.py`, der erst am Ende schreibt); Produktcode und Tests unverändert.
Protokolle (lokal, ignoriert): `.tmp/tests/hostacc-20261119-173233/` (`00-setup.json` mit SHA-256-Fingerprints, je Phase `prompt.txt`, `command.txt`, `raw.jsonl`, `meta.json`, `artifacts.json`). Phase I lief parallel zu A–H (unabhängiger leerer Kontext), jede Phase genau einmal, ohne Wiederholung. Phase G war ein neuer Chat; die tatsächlich gestellte Frage aus F wurde per Wrapper in den Prompt übernommen.

| Phase | Ergebnis | Evidenz |
|---|---|---|
| A Erkennung/Einstieg | PASS | init-Event: alle fünf `interview-coach:*`; genau Lokal/Git/Nicht speichern; Projekt danach ohne Workspace |
| B Lokales Setup | PASS | `project-init` exit ok; `workspace.json` schema_version 3, `.journal/lock`, kein `.zyris`; `validate` rc 0; Pfad korrekt gemeldet |
| C Bewerber mit CV | PASS | `cv-001/original.md` SHA-256 identisch zur Quelle; `extracted.md`; Profil `draft` |
| D Profilbestätigung | PASS | `profile_status: confirmed`, genau eine Erika |
| E Stelle ohne Web | **FAIL (Zeit)** | Phase-Timeout 55 s, Host beendet; Artefakte vorhanden (Job, Ausschreibung byte-gleich, Teilnehmer `unknown`, Research „keine Webrecherche“, Match, Preparation), aber keine Abschlussantwort; kein PASS ohne vollständigen Lauf |
| F Stellenbezogenes Training | PASS | `job-show` für richtige Bewerber/Stelle ohne Fehler; konkrete Python-API-Frage, offene Punkte benannt |
| G Antwort/Stop | **FAIL (Produktbefund)** | Feedback bezieht sich auf die Antwort, aber **0 Werkzeugaufrufe**: kein Run, kein Lernstand; Antwort behauptete, es sei „keine Speicherart gewählt“, obwohl lokal eingerichtet (`state.md`: „no completed runs“, `runs/` leer) |
| H Neuer Chat | **BLOCKED/teilweise** | Bewerber und Stelle korrekt wiedergefunden, nichts neu angelegt; Run nicht auffindbar, weil G keinen speicherte |
| I Nicht speichern | PASS | leeres Projekt blieb leer (nur zwei `Read` auf Referenzen, kein Runtime-Aufruf); Sitzungsartefakte des Hosts nicht als Plugin-Schreibaktion gewertet |

Befund (Produkt, vorläufig): `job-training` in einem neuen Chat prüft bei bereits gelieferter Frage/Antwort die Projektkonfiguration nicht und speichert nichts. Offen: ob das am direkt mitgelieferten Frage-/Antwort-Prompt liegt (Testdesign) oder ein Skill-Defekt ist; nicht diagnostiziert, nicht repariert. Zeitbudget: E war mit 55 s zu knapp.
Grenzen: eine Beobachtung je Phase, Modellverhalten nicht deterministisch, kein Codex, keine Recherche mit Web, kein Git, keine Marketplace-Installation. **Keine vollständige Produktabnahme.**

## 9. Nachtrag 2026-11-19 (zweiter, gezielter Hostlauf E, F→G, H; nach Befundkorrektur)

Historische Fehlschläge aus Abschnitt 8 bleiben unverändert gültig für den damaligen Stand.

**9.1 Implementierte Korrekturen.** `job-training/SKILL.md`: Projekt wird per `project-show` geprüft (nicht aus dem Chat gefolgert), auch bei mitgelieferter Frage/Antwort; Stelle allein ist keine Fortsetzung; mitgelieferter Austausch wird als Run gespeichert, „gespeichert“ erst nach erfolgreichem `finish`; „Nicht speichern“ unverändert ohne Runtime. `candidate-training` analog (kurz). Offene Punkte getrennt in Datensatzlücken (`open_points`) und Recherchelücken (`job-create`, `job-training`, `job-preparation.md`, `interview-coach`). `runtime.md`: einzelne direkte `python3`-Aufrufe, Referenzen per Read. `storage.md`/`session-control.md`: Beispiele auf `schema_version` 3 (Ablehnungstexte zu Format 1/2 bewusst unverändert). Neu: `tests/native/run_host_acceptance.py` (echte Sitzungsfortsetzung per `--session-id`/`--resume`, F und G gleiche Sitzung, H neue; Deadline, Abhängigkeiten, sofortige Protokolle; ohne Sitzungsunterstützung BLOCKED) und `tests/unit/test_host_acceptance.py`. Die Sonderfall-Prüfung „neue Sitzung mit vorgegebener Frage/Antwort“ erfolgte nur statisch (Anweisungstext), kein Hostfall.

**9.2 Deterministische Tests (tatsächlich ausgeführt, Ausgaben `.tmp/tests/det-20261119/`).** `test_skill_contract` 16 OK, `test_scope` 2 OK, `test_distribution_contract` 4 OK, `test_host_acceptance` 22 OK (vor dem Lauf) und 23 OK (nach Korrektur der Antwortwahl), je Exit 0, alle < 10 s. Hostaufrufe gemockt (lokales Fake-Skript).

**9.3 Beobachtetes Hostverhalten** (Claude Code 2.1.319, ein Lauf, 147 s von 600 s; Belege `.tmp/tests/hostacc2-20261119-174833/`, Urteile `VERDICT.md`, Prüfungen je Phase `checks.json`):

| Phase | Status | Kern |
|---|---|---|
| E | PASS | exit 0 in 55,9 s; Stelle bei richtiger Bewerberin; Original byte-gleich; Teilnehmer `unknown`; Recherchverzicht gespeichert; Match/Preparation vorhanden; Antwort nennt „nicht vollständig recherchiert“ |
| F | PASS | Sitzung 54408b12…; `job-show` OK; konkrete API-Frage; Recherchelücken benannt |
| G | **FAIL (Testfehler)** | Gleiche Sitzung belegt, `finish` OK (Bewerberin+Stelle, stopped_early, 1 Antwort, ein Run, kein Plan), Speicherbestätigung wahrheitsgemäß, keine Folgefrage. Aber der Wrapper wählte die Antwort anhand der gesamten F-Antwort (Betriebs-Antwort statt zur API-Frage passend); Kriterium „Antwort passt zur Frage“ verfehlt. Wrapper danach korrigiert (`extract_question`), **nicht erneut gelaufen** |
| H | PASS (Wiederladen) | neue Sitzung a0ddda81…; Run `run-20261119-targeted-001` gelesen und wiedergegeben; Lernstand Baseline/offen; keine Hash-Änderung (ohne `.journal`); Recherchelücken benannt. Der Run enthält die unpassende G-Antwort |

Die Speicherentscheidungs-Korrektur (Befund 1) ist im F→G-Ablauf beobachtet (Host rief `finish` auf); der Sonderfall „neue Sitzung mit mitgelieferter Frage/Antwort“ ist **nicht** per Host belegt.

**9.4 Offen.** G mit passender Antwort (Wrapper-Korrektur ungetestet im Host); mitgelieferte Frage/Antwort in neuer Sitzung (Host); Zeilen-Review der gespeicherten Match-/Preparation-Inhalte; Codex, Webrecherche, Live-Git, Marketplace; keine vollständige Produktabnahme.

## 10. Nachtrag 2026-11-19 (Evidenzeinstufung, Wrapper v3, gezielter Hostlauf E und F→G)

Historische Befunde aus Abschnitt 8 und 9 bleiben für ihren Quellstand unverändert gültig (insbesondere G-Funktionsbelege, F→G-Sitzungsfortsetzung, H-Wiederladen); sie werden hier nicht zurückgesetzt.

**10.1 Implementierte Änderungen.**
- Evidenzeinstufung: `job-preparation.md` Schritt 7 (maßgeblich), `research.md`, `job-create`, `job-training`. *Direkt belegt* nur für die vollständige Anforderung inkl. Dauer/Umfang; Backend-Jahre plus Python-Skill belegen nicht dieselben Python-Jahre; nicht genannte Erfahrung = *unbelegt/zu klären*, nicht „fehlt“; *bestätigte Lücke* nur nach Bestätigung durch die Bewerberin; Fähigkeitslücke und Nachweislücke getrennt; Priorisierung eines unbelegten Themas als Klärungsbedarf; keine Widersprüche zwischen Profil, Match, Vorbereitung, Abschlussantwort; keine erfundenen Fakten. Alte Snapshots unverändert.
- `tests/native/run_host_acceptance.py` (Wrapper v3, gestuft: `prepare`, `evidence`, `review-evidence`, `ask`, `check-answer`, `answer`, `review-answer`, `reload`, `status`; eine absolute Deadline in `state.json`, Wartezeit zählt): `choose_answer`/Schlüsselwortauswahl entfernt; F-Frage samt Teilfragen gesichert (`extract_question` liefert Block und Mehrdeutigkeit); Antwort nur nach geprüftem Passungsreview (`validate_answer_fit`: Hash-Bindung an Frage und Antwort, wörtliche Zitate, jede Teilfrage zugeordnet, verlangte Teile Beispiel/eigene Entscheidung/Rückblick abgedeckt, Echo der Frage zählt nicht), sonst G BLOCKED, kein Ersatztext; Identitätsprüfungen `ok_identity` (Projekt + Bewerber + Job gleichzeitig; finish zusätzlich Projekt; status/project-show gebunden), `session_identity_ok`/`check_h_session` (angeforderte ID muss in den Hostereignissen erscheinen, H ≠ F/G); getrennte Urteile `automatic` und `domain` (`final_verdict`: automatisch PASS ohne fachliche Prüfung = UNREVIEWED); Exitcode 0 nur bei PASS (1 FAIL, 2 BLOCKED/NOT RUN, 3 UNREVIEWED); Fingerprints je Hostphase (Quell- und Payload-Skills, Wrapper) und `status` meldet, ob der Quellstand seit dem Hostlauf unverändert ist (`evidence_current`).
- Fachliche Reviews werden als JSON mit Kriterien und wörtlichen Zitaten aus den Artefakten erfasst (`validate_review` prüft nur, dass Zitate existieren und Kriterien vollständig sind, nicht die Richtigkeit des Urteils).
- Nach dem Hostlauf ergänzt: `promotion_lines` (siehe 10.3, G). Diese Änderung ist nicht hostgeprüft.

**10.2 Deterministische Tests (ausgeführt, Hostaufrufe gemockt, keine Modelle; Belege `.tmp/tests/det-20261119c/*.meta.json|stdout|stderr`).** `test_host_acceptance` 39 Tests OK (7,6 s), nach der G-Korrektur 40 OK (7,6 s); `test_skill_contract` 16 OK, `test_scope` 2 OK, `test_distribution_contract` 4 OK, `test_run_behavior` 8 OK; je Exit 0, Limit 60 s, Gesamtzeit unter 20 s. Abgedeckt: falsches/fehlendes Projekt, Bewerber oder Job trotz erfolgreichem Werkzeugresultat; fehlende/falsche/widersprüchliche Sitzungs-ID, H-Sitzung; Frage mit mehreren Teilfragen und Themenwörtern; unpassende Antwort → BLOCKED; automatisch vs. fachlich (UNREVIEWED, Exitcodes); Review-Validierung. Es gibt keinen Test, der eine Textphrase der Anweisungen als Verhaltensbeweis wertet.

**10.3 Beobachtetes Hostverhalten** (Claude Code 2.1.319, ein Fenster, 181 s von 600 s, keine Wiederholung, keine eigenen Prozesse übrig; Belege `.tmp/tests/hostacc3-20261119-b/`, Zusammenfassung `VERDICT.md`, `state.json`, je Phase `checks.json`, `meta.json`, rohe `*.stdout.jsonl`/`*.stderr.txt`).
| Block | Urteil | Beleg |
|---|---|---|
| A: E job-create, Evidenzeinstufung | **PASS** (automatisch PASS, fachlich PASS) | 62,0 s/120 s. Match: „5+ Jahre Python“ = übertragbar, Dauer/Anteil zu klären; Cloud, Kubernetes, Mentoring, Senior = unbelegt/zu klären; „Direkt belegt: keine“; „Bestätigte Lücken: keine“; Evidenzlücken getrennt; Vorbereitung priorisiert Kubernetes als „Klärungsbedarf: Nachweis fehlt“; Abschlussantwort konsistent („Was fehlt, sind Nachweise, kein bewiesenes Defizit“). `E/domain-review.json` (6 Kriterien, Zitate wörtlich verifiziert) |
| B: F Frage | PASS (nur Vorbereitung) | 27,6 s/60 s; job-show/status/project-show mit Projekt+Bewerber+Job; eindeutiger Fragenblock (Aufgabe, Entscheidungen, Ergebnis) `F/question.json` |
| B: Antwortpassung vor G | PASS | `B/answer-fit-result.json`, fiktive Antwort `B/answer.txt`, Review gegen alle Teilfragen |
| B: G Antwort + stop (gleiche Sitzung) | **FAIL (automatisch, Wrapper-Falschpositiv)** | 36,6 s/120 s. 8 von 9 automatischen Prüfungen OK (finish für Projekt+Bewerber+Job, stopped_early, 1 Antwort, ein Run, kein Plan, Run-ID in Antwort). Fehlgeschlagen: „state.md ohne improving/stable-Zeile“, weil das Wort „improving“ in einem Satz steht („…bevor eine Kompetenz als improving gilt“); alle Kompetenzen stehen auf `open`. Manuelle fachliche Prüfung (außerhalb des Gates, `G/manual-domain-review.json`): Feedback bezieht sich auf die Antwort, keine erfundenen Fakten, keine Folgefrage, Run/Lernstand passen zum Stop, Speicherbericht wahr. Das Urteil bleibt **FAIL**, nicht auf PASS angehoben, nicht wiederholt |
| H | NOT RUN | nicht Teil dieses Auftrags; Sitzungsprüfung nur deterministisch |

Hostbeleg und Quellstand: Die Hostphasen liefen gegen Skills-Fingerprint `ac4835b6…` (unverändert bis zum Statuslauf) und Wrapper `a249e7e4…`. Der Wrapper wurde danach geändert (`9b215711…`); die Korrektur gilt nicht als hostgeprüft. Jede weitere Änderung an `skills/` macht diese Beobachtung für den neuen Stand ungültig (`status` weist das aus).

**10.4 Offen.** G mit korrigierter Statusprüfung im Host (nicht wiederholt, laut Auftrag); mitgelieferte Frage/Antwort in neuer Sitzung (Host); H nach dem neuen Stand; Zeilen-Review weiterer Stellen/Szenarien; Codex, Webrecherche, Live-Git, Marketplace. Der fachliche Review ist ein einzelnes Urteil eines Lesers, kein unabhängiges Gutachten. **Keine vollständige Produktabnahme.**


## 11. Nachtrag 2026-11-19 (Offline-Neubewertung des vorhandenen G-Hostlaufs; kein neuer Hostlauf)

Der historische Hostlauf (Abschnitt 10.3, `.tmp/tests/hostacc3-20261119-b/`) und das damalige **G-FAIL** des Wrappers a249e7e4… bleiben unverändert stehen.

**11.1 Fehlalarm des damaligen Auswerters.** Die Prüfung „state.md ohne improving/stable-Zeile“ wertete das bloße Wort „improving“ in dem Satz „Weitere Antworten in anderen Szenarien nötig, bevor eine Kompetenz als improving gilt.“ als Kompetenzaufwertung. Dieser Satz verneint die Aufwertung; alle Kompetenzen (C08, C03, C07) stehen auf `open`. `promotion_lines` zählt seither nur Zeilen, die einen Status zuweisen (`: improving|stable`).

**11.2 Offline-Neubewertung** (Protokoll: [.tmp/tests/offline-reeval-g-20261119/PROTOKOLL.md](../.tmp/tests/offline-reeval-g-20261119/PROTOKOLL.md); Rohdaten `cmds/`, Skript `reevaluate.py`; Gesamtlaufzeit der Befehle 0,15 s, Limits 30/120 s, keine Timeouts). Ausgeführt: die tatsächliche Funktion `promotion_lines` auf den gespeicherten hinzugekommenen Lernstandszeilen und dem vollständigen Lernstand, Neuprüfung der übrigen automatischen Kriterien aus den G-Rohereignissen und Artefakt-Hashes, der einzelne Regressionstest `LearningState.test_only_status_assignments_count_as_promotion` (1 OK). Keine Testsuite, kein Host, kein Modell.
- Quellstand: Skills-Fingerprint damals und aktuell identisch (`ac4835b6…`, 20 Dateien, keine Abweichung pro Datei); nur der Wrapper unterscheidet sich (damals `a249e7e4…`, aktuell `9b215711…`; vollständige Werte im Protokoll).
- Ergebnis: `promotion_lines` liefert für die fehlinterpretierte Zeile und für den gesamten Lernstand `[]`; keine Kompetenz `improving`/`stable`. Sitzung = F-Sitzung (alle Events), genau ein erfolgreicher `finish` für Projekt, Bewerberin und Stelle, `stopped_early`, 1 Antwort, kein Plan, ein Run.
- Fachliche Prüfung (eigenständig, Frage/Antwort/Feedback/Run/Lernstand): bestanden.

**11.3 Einstufung.** Korrigierte Auswertung **PASS** und fachliche Prüfung **PASS**: Der vorhandene G-Hostlauf gilt damit als fachlich und anhand der korrigierten Auswertung **bestanden**. Der aktuelle Wrapper ist **nicht** erneut im Host gelaufen; der Beleg ist die deterministische Neubewertung gespeicherter Daten.

**11.4 Abgrenzung.** E und F werden nicht neu abgenommen (Stand Abschnitt 10.3 gilt). H wird nicht als Voraussetzung neu geöffnet: Wiederladen wurde separat belegt (Abschnitt 9.3), die verschärfte Identitätsprüfung deterministisch getestet. Der Sonderfall „neue Sitzung mit mitgelieferter Frage/Antwort“ ist durch F→G **nicht** hostgeprüft. Codex, Webrecherche, Live-Git und Marketplace liegen außerhalb dieses Nachtrags. Die fachliche Prüfung ist das Urteil eines einzelnen Lesers. **Keine vollständige Produktabnahme.**


## 12. Nachtrag 2026-11-19 (Sonderfall: `job-training`, neue Sitzung, mitgelieferte Frage und Antwort)

Historische Abschnitte 8–11 bleiben unverändert; E/F/G/H wurden nicht wiederholt. Genau ein neuer Claude-Code-Hostaufruf (2.1.319, `--plugin-dir` auf isolierte Payload-Kopie, `--session-id 35b79dc9-549c-425f-a2d8-9d71983e77c1`, kein resume/continue), Prompt `/interview-coach:job-training Für Erika Beispiel und die gespeicherte Stelle bei Beispiel AG: Die Interviewfrage lautet … Meine Antwort: … Bewerte meine Antwort und beende das Training mit stop.` ohne Speicherpfade, Runtime-Befehle oder Skill-Text. Fixture deterministisch über die Runtime (lokal, Format 3, Erika Beispiel, bestätigtes Fixture-Profil, Stelle Beispiel AG, Rechercheverzicht, Interviewende unbekannt, Match/Vorbereitung ohne erfundene Erfahrung, keine Runs); sie ist Testfixture, keine Hostabnahme.

Belege: [.tmp/tests/2026-11-19-jt-new-session-given-qa/VERDICT.md](../.tmp/tests/2026-11-19-jt-new-session-given-qa/VERDICT.md) (dazu `host.stdout.jsonl`, `host-tools.json`, `auto-checks.json`, `auto-check-7-recheck.json`, `learned-run.md`, `learned-state.md`, `harness.py`, `evaluate.py`).

**Ergebnis: PASS** (automatisch PASS, fachlich PASS). Host 63,7 s von 120 s, Exit 0, kein Timeout, Prozess beendet; Gesamtauswertung etwa 2,5 Minuten von 300 s. Der Skill ermittelte die vorhandene lokale Konfiguration selbst (`project-show` für genau dieses Projekt), lud Bewerberin, Stelle (`job-show`), Profil und Lernstand (`status`), richtete kein neues Setup ein, bewertete die gelieferte Antwort ohne erfundene Fakten, stellte nach stop keine Frage und speicherte mit genau einem `finish` (Projekt, Bewerberin, Stelle, `stopped_early`, answered_count 1, kein Plan) einen Run; Lernstand nur `open`/Baseline, keine stellenspezifische Lücke als allgemeine Schwäche. Diff: nur neuer Run und `state.md`.

**Anmerkungen.** Harness-Prüfung 7 zählte zunächst `finish --help` mit und wurde per dokumentierter Neuprüfung korrigiert (Harnessfehler, kein Produktbefund). Die Pointer-Datei der Fixture wurde vor dem Hostaufruf in das vom Host genutzte Konfigurationsverzeichnis verschoben. Das fachliche Review ist das Urteil eines einzelnen Lesers. Damit ist der Sonderfall „neue Sitzung mit mitgelieferter Frage/Antwort“ (offen in 9.4/10.4/11.4) für `job-training` geschlossen. **Keine vollständige Produktabnahme**; Codex, Webrecherche, Live-Git und Marketplace bleiben separat.


## 13. Nachtrag 2026-11-19 (begrenzte Codex-Hostabnahme: BLOCKED)

Historische Abschnitte bleiben unverändert; die lokalen Claude-Code-Abnahmen (E–H, G, Sonderfall Abschnitt 12) wurden nicht wiederholt. Beleg: [.tmp/tests/codex-host-20261119-183555/VERDICT.md](../.tmp/tests/codex-host-20261119-183555/VERDICT.md) (CLI-Ausgaben `cmds/`, Fingerprints `fingerprints.txt`).

**Ergebnis: A, B und C BLOCKED; kein Hostaufruf, kein Modelllauf.** codex-cli 0.165.0, angemeldet (ChatGPT). Gesamtdauer rund 3 Minuten von 600 s, keine eigenen Prozesse gestartet.

**Grund.** Die lokale CLI-Hilfe bietet kein Flag, das ein Plugin-Verzeichnis nur für einen Aufruf lädt (kein Gegenstück zu Claude Code `--plugin-dir`). Der dokumentierte Weg für das Plugin ist `codex plugin marketplace add` plus `codex plugin add interview-coach@draftmode-ai-plugins` (Aufruf `$interview-coach`, `$candidate-create`, `$candidate-training`, `$job-create`, `$job-training`); beides ist Installation und ändert die globale Konfiguration und war ausgeschlossen. Ohne Installation bleibt nur projektlokale Skill-Ladung (`.agents/skills`, wie `tests/native/run_native.py`); sie ist keine native Plugin-Ladung und wurde nicht als Ersatz gefahren. Umgebung: `codex plugin marketplace list` scheitert an einem fremden, defekten Marketplace-Eintrag, `codex plugin list` lief in ein 20-s-Timeout; nicht repariert.

**Unterscheidung.**
- Native Verfügbarkeit der fünf Skills im Codex-Host: **nicht belegt** (nur Manifest `.codex-plugin/plugin.json` mit `skills: ./skills/` und fünf SKILL.md statisch vorhanden).
- Beobachtete Abläufe A/B/C: **keine**.
- Fachliche Abläufe der übrigen Skills: nicht geprüft.
- Plugin-Ladung gegenüber Marketplace-Installation: Plugin-Ladung ohne Installation ist in Codex 0.165.0 nicht vorgesehen; nur eine autorisierte Marketplace-Installation (am besten mit eigenem `CODEX_HOME`) oder bewusst als solche deklarierte projektlokale Skills können weitergehen.
- Weiter offen: Codex-Hostabnahme A/B/C, Recherche (Web), Live-Git, veröffentlichte Marketplace-Installation. **Keine Codex- oder Produktabnahme.**


## 14. Nachtrag 2026-11-20 (Codex-Ladeweg geklärt, nur CLI-Hilfe; A/B/C weiter BLOCKED)

A, B und C aus Abschnitt 13 bleiben **BLOCKED und wurden nicht ausgeführt**. Es fanden neun CLI-Hilfeabfragen statt (codex-cli 0.165.0; alle Exit 0, kein Timeout, insgesamt 0,1 s), aber **keine Trainings- oder Modellläufe**, keine Installation, Anmeldung oder Konfigurationsänderung. Belege (vollständige stdout/stderr, Zeiten, Exitcodes): [.tmp/tests/codex-loadpath-20261120-080250/](../.tmp/tests/codex-loadpath-20261120-080250/VERDICT.md), `log.json`.

**Gesichert (Hilfeausgaben).** `codex plugin` kennt nur `add`, `list`, `marketplace`, `remove`; keine Hilfe nennt einen nur für einen Aufruf geltenden Plugin-Ladeschalter (`codex --help`, `codex exec --help`, `codex plugin --help`). `plugin add` = „Install a plugin from a configured or remote marketplace“; `plugin marketplace add` = „Add a local or Git marketplace to the configured marketplace sources“. `codex exec --ignore-user-config`: „Do not load $CODEX_HOME/config.toml; auth still uses CODEX_HOME“. `codex login` bietet `--device-auth`, `--with-api-key`, `--with-access-token`, `status`.

**Ungeprüft.** Ob `-c`-Überschreibungen Marketplaces/Plugins pro Aufruf setzen können (Schlüssel nicht dokumentiert); ob ein bereits installiertes Plugin nutzbar ist (nur über Listen/Konfiguration prüfbar, nicht angefasst); ob `plugin add`/`marketplace add` unter einem eigenen `CODEX_HOME` vollständig isoliert; ob dort Anmeldung ohne Kopieren von Zugangsdaten gelingt. Ein fehlender Schalter in einer Hilfe beweist nicht, dass kein anderer Weg existiert.

**Abgrenzung.** Native Plugin-Ladung (Marketplace + `plugin add`) ist ein anderer Weg als projektlokale Skills (`.agents/skills`); letztere sind kein Ersatz für die Plugin-Abnahme. Die historischen Dauerangaben zu Abschnitt 13 (60 s im Protokoll, „rund 3 Minuten“ im Nachtrag) widersprechen sich und sind **nicht eindeutig belegt**; es wird keine neue Zahl festgelegt. Rohbelege des Vorlaufs bleiben unverändert. Offen bleiben Codex-Hostabnahme A/B/C, Webrecherche, Live-Git, veröffentlichte Marketplace-Installation. Keine Codex- oder Produktabnahme.


## 15. Nachtrag 2026-11-20 (Zuständigkeit Marketplace; Übergabe an /plugin-manager)

A, B und C aus Abschnitt 13 bleiben **BLOCKED** (nicht ausgeführt). Die fehlende Marketplace-Bereitstellung für Codex ist eine **externe Voraussetzung**; daraus entsteht **kein Implementierungsauftrag** für interview-coach. Das Plugin legt keinen Marketplace-Katalog an und registriert oder ändert keinen Marketplace, auch nicht als temporäre Testfixture; Registrierung und Änderung erfolgen **ausschließlich über /plugin-manager**. Die vollständige Isolation unter eigenem `CODEX_HOME` ist bisher **nicht nachgewiesen** (Abschnitt 14). Frühere Host- und Claude-Code-Abnahmen (Abschnitte 8–13) bleiben unverändert; die Empfehlung aus der Zwischenantwort zu Abschnitt 14, selbst einen Marketplace aus dem Payload zu bauen, entfällt.

Bestandsaufnahme und Übergabetext (Quellstand, Fingerprints, offene Fragen, freigabepflichtige Schritte): [.tmp/tests/codex-handoff-20261120-083033/UEBERGABE_plugin-manager.md](../.tmp/tests/codex-handoff-20261120-083033/UEBERGABE_plugin-manager.md), [BESTANDSAUFNAHME.md](../.tmp/tests/codex-handoff-20261120-083033/BESTANDSAUFNAHME.md). Die Codex-Abnahme beginnt erst, wenn /plugin-manager den Installationsweg bereitstellt und die nötigen Aktionen ausdrücklich autorisiert sind. Keine Codex- oder Produktabnahme.

**Präzisierung der Belegzuordnung (2026-11-20).** Die Übergabe nutzt das Fingerprint-Verfahren `tree_fingerprint` (`tests/native/run_host_acceptance.py`, statisch gelesen): Aggregat der `skills/`-Dateien ac4835b69aac40200a07b849ff4b90dff84d7ea38dee21ae6f22fbf28d5214a0, 20 Dateien, identisch zum Stand der Hostbelege; Dateiliste mit SHA-256 und vollständige Manifest-Hashes in `.tmp/tests/codex-handoff-20261120-083033/fingerprint-current.txt`. Der in der ersten Fassung der Übergabe genannte Wert `936e182e…` stammt aus einem anderen, unzureichend dokumentierten Verfahren und ist damit ersetzt; ein Produktunterschied wird nicht behauptet. A/B/C bleiben BLOCKED, Isolation unter `CODEX_HOME` bleibt praktisch ungeprüft.
