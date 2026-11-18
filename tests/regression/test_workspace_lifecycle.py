"""End-to-end local storage using only a packaged CLI and fictional candidate data."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import shutil

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'skills/zyris-interview-coach'


class WorkspaceLifecycleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        shutil.copytree(SOURCE, self.base/'installed/skills/zyris-interview-coach', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        self.cli = self.base / 'installed/skills/zyris-interview-coach/scripts/interview_workspace.py'
        self.config = self.base / 'config.json'
        self.workspace = self.base / 'fictional-workspace'
        self.call('init', '--path', str(self.workspace))
        (self.workspace / 'candidate/profile.md').write_text(
            '# Fictional candidate Alex Example\nERP platform team lead practice.\n', encoding='utf-8')

    def call(self, *arguments, expected=0):
        result = subprocess.run([sys.executable, str(self.cli), '--config', str(self.config), *arguments],
                                cwd=self.base, capture_output=True, text=True, timeout=15,
                                env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def save(self, run_id, status, count, transcript, state, digest, *extra):
        run_file = self.base / 'prepared-run.md'
        state_file = self.base / 'prepared-state.md'
        run_file.write_text(transcript, encoding='utf-8')
        state_file.write_text(state, encoding='utf-8')
        return self.call('finish', '--run-id', run_id, '--status', status,
                         '--answered-count', str(count), '--planned-count', '3',
                         '--run-file', str(run_file), '--state-file', str(state_file),
                         '--expected-state-sha256', digest, *extra)

    def test_packaged_cli_pause_resume_stop_then_complete(self):
        self.call('set-language', '--interface', 'de', '--interview', 'en')
        candidate = (self.workspace / 'candidate/profile.md').read_bytes()
        preferences = (self.workspace / 'preferences.json').read_bytes()
        initial = json.loads(self.call('status').stdout)
        first_answer = '# Fictional run\nQuestion 1: Who decides?\nAnswer: I decide within my mandate.\n'
        self.save('checkpoint', 'paused', 1, first_answer,
                  '# State\nPaused after question 1; next: question 2.\n', initial['state_sha256'])
        checkpoint = (self.workspace / 'runs/checkpoint.md').read_bytes()
        before_resume = {p: p.read_bytes() for p in self.workspace.rglob('*') if p.is_file()}
        resumed = json.loads(self.call('resume', '--run-id', 'checkpoint').stdout)
        self.assertEqual(resumed['transcript'], first_answer)
        self.assertEqual(resumed['run']['status'], 'paused')
        self.assertEqual(resumed['run']['answered_count'], 1)
        self.assertIn('next: question 2', resumed['state'])
        self.assertEqual(before_resume, {p: p.read_bytes() for p in before_resume})
        second_answer = first_answer + 'Question 2: Incident?\nAnswer: Assign an owner and restore service.\n'
        self.save('stopped', 'stopped_early', 2, second_answer,
                  '# State\nStopped after 2 of 3; question 3 unanswered; no stable competence.\n',
                  resumed['state_sha256'], '--resume-from', 'checkpoint')
        self.assertEqual((self.workspace / 'runs/checkpoint.md').read_bytes(), checkpoint)
        stopped = (self.workspace / 'runs/stopped.md').read_text()
        self.assertIn('"status": "stopped_early"', stopped)
        self.assertIn('"answered_count": 2', stopped)
        self.assertNotIn('Question 3:', stopped)
        self.call('resume', '--run-id', 'stopped', expected=1)
        self.call('resume', '--run-id', 'checkpoint', expected=1)
        current = json.loads(self.call('status').stdout)
        self.save('completed', 'completed', 3,
                  '# New fictional session\nQ1: a\nQ2: b\nQ3: c\n',
                  '# State\nNew session completed; no invented competence claim.\n', current['state_sha256'])
        self.assertIn('"status": "completed"', (self.workspace / 'runs/completed.md').read_text())
        self.assertEqual(len(list((self.workspace / 'runs').glob('*.md'))), 3)
        self.assertEqual((self.workspace / 'candidate/profile.md').read_bytes(), candidate)
        self.assertEqual((self.workspace / 'preferences.json').read_bytes(), preferences)
        self.assertEqual(self.call('validate').stdout.strip(), 'VALID')
        self.assertEqual(self.call('recover').stdout.strip(), 'No pending transaction')

    def test_stale_cli_write_fails_without_success_message_or_new_run(self):
        initial = json.loads(self.call('status').stdout)
        self.save('first', 'stopped_early', 1, '# Fictional answer', '# New state', initial['state_sha256'])
        result = self.call('finish', '--run-id', 'stale', '--status', 'stopped_early',
                           '--answered-count', '1', '--run-file', str(self.base / 'prepared-run.md'),
                           '--state-file', str(self.base / 'prepared-state.md'),
                           '--expected-state-sha256', initial['state_sha256'], expected=1)
        self.assertEqual(result.stdout, '')
        self.assertIn('Stale state', result.stderr)
        self.assertFalse((self.workspace / 'runs/stale.md').exists())
        self.assertEqual((self.workspace / 'state.md').read_text(), '# New state')

    def test_cli_requires_snapshot_and_reports_pending_recovery(self):
        result = self.call('finish', '--run-id', 'unsafe', '--status', 'completed',
                           '--answered-count', '0', '--run-file', 'absent', '--state-file', 'absent', expected=2)
        self.assertIn('--expected-state-sha256', result.stderr)
        self.assertEqual(list((self.workspace / 'runs').glob('*.md')), [])
        (self.workspace / '.zyris/pending.json').write_text('{"schema_version":999}')
        for command in ('status', 'validate', 'recover'):
            result = self.call(command, expected=1)
            self.assertNotIn('Saved and verified', result.stdout)
        self.assertTrue((self.workspace / '.zyris/pending.json').exists())
