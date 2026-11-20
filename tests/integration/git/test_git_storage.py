"""REQ-GIT: real git flows against a temporary LOCAL bare repository behind a github.com URL.

Provider access is simulated by a fake `gh` executable and a git URL rewrite (insteadOf) plus a controlled identity test double (the bare repository stands for the authorized
repository). This is NOT a live
GitHub/GitLab acceptance: no real provider, authentication or API is involved.
"""
import json
import os
import shutil
import subprocess
import unittest
from unittest import mock

from tests.support.coach import GitCase, REMOTE, gitstore, iw, snapshot


class Connect(GitCase):
    def test_setup_clones_initializes_publishes_and_reports_remote_saved(self):
        result = self.setup_git()
        self.assertEqual('cloned', result['clone'])
        self.assertTrue(result['publish']['remote_saved'])
        self.assertEqual(self.remote_head(), result['publish']['commit'])
        files = subprocess.run(['git', '--git-dir', str(self.bare), 'ls-tree', '-r', '--name-only', 'main'], capture_output=True, text=True).stdout.split()
        self.assertIn('workspace.json', files)
        self.assertNotIn('.journal/lock', files, 'control directory must not be published')
        config = iw.read_project_config(self.project, self.cfg)
        self.assertEqual('private', config['git']['visibility'])
        self.assertEqual(REMOTE, config['git']['remote'])
        self.assertEqual({'fetch', 'push'}, set(config['git']['targets']))
        self.assertNotIn('token', json.dumps(config).lower())

    def test_non_private_repository_refused_before_any_clone_or_config(self):
        self.env['FAKE_GH_PRIVATE'] = 'false'
        with mock.patch.dict(os.environ, self.env):
            with self.assertRaisesRegex(gitstore.GitStorageError, 'not private'):
                self.setup_git()
        self.assertFalse(self.clone.exists())
        self.assertFalse(self.cfg.exists())
        self.assertIsNone(self.remote_head())

    def test_missing_write_permission_refused(self):
        self.env['FAKE_GH_PERMISSION'] = 'READ'
        with mock.patch.dict(os.environ, self.env):
            with self.assertRaisesRegex(gitstore.GitStorageError, 'Write permission not confirmed'):
                self.setup_git()
        self.assertFalse(self.clone.exists())

    def test_unknown_visibility_without_provider_cli_or_attestation_refused(self):
        self._script('gh', '#!/bin/sh\necho "not logged in" >&2\nexit 1\n')
        with self.assertRaisesRegex(gitstore.GitStorageError, 'not confirmed.*gh could not read'):
            self.setup_git()
        self.assertIsNone(self.remote_head())

    def test_connector_attestation_must_name_the_exact_repository_and_carry_user_confirmation(self):
        self._script('gh', '#!/bin/sh\nexit 1\n')
        for bad in (self.attestation(repository='someone-else/other'), self.attestation(user_confirmed=False)):
            with self.assertRaisesRegex(gitstore.GitStorageError, 'must name this exact repository'):
                self.setup_git(attest=bad)
        self.assertFalse(self.clone.exists())
        result = self.setup_git(attest=self.attestation())
        self.assertTrue(result['publish']['remote_saved'])
        self.assertEqual('connector-attestation:example-connector', iw.read_project_config(self.project, self.cfg)['git']['evidence'])
        done = self.cli('project-init', '--project', self.base / 'p2', '--storage', 'git', '--path', self.base / 'c2', '--remote', REMOTE,
                        '--attest-private', expect=1)
        self.assertIn('--attest-user-confirmed', done.stderr)

    def test_only_github_or_gitlab_remotes_accepted(self):
        for url in (str(self.bare), f'file://{self.bare}', 'https://example.com/o/r.git', 'ssh://git@github.com/o/r', 'https://github.com/o',
                    'https://github.com/o/r/extra', 'https://github.com/../x/y'):
            with self.assertRaises(ValueError, msg=url):
                gitstore.parse_remote(url)
        self.assertEqual(('gitlab', 'gitlab.com', 'grp/sub/proj'), gitstore.parse_remote('git@gitlab.com:grp/sub/proj.git'))
        self.assertEqual(('github', 'github.com', 'o/r'), gitstore.parse_remote('https://github.com/o/r'))

    def test_unreadable_remote_reports_missing_access(self):
        shutil.rmtree(self.bare)
        with self.assertRaisesRegex(gitstore.GitStorageError, 'not readable'):
            self.setup_git()
        self.assertFalse(self.cfg.exists())

    def test_rewrite_to_an_unprovable_target_is_refused_before_clone_config_and_remote(self):
        with mock.patch.object(gitstore, 'identity_of', side_effect=self.real_identity):   # no test double: the target is only a local path
            with self.assertRaisesRegex(gitstore.GitStorageError, 'cannot be proven'):
                self.setup_git()
        self.assertIsNone(self.remote_head())
        self.assertFalse(self.cfg.exists())
        self.assertFalse(self.clone.exists())

    def test_there_is_no_flag_that_accepts_an_unprovable_rewrite(self):
        self.assertNotIn('allow-url-rewrite', json.dumps(self.cli('project-show', '--project', self.project, expect=1).stderr))
        done = self.cli('project-init', '--project', self.project, '--storage', 'git', '--path', self.clone, '--remote', REMOTE, '--allow-url-rewrite', expect=2)
        self.assertIn('unrecognized arguments', done.stderr)

    def test_existing_clone_of_other_remote_not_reused(self):
        self.setup_git()
        self.run_git('remote', 'set-url', 'origin', 'https://github.com/example-owner/other.git')
        with self.assertRaisesRegex(gitstore.GitStorageError, 'different remote'):
            self.setup_git()

    def test_failed_initial_publish_writes_no_pointer(self):
        real = gitstore.git

        def failing(args, **kw):
            if args[:1] == ['push']:
                raise gitstore.GitStorageError('git push failed')
            return real(args, **kw)
        with mock.patch.object(gitstore, 'git', side_effect=failing):
            with self.assertRaises(gitstore.GitStorageError):
                self.setup_git()
        self.assertEqual([], list(self.cfg.glob('*.json')), 'no pointer until remote success is confirmed')
        self.assertIsNone(self.remote_head())


