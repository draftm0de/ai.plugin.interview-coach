export PYTHONDONTWRITEBYTECODE := 1
# Developer-only entry points. Not shipped in plugin/skill packages.
PYTHON ?= python3
TARGET ?= claude
DRY_RUN ?= 0
MARKETPLACE ?=
CLI ?= codex
CASE ?=
OUT ?= .tmp/tests/behavior/$(CLI)
JOURNEY ?= teamlead_coaching

.PHONY: help test test-unit test-contracts test-behavior test-journey test-smoke test-scenarios test-host test-research test-list check-plugin sync-plugin

help:
	@echo 'Tests: test (unit + integration + contracts), test-unit, test-integration, test-contracts, test-native, test-behavior'
	@echo "make install-local / update-local TARGET=claude|codex  Shared development marketplace"
	@echo "make test                  Unit + integration + contract tests (no LLM, also in CI)"
	@echo "make test-list             List behavior scenarios"
	@echo "make test-behavior         LLM simulations (CLI=codex|claude; optional CASE=id)"
	@echo "make test-journey          Scripted multi-step coaching test (CLI=codex|claude)"
	@echo "make test-scenarios       Multi-step model scenarios with restricted tool channel (CLI=codex|claude; optional SCENARIO=id)"
	@echo "make test-host              Native host acceptance in a temporary project (CLI=claude|codex)"
	@echo "make test-research          Native live-web research acceptance with a real public posting (CLI=claude|codex)"
	@echo "make test-smoke            Basic LLM smoke checks (CLI=codex|claude)"

# Test layers: deterministic checks by default; native/model tests are explicit.
TEST_GROUP ?=
.PHONY: test test-unit test-integration test-contracts test-native test-behavior
test test-unit test-integration test-contracts test-native:
	$(PYTHON) -B scripts/run_tests.py --kind $(if $(filter test,$@),deterministic,$(patsubst test-%,%,$@)) $(if $(TEST_GROUP),--group "$(TEST_GROUP)",)

test-list:
	$(PYTHON) tests/behavior/run.py --list

test-behavior:
	$(PYTHON) tests/behavior/run.py --cli $(CLI) $(if $(CASE),--case $(CASE),) --output-dir $(OUT)

test-journey:
	$(PYTHON) tests/behavior/run_journey.py --cli $(CLI) --journey $(JOURNEY) --output-dir .tmp/tests/journey/$(CLI)/$(JOURNEY)

test-scenarios:
	$(PYTHON) tests/behavior/run_scenarios.py --cli $(CLI) $(if $(SCENARIO),--scenario $(SCENARIO),) --output-dir .tmp/tests/scenarios/$(CLI)

test-host:
	$(PYTHON) tests/native/run_native.py --host $(CLI) $(if $(ONLY),--only $(ONLY),) --output .tmp/tests/native/$(CLI).json

test-research:
	$(PYTHON) tests/native/run_native.py --host $(CLI) --research --output .tmp/tests/native/$(CLI)-research.json

test-smoke:
	$(PYTHON) tests/behavior/run_smoke.py --cli $(CLI) --output-dir .tmp/tests/smoke/$(CLI)

# Read-only structure check (--review adds scope/source evidence); never installs or publishes.
SOURCE ?= .
.PHONY: verify plugin-verify
verify plugin-verify:
	$(PYTHON) scripts/verify.py --source "$(SOURCE)" --kind plugin $(if $(filter 1,$(REVIEW)),--review,)

# Repository import metadata; no per-plugin marketplace or ZIP builds.
.SUFFIXES:
check-plugin:
	$(PYTHON) scripts/plugin.py check
sync-plugin:
	$(PYTHON) scripts/plugin.py sync

.PHONY: install-local update-local
install-local update-local:
	$(PYTHON) scripts/plugin.py $@ --target "$(TARGET)" $(if $(MARKETPLACE),--marketplace "$(MARKETPLACE)",) $(if $(filter 1,$(DRY_RUN)),--dry-run,)
