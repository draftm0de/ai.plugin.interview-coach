# Installation and updates

[Deutsch](../de/installation.md) | [English](./installation.md)

[Home](../../README.en.md) · [Documentation](README.md) · [Install](installation.md) · [Use](usage.md) · [Examples](screens.md) · [FAQ](faq.md) · [Storage](storage.md) · [Development](development.md)

## Choose your platform

This repository contains **Interview Coach** (`interview-coach`) with five skills (`interview-coach`, `candidate-create`, `candidate-training`, `job-create`, `job-training`) and a shared runtime under `skills/_shared/`; it has no marketplace of its own. Supported hosts: **Claude Code** and **Codex**. The installation source is **Draftmode AI Plugins** (`draftmode-ai-plugins`): `https://github.com/draftm0de/ai.plugins`. Whether the current extension is published there is not evidenced; a repository import delivers the published state.

Prerequisites: Python 3.10+ for the runtime; `pdftotext`, `mutool` or Python `pypdf` for PDF import. **Nothing is installed automatically**; if something is missing the coach names exactly what.

## Install

### Claude Code

Inside a Claude Code session:

```text
/plugin marketplace add https://github.com/draftm0de/ai.plugins
/plugin install interview-coach@draftmode-ai-plugins
```

Then open a new session. Entry: `/interview-coach:interview-coach setup` or natural language. The other skills are `/interview-coach:candidate-create`, `…:candidate-training`, `…:job-create`, `…:job-training`. Claude Code finds them as `skills/*/SKILL.md` directories in the plugin; `skills/_shared/` holds no skill. The Claude Desktop dialog (Settings → Customize → Plugins → add marketplace from repository) leads to the same marketplace; its acceptance is only partly evidenced ([examples](screens.md)).

### Codex

```sh
codex plugin marketplace add https://github.com/draftm0de/ai.plugins
codex plugin add interview-coach@draftmode-ai-plugins
```

In Codex Desktop: Settings → Plugins → add marketplace → install Interview Coach. The manifest points to `./skills/`; entry by skill mention `$interview-coach` (skills: `$candidate-create`, `$candidate-training`, `$job-create`, `$job-training`) or natural language.

The exact invocation spellings depend on the host version and are not proven by an isolated host run in this repository ([acceptance](../acceptance.md)). No ZIP, tag or catalog of its own is required.

## Update

Sync the shared marketplace in plugin settings and open a new session. The manifests do not pin a version. A push alone does not prove that a user installation has updated.

## Remove

Remove **Interview Coach** in plugin settings. Keep private training data outside the installation. Do not remove the entire marketplace if you still want to use Plugin Manager.

## Verify first use

Open a new session and send **“Start interview-coach setup”**. Select English and **Do not save**, practice with a fictional question and finish with `stop`. Persistent storage (Local) needs a target you explicitly confirm; see [Storage](storage.md). Internet research requires internet access.

Check that both **Plugin Manager** and **Interview Coach** are offered by the marketplace. [Development](development.md) · [Evidence](release-evidence.md).

Menu paths come from existing user reports and captures, not a new GUI acceptance run. CLI commands were checked against local help. [Claude Code guide](https://code.claude.com/docs/en/discover-plugins) · [OpenAI plugin documentation](https://developers.openai.com/plugins/build/plugins).