class SetupOrdering(GitCase):
    """Finding A: the switch decision happens before ANY mutation (clone, files, remote, pointer)."""

    def git_calls(self):
        return self.gitlog.read_text() if self.gitlog.exists() else ''

    def test_unconfirmed_git_to_other_target_has_no_side_effects(self):
        self.setup_git()
        pointer = (self.cfg / next(self.cfg.glob('*.json')).name).read_bytes()
        remote_before, before = self.remote_head(), snapshot(self.clone)
        calls = len(self.git_calls().splitlines())
        other = self.base / 'second-clone'
        with self.assertRaisesRegex(ValueError, 'another storage target or type'):
            iw.setup_project(self.project, 'git', other, config_dir=self.cfg, remote=REMOTE)
        self.assertFalse(other.exists())
        self.assertEqual(calls, len(self.git_calls().splitlines()), 'no git/remote action may precede the decision')
        self.assertEqual(remote_before, self.remote_head())
        self.assertEqual(before, snapshot(self.clone))
        self.assertEqual(pointer, (self.cfg / next(self.cfg.glob('*.json')).name).read_bytes())

    def test_unconfirmed_other_repository_at_same_path_is_refused_first(self):
        self.setup_git()
        calls = len(self.git_calls().splitlines())
        with self.assertRaisesRegex(ValueError, 'another storage target or type'):
            iw.setup_project(self.project, 'git', self.clone, config_dir=self.cfg, remote='https://github.com/example-owner/other.git')
        self.assertEqual(calls, len(self.git_calls().splitlines()))

    def test_storage_type_change_at_the_same_path_needs_confirmation(self):
        iw.setup_project(self.project, 'local', self.base / 'shared-dir', config_dir=self.cfg)
        before = snapshot(self.base / 'shared-dir')
        with self.assertRaisesRegex(ValueError, 'another storage target or type'):
            iw.setup_project(self.project, 'git', self.base / 'shared-dir', config_dir=self.cfg, remote=REMOTE)
        self.assertEqual('', self.git_calls())
        self.assertEqual(before, snapshot(self.base / 'shared-dir'))
        self.assertEqual('local', iw.read_project_config(self.project, self.cfg)['storage'])

    def test_confirmed_switch_works(self):
        self.setup_git()
        other_project_dir = self.base / 'second-clone'
        iw.setup_project(self.project, 'local', other_project_dir, config_dir=self.cfg, switch=True)
        self.assertEqual('local', iw.read_project_config(self.project, self.cfg)['storage'])

    def test_invalid_existing_configuration_is_rejected_before_mutations(self):
        self.cfg.mkdir()
        pointer = iw.project_config_path(self.project, self.cfg)
        pointer.write_text('{"schema_version":2,"schema_version":2}')
        target = self.base / 'new-target'
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON field'):
            iw.setup_project(self.project, 'local', target, config_dir=self.cfg)
        self.assertFalse(target.exists())
        self.assertEqual('', self.git_calls())

    def test_concurrent_setup_is_serialized(self):
        self.cfg.mkdir()
        pointer = iw.project_config_path(self.project, self.cfg)
        with iw.file_lock(pointer.with_name(pointer.name + '.lock')):
            with self.assertRaisesRegex(RuntimeError, 'busy'):
                iw.setup_project(self.project, 'local', self.base / 'ws-concurrent', config_dir=self.cfg)
        self.assertFalse((self.base / 'ws-concurrent').exists())


