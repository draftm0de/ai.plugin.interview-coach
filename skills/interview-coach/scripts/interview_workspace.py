#!/usr/bin/env python3
"""Local workspace persistence. Cooperative locks, optimistic state checks and recovery."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

# Current storage identifier; no lookup or migration of previous identifiers.
APP = "interview-coach"
DEFAULT_CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "zyris" / APP / "config.json"
RUN_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,120}$")
LANGUAGE = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
CONTROL = ".zyris"
HEADER = "<!-- zyris-run: "
STATUSES = ("completed", "paused", "stopped_early")
REQUIRED = {"state.md": "file", "candidate/profile.md": "file", "runs": "dir", "jobs": "dir"}


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
    fd, name = tempfile.mkstemp(prefix=".zyris-tmp-", dir=staging)
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


@contextmanager
def workspace_lock(root, *, initializing=False, recovering=False):
    if not root.is_dir():
        raise ValueError(f"Workspace does not exist: {root}")
    if not initializing:
        require_valid(root)
    validate_run_records(root)
    if recovering:
        if journal_path(root).exists():
            read_transaction(root)
    else:
        require_clean(root)
    control = checked_path(root, CONTROL, "dir")
    control.mkdir(mode=0o700, exist_ok=True)
    sync_directory(root)
    with file_lock(checked_path(root, CONTROL + "/lock", "file")):
        validate_run_records(root)
        if not initializing:
            require_valid(root)
        yield


def journal_path(root):
    return checked_path(root, CONTROL + "/pending.json", "file")


def require_clean(root):
    if journal_path(root).exists():
        raise RuntimeError("Pending transaction; run recover before reading/resuming or changing the workspace")


def validate(root):
    root = safe_root(root)
    problems = []
    if (root/'workspace.yaml').exists() or (root/'workspace.yaml').is_symlink():
        problems.append('Unsupported workspace path-mapping manifest; manual reconciliation required')
    for relative, kind in {**REQUIRED, "candidate": "dir", CONTROL: "dir", "preferences.json": "file"}.items():
        try:
            path = checked_path(root, relative, kind)
            if relative in REQUIRED and not path.exists():
                problems.append(f"missing {relative}")
        except ValueError as exc:
            problems.append(str(exc))
    prefs = root / 'preferences.json'
    if prefs.is_file() and not prefs.is_symlink():
        try:
            data = strict_json(prefs.read_text(encoding='utf-8'))
            if not isinstance(data, dict) or type(data.get('schema_version')) is not int or data['schema_version'] != 1:
                raise ValueError('Unsupported preferences schema')
            for field in ('interface_language', 'interview_language'):
                if field in data and (not isinstance(data[field], str) or not LANGUAGE.fullmatch(data[field])):
                    raise ValueError('Invalid preferences language tag: ' + field)
        except (OSError, ValueError) as exc:
            problems.append(str(exc))
    return problems


def require_valid(root):
    problems = validate(root)
    if problems:
        raise ValueError("; ".join(problems))


def read_config(config):
    if config.is_symlink():
        raise ValueError("Config must not be a symlink")
    data = strict_json(config.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data.get("schema_version") != 1 or data.get("storage") != "local" or not isinstance(data.get("workspace"), str):
        raise ValueError("Unsupported config schema or storage adapter")
    return data


def init_workspace(root, config=DEFAULT_CONFIG, force=False):
    root = safe_root(root)
    config = Path(config).expanduser()
    for directory in (root, config.parent):
        for ancestor in (directory, *directory.parents):
            if ancestor.exists() and not ancestor.is_dir():
                raise ValueError('Expected directory: ' + str(ancestor))
    # A config placed inside the workspace could overwrite candidate/state files.
    if config.resolve().is_relative_to(root):
        raise ValueError("Configuration must be outside the candidate workspace")
    validate_run_records(root)
    for relative, kind in {**REQUIRED, "candidate": "dir", "README.md": "file", CONTROL: "dir", "preferences.json": "file"}.items():
        checked_path(root, relative, kind)
    problems = [problem for problem in validate(root) if not problem.startswith('missing ')]
    if problems:
        raise ValueError('; '.join(problems))
    require_clean(root)
    if config.exists() or config.is_symlink():
        existing = read_config(config)
        if existing["workspace"] != str(root) and not force:
            raise ValueError("Configuration exists for another workspace. Use --force to switch explicitly.")
    config.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(config.with_name(config.name + ".lock")):
        existing = read_config(config) if config.exists() or config.is_symlink() else {}
        if existing and existing["workspace"] != str(root) and not force:
            raise ValueError("Configuration exists for another workspace. Use --force to switch explicitly.")
        # Preflight all managed entries before creating defaults in an existing folder.
        for relative, kind in {**REQUIRED, "candidate": "dir", "README.md": "file", CONTROL: "dir", "preferences.json": "file"}.items():
            checked_path(root, relative, kind)
        root.mkdir(parents=True, exist_ok=True)
        with workspace_lock(root, initializing=True):
            require_clean(root)
            for folder in ("candidate", "jobs", "runs"):
                checked_path(root, folder, "dir").mkdir(exist_ok=True)
            defaults = {
                "state.md": "# Interview training state\n\nStatus: initial / no completed runs\n\n## Competencies\n\n## Next training\n",
                "candidate/profile.md": "# Candidate profile\n\nProvide an approved CV or verified profile before targeted interviews.\n",
                "README.md": "# Interview workspace\n\nPrivate candidate data. Skill: interview-coach.\n",
            }
            for name, content in defaults.items():
                target = checked_path(root, name, "file")
                if not target.exists():
                    write_atomic(target, content, create_only=True)
            data = dict(existing, schema_version=1, workspace=str(root), storage="local")
            write_atomic(config, json.dumps(data, allow_nan=False, indent=2) + "\n")
    return root


def configured_root(config=DEFAULT_CONFIG):
    config = Path(config)
    if not config.exists() and not config.is_symlink():
        raise FileNotFoundError("No workspace configured. Run: interview_workspace.py init --path PATH")
    root = safe_root(read_config(config)["workspace"])
    if not root.is_dir():
        raise FileNotFoundError(f"Configured workspace not found: {root}")
    return root


def state_digest(root):
    return hashlib.sha256(checked_path(root, "state.md", "file").read_bytes()).hexdigest()


def snapshot(root):
    root = safe_root(root)
    with workspace_lock(root):
        require_valid(root)
        require_clean(root)
        state = (root / "state.md").read_bytes()
        return {"workspace": str(root), "state": state.decode("utf-8"),
                "state_sha256": hashlib.sha256(state).hexdigest(), "problems": []}


def set_language(root, interface_language, interview_language=None):
    root = safe_root(root)
    if not LANGUAGE.fullmatch(interface_language) or (interview_language and not LANGUAGE.fullmatch(interview_language)):
        raise ValueError("Invalid language tag")
    with workspace_lock(root):
        require_valid(root)
        require_clean(root)
        target = checked_path(root, "preferences.json", "file")
        data = strict_json(target.read_text(encoding="utf-8")) if target.exists() else {"schema_version": 1}
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            raise ValueError("Unsupported preferences schema")
        data["interface_language"] = interface_language
        if interview_language:
            data["interview_language"] = interview_language
        write_atomic(target, json.dumps(data, allow_nan=False, ensure_ascii=False, indent=2) + "\n")
        return data


def run_path(root, run_id):
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id) or ".." in run_id:
        raise ValueError("Invalid run identifier")
    return checked_path(root, "runs/" + run_id + ".md", "file")


def validate_lifecycle(status, answered_count, planned_count):
    if status not in STATUSES or type(answered_count) is not int or answered_count < 0:
        raise ValueError("Invalid status or answered count")
    if planned_count is not None and (type(planned_count) is not int or planned_count < answered_count):
        raise ValueError("Invalid planned count")
    if status == "completed" and planned_count is not None and answered_count != planned_count:
        raise ValueError("Incomplete interview must be paused or stopped_early")


def parse_run(text, run_id):
    line, _, body = text.partition("\n")
    if not line.startswith(HEADER) or not line.endswith(" -->"):
        raise ValueError("Unsupported run format: current lifecycle metadata required; no migration performed")
    metadata = strict_json(line[len(HEADER):-4])
    required = {'schema_version', 'run_id', 'status', 'answered_count', 'planned_count', 'resume_from'}
    if (not isinstance(metadata, dict) or set(metadata) != required
            or type(metadata.get('schema_version')) is not int
            or metadata.get("schema_version") != 1 or metadata.get("run_id") != run_id):
        raise ValueError("Invalid run lifecycle metadata")
    validate_lifecycle(metadata.get("status"), metadata.get("answered_count"), metadata.get("planned_count"))
    source = metadata.get("resume_from")
    if source is not None and (not isinstance(source, str) or not RUN_ID.fullmatch(source) or ".." in source):
        raise ValueError("Invalid continuation identifier")
    return metadata, body


def read_run(root, run_id):
    return parse_run(run_path(root, run_id).read_text(encoding="utf-8"), run_id)


def validate_run_records(root):
    """Reject unsupported records before locks, initialization or other writes."""
    folder = checked_path(root, 'runs', 'dir')
    if not folder.exists():
        return
    records = {}
    for path in sorted(folder.iterdir()):
        try:
            checked_path(root, 'runs/' + path.name, 'file')
            if path.suffix != '.md':
                raise ValueError('Only current .md run records are supported')
            records[path.stem] = read_run(root, path.stem)[0]
        except (OSError, ValueError) as exc:
            raise ValueError(f'Unsupported run {path.name}: {exc}; manual reconciliation required; files unchanged') from exc

    validate_run_links(records)
    return records

def validate_run_links(records):
    successors = set()
    for identifier, metadata in records.items():
        source = metadata['resume_from']
        if source is None:
            continue
        previous = records.get(source)
        if (source == identifier or previous is None or previous['status'] != 'paused'
                or source in successors or metadata['answered_count'] < previous['answered_count']
                or (previous['planned_count'] is not None and metadata['planned_count'] != previous['planned_count'])):
            raise ValueError('Unsupported run continuation: ' + identifier + '; manual reconciliation required; files unchanged')
        successors.add(source)
        seen = {identifier}
        while source is not None and source in records:
            if source in seen:
                raise ValueError('Unsupported run continuation cycle; manual reconciliation required; files unchanged')
            seen.add(source)
            source = records[source]['resume_from']


def require_resumable(root, run_id):
    metadata, body = read_run(root, run_id)
    if metadata["status"] != "paused":
        raise ValueError("Only a paused checkpoint can be resumed")
    for path in (root / "runs").glob("*.md"):
        other, _ = read_run(root, path.stem)
        if other.get("resume_from") == run_id:
            raise ValueError("Checkpoint already continued; use its latest paused successor")
    return metadata, body


def resume(root, run_id):
    root = safe_root(root)
    with workspace_lock(root):
        require_valid(root)
        require_clean(root)
        metadata, body = require_resumable(root, run_id)
        state = (root / "state.md").read_bytes()
        return {"run": metadata, "transcript": body, "state": state.decode("utf-8"),
                "state_sha256": hashlib.sha256(state).hexdigest()}


def read_transaction(root):
    """Read and validate the current journal without creating control paths."""
    pending = journal_path(root)
    transaction = strict_json(pending.read_text(encoding="utf-8"))
    if (not isinstance(transaction, dict)
            or set(transaction) != {"schema_version", "run_id", "run_text", "state_text", "expected_state_sha256"}
            or type(transaction.get("schema_version")) is not int or transaction.get("schema_version") != 1):
        raise ValueError("Unsupported transaction schema; manual reconciliation required")
    for key in ("run_id", "run_text", "state_text", "expected_state_sha256"):
        if not isinstance(transaction.get(key), str):
            raise ValueError("Invalid transaction; manual reconciliation required")
    if not re.fullmatch(r"[0-9a-f]{64}", transaction["expected_state_sha256"]):
        raise ValueError("Invalid transaction state hash; manual reconciliation required")
    metadata, _ = parse_run(transaction["run_text"], transaction["run_id"])
    records = validate_run_records(root) or {}
    records[transaction["run_id"]] = metadata
    validate_run_links(records)
    run = run_path(root, transaction["run_id"])
    state = checked_path(root, "state.md", "file")
    new_digest = hashlib.sha256(transaction["state_text"].encode("utf-8")).hexdigest()
    if state_digest(root) not in (transaction["expected_state_sha256"], new_digest):
        raise ValueError("State changed outside pending transaction; manual reconciliation required")
    if run.exists() and run.read_bytes() != transaction["run_text"].encode("utf-8"):
        raise ValueError("Run conflicts with pending transaction; manual reconciliation required")
    return transaction


def apply_pending(root):
    """Replay validated intent only if targets are still old or intended data."""
    transaction = read_transaction(root)
    pending = journal_path(root)
    run = run_path(root, transaction["run_id"])
    state = checked_path(root, "state.md", "file")
    new_digest = hashlib.sha256(transaction["state_text"].encode("utf-8")).hexdigest()
    if not run.exists():
        write_atomic(run, transaction["run_text"], create_only=True, staging=checked_path(root, CONTROL, "dir"))
    if state_digest(root) != new_digest:
        write_atomic(state, transaction["state_text"])
    # Verify before clearing the recovery record or reporting success.
    if run.read_bytes() != transaction["run_text"].encode("utf-8") or state_digest(root) != new_digest:
        raise RuntimeError("Transaction verification failed; recovery record retained")
    pending.unlink()
    sync_directory(pending.parent)
    return run


def recover(root):
    root = safe_root(root)
    with workspace_lock(root, recovering=True):
        require_valid(root)
        if not journal_path(root).exists():
            return None
        return apply_pending(root)


def finish(root, run_id, run_text, state_text, *, expected_state_sha256,
           status="completed", answered_count=0, planned_count=None, resume_from=None):
    root = safe_root(root)
    validate_lifecycle(status, answered_count, planned_count)
    if not run_text.strip() or not state_text.strip():
        raise ValueError("Run and state must not be empty")
    with workspace_lock(root):
        require_valid(root)
        require_clean(root)
        run = run_path(root, run_id)
        if run.exists():
            raise FileExistsError(f"Run already exists: {run}")
        if state_digest(root) != expected_state_sha256:
            raise ValueError("Stale state snapshot; read status/resume and reconcile before retrying")
        if resume_from is not None:
            previous, _ = require_resumable(root, resume_from)
            if previous["planned_count"] is not None:
                if planned_count is None:
                    planned_count = previous["planned_count"]
                elif planned_count != previous["planned_count"]:
                    raise ValueError("Continuation must preserve the checkpoint's planned count")
            validate_lifecycle(status, answered_count, planned_count)
            if answered_count < previous["answered_count"]:
                raise ValueError("Answered count cannot decrease on continuation")
        metadata = dict(schema_version=1, run_id=run_id, status=status,
                        answered_count=answered_count, planned_count=planned_count,
                        resume_from=resume_from)
        transaction = dict(schema_version=1, run_id=run_id,
                           run_text=HEADER + json.dumps(metadata, allow_nan=False, ensure_ascii=False) + " -->\n" + run_text,
                           state_text=state_text, expected_state_sha256=expected_state_sha256)
        try:
            write_atomic(journal_path(root), json.dumps(transaction, allow_nan=False, ensure_ascii=False) + "\n", create_only=True)
            return apply_pending(root)
        except (OSError, ValueError, RuntimeError) as exc:
            # Recovery is possible only while a recorded intent exists.
            try:
                if journal_path(root).exists():
                    guidance = "Pending transaction. Run recover; if recovery conflicts, reconcile manually"
                elif (run.exists() and run.read_bytes() == transaction["run_text"].encode("utf-8")
                      and state_digest(root) == hashlib.sha256(state_text.encode("utf-8")).hexdigest()):
                    guidance = ("Run and state match the intended content, but final durability was not confirmed. "
                                "No pending transaction; recover cannot replay it. Inspect the existing run/state; "
                                "do not create another run or overwrite them")
                elif not run.exists() and state_digest(root) == expected_state_sha256:
                    guidance = ("No transaction recorded; recover has nothing to replay. Resolve the write error, "
                                "then retry the same run ID with the original state hash; reconcile if stale")
                else:
                    guidance = "No pending transaction; inspect run/state and reconcile manually before retrying"
            except (OSError, ValueError):
                guidance = "Save state could not be inspected; inspect journal/run/state and reconcile manually"
            raise RuntimeError("Save incomplete; do not claim success. " + guidance) from exc


def main(argv=None):
    p = argparse.ArgumentParser(description="ZYRIS Interview Coach workspace manager")
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init", help="Create missing workspace files and local pointer")
    i.add_argument("--path", required=True)
    i.add_argument("--force", action="store_true", help="Switch the pointer; never overwrite candidate files")
    sub.add_parser("status", help="Read state and its hash under the workspace lock")
    v = sub.add_parser("validate")
    v.add_argument("--path")
    f = sub.add_parser("finish", help="Save an immutable run and updated state with recovery")
    f.add_argument("--run-id", required=True)
    f.add_argument("--run-file", type=Path, required=True)
    f.add_argument("--state-file", type=Path, required=True)
    f.add_argument("--expected-state-sha256", required=True, help="Hash from status/resume before preparing state")
    f.add_argument("--status", choices=STATUSES, required=True)
    f.add_argument("--answered-count", type=int, required=True)
    f.add_argument("--planned-count", type=int)
    f.add_argument("--resume-from")
    res = sub.add_parser("resume", help="Read a paused checkpoint without changing it")
    res.add_argument("--run-id", required=True)
    sub.add_parser("recover", help="Complete a pending transaction without overwriting conflicting data")
    lang = sub.add_parser("set-language")
    lang.add_argument("--interface", required=True, dest="interface_language")
    lang.add_argument("--interview", dest="interview_language")
    args = p.parse_args(argv)
    try:
        if args.cmd == "init":
            print(f"Initialized: {init_workspace(args.path, args.config, args.force)}")
        else:
            root = safe_root(args.path) if args.cmd == "validate" and args.path else configured_root(args.config)
            if args.cmd == "status":
                print(json.dumps(snapshot(root), ensure_ascii=False, indent=2))
            elif args.cmd == "validate":
                with workspace_lock(root):
                    problems = validate(root)
                    if journal_path(root).exists():
                        problems.append("pending transaction: run recover")
                print("VALID" if not problems else "\n".join(problems))
                return int(bool(problems))
            elif args.cmd == "set-language":
                print(json.dumps(set_language(root, args.interface_language, args.interview_language)))
            elif args.cmd == "resume":
                print(json.dumps(resume(root, args.run_id), ensure_ascii=False, indent=2))
            elif args.cmd == "recover":
                run = recover(root)
                print(f"Recovered and verified: {run}" if run else "No pending transaction")
            elif args.cmd == "finish":
                run = finish(root, args.run_id, args.run_file.read_text(encoding="utf-8"),
                             args.state_file.read_text(encoding="utf-8"),
                             expected_state_sha256=args.expected_state_sha256, status=args.status,
                             answered_count=args.answered_count, planned_count=args.planned_count,
                             resume_from=args.resume_from)
                print(f"Saved and verified run: {run}\nUpdated state: {root / 'state.md'}")
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
