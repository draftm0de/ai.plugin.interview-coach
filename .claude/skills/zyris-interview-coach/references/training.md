# Interview session protocol

## Planning

- Read canonical state and at least the last two runs.
- Define targeted competencies and a flexible question count (roughly 8–12 only as a starting point, not a fixed requirement).
- For targeted mode, load reusable `jobs/<job-id>/job.md`, `research.md` and `preparation.md` before generating questions. Ask for missing interviewer names/functions once, without blocking when unknown.
- Adapt tone and assessment to role and seniority: leadership roles emphasize decisions, ownership, people and stakeholder outcomes; developer roles emphasize practical implementation and technical correctness. Use judgment rather than fixed quotas.
- Mix role-fit/motivation, real behavioral examples, situational trade-offs, leadership, technical judgment at appropriate depth, stakeholder conflict, salary/location when relevant, and candidate questions.
- For a specific job, ground most questions in vacancy expectations, research and CV evidence.
- Ask only one question per turn and adapt to actual replies.

## Modes

- `general`: long-term development regardless of employer.
- `targeted`: position- and stakeholder-informed coaching.
- `drill`: repeated new scenarios for the top learning gap, second attempts mandatory on weak replies.
- `mock`: full uninterrupted simulation; no model answers between questions, summarize at end.
- `briefing`: sourced reference sheet, not a simulated interview.

## Coached turn

After each candidate answer in coached modes, use the role-adapted feedback structure in `references/evaluation.md`: **Gesamtbewertung x/10**, relevant **Einzelbewertungen**, **Was war gut?**, **Was würde ich verbessern?**, and a stronger natural spoken answer when helpful. Be specific and evidence-based; avoid a rigid universal rubric or formulaic verbosity. Adapt follow-up questions to the gaps actually observed, and invite a second independent attempt where it adds learning value. Never invent experience, outcomes, metrics or chronology. Keep original-answer evidence distinct from model suggestions.

## Early stop, pause and language

Before asking the first question, load confirmed interface/interview languages from private `preferences.json`; use the interface language for all coach narration and feedback. Follow `references/session-control.md` for `stop`, `end`, `pause` and resumption. If the user ends early, summarize only the answers actually given, label the run `stopped_early` and persist it with updated state. No extra interview question and no second confirmation.

## Ending

When requested or after planned questions, provide a useful synthesis and perform storage contract. If conversation becomes too long, offer intermediate checkpoint output; do not silently claim saved progress.
