# Abnahmematrix / Acceptance matrix

Stand: 2026-11-19, uncommitteter Arbeitsbaum auf `47f45f2`. Quelle der Anforderungen: [SCOPE.md](../SCOPE.md).
Ein Source-Verweis oder ein bestandener Text-Vertragstest beweist keinen fachlich korrekten Ablauf. Modelltests sind heuristisch.

**Keine vollständige Abnahme.** Unten stehen getrennt: deterministisch geprüft · modellbasiert geprüft · nativ im Host beobachtet ·
live beim Provider geprüft (nicht erfolgt) · nicht implementiert · noch nicht geprüft.

## Nachtrag 2026-11-21 (Abschluss) — Klärungsfrage, Beispiel-Abzug, Zuschreibungen, zwei Nachfragen, verify.py

**Quellstände und Läufe dieses Nachtrags (jeweils eigener Fingerprint, nicht vermischt):**
| Lauf | Fingerprint (vor = nach dem Lauf) | Dateien | Zweck |
|---|---|---|---|
| Basis nach Commit `0ffda5f` (vor meinen Änderungen) | `58e17182…` | 95 | Ausgangszustand dieser Aufgabe: `deterministic` Exit 0 (305 Tests), `plugin.py check` Exit 0, `verify.py` Exit 0 |
| `final14` | `26879f1ebfe30bc150b99382c666bb6ba1c6a747eb4df083ac45d2049a1df7a9` | 104 | vorab festgelegte Wiederholungen (`PLAN.md`), danach Fehler behoben |
| `final15` (maßgeblich) | `770f8ec75df11dc13d5ed1e07b72aed3aa5a6d256630ef17597906edea0e336a` | 108 | gleicher vorab festgelegter Plan auf dem korrigierten Stand |
Evidenz: `.tmp/tests/final14/`, `.tmp/tests/final15/` (lokal, git-ignoriert); je `PLAN.md` (vor dem Lauf geschrieben), Logs, `scenarios-rep<N>/<id>.json` mit Transkript und Judge-Rohurteilen, `scenarios-rep<N>/artifacts/<id>/{ws,files}` (gespeicherte fiktive Run-/State-/Match-Artefakte), `host-*.json`, `host-*-artifacts/`, `judge-calibration-*.log`. **Gesamtergebnis `final15`: nicht vollständig bestanden** (1 von 17 Szenariodurchläufen FAIL).

### Punkt 5: `scripts/verify.py` (separat eingeordnet)
- `scripts/verify.py` stammt aus Commit `0ffda5f` („Align scripts with the plugin-manager template“, 2026-11-21 01:06, durch den Benutzer), zusammen mit geändertem `scripts/plugin.py`, gelöschtem `scripts/local_marketplace.py`, gelöschtem `.codex-plugin/plugin.json` und angepassten Tests/Makefile/Docs. Der `final13`-Fingerprint `88ddf32f…` (96 Dateien) bezieht sich auf den Baum **vor** diesem Commit und enthält `verify.py` nicht; die `final13`-Ergebnisse (309 Tests usw.) werden **nicht** dem heutigen Baum zugeschrieben. Die Fingerprints von `final14`/`final15` enthalten `scripts/` und damit `verify.py` (der Fingerprint hasht `skills/`, `tests/`, `scripts/`, `.claude-plugin`, `.codex-plugin`, `SCOPE.md`, `plugin.json`).
- Ergebnis, getrennt von den Testschichten: `python3 scripts/verify.py --source .` → Exit 0 (Basis, `final14`, `final15`): `valid: true`, `structure_valid: true`, `kind: plugin`, 5 Skills, `local_development.status: complete`, `target_code_executed: false`, `implementation_status: not_assessed`. Das ist eine strukturelle, lesende Prüfung; sie ersetzt weder Tests noch Source-Review noch Host-Abnahme.

### Punkt 2: Klärungsfrage (`clarify_motivation_neutral`) und „oder“-Widerspruch
- Änderung: SCOPE verlangt nur, mehrdeutige Motivationsaussagen **vor** jeder Schwächenableitung zu klären (Zeile Rollenpassung); das Nennen vorgegebener Bedeutungen ist nirgends Pflicht. Rubrik korrigiert: offene neutrale Klärung und neutrale Auswahlklärung sind zulässig, Nennen von Bedeutungen ist keine Pflicht; unzulässig sind suggestive Fragen (Prämisse/Wertung), vorzeitige Schwächen-/Passungsurteile, zwei Aufgaben, vorweggenommene Bewertung. `followup.md`: der Widerspruch ist beseitigt — verboten sind **mehrere Antwortaufgaben** (zweite Frage, auch nach „Und wie …“, Unterfragen, zwei unabhängige Dinge), nicht das Wort „oder“; „Meinen Sie damit A oder B?“ ist eine Aufgabe und erlaubt.
- Tests: Judge-Kalibrierung mit `clarify_open` und `clarify_choice` (erwartet true) sowie `clarify_suggestive` und `clarify_prejudging` (erwartet false); Unit-Test der Rubrik (Fixture-Erwartungen, ein Fragezeichen bei den positiven Formen); Contract-Test gegen die alte pauschale „oder“-Formulierung.
- Ergebnis: Kalibrierung mit dem echten Judge: alle vier Fälle in jedem der 3 Läufe von `final14` und `final15` wie erwartet. Szenario B Schritt 2 bestand in allen 6 Durchläufen von `final14`/`final15` (zuvor in `final11` und `final13` FAIL).
- Grenze: offene Fragen werden vom Judge geduldet, auch wenn sie sehr unspezifisch wären; Stichprobengröße klein.

### Punkt 3: Beispiel-Abzug in `final13`/B
- Änderung: `evaluation.md`: ein fehlendes Beispiel ist nie ein Abzug und nie eine Pflicht-Verbesserung, außer die Frage verlangt es ausdrücklich oder es ist wesentlich; höchstens eine als „optional“ formulierte Empfehlung, die nicht in Notenbegründung, gespeicherter Bewertung oder Pflicht-Trainingszielen steht. `followup.md`: „Warum wechseln Sie?“ mit „gar nicht, ich möchte selbst umsetzen“ ist beantwortet — kein Kriterium „Substanz der Begründung“ für fehlende Gründe/Situationen/Erfahrungen/Herkunft des Wunsches. Inline-Regeln auch in `candidate-training`/`job-training` `SKILL.md`.
- Tests (negative Regressionen mit dem konkreten Dialog): Kalibrierungsfall `final13_B_unasked_example_deduction` (erwartet `no_unasked_example_deduction` false) mit Kontrollfall `control_B_example_optional` (true); deterministischer Wächter `example_penalty_lines` (Schritt-Flag `no_example_deduction`) findet die final13-Zeile und lässt die optionale Empfehlung durch; Artefakt-Prüfung `stored_text_absent` über gespeicherte Runs, `state.md` und Job-Artefakte (Muster „fehlt … Beispiel“, „mit einem Beispiel belegen“); Unit-Test belegt, dass die in `final13` gespeicherten Formulierungen von den Mustern getroffen würden. Zusätzlich aus `final14`: Fälle `final14_B_rep2_origin_and_situation_demanded` (Judge-Urteil false auf `no_unasked_example_deduction`) und `final14_B_rep3_origin_of_wish_demanded`; Wächter `preference_penalty_lines` um „woher der Wunsch“, „Beweggründe“, „keine Situation“, „Substanz der Begründung … fehlt“ erweitert.
- Gespeicherter Run geprüft: In `final13` stand der Abzug in `block_assessment`, Run-Text und `state.md` (siehe Korrektur oben). In `final15` (B rep1–3) enthalten die gespeicherten Runs kein „Beispiel“-Defizit; Bewertung nur Klarheit/Ehrlichkeit/Direktheit; je ein `match`-Snapshot mit Zuordnung zu Bewerber/Stelle; Präferenz nicht in `state.md` (manuell gelesen, Pfade siehe Evidenz).
- Ergebnis: B in `final15` 3/3 PASS, in `final14` 1/3 PASS (rep2 FAIL: Judge `no_unasked_example_deduction`, Coach forderte „Situation, Erfahrung oder Beweggründe“ und „zum Beispiel aus welcher Arbeit“; rep3 FAIL: Wächter fand „Substanz der Begründung 5/10 … nicht, was Sie an der eigenen Umsetzung reizt oder woher der Wunsch kommt“, der echte Judge ließ rep3 durch).
- Grenze: Der echte Judge erkennt den Fall `final14_B_rep3_origin_of_wish_demanded` auch auf dem korrigierten Stand **nicht** (3 von 3 Kalibrierungsläufen in `final15`: `role_fit_job_specific` true statt false); er wird nur vom deterministischen Wächter gefangen, dessen Muster eng sind.

