from pathlib import Path
import re
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'Makefile').is_file())
SKILL = ROOT / "skills/interview-coach"
class SkillContractTests(unittest.TestCase):
    def test_current_storage_contract_has_no_alternative_path_manifest(self):
        for path in list(SKILL.rglob('*.md')) + list((ROOT/'docs').rglob('*.md')):
            self.assertNotIn('workspace.yaml',path.read_text(),str(path))
        behavior = (ROOT/'tests/behavior/run.py').read_text()
        self.assertIn('references/technical-interview.md',behavior)
        self.assertIn('SKILL = skill_context()', (ROOT/'tests/behavior/run_smoke.py').read_text())

    def test_skill_name_and_references(self):
        text = (SKILL / "SKILL.md").read_text()
        self.assertTrue(text.startswith("---" + chr(10)))
        self.assertIn("name: interview-coach", text)
        for name in ("research", "training", "evaluation", "storage", "technical-interview", "setup", "session-control"):
            self.assertTrue((SKILL / "references" / (name + ".md")).is_file(), name)

    def test_no_personal_baseline_in_public_skill(self):
        for p in SKILL.rglob("*.md"):
            content = p.read_text().lower()
            for private_term in ("peter fux", "armin thurner", "birgit rachinger", "draftm0de/private.job-interview"):
                self.assertNotIn(private_term, content, f"private data in {p}")

    def test_technical_contract_covers_execution_safety(self):
        content = (SKILL / 'references' / 'technical-interview.md').read_text().lower()
        for phrase in ('coding', 'debugging', 'sandbox', 'test', 'security', 'not executed', 'do not leak the reference solution', 'never execute untrusted candidate code'):
            self.assertIn(phrase, content)

    def test_early_stop_and_language_contract(self):
        content = (SKILL / "references/session-control.md").read_text()
        for term in ("preferences.json", "interface_language", "interview_language", "stopped_early", "pause", "stop"):
            self.assertIn(term, content)
        main = (SKILL / "SKILL.md").read_text()
        self.assertIn("Before the first response", main)
        self.assertIn("immediately end questioning", main)

    def test_reusable_job_research_and_interviewer_intake(self):
        research = (SKILL / "references/research.md").read_text()
        training = (SKILL / "references/training.md").read_text()
        main = (SKILL / "SKILL.md").read_text()
        for artifact in ("job.md", "research.md", "preparation.md"):
            self.assertIn(artifact, research)
        self.assertIn("Mit wem führst du das Bewerbungsgespräch?", research)
        self.assertIn("read these artifacts first", research)
        self.assertIn("Always ask who will conduct the interview", main)
        self.assertIn("role and seniority", training)

    def test_structured_role_aware_answer_feedback(self):
        evaluation = (SKILL / "references/evaluation.md").read_text()
        training = (SKILL / "references/training.md").read_text()
        for phrase in ("Gesamtbewertung", "Einzelbewertung", "Was besonders gut war", "Was ich verbessern würde", "mock"):
            self.assertIn(phrase, evaluation)
        self.assertIn("Gesamtbewertung x/10", training)
        self.assertIn("role-adapted", training)

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
