"""REQ-CV: byte-exact originals, real extraction, gaps disclosed, profile confirmation."""
import hashlib
import json
import os
import stat
import unittest

from tests.support.coach import Base, iw, extract, make_docx, make_pdf, snapshot


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CvImport(Base):
    def setUp(self):
        super().setUp()
        self.setup_local()
        self.cid = self.candidate()

    def source(self, cv_id='cv-001'):
        return self.cdir(self.cid) / 'cv' / cv_id

    def test_markdown_import_keeps_original_byte_exact_and_records_provenance(self):
        original = self.write('cv.md', '# Erika Beispiel\n\nBackend Engineer, ACME GmbH 2019-2024\n\näöü\r\n')
        result = iw.import_cv(self.root, self.cid, original)
        self.assertEqual('complete', result['extraction_status'])
        record = json.loads((self.source() / 'source.json').read_text())
        self.assertEqual(sha(original), sha(self.source() / 'original.md'))
        self.assertEqual(sha(original), record['original_sha256'])
        self.assertEqual(hashlib.sha256((self.source() / 'extracted.md').read_bytes()).hexdigest(), record['markdown_sha256'])
        self.assertEqual('cv.md', record['original_name'])
        self.assertEqual(['cv-001'], iw.read_candidate(self.cdir(self.cid))['cv_sources'])

    def test_docx_extraction_reads_real_content_structure_and_discloses_gaps(self):
        path = make_docx(self.base / 'cv.docx', ['Backend Engineer bei ACME', 'Python, Go'], headings=['Erfahrung'],
                         table=[['Skill', 'Level'], ['Python', 'Senior']], textbox='Zertifikat AWS', image=True, footer='Seite 1')
        result = iw.import_cv(self.root, self.cid, path)
        text = (self.source() / 'extracted.md').read_text()
        self.assertIn('# Erfahrung', text)
        self.assertIn('Backend Engineer bei ACME', text)
        self.assertIn('| Python | Senior |', text)
        self.assertEqual(1, text.count('Zertifikat AWS'), 'textbox fallback must not duplicate content')
        self.assertEqual('partial', result['extraction_status'])
        joined = ' '.join(result['warnings'])
        self.assertIn('image', joined)
        self.assertIn('footer1.xml', joined)
        self.assertEqual(sha(path), sha(self.source() / 'original.docx'))

    def test_clean_docx_is_complete(self):
        result = iw.import_cv(self.root, self.cid, make_docx(self.base / 'ok.docx', ['Nur Text']))
        self.assertEqual('complete', result['extraction_status'])

    def test_unreadable_files_rejected_before_any_write(self):
        bad = self.base / 'broken.docx'
        bad.write_bytes(b'not a zip')
        binary = self.base / 'latin.md'
        binary.write_bytes(b'\xff\xfe\x00bad')
        empty = self.base / 'empty.md'
        empty.write_bytes(b'')
        odd = self.write('cv.exe', 'x')
        before = snapshot(self.root)
        for path in (bad, binary, empty, odd, self.base / 'missing.pdf'):
            with self.assertRaises(ValueError, msg=str(path)):
                iw.import_cv(self.root, self.cid, path)
        self.assertEqual(before, snapshot(self.root))

    def test_doctype_in_docx_refused(self):
        import zipfile
        path = self.base / 'evil.docx'
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('word/document.xml', '<!DOCTYPE x [<!ENTITY a "b">]><w:document xmlns:w="x"/>')
        with self.assertRaisesRegex(ValueError, 'DTD'):
            iw.import_cv(self.root, self.cid, path)
        self.assertEqual([], iw.read_candidate(self.cdir(self.cid))['cv_sources'])

    def test_pdf_without_extraction_tool_reports_missing_capability_and_installs_nothing(self):
        pdf = make_pdf(self.base / 'cv.pdf')
        before = snapshot(self.root)
        with unittest.mock.patch.object(extract, '_pdf_tools', return_value=[]):
            with self.assertRaisesRegex(RuntimeError, 'none is available.*Nothing was installed'):
                iw.import_cv(self.root, self.cid, pdf)
        self.assertEqual(before, snapshot(self.root))

    def test_model_transcription_is_accepted_only_as_partial_when_tool_missing(self):
        pdf = make_pdf(self.base / 'cv.pdf')
        transcription = self.write('t.md', '# Erika\nTranskription durch das Modell\n')
        with unittest.mock.patch.object(extract, '_pdf_tools', return_value=[]):
            result = iw.import_cv(self.root, self.cid, pdf, transcription_file=transcription)
        self.assertEqual('partial', result['extraction_status'])
        self.assertEqual('agent-transcription', result['extractor'])
        self.assertEqual(sha(pdf), sha(self.source() / 'original.pdf'))

    def test_stubbed_tool_pipeline_only_exercises_plumbing_not_real_extraction(self):
        pdf = make_pdf(self.base / 'cv.pdf')
        which = lambda name: '/x/pdftotext' if name == 'pdftotext' else None
        run = lambda cmd, **kw: unittest.mock.Mock(returncode=0, stdout=b'Seite eins\n\f\f', stderr=b'')
        info = extract.extract(pdf, which=which, run=run)
        self.assertEqual('partial', info['status'])
        self.assertIn('Seite eins', info['markdown'])
        self.assertIn('Pages without extractable text: 2', info['warnings'][0])

    def require_pdf_tool(self):
        if not extract._pdf_tools():
            self.skipTest('NOT RUN: no PDF extraction tool (pdftotext, mutool, pypdf, macOS swift/PDFKit) is available; nothing was installed')

    def test_real_pdf_import_keeps_original_bytes_extracts_text_and_records_provenance(self):
        self.require_pdf_tool()
        pdf = make_pdf(self.base / 'cv.pdf', 'Erika Beispiel Backend Engineer')
        result = iw.import_cv(self.root, self.cid, pdf)
        record = json.loads((self.source() / 'source.json').read_text())
        self.assertEqual(sha(pdf), sha(self.source() / 'original.pdf'))
        self.assertEqual(sha(pdf), record['original_sha256'])
        self.assertIn('Erika Beispiel Backend Engineer', (self.source() / 'extracted.md').read_text())
        self.assertEqual('complete', result['extraction_status'])
        self.assertIn(record['extractor'], ('pdftotext', 'mutool', 'pypdf', 'pdfkit-swift'))
        self.assertNotEqual('agent-transcription', record['extractor'])
        self.assertEqual([], record['warnings'])

    def test_real_pdf_without_text_layer_is_never_reported_complete(self):
        self.require_pdf_tool()
        scan = make_pdf(self.base / 'scan.pdf', pages=[''])
        result = iw.import_cv(self.root, self.cid, scan)
        self.assertEqual('partial', result['extraction_status'])
        self.assertIn('No text layer', ' '.join(result['warnings']))
        self.assertEqual(sha(scan), sha(self.source() / 'original.pdf'))
        self.assertEqual('', (self.source() / 'extracted.md').read_text().strip())
        with self.assertRaisesRegex(ValueError, 'incomplete or unconfirmed'):
            iw.save_profile(self.root, self.cid, self.write('pr.md', 'x'), status='confirmed', origin='cv', cv_source='cv-001', user_confirmed=True)

    def test_real_pdf_with_a_blank_page_discloses_the_gap(self):
        self.require_pdf_tool()
        mixed = make_pdf(self.base / 'mixed.pdf', pages=['Seite eins Inhalt', '', 'Seite drei Inhalt'])
        result = iw.import_cv(self.root, self.cid, mixed)
        self.assertEqual('partial', result['extraction_status'])
        self.assertIn('Pages without extractable text: 2', ' '.join(result['warnings']))
        text = (self.source() / 'extracted.md').read_text()
        self.assertIn('Seite eins Inhalt', text)
        self.assertIn('Seite drei Inhalt', text)

    def test_corrupt_pdf_is_rejected_without_registering_anything(self):
        self.require_pdf_tool()
        broken = self.base / 'broken.pdf'
        broken.write_bytes(b'%PDF-1.4\nthis is not a pdf at all')
        before = snapshot(self.root)
        with self.assertRaises(ValueError):
            iw.import_cv(self.root, self.cid, broken)
        self.assertEqual(before, snapshot(self.root))

    def test_repeat_import_is_idempotent_and_changed_cv_is_kept_alongside(self):
        first = self.write('cv.md', '# v1\n')
        iw.import_cv(self.root, self.cid, first)
        again = iw.import_cv(self.root, self.cid, first)
        self.assertTrue(again['already_imported'])
        second = self.write('cv2.md', '# v2 other content\n')
        result = iw.import_cv(self.root, self.cid, second)
        self.assertEqual('cv-002', result['cv_source'])
        self.assertEqual('# v1\n', (self.source('cv-001') / 'extracted.md').read_text())
        self.assertEqual(['cv-001', 'cv-002'], iw.read_candidate(self.cdir(self.cid))['cv_sources'])

    def test_interrupted_import_staging_is_preserved_and_blocks_retry(self):
        self.write('cv.md', '# x\n')
        stage = self.cdir(self.cid) / '.journal' / 'stage-cv-001'
        stage.mkdir()
        (stage / 'half').write_text('partial')
        with self.assertRaisesRegex(RuntimeError, 'Interrupted import staging'):
            iw.import_cv(self.root, self.cid, self.base / 'cv.md')
        self.assertEqual('partial', (stage / 'half').read_text())
        self.assertEqual([], iw.read_candidate(self.cdir(self.cid))['cv_sources'])

    def test_failed_copy_verification_does_not_register_the_cv(self):
        path = self.write('cv.md', '# x\n')
        with unittest.mock.patch.object(iw.shutil, 'copyfile', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                iw.import_cv(self.root, self.cid, path)
        self.assertEqual([], iw.read_candidate(self.cdir(self.cid))['cv_sources'])
        self.assertFalse((self.cdir(self.cid) / 'cv/cv-001').exists())

    def test_import_into_other_candidate_does_not_touch_this_one(self):
        other = self.candidate('Max Muster')
        iw.import_cv(self.root, other, self.write('cv.md', '# Max\n'))
        self.assertEqual([], iw.read_candidate(self.cdir(self.cid))['cv_sources'])
        self.assertEqual(['cv-001'], iw.read_candidate(self.cdir(other))['cv_sources'])

    def test_symlinked_source_rejected(self):
        real = self.write('real.md', '# x\n')
        link = self.base / 'link.md'
        link.symlink_to(real)
        with self.assertRaisesRegex(ValueError, 'Not a regular readable file'):
            iw.import_cv(self.root, self.cid, link)


class ProfileFlow(Base):
    def setUp(self):
        super().setUp()
        self.setup_local()
        self.cid = self.candidate()

    def profile(self, text='# Profil\n- Python (Nutzerangabe)\n'):
        return self.write('profile.md', text)

    def test_new_candidate_profile_is_marked_missing(self):
        self.assertEqual('missing', iw.read_candidate(self.cdir(self.cid))['profile']['status'])
        self.assertIn('Status: missing', (self.cdir(self.cid) / 'profile.md').read_text())

    def test_interview_built_profile_stays_draft_until_user_confirms(self):
        draft = iw.save_cv_draft(self.root, self.cid, self.write('draft.md', '# CV-Entwurf\nNur Nutzerangaben\n'))
        self.assertEqual('draft_unconfirmed', draft['status'])
        iw.save_profile(self.root, self.cid, self.profile(), status='draft', origin='interview', cv_source='cv-001')
        self.assertEqual('draft', iw.read_candidate(self.cdir(self.cid))['profile']['status'])
        with self.assertRaisesRegex(ValueError, 'only after the user confirmed'):
            iw.save_profile(self.root, self.cid, self.profile(), status='confirmed', origin='interview', cv_source='cv-001')
        with self.assertRaisesRegex(ValueError, 'incomplete or unconfirmed'):
            iw.save_profile(self.root, self.cid, self.profile(), status='confirmed', origin='interview', cv_source='cv-001', user_confirmed=True)
        iw.save_profile(self.root, self.cid, self.profile(), status='confirmed', origin='interview', cv_source='cv-001',
                        user_confirmed=True, acknowledge_gaps=True)
        self.assertEqual('confirmed', iw.read_candidate(self.cdir(self.cid))['profile']['status'])

    def test_complete_cv_allows_confirmation_and_history_keeps_previous_profile(self):
        iw.import_cv(self.root, self.cid, self.write('cv.md', '# Erika\n'))
        iw.save_profile(self.root, self.cid, self.profile('v1'), status='draft', origin='cv', cv_source='cv-001')
        iw.save_profile(self.root, self.cid, self.profile('v2'), status='confirmed', origin='cv', cv_source='cv-001', user_confirmed=True)
        history = self.cdir(self.cid) / 'profile-history'
        self.assertIn('Status: missing', (history / '001.md').read_text())
        self.assertEqual('v1', (history / '002.md').read_text())
        self.assertEqual('v2', (self.cdir(self.cid) / 'profile.md').read_text())

    def test_foreign_cv_source_rejected_without_writes(self):
        other = self.candidate('Max Muster')
        iw.import_cv(self.root, other, self.write('cv.md', '# Max\n'))
        before = snapshot(self.root)
        with self.assertRaisesRegex(ValueError, 'does not belong'):
            iw.save_profile(self.root, self.cid, self.profile(), status='draft', origin='cv', cv_source='cv-001')
        self.assertEqual(before, snapshot(self.root))

    def test_cv_origin_requires_cv_source(self):
        with self.assertRaisesRegex(ValueError, 'requires a CV source'):
            iw.save_profile(self.root, self.cid, self.profile(), status='draft', origin='cv')


class ProfileReliability(Base):
    """Finding D: a draft is shown/saved but is not evidence for personal comparison."""

    def setUp(self):
        super().setUp()
        self.setup_local()
        self.cid = self.candidate()
        self.job = iw.create_job(self.root, self.cid, 'Engineer', 'ACME', posting_text_file=self.write('p.md', 'Posting'))['job_id']

    def match(self):
        with iw.candidate_lock(self.root, self.cid) as cdir:
            return iw.add_artifact(cdir, iw.job_dir(cdir, self.job), 'match', 'Anforderung A: direkt belegt')

    def test_missing_and_draft_profiles_do_not_unlock_personal_comparison(self):
        self.assertFalse(iw.snapshot(self.root, self.cid)['profile_reliable'])
        with self.assertRaisesRegex(ValueError, 'confirmed profile \\(current: missing\\)'):
            self.match()
        iw.save_cv_draft(self.root, self.cid, self.write('d.md', '# CV-Entwurf\n'))
        iw.save_profile(self.root, self.cid, self.write('pr.md', '- Python [Quelle: Nutzerangabe]\n'), status='draft', origin='interview', cv_source='cv-001')
        snapshot_ = iw.snapshot(self.root, self.cid)
        self.assertEqual('draft', snapshot_['candidate']['profile']['status'])
        self.assertFalse(snapshot_['profile_reliable'])
        with self.assertRaisesRegex(ValueError, 'confirmed profile \\(current: draft\\)'):
            self.match()
        self.assertEqual([], list((self.cdir(self.cid) / 'jobs' / self.job / 'match').iterdir()))

    def test_independent_work_stays_possible_with_a_draft(self):
        with iw.candidate_lock(self.root, self.cid) as cdir:
            jdir = iw.job_dir(cdir, self.job)
            iw.add_artifact(cdir, jdir, 'research', 'Fakt', sources=['https://example.invalid/a'], retrieved_at='2026-11-19')
            iw.add_artifact(cdir, jdir, 'preparation', 'Themen')
        iw.update_job(self.root, self.cid, self.job, participants_status='unknown')
        self.finish(self.cid, 'general-1')

    def test_confirmation_unlocks_the_comparison_and_no_silent_upgrade_happens(self):
        iw.import_cv(self.root, self.cid, self.write('cv.md', '# Erika\n'))
        iw.save_profile(self.root, self.cid, self.write('pr.md', '- Python [Quelle: CV]\n'), status='draft', origin='cv', cv_source='cv-001')
        with self.assertRaises(ValueError):
            self.match()
        with self.assertRaisesRegex(ValueError, 'only after the user confirmed'):
            iw.save_profile(self.root, self.cid, self.write('pr.md', 'x'), status='confirmed', origin='cv', cv_source='cv-001')
        self.assertEqual('draft', iw.read_candidate(self.cdir(self.cid))['profile']['status'])
        iw.save_profile(self.root, self.cid, self.write('pr.md', '- Python [Quelle: CV]\n'), status='confirmed', origin='cv', cv_source='cv-001', user_confirmed=True)
        self.assertTrue(iw.snapshot(self.root, self.cid)['profile_reliable'])
        self.assertEqual(1, self.match()['seq'])

    def test_resaving_a_changed_profile_as_draft_downgrades_reliability(self):
        iw.import_cv(self.root, self.cid, self.write('cv.md', '# Erika\n'))
        iw.save_profile(self.root, self.cid, self.write('a.md', 'v1'), status='confirmed', origin='cv', cv_source='cv-001', user_confirmed=True)
        iw.save_profile(self.root, self.cid, self.write('b.md', 'v2 edited by model'), status='draft', origin='cv', cv_source='cv-001')
        self.assertFalse(iw.snapshot(self.root, self.cid)['profile_reliable'])
        self.assertEqual('v1', (self.cdir(self.cid) / 'profile-history/002.md').read_text())

    def test_origin_of_statements_stays_recorded(self):
        iw.save_cv_draft(self.root, self.cid, self.write('d.md', '# Entwurf\n'))
        iw.save_profile(self.root, self.cid, self.write('pr.md', '- A [Quelle: Nutzerangabe]\n- B [Quelle: Modellvorschlag]\n'), status='draft', origin='interview', cv_source='cv-001')
        record = iw.read_candidate(self.cdir(self.cid))['profile']
        self.assertEqual(('draft', 'interview', 'cv-001'), (record['status'], record['origin'], record['cv_source']))
        source = json.loads((self.cdir(self.cid) / 'cv/cv-001/source.json').read_text())
        self.assertEqual(('draft', 'draft_unconfirmed'), (source['kind'], source['extraction_status']))
        text = (self.cdir(self.cid) / 'profile.md').read_text()
        self.assertIn('[Quelle: Nutzerangabe]', text)
        self.assertIn('[Quelle: Modellvorschlag]', text)


if __name__ == '__main__':
    unittest.main()
