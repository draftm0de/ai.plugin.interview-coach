# Research contract

Applies to targeted interviews and briefing mode.

## Inputs

Confirmed candidate profile (a draft is not reliable evidence; needed for the candidate comparison only), job advertisement or original source URL, company name/website, known interviewers with role and optionally interview date. If mandatory evidence is missing, label it and request only essential clarification.

## Reuse and interviewer intake

When a concrete employer/position is known, ask: "Mit wem führst du das Bewerbungsgespräch? Kennst du Namen und Funktionen?" Skip the question if already answered. If unknown, continue with employer and role research; do not invent identities or make interviewer names mandatory for proceeding.

Before researching, load the candidate's existing job record (`job-show`) and reuse the original vacancy, source-backed employer facts, known interviewers, research history and previously identified question themes. Avoid redundant searches. Refresh only time-sensitive, missing or uncertain details; distinguish previously verified information from newly verified facts.

Store interviewer names, verified professional roles and publicly relevant professional background, source URLs, retrieval dates, open uncertainties and **plausible role-based question perspectives** in the private job research record. Namesakes must be disambiguated with the user before anything is attributed. A recruiter's remit or technical manager's responsibilities can inform likely question themes, but do not claim knowledge of their actual intentions or personality.

## Collection order

1. Job ad: exact responsibilities, expectations, must-haves/nice-to-haves, reporting line and salary/locations **only if explicitly published**.
2. Employer: official site, annual reports, products, markets, company structure, strategy, job-related technology and operating model.
3. Recent developments: official announcements and credible current reporting, dated. Check publication versus event dates.
4. Interviewer: publicly available professional title, scope, articles, talks and relevant career history. Do not infer a person's values, interview style or personality from their age, photo or private information.
5. Crosswalk: map each material vacancy requirement to **direct evidence** (the full requirement incl. duration/scope is evidenced), **transferable adjacent evidence**, **unsupported** (not documented = to clarify, not proven absent) or a confirmed **gap** (candidate confirmed it is missing); classes as defined in `job-preparation.md` step 7. Recognize candidate preferences and real dealbreakers.

## Durable job preparation

Use one stable job identifier (`j-...`, owned by exactly one candidate) for repeated training on the same vacancy. The job is a reusable knowledge base made of append-only snapshots in `jobs/<job-id>/`:

- `postings/NNN.md` (+ original upload): posting text, company, role, source URL, retrieval date, known interview date/format
- `research/NNN.md`: sourced employer, role and interviewer findings, dates, confidence and changes
- `match/NNN.md`: CV-to-role comparison with direct/transferable/unsupported/confirmed-gap evidence (see `job-preparation.md` step 7) — the job-specific fit gaps live here
- `preparation/NNN.md`: relevant examples, likely question themes, interviewer-role perspectives, open questions, preparation priorities

On later sessions read the latest snapshots first and add a new snapshot only for what changed. Earlier snapshots and the original posting are never removed. Training results and answer quality belong in immutable `runs/` and the candidate's `state.md`, not in employer facts.

## Artifact

Save a research snapshot (`job-add --kind research`, retrieval date mandatory) with: date, source URL and retrieval date, verified fact, implications for likely interview questions, uncertainties, open questions, and a compact briefing. Use explicit confidence levels `verified | inferred | unknown`. Never fabricate links.

## Questions generated

Prioritize role-critical challenges and candidate weaknesses. A hypothetical scenario may be plausible, but must not be presented as an actual company incident or as an interviewer's personal opinion.

Before the real interview, refresh current facts where freshness matters. Cached research is not automatically current.
