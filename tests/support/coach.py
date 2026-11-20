"""Shared helpers: fictional fixtures, runtime import, fake provider CLI and local bare Git repositories."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'Makefile').is_file())
SCRIPTS = ROOT / 'skills/_shared/scripts'
sys.path.insert(0, str(SCRIPTS))
sys.dont_write_bytecode = True
import interview_workspace as iw  # noqa: E402
import coach_extract as extract  # noqa: E402
import coach_git as gitstore  # noqa: E402
import coach_core as core  # noqa: E402

RUNTIME = SCRIPTS / 'interview_workspace.py'
REMOTE = 'https://github.com/example-owner/interview-data.git'


def make_docx(path, paragraphs=('Erika Beispiel',), *, headings=(), image=False, footer=None, table=None, textbox=None):
    ns = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"'
    body = ''.join(f'<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>{h}</w:t></w:r></w:p>' for h in headings)
    body += ''.join(f'<w:p><w:r><w:t>{p}</w:t></w:r></w:p>' for p in paragraphs)
    if table:
        body += '<w:tbl>' + ''.join('<w:tr>' + ''.join(f'<w:tc><w:p><w:r><w:t>{c}</w:t></w:r></w:p></w:tc>' for c in row) + '</w:tr>' for row in table) + '</w:tbl>'
    if textbox:
        body += (f'<w:p><w:r><mc:AlternateContent><mc:Choice><w:txbxContent><w:p><w:r><w:t>{textbox}</w:t></w:r></w:p></w:txbxContent></mc:Choice>'
                 f'<mc:Fallback><w:txbxContent><w:p><w:r><w:t>{textbox}</w:t></w:r></w:p></w:txbxContent></mc:Fallback></mc:AlternateContent></w:r></w:p>')
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('[Content_Types].xml', '<Types/>')
        z.writestr('word/document.xml', f'<?xml version="1.0"?><w:document {ns}><w:body>{body}</w:body></w:document>')
        if image:
            z.writestr('word/media/image1.png', b'\x89PNG')
        if footer:
            z.writestr('word/footer1.xml', f'<w:ftr {ns}><w:p><w:r><w:t>{footer}</w:t></w:r></w:p></w:ftr>')
    return Path(path)


def make_pdf(path, text='Erika Beispiel Backend Engineer', pages=None):
    """Minimal valid PDF. `pages` = list of strings; None/'' makes a page without a text layer (like a scan)."""
    pages = [text] if pages is None else pages
    objs = ['<< /Type /Catalog /Pages 2 0 R >>',
            '<< /Type /Pages /Kids [' + ' '.join(f'{3 + 2 * i} 0 R' for i in range(len(pages))) + f'] /Count {len(pages)} >>']
    font_id = 3 + 2 * len(pages)
    for i, page_text in enumerate(pages):
        objs.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Contents {4 + 2 * i} 0 R '
                    f'/Resources << /Font << /F1 {font_id} 0 R >> >> >>')
        stream = f'BT /F1 12 Tf 20 100 Td ({page_text}) Tj ET' if page_text else '0.5 g 20 20 100 100 re f'
        objs.append(f'<< /Length {len(stream)} >>\nstream\n{stream}\nendstream')
    objs.append('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    out = b'%PDF-1.4\n'
    offsets = []
    for i, obj in enumerate(objs, 1):
        offsets.append(len(out))
        out += f'{i} 0 obj\n{obj}\nendobj\n'.encode()
    xref = len(out)
    out += f'xref\n0 {len(objs) + 1}\n0000000000 65535 f \n'.encode()
    out += ''.join(f'{o:010d} 00000 n \n' for o in offsets).encode()
    out += f'trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
    Path(path).write_bytes(out)
    return Path(path)


def snapshot(base):
    """Complete content snapshot used to prove that a failed operation changed nothing."""
    base = Path(base)
    return {str(p.relative_to(base)): (p.read_bytes() if p.is_file() else None) for p in sorted(base.rglob('*'))
            if '.git/' not in str(p) and not str(p.relative_to(base)).startswith('.git')
            and not (p.name == 'lock' and p.parent.name == '.journal' and p.stat().st_size == 0)}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.project = self.base / 'project'
        self.project.mkdir()
        self.cfg = self.base / 'cfg'
        self.root = self.base / 'workspace'

    def setup_local(self, project=None, path=None):
        return iw.setup_project(project or self.project, 'local', path or self.root, config_dir=self.cfg)

    def candidate(self, name='Erika Beispiel'):
        return iw.create_candidate(self.root, name)['candidate_id']

    def cdir(self, cid):
        return self.root / 'candidates' / cid

    def write(self, name, text):
        path = self.base / name
        path.write_text(text, encoding='utf-8')
        return path

    def cli(self, *args, project=None, expect=0):
        done = subprocess.run([sys.executable, '-B', str(RUNTIME), '--config-dir', str(self.cfg), *map(str, args)],
                              capture_output=True, text=True, env=dict(os.environ, **getattr(self, 'extra_env', {})))
        self.assertEqual(expect, done.returncode, done.stderr + done.stdout)
        return done

    def state_hash(self, cid):
        return iw.snapshot(self.root, cid)['state_sha256']

    def finish(self, cid, run_id, **kw):
        defaults = dict(status='completed', answered_count=3, planned_count=3)
        defaults.update(kw)
        if 'expected_state_sha256' not in defaults:
            defaults['expected_state_sha256'] = self.state_hash(cid)
        return iw.finish(self.root, cid, run_id, f'# Run {run_id}\nQ1 ...\n', defaults.pop('state_text', f'# State after {run_id}\n'), **defaults)


class GitCase(Base):
    """Local bare repository behind a github.com URL (rewritten by git config); fake `gh`; logging git wrapper."""
    gh_private = 'true'
    gh_permission = 'WRITE'

    def setUp(self):
        super().setUp()
        self.bare = self.base / 'remote.git'
        subprocess.run(['git', 'init', '-q', '--bare', '-b', 'main', str(self.bare)], check=True)
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        self.gitlog = self.base / 'git-calls.log'
        real = shutil.which('git')
        self._script('git', f'#!/bin/sh\nprintf "%s\\n" "$*" >> "{self.gitlog}"\nexec "{real}" "$@"\n')
        self._script('gh', '#!/bin/sh\nprintf \'{"isPrivate": %s, "viewerPermission": "%s"}\' "$FAKE_GH_PRIVATE" "$FAKE_GH_PERMISSION"\n')
        self.clone = self.base / 'clone'
        self.env = {'PATH': f'{self.bin}{os.pathsep}{os.environ["PATH"]}', 'FAKE_GH_PRIVATE': self.gh_private,
                    'FAKE_GH_PERMISSION': self.gh_permission,
                    'GIT_CONFIG_COUNT': '1', 'GIT_CONFIG_KEY_0': f'url.{self.bare}.insteadOf', 'GIT_CONFIG_VALUE_0': REMOTE,
                    'GIT_AUTHOR_NAME': 'Test', 'GIT_AUTHOR_EMAIL': 'test@example.invalid',
                    'GIT_COMMITTER_NAME': 'Test', 'GIT_COMMITTER_EMAIL': 'test@example.invalid',
                    'GIT_CONFIG_GLOBAL': str(self.base / 'gitconfig'), 'GIT_CONFIG_NOSYSTEM': '1'}
        (self.base / 'gitconfig').write_text('')
        patcher = mock.patch.dict(os.environ, self.env)
        patcher.start()
        self.addCleanup(patcher.stop)
        # Controlled test double: the local bare repository stands for the authorized GitHub repository. Anything else
        # (other paths, other hosts) keeps its real, unprovable identity. Production code has no such bypass.
        self.real_identity = gitstore.identity_of
        authorized = gitstore._normalized(REMOTE)
        self.bare_str = str(self.bare)
        double = lambda url: authorized if url == self.bare_str else self.real_identity(url)  # noqa: E731
        identity = mock.patch.object(gitstore, 'identity_of', side_effect=double)
        identity.start()
        self.addCleanup(identity.stop)
        self.extra_env = self.env

    def _script(self, name, text):
        path = self.bin / name
        path.write_text(text)
        path.chmod(path.stat().st_mode | stat.S_IEXEC)

    def setup_git(self, **kw):
        return iw.setup_project(self.project, 'git', self.clone, config_dir=self.cfg, remote=REMOTE, **kw)

    def cli(self, *args, project=None, expect=0):
        """CLI run in a subprocess with the same identity test double (separate process, so it is applied by a launcher)."""
        launcher = (f"import sys; sys.path.insert(0, {str(SCRIPTS)!r}); import coach_git as g, interview_workspace as iw; "
                    f"a = g._normalized({REMOTE!r}); real = g.identity_of; "
                    f"g.identity_of = lambda u: a if u == {self.bare_str!r} else real(u); "
                    "sys.exit(iw.main(sys.argv[1:]))")
        done = subprocess.run([sys.executable, '-B', '-c', launcher, '--config-dir', str(self.cfg), *map(str, args)],
                              capture_output=True, text=True, env=dict(os.environ, **self.env))
        self.assertEqual(expect, done.returncode, done.stderr + done.stdout)
        return done

    def attestation(self, **kw):
        base = {'private': True, 'write': True, 'source': 'example-connector', 'repository': 'example-owner/interview-data',
                'user_confirmed': True}
        base.update(kw)
        return base

    def run_git(self, *args, cwd=None):
        return subprocess.run(['git', *args], cwd=cwd or self.clone, capture_output=True, text=True, check=True).stdout.strip()

    def remote_head(self):
        done = subprocess.run(['git', '--git-dir', str(self.bare), 'rev-parse', '-q', '--verify', 'refs/heads/main'], capture_output=True, text=True)
        return done.stdout.strip() or None

    def second_clone(self):
        self._clones = getattr(self, '_clones', 0) + 1
        other = self.base / f'other{self._clones}'
        subprocess.run(['git', 'clone', '-q', str(self.bare), str(other)], check=True)
        return other