### Punkt 4: D „von Anfang an“, erfundene Gegensätze, zwei Nachfragen
- Änderung: `evaluation.md` Zuschreibungen: keine erschlossenen Gewohnheiten, Motive, Grade oder Gegensätze („denkt von Anfang an mit“, „immer“, „proaktiv“, „vorab statt erst nach der Entscheidung“, „und nicht erst im Nachhinein“); Aussagen über den Dialogverlauf (Antwort nach der Nachfrage, selbstständig, ohne Hinweis) sind erlaubt. Judge-Prompt: Charakterisierungen ohne Bewerberaussage sind Erfindungen, Aussagen über den Dialogverlauf nicht (Judge-Fehlalarm in `final14` J rep1/rep3). Deterministischer Wächter `unstated_characterizations` (Schritt-Flag `no_unstated_characterization` in A, D, J). Zwei Nachfragen: Regeln jetzt inline in den immer geladenen `SKILL.md` (nicht nur in der Referenz), Regelbeispiel „… Und wie sorgen Sie dafür …“, Selbstprüfung „Fragezeichen und Antwortaufgaben zählen“.
- Tests/Regressionen: Kalibrierungsfälle `final13_D_unsupported_attribution`, `final14_D_rep3_invented_contrast` (beide erwartet `no_invention` false), `final14_J_rep1_dialogue_course_is_no_invention` (erwartet true), `final12_host_claude_two_followups` (`single_followup` false) mit Kontrolle `control_single_choice_followup` (true); Unit-Tests für den Zuschreibungs-Wächter (final13-Satz, final14-Gegensatz, eigene Worte, Empfehlungen), `false_missing_verdict` (Zitate), Hostrunner-Test, dass die Zweifragen-Nachfrage aus `final12` den Check „exactly one question mark“ nicht besteht.
- Ergebnis `final14` (Plan vorab: B, D, F, J je 3×, A, E, G, H, I je 1×; Hosts je 1× plus Claude-nostorage 2 Wiederholungen): 17 Szenariodurchläufe → 12 PASS, 5 FAIL: B rep2, B rep3 (siehe Punkt 3), D rep3 (`no_invention`: „Sie informieren das Produktmanagement vorab statt erst nach der Entscheidung“ — erfundener Gegensatz, Produktfehler), J rep1 und J rep3 (`no_invention` auf Aussagen über den Dialogverlauf: **Judge-Fehlalarm**; in J rep1 enthielt dieselbe Antwort zusätzlich den erfundenen Gegensatz „und nicht erst im Nachhinein“, nach der Korrektur deterministisch auffindbar). Hosts: Claude Code stop 20/20 PASS, pause 15/15 PASS, nostorage 12/13 **FAIL** (Nachfrage mit zwei Fragen: „Wie berücksichtigen Sie diese Zeitgrenze konkret in Ihrem Vorgehen? Und was tun Sie, wenn die Teams … weiterhin auf ihren Positionen bleiben?“), nostorage-Wiederholungen 2 und 3 je 13/13 PASS; Codex stop 20/20, pause 15/15, nostorage 13/13 PASS. Kalibrierung 3×13/13.
- Ergebnis `final15` (derselbe Plan): 17 Szenariodurchläufe → 16 PASS, 1 FAIL: F rep3 (`no_artificial_completion` und `no_false_missing` mit verifizierten Zitaten: „Aus Ihrer Formulierung geht nicht eindeutig hervor, ob Sie selbst oder der Product Owner am Ende entscheiden“ trotz „… mit dem Product Owner priorisieren, entscheiden, ob das Feature in den Sprint passt“ und „Wie das Sprintziel dabei geschützt wird, sagen Sie nicht“; manuell grenzwertig: die Formulierung des Bewerbers lässt offen, wer entscheidet, und der Schutz des Sprintziels könnte als erfragt gelten; wegen der verifizierten Zitate bleibt es ein FAIL). Hosts: alle 8 Durchläufe PASS (Claude Code stop 20/20, pause 15/15, nostorage 13/13 sowie 13/13 und 13/13 in den Wiederholungen; Codex 20/20, 15/15, 13/13). Kalibrierung 3×(16 von 17 wie erwartet; konstanter Fehlgriff `final14_B_rep3_origin_of_wish_demanded`).
- Gesamtbild der Claude-nostorage-Zweifragen-Nachfrage über alle bisherigen Läufe: FAIL in `final10`, `final12`, `final14` (Hauptlauf); PASS in `final11`, `final13`, `final14` rep2/rep3, `final15` (alle drei). Der Fehler ist intermittierend und nicht ausgeschlossen; `final15` ist eine Stichprobe von 3 Durchläufen ohne Auftreten.
- Grenzen: D „von Anfang an“/Gegensätze: in `final15` 3/3 PASS, aber der Wächter kennt nur die gelisteten Marker; der Judge streut. Kleine Stichproben (je 3), keine statistische Aussage.

### Punkt 1: Dokumentationskorrektur
Erledigt durch die KORREKTUR-Hinweise in den Abschnitten von `final13` (7/9 statt 8, B nach Schritt 2 weiter ausgeführt mit Einzelresultaten, übersehener Beispiel-Abzug) und `final10` (B/final10 als übersehener Fachfehler, siehe dort). Die ursprünglichen Texte sind erhalten.

### Befehle, Exitcodes (`final15`, ein Quellstand)
| Prüfung | Exit | Ergebnis |
|---|---|---|
| `python3 -B scripts/run_tests.py --kind deterministic` | 0 | 311 Tests OK |
| `python3 scripts/plugin.py check` | 0 | valid |
| `python3 scripts/verify.py --source .` (separat) | 0 | valid, structure_valid, implementation_status not_assessed |
| `run_scenarios.py --cli claude --scenario …` (17 Durchläufe) | 16×0, 1×1 | 16 PASS, 1 FAIL (F rep3) |
| `run_host_dialogue.py` Claude Code (voll + 2 Wiederholungen nostorage) | 0 ×3 | 3+1+1 Läufe PASS |
| `run_host_dialogue.py` Codex (voll) | 0 | 3 PASS |
| `run_scenarios.py --judge-calibration` ×3 | 1 ×3 | 16 von 17 Fällen je Lauf wie erwartet (Fehlgriff: B rep3 origin of wish) |

### Verbleibende Lücken
- `final15` nicht vollständig bestanden (F rep3); Einzelstichproben, Judge heuristisch, nur Claude; bekannte Judge-Blindstelle (B rep3-Fall) wird nur vom Wächter abgedeckt.
- Intermittierende Zweifragen-Nachfrage im Claude-nostorage (3 von 10 Läufen über `final10`–`final15` FAIL), in `final15` nicht aufgetreten.
- Nicht auf den Hosts geprüft: Rollenpassung/Match-Speicherung, deepening-Zweig, Coaching-Fall E, Mock, Stellen-Training mit Pause.
- Payload-Kopie, keine Marketplace-Installation; Host-Sitzungsverläufe außerhalb des Projekts werden nicht erfasst.
- Ältere Nachweise (`final5`–`final13`) gelten nur für ihre damaligen Stände, nicht für den Baum nach Commit `0ffda5f`.

## Nachtrag 2026-11-21 — Rollenpassung ohne indirekte Bestrafung, nicht erfragte Zusatzaspekte, eine Frage pro Turn, Evidenztreue, aufbewahrte Artefakte

> **KORREKTUR (2026-11-21, nach erneuter Durchsicht der Logs und Transkripte von `final13`): Die Zählung und Einordnung unten sind falsch und bleiben zur Nachvollziehbarkeit erhalten.** (a) Von den 9 Szenarien bestanden in `final13` **7**, nicht 8: A (adr_deadline), E (gap_stays_open), F (optional_example), G (stop_open), H (mock), I (pause_resume), J (no_storage); es fielen D und B durch. In der Tabelle unten steht fälschlich „8 PASS“. (b) Szenario B wurde nach dem fehlgeschlagenen Schritt 2 **weiter ausgeführt**: Schritt 1 PASS, Schritt 2 FAIL (`clarify_motivation_neutral`), Schritt 3 PASS (Judge `role_fit_job_specific` true; Fit-Punkt als `match`-Snapshot gespeichert), Schritt 4 (STOP, `finish` mit `stopped_early`, kein Fortsetzungsversprechen) PASS, Artefaktprüfung ohne Fehler (Run-Felder, Dialog, `job_artifact` match mit Zuordnung, `state.md` ohne Präferenz). Die Aussage „Rest von B wurde nicht erreicht/gewertet“ ist falsch. (c) Übersehener fachlicher Fehler in `final13`/B trotz diesen PASS-Schritten: Die Bewertung nannte „Konkretheit: 5/10. Es fehlt ein Beispiel, was du genau umsetzen möchtest oder wann du das zuletzt getan hast“, obwohl die Frage („Warum möchten Sie in diese Product-Rolle wechseln?“) kein Beispiel verlangte; derselbe Satz stand im gespeicherten Run (`block_assessment`: „Konkretheit 5/10, es fehlt ein Beispiel“), im Run-Text und als Trainingsziel „mit einem Beispiel belegen“ in `state.md`. Die gespeicherten Artefakte liegen in `.tmp/tests/final13/scenarios/artifacts/followup_motivation_role_fit/`. (d) Die ursprünglich gemeldeten Hostergebnisse (6/6) und Kalibrierungsergebnisse (3×4/4) von `final13` sind unverändert.

