"""Follow-up dialogue persistence (run format 4): real runtime, fictional data only (acceptance scenarios A, D, E, G, I)."""
import json
import unittest

from tests.support import coach as support
from tests.support.coach import Base, block, followup, iw, snapshot


def meta_of(path):
    return json.loads(path.read_text(encoding='utf-8').splitlines()[0][len('<!-- zyris-run: '):-4])


class FollowupDialogue(Base):
    def setUp(self):
        super().setUp()
        self.setup_local()
        self.cid = self.candidate()

    def save(self, run_id, dialogue, **kw):
        kw.setdefault('answered_count', sum(1 for b in dialogue if b['initial_answer'] is not None))
        kw.setdefault('planned_count', 3)
        kw.setdefault('status', 'paused')
        return self.finish(self.cid, run_id, dialogue=dialogue, **kw)

    def rejected(self, run_id, dialogue, fragment, **kw):
        before = snapshot(self.root)
        with self.assertRaises(ValueError) as caught:
            self.save(run_id, dialogue, **kw)
        self.assertIn(fragment, str(caught.exception))
        self.assertEqual(before, snapshot(self.root))

    def test_a_completion_followup_is_counted_separately_and_documented(self):
        path = self.save('a1', [block(1, followups=[followup(1, 1, answer='Ich hätte den Termindruck mit dem PO priorisiert.')])],
                         status='completed', planned_count=1)
        meta = meta_of(path)
        self.assertEqual((1, 1, 1, 0), (meta['answered_count'], meta['followup_count'], meta['followup_answered_count'], meta['retry_count']))
        self.assertEqual('q-1-f1', meta['dialogue'][0]['followups'][0]['id'])
        self.assertEqual('after_followup', iw.followup_evidence(meta['dialogue'][0]['followups'][0]))

    def test_followup_never_raises_the_main_question_count(self):
        dialogue = [block(1, followups=[followup(1, 1), followup(1, 2, kind='deepening')])]
        self.rejected('bad', dialogue, 'does not match', answered_count=3, status='completed')
        path = self.save('ok', dialogue, answered_count=1, planned_count=3)
        self.assertEqual((1, 2), (meta_of(path)['answered_count'], meta_of(path)['followup_count']))

    def test_evidence_classes_after_hints_and_retries_after_coaching(self):
        hinted = followup(1, 1, hints=True)
        self.assertEqual('supported', iw.followup_evidence(hinted))
        retry = [dict(answer='Neuer Versuch.', after_coaching=True), dict(answer='Frei.', after_coaching=False)]
        path = self.save('e1', [block(1, followups=[hinted], retries=retry, open_gaps=['Kernanforderung weiter offen'])])
        evidence = iw.describe_dialogue(meta_of(path)['dialogue'])[0]
        self.assertEqual(['supported', 'independent_retry'], [r['evidence'] for r in evidence['retries']])
        self.assertEqual(2, meta_of(path)['retry_count'])
        self.assertEqual(1, meta_of(path)['answered_count'])
        self.assertIn('Kernanforderung weiter offen', evidence['open_gaps'])

    def test_e_gap_stays_open_with_followup_resolution_open(self):
        path = self.save('e2', [block(1, followups=[followup(1, 1, answer='Weiß ich nicht.', resolution='open')])])
        self.assertEqual(['Termindruck nicht behandelt'], iw.describe_dialogue(meta_of(path)['dialogue'])[0]['open_gaps'])

    def test_d_deepening_is_not_a_gap_or_error(self):
        deep = followup(1, 1, kind='deepening')
        self.assertIsNone(deep['gap'])
        self.save('d1', [block(1, followups=[deep])], status='completed', planned_count=1)
        self.rejected('d2', [block(1, followups=[dict(deep, gap='Fehler')])], 'deepening')
        self.rejected('d3', [block(1, followups=[dict(deep, resolution='open')])], 'deepening')

    def test_clarification_and_completion_name_their_gap(self):
        self.rejected('g1', [block(1, followups=[dict(followup(1, 1), gap=None)])], 'name the gap')

    def test_structure_is_strict(self):
        self.rejected('s1', [dict(block(1), key='q-2')], 'q-1')
        self.rejected('s2', [dict(block(1), extra='x')], 'exactly the fields')
        self.rejected('s3', [block(1, followups=[dict(followup(1, 1), id='x')])], 'id must be')
        self.rejected('s4', [block(1, followups=[dict(followup(1, 1), kind='retry')])], 'kind must be')
        self.rejected('s5', [block(1, retries=[dict(answer='x')])], 'exactly the fields')
        self.rejected('s6', [block(1, followups=[dict(followup(1, 1), hints_before='ja')])], 'boolean')
        self.rejected('s7', [block(1, followups=[dict(followup(1, 1), resolution='closed', answer=None)])], 'pending')
        self.rejected('s8', [block(1), block(2, answer=None), block(3)], 'only the last main question')
        with self.assertRaises(ValueError):
            self.finish(self.cid, 'none', dialogue=None)

    def test_g_stop_with_open_followup_is_not_an_answer(self):
        dialogue = [block(1, followups=[followup(1, 1, answer=None)])]
        path = self.save('g1', dialogue, status='stopped_early', planned_count=5)
        meta = meta_of(path)
        self.assertEqual((1, 1, 0), (meta['answered_count'], meta['followup_count'], meta['followup_answered_count']))
        self.assertEqual('q-1-f1', iw.open_followup(meta['dialogue']))
        self.assertEqual('none', iw.describe_dialogue(meta['dialogue'])[0]['followups'][0]['evidence'])
        self.rejected('g2', dialogue, 'only the last follow-up', status='completed', planned_count=1)
        self.rejected('g3', [block(1, followups=[followup(1, 1, answer=None), followup(1, 2)])], 'only the last follow-up')

    def test_unanswered_main_question_on_stop_is_not_counted(self):
        path = self.save('g4', [block(1), block(2, answer=None)], status='stopped_early')
        self.assertEqual(1, meta_of(path)['answered_count'])
        self.rejected('g5', [block(1), block(2, answer=None)], 'only the last main question', status='completed', planned_count=1)

    def test_i_pause_and_continuation_keep_assignment_and_do_not_repeat(self):
        first = [block(1, followups=[followup(1, 1)]), block(2, followups=[followup(2, 1, answer=None)])]
        self.save('p1', first, status='paused')
        resumed = iw.resume(self.root, self.cid, 'p1')
        self.assertEqual('q-2-f1', resumed['open_followup'])
        self.assertEqual(['after_followup'], [f['evidence'] for f in resumed['dialogue_evidence'][0]['followups']])
        answered = [first[0], block(2, followups=[followup(2, 1, answer='Nachgeliefert.')]), block(3)]
        path = self.save('p2', answered, status='completed', planned_count=3, resume_from='p1')
        self.assertEqual((3, 2, 2), (meta_of(path)['answered_count'], meta_of(path)['followup_count'], meta_of(path)['followup_answered_count']))
        self.assertEqual(3, meta_of(path)['planned_count'])
        self.assertEqual(3, iw.validate_run_records(self.cdir(self.cid))['p2']['planned_count'])

    def test_continuation_rejects_changed_or_repeated_content(self):
        base = [block(1, followups=[followup(1, 1)]), block(2, followups=[followup(2, 1, answer=None)])]
        self.save('p1', base, status='paused')
        changed = [dict(base[0], initial_answer='Anders'), base[1]]
        self.rejected('c1', changed, 'closed main question', status='paused', resume_from='p1')
        repeated = [block(1, followups=[followup(1, 1), followup(1, 2)]), base[1]]
        self.rejected('c2', repeated, 'closed main question', status='paused', resume_from='p1')
        altered = [block(1, followups=[followup(1, 1, answer='Neu formuliert')]), base[1]]
        self.rejected('c3', altered, 'closed main question', status='paused', resume_from='p1')
        self.rejected('c4', [base[0]], 'cannot decrease', status='paused', answered_count=1, resume_from='p1')

    def pause_with_open_hinted_followup(self, hints=True, gaps=('Rollen offen',)):
        pending = followup(1, 1, answer=None, hints=hints)
        self.save('p1', [block(1, followups=[pending], open_gaps=list(gaps))], status='paused')
        return pending

    def test_hint_then_pause_then_answer_stays_supported(self):
        pending = self.pause_with_open_hinted_followup()
        resumed = iw.resume(self.root, self.cid, 'p1')
        self.assertEqual('q-1-f1', resumed['open_followup'])
        answered = dict(pending, answer='Nach dem Hinweis ergänzt.', resolution='closed')
        path = self.save('p2', [block(1, followups=[answered], open_gaps=['Rollen offen'])], status='stopped_early', planned_count=3, resume_from='p1')
        meta = meta_of(path)
        self.assertTrue(meta['dialogue'][0]['followups'][0]['hints_before'])
        self.assertEqual('supported', iw.describe_dialogue(meta['dialogue'])[0]['followups'][0]['evidence'])

    def test_documented_hint_cannot_be_removed_on_continuation(self):
        pending = self.pause_with_open_hinted_followup()
        silent = dict(pending, answer='Ergänzt.', resolution='closed', hints_before=False)
        self.rejected('p2', [block(1, followups=[silent], open_gaps=['Rollen offen'])], 'documented hint', status='paused', resume_from='p1')

    def test_hint_may_be_added_to_a_pending_followup_but_not_to_an_answered_one(self):
        pending = self.pause_with_open_hinted_followup(hints=False)
        self.save('p2', [block(1, followups=[dict(pending, hints_before=True, answer='Mit Hinweis.', resolution='closed')],
                               open_gaps=['Rollen offen'])], status='paused', resume_from='p1')

    def test_documented_gaps_cannot_vanish_without_new_evidence(self):
        pending = self.pause_with_open_hinted_followup()
        self.rejected('g1', [block(1, followups=[pending])], 'open gap disappeared', status='paused', resume_from='p1')
        self.rejected('g2', [dict(block(1, followups=[pending], open_gaps=['Rollen offen']), block_assessment='Neu bewertet')],
                      'without new evidence', status='paused', resume_from='p1')
        answered = dict(pending, answer='Jetzt beantwortet.', resolution='closed')
        path = self.save('g3', [dict(block(1, followups=[answered]), block_assessment='Nach Evidenz neu bewertet')],
                         status='stopped_early', planned_count=3, resume_from='p1')
        self.assertEqual([], meta_of(path)['dialogue'][0]['other_open_gaps'])

    def test_answered_gap_resolution_gap_text_and_wording_are_immutable(self):
        answered = followup(1, 1, answer='Weiß ich nicht.', resolution='open')
        self.save('a1', [block(1, followups=[answered]), block(2, answer=None)], status='paused')
        for field, value in (('resolution', 'closed'), ('gap', 'Anderes'), ('text', 'Umformuliert?'), ('reason', 'Anderer Anlass'), ('kind', 'clarification')):
            changed = dict(answered, **{field: value})
            self.rejected('a-' + field, [block(1, followups=[changed]), block(2)], 'closed main question', status='paused', answered_count=2, resume_from='a1')

    def test_last_block_may_only_grow_and_initial_assessment_is_fixed(self):
        self.save('l1', [block(1), dict(block(2), followups=[], block_assessment=None)], status='paused')
        self.rejected('l2', [block(1), dict(block(2), initial_assessment='Andere Erstbewertung')], 'first-answer assessment', status='paused', answered_count=2, resume_from='l1')
        self.save('l3', [block(1), dict(block(2, followups=[followup(2, 1)]), block_assessment='Mit Evidenz')], status='paused', answered_count=2, planned_count=3, resume_from='l1')

    def test_run_format_three_is_refused_before_writes_and_preserved(self):
        old = self.cdir(self.cid) / 'runs' / 'old.md'
        old.write_text('<!-- zyris-run: {"schema_version":3,"run_id":"old","candidate_id":"%s","job_id":null,"status":"completed",'
                       '"answered_count":1,"planned_count":1,"resume_from":null} -->\nalt' % self.cid)
        before = snapshot(self.root)
        with self.assertRaises(ValueError) as caught:
            self.save('new', [block(1)], status='completed', planned_count=1)
        self.assertIn('run format 3', str(caught.exception).replace('Unsupported run format 3', 'run format 3'))
        self.assertEqual(before, snapshot(self.root))

    def test_header_with_comment_terminator_in_answer_roundtrips(self):
        path = self.save('h1', [block(1, answer='Antwort mit --> und <!-- Zeichen.')], status='completed', planned_count=1)
        self.assertEqual(1, len(path.read_text(encoding='utf-8').splitlines()[0].split(' -->')) - 1)
        self.assertIn('-->', iw.read_run(self.cdir(self.cid), 'h1')[0]['dialogue'][0]['initial_answer'])

    def test_cli_requires_dialogue_file_and_saves_it(self):
        cid = self.cid
        status = json.loads(self.cli('status', '--project', self.project, '--candidate', cid).stdout)
        args = ['finish', '--project', self.project, '--candidate', cid, '--run-id', 'r1', '--run-file', self.write('r.md', '# r\n'),
                '--state-file', self.write('s.md', '# s\n'), '--expected-state-sha256', status['state_sha256'],
                '--status', 'stopped_early', '--answered-count', '1']
        self.cli(*args, expect=2)  # argparse: --dialogue-file missing
        dialogue = [block(1, followups=[followup(1, 1, answer=None)])]
        self.cli(*args, '--dialogue-file', self.write('d.json', json.dumps(dialogue)))
        self.cli('resume', '--project', self.project, '--candidate', cid, '--run-id', 'r1', expect=1)  # a stopped run is not resumable
        self.assertEqual('q-1-f1', iw.open_followup(iw.read_run(self.cdir(cid), 'r1')[0]['dialogue']))


