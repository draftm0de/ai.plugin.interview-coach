#!/usr/bin/env python3
"""Manual smoke tests against installed Claude or Codex CLI. Not part of default CI."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "tests/fixtures/behavior-cases.json").read_text())
SKILL = (ROOT / ".claude/skills/zyris-interview-coach/SKILL.md").read_text()
def run_case(cli, prompt, timeout):
    if cli == "claude":
        cmd = ["claude", "-p", prompt, "--output-format", "text"]
    else:
        cmd = ["codex", "exec", "--skip-git-repo-check", "--sandbox", "read-only", prompt]
    cp = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout, check=False)
    return cp.returncode, (cp.stdout + "\n" + cp.stderr)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cli", choices=["claude","codex"], required=True)
    p.add_argument("--timeout", type=int, default=180)
    args = p.parse_args()
    if not shutil.which(args.cli):
        print(f"CLI not found: {args.cli}", file=sys.stderr)
        return 2
    failures = 0
    for case in CASES:
        prompt = "Follow these interview skill instructions:\n" + SKILL + "\n\n" + case["prompt"] + "\nAnswer in German."
        try:
            code, output = run_case(args.cli, prompt, args.timeout)
        except subprocess.TimeoutExpired:
            code, output = 124, "TIMEOUT"
        ok = code == 0 and any(s.lower() in output.lower() for s in case["must_contain_any"]) and not any(s.lower() in output.lower() for s in case["must_not_contain"])
        print(f"{'PASS' if ok else 'FAIL'} {case['id']} (exit={code})")
        if not ok:
            print(output[:1000])
            failures += 1
    print(f"Smoke tests: {len(CASES)-failures}/{len(CASES)} passed. Heuristic only, requires manual review.")
    return int(failures > 0)

if __name__ == "__main__":
    sys.exit(main())
