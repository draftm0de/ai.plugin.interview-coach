import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
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
