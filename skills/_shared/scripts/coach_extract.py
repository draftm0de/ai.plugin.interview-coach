"""CV/posting text extraction for Markdown, DOCX and PDF.

Only real extraction paths are used. Missing capabilities raise ExtractionUnavailable;
nothing is installed and no text is invented. Gaps are reported as warnings and make
the result "partial" rather than "complete".
"""
import hashlib
import importlib.util
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from xml.etree import ElementTree as ET

MAX_BYTES = 25 * 1024 * 1024
MAX_UNZIPPED = 60 * 1024 * 1024
TEXT_SUFFIXES = {".md", ".markdown", ".txt"}
SUPPORTED = TEXT_SUFFIXES | {".docx", ".pdf"}
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"


class ExtractionUnavailable(RuntimeError):
    """A required extraction capability is missing (nothing was installed)."""


class ExtractionFailed(ValueError):
    """The file is unreadable or not a valid document of its type."""


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check_source(path):
    path = Path(path).expanduser()
    if path.is_symlink() or not path.is_file():
        raise ExtractionFailed(f"Not a regular readable file: {path}")
    if path.suffix.lower() not in SUPPORTED:
        raise ExtractionFailed(f"Unsupported file type {path.suffix or '(none)'}; supported: PDF, DOCX, Markdown/Text")
    size = path.stat().st_size
    if size == 0:
        raise ExtractionFailed("File is empty")
    if size > MAX_BYTES:
        raise ExtractionFailed("File exceeds the 25 MB limit")
    return path


def _result(markdown, extractor, warnings):
    return {"markdown": markdown, "extractor": extractor, "warnings": warnings,
            "status": "complete" if not warnings and markdown.strip() else "partial"}


def _extract_text(path):
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ExtractionFailed("Text is not valid UTF-8; no lossy conversion performed") from exc
    warnings = [] if text.strip() else ["File contains no text"]
    return _result(text, "builtin-text", warnings)


def _paragraph_text(paragraph):
    """Paragraph text without nested text boxes or mc:Fallback duplicates."""
    parts = []

    def visit(node):
        for child in node:
            if child.tag in (W + "txbxContent", MC + "Fallback"):
                continue
            if child.tag == W + "t":
                parts.append(child.text or "")
            elif child.tag == W + "tab":
                parts.append("\t")
            elif child.tag in (W + "br", W + "cr"):
                parts.append("\n")
            else:
                visit(child)
    visit(paragraph)
    return "".join(parts)


def _boxes(node):
    for child in node:
        if child.tag == MC + "Fallback":
            continue
        if child.tag == W + "txbxContent":
            yield child
        else:
            yield from _boxes(child)


def _walk(element, lines, skip_fallback=True, seen_boxes=None):
    seen_boxes = set() if seen_boxes is None else seen_boxes
    for child in element:
        if skip_fallback and child.tag == MC + "Fallback":
            continue
        if child.tag == W + "p":
            text = _paragraph_text(child).strip("\n")
            if text.strip():
                style = child.find(f"{W}pPr/{W}pStyle")
                style_id = style.get(W + "val", "") if style is not None else ""
                heading = re.fullmatch(r"(?i)heading\s*([1-6])", style_id)
                if heading:
                    text = "#" * int(heading.group(1)) + " " + text
                elif child.find(f"{W}pPr/{W}numPr") is not None:
                    text = "- " + text
                lines.append(text)
            # Text boxes hold their own paragraphs (mc:Fallback duplicates are skipped).
            for box in _boxes(child):
                if box not in seen_boxes:
                    seen_boxes.add(box)
                    _walk(box, lines, True, seen_boxes)
        elif child.tag == W + "tbl":
            for row in child.iter(W + "tr"):
                cells = []
                for cell in row.findall(W + "tc"):
                    cells.append(" ".join(_paragraph_text(p).strip() for p in cell.iter(W + "p")).strip())
                if any(cells):
                    lines.append("| " + " | ".join(cells) + " |")
        elif child.tag in (W + "sdt", W + "sdtContent", W + "body", MC + "AlternateContent", MC + "Choice"):
            _walk(child, lines, skip_fallback, seen_boxes)


