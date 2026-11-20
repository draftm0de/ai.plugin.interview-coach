#!/usr/bin/env python3
"""Interview Coach runtime (workspace format 3): projects, candidates, CVs, jobs, runs, Git coordination.

Only the current format is supported. Unsupported layouts are rejected before any
write and are never migrated, deleted or overwritten.
"""
import argparse
from contextlib import contextmanager, nullcontext
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import coach_core as core  # noqa: E402
import coach_extract as extractor  # noqa: E402
import coach_git as gitstore  # noqa: E402
from coach_core import (CANDIDATE_ID, CONTROL, LEGACY_CONTROL, JOB_ID, RUN_ID, checked_path, clean_text, file_lock,  # noqa: E402
                        new_identifier, safe_root, strict_json, sync_directory, write_atomic)

APP = "interview-coach"
FORMAT = "interview-coach-workspace"
SCHEMA = 3   # 3: internal control folder `.journal` (format 2 used `.zyris`); no format-2 data is read, migrated or aliased
DEFAULT_CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "zyris" / APP / "projects"
LANGUAGE = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HEADER = "<!-- zyris-run: "
ARTIFACT_HEADER = "<!-- zyris-artifact: "
STATUSES = ("completed", "paused", "stopped_early")
PROFILE_STATUS = ("missing", "draft", "confirmed")
ARTIFACT_KINDS = {"posting": "postings", "research": "research", "match": "match", "preparation": "preparation"}
LEGACY_MARKERS = ("state.md", "candidate", "runs", "jobs", "preferences.json", "workspace.yaml")
TEMP_PREFIXES = ("/tmp", "/private/tmp", "/var/tmp", "/private/var/folders", "/var/folders")


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def dump(data):
    return json.dumps(data, allow_nan=False, ensure_ascii=False, indent=2) + "\n"


def parse_header(text, prefix, what):
    line, _, body = text.partition("\n")
    if not line.startswith(prefix) or not line.endswith(" -->"):
        raise ValueError(f"Unsupported {what} format: current format-{SCHEMA} metadata required; no migration performed")
    return strict_json(line[len(prefix):-4]), body


# ---------------------------------------------------------------- workspace

def scan_layout(root):
    """Read-only layout scan WITHOUT following links. Returns (legacy_markers, unsafe_entries).

    legacy: `.zyris` (folder, file or symlink, also dangling) at workspace level or inside a REAL candidate directory.
    unsafe: `candidates` itself or a candidate entry that is a symlink (also dangling): nothing below it is looked at.
    If the layout cannot be inspected, this raises instead of reporting "no marker".
    """
    root = Path(root)
    legacy, unsafe = [], []
    if os.path.lexists(root / LEGACY_CONTROL):
        legacy.append(LEGACY_CONTROL)
    candidates = root / "candidates"
    if candidates.is_symlink():
        unsafe.append("candidates (symbolic link)")
        return legacy, unsafe
    if not os.path.lexists(candidates):
        return legacy, unsafe
    try:
        with os.scandir(candidates) as entries:
            for entry in sorted(entries, key=lambda e: e.name):
                if entry.is_symlink():
                    unsafe.append(f"candidates/{entry.name} (symbolic link)")
                elif entry.is_dir(follow_symlinks=False) and os.path.lexists(os.path.join(entry.path, LEGACY_CONTROL)):
                    legacy.append(f"candidates/{entry.name}/{LEGACY_CONTROL}")
    except OSError as exc:
        raise ValueError(f"Cannot inspect the candidate directories ({exc}); refusing, because a safe decision is not possible") from exc
    return legacy, unsafe


def layout_refusal(root):
    legacy, unsafe = scan_layout(root)
    if unsafe:
        return ("Unsafe layout: " + ", ".join(unsafe[:6]) + ". Symbolic links are never followed and nothing below them was inspected; "
                "all data is left unchanged")
    if legacy:
        return ("Unsupported old control layout (" + ", ".join(legacy[:6]) + "): format 2 data is not supported. All data is left "
                "unchanged and nothing was migrated, read for resumption, moved or deleted; a new, empty storage location is "
                "required (a mixed layout with .journal is refused as well)")
    return None


def reject_legacy_layout(root):
    message = layout_refusal(root)
    if message:
        raise ValueError(message)


def check_workspace_target(path):
    """Read-only check of existing content BEFORE any lock, journal or write: old/unsafe layout, wrong format, foreign files.

    A genuinely empty target (only `.git`/`.journal`) passes and stays initializable; a valid format-3 workspace passes and is reused.
    """
    reject_legacy_layout(path)
    if [e for e in Path(path).iterdir() if e.name not in (".git", CONTROL)]:
        require_workspace(path)


def workspace_problems(root):
    """Read-only structural validation of the workspace (no writes)."""
    root = safe_root(root)
    try:
        refusal = layout_refusal(root)
    except ValueError as exc:
        return [str(exc)]
    if refusal:
        return [refusal]
    problems = []
    manifest = root / "workspace.json"
    if manifest.is_symlink() or not manifest.is_file():
        legacy = [m for m in LEGACY_MARKERS if (root / m).exists() or (root / m).is_symlink()]
        if legacy:
            return [f"Unsupported workspace format (legacy layout: {', '.join(legacy)}); no migration performed, files unchanged"]
        return ["missing workspace.json"]
    try:
        data = strict_json(manifest.read_text(encoding="utf-8"))
        if (not isinstance(data, dict) or set(data) != {"format", "schema_version", "created_at"}
                or data["format"] != FORMAT or type(data["schema_version"]) is not int or data["schema_version"] != SCHEMA):
            raise ValueError(f"Unsupported workspace manifest (format {FORMAT}, schema {SCHEMA} required)")
        for name, kind in (("candidates", "dir"), (CONTROL, "dir"), ("preferences.json", "file")):
            checked_path(root, name, kind)
        prefs = root / "preferences.json"
        if prefs.is_file():
            value = strict_json(prefs.read_text(encoding="utf-8"))
            if not isinstance(value, dict) or value.get("schema_version") != SCHEMA or type(value.get("schema_version")) is not int:
                raise ValueError("Unsupported preferences schema")
            for field in ("interface_language", "interview_language"):
                if field in value and (not isinstance(value[field], str) or not LANGUAGE.fullmatch(value[field])):
                    raise ValueError("Invalid preferences language tag: " + field)
        folder = checked_path(root, "candidates", "dir")
        if not folder.is_dir():
            raise ValueError("missing candidates/")
        for entry in sorted(e for e in folder.iterdir() if not e.name.startswith('.')):
            problems += [f"{entry.name}: {p}" for p in candidate_problems(root, entry.name)]
    except (OSError, ValueError) as exc:
        problems.append(str(exc))
    return problems


def require_workspace(root):
    problems = workspace_problems(root)
    if problems:
        raise ValueError("; ".join(problems))


def init_workspace(root):
    """Create or reuse a format-3 workspace. Never alters existing content."""
    root = safe_root(root)
    for ancestor in (root, *root.parents):
        if ancestor.exists() and not ancestor.is_dir():
            raise ValueError("Expected directory: " + str(ancestor))
    if root.exists():
        entries = [e for e in root.iterdir() if e.name not in (".git", CONTROL)]
        if entries:
            require_workspace(root)  # reuses a valid workspace, rejects legacy/unrelated content
        if not os.access(root, os.R_OK | os.W_OK | os.X_OK):
            raise PermissionError(f"Directory is not readable and writable: {root}")
    root.mkdir(parents=True, exist_ok=True)
    if not os.access(root, os.R_OK | os.W_OK | os.X_OK):
        raise PermissionError(f"Directory is not readable and writable: {root}")
    checked_path(root, CONTROL, "dir").mkdir(mode=0o700, exist_ok=True)
    with file_lock(checked_path(root, CONTROL + "/lock", "file")):
        defaults = {
            "workspace.json": dump({"format": FORMAT, "schema_version": SCHEMA, "created_at": now()}),
            "README.md": "# Interview workspace\n\nPrivate candidate data. Skill: interview-coach. Format 3.\n",
            ".gitignore": CONTROL + "/\n",
            "preferences.json": dump({"schema_version": SCHEMA}),
        }
        for name, content in defaults.items():
            target = checked_path(root, name, "file")
            if not target.exists():
                write_atomic(target, content, create_only=True)
        checked_path(root, "candidates", "dir").mkdir(exist_ok=True)
        keep = checked_path(root, "candidates/.gitkeep", "file")  # git does not track empty directories
        if not keep.exists():
            write_atomic(keep, "", create_only=True)
        sync_directory(root)
    require_workspace(root)
    return root


