from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".claude/skills/zyris-interview-coach"
class SkillContractTests(unittest.TestCase):
    def test_skill_name_and_references(self):
        text = (SKILL / "SKILL.md").read_text()
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("name: zyris-interview-coach", text)
        for name in ("research", "training", "evaluation", "storage", "technical-interview"):
            self.assertTrue((SKILL / "references" / (name + ".md")).is_file(), name)

    def test_no_personal_baseline_in_public_skill(self):
        for p in SKILL.rglob("*.md"):
            content = p.read_text().lower()
            for private_term in ("peter fux", "armin thurner", "birgit rachinger"):
                self.assertNotIn(private_term, content, f"private data in {p}")

    def test_docs_cover_cli_and_storage(self):
        readme = (ROOT / "README.md").read_text().lower()
        for term in ("claude", "codex", "chatgpt", "local", "github", "init", "pytest"):
            self.assertIn(term, readme)

if __name__ == "__main__":
    unittest.main()
