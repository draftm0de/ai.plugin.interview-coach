import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
ROOT=next(p for p in Path(__file__).resolve().parents if (p / 'Makefile').is_file())
spec=importlib.util.spec_from_file_location('coach_metadata', ROOT/'scripts/plugin.py')
engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
class ImportMetadataTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        for name in ('plugin.json','assets','skills'):
            source=ROOT/name;dest=self.root/name
            if source.is_dir():shutil.copytree(source,dest)
            else:shutil.copy2(source,dest)
    def test_dangling_catalog_paths_block_sync_before_writes(self):
        for relative in ('marketplace.json','.claude-plugin/marketplace.json','.agents/plugins/marketplace.json','.codex-plugin/marketplace.json'):
            path=self.root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.symlink_to(self.root/'missing')
            with self.assertRaisesRegex(ValueError,'must not own'):
                engine.sync(root=self.root)
            self.assertFalse((self.root/'.claude-plugin/plugin.json').exists())
            self.assertTrue(path.is_symlink());path.unlink()

    def test_host_local_sources_block_sync_without_writes(self):
        for relative in ('.claude/skills','.agents/skills'):
            path=self.root/relative;path.parent.mkdir(exist_ok=True)
            for symlink in (False,True):
                if symlink: path.symlink_to(self.root/'missing')
                else: path.mkdir()
                with self.assertRaisesRegex(ValueError,'Unsupported host-local'):
                    engine.sync(root=self.root)
                self.assertFalse((self.root/'.claude-plugin/plugin.json').exists())
                if symlink: path.unlink()
                else: path.rmdir()

    def test_unsupported_metadata_rejected_without_writes(self):
        path = self.root/'plugin.json'; original = json.loads(path.read_text())
        for change in ({'catalogs':True},{'skillRoot':'old/skills'},{'files':'invalid'},{'foo':1}):
            value = json.loads(json.dumps(original));value['extensions']['io.zyris.distribution']=change
            path.write_text(json.dumps(value))
            before = {str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
            with self.assertRaisesRegex(ValueError,'Unsupported distribution'):
                engine.sync(root=self.root)
            self.assertEqual(before,{str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        path.write_text(json.dumps(original))
        for name in ('marketplace.json','.codex-plugin/marketplace.json'):
            target=self.root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text('{}')
            before = {str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
            with self.assertRaisesRegex(ValueError,'must not own'):
                engine.sync(root=self.root)
            self.assertEqual(before,{str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
            target.unlink()

    def test_sync_and_read_only_drift_check(self):
        engine.sync(root=self.root)
        target=self.root/'.claude-plugin/plugin.json';target.write_text('{}')
        with self.assertRaisesRegex(ValueError,'stale'):engine.sync(check=True,root=self.root)
        self.assertEqual('{}',target.read_text())
        engine.sync(root=self.root)
        self.assertTrue(engine.sync(check=True,root=self.root)['valid'])
    def test_version_and_separate_marketplace_are_rejected(self):
        manifest=json.loads((self.root/'plugin.json').read_text());manifest['version']='1.0.0'
        (self.root/'plugin.json').write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError,'version'):engine.expected(self.root)
        del manifest['version'];(self.root/'plugin.json').write_text(json.dumps(manifest))
        market=self.root/'.claude-plugin/marketplace.json';market.parent.mkdir();market.write_text('{}')
        with self.assertRaisesRegex(ValueError,'must not own'):engine.sync(root=self.root)
    def test_symlink_target_is_not_written(self):
        external=self.root/'outside';external.mkdir()
        (self.root/'.claude-plugin').symlink_to(external,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'symlink'):engine.sync(root=self.root)
        self.assertEqual([],list(external.iterdir()))