def set_language(root, interface_language, interview_language=None):
    root = safe_root(root)
    if not LANGUAGE.fullmatch(interface_language) or (interview_language and not LANGUAGE.fullmatch(interview_language)):
        raise ValueError("Invalid language tag")
    require_workspace(root)
    with file_lock(checked_path(root, CONTROL + "/lock", "file")):
        target = checked_path(root, "preferences.json", "file")
        data = strict_json(target.read_text(encoding="utf-8"))
        data["interface_language"] = interface_language
        if interview_language:
            data["interview_language"] = interview_language
        write_atomic(target, dump(data))
        return data


# ----------------------------------------------------------------- projects

def project_key(project):
    return hashlib.sha256(str(project).encode("utf-8")).hexdigest()[:32]


def project_config_path(project, config_dir):
    return Path(config_dir).expanduser() / (project_key(project) + ".json")


def read_project_config(project, config_dir=DEFAULT_CONFIG_DIR):
    """Explicit per-project resolution; there is no global pointer and no discovery."""
    project = safe_root(project)
    path = project_config_path(project, config_dir)
    if path.is_symlink() or not path.is_file():
        raise FileNotFoundError(f"No storage configured for project {project}. Run setup (project-init) first")
    data = strict_json(path.read_text(encoding="utf-8"))
    if (not isinstance(data, dict) or data.get("schema_version") != SCHEMA or type(data.get("schema_version")) is not int
            or data.get("project") != str(project) or data.get("storage") not in ("local", "git")
            or not isinstance(data.get("workspace"), str)):
        raise ValueError("Unsupported project configuration; no fallback or migration performed")
    if data["storage"] == "git" and not (isinstance(data.get("git"), dict) and data["git"].get("visibility") == "private"):
        raise ValueError("Git project configuration lacks confirmed private repository evidence")
    return data


def check_switch(existing, storage, workspace, remote, switch):
    """Refuse a change of target, storage type or repository unless explicitly confirmed. Read-only."""
    if existing is None or switch:
        return
    same = (existing["workspace"] == str(workspace) and existing["storage"] == storage
            and (storage != "git" or existing["git"]["remote"] == remote))
    if not same:
        raise ValueError("This project already uses another storage target or type. Confirm switching explicitly (--switch); "
                         "nothing was changed")


def existing_config(project, config_dir):
    path = project_config_path(project, config_dir)
    if path.exists() or path.is_symlink():
        return read_project_config(project, config_dir)  # invalid configurations are rejected here, before any mutation
    return None


def write_pointer(project, workspace, storage, config_dir, git_evidence, switch, remote):
    """Write the pointer; the caller holds the per-project lock."""
    check_switch(existing_config(project, config_dir), storage, workspace, remote, switch)
    data = {"schema_version": SCHEMA, "project": str(project), "storage": storage, "workspace": str(workspace)}
    if git_evidence:
        data["git"] = dict(git_evidence, checked_at=now())
    write_atomic(project_config_path(project, config_dir), dump(data))
    return data


def project_workspace(project, config_dir=DEFAULT_CONFIG_DIR):
    config = read_project_config(project, config_dir)
    root = safe_root(config["workspace"])
    if not root.is_dir():
        raise FileNotFoundError(f"Configured workspace not found: {root}")
    require_workspace(root)
    return root, config


def setup_project(project, storage, path, *, config_dir=DEFAULT_CONFIG_DIR, switch=False, remote=None, attest=None):
    """Storage setup. 'none' is refused: Nicht speichern writes nothing at all.

    Order: (1) read-only preflight incl. the switch decision, (2) the same decision again under the
    per-project lock, (3) only then any mutation (clone, workspace files, remote publish, pointer).
    """
    if storage not in ("local", "git"):
        raise ValueError("Nicht speichern creates no workspace or pointer; only local and git are configurable")
    project = safe_root(project)
    if not project.is_dir():
        raise ValueError(f"Project folder does not exist: {project}")
    if not path:
        raise ValueError("An explicit storage path is required (the project folder is only a suggestion)")
    path = safe_root(path)
    config_dir = Path(config_dir).expanduser()
    if config_dir.resolve().is_relative_to(path):
        raise ValueError("Configuration must be outside the workspace")
    if storage == "git":
        if not remote:
            raise ValueError("An explicit private GitHub/GitLab repository is required")
        gitstore.parse_remote(remote)
    check_switch(existing_config(project, config_dir), storage, path, remote, switch)  # (1) no side effects so far
    if config_dir.exists() and not config_dir.is_dir():
        raise ValueError("Expected directory: " + str(config_dir))
    if path.exists():  # unsupported/legacy/foreign content is rejected before anything is created
        for ancestor in (path, *path.parents):
            if ancestor.exists() and not ancestor.is_dir():
                raise ValueError("Expected directory: " + str(ancestor))
        if [e for e in path.iterdir() if e.name not in (".git", CONTROL)]:
            require_workspace(path)
    evidence = None
    if storage == "git":  # read-only checks first
        gitstore.check_rewrite(remote)
        evidence = gitstore.verify_target(remote, attest=attest)
    config_dir.mkdir(parents=True, exist_ok=True)
    pointer = project_config_path(project, config_dir)
    with file_lock(pointer.with_name(pointer.name + ".lock")):  # serializes concurrent setups of this project
        check_switch(existing_config(project, config_dir), storage, path, remote, switch)  # (2)
        result = {}
        if storage == "git":
            result["clone"] = gitstore.prepare_clone(path, remote)
            # The clone itself is the only unavoidable write so far. Everything after it starts only if the cloned content is
            # an empty repository or a valid format-3 workspace: check read-only BEFORE any lock, journal, commit, push or pointer.
            check_workspace_target(path)
            evidence["targets"] = gitstore.resolve_targets(path, remote)
            root = safe_root(path)
            with git_save_guard(root, "Initialize interview coach workspace", create=True):
                init_workspace(path)
            with git_lock(root):
                result["publish"] = gitstore.publish(root, evidence["targets"])
        else:
            root = init_workspace(path)
            if str(root).startswith(TEMP_PREFIXES):
                result["warning"] = "Directory is in a temporary location and may not be durable"
        config = write_pointer(project, root, storage, config_dir, evidence, switch, remote)
    return dict(result, project=str(project), storage=storage, workspace=str(root),
                reused=bool(result.get("clone") == "existing"), config=config)


def interrupted_path(root):
    return Path(root) / CONTROL / "interrupted.json"


def git_lock(root):
    """One cooperative lock per Git workspace for saving AND publishing (order: pointer lock -> git lock -> workspace/candidate locks)."""
    control = Path(root) / CONTROL
    control.mkdir(mode=0o700, exist_ok=True)
    return file_lock(checked_path(root, CONTROL + "/git.lock", "file"))


def read_interrupted(root):
    """{relative path: sha256|None} left by a failed save. Unknown formats are refused, never resumed silently."""
    path = interrupted_path(root)
    if not path.exists() and not path.is_symlink():
        return {}
    try:
        data = strict_json(path.read_text(encoding="utf-8"))
        files = data.get("files") if isinstance(data, dict) else None
        if (not isinstance(data, dict) or set(data) != {"schema_version", "files"} or data["schema_version"] != SCHEMA
                or type(data["schema_version"]) is not int or not isinstance(files, dict)
                or not all(isinstance(k, str) and (v is None or (isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v))) for k, v in files.items())):
            raise ValueError("unsupported format")
    except (OSError, ValueError) as exc:
        raise gitstore.GitStorageError(f"Unsupported interrupted-save journal ({exc}); it is left untouched. Inspect {path} "
                                       "and the workspace manually; nothing is resumed automatically") from exc
    return files


