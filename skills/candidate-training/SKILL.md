---
name: candidate-training
description: General interview training for one selected candidate — questions aligned to the candidate's skills, experience, role/seniority and goals; one question per turn, role-relative evaluation, adaptive repeats, mock feedback at the end, each saved session an immutable run, learning state updated for that candidate only.
---

# candidate-training

Read `../_shared/references/candidate-selection.md`, `training.md`, `followup.md`, `evaluation.md`, `session-control.md`, `runtime.md`, `storage.md` (all in `../_shared/references/`). Interface language and interview language are separate; load preferences first.

## Flow

1. A missing storage statement in the chat is not a missing storage decision: unless the user explicitly chose **Nicht speichern**, check `project-show --project PROJECT` first (also when question and answer are supplied in the same message); only its result sends you to setup. Select the candidate (reuse a unique one, ask on ambiguity, never mix candidates). Missing/incomplete/unconfirmed profile → say so clearly; offer completion via `candidate-create`. General practice may start with a draft profile, but only on what the candidate states in the conversation: draft statements are not used as established facts until the user confirms them.
2. Load `status` (state + `state_sha256`), `profile.md` and relevant earlier runs of **this** candidate. Choose mode (`general`, `drill`, `mock`, `briefing`) and 2–3 learning goals from skills, experience, role/seniority and goals.
3. Use the candidate default `interview_language` from `status`; if unconfirmed, ask and save it via `set-interview-language --candidate ID --language TAG` before interview questions. Keep feedback in the interface language. Ask **one** question; wait for the candidate's own answer. Then apply `followup.md`: if an essential requirement is open, ask ONE concrete follow-up on the same main question — one answer task, exactly one question mark, never a second question (also none after "Und wie …"); "Meinen Sie A oder B?" is one task and fine; no hints or rating before it; STOP first. Once the block is closed evaluate the actual answer, first answer and additions apart: **Gesamtbewertung x/10**, fitting criteria, concrete strengths and improvements. State only what the candidate said: no invented habits or contrasts ("von Anfang an", "statt erst …"), no "fehlt" for stated things, no deduction for an example the question did not ask for. A better wording may only use facts the candidate gave. Invite a repeat when it adds value; adapt the next question to the gaps. In `mock` give feedback only at the end.
4. `stop`: end immediately, no second confirmation, finish `stopped_early`; the closing answer never promises to resume an open follow-up (only `pause` keeps a checkpoint). `pause`: checkpoint. Save every session (also partial) as its own immutable run via `finish` with the dialogue record (`--dialogue-file`; main questions, follow-ups and retries counted separately); continuations use a new run ID with `--resume-from`.
5. Progress counts only independent candidate answers. Model answers are never evidence. improving = two spontaneous successful answers in different scenarios; stable = confirmed in a later run without coaching.
6. Update `state.md` of the selected candidate only. Report the real location. Save errors: show them, offer recovery or a new storage choice, never claim success.

## Nicht speichern

Everything stays in the conversation (same follow-up dialogue, no dialogue record); several candidate contexts may be kept apart by label. No runtime call, no file, no export; `stop` gives an in-chat summary. Do not promise it will be available in a later chat.