class Publishing(GitCase):
    def setUp(self):
        super().setUp()
        self.setup_git()
        self.cid = self.candidate()

    def candidate(self, name='Erika Beispiel'):
        with iw.git_save_guard(self.clone, 'test: candidate'):
            return iw.create_candidate(self.clone, name)['candidate_id']

    def cdir(self, cid):
        return self.clone / 'candidates' / cid

    def publish(self, message='x', **kw):
        return iw.git_publish(self.project, message, self.cfg, **kw)

    def remote_edit(self, name, text, message='remote'):
        other = self.second_clone()
        (other / name).parent.mkdir(parents=True, exist_ok=True)
        (other / name).write_text(text)
        subprocess.run(['git', '-C', str(other), 'add', '-A'], check=True)
        subprocess.run(['git', '-C', str(other), 'commit', '-qm', message], check=True)
        subprocess.run(['git', '-C', str(other), 'push', '-q', 'origin', 'main'], check=True)
        return other

    # ------------------------------------------------------------ remote-saved semantics
    def test_local_save_is_not_remote_save_until_publish_confirms(self):
        before = self.remote_head()
        self.assertFalse(gitstore.status(self.clone)['remote_saved'])
        self.assertEqual(before, self.remote_head())
        result = self.publish('Add candidate')
        self.assertTrue(result['remote_saved'])
        self.assertEqual(self.remote_head(), result['commit'])
        self.assertTrue(gitstore.status(self.clone)['remote_saved'])

    def test_cli_finish_commits_locally_warns_and_publish_succeeds(self):
        self.publish()
        state, run = self.write('s.md', '# state\n'), self.write('r.md', '# run\n')
        sha = json.loads(self.cli('status', '--project', self.project, '--candidate', self.cid).stdout)['state_sha256']
        done = self.cli('finish', '--project', self.project, '--candidate', self.cid, '--run-id', 'r1', '--run-file', run, '--state-file', state,
                        '--expected-state-sha256', sha, '--status', 'completed', '--answered-count', '1')
        self.assertIn('NOT saved remotely', done.stdout)
        info = gitstore.status(self.clone)
        self.assertFalse(info['remote_saved'])
        self.assertFalse(info['uncommitted_changes'], 'the save is committed locally by the guard')
        self.assertEqual(1, info['ahead'])
        published = json.loads(self.cli('git-publish', '--project', self.project, '--message', 'Save run r1').stdout)
        self.assertTrue(published['remote_saved'])

    def test_push_rejection_or_interruption_is_reported_as_local_only(self):
        real = gitstore.git

        def reject(args, **kw):
            if args[:1] == ['push']:
                return subprocess.CompletedProcess(args, 1, '', 'remote: Permission denied')
            return real(args, **kw)
        with mock.patch.object(gitstore, 'git', side_effect=reject):
            with self.assertRaisesRegex(gitstore.GitStorageError, 'LOCAL ONLY'):
                self.publish()
        self.assertNotEqual(self.run_git('rev-parse', 'HEAD'), self.remote_head())
        self.assertFalse(gitstore.status(self.clone)['remote_saved'])
        self.assertTrue(self.publish('retry')['remote_saved'])

    def test_unconfirmed_remote_head_is_not_reported_as_success(self):
        real = gitstore.git

        def silent(args, **kw):
            if args[:1] == ['push']:
                return subprocess.CompletedProcess(args, 0, '', '')   # claims success, remote unchanged
            return real(args, **kw)
        with mock.patch.object(gitstore, 'git', side_effect=silent):
            with self.assertRaisesRegex(gitstore.GitStorageError, 'could not be confirmed'):
                self.publish()

    def test_final_verification_reads_the_described_target_not_origin_by_name(self):
        calls = []
        real = gitstore.git

        def spy(args, **kw):
            calls.append(list(args))
            return real(args, **kw)
        with mock.patch.object(gitstore, 'git', side_effect=spy):
            self.publish()
        pushes = [c for c in calls if c[:1] == ['push']]
        verifies = [c for c in calls if c[:1] == ['ls-remote'] and 'refs/heads/main' in c]
        self.assertEqual(1, len(pushes))
        self.assertEqual(str(self.bare), pushes[0][1], 'push goes to the verified effective URL, not to a name')
        self.assertEqual(str(self.bare), verifies[-1][1])
        self.assertEqual('push', 'push' if verifies[-1][1] == pushes[0][1] else 'fetch', 'verification addresses the push target')

    def test_matching_fetch_target_cannot_prove_success_at_the_push_target(self):
        self.publish()
        self.candidate('Max Muster')
        targets = iw.read_project_config(self.project, self.cfg)['git']['targets']
        other = self.base / 'other-push.git'
        subprocess.run(['git', 'init', '-q', '--bare', '-b', 'main', str(other)], check=True)
        split = {'fetch': targets['fetch'], 'push': str(other)}
        real = gitstore.git

        def push_target_unreadable(args, **kw):
            if args[:1] == ['ls-remote'] and args[1] == str(other):
                return subprocess.CompletedProcess(args, 128, '', 'unable to access')
            return real(args, **kw)
        with mock.patch.object(gitstore, 'git', side_effect=push_target_unreadable):
            with self.assertRaisesRegex(gitstore.GitStorageError, 'at the push target'):
                gitstore.publish(self.clone, split)

        def push_target_differs(args, **kw):
            if args[:1] == ['ls-remote'] and args[1] == str(other):
                return subprocess.CompletedProcess(args, 0, '0' * 40 + '\trefs/heads/main\n', '')
            return real(args, **kw)
        with mock.patch.object(gitstore, 'git', side_effect=push_target_differs):
            with self.assertRaisesRegex(gitstore.GitStorageError, 'at the push target'):
                gitstore.publish(self.clone, split)
        self.assertEqual(self.run_git('rev-parse', 'HEAD'), self.run_git('--git-dir', str(other), 'rev-parse', 'refs/heads/main'),
                         'the push really happened; only the confirmation is refused')

    def test_fetch_failure_is_local_only(self):
        real = gitstore.git

        def offline(args, **kw):
            if args[:1] == ['fetch']:
                return subprocess.CompletedProcess(args, 128, '', 'unable to access')
            return real(args, **kw)
        with mock.patch.object(gitstore, 'git', side_effect=offline):
            with self.assertRaisesRegex(gitstore.GitStorageError, 'LOCAL ONLY'):
                self.publish()

    def test_concurrent_remote_change_in_other_files_is_integrated_not_overwritten(self):
        self.publish('first')
        self.remote_edit('foreign.txt', 'from another machine')
        self.candidate('Max Muster')
        self.assertTrue(self.publish('second')['remote_saved'])
        self.assertEqual('from another machine', (self.clone / 'foreign.txt').read_text())
        files = subprocess.run(['git', '--git-dir', str(self.bare), 'ls-tree', '-r', '--name-only', 'main'], capture_output=True, text=True).stdout
        self.assertIn('foreign.txt', files)
        self.assertEqual(2, files.count('candidate.json'))

    def test_conflicting_change_to_same_file_is_never_overwritten_and_not_reported_saved(self):
        self.publish('first')
        self.remote_edit(f'candidates/{self.cid}/state.md', '# remote edit\n')
        remote_before = self.remote_head()
        with iw.git_save_guard(self.clone, 'local state'):
            iw.write_atomic(self.cdir(self.cid) / 'state.md', '# local edit\n')   # a managed write, hence attributed to this save
        with self.assertRaisesRegex(gitstore.GitStorageError, 'Conflicting remote changes.*NOT saved remotely'):
            self.publish('local')
        self.assertEqual(remote_before, self.remote_head())
        self.assertEqual('# local edit\n', (self.cdir(self.cid) / 'state.md').read_text())
        self.assertNotIn('UU', self.run_git('status', '--porcelain'))

    def test_no_force_option_is_ever_passed_to_git(self):
        self.publish('a')
        self.remote_edit('x.txt', 'x')
        self.candidate('Max Muster')
        self.publish('b')
        calls = self.gitlog.read_text().splitlines()
        self.assertTrue(any(c.startswith('push ') for c in calls))
        for call in calls:
            self.assertNotRegex(call, r'(^| )(-f|--force\S*)( |$)')
            self.assertNotIn(' +refs', call.replace('+refs/heads', 'FETCH') if call.startswith('fetch') else call)
        with self.assertRaisesRegex(gitstore.GitStorageError, 'Forced'):
            gitstore.git(['push', '--force', 'origin'], cwd=self.clone)
        with self.assertRaisesRegex(gitstore.GitStorageError, 'Forced'):
            gitstore.git(['push', 'origin', '+HEAD:main'], cwd=self.clone)

    def test_pull_is_fast_forward_only_and_refuses_with_unpublished_work(self):
        self.publish('first')
        self.remote_edit('x.txt', 'x')
        self.candidate('Max Muster')
        before = snapshot(self.clone)
        with self.assertRaisesRegex(gitstore.GitStorageError, 'unpublished'):
            gitstore.pull(self.clone)
        self.assertEqual(before, snapshot(self.clone))
        self.publish('second')
        self.remote_edit('y.txt', 'y')
        self.assertEqual(0, gitstore.pull(self.clone)['behind'])
        self.assertEqual('y', (self.clone / 'y.txt').read_text())

    def test_publish_refused_while_a_transaction_is_pending(self):
        with mock.patch.object(iw, 'apply_pending', side_effect=OSError('crash')):
            with self.assertRaises(RuntimeError):
                with iw.git_save_guard(self.clone, 'x'):
                    iw.finish(self.clone, self.cid, 'r1', '# run\n', '# s\n', expected_state_sha256=iw.snapshot(self.clone, self.cid)['state_sha256'],
                              status='completed', answered_count=1)
        with self.assertRaisesRegex(gitstore.GitStorageError, 'Pending transactions'):
            self.publish()

    def test_missing_git_identity_leaves_changes_local_and_says_so(self):
        env = dict(self.env, GIT_AUTHOR_NAME='', GIT_AUTHOR_EMAIL='', GIT_COMMITTER_NAME='', GIT_COMMITTER_EMAIL='', GIT_CONFIG_GLOBAL=os.devnull)
        with mock.patch.dict(os.environ, env):
            with self.assertRaisesRegex(gitstore.GitStorageError, 'changes remain local only'):
                with iw.git_save_guard(self.clone, 'x'):
                    iw.create_candidate(self.clone, 'Max Muster')
        self.assertTrue(self.clone.joinpath('.journal/interrupted.json').is_file())

    def test_non_git_project_cannot_use_git_commands(self):
        other = self.base / 'p2'
        other.mkdir()
        iw.setup_project(other, 'local', self.base / 'ws2', config_dir=self.cfg)
        with self.assertRaisesRegex(ValueError, 'does not use Git'):
            iw.git_publish(other, 'x', self.cfg)

    # ------------------------------------------------- finding B: authorized vs. actual target
    def test_origin_changed_after_setup_aborts_before_commit_and_push(self):
        self.run_git('remote', 'set-url', 'origin', 'https://github.com/example-owner/other.git')
        remote_before, head = self.remote_head(), self.run_git('rev-parse', 'HEAD')
        with self.assertRaisesRegex(gitstore.GitStorageError, 'does not point to the authorized repository'):
            self.publish()
        self.assertEqual(remote_before, self.remote_head())
        self.assertEqual(head, self.run_git('rev-parse', 'HEAD'))
        self.assertEqual('https://github.com/example-owner/other.git', self.run_git('config', 'remote.origin.url'), 'remote is not reconfigured')

    def test_separate_pushurl_to_another_repository_is_refused(self):
        self.run_git('config', 'remote.origin.pushurl', 'https://github.com/someone-else/elsewhere.git')
        with self.assertRaisesRegex(gitstore.GitStorageError, 'does not point to the authorized repository'):
            self.publish()
        self.assertFalse(any(c.startswith('push ') for c in self.gitlog.read_text().splitlines()[-3:]))

    def test_multiple_push_targets_are_refused(self):
        self.run_git('config', '--add', 'remote.origin.pushurl', REMOTE)
        self.run_git('config', '--add', 'remote.origin.pushurl', REMOTE)
        with self.assertRaisesRegex(gitstore.GitStorageError, 'several push URLs'):
            self.publish()

    def test_url_rewrite_added_after_setup_is_detected(self):
        self.run_git('config', '--global', f'url.{self.base}/evil.git.pushInsteadOf', REMOTE)
        with self.assertRaisesRegex(gitstore.GitStorageError, 'cannot be proven'):
            self.publish()
        self.assertFalse((self.base / 'evil.git').exists())


    def test_repository_turning_public_or_losing_rights_blocks_publishing(self):
        for key, value, message in (('FAKE_GH_PRIVATE', 'false', 'not private'), ('FAKE_GH_PERMISSION', 'READ', 'Write permission not confirmed')):
            env = dict(self.env, **{key: value})
            with mock.patch.dict(os.environ, env):
                with self.assertRaisesRegex(gitstore.GitStorageError, message):
                    self.publish()
        self.assertFalse(gitstore.status(self.clone)['remote_saved'])

    def test_stored_connector_attestation_is_never_sufficient_for_publishing(self):
        self.env['FAKE_GH_PRIVATE'] = 'true'
        # reconfigure the project as attestation-based
        config_path = iw.project_config_path(self.project, self.cfg)
        data = json.loads(config_path.read_text())
        data['git']['evidence'] = 'connector-attestation:example-connector'
        data['git']['checked_at'] = '2020-01-01T00:00:00Z'      # stale
        config_path.write_text(json.dumps(data))
        self._script('gh', '#!/bin/sh\nexit 1\n')                  # provider CLI unavailable
        with self.assertRaisesRegex(gitstore.GitStorageError, 'Private repository status not confirmed'):
            self.publish()
        with self.assertRaisesRegex(gitstore.GitStorageError, 'must name this exact repository'):
            self.publish(attest=self.attestation(repository='other/repo'))
        self.assertTrue(self.publish(attest=self.attestation())['remote_saved'])

    # ------------------------------------------------------- finding C: only own changes are published
    def test_foreign_untracked_file_blocks_the_save_and_is_preserved(self):
        self.publish()
        foreign = self.clone / 'notes-from-me.txt'
        foreign.write_text('private note')
        remote_before = self.remote_head()
        done = self.cli('candidate-create', '--project', self.project, '--name', 'Max Muster', expect=1)
        self.assertIn('Unexpected changes', done.stderr)
        self.assertIn('notes-from-me.txt', done.stderr)
        self.assertEqual('private note', foreign.read_text())
        self.assertEqual(1, len([c for c in (self.clone / 'candidates').iterdir() if not c.name.startswith('.')]), 'the save did not run')
        self.assertEqual(remote_before, self.remote_head())
        with self.assertRaisesRegex(gitstore.GitStorageError, 'Uncommitted changes'):
            self.publish()
        self.assertNotIn('notes-from-me', self.run_git('ls-files'))
        self.assertNotIn('notes-from-me', subprocess.run(['git', '--git-dir', str(self.bare), 'ls-tree', '-r', 'main'], capture_output=True, text=True).stdout)

    def test_prestaged_changes_are_neither_published_nor_lost(self):
        self.publish()
        (self.clone / 'staged.txt').write_text('staged by someone')
        self.run_git('add', 'staged.txt')
        (self.cdir(self.cid) / 'profile.md').write_text('unstaged manual edit')
        done = self.cli('candidate-create', '--project', self.project, '--name', 'Max Muster', expect=1)
        self.assertIn('staged: staged.txt', done.stderr)
        self.assertEqual('staged.txt', self.run_git('diff', '--cached', '--name-only'))
        self.assertEqual('unstaged manual edit', (self.cdir(self.cid) / 'profile.md').read_text())
        with self.assertRaises(gitstore.GitStorageError):
            self.publish()
        self.assertNotIn('staged.txt', subprocess.run(['git', '--git-dir', str(self.bare), 'ls-tree', '-r', 'main'], capture_output=True, text=True).stdout)

    def test_unexpected_edit_inside_a_managed_directory_blocks_too(self):
        self.publish()
        state = self.cdir(self.cid) / 'state.md'
        state.write_text(state.read_text() + '\nedited by hand')
        done = self.cli('candidate-create', '--project', self.project, '--name', 'Max Muster', expect=1)
        self.assertIn(f'candidates/{self.cid}/state.md', done.stderr)
        self.assertTrue(state.read_text().endswith('edited by hand'))

    def test_interrupted_own_save_is_adopted_by_the_next_save_but_foreign_files_are_not(self):
        self.publish()
        with mock.patch.object(iw, 'materialize_candidate', side_effect=OSError('disk full')):
            with self.assertRaises(RuntimeError):
                with iw.git_save_guard(self.clone, 'x'):
                    iw.create_candidate(self.clone, 'Max Muster')
        leftovers = list(json.loads((self.clone / '.journal/interrupted.json').read_text())['files'])
        self.assertTrue(any(p.endswith('candidate.json') for p in leftovers))
        (self.clone / 'foreign.txt').write_text('mine')
        with self.assertRaisesRegex(gitstore.GitStorageError, 'foreign.txt'):
            with iw.git_save_guard(self.clone, 'next'):
                pass
        (self.clone / 'foreign.txt').unlink()
        with iw.git_save_guard(self.clone, 'next'):
            pass                                   # adopts exactly the recorded leftovers
        self.assertFalse(self.clone.joinpath('.journal/interrupted.json').exists())
        (draft,) = [c for c in (self.clone / 'candidates').iterdir() if c.name != self.cid and not c.name.startswith('.')]
        with iw.git_save_guard(self.clone, 'recover'):
            iw.recover_candidate(self.clone, draft.name)
        self.assertTrue(self.publish('after interruption')['remote_saved'])

    def test_publish_never_stages_anything_itself(self):
        self.publish()
        (self.clone / 'late.txt').write_text('x')
        with self.assertRaisesRegex(gitstore.GitStorageError, 'Uncommitted changes'):
            self.publish()
        self.assertEqual('', self.run_git('diff', '--cached', '--name-only'))
        self.assertTrue((self.clone / 'late.txt').exists())

    def test_setup_into_an_existing_clone_with_foreign_files_aborts_cleanly(self):
        subprocess.run(['git', 'clone', '-q', str(self.bare), str(self.base / 'dirty')], check=True)
        (self.base / 'dirty' / 'foreign.txt').write_text('mine')
        other = self.base / 'p3'
        other.mkdir()
        run_before = self.remote_head()
        subprocess.run(['git', '-C', str(self.base / 'dirty'), 'remote', 'set-url', 'origin', REMOTE], check=True)
        with self.assertRaisesRegex(gitstore.GitStorageError, 'Unexpected changes'):
            iw.setup_project(other, 'git', self.base / 'dirty', config_dir=self.base / 'cfg3', remote=REMOTE)
        self.assertEqual(run_before, self.remote_head())
        self.assertEqual('mine', (self.base / 'dirty' / 'foreign.txt').read_text())


