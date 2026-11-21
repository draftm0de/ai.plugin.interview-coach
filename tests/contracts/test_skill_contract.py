"""Skill and payload contracts. These check text and layout; they do NOT prove dialogue behavior."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from tests.support.payload import build_payload

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'Makefile').is_file())
SKILLS = ROOT / 'skills'
SHARED = SKILLS / '_shared'
PUBLIC = ('interview-coach', 'candidate-create', 'candidate-training', 'job-create', 'job-training')
REFERENCES = ('followup', 'research', 'training', 'evaluation', 'storage', 'technical-interview', 'setup', 'session-control',
              'runtime', 'candidate-selection', 'cv-profile', 'job-preparation')


def read(path):
    return Path(path).read_text(encoding='utf-8')


def frontmatter(text):
    match = re.match(r'---\n(.*?)\n---\n', text, re.S)
    return dict(line.split(': ', 1) for line in match.group(1).splitlines()) if match else {}


class SkillLayout(unittest.TestCase):
    def test_exactly_the_five_public_skills_and_shared_without_skill_md(self):
        found = sorted(p.parent.name for p in SKILLS.glob('*/SKILL.md'))
        self.assertEqual(sorted(PUBLIC), found)
        self.assertFalse((SHARED / 'SKILL.md').exists())
        for name in PUBLIC:
            meta = frontmatter(read(SKILLS / name / 'SKILL.md'))
            self.assertEqual(name, meta.get('name'))
            self.assertGreater(len(meta.get('description', '')), 40)

    def test_all_shared_references_exist_and_relative_links_resolve(self):
        for name in REFERENCES:
            self.assertTrue((SHARED / 'references' / f'{name}.md').is_file(), name)
        for skill in PUBLIC:
            text = read(SKILLS / skill / 'SKILL.md')
            for link in re.findall(r'`(\.\./_shared/[^`\s]+)`', text):
                self.assertTrue((SKILLS / skill / link).exists(), f'{skill}: {link}')
        self.assertFalse(list((SKILLS / 'interview-coach').glob('references')), 'old per-skill references must not linger')

    def test_runtime_is_shared_and_root_scripts_are_development_only(self):
        self.assertTrue((SHARED / 'scripts/interview_workspace.py').is_file())
        self.assertFalse((SKILLS / 'interview-coach/scripts/interview_workspace.py').exists())
        self.assertFalse((ROOT / 'scripts/interview_workspace.py').exists())
        for path in SHARED.rglob('*.py'):
            body = read(path)
            self.assertNotRegex(body, r'from scripts|import scripts|tests\.|parents\[\d\]\s*/\s*.scripts', str(path))

    def test_installed_skills_do_not_require_a_developer_checkout(self):
        for path in list(SKILLS.rglob('*.md')):
            text = read(path)
            for forbidden in ('scripts/run_tests.py', 'make test', 'tests/behavior', 'tests/fixtures'):
                if path.name == 'SKILL.md' and path.parent.name == 'interview-coach' and forbidden == 'make test':
                    continue  # the validation section names developer commands as such
                self.assertNotIn(forbidden, text, f'{path}: {forbidden}')

    def test_no_personal_baseline_in_public_skill(self):
        for p in SKILLS.rglob('*.md'):
            content = read(p).lower()
            for private_term in ('peter fux', 'armin thurner', 'birgit rachinger', 'draftm0de/private.job-interview'):
                self.assertNotIn(private_term, content, f'private data in {p}')

    def test_no_alternative_path_manifest_or_legacy_pointer_support(self):
        for path in list(SKILLS.rglob('*.md')) + list((ROOT / 'docs').rglob('*.md')):
            self.assertNotIn('workspace.yaml', read(path), str(path))
        runtime = read(SHARED / 'scripts/interview_workspace.py')
        self.assertNotIn('config.json', runtime.replace('workspace.json', ''))


class StorageOptions(unittest.TestCase):
    def active_texts(self):
        texts = {p: read(p) for p in SKILLS.rglob('*.md')}
        for name in ('README.md', 'README.en.md'):
            texts[ROOT / name] = read(ROOT / name)
        for p in (ROOT / 'docs/de', ROOT / 'docs/en'):
            for q in p.glob('*.md'):
                if q.name not in ('release-evidence.md', 'release-operations.md'):
                    texts[q] = read(q)
        return texts

    def test_exactly_two_options_and_no_self_managed_mode_in_active_instructions(self):
        setup = read(SHARED / 'references/setup.md')
        for option in ('**Lokal**', '**Nicht speichern**'):
            self.assertIn(option, setup)
        self.assertIn('exactly two', setup)
        for path, text in self.active_texts().items():
            for line in text.splitlines():
                low = line.lower()
                if 'dateien selbst verwalten' in low or 'self-managed files' in low or 'manage files yourself' in low:
                    self.assertRegex(low, r'not|kein|nicht|never|entfällt|no longer', f'{path}: {line}')
                self.assertNotRegex(low, r'\b(four|vier)\b.{0,30}(storage|speicher)', f'{path}: {line}')
                self.assertNotRegex(low, r'(storage|speicher)\w*.{0,30}\b(four|vier)\b', f'{path}: {line}')

    def test_storage_type_is_asked_before_path_and_project_folder_is_only_a_suggestion(self):
        setup = read(SHARED / 'references/setup.md')
        self.assertIn('Storage type first, details second', setup)
        self.assertIn('never becomes the storage target without the user', setup)
        self.assertIn('Never offer repository setup', setup)

    def test_no_storage_mode_forbids_runtime_calls_in_every_skill(self):
        for name in PUBLIC:
            text = read(SKILLS / name / 'SKILL.md')
            self.assertIn('Nicht speichern', text, name)
        for name in ('candidate-training', 'job-create', 'job-training'):
            self.assertRegex(read(SKILLS / name / 'SKILL.md'), r'(?is)Nicht speichern.*(no runtime call|call no runtime command)')
        self.assertIn('never run the runtime', read(SKILLS / 'interview-coach/SKILL.md'))
        self.assertIn('No workspace, pointer, lock, journal', read(SHARED / 'references/storage.md'))

    def test_git_storage_is_removed_from_payload_and_cli(self):
        self.assertFalse((SHARED / 'scripts/coach_git.py').exists())
        runtime = read(SHARED / 'scripts/interview_workspace.py')
        for command in ('git-status', 'git-pull', 'git-publish', '--remote', '--attest-private'):
            self.assertNotIn(command, runtime)
        self.assertIn('Git storage is no longer supported', runtime)


class HostEntryPoints(unittest.TestCase):
    def test_entry_points_documented_for_both_hosts_without_overclaiming(self):
        text = read(SKILLS / 'interview-coach/SKILL.md')
        for name in PUBLIC[1:]:
            self.assertIn(f'/interview-coach:{name}', text)
            self.assertIn(f'${name}', text)
        self.assertIn('is not a native command unless the host registers it', text)
        self.assertIn('no automatic activation when a project opens is assumed', text)

    def test_core_behaviors_preserved(self):
        main = read(SKILLS / 'interview-coach/SKILL.md')
        for term in ('general', 'targeted', 'drill', 'mock', 'briefing', 'one question at a time', 'Gesamtbewertung x/10',
                     'stopped_early', 'immediately end questioning', 'without a second confirmation', 'Before the first response',
                     'improving needs two spontaneous successful answers', 'stable needs confirmation in a later run without coaching'):
            self.assertIn(term, main)
        evaluation = read(SHARED / 'references/evaluation.md')
        for phrase in ('Gesamtbewertung', 'Einzelbewertung', 'Was besonders gut war', 'Was ich verbessern würde', 'mock'):
            self.assertIn(phrase, evaluation)
        technical = read(SHARED / 'references/technical-interview.md').lower()
        for phrase in ('coding', 'debugging', 'sandbox', 'not executed', 'do not leak the reference solution',
                       'never execute untrusted candidate code'):
            self.assertIn(phrase, technical)
        control = read(SHARED / 'references/session-control.md')
        for term in ('preferences.json', 'interface_language', 'interview_language', 'stopped_early', 'pause'):
            self.assertIn(term, control)

    def test_followup_dialogue_rules_are_present_and_linked_structural_only(self):
        # Structural text contract: proves wording exists, NOT dialogue behavior (see model scenarios and docs/acceptance.md).
        rules = read(SHARED / 'references/followup.md')
        for term in ('exactly one concrete follow-up', 'clarification', 'completion', 'deepening', 'STOP always wins', 'wenn möglich',
                     'not a retry', 'Nicht speichern', 'job-specific', 'never candidate evidence', 'hints_before'):
            self.assertIn(term, rules, term)
        for skill in ('interview-coach', 'candidate-training', 'job-training'):
            self.assertIn('followup.md', read(SKILLS / skill / 'SKILL.md'), skill)
        self.assertIn('--dialogue-file', read(SHARED / 'references/runtime.md'))
        self.assertIn('follow-up', read(SHARED / 'references/session-control.md'))

    def test_block_close_deepening_stop_and_role_fit_rules_agree_across_files_structural_only(self):
        # Structural: the same rule must be stated consistently; behavior is covered by the model scenarios.
        evaluation, rules = read(SHARED / 'references/evaluation.md'), read(SHARED / 'references/followup.md')
        for text in (evaluation, rules):
            self.assertIn('deepening', text)
            self.assertIn('no quota', text)
        # regression: a complete answer must not be forced to close its block at once
        self.assertNotIn('closes its block immediately', evaluation)
        self.assertNotIn('evaluated at once', evaluation)
        self.assertIn('close the block and evaluate it', evaluation)
        self.assertIn('close the block at once and rate it', rules)
        session = read(SHARED / 'references/session-control.md')
        for term in ('`stopped_early`', 'cannot be resumed', 'NOT promise', '`pause`'):
            self.assertIn(term, session, term)
        for skill in ('job-training', 'candidate-training'):
            self.assertIn('never promises to resume', read(SKILLS / skill / 'SKILL.md'), skill)
        self.assertIn('job-add --kind match', read(SKILLS / 'job-training/SKILL.md'))
        self.assertIn('saved as a new `match` snapshot', rules)
        self.assertIn('Recall the main question', rules)
        for term in ('never a `completion`', 'never list its topic in `other_open_gaps`', 'oder', 'Substanz der Begründung', 'ohne Punktzahl'):
            self.assertIn(term, rules, term)
        evaluation_text = read(SHARED / 'references/evaluation.md')
        for term in ('Evidence fidelity', 'mit beiden Teams durchgehen', 'never drop what was said', 'no score reason built on it', 'wer sie am Ende trifft bleibt offen'):
            self.assertIn(term, evaluation_text, term)
        self.assertIn('no numeric score and no criterion row', rules)
        self.assertIn('never only in a run', read(SHARED / 'references/job-preparation.md'))

    def test_job_skills_cover_required_dialog_elements(self):
        create = read(SKILLS / 'job-create/SKILL.md')
        for phrase in ('link or upload', 'retrieval date', 'namesakes', 'Fakten', 'Schlussfolgerungen', 'Unbekannt',
                       'never invent', 'participants'):
            self.assertIn(phrase.lower(), create.lower())
        training = read(SKILLS / 'job-training/SKILL.md')
        for phrase in ('Reuse existing research', 'cross-job learning state', 'job-specific fit gaps', '--job-id'):
            self.assertIn(phrase, training)
        research = read(SHARED / 'references/research.md')
        self.assertIn('Mit wem führst du das Bewerbungsgespräch?', research)
        self.assertIn('append-only snapshots', research)

    def test_candidate_skills_cover_cv_and_profile_flow(self):
        text = read(SKILLS / 'candidate-create/SKILL.md')
        for phrase in ('Equal names are allowed', 'Gibt es einen Lebenslauf?', 'nothing is installed or invented', 'candidate-recover'):
            self.assertIn(phrase, text)
        profile = read(SHARED / 'references/cv-profile.md')
        for phrase in ('byte-exact', 'one question per turn', '[Quelle: Modellvorschlag]', '--user-confirmed', 'partial'):
            self.assertIn(phrase, profile)


class InstallablePayload(unittest.TestCase):
    """Copy only what a host installs and prove the runtime and references work without the checkout."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.payload = Path(self.tmp.name).resolve() / 'plugin'
        build_payload(self.payload)

    def test_both_hosts_find_all_skills_in_the_payload(self):
        claude = json.loads(read(self.payload / '.claude-plugin/plugin.json'))
        codex = json.loads(read(self.payload / '.codex-plugin/plugin.json'))
        self.assertEqual('interview-coach', claude['name'])
        self.assertEqual('./skills/', codex['skills'])  # Codex: explicit skill root
        self.assertNotIn('skills', claude)             # Claude Code: conventional skills/ directory
        discovered = sorted(p.parent.name for p in (self.payload / 'skills').glob('*/SKILL.md'))
        self.assertEqual(sorted(PUBLIC), discovered)
        for name in PUBLIC:
            for link in re.findall(r'`(\.\./_shared/[^`\s]+)`', read(self.payload / 'skills' / name / 'SKILL.md')):
                self.assertTrue((self.payload / 'skills' / name / link).exists(), link)
        for icon in (codex['interface']['composerIcon'], codex['interface']['logo']):
            self.assertTrue((self.payload / icon).is_file())

    def test_payload_runtime_works_from_the_installed_location_for_a_full_flow(self):
        runtime = self.payload / 'skills/_shared/scripts/interview_workspace.py'
        base = Path(self.tmp.name).resolve()
        (base / 'project').mkdir()
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(base)}

        def run(*args, expect=0):
            done = subprocess.run([sys.executable, '-B', str(runtime), '--config-dir', str(base / 'cfg'), *map(str, args)],
                                  capture_output=True, text=True, cwd=base, env=env)
            self.assertEqual(expect, done.returncode, done.stderr)
            return done
        run('project-init', '--project', base / 'project', '--storage', 'local', '--path', base / 'ws')
        cid = json.loads(run('candidate-create', '--project', base / 'project', '--name', 'Erika Beispiel').stdout)['candidate_id']
        self.assertTrue((base / 'ws/candidates' / cid / 'candidate.json').is_file())
        self.assertEqual([], [p for p in self.payload.rglob('*') if p.is_file() and 'workspace' in p.name.lower() and p.suffix == '.json'])
        self.assertFalse(list(self.payload.rglob('__pycache__')), 'running the runtime must not write into the installed plugin')
