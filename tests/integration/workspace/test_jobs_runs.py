"""REQ-JOB/RUN: candidate-owned jobs, append-only evidence, immutable runs, lifecycle, recovery."""
import hashlib
import json
import os
import stat
import unittest
from unittest import mock

from tests.support import coach as support
from tests.support.coach import Base, iw, make_docx, snapshot


class Jobs(Base):
    def setUp(self):
        super().setUp()
        self.setup_local()
        self.cid = self.candidate()
        self.posting = self.write('posting.md', '# Senior Backend Engineer\nPython, Kubernetes\n')

    def create(self, cid=None, **kw):
        kw.setdefault('title', 'Senior Backend Engineer')
        kw.setdefault('company', 'ACME GmbH')
        kw.setdefault('posting_text_file', self.posting)
        return iw.create_job(self.root, cid or self.cid, **kw)

    def test_job_belongs_to_candidate_keeps_posting_and_origin(self):
        job = self.create(source_url='https://example.invalid/jobs/1', retrieved_at='2026-11-19')
        shown = iw.show_job(self.root, self.cid, job['job_id'])
        posting = shown['latest']['posting']
        self.assertEqual(self.cid, posting['meta']['candidate_id'])
        self.assertEqual(job['job_id'], posting['meta']['job_id'])
        self.assertEqual(['https://example.invalid/jobs/1'], posting['meta']['sources'])
        self.assertEqual('2026-11-19', posting['meta']['retrieved_at'])
        self.assertIn('Kubernetes', posting['content'])

    def test_link_without_retrieval_date_or_content_is_refused_without_writes(self):
        before = snapshot(self.root)
        with self.assertRaisesRegex(ValueError, 'retrieval date'):
            self.create(source_url='https://example.invalid/x')
        with self.assertRaisesRegex(ValueError, 'nothing is invented'):
            iw.create_job(self.root, self.cid, 'Engineer', 'ACME', source_url='https://example.invalid/x', retrieved_at='2026-11-19')
        self.assertEqual(before, snapshot(self.root))

    def test_missing_company_and_unknown_participants_do_not_block_but_are_open_points(self):
        job = self.create(company=None)
        self.assertEqual('active', job['status'])
        shown = iw.show_job(self.root, self.cid, job['job_id'])
        self.assertIn('company missing', shown['open_points'])
        iw.update_job(self.root, self.cid, job['job_id'], company='Beispiel AG', participants_status='unknown')
        shown = iw.show_job(self.root, self.cid, job['job_id'])
        self.assertEqual('Beispiel AG', shown['job']['company'])
        self.assertEqual([], shown['open_points'])
        self.assertEqual('company', shown['job']['changes'][0]['field'])

    def test_participant_rules_and_same_name_people_stay_distinct_until_verified(self):
        job = self.create()
        updated = iw.update_job(self.root, self.cid, job['job_id'], persons=['Max Muster::CTO', 'Max Muster::Recruiter'])
        ids = [p['person_id'] for p in updated['participants']['people']]
        self.assertEqual(['p-1', 'p-2'], ids)
        self.assertEqual('provided', updated['participants']['status'])
        self.assertIn('participant identity unverified', iw.list_jobs(self.root, self.cid)[0]['open_points'])
        iw.update_job(self.root, self.cid, job['job_id'], verify=['p-1', 'p-2'])
        self.assertEqual([], iw.list_jobs(self.root, self.cid)[0]['open_points'])
        with self.assertRaisesRegex(ValueError, 'cannot be .unknown'):
            iw.update_job(self.root, self.cid, job['job_id'], participants_status='unknown')
        with self.assertRaisesRegex(ValueError, 'Unknown participant'):
            iw.update_job(self.root, self.cid, job['job_id'], verify=['p-9'])

    def test_research_requires_date_and_updates_never_remove_history(self):
        job = self.create()
        jid = job['job_id']
        with self.assertRaisesRegex(ValueError, 'retrieval date'):
            self.add(jid, 'research', 'no date')
        self.add(jid, 'research', 'Fact A', sources=['https://example.invalid/a'], retrieved_at='2026-01-01')
        self.add(jid, 'research', 'Fact A updated', sources=['https://example.invalid/b'], retrieved_at='2026-11-19')
        shown = iw.show_job(self.root, self.cid, jid)['latest']['research']
        self.assertEqual([1, 2], shown['history'])
        self.assertIn('updated', shown['content'])
        old = (self.cdir(self.cid) / 'jobs' / jid / 'research/001.md').read_text()
        self.assertIn('Fact A', old)
        self.assertIn('2026-01-01', old)
        self.add(jid, 'posting', 'Revised posting', retrieved_at='2026-11-19')
        self.assertIn('Kubernetes', (self.cdir(self.cid) / 'jobs' / jid / 'postings/001.md').read_text(), 'original posting preserved')

    def add(self, jid, kind, text, **kw):
        with iw.candidate_lock(self.root, self.cid) as cdir:
            return iw.add_artifact(cdir, iw.job_dir(cdir, jid), kind, text, **kw)

    def test_uploaded_docx_posting_keeps_original_bytes(self):
        path = make_docx(self.base / 'posting.docx', ['Senior Engineer', 'Aufgaben: APIs'])
        job = iw.create_job(self.root, self.cid, 'Engineer', 'ACME', posting_file=path)
        stored = self.cdir(self.cid) / 'jobs' / job['job_id'] / 'postings/001.original.docx'
        self.assertEqual(path.read_bytes(), stored.read_bytes())
        self.assertIn('Aufgaben: APIs', iw.show_job(self.root, self.cid, job['job_id'])['latest']['posting']['content'])

    def test_several_jobs_per_candidate_and_jobs_are_not_visible_to_other_candidates(self):
        other = self.candidate('Max Muster')
        one, two = self.create(), self.create(title='Team Lead', company='Beispiel AG')
        self.assertEqual({one['job_id'], two['job_id']}, {j['job_id'] for j in iw.list_jobs(self.root, self.cid)})
        self.assertEqual([], iw.list_jobs(self.root, other))
        with self.assertRaisesRegex(ValueError, 'Unknown job'):
            iw.show_job(self.root, other, one['job_id'])

    def test_interrupted_job_creation_is_an_unusable_draft(self):
        with mock.patch.object(iw, 'add_artifact', side_effect=OSError('disk full')):
            with self.assertRaisesRegex(RuntimeError, 'Job creation incomplete'):
                self.create()
        (entry,) = (self.cdir(self.cid) / 'jobs').iterdir()
        self.assertEqual('creating', json.loads((entry / 'job.json').read_text())['status'])
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            iw.update_job(self.root, self.cid, entry.name, company='X')
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.finish(self.cid, 'r1', job_id=entry.name)


