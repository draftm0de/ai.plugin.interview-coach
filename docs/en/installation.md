# Installation and updates

[Deutsch](../de/installation.md) | [English](./installation.md)

[Home](../../README.en.md) · [Documentation](README.md) · [Install](installation.md) · [Use](usage.md) · [Examples](screens.md) · [FAQ](faq.md) · [Storage](storage.md) · [Development](development.md)

## Choose your platform

Use Python 3.10+, Bash and optionally Make. Run commands from the repository root. Native installation requires the selected host CLI; this repository packages a plugin containing the coaching skill, not a separate application.

Host guidance checked on 2026-11-18: [Claude Code](https://code.claude.com/docs/en/plugins/install), [ChatGPT upload and access](https://help.openai.com/en/articles/20001256-plugins-in-chatgpt), [OpenAI plugins](https://learn.chatgpt.com/docs/plugins). Host availability and permissions remain account-dependent. These sources do not prove acceptance of this particular package.

## Install

Use Python 3.10+, Bash and optionally Make. Claude Code installation additionally requires its CLI. Run commands from this repository. All native plugin installation requires the corresponding host CLI. Both entry points call the same `scripts/plugin.py`; product identity and source paths come from `plugin.json`.

| Action | Make | Equivalent Bash command |
|---|---|---|
| Build all three plugin ZIPs and local marketplaces | `make package` | `bash install.sh build` |
| Install Codex plugin | `make install TARGET=codex` | `bash install.sh install --target codex` |
| Update Codex plugin | `make update TARGET=codex` | `bash install.sh update --target codex` |
| Install Claude Code plugin | `make install TARGET=claude` | `bash install.sh install --target claude` |
| Preview Claude installation | `make install TARGET=claude DRY_RUN=1` | `bash install.sh install --target claude --dry-run` |
| Update Claude Code plugin | `make update TARGET=claude` | `bash install.sh update --target claude` |
| Prepare ChatGPT upload | `make install TARGET=chatgpt` | `bash install.sh install --target chatgpt` |
| Prepare ChatGPT update | `make update TARGET=chatgpt` | `bash install.sh update --target chatgpt` |

A dry run builds artifacts and prints commands without invoking the host. ChatGPT commands always build only; they never claim to upload or install.

### Codex

Run `make install TARGET=codex`, then open a new Codex chat or restart Codex if necessary. The installer uses native `codex plugin marketplace add` and `codex plugin add` commands. Earlier documentation records a test with Codex CLI 0.165.0; that native test was not repeated during this documentation update. The generated marketplace is in `dist/codex-marketplace`, and host metadata lives in `.codex-plugin/plugin.json` inside the package. `make update TARGET=codex` rebuilds and reinstalls the new content version. Keep the repository available for later updates. Existing plugins from other marketplaces and private workspaces are not removed.

### Claude Code

Run `make install TARGET=claude`. The helper builds and registers the local marketplace in `dist/claude-marketplace`, then invokes native plugin installation. Restart Claude Code and ask the installed plugin to run setup. Keep the checkout available: subsequent updates use this local marketplace.

The checkout retains its canonical source under `.claude/skills/zyris-interview-coach`; package paths are normalized to `skills/zyris-interview-coach`. Opening this repository may also expose that project-local capability. Test the installed plugin from a separate project to avoid confusing it with project-local discovery.

### Existing standalone installations

The previous `claude-chat`, `claude-plugin`, `all` and `--yes` installer modes have been retired. They exit with migration guidance rather than copying skills or removing installations. `bash install.sh claude` now installs the Claude plugin; `bash install.sh chatgpt` prepares the ChatGPT plugin ZIP.

Old user-level skill copies remain untouched. After verifying the new plugin, review and remove obsolete copies through the appropriate host or filesystem workflow to avoid duplicate capabilities. Private training workspaces remain separate. Use `TARGET=codex` to install the native Codex plugin. Installing in Claude does not install into another host. The old standalone `codex` mode is replaced by native plugin installation, including the shorthand `bash install.sh codex`.

### ChatGPT plugin upload

Upload `dist/zyris-interview-coach-chatgpt-plugin.zip` through the plugin administration available to your account/workspace, then enable the plugin. The package includes the skill and Python workspace helper, not a remote MCP storage service. ZIP creation does not establish host acceptance or durable cross-chat storage.

## Update

Preserve local changes before updating your checkout. Then run `make update TARGET=claude`, or rebuild for ChatGPT and upload the new version manually. Claude updates require an initial installation of this local marketplace. Start a new session and verify setup and access to your private workspace.

`plugin.json` holds the base version. The builder derives host manifests and appends a deterministic content hash to the package version, so changed runtime content produces a distinct version. Nothing is committed, pushed or published by these commands.

For Codex use `make update TARGET=codex`; for ChatGPT use `make update TARGET=chatgpt` and upload the resulting ZIP.

## Remove

Remove or disable the plugin through the host's plugin management. Old standalone skill copies and project-local sources are separate. Removing a plugin does not delete candidate workspaces or their local configuration pointer.

## Verify first use

Ask for setup, select a language and choose **Nicht speichern**. Try a fictional interview answer, confirm role-relevant feedback, then say `stop`. See [usage](usage.md) and [examples](screens.md). Native installation and a real-host journey remain acceptance checks separate from deterministic packaging tests.
