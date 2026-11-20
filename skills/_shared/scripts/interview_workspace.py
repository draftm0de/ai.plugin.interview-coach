#!/usr/bin/env python3
"""Interview Coach runtime (workspace format 3): projects, candidates, CVs, jobs, runs, local storage.

Only the current format is supported. Unsupported layouts are rejected before any
write and are never migrated, deleted or overwritten.
"""
import argparse
from contextlib import contextmanager
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unicodedata

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import coach_extract as extractor  # noqa: E402
from coach_core import (CANDIDATE_ID, CONTROL, LEGACY_CONTROL, JOB_ID, RUN_ID, checked_path, clean_text, file_lock,  # noqa: E402
                        new_identifier, safe_root, strict_json, sync_directory, write_atomic)

APP = "interview-coach"
FORMAT = "interview-coach-workspace"
SCHEMA = 3   # 3: internal control folder `.journal` (format 2 used `.zyris`); no format-2 data is read, migrated or aliased
DEFAULT_CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "zyris" / APP / "projects"
LANGUAGE = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RUN_SCHEMA = 4   # 4: runs carry the structured follow-up dialogue (main questions, follow-ups, retries); run format 3 is refused, never migrated
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
        validate_preferences(root)
        folder = checked_path(root, "candidates", "dir")
        if not folder.is_dir():
            raise ValueError("missing candidates/")
        for entry in sorted(e for e in folder.iterdir() if not e.name.startswith('.')):
            problems += [f"{entry.name}: {p}" for p in candidate_problems(root, entry.name)]
    except (OSError, ValueError) as exc:
        problems.append(str(exc))
    return problems


