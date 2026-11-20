"""REQ-HOST/PRJ/CAN: project resolution, multiple candidates, safe paths, format rejection, no-storage."""
import json
import os
from pathlib import Path
import stat
import unittest
from unittest import mock

from tests.support.coach import Base, iw, snapshot, core


class ProjectResolution(Base):
    def test_two_projects_resolve_independently_without_switching_each_other(self):
        other_project = self.base / 'project-two'
        other_project.mkdir()
        self.setup_local()
        iw.setup_project(other_project, 'local', self.base / 'ws-two', config_dir=self.cfg)
        root_one, _ = iw.project_workspace(self.project, self.cfg)
        root_two, _ = iw.project_workspace(other_project, self.cfg)
        self.assertNotEqual(root_one, root_two)
        iw.create_candidate(root_one, 'Erika Beispiel')
        self.assertEqual([], iw.list_candidates(root_two))
        self.assertEqual(1, len(iw.list_candidates(root_one)))

    def test_unconfigured_project_fails_without_searching_other_pointers(self):
        self.setup_local()
        other = self.base / 'unconfigured'
        other.mkdir()
        with self.assertRaisesRegex(FileNotFoundError, 'No storage configured'):
            iw.project_workspace(other, self.cfg)
        # a legacy-style global pointer is never consulted
        (self.cfg / 'config.json').write_text(json.dumps({'schema_version': 1, 'workspace': str(self.root), 'storage': 'local'}))
        with self.assertRaises(FileNotFoundError):
            iw.project_workspace(other, self.cfg)

    def test_switching_target_requires_explicit_confirmation_and_keeps_old_data(self):
        self.setup_local()
        iw.create_candidate(self.root, 'Erika Beispiel')
        before = snapshot(self.root)
        with self.assertRaisesRegex(ValueError, 'another storage target'):
            iw.setup_project(self.project, 'local', self.base / 'elsewhere', config_dir=self.cfg)
        self.assertEqual(before, snapshot(self.root))
        iw.setup_project(self.project, 'local', self.base / 'elsewhere', config_dir=self.cfg, switch=True)
        self.assertEqual(before, snapshot(self.root))

    def test_unconfirmed_switch_is_decided_before_any_mutation(self):
        self.setup_local()
        pointer = next(self.cfg.glob('*.json'))
        pointer_before, ws_before = pointer.read_bytes(), snapshot(self.root)
        new_target = self.base / 'new-target'
        with self.assertRaisesRegex(ValueError, 'another storage target or type'):
            iw.setup_project(self.project, 'local', new_target, config_dir=self.cfg)
        self.assertFalse(new_target.exists(), 'no new target directory')
        self.assertEqual(pointer_before, pointer.read_bytes())
        self.assertEqual(ws_before, snapshot(self.root))

    def test_invalid_existing_pointer_is_rejected_before_creating_a_target(self):
        self.cfg.mkdir()
        iw.project_config_path(self.project, self.cfg).write_text('not json')
        with self.assertRaises(ValueError):
            iw.setup_project(self.project, 'local', self.root, config_dir=self.cfg)
        self.assertFalse(self.root.exists())

    def test_same_target_and_type_is_a_confirmed_reuse_without_switch(self):
        self.setup_local()
        self.setup_local()  # idempotent

    def test_reuse_of_valid_workspace_is_reported_and_preserves_data(self):
        self.setup_local()
        cid = self.candidate()
        before = snapshot(self.root)
        again = self.setup_local()
        self.assertEqual(before, snapshot(self.root))
        self.assertEqual([cid], [c['candidate_id'] for c in iw.list_candidates(self.root)])
        self.assertEqual(str(self.root), again['workspace'])

    def test_project_folder_is_only_a_suggestion_explicit_path_required(self):
        with self.assertRaisesRegex(ValueError, 'explicit storage path'):
            iw.setup_project(self.project, 'local', None, config_dir=self.cfg)
        self.assertEqual({}, snapshot(self.project))

    def test_missing_project_folder_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Project folder does not exist'):
            iw.setup_project(self.base / 'nope', 'local', self.root, config_dir=self.cfg)
        self.assertFalse(self.root.exists())

    def test_config_inside_workspace_rejected(self):
        with self.assertRaisesRegex(ValueError, 'outside the workspace'):
            iw.setup_project(self.project, 'local', self.root, config_dir=self.root / 'cfg')

    def test_unwritable_directory_reports_permission_before_creating_files(self):
        target = self.base / 'readonly'
        target.mkdir()
        target.chmod(stat.S_IRUSR | stat.S_IXUSR)
        self.addCleanup(target.chmod, 0o700)
        if os.access(target, os.W_OK):
            self.skipTest('permissions not enforced for this user')
        with self.assertRaises(PermissionError):
            iw.setup_project(self.project, 'local', target, config_dir=self.cfg)
        self.assertEqual([], list(target.iterdir()))


