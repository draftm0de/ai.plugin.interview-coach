import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests/behavior'))
SPEC = importlib.util.spec_from_file_location('run_smoke', ROOT / 'tests/behavior/run_smoke.py')
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class SmokeRunnerTests(unittest.TestCase):
    def test_cli_returns_answer_and_diagnostics_separately(self):
        for cli in ('codex', 'claude'):
            response = subprocess.CompletedProcess([], 0, 'model answer', 'diagnostic')
            with self.subTest(cli=cli), patch('run.subprocess.run', return_value=response):
                self.assertEqual(module.run_case(cli, 'prompt', 1), (0, 'model answer', 'diagnostic'))

    def test_checks_only_answer_and_writes_separate_artifacts(self):
        case = {'id': 'fictional', 'prompt': 'Fictional test',
                'must_contain_any': ['required'], 'must_not_contain': ['forbidden']}
        for answer, diagnostics, expected in (('no answer', 'required', 1), ('required', 'forbidden', 0)):
            with self.subTest(answer=answer), tempfile.TemporaryDirectory() as directory:
                with patch.object(module, 'CASES', [case]), patch.object(module.shutil, 'which', return_value='fake'), patch.object(module, 'run_case', return_value=(0, answer, diagnostics)), patch.object(sys, 'argv', ['run_smoke.py', '--cli', 'codex', '--output-dir', directory]), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(module.main(), expected)
                self.assertEqual((Path(directory) / 'fictional.txt').read_text(), answer)
                self.assertEqual((Path(directory) / 'fictional.stderr.txt').read_text(), diagnostics)

    def test_timeout_is_failure_with_separate_diagnostic(self):
        case = {'id': 'timeout', 'prompt': 'Fictional test',
                'must_contain_any': ['required'], 'must_not_contain': []}
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(module, 'CASES', [case]), patch.object(module.shutil, 'which', return_value='fake'), patch.object(module, 'run_case', side_effect=subprocess.TimeoutExpired('fake', 1)), patch.object(sys, 'argv', ['run_smoke.py', '--cli', 'claude', '--output-dir', directory]), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(), 1)
            self.assertEqual((Path(directory) / 'timeout.txt').read_text(), '')
            self.assertEqual((Path(directory) / 'timeout.stderr.txt').read_text(), 'TIMEOUT')