def validate_preferences(root):
    prefs = checked_path(root, "preferences.json", "file")
    if prefs.is_file():
        value = strict_json(prefs.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or value.get("schema_version") != SCHEMA or type(value.get("schema_version")) is not int:
            raise ValueError("Unsupported preferences schema")
        if "interview_language" in value:
            raise ValueError("Unsupported project interview_language; language belongs to candidate/job. No migration performed; data unchanged")
        for field in ("interface_language",):
            if field in value and (not isinstance(value[field], str) or not LANGUAGE.fullmatch(value[field])):
                raise ValueError("Invalid preferences language tag: " + field)


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


def set_language(root, interface_language):
    root = safe_root(root)
    if not isinstance(interface_language, str) or not LANGUAGE.fullmatch(interface_language):
        raise ValueError("Invalid language tag")
    require_workspace(root)
    with file_lock(checked_path(root, CONTROL + "/lock", "file")):
        target = checked_path(root, "preferences.json", "file")
        data = strict_json(target.read_text(encoding="utf-8"))
        data["interface_language"] = interface_language
        write_atomic(target, dump(data))
        return data


def validate_interview_language(language):
    if language is not None and (not isinstance(language, str) or not LANGUAGE.fullmatch(language)):
        raise ValueError("Invalid interview language tag")


def effective_interview_language(candidate, job=None):
    language = job["interview_language"] if job and job["interview_language"] is not None else candidate["interview_language"]
    return {"interview_language": language,
            "language_source": "job" if job and job["interview_language"] is not None else ("candidate" if language else "unconfirmed")}


def set_interview_language(root, candidate_id, language=None, *, job_id=None, inherit=False):
    validate_interview_language(language)
    if inherit:
        if job_id is None or language is not None:
            raise ValueError("Inherit requires a job and no language tag")
    elif language is None:
        raise ValueError("Confirm an interview language first")
    # Validate all existing records before creating any lock or writing data.
    require_workspace(safe_root(root))
    with candidate_lock(root, candidate_id) as cdir:
        candidate = read_candidate(cdir)
        meta = read_job(cdir, job_id) if job_id else candidate
        if meta["status"] != "active":
            raise ValueError("Cannot set language on an incomplete record")
        before = meta["interview_language"]
        meta["interview_language"] = language
        if job_id and before != language:
            meta["changes"].append({"at": now(), "field": "interview_language", "from": before, "to": language})
        target = job_dir(cdir, job_id) / "job.json" if job_id else cdir / "candidate.json"
        write_atomic(target, dump(meta))
        saved = read_job(cdir, job_id) if job_id else read_candidate(cdir)
        return {"candidate_id": candidate_id, "job_id": job_id,
                **effective_interview_language(candidate if job_id else saved, saved if job_id else None)}


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
    if isinstance(data, dict) and (data.get("storage") == "git" or "git" in data):
        raise ValueError("Git storage is no longer supported. Existing configuration and data are unchanged; no automatic conversion to local storage")
    if (not isinstance(data, dict) or data.get("schema_version") != SCHEMA or type(data.get("schema_version")) is not int
            or data.get("project") != str(project) or data.get("storage") != "local"
            or not isinstance(data.get("workspace"), str)):
        raise ValueError("Unsupported project configuration; no fallback or migration performed")
    return data


def check_switch(existing, storage, workspace, switch):
    """Refuse a change of target, storage type or repository unless explicitly confirmed. Read-only."""
    if existing is None or switch:
        return
    same = (existing["workspace"] == str(workspace) and existing["storage"] == storage)
    if not same:
        raise ValueError("This project already uses another storage target or type. Confirm switching explicitly (--switch); "
                         "nothing was changed")


def existing_config(project, config_dir):
    path = project_config_path(project, config_dir)
    if path.exists() or path.is_symlink():
        return read_project_config(project, config_dir)  # invalid configurations are rejected here, before any mutation
    return None


def write_pointer(project, workspace, storage, config_dir, switch):
    """Write the pointer; the caller holds the per-project lock."""
    check_switch(existing_config(project, config_dir), storage, workspace, switch)
    data = {"schema_version": SCHEMA, "project": str(project), "storage": storage, "workspace": str(workspace)}
    write_atomic(project_config_path(project, config_dir), dump(data))
    return data


def project_workspace(project, config_dir=DEFAULT_CONFIG_DIR):
    config = read_project_config(project, config_dir)
    root = safe_root(config["workspace"])
    if not root.is_dir():
        raise FileNotFoundError(f"Configured workspace not found: {root}")
    require_workspace(root)
    return root, config


def setup_project(project, storage, path, *, config_dir=DEFAULT_CONFIG_DIR, switch=False):
    """Local setup only. No-storage mode never invokes the runtime."""
    if storage != "local":
        raise ValueError("Unsupported storage: only local can be configured. Git storage is removed; Nicht speichern creates no workspace or pointer")
    project = safe_root(project)
    if not project.is_dir():
        raise ValueError(f"Project folder does not exist: {project}")
    if not path:
        raise ValueError("An explicit storage path is required (the project folder is only a suggestion)")
    path = safe_root(path)
    config_dir = Path(config_dir).expanduser()
    if config_dir.resolve().is_relative_to(path):
        raise ValueError("Configuration must be outside the workspace")
    check_switch(existing_config(project, config_dir), storage, path, switch)
    if config_dir.exists() and not config_dir.is_dir():
        raise ValueError("Expected directory: " + str(config_dir))
    if path.exists():
        for ancestor in (path, *path.parents):
            if ancestor.exists() and not ancestor.is_dir():
                raise ValueError("Expected directory: " + str(ancestor))
        if [e for e in path.iterdir() if e.name not in (".git", CONTROL)]:
            require_workspace(path)
    reused = (path / "workspace.json").is_file()
    config_dir.mkdir(parents=True, exist_ok=True)
    pointer = project_config_path(project, config_dir)
    with file_lock(pointer.with_name(pointer.name + ".lock")):
        check_switch(existing_config(project, config_dir), storage, path, switch)
        root = init_workspace(path)
        config = write_pointer(project, root, storage, config_dir, switch)
    result = dict(project=str(project), storage=storage, workspace=str(root), reused=reused, config=config)
    if str(root).startswith(TEMP_PREFIXES):
        result["warning"] = "Directory is in a temporary location and may not be durable"
    return result


# --------------------------------------------------------------- candidates

CANDIDATE_KEYS = {"schema_version", "candidate_id", "display_name", "status", "created_at", "profile", "cv_sources", "interview_language"}
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
        raise ValueError("Unsupported or inconsistent candidate record (current interview_language field required); data unchanged")
    validate_interview_language(data["interview_language"])
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
                "cv_sources": [], "interview_language": None}
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
    validate_preferences(root)


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

