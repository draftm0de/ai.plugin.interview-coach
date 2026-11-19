#!/usr/bin/env python3
"""Opt-in scripted multi-turn interview regression using explicit transcript replay.

Each step starts a fresh CLI invocation with prior user/assistant turns replayed.
This checks cross-turn reasoning, NOT native CLI session persistence or host UI.
"""
import argparse
import json
import re
from pathlib import Path
import shutil
import sys
import subprocess

from run import ROOT, check, run, skill_context

JOURNEYS = ROOT / "tests" / "fixtures" / "behavior" / "journeys"


def load_journey(name):
    path = JOURNEYS / (name + ".json")
    if not path.is_file():
        raise ValueError(f"Unknown journey: {name}")
    journey = json.loads(path.read_text(encoding="utf-8"))
    if not journey.get("steps") or len(journey["steps"]) < 3:
        raise ValueError("Journey requires at least three steps")
    return journey


def build_prompt(context, introduction, history, current_user):
    transcript = "\n\n".join(
        f"{role.upper()}:\n{message}" for role, message in history
    )
    return (
        "Follow the interview skill and references below. This is a fictional "
        "scripted regression simulation. Do not read or write private files. "
        "Do not claim any persistence. Answer in German.\n\n"
        + context + "\n\nTEST CONTEXT:\n" + introduction
        + "\n\nPRIOR CONVERSATION (verbatim; keep chronological order):\n"
        + (transcript or "(no prior turns)")
        + "\n\nLATEST USER MESSAGE:\n" + current_user
        + "\n\nRespond ONLY to the latest user message, using prior conversation as context."
    )


def progress_errors(answer):
    """German evidence heuristics, not a semantic judge; manual review is required.

    Match caution about competence/evidence, not arbitrary 'nicht belegt' text.
    Inspect affirmative claims separately so a disclaimer cannot cancel them.
    Markdown emphasis and quotation marks must not change these checks.
    """
    text = re.sub(r'[*_`"„“”]', '', answer.casefold())
    caution_patterns = (
        r"\bnicht\s+als\s+(?:stabil\w*|gefestigt\w*)(?:\s+\w+){0,4}\s+kompetenz\b",
        r"\bkein\w*\s+nachweis\s+für\s+(?:\w+\s+){0,3}stabil\w*\b",
        r"\b(?:noch\s+)?nicht\s+(?:dauerhaft\s+)?stabil\w*\b",
        r"\bkein\w*\s+(?:dauerhaft\s+)?(?:stabil\w*|kompetenzstatus)\b",
        r"\b(?:stabil\w*\s+kompetenz\w*|kompetenz\w*)\s+"
        r"(?:\w+\s+){0,3}(?:nicht|kein\w*|offen|unbestätigt)\b",
        r"\bkein\w*\s+(?:unabhängig\w*|spontan\w*|dauerhaft\w*)\s+nachweis\b",
        r"\b(?:stabilität|dauerhafte\s+kompetenz)\s+(?:\w+\s+){0,3}"
        r"(?:nicht|unbelegt|unbestätigt|offen)\b",
    )
    errors = []
    if not any(re.search(pattern, text) for pattern in caution_patterns):
        errors.append('missing competence/evidence caution')
    # Sentence/semicolon boundaries keep unrelated disclaimers out of the claim.
    for clause in re.split(r'[.!?;\n]+', text):
        affirmative = re.search(
            r"\b(?:kompetenz\w*|c\d+|schwäche\w*|defizit\w*)\s*"
            r"(?::|ist|sind|gilt\s+als)\s*(?:(?:jetzt|nun|bereits|dauerhaft|stabil)\s+){0,3}"
            r"(?:stabil|behoben|gefestigt|bestätigt)\b", clause)
        if affirmative:
            tail = clause[affirmative.end():]
            if not re.match(r"\s+(?:noch\s+)?nicht\s+(?:belegt|nachgewiesen|bestätigt)", tail):
                errors.append('unsupported stable competence claim')
    return errors


def check_step(step, answer, code=0):
    errors = check(step, answer, code)
    normalized = re.sub(r'[*_`"„“”]', '', answer)
    for group in step.get('required_regex_groups', []):
        if not any(re.search(pattern, normalized, flags=re.IGNORECASE) for pattern in group):
            errors.append('missing semantic pattern: ' + ' | '.join(group))
    if step.get('require_progress_caution'):
        errors.extend(progress_errors(answer))
    return errors


def execute_journey(journey, cli, output_dir, timeout, runner=run):
    output_dir.mkdir(parents=True, exist_ok=True)
    history = []
    results = []
    context = skill_context()
    for index, step in enumerate(journey["steps"], start=1):
        prompt = build_prompt(context, journey["context"], history, step["user"])
        try:
            code, answer, diagnostics = runner(cli, prompt, timeout)
        except TimeoutError:
            code, answer, diagnostics = 124, "", "TIMEOUT"
        except subprocess.TimeoutExpired:
            code, answer, diagnostics = 124, "", "TIMEOUT"
        errors = check_step(step, answer, code)
        prefix = f"{index:02d}-{step['id']}"
        (output_dir / (prefix + ".txt")).write_text(answer, encoding="utf-8")
        (output_dir / (prefix + ".stderr.txt")).write_text(diagnostics, encoding="utf-8")
        results.append({"step": step["id"], "passed": not errors, "errors": errors})
        print(f"{'PASS' if not errors else 'FAIL'} {journey['id']}/{step['id']}")
        for error in errors:
            print("  - " + error)
        if code != 0:
            break
        history.extend([("user", step["user"]), ("assistant", answer)])
    (output_dir / "result.json").write_text(
        json.dumps({"journey": journey["id"], "cli": cli, "results": results},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cli", choices=("codex", "claude"), required=True)
    p.add_argument("--journey", default="teamlead_coaching")
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument("--output-dir", type=Path)
    args = p.parse_args()
    if not shutil.which(args.cli):
        p.error(f"CLI not found: {args.cli}")
    journey = load_journey(args.journey)
    output_dir = args.output_dir or ROOT / ".tmp/tests/journey" / args.cli / args.journey
    results = execute_journey(journey, args.cli, output_dir, args.timeout)
    passed = sum(r["passed"] for r in results)
    print(f"{passed}/{len(journey['steps'])} journey steps passed; "
          "heuristic only, inspect model answers manually.")
    print(f"Artifacts: {output_dir}")
    return int(passed != len(journey["steps"]))


if __name__ == "__main__":
    sys.exit(main())
