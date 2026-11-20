#!/usr/bin/env python3
"""Opt-in multi-step model scenarios with a restricted simulated tool channel. HEURISTIC.

The model gets the skill instructions and may request runtime commands as `TOOL: python3 <runtime> ...`
lines. The harness executes ONLY runtime invocations (never arbitrary shell), against a temporary fictional
project; it records every call and checks artifacts afterwards. Host tools are disabled for the model.
This is not a native Claude Code/Codex host run, and text/tool heuristics never prove quality.
"""
import argparse
import hashlib
import glob
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run import ROOT, check, skill_context  # noqa: E402

sys.path.insert(0, str(ROOT / "skills/_shared/scripts"))
import interview_workspace as iw  # noqa: E402

RUNTIME = ROOT / "skills/_shared/scripts/interview_workspace.py"
SCENARIOS = ROOT / "tests/fixtures/behavior/scenarios"
MAX_TOOL_ROUNDS = 6

PROTOCOL = """TOOL PROTOCOL (test harness): You cannot run shell commands yourself. To call the runtime, write one line per
call exactly as `TOOL: python3 {runtime} <subcommand> <arguments>` (no pipes, no redirects, one command per line). Only
this runtime is executed; every other TOOL line is rejected. The harness answers with `TOOL RESULTS` and you continue.
To create a file (for example a profile, run report or state file that a runtime command needs), write exactly
`WRITE_FILE: <absolute path under the files directory>` on its own line, then a line `<<<`, the content, and a line `>>>`.
Only paths below the files directory given in the context are written. Files you did not create do not exist.
When you need no further tool call, answer the user without any TOOL line. Do not run shell commands yourself and ignore any sandbox note about read-only access: the TOOL channel is your only way to run the runtime and to write files, and it works. Do not write TOOL lines when the chosen
storage is 'Nicht speichern'. Use the absolute paths given in the context. Answer in German."""


def load(name):
    return json.loads((SCENARIOS / f"{name}.json").read_text(encoding="utf-8"))


def all_ids():
    return sorted(p.stem for p in SCENARIOS.glob("*.json"))


def fill(text, env):
    for key, value in env.items():
        text = text.replace("{" + key + "}", str(value))
    return text


