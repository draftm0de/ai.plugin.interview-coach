# Portable workspace and persistence contract

## Storage adapter discovery

- **local**: Write real files when agent has authorized filesystem access. Otherwise generate downloadable Markdown/JSON and ask user to place them locally.
- **git**: Use connected GitHub/GitLab repository, verify read/write permissions, fetch before updates and verify committed changes. Never embed personal state in a public skill repository.
- **chatgpt-files**: Use explicitly attached/available Project or Library files where supported. An uploaded file or old chat is not a writable transactional store. Generate updated state/run files when direct overwrite is unavailable.
- **ephemeral**: Allow practice without persistence but explicitly flag at start/end that next sessions won't automatically inherit state.

Never claim a successful write until tool response confirms it. Saving the run and updating state are separate operations; report partial failures and how to reconcile.

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
