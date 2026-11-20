"""Shared primitives: strict JSON, safe paths, atomic writes, cooperative locks, identifiers.

Reused unchanged from the format-1 runtime; identifier helpers are new.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import secrets
import stat
import tempfile
import unicodedata

# The ONE place that names the internal control folder. `.journal` holds locks, pending transactions, interrupted-save records and
# import staging: protected recovery data that may contain training answers or CV text (never a deletable cache).
CONTROL = ".journal"
LEGACY_CONTROL = ".zyris"                       # previous layout: recognized only to be REFUSED, never read, moved, copied or deleted
RUN_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,120}$")
CANDIDATE_ID = re.compile(r"^c-[a-z0-9]+(?:-[a-z0-9]+)*-[0-9a-f]{8}$")
JOB_ID = re.compile(r"^j-[a-z0-9]+(?:-[a-z0-9]+)*-[0-9a-f]{8}$")


def strict_json(text):
    """Reject ambiguous or non-round-trippable JSON before planning writes."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON field: ' + key)
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError('Invalid JSON numeric constant: ' + value)
    def finite_number(value):
        import math
        from decimal import Decimal
        number = float(value)
        if not math.isfinite(number):
            raise ValueError('Invalid JSON numeric constant: ' + value)
        if Decimal(value) != Decimal(str(number)):
            raise ValueError('Unsupported JSON numeric precision: ' + value)
        return number
    return json.loads(text, object_pairs_hook=unique, parse_constant=invalid_constant, parse_float=finite_number)


def safe_root(path):
    return Path(path).expanduser().resolve()


def checked_path(root, relative, kind=None):
    """Reject symlinks in every managed path component, including dangling links."""
    path = root
    for part in Path(relative).parts:
        if part in ("..", "/"):
            raise ValueError("Unsafe workspace path")
        path = path / part
        if path.is_symlink():
            raise ValueError(f"Managed path is a symlink: {path}")
    if path.exists() and kind and not (path.is_file() if kind == "file" else path.is_dir()):
        raise ValueError(f"{path} must be a {kind}")
    return path


def sync_directory(path):
    if os.name != "nt":
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def write_atomic(path, content, *, create_only=False, staging=None):
    """Publish flushed data from an explicit staging directory (default: sibling)."""
    path = Path(path)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"Unsafe file target: {path}")
    staging = Path(staging) if staging is not None else path.parent
    if staging.is_symlink() or not staging.is_dir():
        raise ValueError('Current staging directory is required')
    fd, name = tempfile.mkstemp(prefix=CONTROL + "-tmp-", dir=staging)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            if path.exists():
                os.chmod(temporary, stat.S_IMODE(path.stat().st_mode))
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if create_only:
            os.link(temporary, path)
        else:
            os.replace(temporary, path)
        sync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def file_lock(path):
    """OS-owned, nonblocking lock; never unlink the lock inode (even on exit)."""
    path = Path(path)
    if path.is_symlink():
        raise ValueError(f"Lock is a symlink: {path}")
    fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "r+b") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError(f"Lock must be a regular file: {path}")
        if os.name == "nt":
            import msvcrt
            if os.fstat(handle.fileno()).st_size == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError("Workspace/config is busy; retry after the other writer finishes") from exc
        else:
            import fcntl
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError("Workspace/config is busy; retry after the other writer finishes") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def slug(text, limit=24):
    """ASCII-only slug; user text never becomes a path component by itself."""
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    folded = re.sub(r"[^a-z0-9]+", "-", folded).strip("-")[:limit].strip("-")
    return folded or "x"


def new_identifier(prefix, text, limit=24):
    return f"{prefix}-{slug(text, limit)}-{secrets.token_hex(4)}"


def clean_text(value, field, limit=200):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"Invalid {field}")
    if any(unicodedata.category(c).startswith("C") for c in value):
        raise ValueError(f"Invalid {field}: control characters are not allowed")
    return value.strip()
