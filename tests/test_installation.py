import subprocess
import tempfile
from pathlib import Path
import zipfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".claude/skills/zyris-interview-coach"

class InstallationTests(unittest.TestCase):
    def test_makefile_targets(self):
        makefile = (ROOT / "Makefile").read_text()
        for name in ("install-claude:", "install-codex:", "install-chatgpt:", "test:"):
            self.assertIn(name, makefile)

    def test_portable_package_has_no_private_files(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "skill.zip"
            subprocess.run(["python3", str(ROOT / "scripts/package_skill.py"),
                            "--source", str(SOURCE), "--output", str(dest)], check=True, capture_output=True)
            with zipfile.ZipFile(dest) as z:
                names = z.namelist()
                self.assertIn("zyris-interview-coach/SKILL.md", names)
                self.assertIn("zyris-interview-coach/references/setup.md", names)
                self.assertFalse(any("/candidate/" in n or "/runs/" in n or "/jobs/" in n for n in names))

    def test_setup_contract_present(self):
        text = (SOURCE / "references/setup.md").read_text().lower()
        for term in ("access verification", "cv", "linkedin", "local", "git", "chatgpt"):
            self.assertIn(term, text)