JOB_KEYS = {"schema_version", "job_id", "candidate_id", "status", "title", "company", "created_at", "participants", "changes", "interview_language"}


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
        raise ValueError(f"Unsupported or foreign job record (current interview_language field required): {job_id}, candidate {cdir.name}; data unchanged")
    validate_interview_language(data["interview_language"])
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
                "company": company, "created_at": now(), "participants": {"status": "pending", "people": []}, "changes": [], "interview_language": None}
        try:
            write_atomic(jdir / "job.json", dump(meta), create_only=True)
            for folder in ARTIFACT_KINDS.values():
                (jdir / folder).mkdir(exist_ok=True)
            extra = {"origin": "upload" if original else ("link" if source_url else "text")}
            if original:
                digest = extractor.sha256_file(original)
                stored = jdir / "postings" / ("001.original" + original.suffix.lower())
                shutil.copyfile(original, stored)
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
                     **effective_interview_language(read_candidate(cdir), meta),
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
    return {"job": meta, **effective_interview_language(read_candidate(cdir), meta),
            "open_points": job_open_points(meta), "latest": latest}


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


RUN_KEYS = {"schema_version", "run_id", "candidate_id", "job_id", "status", "answered_count", "planned_count", "resume_from",
            "followup_count", "followup_answered_count", "retry_count", "dialogue"}

# ---- follow-up dialogue (one block per main question) -------------------------------------------------------------
FOLLOWUP_KINDS = ("clarification", "completion", "deepening")
RESOLUTIONS = ("pending", "closed", "open")
BLOCK_KEYS = {"key", "question", "initial_answer", "initial_assessment", "block_assessment", "followups", "retries", "other_open_gaps"}
FOLLOWUP_KEYS = {"id", "kind", "reason", "text", "answer", "hints_before", "gap", "resolution"}
RETRY_KEYS = {"answer", "after_coaching"}
DIALOGUE_TEXT_LIMIT = 8000


def dialogue_text(value, field, *, optional=False):
    """Verbatim dialogue text: non-empty string, newlines allowed, other control characters not."""
    if value is None and optional:
        return None
    if (not isinstance(value, str) or not value.strip() or len(value) > DIALOGUE_TEXT_LIMIT
            or any(unicodedata.category(c).startswith("C") and c not in "\n\t\r" for c in value)):
        raise ValueError(f"Invalid dialogue field {field}")
    return value


def dialogue_flag(value, field):
    if type(value) is not bool:
        raise ValueError(f"Invalid dialogue field {field}: boolean required")
    return value


def exact_keys(record, keys, what):
    if not isinstance(record, dict) or set(record) != keys:
        raise ValueError(f"Invalid dialogue {what}: exactly the fields {sorted(keys)} are required")