class Sandbox:
    """Temporary fictional project, files, workspace and pointer directory."""

    def __init__(self, scenario):
        self.tmp = Path(tempfile.mkdtemp(prefix="coach-scenario-")).resolve()
        self.project, self.files = self.tmp / "project", self.tmp / "files"
        self.workspace, self.config = self.tmp / "ws", self.tmp / "cfg"
        self.project.mkdir()
        self.files.mkdir()
        for name, content in scenario.get("files", {}).items():
            (self.files / name).write_text(content, encoding="utf-8")
        self.ids = {}
        self.preset(scenario.get("preset", {}))
        self.env = {"PROJECT": self.project, "FILES": self.files, "WS": self.workspace, "RUNTIME": RUNTIME,
                    "CONFIG": self.config, **{k: v for k, v in self.ids.items()}}

    def preset(self, preset):
        if preset.get("storage") != "local":
            return
        iw.setup_project(self.project, "local", self.workspace, config_dir=self.config)
        candidates = []
        for i, spec in enumerate(preset.get("candidates", [])):
            cid = iw.create_candidate(self.workspace, spec["name"])["candidate_id"]
            candidates.append(cid)
            self.ids[f"CANDIDATE{i}"] = cid
            if spec.get("cv"):
                cv = self.files / "preset-cv.md"
                cv.write_text(spec["cv"], encoding="utf-8")
                iw.import_cv(self.workspace, cid, cv)
            if spec.get("profile"):
                profile = self.files / f"preset-profile-{i}.md"
                profile.write_text(spec["profile"], encoding="utf-8")
                iw.save_profile(self.workspace, cid, profile, status=spec.get("profile_status", "confirmed"),
                                origin="cv" if spec.get("cv") else "interview", cv_source="cv-001" if spec.get("cv") else None,
                                user_confirmed=spec.get("profile_status", "confirmed") == "confirmed", acknowledge_gaps=True)
        for j, spec in enumerate(preset.get("jobs", [])):
            cid = candidates[spec.get("candidate", 0)]
            posting = self.files / f"preset-posting-{j}.md"
            posting.write_text(spec["posting"], encoding="utf-8")
            job = iw.create_job(self.workspace, cid, spec["title"], spec.get("company"), posting_text_file=posting)["job_id"]
            self.ids[f"JOB{j}"] = job
            if spec.get("research"):
                with iw.candidate_lock(self.workspace, cid) as cdir:
                    iw.add_artifact(cdir, iw.job_dir(cdir, job), "research", spec["research"],
                                    sources=["https://example.com/beispiel-ag/ueber-uns"], retrieved_at="2026-11-01")
            if spec.get("participants_unknown"):
                iw.update_job(self.workspace, cid, job, participants_status="unknown")
        for spec in preset.get("runs", []):
            cid = candidates[spec.get("candidate", 0)]
            state = iw.snapshot(self.workspace, cid)["state_sha256"]
            iw.finish(self.workspace, cid, spec["id"], spec.get("text", "# earlier run\n"), spec.get("state", "# state\nEarlier evidence\n"),
                      expected_state_sha256=state, status="completed", answered_count=1, planned_count=1, job_id=self.ids.get("JOB0") if spec.get("job") else None)
        if preset.get("readonly_runs"):
            for cid in candidates:
                (self.workspace / "candidates" / cid / "runs").chmod(0o500)

    def cleanup(self):
        for path in self.tmp.rglob("*"):
            try:
                if path.is_dir():
                    path.chmod(0o700)
            except OSError:
                pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, target, content, log):
        """Create a file for the model, strictly below the files directory."""
        path = Path(target)
        if not path.is_absolute() or ".." in path.parts or not path.resolve().is_relative_to(self.files.resolve()):
            log.append({"rejected_write": target})
            return "REJECTED: files may only be written below the files directory"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        log.append({"write": str(path)})
        return "written"

    def execute(self, line, log):
        """Run one TOOL line. Only `python3 <runtime> ...` is accepted."""
        try:
            argv = shlex.split(line)
        except ValueError as exc:
            return f"REJECTED: unparsable command ({exc})"
        if len(argv) < 3 or Path(argv[0]).name not in ("python3", "python") or Path(argv[1]).resolve() != RUNTIME:
            log.append({"rejected": line})
            return "REJECTED: only python3 <runtime> commands are executed"
        args = argv[2:]
        for index, value in enumerate(args):
            if value in ("--project",) and index + 1 < len(args) and Path(args[index + 1]).resolve() != self.project:
                log.append({"rejected": line})
                return "REJECTED: --project must be the test project folder"
        command = [sys.executable, "-B", str(RUNTIME), "--config-dir", str(self.config), *args]
        done = subprocess.run(command, capture_output=True, text=True, cwd=self.tmp, timeout=120,
                              env={"PATH": os.environ.get("PATH", ""), "HOME": str(self.tmp)})
        log.append({"argv": args, "subcommand": args[0], "rc": done.returncode, "line": line})
        out = (done.stdout + done.stderr)[:3000]
        return f"exit={done.returncode}\n{out}"


RUBRIC = {
    "strengths": "The reply names at least one concrete strength that is visible in the candidate's actual answer.",
    "improvements": "The reply gives at least one specific, actionable improvement tied to what is missing in the candidate's actual answer.",
    "no_invention": "The reply does not attribute experiences, numbers, tools or outcomes to the candidate that the candidate did not state. Restating what the candidate said is not invention.",
    "reason": "The reply states concretely what is missing from the candidate's answer (for example the situation, the candidate's own action, a decision or the result).",
    "followup": "The reply asks the candidate to supply the missing evidence, with a fitting question or prompt (for example to describe a real example).",
    "score_cautious": "If the reply gives a numeric score, it is low or explicitly provisional and justified by the missing evidence; the reply does not present the answer as strong.",
    "save_failed_honestly": "The reply states that saving failed or is incomplete, does not claim that anything was saved successfully, and names the error or the recovery option (or offers a new storage choice).",
    "confirm_question": "The reply restates the facts the candidate gave and asks the candidate to confirm or correct them.",
    "participants_question": "The reply asks who will conduct the interview (names or functions) and makes clear that 'unknown' is acceptable.",
    "one_question": "The reply poses a single interview question or task for the candidate to answer. Sub-aspects of that one question (for example situation, action, result) are fine; several separate, unrelated questions are not.",
    "single_followup": "The reply asks for the missing evidence with ONE question or ONE task (it may name the aspects wanted, but it is not a list of several separate questions).",
    "no_success_claim": "The reply does NOT claim that anything (run, state, profile) was saved, stored or verified successfully; it reports the failure instead.",
    "no_attribution": "The reply does not treat any one of the namesakes (or a role) as THE interviewer and does not ascribe expertise, preferences or intentions to the actual interviewer; it asks the user to disambiguate first. Listing the possible namesakes with their documented roles as options, clearly attributed to the sources, is fine.",
    "reuses_research": "The reply makes clear that stored research/preparation is reused rather than starting from scratch.",
}
SCORE = re.compile(r"(?<![\d.,])(\d{1,2}(?:[.,]\d)?)\s*/\s*10\b")


