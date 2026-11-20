#!/usr/bin/env python3
"""Manual smoke tests against installed Claude or Codex CLI. Not part of default CI."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

# Share answer/diagnostic separation with behavior and journey tests.
from run import ROOT, run as run_case, check, skill_context

CASES = json.loads((ROOT / "tests/fixtures/behavior/behavior-cases.json").read_text())
SKILL = skill_context()
FIXTURES = "\n\n".join(f"=== tests/fixtures/{name} (fictional) ===\n" + (ROOT / "tests/fixtures" / name).read_text(encoding="utf-8")
                        for name in ("candidate.md", "job.md"))  # the model has no file access in this harness

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cli", choices=["claude","codex"], required=True)
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument("--output-dir", type=Path, default=None)
    args = p.parse_args()
    if not shutil.which(args.cli):
        print(f"CLI not found: {args.cli}", file=sys.stderr)
        return 2
    output_dir = args.output_dir or ROOT / ".tmp" / "tests" / "smoke" / args.cli
    output_dir.mkdir(parents=True, exist_ok=True)
    failures = 0
    for case in CASES:
        prompt = ("Follow these interview skill instructions:\n" + SKILL + "\n\nFICTIONAL FIXTURES (you cannot read files; they are given here):\n" + FIXTURES
                  + "\n\n" + case["prompt"] + "\nAnswer in German. Do not ask for files or storage; this is a fictional test.")
        try:
            code, output, diagnostics = run_case(args.cli, prompt, args.timeout)
        except subprocess.TimeoutExpired:
            code, output, diagnostics = 124, "", "TIMEOUT"
        (output_dir / (case["id"] + ".txt")).write_text(output, encoding="utf-8")
        (output_dir / (case["id"] + ".stderr.txt")).write_text(diagnostics, encoding="utf-8")
        ok = not check(case, output, code)
        print(f"{'PASS' if ok else 'FAIL'} {case['id']} (exit={code})")
        if not ok:
            print(output[:1000])
            failures += 1
    print(f"Smoke tests: {len(CASES)-failures}/{len(CASES)} passed. Heuristic only, requires manual review.")
    return int(failures > 0)

if __name__ == "__main__":
    sys.exit(main())