**Maßgeblicher Lauf: `final13`, Quellstand `88ddf32f6f3140a3696ee09b4d20db70f57ab050cadef63d7280d6a49f758844` (96 Dateien; identisch in `fingerprint-start.txt`/`fingerprint-end.txt`, nach der Doku erneut geprüft).** Belege: `.tmp/tests/final13/` (lokal, git-ignoriert), darin `scenarios/artifacts/<szenario>/{ws,files}` (gespeicherte fiktive Run-/State-/Match-Artefakte, ohne `.journal`) und `host-*-artifacts/`. **Gesamtergebnis: nicht vollständig bestanden** (2 von 9 Szenarien FAIL). Frühere Läufe `final11` und `final12` (eigene Stände) sind unten erhalten und nicht mit `final13` vermischt.

### Änderungen, Tests, Ergebnisse, Grenzen
**1. Rollenpassung / Judge (B, final10)**
- Änderung: `followup.md`/`evaluation.md`: Noten *und deren Begründungen* dürfen nicht auf fehlender Begeisterung, fehlendem Interesse oder fehlenden Gründen für die abgelehnte Rolle beruhen (auch nicht in „Substanz der Begründung“ oder „wirkt wie eine Absage“); bewertet werden Klarheit, Ehrlichkeit, Konkretheit; die Überschrift „Passung (ohne Punktzahl)“ genügt nicht. Rubrik `role_fit_job_specific` nennt genau diese Muster. Neu: deterministischer Wächter `preference_penalty_lines` (Schritt-Flag `no_preference_penalty` in Szenario B).
- Tests: negativer Regressionstest mit dem konkreten final10-Dialog (`tests/fixtures/behavior/judge_cases/final10_B_role_fit_penalty.json`): findet die Zeilen „reizt“, „anspricht“, „Absage“; Kontrollfall mit sauber getrennter Bewertung (`control_B_separated_rating.json`) wird nicht beanstandet; ein „lenienter“ Judge, der final10 durchließ, wird von der Kalibrierung erkannt. Der echte Judge wurde mit `run_scenarios.py --cli claude --judge-calibration` 3× in `final13` und 1× vorab befragt: alle 4 Fälle in allen 3 Läufen mit dem erwarteten Urteil.
- Ergebnis `final13`: Das Stellen-Szenario B schlug an einer anderen Prüfung fehl (siehe Fehlschläge), nicht an der Notenbegründung. In `final11` bestand die Notenbegründungsprüfung; im damaligen Transkript lautete eine Begründung „Substanz der Begründung 5/10: Es fehlt ein Anlass oder Beispiel, was Sie zu diesem Wunsch geführt hat“ — vom Wächter und vom Judge nicht beanstandet, **manuell grenzwertig** (fordert eine Rechtfertigung der Präferenz); nicht automatisch entschieden.
- Grenze: Judge heuristisch, Einzelstichproben (3 Kalibrierungsläufe belegen kein Dauerverhalten); der Wächter erkennt nur die beobachteten Formulierungen.

**2. Szenario F: nicht erfragte Zusatzaspekte**
- Änderung: `followup.md`: nicht erfragte Aspekte sind nie `completion`, nur optionale `deepening` (Formulierung als optional, `gap: null`, nie in `other_open_gaps`, nie „fehlt/offen“ in der Bewertung, bei Ablehnung Abschluss ohne Abzug); eine vom Coach selbst angehängte Zweitfrage kann nie als unbeantwortet bewertet werden. Szenario F prüft jetzt `allowed_kinds: [deepening]` **und** `no_gaps` (keine Lücke, kein offenes Resolution, keine `other_open_gaps`); Rubrik `no_false_missing` (nur bei bewerteter Antwort, `judge_if_rated`).
- Tests: Unit-Test `dialogue_matches` (`no_gaps`), Fixture-Test.
- Ergebnis: F PASS in `final12` und `final13`; in `final11` FAIL (Judge `no_false_missing`: „wer sie am Ende trifft bleibt offen“, obwohl „ich … entscheide“ gesagt war — dritter Befund dieser Art; danach Beispiel in `evaluation.md` ergänzt).
- Grenze: Der deepening-Zweig mit gespeicherter Vertiefungs-Nachfrage wurde in `final13` nicht beobachtet (Coach bewertete direkt).

**3. Eine Nachfrage pro Turn, Evidenztreue (Claude-nostorage)**
- Änderung: `followup.md`: zusätzliche Fehlbeispiele (zwei Fragen nach „Und wie …“, „oder“-Alternativen, das final10-Beispiel); `evaluation.md` „Evidence fidelity“ (jede „fehlt/offen“-Behauptung gegen alle Bewerberaussagen prüfen; „mit beiden Teams durchgehen“ = Teameinbindung genannt; mehr Tiefe nur als Empfehlung). Szenarien: Flag `max_question_marks: 1` an allen Nachfrage-Schritten; Rubrik `no_false_missing` an Bewertungsschritten; Hostrunner: `false_missing_claims` gegen die skriptierten Antworten in jeder Bewertungs- und STOP-Antwort.
- Judge-Zuverlässigkeit: `no_false_missing=false` gilt nur mit wörtlichem Zitat der Behauptung **und** des widersprechenden Bewerberzitats (geprüft, inhaltlich überlappend); sonst UNCLEAR (`false_missing_verdict`, Tests inkl. erfundener Zitate).
- Regressionen aus dem final10-Transkript: `final10_host_claude_false_missing.json` (Judge-Kalibrierung), `test_final10_host_rating_calls_the_stated_team_involvement_missing` (Hostrunner-Wächter findet „Sie sagen nicht, wie Sie die Teams einbinden“ und lässt die treue Kontrollbewertung durch).
- Ergebnis `final13`: Host Claude Code stop/pause/nostorage PASS, Codex stop/pause/nostorage PASS (Checks laut `host-*.json`: claude stop 20/20; claude pause 15/15; claude nostorage 13/13; codex stop 20/20; codex pause 15/15; codex nostorage 13/13). In `final12` trat die Zweifragen-Nachfrage im Claude-nostorage erneut auf (Hostlauf FAIL), in `final10` ebenfalls; in `final11` und `final13` nicht → **intermittierend (2 von 4 Claude-nostorage-Läufen), nicht behoben**, nur nicht in `final13` beobachtet.
- Grenze: Nachfrage-Wortlaut ist modellabhängig; die Hostprüfung erkennt nur die Zahl der Fragezeichen.

**4. Aufbewahrung der Artefakte**
- Änderung: `run_scenarios.py` kopiert nach jedem Szenario `ws/` (ohne `.journal`) und `files/` nach `<output>/artifacts/<id>/`; der Hostrunner kopiert den Speicher nach `<output>-artifacts/<szenario>/`. Test: `test_model_run_artifacts_are_preserved_for_independent_review`.
- Ergebnis: Für `final13` vorhanden, u. a. gespeicherter `match`-Snapshot, Run und `state.md` von Szenario B (`scenarios/artifacts/followup_motivation_role_fit/ws/candidates/.../{jobs/.../match/001.md,runs/run-001.md,state.md}`); in `final11` gelesen: der Match-Snapshot enthält die Präferenz in den Worten der Bewerberin, die Anzeigenfakten, als Interpretation markiert, und „kein Teil des übergreifenden Lernstands“; `state.md` enthält die Präferenz nicht.
- Grenze: Für Nicht speichern entsteht per Definition nichts; Hostläufe bewahren nur den Speicher der Szenarien stop/pause.

### Befehle, Exitcodes, Ergebnisse (`final13`, ein Quellstand)
| Prüfung | Exit | Ergebnis |
|---|---|---|
| `python3 -B scripts/run_tests.py --kind deterministic` | 0 | 309 Tests OK |
| `python3 scripts/plugin.py check` | 0 | valid |
| Szenarien A, C, E, G, H, I, J, F (je `scenario-*.log`) | 0 | 8 PASS |
| Szenario D `followup_complete_answer` | 1 | **FAIL** |
| Szenario B `followup_motivation_role_fit` | 1 | **FAIL** |
| Host Claude Code und Codex: stop, pause, nostorage | 0 / 0 | 6 von 6 PASS |
| Judge-Kalibrierung ×3 (`judge-calibration-{1,2,3}.log`) | 0 ×3 | 4 von 4 Fällen je Lauf wie erwartet |

