"""Storage coordination for private GitHub/GitLab repositories using the git CLI.

Boundary: this module coordinates *when* a save counts as remote-saved. Transport,
credentials and provider authentication belong entirely to the external `git`
(and, for the visibility check, `gh`/`glab`) tools or to a host connector the agent
attests to. No tokens are requested, read or stored. No force push is ever issued.
"""
from coach_core import CONTROL_SEGMENTS
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import quote

PROVIDERS = {"github.com": "github", "gitlab.com": "gitlab"}
SSH = re.compile(r"^git@([a-z0-9.-]+):([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+)/?$")
HTTPS = re.compile(r"^https://([a-z0-9.-]+)/([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+)/?$")


class GitStorageError(RuntimeError):
    """Remote storage was not (or not provably) updated."""


def parse_remote(url):
    """Accept only github.com / gitlab.com remotes; return (provider, host, project_path)."""
    if not isinstance(url, str):
        raise ValueError("Repository must be a URL")
    match = HTTPS.fullmatch(url.strip()) or SSH.fullmatch(url.strip())
    if not match or match.group(1) not in PROVIDERS:
        raise ValueError("Only private GitHub or GitLab repositories (github.com, gitlab.com) are supported")
    host, path = match.group(1), match.group(2)
    path = path[:-4] if path.endswith(".git") else path
    if ".." in path.split("/"):
        raise ValueError("Unsafe repository path")
    if PROVIDERS[host] == "github" and path.count("/") != 1:
        raise ValueError("GitHub repositories must be OWNER/REPO")
    return PROVIDERS[host], host, path


def git(args, cwd=None, check=True):
    """Single choke point for git calls: refuses force options and never prompts."""
    for arg in args:
        if arg in ("-f", "--force", "--force-with-lease", "--force-if-includes") or arg.startswith("--force") \
                or (args[:1] == ["push"] and arg.startswith("+")):
            raise GitStorageError("Forced git operations are not permitted")
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    if not shutil.which("git"):
        raise GitStorageError("git is not available; nothing was installed")
    done = subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=300)
    if check and done.returncode != 0:
        raise GitStorageError(f"git {args[0]} failed: " + (done.stderr or done.stdout).strip()[:400])
    return done


def check_visibility(provider, path, *, which=shutil.which, run=subprocess.run):
    """Ask the provider CLI (already authenticated by the user) for visibility and push rights."""
    tool = "gh" if provider == "github" else "glab"
    if not which(tool):
        return {"private": None, "can_push": None, "source": None,
                "reason": f"{tool} is not available; use a host connector attestation or install/authenticate it yourself"}
    if provider == "github":
        command = ["gh", "repo", "view", path, "--json", "isPrivate,viewerPermission"]
    else:
        command = ["glab", "api", "projects/" + quote(path, safe="")]
    done = run(command, capture_output=True, text=True, timeout=60)
    if done.returncode != 0:
        return {"private": None, "can_push": None, "source": tool,
                "reason": f"{tool} could not read the repository (not authenticated or no access): " + done.stderr.strip()[:300]}
    try:
        data = json.loads(done.stdout)
    except ValueError:
        return {"private": None, "can_push": None, "source": tool, "reason": f"{tool} returned unreadable output"}
    if provider == "github":
        return {"private": data.get("isPrivate") if isinstance(data.get("isPrivate"), bool) else None,
                "can_push": data.get("viewerPermission") in ("ADMIN", "MAINTAIN", "WRITE"), "source": tool}
    permissions = data.get("permissions") or {}
    levels = [(permissions.get(k) or {}).get("access_level", 0) for k in ("project_access", "group_access")]
    return {"private": (data.get("visibility") == "private") if "visibility" in data else None,
            "can_push": max(levels) >= 30, "source": tool}