def _extract_docx(path):
    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise ExtractionFailed("Not a valid DOCX (zip) file") from exc
    with archive:
        infos = archive.infolist()
        if len(infos) > 2000 or sum(i.file_size for i in infos) > MAX_UNZIPPED:
            raise ExtractionFailed("DOCX exceeds archive safety limits")
        names = {i.filename for i in infos}
        if "word/document.xml" not in names:
            raise ExtractionFailed("DOCX has no word/document.xml")

        def parse(name):
            data = archive.read(name)
            if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
                raise ExtractionFailed(f"{name} contains a DTD/entity declaration; refused")
            try:
                return ET.fromstring(data)
            except ET.ParseError as exc:
                raise ExtractionFailed(f"{name} is not well-formed XML") from exc

        lines = []
        _walk(parse("word/document.xml"), lines)
        warnings = []
        media = sorted(n for n in names if n.startswith("word/media/"))
        if media:
            warnings.append(f"{len(media)} embedded image(s) were not transcribed (no OCR)")
        for part, label in (("word/footnotes.xml", "footnotes"), ("word/endnotes.xml", "endnotes")):
            if part in names:
                notes = [_paragraph_text(p).strip() for p in parse(part).iter(W + "p")]
                if any(notes):
                    warnings.append(f"{label} are present but not transcribed")
        for name in sorted(names):
            if re.fullmatch(r"word/(header|footer)\d*\.xml", name):
                if any(_paragraph_text(p).strip() for p in parse(name).iter(W + "p")):
                    warnings.append(f"{name.split('/')[-1]} content is not transcribed")
        if not lines:
            warnings.append("No text found in document body")
    return _result("\n\n".join(lines) + ("\n" if lines else ""), "builtin-docx", warnings)


PDFKIT_SCRIPT = """import Foundation
import PDFKit
let args = CommandLine.arguments
guard args.count > 1, let doc = PDFDocument(url: URL(fileURLWithPath: args[1])), doc.pageCount > 0 else {
    FileHandle.standardError.write("cannot open PDF\\n".data(using: .utf8)!); exit(2)
}
var out = ""
for i in 0..<doc.pageCount { out += (doc.page(at: i)?.string ?? "") + "\\u{0C}" }
FileHandle.standardOutput.write(out.data(using: .utf8)!)
"""


def _pdf_tools(which=shutil.which):
    tools = []
    if which("pdftotext"):
        tools.append("pdftotext")
    if which("mutool"):
        tools.append("mutool")
    if importlib.util.find_spec("pypdf") is not None:
        tools.append("pypdf")
    if sys.platform == "darwin" and which("swift"):  # PDFKit ships with macOS; a fixed built-in script is run, nothing is installed
        tools.append("pdfkit-swift")
    return tools


def _extract_pdf(path, which=shutil.which, run=subprocess.run):
    tools = _pdf_tools(which)
    if not tools:
        raise ExtractionUnavailable(
            "PDF extraction needs pdftotext (poppler), mutool, the Python package pypdf or (macOS) swift with PDFKit; none is available. "
            "Nothing was installed. Provide DOCX/Markdown, supply your own transcription, or install a tool yourself")
    tool = tools[0]
    if tool == "pdftotext":
        done = run(["pdftotext", "-enc", "UTF-8", str(path), "-"], capture_output=True, timeout=120)
        if done.returncode != 0:
            raise ExtractionFailed("pdftotext failed: " + done.stderr.decode("utf-8", "replace").strip()[:300])
        pages = done.stdout.decode("utf-8", "replace").split("\f")
    elif tool == "mutool":
        done = run(["mutool", "draw", "-q", "-F", "txt", "-o", "-", str(path)], capture_output=True, timeout=120)
        if done.returncode != 0:
            raise ExtractionFailed("mutool failed: " + done.stderr.decode("utf-8", "replace").strip()[:300])
        pages = done.stdout.decode("utf-8", "replace").split("\f")
    elif tool == "pdfkit-swift":
        with tempfile.TemporaryDirectory(prefix="coach-pdfkit-") as scratch:
            script = Path(scratch) / "extract.swift"
            script.write_text(PDFKIT_SCRIPT, encoding="utf-8")
            done = run(["swift", str(script), str(path)], capture_output=True, timeout=300, cwd=scratch)
        if done.returncode != 0:
            raise ExtractionFailed("PDFKit could not read the PDF: " + done.stderr.decode("utf-8", "replace").strip()[:300])
        pages = done.stdout.decode("utf-8", "replace").split("\f")
    else:
        import pypdf  # noqa: PLC0415
        try:
            pages = [page.extract_text() or "" for page in pypdf.PdfReader(str(path)).pages]
        except Exception as exc:  # third-party parser errors are many
            raise ExtractionFailed("pypdf could not read the PDF: " + str(exc)[:300]) from exc
    if pages and not pages[-1].strip():
        pages = pages[:-1]
    warnings = []
    empty = [str(i + 1) for i, page in enumerate(pages) if not page.strip()]
    if not pages or len(empty) == len(pages):
        warnings.append("No text layer found (scanned document?); OCR is not available")
    elif empty:
        warnings.append("Pages without extractable text: " + ", ".join(empty))
    markdown = "\n\n".join(f"<!-- page {i + 1} -->\n{page.strip()}" for i, page in enumerate(pages) if page.strip())
    return _result(markdown + ("\n" if markdown else ""), tool, warnings)


def extract(path, *, which=shutil.which, run=subprocess.run):
    path = check_source(path)
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return _extract_text(path)
    if suffix == ".docx":
        return _extract_docx(path)
    return _extract_pdf(path, which, run)
