# Interview Coach

Portable interview coaching skill with targeted research on a vacancy, employer and publicly documented professional interviewers; evidence-based interview practice; and persistence of learning progress.

## Canonical skill source

**[.claude/skills/interview-coach/SKILL.md](.claude/skills/interview-coach/SKILL.md)** is the single authoritative implementation. All supporting references are in its own `references/` directory.

## Claude Code

**Project-local:** Clone the repository and launch Claude Code from its root. Claude Code discovers the skill in `.claude/skills/interview-coach/` and can invoke `/interview-coach`.

**Globally installed:** Copy the entire skill directory (including `references/`) to:

```text
~/.claude/skills/interview-coach/
  SKILL.md
  references/
```

For example (run from a clone of this repository):

```bash
mkdir -p ~/.claude/skills
cp -R .claude/skills/interview-coach ~/.claude/skills/
```

A repository containing `.claude/skills/` does not automatically install the skill in unrelated projects. For global availability, use the user-level directory.

## ChatGPT / Codex / other agents

Use the **same skill folder** as the source for import or attachment. ChatGPT availability depends on the specific Skills installation capability in the client. For Codex project discovery, copy or link the folder into `.agents/skills/interview-coach/` (Codex supports symlinked skill directories). <https://learn.chatgpt.com/docs/build-skills>

Do not maintain duplicate instruction copies across clients; copy or link from the canonical directory.

## Private workspace

No CV, job ad, interviewer research or user training history belongs here. A separate workspace such as `draftm0de/private.job-interview` holds `state.md`, `candidate/profile.md`, `jobs/` and immutable `runs/`. It can alternatively be a local folder or supported ChatGPT project files.

## How to start

> Use the interview-coach skill. My persistent workspace is draftm0de/private.job-interview. Read my CV/profile, state.md, prior runs and target vacancy. Research the employer and known interviewers, then start an adaptive targeted interview. After completion write a run report and update state.md.

## Contracts

- [Research](.claude/skills/interview-coach/references/research.md)
- [Training](.claude/skills/interview-coach/references/training.md)
- [Evaluation](.claude/skills/interview-coach/references/evaluation.md)
- [Storage](.claude/skills/interview-coach/references/storage.md)