def verify_target(remote, *, attest=None, **tools):
    """Require confirmed private visibility and write ability for exactly this repository.

    Independent evidence comes only from the provider CLI. A connector attestation is a claim relayed by the
    agent after the user saw the connector's answer: it must name this repository, is never persisted as proof
    and must be supplied again for every setup/publish.
    """
    provider, host, path = parse_remote(remote)
    found = git(["ls-remote", remote], check=False)
    if found.returncode != 0:
        raise GitStorageError("Remote is not readable with the available git authentication: "
                              + (found.stderr or "").strip()[:300])
    evidence = check_visibility(provider, path, **tools)
    if evidence["private"] is None or evidence["can_push"] is None:
        if not attest:
            raise GitStorageError("Private repository status not confirmed"
                                  + (": " + evidence["reason"] if evidence.get("reason") else "")
                                  + ". Only confirmed private repositories are accepted")
        if attest.get("repository") != path or not attest.get("user_confirmed"):
            raise GitStorageError("Connector attestation must name this exact repository (" + path
                                  + ") and carry the user's confirmation; it is renewed for every action")
        evidence = {"private": attest["private"], "can_push": attest["write"],
                    "source": "connector-attestation:" + attest["source"]}
    if evidence["private"] is not True:
        raise GitStorageError("Private repository status not confirmed: repository is not private. "
                              "Only confirmed private repositories are accepted")
    if evidence["can_push"] is not True:
        raise GitStorageError("Write permission not confirmed for this repository")
    return {"provider": provider, "host": host, "repository": path, "remote": remote,
            "visibility": "private", "write_confirmed": True, "evidence": evidence["source"]}


def _normalized(url):
    provider, host, path = parse_remote(url)
    return (provider, host, path)


def _lines(result):
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def identity_of(url):
    """Repository identity (provider, host, path) of a URL, or None if it cannot be proven to be a GitHub/GitLab repository.

    Local paths, other hosts and unknown schemes have no provable identity. Tests that reach a local bare repository
    replace this single function with a controlled double; there is no flag or environment bypass.
    """
    try:
        return _normalized(url)
    except ValueError:
        return None


def check_rewrite(remote):
    """Before cloning: what git would really contact for the authorized URL must be that same repository."""
    effective = git(["ls-remote", "--get-url", remote], check=False).stdout.strip()
    if effective and identity_of(effective) != _normalized(remote):
        raise GitStorageError("git rewrites the authorized URL to a target whose identity cannot be proven to be the authorized "
                              "repository; refusing before any write. Fix the git configuration (insteadOf)")


def resolve_targets(path, remote, *, pinned=None):
    """Bind fetch AND push targets of origin to the authorized repository before anything is written.

    Raw configuration (remote.origin.url / pushurl) and the effective URLs git will really use (after
    insteadOf/pushInsteadOf) must each be single and each have a provable identity equal to the authorized repository.
    A different or unprovable effective target is refused; after setup the targets must also equal the pinned values.
    """
    authorized = _normalized(remote)
    raw_fetch = _lines(git(["config", "--local", "--get-all", "remote.origin.url"], cwd=path, check=False))
    raw_push = _lines(git(["config", "--local", "--get-all", "remote.origin.pushurl"], cwd=path, check=False))
    if len(raw_fetch) != 1:
        raise GitStorageError("origin must have exactly one fetch URL")
    if len(raw_push) > 1:
        raise GitStorageError("origin has several push URLs; refusing to publish to more than one target")
    for url in raw_fetch + raw_push:
        if identity_of(url) != authorized:
            raise GitStorageError("origin does not point to the authorized repository (" + authorized[2]
                                  + "); not publishing. The remote is never reconfigured automatically")
    eff_fetch = _lines(git(["remote", "get-url", "--all", "origin"], cwd=path))
    eff_push = _lines(git(["remote", "get-url", "--push", "--all", "origin"], cwd=path))
    if len(eff_fetch) != 1 or len(eff_push) != 1:
        raise GitStorageError("origin resolves to several fetch or push targets; refusing to publish")
    for url in eff_fetch + eff_push:
        if identity_of(url) != authorized:
            raise GitStorageError("The effective git target (after URL rewriting) cannot be proven to be the authorized repository ("
                                  + authorized[2] + "); refusing before any write")
    targets = {"fetch": eff_fetch[0], "push": eff_push[0]}
    if pinned is not None and (pinned["fetch"], pinned["push"]) != (targets["fetch"], targets["push"]):
        raise GitStorageError("The effective git target changed since setup (URL rewriting or remote edit); not publishing")
    return targets