def validate_dialogue(dialogue, status):
    """Validate the current-format dialogue; return the separately counted totals.

    Main questions (answered_count), follow-ups and retry attempts are counted independently. A follow-up never raises
    the main-question count. Only the very last follow-up (or main question) of an unfinished run may be unanswered.
    """
    if not isinstance(dialogue, list):
        raise ValueError("Invalid dialogue: a list of main-question blocks is required (use [] without questions)")
    answered = followups = followups_answered = retries = 0
    for index, block in enumerate(dialogue):
        exact_keys(block, BLOCK_KEYS, "block")
        last_block = index == len(dialogue) - 1
        if block["key"] != f"q-{index + 1}":
            raise ValueError(f"Invalid dialogue block key {block['key']!r}: expected q-{index + 1}")
        dialogue_text(block["question"], block["key"] + ".question")
        has_answer = dialogue_text(block["initial_answer"], block["key"] + ".initial_answer", optional=True) is not None
        for field in ("initial_assessment", "block_assessment"):
            dialogue_text(block[field], f"{block['key']}.{field}", optional=True)
        for field in ("followups", "retries", "other_open_gaps"):
            if not isinstance(block[field], list):
                raise ValueError(f"Invalid dialogue field {block['key']}.{field}: list required")
        for gap in block["other_open_gaps"]:
            dialogue_text(gap, block["key"] + ".other_open_gaps")
        if not has_answer:
            if status == "completed" or not last_block:
                raise ValueError(f"{block['key']}: only the last main question of a paused or stopped run may be unanswered")
            if (block["followups"] or block["retries"] or block["other_open_gaps"]
                    or block["initial_assessment"] is not None or block["block_assessment"] is not None):
                raise ValueError(f"{block['key']}: an unanswered main question has no follow-ups, retries, gaps or assessment")
        else:
            answered += 1
        for position, followup in enumerate(block["followups"]):
            exact_keys(followup, FOLLOWUP_KEYS, "follow-up")
            where = f"{block['key']}.followups[{position}]"
            if followup["id"] != f"{block['key']}-f{position + 1}":
                raise ValueError(f"{where}: id must be {block['key']}-f{position + 1}")
            if followup["kind"] not in FOLLOWUP_KINDS:
                raise ValueError(f"{where}: kind must be one of {', '.join(FOLLOWUP_KINDS)}")
            dialogue_text(followup["reason"], where + ".reason")
            dialogue_text(followup["text"], where + ".text")
            answer = dialogue_text(followup["answer"], where + ".answer", optional=True)
            dialogue_flag(followup["hints_before"], where + ".hints_before")
            gap = dialogue_text(followup["gap"], where + ".gap", optional=True)
            if followup["kind"] == "deepening":
                if gap is not None or followup["resolution"] == "open":
                    raise ValueError(f"{where}: a deepening follow-up is not a gap of the original answer (gap must be null, resolution not open)")
            elif gap is None:
                raise ValueError(f"{where}: clarification and completion follow-ups name the gap they address")
            if followup["resolution"] not in RESOLUTIONS or (followup["resolution"] == "pending") != (answer is None):
                raise ValueError(f"{where}: resolution must be pending exactly while the follow-up is unanswered")
            if not has_answer:
                raise ValueError(f"{where}: follow-up without an answer to the main question")
            followups += 1
            if answer is None:
                if status == "completed" or not (last_block and position == len(block["followups"]) - 1):
                    raise ValueError(f"{where}: only the last follow-up of a paused or stopped run may stay unanswered")
            else:
                followups_answered += 1
        for position, retry in enumerate(block["retries"]):
            exact_keys(retry, RETRY_KEYS, "retry")
            dialogue_text(retry["answer"], f"{block['key']}.retries[{position}].answer")
            dialogue_flag(retry["after_coaching"], f"{block['key']}.retries[{position}].after_coaching")
            retries += 1
    return dict(answered_count=answered, followup_count=followups, followup_answered_count=followups_answered, retry_count=retries)


def followup_evidence(followup):
    """none = unanswered; supported = content hints/coaching came first; after_followup = own answer to a neutral prompt."""
    if followup["answer"] is None:
        return "none"
    return "supported" if followup["hints_before"] else "after_followup"


def describe_dialogue(dialogue):
    """Evidence view for resumption and state updates (derived, never stored)."""
    return [dict(key=b["key"], initial_answer_given=b["initial_answer"] is not None,
                 followups=[dict(id=f["id"], kind=f["kind"], resolution=f["resolution"], evidence=followup_evidence(f)) for f in b["followups"]],
                 retries=[dict(evidence="supported" if r["after_coaching"] else "independent_retry") for r in b["retries"]],
                 open_gaps=[f["gap"] for f in b["followups"] if f["resolution"] == "open"] + list(b["other_open_gaps"]))
            for b in dialogue]


def open_followup(dialogue):
    if dialogue and dialogue[-1]["followups"] and dialogue[-1]["followups"][-1]["answer"] is None:
        return dialogue[-1]["followups"][-1]["id"]
    return None


