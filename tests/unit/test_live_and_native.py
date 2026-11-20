"""Harness logic of the explicit native/live runners. The runners themselves are NOT run by the deterministic suite."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'Makefile').is_file())


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    return module


native = load('tests/native/run_native.py', 'run_native')
live = ROOT / 'tests/live/run_live_git.py'


class LiveGitRunner(unittest.TestCase):
    def run_live(self, *args):
        return subprocess.run([sys.executable, '-B', str(live), *args], capture_output=True, text=True)

    def test_dry_run_prints_plan_and_phrase_without_any_action(self):
        done = self.run_live('--provider', 'github', '--repo', 'example-owner/test', '--branch', 'coach-live-test', '--dry-run')
        self.assertEqual(0, done.returncode)
        self.assertIn("'WRITE fictional data to github:example-owner/test@coach-live-test'", done.stdout)
        self.assertIn('DRY RUN: nothing was executed', done.stdout)

    def test_without_the_exact_approval_phrase_nothing_runs(self):
        for extra in ([], ['--approve', 'yes'], ['--approve', 'WRITE fictional data to github:other/repo@coach-live-test']):
            done = self.run_live('--provider', 'github', '--repo', 'example-owner/test', '--branch', 'coach-live-test', *extra)
            self.assertEqual(2, done.returncode)
            self.assertIn('NOT RUN', done.stdout)

    def test_primary_branches_are_refused(self):
        for branch in ('main', 'master', 'develop'):
            self.assertNotEqual(0, self.run_live('--provider', 'gitlab', '--repo', 'g/p', '--branch', branch, '--dry-run').returncode)


class NativeRunner(unittest.TestCase):
    def test_event_parsing_for_both_hosts(self):
        claude = native.Host.__new__(native.Host)
        claude.name = 'claude'
        out = '\n'.join(json.dumps(e) for e in (
            {'type': 'system', 'subtype': 'init', 'skills': ['interview-coach:job-create', 'other']},
            {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'Bash', 'input': {'command': 'python3 x/interview_workspace.py project-show --project P'}},
                                                         {'type': 'tool_use', 'name': 'WebFetch', 'input': {'url': 'https://example.com/a'}}]}},
            {'type': 'result', 'result': 'fertig'}))
        parsed = claude.parse(subprocess.CompletedProcess([], 0, out, ''))
        self.assertEqual(['interview-coach:job-create'], parsed['skills'])
        self.assertEqual(['project-show'], native.subcommands(parsed))
        self.assertEqual('https://example.com/a', parsed['web'][0]['input']['url'])
        codex = native.Host.__new__(native.Host)
        codex.name = 'codex'
        out = '\n'.join(json.dumps(e) for e in (
            {'type': 'item.completed', 'item': {'type': 'command_execution', 'command': "python3 .agents/skills/_shared/scripts/interview_workspace.py status --project P", 'exit_code': 0}},
            {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'ok'}}))
        parsed = codex.parse(subprocess.CompletedProcess([], 0, out, ''))
        self.assertEqual(['status'], native.subcommands(parsed))
        self.assertEqual('ok', parsed['text'])

    def test_phase_list_covers_the_required_native_checks(self):
        class Stub:
            pass
        run = Stub()
        run.ws = Path('/x/ws')
        run.project = Path('/x/p')
        run.files = Path('/x/f')
        names = [p[0] for p in native.phases(run)]
        for needed in ('discovery', 'three_options', 'setup_local', 'candidate_with_cv', 'candidate_without_cv_unconfirmed',
                       'candidate_confirm_new_chat', 'same_name_selection', 'job_create', 'job_training', 'training_saved', 'reload_new_chat'):
            self.assertIn(needed, names)


class NativeJobTrainingCheck(unittest.TestCase):
    """Deterministic acceptance logic with fictional host results (no model, no host run)."""

    QUESTION = ("Wir üben für die Stelle Senior Backend Engineer bei der Beispiel AG.\n"
                "**Erste Frage:** Erzähl mir von einer Python-API, bei der du eine technische Entscheidung getroffen hast.")

    def test_job_related_interview_question_is_accepted(self):
        self.assertEqual((True, ''), native.training_question(self.QUESTION))

    def test_pure_profile_confirmation_question_is_rejected(self):
        ok, why = native.training_question("Für die Stelle bei der Beispiel AG: Stimmen die Angaben in deinem Profil und soll ich es bestätigen?")
        self.assertFalse(ok)
        self.assertIn('no job-related interview question', why)

    def test_selection_question_is_rejected(self):
        ok, _ = native.training_question("Es gibt zwei Kandidatinnen namens Erika Beispiel (Beispiel AG, Python). Welche meinst du?")
        self.assertFalse(ok)

    def test_missing_preparation_question_is_rejected(self):
        ok, _ = native.training_question("Zur Stelle Backend bei der Beispiel AG fehlt noch die Vorbereitung. Soll ich zuerst eine anlegen?")
        self.assertFalse(ok)

    def test_reply_without_reference_to_the_stored_job_is_rejected(self):
        ok, why = native.training_question("Erzähl mir von deinem größten beruflichen Erfolg?")
        self.assertFalse(ok)
        self.assertIn('stored job', why)

    def test_failed_job_show_does_not_count_as_success(self):
        failed = {'commands': [{'command': 'python3 p/skills/_shared/scripts/interview_workspace.py job-show --job j', 'exit': 1},
                               {'command': 'python3 p/skills/_shared/scripts/interview_workspace.py status --candidate c', 'exit': 0}]}
        self.assertEqual(['job-show', 'status'], native.subcommands(failed))
        self.assertEqual(['status'], native.subcommands(failed, ok_only=True))
        unknown = {'commands': [{'command': 'python3 x/interview_workspace.py job-show', 'exit': None}]}
        self.assertEqual([], native.subcommands(unknown, ok_only=True))

    def test_claude_tool_results_set_the_exit_status(self):
        host = native.Host.__new__(native.Host)
        host.name = 'claude'
        out = '\n'.join(json.dumps(e) for e in (
            {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'id': 't1', 'name': 'Bash', 'input': {'command': 'python3 x/interview_workspace.py job-show'}},
                                                         {'type': 'tool_use', 'id': 't2', 'name': 'Bash', 'input': {'command': 'python3 x/interview_workspace.py status'}}]}},
            {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': 't1', 'is_error': True, 'content': 'ERROR'},
                                                    {'type': 'tool_result', 'tool_use_id': 't2', 'is_error': False, 'content': 'ok'}]}}))
        parsed = host.parse(subprocess.CompletedProcess([], 0, out, ''))
        self.assertEqual(['status'], native.subcommands(parsed, ok_only=True))

    def test_phase_order_confirms_the_right_profile_before_training_and_creates_the_namesake_last(self):
        class Stub:
            ws, project, files = Path('/x/ws'), Path('/x/p'), Path('/x/f')
        names = [p[0] for p in native.phases(Stub())]
        self.assertLess(names.index('candidate_confirm_erika'), names.index('job_training'))
        self.assertLess(names.index('job_create'), names.index('job_training'))
        self.assertLess(names.index('job_training'), names.index('same_name_selection'))
        text = {p[0]: p[2] for p in native.phases(Stub())}['candidate_confirm_erika']
        self.assertIn('Erika Beispiel', text)
        self.assertNotIn('Max', text)


def host_result(*calls):
    return {'commands': [{'command': c, 'exit': e} for c, e in calls], 'text': '', 'web': [], 'skills': []}


RT = '/plugin/skills/_shared/scripts/interview_workspace.py'


class QuestionHeuristic(unittest.TestCase):
    """training_question is a bounded deterministic heuristic (no model); see its docstring for limits."""
    CONTEXT = 'Wir üben für die Stelle Senior Backend Engineer bei der Beispiel AG. '

    def accepted(self, sentence):
        return native.training_question(self.CONTEXT + sentence)[0]

    def test_general_interview_question_words_are_not_clarifications(self):
        for sentence in ('Welche technische Entscheidung hast du bei einer Python-API getroffen?',
                         'Nenne zwei Risiken beim Betrieb einer Python-API.',
                         'Wie stellst du sicher, dass eine API fachlich korrekt arbeitet?',
                         '**Erste Frage:** Erzähl mir von einer Python-API, bei der du eine technische Entscheidung getroffen hast.'):
            self.assertTrue(self.accepted(sentence), sentence)

    def test_candidate_selection_profile_confirmation_and_missing_preparation_are_clarifications(self):
        for sentence in ('Welche Erika Beispiel meinst du?', 'Sind die Angaben in deinem Profil korrekt?',
                         'Soll ich zuerst die fehlende Stellenvorbereitung anlegen?',
                         'Welche der beiden Kandidatinnen soll ich verwenden?'):
            self.assertFalse(self.accepted(sentence), sentence)

    def test_reply_that_only_mentions_the_job_and_then_asks_for_selection_or_confirmation_fails(self):
        for tail in ('Welche Erika Beispiel meinst du?', 'Sind die Angaben in deinem Profil korrekt?'):
            ok, why = native.training_question('Die Stelle Backend bei der Beispiel AG ist gespeichert (Python, Kubernetes). ' + tail)
            self.assertFalse(ok)
            self.assertIn('no job-related interview question', why)

    def test_limits_are_documented(self):
        self.assertIn('Limits', native.training_question.__doc__)
        self.assertIn('no proof of interview quality', native.training_question.__doc__)


class StrictRuntimeSuccess(unittest.TestCase):
    P = '/tmp/p'

    def call(self, command, exit_code=0):
        return host_result((command, exit_code))

    def ok(self, result, **expected):
        return bool(native.successful_calls(result, 'job-show', **expected))

    def test_clear_single_call_with_matching_ids_is_accepted(self):
        r = self.call(f'python3 {RT} job-show --project {self.P} --candidate c-erika-beispiel-12345678 --job j-be-12345678')
        self.assertTrue(self.ok(r, project=self.P, candidate='c-erika-beispiel-12345678', job='j-be-12345678'))
        self.assertEqual(['job-show'], native.subcommands(r, ok_only=True))

    def test_nonzero_and_unknown_status_are_rejected(self):
        base = f'python3 {RT} job-show --project {self.P} --candidate c --job j'
        for status in (1, 2, None, '0'):
            self.assertEqual([], native.subcommands(self.call(base, status), ok_only=True), status)
        self.assertEqual([], native.successful_calls(self.call(base, None), 'job-show'))

    def test_failed_runtime_call_followed_by_successful_echo_is_not_runtime_success(self):
        for tail in ('; echo fertig', ' && echo fertig', ' || true', ' | tee /tmp/x', ' 2>&1', '; true'):
            r = self.call(f'python3 {RT} job-show --project {self.P} --candidate c --job j{tail}', 0)
            self.assertIsNone(native.parse_runtime_call(f'python3 {RT} job-show --project {self.P}{tail}'), tail)
            self.assertEqual([], native.subcommands(r, ok_only=True), tail)
            self.assertEqual([], native.successful_calls(r, 'job-show'), tail)

    def test_wrong_project_candidate_or_job_is_rejected(self):
        r = self.call(f'python3 {RT} job-show --project {self.P} --candidate c-a-12345678 --job j-a-12345678')
        self.assertTrue(self.ok(r, project=self.P, candidate='c-a-12345678', job='j-a-12345678'))
        self.assertFalse(self.ok(r, project='/tmp/other', candidate='c-a-12345678', job='j-a-12345678'))
        self.assertFalse(self.ok(r, project=self.P, candidate='c-b-12345678', job='j-a-12345678'))
        self.assertFalse(self.ok(r, project=self.P, candidate='c-a-12345678', job='j-b-12345678'))

    def test_quoted_paths_and_arguments_work_and_shell_wrappers_are_unwrapped(self):
        quoted = f'python3 "{RT}" job-show --project "/tmp/with space/p" --candidate \'c-a-12345678\' --job=j-a-12345678'
        parsed = native.parse_runtime_call(quoted)
        self.assertEqual(('job-show', '/tmp/with space/p', 'c-a-12345678', 'j-a-12345678'),
                         (parsed['subcommand'], parsed['options']['project'], parsed['options']['candidate'], parsed['options']['job']))
        wrapped = f"/bin/zsh -lc 'python3 {RT} job-show --project {self.P} --candidate c --job j'"
        self.assertEqual('job-show', native.parse_runtime_call(wrapped)['subcommand'])
        self.assertIsNone(native.parse_runtime_call(f"/bin/zsh -lc 'python3 {RT} job-show --project {self.P}; echo x'"))

    def test_unresolved_shell_variables_cannot_prove_ids(self):
        r = self.call(f'python3 {RT} job-show --project "$PWD" --candidate c --job j')
        self.assertTrue(native.parse_runtime_call(f'python3 {RT} job-show --project "$PWD"')['unresolved'])
        self.assertEqual([], native.successful_calls(r, 'job-show'))

    def test_other_interpreters_and_scripts_are_not_runtime_calls(self):
        for command in ('cat x/interview_workspace.py', f'bash {RT} job-show', f'python3 other.py job-show', 'FOO=1 python3 ' + RT + ' job-show --project p',
                        f'python3 {RT} --project p job-show'):
            self.assertIsNone(native.parse_runtime_call(command), command)

    def test_job_training_requires_the_right_project_candidate_and_job(self):
        class Stub:
            ws, project, files = Path('/x/ws'), Path('/tmp/p'), Path('/x/f')
            host = type('H', (), {'name': 'claude'})()
        stub = Stub()
        calls = {}

        def rt(*args):
            if args[0] == 'candidate-list':
                return 0, json.dumps([{'candidate_id': 'c-erika-beispiel-12345678', 'display_name': 'Erika Beispiel', 'profile_status': 'confirmed'}]), ''
            return 0, json.dumps([{'job_id': 'j-beispiel-12345678', 'company': 'Beispiel AG'}]), ''
        stub.rt = rt
        stub.candidates = lambda: json.loads(rt('candidate-list')[1])
        check = next(p for p in native.phases(stub) if p[0] == 'job_training')[3]
        question = 'Wir üben für die Stelle Backend bei der Beispiel AG. **Erste Frage:** Erzähl mir von einer Python-API, die du verantwortet hast.'
        good = f'python3 {RT} job-show --project /tmp/p --candidate c-erika-beispiel-12345678 --job j-beispiel-12345678'
        for command, status, accepted in ((good, 0, True), (good, 1, False), (good, None, False), (good + '; echo done', 0, False),
                                          (good.replace('c-erika-beispiel-12345678', 'c-other-12345678'), 0, False),
                                          (good.replace('j-beispiel-12345678', 'j-other-12345678'), 0, False),
                                          (good.replace('/tmp/p', '/tmp/other-project'), 0, False)):
            result = host_result((command, status))
            result['text'] = question
            self.assertEqual(accepted, check(result) == [], (command, status))


class HeadingsAreNotQuestions(unittest.TestCase):
    INTRO = 'Wir bereiten die Python-Stelle bei der Beispiel AG vor.\n'

    def check(self, tail):
        return native.training_question(self.INTRO + tail)

    def test_stand_alone_heading_followed_by_a_selection_question_is_rejected(self):
        ok, why = self.check('**Erste Frage:**\nWelche Erika Beispiel meinst du?')
        self.assertFalse(ok)
        self.assertIn('no job-related interview question', why)

    def test_heading_followed_by_profile_confirmation_or_preparation_clarification_is_rejected(self):
        for tail in ('**Erste Frage:**\nSind die Angaben in deinem Profil korrekt?', 'Frage 1 von 4:\nSoll ich zuerst die Stellenvorbereitung anlegen?',
                     '1.\nWelche der beiden Kandidatinnen soll ich verwenden?'):
            self.assertFalse(self.check(tail)[0], tail)

    def test_heading_alone_is_rejected_even_with_job_context_in_the_intro(self):
        for tail in ('**Erste Frage:**', '**Frage 2 von 4:**', '## Erste Frage', '1.', ''):
            self.assertFalse(self.check(tail)[0], tail)

    def test_heading_plus_a_real_job_question_is_accepted(self):
        for tail in ('**Erste Frage:**\nWelche technische Entscheidung hast du bei einer Python-API getroffen?',
                     'Frage 2 von 4:\nNenne zwei Risiken beim Betrieb einer Python-API.',
                     '**Erste Frage:**\nBerichte von einer API, die du verantwortet hast.'):     # task without a typical verb, forced by the heading
            self.assertEqual((True, ''), self.check(tail), tail)

    def test_real_question_on_the_same_line_as_the_heading_is_accepted(self):
        self.assertTrue(self.check('**Erste Frage:** Welche technische Entscheidung hast du bei einer Python-API getroffen?')[0])
        self.assertTrue(self.check('Frage 1: Erzähl mir von einer Python-API.')[0])
        self.assertFalse(self.check('**Erste Frage:** Welche Erika Beispiel meinst du?')[0])

    def test_general_question_words_stay_allowed(self):
        for sentence in ('Welche Risiken siehst du beim Betrieb einer Python-API?', 'Nenne zwei Wege, eine API korrekt zu testen.'):
            self.assertTrue(self.check(sentence)[0], sentence)

    def test_a_heading_does_not_turn_arbitrary_following_text_into_a_question(self):
        counter = 'Wir trainieren für die Python-Stelle.\n**Erste Frage:**\nEinen Moment bitte.'
        ok, why = native.training_question(counter)
        self.assertFalse(ok)
        self.assertIn('no job-related interview question', why)
        for text in ('Wir trainieren für die Python-Stelle. **Erste Frage:** Einen Moment bitte.',        # same-line variant
                     'Wir trainieren für die Python-Stelle.\n**Erste Frage:**',                           # heading without content
                     'Wir trainieren für die Python-Stelle.\n**Frage 2 von 4:**\nGleich geht es los.',
                     'Wir trainieren für die Python-Stelle.\n1.\nEinen Moment bitte.',
                     'Wir trainieren für die Python-Stelle.\n**Erste Frage:** Einen Moment bitte.',
                     'Wir trainieren für die Python-Stelle.\n**Erste Frage:**\n**Zweite Frage:**'):
            self.assertFalse(native.training_question(text)[0], text)

    def test_clarifications_after_headings_stay_rejected_and_real_questions_stay_accepted(self):
        job = 'Wir trainieren für die Python-Stelle bei der Beispiel AG.\n'
        for rejected in ('**Erste Frage:**\nWelche Erika Beispiel meinst du?', '**Erste Frage:** Sind die Angaben in deinem Profil korrekt?',
                         'Frage 1:\nSoll ich zuerst die Stellenvorbereitung anlegen?'):
            self.assertFalse(native.training_question(job + rejected)[0], rejected)
        for accepted in ('**Erste Frage:**\nWelche technische Entscheidung hast du bei einer Python-API getroffen?',
                         '**Erste Frage:** Beschreibe eine Python-API, die du verantwortet hast.',
                         'Frage 2 von 4:\nNenne zwei Risiken beim Betrieb einer Python-API.',
                         '**Erste Frage:**\nBerichte von einer API, die du verantwortet hast.'):
            self.assertEqual((True, ''), native.training_question(job + accepted), accepted)

    def test_documented_limits_mention_headings(self):
        self.assertIn('heading', native.training_question.__doc__)
        self.assertIn('Limits', native.training_question.__doc__)


def claude_events(uses, results):
    """Fictional Claude stream: `uses` = [(id, command)], `results` = [(tool_use_id, is_error)] in the given order."""
    events = [{'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'id': i, 'name': 'Bash', 'input': {'command': c}} for i, c in uses]}}]
    for tool_id, is_error in results:
        events.append({'type': 'user', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': tool_id, 'is_error': is_error, 'content': 'x'}]}})
    return '\n'.join(json.dumps(e) for e in events)


def parse_claude(uses, results):
    host = native.Host.__new__(native.Host)
    host.name = 'claude'
    return host.parse(subprocess.CompletedProcess([], 0, claude_events(uses, results), ''))


class ConflictingToolResults(unittest.TestCase):
    CMD = f'python3 {RT} job-show --project /tmp/p --candidate c-a-12345678 --job j-a-12345678'

    def success(self, parsed):
        return native.successful_calls(parsed, 'job-show', project='/tmp/p', candidate='c-a-12345678', job='j-a-12345678')

    def test_error_then_success_for_the_same_id_is_no_evidence(self):
        parsed = parse_claude([('t1', self.CMD)], [('t1', True), ('t1', False)])
        self.assertIsNone(parsed['commands'][0]['exit'])
        self.assertTrue(parsed['commands'][0]['conflict'])
        self.assertEqual([], self.success(parsed))
        self.assertEqual([], native.subcommands(parsed, ok_only=True))

    def test_success_then_error_is_no_evidence_either(self):
        parsed = parse_claude([('t1', self.CMD)], [('t1', False), ('t1', True)])
        self.assertTrue(parsed['commands'][0]['conflict'])
        self.assertEqual([], self.success(parsed))

    def test_a_further_success_after_a_contradiction_does_not_repair_it(self):
        parsed = parse_claude([('t1', self.CMD)], [('t1', True), ('t1', False), ('t1', False), ('t1', False)])
        self.assertTrue(parsed['commands'][0]['conflict'])
        self.assertEqual([], self.success(parsed))

    def test_a_single_unambiguous_success_stays_valid_and_labels_its_source(self):
        parsed = parse_claude([('t1', self.CMD)], [('t1', False)])
        self.assertEqual(0, parsed['commands'][0]['exit'])
        self.assertEqual('derived-from-is_error', parsed['commands'][0]['exit_source'])   # not a host-reported numeric exit code
        self.assertEqual(1, len(self.success(parsed)))

    def test_identical_repeated_results_are_consistent_by_documented_rule(self):
        ok = parse_claude([('t1', self.CMD)], [('t1', False), ('t1', False)])
        self.assertEqual(0, ok['commands'][0]['exit'])
        self.assertFalse(ok['commands'][0]['conflict'])
        failed = parse_claude([('t1', self.CMD)], [('t1', True), ('t1', True)])
        self.assertEqual(1, failed['commands'][0]['exit'])
        self.assertEqual([], self.success(failed))
        self.assertIn('Identical repeated results are consistent', ' '.join(native.Host.parse.__doc__.split()))

    def test_missing_or_unknown_ids_confirm_no_other_call(self):
        parsed = parse_claude([('t1', self.CMD), ('t2', self.CMD)], [(None, False), ('zzz', False), ('', False)])
        self.assertEqual([None, None], [c['exit'] for c in parsed['commands']])
        self.assertEqual([], self.success(parsed))
        no_ids = parse_claude([(None, self.CMD)], [(None, False)])      # a call without id cannot be matched by an id-less result
        self.assertIsNone(no_ids['commands'][0]['exit'])
        unanswered = parse_claude([('t1', self.CMD)], [])
        self.assertIsNone(unanswered['commands'][0]['exit'])

    def test_two_different_ids_are_judged_independently(self):
        other = self.CMD.replace('j-a-12345678', 'j-b-12345678')
        parsed = parse_claude([('t1', self.CMD), ('t2', other)], [('t1', False), ('t2', True)])
        self.assertEqual([0, 1], [c['exit'] for c in parsed['commands']])
        self.assertEqual(1, len(self.success(parsed)))
        self.assertEqual([], native.successful_calls(parsed, 'job-show', project='/tmp/p', candidate='c-a-12345678', job='j-b-12345678'))

    def test_the_same_tool_id_on_two_calls_is_ambiguous(self):
        parsed = parse_claude([('t1', self.CMD), ('t1', self.CMD)], [('t1', False)])
        self.assertTrue(all(c['ambiguous'] for c in parsed['commands']))
        self.assertEqual([None, None], [c['exit'] for c in parsed['commands']])
        self.assertEqual([], self.success(parsed))

    def test_codex_exit_codes_are_host_reported_and_conflicts_are_detected(self):
        host = native.Host.__new__(native.Host)
        host.name = 'codex'
        event = lambda i, code: {'type': 'item.completed', 'item': {'id': i, 'type': 'command_execution', 'command': self.CMD, 'exit_code': code}}  # noqa: E731
        ok = host.parse(subprocess.CompletedProcess([], 0, json.dumps(event('i1', 0)), ''))
        self.assertEqual((0, 'host-exit_code'), (ok['commands'][0]['exit'], ok['commands'][0]['exit_source']))
        self.assertEqual(1, len(self.success(ok)))
        clash = host.parse(subprocess.CompletedProcess([], 0, '\n'.join(json.dumps(event('i1', c)) for c in (1, 0)), ''))
        self.assertTrue(clash['commands'][0]['conflict'])
        self.assertEqual([], self.success(clash))
        self.assertEqual([None], [c['exit'] for c in host.parse(subprocess.CompletedProcess([], 0, json.dumps(event('i2', None)), ''))['commands']])

    def test_existing_single_command_and_id_checks_are_preserved(self):
        parsed = parse_claude([('t1', self.CMD)], [('t1', False)])
        self.assertEqual([], native.successful_calls(parsed, 'job-show', project='/tmp/p', candidate='c-other-12345678', job='j-a-12345678'))
        chained = parse_claude([('t1', self.CMD + '; echo done')], [('t1', False)])
        self.assertEqual([], self.success(chained))


if __name__ == '__main__':
    unittest.main()
