# Developer-only entry points. Not shipped in plugin/skill packages.
PYTHON ?= python3
CLI ?= codex
CASE ?=
OUT ?= /tmp/zyris-quality

.PHONY: help test test-unit test-behavior test-smoke test-list package-chatgpt package-claude-plugin package-claude-chat package-all

help:
	@echo "make test                  Deterministic tests (no LLM, also in CI)"
	@echo "make test-list             List behavior scenarios"
	@echo "make test-behavior         LLM simulations (CLI=codex|claude; optional CASE=id)"
	@echo "make test-smoke            Legacy LLM smoke checks (CLI=codex|claude)"
	@echo "make package-chatgpt       Build ChatGPT plugin ZIP"
	@echo "make package-claude-plugin Build Claude Code plugin ZIP"
	@echo "make package-claude-chat   Build Claude Chat skill ZIP"
	@echo "make package-all           Build all ZIPs"

test: test-unit

test-unit:
	$(PYTHON) -m unittest discover -s tests -v

test-list:
	$(PYTHON) tests/run_behavior.py --list

test-behavior:
	$(PYTHON) tests/run_behavior.py --cli $(CLI) $(if $(CASE),--case $(CASE),) --output-dir $(OUT)

test-smoke:
	$(PYTHON) tests/run_smoke.py --cli $(CLI)

package-chatgpt:
	bash install.sh chatgpt

package-claude-plugin:
	bash install.sh claude-plugin

package-claude-chat:
	bash install.sh claude-chat

package-all:
	bash install.sh chatgpt
	bash install.sh claude-plugin
	bash install.sh claude-chat
