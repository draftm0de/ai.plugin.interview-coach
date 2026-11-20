"""Harness logic only (fake model). Real model scenarios are explicit and heuristic: make test-scenarios."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'Makefile').is_file())
SPEC = importlib.util.spec_from_file_location('run_scenarios', ROOT / 'tests/behavior/run_scenarios.py')
scenarios = importlib.util.module_from_spec(SPEC)
import sys
sys.path.insert(0, str(ROOT / 'tests/behavior'))
SPEC.loader.exec_module(scenarios)

REQUIRED = {'setup_three_options', 'candidate_create_with_cv', 'candidate_create_without_cv', 'same_name_selection',
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
        scenario = scenarios.load('setup_three_options')
        replies = ['Wo möchtest du speichern? Lokal, Git (privates Repository) oder Nicht speichern.',
                   'Welches Verzeichnis (Pfad) soll verwendet werden?']
        holder = {}

        def model(prompt):
            if replies:
                return replies.pop(0)
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

    def test_invention_verdicts_need_a_verifiable_quote_with_new_content(self):
        user = 'Ich habe den Fehler in der Retry-Logik gefunden und den Support informiert.'
        reply = 'Gut. Formulierung: "Ich habe mich auf stabile Produktionssysteme konzentriert und den Support informiert."'
        real = '{"no_invention": false, "invented": ["mich auf stabile Produktionssysteme konzentriert"]}'
        self.assertEqual(['rubric failed: no_invention'], scenarios.run_judge(lambda p: real, ['no_invention'], user, reply)[1])
        restated = '{"no_invention": false, "invented": ["den Support informiert"]}'              # only restates the candidate's words
        self.assertEqual([], scenarios.run_judge(lambda p: restated, ['no_invention'], user, reply)[1])
        fabricated = '{"no_invention": false, "invented": ["quote that is not in the reply"]}'      # judge hallucinated a quote
        self.assertEqual([], scenarios.run_judge(lambda p: fabricated, ['no_invention'], user, reply)[1])
        self.assertEqual([], scenarios.run_judge(lambda p: '{"no_invention": false}', ['no_invention'], user, reply)[1])  # unverifiable accusation

    def test_judge_verdicts_are_enforced_and_a_missing_judge_is_never_a_pass(self):
        verdicts, problems = scenarios.run_judge(lambda prompt: '{"strengths": true, "improvements": false}', ['strengths', 'improvements'], 'u', 'r')
        self.assertEqual({'strengths': True, 'improvements': False}, verdicts)
        self.assertEqual(['rubric failed: improvements'], problems)
        self.assertTrue(scenarios.run_judge(lambda prompt: 'no json', ['strengths'], 'u', 'r')[1])
        self.assertIn('not checked', scenarios.run_judge(None, ['strengths'], 'u', 'r')[1][0])
        self.assertEqual(({}, []), scenarios.run_judge(None, [], 'u', 'r'))

    def test_failed_tool_calls_cannot_support_success_claims_or_required_calls(self):
        failed = [{'argv': ['finish'], 'subcommand': 'finish', 'rc': 1, 'line': 'python3 rt finish --x'}]
        errors = scenarios.evaluate_tools({'tools_include': ['finish']}, failed, 0, 'Der Lauf wurde gespeichert und verifiziert.')
        self.assertIn('missing successful tool call: finish (call failed)', errors)
        self.assertIn('reply claims a successful save although the save command failed', errors)
        honest = scenarios.evaluate_tools({'tools_attempted': ['finish'], 'tools_must_fail': ['finish']}, failed, 0,
                                          'Das Speichern ist fehlgeschlagen; es wurde nichts gespeichert.')
        self.assertEqual([], honest)

    def test_save_claim_detection(self):
        for claim in ('Der Lauf wurde gespeichert.', 'Ich habe alles gespeichert und verifiziert.'):
            self.assertTrue(scenarios.claims_saved(claim), claim)
        for no_claim in ('Es wurde nichts gespeichert.', 'Der Lauf wurde nicht gespeichert.', 'Speichern fehlgeschlagen, nicht gespeichert.',
                         'Das Training ist beendet, gespeichert ist der Abbruch aber **nicht**.', 'Der Lauf ist nicht persistiert.'):
            self.assertFalse(scenarios.claims_saved(no_claim), no_claim)

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


class ArtifactChecks(unittest.TestCase):
    def sandbox_with_runs(self, second_answered=3, second_job=None):
        sandbox = scenarios.Sandbox({'id': 'x', 'steps': [], 'preset': {'storage': 'local', 'candidates': [{'name': 'Erika Beispiel'}]}})
        self.addCleanup(sandbox.cleanup)
        cid = sandbox.ids['CANDIDATE0']
        iw = scenarios.iw
        state = iw.snapshot(sandbox.workspace, cid)['state_sha256']
        iw.finish(sandbox.workspace, cid, 'p1', '# p\n', '# s1\n', expected_state_sha256=state, status='paused', answered_count=1, planned_count=4)
        state = iw.snapshot(sandbox.workspace, cid)['state_sha256']
        iw.finish(sandbox.workspace, cid, 'p2', '# q\n', '# s2\n', expected_state_sha256=state, status='stopped_early',
                  answered_count=second_answered, planned_count=4, resume_from='p1')
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
