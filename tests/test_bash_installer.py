import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "install.sh"

class BashInstallerTests(unittest.TestCase):
    def test_bash_syntax(self):
        subprocess.run(["bash", "-n", str(INSTALLER)], check=True)

    def test_claude_install_and_idempotent_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, CLAUDE_HOME=str(Path(tmp) / "claude"))
            subprocess.run(["bash", str(INSTALLER), "claude", "--yes"], env=env, check=True, capture_output=True)
            dest = Path(tmp) / "claude/skills/zyris-interview-coach"
            self.assertTrue((dest / "SKILL.md").exists())
            self.assertTrue((dest / "references/setup.md").exists())
            (dest / "obsolete.txt").write_text("old")
            subprocess.run(["bash", str(INSTALLER), "claude", "--yes"], env=env, check=True, capture_output=True)
            self.assertFalse((dest / "obsolete.txt").exists())

    def test_codex_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, CODEX_HOME=str(Path(tmp) / "agents"))
            subprocess.run(["bash", str(INSTALLER), "codex", "--yes"], env=env, check=True, capture_output=True)
            self.assertTrue((Path(tmp) / "agents/skills/zyris-interview-coach/SKILL.md").exists())

    def test_claude_chat_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Work on an isolated copy to avoid writing to the checkout.
            import shutil
            work = Path(tmp) / "repo"
            shutil.copytree(ROOT / ".claude", work / ".claude")
            shutil.copytree(ROOT / "scripts", work / "scripts")
            shutil.copy2(INSTALLER, work / "install.sh")
            subprocess.run(["bash", str(work / "install.sh"), "claude-chat"], check=True, capture_output=True)
            package = work / "dist/zyris-interview-coach.zip"
            self.assertTrue(package.is_file())
            with zipfile.ZipFile(package) as z:
                self.assertIn("zyris-interview-coach/SKILL.md", z.namelist())

    def test_noninteractive_without_target_rejected(self):
        cp = subprocess.run(["bash", str(INSTALLER)], input="", text=True, capture_output=True)
        self.assertEqual(cp.returncode, 2)