class OwnChanges(GitCase):
    """Findings C/lock: attribution by recorded writes and content hashes; one cooperative Git lock per workspace."""

    def setUp(self):
        super().setUp()
        self.setup_git()

    def save_candidate(self, name):
        with iw.git_save_guard(self.clone, 'test: ' + name):
            return iw.create_candidate(self.clone, name)['candidate_id']

    def interrupt(self, name='Max Muster'):
        with mock.patch.object(iw, 'materialize_candidate', side_effect=OSError('disk full')):
            with self.assertRaises(RuntimeError):
                with iw.git_save_guard(self.clone, 'x'):
                    iw.create_candidate(self.clone, name)
        return json.loads((self.clone / '.journal/interrupted.json').read_text())

    def test_journal_records_content_hashes_not_just_paths(self):
        journal = self.interrupt()
        self.assertEqual(3, journal['schema_version'])
        (path, digest), = [(k, v) for k, v in journal['files'].items() if k.endswith('candidate.json')]
        self.assertEqual(gitstore.file_digest(self.clone, path), digest)

    def test_unchanged_interrupted_save_is_resumed_and_committed(self):
        journal = self.interrupt()
        draft = next(c for c in (self.clone / 'candidates').iterdir() if not c.name.startswith('.') and (c / 'candidate.json').exists())
        with iw.git_save_guard(self.clone, 'recover'):
            iw.recover_candidate(self.clone, draft.name)
        self.assertFalse((self.clone / '.journal/interrupted.json').exists())
        self.assertIn(f'candidates/{draft.name}/candidate.json', self.run_git('show', '--name-only', '--format=', 'HEAD').splitlines())

    def test_leftover_modified_afterwards_is_not_adopted_and_keeps_its_content(self):
        journal = self.interrupt()
        leftover = next(k for k in journal['files'] if k.endswith('candidate.json'))
        (self.clone / leftover).write_text('{"edited": "by someone else"}')
        head = self.run_git('rev-parse', 'HEAD')
        with self.assertRaisesRegex(gitstore.GitStorageError, 'changed since an interrupted save'):
            with iw.git_save_guard(self.clone, 'next'):
                pass
        self.assertEqual('{"edited": "by someone else"}', (self.clone / leftover).read_text())
        self.assertEqual(head, self.run_git('rev-parse', 'HEAD'))
        self.assertEqual('', self.run_git('diff', '--cached', '--name-only'))

    def test_unknown_journal_format_is_never_resumed(self):
        (self.clone / '.journal').mkdir(exist_ok=True)
        old = '{"paths": ["candidates/x/candidate.json"]}'
        (self.clone / '.journal/interrupted.json').write_text(old)
        with self.assertRaisesRegex(gitstore.GitStorageError, 'Unsupported interrupted-save journal'):
            with iw.git_save_guard(self.clone, 'x'):
                iw.create_candidate(self.clone, 'Max Muster')
        self.assertEqual(old, (self.clone / '.journal/interrupted.json').read_text())

    def test_file_added_by_someone_else_during_the_save_is_not_committed(self):
        head = self.run_git('rev-parse', 'HEAD')
        with self.assertRaisesRegex(gitstore.GitStorageError, 'appeared during the save.*late-foreign.txt'):
            with iw.git_save_guard(self.clone, 'x'):
                iw.create_candidate(self.clone, 'Max Muster')
                (self.clone / 'late-foreign.txt').write_text('not mine')   # appears after the pre-check
        self.assertEqual(head, self.run_git('rev-parse', 'HEAD'))
        self.assertEqual('not mine', (self.clone / 'late-foreign.txt').read_text())
        self.assertNotIn('late-foreign.txt', self.run_git('ls-files'))
        self.assertEqual('', self.run_git('diff', '--cached', '--name-only'))
        journal = json.loads((self.clone / '.journal/interrupted.json').read_text())
        self.assertNotIn('late-foreign.txt', journal['files'])        # never attributed to us
        self.assertTrue(any(k.endswith('candidate.json') for k in journal['files']))

    def test_staging_is_by_explicit_path_never_add_all(self):
        self.save_candidate('Max Muster')
        adds = [c for c in self.gitlog.read_text().splitlines() if c.startswith('add ')]
        self.assertTrue(adds)
        for call in adds:
            self.assertNotIn('-A', call.split())
            self.assertNotIn('--all', call.split())
            self.assertIn(' -- ', call)

    def test_two_cooperating_saves_for_the_same_workspace_never_mix(self):
        import threading
        entered, release, outcome = threading.Event(), threading.Event(), {}

        def first():
            try:
                with iw.git_save_guard(self.clone, 'first'):
                    outcome['a'] = iw.create_candidate(self.clone, 'Anna Alpha')['candidate_id']
                    entered.set()
                    release.wait(20)
            except BaseException as exc:   # pragma: no cover - reported through the assertion below
                outcome['error'] = exc
                entered.set()
        worker = threading.Thread(target=first)
        worker.start()
        self.assertTrue(entered.wait(20))
        with self.assertRaisesRegex(RuntimeError, 'busy'):
            with iw.git_save_guard(self.clone, 'second'):
                iw.create_candidate(self.clone, 'Berta Beta')      # a different candidate, same Git workspace
        with self.assertRaisesRegex(RuntimeError, 'busy'):
            iw.git_publish(self.project, 'during save', self.cfg)  # publishing is serialized with saving too
        release.set()
        worker.join(20)
        self.assertNotIn('error', outcome)
        names = self.run_git('show', '--name-only', '--format=%s', 'HEAD').splitlines()
        self.assertEqual('first', names[0])
        self.assertTrue(all(outcome['a'] in n for n in names[1:] if n.startswith('candidates/')))
        self.assertEqual(1, len([c for c in (self.clone / 'candidates').iterdir() if not c.name.startswith('.')]))
        self.save_candidate('Berta Beta')       # after release the second save works and commits separately
        self.assertEqual('test: Berta Beta', self.run_git('log', '-1', '--format=%s'))


