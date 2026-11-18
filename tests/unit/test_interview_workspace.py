import json
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
import sys
import subprocess
import os
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills/zyris-interview-coach/scripts"))
import interview_workspace as workspace
from interview_workspace import init_workspace, configured_root, validate, finish, set_language

class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.cfg = self.base / "config.json"
        self.root = self.base / "workspace"

    def test_init_is_idempotent_and_does_not_overwrite(self):
        init_workspace(self.root, self.cfg)
        (self.root / "state.md").write_text("my state")
        init_workspace(self.root, self.cfg)
        self.assertEqual((self.root / "state.md").read_text(), "my state")
        self.assertEqual(configured_root(self.cfg), self.root.resolve())
        self.assertEqual(validate(self.root), [])

    def test_switch_requires_explicit_force(self):
        init_workspace(self.root, self.cfg)
        with self.assertRaises(ValueError):
            init_workspace(self.base / "other", self.cfg)
        init_workspace(self.base / "other", self.cfg, force=True)
        self.assertEqual(configured_root(self.cfg), (self.base / "other").resolve())

    def test_finish_writes_both_and_never_overwrites_run(self):
        init_workspace(self.root, self.cfg)
        finish(self.root, "2026-11-17-demo", "# Answer A", "# State B", expected_state_sha256=workspace.state_digest(self.root))
        self.assertEqual((self.root / "state.md").read_text(), "# State B")
        with self.assertRaises(FileExistsError):
            finish(self.root, "2026-11-17-demo", "# Answer C", "# State C", expected_state_sha256=workspace.state_digest(self.root))
        self.assertEqual((self.root / "state.md").read_text(), "# State B")

    def test_path_traversal_rejected(self):
        init_workspace(self.root, self.cfg)
        for bad in ("../outside", "/tmp/foo", "a/b", ".."):
            with self.assertRaises(ValueError):
                finish(self.root, bad, "run", "state", expected_state_sha256=workspace.state_digest(self.root))

    def test_language_preferences_are_explicit_and_persistent(self):
        init_workspace(self.root, self.cfg)
        prefs = self.root / "preferences.json"
        self.assertFalse(prefs.exists(), "No language should be assumed")
        set_language(self.root, "de", "en")
        self.assertEqual(json.loads(prefs.read_text())["interface_language"], "de")
        self.assertEqual(json.loads(prefs.read_text())["interview_language"], "en")
        set_language(self.root, "fr")
        self.assertEqual(json.loads(prefs.read_text())["interview_language"], "en")
        with self.assertRaises(ValueError):
            set_language(self.root, "../invalid")

    def test_missing_files_reported(self):
        self.root.mkdir()
        self.assertTrue(validate(self.root))


    def prepare(self):
        init_workspace(self.root, self.cfg)
        (self.root / 'candidate/profile.md').write_text('Fictional Alex; no real candidate data')
        return workspace.snapshot(self.root)['state_sha256']

    def save(self, run_id='test', **kwargs):
        return finish(self.root, run_id, 'Fictional answer', '# New state',
                      expected_state_sha256=self.digest, **kwargs)

    def test_stale_state_rejected_without_creating_run(self):
        self.digest = self.prepare()
        self.save('first')
        with self.assertRaisesRegex(ValueError, 'Stale state'):
            self.save('second')
        self.assertFalse((self.root / 'runs/second.md').exists())
        self.assertEqual((self.root / 'state.md').read_text(), '# New state')

    def test_faults_before_each_publication_are_recoverable(self):
        for target in ('pending.json', 'test.md', 'state.md'):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / 'workspace'
                init_workspace(root, Path(directory) / 'config.json')
                old = (root / 'state.md').read_bytes()
                original = workspace.write_atomic
                def fail(path, content, **kwargs):
                    if path.name == target:
                        raise OSError('injected disk error')
                    return original(path, content, **kwargs)
                with patch.object(workspace, 'write_atomic', side_effect=fail):
                    with self.assertRaisesRegex(RuntimeError, 'do not claim success'):
                        finish(root, 'test', 'fictional answer', 'new state',
                               expected_state_sha256=workspace.state_digest(root))
                self.assertEqual((root / 'state.md').read_bytes(), old)
                if target == 'pending.json':
                    self.assertIsNone(workspace.recover(root))
                    self.assertFalse((root / 'runs/test.md').exists())
                else:
                    with self.assertRaisesRegex(RuntimeError, 'Pending transaction'):
                        workspace.snapshot(root)
                    self.assertEqual(workspace.recover(root), root.resolve() / 'runs/test.md')
                    self.assertEqual((root / 'state.md').read_text(), 'new state')
                    self.assertIsNone(workspace.recover(root))

    def test_failure_after_state_publication_is_idempotently_recoverable(self):
        self.digest = self.prepare()
        original = workspace.write_atomic
        def fail_after(path, content, **kwargs):
            original(path, content, **kwargs)
            if path.name == 'state.md':
                raise OSError('injected sync failure after publication')
        with patch.object(workspace, 'write_atomic', side_effect=fail_after):
            with self.assertRaises(RuntimeError):
                self.save()
        immutable = (self.root / 'runs/test.md').read_bytes()
        workspace.recover(self.root)
        self.assertEqual((self.root / 'runs/test.md').read_bytes(), immutable)
        self.assertEqual((self.root / 'state.md').read_text(), '# New state')

    def test_journal_cleanup_failure_does_not_report_success(self):
        self.digest = self.prepare()
        original = Path.unlink
        def fail_pending(path, *args, **kwargs):
            if path.name == 'pending.json':
                raise OSError('injected cleanup failure')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'unlink', fail_pending):
            with self.assertRaises(RuntimeError):
                self.save()
        workspace.recover(self.root)
        self.assertFalse(workspace.journal_path(self.root).exists())

    def test_recovery_refuses_external_state_or_run_conflict(self):
        for conflict in ('state.md', 'runs/test.md'):
            with self.subTest(conflict=conflict), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / 'workspace'
                init_workspace(root, Path(directory) / 'config.json')
                original = workspace.write_atomic
                def fail(path, content, **kwargs):
                    if path.name == 'state.md':
                        raise OSError('injected failure')
                    return original(path, content, **kwargs)
                with patch.object(workspace, 'write_atomic', side_effect=fail):
                    with self.assertRaises(RuntimeError):
                        finish(root, 'test', 'fictional answer', 'new state',
                               expected_state_sha256=workspace.state_digest(root))
                (root / conflict).write_text('External edit must survive')
                before = {p: p.read_bytes() for p in (root / 'state.md', root / 'runs/test.md')}
                with self.assertRaisesRegex(ValueError, 'manual reconciliation'):
                    workspace.recover(root)
                self.assertEqual(before, {p: p.read_bytes() for p in before})
                self.assertTrue(workspace.journal_path(root).exists())

    def test_atomic_publish_collision_preserves_other_file_and_cleans_temp(self):
        self.prepare()
        target = self.root / 'runs/collision.md'
        original = os.link
        def competing_link(source, destination):
            Path(destination).write_text('Other writer')
            return original(source, destination)
        with patch.object(workspace.os, 'link', side_effect=competing_link):
            with self.assertRaises(FileExistsError):
                workspace.write_atomic(target, 'Replacement', create_only=True)
        self.assertEqual(target.read_text(), 'Other writer')
        self.assertEqual(list(target.parent.glob('.zyris-tmp-*')), [])

    def test_atomic_replace_failure_preserves_original_permissions_and_cleans_temp(self):
        self.prepare()
        target = self.root / 'state.md'
        target.chmod(0o600)
        old = target.read_bytes()
        with patch.object(workspace.os, 'replace', side_effect=OSError('injected rename failure')):
            with self.assertRaises(OSError):
                workspace.write_atomic(target, 'Replacement')
        self.assertEqual(target.read_bytes(), old)
        self.assertEqual(list(self.root.glob('.zyris-tmp-*')), [])
        workspace.write_atomic(target, 'Replacement')
        if os.name != 'nt':
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_init_preserves_existing_content_preferences_and_config_extensions(self):
        self.prepare()
        (self.root / 'runs/legacy.md').write_text('Legacy fictional run')
        (self.root / 'jobs/example').mkdir()
        (self.root / 'jobs/example/job.md').write_text('Fictional vacancy')
        (self.root / 'preferences.json').write_text('{"schema_version":1,"custom":"keep"}')
        data = json.loads(self.cfg.read_text())
        data['custom'] = 'keep'
        self.cfg.write_text(json.dumps(data))
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        init_workspace(self.root, self.cfg, force=True)
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        self.assertEqual(json.loads(self.cfg.read_text())['custom'], 'keep')
        set_language(self.root, 'de')
        self.assertEqual(json.loads((self.root / 'preferences.json').read_text())['custom'], 'keep')

    def test_wrong_types_and_symlinks_fail_before_initializing(self):
        outside = self.base / 'outside'
        outside.mkdir()
        (outside / 'state.md').write_text('Protected')
        for relative, symlink in (('runs', False), ('candidate', True), ('state.md', True)):
            root = self.base / ('case-' + relative)
            root.mkdir()
            path = root / relative
            if symlink:
                path.symlink_to(outside if relative == 'candidate' else outside / 'state.md')
            else:
                path.write_text('Not a directory')
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                init_workspace(root, self.base / (relative + '-config.json'))
            self.assertFalse((root / 'README.md').exists())
        self.assertEqual((outside / 'state.md').read_text(), 'Protected')

    def test_dangling_run_and_preferences_links_rejected(self):
        self.digest = self.prepare()
        destination = self.base / 'must-not-be-created'
        (self.root / 'runs/test.md').symlink_to(destination)
        with self.assertRaises(ValueError):
            self.save()
        (self.root / 'preferences.json').symlink_to(destination)
        with self.assertRaises(ValueError):
            set_language(self.root, 'de')
        self.assertFalse(destination.exists())

    def test_invalid_lifecycle_and_nonpaused_resume_rejected(self):
        self.digest = self.prepare()
        for options in ({'status':'completed', 'answered_count':1, 'planned_count':3},
                        {'status':'other'}, {'answered_count':-1}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.save(**options)
        self.save(status='stopped_early', answered_count=1, planned_count=3)
        with self.assertRaisesRegex(ValueError, 'Only a paused'):
            workspace.resume(self.root, 'test')

    def test_pending_transaction_blocks_other_mutations(self):
        self.digest = self.prepare()
        workspace.journal_path(self.root).write_text('{"schema_version":999}')
        for operation in (lambda: self.save(), lambda: set_language(self.root, 'de'),
                          lambda: init_workspace(self.root, self.cfg)):
            with self.assertRaisesRegex(RuntimeError, 'Pending transaction'):
                operation()
        with self.assertRaisesRegex(ValueError, 'Unsupported transaction'):
            workspace.recover(self.root)

    def test_config_inside_workspace_cannot_overwrite_candidate_files(self):
        self.prepare()
        target = self.root / 'state.md'
        original = target.read_bytes()
        with self.assertRaisesRegex(ValueError, 'outside'):
            init_workspace(self.root, target, force=True)
        self.assertEqual(target.read_bytes(), original)

    def test_checkpoint_planned_count_cannot_be_dropped_to_claim_completion(self):
        self.digest = self.prepare()
        self.save('pause', status='paused', answered_count=1, planned_count=3)
        self.digest = workspace.resume(self.root, 'pause')['state_sha256']
        with self.assertRaisesRegex(ValueError, 'Incomplete interview'):
            self.save('premature', status='completed', answered_count=2, resume_from='pause')
        self.assertFalse((self.root / 'runs/premature.md').exists())
        self.save('stop', status='stopped_early', answered_count=2, resume_from='pause')
        metadata, _ = workspace.read_run(self.root, 'stop')
        self.assertEqual(metadata['planned_count'], 3)
        with self.assertRaisesRegex(ValueError, 'already continued'):
            workspace.resume(self.root, 'pause')

    def test_corrupt_lifecycle_metadata_and_journal_fail_without_writes(self):
        self.digest = self.prepare()
        (self.root / 'runs/bad.md').write_text(workspace.HEADER +
            json.dumps({'schema_version':1, 'run_id':'bad', 'status':'paused'}) + ' -->\n')
        with self.assertRaises(ValueError):
            workspace.resume(self.root, 'bad')
        old = (self.root / 'state.md').read_bytes()
        workspace.journal_path(self.root).write_text(json.dumps({
            'schema_version':1, 'run_id':'bad', 'run_text':'Not a structured run',
            'state_text':'Must not be written', 'expected_state_sha256':self.digest}))
        with self.assertRaises(ValueError):
            workspace.recover(self.root)
        self.assertEqual((self.root / 'state.md').read_bytes(), old)

    def test_flush_failure_keeps_old_file_and_removes_temporary_file(self):
        self.prepare()
        target = self.root / 'state.md'
        old = target.read_bytes()
        with patch.object(workspace.os, 'fsync', side_effect=OSError('injected flush failure')):
            with self.assertRaises(OSError):
                workspace.write_atomic(target, 'Must not replace original')
        self.assertEqual(target.read_bytes(), old)
        self.assertEqual(list(self.root.glob('.zyris-tmp-*')), [])

    def test_failed_pointer_switch_preserves_old_config_and_workspace(self):
        self.prepare()
        old_config = self.cfg.read_bytes()
        old_state = (self.root / 'state.md').read_bytes()
        original = workspace.write_atomic
        def fail_config(path, content, **kwargs):
            if path == self.cfg:
                raise OSError('injected pointer write failure')
            return original(path, content, **kwargs)
        with patch.object(workspace, 'write_atomic', side_effect=fail_config):
            with self.assertRaises(OSError):
                init_workspace(self.base / 'other', self.cfg, force=True)
        self.assertEqual(self.cfg.read_bytes(), old_config)
        self.assertEqual((self.root / 'state.md').read_bytes(), old_state)
        self.assertEqual(configured_root(self.cfg), self.root.resolve())

    def test_cli_partial_save_has_no_success_output_and_can_recover(self):
        self.digest = self.prepare()
        run_file = self.base / 'prepared-run.md'
        state_file = self.base / 'prepared-state.md'
        run_file.write_text('Fictional answer')
        state_file.write_text('Fictional updated state')
        original = workspace.write_atomic
        def fail_state(path, content, **kwargs):
            if path.name == 'state.md':
                raise OSError('injected disk failure')
            return original(path, content, **kwargs)
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(workspace, 'write_atomic', side_effect=fail_state), contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = workspace.main(['--config', str(self.cfg), 'finish', '--run-id', 'partial',
                '--run-file', str(run_file), '--state-file', str(state_file),
                '--expected-state-sha256', self.digest, '--status', 'stopped_early',
                '--answered-count', '1', '--planned-count', '3'])
        self.assertEqual(code, 1)
        self.assertEqual(output.getvalue(), '')
        self.assertIn('do not claim success', errors.getvalue())
        self.assertTrue((self.root / 'runs/partial.md').exists())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(workspace.main(['--config', str(self.cfg), 'recover']), 0)
        self.assertEqual((self.root / 'state.md').read_text(), 'Fictional updated state')

    def test_two_processes_cannot_publish_competing_prepared_states(self):
        for same_id in (True, False):
            with self.subTest(same_id=same_id), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / 'workspace'
                init_workspace(root, Path(directory) / 'config.json')
                digest = workspace.state_digest(root)
                script = """import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from interview_workspace import finish
print('READY', flush=True)
sys.stdin.readline()
try:
    finish(Path(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[4], expected_state_sha256=sys.argv[5])
except (OSError, ValueError, RuntimeError) as exc:
    print(str(exc))
    sys.exit(1)
"""
                workers = []
                try:
                    for index in range(2):
                        worker = subprocess.Popen([sys.executable, '-c', script, str(Path(workspace.__file__).parent),
                            str(root), 'same' if same_id else str(index), 'state-' + str(index), digest],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        workers.append(worker)
                    for worker in workers:
                        self.assertEqual(worker.stdout.readline().strip(), 'READY')
                    for worker in workers:
                        worker.stdin.write('GO\n')
                        worker.stdin.flush()
                    for worker in workers:
                        worker.communicate(timeout=15)
                    self.assertEqual(sorted(w.returncode for w in workers), [0, 1])
                    runs = list((root / 'runs').glob('*.md'))
                    self.assertEqual(len(runs), 1)
                    _, body = workspace.read_run(root, runs[0].stem)
                    self.assertEqual((root / 'state.md').read_text(), body)
                finally:
                    for worker in workers:
                        if worker.poll() is None:
                            worker.kill()
                        worker.communicate()

    def test_process_crash_releases_lock_and_preserves_recovery_intent(self):
        self.digest = self.prepare()
        old = (self.root / 'state.md').read_bytes()
        script = """import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import interview_workspace as w
original = w.write_atomic
def wait_after_run(path, content, **kwargs):
    original(path, content, **kwargs)
    if path.name == 'crash.md':
        print('RUN_PUBLISHED', flush=True)
        sys.stdin.readline()
w.write_atomic = wait_after_run
w.finish(Path(sys.argv[2]), 'crash', 'Fictional checkpoint', 'Recovered state', expected_state_sha256=sys.argv[3])
"""
        worker = subprocess.Popen([sys.executable, '-c', script, str(Path(workspace.__file__).parent),
                                   str(self.root), self.digest], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(worker.stdout.readline().strip(), 'RUN_PUBLISHED')
            with self.assertRaisesRegex(RuntimeError, 'busy'):
                self.save('competing')
            worker.kill()
            worker.communicate(timeout=15)
            self.assertEqual((self.root / 'state.md').read_bytes(), old)
            with self.assertRaisesRegex(RuntimeError, 'Pending transaction'):
                workspace.snapshot(self.root)
            workspace.recover(self.root)
            self.assertEqual((self.root / 'state.md').read_text(), 'Recovered state')
        finally:
            if worker.poll() is None:
                worker.kill()
            worker.communicate()


if __name__ == '__main__':
    unittest.main()
