"""Shared helpers: fictional fixtures, runtime import, local workspaces."""
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
import coach_core as core  # noqa: E402

RUNTIME = SCRIPTS / 'interview_workspace.py'


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


def block(n, *, answer='Eigene Antwort.', followups=(), retries=(), open_gaps=()):
    """Fictional dialogue block for main question n (1-based)."""
    return dict(key=f'q-{n}', question=f'Frage {n}?', initial_answer=answer,
                initial_assessment=None if answer is None else 'Erstantwort: solide.',
                block_assessment=None if answer is None else 'Frageblock: solide.',
                followups=list(followups), retries=list(retries), other_open_gaps=list(open_gaps))


def followup(block_n, n, *, kind='completion', answer='Ergänzung.', hints=False, gap='Termindruck nicht behandelt',
             resolution=None, text=None):
    if kind == 'deepening':
        gap = None
    return dict(id=f'q-{block_n}-f{n}', kind=kind, reason='Konkreter Anlass', text=text or f'Nachfrage {n}?', answer=answer,
                hints_before=hints, gap=gap, resolution=resolution or ('pending' if answer is None else 'closed'))


def dialogue(answered):
    return [block(i + 1) for i in range(answered)]


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
        if 'dialogue' not in defaults:
            defaults['dialogue'] = dialogue(defaults['answered_count'])
        if 'expected_state_sha256' not in defaults:
            defaults['expected_state_sha256'] = self.state_hash(cid)
        return iw.finish(self.root, cid, run_id, f'# Run {run_id}\nQ1 ...\n', defaults.pop('state_text', f'# State after {run_id}\n'), **defaults)