def record_interrupted(root, touched):
    """Remember what a failed save wrote, with content hashes, so unchanged leftovers can be resumed and changed ones cannot."""
    root = Path(root)
    try:
        known = read_interrupted(root)
    except gitstore.GitStorageError:
        return  # keep the unreadable journal as it is
    changed = set(gitstore.changed_paths(root))
    for relative in changed & touched | (changed & set(known)):
        known[relative] = gitstore.file_digest(root, relative)
    if (root / CONTROL).is_dir() and not (root / CONTROL).is_symlink() and known:
        write_atomic(interrupted_path(root), dump({"schema_version": SCHEMA, "files": dict(sorted(known.items()))}))


@contextmanager
def git_save_guard(root, message, create=False):
    """Git storage: under the workspace Git lock refuse foreign/staged changes, run the save, commit exactly its own paths.

    Own paths = what this process wrote through the managed writers plus unchanged leftovers of an interrupted save.
    Anything else that appears is never committed. Limit: programs that ignore the cooperative lock can still race.
    """
    root = Path(root)
    if create:
        (root / CONTROL).mkdir(parents=True, exist_ok=True)
    with git_lock(root):
        leftovers = read_interrupted(root)
        gitstore.baseline(root, allowed=leftovers)
        with core.recording() as touched:
            try:
                yield
                relative = {str(Path(t).resolve().relative_to(root.resolve())) for t in touched if Path(t).resolve().is_relative_to(root.resolve())}
                gitstore.commit_own(root, message, relative | set(leftovers))
            except BaseException:
                inside = {str(Path(t).resolve().relative_to(root.resolve())) for t in touched if Path(t).resolve().is_relative_to(root.resolve())}
                record_interrupted(root, inside)
                raise
        interrupted_path(root).unlink(missing_ok=True)


# --------------------------------------------------------------- candidates

CANDIDATE_KEYS = {"schema_version", "candidate_id", "display_name", "status", "created_at", "profile", "cv_sources"}
PROFILE_KEYS = {"status", "origin", "cv_source", "updated_at"}


def candidate_dir(root, candidate_id):
    if not isinstance(candidate_id, str) or not CANDIDATE_ID.fullmatch(candidate_id):
        raise ValueError("Invalid candidate identifier")
    return checked_path(root, "candidates/" + candidate_id, "dir")


def read_candidate(cdir):
    path = checked_path(cdir, "candidate.json", "file")
    data = strict_json(path.read_text(encoding="utf-8"))
    if (not isinstance(data, dict) or set(data) != CANDIDATE_KEYS or data["schema_version"] != SCHEMA
            or type(data["schema_version"]) is not int or data["candidate_id"] != cdir.name
            or data["status"] not in ("creating", "active") or not isinstance(data["display_name"], str)
            or not isinstance(data["cv_sources"], list)
            or not isinstance(data["profile"], dict) or set(data["profile"]) != PROFILE_KEYS
            or data["profile"]["status"] not in PROFILE_STATUS):
        raise ValueError("Unsupported or inconsistent candidate record")
    return data


def candidate_problems(root, candidate_id):
    problems = []
    try:
        cdir = candidate_dir(root, candidate_id)
        meta = read_candidate(cdir)
        if meta["status"] != "active":
            return [f"candidate {candidate_id} is incomplete (status creating); run candidate-recover"]
        for name, kind in (("state.md", "file"), ("profile.md", "file"), ("runs", "dir"), ("jobs", "dir"), ("cv", "dir")):
            if not checked_path(cdir, name, kind).exists():
                problems.append(f"candidate {candidate_id}: missing {name}")
        for source in meta["cv_sources"]:
            if not checked_path(cdir, "cv/" + str(source), "dir").is_dir():
                problems.append(f"candidate {candidate_id}: missing cv source {source}")
        validate_run_records(cdir)
        for job in sorted(checked_path(cdir, "jobs", "dir").iterdir()):
            read_job(cdir, job.name)
    except (OSError, ValueError) as exc:
        problems.append(f"candidate {candidate_id}: {exc}")
    return problems


MATERIALIZE = {
    "state.md": "# Interview training state\n\nStatus: initial / no completed runs\n\n## Competencies\n\n## Next training\n",
    "profile.md": "# Candidate profile\n\nStatus: missing. Import a CV or build a profile before targeted preparation.\n",
}


def materialize_candidate(cdir):
    """Idempotent: creates only what is missing and never overwrites."""
    checked_path(cdir, CONTROL, "dir").mkdir(mode=0o700, exist_ok=True)
    for folder in ("runs", "jobs", "cv"):
        checked_path(cdir, folder, "dir").mkdir(exist_ok=True)
    for name, content in MATERIALIZE.items():
        target = checked_path(cdir, name, "file")
        if not target.exists():
            write_atomic(target, content, create_only=True)
    sync_directory(cdir)


def create_candidate(root, name):
    root = safe_root(root)
    name = clean_text(name, "name")
    require_workspace(root)
    with file_lock(checked_path(root, CONTROL + "/lock", "file")):
        for _ in range(8):
            candidate_id = new_identifier("c", name)
            cdir = checked_path(root, "candidates/" + candidate_id)
            try:
                cdir.mkdir()
                break
            except FileExistsError:
                continue
        else:
            raise RuntimeError("Could not allocate a unique candidate identifier")
        meta = {"schema_version": SCHEMA, "candidate_id": candidate_id, "display_name": name, "status": "creating",
                "created_at": now(), "profile": {"status": "missing", "origin": "none", "cv_source": None, "updated_at": None},
                "cv_sources": []}
        try:
            write_atomic(cdir / "candidate.json", dump(meta), create_only=True)
            materialize_candidate(cdir)
            meta["status"] = "active"
            write_atomic(cdir / "candidate.json", dump(meta))
            read_candidate(cdir)
        except (OSError, ValueError, RuntimeError) as exc:
            raise RuntimeError(f"Candidate creation incomplete ({candidate_id}); the record is kept as a draft and is not usable. "
                               f"Resolve the error ({exc}) and run candidate-recover --candidate {candidate_id}") from exc
    return meta


def recover_candidate(root, candidate_id):
    root = safe_root(root)
    require_workspace_shallow(root)
    with file_lock(checked_path(root, CONTROL + "/lock", "file")):
        cdir = candidate_dir(root, candidate_id)
        meta = read_candidate(cdir)
        if meta["status"] == "active":
            return meta
        materialize_candidate(cdir)
        meta["status"] = "active"
        write_atomic(cdir / "candidate.json", dump(meta))
        return read_candidate(cdir)


def require_workspace_shallow(root):
    reject_legacy_layout(root)
    manifest = checked_path(root, "workspace.json", "file")
    data = strict_json(manifest.read_text(encoding="utf-8"))
    if data.get("format") != FORMAT or data.get("schema_version") != SCHEMA:
        raise ValueError("Unsupported workspace format")


def list_candidates(root):
    root = safe_root(root)
    require_workspace_shallow(root)
    result = []
    for entry in sorted(e for e in checked_path(root, "candidates", "dir").iterdir() if not e.name.startswith(".")):
        meta = read_candidate(candidate_dir(root, entry.name))
        result.append({"candidate_id": meta["candidate_id"], "display_name": meta["display_name"], "status": meta["status"],
                       "profile_status": meta["profile"]["status"], "created_at": meta["created_at"]})
    names = [c["display_name"].casefold() for c in result]
    for c in result:
        c["name_is_ambiguous"] = names.count(c["display_name"].casefold()) > 1
    return result