class FormatRejection(Base):
    def test_legacy_format1_workspace_rejected_and_untouched(self):
        self.root.mkdir()
        (self.root / 'state.md').write_text('legacy state')
        (self.root / 'candidate').mkdir()
        (self.root / 'candidate/profile.md').write_text('legacy profile')
        (self.root / 'runs').mkdir()
        before = snapshot(self.root)
        with self.assertRaisesRegex(ValueError, 'Unsupported workspace format .*legacy'):
            iw.setup_project(self.project, 'local', self.root, config_dir=self.cfg)
        self.assertEqual(before, snapshot(self.root))
        self.assertFalse(self.cfg.exists())

    def test_unrelated_non_empty_directory_rejected(self):
        self.root.mkdir()
        (self.root / 'notes.txt').write_text('mine')
        before = snapshot(self.root)
        with self.assertRaises(ValueError):
            iw.setup_project(self.project, 'local', self.root, config_dir=self.cfg)
        self.assertEqual(before, snapshot(self.root))

    def test_wrong_schema_version_blocks_writes(self):
        self.setup_local()
        manifest = self.root / 'workspace.json'
        data = json.loads(manifest.read_text())
        data['schema_version'] = 1
        manifest.write_text(json.dumps(data))
        before = snapshot(self.root)
        with self.assertRaisesRegex(ValueError, 'Unsupported workspace manifest'):
            iw.create_candidate(self.root, 'Erika Beispiel')
        self.assertEqual(before, snapshot(self.root))

    def test_duplicate_json_keys_rejected_before_writes(self):
        self.setup_local()
        cid = self.candidate()
        meta = self.cdir(cid) / 'candidate.json'
        meta.write_text('{"schema_version":2,"schema_version":2}')
        before = snapshot(self.root)
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON field'):
            self.finish(cid, 'run-1')
        self.assertEqual(before, snapshot(self.root))

    def test_format1_run_record_blocks_candidate_operations_and_is_preserved(self):
        self.setup_local()
        cid = self.candidate()
        old = self.cdir(cid) / 'runs/old.md'
        old.write_text('<!-- zyris-run: {"schema_version":1,"run_id":"old"} -->\nold')
        before = snapshot(self.root)
        with self.assertRaisesRegex(ValueError, 'Unsupported run old.md'):
            self.finish(cid, 'new-run', expected_state_sha256='0' * 64)
        self.assertEqual(before, snapshot(self.root))


