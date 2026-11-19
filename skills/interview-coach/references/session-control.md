# Session language and lifecycle contract

## Persistent language preference

The user's **interface language** governs the coach's own introduction, instructions, question framing, feedback, summaries, setup, confirmations and storage reports. It is independent of the language in which the candidate is being interviewed.

During setup, detect the user's predominant conversation language as a *proposal*, then ask once for confirmation (e.g. "Deutsch für die Bedienung verwenden? 1. Ja 2. Andere Sprache"). Do not infer nationality from CV or job advertisement. Store the confirmed language in private workspace `preferences.json` (schema version 1: `{"schema_version":1,"interface_language":"de","interview_language":"de"}`). Preserve all other keys on updates. If no persistent storage is available, state that preference may not carry over.

At the **start of every session, before the first visible reply**, load preferences from the existing workspace. If absent, follow the user's current language; avoid defaulting to English merely because the skill instructions are in English. A single answer in another language does not change the stored preference. Ask for explicit confirmation before changing it.

The interview language may differ (e.g. English practice). Announce any switch briefly in the interface language. After an English interview segment, return to the configured interface language for feedback unless the user requests otherwise.

## Commands

Interpret `stop`, `end`, `finish`, `abbrechen`, `beenden`, `Interview beenden` and `/interview-coach stop` or `/interview-coach end` as session control **only when issued as user commands**, not when quoted as part of an interview answer or job posting.

- `stop` / `end`: Immediately stop asking interview questions. Produce a concise summary of answered questions, demonstrated strengths, weaknesses, evidence and next practice. Persist an immutable **partial** run and update canonical state, including completion status `stopped_early`, answered count and planned count. Do not claim the entire interview was completed or promote a competency without adequate evidence.
- `finish`: Same early-stop behavior when questions remain; after the planned final answer, status is `completed`.
- `pause` / `unterbrechen`: Stop questioning and offer to save a resumable checkpoint, with status `paused`. On resumption, read the checkpoint and avoid repeating answered questions. Never silently overwrite an immutable run.
- If no answer has been given, record an empty or cancelled session **only when useful or requested**; do not invent answers, scores or improvements.
- Do not require the user to confirm `stop` a second time. The stop command itself authorizes saving the session to the previously confirmed workspace. If saving fails, provide the full report and clearly identify what was not persisted.
- A stop command must take priority over the normal "one question at a time" coaching loop. Do not ask another interview question after receiving it.

## Resume and concurrency

Do not assume that a new chat is a continuation of an in-progress interview simply because a targeted job exists. Check for a persisted `paused` or `in_progress` checkpoint, explain it, and offer "Fortsetzen / Neu beginnen". Do not infer a completed run from an empty runs directory. Separate session completion from job preparation state.

For local persistence, implement pause and stop via the transaction protocol in `storage.md`: retain the original state hash, save a new immutable run with explicit lifecycle status and cumulative answered/planned counts, and verify success. Resume only an explicitly selected `paused` checkpoint with `resume --run-id`; it returns transcript and state without changing them. Save a continuation under a new ID with `--resume-from`. Never mark an unfinished known plan completed or treat a stopped run as a resumable pause. If the user chose **Nicht speichern**, give only the in-chat summary and invoke no workspace CLI commands.
