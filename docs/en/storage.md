# Storage and recovery

[Deutsch](../de/storage.md) | [English](./storage.md)

[Home](../../README.en.md) · [Documentation](README.md) · [Install](installation.md) · [Use](usage.md) · [Examples](screens.md) · [FAQ](faq.md) · [Storage](storage.md) · [Development](development.md)

The authoritative description is [storage.md in the skills](../../skills/_shared/references/storage.md); this page explains it for users.

## Three storage options

On first use (or with `setup`) the coach asks for the storage type first and the concrete target second. The current project folder may be suggested but never becomes the target unasked.

| Option | Meaning |
|---|---|
| **Local** (Lokal) | A durable directory you name. Read/write access is checked before setup. |
| **Git** | An explicitly named **private** GitHub or GitLab repository. Saving means committing and pushing changes in that repository. |
| **Do not save** (Nicht speichern) | Nothing is persisted: no files, pointers, locks, journals, exports, CV copies, jobs, runs or learning state. Several candidates and jobs stay distinguishable inside the chat only; a later chat does not know them. `stop` gives an in-chat summary. |

"Manage files yourself" no longer exists, neither as a mode nor as a fallback. On save errors the coach shows the error and offers recovery or a new storage choice; it never exports unasked or switches the mode.

## Per-project resolution

Every project folder has its own pointer to its storage target (`~/.config/zyris/interview-coach/projects/<hash>.json`, or under `$XDG_CONFIG_HOME`). Two projects never switch each other; changing the target needs explicit confirmation (`--switch`). Old global pointers are neither searched nor read.

## Data structure (format 3)

```text
<storage target>/
  workspace.json  preferences.json  README.md  .gitignore
  candidates/<candidate-id>/
    candidate.json  profile.md  profile-history/NNN.md  state.md
    cv/cv-NNN/{original.<ext>, extracted.md, source.json}
    jobs/<job-id>/{job.json, postings/, research/, match/, preparation/}
    runs/<run-id>.md
  .journal/      (locks/journals/staging, protected, not in Git)
```

- **Candidate IDs** (`c-erika-beispiel-3f9a1c2b`) are stable and unique; equal names are allowed. Names are data and never become paths.
- **CV**: the original stays byte-identical (SHA-256 in `source.json`); `extracted.md` carries the content, not the layout. Status `complete` or `partial` (gaps such as images, unreadable pages, headers/footers, missing text layer). Partial imports are not reported as done.
- **Profile**: `missing`, `draft` or `confirmed`; confirmed only after you confirmed the factual content. Statement origin (CV, user statement, model suggestion) stays visible.
- **Jobs** belong to exactly one candidate. Posting, research (with sources and retrieval date), match and preparation are numbered snapshots; earlier versions and the original posting remain.
- **Runs** are immutable; the header names `candidate_id` and optionally `job_id`. The **learning state** (`state.md`) is per candidate and spans jobs; job-specific fit gaps live in the job's `match` snapshot.

## Git in detail

- Only `github.com` and `gitlab.com`. No tokens or passwords are requested or stored; access uses your existing `git`/`gh`/`glab` or an authorized connector.
- Before setup, read access, **private** status and write permission for exactly this repository are confirmed (via `gh`/`glab`, or a connector attestation that names the repository and carries your confirmation). A connector attestation is a relayed statement, not independent proof; it is never stored as evidence and is required again for every setup/publish. A change of target, storage type or repository is decided before any change and needs `--switch`. No test commit is made to probe permissions.
- Every saving command first requires a **clean** Git working tree (no staged, edited or foreign files, also not inside managed folders) and then commits exactly its own changes locally. Unexpected changes abort; nothing is stashed, reset or published — you resolve them yourself. All saving and publishing commands run under one shared cooperative Git-workspace lock (also across different candidates); only the paths the command wrote itself are committed, by explicit path (never `git add -A`); leftovers of a failed save are recorded with SHA-256 and resumed only while unchanged, unknown journal formats never. `git-pull`/`git-status` use the same lock. Staged changes of any kind (also under `.journal/`) are never hidden and abort saving and publishing with the affected paths (nothing is unstaged, deleted or reset automatically); unpublished commits containing `.journal` (or legacy `.zyris`) path segments are not pushed. Not protected: programs that ignore the cooperative lock. `git-publish` never stages: it re-checks privacy and write access and that `origin` (fetch and push URL) still names exactly the authorized repository and the URLs pinned at setup (several push targets, a different `pushurl`, any target without a provable identity of the authorized repository — for example redirected to a local path via `insteadOf` → abort before any write, no remote reconfiguration and no override switch), integrates foreign changes by rebase, pushes **without force** and verifies the remote head at the push target (a matching fetch target proves nothing). Only then does the coach report **remote saved**. A local-only change or a commit is not a remote success.
- A conflict in the same file, a rejected or interrupted push, missing rights or an unconfirmed remote head end in an error; local commits are kept and foreign changes are not overwritten.
- At session start `git-pull` fetches foreign changes (fast-forward only).
- Limits: attributing changes to a save assumes nobody else writes to the working tree during it. The runtime coordinates when a save counts as remotely successful; transport and sign-in belong to external tools. There is no provider SDK. Live behavior against GitHub/GitLab is untested (see [acceptance](../acceptance.md)).

## Errors and recovery (local and Git working copy)

Each candidate has its own lock and journal. A run is reported saved only after content verification. Run and learning state are not one atomic multi-file transaction; `.journal/pending.json` records the intent.

- Pending journal → `recover`; resolve conflicts with external edits manually and keep the journal.
- No journal, write error → fix the cause, retry the same run ID with the original state hash.
- Content exists, durability unconfirmed → inspect, do not overwrite, do not create a second run.
- "busy" → wait, never delete `.journal/lock`. "stale state" → re-read and reconcile content.
- An interrupted candidate or job creation stays an unusable draft (`creating`); `candidate-recover` completes it without overwriting. Interrupted CV staging under `.journal/stage-*` is never deleted automatically.

## The `.journal` folder

`.journal/` holds protected internal management and recovery data (locks, pending transactions, import staging) that may contain training answers or CV text. Do not delete or move it manually; it is never published to Git.

## Format limits

Only the current format 3 is supported. **Format 2 (control folder `.zyris`) is not supported:** a `.zyris` folder, file or symlink at workspace or candidate level — also mixed with `.journal` — is refused before any change ("old, unsupported layout"). Data stays unchanged; there is no migration, no reading of old journals for resumption and no renaming, copying, moving or deleting; no locks, journals, pointers or Git actions are created before the check. A new, empty storage location is required. Directories with the earlier layout (`state.md`, `candidate/profile.md`, `runs/` at the root), unrelated files, wrong schema versions, duplicate JSON keys, run files without current metadata or with a foreign candidate/job assignment are rejected **before any write** with a concrete reason. Existing data is neither migrated, deleted nor overwritten; pick an empty target for new data or reconcile manually.

Guarantees apply to cooperating processes on local file systems; network or cloud-sync directories are not a supported transaction backend.