class CandidateIdentity(Base):
    def setUp(self):
        super().setUp()
        self.setup_local()

    def test_same_names_get_distinct_stable_ids_and_need_disambiguation(self):
        first, second = self.candidate('Erika Beispiel'), self.candidate('Erika Beispiel')
        self.assertNotEqual(first, second)
        listing = iw.list_candidates(self.root)
        self.assertTrue(all(c['name_is_ambiguous'] for c in listing))
        with self.assertRaises(LookupError) as raised:
            iw.resolve_candidate(self.root, name='erika beispiel')
        self.assertIn('ambiguous', raised.exception.args[0])
        self.assertEqual(first, iw.resolve_candidate(self.root, candidate_id=first)['candidate_id'])
        self.assertEqual(iw.list_candidates(self.root), iw.list_candidates(self.root))

    def test_unique_name_resolves_and_unknown_does_not(self):
        cid = self.candidate('Zoë Müller')
        self.assertEqual(cid, iw.resolve_candidate(self.root, name='zoë müller')['candidate_id'])
        with self.assertRaises(LookupError):
            iw.resolve_candidate(self.root, name='Niemand')

    def test_hostile_names_never_become_paths(self):
        for name in ('../../etc/passwd', '/abs/path', 'a\\b', '..'):
            cid = self.candidate(name)
            self.assertRegex(cid, r'^c-[a-z0-9-]+-[0-9a-f]{8}$')
            self.assertTrue(self.cdir(cid).is_dir())
            self.assertEqual(name, iw.read_candidate(self.cdir(cid))['display_name'])
        self.assertEqual([], [p for p in self.base.iterdir() if p.name in ('passwd', 'etc')])
        for bad in ('', '   ', 'a\x00b', 'x\ny', 'n' * 300):
            with self.assertRaises(ValueError):
                iw.create_candidate(self.root, bad)

    def test_foreign_or_traversal_ids_rejected(self):
        for bad in ('../x', 'c-x', '', 'c-a-12345678/../..', 'C-UPPER-12345678'):
            with self.assertRaises(ValueError):
                iw.snapshot(self.root, bad)

    def test_symlinked_candidate_directory_rejected(self):
        cid = self.candidate()
        outside = self.base / 'outside'
        outside.mkdir()
        link = self.root / 'candidates' / 'c-link-12345678'
        link.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'symlink|symbolic link'):
            iw.snapshot(self.root, 'c-link-12345678')
        self.assertTrue(self.cdir(cid).is_dir())
        self.assertEqual([], list(outside.iterdir()))

    def test_interrupted_creation_leaves_unusable_draft_and_can_be_recovered(self):
        with mock.patch.object(iw, 'materialize_candidate', side_effect=OSError('disk full')):
            with self.assertRaisesRegex(RuntimeError, 'Candidate creation incomplete'):
                iw.create_candidate(self.root, 'Erika Beispiel')
        (draft,) = [c for c in (self.root / 'candidates').iterdir() if not c.name.startswith('.')]
        self.assertEqual('creating', iw.read_candidate(draft)['status'])
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            iw.snapshot(self.root, draft.name)
        self.assertTrue(any('incomplete' in p for p in iw.workspace_problems(self.root)))
        (draft / 'profile.md').write_text('user content that must survive')
        recovered = iw.recover_candidate(self.root, draft.name)
        self.assertEqual('active', recovered['status'])
        self.assertEqual('user content that must survive', (draft / 'profile.md').read_text())
        self.assertEqual([], iw.workspace_problems(self.root))

    def test_candidates_have_independent_learning_state(self):
        a, b = self.candidate('Erika Beispiel'), self.candidate('Max Muster')
        self.finish(a, 'run-a', state_text='# State A: strong on structure\n')
        self.assertIn('State A', iw.snapshot(self.root, a)['state'])
        self.assertNotIn('State A', iw.snapshot(self.root, b)['state'])
        self.assertEqual([], iw.snapshot(self.root, b)['runs'])


class NoStorageMode(Base):
    def test_none_is_refused_and_creates_nothing(self):
        for path in (None, self.root):
            with self.assertRaisesRegex(ValueError, 'Nicht speichern'):
                iw.setup_project(self.project, 'none', path, config_dir=self.cfg)
        self.assertFalse(self.root.exists())
        self.assertFalse(self.cfg.exists())
        self.assertEqual({}, snapshot(self.project))
        self.cli('project-init', '--project', self.project, '--storage', 'none', expect=1)


