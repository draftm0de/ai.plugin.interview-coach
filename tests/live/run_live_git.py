#!/usr/bin/env python3
"""Live GitHub/GitLab acceptance for the Git storage flow. NEVER runs without explicit approval.

It writes ONLY fictional data to ONE dedicated TEST BRANCH of ONE private test repository that the user names.
No force-push, no deletion of branches or repositories, no personal data. Authentication is whatever the user's
own `git` and `gh`/`glab` already provide; nothing is read or stored by this script.

Usage (after the user approved repository, branch and writes):
  python3 tests/live/run_live_git.py --provider github --repo OWNER/REPO --branch interview-coach-live-test \
      --approve "WRITE fictional data to github:OWNER/REPO@interview-coach-live-test"
  python3 tests/live/run_live_git.py ... --dry-run     # prints the plan only; performs no network or write action
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "skills/_shared/scripts/interview_workspace.py"
HOSTS = {"github": "github.com", "gitlab": "gitlab.com"}


def plan(args):
    remote = f"https://{HOSTS[args.provider]}/{args.repo}.git"
    steps = [f"read provider visibility/permissions via {'gh' if args.provider == 'github' else 'glab'} for {args.repo}",
             f"clone {remote} to a temporary directory and create local branch {args.branch}",
             "project-init --storage git (verifies private + write, commits and pushes the empty workspace to the test branch)",
             "create a fictional candidate, import a fictional Markdown CV, create a fictional job, save one run, git-publish",
             "read the remote branch with a fresh clone and compare file hashes",
             "git-pull in a second pointer/clone and list the data again (reload)",
             "make an unpublished local change and check git-status reports remote_saved=false"]
    return remote, steps


def sh(*cmd, cwd=None, check=True):
    done = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and done.returncode:
        raise SystemExit(f"FAILED: {' '.join(cmd[:4])}: {done.stderr.strip()[:300]}")
    return done


def rt(cfg, *args, check=True):
    return sh(sys.executable, "-B", str(RUNTIME), "--config-dir", str(cfg), *map(str, args), check=check)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--provider", choices=sorted(HOSTS), required=True)
    p.add_argument("--repo", required=True, help="OWNER/REPO (GitLab: group/project)")
    p.add_argument("--branch", required=True)
    p.add_argument("--approve", help="exact approval phrase printed by --dry-run")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    if args.branch in ("main", "master", "develop"):
        p.error("use a dedicated test branch, never a primary branch")
    remote, steps = plan(args)
    phrase = f"WRITE fictional data to {args.provider}:{args.repo}@{args.branch}"
    print("Planned actions:\n" + "\n".join(f"  {i + 1}. {s}" for i, s in enumerate(steps)))
    if args.dry_run:
        print(f"Approval phrase required: {phrase!r}\nDRY RUN: nothing was executed.")
        return 0
    if args.approve != phrase:
        print("NOT RUN: explicit approval phrase missing or different (see --dry-run)")
        return 2
    report = {"provider": args.provider, "repo": args.repo, "branch": args.branch, "steps": []}
    with tempfile.TemporaryDirectory(prefix="coach-live-") as tmp:
        tmp = Path(tmp)
        project, cfg, clone = tmp / "project", tmp / "cfg", tmp / "clone"
        project.mkdir()
        files = tmp / "files"
        files.mkdir()
        (files / "cv.md").write_text("# Erika Beispiel (fiktiv)\n\nBackend-Entwicklerin, Muster GmbH.\n")
        (files / "posting.md").write_text("# Senior Backend Engineer (fiktiv)\nBeispiel AG\n")
        sh("git", "clone", remote, str(clone))
        sh("git", "checkout", "-b", args.branch, cwd=clone)
        init = json.loads(rt(cfg, "project-init", "--project", project, "--storage", "git", "--path", clone, "--remote", remote).stdout)
        report["steps"].append({"project-init": {"remote_saved": init["publish"]["remote_saved"], "evidence": init["config"]["git"]["evidence"],
                                                  "visibility": init["config"]["git"]["visibility"], "target": init["publish"]["target"]}})
        cid = json.loads(rt(cfg, "candidate-create", "--project", project, "--name", "Erika Beispiel").stdout)["candidate_id"]
        rt(cfg, "cv-import", "--project", project, "--candidate", cid, "--file", files / "cv.md")
        rt(cfg, "job-create", "--project", project, "--candidate", cid, "--title", "Senior Backend Engineer", "--company", "Beispiel AG",
           "--posting-text-file", files / "posting.md")
        status = json.loads(rt(cfg, "status", "--project", project, "--candidate", cid).stdout)
        (files / "run.md").write_text("# Run (fiktiv)\n")
        (files / "state.md").write_text("# Zustand (fiktiv)\n")
        rt(cfg, "finish", "--project", project, "--candidate", cid, "--run-id", "live-run-1", "--run-file", files / "run.md",
           "--state-file", files / "state.md", "--expected-state-sha256", status["state_sha256"], "--status", "completed", "--answered-count", "1")
        before = json.loads(rt(cfg, "git-status", "--project", project).stdout)
        published = json.loads(rt(cfg, "git-publish", "--project", project, "--message", "live acceptance: fictional data").stdout)
        report["steps"].append({"before_publish_remote_saved": before["remote_saved"], "publish": published})
        fresh = tmp / "fresh"
        sh("git", "clone", "--branch", args.branch, remote, str(fresh))
        same = (fresh / "candidates" / cid / "runs/live-run-1.md").read_bytes() == (clone / "candidates" / cid / "runs/live-run-1.md").read_bytes()
        report["steps"].append({"remote_readback_matches": same, "head": sh("git", "rev-parse", "HEAD", cwd=fresh).stdout.strip()})
        project2, cfg2 = tmp / "project2", tmp / "cfg2"
        project2.mkdir()
        rt(cfg2, "project-init", "--project", project2, "--storage", "git", "--path", fresh, "--remote", remote)
        reloaded = json.loads(rt(cfg2, "candidate-list", "--project", project2).stdout)
        report["steps"].append({"reload_candidates": [c["candidate_id"] for c in reloaded]})
        (clone / "unpublished.txt").write_text("x")
        local = rt(cfg, "git-status", "--project", project).stdout
        report["steps"].append({"unpublished_change_reported_as_remote_saved": json.loads(local)["remote_saved"]})
    print(json.dumps(report, indent=1))
    ok = (report["steps"][0]["project-init"]["remote_saved"] and report["steps"][2]["remote_readback_matches"]
          and not report["steps"][4]["unpublished_change_reported_as_remote_saved"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