class ControlFilesAndPull(GitCase):
    """Findings: staged control files are never hidden or published; git-pull/git-status use the shared Git-workspace lock."""

    def setUp(self):
        super().setUp()
        self.setup_git()
        self.control = self.clone / '.journal' / 'foreign-journal.json'

    def commit_control_file(self):
        self.control.parent.mkdir(exist_ok=True)
        self.control.write_text('{"foreign": true}')
        self.run_git('add', '-f', '.journal/foreign-journal.json')
        self.run_git('commit', '-qm', 'foreign control file')

    def tree(self):
        return subprocess.run(['git', '--git-dir', str(self.bare), 'ls-tree', '-r', '--name-only', 'main'], capture_output=True, text=True).stdout

    def assert_save_refused(self, expected_path):
        head, remote = self.run_git('rev-parse', 'HEAD'), self.remote_head()
        candidates = len([c for c in (self.clone / 'candidates').iterdir() if not c.name.startswith('.')])
        with self.assertRaisesRegex(gitstore.GitStorageError, 'staged: .*' + expected_path.replace('.', r'\.')):
            with iw.git_save_guard(self.clone, 'must not commit'):
                iw.create_candidate(self.clone, 'Max Muster')
        self.assertEqual(head, self.run_git('rev-parse', 'HEAD'), 'no commit')
        self.assertEqual(remote, self.remote_head(), 'no push')
        self.assertEqual(candidates, len([c for c in (self.clone / 'candidates').iterdir() if not c.name.startswith('.')]), 'save did not run')
        with self.assertRaisesRegex(gitstore.GitStorageError, 'Staged changes exist'):
            iw.git_publish(self.project, 'must not publish', self.cfg)
        self.assertEqual(remote, self.remote_head())

    def test_staged_new_control_file_blocks_save_and_publish_and_stays_staged(self):
        self.control.parent.mkdir(exist_ok=True)
        self.control.write_text('{"foreign": true}')
        self.run_git('add', '-f', '.journal/foreign-journal.json')
        self.assert_save_refused('.journal/foreign-journal.json')
        self.assertEqual('.journal/foreign-journal.json', self.run_git('diff', '--cached', '--name-only'), 'index untouched')
        self.assertEqual('{"foreign": true}', self.control.read_text())
        self.assertNotIn('.journal', self.tree())

    def test_staged_modification_of_a_tracked_control_file_is_refused(self):
        self.commit_control_file()
        self.control.write_text('{"foreign": "changed"}')
        self.run_git('add', '-f', '.journal/foreign-journal.json')
        self.assert_save_refused('.journal/foreign-journal.json')
        self.assertEqual('{"foreign": "changed"}', self.control.read_text())

    def test_staged_deletion_of_a_tracked_control_file_is_refused(self):
        self.commit_control_file()
        self.run_git('rm', '--cached', '-q', '.journal/foreign-journal.json')
        self.assert_save_refused('.journal/foreign-journal.json')
        self.assertTrue(self.control.exists(), 'working file kept')

    def test_staged_rename_of_a_control_file_is_refused(self):
        self.commit_control_file()
        self.run_git('mv', '.journal/foreign-journal.json', '.journal/renamed-journal.json')
        self.assert_save_refused('.journal/')
        self.assertIn('renamed-journal.json', self.run_git('diff', '--cached', '--name-only'))

    def test_local_commit_with_control_file_is_not_published_as_a_safe_save(self):
        self.commit_control_file()
        remote, head = self.remote_head(), self.run_git('rev-parse', 'HEAD')
        with self.assertRaisesRegex(gitstore.GitStorageError, r'Unpublished commits contain control files \(.journal/foreign-journal.json'):
            iw.git_publish(self.project, 'x', self.cfg)
        self.assertEqual(remote, self.remote_head())
        self.assertEqual(head, self.run_git('rev-parse', 'HEAD'), 'history is not rewritten')
        self.assertFalse(gitstore.status(self.clone)['remote_saved'])

    def test_ordinary_untracked_or_ignored_control_files_do_not_block_a_valid_save(self):
        (self.clone / '.journal').mkdir(exist_ok=True)
        (self.clone / '.journal' / 'scratch.tmp').write_text('ignored by .gitignore')
        (self.clone / '.journal' / 'interrupted.json.lock').write_text('x')
        with iw.git_save_guard(self.clone, 'valid save'):
            iw.create_candidate(self.clone, 'Max Muster')
        self.assertTrue(iw.git_publish(self.project, 'valid publish', self.cfg)['remote_saved'])
        self.assertNotIn('.journal', self.tree())
        self.assertEqual('ignored by .gitignore', (self.clone / '.journal' / 'scratch.tmp').read_text())

    def test_status_entries_hide_only_unstaged_control_files(self):
        (self.clone / '.journal').mkdir(exist_ok=True)
        (self.clone / '.journal' / 'a.tmp').write_text('x')
        self.assertEqual([], gitstore._status_entries(self.clone))
        self.run_git('add', '-f', '.journal/a.tmp')
        self.assertEqual([('A', ' ', '.journal/a.tmp')], gitstore._status_entries(self.clone))
        self.assertEqual(['.journal/a.tmp'], gitstore.staged_paths(self.clone))

    # ------------------------------------------------ control files inside unpublished commits (root, nested, intermediate)
    def commit_file(self, relative, text='fictional'):
        target = self.clone / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        self.run_git('add', '-f', '--', relative)
        self.run_git('commit', '-qm', 'add ' + relative)

    def real_candidate(self):
        """A valid candidate (so the workspace stays valid) whose folder can hold extra control-like files."""
        with iw.git_save_guard(self.clone, 'candidate'):
            cid = iw.create_candidate(self.clone, 'Erika Beispiel')['candidate_id']
        iw.git_publish(self.project, 'baseline', self.cfg)
        return cid

    def assert_publish_refused_for(self, relative):
        remote, head = self.remote_head(), self.run_git('rev-parse', 'HEAD')
        pushes = []
        real = gitstore.git

        def spy(args, **kw):
            if args[:1] == ['push']:
                pushes.append(args)
            return real(args, **kw)
        with mock.patch.object(gitstore, 'git', side_effect=spy):
            with self.assertRaisesRegex(gitstore.GitStorageError, 'Unpublished commits contain control files.*' + relative.replace('.', r'\.')):
                iw.git_publish(self.project, 'x', self.cfg)
        self.assertEqual([], pushes, 'no push')
        self.assertEqual(remote, self.remote_head())
        self.assertEqual(head, self.run_git('rev-parse', 'HEAD'), 'history not rewritten')

    def test_control_directory_is_recognized_by_complete_path_segments(self):
        for yes in ('.journal/a', 'candidates/c-x-12345678/.journal/pending.json', 'a/b/.journal/c/d', '.journal', '.zyris/a', 'candidates/x/.zyris/b'):
            self.assertTrue(gitstore.is_control_path(yes), yes)
        for no in ('.journal-notes/a', 'candidates/x/.journal-notes/b', 'zyris/c', 'my.journal/d', 'candidates/x/zyris.json', 'a/.journalx/b'):
            self.assertFalse(gitstore.is_control_path(no), no)

    def test_committed_candidate_control_file_is_refused_before_push(self):
        relative = f'candidates/{self.real_candidate()}/.journal/foreign-note.json'
        self.commit_file(relative)
        self.assert_publish_refused_for(relative)
        self.assertTrue((self.clone / relative).exists(), 'nothing deleted')

    def test_control_file_in_an_intermediate_commit_is_found_although_removed_again(self):
        relative = f'candidates/{self.real_candidate()}/.journal/foreign-note.json'
        self.commit_file(relative)
        self.run_git('rm', '-q', '--', relative)
        self.run_git('commit', '-qm', 'remove it again')
        self.assertNotIn('.journal', self.run_git('ls-tree', '-r', '--name-only', 'HEAD'), 'HEAD itself is clean')
        self.assert_publish_refused_for(relative)

    def test_similarly_named_ordinary_directories_are_not_blocked(self):
        cid = self.real_candidate()
        for relative in ('.journal-notes/a.txt', f'candidates/{cid}/.journal-notes/b.txt', 'zyris/c.txt', 'my.journal/d.txt'):
            self.commit_file(relative)
        self.assertTrue(iw.git_publish(self.project, 'ordinary names', self.cfg)['remote_saved'])
        tree = self.tree()
        for relative in ('.journal-notes/a.txt', f'candidates/{cid}/.journal-notes/b.txt', 'zyris/c.txt', 'my.journal/d.txt'):
            self.assertIn(relative, tree)

    def test_failing_history_queries_abort_before_the_push_and_are_not_read_as_empty(self):
        self.commit_file('notes/ordinary.txt')
        real = gitstore.git
        for failing in (['rev-list'], ['diff-tree'], ['rev-parse', '--verify', '-q', 'refs/remotes/origin/main']):
            pushes = []

            def broken(args, _failing=failing, **kw):
                if args[:1] == ['push']:
                    pushes.append(args)
                if list(args[:len(_failing)]) == _failing:
                    return subprocess.CompletedProcess(args, 128, '', 'fatal: simulated failure')
                return real(args, **kw)
            with mock.patch.object(gitstore, 'git', side_effect=broken):
                with self.assertRaisesRegex(gitstore.GitStorageError, 'nothing was pushed|Could not'):
                    iw.git_publish(self.project, 'x', self.cfg)
            self.assertEqual([], pushes, failing)
        self.assertNotIn('notes/ordinary.txt', self.tree())

    def test_first_push_without_an_existing_remote_branch_is_an_explicit_valid_state(self):
        bare = self.base / 'fresh.git'
        subprocess.run(['git', 'init', '-q', '--bare', '-b', 'main', str(bare)], check=True)
        solo = self.base / 'solo'
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(solo)], check=True)
        (solo / 'a.txt').write_text('fictional')
        subprocess.run(['git', '-C', str(solo), 'add', 'a.txt'], check=True)
        subprocess.run(['git', '-C', str(solo), 'commit', '-qm', 'first'], check=True)
        self.assertEqual([], gitstore.control_files_in_unpublished_commits(solo, 'main'))
        result = gitstore.publish(solo, {'fetch': str(bare), 'push': str(bare)})
        self.assertTrue(result['remote_saved'])
        self.assertEqual(result['commit'], subprocess.run(['git', '--git-dir', str(bare), 'rev-parse', 'refs/heads/main'], capture_output=True, text=True).stdout.strip())

    def test_first_push_with_a_nested_control_file_in_history_is_refused(self):
        bare = self.base / 'fresh2.git'
        subprocess.run(['git', 'init', '-q', '--bare', '-b', 'main', str(bare)], check=True)
        solo = self.base / 'solo2'
        (solo / 'candidates/x/.journal').mkdir(parents=True)
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(solo)], check=True)
        (solo / 'candidates/x/.journal/pending.json').write_text('fictional')
        subprocess.run(['git', '-C', str(solo), 'add', '-f', '--', 'candidates/x/.journal/pending.json'], check=True)
        subprocess.run(['git', '-C', str(solo), 'commit', '-qm', 'control'], check=True)
        with self.assertRaisesRegex(gitstore.GitStorageError, 'control files'):
            gitstore.publish(solo, {'fetch': str(bare), 'push': str(bare)})
        self.assertEqual('', subprocess.run(['git', '--git-dir', str(bare), 'for-each-ref'], capture_output=True, text=True).stdout)

    # ------------------------------------------------------------------ pull and the shared lock
    def git_calls(self):
        return len(self.gitlog.read_text().splitlines())

    def test_held_git_lock_stops_pull_before_any_git_action_with_a_busy_message(self):
        self.publish_state()
        self.remote_commit('x.txt', 'x')
        before, tree = self.git_calls(), sorted(p.name for p in self.clone.iterdir())
        with iw.git_lock(self.clone):
            with self.assertRaisesRegex(RuntimeError, 'busy'):
                iw.git_pull(self.project, self.cfg)
            with self.assertRaisesRegex(RuntimeError, 'busy'):
                iw.git_status(self.project, self.cfg)
            done = self.cli('git-pull', '--project', self.project, expect=1)
            self.assertIn('busy', done.stderr)
            self.assertIn('busy', self.cli('git-status', '--project', self.project, expect=1).stderr)
        self.assertEqual(before, self.git_calls(), 'no fetch/merge before the lock was held')
        self.assertEqual(tree, sorted(p.name for p in self.clone.iterdir()))
        self.assertFalse((self.clone / 'x.txt').exists())

    def test_pull_fast_forwards_after_release_through_the_cli(self):
        self.publish_state()
        self.remote_commit('x.txt', 'from remote')
        with iw.git_lock(self.clone):
            pass
        info = json.loads(self.cli('git-pull', '--project', self.project).stdout)
        self.assertEqual(0, info['behind'])
        self.assertEqual('from remote', (self.clone / 'x.txt').read_text())

    def test_pull_never_mixes_with_a_running_cooperating_save(self):
        import threading
        self.publish_state()
        self.remote_commit('x.txt', 'from remote')
        entered, release, outcome = threading.Event(), threading.Event(), {}

        def save():
            try:
                with iw.git_save_guard(self.clone, 'cooperating save'):
                    outcome['id'] = iw.create_candidate(self.clone, 'Anna Alpha')['candidate_id']
                    entered.set()
                    release.wait(20)
            except BaseException as exc:   # pragma: no cover
                outcome['error'] = exc
                entered.set()
        worker = threading.Thread(target=save)
        worker.start()
        self.assertTrue(entered.wait(20))
        with self.assertRaisesRegex(RuntimeError, 'busy'):
            iw.git_pull(self.project, self.cfg)
        self.assertFalse((self.clone / 'x.txt').exists(), 'the working tree was not changed by the pull during the save')
        release.set()
        worker.join(20)
        self.assertNotIn('error', outcome)
        self.assertFalse((self.clone / 'x.txt').exists())
        with self.assertRaisesRegex(gitstore.GitStorageError, 'unpublished'):
            iw.git_pull(self.project, self.cfg)           # after the save the local commit is still unpublished: pull refuses safely

    def test_pull_refuses_while_a_recovery_is_pending(self):
        self.publish_state()
        cid = self.save_candidate_id()
        with mock.patch.object(iw, 'apply_pending', side_effect=OSError('crash')):
            with self.assertRaises(RuntimeError):
                with iw.git_save_guard(self.clone, 'x'):
                    iw.finish(self.clone, cid, 'r1', '# run\n', '# s\n', expected_state_sha256=iw.snapshot(self.clone, cid)['state_sha256'],
                              status='completed', answered_count=1)
        self.remote_commit('x.txt', 'x')
        with self.assertRaisesRegex(gitstore.GitStorageError, 'Pending transactions'):
            iw.git_pull(self.project, self.cfg)
        self.assertFalse((self.clone / 'x.txt').exists())

    # helpers
    def publish_state(self):
        return iw.git_publish(self.project, 'baseline', self.cfg)

    def save_candidate_id(self):
        with iw.git_save_guard(self.clone, 'candidate'):
            cid = iw.create_candidate(self.clone, 'Erika Beispiel')['candidate_id']
        self.publish_state()
        return cid

    def remote_commit(self, name, text):
        other = self.second_clone()
        (other / name).write_text(text)
        subprocess.run(['git', '-C', str(other), 'add', '-A'], check=True)
        subprocess.run(['git', '-C', str(other), 'commit', '-qm', 'remote ' + name], check=True)
        subprocess.run(['git', '-C', str(other), 'push', '-q', 'origin', 'main'], check=True)