class Locking(Base):
    def test_busy_candidate_fails_immediately_and_does_not_block_other_candidate(self):
        self.setup_local()
        a, b = self.candidate('A'), self.candidate('B')
        with iw.candidate_lock(self.root, a):
            with self.assertRaisesRegex(RuntimeError, 'busy'):
                iw.snapshot(self.root, a)
            self.assertIn('state', iw.snapshot(self.root, b))


class JournalFolderAndLegacyLayout(Base):
    """Format 3 uses `.journal`; the old `.zyris` layout is only ever refused (no migration, no reading, no touching)."""

    def old_workspace(self, *, schema=2, workspace_marker=True, candidate_marker=True):
        self.root.mkdir()
        (self.root / 'workspace.json').write_text(json.dumps({'format': 'interview-coach-workspace', 'schema_version': schema, 'created_at': '2026-01-01T00:00:00Z'}))
        (self.root / 'preferences.json').write_text(json.dumps({'schema_version': schema}))
        candidate = self.root / 'candidates' / 'c-erika-beispiel-12345678'
        candidate.mkdir(parents=True)
        (candidate / 'candidate.json').write_text('{"fictional": "old candidate"}')
        if workspace_marker:
            (self.root / '.zyris').mkdir()
            (self.root / '.zyris' / 'lock').write_text('')
        if candidate_marker:
            (candidate / '.zyris').mkdir()
            (candidate / '.zyris' / 'pending.json').write_text('{"secret": "fictional training answer in an old journal"}')
        return candidate

    def assert_refused_untouched(self, call):
        before = snapshot(self.root)
        with self.assertRaisesRegex(ValueError, 'Unsupported old control layout|Unsupported workspace manifest'):
            call()
        self.assertEqual(before, snapshot(self.root))
        self.assertFalse(self.cfg.exists(), 'no pointer, lock or configuration was created')
        self.assertFalse(list(self.root.rglob('.journal')), 'no new control folder was created')

    def test_new_workspace_uses_only_the_journal_folder(self):
        self.setup_local()
        cid = self.candidate()
        self.assertTrue((self.root / '.journal' / 'lock').is_file())
        self.assertTrue((self.cdir(cid) / '.journal').is_dir())
        self.assertEqual([], list(self.root.rglob('.zyris')))
        self.assertEqual('.journal/\n', (self.root / '.gitignore').read_text())
        self.assertEqual(3, json.loads((self.root / 'workspace.json').read_text())['schema_version'])
        self.assertNotIn('.zyris', (self.root / 'README.md').read_text() + (self.root / '.gitignore').read_text())

    def test_old_workspace_with_workspace_and_candidate_markers_is_refused_without_any_change(self):
        candidate = self.old_workspace()
        old_journal = (candidate / '.zyris' / 'pending.json').read_bytes()
        self.assert_refused_untouched(lambda: iw.setup_project(self.project, 'local', self.root, config_dir=self.cfg))
        self.assert_refused_untouched(lambda: iw.create_candidate(self.root, 'Max Muster'))
        self.assert_refused_untouched(lambda: iw.recover(self.root, 'c-erika-beispiel-12345678'))
        self.assert_refused_untouched(lambda: iw.list_candidates(self.root))
        self.assertEqual(old_journal, (candidate / '.zyris' / 'pending.json').read_bytes(), 'old journal neither read for resumption nor altered')
        done = self.cli('validate', '--path', self.root, expect=1)
        self.assertIn('Unsupported old control layout', done.stdout + done.stderr)
        self.assertIn('new, empty storage location', done.stdout + done.stderr)

    def test_candidate_level_marker_alone_is_enough_to_refuse(self):
        self.old_workspace(workspace_marker=False)
        self.assert_refused_untouched(lambda: iw.setup_project(self.project, 'local', self.root, config_dir=self.cfg))

    def test_mixed_layout_with_zyris_and_journal_is_refused(self):
        self.setup_local()
        cid = self.candidate()
        (self.root / '.zyris').mkdir()
        (self.root / '.zyris' / 'pending.json').write_text('old')
        before = snapshot(self.root)
        for call in (lambda: iw.create_candidate(self.root, 'Max Muster'), lambda: iw.snapshot(self.root, cid),
                     lambda: iw.setup_project(self.project, 'local', self.root, config_dir=self.cfg)):
            with self.assertRaisesRegex(ValueError, 'Unsupported old control layout'):
                call()
        self.assertEqual(before, snapshot(self.root))
        (self.root / '.zyris').rename(self.root / 'moved-away')       # (the test itself moves it; the tool never does)
        (self.cdir(cid) / '.zyris').write_text('candidate-level marker as a plain file')
        with self.assertRaisesRegex(ValueError, 'Unsupported old control layout'):
            iw.snapshot(self.root, cid)
        self.assertEqual('candidate-level marker as a plain file', (self.cdir(cid) / '.zyris').read_text())

    def test_old_marker_as_file_or_symlink_is_refused_and_never_followed(self):
        outside = self.base / 'outside'
        outside.mkdir()
        (outside / 'keep.txt').write_text('fictional')
        for kind in ('file', 'symlink', 'dangling'):
            root = self.base / f'ws-{kind}'
            root.mkdir()
            marker = root / '.zyris'
            if kind == 'file':
                marker.write_text('old marker file')
            elif kind == 'symlink':
                marker.symlink_to(outside, target_is_directory=True)
            else:
                marker.symlink_to(self.base / 'does-not-exist')
            before = snapshot(root)
            with self.assertRaisesRegex(ValueError, 'Unsupported old control layout'):
                iw.setup_project(self.project, 'local', root, config_dir=self.cfg)
            self.assertEqual(before, snapshot(root), kind)
            self.assertTrue(marker.is_symlink() or marker.is_file(), kind)
        self.assertEqual(['keep.txt'], [p.name for p in outside.iterdir()], 'a symlinked marker target was not written to')
        self.assertFalse(self.cfg.exists())

    def test_format_2_metadata_without_any_marker_is_not_accepted_silently(self):
        self.old_workspace(workspace_marker=False, candidate_marker=False)
        self.assert_refused_untouched(lambda: iw.setup_project(self.project, 'local', self.root, config_dir=self.cfg))
        self.assert_refused_untouched(lambda: iw.create_candidate(self.root, 'Max Muster'))

    def test_pointer_of_the_previous_format_is_not_read(self):
        self.cfg.mkdir()
        pointer = iw.project_config_path(self.project, self.cfg)
        pointer.write_text(json.dumps({'schema_version': 2, 'project': str(self.project), 'storage': 'local', 'workspace': str(self.root)}))
        with self.assertRaisesRegex(ValueError, 'Unsupported project configuration'):
            iw.read_project_config(self.project, self.cfg)

    def test_no_storage_never_creates_a_control_folder(self):
        with self.assertRaisesRegex(ValueError, 'Nicht speichern'):
            iw.setup_project(self.project, 'none', self.root, config_dir=self.cfg)
        self.assertEqual([], list(self.base.rglob('.journal')) + list(self.base.rglob('.zyris')))