**Fehlschläge in `final13` (nicht abgeschwächt):**
- **D (Produktfehler, gering):** Die Bewertung schrieb der Bewerberin zu: „Du denkst den Termindruck von Anfang an mit und lässt ihn nicht erst am Ende nachträglich einfließen.“ Die Antwort sagte nur, dass wegen des festen Termins der Umfang reduziert wird; „von Anfang an“ ist eine nicht belegte Zuschreibung. Judge (mit Zitat, neue Wörter) und manuelle Durchsicht stimmen überein.
- **B (offen, Rubrik- oder Produktfrage):** Die Klärung lautete „Was verstehen Sie konkret unter ‚echter Realisierung‘ in Ihrer täglichen Arbeit?“ — eine neutrale Frage, nennt aber keine möglichen Bedeutungen. Die Rubrik `clarify_motivation_neutral` verlangt das Nennen möglicher Bedeutungen („eigene technische Umsetzung oder Produktverantwortung“); dieselbe Prüfung schlug in `final11` an derselben Stelle fehl, bestand in `final12` und `final10`. Ob eine offene neutrale Klärungsfrage reicht, ist **eine Entscheidung über das Soll** (bestätigt ist nur „vor der Schwächenableitung klären“, das Beispiel ist „e.g.“); ich habe die Rubrik nicht abgeschwächt. Der Rest von B (Match-Snapshot, Zuordnung, keine Notenbegründung durch die Präferenz) wurde in `final13` nicht erreicht/gewertet, weil Schritt 2 bereits fehlschlug; die Artefakte des Laufs sind in `scenarios/artifacts/followup_motivation_role_fit/` zu prüfen.

### Läufe auf anderen Ständen (erhalten, nicht für den Endstand gültig)
| Lauf | Quellstand (Anfang) | Ergebnis |
|---|---|---|
| `final10` | `fff306d1…` | siehe Korrektur oben; F und Claude-nostorage FAIL |
| `final11` | `2c5f8073…` | 7 von 9 Szenarien PASS; B FAIL (`clarify_motivation_neutral`), F FAIL (`no_false_missing`, „wer sie am Ende trifft“ trotz „ich … entscheide“); Hosts 6/6 PASS; Kalibrierung 3×4/4 |
| `final12` | `9aee4a79…` | 8 von 9 PASS; J FAIL (`no_false_missing`, Judge ohne Zitate: UNCLEAR-würdig, dadurch `false_missing_verdict` ergänzt); Host Claude pause FAIL (Fehlalarm des Resume-Detektors auf „Dort greife ich den gespeicherten Lernstand auf.“ in neuem Training → Detektor eingeengt) und nostorage FAIL (Nachfrage mit zwei Fragen, echter Produktfehler); Codex 3/3 PASS; Kalibrierung 3×4/4 |

### Verbleibende Lücken
- Nicht vollständig bestanden: D (gering) und B (Soll-Entscheidung offen); Claude-nostorage-Zweifragen-Nachfrage intermittierend.
- Einzelstichproben, Judge heuristisch und nur mit Claude; der Judge streut zwischen Läufen (z. B. `no_false_missing`).
- Nicht auf den Hosts geprüft: Rollenpassung/Match-Speicherung (nur Modellszenario), deepening-Zweig, Coaching-Fall E, Mock, Stellen-Training mit Pause.
- Payload-Kopie, keine Marketplace-Installation; Host-Sitzungsverläufe außerhalb des Projekts werden nicht erfasst.

## Nachtrag 2026-11-20 (Nachbesserung 2) — Blockabschluss, Rollenpräferenz im Match-Artefakt, STOP ohne Fortsetzungsversprechen

> **KORREKTUR (2026-11-21): Szenario B bestand in `final10` automatisch, enthielt aber einen übersehenen fachlichen Fehler.** Gesamtnote 5/10 und „Substanz der Begründung: 4/10“ wurden damit begründet, dass die Bewerberin nicht sagt, „was dich an dieser Rolle oder an Beispiel AG anspricht“, und die Antwort „wirkt wie eine Absage“. Das bestraft die ausdrücklich abgelehnte Rollenpräferenz indirekt; die Überschrift „Passung zur Stelle (ohne Punktzahl)“ ändert daran nichts. Der Judge meldete `role_fit_job_specific: true`, die Rubrik war zu schwach formuliert, und ein deterministischer Test für Notenbegründungen fehlte. Die ursprüngliche Aussage unten (B PASS, manuell gelesen) bleibt unverändert stehen und gilt als widerlegt. Ebenfalls in `final10` übersehen: Das Bewertungstranskript des Claude-nostorage-Hostlaufs nannte die Teameinbindung fehlend, obwohl die Bewerberin „mit beiden Teams durchgehen“ gesagt hatte, und wertete eine selbst hinzugefügte Zweitfrage als „nur halb beantwortet“. Beide Texte sind als Kalibrierungsfälle gespeichert (`tests/fixtures/behavior/judge_cases/`). Für `final10` wurden die gespeicherten Run-/State-/Match-Artefakte nicht aufbewahrt, nur die Transkripte.

**Maßgeblicher Lauf: `final10`, Quellstand `fff306d1d5d963335edada3a29422d6485bbf60c30f2d070579cf27aa93a4bb9` (92 Dateien; identisch in `fingerprint-start.txt` und `fingerprint-end.txt`).** Belege: `.tmp/tests/final10/` (lokal, git-ignoriert; nicht mit `final5` vermischt). **Gesamtergebnis: nicht vollständig bestanden** (siehe Fehlschläge). Die Doku-Änderung nach dem Lauf berührt keine fingerprint-relevante Datei.

### Pro Punkt: Änderung, Test, Ergebnis, Grenze
**1. Blockabschluss (evaluation.md:15)**
- Änderung: Die Pflicht „vollständige Antwort schließt den Block sofort“ ist entfernt. Einheitliche Regel in `evaluation.md` (Zeile 15 und „Follow-up blocks“), `followup.md` Schritt 5 und `SKILL.md` 2a: vollständige Antwort ⇒ keine completion-/clarification-Nachfrage; optional genau eine sinnvolle deepening-Nachfrage ohne Bewertung/Hinweis/Lösung, sonst Block schließen und bewerten; keine Pflicht, keine Quote.
- Test: `test_block_close_deepening_stop_and_role_fit_rules_agree_across_files_structural_only` (Regression: „closes its block immediately“/„evaluated at once“ dürfen nicht mehr vorkommen; beide Dateien nennen die gleiche Regel). Modellszenario D (`deepening_or_close`, Judge sieht bei `evaluable_over` den ganzen Block).
- Ergebnis: Contract-Test OK; Szenario D PASS in `final10` (einzelner Lauf).
- Grenze: Der Zweig „genau eine deepening-Nachfrage“ wurde nicht beobachtet; strukturelle Prüfung beweist kein Dialogverhalten. In `final6` schlug D an einer unklaren Rubrik fehl (`deepening_or_close` false bei Abschluss mit Bewertung; Rubrikformulierung war widersprüchlich und wurde präzisiert).

**2. Rollenpräferenz im stellenspezifischen Match-Artefakt**
- Änderung: `followup.md`, `job-preparation.md`, `job-training/SKILL.md`: bestätigte Präferenz wird spätestens am Sitzungsende als neuer vollständiger `match`-Snapshot (`job-add --kind match`) gespeichert, nie nur im Run, nicht in `state.md`; ohne Job bleibt sie im Run/Chat; bei Fehlschlag wird ausdrücklich „nicht gespeichert“ gesagt. Zusätzlich (aus Beobachtung in `final7`/`final8`): keine Zahl und keine Kriterienzeile für die Präferenz (z. B. „Bezug zur Rolle: 2/10“).
- Tests: Runtime `test_confirmed_role_preference_is_stored_in_the_job_match_not_only_in_the_run_and_not_in_state` (unbestätigtes Profil verweigert, append-only Snapshot, Header mit candidate_id/job_id, Run mit gleicher Zuordnung, `state.md` ohne Präferenz); Harness `job_artifact_errors` mit Unit-Test; Szenario B prüft das tatsächlich gespeicherte Artefakt (Art `match`, Zuordnung zu Bewerber/Stelle des gespeicherten Runs, Inhaltsmuster, `state.md` ohne Präferenz) und die Judge-Rubrik `role_fit_job_specific` (jetzt auch: keine Note wegen der Präferenz).
- Ergebnis: Szenario B PASS in `final10` (`job-add` Exit 0, `match`-Snapshot 1, Run und Match derselben Stelle zugeordnet, Fit-Punkt „ohne Punktzahl“); manuell gelesen. In `final7`/`final8` zeigte das Szenario echte Fehler: Präferenz bestrafte die Note („Bezug zur Rolle 2/10“, `final7`: Gesamtnote 4/10) bzw. wurde vom verschärften Judge erkannt (`final8`).
- Grenze: Einzelstichprobe; der Fit-Punkt wird nur im Szenario mit Job geprüft; ob der Inhalt des Snapshots fachlich vollständig ist, ist manuell nur einmal gelesen. Einen Snapshot-Inhalt „ohne frühere Inhalte“ erkennt kein automatischer Test im Modelllauf.

