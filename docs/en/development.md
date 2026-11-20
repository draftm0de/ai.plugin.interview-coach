# Development and validation

[Deutsch](../de/development.md) | [English](./development.md)

[Home](../../README.en.md) · [Documentation](README.md) · [Install](installation.md) · [Use](usage.md) · [Examples](screens.md) · [FAQ](faq.md) · [Storage](storage.md) · [Development](development.md)

## Source of truth

Five public skills live under `skills/` (`interview-coach`, `candidate-create`, `candidate-training`, `job-create`, `job-training`); `skills/_shared/` holds, without a `SKILL.md`, the shared runtime (`scripts/`: `interview_workspace.py`, `coach_core.py`, `coach_extract.py`, `coach_git.py`) and the shared references (`references/`). Root `scripts/` contains development tooling only. `plugin.json` defines `interview-coach` with display name **Interview Coach**. `make sync-plugin` derives `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`; `make check-plugin` detects drift. All manifests remain versionless. The shared marketplace lives in the separate `ai.plugins` repository; this plugin has no catalog of its own.

Management tools require Git and Python 3.10+; Make is an optional convenience wrapper. No additional Python packages. The host CLI is needed only for automatic local installation/updates and explicitly selected model tests. The runtime needs Python 3.10+; Git only for Git storage. Missing tools are not installed automatically.

## Checks

The shared [test layout](../../tests/README.md) groups by test type first: `unit/`, `integration/`, `contracts/`, and optional `behavior/` and `native/`. Skills or components sit underneath; data and helpers live in `fixtures/` and `support/`.

`make test` runs only unit, integration and contract tests. Individual layers: `make test-unit`, `make test-integration`, `make test-contracts`. `make test-native` and `make test-behavior` are requested separately. Absent suites explicitly report `NOT RUN`; native tests require explicit layer selection.

Run deterministic unit, packaging and workspace checks after every change:

```bash
python3 -B scripts/run_tests.py --kind deterministic
```

Run **opt-in model behavior simulations** locally with an authenticated Codex CLI or Claude Code CLI. They use fictional candidates and do not need the ChatGPT UI:

```bash
python3 tests/behavior/run.py --list
python3 tests/behavior/run.py --cli codex --output-dir .tmp/tests/behavior/codex
# or:
python3 tests/behavior/run.py --cli claude --output-dir .tmp/tests/behavior/claude
```

The behavior suite checks role-aware score structure, feedback, no-storage stop behavior and interviewer uncertainty. It sends skill/reference text and fictional prompts to the selected model, may consume API/CLI credits, and uses **heuristic** text checks. Review generated outputs manually; a passing score does not prove good coaching or UI behavior. It does not read private candidate workspaces. Run it explicitly, not automatically on every commit.

**Platform acceptance remains manual:** Install the generated plugin in the selected host and verify native selection controls, permissions, durable workspace reuse across a new chat, saved job research and end-of-run persistence. A CLI simulation cannot validate those host-specific interactions. Use a disposable workspace for acceptance tests; do not overwrite a real candidate's data.

```bash
make help
make test                         # unit + integration + contracts, no LLM costs
make test-unit                    # only source-oriented unit tests
make test-integration             # filesystem and workflow integration
make test-contracts               # skill and distribution contracts
make test-list                    # list fictional behavior scenarios
make test-behavior CLI=codex      # opt-in model tests, may use credits
make test-behavior CLI=claude CASE=lead_feedback
make test-smoke CLI=codex         # older smoke suite
```

Test results from LLMs must be reviewed; the checks are heuristic and cannot validate ChatGPT's native UI. All three model runners separate the model's stdout from diagnostic stderr to avoid false passes from echoed prompts or CLI warnings.

### Local test output layout

Generated model-test artifacts are kept under the repository-local ignored `.tmp/` directory. Deterministic tests use disposable temporary directories:

