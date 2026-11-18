import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("interview_behavior", ROOT / "tests/behavior/run.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

class BehaviorHarnessTests(unittest.TestCase):
    def test_cases_are_fictional_and_complete(self):
        cases = json.loads((ROOT / "tests/behavior/fixtures/quality-cases.json").read_text())
        self.assertGreaterEqual(len(cases), 4)
        self.assertEqual(len({c["id"] for c in cases}), len(cases))
        for case in cases:
            self.assertTrue(case["prompt"])
            self.assertTrue(case["must_contain_any"])
            self.assertIn("required_groups", case)

    def test_scoring_feedback_passes(self):
        case = {"must_contain_any": ["Gesamtbewertung"], "must_not_contain": [],
                "required_groups": [["/10"], ["Einzelbewertung"], ["gut"], ["verbessern"]]}
        answer = "Gesamtbewertung 7/10. Einzelbewertung: 8/10. Was war gut? Klar. Was verbessern? Mehr Details."
        self.assertEqual(module.check(case, answer), [])

    def test_missing_dimension_fails(self):
        case = {"must_contain_any": ["Gesamtbewertung"], "must_not_contain": [],
                "required_groups": [["Einzelbewertung"], ["verbessern"]]}
        errors = module.check(case, "Gesamtbewertung 7/10. Gut.")
        self.assertEqual(len(errors), 2)

    def test_forbidden_storage_claim_fails(self):
        case = {"must_contain_any": ["Zusammenfassung"],
                "must_not_contain": ["state.md aktualisiert"], "required_groups": []}
        self.assertTrue(module.check(case, "Zusammenfassung. state.md aktualisiert."))

    def test_stop_accepts_valid_completion_without_summary_heading(self):
        cases = json.loads((ROOT / "tests/behavior/fixtures/quality-cases.json").read_text())
        case = next(c for c in cases if c["id"] == "stop_without_storage")
        answer = ("Das Interview ist beendet (stopped_early). Es wurde genau eine Frage "
                  "beantwortet. Der Wortlaut fehlt, daher keine Bewertung möglich. "
                  "Es wurden keine Dateien erstellt und nichts gespeichert.")
        self.assertEqual(module.check(case, answer), [])

    def test_stop_rejects_false_persistence_claim(self):
        cases = json.loads((ROOT / "tests/behavior/fixtures/quality-cases.json").read_text())
        case = next(c for c in cases if c["id"] == "stop_without_storage")
        answer = ("Das Interview ist beendet. Genau eine Frage beantwortet. "
                  "Nicht gespeichert. state.md aktualisiert.")
        self.assertTrue(module.check(case, answer))

    def test_skill_context_includes_evaluation_and_research(self):
        context = module.skill_context()
        self.assertIn("Gesamtbewertung", context)
        self.assertIn("interviewer", context.lower())

if __name__ == "__main__":
    unittest.main()