**3. STOP ⇒ `stopped_early`, kein Fortsetzungsversprechen**
- Änderung: `session-control.md`, `job-training`/`candidate-training` `SKILL.md`: STOP endet immer mit `stopped_early`; die Abschlussantwort verspricht keine Wiederaufnahme der offenen Nachfrage, verweist ggf. auf `pause`. `followup.md` Schritt 8: Bei Wiederaufnahme eines `paused`-Checkpoints Kontext als Aussage, nicht als zweite Frage.
- Tests: negativer Detektortest `promises_resume` mit dem genauen Satz aus `final5` plus englischen/umschriebenen Varianten; Fehlalarm-Tests aus beobachteten Antworten (Hinweis auf `pause`, neuer Lauf, Dateinamen, Ratschläge); Step-Flag `no_resume_promise` an jedem STOP-Schritt aller `followup_*`-Szenarien (Unit-Test prüft die Fixtures) und `stop_checks` in jedem STOP-Turn des Hostrunners; Runtime `test_a_stopped_run_is_final_and_cannot_be_resumed_while_a_paused_one_can` (Resume eines `stopped_early`-Runs wird abgelehnt, `completed` mit offener Nachfrage abgelehnt, positiver Pause→Resume→Antwort→STOP mit `resume_from`, Zählern und unveränderter Zuordnung); Hostszenario `pause` (Neue Sitzung, Resume, Antwort, STOP).
- Ergebnis: Unit/Integration OK; Hostszenario `pause` PASS auf Claude Code und Codex in `final10`.
- Grenze: Der Detektor ist regelbasiert (Assistenten-Versprechen mit „ich/wir“, „beim Fortsetzen“, „kann fortgesetzt werden“, „stelle ich … erneut“); neue Formulierungen können durchrutschen oder, wie in `final6`–`final8` beobachtet, zu Fehlalarmen führen. Er musste dreimal an beobachteten Fehlalarmen nachgeschärft werden (siehe Läufe); die echten Versprechen aus `final5` werden weiterhin erkannt.

### Befehle, Exitcodes, Ergebnisse (`final10`, ein Quellstand)
| Prüfung | Exit | Ergebnis |
|---|---|---|
| `python3 -B scripts/run_tests.py --kind deterministic` (`deterministic.log`) | 0 | 301 Tests OK |
| `python3 scripts/plugin.py check` (`plugin-check.log`) | 0 | valid |
| Szenarien A, B, C, D, G, H, I, J (Claude, `scenario-*.log`) | 0 | 8 PASS |
| Szenario F `followup_optional_example` | 1 | **FAIL** |
| Host Claude Code (`host-claude.json`): stop, pause / nostorage | 0 / 1 | stop PASS, pause PASS / nostorage **FAIL** |
| Host Codex (`host-codex.json`): stop, pause, nostorage | 0 | alle PASS |

**Fehlschläge in `final10` (nicht abgeschwächt, nicht behoben):**
- **F (Produktfehler, zweimal in Folge beobachtet: `final8`, `final10`):** Auf eine vollständig beantwortete Frage, deren Kriterien nicht erfragt waren, fragte der Coach „Nach welchen Kriterien entscheiden Sie, ob das Feature in den Sprint passt oder verschoben wird?“ statt zu bewerten; im Run kein deepening. Die Frage verlangt nur Vorgehen und ein optionales Beispiel; Kriterien waren nicht gefragt, die Nachfrage ist damit eine künstliche completion-Nachfrage nach `followup.md`. Der Judge meldete `no_artificial_completion: false` (in `final8` in einem anderen Durchlauf `true`: Judge streut).
- **Host Claude nostorage (Produktfehler):** Nachfrage mit zwei Fragezeichen und zwei Fragen („Wie gehen Sie konkret mit dem Termin um? Was tun Sie, wenn die Teams … uneinig sind …?“) verletzt „genau eine Nachfrage / ein Fragezeichen“. Auf Codex und im Stop-/Pause-Lauf von Claude nicht aufgetreten.

### Läufe auf früheren Ständen (erhalten, nicht für den Endstand gültig)
| Lauf | Quellstand (Anfang) | Ergebnis | Ursache |
|---|---|---|---|
| `final5` | `3256005a…` | B FAIL (+ 3 PASS-Wiederholungen) | siehe Korrektur oben |
| `final6` | `072dca47…` | 5 Szenarien FAIL (A, D, F, I, J), Host Claude und Codex: pause FAIL | Detektor `promises_resume` überbreit (Neustart in neuer Sitzung als „Versprechen“ gewertet); D `deepening_or_close` Rubrikwiderspruch; Host Resume-Antwort mit Rückfrage-Wiederholung (zwei Fragezeichen). Szenario B bestand erstmals mit gespeichertem Match. |
| `final7` | `0fbbc231…` | 8 von 9 Szenarien FAIL (nur J PASS), Host Claude stop und pause FAIL, Codex PASS | Detektor verwarf `pause` in Backticks (eigener Fehler beim Entfernen von Codespans); D: Judge sah nur die letzte Antwort; B: Präferenz in `state.md` gefunden. |
| `final8` | `38904f81…` | 5 Szenarien FAIL (B, D, F, H, J), Host Claude stop und pause FAIL, Codex PASS | Detektor weiterhin überbreit (Ratschläge, „neuer Durchlauf“); B: Rubrik erkannte Notenabzug (`Bezug zur Rolle: 2/10`) = echter Produktfehler; F: Rückfrage statt Bewertung. |
| `final9-aborted` | `a1821bbf…` | abgebrochen | Start trotz rotem Unit-Test (Testfehler im eigenen Test); manuell gestoppt, nicht gewertet. |

### Verbleibende Lücken
- Nicht vollständig bestanden: F und Host-Claude-nostorage (siehe oben). Keine Abnahme des Gesamtstands.
- Alles Einzelstichproben; Judge heuristisch, nur Claude; der Judge streut (F `no_artificial_completion` false/true auf verschiedenen Läufen).
- Nicht auf den Hosts: Rollenpassung/Match-Speicherung (nur Modellszenario B), deepening-Zweig, Coaching-/Hinweisfall E, Mock, Stellen-Training-Pause.
- Payload-Kopie, keine Marketplace-Installation; Host-Sitzungsverläufe außerhalb des Projekts werden nicht erfasst.

## Nachtrag 2026-11-20 (Nachbesserung) — Judge-Semantik, Nicht-speichern-Hosttest, Vertiefung/Blockabschluss

**Quellstand: `3256005a2ded17a7999ee242edbb0a04324b2035af9244afa72f57714b1a34d2` (92 Dateien, `.tmp/tests/fingerprint.py`; am Anfang und Ende des Laufs `final5` und nach der Doku identisch).** Alle Ergebnisse dieses Abschnitts gelten nur für diesen Stand. Die Ergebnisse des Abschluss-Nachtrags darunter (`f9df5367…`) gelten ausdrücklich nicht für ihn; Stop- und Pause-Hostläufe wurden hier auf dem neuen Stand erneut gefahren, nicht übernommen.

### Änderungen
1. **Judge (`tests/behavior/run_scenarios.py`, `invention_verdict`)**: Die automatische Überstimmung „keine neuen Inhaltswörter ⇒ PASS“ ist entfernt. Ein als unbelegt gemeldeter Kandidatenfakt ist nur FAIL, wenn neue Inhaltswörter oder neue Zahlen belegbar sind; sonst UNCLEAR (Bedeutung, Akteur, Negation oder Beziehung nicht geklärt). „Belegt“ gilt nur mit einem `evidence_quote`, der wörtlich in Quellen/Bewerberzeilen steht, Inhalt mit der Aussage teilt und Zahlen (Ziffern und Zahlwörter) sowie Negation gleich hat (`semantic_divergence`); Abweichung ⇒ FAIL, fehlender Beleg ⇒ UNCLEAR. Vertauschte Akteure erkennt nur der Judge; ohne Beleg bleibt der Befund UNCLEAR (bekannte Grenze: behauptet der Judge fälschlich „belegt“ mit einem thematisch passenden Zitat, wird ein reiner Akteurtausch nicht deterministisch gefunden). `coach_suggestion` verlangt `suggestion_kind`: `recommendation` ist zulässig; `first_person_answer` ist FAIL bei `invents_experience=true` oder neuen Zahlen, UNCLEAR ohne Urteil oder bei Ich-Behauptung mit fremdem Inhalt; Ich-Perfektformulierungen gelten unabhängig vom Label als Ich-Antwort.
2. **Nicht-speichern-Hosttest (`tests/native/run_host_dialogue.py`)**: keine Ausnahmen für `.cfg`/`.agents` mehr. Der Konfigurationsordner liegt außerhalb des Projekts; vor dem Dialog (nach Vorbereitung des Host-Skillordners) werden Projekt und Konfigurationsordner mit Inhaltshashes erfasst (`snapshot`), danach neue/geänderte/gelöschte Einträge geprüft (`diff_snapshots`). Ausnahmen nur als exakter Pfad mit Begründung (`NOSTORAGE_ALLOWED`, leer; Präfixe/Muster werden abgelehnt). Zusätzlich: kein Eintrag im Konfigurationsordner (= kein Zeiger), kein Runtime-Aufruf, und `claims_saved` prüft die STOP-Antwort sowie jede Turn-Antwort auf Speicherbehauptungen (erweitert um „gesichert/archiviert/Gespeichert unter/saved/stored“, Verneinungen ausgenommen).
3. **Vertiefung/Blockabschluss**: `followup.md` (Schritt 5), `evaluation.md` („Follow-up blocks“, Entscheidung am Antwortende) und `interview-coach/SKILL.md` (2a) sind angeglichen: Vollständige Antwort ⇒ keine completion-/clarification-Nachfrage; höchstens eine sinnvolle deepening-Nachfrage (kein Abzug, keine vorweggenommene Bewertung/Lösung, keine Pflicht, keine Quote), sonst Block schließen und bewerten; nach einer Vertiefung schließt der Block. Szenario D prüft das über die neue Rubrik `deepening_or_close` (entweder genau eine Vertiefungsfrage ohne Bewertung/Hinweis oder Abschluss mit Bewertung, nie beides, keine completion-Frage).

