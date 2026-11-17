# ZYRIS Interview Coach

## Quick install (recommended)

Clone this public repository and run the interactive installer:

```bash
git clone https://github.com/draftm0de/zyris.skill.interview-coach.git
cd zyris.skill.interview-coach
bash install.sh
```

Choose **Claude Code**, **Codex CLI**, **ChatGPT ZIP**, or **all**. For automation use `bash install.sh claude --yes`, `bash install.sh codex --yes`, or `bash install.sh chatgpt`. Existing CLI installations require confirmation before replacement (or explicit `--yes`). Only public skill files are installed; no private CV, state or runs are accessed. The ChatGPT target creates a ZIP for manual import where supported, not an automatic installation.

After installation, start `/zyris-interview-coach setup` in Claude Code. For ChatGPT, first import the skill where supported, then request `zyris-interview-coach setup`.


Portable interview coaching skill with targeted research on a vacancy, employer and publicly documented professional interviewers; evidence-based interview practice; and persistence of learning progress.

## Canonical skill source

**[.claude/skills/zyris-interview-coach/SKILL.md](.claude/skills/zyris-interview-coach/SKILL.md)** is the single authoritative implementation. All supporting references are in its own `references/` directory.

## Claude Code

**Project-local:** Clone the repository and launch Claude Code from its root. Claude Code discovers the skill in `.claude/skills/zyris-interview-coach/` and can invoke `/zyris-interview-coach`.

**Globally installed:** Copy the entire skill directory (including `references/`) to:

```text
~/.claude/skills/zyris-interview-coach/
  SKILL.md
  references/
```

Use `bash install.sh claude` from the cloned repository.\n\nA repository containing `.claude/skills/` does not automatically install the skill in unrelated projects. For global availability, use the user-level directory.

## ChatGPT / Codex / other agents

Use the **same skill folder** as the source for import or attachment. ChatGPT availability depends on the specific Skills installation capability in the client. For Codex project discovery, copy or link the folder into `.agents/skills/zyris-interview-coach/` (Codex supports symlinked skill directories). <https://learn.chatgpt.com/docs/build-skills>

Do not maintain duplicate instruction copies across clients; copy or link from the canonical directory.

## Private workspace

No CV, job ad, interviewer research or user training history belongs here. A separate private workspace (for example, your own private repository) holds `state.md`, `candidate/profile.md`, `jobs/` and immutable `runs/`. It can alternatively be a local folder or supported ChatGPT project files.

## How to start

> Use the zyris-interview-coach skill. My persistent workspace is <your private workspace path or repository>. Read my CV/profile, state.md, prior runs and target vacancy. Research the employer and known interviewers, then start an adaptive targeted interview. After completion write a run report and update state.md.

## Contracts

- [Research](.claude/skills/zyris-interview-coach/references/research.md)
- [Training](.claude/skills/zyris-interview-coach/references/training.md)
- [Evaluation](.claude/skills/zyris-interview-coach/references/evaluation.md)
- [Storage](.claude/skills/zyris-interview-coach/references/storage.md)

## First-time setup and storage

### Local workspace (no Git required)

Requires Python 3.10+ and a writable local directory:

```bash
python3 scripts/interview_workspace.py init --path ~/interview-workspace
python3 scripts/interview_workspace.py status
python3 scripts/interview_workspace.py validate
```

The local pointer is stored in `~/.config/zyris/zyris-interview-coach/config.json` (or `$XDG_CONFIG_HOME/zyris/zyris-interview-coach/config.json`). The `init` command preserves existing files. To intentionally change workspace, use `init --path NEW_PATH --force`. This configuration is local to the machine and **does not synchronize to ChatGPT**.

At the end of a run, prepare a complete Markdown run file and updated state file, then save both:

```bash
python3 scripts/interview_workspace.py finish \
  --run-id 2026-11-17-example \
  --run-file /path/to/new-run.md \
  --state-file /path/to/new-state.md
```

This is not an atomic transaction across two files: if the state update fails after the run is saved, the command reports partial failure for manual reconciliation. A second run with the same ID is refused.

### Private GitHub / GitLab workspace

Use the agent's authenticated Git connector or a separately authenticated Git CLI to read the private workspace manifest, runs and state. Git writes must be explicitly performed and verified. The Python workspace CLI currently **does not** implement remote Git storage. Do not put private candidate data in this public repository.

### ChatGPT with supplied files

Provide the CV, vacancy and workspace files as attachments or Project files. Where no writable persistent file interface exists, the agent must return complete updated files for the user to save. An attached file is not automatically a persistent writeable state.

## Technical and coding interviews

The skill supports developer/engineering role question types in [technical-interview.md](.claude/skills/zyris-interview-coach/references/technical-interview.md): coding, debugging, code review, system design, SQL, testing and reliability. Execute untrusted candidate code only in an isolated sandbox; if no runner is available, mark review as static and unverified by execution.

## Testing

**Deterministic checks (no model calls):**

```bash
python3 -m unittest discover -s tests -v
# or: python3 -m pip install pytest && python3 -m pytest -q
```

**Optional local model smoke tests (may incur usage costs):**

```bash
python3 scripts/run_llm_smoke.py --cli claude
python3 scripts/run_llm_smoke.py --cli codex
```

Prerequisites: installed and authenticated `claude` or `codex` CLI, suitable permissions and model quota. The smoke harness uses `claude -p` and `codex exec` with read-only sandbox where supported. It only tests selected output heuristics, not complete interview quality or storage integration. Run manually, review outputs and avoid placing private CVs in public fixtures. CLI flags may change with installed versions; check `claude --help` / `codex exec --help`.

**CI:** GitHub Actions runs only deterministic Python tests on changes to skill/tests/scripts. No automatic paid model calls.

## Verification checklist

1. Unit tests pass locally and in GitHub Actions.
2. Local `init/status/validate/finish` succeeds in a disposable directory.
3. Claude and Codex CLI smoke tests are run manually and reviewed.
4. End-to-end trial uses a **fictional** CV and vacancy; check research claims, question quality, repeated answers, immutable run and state update.
5. Private workspace is used for real candidate interviews; no private artifacts leak into this public repository.


### Guided setup

In Claude Code after installation, invoke `/zyris-interview-coach setup`. In ChatGPT with the skill instructions available, say **"zyris-interview-coach setup"**. The coach asks conversationally for storage (local, private Git or ChatGPT files), verifies authorized access, requests your current CV and optionally a job posting, then reuses or initializes the state. It does **not** overwrite existing data.

Local-only command alternative: `python3 scripts/interview_workspace.py init --path ~/interview-workspace`.

See [setup contract](.claude/skills/zyris-interview-coach/references/setup.md). LinkedIn import is **planned**, not implemented; a user-authorized profile export may later supplement an approved CV.
