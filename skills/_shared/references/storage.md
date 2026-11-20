# Storage contract (workspace format 3)

Single canonical layout. Private data lives in the user's storage target, never in the installed plugin.

```text
<storage target>/                      # chosen by the user: local directory
  workspace.json                       # {"format":"interview-coach-workspace","schema_version":3,...}
  preferences.json                     # {"schema_version":3,"interface_language":"de"}
  candidates/<candidate-id>/           # one folder per candidate; IDs like c-erika-beispiel-3f9a1c2b
    candidate.json                     # identity, status creating|active, profile status, CV sources
    profile.md  profile-history/NNN.md # current profile and earlier versions
    cv/cv-NNN/{original.<ext>, extracted.md, source.json}   # original byte-exact + Markdown + provenance
    state.md                           # this candidate's evidence-based learning state (cross-job)
    jobs/<job-id>/                     # IDs like j-acme-gmbh-senior-backend-3f9a1c2b
      job.json                         # company, title, participants, change log
      postings/NNN.md (+001.original.<ext>)  research/NNN.md  match/NNN.md  preparation/NNN.md
    runs/<run-id>.md                   # immutable runs; header names candidate_id and optional job_id
  .journal/                            # protected recovery data: locks, journals, staging (never delete by hand)
```

- Artifacts under `jobs/` are append-only snapshots (`NNN`); the highest number is current, earlier ones remain.
  Each header carries `candidate_id`, `job_id`, `kind`, `seq`, sources and retrieval date.
- `state.md` holds cross-job learning evidence. Job-specific fit gaps belong in `match/NNN.md`, never in `state.md`.
- Candidates share no learning state. Two candidates may have the same name; the ID decides.
- **`.journal` is protected internal data, not a cache**: it may contain training answers or CV text and is never deleted or moved by hand or by the tool.
- **Format 2 (control folder `.zyris`) is not supported**: a `.zyris` folder, file or symlink at workspace or candidate level — also mixed with `.journal` — is detected only to refuse. Everything is left unchanged; nothing is migrated, read for resumption, renamed, copied, moved or deleted; no lock, journal, pointer or Git write is created before the check passed. A new, empty storage location is required. Format 3 (this layout) is required in `workspace.json`/all records, so a format-2 workspace is not accepted even if its `.zyris` folder is missing.
- Format 1 workspaces (flat `state.md`, `candidate/profile.md`, `runs/` at the root) and any other layout are
  **not supported**: rejected before writes, left unchanged, never migrated.

## Local

Real files. `finish` is verified (run and state) before success is reported. Details: transaction protocol below.

## Removed Git storage

Only local storage and no-storage chat mode are supported. Git configuration is explicitly refused before
writes, including when switching to local; existing pointers and data stay unchanged. No clone, commit,
push, pull, provider authentication or connector storage is available. Never migrate data automatically.

## Nicht speichern

No workspace, pointer, lock, journal, export, CV copy, job, run or learning state. See `setup.md`.

## Language ownership

`candidate.json` requires `interview_language`: a confirmed language tag or null (not yet confirmed).
`job.json` requires `interview_language`: an explicit override or null (inherit that candidate's default).
`preferences.json` holds only the interface language, never an interview default. Records missing the current
language field and preferences with the former project-level `interview_language` are unsupported and refused
before writes, without migration or removal. Use a new empty target for testing this format; existing data stays untouched.
`set-interview-language` uses candidate locking like other candidate saving commands.

## Preferences and lifecycle

Run format 4 (header `schema_version: 4`) stores the structured follow-up dialogue in the run header next to the lifecycle fields; see `followup.md`/`runtime.md`. Run format 3 is refused without migration. Run status `completed | stopped_early | paused` with cumulative `answered_count`/`planned_count`. Unasked questions
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
