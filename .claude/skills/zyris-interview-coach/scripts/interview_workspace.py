#!/usr/bin/env python3
"""Portable interview workspace CLI. Stdlib only. No remote writes without explicit git push."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

APP = "zyris-interview-coach"
DEFAULT_CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "zyris" / APP / "config.json"
RUN_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,120}$")
REQUIRED = ("state.md", "candidate/profile.md", "runs", "jobs")

def write_atomic(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(content, encoding="utf-8")
    temp.replace(path)

def safe_root(path):
    return Path(path).expanduser().resolve()

def init_workspace(root, config=DEFAULT_CONFIG, force=False):
    root = safe_root(root)
    if config.exists() and not force:
        old = json.loads(config.read_text(encoding="utf-8"))
        if old.get("workspace") != str(root):
            raise ValueError("Configuration exists for another workspace. Use --force to switch explicitly.")
    root.mkdir(parents=True, exist_ok=True)
    for folder in ("candidate", "jobs", "runs"):
        (root / folder).mkdir(exist_ok=True)
    defaults = {
        "state.md": "# Interview training state\n\nStatus: initial / no completed runs\n\n## Competencies\n\n## Next training\n",
        "candidate/profile.md": "# Candidate profile\n\nProvide an approved CV or verified profile before targeted interviews.\n",
        "README.md": "# Interview workspace\n\nPrivate candidate data. Skill: zyris-interview-coach.\n",
    }
    for name, content in defaults.items():
        target = root / name
        if not target.exists():
            write_atomic(target, content)
    write_atomic(config, json.dumps({"schema_version": 1, "workspace": str(root), "storage": "local"}, indent=2) + "\n")
    return root

def configured_root(config=DEFAULT_CONFIG):
    if not config.is_file():
        raise FileNotFoundError("No workspace configured. Run: interview_workspace.py init --path PATH")
    data = json.loads(config.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("storage") != "local":
        raise ValueError("Unsupported config schema or storage adapter")
    root = safe_root(data["workspace"])
    if not root.is_dir():
        raise FileNotFoundError(f"Configured workspace not found: {root}")
    return root

def validate(root):
    root = safe_root(root)
    problems = [f"missing {p}" for p in REQUIRED if not (root / p).exists()]
    if (root / "state.md").exists() and not (root / "state.md").is_file():
        problems.append("state.md must be a file")
    return problems

def finish(root, run_id, run_text, state_text):
    """Local completion: prepare files, refuse overwrite, write run then state with recovery notice on failure."""
    root = safe_root(root)
    problems = validate(root)
    if problems:
        raise ValueError("; ".join(problems))
    if not RUN_ID.fullmatch(run_id) or ".." in run_id:
        raise ValueError("Invalid run identifier")
    if not run_text.strip() or not state_text.strip():
        raise ValueError("Run and state must not be empty")
    run = root / "runs" / (run_id + ".md")
    if run.exists():
        raise FileExistsError(f"Run already exists: {run}")
    write_atomic(run, run_text)
    try:
        write_atomic(root / "state.md", state_text)
    except Exception as exc:
        raise RuntimeError(f"Run saved at {run}, but state update failed; reconcile manually") from exc
    return run

def main(argv=None):
    p = argparse.ArgumentParser(description="ZYRIS Interview Coach workspace manager")
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init", help="Create workspace and local pointer")
    i.add_argument("--path", required=True)
    i.add_argument("--force", action="store_true", help="Explicitly switch existing workspace pointer")
    sub.add_parser("status", help="Show current local workspace")
    v = sub.add_parser("validate", help="Validate configured or specified workspace")
    v.add_argument("--path")
    f = sub.add_parser("finish", help="Save immutable run and replace state from prepared files")
    f.add_argument("--run-id", required=True)
    f.add_argument("--run-file", type=Path, required=True)
    f.add_argument("--state-file", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        if args.cmd == "init":
            root = init_workspace(args.path, args.config, args.force)
            print(f"Initialized: {root}")
        elif args.cmd == "status":
            root = configured_root(args.config)
            print(json.dumps({"workspace": str(root), "problems": validate(root)}, indent=2))
        elif args.cmd == "validate":
            root = safe_root(args.path) if args.path else configured_root(args.config)
            problems = validate(root)
            print("VALID" if not problems else "\n".join(problems))
            if problems:
                return 1
        elif args.cmd == "finish":
            root = configured_root(args.config)
            run = finish(root, args.run_id, args.run_file.read_text(encoding="utf-8"), args.state_file.read_text(encoding="utf-8"))
            print(f"Saved run: {run}\nUpdated state: {root / 'state.md'}")
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
