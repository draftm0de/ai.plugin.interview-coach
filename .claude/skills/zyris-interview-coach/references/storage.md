# Portable workspace and persistence contract

## Storage adapter discovery

- **local**: Write real files when agent has authorized filesystem access. Otherwise generate downloadable Markdown/JSON and ask user to place them locally.
- **git**: Use connected GitHub/GitLab repository, verify read/write permissions, fetch before updates and verify committed changes. Never embed personal state in a public skill repository.
- **chatgpt-files**: Use explicitly attached/available Project or Library files where supported. An uploaded file or old chat is not a writable transactional store. Generate updated state/run files when direct overwrite is unavailable.
- **ephemeral / Nicht speichern**: Explicit opt-out of all skill-managed persistence. Do not create a workspace, write state, run files, preferences, CV copies, job research, or downloadable export automatically. Feedback and adaptive coaching still work during the current conversation; no accumulated learning state or prior-job knowledge is available in later chats unless the user supplies it anew. Explain this briefly before beginning. The chat platform may retain conversation history under its own separate settings; do not promise that the conversation itself is unrecorded.

In explicit **Nicht speichern** mode, `stop` and `end` give an in-chat summary only, and `pause` cannot offer a persisted checkpoint. Do not invoke the normal completion-write contract unless the user later explicitly opts into storage.

Never claim a successful write until tool response confirms it. Saving the run and updating state are separate operations; report partial failures and how to reconcile.

## First-run initialization and pointer

Local storage with verified persistent filesystem: `python3 <skill-directory>/scripts/interview_workspace.py init --path ~/interview-workspace` creates missing files without overwriting existing data and writes a user-local JSON pointer at `~/.config/zyris/zyris-interview-coach/config.json` (or under `$XDG_CONFIG_HOME`). `status`, `validate` and `finish` provide deterministic operations. Changing the pointer requires explicit `init --force`. The CLI is bundled with the installed skill and currently implements **local storage only**. In hosted Claude Chat/ChatGPT execution, a home directory may be ephemeral and is not automatically the user's computer. Never claim cross-chat persistence without verifying the storage mechanism.

GitHub/GitLab: choose an existing authorized private repository, verify access, and persist its location via a workspace manifest or explicit prompt. Do not pretend the local CLI supports remote Git writes. For Git write use the host's connector or separately authenticated Git CLI, and verify commits.

ChatGPT: no universal user-local config file; provide the workspace location through attached project instructions or explicitly each new session when unavailable.

## Language preferences and partial sessions

Store user-confirmed `preferences.json` in the **private workspace** using `{"schema_version":1,"interface_language":"de","interview_language":"de"}` (example only). The local bundled CLI supports `set-language --interface de --interview de`; no language is preselected until confirmed. Read preferences at the start of every new session before the first visible response.

Runs have explicit lifecycle status `completed | stopped_early | paused` and answered/planned counts. For early stop, persist an immutable partial run and update state, without treating the interview as completed or inferring competence from missing answers. For pause, save a checkpoint for later continuation; never overwrite an immutable run. If storage is unavailable, state that clearly and return the report for manual saving.

## Portable canonical layout

```text
workspace/
  README.md
  state.md
  candidate/
    profile.md
    cv.pdf                  # optional original, private
  jobs/
    <job-id>/
      job.md                # complete posting text + source
      research.md           # sourced snapshot
      preparation.md        # candidate-role fit, gaps, question bank
  runs/
    YYYY-MM-DD-<scope>-<slug>.md
```

A job folder is persistent across multiple interview sessions for the same vacancy. Preserve its source-backed posting, research on employer and professional interviewers, role-specific question perspectives and preparation notes. Reuse before researching again; refresh outdated facts with dates and sources. Keep separate immutable run reports for each training attempt.

Existing private workspaces may provide paths in a `workspace.yaml` manifest. Prefer mapping paths over duplicating facts.

## Run format

A run contains identifier, date, type/mode/target role, research snapshot reference, competency goals, numbered interview questions, **actual answer quotes** where available, qualitative feedback, improved spoken wording, optional repeated attempt, final assessment, follow-up exercises and evidence for state changes.

Historical reconstructions must be marked. Never represent paraphrases as verbatim source.

## State format

`state.md`: as-of date, authoritative profile/CV path, list of completed runs, competency ID/status/priority, supporting evidence, next exercises, notes on persistent storage status. Updated at completion; never infer progress from generated model answers.

## Git hygiene

Keep immutable run records; avoid overwriting historical runs, append a suffix to a collision. Preserve candidate privacy. Do not create public issues containing candidate details. No secrets, interview recordings or private email addresses in public repository. Prefer a coherent atomic commit for run + state when supported; otherwise verify both writes and document any partial state.

## Local transaction and checkpoint protocol

1. Read `status` (or `resume --run-id ID` for an explicitly selected paused checkpoint) before preparing a replacement state. Retain the returned `state_sha256` from that read; never refresh the hash alone to bypass a stale-state error.
2. Save with `finish --run-id NEW_ID --run-file RUN.md --state-file STATE.md --expected-state-sha256 HASH --status completed|paused|stopped_early --answered-count N [--planned-count TOTAL] [--resume-from CHECKPOINT_ID]`. Counts are cumulative for the interview; unasked/unanswered questions are not evidence. A known plan must be fully answered for `completed`.
3. A successful CLI result verifies both immutable run and canonical state. The two files are not jointly atomic to outside readers. On failure, do not claim success or create a second run ID as a workaround. Use `recover` to finish the recorded intent. Conflicting external edits require manual reconciliation; preserve `.zyris/pending.json` until resolved.
4. A busy workspace fails immediately; retry after the other process finishes. A stale state requires re-reading and reconciling the actual state with the proposed update. OS locks are automatically released on process exit. Never delete `.zyris/lock` to bypass a writer.
5. New runs carry a versioned lifecycle metadata comment. `resume` returns the exact supplied report body, current state and hash without modifying the checkpoint. Saving a continuation requires a new immutable run and `--resume-from`; a checkpoint already continued cannot be forked implicitly. Legacy Markdown records are preserved and require manual inspection rather than inferred lifecycle metadata.
6. Existing candidate profiles, research, preferences and legacy runs are preserved by `init`, including `--force`. Managed symlinks and invalid path types are rejected. Configuration must be outside the candidate workspace. Local-filesystem and cooperating-CLI guarantees do not extend to direct external edits or network/cloud-synchronized filesystem semantics.

In **Nicht speichern** mode none of these CLI operations should run: no initialization, lock, journal, run, checkpoint, preference or export is created by the skill. Test harness artifacts are separate fictional developer data, not candidate persistence.