class JournalFolderGit(GitCase):
    """`.journal` in Git workspaces; historical `.zyris` control files stay out of every push; old layouts are refused first."""

    def setUp(self):
        super().setUp()
        self.setup_git()

    def targets(self):
        return iw.read_project_config(self.project, self.cfg)['git']['targets']

    def commit_file(self, relative):
        target = self.clone / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('fictional')
        self.run_git('add', '-f', '--', relative)
        self.run_git('commit', '-qm', 'add ' + relative)

    def real_candidate(self):
        with iw.git_save_guard(self.clone, 'candidate'):
            cid = iw.create_candidate(self.clone, 'Erika Beispiel')['candidate_id']
        iw.git_publish(self.project, 'baseline', self.cfg)
        return cid

    def test_all_git_paths_share_one_journal_git_lock_and_nothing_of_it_is_published(self):
        cid = self.real_candidate()
        self.assertTrue((self.clone / '.journal' / 'git.lock').is_file())
        self.assertEqual([], list(self.clone.rglob('.zyris')))
        with iw.git_lock(self.clone):
            with self.assertRaisesRegex(RuntimeError, 'busy'):
                with iw.core.file_lock(self.clone / '.journal' / 'git.lock'):    # the very same file
                    pass
            for call in (lambda: iw.git_pull(self.project, self.cfg), lambda: iw.git_publish(self.project, 'x', self.cfg),
                         lambda: iw.git_status(self.project, self.cfg)):
                with self.assertRaisesRegex(RuntimeError, 'busy'):
                    call()
            with self.assertRaisesRegex(RuntimeError, 'busy'):
                with iw.git_save_guard(self.clone, 'x'):
                    pass
        tree = subprocess.run(['git', '--git-dir', str(self.bare), 'ls-tree', '-r', '--name-only', 'main'], capture_output=True, text=True).stdout
        self.assertNotIn('.journal', tree)
        self.assertNotIn(f'candidates/{cid}/.journal', tree)
        self.assertEqual('.journal/\n', (self.clone / '.gitignore').read_text())

    def test_journal_files_are_detected_at_workspace_and_candidate_level_staged_and_committed(self):
        cid = self.real_candidate()
        for relative in ('.journal/foreign.json', f'candidates/{cid}/.journal/foreign.json'):
            (self.clone / relative).parent.mkdir(parents=True, exist_ok=True)
            (self.clone / relative).write_text('fictional')
            self.run_git('add', '-f', '--', relative)
            with self.assertRaisesRegex(gitstore.GitStorageError, 'staged: .*' + relative.replace('.', r'\.')):
                with iw.git_save_guard(self.clone, 'must not commit'):
                    pass
            with self.assertRaisesRegex(gitstore.GitStorageError, 'Staged changes exist'):
                iw.git_publish(self.project, 'x', self.cfg)
            self.run_git('commit', '-qm', 'foreign control commit')
            with self.assertRaisesRegex(gitstore.GitStorageError, 'Unpublished commits contain control files.*' + relative.replace('.', r'\.')):
                iw.git_publish(self.project, 'x', self.cfg)
            self.run_git('reset', '-q', '--soft', 'HEAD~1')      # test cleanup only (the tool never resets)
            self.run_git('reset', '-q', '--', relative)
            (self.clone / relative).unlink()

    def test_historical_zyris_control_files_are_never_pushed(self):
        cid = self.real_candidate()
        remote = self.remote_head()
        for relative in ('.zyris/old-journal.json', f'candidates/{cid}/.zyris/old-pending.json'):
            self.commit_file(relative)
            with self.assertRaisesRegex(gitstore.GitStorageError, 'Unpublished commits contain control files.*' + relative.replace('.', r'\.')):
                gitstore.publish(self.clone, self.targets())          # the publish guard itself, independent of the layout check
            self.assertEqual(remote, self.remote_head())
            self.run_git('reset', '-q', '--soft', 'HEAD~1')      # test cleanup only (the tool never resets)
            self.run_git('reset', '-q', '--', relative)
            (self.clone / relative).unlink()
            if (self.clone / relative).parent.exists() and not list((self.clone / relative).parent.iterdir()):
                (self.clone / relative).parent.rmdir()
        for name in ('.zyris-notes/a.txt', 'zyris/b.txt'):     # similar ordinary names are not control folders
            self.assertFalse(gitstore.is_control_path(name), name)
        for name in ('.zyris/a', 'x/.zyris/b', '.journal/a', 'x/.journal/b'):
            self.assertTrue(gitstore.is_control_path(name), name)

    def test_old_layout_in_a_git_workspace_is_refused_by_the_runtime_before_any_write(self):
        cid = self.real_candidate()
        (self.clone / '.zyris').mkdir()
        (self.clone / '.zyris' / 'pending.json').write_text('old journal')
        head, remote = self.run_git('rev-parse', 'HEAD'), self.remote_head()
        for args in (('candidate-create', '--name', 'Max Muster'), ('git-pull',), ('git-publish', '--message', 'x'), ('git-status',)):
            done = self.cli(*args[:1], '--project', self.project, *args[1:], expect=1)
            self.assertIn('Unsupported old control layout', done.stderr, args)
        self.assertEqual(head, self.run_git('rev-parse', 'HEAD'))
        self.assertEqual(remote, self.remote_head())
        self.assertEqual('old journal', (self.clone / '.zyris' / 'pending.json').read_text())
        self.assertEqual([cid], [c.name for c in (self.clone / 'candidates').iterdir() if not c.name.startswith('.')])

    def test_setup_into_a_clone_that_contains_old_control_files_is_refused_before_any_journal_or_pointer(self):
        other = self.second_clone()
        (other / '.zyris').mkdir()
        (other / '.zyris' / 'lock').write_text('old')
        (other / 'workspace.json').write_text('{}')
        subprocess.run(['git', '-C', str(other), 'add', '-f', '--', '.zyris/lock', 'workspace.json'], check=True)
        subprocess.run(['git', '-C', str(other), 'commit', '-qm', 'old layout'], check=True)
        subprocess.run(['git', '-C', str(other), 'push', '-q', 'origin', 'main'], check=True)
        remote = self.remote_head()
        project, cfg, clone = self.base / 'p-old', self.base / 'cfg-old', self.base / 'clone-old'
        project.mkdir()
        with self.assertRaisesRegex(ValueError, 'Unsupported old control layout'):
            iw.setup_project(project, 'git', clone, config_dir=cfg, remote=REMOTE)
        self.assertFalse((clone / '.journal').exists(), 'no lock or journal before the layout check')
        self.assertEqual([], list(cfg.glob('*.json')), 'no pointer')
        self.assertEqual(remote, self.remote_head())


