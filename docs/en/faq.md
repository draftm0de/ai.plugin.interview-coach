# FAQ and troubleshooting

[Deutsch](../de/faq.md) | [English](./faq.md)

[Home](../../README.en.md) · [Documentation](README.md) · [Install](installation.md) · [Use](usage.md) · [Examples](screens.md) · [FAQ](faq.md) · [Storage](storage.md) · [Development](development.md)

## Product and access

### Is this an application or a skill?

It is a portable skill with a local Python workspace helper and platform-specific package builders. It runs inside a supported agent host; it does not provide its own model, chat application or hosted backend.

### Does a public repository mean there is a paid license or an open-source license?

The project is licensed under [MIT](../../LICENSE), as declared in [plugin.json](../../plugin.json). It has no payment system, customer accounts or license enforcement. Host access and model usage have their own terms.

## Requirements

### Do I need Git or Python to practise?

The documented build/install path uses Git and Bash, with Python 3.10+ for packaging and the local storage helper. A person receiving an already-built ZIP does not need the repository to upload it. Host-side code execution and persistence capabilities vary. Git is not required for a local candidate workspace.

## Privacy and persistence

### Will it remember me in a new chat?

Only when the host can read the verified persistent workspace again. Local paths on your computer do not automatically exist in a cloud sandbox. Attached files are not automatically writable state. See [storage](storage.md).

### What does “Nicht speichern” mean?

The skill creates no workspace, saved run, preference, research archive or automatic export. Conversation history may still be retained by the host under its own settings. It is not a promise that the platform records nothing.

### Can I put my CV in this repository?

No. Keep all real candidate data in a separate private workspace or supply it privately through your host. Public fixtures and examples are fictional. Never post CVs, interview transcripts, tokens or private workspace files in GitHub issues.

## Troubleshooting

### Why does the skill not appear?

Check the selected installation target and printed destination. Claude Code, Claude Chat skill upload and plugin ZIP upload are different workflows. Start a new host session after installation. Check permissions and the [installation guide](installation.md); do not assume a local install is visible on the web.

### Why can I not upload a ChatGPT plugin?

Upload availability depends on account, workspace and permissions. Building the ZIP cannot grant upload access. Ask the workspace administrator to check the host's documented plugin controls. See [installation](installation.md).

### Why am I still using an old version?

Local copies and manual ZIP uploads do not update when the repository changes. Pull the intended source, reinstall or rebuild, upload the new package as required, and start a new session. The MVP does not configure automatic marketplace updates.

### What if saving reports “busy”, “stale state” or “pending transaction”?

- **Busy:** another CLI process holds the workspace lock. Retry after it finishes; do not delete the lock file.
- **Stale state:** the prepared update was based on an older state. Re-read and reconcile; do not merely replace the hash to force the write.
- **Pending transaction:** run `recover`. Preserve the journal until recovery succeeds. External conflicts require manual reconciliation.

Never interpret a failed command as a saved run/state pair. [Commands and recovery details](storage.md).

### Why does resume reject a run?

Only a structured `paused` checkpoint that has not already been continued is resumable. Completed/stopped records and legacy Markdown require a new session or manual inspection. The CLI must not infer unrecorded answers.

## Validation limits

### Does a higher score prove that my interview skill is stable?

No. Scores assess particular answers. A polished coached revision is not an independent competence demonstration or a hiring prediction. The coach should seek evidence across distinct scenarios and later sessions.

### Are the examples real screenshots?

The current gallery contains a rendered preview and selected text from fictional CLI test responses. They are explicitly labelled as transcript excerpts. Native host UI screenshots have not yet been captured; see [Screens & examples](screens.md).

### What has been verified?

Deterministic tests cover packaging, installer behavior and local persistence, including concurrency, failure recovery and a packaged-CLI lifecycle. Optional CLI journeys test conversational heuristics with fictional data. Native platform UI, permissions and durable cross-chat storage still need platform acceptance. See [development](development.md).