def prepare_clone(path, remote):
    """Clone into an empty directory or validate an existing clone of the same remote."""
    path = Path(path)
    if path.is_symlink():
        raise ValueError("Clone path must not be a symlink")
    if path.exists() and not path.is_dir():
        raise ValueError(f"Expected directory: {path}")
    if (path / ".git").exists():
        origin = git(["config", "--local", "--get", "remote.origin.url"], cwd=path, check=False).stdout.strip()
        if origin != remote:
            raise GitStorageError("Existing clone points to a different remote; refusing to reuse it")
        return "existing"
    if path.exists() and any(path.iterdir()):
        raise ValueError("Clone path must be empty or an existing clone of the repository")
    path.parent.mkdir(parents=True, exist_ok=True)
    git(["clone", remote, str(path)])
    return "cloned"


def branch_of(path):
    return git(["symbolic-ref", "--short", "HEAD"], cwd=path).stdout.strip()


def _fetch(path, branch, targets):
    done = git(["fetch", targets["fetch"] if targets else "origin", f"+refs/heads/{branch}:refs/remotes/origin/{branch}"],
               cwd=path, check=False)
    ok = done.returncode == 0 or "couldn't find remote ref" in done.stderr
    return ok, done


def status(path, targets=None):
    branch = branch_of(path)
    dirty = bool(git(["status", "--porcelain"], cwd=path).stdout.strip())
    reachable, fetched = _fetch(path, branch, targets)
    remote_ref = f"refs/remotes/origin/{branch}"
    has_remote = git(["rev-parse", "--verify", "-q", remote_ref], cwd=path, check=False).returncode == 0
    has_head = git(["rev-parse", "--verify", "-q", "HEAD"], cwd=path, check=False).returncode == 0
    ahead = behind = 0
    if has_remote and has_head:
        counts = git(["rev-list", "--left-right", "--count", f"HEAD...{remote_ref}"], cwd=path).stdout.split()
        ahead, behind = int(counts[0]), int(counts[1])
    elif has_head:
        ahead = int(git(["rev-list", "--count", "HEAD"], cwd=path).stdout.strip())
    return {"branch": branch, "uncommitted_changes": dirty, "ahead": ahead, "behind": behind,
            "remote_reachable": reachable,
            "remote_saved": reachable and not dirty and ahead == 0 and (has_remote or not has_head)}


def pull(path, targets=None):
    """Fast-forward only; never merges, rebases or discards local work."""
    info = status(path, targets)
    if not info["remote_reachable"]:
        raise GitStorageError("Remote not reachable; local copy may be outdated")
    if info["uncommitted_changes"] or info["ahead"]:
        raise GitStorageError("Local unpublished changes exist; publish them before pulling")
    if info["behind"]:
        git(["merge", "--ff-only", f"origin/{info['branch']}"], cwd=path)
    return status(path, targets)


def _status_entries(path):
    out = git(["status", "--porcelain=v1", "-z", "--untracked-files=all"], cwd=path).stdout.split("\0")
    entries, skip = [], False
    for token in out:
        if skip:
            skip = False
            continue
        if len(token) < 4:
            continue
        if is_control_path(token[3:]) and token[0] in " ?!":
            continue  # untracked/ignored/unstaged control files (locks, journals) are never workspace data; STAGED ones are not hidden
        entries.append((token[0], token[1], token[3:]))
        if token[0] in "RC":
            skip = True
    return entries


def staged_paths(path):
    """Every path staged in the index (add, modify, delete, rename), including control files."""
    out = git(["diff", "--cached", "--name-only", "--no-renames", "-z"], cwd=path).stdout
    return sorted({p for p in out.split("\0") if p})


