import importlib.util
import io
from unittest.mock import patch
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
    def setUp(self):
        output = patch("sys.stdout", new_callable=io.StringIO)
        output.start()
        self.addCleanup(output.stop)

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

    def test_progress_caution_accepts_markdown_and_claude_wording(self):
        for answer in (
            'Es lässt sich **kein Kompetenzstatus** ableiten, weder „verbessert" noch „stabil".',
            'Deutlicher Fortschritt, aber kein unabhängiger Nachweis.',
            'Ich stufe das nicht als stabile oder gefestigte Kompetenz ein.',
            'Das ist kein Nachweis für einen stabilen oder auch nur verbesserten Kompetenzstatus.',
            'Ein stabiler Kompetenzstatus ist nicht belegt.',
            'Die Kompetenz ist stabil nicht nachgewiesen.',
            'Die Schwäche ist nicht dauerhaft behoben; noch nicht stabil.',
        ):
            with self.subTest(answer=answer):
                self.assertEqual(module.progress_errors(answer), [])

    def test_progress_caution_rejects_unrelated_disclaimer_and_contradiction(self):
        for answer in (
            'Ein weiterer Test ist nicht belegt.',
            'Das ist ein Nachweis für einen stabilen Kompetenzstatus.',
            'Ich stufe das als stabile oder gefestigte Kompetenz ein.',
            'Kompetenz ist jetzt stabil; ein weiterer Test ist nicht belegt.',
            'Noch nicht stabil. C01 ist jetzt dauerhaft stabil.',
            'Kein unabhängiger Nachweis. Kompetenz: stabil.',
            'Noch nicht stabil. Die Schwäche ist dauerhaft behoben.',
        ):
            with self.subTest(answer=answer):
                self.assertTrue(module.progress_errors(answer))

    def test_revision_also_requires_evidence_caution(self):
        revision = module.load_journey('teamlead_coaching')['steps'][-2]
        answer = 'Konkreter als die ursprüngliche Antwort, Risiko und Entscheidung sind klarer. Weiter so!'
        self.assertTrue(module.check_step(revision, answer))

    def test_diagnostics_cannot_supply_missing_guarantees(self):
        journey = module.load_journey('teamlead_coaching')
        def fake(cli, prompt, timeout):
            return 0, 'Keine bewertbare Antwort.', 'Gesamtbewertung 7/10. Einzelbewertung. Risiko. Verbesserung.'
        with tempfile.TemporaryDirectory() as directory:
            results = module.execute_journey(journey, 'codex', Path(directory), 1, runner=fake)
            self.assertTrue(all(not result['passed'] for result in results))
            self.assertNotIn('Gesamtbewertung', (Path(directory) / '01-priority.txt').read_text())
            self.assertIn('Gesamtbewertung', (Path(directory) / '01-priority.stderr.txt').read_text())

    def test_execution_replays_actual_answers_but_not_diagnostics(self):
        journey = module.load_journey('teamlead_coaching')
        prompts = []
        def fake(cli, prompt, timeout):
            prompts.append(prompt)
            return 0, f'ACTUAL_ANSWER_{len(prompts)}', 'DIAGNOSTIC_ONLY'
        with tempfile.TemporaryDirectory() as directory:
            module.execute_journey(journey, 'codex', Path(directory), 1, runner=fake)
        self.assertEqual(len(prompts), 5)
        for index, prompt in enumerate(prompts):
            self.assertNotIn('DIAGNOSTIC_ONLY', prompt)
            for previous in range(1, index + 1):
                self.assertIn(f'ACTUAL_ANSWER_{previous}', prompt)
            self.assertNotIn(f'ACTUAL_ANSWER_{index + 1}', prompt)

    def test_timeout_and_nonzero_exit_stop_transcript_replay(self):
        journey = module.load_journey('teamlead_coaching')
        for timeout in (False, True):
            calls = []
            def fake(cli, prompt, seconds):
                calls.append(prompt)
                if timeout:
                    raise module.subprocess.TimeoutExpired('fake', seconds)
                return 1, 'Partial answer', 'CLI failed'
            with self.subTest(timeout=timeout), tempfile.TemporaryDirectory() as directory:
                results = module.execute_journey(journey, 'codex', Path(directory), 1, runner=fake)
                self.assertEqual(len(calls), 1)
                self.assertEqual(len(results), 1)
                self.assertFalse(results[0]['passed'])
                self.assertTrue((Path(directory) / 'result.json').exists())

    def test_missing_stop_constraints_fail(self):
        j = module.load_journey("teamlead_coaching")
        from run import check
        self.assertTrue(check(j["steps"][-1], "Das Interview ist beendet."))


if __name__ == "__main__":
    unittest.main()
