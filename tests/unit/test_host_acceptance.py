"""Deterministic tests of the host acceptance wrapper. The host is a local fake script; no model and no real host are started."""
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import time
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'Makefile').is_file())
spec = importlib.util.spec_from_file_location('run_host_acceptance', ROOT / 'tests/native/run_host_acceptance.py')
acc = importlib.util.module_from_spec(spec)
sys.dont_write_bytecode = True
spec.loader.exec_module(acc)


def fake_host(directory, body):
    path = Path(directory) / 'fake_claude.py'
    path.write_text('#!/usr/bin/env python3\n' + body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return str(path)


def stream(*events):
    return '\n'.join(json.dumps(e) for e in events)


def tool_use(i, command):
    return {'type': 'assistant', 'session_id': 's1', 'message': {'content': [{'type': 'tool_use', 'id': i, 'name': 'Bash', 'input': {'command': command}}]}}


def tool_result(i, content, error=False):
    return {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': i, 'content': content, 'is_error': error}]}}


RT = '/p/skills/_shared/scripts/interview_workspace.py'


class SessionMapping(unittest.TestCase):
    def test_f_and_g_share_one_session_and_h_gets_another(self):
        f_id, h_id = acc.new_session_ids()
        self.assertNotEqual(f_id, h_id)
        f = acc.build_command('claude', 'F', '/pl', ('new', f_id))
        g = acc.build_command('claude', 'G', '/pl', ('resume', f_id))
        h = acc.build_command('claude', 'H', '/pl', ('new', h_id))
        self.assertEqual(f_id, f[f.index('--session-id') + 1])
        self.assertEqual(f_id, g[g.index('--resume') + 1])
        self.assertNotIn('--session-id', g)
        self.assertEqual(h_id, h[h.index('--session-id') + 1])
        for cmd in (f, g, h):
            self.assertNotIn('--no-session-persistence', cmd)
            self.assertNotIn('--continue', cmd)
            self.assertIn('--plugin-dir', cmd)
        self.assertNotIn(f_id, h)

    def test_session_ids_are_taken_from_host_events(self):
        info = acc.parse_events(stream({'type': 'system', 'subtype': 'init', 'session_id': 'abc', 'skills': ['interview-coach:job-training']},
                                       {'type': 'result', 'session_id': 'abc', 'result': 'x', 'is_error': False}))
        self.assertEqual(['abc'], info['session_ids'])
        self.assertEqual(['interview-coach:job-training'], info['skills'])


class Budget(unittest.TestCase):
    def test_timeout_is_limit_or_remaining_minus_reserve_and_never_raised(self):
        d = acc.Deadline(1000)
        self.assertEqual(120, d.phase_timeout(120, 1000))
        self.assertEqual(40, d.phase_timeout(120, 1500))     # 1600 - 60 - 1500
        self.assertIsNone(d.phase_timeout(60, 1530))          # < minimum
        self.assertLessEqual(d.phase_timeout(60, 1400), 60)

    def test_end_to_end_window_is_600_seconds_with_60_reserve(self):
        d = acc.Deadline(0)
        self.assertEqual(600, d.end)
        self.assertIsNone(d.phase_timeout(120, 530))   # 600-60-530 = 10 < minimum


class Processes(unittest.TestCase):
    def test_timeout_ends_group_and_logs_immediately(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = fake_host(tmp, 'import subprocess, sys, time\nsubprocess.Popen(["sleep","60"])\nprint("{\\"type\\":\\"system\\"}", flush=True)\ntime.sleep(60)\n')
            seen = {}

            def on_start(proc):
                seen['start_record'] = (Path(tmp) / 'out/E.start.json').is_file()
                seen['pid'] = proc.pid
            t0 = time.time()
            meta = acc.run_process([sys.executable, host], tmp, dict(os.environ), 1, Path(tmp) / 'out', 'E', on_start=on_start)
            self.assertLess(time.time() - t0, 15)
            self.assertTrue(seen['start_record'], 'start record must exist while the process runs')
            self.assertTrue(meta['timed_out'])
            self.assertIn('TERM', meta['ended_by'])
            with self.assertRaises(ProcessLookupError):
                os.killpg(seen['pid'], 0)     # no member of the group survives (the child sleep as well)
            self.assertTrue((Path(tmp) / 'out/E.process.json').is_file())
            self.assertIn('system', (Path(tmp) / 'out/E.stdout.jsonl').read_text())

    def test_sigterm_ignoring_host_is_killed_after_grace(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = fake_host(tmp, 'import signal, time\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\ntime.sleep(60)\n')
            meta = acc.run_process([sys.executable, host], tmp, dict(os.environ), 1, Path(tmp) / 'o', 'F')
            self.assertTrue(meta['timed_out'])
            self.assertIn('KILL', meta['ended_by'])

    def test_clean_exit_is_recorded_without_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = fake_host(tmp, 'print("hi")\n')
            meta = acc.run_process([sys.executable, host], tmp, dict(os.environ), 20, Path(tmp) / 'o', 'H')
            self.assertFalse(meta['timed_out'])
            self.assertEqual(0, meta['exit_code'])


class ToolResults(unittest.TestCase):
    def info(self, *events):
        return acc.parse_events(stream(*events))

    def test_successful_and_failed_runtime_calls_are_distinguished(self):
        cmd = f'python3 {RT} finish --project /p --candidate c-1 --run-id r --job-id j-1 --status stopped_early --answered-count 1'
        ok = self.info(tool_use('a', cmd), tool_result('a', '{"ok": true}'))
        bad = self.info(tool_use('a', cmd), tool_result('a', 'ERROR: stale hash', error=True))
        missing = self.info(tool_use('a', cmd))
        self.assertEqual(1, len(acc.ok_runtime(ok, 'finish', candidate='c-1', **{'job-id': 'j-1'})))
        self.assertEqual([], acc.ok_runtime(bad, 'finish'))
        self.assertEqual([], acc.ok_runtime(missing, 'finish'))
        self.assertEqual(1, len(acc.runtime_calls(bad, 'finish')))   # visible as attempted, not as success

    def test_compound_or_variable_commands_do_not_vouch_for_a_runtime_call(self):
        compound = f'cd /p && python3 {RT} finish --project /p --candidate c-1'
        variable = f'python3 {RT} finish --project $P --candidate c-1'
        for command in (compound, variable):
            info = self.info(tool_use('a', command), tool_result('a', 'fine'))
            self.assertEqual([], acc.ok_runtime(info, 'finish'), command)

    def test_wrong_ids_are_not_accepted(self):
        cmd = f'python3 {RT} finish --project /p --candidate c-OTHER --job-id j-1 --status stopped_early'
        info = self.info(tool_use('a', cmd), tool_result('a', 'ok'))
        self.assertEqual([], acc.ok_runtime(info, 'finish', candidate='c-1'))

    def test_claimed_save_in_text_alone_is_no_runtime_call(self):
        info = self.info({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': 'Gespeichert als run-1.'}]}})
        self.assertEqual([], acc.runtime_calls(info))

    def test_conflicting_or_duplicate_results_are_not_success(self):
        cmd = f'python3 {RT} job-show --project /p --candidate c --job j'
        info = self.info(tool_use('a', cmd), tool_result('a', 'x'), tool_result('a', 'y', error=True))
        self.assertEqual([], acc.ok_runtime(info, 'job-show'))


PROJECT, CAND, JOB = '/p/project', 'c-1', 'j-1'


def runtime_cmd(sub, **opts):
    return f'python3 {RT} {sub} ' + ' '.join(f'--{k} {v}' for k, v in opts.items())


class Identities(unittest.TestCase):
    """A successful tool result is not enough: project, candidate and job must match together."""

    def ok(self, cmd):
        return acc.parse_events(stream(tool_use('a', cmd), tool_result('a', '{"ok": true}')))

    def test_job_show_needs_project_candidate_and_job_together(self):
        good = self.ok(runtime_cmd('job-show', project=PROJECT, candidate=CAND, job=JOB))
        self.assertEqual(1, len(acc.ok_identity(good, 'job-show', PROJECT, candidate=CAND, job=JOB)))
        for opts in (dict(project='/other', candidate=CAND, job=JOB), dict(project=PROJECT, candidate='c-X', job=JOB),
                     dict(project=PROJECT, candidate=CAND, job='j-X'), dict(candidate=CAND, job=JOB), dict(project=PROJECT, job=JOB),
                     dict(project=PROJECT, candidate=CAND)):
            info = self.ok(runtime_cmd('job-show', **opts))
            self.assertEqual([], acc.ok_identity(info, 'job-show', PROJECT, candidate=CAND, job=JOB), opts)
            self.assertEqual(1 if 'job' in opts else 1, len(acc.ok_runtime(info, 'job-show')), 'the old check would have accepted it')

    def test_finish_needs_expected_project_too(self):
        base = dict(candidate=CAND, **{'job-id': JOB}, status='stopped_early')
        good = self.ok(runtime_cmd('finish', project=PROJECT, **base))
        wrong = self.ok(runtime_cmd('finish', project='/p/other', **base))
        none = self.ok(runtime_cmd('finish', **base))
        self.assertEqual(1, len(acc.ok_identity(good, 'finish', PROJECT, candidate=CAND, job=JOB, job_keys=('job-id',))))
        for info in (wrong, none):
            self.assertEqual([], acc.ok_identity(info, 'finish', PROJECT, candidate=CAND, job=JOB, job_keys=('job-id',)))

    def test_tool_error_with_right_identity_is_still_no_success(self):
        info = acc.parse_events(stream(tool_use('a', runtime_cmd('job-show', project=PROJECT, candidate=CAND, job=JOB)), tool_result('a', 'ERROR', error=True)))
        self.assertEqual([], acc.ok_identity(info, 'job-show', PROJECT, candidate=CAND, job=JOB))

    def test_status_is_bound_to_project_and_candidate(self):
        self.assertEqual([], acc.ok_identity(self.ok(runtime_cmd('status', project=PROJECT, candidate='c-X')), 'status', PROJECT, candidate=CAND))
        self.assertEqual([], acc.ok_identity(self.ok(runtime_cmd('status', candidate=CAND)), 'status', PROJECT, candidate=CAND))

    def test_sessions_missing_wrong_or_conflicting_ids(self):
        self.assertTrue(acc.session_identity_ok('s-F', ['s-F']))
        for seen in ([], ['s-OTHER'], ['s-F', 's-OTHER']):
            self.assertFalse(acc.session_identity_ok('s-F', seen), seen)
        self.assertFalse(acc.session_identity_ok('', ['']))

    def test_h_session_must_appear_and_differ_from_f_and_g(self):
        self.assertTrue(acc.check_h_session('s-H', 's-F', ['s-H']))
        self.assertFalse(acc.check_h_session('s-H', 's-F', []), 'requested id absent from events')
        self.assertFalse(acc.check_h_session('s-H', 's-F', ['s-F']), 'reused the F/G session')
        self.assertFalse(acc.check_h_session('s-F', 's-F', ['s-F']), 'H id equals F id')
        self.assertFalse(acc.check_h_session('s-H', 's-F', ['s-H', 's-F']), 'conflicting ids')


QUESTION = ('Du hast von 2019 bis 2024 als Backend-Entwicklerin gearbeitet. Beschreibe bitte eine Python-API, die du entworfen hast. '
            'Welche Entscheidungen hast du dabei selbst getroffen, und was würdest du heute anders machen?')
ANSWER = ('Bei der Muster GmbH habe ich die Schnittstelle für Zahlungsbenachrichtigungen entworfen, über die Händlersysteme Statusänderungen abrufen. '
          'Ich habe selbst entschieden, Wiederholungen idempotent zu machen und Anfragen über Schlüssel zu deduplizieren. '
          'Heute würde ich früher Lasttests mit echten Datenmengen fahren, weil die erste Version Spitzen schlecht abfing.')


def sha256(text):
    return __import__('hashlib').sha256(text.encode()).hexdigest()


def fit_review(**over):
    review = {'question_sha256': sha256(QUESTION), 'answer_sha256': sha256(ANSWER), 'fictional': True, 'verdict': 'PASS',
              'question_assessment': {'concrete': True, 'job_related': True},
              'parts': [{'kind': 'context', 'question_quote': 'Du hast von 2019 bis 2024 als Backend-Entwicklerin gearbeitet.'},
                        {'kind': 'example', 'question_quote': 'Beschreibe bitte eine Python-API, die du entworfen hast.', 'covered': True,
                         'answer_quote': 'habe ich die Schnittstelle für Zahlungsbenachrichtigungen entworfen, über die Händlersysteme Statusänderungen abrufen'},
                        {'kind': 'own_decisions', 'question_quote': 'Welche Entscheidungen hast du dabei selbst getroffen', 'covered': True,
                         'answer_quote': 'Ich habe selbst entschieden, Wiederholungen idempotent zu machen und Anfragen über Schlüssel zu deduplizieren'},
                        {'kind': 'retrospective', 'question_quote': 'was würdest du heute anders machen?', 'covered': True,
                         'answer_quote': 'Heute würde ich früher Lasttests mit echten Datenmengen fahren, weil die erste Version Spitzen schlecht abfing'}]}
    review.update(over)
    return review


class QuestionExtraction(unittest.TestCase):
    def test_block_keeps_all_subquestions_of_the_last_question_group(self):
        reply = '**Offene Punkte**\n- Kubernetes ist unbelegt.\n\n**Erste Frage**\n\n' + QUESTION
        got = acc.extract_question(reply)
        self.assertEqual(QUESTION, got['block'])
        self.assertFalse(got['ambiguous'])

    def test_attached_bullets_belong_to_the_question(self):
        got = acc.extract_question('Intro.\n\nWie hast du das gelöst?\n\n- Was war dein Anteil?\n- Was lief schief?')
        self.assertIn('Was lief schief?', got['block'])

    def test_two_separate_question_groups_are_ambiguous_and_no_question_is_none(self):
        self.assertTrue(acc.extract_question('Frage A?\n\nText ohne Zeichen.\n\nFrage B?')['ambiguous'])
        self.assertIsNone(acc.extract_question('Keine Frage hier.')['block'])


class AnswerFit(unittest.TestCase):
    """Fit is a reviewed judgement tied to question parts; shared words or topic words never prove it."""

    def test_reviewed_answer_covering_all_parts_passes(self):
        self.assertEqual(('PASS', []), acc.validate_answer_fit(QUESTION, ANSWER, fit_review()))

    def test_answer_that_shares_the_topic_word_but_skips_the_retrospective_is_blocked(self):
        answer = ANSWER.split(' Heute')[0]
        review = fit_review(answer_sha256=sha256(answer))
        review['parts'] = [p for p in review['parts'] if p['kind'] != 'retrospective']
        verdict, reasons = acc.validate_answer_fit(QUESTION, answer, review)
        self.assertEqual('BLOCKED', verdict)
        self.assertTrue(any('retrospective' in r for r in reasons), reasons)

    def test_claiming_a_part_covered_without_a_literal_answer_passage_is_blocked(self):
        review = fit_review()
        review['parts'][3]['answer_quote'] = 'Ich würde im Betrieb von Kubernetes Störungen anders behandeln und Tests ausbauen'
        self.assertEqual('BLOCKED', acc.validate_answer_fit(QUESTION, ANSWER, review)[0])

    def test_echoing_the_question_is_not_fit(self):
        review = fit_review()
        review['parts'][1]['answer_quote'] = 'Beschreibe bitte eine Python-API, die du entworfen hast'
        verdict, reasons = acc.validate_answer_fit(QUESTION, QUESTION + ' ' + ANSWER, dict(review, answer_sha256=sha256(QUESTION + ' ' + ANSWER)))
        self.assertEqual('BLOCKED', verdict)
        self.assertTrue(any('repeats the question' in r for r in reasons), reasons)

    def test_review_for_another_question_or_answer_unclear_or_unfictional_is_blocked(self):
        for over in (dict(question_sha256=sha256('andere Frage?')), dict(answer_sha256=sha256('x')), dict(verdict='UNCLEAR'),
                     dict(fictional=False), dict(question_assessment={'concrete': False, 'job_related': True})):
            self.assertEqual('BLOCKED', acc.validate_answer_fit(QUESTION, ANSWER, fit_review(**over))[0], over)

    def test_no_review_no_block_or_empty_answer_is_blocked_without_a_substitute(self):
        self.assertEqual('BLOCKED', acc.validate_answer_fit(None, ANSWER, fit_review())[0])
        self.assertEqual('BLOCKED', acc.validate_answer_fit(QUESTION, '', fit_review())[0])
        self.assertEqual('BLOCKED', acc.validate_answer_fit(QUESTION, ANSWER, {})[0])
        self.assertFalse(hasattr(acc, 'choose_answer'), 'no automatic answer selection may exist')


class DomainReview(unittest.TestCase):
    MATERIAL = {'match': 'Python: Skill belegt, Dauer nicht belegt, zu klären. Kubernetes: im Profil nicht belegt.', 'reply': 'Kubernetes ist unbelegt.'}
    REQUIRED = ('a', 'b')

    def review(self, **over):
        r = {'verdict': 'PASS', 'criteria': [
            {'id': 'a', 'verdict': 'PASS', 'finding': 'ok', 'quotes': [{'artifact': 'match', 'text': 'Dauer nicht belegt, zu klären'}]},
            {'id': 'b', 'verdict': 'PASS', 'finding': 'ok', 'quotes': [{'artifact': 'reply', 'text': 'Kubernetes ist unbelegt'}]}]}
        r.update(over)
        return r

    def test_valid_review_gives_its_verdict(self):
        self.assertEqual('PASS', acc.validate_review(self.review(), self.MATERIAL, self.REQUIRED)[0])
        failing = self.review(verdict='FAIL')
        failing['criteria'][1]['verdict'] = 'FAIL'
        self.assertEqual('FAIL', acc.validate_review(failing, self.MATERIAL, self.REQUIRED)[0])

    def test_unusable_reviews_are_refused(self):
        bad = self.review()
        bad['criteria'][0]['quotes'][0]['text'] = 'Python ist direkt belegt und genügend'
        missing = self.review()
        missing['criteria'].pop()
        noquote = self.review()
        noquote['criteria'][0]['quotes'] = []
        for review in (bad, missing, noquote, self.review(verdict='FAIL'), 'x'):
            with self.assertRaises(acc.ReviewError):
                acc.validate_review(review, self.MATERIAL, self.REQUIRED)


class LearningState(unittest.TestCase):
    def test_only_status_assignments_count_as_promotion(self):
        base = '- C08 Genuine behavioral evidence: open — Baseline (Lauf 1)'
        note = '- Weitere Antworten in anderen Szenarien nötig, bevor eine Kompetenz als improving gilt.'
        self.assertEqual([], acc.promotion_lines([base, note]))
        promoted = '- C08 Genuine behavioral evidence: improving — zwei spontane Antworten'
        self.assertEqual([promoted], acc.promotion_lines([base, promoted]))
        self.assertEqual(['- C03 Governance: stable — bestätigt'], acc.promotion_lines(['- C03 Governance: stable — bestätigt']))


class SeparatedVerdicts(unittest.TestCase):
    def test_automatic_pass_without_domain_review_is_not_an_acceptance(self):
        self.assertEqual('UNREVIEWED', acc.final_verdict('PASS', 'NOT REVIEWED'))
        self.assertNotEqual(0, acc.exit_code('UNREVIEWED'))
        self.assertEqual('PASS', acc.final_verdict('PASS', 'PASS'))
        self.assertEqual(0, acc.exit_code('PASS'))

    def test_failure_on_either_side_never_looks_like_success(self):
        self.assertEqual('FAIL', acc.final_verdict('PASS', 'FAIL'))
        self.assertEqual('FAIL', acc.final_verdict('FAIL', 'PASS'))
        self.assertEqual('BLOCKED', acc.final_verdict('BLOCKED', 'PASS'))
        self.assertEqual('BLOCKED', acc.final_verdict('PASS', 'BLOCKED'))
        for final in ('FAIL', 'BLOCKED', 'NOT RUN', 'UNREVIEWED'):
            self.assertNotEqual(0, acc.exit_code(final), final)

    def test_automatic_verdict_is_never_a_pass_with_a_failed_check_or_none(self):
        self.assertEqual('FAIL', acc.auto_verdict([acc.check('x', True, 1), acc.check('y', False, 2)]))
        self.assertEqual('BLOCKED', acc.auto_verdict([]))
        self.assertEqual('PASS', acc.auto_verdict([acc.check('x', True, 1)]))

    def test_evidence_counts_only_for_the_unchanged_source_state(self):
        self.assertTrue(acc.evidence_current('abc', 'abc'))
        self.assertFalse(acc.evidence_current('abc', 'abd'))
        self.assertFalse(acc.evidence_current(None, None))

    def test_tree_fingerprint_changes_with_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'skills').mkdir()
            (Path(tmp) / 'skills/a.md').write_text('1')
            first = acc.tree_fingerprint(tmp)['aggregate']
            (Path(tmp) / 'skills/a.md').write_text('2')
            self.assertNotEqual(first, acc.tree_fingerprint(tmp)['aggregate'])


class StagedOrchestration(unittest.TestCase):
    HELP = 'import sys\nif "--version" in sys.argv: print("9.9.9 (fake)"); raise SystemExit\nif "--help" in sys.argv: print("{help}"); raise SystemExit\n'

    def prepare(self, tmp, body, help_text='--session-id --resume'):
        host = fake_host(tmp, self.HELP.replace('{help}', help_text) + body)
        os.environ['FAKE_LOG'] = str(Path(tmp) / 'calls.log')
        res = Path(tmp) / 'res'
        code = acc.main(['prepare', '--results', str(res), '--claude', host])
        if (res / 'state.json').is_file() and 'tmp' in acc.read_state(res):
            self.addCleanup(__import__('shutil').rmtree, acc.read_state(res)['tmp'], True)
        return code, res

    def calls(self, tmp):
        log = Path(tmp) / 'calls.log'
        return log.read_text().splitlines() if log.is_file() else []

    LOG = 'open(__import__("os").environ["FAKE_LOG"],"a").write("call\\n")\n'

    def test_cli_without_session_support_blocks_everything_and_starts_no_host(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, res = self.prepare(tmp, self.LOG, help_text='--print')
            self.assertEqual(2, code)
            state = acc.read_state(res)
            self.assertEqual({'BLOCKED'}, {v['final'] for v in state['phases'].values()})
            self.assertEqual([], self.calls(tmp))

    def test_failed_e_runs_one_host_call_then_blocks_f_and_g_and_all_exit_codes_are_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, res = self.prepare(tmp, self.LOG + 'print("{\\"type\\":\\"result\\",\\"result\\":\\"done\\",\\"is_error\\":false}")\n')
            self.assertEqual(0, code)
            self.assertTrue((res / '00-setup.json').is_file() and (res / '01-fixture.json').is_file())
            e = acc.main(['evidence', '--results', str(res)])
            self.assertEqual(1, e, 'no job was created: FAIL, never a success exit')
            self.assertEqual(1, len(self.calls(tmp)))
            self.assertEqual(2, acc.main(['ask', '--results', str(res)]))
            self.assertEqual(1, len(self.calls(tmp)), 'F must not start a host after a failed E')
            state = acc.read_state(res)
            self.assertEqual('FAIL', state['phases']['E']['final'])
            self.assertEqual('BLOCKED', state['phases']['F']['final'])
            self.assertNotEqual(0, acc.main(['status', '--results', str(res)]))
            self.assertTrue((res / 'E/E.process.json').is_file())

    def test_review_does_not_override_a_failed_automatic_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, res = self.prepare(tmp, self.LOG)
            acc.main(['evidence', '--results', str(res)])
            review = Path(tmp) / 'review.json'
            review.write_text(json.dumps({'verdict': 'PASS', 'criteria': []}))
            acc.main(['review-evidence', '--results', str(res), '--review', str(review)])
            state = acc.read_state(res)
            self.assertEqual('FAIL', state['phases']['E']['final'])
            self.assertEqual('NOT RUN', state['phases']['E']['domain'])

    def test_g_is_blocked_without_a_passing_answer_check_and_starts_no_host(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, res = self.prepare(tmp, self.LOG)
            before = len(self.calls(tmp))
            self.assertEqual(2, acc.main(['answer', '--results', str(res)]))
            self.assertEqual(before, len(self.calls(tmp)))
            self.assertEqual('BLOCKED', acc.read_state(res)['phases']['G']['final'])

    def test_ambiguous_f_question_blocks_the_answer_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, res = self.prepare(tmp, self.LOG)
            state = acc.read_state(res)
            state['phases']['F'] = {'automatic': 'PASS', 'domain': 'NOT REVIEWED', 'final': 'UNREVIEWED'}
            acc.write_state(res, state)
            (res / 'F').mkdir(exist_ok=True)
            (res / 'F/question.json').write_text(json.dumps({'reply': 'x', 'block': 'B?', 'ambiguous': True}))
            answer, review = Path(tmp) / 'a.txt', Path(tmp) / 'r.json'
            answer.write_text(ANSWER)
            review.write_text(json.dumps(fit_review()))
            self.assertEqual(2, acc.main(['check-answer', '--results', str(res), '--answer', str(answer), '--review', str(review)]))
            self.assertEqual('BLOCKED', acc.read_state(res)['phases']['G']['final'])
            self.assertEqual(2, acc.main(['answer', '--results', str(res)]))


if __name__ == '__main__':
    unittest.main()