def judge_prompt(items, user, reply):
    rules = "\n".join(f"- {key}: {RUBRIC[key]}" for key in items)
    return ("You are a strict grader of a fictional interview-coaching test. Judge ONLY the assistant reply against each rule. "
            "Answer with one JSON object mapping every rule key to true or false. If you answer false for no_invention, add a key \"invented\" with a list of EXACT quotes from the assistant reply that state something the candidate never said. Nothing else.\n\nRULES:\n" + rules
            + f"\n\nCANDIDATE MESSAGE:\n{user}\n\nASSISTANT REPLY:\n{reply}\n")


def run_judge(judge, items, user, reply):
    """Return ({item: bool}, [problems]). A missing judge leaves the semantic items UNCHECKED (reported, never passed)."""
    if not items:
        return {}, []
    if judge is None:
        return {}, [f"semantic rubric not checked (no judge available): {', '.join(items)}"]
    raw = judge(judge_prompt(items, user, reply))
    match = re.search(r"\{.*\}", raw, re.S)
    try:
        verdict = json.loads(match.group(0)) if match else {}
    except ValueError:
        verdict = {}
    problems = []
    for key in items:
        if verdict.get(key) is True:
            continue
        if key == "no_invention" and not verified_inventions(verdict.get("invented"), user, reply):
            continue  # the judge could not point to a quote with content that the candidate did not provide: not counted
        problems.append(f"rubric failed: {key}")
    return {key: key not in "".join(problems) for key in items}, problems


def _tokens(text):
    return {t for t in re.findall(r"[A-Za-zÄÖÜäöüß0-9][A-Za-zÄÖÜäöüß0-9\-]{4,}", text.casefold())}


def verified_inventions(quotes, user, reply):
    """Keep only judge quotes that really occur in the reply AND carry content words absent from the candidate's message."""
    confirmed = []
    for quote in quotes or []:
        if not isinstance(quote, str) or quote.casefold() not in reply.casefold():
            continue
        novel = _tokens(quote) - _tokens(user)
        if novel:
            confirmed.append((quote, sorted(novel)[:5]))
    return confirmed


def structural_errors(step, reply):
    """Deterministic checks on the shape of an evaluation; independent of wording."""
    errors = []
    if step.get("evaluable"):
        scores = SCORE.findall(reply)
        if not scores:
            errors.append("evaluable answer: no overall score x/10")
        if len(scores) < 3:
            errors.append("evaluable answer: overall score plus at least two criterion scores expected")
        if len(reply.strip()) < 350:
            errors.append("evaluable answer: feedback is not substantial")
    if step.get("needs_evidence") and len(reply.strip()) < 120:
        errors.append("insufficient answer: no concrete reasoning")
    return errors


SAVED = re.compile(r"(?i)(?<!nicht )(?<!kein )(?<!nichts )(?:wurde|wurden|ist|sind|habe|haben)\b[^.\n]{0,60}\b(?:gespeichert|abgelegt|verifiziert)\b")
NEGATED = re.compile(r"(?i)\b(?:nicht|nichts|kein|keine|konnte nicht|fehlgeschlagen|ohne)\b[^.\n]{0,40}\b(?:gespeichert|abgelegt|persistiert)\b|\b(?:gespeichert|abgelegt|persistiert)\b[^.\n]{0,40}\b(?:nicht|nichts|kein)\b|\b(?:gespeichert|abgelegt)\b[^.\n]{0,20}\bwurde\s+nicht\b")


