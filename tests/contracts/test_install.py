import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'Makefile').is_file())
spec = importlib.util.spec_from_file_location('coach_metadata', ROOT / 'scripts/plugin.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)


class ImportMetadataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ('plugin.json', 'assets', 'skills'):
            source, dest = ROOT / name, self.root / name
            if source.is_dir():
                shutil.copytree(source, dest)
            else:
                shutil.copy2(source, dest)
        patcher = patch.object(engine, 'ROOT', self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def snapshot(self):
        return {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def test_catalogs_and_host_local_skills_block_sync_without_writes(self):
        for relative in ('marketplace.json', '.claude-plugin/marketplace.json', '.agents/plugins/marketplace.json'):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{}')
            before = self.snapshot()
            with self.assertRaisesRegex(ValueError, 'Unsupported host-local skill layout'):
                engine.repository_metadata()
            self.assertEqual(before, self.snapshot())
            path.unlink()
        for relative in ('.claude/skills', '.agents/skills'):
            path = self.root / relative
            path.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, 'Unsupported host-local'):
                engine.repository_metadata()
            self.assertFalse((self.root / '.claude-plugin/plugin.json').exists())
            path.rmdir()

    def test_unsupported_metadata_rejected_without_writes(self):
        path = self.root / 'plugin.json'
        original = json.loads(path.read_text())
        for change in ({'catalogs': True}, {'skillRoot': 'old/skills'}, {'files': 'invalid'}, {'foo': 1}):
            value = json.loads(json.dumps(original))
            value['extensions']['io.zyris.distribution'] = change
            path.write_text(json.dumps(value))
            before = self.snapshot()
            with self.assertRaises(ValueError):
                engine.repository_metadata()
            self.assertEqual(before, self.snapshot())

    def test_sync_and_read_only_drift_check(self):
        engine.repository_metadata()
        target = self.root / '.claude-plugin/plugin.json'
        target.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'stale'):
            engine.repository_metadata(check=True)
        self.assertEqual('{}', target.read_text())
        engine.repository_metadata()
        self.assertTrue(engine.repository_metadata(check=True)['valid'])

    def test_version_is_rejected(self):
        manifest = json.loads((self.root / 'plugin.json').read_text())
        manifest['version'] = '1.0.0'
        (self.root / 'plugin.json').write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'version'):
            engine.configuration()

    def test_symlink_target_is_not_written(self):
        external = self.root / 'outside'
        external.mkdir()
        (self.root / '.claude-plugin').symlink_to(external, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'ymlink'):
            engine.repository_metadata()
        self.assertEqual([], list(external.iterdir()))


if __name__ == '__main__':
    unittest.main()