def is_control_path(relative):
    """True if any COMPLETE path segment is `.journal` or the legacy `.zyris` (root or nested, e.g. candidates/<id>/.journal/pending.json)."""
    return any(segment in CONTROL_SEGMENTS for segment in relative.split("/"))


def control_files_in_unpublished_commits(path, branch):
    """Control files inside ANY commit a push would publish (also intermediate commits that removed them again).

    Uses `rev-list` + `diff-tree -z` per commit, so path names are never split on newlines. Failing git queries raise: an error is
    never read as "no matches". A remote branch that does not exist yet (probe exit 1) is the explicit "first push" state: all
    commits reachable from HEAD are checked.
    """
    remote_ref = f"refs/remotes/origin/{branch}"
    probe = git(["rev-parse", "--verify", "-q", remote_ref], cwd=path, check=False)
    if probe.returncode not in (0, 1):
        raise GitStorageError("Could not determine the remote branch state; nothing was pushed: " + probe.stderr.strip()[:300])
    listed = git(["rev-list", f"{remote_ref}..HEAD" if probe.returncode == 0 else "HEAD"], cwd=path, check=False)
    if listed.returncode != 0:
        raise GitStorageError("Could not list the commits to publish; nothing was pushed: " + listed.stderr.strip()[:300])
    found = set()
    for commit in listed.stdout.split():
        tree = git(["diff-tree", "--no-commit-id", "--name-only", "-r", "-z", "--no-renames", "--root", "-m", commit], cwd=path, check=False)
        if tree.returncode != 0:
            raise GitStorageError(f"Could not read the files of commit {commit[:12]}; nothing was pushed: " + tree.stderr.strip()[:300])
        found.update(p for p in tree.stdout.split("\0") if p and is_control_path(p))
    return sorted(found)


def changed_paths(path):
    return sorted({p for _, _, p in _status_entries(path)})


def file_digest(root, relative):
    """SHA-256 of a working-tree file, or None if it does not exist (deleted)."""
    import hashlib
    target = Path(root) / relative
    return hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() and not target.is_symlink() else None


def baseline(path, allowed=None):
    """Refuse to proceed when the working tree holds anything this save did not create.

    Staged changes, unstaged edits and untracked foreign files all block (nothing is touched, stashed or reset).
    `allowed` maps paths left behind by an earlier interrupted save of this tool to the SHA-256 recorded then; a path
    whose content changed since is foreign work and blocks like any other change.
    """
    allowed = allowed or {}
    entries = _status_entries(path)
    staged = sorted(set(staged_paths(path)) | {p for x, _, p in entries if x not in " ?!"})
    unexpected = sorted({p for _, _, p in entries if p not in allowed})
    modified = sorted({p for _, _, p in entries if p in allowed and file_digest(path, p) != allowed[p]})
    if staged or unexpected or modified:
        shown = (staged + [p for p in unexpected + modified if p not in staged])[:12]
        raise GitStorageError("Unexpected changes in the Git workspace (" + ("staged: " if staged else "")
                              + ", ".join(shown) + (" — changed since an interrupted save" if modified else "")
                              + "); they cannot be attributed to this save. Nothing was changed or published; "
                              "resolve them manually (commit, move or discard them yourself) and retry")


def commit_own(path, message, own):
    """Stage and commit exactly the paths in `own` (relative, as written by this save). Returns False if nothing changed.

    Any other change that appeared meanwhile aborts before staging: nothing is committed, staged or discarded.
    """
    own = set(own)
    staged = staged_paths(path)
    if staged:
        raise GitStorageError("Staged changes exist (" + ", ".join(staged[:12]) + "); nothing was committed. They are neither "
                              "unstaged nor published by this tool; resolve them manually and repeat the save")
    changed = {p for _, _, p in _status_entries(path)}
    if not changed:
        return False
    foreign = sorted(changed - own)
    if foreign:
        raise GitStorageError("Unexpected changes appeared during the save (" + ", ".join(foreign[:12])
                              + "); nothing was committed. Resolve them manually and repeat the save")
    env = {"GIT_LITERAL_PATHSPECS": "1"}
    import os as _os
    saved = {k: _os.environ.get(k) for k in env}
    _os.environ.update(env)
    try:
        git(["add", "--", *sorted(changed)], cwd=path)
    finally:
        for k, v in saved.items():
            if v is None:
                _os.environ.pop(k, None)
            else:
                _os.environ[k] = v
    committed = git(["commit", "-m", message], cwd=path, check=False)
    if committed.returncode != 0:
        raise GitStorageError("Commit failed (is a git user.name/user.email configured?); changes remain local only: "
                              + (committed.stderr or committed.stdout).strip()[:300])
    return True


