# Storage and recovery

[Deutsch](../de/storage.md) | [English](./storage.md)

[Home](../../README.en.md) · [Documentation](README.md) · [Install](installation.md) · [Use](usage.md) · [Examples](screens.md) · [FAQ](faq.md) · [Storage](storage.md) · [Development](development.md)

The authoritative description is [storage.md in the skills](../../skills/_shared/references/storage.md); this page explains it for users.

## Two storage options

On first use (or with `setup`) the coach asks for the storage type first and the concrete target second. The current project folder may be suggested but never becomes the target unasked.

| Option | Meaning |
|---|---|
| **Local** (Lokal) | A durable directory you name. Read/write access is checked before setup. |
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
- **Runs** are immutable (run format 4); the header names `candidate_id`, optionally `job_id` and, per main question `q-N`, the dialogue: original answer, follow-ups (`q-N-fM`: wording, kind, trigger, answer, hint flag, gaps) and retries. `answered_count` counts main questions only; `followup_count`, `followup_answered_count` and `retry_count` are kept separately. Run format 3 (without dialogue data) is rejected before writes and never migrated. The **learning state** (`state.md`) is per candidate and spans jobs; job-specific fit gaps live in the job's `match` snapshot.

## Removed storage mode

Git storage is no longer supported. Existing Git configurations are rejected unchanged; there is no automatic migration to local storage.

## Errors and recovery (local)

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