class SymlinkedCandidateDirectories(Base):
    """The layout scan never follows links: no path below a symlinked entry is inspected (proved by instrumentation)."""

    def setUp(self):
        super().setUp()
        self.setup_local()
        self.external = self.base / 'external'
        (self.external / '.zyris').mkdir(parents=True)                 # a trap: would be found if the link were followed
        (self.external / '.zyris' / 'trap.json').write_text('fictional outside data')
        (self.external / 'notes.txt').write_text('fictional')

    def spied_scan(self, call):
        inspected = []
        real = iw.os.path.lexists

        def spy(path):
            inspected.append(str(path))
            return real(path)
        with mock.patch.object(iw.os.path, 'lexists', side_effect=spy):
            with self.assertRaisesRegex(ValueError, 'Unsafe layout.*symbolic link'):
                call()
        return inspected

    def assert_nothing_followed(self, inspected, link):
        self.assertFalse([p for p in inspected if p.startswith(str(link) + os.sep) or str(self.external) in p],
                         'no path below the link or in the external target was inspected')

    def test_symlinked_candidate_to_an_external_directory_is_refused_without_looking_below_it(self):
        link = self.root / 'candidates' / 'c-erika-beispiel-12345678'
        link.symlink_to(self.external, target_is_directory=True)
        before, outside = snapshot(self.root), snapshot(self.external)
        for call in (lambda: iw.create_candidate(self.root, 'Max Muster'), lambda: iw.list_candidates(self.root),
                     lambda: iw.setup_project(self.project, 'local', self.root, config_dir=self.cfg)):
            inspected = self.spied_scan(call)
            self.assertTrue(any(p == str(self.root / '.zyris') for p in inspected), 'the scan did run (workspace-level marker probe)')
            self.assert_nothing_followed(inspected, link)
        self.assertEqual(before, snapshot(self.root))
        self.assertEqual(outside, snapshot(self.external), 'external test data untouched')
        self.assertFalse(list(self.external.rglob('.journal')))

    def test_dangling_candidate_symlink_is_refused_safely(self):
        link = self.root / 'candidates' / 'c-erika-beispiel-12345678'
        link.symlink_to(self.base / 'does-not-exist')
        before = snapshot(self.root)
        inspected = self.spied_scan(lambda: iw.create_candidate(self.root, 'Max Muster'))
        self.assert_nothing_followed(inspected, link)
        self.assertEqual(before, snapshot(self.root))
        self.assertTrue(link.is_symlink())

    def test_symlinked_candidates_folder_itself_is_refused(self):
        folder = self.root / 'candidates'
        moved = self.base / 'real-candidates'
        folder.rename(moved)                              # test setup only
        folder.symlink_to(moved, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Unsafe layout.*candidates \\(symbolic link\\)'):
            iw.create_candidate(self.root, 'Max Muster')

    def test_regular_candidate_with_an_old_marker_is_still_detected_and_a_current_workspace_stays_valid(self):
        cid = self.candidate()
        self.assertEqual(([], []), iw.scan_layout(self.root))
        self.assertEqual([], iw.workspace_problems(self.root))
        (self.cdir(cid) / '.zyris').write_text('old marker')
        self.assertEqual(([f'candidates/{cid}/.zyris'], []), iw.scan_layout(self.root))
        with self.assertRaisesRegex(ValueError, 'Unsupported old control layout'):
            iw.snapshot(self.root, cid)

    def test_workspace_level_marker_kinds_are_still_detected(self):
        for kind in ('dir', 'file', 'symlink', 'dangling'):
            root = self.base / f'w-{kind}'
            root.mkdir()
            marker = root / '.zyris'
            {'dir': marker.mkdir, 'file': lambda: marker.write_text('x'),
             'symlink': lambda: marker.symlink_to(self.external, target_is_directory=True),
             'dangling': lambda: marker.symlink_to(self.base / 'nope')}[kind]()
            self.assertEqual((['.zyris'], []), iw.scan_layout(root), kind)

    def test_uninspectable_candidate_directory_is_an_error_not_no_marker(self):
        with mock.patch.object(iw.os, 'scandir', side_effect=PermissionError('denied')):
            with self.assertRaisesRegex(ValueError, 'Cannot inspect the candidate directories'):
                iw.scan_layout(self.root)
            self.assertTrue(any('Cannot inspect' in p for p in iw.workspace_problems(self.root)))


if __name__ == '__main__':
    unittest.main()