def resolve_candidate(root, candidate_id=None, name=None):
    """Exact ID, or a name that matches exactly one active candidate; otherwise report the choices."""
    candidates = list_candidates(root)
    if candidate_id:
        found = [c for c in candidates if c["candidate_id"] == candidate_id]
    elif name:
        found = [c for c in candidates if c["display_name"].casefold() == name.casefold()]
    else:
        found = candidates
    if len(found) != 1:
        raise LookupError(json.dumps({"resolved": False, "reason": "no match" if not found else "ambiguous: ask the user",
                                      "choices": found}, ensure_ascii=False))
    if found[0]["status"] != "active":
        raise ValueError(f"Candidate {found[0]['candidate_id']} is incomplete; run candidate-recover")
    return found[0]


# --------------------------------------------------------- candidate locking

def candidate_journal(cdir):
    return checked_path(cdir, CONTROL + "/pending.json", "file")


def require_clean(cdir):
    if candidate_journal(cdir).exists():
        raise RuntimeError("Pending transaction; run recover before reading/resuming or changing this candidate")


def require_active(cdir):
    meta = read_candidate(cdir)
    if meta["status"] != "active":
        raise ValueError(f"Candidate {cdir.name} is incomplete; run candidate-recover")
    for name, kind in (("state.md", "file"), ("profile.md", "file"), ("runs", "dir"), ("jobs", "dir"), ("cv", "dir")):
        if not checked_path(cdir, name, kind).exists():
            raise ValueError(f"Candidate {cdir.name} is missing {name}")
    return meta




@contextmanager
def candidate_lock(root, candidate_id, *, recovering=False):
    root = safe_root(root)
    require_workspace_shallow(root)
    cdir = candidate_dir(root, candidate_id)
    require_active(cdir)
    validate_run_records(cdir)
    if recovering:
        if candidate_journal(cdir).exists():
            read_transaction(cdir)
    else:
        require_clean(cdir)
    checked_path(cdir, CONTROL, "dir").mkdir(mode=0o700, exist_ok=True)
    sync_directory(cdir)
    with file_lock(checked_path(cdir, CONTROL + "/lock", "file")):
        validate_run_records(cdir)
        require_active(cdir)
        yield cdir


# --------------------------------------------------------------------- jobs

JOB_KEYS = {"schema_version", "job_id", "candidate_id", "status", "title", "company", "created_at", "participants", "changes"}


def job_dir(cdir, job_id):
    if not isinstance(job_id, str) or not JOB_ID.fullmatch(job_id):
        raise ValueError("Invalid job identifier")
    return checked_path(cdir, "jobs/" + job_id, "dir")


def read_job(cdir, job_id):
    jdir = job_dir(cdir, job_id)
    record = checked_path(jdir, "job.json", "file")
    if not record.is_file():
        raise ValueError(f"Unknown job {job_id} for candidate {cdir.name} (jobs belong to exactly one candidate)")
    data = strict_json(record.read_text(encoding="utf-8"))
    people = data.get("participants") if isinstance(data, dict) else None
    if (not isinstance(data, dict) or set(data) != JOB_KEYS or data["schema_version"] != SCHEMA
            or type(data["schema_version"]) is not int or data["job_id"] != job_id or data["candidate_id"] != cdir.name
            or data["status"] not in ("creating", "active") or not isinstance(data["title"], str)
            or not (data["company"] is None or isinstance(data["company"], str))
            or not isinstance(people, dict) or set(people) != {"status", "people"}
            or people["status"] not in ("pending", "provided", "unknown") or not isinstance(people["people"], list)
            or not isinstance(data["changes"], list)):
        raise ValueError(f"Unsupported or foreign job record: {job_id} does not belong to candidate {cdir.name}")
    return data


def artifact_dir(jdir, kind):
    if kind not in ARTIFACT_KINDS:
        raise ValueError("Unknown artifact kind: " + str(kind))
    return checked_path(jdir, ARTIFACT_KINDS[kind], "dir")


def artifact_seqs(jdir, kind):
    folder = artifact_dir(jdir, kind)
    return sorted(int(p.stem) for p in folder.glob("[0-9][0-9][0-9].md")) if folder.is_dir() else []


def read_artifact(jdir, cdir, kind, seq):
    path = checked_path(jdir, f"{ARTIFACT_KINDS[kind]}/{seq:03d}.md", "file")
    meta, body = parse_header(path.read_text(encoding="utf-8"), ARTIFACT_HEADER, "job artifact")
    if (not isinstance(meta, dict) or meta.get("schema_version") != SCHEMA or meta.get("candidate_id") != cdir.name
            or meta.get("job_id") != jdir.name or meta.get("kind") != kind or meta.get("seq") != seq):
        raise ValueError(f"Job artifact {path.name} does not belong to this candidate/job")
    return meta, body


def add_artifact(cdir, jdir, kind, text, *, sources=(), retrieved_at=None, extra=None):
    if kind in ("research", "posting") and sources and not retrieved_at:
        raise ValueError("Sources require a retrieval date (YYYY-MM-DD)")
    if kind == "research" and not retrieved_at:
        raise ValueError("Research requires a retrieval date (YYYY-MM-DD)")
    if retrieved_at is not None and not DATE.fullmatch(retrieved_at):
        raise ValueError("Retrieval date must be YYYY-MM-DD")
    if not text.strip():
        raise ValueError("Artifact content must not be empty")
    if kind == "match":
        profile_status = read_candidate(cdir)["profile"]["status"]
        if profile_status != "confirmed":
            raise ValueError(f"A personal comparison needs a confirmed profile (current: {profile_status}). "
                             "Ask the user to confirm the profile facts first")
    folder = artifact_dir(jdir, kind)
    folder.mkdir(exist_ok=True)
    seq = (artifact_seqs(jdir, kind) or [0])[-1] + 1
    meta = dict(schema_version=SCHEMA, candidate_id=cdir.name, job_id=jdir.name, kind=kind, seq=seq,
                created_at=now(), retrieved_at=retrieved_at, sources=list(sources), **(extra or {}))
    write_atomic(folder / f"{seq:03d}.md", ARTIFACT_HEADER + json.dumps(meta, ensure_ascii=False, allow_nan=False) + " -->\n" + text,
                 create_only=True)
    return meta


def read_source_text(file_path, text_file):
    """Return (text, original_path|None, extraction_info|None) for a posting."""
    if file_path:
        path = extractor.check_source(file_path)
        info = extractor.extract(path)
        return info["markdown"], path, info
    if text_file:
        path = Path(text_file).expanduser()
        if path.is_symlink() or not path.is_file():
            raise ValueError("Posting text file is not a regular file")
        return path.read_text(encoding="utf-8"), None, None
    raise ValueError("Posting content (link text or upload) is required; nothing is invented")


def create_job(root, candidate_id, title, company=None, *, posting_file=None, posting_text_file=None,
               source_url=None, retrieved_at=None):
    title = clean_text(title, "title")
    company = clean_text(company, "company") if company else None
    if source_url is not None:
        source_url = clean_text(source_url, "source url", 2000)
    if source_url and not retrieved_at:
        raise ValueError("A source link requires its retrieval date (YYYY-MM-DD)")
    text, original, info = read_source_text(posting_file, posting_text_file)  # may fail before any write
    if not text.strip():
        raise ValueError("Posting content is empty; ask for the text or another upload")
    if retrieved_at is not None and not DATE.fullmatch(retrieved_at):
        raise ValueError("Retrieval date must be YYYY-MM-DD")
    with candidate_lock(root, candidate_id) as cdir:
        for _ in range(8):
            job_id = new_identifier("j", f"{company or ''} {title}", 40)
            jdir = checked_path(cdir, "jobs/" + job_id)
            try:
                jdir.mkdir()
                break
            except FileExistsError:
                continue
        else:
            raise RuntimeError("Could not allocate a unique job identifier")
        meta = {"schema_version": SCHEMA, "job_id": job_id, "candidate_id": cdir.name, "status": "creating", "title": title,
                "company": company, "created_at": now(), "participants": {"status": "pending", "people": []}, "changes": []}
        try:
            write_atomic(jdir / "job.json", dump(meta), create_only=True)
            for folder in ARTIFACT_KINDS.values():
                (jdir / folder).mkdir(exist_ok=True)
            extra = {"origin": "upload" if original else ("link" if source_url else "text")}
            if original:
                digest = extractor.sha256_file(original)
                stored = jdir / "postings" / ("001.original" + original.suffix.lower())
                shutil.copyfile(original, stored)
                core.touch(stored)
                if extractor.sha256_file(stored) != digest:
                    raise RuntimeError("Original posting copy did not verify")
                extra.update(original=stored.name, original_sha256=digest, original_name=original.name,
                             extractor=info["extractor"], extraction_status=info["status"], warnings=info["warnings"])
            add_artifact(cdir, jdir, "posting", text, sources=[source_url] if source_url else [],
                         retrieved_at=retrieved_at, extra=extra)
            meta["status"] = "active"
            write_atomic(jdir / "job.json", dump(meta))
            read_job(cdir, job_id)
        except (OSError, ValueError, RuntimeError) as exc:
            raise RuntimeError(f"Job creation incomplete ({job_id}); kept as an unusable draft, nothing was marked done: {exc}") from exc
    return meta


