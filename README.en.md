# Interview Coach

[![Validate interview coach](https://github.com/draftm0de/ai.plugin.interview-coach/actions/workflows/validate.yml/badge.svg)](https://github.com/draftm0de/ai.plugin.interview-coach/actions/workflows/validate.yml)
[Deutsch](README.md) | [English](README.en.md)

<img src="docs/assets/zyris-icon.png" width="48" alt="ZYRIS documentation icon">

Practice job interviews with role-specific questions, concrete feedback and evidence-based learning progress in **Claude Code** and **Codex**. One project manages several candidates, each with their own profile, CV, jobs, runs and learning state.

**[Install](docs/en/installation.md) · [Usage](docs/en/usage.md) · [Storage](docs/en/storage.md) · [Examples](docs/en/screens.md) · [FAQ](docs/en/faq.md) · [Documentation](docs/en/README.md) · [Acceptance](docs/acceptance.md)**

**Installation:** [Claude Code](docs/en/installation.md#claude-code) · [Codex](docs/en/installation.md#codex). Marketplace: `https://github.com/draftm0de/ai.plugins`. The publication state of this extension is not evidenced; host and live acceptance are open ([acceptance](docs/acceptance.md)).

## Who it is for

Use this when you want to prepare for a specific vacancy, practise clearer answers, rehearse a realistic interview or review what to improve before the next conversation. Technical roles can include coding, debugging, code review and system design exercises.

The coach adapts questions and criteria to your role and seniority. It distinguishes your own answers from suggested wording and does not invent professional experience or achievements.

## What it looks like

![Fictional coaching example: original answer, revised answer and stopping without saving](docs/assets/en/coaching-preview.svg)

*English translation of rendered excerpts from a fictional Codex CLI test, not a screenshot of Claude or ChatGPT. Scores illustrate one response, not a guaranteed result. [Read the example and its provenance](docs/en/screens.md).*

1. Set up: choose a storage type – exactly two options: **Local**, **Do not save** – then the local path.
2. Create a candidate (`candidate-create`): import a CV (PDF, DOCX, Markdown) or build a profile without one.
3. Train generally (`candidate-training`), or prepare a job (`job-create`) and train for it (`job-training`).
4. In coached modes answer one question at a time; receive an overall score, criteria, strengths and improvements.
5. Say `stop` whenever you want to finish.

## Capabilities and modes

| Mode | Use it for | Example request |
|---|---|---|
| `general` | Broad interview practice | “Practise general interview questions for a senior developer.” |
| `targeted` | A specific role, employer and interview | “Use my CV and this vacancy to prepare a targeted interview.” |
| `drill` | One recurring weakness | “Help me make my answers more concrete.” |
| `mock` | An uninterrupted simulation | “Run a mock interview; give feedback at the end.” |
| `briefing` | A concise preparation summary | “Summarize what I should review before this interview.” |

Research uses available public professional sources and marks uncertainty. Employer/interviewer research requires browsing access. [Usage guide](docs/en/usage.md).

## Quick start

Open the [installation guide](docs/en/installation.md). Then use `/interview-coach:interview-coach setup` in Claude Code or `$interview-coach` in Codex – or simply write "Start interview-coach setup". Setup runs on first use or on `setup`; no automatic activation when a project opens is claimed.

| Skill | Purpose | Claude Code | Codex |
|---|---|---|---|
| `interview-coach` | Entry point, setup | `/interview-coach:interview-coach` | `$interview-coach` |
| `candidate-create` | Create a candidate | `/interview-coach:candidate-create` | `$candidate-create` |
| `candidate-training` | General training | `/interview-coach:candidate-training` | `$candidate-training` |
| `job-create` | Prepare a job | `/interview-coach:job-create` | `$job-create` |
| `job-training` | Train for a job | `/interview-coach:job-training` | `$job-training` |

The invocation spellings follow host documentation; a native `:job-create` command is not claimed. See [usage](docs/en/usage.md).

| Control | Result |
|---|---|
| `stop` / `end` | End questioning immediately; summarize the answers given |
| `pause` | Save a resumable checkpoint (only with a chosen storage) |
| **Do not save** (`Nicht speichern`) | Nothing is persisted: no files, pointers, exports or learning state |

## Storage and privacy

Exactly two options: **Local** (a directory you name), **Do not save**. "Manage files yourself" no longer exists. Private data lives outside the installed plugin. No tokens are requested. See [storage, formats and recovery](docs/en/storage.md).

## Project status

This MVP uses versionless plugin manifests and repository import through Draftmode AI Plugins. There is no customer portal, payment system, license server or claimed listing in an additional official plugin directory.

Local persistence, extraction and packaging have deterministic tests. Model scenarios use fictional data and heuristic checks. Host acceptance for Claude Code and Codex with isolated profiles is open; results and gaps are in the [acceptance matrix](docs/acceptance.md).

License: [MIT](LICENSE). The earlier [release evidence](docs/en/release-evidence.md) is history.

## Development

The [test guide](tests/README.md) describes the shared layout by test type. `make test` runs unit, integration and contract tests; native host and model tests are started separately.


```bash
make test          # deterministic unit, integration and contract tests; no model calls
make check-plugin  # validate versionless host manifests
```

Tests require no additional Python packages such as pytest. Management tools require Git and Python 3.10+; the runtime requires Python 3.10+. PDF import needs `pdftotext`, `mutool` or `pypdf` (never installed automatically). Make is optional. See [development and testing](docs/en/development.md) for model tests and repository boundaries.

The five skills under [skills/](skills/) and the shared runtime under [skills/_shared/](skills/_shared/) define the behavior; [SCOPE.md](SCOPE.md) is authoritative. User documentation lives in [docs/](docs/en/README.md).

Publisher: **draftmode** · [draftmode.io](https://draftmode.io) · Author: **Peter Fux**.

Documentation prepared with Plugin Manager.
