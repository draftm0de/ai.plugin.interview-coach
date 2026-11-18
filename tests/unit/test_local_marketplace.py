import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('local_forwarder',ROOT/'scripts/local_marketplace.py')
engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
class LocalForwardingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        base=Path(self.tmp.name).resolve()
        self.plugin=base/'coach';self.plugin.mkdir()
        self.market=base/'market';(self.market/'scripts').mkdir(parents=True)
        (self.market/'scripts/local_plugins.py').write_text('# fixture')
        (self.market/'marketplace.json').write_text('{}')
        (self.market/'.local').mkdir()
        (self.market/'.local/marketplace.json').write_text(json.dumps({'sources':{'interview-coach':str(self.plugin)}}))
        (self.plugin/'plugin.json').write_text(json.dumps({'name':'interview-coach'}))
        (self.plugin/'.local').mkdir()
        (self.plugin/'.local/marketplace.json').write_text(json.dumps({'marketplace':str(self.market)}))
    def test_forwards_to_shared_catalog_with_dry_run_and_target(self):
        with patch.object(engine,'ROOT',self.plugin),patch.object(engine.sys,'argv',['local_marketplace.py','update-local','--target','codex','--dry-run']),patch.object(engine.subprocess,'run') as run:
            run.return_value.returncode=0
            self.assertEqual(0,engine.main())
            args=run.call_args.args[0]
            self.assertEqual(str(self.market/'scripts/local_plugins.py'),args[1])
            self.assertEqual(['update-local','--target','codex','--dry-run'],args[2:])
    def test_wrong_checkout_mapping_fails_without_calling_host(self):
        (self.market/'.local/marketplace.json').write_text(json.dumps({'sources':{'interview-coach':'../different'}}))
        with patch.object(engine,'ROOT',self.plugin),patch.object(engine.sys,'argv',['local_marketplace.py','install-local']),patch.object(engine.subprocess,'run') as run:
            self.assertEqual(1,engine.main());run.assert_not_called()
    def test_missing_configuration_never_chooses_a_random_marketplace(self):
        (self.plugin/'.local/marketplace.json').unlink()
        with patch.object(engine,'ROOT',self.plugin),patch.object(engine.sys,'argv',['local_marketplace.py','install-local']),patch.object(engine.subprocess,'run') as run:
            self.assertEqual(1,engine.main());run.assert_not_called()
