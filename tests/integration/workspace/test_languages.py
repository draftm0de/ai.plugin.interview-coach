"""R5: candidate defaults and independent per-job interview languages."""
import json

from tests.support.coach import Base, iw, snapshot


class InterviewLanguages(Base):
    def setUp(self):
        super().setUp()
        self.setup_local()
        self.cid = self.candidate()
        self.other = self.candidate('Alex Beispiel')
        posting = self.write('posting.md', 'Fictional backend position')
        self.jobs = [iw.create_job(self.root, self.cid, title, 'Example Company', posting_text_file=posting)['job_id']
                     for title in ('Backend Engineer', 'Team Lead')]

    def test_candidate_default_job_override_and_dynamic_inheritance_are_isolated(self):
        iw.set_language(self.root, 'de')
        self.assertIsNone(iw.snapshot(self.root, self.cid)['interview_language'])
        iw.set_interview_language(self.root, self.cid, 'de')
        iw.set_interview_language(self.root, self.other, 'fr')
        iw.set_interview_language(self.root, self.cid, 'en', job_id=self.jobs[0])
        first = iw.show_job(self.root, self.cid, self.jobs[0])
        second = iw.show_job(self.root, self.cid, self.jobs[1])
        self.assertEqual(('en', 'job'), (first['interview_language'], first['language_source']))
        self.assertEqual(('de', 'candidate'), (second['interview_language'], second['language_source']))
        iw.set_interview_language(self.root, self.cid, 'it')
        self.assertEqual('en', iw.show_job(self.root, self.cid, self.jobs[0])['interview_language'])
        self.assertEqual('it', iw.show_job(self.root, self.cid, self.jobs[1])['interview_language'])
        self.assertEqual('fr', iw.snapshot(self.root, self.other)['interview_language'])
        iw.set_interview_language(self.root, self.cid, job_id=self.jobs[0], inherit=True)
        self.assertEqual('it', iw.show_job(self.root, self.cid, self.jobs[0])['interview_language'])
        prefs = json.loads((self.root / 'preferences.json').read_text())
        self.assertEqual({'schema_version': iw.SCHEMA, 'interface_language': 'de'}, prefs)

    def test_cli_exposes_candidate_and_job_choices_and_rejects_global_interview_flag(self):
        self.cli('set-interview-language', '--project', self.project, '--candidate', self.cid, '--language', 'fr-CA')
        self.cli('set-interview-language', '--project', self.project, '--candidate', self.cid,
                 '--job', self.jobs[0], '--language', 'en')
        result = self.cli('job-show', '--project', self.project, '--candidate', self.cid, '--job', self.jobs[0])
        self.assertEqual('en', json.loads(result.stdout)['interview_language'])
        self.cli('set-interview-language', '--project', self.project, '--candidate', self.cid,
                 '--job', self.jobs[0], '--inherit')
        before = snapshot(self.root)
        self.cli('set-language', '--project', self.project, '--interface', 'de', '--interview', 'en', expect=2)
        self.assertEqual(before, snapshot(self.root))

    def test_invalid_language_or_foreign_job_preserves_data(self):
        before = snapshot(self.root)
        for language in ('', '../en', 42):
            with self.assertRaises(ValueError):
                iw.set_interview_language(self.root, self.cid, language)
        with self.assertRaises(ValueError):
            iw.set_interview_language(self.root, self.cid, inherit=True)
        with self.assertRaises(ValueError):
            iw.set_interview_language(self.root, self.other, 'en', job_id=self.jobs[0])
        self.assertEqual(before, snapshot(self.root))

    def test_former_project_language_is_refused_without_migration(self):
        prefs = self.root / 'preferences.json'
        prefs.write_text(json.dumps({'schema_version': iw.SCHEMA, 'interface_language': 'de', 'interview_language': 'en'}))
        before = snapshot(self.root)
        with self.assertRaisesRegex(ValueError, 'project interview_language'):
            iw.set_interview_language(self.root, self.cid, 'fr')
        with self.assertRaisesRegex(ValueError, 'project interview_language'):
            iw.set_language(self.root, 'fr')
        self.assertEqual(before, snapshot(self.root))

    def test_records_without_language_field_are_refused_without_writes(self):
        for target in (self.cdir(self.cid) / 'candidate.json', self.cdir(self.cid) / 'jobs' / self.jobs[0] / 'job.json'):
            original = target.read_bytes()
            record = json.loads(original)
            del record['interview_language']
            target.write_text(json.dumps(record))
            before = snapshot(self.root)
            with self.assertRaisesRegex(ValueError, 'interview_language field required'):
                iw.set_interview_language(self.root, self.cid, 'en')
            self.assertEqual(before, snapshot(self.root))
            target.write_bytes(original)
