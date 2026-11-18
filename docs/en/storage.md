# Storage and recovery

[Deutsch](../de/storage.md) | [English](./storage.md)

[Home](../../README.en.md) · [Documentation](README.md) · [Install](installation.md) · [Use](usage.md) · [Examples](screens.md) · [FAQ](faq.md) · [Storage](storage.md) · [Development](development.md)

## Storage model

The bundled Python CLI implements local storage only. A private workspace contains `candidate/profile.md`, `state.md`, immutable `runs/`, reusable `jobs/<job-id>/job.md`, `research.md` and `preparation.md`, plus optional `preferences.json` and the original CV with permission. Existing `workspace.yaml` can map paths. No real candidate data belongs in the public repository.

### Private GitHub / GitLab workspace

Use the agent's authenticated Git connector or a separately authenticated Git CLI to read the private workspace manifest, runs and state. Git writes must be explicitly performed and verified. The Python workspace CLI currently **does not** implement remote Git storage. Do not put private candidate data in this public repository.

### ChatGPT with supplied files

Provide the CV, vacancy and workspace files as attachments or Project files. Where no writable persistent file interface exists, the agent must return complete updated files for the user to save. An attached file is not automatically a persistent writeable state.

## Setup and configuration

Requires Python 3.10+ and a writable local directory; Git is not required. Replace `<installed-skill-directory>` with the actual installed skill directory:

```bash
python3 <installed-skill-directory>/scripts/interview_workspace.py init --path ~/interview-workspace
python3 <installed-skill-directory>/scripts/interview_workspace.py status
python3 <installed-skill-directory>/scripts/interview_workspace.py validate
```

The local pointer is stored in `~/.config/zyris/zyris-interview-coach/config.json` (or `$XDG_CONFIG_HOME/zyris/zyris-interview-coach/config.json`). The `init` command preserves existing files. To intentionally change workspace, use `init --path NEW_PATH --force`. This configuration is local to the machine and **does not synchronize to ChatGPT**.

After confirming the preference, use `set-language --interface de --interview en` with the same CLI. `--config PATH` is a global option before the subcommand; its file must be outside the workspace. Other preference keys are preserved.

## Save and resume

Before preparing an updated state, run `status` and retain its `state_sha256` with the state you read. Replace the example paths and hash below with actual values. At the end of a run, prepare a complete Markdown run file and updated state file, then save both. The snapshot hash and lifecycle arguments are now required (older `finish` invocations must be updated):

```bash
python3 <installed-skill-directory>/scripts/interview_workspace.py finish \
  --run-id 2026-11-17-example \
  --expected-state-sha256 <hash-from-status-before-editing> \
  --status stopped_early --answered-count 2 --planned-count 3 \
  --run-file /path/to/new-run.md \
  --state-file /path/to/new-state.md
```

For a checkpoint, save with `--status paused`, then use:

```bash
python3 <installed-skill-directory>/scripts/interview_workspace.py resume --run-id <checkpoint-id>
```

`resume` reads the checkpoint transcript, lifecycle metadata and current state/hash without consuming the checkpoint. Continue with a **new** run ID and `--resume-from <checkpoint-id>`; use `paused`, `stopped_early` or `completed` as appropriate. Answer counts are cumulative for that interview; the planned count is preserved. A known plan must be fully answered before using `completed`. Completed/stopped checkpoints and checkpoints already continued cannot be resumed. Legacy Markdown runs remain readable manually but are not automatically treated as resumable checkpoints. New runs include a small machine-readable HTML comment before the supplied Markdown; the original answer text remains in the body.

## Failures and recovery

The CLI serializes cooperating writers with an OS file lock and rejects stale prepared states. Runs are published without replacing an existing file. Unique temporary files are flushed before publication; existing file permissions are preserved. Candidate files and legacy runs are never migrated or rewritten by initialization, and `--force` only switches the workspace pointer. Configuration must be outside the candidate workspace; symlinks in managed workspace paths are refused.

Run and state remain separate files, so this is **not a multi-file atomic transaction**. A private `.zyris/pending.json` records recovery intent before publication. On any incomplete save, do not claim success: run `python3 <installed-skill-directory>/scripts/interview_workspace.py recover`. Recovery verifies existing contents and completes the same transaction; conflicts require manual reconciliation and are never overwritten. Until recovery, other writes and `status`/`resume` fail explicitly. Keep the journal until recovery succeeds; do not delete the persistent lock file to bypass a busy writer. OS locks are released automatically when a process exits or crashes.

## Limitations

These guarantees apply to cooperating CLI processes on a local filesystem. Direct external edits do not acquire the lock, and network/cloud-synchronized filesystems are not a supported transactional backend. The automated storage tests exercise real processes, interrupted writes, recovery and the packaged CLI with fictional data; they do not establish hosted-platform persistence. In **Do not save** (`Nicht speichern`) mode, do not invoke workspace commands: no initialization, lock, journal, run, checkpoint, preference or export is created. Feedback remains in the current conversation; host chat retention is separate.