```text
.tmp/
  tests/
    behavior/
      codex/       # scenario answers and stderr diagnostics
      claude/
    smoke/
      codex/       # basic smoke outputs
      claude/
```

The runners create the directories on demand. The entire `.tmp/` tree is gitignored; test fixtures and source files remain versioned under `tests/`. Use `OUT=.tmp/tests/behavior/custom` to override the behavior output location.

### Multi-step scenarios (`make test-scenarios`)

`tests/behavior/run_scenarios.py` replays 13 multi-step scenarios (setup, candidates with/without CV, equal-name candidates, training, job creation, job training, stop/pause, do-not-save, save failure). The model may only emit `TOOL: python3 <runtime> …` lines; the harness executes exclusively the runtime against a temporary fictional project, logs every call and checks artifacts (hashes, files, statuses). Host tools are disabled. This is **heuristic** and not a native host run. The runs use the already signed-in CLI (no credentials are read or copied); an isolated profile without sign-in cannot call a model, so genuinely isolated host runs are `NOT RUN` ([acceptance](../acceptance.md)).

### Scenario checks: structure, rubric and tool results

The scenarios check the domain contract rather than single words: (1) tool calls count only with exit code 0 (exception: `candidate-resolve` exit 2 = "ask the user"); a failed `finish` can never be turned into a success by matching text. (2) Saved artifacts are checked (hashes, status, assignment; continuation with predecessor reference, growing counter, unchanged checkpoint). (3) Evaluable answers require an overall score x/10, criteria and substantial feedback (structural) plus, by rubric, concrete strengths, concrete improvements and no invented facts. (4) Insufficient answers require a concrete reason, one fitting follow-up and a cautious score — no confident grade. (5) The rubric is judged by a second model call (the "judge"); without a judge the semantic items stay unchecked = FAIL. Invention accusations count only with a verbatim quote that occurs in the reply and contains content words outside the candidate's message. The judge is itself a model and can be wrong.

### Native check logic

`tests/native/run_native.py` counts a runtime call as successful only if it is provably ONE call (`parse_runtime_call`: shlex with quoting, optionally one `sh|bash|zsh -c` wrapper; `;`, `&&`, `||`, pipes, redirects, variable prefixes → not proven) and its own tool result has exit code 0 (unknown ≠ 0). For training, project, candidate and job IDs of `job-show` must match. `training_question` is a bounded deterministic heuristic (posting vocabulary + a question/task that is not a selection/confirmation/preparation clarification); it does not understand meaning and proves no interview quality. A real run can therefore fail more strictly (compound shell commands are not evidence).

### Git tests

`tests/integration/git/` uses temporary local bare repositories behind a `github.com` URL (via `url.<bare>.insteadOf`), a fake `gh` and a logging `git` wrapper (asserting that force is never used). This exercises real git flows but is **not a live GitHub or GitLab acceptance**; private repositories, real authentication and connectors are untested. Write tests against personal repositories are not part of development.

### Scripted multi-step coaching regression

`make test-journey CLI=codex` (or `CLI=claude`) runs the fictional
`teamlead_coaching` journey: three separate interview answers, a candidate-written
revision of answer one after coaching, then `stop` in explicit no-storage mode.

Each step invokes the model afresh and **replays the prior user/assistant transcript**
in the next prompt. This tests contextual coaching and end-of-session reasoning,
**not** native CLI session continuity, real filesystem persistence or ChatGPT UI.
It uses five model calls, so it may consume appreciable tokens.

Artifacts are written under `.tmp/tests/journey/<cli>/<journey>/`:
one answer and diagnostic file per step plus `result.json`.
Checks are heuristic and inspect only the model answer, not stderr.
Manually inspect the content before treating the journey as a release signal.

```bash
make test
make test-journey CLI=codex
make test-journey CLI=claude
make test-scenarios CLI=claude          # multi-step scenarios with a restricted tool channel
```

