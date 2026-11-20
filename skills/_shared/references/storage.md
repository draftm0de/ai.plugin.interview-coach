# Storage contract (workspace format 3)

Single canonical layout. Private data lives in the user's storage target, never in the installed plugin.

```text
<storage target>/                      # chosen by the user: local directory or clone of a private repository
  workspace.json                       # {"format":"interview-coach-workspace","schema_version":3,...}
  preferences.json                     # {"schema_version":3,"interface_language":"de","interview_language":"de"}
  candidates/<candidate-id>/           # one folder per candidate; IDs like c-erika-beispiel-3f9a1c2b
    candidate.json                     # identity, status creating|active, profile status, CV sources
    profile.md  profile-history/NNN.md # current profile and earlier versions
    cv/cv-NNN/{original.<ext>, extracted.md, source.json}   # original byte-exact + Markdown + provenance
    state.md                           # this candidate's evidence-based learning state (cross-job)
    jobs/<job-id>/                     # IDs like j-acme-gmbh-senior-backend-3f9a1c2b
      job.json                         # company, title, participants, change log
      postings/NNN.md (+001.original.<ext>)  research/NNN.md  match/NNN.md  preparation/NNN.md
    runs/<run-id>.md                   # immutable runs; header names candidate_id and optional job_id
  .journal/                            # protected recovery data: locks, journals, staging (never published to Git; never delete by hand)
```

- Artifacts under `jobs/` are append-only snapshots (`NNN`); the highest number is current, earlier ones remain.
  Each header carries `candidate_id`, `job_id`, `kind`, `seq`, sources and retrieval date.
- `state.md` holds cross-job learning evidence. Job-specific fit gaps belong in `match/NNN.md`, never in `state.md`.
- Candidates share no learning state. Two candidates may have the same name; the ID decides.
- **`.journal` is protected internal data, not a cache**: it may contain training answers or CV text and is never deleted, moved or published by hand or by the tool.
- **Format 2 (control folder `.zyris`) is not supported**: a `.zyris` folder, file or symlink at workspace or candidate level — also mixed with `.journal` — is detected only to refuse. Everything is left unchanged; nothing is migrated, read for resumption, renamed, copied, moved or deleted; no lock, journal, pointer or Git write is created before the check passed. A new, empty storage location is required. Format 3 (this layout) is required in `workspace.json`/all records, so a format-2 workspace is not accepted even if its `.zyris` folder is missing.
- Format 1 workspaces (flat `state.md`, `candidate/profile.md`, `runs/` at the root) and any other layout are
  **not supported**: rejected before writes, left unchanged, never migrated.

## Local

Real files. `finish` is verified (run and state) before success is reported. Details: transaction protocol below.

## Git (private GitHub or GitLab only)

Boundary: the runtime coordinates *when a save counts as remote-saved*; transport and authentication belong to the
external `git` (and `gh`/`glab`) or to an authorized host connector. No provider SDK adapter, no credential handling.

1. `project-init --storage git` first decides (read-only) whether the setup or switch is allowed — a different target, storage type or
   repository needs `--switch` and is otherwise refused before anything is created. It then verifies: remote readable with existing
   authentication, **private** visibility and write permission for exactly that repository (via `gh`/`glab`, or a connector attestation
   naming the repository with the user's confirmation), clones into an empty directory (or reuses a clone of the same remote),
   pins the effective fetch/push URLs, creates the workspace and publishes it. The pointer is written only after remote success
   is confirmed. No test commit is made to probe permissions.
2. Start of a session: `git-pull` (fast-forward only; refuses while local work is unpublished or a recovery is pending). `git-pull`, `git-status`, saving and `git-publish` all use the same Git-workspace lock and re-check their state after acquiring it.
3. Each saving command (`finish`, `cv-import`, `profile-save`, `job-*`, `candidate-*`, `set-language`, `recover`) runs under one cooperative
   **Git workspace lock** (also held by `git-publish`, so saves and publishes of any candidates never mix; a second one fails as busy). It
   requires a clean working tree first (staged, edited or foreign files, also inside managed directories, abort without touching anything)
   and then stages and commits **only the paths this save wrote itself** (recorded by the managed writers), by explicit path — never
   `git add -A`. Anything that appears meanwhile aborts the commit and stays untouched. After a failed save, `.journal/interrupted.json`
   (schema 2) records its paths **with SHA-256**; the next save resumes them only while their content is unchanged. A leftover edited
   since, or a journal in an unknown format, aborts with a concrete message (nothing is resumed, migrated, deleted or reset). Then
   `git-publish`: before touching the remote it re-checks privacy/write evidence for the repository and that the fetch **and** push targets
   of `origin` (raw configuration and effective URLs after `insteadOf`/`pushInsteadOf`) each have a provable identity equal to the
   authorized repository and equal the URLs pinned at setup. A different, unprovable (for example local-path) or additional target is
   refused before any write; there is no flag to accept a rewrite. It fetches, integrates remote work by rebase, pushes **without force**
   to the verified push URL and verifies the remote head **at that push URL** (a matching fetch target proves nothing). Only exit 0 means
   **remote gespeichert**. Otherwise say plainly that the change is local only and show the error.
   Staged changes of any kind (add, modify, delete, rename) are never hidden — also under any `.journal/` — and abort a save or publish with the affected paths (nothing is unstaged, deleted or reset); `git-publish` also refuses to push any unpublished commit (including intermediate ones that removed the file again) that contains a `.journal` or legacy `.zyris` path segment — at the root or nested such as `candidates/<id>/.journal/…`; failing history queries abort before the push. Untracked or ignored control files (locks, journals) do not block.
   Limits: programs that ignore the cooperative locks can still race; a connector attestation is the user's relayed confirmation, not
   independent proof.
4. Conflicts in the same file, rejected or interrupted pushes, missing rights and an unconfirmed remote head all end in
   an error; local commits are kept, nothing is overwritten, nothing is force-pushed.
5. Without a local git client, a host connector may be used for the same layout only if it can read back and confirm the
   written content; otherwise report that Git storage is unavailable. (Live connector behavior is not covered by tests.)

## Nicht speichern

No workspace, pointer, lock, journal, export, CV copy, job, run or learning state. See `setup.md`.

## Preferences and lifecycle

Run status `completed | stopped_early | paused` with cumulative `answered_count`/`planned_count`. Unasked questions
are not evidence. `completed` requires the known plan to be fully answered.

## Local transaction protocol

1. `status` (or `resume`) returns `state_sha256`; keep it.
2. `finish` writes a journal under the candidate's `.journal/`, publishes the immutable run and the new state, and verifies both.
3. On failure: with a pending journal run `recover`; before a journal exists resolve the error and retry the same run ID
   with the original hash; if intended content already exists but durability is unconfirmed, inspect without creating another run.
   Conflicting external edits require manual reconciliation; the journal is kept.
4. A busy candidate fails immediately (cooperative lock); retry later. Never delete `.journal/lock`.
5. Continuations (`--resume-from`) need a new run ID, the same candidate and the same job, keep the planned count and
   never decrease the answered count. A checkpoint can be continued once.
6. Interrupted candidate/job creation leaves a draft marked `creating` that is not usable; `candidate-recover` completes
   a candidate without overwriting. Interrupted CV staging under `.journal/stage-*` is preserved, never auto-deleted.
7. Unsupported or foreign records block operations before any write and stay untouched.
