# Development and validation

[Deutsch](../de/development.md) | [English](./development.md)

[Home](../../README.en.md) · [Documentation](README.md) · [Install](installation.md) · [Use](usage.md) · [Examples](screens.md) · [FAQ](faq.md) · [Storage](storage.md) · [Development](development.md)

## Source of truth

The [canonical skill](../../skills/zyris-interview-coach/SKILL.md) contains runtime instructions, references and the bundled workspace CLI. Root `scripts/` contains packaging tools only. Keep documentation and demo assets under `docs/`; they are not shipped in plugin ZIPs.

- `skills/zyris-interview-coach/`: **shipped runtime**, including `SKILL.md`, references and the one canonical `scripts/interview_workspace.py`.
- Root `scripts/`: **development/build-only**, with the sole manifest-driven builder `plugin.py`; these are not shipped as runtime.
- Root `tests/`: **development/test-only**: `unit/test_<source_module>.py` for source-oriented unit tests, `regression/test_<behavior>.py` for contracts and cross-component regressions, and `behavior/run.py`, `behavior/run_smoke.py`, `behavior/fixtures/` for opt-in LLM simulations; never shipped.
- `Makefile` includes `plugin.mk`; it and `install.sh` delegate to `scripts/plugin.py`. These installer files are generated snapshots of the documentation plugin templates. Update the templates first and propagate reviewed changes; the documentation verify action detects drift.

Shared hygiene: `.tmp/` is created only when local scratch work or diagnostic output needs it; `dist/` contains generated packages. `.DS_Store`, `.idea/`, caches, bytecode and dependency environments are ignored. Preserve project-specific ignore rules and diagnostic evidence. Development scripts belong in root `scripts/`; runtime scripts belong with their skill. Use bytecode suppression for local Python imports and test extracted packages independently of the checkout. Documentation-plugin verify checks effective ignore rules, tracked generated files and static packaged-Python syntax/imports; it does not run target code or prove host acceptance.

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
make package                  # all distribution ZIPs
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

`make package` produces ChatGPT, Claude and Codex plugin ZIPs plus `dist/claude-marketplace` and `dist/codex-marketplace`. `make check-plugin` validates the manifest. Package aliases `package-chatgpt`, `package-claude-plugin` and `package-all` delegate to the same builder; `package-claude-chat` exits with migration guidance. The legacy help text saying “both” is outdated: three ZIPs are built.

`plugin.json` owns identity, base version, MIT license and distribution configuration. Generated host manifests and versions with content hashes are derived. The builder includes `LICENSE`; docs and tests are excluded. No host manifest is maintained separately in the checkout.

## CI and releases

[GitHub Actions](../../.github/workflows/validate.yml) runs deterministic tests, manifest validation and plugin packaging. Model tests remain opt-in. The builder generates a local Claude marketplace under `dist/claude-marketplace`; it does not publish a directory listing or GitHub Release. `plugin.json` owns the base version; host package versions include a content hash.

The workflow path filters do not include documentation-only changes. Local documentation validation remains necessary.

## Maintain documentation

### Website export

`make check-docs-export` validates the contract; `make export-docs` creates `dist/<plugin-name>-documentation.zip` with `index.json`, unchanged Markdown pages and selected assets. The `export` configuration in `docs/documentation.json` contains only page and asset pointers. Product metadata comes from `plugin.json`; languages come from the existing documentation settings. The index adds link mappings, checksums and Git provenance, explicitly marking local changes. The website owns routing and safe rendering. Nothing is published.

Edit Markdown and relative links directly in this repository. GitHub renders the README, pages, tables and SVG previews without a separate website build, Wiki or Pages deployment. Keep product claims aligned with runtime behavior and add real platform screenshots only after reviewing them for private information. The [screens page](screens.md) documents provenance and the remaining capture work.

Before a public directory submission, supply actual required publisher/privacy/terms metadata and perform the host's platform acceptance. Do not invent legal URLs or describe a generated ZIP as a published plugin.

Native Codex installer integration can be tested with `ZYRIS_TEST_CODEX_NATIVE=1 make test`. It uses a temporary isolated Codex profile to verify installation, reinstallation and content updates without changing the personal profile. This native integration test was not run during this documentation update.

German defaults: `README.md`, `docs/de/`. Full English equivalents: `README.en.md`, `docs/en/`. Keep counterpart links, heading order and asset provenance aligned. `docs/documentation.json` stores source pointers and this repository’s documentation language policy (`documentation.languages`: `de`, `en`; `default_language`: `de`). Product facts remain in their canonical sources. Use the installed ZYRIS documentation update action, then validate and verify; `make update` updates the installed coaching plugin instead. Documentation prepared with ZYRIS Skill Documentation.