class Runs(Base):
    def setUp(self):
        super().setUp()
        self.setup_local()
        self.cid = self.candidate()
        self.job = iw.create_job(self.root, self.cid, 'Engineer', 'ACME', posting_text_file=self.write('p.md', 'Posting text'))['job_id']

    def test_run_header_records_candidate_and_job_and_runs_are_immutable(self):
        path = self.finish(self.cid, 'run-1', job_id=self.job)
        header = path.read_text().splitlines()[0]
        meta = json.loads(header[len('<!-- zyris-run: '):-4])
        self.assertEqual((self.cid, self.job, iw.RUN_SCHEMA), (meta['candidate_id'], meta['job_id'], meta['schema_version']))
        with self.assertRaises(FileExistsError):
            self.finish(self.cid, 'run-1', job_id=self.job)
        self.assertEqual(header, path.read_text().splitlines()[0])

    def test_two_runs_for_the_same_job_and_a_general_run(self):
        self.finish(self.cid, 'job-run-1', job_id=self.job)
        self.finish(self.cid, 'job-run-2', job_id=self.job)
        self.finish(self.cid, 'general-1')
        self.assertEqual(['general-1', 'job-run-1', 'job-run-2'], iw.snapshot(self.root, self.cid)['runs'])

    def test_foreign_job_id_rejected_before_writes(self):
        other = self.candidate('Max Muster')
        foreign = iw.create_job(self.root, other, 'Other', 'Corp', posting_text_file=self.write('q.md', 'Other posting'))['job_id']
        before = snapshot(self.root)
        with self.assertRaises(ValueError):
            self.finish(self.cid, 'bad', job_id=foreign)
        with self.assertRaises(ValueError):
            self.finish(self.cid, 'bad', job_id='j-nonexistent-12345678')
        self.assertEqual(before, snapshot(self.root))

    def test_finish_cannot_touch_another_candidates_state(self):
        other = self.candidate('Max Muster')
        other_state = (self.cdir(other) / 'state.md').read_bytes()
        self.finish(self.cid, 'run-1', state_text='# only mine\n')
        self.assertEqual(other_state, (self.cdir(other) / 'state.md').read_bytes())
        self.assertFalse((self.cdir(other) / 'runs/run-1.md').exists())

    def test_stale_state_rejected_and_nothing_written(self):
        stale = self.state_hash(self.cid)
        self.finish(self.cid, 'run-1')
        before = snapshot(self.root)
        with self.assertRaisesRegex(ValueError, 'Stale state snapshot'):
            self.finish(self.cid, 'run-2', expected_state_sha256=stale)
        self.assertEqual(before, snapshot(self.root))

    def test_pause_resume_creates_new_run_and_preserves_checkpoint_and_plan(self):
        self.finish(self.cid, 'p1', status='paused', answered_count=2, planned_count=5, job_id=self.job)
        resumed = iw.resume(self.root, self.cid, 'p1')
        self.assertEqual('paused', resumed['run']['status'])
        with self.assertRaisesRegex(ValueError, 'another job'):
            self.finish(self.cid, 'bad', status='paused', answered_count=3, planned_count=5, resume_from='p1')
        with self.assertRaisesRegex(ValueError, 'planned count'):
            self.finish(self.cid, 'bad2', status='paused', answered_count=5, planned_count=6, resume_from='p1', job_id=self.job)
        self.finish(self.cid, 'p2', status='completed', answered_count=5, planned_count=None, resume_from='p1', job_id=self.job)
        self.assertEqual(5, json.loads(self.cdir(self.cid).joinpath('runs/p2.md').read_text().splitlines()[0][16:-4])['planned_count'])
        with self.assertRaisesRegex(ValueError, 'Only a paused checkpoint'):
            iw.resume(self.root, self.cid, 'p2')
        with self.assertRaisesRegex(ValueError, 'already continued'):
            iw.resume(self.root, self.cid, 'p1')
        self.assertIn('Run p1', self.cdir(self.cid).joinpath('runs/p1.md').read_text())

    def test_stopped_early_is_partial_evidence_and_incomplete_completed_is_refused(self):
        self.finish(self.cid, 's1', status='stopped_early', answered_count=1, planned_count=5)
        with self.assertRaisesRegex(ValueError, 'Incomplete interview'):
            self.finish(self.cid, 's2', status='completed', answered_count=1, planned_count=5)

    def test_resume_from_run_of_other_candidate_is_rejected(self):
        other = self.candidate('Max Muster')
        self.finish(other, 'other-p', status='paused', answered_count=1, planned_count=3)
        with self.assertRaises(ValueError):
            self.finish(self.cid, 'mine', status='paused', answered_count=2, planned_count=3, resume_from='other-p')

    def test_tampered_run_belonging_to_other_candidate_blocks_operations(self):
        other = self.candidate('Max Muster')
        path = self.finish(other, 'r-other')
        (self.cdir(self.cid) / 'runs/r-other.md').write_text(path.read_text())
        before = snapshot(self.root)
        with self.assertRaisesRegex(ValueError, 'belongs to another candidate'):
            self.finish(self.cid, 'new')
        self.assertEqual(before, snapshot(self.root))

    def test_crash_after_journal_is_recovered_without_loss(self):
        expected = self.state_hash(self.cid)
        with mock.patch.object(iw, 'apply_pending', side_effect=OSError('crash')):
            with self.assertRaisesRegex(RuntimeError, 'Save incomplete.*Run recover'):
                self.finish(self.cid, 'r1', job_id=self.job, state_text='# new state\n')
        with self.assertRaisesRegex(RuntimeError, 'Pending transaction'):
            iw.snapshot(self.root, self.cid)
        self.assertEqual(expected, hashlib.sha256((self.cdir(self.cid) / 'state.md').read_bytes()).hexdigest())
        self.assertTrue(iw.recover(self.root, self.cid).is_file())
        self.assertEqual('# new state\n', (self.cdir(self.cid) / 'state.md').read_text())
        self.assertIsNone(iw.recover(self.root, self.cid))

    def test_conflicting_external_edit_during_pending_is_not_overwritten(self):
        with mock.patch.object(iw, 'apply_pending', side_effect=OSError('crash')):
            with self.assertRaises(RuntimeError):
                self.finish(self.cid, 'r1', state_text='# intended\n')
        (self.cdir(self.cid) / 'state.md').write_text('# edited by someone else\n')
        with self.assertRaisesRegex(ValueError, 'State changed outside pending transaction'):
            iw.recover(self.root, self.cid)
        self.assertEqual('# edited by someone else\n', (self.cdir(self.cid) / 'state.md').read_text())
        self.assertTrue((self.cdir(self.cid) / '.journal/pending.json').exists())

    def test_missing_write_permission_reports_failure_not_success(self):
        runs = self.cdir(self.cid) / 'runs'
        runs.chmod(stat.S_IRUSR | stat.S_IXUSR)
        self.addCleanup(runs.chmod, 0o700)
        if os.access(runs, os.W_OK):
            self.skipTest('permissions not enforced for this user')
        with self.assertRaisesRegex(RuntimeError, 'Save incomplete; do not claim success'):
            self.finish(self.cid, 'r1')
        self.assertFalse((runs / 'r1.md').exists())

    def test_fsync_failure_is_not_reported_as_success(self):
        expected = self.state_hash(self.cid)
        with mock.patch('coach_core.os.fsync', side_effect=OSError('io error')):
            with self.assertRaises((OSError, RuntimeError)):
                self.finish(self.cid, 'r1', expected_state_sha256=expected)
        self.assertFalse((self.cdir(self.cid) / 'runs/r1.md').exists())
        self.assertEqual(expected, self.state_hash(self.cid))

    def test_unsafe_run_ids_and_symlinks_rejected(self):
        for bad in ('../x', 'a/b', '', '..', '.hidden'):
            with self.assertRaises(ValueError):
                self.finish(self.cid, bad)
        outside = self.base / 'outside.md'
        outside.write_text('keep')
        (self.cdir(self.cid) / 'runs/link.md').symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.finish(self.cid, 'r2')
        self.assertEqual('keep', outside.read_text())