### Neue deterministische Tests
`tests/unit/test_run_scenarios.py`: gleicher Wortschatz überstimmt den Judge nicht (hinzugefügte Negation, vertauschte Akteure), entfernte/hinzugefügte Negation und geänderte Zahl gegen `evidence_quote`, Zahlwort = Ziffer, korrekte Paraphrase früherer Bewerberaussage (PASS nur mit prüfbarem Zitat, ohne die frühere Zeile UNCLEAR), `coach_suggestion` gibt erfundene Ich-Antworten nicht frei (auch bei falschem Label), Speicherbehauptungen. `tests/unit/test_host_dialogue.py`: neue/geänderte/gelöschte Dateien über Hashes, Zeiger im Konfigurationsordner, Ausnahmen nur exakt und begründet.

### Befehle, Exitcodes, Ergebnisse (Lauf `final5`, Belege `.tmp/tests/final5/`, lokal und git-ignoriert)
| Prüfung | Exit | Ergebnis |
|---|---|---|
| `python3 -B scripts/run_tests.py --kind deterministic` (`deterministic.log`; nach der Doku erneut) | 0 / 0 | 290 Tests OK |
| `python3 scripts/plugin.py check` (`plugin-check.log`) | 0 | valid |
| Szenarien A, C–J (`run_scenarios.py --cli claude --scenario …`, je `scenario-*.log`) | 0 | 8 von 9 Szenarien PASS |
| Szenario B `followup_motivation_role_fit` im selben Lauf | 1 | **FAIL** (Details unten) |
| `run_host_dialogue.py --host claude` (`host-claude.json`) | 0 | stop 17/17, pause 13/13, nostorage 10/10 |
| `run_host_dialogue.py --host codex` (`host-codex.json`) | 0 | stop 17/17, pause 13/13, nostorage 10/10 |

> **KORREKTUR (2026-11-20, nach Transkript-Durchsicht von final5): Die folgende Einordnung von Szenario B ist teilweise falsch und bleibt zur Nachvollziehbarkeit erhalten.** Die Rollenpassung wurde laut Transkript des Hauptlaufs *nur im Run* festgehalten (die STOP-Antwort sagt selbst: „Ein `match`- oder `preparation`-Snapshot für den Job wurde nicht angelegt. Der Passungspunkt steht bisher nur im Lauf.“), nicht im stellenspezifischen Match-Artefakt; und nach STOP wurde fälschlich eine Fortsetzung angeboten („Beim Fortsetzen stelle ich die offene Nachfrage einmal erneut.“), obwohl ein gestoppter Lauf final ist und die Runtime nur `paused` fortsetzt. Das waren zwei Produktfehler, nicht (nur) eine zu enge Erwartung „genau eine Nachfrage“. Die Aussage unten „die Rollenpassung wurde korrekt als stellenbezogener Passungspunkt gespeichert“ und die Wertung „kein Verstoß“ gelten nicht. Die 3 bestandenen Wiederholungen von B prüften diese beiden Punkte nicht (das Artefakt prüfte nur Run-Felder).

**Szenario B (FAIL, manuell eingeordnet).** Im Lauf stellte der Coach nach der beantworteten Klärung („Meinen Sie damit eigene technische Umsetzung oder die Verantwortung für ein Produkt …?“ → eigenes Programmieren) eine zweite Nachfrage („Was hat Sie trotzdem dazu bewogen, sich auf die Stelle … zu bewerben?“), die beim STOP offen blieb. Das Skript erwartet `followup_count=1` und keine offene Nachfrage; die Run-Artefaktprüfung schlug deshalb fehl. Einordnung: kein Verstoß gegen die bestätigten Regeln (keine feste Quote; die Nachfrage ist einzeln, neutral, ohne Bewertung; die Rollenpassung wurde korrekt als stellenbezogener Passungspunkt gespeichert, nicht als Schwäche), aber die Erwartung des Szenarios an die genaue Anzahl ist eng. Sie wurde **nicht** abgeschwächt, weil eine Änderung den Quellstand verändern und alle Ergebnisse entwerten würde. Drei Wiederholungen auf demselben Quellstand (`rerunB1–3.log`, Exit 0) bestanden alle; das ist keine Kompensation des FAIL im Hauptlauf, sondern die Streuung: B bestand 3 von 4 Läufen auf `3256005a…`. Offen: Soll das Szenario eine zweite, nicht beantwortete Nachfrage tolerieren? Das ist eine Entscheidung über das Soll, nicht von mir getroffen.

**Fachliche Durchsicht (manuell, Transkripte aus `scenarios/*.json` und `host-*.json`).**
- Nicht-speichern, Claude und Codex: STOP-Antworten sagen „nichts gespeichert“ bzw. fassen nur im Chat zusammen; keine Datei im Projekt (Claude 0 Dateien vorher, Codex 30 gehashte Skill-Dateien vorher, keine Änderung), kein Eintrag im Konfigurationsordner, kein Runtime-Aufruf. Die Erkennung falscher Erfolgsmeldungen und unerlaubter Dateien ist durch die Unit-Tests belegt, nicht durch einen absichtlich fehlerhaften Hostlauf.
- Szenario D: Der Coach schloss und bewertete den Block sofort (7/10) ohne Nachfrage (Judge-Rohurteil `deepening_or_close: true`). Der Zweig „genau eine deepening-Frage“ wurde in diesem Lauf nicht durchlaufen. Kleine Ungenauigkeit: „zeitlicher Rahmen fehlt“, obwohl der Termin in drei Wochen genannt war (als Verbesserungsvorschlag vertretbar, nicht als Fehlbehauptung gewertet).

### Verbleibende Lücken
- Szenario B im Hauptlauf FAIL (siehe oben); alle Szenarien sind Einzelstichproben, Judge heuristisch und nur mit Claude.
- Deepening-Zweig von Szenario D und der Coaching-/Hinweisfall E sind nicht auf den Hosts geprüft; Mock, Rollenpassung (B/C) und Stellen-Training mit Pause laufen nicht als Hostlauf (Stellen-Training-Pause nur deterministisch).
- Nicht-speichern-Host: Zwei Läufe (je einer pro Host), `NOSTORAGE_ALLOWED` blieb leer, weil keine unvermeidbaren Artefakte im Projekt auftraten; Host-eigene Sitzungsverläufe außerhalb von Projekt und Konfigurationsordner (z. B. unter `~/.claude`, `~/.codex`) werden nicht erfasst.
- Payload-Kopie, keine Marketplace-Installation; Akteurtausch bei fälschlich „belegt“ gemeldeten Aussagen bleibt eine Judge-Grenze.

## Nachtrag 2026-11-20 (Abschluss) — Nachfrage-Dialog R20: Source-Review-Punkte behoben, finaler Lauf auf einem Quellstand

Dieser Abschnitt ersetzt die Ergebnisse des darunter stehenden früheren Nachtrags „Nachfrage-Dialog (R20)“ (anderer, älterer Stand; dort „Codex NOT RUN“ und offene `no_invention`-Befunde sind überholt). Ergebnisse verschiedener Stände werden **nicht** zusammengerechnet: das Gesamtergebnis unten gilt nur für den Lauf `final4`.

**Quellstand.** Fingerprint (SHA-256 über sortierte Dateihashes von `skills/`, `tests/`, `scripts/`, beiden Plugin-Manifestordnern, `SCOPE.md`, `plugin.json`; 92 Dateien; Skript `.tmp/tests/fingerprint.py`): `f9df5367bc49f3233992b87ffb5bcab0277045ab66bf8acfdf07da5de222fc57` am Anfang **und** am Ende des Laufs (keine Änderung während des Laufs). Uncommitteter Arbeitsbaum auf `868c3db`. Evidenz (lokal, git-ignoriert): `.tmp/tests/final4/` (`deterministic.log`, `plugin-check.log`, `scenario-*.log`, `scenarios/*.json` mit vollständigen Dialogen und Judge-Rohurteilen, `host-claude.json`, `host-codex.json` mit allen Turns, Checks und Details, `fingerprint-*.txt`). Orchestrierung: `.tmp/tests/run_final.sh`.

