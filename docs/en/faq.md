# FAQ and troubleshooting

[Deutsch](../de/faq.md) | [English](./faq.md)

[Home](../../README.en.md) · [Documentation](README.md) · [Install](installation.md) · [Use](usage.md) · [Examples](screens.md) · [FAQ](faq.md) · [Storage](storage.md) · [Development](development.md)

## Product and access

### Is this an application or a skill?

It is a plugin with five coaching skills, a local Python runtime and derived host manifests for Claude Code and Codex. It runs inside a supported agent host; it does not provide its own model, chat application or hosted backend.

### Does a public repository mean there is a paid license or an open-source license?

The project is licensed under [MIT](../../LICENSE), as declared in [plugin.json](../../plugin.json). It has no payment system, customer accounts or license enforcement. Host access and model usage have their own terms.

## Requirements

### Do I need Git or Python to practise?

Add `https://github.com/draftm0de/ai.plugins` as a marketplace and select Interview Coach. No ZIP or local checkout is needed. The runtime requires Python 3.10+; Git only for Git storage. Host-side execution and persistence capabilities still need verification.

## Privacy and persistence

### Will it remember me in a new chat?

Only when the host can read the verified persistent workspace again. Local paths on your computer do not automatically exist in a cloud sandbox. Attached files are not automatically writable state. See [storage](storage.md).

### What does “Nicht speichern” (do not save) mean?

Nothing is persisted: no files, pointers, locks, journals, exports, CV copies, jobs, runs or learning state. Several candidates and jobs stay distinguishable inside the chat only; a later chat does not know them. The host may still retain the conversation under its own settings; this is not a promise that the platform records nothing.

### Which storage options exist?

Exactly three: **Local**, **Git** (private GitHub/GitLab repository only) and **Do not save**. "Manage files yourself" no longer exists; on save errors the coach offers recovery or a new storage choice.

### When is something "remote saved"?

Only after a successful push without force whose remote head was verified. A local change or commit alone is not a remote success. On conflicts, permission or transfer errors everything stays local and the coach says so openly.

### Can one project hold several candidates?

Yes, including equal names. Each candidate has their own ID and data; the coach asks when a choice is ambiguous. Learning states are never mixed.

### Why is my existing folder rejected?

Only the current format 3 is supported (the earlier format 2 with control folder `.zyris` is refused as well). Older layouts or unrelated files are rejected before any write and left unchanged; there is no migration. Choose an empty target.

### Why does a CV import report "partial" or a missing tool?

Images, unreadable pages, headers/footers or a missing text layer are disclosed. For PDF the runtime needs `pdftotext`, `mutool` or `pypdf`; it installs nothing and invents no extraction.

### Does the plugin support ChatGPT or Claude chat?

No. Supported hosts are Claude Code and Codex with local project folders. A hosted sandbox path is not automatically your computer; the coach claims no durability it cannot verify.

### Can I put my CV in this repository?

No. Keep all real candidate data in a separate private workspace or supply it privately through your host. Public fixtures and examples are fictional. Never post CVs, interview transcripts, tokens or private workspace files in GitHub issues.

## Troubleshooting

### Why does the skill not appear?

Check the Draftmode AI Plugins marketplace, repository access and permissions. Sync the catalog, select Interview Coach and start a new session. See [Installation](installation.md); local CLI installation does not establish web or account UI visibility.

### Why am I still using an old version?

Sync the shared marketplace in the host and start a new session. A repository push alone does not prove that installed content has refreshed. Verify the actual behavior after updating.

### What if saving reports “busy”, “stale state” or “pending transaction”?

- **Busy:** another CLI process holds the workspace lock. Retry after it finishes; do not delete the lock file.
- **Stale state:** the prepared update was based on an older state. Re-read and reconcile; do not merely replace the hash to force the write.
- **Pending transaction:** run `recover`. Preserve the journal until recovery succeeds. External conflicts require manual reconciliation.

Never interpret a failed command as a saved run/state pair. [Commands and recovery details](storage.md).

### Why does resume reject a run?

Only a structured `paused` checkpoint that has not already been continued is resumable. Completed/stopped records are not resumable; unsupported formats block workspace operations without migration. The CLI must not infer unrecorded answers.

## Validation limits

### Does a higher score prove that my interview skill is stable?

No. Scores assess particular answers. A polished coached revision is not an independent competence demonstration or a hiring prediction. The coach should seek evidence across distinct scenarios and later sessions.

### Are the examples real screenshots?

The current gallery contains a rendered preview and selected text from fictional CLI test responses. They are explicitly labelled as transcript excerpts. User-supplied Claude installation dialogs are included, but coaching UI screenshots have not yet been captured; see [Screens & examples](screens.md).

### What has been verified?

Deterministic tests cover manifests, the installable payload, candidate/job/run logic, CV extraction, recovery and the Git flow against local bare repositories – **not** GitHub/GitLab live. Model scenarios are heuristic. Isolated Claude Code/Codex runs and live Git remain open; see the [acceptance matrix](../acceptance.md) and [development](development.md).
