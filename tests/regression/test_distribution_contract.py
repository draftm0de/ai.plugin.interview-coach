import json
import subprocess
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "skills/zyris-interview-coach"

class InstallationTests(unittest.TestCase):

    def test_repository_manifests_without_marketplace_or_version(self):
        subprocess.run(['python3', str(ROOT/'scripts/plugin.py'), 'check'], check=True, capture_output=True)
        for relative in ('plugin.json','.claude-plugin/plugin.json','.codex-plugin/plugin.json'):
            manifest=json.loads((ROOT/relative).read_text())
            self.assertEqual('interview-coach',manifest['name'])
            self.assertNotIn('version',manifest)
        self.assertEqual('Interview Coach',json.loads((ROOT/'.claude-plugin/plugin.json').read_text())['displayName'])
        for relative in ('.claude-plugin/marketplace.json','.agents/plugins/marketplace.json'):
            self.assertFalse((ROOT/relative).exists())
        self.assertTrue((SOURCE/'SKILL.md').is_file())

    def test_user_entrypoint_is_separate_from_developer_installer(self):
        installer = ROOT / "install.sh"
        self.assertFalse(installer.exists())
        readme = (ROOT / "README.md").read_text().lower()
        self.assertIn("docs/de/installation.md", readme)
        quickstart = readme.split("## schnellstart\n", 1)[1].split("\n## ", 1)[0]
        self.assertNotIn("git clone", quickstart)
        self.assertNotIn("bash install.sh", quickstart)
        self.assertNotIn("make install-", readme)


    def test_workspace_cli_bundled_and_in_sync(self):
        bundled = SOURCE / "scripts/interview_workspace.py"
        self.assertTrue(bundled.is_file())
        self.assertFalse((ROOT / "scripts/interview_workspace.py").exists(), "Runtime belongs only in the distributable skill")

    def test_storage_type_selection_precedes_path(self):
        setup = (SOURCE / "references/setup.md").read_text()
        self.assertIn("selection first, details second", setup)
        self.assertIn("Do not require a path in the first reply", setup)
        for choice in ("Lokales Verzeichnis", "Privates Git-Repository", "Dateien selbst verwalten", "Nicht speichern"):
            self.assertIn(choice, setup)

    def test_setup_confirmation_pattern(self):
        text = (SOURCE / "references/setup.md").read_text()
        for phrase in ("native choice/question tool", "weiterverwenden", "Wait for permission", "natural-language question"):
            self.assertIn(phrase, text)

    def test_setup_contract_present(self):
        text = (SOURCE / "references/setup.md").read_text().lower()
        for term in ("access verification", "cv", "linkedin", "local", "git", "chatgpt"):
            self.assertIn(term, text)
