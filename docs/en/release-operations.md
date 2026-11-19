# Publication

1. Run `make test check-plugin` in the Coach repository and review the diff.
2. Use `publish` (Plugin Manager) to prepare a concrete plan for this repository: files, checks, commit/PR text, GitHub destination and a descriptive feature branch without `claude/` or `codex/`.
3. After explicit approval: create the approved branch → commit → push → PR → checks → controlled merge. Never publish normally on the default branch. On resumption reuse the same verified journal branch.
4. For new catalog entries, publish and verify the plugin source first, then approve a separate plan for `ai.plugins`. A plugin-only edit does not require an artificial catalog commit.
5. Sync **Draftmode AI Plugins** and separately verify installation, behavior and updates in the host.

Publication supports GitHub through a sufficiently capable GitHub connector or alternatively authenticated `gh`. Before approval verify capabilities and rights for remote/default-branch read, push, PR create/read, checks, rules and controlled merge. Report specific missing capabilities; never install tools automatically or bypass rules. GitLab MRs are unsupported.

A PR requires an existing base branch. Only completely empty local and remote repositories can use the separate bootstrap: a concrete plan and explicit approval for the first commit and direct push, including `--confirm-initial-publication`. No automatic initial commit. This existing repository needs no bootstrap.

No plugin ZIPs, manifest versions, tags, release Actions or GitHub Releases are required. Documentation updates and local tests do not authorize publication. [Installation](installation.md) · [Evidence](release-evidence.md).