class CliSmoke(Base):
    def test_cli_end_to_end_with_explicit_project_selection(self):
        self.cli('project-init', '--project', self.project, '--storage', 'local', '--path', self.root)
        created = json.loads(self.cli('candidate-create', '--project', self.project, '--name', 'Erika Beispiel').stdout)
        cid = created['candidate_id']
        cv = self.write('cv.md', '# Erika\n')
        self.assertEqual('complete', json.loads(self.cli('cv-import', '--project', self.project, '--candidate', cid, '--file', cv).stdout)['extraction_status'])
        status = json.loads(self.cli('status', '--project', self.project, '--candidate', cid).stdout)
        run, state = self.write('run.md', '# run\n'), self.write('state.md', '# state\n')
        dialogue_file = self.write('dialogue.json', json.dumps(support.dialogue(1)))
        self.cli('finish', '--project', self.project, '--candidate', cid, '--run-id', 'r1', '--run-file', run, '--state-file', state,
                 '--expected-state-sha256', status['state_sha256'], '--status', 'completed', '--answered-count', '1', '--dialogue-file', dialogue_file)
        self.cli('finish', '--project', self.project, '--candidate', cid, '--run-id', 'r1', '--run-file', run, '--state-file', state,
                 '--expected-state-sha256', status['state_sha256'], '--status', 'completed', '--answered-count', '1', '--dialogue-file', dialogue_file, expect=1)
        self.assertIn('VALID', self.cli('validate', '--project', self.project).stdout)
        self.cli('status', '--project', self.base, '--candidate', cid, expect=1)  # other project: unresolved
        ambiguous = self.cli('candidate-create', '--project', self.project, '--name', 'Erika Beispiel')
        done = self.cli('candidate-resolve', '--project', self.project, '--name', 'Erika Beispiel', expect=2)
        self.assertIn('ambiguous', done.stderr)


if __name__ == '__main__':
    unittest.main()
