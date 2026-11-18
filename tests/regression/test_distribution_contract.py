import json
import subprocess
import tempfile
from pathlib import Path
import zipfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "skills/zyris-interview-coach"

class InstallationTests(unittest.TestCase):
    def test_plugin_metadata(self):
        chatgpt = json.loads((ROOT / "plugin.json").read_text())
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(['python3', str(ROOT / 'scripts/plugin.py'), 'build', '--output', td], check=True, capture_output=True)
            with zipfile.ZipFile(Path(td) / 'zyris-interview-coach-claude-plugin.zip') as package:
                claude = json.loads(package.read('.claude-plugin/plugin.json'))
            expected = {str(p.relative_to(ROOT)): p.read_bytes() for p in SOURCE.rglob('*')
                        if p.is_file() and '__pycache__' not in p.parts}
            for archive in Path(td).glob('*.zip'):
                with zipfile.ZipFile(archive) as package:
                    runtime = {name: package.read(name) for name in package.namelist() if name.startswith('skills/')}
                    self.assertEqual(expected, runtime, archive.name)
                    self.assertFalse(any(name.startswith('.claude/skills/') for name in package.namelist()))
        self.assertEqual('skills', chatgpt['extensions']['io.zyris.distribution']['skillRoot'])
        self.assertFalse((ROOT / '.claude/skills').exists())
        self.assertFalse((ROOT / '.codex-plugin/plugin.json').exists())
        self.assertFalse((ROOT / '.claude-plugin/plugin.json').exists())
        for manifest in (chatgpt, claude):
            self.assertEqual(manifest["name"], "zyris-interview-coach")
            self.assertEqual(manifest["author"]["name"], "Peter Fux")
            self.assertEqual(manifest["author"]["url"], "https://draftmode.io")
            self.assertIn("Job Coach", manifest["keywords"])
        ui = chatgpt["extensions"]["com.openai"]["interface"]
        self.assertEqual(ui["developerName"], "draftmode")
        self.assertEqual(ui["websiteURL"], "https://draftmode.io")
        self.assertTrue((ROOT / "assets/icon.png").is_file())

    def test_user_entrypoint_is_separate_from_developer_installer(self):
        installer = ROOT / "install.sh"
        self.assertTrue(installer.is_file())
        readme = (ROOT / "README.md").read_text().lower()
        self.assertIn("docs/de/installation.md", readme)
        quickstart = readme.split("## schnellstart\n", 1)[1].split("\n## ", 1)[0]
        self.assertNotIn("git clone", quickstart)
        self.assertNotIn("bash install.sh", quickstart)
        self.assertNotIn("make install-", readme)

    def test_portable_package_has_no_private_files(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "zyris-interview-coach-chatgpt-plugin.zip"
            subprocess.run(["python3", str(ROOT / "scripts/plugin.py"),
                            "build", "--output", td], check=True, capture_output=True)
            with zipfile.ZipFile(dest) as z:
                names = z.namelist()
                self.assertIn("skills/zyris-interview-coach/SKILL.md", names)
                self.assertIn("skills/zyris-interview-coach/references/setup.md", names)
                self.assertIn("skills/zyris-interview-coach/scripts/interview_workspace.py", names)
                self.assertFalse(any("/candidate/" in n or "/runs/" in n or "/jobs/" in n for n in names))

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