**Behobene Review-Punkte (Source, getrennt von Tests).**
1. `evaluation.md`: pauschale Bewertung nach jeder Einzelantwort entfernt; Bewertung erst bei Blockabschluss (vollständige Antwort schließt sofort), Mock erst am Interviewende; optionale Beispiele werden nie nachträglich Pflicht; Bewertung bleibt bei Bewerberaussagen (keine unterstellten Motive/Zwecke, nichts als „offen“ bezeichnen, was gesagt wurde).
2. Judge-Kontext (`tests/behavior/run_scenarios.py`): Judge erhält freigegebene fiktive Quellen (CV/Profil/Posting/Dateien) und den bisherigen Dialog mit getrennten Zeilen `CANDIDATE`/`COACH`; Coach-Zeilen sind keine Evidenz.
3. Judge-Zuverlässigkeit: Status `PASS|FAIL|UNCLEAR`. Ungültiges JSON, fehlende/nicht-boolesche Urteile, Anschuldigung ohne verifizierbares Zitat, nicht klassifizierte oder widersprüchliche Evidenzangaben → `UNCLEAR`, nie PASS. `no_invention` scheitert nur bei verifiziertem Zitat, `candidate_fact`, fehlender Evidenz und neuem Inhalt; neue Wörter allein beweisen nichts; frühere Bewerberaussagen zählen; `coach_suggestion` ist keine Bewerberbehauptung. Skript-Antworten werden gegen die letzte Coach-Frage geprüft (`script_fits_question`); ein Mismatch ist `UNCLEAR` (Testskript-, kein Produktbefund).
4. Fortsetzung (`continuation_problem`, Runtime): erlaubt sind Beantworten einer offenen Nachfrage, `hints_before` einer offenen Nachfrage nur false→true, Anhängen von Nachfragen/Wiederholungen/Hauptfragen, Füllen einer leeren `initial_assessment`, Ersetzen von `block_assessment` bzw. Entfernen von `other_open_gaps` im letzten Checkpoint-Block **nur mit neuer Evidenz**. Abgelehnt (vor dem Schreiben): Entfernen eines dokumentierten Hinweises, Ändern von Antwort/Art/Anlass/Wortlaut/Lücke/Auflösung beantworteter Nachfragen, Ändern früherer Blöcke, Verschwinden dokumentierter Lücken ohne Evidenz.
5. Szenarien: D/F erlauben `deepening` (`allowed_kinds`) statt `followup_count=0`; D wertet den Block über Schritte (`evaluable_over`); F ohne unterstellte Nachfrage.
6. Nachfrage-Regel geschärft (eine Fragezeichen, keine mit „und“ verbundene zweite Frage).

**Offene Modellbefunde A/F/J (aus gespeicherten fiktiven Dialogen der Läufe `claude-r2/r3`; Zitate sinngemäß aus den Transkripten).**
- A (`followup_adr_deadline`, Schritt 3): Der Satz „Offen bleibt, ob Sie vorher beide Teams anhören“ widerspricht der Erstantwort („mit beiden Teams durchgehen“) → **Produktfehler (gering)**: ungenaue Wiedergabe, keine erfundene Bewerberbehauptung; durch die Regel „nichts als offen bezeichnen, was gesagt wurde“ adressiert. Zusätzlich im Lauf `final` (älterer Stand) in D: „damit sich keine Seite als Verlierer fühlt“ → **Produktfehler**: unterstellter Zweck; Regel „keine Motive/Zwecke unterstellen“ ergänzt.
- F (Schritt 3): Beanstandet war vermutlich die Beispielformulierung „Ich bereite die Entscheidung vor …, der Product Owner entscheidet“; sie ist als „etwa:“-Vorschlag markiert → **Judge-Fehler** (Coach-Vorschlag), im neuen Judge als `coach_suggestion` behandelt. Das Judge-Rohurteil mit Zitaten lag damals nicht gespeichert vor → dieser Punkt bleibt **unklarer Befund** (nur aus dem Transkript rekonstruiert).
- J (Schritt 3, Lauf `r2`): „Kommunikation / Prägnanz: 7/10 – Antworten sind knapp und sachlich“ bewertet einen nicht erfragten Stilaspekt; „Beziehen Sie beide Teams … ein“ ignoriert, dass die Erstantwort das nannte → **Produktfehler (gering)** bzw. unklar, welches Zitat der Judge meinte; durch die neuen Regeln adressiert.
- Wiederkehrender **Produktfehler** (Läufe `final3`, 2 von 9 Szenarien, ältere Regelfassung): zweiteilige Nachfrage („…, und bis wann würden Sie entscheiden?“), vom Judge zu Recht beanstandet; Regel verschärft, Lauf `final4` ohne diesen Befund (Einzelstichprobe, kein Beweis der Dauerhaftigkeit).

**Befehle, Exitcodes, Ergebnisse (alle auf Quellstand `f9df5367…`, Lauf `final4`).**

| Prüfart | Befehl | Exit | Ergebnis |
|---|---|---|---|
| Deterministische Gesamtsuite (Unit/Integration/Contracts; Runtime-Tests) | `python3 -B scripts/run_tests.py --kind deterministic` | 0 | 283 Tests OK (u. a. `test_followups.py` 20 Tests inkl. Regression Hinweis→Pause→Fortsetzung→Antwort bleibt `supported`, erlaubte/verbotene Änderungen; `test_run_scenarios.py` Judge-Fälle: ungültiges JSON, fehlende Urteile, fehlende Zitate, Rückbezüge auf frühere Bewerberaussagen; `test_host_dialogue.py`) |
| Manifestprüfung (aktuelle Architektur) | `python3 scripts/plugin.py check` | 0 | valid |
| Modellszenarien A–J (heuristisch, Claude CLI 2.1.319, Tools aus, Judge = zweiter Modellaufruf) | `python3 -B tests/behavior/run_scenarios.py --cli claude --scenario <id> --timeout 300 --output-dir …/scenarios` je Szenario | 0 (9×) | 9/9 PASS: adr_deadline (A), motivation_role_fit (B/C), complete_answer (D), gap_stays_open (E), optional_example (F), stop_open (G), mock (H), pause_resume (I), no_storage (J) |
| Mehrturn-Host Claude Code 2.1.319 | `python3 -B tests/native/run_host_dialogue.py --host claude --output …/host-claude.json` | 0 | stop 17/17, pause 13/13, nostorage 7/7 Checks |
| Mehrturn-Host Codex 0.165.0 | `python3 -B tests/native/run_host_dialogue.py --host codex --output …/host-codex.json` | 0 | stop 17/17, pause 13/13, nostorage 7/7 Checks |

**Host-Szenarien (beobachtet; je ein Lauf pro Host, fiktive Daten, isolierte temporäre Projekte, Payload-Kopie, keine Installation).** `stop`: Hauptfrage → unvollständige Antwort → genau eine Nachfrage zum Termin (ohne Bewertung/Lösungshinweis) → Ergänzung → Blockbewertung (Erstantwort und Ergänzung getrennt) → STOP → ein gespeicherter Run. Aus dem Run mit der echten Runtime geprüft: Bewerber-ID, `job_id` null, `stopped_early`, Zähler 1/1/1/0 (Haupt/Nachfrage/beantwortete Nachfrage/Wiederholung), Hauptfrage und Originalantwort wörtlich, Nachfragewortlaut/Art/Anlass/Lücke, Ergänzung wörtlich, `hints_before=false` → eigene Evidenz nach Nachfrage (nicht unterstützt), getrennte Erst-/Blockbewertung, Planzahl 3. `pause`: Pause bei offener Nachfrage (Checkpoint `paused`, 1/1/0, Nachfrage `pending`, Planzahl 3) → **neue Sitzung** → `resume` → nur die offene Nachfrage wird einmal erneut gestellt → Antwort → STOP → zweiter Run mit `resume_from`, gleicher Bewerber/Stelle, Planzahl erhalten, Zähler 1/1/1/0 (keine Doppelzählung), Checkpoint-Datei byte-identisch. `nostorage`: derselbe Dialog, kein Runtime-Aufruf, keine Datei, Chat-Zusammenfassung. Zwei Hosts nutzen die Session-Fortsetzung der CLI (Claude `--session-id/--resume`, Codex `exec resume`); die Hosts legen dabei ihre üblichen Sitzungsverläufe ab (kein Eingriff in Plugin-Installation/Einstellungen).

**Verbleibende Lücken / Grenzen (ausdrücklich).**
- Stichproben: jedes Szenario genau ein Lauf pro Stand; Modellverhalten ist nichtdeterministisch (frühere Läufe `final`–`final3` zeigten Abweichungen, siehe oben). Kein Wiederholbarkeitsnachweis.
- Judge heuristisch (zweiter Modellaufruf, nur Claude); Host-Dialogchecks sind strukturell (Fragezeichen, Schlüsselwörter, Leak-Muster, Runtime-Zustand), die inhaltliche Qualität der Transkripte wurde stichprobenartig, nicht vollständig manuell geprüft.
- Nicht auf den Hosts geprüft: Coaching-/Hinweisfälle (Szenario E: Lücke bleibt offen, Antworten nach Coaching als `supported`; Hinweis→Pause→Fortsetzung) — nur deterministisch (Runtime) und im Modellszenario E (Claude, ohne Host); Mock (H) und Rollenpassung (B/C) nur als Modellszenario; Pause bei Stellen-Training (`job-training`, mit `job_id`) nur deterministisch.
- Keine Prüfung gegen echte veröffentlichte Installation (Marketplace), nur Payload-Kopie; keine Live-/Provider-Abnahme (nicht Teil dieses Auftrags).
- Während der Arbeit mussten Testskripte nachgebessert werden (Judge, Szenarien, Host-Runner); frühere Zwischenläufe (`final`, `final2`, `final3`/`final3-superseded`) sind keine Abnahme des finalen Stands. `final3` scheiterte an zwei Szenarien (Mock, Pause/Fortsetzung: zweiteilige Nachfrage) → Regel verschärft → `final4`.
- Run-Format 4 lehnt Altruns (Format 3) ab; keine Migration; keine privaten Daten gelesen oder verändert.

