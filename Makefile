include docs.mk
export PYTHONDONTWRITEBYTECODE := 1
# Developer-only entry points. Not shipped in plugin/skill packages.
PYTHON ?= python3
CLI ?= codex
CASE ?=
OUT ?= .tmp/tests/behavior/$(CLI)
JOURNEY ?= teamlead_coaching

.PHONY: help test test-unit test-regression test-behavior test-journey test-smoke test-list check-plugin sync-plugin

help:
	@echo 'make check-docs-export / export-docs  Validate / build the website documentation bundle'
	@echo "make test                  Unit + regression tests (no LLM, also in CI)"
	@echo "make test-list             List behavior scenarios"
	@echo "make test-behavior         LLM simulations (CLI=codex|claude; optional CASE=id)"
	@echo "make test-journey          Scripted multi-step coaching test (CLI=codex|claude)"
	@echo "make test-smoke            Legacy LLM smoke checks (CLI=codex|claude)"

test: test-unit test-regression

test-unit:
	$(PYTHON) -m unittest discover -s tests/unit -p 'test_*.py' -v

test-regression:
	$(PYTHON) -m unittest discover -s tests/regression -p 'test_*.py' -v

test-list:
	$(PYTHON) tests/behavior/run.py --list

test-behavior:
	$(PYTHON) tests/behavior/run.py --cli $(CLI) $(if $(CASE),--case $(CASE),) --output-dir $(OUT)

test-journey:
	$(PYTHON) tests/behavior/run_journey.py --cli $(CLI) --journey $(JOURNEY) --output-dir .tmp/tests/journey/$(CLI)/$(JOURNEY)

test-smoke:
	$(PYTHON) tests/behavior/run_smoke.py --cli $(CLI) --output-dir .tmp/tests/smoke/$(CLI)

# Repository import metadata; no per-plugin marketplace or ZIP builds.
.SUFFIXES:
check-plugin:
	$(PYTHON) scripts/plugin.py check
sync-plugin:
	$(PYTHON) scripts/plugin.py sync
