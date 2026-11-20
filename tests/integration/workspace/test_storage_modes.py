"""R1/R19: only local storage; removed Git entry points never mutate data."""
import json
from tests.support.coach import Base, iw, snapshot


class StorageModes(Base):
    def test_git_setup_is_refused_before_any_write(self):
        before = snapshot(self.base)
        with self.assertRaisesRegex(ValueError, 'Git storage is removed'):
            iw.setup_project(self.project, 'git', self.root, config_dir=self.cfg)
        self.assertEqual(before, snapshot(self.base))
        self.cli('project-init', '--project', self.project, '--storage', 'git', '--path', self.root, expect=2)
        self.assertEqual(before, snapshot(self.base))

    def test_removed_git_commands_and_parameters_are_rejected(self):
        before = snapshot(self.base)
        for command in ('git-status', 'git-pull', 'git-publish'):
            self.cli(command, '--project', self.project, expect=2)
        for args in (('--remote', 'https://github.com/example/private.git'), ('--attest-private',)):
            self.cli('project-init', '--project', self.project, '--storage', 'local', '--path', self.root, *args, expect=2)
        self.assertEqual(before, snapshot(self.base))

    def test_existing_git_pointer_is_preserved_and_cannot_be_switched_implicitly(self):
        self.setup_local()
        pointer = iw.project_config_path(self.project, self.cfg)
        data = json.loads(pointer.read_text())
        data['storage'] = 'git'
        data['git'] = {'remote': 'https://github.com/example/private.git', 'visibility': 'private'}
        pointer.write_text(json.dumps(data))
        before = snapshot(self.base)
        for command in ('project-show', 'candidate-list'):
            result = self.cli(command, '--project', self.project, expect=1)
            self.assertIn('Git storage is no longer supported', result.stderr)
        for switch in (False, True):
            with self.assertRaisesRegex(ValueError, 'Git storage is no longer supported'):
                iw.setup_project(self.project, 'local', self.base / 'new-target', config_dir=self.cfg, switch=switch)
        self.assertEqual(before, snapshot(self.base))

    def test_local_setup_and_no_storage_contract_remain_available(self):
        self.setup_local()
        cid = self.candidate()
        self.cli('validate', '--project', self.project)
        self.assertEqual(cid, iw.snapshot(self.root, cid)['candidate']['candidate_id'])
        before = snapshot(self.base)
        with self.assertRaisesRegex(ValueError, 'Nicht speichern creates no workspace'):
            iw.setup_project(self.project, 'none', self.base / 'unused', config_dir=self.cfg)
        self.assertEqual(before, snapshot(self.base))
