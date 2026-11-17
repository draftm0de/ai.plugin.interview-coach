import subprocess
import tempfile
from pathlib import Path
import zipfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".claude/skills/zyris-interview-coach"

class InstallationTests(unittest.TestCase):
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

    def test_setup_confirmation_pattern(self):
        text = (SOURCE / "references/setup.md").read_text()
        for phrase in ("Ja, verwenden", "Nein, anderen Wert angeben", "Wait for confirmation", "plain text chat"):
            self.assertIn(phrase, text)

    def test_setup_contract_present(self):
        text = (SOURCE / "references/setup.md").read_text().lower()
        for term in ("access verification", "cv", "linkedin", "local", "git", "chatgpt"):
            self.assertIn(term, text)