Journey checks normalize Markdown for pattern matching and check competence caution separately from affirmative stability claims. They remain German-language heuristics: passing checks cannot establish factual correctness, and valid alternative wording may still require review. Diagnose failures as product, runner or scenario issues before changing checks.

### Local development through the shared marketplace

Use the Manager's `configure` action with this plugin checkout and the chosen marketplace. It preserves other associations, selects the local default and checks effective ignore rules before writing. `local-marketplace.example.json` is only an optional manual copy template. Runtime reads only Git-ignored `.local/marketplace.json`; never commit local mappings. `MARKETPLACE=/path/to/ai.plugins` overrides the default for one invocation.

From the Coach repository:

```sh
make install-local TARGET=claude
make update-local TARGET=codex
# Without Make:
python3 -B scripts/local_marketplace.py update-local --target codex
```

Both commands delegate to the configured marketplace and include all associated local plugins in the shared `draftmode-ai-plugins-dev` catalog. Missing required checkouts block before host changes. `DRY_RUN=1` creates snapshots without invoking a host.

Snapshots use the current checkout including uncommitted changes, regardless of branch. After edits or branch switches run `update-local` and open a new host session. Local tests need no commit, push or PR; do not add marketplaces per branch.

The Manager's `plugin-verify` reads this repository only. Publishable structure is independent of complete local development configuration: missing checkouts or `.local` files are expected on a fresh clone and are reported as unavailable local checks.

## Packaging

Repository imports need no plugin ZIPs. `plugin.mk`, legacy installation scripts and tag/release tooling are removed. Tests check committed manifests and a separately copied coaching runtime. Local development uses the shared `draftmode-ai-plugins-dev` marketplace.

## CI and releases

[CI](../../.github/workflows/validate.yml) runs `make test` and `make check-plugin`. Model tests remain optional. For new catalog entries, publish this plugin repository first, then the `ai.plugins` entry. Existing entries need no artificial catalog commit for a plugin-only edit. No tag or GitHub Release is required. [Workflow](release-operations.md) · [Evidence](release-evidence.md).

## Maintain documentation

Edit Markdown and relative links directly in this repository. GitHub renders the README, pages, tables and SVG previews without a separate website build, Wiki or Pages deployment. Keep product claims aligned with runtime behavior and add real platform screenshots only after reviewing them for private information. The [screens page](screens.md) documents provenance and the remaining capture work.

Before a public directory submission, supply actual required publisher/privacy/terms metadata and perform the host's platform acceptance. Do not invent legal URLs or describe a generated ZIP as a published plugin.


German defaults: `README.md`, `docs/de/`. Full English equivalents: `README.en.md`, `docs/en/`. Keep counterpart links, heading order and asset provenance aligned. `docs/documentation.json` stores source pointers and this repository’s documentation language policy (`documentation.languages`: `de`, `en`; `default_language`: `de`). Product facts remain in their canonical sources. Use `update` (Plugin Manager) to reread sources and refresh README and guides, then validate and verify; `update-local` refreshes local plugin snapshots instead. Documentation prepared with Plugin Manager.


README and guides are maintained Markdown, not files regenerated on every build. `update` (Plugin Manager) uses source evidence, language configuration and templates; the agent authors the content. Structural validation does not replace content review.

### Scope and development

Confirmed requirements are in [SCOPE.md](../../SCOPE.md), shared development rules in
[AGENTS.md](../../AGENTS.md) and [architecture](../architecture.md). CLAUDE.md points to
the same rules. Source/test references are not acceptance; model checks are heuristic.
Read-only review never executes source or tests.

Runs without current metadata (workspace format 3) or with a foreign candidate/job assignment are rejected before writes and remain intact. Follow the specific save diagnostic: pending journal → recover; no
recorded intent → resolve the write error and retry the same run ID with the original
state hash; intended contents exist without confirmed final durability → inspect them
without overwriting.
