from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".claude/skills/zyris-interview-coach"
class SkillContractTests(unittest.TestCase):
    def test_skill_name_and_references(self):
        text = (SKILL / "SKILL.md").read_text()
        self.assertTrue(text.startswith("---" + chr(10)))
        self.assertIn("name: zyris-interview-coach", text)
        for name in ("research", "training", "evaluation", "storage", "technical-interview", "setup"):
            self.assertTrue((SKILL / "references" / (name + ".md")).is_file(), name)

    def test_no_personal_baseline_in_public_skill(self):
        for p in SKILL.rglob("*.md"):
            content = p.read_text().lower()
            for private_term in ("peter fux", "armin thurner", "birgit rachinger", "draftm0de/private.job-interview"):
                self.assertNotIn(private_term, content, f"private data in {p}")

    def test_technical_contract_covers_execution_safety(self):
        content = (SKILL / 'references' / 'technical-interview.md').read_text().lower()
        for phrase in ('coding', 'debugging', 'sandbox', 'test', 'security'):
            self.assertIn(phrase, content)

    def test_neutral_first_run(self):
        setup = (SKILL / 'references/setup.md').read_text().lower()
        self.assertIn('do not silently select a default private repository', setup)
        readme = (ROOT / 'README.md').read_text()
        self.assertNotIn('draftm0de/private.job-interview', readme)

    def test_docs_cover_cli_and_storage(self):
        readme = (ROOT / "README.md").read_text().lower()
        for term in ("claude", "codex", "chatgpt", "local", "github", "init", "pytest"):
            self.assertIn(term, readme)

if __name__ == "__main__":
    unittest.main()