def claims_saved(reply):
    """True if the reply asserts a successful save (negated statements do not count)."""
    return any(not NEGATED.search(sentence) and SAVED.search(sentence) for sentence in re.split(r"(?<=[.!?\n])\s+", reply))


def extract_tool_lines(text):
    return [line.strip()[5:].strip() for line in text.splitlines() if line.strip().startswith("TOOL:")]


WRITE = re.compile(r"^WRITE_FILE:[ \t]*(\S+)[ \t]*\n<<<\n(.*?)\n>>>[ \t]*$", re.S | re.M)


def extract_writes(text):
    return [(m.group(1), m.group(2)) for m in WRITE.finditer(text)]


def build_prompt(context, scenario, env, history, user):
    transcript = "\n\n".join(f"{role.upper()}:\n{message}" for role, message in history)
    return (f"{PROTOCOL.format(runtime=RUNTIME)}\n\nThis is a fictional regression simulation. No real candidate exists.\n\n"
            f"{context}\n\nTEST CONTEXT:\n{fill(scenario['context'], env)}\n\nPRIOR CONVERSATION:\n{transcript or '(none)'}\n\n"
            f"LATEST USER MESSAGE:\n{user}\n\nRespond only to the latest user message.")


def run_turn(model, sandbox, context, scenario, history, user, log):
    prompt = build_prompt(context, scenario, sandbox.env, history, user)
    activity = []
    for _ in range(MAX_TOOL_ROUNDS):
        reply = model(prompt)
        lines = extract_tool_lines(reply)
        writes = extract_writes(reply)
        if not lines and not writes:
            return reply, activity
        results = []
        for target, content in writes:
            result = sandbox.write(target, content, log)
            activity.append(f"WRITE_FILE: {target}\n{result}")
            results.append(f"WRITE_FILE: {target}\n{result}")
        for line in lines:
            result = sandbox.execute(line, log)
            activity.append(f"TOOL: {line}\n{result}")
            results.append(f"TOOL: {line}\n{result}")
        prompt += f"\n\nYOUR PREVIOUS REPLY:\n{reply}\n\nTOOL RESULTS:\n" + "\n\n".join(results) + "\n\nContinue: answer the user or call further tools."
    return "(tool round limit reached)", activity


SAVE_COMMANDS = {"finish", "profile-save", "cv-import", "cv-draft-save", "job-create", "job-add", "job-update", "candidate-create"}
OK_EXIT = {"candidate-resolve": (0, 2)}  # exit 2 is the runtime's defined 'ambiguous or unknown: ask the user' answer


def evaluate_tools(step, log, start, reply="", judged=False):
    calls = [e for e in log[start:] if "subcommand" in e]
    ok = [e for e in calls if e["rc"] in OK_EXIT.get(e["subcommand"], (0,))]
    failed = [e for e in calls if e not in ok]
    joined = " ".join(e["line"] for e in ok)
    attempted = " ".join(e["line"] for e in calls)
    errors = []
    if step.get("no_tool_calls") and log[start:]:
        errors.append("tool calls issued although none are allowed")
    for needed in step.get("tools_include", []):  # only SUCCESSFUL calls count as evidence
        if not any(needed == e["subcommand"] for e in ok) and needed not in joined:
            errors.append(f"missing successful tool call: {needed}" + (" (call failed)" if needed in attempted else ""))
    for needed in step.get("tools_attempted", []):
        if needed not in attempted:
            errors.append(f"tool call not attempted: {needed}")
    for needed in step.get("tools_must_fail", []):
        if not any(needed in e["line"] for e in failed):
            errors.append(f"expected a failing tool call: {needed}")
    for banned in step.get("tools_exclude", []):
        if banned in attempted:
            errors.append(f"forbidden tool call: {banned}")
    if failed and not judged and claims_saved(reply) and not any(e["subcommand"] in ("finish", "profile-save", "cv-import", "job-create", "job-add",
                                                                  "candidate-create") and e["rc"] == 0 for e in calls):
        errors.append("reply claims a successful save although the save command failed")
    return errors


