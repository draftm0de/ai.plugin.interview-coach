# Session language and lifecycle contract

## Persistent language preference

The user's **interface language** governs the coach's own introduction, instructions, question framing, feedback, summaries, setup, confirmations and storage reports. It is independent of the language in which the candidate is being interviewed.

During setup, detect the user's predominant conversation language as a *proposal*, then ask once for confirmation (e.g. "Deutsch für die Bedienung verwenden? 1. Ja 2. Andere Sprache"). Do not infer nationality from CV or job advertisement. Store the confirmed language in the workspace's `preferences.json` via `set-language` (schema version 3: `{"schema_version":3,"interface_language":"de"}`). Preserve all other keys on updates. If no persistent storage is available, state that preference may not carry over.

At the **start of every session, before the first visible reply**, load preferences from the existing workspace. If absent, follow the user's current language; avoid defaulting to English merely because the skill instructions are in English. A single answer in another language does not change the stored preference. Ask for explicit confirmation before changing it.

Interview language belongs to the selected candidate and optionally the selected job, never to project preferences.
During candidate creation confirm the default and save `candidate.json.interview_language` via
`set-interview-language --candidate ID --language TAG`. Null means not yet confirmed; ask before starting interview questions.
During job creation offer the candidate default or another language for this specific job; save an explicit override via
`set-interview-language --candidate ID --job JOB --language TAG`. `--inherit` removes only this job's override.
A null job language inherits the candidate default dynamically; it is not a company-wide setting. Two jobs at the
same company can use different languages. Never copy a job override into the candidate or another job.
Use `status` for general training and `job-show` for job training: `interview_language` and `language_source`
report the effective choice (job > candidate; unconfirmed means ask, never silently use the interface language).
Language choices are not limited to German and English; accept other language names and map confirmed choices to language tags.
In Nicht speichern mode maintain the same candidate/job distinction only in chat, without runtime calls.
The interview language may differ from the interface language (e.g. English practice). Announce any switch briefly in the interface language. After an English interview segment, return to the configured interface language for feedback unless the user requests otherwise.

## Commands

Interpret `stop`, `end`, `finish`, `abbrechen`, `beenden`, `Interview beenden` and `/interview-coach stop`, `/interview-coach:interview-coach stop` or the same word in the host's native syntax as session control **only when issued as user commands**, not when quoted as part of an interview answer or job posting.

- `stop` / `end`: Immediately stop asking interview questions, including an open follow-up (it stays unanswered: not an answer, not a failed answer, no invented evidence). Produce a concise summary of answered questions, demonstrated strengths, weaknesses, evidence and next practice. Persist an immutable **partial** run and update canonical state, including completion status `stopped_early`, answered count and planned count. Do not claim the entire interview was completed or promote a competency without adequate evidence. `stop` always finishes with `stopped_early`, never `paused`: the run is final and a stopped run cannot be resumed (the runtime resumes only `paused` checkpoints). The closing answer must therefore NOT promise to pick up the open follow-up or the session later (no "beim Fortsetzen stelle ich die Nachfrage erneut"); state that the follow-up stays unanswered and, if the user wants to continue another time, that `pause` is the command that keeps a checkpoint.
- `finish`: Same early-stop behavior when questions remain; after the planned final answer, status is `completed`.
- `pause` / `unterbrechen`: Stop questioning and offer to save a resumable checkpoint, with status `paused`. On resumption, read the checkpoint (`resume` → `open_followup`, `dialogue_evidence`), avoid repeating answered main questions or follow-ups and re-ask only an open follow-up. Never silently overwrite an immutable run.
- If no answer has been given, record an empty or cancelled session **only when useful or requested**; do not invent answers, scores or improvements.
- Do not require the user to confirm `stop` a second time. The stop command itself authorizes saving the session to the previously confirmed workspace. If saving fails, provide the full report and clearly identify what was not persisted.
- A stop command must take priority over the normal "one question at a time" coaching loop. Do not ask another interview question after receiving it.

## Resume and concurrency

Do not assume that a new chat is a continuation of an in-progress interview simply because a targeted job exists. Check for a persisted `paused` or `in_progress` checkpoint, explain it, and offer "Fortsetzen / Neu beginnen". Do not infer a completed run from an empty runs directory. Separate session completion from job preparation state.

For local persistence, implement pause and stop via the transaction protocol in `storage.md`: retain the original state hash, save a new immutable run with explicit lifecycle status and cumulative answered/planned counts, and verify success. Resume only an explicitly selected `paused` checkpoint of the selected candidate (and job) with `resume --candidate ID --run-id`; it returns transcript and state without changing them. Save a continuation under a new ID with `--resume-from` and the same `--job-id`. Never mark an unfinished known plan completed or treat a stopped run as a resumable pause. If the user chose **Nicht speichern**, give only the in-chat summary and invoke no workspace CLI commands.
