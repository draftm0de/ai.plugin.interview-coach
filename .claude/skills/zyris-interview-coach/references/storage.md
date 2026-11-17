# Portable workspace and persistence contract

## Storage adapter discovery

- **local**: Write real files when agent has authorized filesystem access. Otherwise generate downloadable Markdown/JSON and ask user to place them locally.
- **git**: Use connected GitHub/GitLab repository, verify read/write permissions, fetch before updates and verify committed changes. Never embed personal state in a public skill repository.
- **chatgpt-files**: Use explicitly attached/available Project or Library files where supported. An uploaded file or old chat is not a writable transactional store. Generate updated state/run files when direct overwrite is unavailable.
- **ephemeral**: Allow practice without persistence but explicitly flag at start/end that next sessions won't automatically inherit state.

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

Existing private workspaces may provide paths in a `workspace.yaml` manifest. Prefer mapping paths over duplicating facts.

## Run format

A run contains identifier, date, type/mode/target role, research snapshot reference, competency goals, numbered interview questions, **actual answer quotes** where available, qualitative feedback, improved spoken wording, optional repeated attempt, final assessment, follow-up exercises and evidence for state changes.

Historical reconstructions must be marked. Never represent paraphrases as verbatim source.

## State format

`state.md`: as-of date, authoritative profile/CV path, list of completed runs, competency ID/status/priority, supporting evidence, next exercises, notes on persistent storage status. Updated at completion; never infer progress from generated model answers.

## Git hygiene

Keep immutable run records; avoid overwriting historical runs, append a suffix to a collision. Preserve candidate privacy. Do not create public issues containing candidate details. No secrets, interview recordings or private email addresses in public repository. Prefer a coherent atomic commit for run + state when supported; otherwise verify both writes and document any partial state.
