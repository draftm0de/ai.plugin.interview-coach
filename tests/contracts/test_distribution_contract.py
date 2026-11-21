import json
import subprocess
import tempfile
from pathlib import Path
import unittest

from tests.support.payload import build_payload

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'Makefile').is_file())
SOURCE = ROOT / "skills/interview-coach"

class InstallationTests(unittest.TestCase):

    def test_repository_manifests_without_marketplace_or_version(self):
        subprocess.run(['python3', str(ROOT/'scripts/plugin.py'), 'check'], check=True, capture_output=True)
        for relative in ('plugin.json','.claude-plugin/plugin.json'):
            manifest=json.loads((ROOT/relative).read_text())
            self.assertEqual('interview-coach',manifest['name'])
            self.assertNotIn('version',manifest)
        self.assertFalse((ROOT/'.codex-plugin').exists(), 'the Codex manifest is generated into the install payload only')
        self.assertEqual('Interview Coach',json.loads((ROOT/'.claude-plugin/plugin.json').read_text())['displayName'])
        for relative in ('.claude-plugin/marketplace.json','.agents/plugins/marketplace.json'):
            self.assertFalse((ROOT/relative).exists())
        self.assertTrue((SOURCE/'SKILL.md').is_file())
        self.assertFalse((ROOT/'skills/zyris-interview-coach').exists())
        self.assertEqual('./skills/interview-coach/SKILL.md',
                         json.loads((ROOT/'plugin.json').read_text())['extensions']['com.openai']['onboardingSkill'])

    def test_user_entrypoint_is_separate_from_developer_installer(self):
        installer = ROOT / "install.sh"
        self.assertFalse(installer.exists())
        readme = (ROOT / "README.md").read_text().lower()
        self.assertIn("docs/de/installation.md", readme)
        quickstart = readme.split("## schnellstart\n", 1)[1].split("\n## ", 1)[0]
        self.assertNotIn("git clone", quickstart)
        self.assertNotIn("bash install.sh", quickstart)
        self.assertNotIn("make install-", readme)


    def test_workspace_runtime_is_shared_not_in_root_scripts(self):
        self.assertTrue((ROOT / "skills/_shared/scripts/interview_workspace.py").is_file())
        self.assertFalse((ROOT / "scripts/interview_workspace.py").exists(), "Runtime belongs only in the distributable skills")
        self.assertFalse((SOURCE / "scripts").exists())

    def test_all_five_skills_declared_by_manifest_layout(self):
        names = sorted(p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md"))
        self.assertEqual(["candidate-create", "candidate-training", "interview-coach", "job-create", "job-training"], names)
        with tempfile.TemporaryDirectory() as tmp:
            codex = json.loads((build_payload(Path(tmp)) / ".codex-plugin/plugin.json").read_text())
        self.assertEqual("./skills/", codex["skills"])
        self.assertEqual("Interview Coach", codex["interface"]["displayName"])
