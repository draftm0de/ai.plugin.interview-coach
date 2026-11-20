#!/usr/bin/env python3
"""Multi-turn host acceptance of the follow-up dialogue (explicit, consumes model credits; observation of ONE run per scenario).

Real Claude Code / Codex CLI in an isolated temporary project (fictional data, payload copy; nothing is installed, personal
plugin configuration is untouched). Turns of one scenario share a host session (Claude: --session-id/--resume, Codex: exec resume);
a pause is resumed in a NEW session. The host stores its own session transcripts in its normal session directory.
Scenarios: stop (follow-up -> addition -> rating -> STOP -> saved run), pause (pause with open follow-up -> new session -> resume ->
answer -> STOP), nostorage (same dialogue, no runtime call, no file). Automatic checks (structure, runtime calls, stored run
verified with the real runtime) are separate from the transcript saved for manual domain review. A timeout is ABORTED, never PASS.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_native as native  # noqa: E402
sys.path.insert(0, str(HERE.parent / "behavior"))
import run_scenarios as scenarios  # noqa: E402  (claims_saved: reply text that asserts a successful save)

iw = native.iw
Q_ADR = ("Zwei Teams streiten über die Architektur eines neuen Moduls, und der Release-Termin in drei Wochen steht fest. "
         "Wie lösen Sie diesen Architekturkonflikt?")
A_ADR = ("Ich würde die beiden Optionen in einem ADR festhalten, Pro und Contra mit Kriterien wie Wartbarkeit und Betriebsaufwand "
         "aufschreiben, mit beiden Teams durchgehen und am Ende als Verantwortliche die Entscheidung treffen und im ADR begründen.")
A_ADR2 = ("Wegen des Termins würde ich den Umfang für den Release auf das Nötigste reduzieren, die schwierigere Option nach dem Release "
          "nachziehen und das als bewusste technische Schuld im ADR vermerken. Das Produktmanagement informiere ich vorab.")
LEAK = re.compile(r"(?i)reduzier|nachzieh|technische schuld|kompromiss|mvp|umfang (kürz|reduz)|musterantwort|bessere gesprochene|was ich verbessern")
SCORE = re.compile(r"(?<![\d.,])\d{1,2}(?:[.,]\d)?\s*/\s*10\b")


class SessionHost(native.Host):
    """Host with session continuity. `invoke(text, session)`: session = {"id": ..., "started": bool}."""

    def __init__(self, name, project, payload, config, timeout, web=False):
        self.name, self.project, self.payload, self.config, self.timeout, self.web = name, project, payload, config, timeout, web
        if name == "codex" and not (project / ".agents/skills").exists():
            native.shutil.copytree(payload / "skills", project / ".agents/skills")

    def invoke(self, text, session, skill=None):
        env = dict(native.os.environ, XDG_CONFIG_HOME=str(self.config))
        prefix = (f"/interview-coach:{skill} " if self.name == "claude" else f"${skill} ") if skill else ""
        if self.name == "claude":
            cmd = ["claude", "-p", prefix + text, "--plugin-dir", str(self.payload), "--setting-sources", "project",
                   "--permission-mode", "acceptEdits", "--allowedTools", "Skill", "Bash(python3 *)", "Read", "Write",
                   "--output-format", "stream-json", "--verbose",
                   *(["--resume", session["id"]] if session["started"] else ["--session-id", session["id"]])]
        elif not session["started"]:
            cmd = ["codex", "exec", "--json", "--skip-git-repo-check", "--ignore-user-config", "--ignore-rules",
                   "--sandbox", "workspace-write", "-C", str(self.project), prefix + text]
        else:
            cmd = ["codex", "exec", "resume", "--json", "--skip-git-repo-check", "--ignore-user-config", "--ignore-rules",
                   "-c", 'sandbox_mode="workspace-write"', session["id"], text]
        done = subprocess.run(cmd, cwd=self.project, env=env, capture_output=True, text=True, timeout=self.timeout)
        result = self.parse(done)
        if self.name == "codex" and not session["started"]:
            for line in done.stdout.splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if event.get("type") == "thread.started" and event.get("thread_id"):
                    session["id"] = event["thread_id"]
        session["started"] = True
        result["session"] = session["id"]
        return result


class Scenario:
    def __init__(self, host, timeout, keep):
        self.run = native.Run(host, timeout, keep)
        self.run.host = SessionHost(host, self.run.project, self.run.payload, self.run.config, timeout)
        self.host_name = host
        self.turns, self.checks, self.status, self.note = [], [], "PASS", ""

    def new_session(self):
        return {"id": str(uuid.uuid4()) if self.host_name == "claude" else None, "started": False}

    def prepare(self):
        rt, project = self.run.rt, self.run.project
        assert rt("project-init", "--project", project, "--storage", "local", "--path", self.run.ws)[0] == 0
        cid = json.loads(rt("candidate-create", "--project", project, "--name", "Erika Beispiel")[1])["candidate_id"]
        profile = self.run.files / "profile.md"
        profile.write_text("# Profil Erika Beispiel (fiktiv)\n- Backend-Entwicklerin, 5 Jahre Python (Quelle: Nutzerangabe)\n")
        assert rt("profile-save", "--project", project, "--candidate", cid, "--file", profile, "--status", "confirmed", "--origin", "interview", "--user-confirmed")[0] == 0
        assert rt("set-interview-language", "--project", project, "--candidate", cid, "--language", "de")[0] == 0
        self.cid = cid

    def turn(self, label, text, session, skill=None):
        try:
            result = self.run.host.invoke(text, session, skill)
        except subprocess.TimeoutExpired:
            self.status, self.note = "ABORTED", f"timeout in turn {label}"
            self.turns.append({"turn": label, "user": text, "timeout": True})
            raise
        result["ok_subcommands"] = native.subcommands(result, ok_only=True)
        self.turns.append({"turn": label, "user": text, "reply": result["text"], "subcommands": native.subcommands(result),
                           "ok_subcommands": result["ok_subcommands"], "exit": result["exit"], "session": result["session"]})
        return result

    def check(self, name, ok, detail=None):
        self.checks.append({"check": name, "ok": bool(ok), "detail": detail})
        if not ok and self.status == "PASS":
            self.status = "FAIL"

    def runs(self):
        folder = self.run.ws / "candidates" / getattr(self, "cid", "x") / "runs"
        return {p.stem: (iw.parse_header(p.read_text(encoding="utf-8"), iw.HEADER, "run")[0], hashlib.sha256(p.read_bytes()).hexdigest())
                for p in sorted(folder.glob("*.md"))} if folder.is_dir() else {}


# Facts the scripted candidate answers state, each with the form of a FALSE "missing" claim about it (evidence fidelity of the rating).
STATED_FACTS = {
    "team involvement (answer: 'mit beiden Teams durchgehen')": (
        re.compile(r"(?i)mit beiden Teams durchgehen"),
        re.compile(r"(?i)\b(?:fehl\w*|nicht|kein\w*|ohne)\b[^.\n]{0,80}\b(?:Teams?\s+(?:einbind\w*|anhör\w*|einbezieh\w*)|(?:Team-?)?Einbindung|Teameinbindung)")),
    "decision owner (answer: 'als Verantwortliche die Entscheidung treffen')": (
        re.compile(r"(?i)als Verantwortliche die Entscheidung treffen"),
        re.compile(r"(?i)\b(?:fehl\w*|nicht (?:gesagt|genannt|klar)|unklar)\b[^.\n]{0,60}\bwer\b[^.\n]{0,30}\b(?:entscheidet|die Entscheidung trifft)")),
    "product management informed (answer: 'Das Produktmanagement informiere ich vorab')": (
        re.compile(r"(?i)Produktmanagement informiere ich vorab"),
        re.compile(r"(?i)\b(?:fehl\w*|nicht (?:gesagt|genannt|erwähnt))\b[^.\n]{0,60}Produktmanagement")),
}


def false_missing_claims(answers, reply):
    """Names of stated facts that the reply calls missing although the scripted candidate said them (reply sentences are checked one by one)."""
    sentences = re.split(r"(?<=[.!?])\s+|\n+", reply)
    return [name for name, (said, claim) in STATED_FACTS.items() if said.search(answers) and any(claim.search(s) for s in sentences)]


def rating_checks(sc, label, reply, answers=None):
    answers = answers or (A_ADR + " " + A_ADR2)
    wrong = false_missing_claims(answers, reply)
    sc.check(f"{label}: rating does not call stated facts missing (evidence fidelity)", not wrong, wrong)


def stop_checks(sc, label, reply):
    """STOP is final (`stopped_early`): the closing answer must not promise to resume the open follow-up (only `pause` keeps a checkpoint)."""
    sc.check(f"{label}: STOP reply does not promise to resume the open follow-up or session", not scenarios.promises_resume(reply), reply[:300])
    rating_checks(sc, label, reply)


def one_followup(sc, label, reply):
    sc.check(f"{label}: exactly one question mark", reply.count("?") == 1, reply.count("?"))
    sc.check(f"{label}: addresses the deadline", re.search(r"(?i)termin|release|frist|zeit|druck", reply), None)
    sc.check(f"{label}: no rating, hint, model answer or solution revealed", not SCORE.search(reply) and not LEAK.search(reply),
             [m.group(0) for m in LEAK.finditer(reply)] + SCORE.findall(reply))


def same(a, b):
    return " ".join((a or "").split()) == " ".join(b.split())


def scenario_stop(sc):
    sc.prepare()
    s = sc.new_session()
    first = sc.turn("1 question", f"Allgemeines Training für Erika Beispiel, geplant sind 3 Fragen. Stelle mir bitte genau diese Frage als erste Hauptfrage: {Q_ADR}", s, "candidate-training")
    sc.check("1: main question asked, nothing saved", "?" in first["text"] and "finish" not in native.subcommands(first), native.subcommands(first))
    follow = sc.turn("2 incomplete answer", A_ADR, s)
    one_followup(sc, "2", follow["text"])
    sc.check("2: block still open, nothing saved", "finish" not in native.subcommands(follow), native.subcommands(follow))
    rating = sc.turn("3 addition", A_ADR2, s)
    sc.check("3: block rated after the addition", bool(SCORE.search(rating["text"])), rating["text"][:200])
    rating_checks(sc, "3", rating["text"])
    sc.check("3: first answer and addition kept apart", re.search(r"(?i)erstantwort|nachfrage|ergänz", rating["text"]), None)
    stop = sc.turn("4 stop", "stop", s)
    stop_checks(sc, "4", stop["text"])
    saved = sc.runs()
    sc.check("4: exactly one immutable run saved via a successful finish", len(saved) == 1 and "finish" in stop["ok_subcommands"], [list(saved), stop["ok_subcommands"]])
    if len(saved) == 1:
        meta = next(iter(saved.values()))[0]
        d = meta["dialogue"]
        sc.check("run: candidate, no job, stopped_early", meta["candidate_id"] == sc.cid and meta["job_id"] is None and meta["status"] == "stopped_early", {k: meta[k] for k in ("candidate_id", "job_id", "status")})
        sc.check("run: counters main/follow-up/answered/retries = 1/1/1/0",
                 (meta["answered_count"], meta["followup_count"], meta["followup_answered_count"], meta["retry_count"]) == (1, 1, 1, 0),
                 {k: meta[k] for k in ("answered_count", "followup_count", "followup_answered_count", "retry_count", "planned_count")})
        sc.check("run: only block 1 answered (a later asked main question may be stored unanswered)", bool(d) and all(b["initial_answer"] is None for b in d[1:]), [b["key"] for b in d])
        sc.check("run: main question stored as asked (verbatim)", bool(d) and same(d[0]["question"], Q_ADR), d[0]["question"] if d else None)
        sc.check("run: original answer stored verbatim", bool(d) and same(d[0]["initial_answer"], A_ADR), d[0]["initial_answer"] if d else None)
        f = d[0]["followups"] if d else []
        sc.check("run: follow-up text, kind, reason, gap and verbatim addition", len(f) == 1 and f[0]["kind"] in ("completion", "clarification") and f[0]["reason"] and f[0]["gap"] and same(f[0]["answer"], A_ADR2), f[:1])
        sc.check("run: no prior hint -> own evidence after follow-up (not supported)", len(f) == 1 and f[0]["hints_before"] is False and iw.followup_evidence(f[0]) == "after_followup", f[:1] and f[0]["hints_before"])
        sc.check("run: first answer and block assessed separately", bool(d and d[0]["initial_assessment"] and d[0]["block_assessment"]), None)
        sc.check("run: planned count 3 kept", meta["planned_count"] == 3, meta["planned_count"])


def scenario_pause(sc):
    sc.prepare()
    s = sc.new_session()
    sc.turn("1 question", f"Allgemeines Training für Erika Beispiel, geplant sind 3 Fragen. Stelle mir bitte genau diese Frage als erste Hauptfrage: {Q_ADR}", s, "candidate-training")
    follow = sc.turn("2 incomplete answer", A_ADR, s)
    one_followup(sc, "2", follow["text"])
    pause = sc.turn("3 pause", "pause", s)
    saved = sc.runs()
    sc.check("3: checkpoint saved via successful finish", len(saved) == 1 and "finish" in pause["ok_subcommands"], [list(saved), pause["ok_subcommands"]])
    if len(saved) != 1:
        return
    pid, (pmeta, phash) = next(iter(saved.items()))
    pf = pmeta["dialogue"][0]["followups"] if pmeta["dialogue"] else []
    sc.check("checkpoint: paused, 1 main answered, 1 follow-up open and unanswered, planned 3",
             (pmeta["status"], pmeta["answered_count"], pmeta["followup_count"], pmeta["followup_answered_count"], pmeta["planned_count"]) == ("paused", 1, 1, 0, 3) and len(pf) == 1 and pf[0]["answer"] is None and pf[0]["resolution"] == "pending",
             {k: pmeta[k] for k in ("status", "answered_count", "followup_count", "followup_answered_count", "planned_count")})
    sc.check("checkpoint: main question and original answer verbatim", same(pmeta["dialogue"][0]["question"], Q_ADR) and same(pmeta["dialogue"][0]["initial_answer"], A_ADR), pmeta["dialogue"][0]["question"])
    s2 = sc.new_session()   # a NEW chat resumes the stored checkpoint
    resumed = sc.turn("4 resume in a new session", "Setze das pausierte Training für Erika Beispiel fort.", s2, "candidate-training")
    sc.check("4: stored checkpoint loaded with resume", "resume" in resumed["ok_subcommands"], resumed["ok_subcommands"])
    sc.check("4: only the open follow-up is re-asked (one question, deadline, nothing revealed, no new main question)",
             resumed["text"].count("?") == 1 and re.search(r"(?i)termin|release|frist", resumed["text"]) and not SCORE.search(resumed["text"]) and not LEAK.search(resumed["text"]), resumed["text"][:300])
    after = sc.turn("5 answer", A_ADR2, s2)
    stop = sc.turn("6 stop", "stop", s2)
    stop_checks(sc, "6", stop["text"])
    runs = sc.runs()
    sc.check("6: second immutable run saved by a successful finish; checkpoint file unchanged",
             len(runs) == 2 and "finish" in stop["ok_subcommands"] and runs.get(pid, (None, None))[1] == phash, [list(runs), stop["ok_subcommands"]])
    others = [(k, v[0]) for k, v in runs.items() if k != pid]
    if len(runs) == 2 and others:
        _, meta = others[0]
        d = meta["dialogue"]
        sc.check("continuation: resume_from checkpoint, same candidate and job, planned count kept",
                 meta["resume_from"] == pid and meta["candidate_id"] == sc.cid and meta["job_id"] is None and meta["planned_count"] == 3, {k: meta[k] for k in ("resume_from", "job_id", "planned_count")})
        sc.check("continuation: no double counting (1 main, 1 follow-up asked and answered once)",
                 (meta["answered_count"], meta["followup_count"], meta["followup_answered_count"], meta["retry_count"]) == (1, 1, 1, 0) and bool(d) and len(d[0]["followups"]) == 1 and all(b["initial_answer"] is None for b in d[1:]),
                 {k: meta[k] for k in ("answered_count", "followup_count", "followup_answered_count", "retry_count")})
        sc.check("continuation: original answer, follow-up wording unchanged and the late answer verbatim",
                 same(d[0]["initial_answer"], A_ADR) and d[0]["followups"][0]["text"] == pf[0]["text"] and same(d[0]["followups"][0]["answer"], A_ADR2), d[0]["followups"][0])
        sc.check("continuation: answer after neutral follow-up is own evidence, hints_before false", d[0]["followups"][0]["hints_before"] is False, None)


def snapshot(root):
    """Relative path -> "dir" or the sha256 of the file content, for everything below `root` (symlinks are recorded, not followed)."""
    state = {}
    for path in sorted(Path(root).rglob("*")):
        rel = str(path.relative_to(root))
        if path.is_symlink():
            state[rel] = "link:" + str(path.readlink())
        elif path.is_dir():
            state[rel] = "dir"
        else:
            state[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return state


def diff_snapshots(before, after, allowed=None):
    """New, changed and deleted entries. `allowed` maps EXACT relative paths to a reason; no prefixes or patterns, a reason is mandatory."""
    allowed = allowed or {}
    for path, reason in allowed.items():
        if not str(reason).strip() or path.endswith(("/", "*")):
            raise ValueError(f"narrow exception needs an exact path and a reason: {path!r}")
    skip = set(allowed)
    return {"created": sorted(set(after) - set(before) - skip),
            "modified": sorted(p for p in set(before) & set(after) if before[p] != after[p] and p not in skip),
            "deleted": sorted(set(before) - set(after) - skip)}


def unexpected_changes(diff):
    return [f"{kind}: {path}" for kind, paths in diff.items() for path in paths]


# Host artifacts that cannot be avoided. Empty on purpose: add an EXACT path with a reason only after an observed, justified case.
NOSTORAGE_ALLOWED = {}


def scenario_nostorage(sc):
    root = sc.run.tmp / "nostorage"
    project, config = root / "project", root / "config"
    project.mkdir(parents=True)
    config.mkdir()  # pointer directory OUTSIDE the project: any file appearing there is a configuration pointer
    sc.run.host = SessionHost(sc.host_name, project, sc.run.payload, config, sc.run.host.timeout)  # prepares the host's skill copy first
    s = sc.new_session()
    before_project, before_config = snapshot(project), snapshot(config)
    sc.turn("1 question", f"Nicht speichern. Allgemeines Training für eine Team-Lead-Rolle, Interviewsprache Deutsch, geplant sind 3 Fragen. Stelle mir bitte genau diese Frage als erste Hauptfrage: {Q_ADR}", s, "candidate-training")
    follow = sc.turn("2 incomplete answer", A_ADR, s)
    one_followup(sc, "2", follow["text"])
    rating = sc.turn("3 addition", A_ADR2, s)
    sc.check("3: block rated after the addition", bool(SCORE.search(rating["text"])), rating["text"][:200])
    rating_checks(sc, "3", rating["text"])
    stop = sc.turn("4 stop", "stop", s)
    stop_checks(sc, "4", stop["text"])
    sc.check("4: chat summary given", len(stop["text"]) > 150, stop["text"][:200])
    sc.check("4: STOP reply does not claim anything was saved", not scenarios.claims_saved(stop["text"]), stop["text"][:300])
    sc.check("no turn reply claims a successful save", not [t["turn"] for t in sc.turns if scenarios.claims_saved(t.get("reply", ""))],
             [t["turn"] for t in sc.turns if scenarios.claims_saved(t.get("reply", ""))])
    runtime = [t for t in sc.turns if t.get("subcommands")]
    sc.check("no runtime call in any turn", not runtime, [t["subcommands"] for t in runtime])
    config_diff = diff_snapshots(before_config, snapshot(config))
    sc.check("no configuration pointer or any file in the pointer directory", not unexpected_changes(config_diff), config_diff)
    project_diff = diff_snapshots(before_project, snapshot(project), NOSTORAGE_ALLOWED)
    sc.check("project: no file created, changed or deleted compared with the prepared state (content hashes)", not unexpected_changes(project_diff),
             {"diff": project_diff, "files_before": len(before_project), "allowed": NOSTORAGE_ALLOWED})


SCENARIOS = {"stop": scenario_stop, "pause": scenario_pause, "nostorage": scenario_nostorage}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", choices=("claude", "codex"), required=True)
    p.add_argument("--timeout", type=int, default=420, help="seconds per host turn")
    p.add_argument("--only", help="comma separated: " + ",".join(SCENARIOS))
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--keep", action="store_true")
    args = p.parse_args()
    if not native.shutil.which(args.host):
        print(f"NOT RUN: {args.host} CLI not available")
        return 2
    results = []
    for name, fn in SCENARIOS.items():
        if args.only and name not in args.only.split(","):
            continue
        sc = Scenario(args.host, args.timeout, args.keep)
        try:
            fn(sc)
        except subprocess.TimeoutExpired:
            pass
        except Exception as exc:  # a broken precondition is a failure, never a pass
            sc.status, sc.note = "FAIL", f"{type(exc).__name__}: {exc}"
        finally:
            results.append({"scenario": name, "host": args.host, "status": sc.status, "note": sc.note, "checks": sc.checks, "turns": sc.turns})
            if args.output:
                src = sc.run.ws
                if src.exists():
                    native.shutil.copytree(src, args.output.parent / (args.output.stem + "-artifacts") / name, ignore=native.shutil.ignore_patterns(".journal"), dirs_exist_ok=True)
            sc.run.cleanup()
        print(sc.status, name, sc.note, flush=True)
        for c in sc.checks:
            if not c["ok"]:
                print("  - FAILED:", c["check"], json.dumps(c["detail"], ensure_ascii=False, default=str)[:200], flush=True)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return int(any(r["status"] != "PASS" for r in results))


if __name__ == "__main__":
    sys.exit(main())