def parse_person(spec):
    name, _, role = spec.partition("::")
    return clean_text(name, "participant name"), (clean_text(role, "participant role") if role.strip() else None)


def update_job(root, candidate_id, job_id, *, company=None, title=None, participants_status=None, persons=(), verify=()):
    with candidate_lock(root, candidate_id) as cdir:
        meta = read_job(cdir, job_id)
        if meta["status"] != "active":
            raise ValueError("Job is incomplete")
        stamp = now()

        def change(field, old, new):
            meta["changes"].append({"at": stamp, "field": field, "from": old, "to": new})
        if company:
            company = clean_text(company, "company")
            change("company", meta["company"], company)
            meta["company"] = company
        if title:
            title = clean_text(title, "title")
            change("title", meta["title"], title)
            meta["title"] = title
        people = meta["participants"]["people"]
        for spec in persons:
            name, role = parse_person(spec)
            person = {"person_id": f"p-{len(people) + 1}", "name": name, "role": role, "identity": "unverified"}
            people.append(person)
            change("participant_added", None, person["person_id"])
        for person_id in verify:
            match = [p for p in people if p["person_id"] == person_id]
            if not match:
                raise ValueError("Unknown participant: " + person_id)
            change("participant_verified", match[0]["identity"], "verified")
            match[0]["identity"] = "verified"
        if participants_status:
            if participants_status not in ("pending", "provided", "unknown"):
                raise ValueError("Invalid participants status")
            if participants_status == "provided" and not people:
                raise ValueError("Participants cannot be 'provided' without any person")
            if participants_status == "unknown" and people:
                raise ValueError("Participants are listed; status cannot be 'unknown'")
            change("participants_status", meta["participants"]["status"], participants_status)
            meta["participants"]["status"] = participants_status
        elif persons and meta["participants"]["status"] != "provided":
            change("participants_status", meta["participants"]["status"], "provided")
            meta["participants"]["status"] = "provided"
        write_atomic(job_dir(cdir, job_id) / "job.json", dump(meta))
        return meta


def job_open_points(meta):
    points = []
    if not meta["company"]:
        points.append("company missing")
    if meta["participants"]["status"] == "pending":
        points.append("interview participants not yet asked")
    if any(p["identity"] != "verified" for p in meta["participants"]["people"]):
        points.append("participant identity unverified")
    return points


def list_jobs(root, candidate_id):
    cdir = candidate_dir(safe_root(root), candidate_id)
    require_active(cdir)
    jobs = []
    for entry in sorted(checked_path(cdir, "jobs", "dir").iterdir()):
        meta = read_job(cdir, entry.name)
        jobs.append({"job_id": meta["job_id"], "title": meta["title"], "company": meta["company"], "status": meta["status"],
                     "open_points": job_open_points(meta),
                     "artifacts": {k: len(artifact_seqs(job_dir(cdir, entry.name), k)) for k in ARTIFACT_KINDS}})
    return jobs


def show_job(root, candidate_id, job_id):
    cdir = candidate_dir(safe_root(root), candidate_id)
    require_active(cdir)
    meta = read_job(cdir, job_id)
    jdir = job_dir(cdir, job_id)
    latest = {}
    for kind in ARTIFACT_KINDS:
        seqs = artifact_seqs(jdir, kind)
        if seqs:
            info, body = read_artifact(jdir, cdir, kind, seqs[-1])
            latest[kind] = {"seq": seqs[-1], "history": seqs, "meta": info, "content": body}
    return {"job": meta, "open_points": job_open_points(meta), "latest": latest}


# ------------------------------------------------------------ CV and profile

def cv_source_dirs(cdir):
    folder = checked_path(cdir, "cv", "dir")
    return sorted(p.name for p in folder.iterdir() if re.fullmatch(r"cv-\d{3}", p.name))


def next_cv_id(cdir):
    names = cv_source_dirs(cdir)
    return f"cv-{(int(names[-1][3:]) if names else 0) + 1:03d}"


def import_cv(root, candidate_id, file_path, *, transcription_file=None, which=shutil.which, run=None):
    """Keep the original byte-exact, produce Markdown, record provenance; incomplete imports stay 'partial'."""
    source = extractor.check_source(file_path)
    digest = extractor.sha256_file(source)
    kwargs = {"which": which}
    if run is not None:
        kwargs["run"] = run
    transcription = None
    if transcription_file:
        transcription = Path(transcription_file).expanduser().read_text(encoding="utf-8")
        if not transcription.strip():
            raise ValueError("Transcription is empty")
    try:
        info = extractor.extract(source, **kwargs)
    except extractor.ExtractionUnavailable:
        if transcription is None:
            raise
        info = {"markdown": transcription, "extractor": "agent-transcription", "status": "partial",
                "warnings": ["No extraction tool available; text was transcribed by the model and is unverified"]}
    with candidate_lock(root, candidate_id) as cdir:
        meta = read_candidate(cdir)
        for existing in meta["cv_sources"]:
            known = json.loads(checked_path(cdir, f"cv/{existing}/source.json", "file").read_text(encoding="utf-8"))
            if known.get("original_sha256") == digest:
                return {"cv_source": existing, "already_imported": True, "extraction_status": known["extraction_status"],
                        "warnings": known["warnings"]}
        source_id = next_cv_id(cdir)
        stage = checked_path(cdir, CONTROL + "/stage-" + source_id)
        if stage.exists():
            raise RuntimeError(f"Interrupted import staging found at {stage}; inspect it, it is never deleted automatically")
        stage.mkdir()
        original_name = "original" + source.suffix.lower()
        shutil.copyfile(source, stage / original_name)
        if extractor.sha256_file(stage / original_name) != digest:
            raise RuntimeError("Original copy did not verify byte-exactly; nothing was imported")
        record = {"schema_version": SCHEMA, "kind": "imported", "source_id": source_id, "original": original_name,
                  "original_name": source.name, "original_sha256": digest, "size": source.stat().st_size,
                  "extractor": info["extractor"], "extraction_status": info["status"], "warnings": info["warnings"],
                  "markdown_sha256": hashlib.sha256(info["markdown"].encode("utf-8")).hexdigest(), "imported_at": now()}
        (stage / "extracted.md").write_text(info["markdown"], encoding="utf-8")
        (stage / "source.json").write_text(dump(record), encoding="utf-8")
        target = checked_path(cdir, "cv/" + source_id)
        os.rename(stage, target)
        core.touch_tree(target)
        sync_directory(target.parent)
        meta["cv_sources"].append(source_id)
        write_atomic(cdir / "candidate.json", dump(meta))
    return {"cv_source": source_id, "already_imported": False, "extraction_status": record["extraction_status"],
            "warnings": record["warnings"], "original_sha256": digest, "extractor": record["extractor"]}


