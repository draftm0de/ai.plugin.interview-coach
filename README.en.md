# ZYRIS Interview Coach

[![Validate interview coach](https://github.com/draftm0de/zyris.skill.interview-coach/actions/workflows/validate.yml/badge.svg)](https://github.com/draftm0de/zyris.skill.interview-coach/actions/workflows/validate.yml)
[Deutsch](README.md) | [English](README.en.md)

<img src="docs/assets/zyris-icon.png" width="48" alt="ZYRIS documentation icon">

Practice job interviews with role-specific questions, concrete feedback and evidence-based learning progress in Claude, ChatGPT or Codex.

**[Install](docs/en/installation.md) · [Usage](docs/en/usage.md) · [Examples](docs/en/screens.md) · [FAQ](docs/en/faq.md) · [Documentation](docs/en/README.md)**

## Who it is for

Use this when you want to prepare for a specific vacancy, practise clearer answers, rehearse a realistic interview or review what to improve before the next conversation. Technical roles can include coding, debugging, code review and system design exercises.

The coach adapts questions and criteria to your role and seniority. It distinguishes your own answers from suggested wording and does not invent professional experience or achievements.

## What it looks like

![Fictional coaching example: original answer, revised answer and stopping without saving](docs/assets/en/coaching-preview.svg)

*English translation of rendered excerpts from a fictional Codex CLI test, not a screenshot of Claude or ChatGPT. Scores illustrate one response, not a guaranteed result. [Read the example and its provenance](docs/en/screens.md).*

1. Choose your language, training goal and whether to save progress.
2. Answer one question at a time in coached modes.
3. Receive an overall score out of 10, relevant criteria, strengths and specific improvements.
4. Try again in your own words; a coached revision is not proof of stable competence.
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

Clone this public repository and choose an installation target:

```bash
git clone https://github.com/draftm0de/zyris.skill.interview-coach.git
cd zyris.skill.interview-coach
bash install.sh install --target claude
```

The installer and Makefile delegate to one manifest-driven plugin helper. Claude Code and Codex use native plugin management (`TARGET=claude` or `TARGET=codex`); ChatGPT uses manual plugin ZIP upload. Existing standalone skill installations are left untouched. Building a ZIP does not install or publish it. See the [platform-specific installation and update guide](docs/en/installation.md).

## Usage

After installation, ask:

> Use zyris-interview-coach and run setup. I want to practise for a Team Lead role. Use English. Do not save anything.

For targeted preparation, provide your approved profile/CV and the job posting privately. Do not add them to this repository. Unknown interviewer names do not prevent training.

| Control | Result |
|---|---|
| `stop` / `beenden` | End questioning immediately; summarize the answers given |
| `pause` | Request a resumable checkpoint when verified storage is available |
| Do not save (`Nicht speichern`) | No skill-managed files, workspace, exports or saved learning state |

In `mock`, feedback is deferred until the end. Platform chat history has separate retention settings.

## Storage and privacy

You can practise without persistence. For learning across sessions, use a separate private workspace and a verified storage adapter. A hosted sandbox or an uploaded attachment does not automatically provide durable cross-chat storage.

The local Python CLI supports `init`, `status`, `finish`, `resume`, `recover`, `validate` and language preferences. It protects immutable runs, checks for stale state and supports recovery after partial writes. See [storage and recovery](docs/en/storage.md) for commands and limitations.

## Project status

This is a public repository MVP with a base version in `plugin.json` and content-derived package versions. There is no customer portal, payment system, license server or published plugin-directory listing established by this repository.

Local persistence and packaging have deterministic tests. CLI model journeys use fictional scenarios and heuristic checks. Native Claude/ChatGPT/Codex platform acceptance remains separate; a passing model test does not prove host UI or storage integration.

License: [MIT](LICENSE). Native installation tests were not repeated for this documentation update.

## Development

Website export from the same sources: `make check-docs-export` and `make export-docs`. See the [development guide](docs/en/development.md).

```bash
make test          # deterministic unit and regression tests; no model calls
make package       # generate three plugin ZIPs and local Claude/Codex marketplaces
```

Optional alternative after installing pytest: `python3 -m pytest -q`. Python 3.10+ is required for packaging and the local workspace CLI. See [development and testing](docs/en/development.md) for model tests and repository boundaries.

The [canonical skill](.claude/skills/zyris-interview-coach/SKILL.md) is the single runtime source. User documentation lives in [docs/](docs/en/README.md).

Publisher: **draftmode** · [draftmode.io](https://draftmode.io) · Author: **Peter Fux**.

Documentation prepared with ZYRIS Skill Documentation.
