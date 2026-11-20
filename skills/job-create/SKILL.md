---
name: job-create
description: Prepare a job for one selected candidate — secure the posting and its origin, ask for the company and interview participants (unknown is fine), research public company and professional person information with sources and dates, compare requirements with the candidate's evidence, and save reusable preparation.
---

# job-create

Read (Read tool) `../_shared/references/job-preparation.md`, `research.md`, `candidate-selection.md`, `runtime.md`, `storage.md`, `setup.md` (in `../_shared/references/`). One question per turn; interface language from preferences.

## Flow

1. Storage decision missing → setup. Select the candidate unambiguously. Draft or missing profile → say so: steps 2–4 (posting, company, participants, public research) continue, but the candidate comparison in step 5 waits until the user has confirmed the profile facts (a draft is not reliable evidence; the label "unbestätigt" does not replace confirmation).
2. Ask for the job link or upload. Secure the posting text and origin with `job-create` (link needs retrieval date; uploads keep original bytes). Inaccessible link → ask for pasted text or a file; never invent content.
3. Company missing or ambiguous → ask. Ask who will conduct the interview (names, functions). "Unbekannt" is accepted (`--participants-status unknown`) and blocks nothing.
4. Research public, professional information about company and people: position and evidenced expertise. Clarify namesakes **before** attributing. No psychological profiles, private details or unevidenced skills. Separate **Fakten**, **Schlussfolgerungen**, **Unbekannt**. Save with sources and retrieval date (`job-add --kind research`).
5. With a confirmed profile, compare posting requirements with the candidate's evidence and gaps (`--kind match`; refused by the runtime otherwise), applying the evidence classes of `job-preparation.md` step 7: *direkt belegt* only when the requirement itself (incl. duration/scope) is evidenced; role years plus a listed skill do not prove the same years with that skill; not mentioned means *unbelegt/zu klären*, never "fehlende Erfahrung"; *bestätigte Lücke* only after the candidate confirmed it; keep capability gaps and evidence gaps apart. Then topics and open questions (`--kind preparation`); a prioritized unsupported topic is justified as Klärungsbedarf. Profile, match, preparation and the final answer must use the same class per requirement. Updates add snapshots; the original posting and earlier evidence remain.
6. Report: job ID, saved artifacts, open points in two separate groups — job record gaps (`job-show` → `open_points`: company missing, participants pending/unverified) and research gaps (still unresearched company or people, unknown interviewers, no web research, everything under **Unbekannt**) — and location (Git: `git-publish`, **remote gespeichert** only after success). Offer `job-training`.

## Nicht speichern

Do all research and comparison in the conversation, label each job, call no runtime command, write no file; say that nothing persists.

## Guardrails

A completely created job is not a completely researched job: an empty `open_points` list covers only the required job record fields. Never say "ohne offene Punkte" or "fully researched" while the saved research names pending company research, unknown or unverified interviewers or skipped web research.


An interrupted job creation is an unusable draft (`creating`) — never report it as ready. A job belongs to exactly one candidate; never reuse it for another.
