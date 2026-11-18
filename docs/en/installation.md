# Installation and updates

[Deutsch](../de/installation.md) | [English](./installation.md)

[Home](../../README.en.md) · [Documentation](README.md) · [Install](installation.md) · [Use](usage.md) · [Examples](screens.md) · [FAQ](faq.md) · [Storage](storage.md) · [Development](development.md)

## Choose a platform

This repository contains **Interview Coach** (`interview-coach`), with no marketplace of its own. Its bundled skill identity `zyris-interview-coach` is unchanged. Install through **Draftmode AI Plugins** (`draftmode-ai-plugins`): `https://github.com/draftm0de/ai.plugins`.

Publish the new `ai.plugin.interview-coach` content first, then the `ai.plugins` catalog. Graphical acceptance of this new entry is still pending. Your account needs access to both repositories.

## Install

### Claude Desktop

1. Open **Settings → Customizations → Plugins**.
2. Select **+ Add → Add marketplace → Add from a repository**.
3. Enter `https://github.com/draftm0de/ai.plugins` and select **Sync**.
4. Select **Interview Coach** and install the plugin.

### Codex Desktop

1. Open **User Icon → Settings → Integration → Plugins**.
2. Select **+ Add → A Marketplace**.
3. Enter `https://github.com/draftm0de/ai.plugins` and sync the marketplace.
4. Select **Interview Coach** and install the plugin.

### Optional terminal installation

Inside a Claude Code terminal session, not the Desktop Code tab input:

```text
/plugin marketplace add https://github.com/draftm0de/ai.plugins
/plugin install interview-coach@draftmode-ai-plugins
```

For Codex CLI:

```sh
codex plugin marketplace add https://github.com/draftm0de/ai.plugins
codex plugin add interview-coach@draftmode-ai-plugins
```

The technical plugin identity is `interview-coach`; the display name is **Interview Coach**. No ZIP, tag or separate catalog is required. ChatGPT account imports and organization permissions require separate acceptance.

## Update

Sync the shared marketplace in plugin settings and open a new session. The manifests do not pin a version. A push alone does not prove that a user installation has updated.

## Remove

Remove **Interview Coach** in plugin settings. Keep private training data outside the installation. Do not remove the entire marketplace if you still want to use Plugin Manager.

## Verify first use

Open a new chat and send **“Start interview coach setup”**. Select English and **Do not save**, practice with a fictional question and finish with `stop`. Persistent storage needs an authorized private workspace and a compatible Python runtime in the host; see [Storage](storage.md). Internet research requires internet access.

Check that both **Plugin Manager** and **Interview Coach** are offered by the marketplace. [Development](development.md) · [Evidence](release-evidence.md).
