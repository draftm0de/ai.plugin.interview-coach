PYTHON ?= python3
SKILL_NAME := zyris-interview-coach
SOURCE := .claude/skills/$(SKILL_NAME)
CLAUDE_HOME ?= $(HOME)/.claude
CODEX_HOME ?= $(HOME)/.agents
DIST := dist

.PHONY: help install-claude install-codex install-chatgpt package-chatgpt test smoke-claude smoke-codex clean

help:
	@echo "make install-claude    Install skill into ~/.claude/skills/"
	@echo "make install-codex     Install skill into ~/.agents/skills/"
	@echo "make install-chatgpt   Build portable ChatGPT skill ZIP (manual import)"
	@echo "make test              Run deterministic Python tests"
	@echo "make smoke-claude      Manual LLM smoke tests (usage may be billed)"
	@echo "make smoke-codex       Manual LLM smoke tests (usage may be billed)"

install-claude:
	@test -f "$(SOURCE)/SKILL.md"
	@mkdir -p "$(CLAUDE_HOME)/skills/$(SKILL_NAME)"
	@cp -R "$(SOURCE)/." "$(CLAUDE_HOME)/skills/$(SKILL_NAME)/"
	@echo "Installed Claude skill: $(CLAUDE_HOME)/skills/$(SKILL_NAME)"
	@echo "Invoke: /$(SKILL_NAME) setup"

install-codex:
	@test -f "$(SOURCE)/SKILL.md"
	@mkdir -p "$(CODEX_HOME)/skills/$(SKILL_NAME)"
	@cp -R "$(SOURCE)/." "$(CODEX_HOME)/skills/$(SKILL_NAME)/"
	@echo "Installed Codex skill: $(CODEX_HOME)/skills/$(SKILL_NAME)"

install-chatgpt: package-chatgpt

package-chatgpt:
	@$(PYTHON) scripts/package_skill.py --source "$(SOURCE)" --output "$(DIST)/$(SKILL_NAME).zip"
	@echo "ChatGPT package ready: $(DIST)/$(SKILL_NAME).zip"
	@echo "Import manually where custom skills are supported; this does NOT install into ChatGPT."

test:
	@$(PYTHON) -m unittest discover -s tests -v

smoke-claude:
	@$(PYTHON) scripts/run_llm_smoke.py --cli claude

smoke-codex:
	@$(PYTHON) scripts/run_llm_smoke.py --cli codex

clean:
	@rm -rf "$(DIST)"
