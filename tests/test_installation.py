import json
import subprocess
import tempfile
from pathlib import Path
import zipfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".claude/skills/zyris-interview-coach"

class InstallationTests(unittest.TestCase):
    def test_plugin_metadata(self):
        chatgpt = json.loads((ROOT / "plugin.json").read_text())
        claude = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
        for manifest in (chatgpt, claude):
            self.assertEqual(manifest["name"], "zyris-interview-coach")
            self.assertEqual(manifest["author"]["name"], "Peter Fux")
            self.assertEqual(manifest["author"]["url"], "https://draftmode.io")
            self.assertIn("Job Coach", manifest["keywords"])
        ui = chatgpt["extensions"]["com.openai"]["interface"]
        self.assertEqual(ui["developerName"], "draftmode")
        self.assertEqual(ui["websiteURL"], "https://draftmode.io")
        self.assertTrue((ROOT / "assets/icon.png").is_file())

    def test_bash_installer_is_primary(self):
        installer = ROOT / "install.sh"
        self.assertTrue(installer.is_file())
        readme = (ROOT / "README.md").read_text().lower()
        self.assertIn("bash install.sh", readme)
        self.assertNotIn("make install-", readme)

    def test_portable_package_has_no_private_files(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "skill.zip"
            subprocess.run(["python3", str(ROOT / "scripts/package_skill.py"),
                            "--source", str(SOURCE), "--output", str(dest)], check=True, capture_output=True)
            with zipfile.ZipFile(dest) as z:
                names = z.namelist()
                self.assertIn("zyris-interview-coach/SKILL.md", names)
                self.assertIn("zyris-interview-coach/references/setup.md", names)
                self.assertIn("zyris-interview-coach/scripts/interview_workspace.py", names)
                self.assertFalse(any("/candidate/" in n or "/runs/" in n or "/jobs/" in n for n in names))

    def test_workspace_cli_bundled_and_in_sync(self):
        bundled = SOURCE / "scripts/interview_workspace.py"
        self.assertTrue(bundled.is_file())
        self.assertEqual(bundled.read_bytes(), (ROOT / "scripts/interview_workspace.py").read_bytes())

    def test_storage_type_selection_precedes_path(self):
        setup = (SOURCE / "references/setup.md").read_text()
        self.assertIn("selection first, details second", setup)
        self.assertIn("without requiring a path in that first reply", setup)
        for choice in ("Lokales Verzeichnis", "Privates Git-Repository", "Dateien selbst verwalten"):
            self.assertIn(choice, setup)

    def test_setup_confirmation_pattern(self):
        text = (SOURCE / "references/setup.md").read_text()
        for phrase in ("Ja, verwenden", "Nein, anderen Wert angeben", "Wait for confirmation", "plain text chat"):
            self.assertIn(phrase, text)

    def test_setup_contract_present(self):
        text = (SOURCE / "references/setup.md").read_text().lower()
        for term in ("access verification", "cv", "linkedin", "local", "git", "chatgpt"):
            self.assertIn(term, text)
