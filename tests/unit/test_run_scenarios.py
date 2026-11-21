"""Harness logic only (fake model). Real model scenarios are explicit and heuristic: make test-scenarios."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'Makefile').is_file())
SPEC = importlib.util.spec_from_file_location('run_scenarios', ROOT / 'tests/behavior/run_scenarios.py')
scenarios = importlib.util.module_from_spec(SPEC)
import sys
sys.path.insert(0, str(ROOT / 'tests/behavior'))
SPEC.loader.exec_module(scenarios)
sys.path.insert(0, str(ROOT))
from tests.support import coach as support  # noqa: E402

REQUIRED = {'followup_adr_deadline', 'followup_motivation_role_fit', 'followup_complete_answer', 'followup_gap_stays_open',
            'followup_optional_example', 'followup_stop_open', 'followup_mock', 'followup_pause_resume', 'followup_no_storage',
            'setup_two_options', 'setup_local_accept', 'candidate_create_with_cv', 'candidate_create_without_cv', 'same_name_selection',
            'general_training_answer', 'job_create_missing_company', 'job_create_unknown_participants',
            'job_create_ambiguous_person', 'job_training_reuse_second_run', 'job_training_second_run',
            'stop_pause_resume', 'no_storage_no_writes', 'storage_failure_no_false_success',
            'job_training_insufficient_answer', 'general_training_insufficient_answer', 'research_fixture_namesake'}


class Fixtures(unittest.TestCase):
    def test_all_required_scenarios_exist_and_are_well_formed(self):
        self.assertEqual(REQUIRED, set(scenarios.all_ids()))
        for name in scenarios.all_ids():
            data = scenarios.load(name)
            self.assertEqual(name, data['id'])
            self.assertTrue(data['steps'] and all(s['user'] for s in data['steps']), name)
            for skill in data['skills']:
                self.assertTrue((ROOT / 'skills' / skill / 'SKILL.md').is_file(), skill)

    def test_every_scenario_sandbox_builds_with_real_runtime(self):
        for name in scenarios.all_ids():
            sandbox = scenarios.Sandbox(scenarios.load(name))
            self.addCleanup(sandbox.cleanup)
            self.assertTrue(sandbox.project.is_dir())
            if scenarios.load(name).get('preset', {}).get('storage') == 'local':
                self.assertEqual(0, scenarios.iw.workspace_problems(sandbox.workspace) and 1 or 0, name)


class Harness(unittest.TestCase):
    def scripted(self, replies):
        calls = iter(replies)
        return lambda prompt: next(calls)

    def tool(self, sub):
        return f'TOOL: python3 {scenarios.RUNTIME} {sub}'

    def test_scripted_good_model_passes_setup_scenario_and_creates_artifacts(self):
        scenario = scenarios.load('setup_two_options')
        replies = ['Wo möchtest du speichern? Lokal oder Nicht speichern.',
                   'PLACEHOLDER', 'Welches Verzeichnis (Pfad) soll verwendet werden?']
        holder = {}

        def model(prompt):
            if replies:
                reply = replies.pop(0)
                if reply == 'PLACEHOLDER':
                    import re
                    project = re.search(r'Current project folder: (\S+)\.', prompt).group(1)
                    return f'Ordner {project}/interview-data: Ja, hier speichern / Nein, anderen Ordner wählen'
                return reply
            if 'YOUR PREVIOUS REPLY' not in prompt:
                import re
                path = re.search(r'in (/\S+/ws) speichern', prompt).group(1)
                project = re.search(r'Current project folder: (\S+)\.', prompt).group(1)
                return self.tool(f'project-init --project {project} --storage local --path {path}')
            return 'Die lokale Einrichtung ist abgeschlossen: der Speicherort ist eingerichtet.'
        result = scenarios.run_scenario(scenario, model, context='CTX')
        self.assertTrue(result['passed'], json.dumps(result, indent=1, default=str)[:2000])
        self.assertEqual(['project-init'], [e['subcommand'] for e in result['tool_log']])

    def test_arbitrary_shell_and_foreign_project_are_rejected_not_executed(self):
        sandbox = scenarios.Sandbox({'id': 'x', 'steps': []})
        self.addCleanup(sandbox.cleanup)
        log = []
        self.assertIn('REJECTED', sandbox.execute('rm -rf /', log))
        self.assertIn('REJECTED', sandbox.execute('python3 /etc/passwd', log))
        self.assertIn('REJECTED', sandbox.execute(f'python3 {scenarios.RUNTIME} validate --project /tmp', log))
        self.assertIn('REJECTED', sandbox.execute('python3 "unterminated', log))
        self.assertFalse([e for e in log if 'subcommand' in e])

    def test_write_channel_is_confined_to_the_files_directory(self):
        sandbox = scenarios.Sandbox({'id': 'x', 'steps': []})
        self.addCleanup(sandbox.cleanup)
        log = []
        self.assertEqual('written', sandbox.write(str(sandbox.files / 'sub/a.md'), 'hello', log))
        self.assertEqual('hello', (sandbox.files / 'sub/a.md').read_text())
        for bad in (str(sandbox.tmp / 'ws/x.md'), '/etc/x', 'relative.md', str(sandbox.files / '../escape.md')):
            self.assertIn('REJECTED', sandbox.write(bad, 'x', log))
        self.assertFalse((sandbox.tmp / 'escape.md').exists())
        parsed = scenarios.extract_writes('text\nWRITE_FILE: /a/b.md\n<<<\nline1\nline2\n>>>\nmore')
        self.assertEqual([('/a/b.md', 'line1\nline2')], parsed)

    def test_no_storage_violations_are_detected(self):
        scenario = scenarios.load('no_storage_no_writes')
        bad = self.scripted([self.tool('project-init --project X --storage local --path Y'), 'Eine Frage?', 'Gesamtbewertung 5/10', 'Beendet. Zusammenfassung. nicht gespeichert.'])
        result = scenarios.run_scenario(scenario, bad, context='CTX')
        self.assertFalse(result['passed'])
        self.assertTrue(any('tool calls issued' in e for step in result['steps'] for e in step['errors']))

    def test_false_success_claim_is_detected(self):
        scenario = scenarios.load('storage_failure_no_false_success')
        sandbox_ids = {}

        def model(prompt):
            if 'LATEST USER MESSAGE:\nstop' in prompt and 'YOUR PREVIOUS REPLY' not in prompt:
                return 'Das Training ist beendet und erfolgreich gespeichert.'
            return 'Erste Frage: Wie gehst du vor?' if 'Starte' in prompt else 'Gesamtbewertung 6/10'
        result = scenarios.run_scenario(scenario, model, context='CTX', judge=lambda p: '{"one_question": true, "reason": true, "save_failed_honestly": false}')
        self.assertFalse(result['passed'])
        joined = ' '.join(e for step in result['steps'] for e in step['errors'])
        self.assertIn('rubric failed: save_failed_honestly', joined)
        self.assertIn('tool call not attempted: finish', joined)

    def test_artifact_checks_report_missing_and_non_byte_exact_files(self):
        sandbox = scenarios.Sandbox({'id': 'x', 'steps': [], 'files': {'cv.md': 'abc'}})
        self.addCleanup(sandbox.cleanup)
        (sandbox.tmp / 'ws').mkdir()
        (sandbox.tmp / 'ws/copy.md').write_text('different')
        errors = scenarios.check_artifacts(sandbox, [
            {'type': 'exists', 'glob': 'ws/missing.md'}, {'type': 'sha_equals', 'glob': 'ws/copy.md', 'file': 'cv.md'},
            {'type': 'count', 'glob': 'ws/*.md', 'equals': 2}, {'type': 'absent', 'path': 'ws'}])
        self.assertEqual(4, len(errors))


class Rubric(unittest.TestCase):
    """Negative and positive cases for the semantic-contract checks (no word lists)."""
    GOOD = ("**Gesamtbewertung: 6/10** Dein Vorgehen ist nachvollziehbar, aber die Wirkung bleibt offen.\n"
            "- Vorgehen: 8/10 – klare Abfolge aus Analyse, Fix und Test.\n- Qualität: 7/10 – Regressionstest erwähnt.\n"
            "- Wirkung: 4/10 – Ergebnis nicht belegt. " + "Mehr Kontext wäre hilfreich. " * 6)

    def test_evaluable_answer_requires_score_criteria_and_substance(self):
        step = {'evaluable': True}
        self.assertEqual([], scenarios.structural_errors(step, self.GOOD))
        self.assertTrue(scenarios.structural_errors(step, 'Gute Antwort, weiter so. ' * 30))          # feedback without any score
        self.assertTrue(scenarios.structural_errors(step, 'Gesamtbewertung 6/10. Gut.'))              # score but no criteria/substance
        self.assertTrue(scenarios.structural_errors(step, 'Gesamtbewertung 6/10 ' + 'x ' * 200))      # no criterion scores

    def test_insufficient_answer_structure_requires_concrete_reasoning_and_leaves_the_follow_up_to_the_rubric(self):
        step = {'needs_evidence': True}
        reply = ('Deine Antwort nennt keine konkrete Situation, keine eigene Handlung und kein Ergebnis; deshalb kann ich sie noch '
                 'nicht fair bewerten. Beschreibe bitte ein tatsächliches Beispiel.')
        self.assertEqual([], scenarios.structural_errors(step, reply))     # an imperative prompt is a valid follow-up, no '?' needed
        self.assertTrue(scenarios.structural_errors(step, 'Mehr Details?'))  # no reasoning
        self.assertIn('single_followup', scenarios.RUBRIC)
        verdict = lambda prompt: '{"reason": true, "followup": true, "single_followup": false, "score_cautious": true}'
        self.assertEqual(['rubric failed: single_followup'], scenarios.run_judge(verdict, ['reason', 'followup', 'single_followup', 'score_cautious'], 'u', reply)[1])

    def invented(self, *items):
        return json.dumps({'no_invention': False, 'invented': list(items)})

    def test_invention_needs_verified_quote_candidate_fact_and_new_content(self):
        user = 'Ich habe den Fehler in der Retry-Logik gefunden und den Support informiert.'
        reply = 'Gut. Formulierung: "Ich habe mich auf stabile Produktionssysteme konzentriert und den Support informiert."'
        run = lambda raw, **kw: scenarios.run_judge(lambda p: raw, ['no_invention'], user, reply, **kw)
        fact = {'quote': 'mich auf stabile Produktionssysteme konzentriert', 'source': 'candidate_fact', 'in_evidence': False}
        self.assertTrue(run(self.invented(fact))[1][0].startswith('rubric failed: no_invention'))
        # supported restatement: only with a verifiable evidence quote
        restated = {'quote': 'den Support informiert', 'source': 'candidate_fact', 'in_evidence': True, 'evidence_quote': 'den Support informiert'}
        self.assertEqual(([], True), (run(self.invented(restated))[1], run(self.invented(restated))[0]['no_invention']))
        # NOT a pass: hallucinated quote, accusation without quote, unclassified statement, evidence claim without a verifiable quote
        no_anchor = dict(restated, evidence_quote='steht nirgends')
        for raw in (self.invented(dict(fact, quote='quote that is not in the reply')), '{"no_invention": false}', self.invented({'quote': fact['quote']}),
                    self.invented(dict(restated, evidence_quote=None)), self.invented(no_anchor)):
            verdicts, problems = run(raw)
            self.assertIsNone(verdicts['no_invention'], raw)
            self.assertTrue(problems[0].startswith('rubric unclear: no_invention'), problems)

    def test_same_vocabulary_does_not_overrule_a_negative_judge(self):
        # every content word occurs in the candidate evidence, but the meaning differs: never PASS
        user = 'Wir haben den Release nicht verschoben. Die Plattform-Gruppe hat entschieden, ich habe 2 Wochen Puffer eingeplant.'
        cases = {
            'added negation': ('Sie haben den Release nicht verschoben, nicht wahr?', 'Sie haben den Release nicht nicht verschoben'),
            'swapped actors': ('Ich habe entschieden, die Plattform-Gruppe hat Puffer eingeplant.', 'die Plattform-Gruppe hat Puffer eingeplant'),
        }
        for name, (reply, quote) in cases.items():
            claim = self.invented({'quote': quote if quote in reply else reply[:30], 'source': 'candidate_fact', 'in_evidence': False})
            verdicts, problems = scenarios.run_judge(lambda p: claim, ['no_invention'], user, reply)
            self.assertIsNone(verdicts['no_invention'], name)       # unsupported + same words: UNCLEAR, not the old automatic PASS
            self.assertTrue(problems and problems[0].startswith('rubric unclear'), (name, problems))

    def test_removed_or_added_negation_and_changed_numbers_are_found_against_the_evidence_quote(self):
        evidence = 'Wir haben den Release nicht verschoben. Ich habe 2 Wochen Puffer eingeplant.'
        def check(reply, quote, anchor):
            claim = self.invented({'quote': quote, 'source': 'candidate_fact', 'in_evidence': True, 'evidence_quote': anchor})
            return scenarios.run_judge(lambda p: claim, ['no_invention'], 'Weiter.', reply, [], evidence)
        # removed negation
        verdicts, problems = check('Sie haben den Release verschoben.', 'den Release verschoben', 'den Release nicht verschoben')
        self.assertIs(False, verdicts['no_invention'])
        self.assertIn('negation differs', problems[0])
        # added negation
        evidence_pos = 'Wir haben den Release verschoben.'
        claim = self.invented({'quote': 'den Release nicht verschoben', 'source': 'candidate_fact', 'in_evidence': True, 'evidence_quote': 'den Release verschoben'})
        verdicts, problems = scenarios.run_judge(lambda p: claim, ['no_invention'], 'Weiter.', 'Sie haben den Release nicht verschoben.', [], evidence_pos)
        self.assertIs(False, verdicts['no_invention'])
        self.assertIn('negation differs', problems[0])
        # changed number (digit versus spelled-out number counts as equal)
        verdicts, problems = check('Sie haben 4 Wochen Puffer eingeplant.', '4 Wochen Puffer eingeplant', '2 Wochen Puffer eingeplant')
        self.assertIs(False, verdicts['no_invention'])
        self.assertIn('numbers differ', problems[0])
        self.assertEqual(([], True), (lambda r: (r[1], r[0]['no_invention']))(check('Sie haben zwei Wochen Puffer eingeplant.', 'zwei Wochen Puffer eingeplant', '2 Wochen Puffer eingeplant')))

    def test_correct_paraphrase_of_an_earlier_candidate_statement_passes_with_a_verifiable_quote(self):
        history = [('user', 'Ich habe die Entscheidung im ADR begründet und beide Teams vorher angehört.'), ('assistant', 'Danke.')]
        reply = 'Sie sagten, dass Sie vor der Entscheidung beide Teams gehört und sie im ADR dokumentiert haben.'
        claim = self.invented({'quote': 'vor der Entscheidung beide Teams gehört', 'source': 'candidate_fact', 'in_evidence': True,
                               'evidence_quote': 'beide Teams vorher angehört'})
        verdicts, problems = scenarios.run_judge(lambda p: claim, ['no_invention'], 'Weiter.', reply, history)
        self.assertEqual(([], True), (problems, verdicts['no_invention']))
        # the same claim without the earlier candidate line: not evidence
        self.assertIsNone(scenarios.run_judge(lambda p: claim, ['no_invention'], 'Weiter.', reply, [])[0]['no_invention'])

    def test_coach_suggestion_label_does_not_release_invented_first_person_answers(self):
        user = 'Ich würde die Optionen im ADR festhalten.'
        run = lambda reply, **item: scenarios.run_judge(lambda p: self.invented(dict(item, source='coach_suggestion')), ['no_invention'], user, reply)
        recommendation = 'Sie könnten die Kriterien vorab mit beiden Teams abstimmen.'
        self.assertEqual(([], True), (lambda r: (r[1], r[0]['no_invention']))(run(recommendation, quote=recommendation, suggestion_kind='recommendation')))
        invented_answer = 'Sagen Sie: "Ich habe im letzten Projekt die Latenz um 40 % gesenkt."'
        quote = 'Ich habe im letzten Projekt die Latenz um 40 % gesenkt'
        verdicts, problems = run(invented_answer, quote=quote, suggestion_kind='first_person_answer', invents_experience=True)
        self.assertIs(False, verdicts['no_invention'])
        self.assertIn('invents experience', problems[0])
        # judge says "does not invent" but the numbers are new: still found; mislabelled as recommendation: wording decides
        for kind, flag in (('first_person_answer', False), ('recommendation', None)):
            verdicts, problems = run(invented_answer, quote=quote, suggestion_kind=kind, invents_experience=flag)
            self.assertIs(False, verdicts['no_invention'], kind)
        # hypothetical wording without invented facts is fine; a missing kind or missing verdict stays unclear
        hypothetical = 'Etwa: "Ich würde die Optionen im ADR festhalten und beide Teams anhören."'
        hq = 'Ich würde die Optionen im ADR festhalten und beide Teams anhören'
        self.assertEqual([], run(hypothetical, quote=hq, suggestion_kind='first_person_answer', invents_experience=False)[1])
        self.assertIsNone(run(hypothetical, quote=hq)[0]['no_invention'])
        claim_past = 'Sagen Sie: "Ich habe das Team neu aufgestellt."'
        self.assertIsNone(run(claim_past, quote='Ich habe das Team neu aufgestellt', suggestion_kind='first_person_answer')[0]['no_invention'])
        self.assertIsNone(run(claim_past, quote='Ich habe das Team neu aufgestellt', suggestion_kind='first_person_answer', invents_experience=False)[0]['no_invention'])

    def test_earlier_candidate_statements_and_released_sources_count_as_evidence(self):
        reply = 'Sie sagten, Sie hätten das Produktmanagement vorab über den Kompromiss informiert.'
        quote = 'das Produktmanagement vorab über den Kompromiss informiert'
        claim = self.invented({'quote': quote, 'source': 'candidate_fact', 'in_evidence': True, 'evidence_quote': quote})
        history = [('user', 'Ich habe das Produktmanagement vorab über den Kompromiss informiert.'), ('assistant', 'Danke.')]
        self.assertEqual([], scenarios.run_judge(lambda p: claim, ['no_invention'], 'Weiter.', reply, history)[1])
        # earlier COACH lines are not evidence
        coach_only = [('assistant', 'Denken Sie an das Produktmanagement vorab über den Kompromiss informieren.')]
        self.assertIsNone(scenarios.run_judge(lambda p: claim, ['no_invention'], 'Weiter.', reply, coach_only)[0]['no_invention'])
        # released fictional sources count
        source_claim = self.invented({'quote': quote, 'source': 'candidate_fact', 'in_evidence': True, 'evidence_quote': 'Produktmanagement vorab über den Kompromiss informiert'})
        self.assertEqual([], scenarios.run_judge(lambda p: source_claim, ['no_invention'], 'Weiter.', reply, [], 'Profil: Produktmanagement vorab über den Kompromiss informiert')[1])
        # unsupported and nowhere in the evidence: a verified finding
        denied = self.invented({'quote': quote, 'source': 'candidate_fact', 'in_evidence': False})
        self.assertEqual(['rubric failed'], [x[:13] for x in scenarios.run_judge(lambda p: denied, ['no_invention'], 'Weiter.', reply, [])[1]])

    def test_new_words_alone_are_no_proof(self):
        reply = 'Sie haben also Entscheidungskompetenz bewiesen.'
        claim = self.invented({'quote': 'Entscheidungskompetenz bewiesen', 'source': 'candidate_fact', 'in_evidence': True})
        self.assertTrue(scenarios.run_judge(lambda p: claim, ['no_invention'], 'Ich entscheide.', reply)[1][0].startswith('rubric unclear'))

    def test_judge_prompt_separates_candidate_and_coach_lines_and_carries_sources(self):
        prompt = scenarios.judge_prompt(['no_invention'], 'jetzt', 'Antwort', [('user', 'U1'), ('assistant', 'C1')], 'CV-Text')
        self.assertIn('CANDIDATE (scripted test user): U1', prompt)
        self.assertIn('COACH: C1', prompt)
        self.assertIn('RELEASED FICTIONAL SOURCES:\nCV-Text', prompt)
        self.assertIn('coach_suggestion', prompt)
        for key in ('evidence_quote', 'suggestion_kind', 'invents_experience'):
            self.assertIn(key, prompt)

    def test_judge_verdicts_are_enforced_and_unclear_or_missing_is_never_a_pass(self):
        verdicts, problems = scenarios.run_judge(lambda prompt: '{"strengths": true, "improvements": false}', ['strengths', 'improvements'], 'u', 'r')
        self.assertEqual({'strengths': True, 'improvements': False}, verdicts)
        self.assertEqual(['rubric failed: improvements'], problems)
        for raw in ('no json', '[1]', '{"strengths": "yes"}', '{}', '{"strengths": null}'):
            verdicts, problems = scenarios.run_judge(lambda prompt, r=raw: r, ['strengths'], 'u', 'r')
            self.assertIsNone(verdicts['strengths'], raw)
            self.assertTrue(problems[0].startswith('rubric unclear'), (raw, problems))
        self.assertIn('not checked', scenarios.run_judge(None, ['strengths'], 'u', 'r')[1][0])
        self.assertEqual(({}, []), scenarios.run_judge(None, [], 'u', 'r'))

    def test_scenario_status_distinguishes_fail_unclear_and_pass(self):
        scenario = {'id': 'x', 'context': 'c', 'steps': [{'user': 'Hallo', 'judge': ['strengths']}]}
        run = lambda raw: scenarios.run_scenario(scenario, lambda p: 'Antwort', context='CTX', judge=lambda p: raw)
        self.assertEqual(('PASS', True), (run('{"strengths": true}')['status'], run('{"strengths": true}')['passed']))
        self.assertEqual('FAIL', run('{"strengths": false}')['status'])
        unclear = run('garbage')
        self.assertEqual(('UNCLEAR', False), (unclear['status'], unclear['passed']))
        self.assertTrue(unclear['unclear'])
        self.assertEqual('UNCLEAR', scenarios.run_scenario(scenario, lambda p: 'Antwort', context='CTX', judge=None)['status'])

    def test_block_evaluation_may_span_earlier_steps_but_must_exist_somewhere(self):
        full = 'Gesamtbewertung: 7/10. ' + 'Einzelbewertung: Struktur 8/10, Verantwortung 7/10, Termin 6/10. ' * 5
        scenario = {'id': 'x', 'context': 'c', 'steps': [{'user': 'Antwort'}, {'user': 'Bewerte den Block.', 'evaluable_over': [1]}]}
        replies = iter([full, 'Gerne, es bleibt dabei.'])
        ok = scenarios.run_scenario(scenario, lambda p: next(replies), context='CTX', judge=lambda p: '{}')
        self.assertEqual('PASS', ok['status'])
        replies = iter(['Danke.', 'Gerne, es bleibt dabei.'])
        bad = scenarios.run_scenario(scenario, lambda p: next(replies), context='CTX', judge=lambda p: '{}')
        self.assertEqual('FAIL', bad['status'])
        self.assertTrue(any('no overall score' in e for e in bad['steps'][1]['errors']))

    def test_scripted_answer_must_fit_the_coach_question(self):
        scenario = {'id': 'x', 'context': 'c', 'steps': [{'user': 'Start'}, {'user': 'Kriterien sind Aufwand.', 'answers_previous_question': True}]}
        model = lambda p: 'Welche Frist gilt?'
        fits = scenarios.run_scenario(scenario, model, context='CTX', judge=lambda p: '{"script_fits_question": true}')
        self.assertEqual('PASS', fits['status'])
        misfit = scenarios.run_scenario(scenario, model, context='CTX', judge=lambda p: '{"script_fits_question": false}')
        self.assertEqual('UNCLEAR', misfit['status'])           # a test-script problem, not a product verdict
        self.assertTrue(any('scenario script' in e for e in misfit['unclear']))
        self.assertEqual('UNCLEAR', scenarios.run_scenario(scenario, model, context='CTX', judge=lambda p: 'x')['status'])

    def test_failed_tool_calls_cannot_support_success_claims_or_required_calls(self):
        failed = [{'argv': ['finish'], 'subcommand': 'finish', 'rc': 1, 'line': 'python3 rt finish --x'}]
        errors = scenarios.evaluate_tools({'tools_include': ['finish']}, failed, 0, 'Der Lauf wurde gespeichert und verifiziert.')
        self.assertIn('missing successful tool call: finish (call failed)', errors)
        self.assertIn('reply claims a successful save although the save command failed', errors)
        honest = scenarios.evaluate_tools({'tools_attempted': ['finish'], 'tools_must_fail': ['finish']}, failed, 0,
                                          'Das Speichern ist fehlgeschlagen; es wurde nichts gespeichert.')
        self.assertEqual([], honest)

    def test_save_claim_detection(self):
        for claim in ('Der Lauf wurde gespeichert.', 'Ich habe alles gespeichert und verifiziert.', 'Gespeichert.', '\u2705 Gespeichert unter runs/q.md',
                      'Die Sitzung wurde gesichert.', 'Your run has been saved.', 'Ergebnis: **Gespeichert**'):
            self.assertTrue(scenarios.claims_saved(claim), claim)
        for no_claim in ('Es wurde nichts gespeichert.', 'Der Lauf wurde nicht gespeichert.', 'Speichern fehlgeschlagen, nicht gespeichert.',
                         'Das Training ist beendet, gespeichert ist der Abbruch aber **nicht**.', 'Der Lauf ist nicht persistiert.',
                         'Nicht speichern: Es wurde nichts gespeichert oder abgelegt.', 'Nothing was saved.', 'Wenn Sie speichern möchten, wählen Sie Lokal.'):
            self.assertFalse(scenarios.claims_saved(no_claim), no_claim)

    def test_resume_promise_after_stop_is_detected_and_pause_or_negation_is_not(self):
        promise = 'Die Sitzung ist beendet. Beim Fortsetzen stelle ich die offene Nachfrage einmal erneut.'
        for reply in (promise, 'Gespeichert. Wir können morgen weitermachen und ich greife die Nachfrage wieder auf.',
                      'You can resume later and I will ask the open follow-up again.',
                      'Beim Fortsetzen mit `resume` stelle ich die offene Nachfrage einmal erneut.',
                      'Ich greife die offene Nachfrage später wieder auf.'):
            self.assertTrue(scenarios.promises_resume(reply), reply)
        for reply in ('Die Sitzung ist beendet; die Nachfrage bleibt unbeantwortet und kann nicht fortgesetzt werden.',
                      'Ein beendeter Lauf ist final. Zum späteren Weitermachen hätten Sie pause genutzt.',
                      'Nur ein pausierter Lauf kann fortgesetzt werden.', 'Die Sitzung ist beendet und gespeichert.',
                      # observed false positives (final7): pointing to `pause` is the honest answer, not a promise
                      'Wenn Sie ein andermal an einer offenen Frage weitermachen wollen, nutzen Sie dafür künftig `pause`.',
                      'Mit `pause` statt `stop` hätte ich einen Fortsetzungspunkt gespeichert.',
                      'Die offene Nachfrage ist beantwortet, es gibt also nichts zum Fortsetzen.',
                      # observed false positives of the first detector (final6): starting something NEW is not resuming this session
                      'Frage 2 stelle ich in einer neuen Session erneut.', 'Wenn Sie später weitermachen möchten, starten Sie eine neue Sitzung.',
                      'Wenn Sie ein andermal weitermachen möchten, starte ich ein neues Training.',
                      'Lauf `run-002` mit Status `stopped_early` und Fortsetzung von `run-001`.',
                      'Der Verlauf liegt unter [run-continuation-01.md](/tmp/x/runs/run-continuation-01.md).',
                      # observed false positives (final8): advice to the user, descriptions of `pause`, a new run
                      '**Nächstes Training:** Beantworten Sie Frage 1 später unabhängig noch einmal, diesmal mit Kriterien und Wirkung.',
                      'Wenn Sie ein andermal weitermachen möchten, starten Sie einen neuen Durchlauf.',
                      'Wenn du ein andermal weitermachen willst, nenne mir die Frage und deine Antwort erneut.',
                      'Das speichert einen Fortsetzungspunkt.', '- Den Termin schon in der Erstantwort aufgreifen.',
                      # observed false positive (final12): a new training takes up the stored learning state
                      'Wenn Sie ein anderes Mal weitermachen wollen, starten Sie ein neues Training. Dort greife ich den gespeicherten Lernstand auf.'):
            self.assertFalse(scenarios.promises_resume(reply), reply)

    def test_judge_if_rated_items_apply_only_to_replies_that_contain_a_rating(self):
        scenario = {'id': 'x', 'context': 'c', 'steps': [{'user': 'a', 'judge_if_rated': ['strengths']}]}
        asked = []
        for reply in ('Welche Kriterien nutzen Sie?', 'Gesamtbewertung 7/10. Gut.'):
            scenarios.run_scenario(scenario, lambda p, r=reply: r, context='CTX', judge=lambda p: (asked.append('strengths' in p.split('RULES:')[1]), '{"strengths": true}')[1])
        self.assertEqual([True], asked)       # the judge is not asked at all for the unrated follow-up reply

    def test_judge_sees_the_whole_block_evaluation_when_it_was_given_in_earlier_replies(self):
        full = 'Gesamtbewertung: 7/10. ' + 'Einzelbewertung: Struktur 8/10, Verantwortung 7/10, Termin 6/10. ' * 5
        scenario = {'id': 'x', 'context': 'c', 'steps': [{'user': 'Antwort'}, {'user': 'Bewerte den Block.', 'evaluable_over': [1], 'judge': ['strengths']}]}
        seen = []
        replies = iter([full, 'Zu Frage 2 liegt noch keine Antwort vor.'])
        scenarios.run_scenario(scenario, lambda p: next(replies), context='CTX', judge=lambda p: (seen.append(p), '{"strengths": true}')[1])
        self.assertIn('Gesamtbewertung: 7/10', seen[-1].split('FINAL COACH REPLY:')[1])

    def test_step_flag_turns_a_resume_promise_into_a_scenario_failure_only_where_requested(self):
        promise = 'Beendet. Beim Fortsetzen stelle ich die offene Nachfrage einmal erneut.'
        flagged = {'id': 'x', 'context': 'c', 'steps': [{'user': 'stop', 'no_resume_promise': True}]}
        result = scenarios.run_scenario(flagged, lambda p: promise, context='CTX', judge=lambda p: '{}')
        self.assertEqual('FAIL', result['status'])
        self.assertTrue(any('promises to resume' in e for e in result['steps'][0]['errors']))
        pause = {'id': 'x', 'context': 'c', 'steps': [{'user': 'pause'}]}      # a pause may offer the resumption
        self.assertEqual('PASS', scenarios.run_scenario(pause, lambda p: 'Zwischenstand gespeichert, zum Fortsetzen nutzen Sie resume.', context='CTX', judge=lambda p: '{}')['status'])
        shipped = [json.loads(p.read_text()) for p in sorted((ROOT / 'tests/fixtures/behavior/scenarios').glob('followup_*.json'))]
        for scenario in shipped:   # every shipped stop step of the follow-up scenarios carries the check
            for step in scenario['steps']:
                if step['user'].strip().lower() == 'stop':
                    self.assertTrue(step.get('no_resume_promise'), scenario['id'])

    def test_dialogue_matches_first_kind_and_minimum_without_fixing_the_count(self):
        header = {'dialogue': [{'followups': [{'kind': 'clarification', 'answer': 'x', 'resolution': 'closed'},
                                              {'kind': 'completion', 'answer': None, 'resolution': 'pending'}], 'retries': [], 'other_open_gaps': []}]}
        self.assertTrue(scenarios.dialogue_matches(header, {'first_followup_kind': 'clarification', 'min_followups': 1}))
        self.assertFalse(scenarios.dialogue_matches(header, {'first_followup_kind': 'completion'}))
        self.assertFalse(scenarios.dialogue_matches(header, {'min_followups': 3}))
        self.assertFalse(scenarios.dialogue_matches({'dialogue': [{'followups': [], 'retries': [], 'other_open_gaps': []}]}, {'min_followups': 1}))

    def test_job_artifact_check_reads_the_stored_match_assignment_and_keeps_state_free_of_it(self):
        iw = scenarios.iw
        scenario = scenarios.load('followup_motivation_role_fit')
        sandbox = scenarios.Sandbox(scenario)
        self.addCleanup(sandbox.cleanup)
        spec = next(a for a in scenario['artifacts'] if a['type'] == 'job_artifact')
        self.assertEqual(['no stored match snapshot under any job'], scenarios.job_artifact_errors(sandbox, spec))
        cid = sandbox.ids['CANDIDATE0']
        job = iw.list_jobs(sandbox.workspace, cid)[0]['job_id']
        with iw.candidate_lock(sandbox.workspace, cid) as cdir:
            iw.add_artifact(cdir, iw.job_dir(cdir, job), 'match', 'Passung Product Owner: Wunsch nach eigener technischer Umsetzung, Produktverantwortung dagegen.')
        # snapshot exists, but no saved run belongs to this candidate/job yet
        self.assertTrue(any('without a saved run' in e for e in scenarios.job_artifact_errors(sandbox, spec)))
        state = sandbox.workspace / 'candidates' / cid / 'state.md'
        iw.finish(sandbox.workspace, cid, 'r1', '# Run\n', state.read_text(encoding='utf-8'), status='stopped_early', answered_count=1, planned_count=3,
                  job_id=job, expected_state_sha256=iw.snapshot(sandbox.workspace, cid)['state_sha256'], dialogue=[support.block(1, followups=[support.followup(1, 1)])])
        self.assertEqual([], scenarios.job_artifact_errors(sandbox, spec))
        # the same point written into the cross-job state is a failure: it would be a general weakness
        state.write_text(state.read_text(encoding='utf-8') + '\n- Schwäche: will selbst programmieren\n', encoding='utf-8')
        self.assertTrue(any('state.md' in e for e in scenarios.job_artifact_errors(sandbox, spec)))
        # a snapshot that lacks the preference fails
        self.assertTrue(any('lacks' in e for e in scenarios.job_artifact_errors(sandbox, dict(spec, patterns=['Kubernetes-Betrieb']))))

    def case(self, name):
        return json.loads((ROOT / 'tests/fixtures/behavior/judge_cases' / f'{name}.json').read_text(encoding='utf-8'))

    def test_final10_role_fit_dialogue_is_a_negative_case_for_score_reasons_built_on_the_declined_role(self):
        bad, control = self.case('final10_B_role_fit_penalty'), self.case('control_B_separated_rating')
        self.assertIs(False, bad['expect']['role_fit_job_specific'])
        found = scenarios.preference_penalty_lines(bad['reply'])
        self.assertTrue(any('reizt' in line for line in found), found)                       # overall 5/10 justified by missing appeal
        self.assertTrue(any('anspricht' in line for line in found), found)                   # 'Substanz der Begründung: 4/10'
        self.assertTrue(any('Absage' in line for line in found), found)
        self.assertIn('ohne Punktzahl', bad['reply'])                                         # the heading did not rescue it
        self.assertEqual([], scenarios.preference_penalty_lines(control['reply']))
        # the step flag turns this into a scenario failure
        scenario = {'id': 'x', 'context': 'c', 'steps': [{'user': 'u', 'no_preference_penalty': True}]}
        failed = scenarios.run_scenario(scenario, lambda p: bad['reply'], context='CTX', judge=lambda p: '{}')
        self.assertEqual('FAIL', failed['status'])
        self.assertEqual('PASS', scenarios.run_scenario(scenario, lambda p: control['reply'], context='CTX', judge=lambda p: '{}')['status'])
        # shipped scenario B carries the flag on the rating step
        self.assertTrue(scenarios.load('followup_motivation_role_fit')['steps'][2]['no_preference_penalty'])

    def test_judge_calibration_cases_are_wired_to_the_real_rubric_and_detect_a_wrong_judge(self):
        cases = scenarios.calibration_cases()
        self.assertGreaterEqual(len(cases), 17)
        for case in cases:
            for key in case['expect']:
                self.assertIn(key, scenarios.RUBRIC, case['id'])
        evidence_keys = {'no_invention', 'no_false_missing'}       # a negative verdict there needs quotes (tested separately)
        plain = [c for c in cases if not any(v is False and k in evidence_keys for k, v in c['expect'].items())]
        answers = {c['reply'].strip(): c['expect'] for c in plain}
        right = lambda p: json.dumps(answers[p.split('FINAL COACH REPLY:')[1].strip()])
        self.assertTrue(all(row[4] for row in scenarios.run_calibration(right, plain)))
        lenient = lambda p: json.dumps({k: True for k in scenarios.RUBRIC})                         # the judge that let the overlooked errors pass
        missed = {row[0] for row in scenarios.run_calibration(lenient, cases) if not row[4]}
        self.assertEqual({c['id'] for c in cases if False in c['expect'].values()}, missed)
        self.assertTrue({'final10_B_role_fit_penalty', 'final10_host_claude_false_missing', 'final13_B_unasked_example_deduction',
                         'final13_D_unsupported_attribution', 'final12_host_claude_two_followups', 'clarify_suggestive', 'clarify_prejudging',
                         'final14_B_rep2_origin_and_situation_demanded', 'final14_B_rep3_origin_of_wish_demanded', 'final14_D_rep3_invented_contrast'} <= missed)
        self.assertFalse(all(row[4] for row in scenarios.run_calibration(lambda p: 'no json', cases)))   # UNCLEAR is never an accepted verdict

    def test_final13_D_unsupported_attribution_is_found_only_with_a_verifiable_quote(self):
        case = self.case('final13_D_unsupported_attribution')
        quote = 'Du denkst den Termindruck von Anfang an mit und lässt ihn nicht erst am Ende nachträglich einfließen.'
        raw = json.dumps({'no_invention': False, 'invented': [{'quote': quote, 'source': 'candidate_fact', 'in_evidence': False}]})
        verdicts, problems = scenarios.run_judge(lambda p: raw, ['no_invention'], case['user'], case['reply'], [tuple(x) for x in case['history']])
        self.assertIs(False, verdicts['no_invention'])
        self.assertIn('Anfang', problems[0])
        # a faithful restatement of what the candidate said is supported by their own words
        ok = json.dumps({'no_invention': False, 'invented': [{'quote': 'Wegen des festen Termins in drei Wochen würde ich den Release-Umfang reduzieren', 'source': 'candidate_fact',
                                                               'in_evidence': True, 'evidence_quote': 'Wegen des festen Termins in drei Wochen würde ich den Release-Umfang reduzieren'}]})
        reply = case['reply'] + '\nWegen des festen Termins in drei Wochen würde ich den Release-Umfang reduzieren'
        self.assertEqual([], scenarios.run_judge(lambda p: ok, ['no_invention'], case['user'], reply, [])[1])

    def test_unstated_characterizations_are_found_in_the_final13_rating_and_not_in_recommendations_or_own_words(self):
        case = self.case('final13_D_unsupported_attribution')
        said = ' '.join(m for r, m in [tuple(x) for x in case['history']] if r == 'user') + ' ' + case['user']
        found = scenarios.unstated_characterizations(case['reply'], said)
        self.assertEqual(1, len(found), found)
        self.assertIn('von Anfang an', found[0])
        self.assertEqual([], scenarios.unstated_characterizations('Du denkst den Termindruck von Anfang an mit.', said + ' Ich denke den Termin von Anfang an mit.'))   # own words
        self.assertEqual([], scenarios.unstated_characterizations('Sie könnten den Termin von Anfang an einbeziehen.', said))                  # recommendation
        scenario = {'id': 'x', 'context': 'c', 'steps': [{'user': 'u', 'no_unstated_characterization': True}]}
        self.assertEqual('FAIL', scenarios.run_scenario(scenario, lambda p: case['reply'], context='CTX', judge=lambda p: '{}')['status'])
        shipped = scenarios.load('followup_complete_answer')
        self.assertTrue(all(shipped['steps'][i].get('no_unstated_characterization') for i in (1, 2)))
        self.assertIn("von Anfang an", scenarios.judge_prompt(['no_invention'], 'u', 'r'))

    def test_final14_regressions_origin_of_wish_invented_contrasts_and_dialogue_course(self):
        rep2, rep3 = self.case('final14_B_rep2_origin_and_situation_demanded'), self.case('final14_B_rep3_origin_of_wish_demanded')
        # rep3: the deterministic guard found it although the judge passed it; rep2: the example/situation guard and the judge
        self.assertTrue(scenarios.preference_penalty_lines(rep3['reply']), 'origin of the wish as score reason')
        self.assertTrue(scenarios.preference_penalty_lines(rep2['reply']), 'no situation/experience/motives as score reason')
        self.assertEqual({'no_unasked_example_deduction': False}, rep2['expect'])
        self.assertEqual({'role_fit_job_specific': False}, rep3['expect'])
        # D rep3 and J rep1: invented contrasts are found deterministically, own words and recommendations are not
        d3 = self.case('final14_D_rep3_invented_contrast')
        said = ' '.join(m for r, m in [tuple(x) for x in d3['history']] if r == 'user') + ' ' + d3['user']
        found = scenarios.unstated_characterizations(d3['reply'], said)
        self.assertTrue(any('statt erst' in x for x in found), found)
        j = 'Der Kompromiss wird dem Produktmanagement vorab erklärt und nicht erst im Nachhinein.'
        self.assertTrue(scenarios.unstated_characterizations(j, said))
        self.assertEqual([], scenarios.unstated_characterizations(j, said + ' nicht erst im Nachhinein'))
        self.assertEqual([], scenarios.unstated_characterizations('Sie könnten es vorab erklären statt erst nach der Entscheidung.', said))
        # the judge false positive of final14 J: dialogue-course statements are allowed by prompt and kept as a control case
        prompt = scenarios.judge_prompt(['no_invention'], 'u', 'r')
        self.assertIn('COURSE of this dialogue', prompt)
        self.assertEqual({'no_invention': True}, self.case('final14_J_rep1_dialogue_course_is_no_invention')['expect'])
        for key in ('followup_complete_answer', 'followup_adr_deadline', 'followup_no_storage'):
            self.assertTrue(any(s.get('no_unstated_characterization') for s in scenarios.load(key)['steps']), key)

    def test_clarification_rubric_accepts_open_and_neutral_choice_and_rejects_suggestive_or_prejudging(self):
        rubric = scenarios.RUBRIC['clarify_motivation_neutral']
        self.assertIn('OPEN', rubric)
        self.assertIn('NEUTRAL choice', rubric)
        self.assertIn('naming possible meanings is NOT required', rubric)
        self.assertIn('suggestive', rubric)
        expect = {c['id']: c['expect']['clarify_motivation_neutral'] for c in scenarios.calibration_cases() if 'clarify_motivation_neutral' in c['expect']}
        self.assertEqual({'clarify_open': True, 'clarify_choice': True, 'clarify_suggestive': False, 'clarify_prejudging': False}, expect)
        for name in ('open', 'choice'):                              # both accepted forms are one answer task with one question mark
            self.assertEqual(1, scenarios.question_marks(self.case(f'clarify_{name}')['reply']))

    def test_final13_B_missing_example_is_found_in_scores_stored_text_and_by_the_rubric(self):
        bad, control = self.case('final13_B_unasked_example_deduction'), self.case('control_B_example_optional')
        self.assertTrue(any('Beispiel' in line for line in scenarios.example_penalty_lines(bad['reply'])), scenarios.example_penalty_lines(bad['reply']))
        self.assertEqual([], scenarios.example_penalty_lines(control['reply']))
        self.assertIn('Optional: ein Beispiel', control['reply'])        # an optional recommendation stays allowed
        scenario = {'id': 'x', 'context': 'c', 'steps': [{'user': 'u', 'no_example_deduction': True}]}
        self.assertEqual('FAIL', scenarios.run_scenario(scenario, lambda p: bad['reply'], context='CTX', judge=lambda p: '{}')['status'])
        self.assertEqual('PASS', scenarios.run_scenario(scenario, lambda p: control['reply'], context='CTX', judge=lambda p: '{}')['status'])
        shipped = scenarios.load('followup_motivation_role_fit')
        self.assertTrue(shipped['steps'][2]['no_example_deduction'])
        self.assertIn('no_unasked_example_deduction', shipped['steps'][2]['judge'])
        stored = next(a for a in shipped['artifacts'] if a['type'] == 'stored_text_absent')
        # what final13 really stored (run block_assessment, run text, state next-training) matches the patterns
        import re
        for text in ('Konkretheit 5/10, es fehlt ein Beispiel.', 'Konkretheit 5/10 (kein Beispiel).', '- Antworten konkret formulieren und mit einem Beispiel belegen.'):
            self.assertTrue(any(re.search(p, text) for p in stored['patterns']), text)
        self.assertFalse(any(re.search(p, 'Optional: ein Beispiel würde die Aussage stützen.') for p in stored['patterns']))

    def test_false_missing_needs_verifiable_quotes_on_both_sides_and_stays_unclear_otherwise(self):
        case = self.case('final10_host_claude_false_missing')
        history = [tuple(x) for x in case['history']]
        quote = {'quote': 'Sie sagen nicht, wie Sie die Teams einbinden', 'candidate_quote': 'mit beiden Teams durchgehen'}
        run = lambda raw: scenarios.run_judge(lambda p: raw, ['no_false_missing'], case['user'], case['reply'], history)
        verdicts, problems = run(json.dumps({'no_false_missing': False, 'false_missing': [quote]}))
        self.assertIs(False, verdicts['no_false_missing'])
        self.assertTrue(problems[0].startswith('rubric failed: no_false_missing'))
        # a bare 'false', a hallucinated claim quote, a candidate quote that no candidate line contains, unrelated quotes: UNCLEAR, never PASS and never FAIL
        for raw in ({'no_false_missing': False}, {'no_false_missing': False, 'false_missing': [dict(quote, quote='steht nirgends in der Antwort')]},
                    {'no_false_missing': False, 'false_missing': [dict(quote, candidate_quote='das hat niemand gesagt')]},
                    {'no_false_missing': False, 'false_missing': [{'quote': 'Sie sagen nicht, wie Sie die Teams einbinden', 'candidate_quote': 'Release-Termin in drei Wochen'}]},
                    {'no_false_missing': False, 'false_missing': [{'quote': quote['quote']}]}):
            verdicts, problems = run(json.dumps(raw))
            self.assertIsNone(verdicts['no_false_missing'], raw)
            self.assertTrue(problems[0].startswith('rubric unclear: no_false_missing'), problems)
        self.assertIn('false_missing', scenarios.judge_prompt(['no_false_missing'], 'u', 'r'))

    def test_rubric_names_the_overlooked_reason_patterns_and_the_false_missing_rule(self):
        self.assertIn('Substanz der Begründung', scenarios.RUBRIC['role_fit_job_specific'])
        self.assertIn('Passung ohne Punktzahl', scenarios.RUBRIC['role_fit_job_specific'])
        self.assertIn('mit beiden Teams durchgehen', scenarios.RUBRIC['no_false_missing'])

    def test_one_question_mark_per_turn_flag_and_no_gaps_for_unasked_aspects(self):
        two = 'Der Release ist fest. Wie gehen Sie mit dem Termin um? Was tun Sie, wenn die Teams uneinig sind?'
        scenario = {'id': 'x', 'context': 'c', 'steps': [{'user': 'u', 'max_question_marks': 1}]}
        self.assertEqual('FAIL', scenarios.run_scenario(scenario, lambda p: two, context='CTX', judge=lambda p: '{}')['status'])
        self.assertEqual('PASS', scenarios.run_scenario(scenario, lambda p: 'Wie gehen Sie mit dem Termin um?', context='CTX', judge=lambda p: '{}')['status'])
        deepening = {'kind': 'deepening', 'answer': None, 'resolution': 'pending', 'gap': None}
        clean = {'dialogue': [{'followups': [deepening], 'retries': [], 'other_open_gaps': []}]}
        self.assertTrue(scenarios.dialogue_matches(clean, {'allowed_kinds': ['deepening'], 'no_gaps': True}))
        gap = {'dialogue': [{'followups': [deepening], 'retries': [], 'other_open_gaps': ['Entscheidungskriterien']}]}
        self.assertFalse(scenarios.dialogue_matches(gap, {'no_gaps': True}))
        completion = {'dialogue': [{'followups': [dict(deepening, kind='completion', gap='Kriterien')], 'retries': [], 'other_open_gaps': []}]}
        self.assertFalse(scenarios.dialogue_matches(completion, {'allowed_kinds': ['deepening'], 'no_gaps': True}))
        shipped = scenarios.load('followup_optional_example')
        self.assertIn({'type': 'run_dialogue', 'allowed_kinds': ['deepening'], 'no_gaps': True}, shipped['artifacts'])

    def test_model_run_artifacts_are_preserved_for_independent_review(self):
        scenario = scenarios.load('followup_motivation_role_fit')
        sandbox = scenarios.Sandbox(scenario)
        self.addCleanup(sandbox.cleanup)
        (sandbox.files / 'dialogue-001.json').write_text('[]', encoding='utf-8')
        out = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(out, ignore_errors=True))
        scenarios.preserve_artifacts(sandbox, out / 'artifacts' / 'x')
        cid = sandbox.ids['CANDIDATE0']
        self.assertTrue((out / 'artifacts/x/ws/candidates' / cid / 'state.md').is_file())
        self.assertTrue(list((out / 'artifacts/x/ws/candidates' / cid / 'jobs').glob('*/postings/*.md')))
        self.assertTrue((out / 'artifacts/x/files/dialogue-001.json').is_file())
        self.assertFalse((out / 'artifacts/x/ws/.journal').exists())

    def test_missing_confirmation_is_detected_in_the_profile_scenario(self):
        scenario = scenarios.load('candidate_create_without_cv')
        rt = scenarios.RUNTIME

        def model(prompt):
            if 'LATEST USER MESSAGE:\nLege den Bewerber' in prompt and 'YOUR PREVIOUS REPLY' not in prompt:
                return f'TOOL: python3 {rt} candidate-create --project {prompt.split("project folder: ")[1].split(".")[0]} --name "Max Muster"'
            if 'LATEST USER MESSAGE:\nLege den Bewerber' in prompt:
                return 'Welche Berufserfahrung hast du?'
            if 'LATEST USER MESSAGE:\nBerufserfahrung' in prompt:
                return 'Danke, gespeichert und bestätigt.'      # asks nothing, confirms on its own
            return 'Fertig.'
        result = scenarios.run_scenario(scenario, model, context='CTX', judge=lambda prompt: '{"confirm_question": false, "no_invention": true}')
        self.assertFalse(result['passed'])
        joined = ' '.join(e for step in result['steps'] for e in step['errors'])
        self.assertIn('rubric failed: confirm_question', joined)

    def test_missing_feedback_is_detected_in_the_training_scenario(self):
        scenario = scenarios.load('general_training_answer')
        result = scenarios.run_scenario(scenario, lambda prompt: 'Danke für deine Antwort, weiter so!', context='CTX', judge=lambda p: '{}')
        self.assertFalse(result['passed'])
        self.assertTrue(any('no overall score' in e for step in result['steps'] for e in step['errors']))


class DialogueArtifact(unittest.TestCase):
    def header(self, **kw):
        return {'dialogue': [{'followups': kw.get('followups', []), 'retries': kw.get('retries', []), 'other_open_gaps': kw.get('gaps', [])}]}

    def test_dialogue_matching_is_structural(self):
        match = scenarios.dialogue_matches
        completion = {'kind': 'completion', 'answer': None, 'resolution': 'pending'}
        self.assertTrue(match(self.header(followups=[completion]), {'followup_kinds': ['completion'], 'open_followup': True}))
        self.assertFalse(match(self.header(followups=[completion]), {'open_followup': False}))
        self.assertFalse(match(self.header(), {'followup_kinds': ['completion']}))
        deep = {'kind': 'deepening', 'answer': 'x', 'resolution': 'closed'}
        self.assertTrue(match(self.header(followups=[deep]), {'allowed_kinds': ['deepening']}))   # a deepening follow-up on a good answer is fine
        self.assertTrue(match(self.header(), {'allowed_kinds': ['deepening']}))                  # none needed is fine as well
        self.assertFalse(match(self.header(followups=[completion]), {'allowed_kinds': ['deepening']}))   # an artificial completion question is not
        self.assertTrue(match(self.header(retries=[{'after_coaching': True}], gaps=['x']), {'retry_after_coaching': True, 'open_gap': True}))
        self.assertFalse(match(self.header(retries=[{'after_coaching': False}]), {'retry_after_coaching': True}))


class ArtifactChecks(unittest.TestCase):
    def sandbox_with_runs(self, second_answered=3, second_job=None):
        sandbox = scenarios.Sandbox({'id': 'x', 'steps': [], 'preset': {'storage': 'local', 'candidates': [{'name': 'Erika Beispiel'}]}})
        self.addCleanup(sandbox.cleanup)
        cid = sandbox.ids['CANDIDATE0']
        iw = scenarios.iw
        state = iw.snapshot(sandbox.workspace, cid)['state_sha256']
        iw.finish(sandbox.workspace, cid, 'p1', '# p\n', '# s1\n', expected_state_sha256=state, status='paused', answered_count=1, planned_count=4,
                  dialogue=[support.block(1)])
        state = iw.snapshot(sandbox.workspace, cid)['state_sha256']
        iw.finish(sandbox.workspace, cid, 'p2', '# q\n', '# s2\n', expected_state_sha256=state, status='stopped_early',
                  answered_count=second_answered, planned_count=4, resume_from='p1',
                  dialogue=support.dialogue(second_answered))
        return sandbox

    def test_valid_continuation_and_immutability(self):
        sandbox = self.sandbox_with_runs()
        first = next(sandbox.tmp.glob('ws/candidates/*/runs/p1.md'))
        import hashlib
        snaps = {3: {str(first): hashlib.sha256(first.read_bytes()).hexdigest()}}
        self.assertEqual([], scenarios.check_artifacts(sandbox, [{'type': 'continuation'}, {'type': 'unchanged_since_step', 'step': 3},
                                                                {'type': 'run_field', 'equals': {'status': 'paused', 'planned_count': 4}}], snaps))

    def test_continuation_without_a_further_answer_and_changed_checkpoint_are_detected(self):
        sandbox = self.sandbox_with_runs(second_answered=1)
        errors = scenarios.check_artifacts(sandbox, [{'type': 'continuation'}], {})
        self.assertTrue(any('answered_count did not grow' in e for e in errors))
        first = next(sandbox.tmp.glob('ws/candidates/*/runs/p1.md'))
        errors = scenarios.check_artifacts(sandbox, [{'type': 'unchanged_since_step', 'step': 3}], {3: {str(first): '0' * 64}})
        self.assertTrue(any('immutable file changed' in e for e in errors))
        none = scenarios.Sandbox({'id': 'y', 'steps': []})
        self.addCleanup(none.cleanup)
        self.assertTrue(scenarios.check_artifacts(none, [{'type': 'continuation'}], {}))


if __name__ == '__main__':
    unittest.main()
