#!/usr/bin/env python3
"""Opt-in LLM behavior regression checks; no GUI or credentials embedded."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]

def skill_context(skills=None):
    """All public skill instructions plus shared references (what a host would load on demand)."""
    shared = ROOT / "skills/_shared/references"
    names = skills or ("interview-coach", "candidate-create", "candidate-training", "job-create", "job-training")
    paths = [ROOT / "skills" / name / "SKILL.md" for name in names] + sorted(shared.glob("*.md"))
    return "\n\n".join(f"=== {p.relative_to(ROOT)} ===\n" + p.read_text(encoding="utf-8") for p in paths)


def check(case, output, exit_code=0):
    lower = output.casefold()
    errors = []
    if exit_code:
        errors.append(f"CLI exit code: {exit_code}")
    if not any(x.casefold() in lower for x in case["must_contain_any"]):
        errors.append("missing required anchor")
    for forbidden in case.get("must_not_contain", []):
        if forbidden.casefold() in lower:
            errors.append(f"forbidden text: {forbidden}")
    for group in case.get("required_groups", []):
        if not any(term.casefold() in lower for term in group):
            errors.append("missing one of: " + " | ".join(group))
    return errors

def run(cli, prompt, timeout):
    """Text-only model call from an empty temporary directory: host tools disabled, no session persistence."""
    import tempfile
    with tempfile.TemporaryDirectory(prefix="coach-behavior-") as workdir:
        if cli == "codex":
            cmd = ["codex", "exec", "--skip-git-repo-check", "--ephemeral", "--ignore-user-config", "--ignore-rules",
                   "--sandbox", "read-only", "-C", workdir, prompt]
        else:
            cmd = ["claude", "-p", prompt, "--output-format", "text", "--tools", "", "--no-session-persistence",
                   "--disable-slash-commands", "--strict-mcp-config", "--setting-sources", "project"]
        result = subprocess.run(cmd, cwd=workdir, text=True, capture_output=True, timeout=timeout, check=False)
    return result.returncode, result.stdout, result.stderr

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", choices=("codex", "claude"))
    parser.add_argument("--case", help="Only one case ID")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--output-dir", type=Path, help="Optional directory for reviewing generated outputs")
    parser.add_argument("--list", action="store_true", help="List scenarios without invoking an LLM")
    args = parser.parse_args()
    cases = json.loads((ROOT / "tests/fixtures/behavior/quality-cases.json").read_text(encoding="utf-8"))
    if args.case:
        cases = [c for c in cases if c["id"] == args.case]
        if not cases:
            parser.error("unknown case")
    if args.list:
        for case in cases:
            print(case["id"])
        return 0
    if not args.cli:
        parser.error("--cli is required unless --list is used")
    if not shutil.which(args.cli):
        parser.error(f"{args.cli} CLI not installed")
    context = skill_context()
    if args.output_dir is None and args.cli:
        args.output_dir = ROOT / ".tmp" / "tests" / "behavior" / args.cli
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
    failures = 0
    for case in cases:
        prompt = ("Follow this interview coaching skill and references. "
                  "This is a fictional regression test, not a real candidate. "
                  "Do not access or write private files. Answer in German.\n\n"
                  + context + "\n\nSCENARIO:\n" + case["prompt"])
        try:
            code, output, diagnostics = run(args.cli, prompt, args.timeout)
        except subprocess.TimeoutExpired:
            code, output, diagnostics = 124, "TIMEOUT", "Timeout exceeded"
        errors = check(case, output, code)
        if args.output_dir:
            (args.output_dir / (case["id"] + ".txt")).write_text(output, encoding="utf-8")
            (args.output_dir / (case["id"] + ".stderr.txt")).write_text(diagnostics, encoding="utf-8")
        print(f"{'FAIL' if errors else 'PASS'} {case['id']}")
        for error in errors:
            print("  - " + error)
        failures += bool(errors)
    print(f"{len(cases)-failures}/{len(cases)} heuristic behavior checks passed; manually review quality.")
    return int(bool(failures))

if __name__ == "__main__":
    sys.exit(main())
