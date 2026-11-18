#!/usr/bin/env bash
# ZYRIS Interview Coach installer — copies public skill only; never touches private workspaces.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$ROOT/.claude/skills/zyris-interview-coach"
NAME="zyris-interview-coach"
usage() {
  cat <<'EOF'
Usage: bash install.sh [claude|claude-chat|claude-plugin|codex|chatgpt|all] [--yes]
Without a target, the installer asks interactively.
  claude   Install for Claude Code to ~/.claude/skills/zyris-interview-coach/
  claude-chat  Build ZIP for upload to claude.ai Customize > Skills
  claude-plugin  Build a Claude Code plugin ZIP\n  codex    Install to ~/.agents/skills/zyris-interview-coach/
  chatgpt  Build dist/zyris-interview-coach-chatgpt-plugin.zip
  all      Install Claude Code and Codex skills; build both plugins and Claude Chat skill ZIP
--yes skips overwrite confirmation (useful for scripted upgrades).
No CV or private training data is copied.
EOF
}
TARGET=""
YES=0
for arg in "$@"; do
  case "$arg" in
    claude|claude-chat|claude-plugin|codex|chatgpt|all) if [[ -n "$TARGET" ]]; then echo "Only one target allowed" >&2; exit 2; fi; TARGET="$arg" ;;
    --yes) YES=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $arg" >&2; usage; exit 2 ;;
  esac
done
if [[ ! -f "$SOURCE/SKILL.md" ]]; then echo "Skill source missing: $SOURCE" >&2; exit 1; fi
if [[ -z "$TARGET" ]]; then
  if [[ ! -t 0 ]]; then echo "Noninteractive session: specify claude, claude-chat, codex, chatgpt or all." >&2; exit 2; fi
  printf 'Install ZYRIS Interview Coach for:\n  1) Claude Code skill\n  2) Claude Chat skill ZIP\n  3) Claude Code plugin ZIP\n  4) Codex CLI skill\n  5) ChatGPT plugin ZIP\n  6) All\nSelection [1-6]: '
  read -r choice
  case "$choice" in 1) TARGET=claude;; 2) TARGET=claude-chat;; 3) TARGET=claude-plugin;; 4) TARGET=codex;; 5) TARGET=chatgpt;; 6) TARGET=all;; *) echo "Invalid selection" >&2; exit 2;; esac
fi
copy_skill() {
  local dest="$1"
  if [[ -e "$dest" && "$YES" -ne 1 ]]; then
    if [[ ! -t 0 ]]; then echo "Existing install: $dest (use --yes to replace)" >&2; exit 2; fi
    printf 'Replace existing installation at %s? [y/N]: ' "$dest"
    read -r answer
    [[ "$answer" == y || "$answer" == Y ]] || { echo "Skipped: $dest"; return; }
  fi
  local parent stage backup=""
  parent="$(dirname "$dest")"
  mkdir -p "$parent"
  stage="$(mktemp -d "$parent/.zyris-interview-coach.XXXXXXXX")"
  cp -R "$SOURCE/." "$stage/"
  if [[ -e "$dest" ]]; then
    backup="$parent/.zyris-interview-coach.backup.$$"
    mv "$dest" "$backup"
  fi
  if ! mv "$stage" "$dest"; then
    [[ -n "$backup" && -e "$backup" ]] && mv "$backup" "$dest"
    rm -rf "$stage"
    echo "Installation failed: $dest" >&2
    exit 1
  fi
  if [[ -n "$backup" ]]; then rm -rf "$backup"; fi
  echo "Installed: $dest"
}
package_claude_chat() {
  command -v python3 >/dev/null || { echo "Python 3 required for ChatGPT ZIP packaging" >&2; exit 1; }
  python3 "$ROOT/scripts/package_skill.py" --source "$SOURCE" --output "$ROOT/dist/$NAME.zip"
  echo "Claude Chat skill package created: $ROOT/dist/$NAME.zip"
  echo "Upload this skill ZIP in Claude Chat. This is not the Claude Code plugin ZIP."
}
package_plugin() {
  local platform="$1"
  command -v python3 >/dev/null || { echo "Python 3 required for plugin packaging" >&2; exit 1; }
  python3 "$ROOT/scripts/package_plugin.py" --platform "$platform" --output "$ROOT/dist/$NAME-$platform-plugin.zip"
  echo "$platform plugin ZIP created. Import or publish it through the platform's supported plugin workflow."
}
case "$TARGET" in
  claude) copy_skill "${CLAUDE_HOME:-$HOME/.claude}/skills/$NAME" ;;
  codex) copy_skill "${CODEX_HOME:-$HOME/.agents}/skills/$NAME" ;;
  chatgpt) package_plugin chatgpt ;;\n  claude-plugin) package_plugin claude ;;
  claude-chat) package_claude_chat; echo "Upload ZIP in claude.ai: Customize > Skills > + > Create skill > Upload a skill; enable it." ;;
  all)
    copy_skill "${CLAUDE_HOME:-$HOME/.claude}/skills/$NAME"
    copy_skill "${CODEX_HOME:-$HOME/.agents}/skills/$NAME"
    package_claude_chat\n    package_plugin claude\n    package_plugin chatgpt
    ;;
esac
echo "Next: in Claude Code use /zyris-interview-coach setup; in Claude Chat upload the ZIP first; in ChatGPT install the plugin and run its onboarding skill."
