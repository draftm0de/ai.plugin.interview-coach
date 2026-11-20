---
name: candidate-create
description: Create a new interview candidate in the current project — ask the name, assign a unique stable ID, import an existing CV (PDF, DOCX, Markdown) or build a profile step by step without one, and show what was saved and where.
---

# candidate-create

Creates a candidate inside the project's storage target. Read `../_shared/references/setup.md` (if no storage decision exists), `../_shared/references/cv-profile.md`, `../_shared/references/runtime.md`, `../_shared/references/storage.md`. Reply in the configured interface language; ask **one question per turn**.

## Flow

1. Storage: no decision yet → complete the shared setup flow (exactly **Lokal**, **Nicht speichern**, target confirmation, then interface-language confirmation) before candidate creation. For Lokal, offer the known project's `interview-data` subfolder with yes/other-folder choices per `setup.md`; do not demand a typed path first or repeat the question.
2. Ask for the candidate's name. Equal names are allowed. Names are data, never file paths. Create with `candidate-create --name` — the runtime assigns the stable ID. Before creating, run `candidate-list`; if the same name exists, ask whether this is the same person (then select that candidate instead) or a different one.
3. Confirm this candidate's default interview language (one question, separate from the name and CV question).
   Offer a sensible proposal and allow other languages, not just German/English. Save via
   `set-interview-language --candidate ID --language TAG`; in Nicht speichern keep it only in this candidate's chat context.
   Then ask: "Gibt es einen Lebenslauf?"
   - **Yes** → request upload or accessible file, `cv-import`, Markdown + profile per `cv-profile.md`. Report extraction status and every warning. Missing extraction capability → say exactly what is missing; nothing is installed or invented. A partial import is not "done".
   - **No** → build the profile with single questions (experience, education, skills, projects, goals); labeled CV draft + profile as `draft`; confirm facts with the user before they count as verified.
4. Report: name and ID, CV/profile status, open points, the real storage location. Nicht speichern: say that nothing was stored and what stays only in this chat.
5. Offer `candidate-training` or `job-create`.

## Guardrails

- Never invent experience; keep source CV, user statements and model wording distinguishable.
- Original CV bytes are kept unchanged; repeated or colliding imports keep earlier sources.
- An interrupted creation leaves an unusable draft marked `creating`; never present it as finished. Use `candidate-recover` to complete it.
- In Nicht speichern mode run no runtime command and write no file.