def run_headers(sandbox):
    result = {}
    for path in sorted(glob.glob(str(sandbox.tmp / "ws/candidates/*/runs/*.md"))):
        first = Path(path).read_text(encoding="utf-8").splitlines()[0]
        result[Path(path).stem] = (path, json.loads(first[len("<!-- zyris-run: "):-4]))
    return result


def check_artifacts(sandbox, checks, snapshots=None):
    errors = []
    snapshots = snapshots or {}
    for item in checks:
        pattern = str(sandbox.tmp / fill(item["glob"], sandbox.env)) if "glob" in item else None
        matches = sorted(glob.glob(pattern)) if pattern else []
        kind = item["type"]
        if kind == "exists" and not matches:
            errors.append(f"artifact missing: {item['glob']}")
        elif kind == "absent" and (Path(sandbox.tmp / item["path"]).exists()):
            errors.append(f"unexpected path exists: {item['path']}")
        elif kind == "no_files" and any(p.is_file() for p in (sandbox.tmp / item["path"]).rglob("*") if (sandbox.tmp / item["path"]).exists()):
            errors.append(f"unexpected files under {item['path']}")
        elif kind == "count" and len(matches) != item["equals"]:
            errors.append(f"expected {item['equals']} of {item['glob']}, found {len(matches)}")
        elif kind == "sha_equals":
            expected = hashlib.sha256((sandbox.files / item["file"]).read_bytes()).hexdigest()
            if not matches or any(hashlib.sha256(Path(m).read_bytes()).hexdigest() != expected for m in matches):
                errors.append(f"original not byte-exact: {item['glob']}")
        elif kind == "contains" and not any(item["text"] in Path(m).read_text(encoding="utf-8", errors="replace") for m in matches):
            errors.append(f"text {item['text']!r} not found in {item['glob']}")
        elif kind == "continuation":
            runs = run_headers(sandbox)
            pairs = [(runs[m["resume_from"]][1], m) for m in (v[1] for v in runs.values()) if m["resume_from"] in runs]
            if not pairs:
                errors.append("no continuation run with a valid predecessor reference was saved")
            for previous, nxt in pairs:
                if previous["status"] != "paused" or nxt["candidate_id"] != previous["candidate_id"] or nxt["job_id"] != previous["job_id"]:
                    errors.append("continuation: predecessor/candidate/job assignment inconsistent")
                if not nxt["answered_count"] > previous["answered_count"]:
                    errors.append("continuation: answered_count did not grow (no further answer was saved)")
                if nxt["planned_count"] != previous["planned_count"]:
                    errors.append("continuation: planned_count not preserved")
        elif kind == "unchanged_since_step":
            before = snapshots.get(item["step"], {})
            if not before:
                errors.append(f"no snapshot for step {item['step']}")
            for path, digest in before.items():
                if not Path(path).is_file() or hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
                    errors.append(f"immutable file changed: {Path(path).name}")
        elif kind == "run_field":
            runs = [h for _, h in run_headers(sandbox).values()]
            if not any(all(h.get(k) == v for k, v in item["equals"].items()) for h in runs):
                errors.append(f"no run header with {item['equals']}")
        elif kind == "json_field":
            ok = False
            for m in matches:
                value = json.loads(Path(m).read_text(encoding="utf-8"))
                for part in item["path"].split("."):
                    value = value.get(part) if isinstance(value, dict) else None
                ok = ok or value == item["equals"]
            if not ok:
                errors.append(f"{item['glob']}:{item['path']} != {item['equals']!r}")
    return errors


