import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests/behavior"))
SPEC = importlib.util.spec_from_file_location("run_journey", ROOT / "tests/behavior/run_journey.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class JourneyRunnerTests(unittest.TestCase):
    def test_fixture_has_three_questions_revision_and_stop(self):
        j = module.load_journey("teamlead_coaching")
        self.assertEqual([s["id"] for s in j["steps"]],
                         ["priority", "ownership", "incident", "revision", "stop"])
        self.assertEqual(j["steps"][-1]["user"], "stop")

    def test_prompt_replays_actual_answers_in_order(self):
        p = module.build_prompt("SKILL", "CONTEXT",
                                [("user", "first"), ("assistant", "feedback")], "stop")
        self.assertLess(p.index("first"), p.index("feedback"))
        self.assertLess(p.index("feedback"), p.index("LATEST USER MESSAGE"))
        self.assertIn("stop", p)

    def test_mock_runner_writes_artifacts_and_checks_each_step(self):
        j = module.load_journey("teamlead_coaching")
        def fake(cli, prompt, timeout):
            if "LATEST USER MESSAGE:\nstop" in prompt:
                return 0, ("Interview beendet, drei Fragen und ein zweiter Versuch. "
                           "Nichts gespeichert. Noch nicht stabil."), ""
            if "Vergleiche diese neue eigene" in prompt.split("LATEST USER MESSAGE:")[-1]:
                return 0, ("Die verbesserte Antwort ist konkreter als die ursprüngliche. "
                           "Risiko und Entscheidung sind klarer, aber noch nicht stabil."), ""
            if "Frage 3:" in prompt.split("LATEST USER MESSAGE:")[-1]:
                return 0, "Gesamtbewertung 7/10. Einzelbewertung: Incident und Betrieb.", ""
            if "Frage 2:" in prompt.split("LATEST USER MESSAGE:")[-1]:
                return 0, "Gesamtbewertung 7/10. Einzelbewertung: Entscheidung und Freigabe.", ""
            return 0, ("Gesamtbewertung 3/10. Einzelbewertung: Risiko für den Betrieb. "
                       "Was verbessern? Mehr Details."), ""
        with tempfile.TemporaryDirectory() as d:
            results = module.execute_journey(j, "codex", Path(d), 1, runner=fake)
            self.assertEqual(len(results), 5)
            self.assertTrue(all(r["passed"] for r in results), results)
            self.assertTrue((Path(d) / "result.json").exists())
            self.assertTrue((Path(d) / "05-stop.txt").exists())

    def test_stop_accepts_realistic_codex_wording(self):
        stop = module.load_journey("teamlead_coaching")["steps"][-1]
        answer = ("Das Interview ist beendet (stopped_early). Bearbeitet wurden "
                  "drei unterschiedliche Fragen und eine Wiederholung von Frage 1. "
                  "Ein stabiler Kompetenzstatus ist nicht belegt. "
                  "Keine privaten Dateien gelesen oder geschrieben, "
                  "nichts durch den Skill gespeichert.")
        self.assertEqual(module.check_step(stop, answer), [])

    def test_stop_rejects_missing_no_storage_or_stability(self):
        stop = module.load_journey("teamlead_coaching")["steps"][-1]
        answer = ("Interview beendet. Drei Fragen und eine Wiederholung. "
                  "C01 ist jetzt dauerhaft stabil.")
        self.assertTrue(module.check_step(stop, answer))

    def test_missing_stop_constraints_fail(self):
        j = module.load_journey("teamlead_coaching")
        from run import check
        self.assertTrue(check(j["steps"][-1], "Das Interview ist beendet."))


if __name__ == "__main__":
    unittest.main()