def save_cv_draft(root, candidate_id, draft_file):
    text = Path(draft_file).expanduser().read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError("Draft is empty")
    with candidate_lock(root, candidate_id) as cdir:
        meta = read_candidate(cdir)
        source_id = next_cv_id(cdir)
        target = checked_path(cdir, "cv/" + source_id)
        target.mkdir()
        write_atomic(target / "extracted.md", text, create_only=True)
        record = {"schema_version": SCHEMA, "kind": "draft", "source_id": source_id, "original": None,
                  "extraction_status": "draft_unconfirmed", "warnings": ["Model-drafted CV; facts need user confirmation"],
                  "markdown_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "imported_at": now()}
        write_atomic(target / "source.json", dump(record), create_only=True)
        meta["cv_sources"].append(source_id)
        write_atomic(cdir / "candidate.json", dump(meta))
    return {"cv_source": source_id, "status": "draft_unconfirmed"}


def save_profile(root, candidate_id, profile_file, *, status, origin, cv_source=None, user_confirmed=False, acknowledge_gaps=False):
    if status not in ("draft", "confirmed") or origin not in ("cv", "interview"):
        raise ValueError("Invalid profile status or origin")
    text = Path(profile_file).expanduser().read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError("Profile must not be empty")
    if status == "confirmed" and not user_confirmed:
        raise ValueError("A profile counts as verified only after the user confirmed its factual content (--user-confirmed)")
    with candidate_lock(root, candidate_id) as cdir:
        meta = read_candidate(cdir)
        if cv_source is not None:
            if cv_source not in meta["cv_sources"]:
                raise ValueError("CV source does not belong to this candidate")
            record = strict_json(checked_path(cdir, f"cv/{cv_source}/source.json", "file").read_text(encoding="utf-8"))
            if status == "confirmed" and record["extraction_status"] != "complete" and not acknowledge_gaps:
                raise ValueError("The CV source is incomplete or unconfirmed (" + record["extraction_status"]
                                 + "); confirm only after the user acknowledged the gaps (--acknowledge-gaps)")
        elif origin == "cv":
            raise ValueError("Profile origin 'cv' requires a CV source")
        profile = checked_path(cdir, "profile.md", "file")
        history = checked_path(cdir, "profile-history", "dir")
        history.mkdir(exist_ok=True)
        seq = len(list(history.glob("[0-9][0-9][0-9].md"))) + 1
        write_atomic(history / f"{seq:03d}.md", profile.read_text(encoding="utf-8"), create_only=True)
        write_atomic(profile, text)
        meta["profile"] = {"status": status, "origin": origin, "cv_source": cv_source, "updated_at": now()}
        write_atomic(cdir / "candidate.json", dump(meta))
    return meta["profile"]


# --------------------------------------------------------------------- runs

def state_digest(cdir):
    return hashlib.sha256(checked_path(cdir, "state.md", "file").read_bytes()).hexdigest()


def run_path(cdir, run_id):
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id) or ".." in run_id:
        raise ValueError("Invalid run identifier")
    return checked_path(cdir, "runs/" + run_id + ".md", "file")


def validate_lifecycle(status, answered_count, planned_count):
    if status not in STATUSES or type(answered_count) is not int or answered_count < 0:
        raise ValueError("Invalid status or answered count")
    if planned_count is not None and (type(planned_count) is not int or planned_count < answered_count):
        raise ValueError("Invalid planned count")
    if status == "completed" and planned_count is not None and answered_count != planned_count:
        raise ValueError("Incomplete interview must be paused or stopped_early")


RUN_KEYS = {"schema_version", "run_id", "candidate_id", "job_id", "status", "answered_count", "planned_count", "resume_from"}


def parse_run(text, run_id, candidate_id):
    metadata, body = parse_header(text, HEADER, "run")
    if (not isinstance(metadata, dict) or set(metadata) != RUN_KEYS or type(metadata.get("schema_version")) is not int
            or metadata["schema_version"] != SCHEMA or metadata["run_id"] != run_id):
        raise ValueError("Invalid run lifecycle metadata")
    if metadata["candidate_id"] != candidate_id:
        raise ValueError("Run belongs to another candidate")
    job = metadata["job_id"]
    if job is not None and (not isinstance(job, str) or not JOB_ID.fullmatch(job)):
        raise ValueError("Invalid run job identifier")
    validate_lifecycle(metadata["status"], metadata["answered_count"], metadata["planned_count"])
    source = metadata["resume_from"]
    if source is not None and (not isinstance(source, str) or not RUN_ID.fullmatch(source) or ".." in source):
        raise ValueError("Invalid continuation identifier")
    return metadata, body


def read_run(cdir, run_id):
    path = run_path(cdir, run_id)
    if not path.is_file():
        raise ValueError(f"Unknown run {run_id} for candidate {cdir.name}")
    return parse_run(path.read_text(encoding="utf-8"), run_id, cdir.name)


def validate_run_records(cdir):
    folder = checked_path(cdir, "runs", "dir")
    if not folder.exists():
        return {}
    records = {}
    for path in sorted(folder.iterdir()):
        try:
            checked_path(cdir, "runs/" + path.name, "file")
            if path.suffix != ".md":
                raise ValueError("Only current .md run records are supported")
            metadata = read_run(cdir, path.stem)[0]
            if metadata["job_id"] is not None:
                read_job(cdir, metadata["job_id"])  # must exist and belong to this candidate
            records[path.stem] = metadata
        except (OSError, ValueError) as exc:
            raise ValueError(f"Unsupported run {path.name}: {exc}; manual reconciliation required; files unchanged") from exc
    validate_run_links(records)
    return records


def validate_run_links(records):
    successors = set()
    for identifier, metadata in records.items():
        source = metadata["resume_from"]
        if source is None:
            continue
        previous = records.get(source)
        if (source == identifier or previous is None or previous["status"] != "paused" or source in successors
                or metadata["answered_count"] < previous["answered_count"] or previous["job_id"] != metadata["job_id"]
                or (previous["planned_count"] is not None and metadata["planned_count"] != previous["planned_count"])):
            raise ValueError("Unsupported run continuation: " + identifier + "; manual reconciliation required; files unchanged")
        successors.add(source)
        seen = {identifier}
        while source is not None and source in records:
            if source in seen:
                raise ValueError("Unsupported run continuation cycle; manual reconciliation required; files unchanged")
            seen.add(source)
            source = records[source]["resume_from"]


_ANY = object()


def require_resumable(cdir, run_id, job_id=_ANY):
    metadata, body = read_run(cdir, run_id)
    if metadata["status"] != "paused":
        raise ValueError("Only a paused checkpoint can be resumed")
    if job_id is not _ANY and metadata["job_id"] != job_id:
        raise ValueError("Checkpoint belongs to another job (or to no job); a continuation keeps the checkpoint's job")
    for path in checked_path(cdir, "runs", "dir").glob("*.md"):
        if read_run(cdir, path.stem)[0]["resume_from"] == run_id:
            raise ValueError("Checkpoint already continued; use its latest paused successor")
    return metadata, body


def snapshot(root, candidate_id):
    with candidate_lock(root, candidate_id) as cdir:
        state = checked_path(cdir, "state.md", "file").read_bytes()
        meta = read_candidate(cdir)
        jobs = [read_job(cdir, p.name) for p in sorted(checked_path(cdir, "jobs", "dir").iterdir())]
        return {"candidate": meta, "profile_reliable": meta["profile"]["status"] == "confirmed",
                "state": state.decode("utf-8"), "state_sha256": hashlib.sha256(state).hexdigest(),
                "jobs": [{"job_id": j["job_id"], "title": j["title"], "company": j["company"]} for j in jobs],
                "runs": sorted(p.stem for p in checked_path(cdir, "runs", "dir").glob("*.md"))}


def resume(root, candidate_id, run_id):
    with candidate_lock(root, candidate_id) as cdir:
        metadata, body = require_resumable(cdir, run_id)
        state = checked_path(cdir, "state.md", "file").read_bytes()
        return {"run": metadata, "transcript": body, "state": state.decode("utf-8"),
                "state_sha256": hashlib.sha256(state).hexdigest()}


