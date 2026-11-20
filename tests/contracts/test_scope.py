from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ScopeContractTests(unittest.TestCase):
    def test_confirmed_requirements_have_existing_public_evidence_pointers(self):
        text = (ROOT / 'SCOPE.md').read_text()
        sections = re.split(r'(?m)^## R\d+:', text)[1:]
        ids = re.findall(r'(?m)^## (R\d+):', text)
        self.assertEqual([f'R{i}' for i in range(1, 21)], ids)
        for identifier, section in zip(ids, sections):
            self.assertIn('Status: confirmed', section, identifier)
            self.assertIn('Acceptance:', section, identifier)
            for kind in ('Source', 'Test'):
                paths = re.findall(r'^' + kind + r': (.+)$', section, re.M)
                self.assertTrue(paths, f'{identifier}: {kind}')
            for name in re.findall(r'^(?:Source|Test|Fixture): (.+)$', section, re.M):
                self.assertNotIn('..', Path(name).parts)
                self.assertTrue((ROOT / name).is_file(), f'{identifier}: {name}')
        for name in ('AGENTS.md', 'CLAUDE.md', 'docs/architecture.md', 'docs/acceptance.md'):
            self.assertTrue((ROOT / name).is_file(), name)

    def test_scope_names_both_hosts_two_options_and_removed_git(self):
        text = (ROOT / 'SCOPE.md').read_text()
        for term in ('Claude Code', 'Codex', 'genau zwei Speicheroptionen', 'mehrere', 'Git-Speicher entfernt'):
            self.assertIn(term, text)
        self.assertNotRegex(text, r'vier Speicheroptionen')
