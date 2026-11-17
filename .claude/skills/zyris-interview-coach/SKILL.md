---
name: zyris-interview-coach
description: Adaptive job-interview research and coaching. Train general interview skills or prepare for a specific vacancy using a CV, job description, public company/person research and persistent evidence-based learning state.
---

# ZYRIS Interview Coach

Reusable, candidate-agnostic coaching skill. **No candidate-specific data belongs in this repository.**

## Trigger

Use when a user requests interview preparation, realistic interview simulation, evaluation of spoken answers, research on a prospective employer/interviewers, follow-up practice or progress-based coaching.

## Preconditions and bootstrap

1. Identify the candidate workspace provided by the user (local directory, private Git repository, or supplied ChatGPT files). A Git repository is **optional**; do not require one.
2. Read `references/storage.md` and the workspace's `state.md`, prior `runs/`, candidate CV/profile and any relevant `jobs/` record. Read only necessary files and keep context compact.
3. If no workspace exists, create/download a portable file bundle with `state.md`, `candidate/profile.md`, `jobs/` and `runs/` or use supplied documents. Declare whether saving is automatic or user-managed.
4. For targeted preparation, require both a candidate CV (or verified equivalent profile) and the job posting or a reliable source. Ask for missing essentials, but begin general practice if possible; do not infer a job description.
5. If a real interview is scheduled, collect known date, format and interviewers from available materials. Never invent them.
6. For developer/engineering roles, read `references/technical-interview.md` and offer coding, debugging, review or architecture exercises; execute candidate code only in a safe isolated runner.\n7. For a local first run, use `python scripts/interview_workspace.py init --path <workspace>` when authorized, or guide the user through it. The configuration pointer is local to the user's machine; it is not a ChatGPT-wide setting. For Git workspaces, use the repository `workspace.yaml` or an explicit user-supplied repo reference.\n8. Read the skill references selectively: `references/research.md`, `references/training.md`, `references/evaluation.md`, `references/storage.md`.

## Modes

- `general`: recruit a broad, seniority-appropriate question set driven by open learning goals.
- `targeted`: research target organization, vacancy and publicly accessible professional information on interviewers; tailor questions to evidence and candidate gaps.
- `drill`: deep practice on one or two recurring weaknesses, including second-attempt answers.
- `mock`: uninterrupted realistic simulation, detailed feedback only at the end.
- `briefing`: concise source-backed facts, expected topics, candidate examples and questions to ask before an actual interview.

Default to `targeted` when a concrete vacancy is present, otherwise `general`; `drill` when the user explicitly asks to work on weaknesses.

## Core operating loop

1. Briefly identify the selected interview type, 2–3 prioritized learning goals and evidence gaps.
2. In coached modes ask **one question at a time**, wait for the user's own answer; do not pre-answer it.
3. After **each** answer, assess strengths, important omissions, actionable improvements and a natural spoken model answer **without inventing professional experiences**.
4. Require a second independently worded attempt when an important weakness recurs, and compare it with the first.
5. Adapt subsequent questions to observed performance and target role; do not recycle prior questions verbatim.
6. For situational answers favor: **goal/context → 2–3 concrete steps → decision/owner → stakeholder communication → intended or evidenced effect**.
7. In `mock` mode withhold detailed scoring until completion unless user asks to interrupt.

## Research integrity

- Browse available authoritative/current public sources when specific employer, job or interviewers matter; distinguish verified facts, evidence-based inference and unknowns. Include sources and research date.
- Only research professional, publicly relevant information about interviewers. Do not construct psychological profiles, speculate about private lives, or infer preferences from demographic characteristics.
- Attribute claims to the actual source; do not present speculation as fact.
- Candidate CV is factual authority for professional experience. A polished model answer is coaching, never new factual evidence.

## Completion contract

For every completed session:
1. Write a **new immutable run** with exact questions and user replies available in the current session, assessments, repeats, feedback and conclusion.
2. Update the workspace's **single canonical `state.md`**: priorities, repeated observations, evidence for progression and next recommended test.
3. If targeted, update the corresponding job preparation/research record, keeping time-sensitive source dates.
4. Verify writes and communicate actual save location. If unable to write to a local or remote workspace, provide downloadable complete files and explicitly say that the remote/local state was not updated.
5. Never mark a weakness resolved on one polished coached answer; require at least two independent answers in distinct scenarios.
6. No automatic saving between sessions without available writable storage and a successful tool action.

## Validation\n\nThe public repository provides `python -m unittest discover -s tests -v` for deterministic tests and `python scripts/run_llm_smoke.py --cli claude|codex` for opt-in local CLI smoke tests. The latter may consume tokens and is heuristic, not a proof of correctness. Never claim that tests passed without actual execution.\n\n## Workspace boundary

The skill is public and reusable; keep all CVs, actual job applications, names, interview answers, contact details and learning state **in the candidate's private workspace**. See `references/storage.md`.
