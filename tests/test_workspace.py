import json
from pathlib import Path
import tempfile
import unittest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
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
        finish(self.root, "2026-11-17-demo", "# Answer A", "# State B")
        self.assertEqual((self.root / "state.md").read_text(), "# State B")
        with self.assertRaises(FileExistsError):
            finish(self.root, "2026-11-17-demo", "# Answer C", "# State C")
        self.assertEqual((self.root / "state.md").read_text(), "# State B")

    def test_path_traversal_rejected(self):
        init_workspace(self.root, self.cfg)
        for bad in ("../outside", "/tmp/foo", "a/b", ".."):
            with self.assertRaises(ValueError):
                finish(self.root, bad, "run", "state")

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

if __name__ == "__main__":
    unittest.main()