## Nachtrag 2026-11-20 (überholt durch den Abschluss-Nachtrag oben) — Nachfrage-Dialog (R20), Run-Format 4

Getrennt nach Prüfart. Alle Daten fiktiv, isolierte temporäre Projekte; keine persönliche Plugin-Installation, keine privaten Daten, kein Commit.

**1. Strukturelle Vertragsprüfung (beweist kein Dialogverhalten).** `tests/contracts/test_skill_contract.py::test_followup_dialogue_rules_are_present_and_linked_structural_only`, `test_scope.py` (R1–R20), `python3 scripts/plugin.py check` → valid. Ergebnis: bestanden.

**2. Tatsächliche Runtime-Tests (deterministisch).** `python3 -B scripts/run_tests.py --kind deterministic`: 267 Tests, OK. Neu `tests/integration/workspace/test_followups.py` (14 Tests): getrennte Zähler (Nachfrage erhöht `answered_count` nicht, Abweichung wird vor dem Schreiben abgelehnt), Art/Evidenzklassen, deepening ohne Lücke, offene Lücke, unterstützte Wiederholung nach Coaching (E), STOP/Pause mit unbeantworteter Nachfrage (G), Fortsetzung ohne Wiederholung/Änderung beantworteter Inhalte und mit unveränderter Planzahl (I), Run-Format 3 wird vor Schreibzugriffen abgelehnt und bleibt unverändert, `-->` in Antworten, CLI `--dialogue-file`. Gesamtsuite zuvor bereits rot-grün geprüft (Anpassung bestehender Tests an Format 4).

**3. Heuristische Modellprüfung** (`tests/behavior/run_scenarios.py`, Claude CLI 2.1.319, Tools aus, Rubrik-Judge = zweiter Modellaufruf; Szenarien A–J als `followup_*.json`). Drei Läufe mit Korrekturen dazwischen (Interviewsprache im Preset bestätigt; Szenario D vollständigere Antwort; F ohne Pflicht „keine Nachfrage“; Harness: Fortsetzung darf nur Nachfragen schließen, wiederholter erfolgreicher Save ist kein Fehlschlag). Letzter Stand je Szenario: PASS: complete_answer (D), gap_stays_open (E), stop_open (G), mock (H), motivation_role_fit (B/C), pause_resume (I) – jeweils im letzten Lauf, in dem das Szenario lief. FAIL (nur Rubrik `no_invention`, Judge-Beanstandung von Verbesserungsvorschlägen im Bewertungstext, nicht manuell als echte Erfindung bestätigt): adr_deadline (A) Schritt 3, optional_example (F) Schritt 3, no_storage (J) Schritt 3 (Lauf 2; nicht wiederholt). Beobachtete reale Befunde, behoben: vor der Nachfrage lobte das Modell die Erstantwort („klare Struktur …“) → Regel „nur neutrale Bestätigung ohne Wertung“; Passungspräferenz wurde als niedrige Antwortnote gewertet → Regel „Klärung ist kein Abzug, Passung getrennt“; Dialogdatei ohne `gap` bei clarification wurde von der Runtime korrekt abgelehnt → Hinweis in runtime.md. Eine mehrteilige statt einer einzelnen Nachfrage in A wurde in einem Lauf vom Judge beanstandet (nicht erneut geprüft). Nicht durchgängig grün: kein Gesamt-PASS.

**4. Beobachtetes Hostverhalten (ein Turn, `tests/native/run_native.py`, Phase `followup_adr_deadline`).** Claude Code (Payload-Kopie, temporäres Projekt): 4/4 Phasen bestanden; Nachfrage genau eine, zum Release-Termin, ohne Bewertung/Musterantwort, kein `finish`. Einzelner Lauf, keine Mehrturn-Hostabnahme. Dabei wurden zwei ältere Phasen-Prompts um die Interviewsprache ergänzt (vorher scheiterte `candidate_with_cv` an der korrekten Sprachrückfrage). **Codex: NOT RUN** für den Dialog – der Lauf `setup_local,candidate_with_cv,candidate_confirm_erika` lief in das 150-s-Timeout (zuvor bestand `setup_local` allein); kein Ersatz durch Texttest.

**Nicht ausgeführt / offen.** Mehrturn-Hostlauf (Claude Code und Codex) der Szenarien A–J (nur Einzelturn A auf Claude Code); `make test-behavior|journey` nicht neu gelaufen; `no_invention`-Beanstandungen in A/F/J nicht manuell verifiziert; Szenario-Judge ist heuristisch; Modellverhalten kann pro Lauf abweichen.

**Datenformat.** Run-Format 4 (Header `schema_version: 4`, neue Felder `followup_count`, `followup_answered_count`, `retry_count`, `dialogue`). Vorhandene Runs im Format 3 werden vor Schreibzugriffen abgelehnt (Bewerber blockiert), nicht migriert, nicht verändert. `finish` verlangt `--dialogue-file`. Workspace-, Kandidaten-, Job- und Journal-Format unverändert (3).

## Nachtrag 2026-11-20 — Deterministische Tests nach Git-Entfernung und Sprachänderung

Nach ausdrücklicher Testfreigabe ausgeführt:

- `make test`: **251 Tests, OK**, 14,063 Sekunden, Exitcode 0 (Unit, Integration, Verträge).
- `make check-plugin`: **valid: true**, Exitcode 0; keine Manifeständerungen nötig.
- `git diff --check`: Exitcode 0.

Der erste Testlauf hatte zwei fehlgeschlagene Assertions (neues Szenario fehlte in der erwarteten Liste;
Symlink-Test erwartete nur „symlink“, Diagnose verwendet „symbolic link“) und drei PDF-Fehler wegen des
nicht beschreibbaren Swift-Compiler-Caches. Die Testdefinitionen wurden korrigiert. Beim erfolgreichen
Gesamtlauf zeigten `CLANG_MODULE_CACHE_PATH` und `SWIFT_MODULECACHE_PATH` auf separate Unterordner eines
neuen temporären Verzeichnisses. Keine Änderung an der PDF-Runtime oder Installation von Werkzeugen.
Rohprotokoll dieser lokalen Sitzung: `/tmp/interview-coach-tests.vGpDgT/results.log` (temporär).

Diese Ergebnisse ersetzen die NOT-RUN-Angaben der folgenden beiden Nachträge nur für die deterministischen
Tests. Modelltests und echte Claude-Code-/Codex-Dialogabnahme wurden nicht ausgeführt. FAIL/BLOCKED-Ausgaben
im Rohprotokoll stammen aus absichtlich simulierten Negativfällen der bestandenen Runner-Unit-Tests.

## Nachtrag 2026-11-20 — Git-Speicherung entfernt

Aktueller Umfang: ausschließlich Lokal und Nicht speichern. Git-Runtime, CLI-Befehle,
Provider-Parameter und Git-Speichertests entfernt; frühere Git-Ergebnisse unten sind historische Nachweise
für den damaligen Umfang, keine aktuellen Produktzusagen. Neue Ablehnungstests:
`tests/integration/workspace/test_storage_modes.py`. Dialogszenarien prüfen zwei Speicheroptionen.
**NOT RUN**: Tests und Host-Abnahme dieser Änderung wurden nicht ausgeführt. Bestehende Git-Zeiger und
Daten werden abgelehnt und unverändert erhalten; keine automatische Migration.

## Nachtrag 2026-11-20 — Interviewsprache pro Bewerber und Stelle

R5 erweitert: Bediensprache bleibt projektbezogen; Interviewsprache als Bewerberstandard mit optionaler
Stellenabweichung. Runtime, Dialogregeln und Nutzungshinweise angepasst. Neue Akzeptanztests:
`tests/integration/workspace/test_languages.py` (Trennung, Vererbung, CLI, Ablehnung bisheriger Sprachdaten).
**NOT RUN**: keine Testausführung für diesen Nachtrag; frühere Ergebnisse belegen diese Änderungen nicht.
Native Claude-Code-/Codex-Dialogabnahme und Git-Verhalten des neuen Sprachbefehls sind noch ungeprüft.
Bestehende globale Interviewpräferenzen und Datensätze ohne Sprachfeld werden ohne Migration abgelehnt.

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
- Native Verfügbarkeit der fünf Skills im Codex-Host: **nicht belegt** (nur das aus dem Installationspaket erzeugte Manifest `.codex-plugin/plugin.json` mit `skills: ./skills/` und fünf SKILL.md statisch vorhanden).
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