def run_scenario(scenario, model, context=None, judge=None):
    context = context if context is not None else skill_context()
    sandbox = Sandbox(scenario)
    log, history, results, snapshots = [], [], [], {}
    try:
        for index, step in enumerate(scenario["steps"], 1):
            user = fill(step["user"], sandbox.env)
            start = len(log)
            reply, activity = run_turn(model, sandbox, context, scenario, history, user, log)
            expect = json.loads(fill(json.dumps({"must_contain_any": step.get("must_contain_any", [""]),
                                                 "must_not_contain": step.get("must_not_contain", []),
                                                 "required_groups": step.get("required_groups", [])}), {k: json.dumps(str(v))[1:-1] for k, v in sandbox.env.items()}))
            errors = check(expect, reply)
            failed_save = any("subcommand" in e and e["rc"] not in OK_EXIT.get(e["subcommand"], (0,)) and e["subcommand"] in SAVE_COMMANDS for e in log[start:])
            judge_items = list(step.get("judge", [])) + (["no_success_claim"] if failed_save and judge is not None and "no_success_claim" not in step.get("judge", []) else [])
            errors += evaluate_tools(step, log, start, reply, judged=judge is not None)
            errors += structural_errors(step, reply)
            _, judge_problems = run_judge(judge, judge_items, user, reply)
            errors += judge_problems
            results.append({"step": index, "errors": errors, "reply": reply, "tools": [e.get("line") or e.get("rejected") for e in log[start:]]})
            snapshots[index] = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
                                for p in glob.glob(str(sandbox.tmp / "ws/candidates/*/runs/*.md"))}
            history.append(("user", user))
            history.append(("assistant", ("\n".join(activity) + "\n" if activity else "") + reply))
        final = check_artifacts(sandbox, scenario.get("artifacts", []), snapshots)
        return {"id": scenario["id"], "steps": results, "artifact_errors": final, "tool_log": log,
                "judge": judge is not None, "passed": not final and not any(r["errors"] for r in results)}
    finally:
        sandbox.cleanup()


def cli_model(cli, timeout, workdir, codex_sandbox="workspace-write"):
    def call(prompt):
        if cli == "claude":
            cmd = ["claude", "-p", prompt, "--output-format", "text", "--tools", "", "--no-session-persistence",
                   "--disable-slash-commands", "--strict-mcp-config", "--setting-sources", "project"]
        else:
            cmd = ["codex", "exec", "--skip-git-repo-check", "--ephemeral", "--ignore-user-config", "--ignore-rules",
                   "--sandbox", codex_sandbox, "-C", str(workdir), prompt]
        done = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True, timeout=timeout)
        if done.returncode:
            raise RuntimeError(f"{cli} exited {done.returncode}: {done.stderr[:300]}")
        return done.stdout
    return call


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cli", choices=("claude", "codex"))
    p.add_argument("--scenario", help="single scenario id")
    p.add_argument("--timeout", type=int, default=240)
    p.add_argument("--output-dir", type=Path)
    p.add_argument("--list", action="store_true")
    p.add_argument("--codex-sandbox", choices=("read-only", "workspace-write"), default="workspace-write",
                   help="read-only makes Codex report \"no write access\" and skip the TOOL channel (observed); workspace-write confines it to a temporary directory")
    p.add_argument("--no-judge", action="store_true", help="skip the rubric judge; semantic rubric items are then reported as unchecked failures")
    args = p.parse_args()
    ids = [args.scenario] if args.scenario else all_ids()
    if args.list:
        print("\n".join(ids))
        return 0
    if not args.cli or not shutil.which(args.cli):
        print(f"NOT RUN: CLI {args.cli!r} not available", file=sys.stderr)
        return 2
    out = args.output_dir or ROOT / ".tmp/tests/scenarios" / args.cli
    out.mkdir(parents=True, exist_ok=True)
    failures = 0
    with tempfile.TemporaryDirectory(prefix="coach-model-cwd-") as workdir:
        model = cli_model(args.cli, args.timeout, workdir, args.codex_sandbox)
        judge = None if args.no_judge else model
        for name in ids:
            try:
                result = run_scenario(load(name), model, judge=judge)
            except (RuntimeError, subprocess.TimeoutExpired) as exc:
                result = {"id": name, "passed": False, "error": str(exc), "steps": [], "artifact_errors": [], "tool_log": []}
            (out / f"{name}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
            print(("PASS " if result["passed"] else "FAIL ") + name)
            if result.get("error"):
                print("  - " + result["error"])
            for step in result["steps"]:
                for error in step["errors"]:
                    print(f"  - step {step['step']}: {error}")
            for error in result["artifact_errors"]:
                print("  - artifacts: " + error)
            failures += not result["passed"]
    print(f"{len(ids) - failures}/{len(ids)} heuristic scenarios passed; review the saved transcripts manually.")
    return int(bool(failures))


if __name__ == "__main__":
    sys.exit(main())