def publish(path, targets):
    """Integrate remote work without overwriting it, push without force to the pinned target, verify remotely.

    Never stages or commits: uncommitted changes (own or foreign) abort the publication.
    """
    path = Path(path)
    branch = branch_of(path)
    staged = staged_paths(path)
    if staged:
        raise GitStorageError("Staged changes exist in the Git workspace (" + ", ".join(staged[:12])
                              + "); nothing was published. Resolve them manually (nothing is unstaged automatically)")
    if _status_entries(path):
        raise GitStorageError("Uncommitted changes exist in the Git workspace (" + ", ".join(changed_paths(path)[:12])
                              + "); nothing was published. Repeat the saving action or resolve them manually")
    if git(["rev-parse", "--verify", "-q", "HEAD"], cwd=path, check=False).returncode != 0:
        raise GitStorageError("Nothing to publish")
    fetched = git(["fetch", targets["fetch"], f"+refs/heads/{branch}:refs/remotes/origin/{branch}"], cwd=path, check=False)
    if fetched.returncode != 0 and "couldn't find remote ref" not in fetched.stderr:
        raise GitStorageError("Remote fetch failed; changes are LOCAL ONLY, not saved remotely: " + fetched.stderr.strip()[:300])
    remote_ref = f"refs/remotes/origin/{branch}"
    if git(["rev-parse", "--verify", "-q", remote_ref], cwd=path, check=False).returncode == 0:
        if git(["merge-base", "--is-ancestor", remote_ref, "HEAD"], cwd=path, check=False).returncode != 0:
            if git(["merge-base", "--is-ancestor", "HEAD", remote_ref], cwd=path, check=False).returncode == 0:
                git(["merge", "--ff-only", remote_ref], cwd=path)
            else:
                rebased = git(["rebase", remote_ref], cwd=path, check=False)
                if rebased.returncode != 0:
                    git(["rebase", "--abort"], cwd=path, check=False)
                    raise GitStorageError("Conflicting remote changes in the same files; local commits are kept unmodified and are "
                                          "NOT saved remotely. Reconcile manually; nothing was overwritten")
    control = control_files_in_unpublished_commits(path, branch)
    if control:
        raise GitStorageError("Unpublished commits contain control files (" + ", ".join(control[:12])
                              + "); nothing was pushed. Remove them from the history yourself; nothing is rewritten automatically")
    pushed = git(["push", targets["push"], f"HEAD:refs/heads/{branch}"], cwd=path, check=False)
    if pushed.returncode != 0:
        raise GitStorageError("Push rejected or interrupted; changes are LOCAL ONLY, not saved remotely: "
                              + pushed.stderr.strip()[:300])
    head = git(["rev-parse", "HEAD"], cwd=path).stdout.strip()
    # Verify exactly where we wrote: a matching head at the fetch target proves nothing about the push target.
    listed = git(["ls-remote", targets["push"], f"refs/heads/{branch}"], cwd=path, check=False)
    remote_head = listed.stdout.split()[0] if listed.returncode == 0 and listed.stdout.split() else None
    if remote_head != head:
        raise GitStorageError("Remote success could not be confirmed at the push target (head differs or is unreadable); "
                              "do not report this as remotely saved")
    return {"remote_saved": True, "branch": branch, "commit": head, "target": targets["push"]}