if __name__ == '__main__':
    unittest.main()


class RoleFitAndStop(Base):
    """Confirmed role preference -> job-specific match snapshot; STOP is final, only PAUSE can be resumed (acceptance C, G, I)."""

    def setUp(self):
        super().setUp()
        self.setup_local()
        self.cid = self.candidate()
        iw.import_cv(self.root, self.cid, self.write('cv.md', '# Erika\n'))
        self.job = iw.create_job(self.root, self.cid, 'Product Owner Plattform', 'Beispiel AG', posting_text_file=self.write('p.md', 'Produktstrategie, Führung'))['job_id']

    def confirm_profile(self):
        iw.save_profile(self.root, self.cid, self.write('pr.md', '- Backend [Quelle: CV]\n'), status='confirmed', origin='cv', cv_source='cv-001', user_confirmed=True)

    def match(self, text):
        with iw.candidate_lock(self.root, self.cid) as cdir:
            return iw.add_artifact(cdir, iw.job_dir(cdir, self.job), 'match', text)

    def test_confirmed_role_preference_is_stored_in_the_job_match_not_only_in_the_run_and_not_in_state(self):
        preference = 'Fit-Punkt (im Training bestätigt): Wunsch nach eigener technischer Umsetzung; spricht gegen den Product-Schwerpunkt.'
        with self.assertRaisesRegex(ValueError, 'confirmed profile'):
            self.match(preference)                     # unconfirmed profile: nothing is written, the fit point is NOT saved
        self.assertFalse((self.cdir(self.cid) / 'jobs' / self.job / 'match').exists() and list((self.cdir(self.cid) / 'jobs' / self.job / 'match').iterdir()))
        self.confirm_profile()
        first = self.match('Anforderung A: direkt belegt')
        second = self.match('Anforderung A: direkt belegt\n' + preference)   # new full snapshot carries the earlier content
        self.assertEqual((1, 2), (first['seq'], second['seq']))
        folder = self.cdir(self.cid) / 'jobs' / self.job / 'match'
        self.assertNotIn(preference, (folder / '001.md').read_text(encoding='utf-8'))      # earlier snapshot stays unchanged
        latest = (folder / '002.md').read_text(encoding='utf-8')
        meta = json.loads(latest.splitlines()[0].split(': ', 1)[1][:-4])
        self.assertEqual((self.cid, self.job, 'match'), (meta['candidate_id'], meta['job_id'], meta['kind']))
        self.assertIn(preference, latest)
        dialogue = [block(1, followups=[followup(1, 1, kind='clarification')])]
        path = self.save_run('r1', dialogue, status='stopped_early', state_text='# State\n- keine Kompetenzänderung\n')
        header = meta_of(path)
        self.assertEqual((self.cid, self.job), (header['candidate_id'], header['job_id']))   # run and match share the assignment
        self.assertNotIn('technischen Umsetzung', (self.cdir(self.cid) / 'state.md').read_text(encoding='utf-8'))

    def save_run(self, run_id, dialogue, **kw):
        kw.setdefault('answered_count', sum(1 for b in dialogue if b['initial_answer'] is not None))
        kw.setdefault('planned_count', 3)
        return self.finish(self.cid, run_id, dialogue=dialogue, job_id=self.job, **kw)

    def test_a_stopped_run_is_final_and_cannot_be_resumed_while_a_paused_one_can(self):
        open_dialogue = [block(1, followups=[followup(1, 1, answer=None)])]
        self.save_run('s1', open_dialogue, status='stopped_early')
        with self.assertRaisesRegex(ValueError, 'Only a paused checkpoint can be resumed'):
            iw.resume(self.root, self.cid, 's1')
        with self.assertRaises(ValueError):                 # STOP never finishes as completed while the follow-up is open
            self.save_run('s2', open_dialogue, status='completed', planned_count=1)
        self.save_run('p1', open_dialogue, status='paused')
        resumed = iw.resume(self.root, self.cid, 'p1')
        self.assertEqual('q-1-f1', resumed['open_followup'])
        answered = [block(1, followups=[followup(1, 1, answer='Nachgeliefert.')])]
        path = self.save_run('p2', answered, status='stopped_early', resume_from='p1', planned_count=3)
        self.assertEqual(('stopped_early', 'p1'), (meta_of(path)['status'], meta_of(path)['resume_from']))
        self.assertEqual((1, 1), (meta_of(path)['answered_count'], meta_of(path)['followup_answered_count']))