def continuation_problem(previous, current):
    """Why `current` may not continue `previous` (None when valid).

    Allowed: fill a pending main answer; answer a pending follow-up (resolution may leave `pending`); raise `hints_before` of a
    pending follow-up false->true; append follow-ups, retries and main questions; fill a null `initial_assessment`; replace
    `block_assessment` or drop `other_open_gaps` entries of the LAST checkpoint block only if that block gained new evidence.
    Everything else is rejected: earlier blocks stay byte-equal; answered content, kinds, reasons, wording, gaps, hint flags and
    documented resolutions never change; a documented hint is never removed; gaps never vanish without new evidence.
    """
    old, new = previous["dialogue"], current["dialogue"]
    if len(new) < len(old):
        return "continuation drops main questions of the checkpoint"
    for index, before in enumerate(old):
        after = new[index]
        key = before["key"]
        if index < len(old) - 1:
            if after != before:
                return f"{key}: a closed main question of the checkpoint changed"
            continue
        if after["question"] != before["question"]:
            return f"{key}: main question changed"
        if before["initial_answer"] is not None and after["initial_answer"] != before["initial_answer"]:
            return f"{key}: original answer changed"
        if before["initial_assessment"] is not None and after["initial_assessment"] != before["initial_assessment"]:
            return f"{key}: first-answer assessment changed"
        if len(after["followups"]) < len(before["followups"]) or len(after["retries"]) < len(before["retries"]):
            return f"{key}: follow-ups or retries were dropped"
        new_evidence = before["initial_answer"] is None and after["initial_answer"] is not None
        for position, later in enumerate(after["followups"]):
            if position >= len(before["followups"]):
                new_evidence = new_evidence or later["answer"] is not None
                continue
            earlier = before["followups"][position]
            if any(earlier[f] != later[f] for f in ("id", "kind", "reason", "text", "gap")):
                return f"{earlier['id']}: follow-up changed"
            if earlier["answer"] is not None:
                if any(earlier[f] != later[f] for f in ("answer", "hints_before", "resolution")):
                    return f"{earlier['id']}: answered follow-up changed or was repeated"
            else:
                if earlier["hints_before"] and not later["hints_before"]:
                    return f"{earlier['id']}: a documented hint (hints_before) was removed"
                new_evidence = new_evidence or later["answer"] is not None
        if before["retries"] != after["retries"][:len(before["retries"])]:
            return f"{key}: earlier retries changed"
        new_evidence = new_evidence or len(after["retries"]) > len(before["retries"])
        if not new_evidence:
            if after["block_assessment"] != before["block_assessment"]:
                return f"{key}: block assessment changed without new evidence"
            if any(gap not in after["other_open_gaps"] for gap in before["other_open_gaps"]):
                return f"{key}: documented open gap disappeared without new evidence"
    return None


def parse_run(text, run_id, candidate_id):
    metadata, body = parse_header(text, HEADER, "run")
    if isinstance(metadata, dict) and metadata.get("schema_version") != RUN_SCHEMA:
        raise ValueError(f"Unsupported run format {metadata.get('schema_version')!r}: current run format {RUN_SCHEMA} "
                         "(structured follow-up dialogue) is required; no migration performed")
    if (not isinstance(metadata, dict) or set(metadata) != RUN_KEYS or type(metadata.get("schema_version")) is not int
            or metadata["run_id"] != run_id):
        raise ValueError("Invalid run lifecycle metadata")
    if metadata["candidate_id"] != candidate_id:
        raise ValueError("Run belongs to another candidate")
    job = metadata["job_id"]
    if job is not None and (not isinstance(job, str) or not JOB_ID.fullmatch(job)):
        raise ValueError("Invalid run job identifier")
    validate_lifecycle(metadata["status"], metadata["answered_count"], metadata["planned_count"])
    counts = validate_dialogue(metadata["dialogue"], metadata["status"])
    if any(metadata[key] != value for key, value in counts.items()):
        raise ValueError(f"Run counters do not match the dialogue: expected {counts}")
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
                or (previous["planned_count"] is not None and metadata["planned_count"] != previous["planned_count"])
                or continuation_problem(previous, metadata)):
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
        return {"candidate": meta, **effective_interview_language(meta), "profile_reliable": meta["profile"]["status"] == "confirmed",
                "state": state.decode("utf-8"), "state_sha256": hashlib.sha256(state).hexdigest(),
                "jobs": [{"job_id": j["job_id"], "title": j["title"], "company": j["company"]} for j in jobs],
                "runs": sorted(p.stem for p in checked_path(cdir, "runs", "dir").glob("*.md"))}


