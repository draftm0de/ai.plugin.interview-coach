"""Logic of tests/native/run_host_dialogue.py with a mocked host (the runner itself needs signed-in Claude Code / Codex)."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'Makefile').is_file())
import sys
sys.path.insert(0, str(ROOT / 'tests/native'))
SPEC = importlib.util.spec_from_file_location('run_host_dialogue', ROOT / 'tests/native/run_host_dialogue.py')
hd = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hd)


def done(stdout=''):
    return subprocess.CompletedProcess([], 0, stdout, '')


class Commands(unittest.TestCase):
    def host(self, name):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__('shutil').rmtree(tmp, ignore_errors=True))
        (tmp / 'payload/skills').mkdir(parents=True)
        (tmp / 'project').mkdir()
        return hd.SessionHost(name, tmp / 'project', tmp / 'payload', tmp / 'cfg', 5)

    def test_claude_uses_session_id_then_resume_and_never_no_persistence(self):
        host = self.host('claude')
        session = {'id': 'abc', 'started': False}
        with mock.patch.object(subprocess, 'run', return_value=done()) as run:
            host.invoke('Hallo', session, 'candidate-training')
            host.invoke('Weiter', session)
        first, second = (c.args[0] for c in run.call_args_list)
        self.assertEqual(('--session-id', 'abc'), (first[first.index('--session-id')], first[first.index('--session-id') + 1]))
        self.assertIn('/interview-coach:candidate-training Hallo', first)
        self.assertIn('--resume', second)
        self.assertNotIn('--session-id', second)
        self.assertNotIn('Weiter', ' '.join(a for a in second if a.startswith('/')))
        self.assertTrue(all('--no-session-persistence' not in c for c in (first, second)))

    def test_codex_takes_the_thread_id_from_the_first_turn_and_resumes_it(self):
        host = self.host('codex')
        session = {'id': None, 'started': False}
        events = json.dumps({'type': 'thread.started', 'thread_id': 'thread-1'})
        with mock.patch.object(subprocess, 'run', return_value=done(events)) as run:
            host.invoke('Hallo', session, 'candidate-training')
            host.invoke('Weiter', session)
        first, second = (c.args[0] for c in run.call_args_list)
        self.assertNotIn('--ephemeral', first)
        self.assertEqual(['codex', 'exec', 'resume'], second[:3])
        self.assertIn('thread-1', second)
        self.assertEqual('Weiter', second[-1])

    def test_checks_distinguish_leaks_scores_and_verbatim_answers(self):
        self.assertTrue(hd.LEAK.search('Reduzieren Sie den Umfang'))
        self.assertTrue(hd.SCORE.search('Gesamtbewertung: 7/10'))
        self.assertFalse(hd.SCORE.search('Wie wirkt sich der Termin aus?'))
        self.assertTrue(hd.same('a  b\n c', 'a b c'))
        self.assertFalse(hd.same('a b', 'a b c'))
        self.assertFalse(hd.same(None, 'x'))

    def test_a_timeout_is_aborted_never_pass(self):
        sc = hd.Scenario.__new__(hd.Scenario)
        sc.status, sc.note, sc.turns, sc.checks = 'PASS', '', [], []
        sc.run = mock.Mock()
        sc.run.host.invoke.side_effect = subprocess.TimeoutExpired('x', 1)
        with self.assertRaises(subprocess.TimeoutExpired):
            sc.turn('1', 'text', {'id': 'x', 'started': False})
        self.assertEqual('ABORTED', sc.status)


if __name__ == '__main__':
    unittest.main()


class NoStorageChecks(unittest.TestCase):
    def tree(self, files):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__('shutil').rmtree(tmp, ignore_errors=True))
        for name, text in files.items():
            (tmp / name).parent.mkdir(parents=True, exist_ok=True)
            (tmp / name).write_text(text)
        return tmp

    def test_new_changed_and_deleted_files_are_found_by_content(self):
        root = self.tree({'.agents/skills/a/SKILL.md': 'alt', 'files/cv.md': 'cv'})
        before = hd.snapshot(root)
        self.assertEqual([], hd.unexpected_changes(hd.diff_snapshots(before, hd.snapshot(root))))
        (root / '.agents/skills/a/SKILL.md').write_text('geändert')  # same size class, same name: only the hash shows it
        (root / 'storage').mkdir()
        (root / 'storage/state.md').write_text('x')
        (root / 'files/cv.md').unlink()
        diff = hd.diff_snapshots(before, hd.snapshot(root))
        self.assertEqual(['storage', 'storage/state.md'], diff['created'])
        self.assertEqual(['.agents/skills/a/SKILL.md'], diff['modified'])
        self.assertEqual(['files/cv.md'], diff['deleted'])
        self.assertEqual(4, len(hd.unexpected_changes(diff)))

    def test_pointer_in_the_config_directory_is_detected_and_no_directory_prefix_is_exempt(self):
        config = self.tree({})
        before = hd.snapshot(config)
        (config / 'zyris/interview-coach/projects').mkdir(parents=True)
        (config / 'zyris/interview-coach/projects/abc.json').write_text('{}')
        self.assertTrue(hd.unexpected_changes(hd.diff_snapshots(before, hd.snapshot(config))))
        project = self.tree({'a.txt': '1'})
        before = hd.snapshot(project)
        (project / '.cfg').mkdir()
        (project / '.cfg/pointer.json').write_text('{}')
        for bad in ({'.cfg/': 'x'}, {'.cfg/*': 'x'}, {'.cfg/pointer.json': ''}):
            with self.assertRaises(ValueError):
                hd.diff_snapshots(before, hd.snapshot(project), bad)
        # an exact, justified exception removes only that file
        diff = hd.diff_snapshots(before, hd.snapshot(project), {'.cfg/pointer.json': 'host writes it itself (example)'})
        self.assertEqual(['.cfg'], diff['created'])
        self.assertEqual({}, hd.NOSTORAGE_ALLOWED)  # the real runner has no exception

    def test_false_success_message_is_recognised_in_a_stop_reply(self):
        self.assertTrue(hd.scenarios.claims_saved('Training beendet. Ihr Lauf wurde gespeichert.'))
        self.assertTrue(hd.scenarios.claims_saved('Zusammenfassung:\n\n✅ Gespeichert unter storage/runs/q.md'))
        self.assertFalse(hd.scenarios.claims_saved('Training beendet. Weil Sie Nicht speichern gewählt haben, wurde nichts gespeichert.'))


class StopReplyChecks(unittest.TestCase):
    class Sc:
        def __init__(self):
            self.checks = []

        def check(self, name, ok, detail=None):
            self.checks.append((name, bool(ok)))

    def test_resume_promise_in_a_stop_reply_fails_the_host_check_and_an_honest_reply_passes(self):
        bad, good = self.Sc(), self.Sc()
        hd.stop_checks(bad, '4', 'Beendet und gespeichert. Beim Fortsetzen stelle ich die offene Nachfrage einmal erneut.')
        hd.stop_checks(good, '4', 'Beendet und gespeichert. Die offene Nachfrage bleibt unbeantwortet; für späteres Weitermachen gibt es pause.')
        self.assertEqual([False, True], [ok for _, ok in bad.checks])      # promise check fails, rating check is a separate check
        self.assertEqual([True, True], [ok for _, ok in good.checks])

    def test_every_stop_turn_of_the_runner_is_followed_by_the_check(self):
        source = (ROOT / 'tests/native/run_host_dialogue.py').read_text()
        self.assertEqual(source.count(', "stop", s'), source.count('    stop_checks(sc, "'))


class EvidenceFidelity(unittest.TestCase):
    def case(self, name):
        return json.loads((ROOT / 'tests/fixtures/behavior/judge_cases' / f'{name}.json').read_text(encoding='utf-8'))

    def test_final10_host_rating_calls_the_stated_team_involvement_missing(self):
        answers = hd.A_ADR + ' ' + hd.A_ADR2
        wrong = hd.false_missing_claims(answers, self.case('final10_host_claude_false_missing')['reply'])
        self.assertEqual(["team involvement (answer: 'mit beiden Teams durchgehen')"], wrong)
        # faithful rating: more depth only as a recommendation
        self.assertEqual([], hd.false_missing_claims(answers, self.case('control_faithful_rating')['reply']))
        # a fact the candidate did NOT state may be called missing
        self.assertEqual([], hd.false_missing_claims('Ich entscheide.', 'Sie sagen nicht, wie Sie die Teams einbinden.'))

    def test_rating_check_is_wired_into_every_stop_and_rating_turn(self):
        sc = StopReplyChecks.Sc()
        hd.rating_checks(sc, '3', 'Sie sagen nicht, wie Sie die Teams einbinden.')
        self.assertEqual([False], [ok for _, ok in sc.checks])
        sc = StopReplyChecks.Sc()
        hd.stop_checks(sc, '4', 'Beendet. Sie sagen nicht, wie Sie die Teams einbinden.')
        self.assertIn(False, [ok for _, ok in sc.checks])
        source = (ROOT / 'tests/native/run_host_dialogue.py').read_text()
        self.assertEqual(2, source.count('    rating_checks(sc, "3", rating["text"])'))


class OneFollowupCheck(unittest.TestCase):
    def test_final12_two_followups_fail_the_host_check_and_a_single_choice_passes(self):
        def run(reply):
            sc = StopReplyChecks.Sc()
            hd.one_followup(sc, '2', reply)
            return dict(sc.checks)
        cases = {c['id']: c for c in (json.loads(p.read_text(encoding='utf-8')) for p in (ROOT / 'tests/fixtures/behavior/judge_cases').glob('*.json'))}
        bad = run(cases['final12_host_claude_two_followups']['reply'])
        self.assertFalse(bad['2: exactly one question mark'])
        good = run('Geht es Ihnen beim festen Termin eher darum, den Umfang zu begrenzen oder die Entscheidung zu beschleunigen?')
        self.assertTrue(good['2: exactly one question mark'])
