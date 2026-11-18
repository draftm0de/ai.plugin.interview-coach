# Development and validation

[Deutsch](../de/development.md) | [English](./development.md)

[Home](../../README.en.md) · [Documentation](README.md) · [Install](installation.md) · [Use](usage.md) · [Examples](screens.md) · [FAQ](faq.md) · [Storage](storage.md) · [Development](development.md)

## Source of truth

`skills/zyris-interview-coach/` retains the coaching runtime. `plugin.json` defines `interview-coach` with display name **Interview Coach**. `make sync-plugin` derives `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`; `make check-plugin` detects drift. All manifests remain versionless. The shared marketplace lives in the separate `ai.plugins` repository; this plugin has no catalog of its own.

## Checks

Run deterministic unit, packaging and workspace checks after every change:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
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
make test                         # unit + regression, no LLM costs
make test-unit                    # only source-oriented unit tests
make test-regression              # only regression/contract tests
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
      codex/       # legacy smoke outputs
      claude/
```

The runners create the directories on demand. The entire `.tmp/` tree is gitignored; test fixtures and source files remain versioned under `tests/`. Use `OUT=.tmp/tests/behavior/custom` to override the behavior output location.

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
```

Journey checks normalize Markdown for pattern matching and check competence caution separately from affirmative stability claims. They remain German-language heuristics: passing checks cannot establish factual correctness, and valid alternative wording may still require review. Diagnose failures as product, runner or scenario issues before changing checks.

## Packaging

Repository imports need no plugin ZIPs. `plugin.mk`, legacy installation scripts and tag/release tooling are removed. Tests check committed manifests and a separately copied coaching runtime. Local development uses the shared `draftmode-ai-plugins-dev` marketplace.

## CI and releases

[CI](../../.github/workflows/validate.yml) runs `make test`, `make check-plugin` and website export validation. Model tests remain optional. Publish this plugin repository first, then the new `ai.plugins` entry. No tag or GitHub Release is required. [Workflow](release-operations.md) · [Evidence](release-evidence.md).

## Maintain documentation

### Website export

`make check-docs-export` validates the contract; `make export-docs` creates `dist/<plugin-name>-documentation.zip` with `index.json`, unchanged Markdown pages and selected assets. The `export` configuration in `docs/documentation.json` contains only page and asset pointers. Product metadata comes from `plugin.json`; languages come from the existing documentation settings. The index adds link mappings, checksums and Git provenance, explicitly marking local changes. The website owns routing and safe rendering. Nothing is published.

Edit Markdown and relative links directly in this repository. GitHub renders the README, pages, tables and SVG previews without a separate website build, Wiki or Pages deployment. Keep product claims aligned with runtime behavior and add real platform screenshots only after reviewing them for private information. The [screens page](screens.md) documents provenance and the remaining capture work.

Before a public directory submission, supply actual required publisher/privacy/terms metadata and perform the host's platform acceptance. Do not invent legal URLs or describe a generated ZIP as a published plugin.


German defaults: `README.md`, `docs/de/`. Full English equivalents: `README.en.md`, `docs/en/`. Keep counterpart links, heading order and asset provenance aligned. `docs/documentation.json` stores source pointers and this repository’s documentation language policy (`documentation.languages`: `de`, `en`; `default_language`: `de`). Product facts remain in their canonical sources. Use the installed ZYRIS documentation update action, then validate and verify; plugin updates use the shared marketplace. Documentation prepared with ZYRIS Skill Manager.

### Local development through the shared marketplace

This machine is already mapped through Git-ignored `.local/marketplace.json`. On a new machine copy `local-marketplace.example.json` there and adjust the path to `ai.plugins`. Its `.local/marketplace.json` must map `sources.interview-coach` to this checkout. Alternatively pass `MARKETPLACE=/path/to/ai.plugins` to Make.

```sh
make install-local TARGET=claude
# or TARGET=codex
make update-local TARGET=claude
```

Both commands delegate to `ai.plugins` and include Manager and Coach in the same development catalog. No separate catalog or ZIP is created here. `DRY_RUN=1` creates shared snapshots without invoking a host. Open a new local session and enable only the intended development copy. Use the Manager plugin-verify action on this repository path for read-only verification.
