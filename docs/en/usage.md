# Using the coach

[Deutsch](../de/usage.md) | [English](./usage.md)

[Home](../../README.en.md) · [Documentation](README.md) · [Install](installation.md) · [Use](usage.md) · [Examples](screens.md) · [FAQ](faq.md) · [Storage](storage.md) · [Development](development.md)

## Set up

After [installation](installation.md), ask:

> Use zyris-interview-coach and run setup. I want to practise for a Team Lead ERP Platform role. Use English and do not save anything.

The coach asks about storage before a path, confirms the interface/interview language and requests relevant profile information. For targeted preparation, supply your approved CV/profile and the job posting privately. Without a CV, general practice remains available; targeted preparation needs an approved profile. Original documents are stored only with permission. Known interviewers are optional; public professional information can help tailor preparation.

## Choose a workflow

| Mode | Example prompt | Feedback |
|---|---|---|
| `general` | “Practise common interview questions for a junior developer.” | After each answer |
| `targeted` | “Prepare me for this vacancy using my CV and the employer's public information.” | After each answer |
| `drill` | “Train decision ownership. Ask me to improve an unclear answer in my own words.” | Focused feedback and comparison |
| `mock` | “Simulate a realistic interview and save the assessment until the end.” | At the end |
| `briefing` | “Summarize verified employer facts, relevant examples and questions I can ask.” | Preparation summary; no answer scoring |

Research requires available browsing tools. Facts, hypotheses and unknowns must remain distinct. Interviewer research is limited to relevant public professional information.

## Understand the output

In coached modes, expect an overall **overall assessment x/10**, relevant individual criteria, supported strengths and concrete improvement suggestions. A natural spoken example is a suggestion, not evidence of your professional experience. Scores are qualitative and role-relative, not hiring probabilities.

A second attempt can show that your answer improved after coaching. It is not an independent demonstration of stable competence. Learning status uses actual candidate answers, distinct scenarios and later confirmation. See the [evaluation contract](../../skills/zyris-interview-coach/references/evaluation.md).

Learning status `improving` requires two spontaneous successful answers in distinct scenarios; `stable` requires confirmation in a later run without coaching. Relevant criteria usually number three to six; the overall score is not a mechanical average. Role-fit gaps remain separate from communication weaknesses.

## Control the session

- Say **stop**, **end**, **beenden** or **abbrechen** to end questioning immediately and receive a summary. With previously verified storage, a partial run is saved as `stopped_early`.
- Say **pause** to request a checkpoint when persistent storage is available. On return, explicitly select the paused session to continue; no past question should silently count as answered.
- Choose **Do not save** (`Nicht speichern`) to keep skill-managed coaching state within the conversation. No workspace, preference, report file or export is automatically created. Platform chat retention is separate.
- Ask to change the interface language or practise in a different interview language; confirm preference changes before persistence.

`finish` ends early while questions remain; after the planned final answer the status is `completed`. Quoted control words inside an answer are not commands. These are conversational controls. The agent must use the available tools and verify saves; saying “saved” is not a successful write. If persistence fails, keep the report and follow [recovery instructions](storage.md).

## Return later

With a verified private workspace, ask the coach to read its state, preferences and prior runs. For a paused local interview, the helper's `resume` command provides the checkpoint and current state; see [storage](storage.md). Stopped/completed runs are history, not resumable checkpoints.

Without persistence, supply the context again. A hosted sandbox, previous chat or uploaded attachment alone is not a verified durable storage adapter.

## Specialized workflows

Ask for coding, debugging, code review, SQL, testing or system-design practice. Candidate code should only execute in an appropriate isolated sandbox. When execution is unavailable, the coach must distinguish static review from tested behavior.

Technical tasks define inputs/outputs, constraints, runtime, timebox and criteria; the reference solution stays hidden until your attempt. Security, CI/CD and operations can also be practised.

Repeated targeted preparation reuses `jobs/<job-id>/job.md`, `research.md` and `preparation.md`, with sources, retrieval dates and `verified | inferred | unknown` confidence. Refresh outdated facts. LinkedIn import is a future option, not an implemented feature.