def read_transaction(cdir):
    pending = candidate_journal(cdir)
    transaction = strict_json(pending.read_text(encoding="utf-8"))
    if (not isinstance(transaction, dict)
            or set(transaction) != {"schema_version", "run_id", "run_text", "state_text", "expected_state_sha256"}
            or type(transaction.get("schema_version")) is not int or transaction["schema_version"] != SCHEMA):
        raise ValueError("Unsupported transaction schema; manual reconciliation required")
    for key in ("run_id", "run_text", "state_text", "expected_state_sha256"):
        if not isinstance(transaction.get(key), str):
            raise ValueError("Invalid transaction; manual reconciliation required")
    if not re.fullmatch(r"[0-9a-f]{64}", transaction["expected_state_sha256"]):
        raise ValueError("Invalid transaction state hash; manual reconciliation required")
    metadata, _ = parse_run(transaction["run_text"], transaction["run_id"], cdir.name)
    if metadata["job_id"] is not None:
        read_job(cdir, metadata["job_id"])
    records = validate_run_records(cdir) or {}
    records[transaction["run_id"]] = metadata
    validate_run_links(records)
    run = run_path(cdir, transaction["run_id"])
    new_digest = hashlib.sha256(transaction["state_text"].encode("utf-8")).hexdigest()
    if state_digest(cdir) not in (transaction["expected_state_sha256"], new_digest):
        raise ValueError("State changed outside pending transaction; manual reconciliation required")
    if run.exists() and run.read_bytes() != transaction["run_text"].encode("utf-8"):
        raise ValueError("Run conflicts with pending transaction; manual reconciliation required")
    return transaction


def apply_pending(cdir):
    transaction = read_transaction(cdir)
    pending = candidate_journal(cdir)
    run = run_path(cdir, transaction["run_id"])
    state = checked_path(cdir, "state.md", "file")
    new_digest = hashlib.sha256(transaction["state_text"].encode("utf-8")).hexdigest()
    if not run.exists():
        write_atomic(run, transaction["run_text"], create_only=True, staging=checked_path(cdir, CONTROL, "dir"))
    if state_digest(cdir) != new_digest:
        write_atomic(state, transaction["state_text"])
    if run.read_bytes() != transaction["run_text"].encode("utf-8") or state_digest(cdir) != new_digest:
        raise RuntimeError("Transaction verification failed; recovery record retained")
    pending.unlink()
    sync_directory(pending.parent)
    return run


def recover(root, candidate_id):
    with candidate_lock(root, candidate_id, recovering=True) as cdir:
        if not candidate_journal(cdir).exists():
            return None
        return apply_pending(cdir)


def finish(root, candidate_id, run_id, run_text, state_text, *, expected_state_sha256, status="completed",
           answered_count=0, planned_count=None, resume_from=None, job_id=None):
    validate_lifecycle(status, answered_count, planned_count)
    if not run_text.strip() or not state_text.strip():
        raise ValueError("Run and state must not be empty")
    with candidate_lock(root, candidate_id) as cdir:
        if job_id is not None and read_job(cdir, job_id)["status"] != "active":
            raise ValueError("Job is incomplete")
        run = run_path(cdir, run_id)
        if run.exists():
            raise FileExistsError(f"Run already exists: {run}")
        if state_digest(cdir) != expected_state_sha256:
            raise ValueError("Stale state snapshot; read status/resume and reconcile before retrying")
        if resume_from is not None:
            previous, _ = require_resumable(cdir, resume_from, job_id)
            if previous["planned_count"] is not None:
                if planned_count is None:
                    planned_count = previous["planned_count"]
                elif planned_count != previous["planned_count"]:
                    raise ValueError("Continuation must preserve the checkpoint's planned count")
            validate_lifecycle(status, answered_count, planned_count)
            if answered_count < previous["answered_count"]:
                raise ValueError("Answered count cannot decrease on continuation")
        metadata = dict(schema_version=SCHEMA, run_id=run_id, candidate_id=cdir.name, job_id=job_id, status=status,
                        answered_count=answered_count, planned_count=planned_count, resume_from=resume_from)
        transaction = dict(schema_version=SCHEMA, run_id=run_id,
                           run_text=HEADER + json.dumps(metadata, allow_nan=False, ensure_ascii=False) + " -->\n" + run_text,
                           state_text=state_text, expected_state_sha256=expected_state_sha256)
        try:
            write_atomic(candidate_journal(cdir), json.dumps(transaction, allow_nan=False, ensure_ascii=False) + "\n", create_only=True)
            return apply_pending(cdir)
        except (OSError, ValueError, RuntimeError) as exc:
            try:
                if candidate_journal(cdir).exists():
                    guidance = "Pending transaction. Run recover; if recovery conflicts, reconcile manually"
                elif (run.exists() and run.read_bytes() == transaction["run_text"].encode("utf-8")
                      and state_digest(cdir) == hashlib.sha256(state_text.encode("utf-8")).hexdigest()):
                    guidance = ("Run and state match the intended content, but final durability was not confirmed. "
                                "No pending transaction; recover cannot replay it. Inspect the existing run/state; "
                                "do not create another run or overwrite them")
                elif not run.exists() and state_digest(cdir) == expected_state_sha256:
                    guidance = ("No transaction recorded; recover has nothing to replay. Resolve the write error, "
                                "then retry the same run ID with the original state hash; reconcile if stale")
                else:
                    guidance = "No pending transaction; inspect run/state and reconcile manually before retrying"
            except (OSError, ValueError):
                guidance = "Save state could not be inspected; inspect journal/run/state and reconcile manually"
            raise RuntimeError("Save incomplete; do not claim success. " + guidance) from exc


# ---------------------------------------------------------------------- git

def git_workspace(project, config_dir):
    root, config = project_workspace(project, config_dir)
    if config["storage"] != "git":
        raise ValueError("This project does not use Git storage")
    return root, config


def pending_journals(root):
    return [c.name for c in checked_path(root, "candidates", "dir").iterdir() if not c.name.startswith(".") and candidate_journal(c).exists()]


def git_targets(root, config, attest=None):
    """Re-verify, immediately before touching the remote, that the real fetch/push target is the authorized private repo."""
    evidence = config["git"]
    gitstore.verify_target(evidence["remote"], attest=attest)  # current privacy + write evidence for exactly this repository
    return gitstore.resolve_targets(root, evidence["remote"], pinned=evidence.get("targets"))


def git_pull(project, config_dir):
    """Fast-forward pull under the same Git-workspace lock as saving and publishing; every state is checked after acquiring it."""
    root, config = git_workspace(project, config_dir)
    with git_lock(root):
        if pending_journals(root):
            raise gitstore.GitStorageError("Pending transactions exist (" + ", ".join(pending_journals(root)) + "); run recover first")
        targets = gitstore.resolve_targets(root, config["git"]["remote"], pinned=config["git"].get("targets"))
        return gitstore.pull(root, targets)


def git_status(project, config_dir):
    """Status fetches (updates tracking refs), so it also runs under the Git-workspace lock."""
    root, config = git_workspace(project, config_dir)
    with git_lock(root):
        targets = gitstore.resolve_targets(root, config["git"]["remote"], pinned=config["git"].get("targets"))
        return gitstore.status(root, targets)


def git_publish(project, message, config_dir, attest=None):
    root, config = git_workspace(project, config_dir)
    with git_lock(root):
        if pending_journals(root):
            raise gitstore.GitStorageError("Pending transactions exist (" + ", ".join(pending_journals(root)) + "); run recover first")
        targets = git_targets(root, config, attest)
        return gitstore.publish(root, targets)


# ---------------------------------------------------------------------- CLI