class FormatCheckAfterClone(GitCase):
    """The cloned content is checked read-only before any lock, journal, commit, push or pointer (the clone itself is the only prior write)."""

    def seed_remote(self, files):
        other = self.second_clone()
        for name, text in files.items():
            (other / name).parent.mkdir(parents=True, exist_ok=True)
            (other / name).write_text(text)
        subprocess.run(['git', '-C', str(other), 'add', '-A'], check=True)
        subprocess.run(['git', '-C', str(other), 'commit', '-qm', 'seed'], check=True)
        subprocess.run(['git', '-C', str(other), 'push', '-q', 'origin', 'HEAD:refs/heads/main'], check=True)

    def fresh_target(self, name):
        project, cfg, clone = self.base / f'p-{name}', self.base / f'cfg-{name}', self.base / f'clone-{name}'
        project.mkdir()
        return project, cfg, clone

    def test_format_2_clone_without_any_zyris_marker_is_refused_before_every_write(self):
        manifest = json.dumps({'format': 'interview-coach-workspace', 'schema_version': 2, 'created_at': '2026-01-01T00:00:00Z'})
        self.seed_remote({'workspace.json': manifest, 'preferences.json': '{"schema_version": 2}', 'candidates/.gitkeep': ''})
        remote = self.remote_head()
        project, cfg, clone = self.fresh_target('f2')
        mark = len(self.gitlog.read_text().splitlines())          # git calls of the seeding are not part of the setup
        with self.assertRaisesRegex(ValueError, 'Unsupported workspace manifest'):
            iw.setup_project(project, 'git', clone, config_dir=cfg, remote=REMOTE)
        self.assertTrue(clone.is_dir(), 'the clone itself is the only prior write and is kept')
        self.assertFalse((clone / '.journal').exists(), 'no control folder, no lock')
        self.assertEqual(manifest, (clone / 'workspace.json').read_text(), 'cloned original content unchanged')
        self.assertEqual({'.git', 'workspace.json', 'preferences.json', 'candidates'}, {p.name for p in clone.iterdir()})
        self.assertEqual('', subprocess.run(['git', '-C', str(clone), 'status', '--porcelain'], capture_output=True, text=True).stdout)
        self.assertEqual(remote, self.remote_head(), 'no remote update')
        self.assertEqual([], list(cfg.glob('*.json')), 'no pointer')
        calls = self.gitlog.read_text().splitlines()[mark:]
        self.assertTrue([c for c in calls if c.startswith('clone ')], 'the clone happened')
        self.assertFalse([c for c in calls if c.split(' ')[0] in ('commit', 'push', 'add')], 'no commit, add or push after the clone')

    def test_genuinely_empty_repository_remains_initializable(self):
        result = self.setup_git()
        self.assertEqual('cloned', result['clone'])
        self.assertTrue(result['publish']['remote_saved'])
        self.assertTrue((self.clone / '.journal').is_dir())
        self.assertEqual([], iw.workspace_problems(self.clone))

    def test_valid_format_3_clone_is_reused(self):
        self.setup_git()
        project, cfg, clone = self.fresh_target('f3')
        result = iw.setup_project(project, 'git', clone, config_dir=cfg, remote=REMOTE)
        self.assertEqual('cloned', result['clone'])
        self.assertTrue(result['publish']['remote_saved'])
        self.assertEqual([], iw.workspace_problems(clone))
        self.assertEqual(3, json.loads((clone / 'workspace.json').read_text())['schema_version'])

    def test_clone_with_foreign_unrelated_files_is_refused_before_writes(self):
        self.seed_remote({'README.md': 'someone else repository'})
        project, cfg, clone = self.fresh_target('foreign')
        with self.assertRaisesRegex(ValueError, 'missing workspace.json'):
            iw.setup_project(project, 'git', clone, config_dir=cfg, remote=REMOTE)
        self.assertFalse((clone / '.journal').exists())
        self.assertEqual('someone else repository', (clone / 'README.md').read_text())

    def test_the_old_marker_test_stays_valid(self):
        self.assertTrue(hasattr(JournalFolderGit, 'test_setup_into_a_clone_that_contains_old_control_files_is_refused_before_any_journal_or_pointer'))


if __name__ == '__main__':
    unittest.main()