def resume(root, candidate_id, run_id):
    with candidate_lock(root, candidate_id) as cdir:
        metadata, body = require_resumable(cdir, run_id)
        state = checked_path(cdir, "state.md", "file").read_bytes()
        return {"run": metadata, "transcript": body, "open_followup": open_followup(metadata["dialogue"]),
                "dialogue_evidence": describe_dialogue(metadata["dialogue"]), "state": state.decode("utf-8"),
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
           answered_count=0, planned_count=None, resume_from=None, job_id=None, dialogue=None):
    validate_lifecycle(status, answered_count, planned_count)
    if dialogue is None:
        raise ValueError("A dialogue record is required (use an empty list when no question was asked)")
    counts = validate_dialogue(dialogue, status)
    if counts["answered_count"] != answered_count:
        raise ValueError(f"answered_count {answered_count} does not match the {counts['answered_count']} main questions answered "
                         "in the dialogue; follow-ups and retries never raise it")
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
        metadata = dict(schema_version=RUN_SCHEMA, run_id=run_id, candidate_id=cdir.name, job_id=job_id, status=status,
                        answered_count=answered_count, planned_count=planned_count, resume_from=resume_from,
                        followup_count=counts["followup_count"], followup_answered_count=counts["followup_answered_count"],
                        retry_count=counts["retry_count"], dialogue=dialogue)
        if resume_from is not None:
            problem = continuation_problem(previous, metadata)
            if problem:
                raise ValueError("Unsupported continuation: " + problem)
        header = json.dumps(metadata, allow_nan=False, ensure_ascii=False).replace("-->", "--\\u003e")
        transaction = dict(schema_version=SCHEMA, run_id=run_id,
                           run_text=HEADER + header + " -->\n" + run_text,
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


def pending_journals(root):
    return [c.name for c in checked_path(root, "candidates", "dir").iterdir()
            if not c.name.startswith(".") and candidate_journal(c).exists()]


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
    command("project-init", arg("--storage", required=True, choices=["local", "none"]), arg("--path"),
            arg("--switch", action="store_true"), help="Configure local storage; Nicht speichern never calls the runtime")
    command("project-show")
    command("validate", arg("--path"), project=False)
    sub.choices["validate"].add_argument("--project")
    command("set-language", arg("--interface", required=True, dest="interface_language"))
    language_cmd = command("set-interview-language", cand, arg("--job"))
    language_choice = language_cmd.add_mutually_exclusive_group(required=True)
    language_choice.add_argument("--language")
    language_choice.add_argument("--inherit", action="store_true")
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
            arg("--planned-count", type=int), arg("--resume-from"), arg("--job-id"),
            arg("--dialogue-file", type=Path, required=True))
    return p


def emit(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main(argv=None):
    args = build_parser().parse_args(argv)
    cfg = args.config_dir
    try:
        if args.cmd == "project-init":
            emit(setup_project(args.project, args.storage, args.path, config_dir=cfg, switch=args.switch))
            return 0
        if args.cmd == "validate" and args.path:
            problems = workspace_problems(args.path)
            print("VALID" if not problems else "\n".join(problems))
            return int(bool(problems))
        if args.cmd == "validate" and not args.project:
            raise ValueError("--project or --path is required")
        root, config = project_workspace(args.project, cfg)
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
        emit(set_language(root, args.interface_language))
    elif args.cmd == "set-interview-language":
        emit(set_interview_language(root, args.candidate, args.language, job_id=args.job, inherit=args.inherit))
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
                     resume_from=args.resume_from, job_id=args.job_id,
                     dialogue=strict_json(args.dialogue_file.read_text(encoding="utf-8")))
        print(f"Saved and verified run (local): {run}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