def build_parser():
    p = argparse.ArgumentParser(description="Interview Coach runtime (format 3)")
    p.add_argument("--config-dir", type=Path, default=DEFAULT_CONFIG_DIR, help="Per-project pointer directory (machine-local)")
    sub = p.add_subparsers(dest="cmd", required=True)

    def command(name, *flags, project=True, **kw):
        c = sub.add_parser(name, **kw)
        if project:
            c.add_argument("--project", required=True, help="Project folder; selects the storage target explicitly")
        for flag in flags:
            c.add_argument(*flag[0], **flag[1])
        return c
    arg = lambda *names, **kw: (names, kw)  # noqa: E731
    cand = arg("--candidate", required=True)
    job = arg("--job", required=True)
    command("project-init", arg("--storage", required=True, choices=["local", "git", "none"]), arg("--path"), arg("--remote"),
            arg("--switch", action="store_true"),
            arg("--attest-private", action="store_true"),
            arg("--attest-write", action="store_true"), arg("--attest-source"), arg("--attest-repository"),
            arg("--attest-user-confirmed", action="store_true"),
            help="Configure storage for this project (local or git). 'none' is refused: nothing is stored")
    command("project-show")
    command("validate", arg("--path"), project=False)
    sub.choices["validate"].add_argument("--project")
    command("set-language", arg("--interface", required=True, dest="interface_language"), arg("--interview", dest="interview_language"))
    command("candidate-create", arg("--name", required=True))
    command("candidate-list")
    command("candidate-resolve", arg("--id"), arg("--name"))
    command("candidate-recover", cand)
    command("candidate-status", cand)
    command("cv-import", cand, arg("--file", required=True), arg("--transcription-file"))
    command("cv-draft-save", cand, arg("--file", required=True))
    command("profile-save", cand, arg("--file", required=True), arg("--status", required=True, choices=["draft", "confirmed"]),
            arg("--origin", required=True, choices=["cv", "interview"]), arg("--cv-source"),
            arg("--user-confirmed", action="store_true"), arg("--acknowledge-gaps", action="store_true"))
    command("job-create", cand, arg("--title", required=True), arg("--company"), arg("--posting-file"),
            arg("--posting-text-file"), arg("--source-url"), arg("--retrieved-at"))
    command("job-list", cand)
    command("job-show", cand, job)
    command("job-add", cand, job, arg("--kind", required=True, choices=sorted(ARTIFACT_KINDS)), arg("--file", required=True),
            arg("--source", action="append", default=[]), arg("--retrieved-at"))
    command("job-update", cand, job, arg("--company"), arg("--title"), arg("--participants-status"),
            arg("--person", action="append", default=[]), arg("--verify-person", action="append", default=[]))
    command("status", cand)
    command("resume", cand, arg("--run-id", required=True))
    command("recover", cand)
    command("finish", cand, arg("--run-id", required=True), arg("--run-file", type=Path, required=True),
            arg("--state-file", type=Path, required=True), arg("--expected-state-sha256", required=True),
            arg("--status", choices=STATUSES, required=True), arg("--answered-count", type=int, required=True),
            arg("--planned-count", type=int), arg("--resume-from"), arg("--job-id"))
    command("git-status")
    command("git-pull")
    command("git-publish", arg("--message"), arg("--attest-private", action="store_true"),
            arg("--attest-write", action="store_true"), arg("--attest-source"), arg("--attest-repository"),
            arg("--attest-user-confirmed", action="store_true"))
    return p


def emit(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


MUTATING = {"set-language", "candidate-create", "candidate-recover", "cv-import", "cv-draft-save", "profile-save",
            "job-create", "job-add", "job-update", "recover", "finish"}


def parse_attest(args):
    if not (args.attest_private or args.attest_write or args.attest_source or args.attest_repository):
        return None
    if not (args.attest_private and args.attest_write and args.attest_source and args.attest_repository
            and args.attest_user_confirmed):
        raise ValueError("Connector attestation needs --attest-private, --attest-write, --attest-source NAME, "
                         "--attest-repository OWNER/REPO and --attest-user-confirmed (the user saw the connector's answer)")
    return {"private": True, "write": True, "source": clean_text(args.attest_source, "attestation source", 80),
            "repository": args.attest_repository, "user_confirmed": True}


def main(argv=None):
    args = build_parser().parse_args(argv)
    cfg = args.config_dir
    try:
        if args.cmd == "project-init":
            emit(setup_project(args.project, args.storage, args.path, config_dir=cfg, switch=args.switch, remote=args.remote,
                               attest=parse_attest(args)))
            return 0
        if args.cmd == "validate" and args.path:
            problems = workspace_problems(args.path)
            print("VALID" if not problems else "\n".join(problems))
            return int(bool(problems))
        if args.cmd == "validate" and not args.project:
            raise ValueError("--project or --path is required")
        root, config = project_workspace(args.project, cfg)
        git_mode = config["storage"] == "git"
        guard = git_save_guard(root, f"interview-coach: {args.cmd}") if git_mode and args.cmd in MUTATING else nullcontext()
        with guard:
            return run_command(args, root, config, cfg)
    except LookupError as exc:
        print(exc.args[0], file=sys.stderr)
        return 2
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def run_command(args, root, config, cfg):
    if args.cmd == "project-show":
        emit(config)
    elif args.cmd == "validate":
        problems = workspace_problems(root) + [f"{n}: pending transaction: run recover" for n in pending_journals(root)]
        print("VALID" if not problems else "\n".join(problems))
        return int(bool(problems))
    elif args.cmd == "set-language":
        emit(set_language(root, args.interface_language, args.interview_language))
    elif args.cmd == "candidate-create":
        emit(create_candidate(root, args.name))
    elif args.cmd == "candidate-list":
        emit(list_candidates(root))
    elif args.cmd == "candidate-resolve":
        emit(resolve_candidate(root, args.id, args.name))
    elif args.cmd == "candidate-recover":
        emit(recover_candidate(root, args.candidate))
    elif args.cmd == "candidate-status" or args.cmd == "status":
        emit(snapshot(root, args.candidate))
    elif args.cmd == "cv-import":
        emit(import_cv(root, args.candidate, args.file, transcription_file=args.transcription_file))
    elif args.cmd == "cv-draft-save":
        emit(save_cv_draft(root, args.candidate, args.file))
    elif args.cmd == "profile-save":
        emit(save_profile(root, args.candidate, args.file, status=args.status, origin=args.origin, cv_source=args.cv_source,
                          user_confirmed=args.user_confirmed, acknowledge_gaps=args.acknowledge_gaps))
    elif args.cmd == "job-create":
        emit(create_job(root, args.candidate, args.title, args.company, posting_file=args.posting_file,
                        posting_text_file=args.posting_text_file, source_url=args.source_url, retrieved_at=args.retrieved_at))
    elif args.cmd == "job-list":
        emit(list_jobs(root, args.candidate))
    elif args.cmd == "job-show":
        emit(show_job(root, args.candidate, args.job))
    elif args.cmd == "job-add":
        with candidate_lock(root, args.candidate) as cdir:
            if read_job(cdir, args.job)["status"] != "active":
                raise ValueError("Job is incomplete")
            emit(add_artifact(cdir, job_dir(cdir, args.job), args.kind,
                              Path(args.file).expanduser().read_text(encoding="utf-8"),
                              sources=args.source, retrieved_at=args.retrieved_at))
    elif args.cmd == "job-update":
        emit(update_job(root, args.candidate, args.job, company=args.company, title=args.title,
                        participants_status=args.participants_status, persons=args.person, verify=args.verify_person))
    elif args.cmd == "resume":
        emit(resume(root, args.candidate, args.run_id))
    elif args.cmd == "recover":
        run = recover(root, args.candidate)
        print(f"Recovered and verified: {run}" if run else "No pending transaction")
    elif args.cmd == "finish":
        run = finish(root, args.candidate, args.run_id, args.run_file.read_text(encoding="utf-8"),
                     args.state_file.read_text(encoding="utf-8"), expected_state_sha256=args.expected_state_sha256,
                     status=args.status, answered_count=args.answered_count, planned_count=args.planned_count,
                     resume_from=args.resume_from, job_id=args.job_id)
        print(f"Saved and verified run (local): {run}")
        if config["storage"] == "git":
            print("Git storage: committed locally only, NOT saved remotely. Run git-publish and report remote saved only if it succeeds.")
    elif args.cmd == "git-status":
        emit(git_status(args.project, cfg))
    elif args.cmd == "git-pull":
        emit(git_pull(args.project, cfg))
    elif args.cmd == "git-publish":
        emit(git_publish(args.project, args.message or "interview-coach: publish", cfg, parse_attest(args)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
