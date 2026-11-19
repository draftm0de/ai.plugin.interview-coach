from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]

class ScopeContractTests(unittest.TestCase):
    def test_confirmed_requirements_have_existing_public_evidence(self):
        text = (ROOT / 'SCOPE.md').read_text()
        sections = re.split(r'(?m)^## R\d+:', text)[1:]
        self.assertEqual(len(sections), 9)
        for section in sections:
            self.assertIn('Status: confirmed', section)
            self.assertIn('Acceptance:', section)
            for kind in ('Source', 'Test'):
                paths = re.findall(r'^' + kind + r': (.+)$', section, re.M)
                self.assertTrue(paths)
                for name in paths:
                    self.assertNotIn('..', Path(name).parts)
                    self.assertTrue((ROOT / name).is_file(), name)
        for name in ('AGENTS.md', 'CLAUDE.md', 'docs/architecture.md'):
            self.assertTrue((ROOT / name).is_file())
