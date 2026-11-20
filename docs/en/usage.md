# Using the coach

[Deutsch](../de/usage.md) | [English](./usage.md)

[Home](../../README.en.md) · [Documentation](README.md) · [Install](installation.md) · [Use](usage.md) · [Examples](screens.md) · [FAQ](faq.md) · [Storage](storage.md) · [Development](development.md)

## Entry points per host

All capabilities live in five skills of the same plugin. Natural language works in both hosts ("create a candidate", "prepare the ACME job"). Host-specific invocations are additionally documented:

| Task | Skill | Claude Code | Codex |
|---|---|---|---|
| Setup, status, routing | `interview-coach` | `/interview-coach:interview-coach setup` | `$interview-coach` or the skill picker |
| Create a candidate | `candidate-create` | `/interview-coach:candidate-create` | `$candidate-create` |
| General training | `candidate-training` | `/interview-coach:candidate-training` | `$candidate-training` |
| Prepare a job | `job-create` | `/interview-coach:job-create` | `$job-create` |
| Train for a saved job | `job-training` | `/interview-coach:job-training` | `$job-training` |

The spellings follow each host's documentation and are **not** proven by isolated host runs in this repository (see [acceptance](../acceptance.md)). A native `:job-create` command without host support is not claimed. There is no automatic activation when a project opens: setup starts on first use or on an explicit `setup`.

## 1. Set up

> Start interview-coach setup. Use English.

The coach offers exactly three storage options: **Local**, **Git** (private GitHub/GitLab repository), **Do not save**. It then asks for the path or repository and confirms the target. With Git, commits and pushes in the chosen repository are part of saving. Details: [Storage](storage.md).

## 2. Create a candidate (`candidate-create`)

Ask for the name → unique ID → "Is there a CV?".

- **With a CV** (PDF, DOCX, Markdown): provide the file. The original stays byte-identical; a Markdown transfer and a profile are created. Gaps (images, unreadable pages, missing text layer) are disclosed and partial imports are not reported as done. If a tool is missing (e.g. for PDF: `pdftotext`, `mutool` or Python `pypdf`), the coach names exactly what is missing; nothing is installed and nothing invented.
- **Without a CV**: the coach asks one question at a time (experience, education, skills, projects, goals), writes a CV draft marked as a draft plus a profile, and has you confirm the facts. Only then do they count as a verified basis; a draft can be saved and shown but is not reliable evidence. The job-specific comparison and profile-based training wait for your confirmation (posting intake, company research and general training do not).

At the end you see the result, open points and the actual storage location. A project can hold several candidates, including equal names; the coach asks when a choice is ambiguous.

## 3. General training (`candidate-training`)

Choose the candidate → profile, learning state and earlier runs are loaded → one question per turn, aligned with skills, experience, role and goals. You get an **overall score x/10**, fitting criteria, strengths and improvements; wording suggestions use only facts you provided. Every saved session is its own immutable run, and the learning state changes only for the chosen candidate.

## 4. Prepare a job (`job-create`)

Choose the candidate → job link or upload (a link needs its retrieval date; if it is unreachable you provide text/upload) → company (if unclear) → known interview participants ("unknown" is allowed and blocks nothing) → public professional research with sources and dates, namesakes are clarified before attribution, no psychological profiles → requirement ↔ evidence/gap comparison → saved preparation with topics and open questions. A job belongs to one candidate and is reusable across trainings.

## 5. Train for a job (`job-training`)

Choose candidate and job → existing research is reused, time-sensitive facts refreshed when needed → questions and evaluation follow requirements, seniority and gaps → each session is its own run with candidate and job assignment. The cross-job learning state stays separate from job-specific fit gaps.

## Modes and controls

| Mode | Purpose | Feedback |
|---|---|---|
| `general` | General training | after each answer |
| `targeted` | Saved job | after each answer |
| `drill` | One learning gap, second attempt | focused |
| `mock` | Uninterrupted simulation | at the end |
| `briefing` | Compact preparation | no answer scoring |

- `stop` / `end` ends immediately without a second confirmation; for a stored candidate a partial run (`stopped_early`) is saved.
- `pause` saves a checkpoint; continuing happens under a new run ID, only for the same candidate and job.
- Interface and interview language are configurable separately.
- Progress: only independent answers count; `improving` after two spontaneous successes in different scenarios, `stable` only after confirmation in a later run without coaching. Model answers are not evidence of competence.

Technical roles can practice coding, debugging, review and system design; code is executed only in a safe, authorized isolation, otherwise it is evaluated as "not executed".
