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

APP = "zyris-interview-coach"
DEFAULT_CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "zyris" / APP / "config.json"
RUN_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,120}$")
LANGUAGE = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
CONTROL = ".zyris"
HEADER = "<!-- zyris-run: "
STATUSES = ("completed", "paused", "stopped_early")
REQUIRED = {"state.md": "file", "candidate/profile.md": "file", "runs": "dir", "jobs": "dir"}


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


def write_atomic(path, content, *, create_only=False):
    """Publish a flushed, unique sibling file; create_only never replaces a target."""
    path = Path(path)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"Unsafe file target: {path}")
    fd, name = tempfile.mkstemp(prefix=".zyris-tmp-", dir=path.parent)
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
def workspace_lock(root):
    if not root.is_dir():
        raise ValueError(f"Workspace does not exist: {root}")
    control = checked_path(root, CONTROL, "dir")
    control.mkdir(mode=0o700, exist_ok=True)
    sync_directory(root)
    with file_lock(checked_path(root, CONTROL + "/lock", "file")):
        yield


def journal_path(root):
    return checked_path(root, CONTROL + "/pending.json", "file")


def require_clean(root):
    if journal_path(root).exists():
        raise RuntimeError("Pending transaction; run recover before reading/resuming or changing the workspace")


def validate(root):
    root = safe_root(root)
    problems = []
    for relative, kind in {**REQUIRED, "candidate": "dir", CONTROL: "dir", "preferences.json": "file"}.items():
        try:
            path = checked_path(root, relative, kind)
            if relative in REQUIRED and not path.exists():
                problems.append(f"missing {relative}")
        except ValueError as exc:
            problems.append(str(exc))
    return problems


def require_valid(root):
    problems = validate(root)
    if problems:
        raise ValueError("; ".join(problems))


def read_config(config):
    if config.is_symlink():
        raise ValueError("Config must not be a symlink")
    data = json.loads(config.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1 or data.get("storage") != "local" or not isinstance(data.get("workspace"), str):
        raise ValueError("Unsupported config schema or storage adapter")
    return data


def init_workspace(root, config=DEFAULT_CONFIG, force=False):
    root = safe_root(root)
    config = Path(config).expanduser()
    # A config placed inside the workspace could overwrite candidate/state files.
    if config.resolve().is_relative_to(root):
        raise ValueError("Configuration must be outside the candidate workspace")
    config.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(config.with_name(config.name + ".lock")):
        existing = read_config(config) if config.exists() or config.is_symlink() else {}
        if existing and existing["workspace"] != str(root) and not force:
            raise ValueError("Configuration exists for another workspace. Use --force to switch explicitly.")
        # Preflight all managed entries before creating defaults in an existing folder.
        for relative, kind in {**REQUIRED, "candidate": "dir", "README.md": "file", CONTROL: "dir", "preferences.json": "file"}.items():
            checked_path(root, relative, kind)
        root.mkdir(parents=True, exist_ok=True)
        with workspace_lock(root):
            require_clean(root)
            for folder in ("candidate", "jobs", "runs"):
                checked_path(root, folder, "dir").mkdir(exist_ok=True)
            defaults = {
                "state.md": "# Interview training state\n\nStatus: initial / no completed runs\n\n## Competencies\n\n## Next training\n",
                "candidate/profile.md": "# Candidate profile\n\nProvide an approved CV or verified profile before targeted interviews.\n",
                "README.md": "# Interview workspace\n\nPrivate candidate data. Skill: zyris-interview-coach.\n",
            }
            for name, content in defaults.items():
                target = checked_path(root, name, "file")
                if not target.exists():
                    write_atomic(target, content, create_only=True)
            data = dict(existing, schema_version=1, workspace=str(root), storage="local")
            write_atomic(config, json.dumps(data, indent=2) + "\n")
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
        data = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {"schema_version": 1}
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            raise ValueError("Unsupported preferences schema")
        data["interface_language"] = interface_language
        if interview_language:
            data["interview_language"] = interview_language
        write_atomic(target, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
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
        raise ValueError("Legacy run has no verified lifecycle metadata; inspect manually")
    metadata = json.loads(line[len(HEADER):-4])
    if not isinstance(metadata, dict) or metadata.get("schema_version") != 1 or metadata.get("run_id") != run_id:
        raise ValueError("Invalid run lifecycle metadata")
    validate_lifecycle(metadata.get("status"), metadata.get("answered_count"), metadata.get("planned_count"))
    source = metadata.get("resume_from")
    if source is not None and (not isinstance(source, str) or not RUN_ID.fullmatch(source) or ".." in source):
        raise ValueError("Invalid continuation identifier")
    return metadata, body


def read_run(root, run_id):
    return parse_run(run_path(root, run_id).read_text(encoding="utf-8"), run_id)


def require_resumable(root, run_id):
    metadata, body = read_run(root, run_id)
    if metadata["status"] != "paused":
        raise ValueError("Only a paused checkpoint can be resumed")
    for path in (root / "runs").glob("*.md"):
        # Do not interpret or rewrite legacy records; reject unsafe links.
        text = run_path(root, path.stem).read_text(encoding="utf-8")
        if text.startswith(HEADER):
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


def apply_pending(root):
    """Replay a recorded intent only if both targets are still old or intended data."""
    pending = journal_path(root)
    transaction = json.loads(pending.read_text(encoding="utf-8"))
    if not isinstance(transaction, dict) or transaction.get("schema_version") != 1:
        raise ValueError("Unsupported transaction schema; manual reconciliation required")
    for key in ("run_id", "run_text", "state_text", "expected_state_sha256"):
        if not isinstance(transaction.get(key), str):
            raise ValueError("Invalid transaction; manual reconciliation required")
    if not re.fullmatch(r"[0-9a-f]{64}", transaction["expected_state_sha256"]):
        raise ValueError("Invalid transaction state hash; manual reconciliation required")
    parse_run(transaction["run_text"], transaction["run_id"])
    run = run_path(root, transaction["run_id"])
    state = checked_path(root, "state.md", "file")
    new_digest = hashlib.sha256(transaction["state_text"].encode("utf-8")).hexdigest()
    if state_digest(root) not in (transaction["expected_state_sha256"], new_digest):
        raise ValueError("State changed outside pending transaction; manual reconciliation required")
    if run.exists() and run.read_bytes() != transaction["run_text"].encode("utf-8"):
        raise ValueError("Run conflicts with pending transaction; manual reconciliation required")
    if not run.exists():
        write_atomic(run, transaction["run_text"], create_only=True)
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
    with workspace_lock(root):
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
                           run_text=HEADER + json.dumps(metadata, ensure_ascii=False) + " -->\n" + run_text,
                           state_text=state_text, expected_state_sha256=expected_state_sha256)
        try:
            write_atomic(journal_path(root), json.dumps(transaction, ensure_ascii=False) + "\n", create_only=True)
            return apply_pending(root)
        except (OSError, ValueError, RuntimeError) as exc:
            raise RuntimeError("Save incomplete; do not claim success. Run recover; if recovery conflicts, reconcile manually") from exc


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
