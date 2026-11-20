#!/usr/bin/env python3
"""Staged targeted host acceptance for job-create (E) and job-training F->G (explicit, consumes model credits, no full run).

WRAPPER_VERSION 3. Stages are separate commands that share one results directory and ONE absolute deadline (state.json):
prepare -> evidence (E) -> review-evidence -> ask (F) -> check-answer -> answer (G) -> review-answer -> status. `reload` (H) exists
but is not part of the targeted window. Waiting time between stages (including the human/agent content review) counts to the budget.

Every phase has two separate verdicts: `automatic` (structure, tool results, identities derived from host events) and `domain`
(content review against the saved artifacts). A phase is PASS only when both are PASS; automatic-only results are reported as
UNREVIEWED and never as acceptance. Review quotes must occur literally in the named artifact (the check proves the citation exists, not
that the judgement is right). There is no automatic substitute answer: an answer that is not reviewed against all parts of the
actual question keeps G BLOCKED.

No automatic retries. On timeout only the own process group is ended (TERM, then KILL after a fixed grace). Fictional data only.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WRAPPER_VERSION = "3"
TOTAL_S, RESERVE_S, MIN_PHASE_S, KILL_GRACE_S = 600, 60, 15, 3
LIMITS = {"E": 120, "F": 60, "G": 120, "H": 60}
FIXTURE_CV = "# Erika Beispiel\n\n## Berufserfahrung\n- Backend-Entwicklerin, Muster GmbH, 2019-2024\n\n## Skills\nPython, Go, SQL\n"
FIXTURE_PROFILE = ("# Profil — Erika Beispiel (bestätigt)\n\n## Berufserfahrung\n- Backend-Entwicklerin, Muster GmbH, 2019–2024 [Quelle: CV]\n\n"
                   "## Skills\n- Python [Quelle: CV]\n- Go [Quelle: CV]\n- SQL [Quelle: CV]\n")
FIXTURE_POSTING = ("# Senior Backend Engineer (m/w/d)\nBeispiel AG, Zürich\nAufgaben: Python-APIs, Kubernetes-Betrieb, Mentoring.\n"
                   "Anforderungen: 5+ Jahre Python, Cloud-Betrieb.\n")

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Deadline:
    def __init__(self, start, total=TOTAL_S, reserve=RESERVE_S):
        self.start, self.total, self.reserve = start, total, reserve
        self.end = start + total

    def phase_timeout(self, limit, now):
        """min(phase limit, remaining budget minus reserve); None when too little is left. A limit is never raised."""
        value = min(limit, self.end - self.reserve - now)
        return None if value < MIN_PHASE_S else value


def new_session_ids():
    return str(uuid.uuid4()), str(uuid.uuid4())


def build_command(claude, prompt, payload, session):
    """session = ("new", id) | ("resume", id). No --no-session-persistence, no --continue (that picks 'most recent' ambiguously)."""
    mode, sid = session
    cmd = [claude, "-p", prompt, "--plugin-dir", str(payload),
           "--setting-sources", "project", "--permission-mode", "acceptEdits", "--tools", "Skill,Bash,Read,Write",
           "--allowedTools", "Skill", "Bash(python3 *)", "Read", "Write",
           "--disallowedTools", "WebFetch", "WebSearch", "--strict-mcp-config",
           "--output-format", "stream-json", "--verbose"]
    cmd += ["--session-id", sid] if mode == "new" else ["--resume", sid]
    return cmd


def terminate_group(proc, grace=KILL_GRACE_S):
    """TERM, then KILL after a fixed grace, own process group only. Returns how it ended."""
    ended = "already-exited"
    if proc.poll() is None:
        ended = "TERM"
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            return ended
        try:
            proc.wait(grace)
        except subprocess.TimeoutExpired:
            ended = "KILL"
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait(grace)
    # any remaining member of the group (not only the leader)?
    try:
        os.killpg(proc.pid, 0)
        alive = True
    except (ProcessLookupError, PermissionError):
        alive = False
    if alive:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        time.sleep(0.2)
        ended += "+KILL-group"
    return ended


def run_process(cmd, cwd, env, timeout, outdir, name, on_start=None, clock=time.time):
    """Run ONE host process; write start record before, raw streams while running, meta after (also on timeout)."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    started = clock()
    (outdir / f"{name}.command.json").write_text(json.dumps({"args": cmd, "cwd": str(cwd), "timeout_s": round(timeout, 1)}, indent=1, ensure_ascii=False))
    (outdir / f"{name}.start.json").write_text(json.dumps({"phase": name, "start": started, "timeout_s": round(timeout, 1)}))
    with open(outdir / f"{name}.stdout.jsonl", "w") as out, open(outdir / f"{name}.stderr.txt", "w") as err:
        proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=out, stderr=err, text=True, start_new_session=True)
        if on_start:
            on_start(proc)
        timed_out, ended = False, None
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            ended = terminate_group(proc)
        else:
            ended = terminate_group(proc)   # reap leftover children of a clean exit as well
    finished = clock()
    meta = {"phase": name, "pid": proc.pid, "start": started, "end": finished, "duration_s": round(finished - started, 1),
            "exit_code": proc.returncode, "timed_out": timed_out, "ended_by": ended, "timeout_s": round(timeout, 1)}
    (outdir / f"{name}.process.json").write_text(json.dumps(meta, indent=1))
    return meta


def parse_events(text):
    """Stream-json -> tool calls with their RESULTS (full content), session ids, final text. Unmatched calls keep result None."""
    info = {"session_ids": [], "skills": [], "calls": [], "text": "", "result": None, "errors": 0}
    by_id = {}
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            info["errors"] += 1
            continue
        sid = event.get("session_id")
        if sid and sid not in info["session_ids"]:
            info["session_ids"].append(sid)
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init":
            info["skills"] = [s for s in event.get("skills", []) if "interview-coach" in s]
        elif kind == "assistant":
            for part in event.get("message", {}).get("content", []):
                if part.get("type") == "tool_use":
                    call = {"id": part.get("id"), "tool": part.get("name"), "input": part.get("input", {}), "results": []}
                    info["calls"].append(call)
                    by_id.setdefault(call["id"], []).append(call)
                elif part.get("type") == "text":
                    info["text"] = part["text"]
        elif kind == "user" and isinstance(event.get("message", {}).get("content"), list):
            for part in event["message"]["content"]:
                if isinstance(part, dict) and part.get("type") == "tool_result":
                    content = part.get("content")
                    if isinstance(content, list):
                        content = "".join(c.get("text", "") for c in content if isinstance(c, dict))
                    for call in by_id.get(part.get("tool_use_id"), []):
                        call["results"].append({"is_error": bool(part.get("is_error")), "content": content})
        elif kind == "result":
            info["result"] = {"is_error": bool(event.get("is_error")), "subtype": event.get("subtype"), "session_id": event.get("session_id")}
            info["text"] = event.get("result") or info["text"]
    for call in info["calls"]:   # ambiguous (duplicate ids) or conflicting results are never success
        ids = [c["id"] for c in info["calls"] if c["id"] == call["id"]]
        call["ok"] = len(ids) == 1 and len(call["results"]) == 1 and not call["results"][0]["is_error"]
    return info


def _load_native():
    spec = importlib.util.spec_from_file_location("run_native_for_acceptance", ROOT / "tests/native/run_native.py")
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    return module


def runtime_calls(info, subcommand=None, **expected):
    """Runtime calls that are ONE plain `python3 .../interview_workspace.py SUB --opt v` invocation. Returns (call, parsed) pairs.

    `ok` of the call comes from the host's own tool result (is_error false); a claimed save without such a call proves nothing.
    """
    native = _load_native()
    found = []
    for call in info["calls"]:
        if call["tool"] != "Bash":
            continue
        parsed = native.parse_runtime_call(call["input"].get("command", ""))
        if parsed is None or parsed["unresolved"]:
            continue
        if subcommand and parsed["subcommand"] != subcommand:
            continue
        if any(parsed["options"].get(k) != v for k, v in expected.items()):
            continue
        found.append((call, parsed))
    return found


def ok_runtime(info, subcommand, **expected):
    return [(c, p) for c, p in runtime_calls(info, subcommand, **expected) if c["ok"]]


def file_hashes(root, skip_parts=()):
    root = Path(root)
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob("*"))
            if p.is_file() and not any(part in skip_parts for part in p.relative_to(root).parts)}


def diff_hashes(before, after):
    return {"added": sorted(set(after) - set(before)), "removed": sorted(set(before) - set(after)),
            "changed": sorted(k for k in before if k in after and before[k] != after[k])}




# ---------------------------------------------------------------- question and answer fit


def norm(text):
    return re.sub(r"\s+", " ", re.sub(r"[*_`]", "", text or "")).strip().lower()


def _is_bullet(paragraph):
    return bool(re.match(r"\s*([-*•]|\d+[.)])\s+", paragraph))


def extract_question(reply):
    """The asked question including its sub-questions, taken from the reply: the LAST group of paragraphs that contain a question mark,
    plus directly attached bullet paragraphs. Returns {"block", "ambiguous"}; ambiguous = several separate question groups, so
    which one is the asked question cannot be decided from the text (G then stays BLOCKED). No question mark -> block None."""
    paragraphs = [x.strip() for x in (reply or "").split("\n\n") if x.strip()]
    marks = [i for i, x in enumerate(paragraphs) if "?" in x]
    if not marks:
        return {"block": None, "ambiguous": False}
    groups, current = [], [marks[0]]
    for i in marks[1:]:
        between = paragraphs[current[-1] + 1:i]
        if all(_is_bullet(x) for x in between):
            current.append(i)
        else:
            groups.append(current)
            current = [i]
    groups.append(current)
    last = groups[-1]
    end = last[-1] + 1
    while end < len(paragraphs) and _is_bullet(paragraphs[end]):
        end += 1
    return {"block": "\n\n".join(paragraphs[last[0]:end]), "ambiguous": len(groups) > 1}


def split_sentences(block):
    flat = re.sub(r"^\s*([-*•]|\d+[.)])\s+", "", re.sub(r"[*_`]", "", block or ""), flags=re.M)
    return [s.strip() for s in re.split(r"(?<=[.!?:])\s+|\n+", flat) if len(s.strip()) > 3]


CUES = (("retrospective", r"anders|rückblick|rückschau|im nachhinein|gelernt|lessons|heute"),
        ("example", r"beispiel|beschreib|erzähl|situation|projekt|fall"),
        ("own_decisions", r"entscheid|selbst|deine rolle|dein beitrag|verantwort"))
KINDS = {"topic", "example", "own_decisions", "retrospective", "context", "other"}


def validate_answer_fit(question_block, answer, review):
    """Check a REVIEWED answer against ALL parts of the asked question. Returns ("PASS"|"BLOCKED", reasons).

    The review is a judgement written by a reader of the question and the answer; this function only refuses reviews that are
    not tied to these texts (hashes, literal quotes), skip a sub-question, omit a part the question visibly asks for, or rely on
    shared words. A common string or topic word never counts as fit. Anything unclear -> BLOCKED, never an automatic substitute."""
    reasons = []
    if not question_block:
        return "BLOCKED", ["no question block extracted from F"]
    if not (answer or "").strip():
        return "BLOCKED", ["empty answer"]
    if not isinstance(review, dict):
        return "BLOCKED", ["review is not an object"]
    if review.get("question_sha256") != hashlib.sha256(question_block.encode()).hexdigest():
        reasons.append("review refers to another question (sha256 mismatch)")
    if review.get("answer_sha256") != hashlib.sha256(answer.encode()).hexdigest():
        reasons.append("review refers to another answer (sha256 mismatch)")
    if review.get("fictional") is not True:
        reasons.append("review must state that the answer is a fictional test answer")
    qa = review.get("question_assessment")
    if not (isinstance(qa, dict) and qa.get("concrete") is True and qa.get("job_related") is True):
        reasons.append("question not assessed as concrete and job-related")
    parts = review.get("parts")
    if not isinstance(parts, list) or not parts:
        return "BLOCKED", reasons + ["no question parts listed"]
    nq, na = norm(question_block), norm(answer)
    answered, answer_quotes = [], set()
    for number, part in enumerate(parts, 1):
        if not isinstance(part, dict) or part.get("kind") not in KINDS:
            reasons.append(f"part {number}: invalid structure or kind")
            continue
        quote = norm(part.get("question_quote"))
        if len(quote) < 8 or quote not in nq:
            reasons.append(f"part {number}: question_quote does not occur in the asked question")
            continue
        if part["kind"] == "context":
            continue
        aq = norm(part.get("answer_quote"))
        if part.get("covered") is not True:
            reasons.append(f"part {number} ({part['kind']}) is not covered by the answer")
        if len(aq.split()) < 5 or aq not in na:
            reasons.append(f"part {number}: answer_quote missing, too short or not literally in the answer")
        elif aq in nq:
            reasons.append(f"part {number}: answer_quote repeats the question; shared wording is no evidence of fit")
        else:
            answer_quotes.add(aq)
        answered.append(part)
    for sentence in split_sentences(question_block):
        s = norm(sentence)
        if not any(len(q) >= 8 and (q in s or s in q) for q in (norm(p.get("question_quote")) for p in parts if isinstance(p, dict))):
            reasons.append(f"sentence of the question is not assigned to any part: {sentence[:80]!r}")
    kinds = {p["kind"] for p in answered if p.get("covered") is True}
    for kind, cue in CUES:
        if re.search(cue, nq) and kind not in kinds:
            reasons.append(f"question text asks for '{kind}' (cue /{cue}/) but no covered part of that kind is listed")
    if len(answer_quotes) < (len(answered) + 1) // 2:
        reasons.append("too few distinct answer passages for the listed parts")
    if review.get("verdict") != "PASS":
        reasons.append(f"reviewer verdict is {review.get('verdict')!r}")
    return ("PASS", []) if not reasons else ("BLOCKED", reasons)


# ---------------------------------------------------------------- content review (domain verdict)


class ReviewError(ValueError):
    pass


EVIDENCE_CRITERIA = ("python_years_not_direct", "unmentioned_is_unsupported_not_absent", "capability_vs_evidence_gap_separated",
                     "preparation_priority_justified_as_clarification", "consistent_across_profile_match_preparation_reply",
                     "no_invented_facts_and_confirmed_scope_kept")
ANSWER_CRITERIA = ("feedback_refers_to_actual_answer", "feedback_evidence_based_no_invented_facts", "no_further_interview_question",
                   "run_and_learning_state_match_the_stop", "save_report_truthful")


def validate_review(review, material, required):
    """Domain review -> ("PASS"|"FAIL", per-criterion). Raises ReviewError when the review is not usable (missing criterion, no
    quote, quote not literally in the named artifact, verdict contradicting the criteria). The quotes prove that the review read
    the artifacts; they do not make the judgement correct."""
    if not isinstance(review, dict) or not isinstance(review.get("criteria"), list):
        raise ReviewError("review needs a criteria list")
    by_id = {c.get("id"): c for c in review["criteria"] if isinstance(c, dict)}
    results = {}
    for rid in required:
        c = by_id.get(rid)
        if c is None:
            raise ReviewError(f"criterion missing: {rid}")
        if c.get("verdict") not in ("PASS", "FAIL") or not str(c.get("finding", "")).strip():
            raise ReviewError(f"{rid}: needs verdict PASS|FAIL and a finding")
        quotes = c.get("quotes")
        if not isinstance(quotes, list) or not quotes:
            raise ReviewError(f"{rid}: needs at least one quote")
        for q in quotes:
            artifact, text = (q or {}).get("artifact"), (q or {}).get("text")
            if artifact not in material:
                raise ReviewError(f"{rid}: unknown artifact {artifact!r}")
            if len(norm(text)) < 12 or norm(text) not in norm(material[artifact]):
                raise ReviewError(f"{rid}: quote not literally in {artifact}")
        results[rid] = c["verdict"]
    computed = "PASS" if all(v == "PASS" for v in results.values()) else "FAIL"
    if review.get("verdict") != computed:
        raise ReviewError(f"overall verdict {review.get('verdict')!r} contradicts criteria ({computed})")
    return computed, results


# ---------------------------------------------------------------- verdicts, identities, fingerprints


def check(name, ok, evidence):
    return {"check": name, "ok": bool(ok), "evidence": evidence}


def auto_verdict(checks):
    """Automatic (structural) verdict only: PASS/FAIL/BLOCKED. Never an acceptance on its own."""
    if not checks:
        return "BLOCKED"
    return "PASS" if all(c["ok"] for c in checks) else "FAIL"


def final_verdict(automatic, domain):
    """Phase verdict from both parts. PASS needs automatic PASS and domain PASS; automatic PASS without review is UNREVIEWED."""
    if automatic != "PASS":
        return automatic
    if domain == "PASS":
        return "PASS"
    if domain == "NOT REVIEWED":
        return "UNREVIEWED"
    return domain if domain in ("FAIL", "BLOCKED", "NOT RUN") else "BLOCKED"


def exit_code(final):
    """0 only for a verified PASS; 1 FAIL; 2 BLOCKED/NOT RUN; 3 UNREVIEWED (automatic checks only)."""
    return {"PASS": 0, "FAIL": 1, "UNREVIEWED": 3}.get(final, 2)


def same_path(a, b):
    return bool(a) and bool(b) and os.path.realpath(a) == os.path.realpath(b)


def ok_identity(info, subcommand, project, candidate=None, job=None, job_keys=("job", "job-id"), **options):
    """Successful runtime calls whose options carry the expected identity ALL AT ONCE: project path, candidate id, job id (and extra
    option values). A missing option is a mismatch; success of the tool result alone is never enough."""
    found = []
    for call, parsed in ok_runtime(info, subcommand):
        o = parsed["options"]
        if not same_path(o.get("project"), project):
            continue
        if candidate is not None and o.get("candidate") != candidate:
            continue
        if job is not None and not any(o.get(k) == job for k in job_keys):
            continue
        if any(o.get(k) != v for k, v in options.items()):
            continue
        found.append((call, parsed))
    return found


def session_identity_ok(requested, seen):
    """The requested session id must be the one (and only one) the host events report."""
    return bool(requested) and list(seen) == [requested]


def check_h_session(requested, f_id, seen):
    """H: the requested NEW id appears in the host events, is not the F/G id, and the F/G id does not appear."""
    return bool(requested) and requested != f_id and session_identity_ok(requested, seen) and f_id not in seen


def tree_fingerprint(root, subdir="skills"):
    base = Path(root) / subdir
    parts = {str(p.relative_to(base)): sha(p) for p in sorted(base.rglob("*")) if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
    return {"aggregate": hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest(), "files": len(parts)}


def evidence_current(recorded_aggregate, current_aggregate):
    """A host observation only counts for the source state it ran against."""
    return bool(recorded_aggregate) and recorded_aggregate == current_aggregate


# ---------------------------------------------------------------- staged orchestration


def read_state(res):
    return json.loads((Path(res) / "state.json").read_text())


def write_state(res, state):
    (Path(res) / "state.json").write_text(json.dumps(state, indent=1, ensure_ascii=False, default=str))


def write(res, name, data):
    path = Path(res) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data, indent=1, ensure_ascii=False, default=str))


def set_phase(state, name, automatic=None, domain=None, note=None):
    ph = state["phases"].setdefault(name, {"automatic": "NOT RUN", "domain": "NOT RUN", "note": ""})
    if automatic is not None:
        ph["automatic"] = automatic
    if domain is not None:
        ph["domain"] = domain
    if note is not None:
        ph["note"] = note
    ph["final"] = final_verdict(ph["automatic"], ph["domain"])
    return ph


def report(res, state, name):
    ph = state["phases"][name]
    write_state(res, state)
    print(json.dumps({"phase": name, "automatic": ph["automatic"], "domain": ph["domain"], "final": ph["final"], "note": ph.get("note", "")}, ensure_ascii=False))
    return exit_code(ph["final"])


def runtime(state, *a):
    done = subprocess.run([sys.executable, "-B", state["rt"], "--config-dir", state["cfgdir"], *map(str, a)], capture_output=True, text=True, timeout=20)
    return done.returncode, done.stdout, done.stderr


def prepare(res, claude):
    start = time.time()
    res = Path(res).resolve()
    res.mkdir(parents=True, exist_ok=True)
    state = {"wrapper_version": WRAPPER_VERSION, "start": start, "deadline": start + TOTAL_S, "reserve_s": RESERVE_S, "claude": claude,
             "res": str(res), "phases": {}}
    write_state(res, state)   # deadline is fixed BEFORE any preparation
    tmp = Path(tempfile.mkdtemp(prefix="coach-hostacc3-")).resolve()
    payload, project = tmp / "plugin", tmp / "project"
    for n in ("skills", "assets", ".claude-plugin", ".codex-plugin"):
        shutil.copytree(ROOT / n, payload / n, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (payload / "README.md").write_text("Interview Coach payload copy for host acceptance.\n")
    (project / "files").mkdir(parents=True)
    (project / "files/cv.md").write_text(FIXTURE_CV)
    (project / "files/posting.md").write_text(FIXTURE_POSTING)
    (project / "files/profile.md").write_text(FIXTURE_PROFILE)
    cfg = project / ".cfg"
    state.update({"tmp": str(tmp), "payload": str(payload), "project": str(project), "ws": str(project / "storage"), "cfg": str(cfg),
                  "cfgdir": str(cfg / "zyris/interview-coach/projects"), "rt": str(payload / "skills/_shared/scripts/interview_workspace.py")})
    version = subprocess.run([claude, "--version"], capture_output=True, text=True, timeout=15).stdout.strip()
    help_text = subprocess.run([claude, "--help"], capture_output=True, text=True, timeout=15).stdout
    src, pay = tree_fingerprint(ROOT), tree_fingerprint(payload)
    state["fingerprints"] = {"source_skills": src, "payload_skills": pay, "wrapper": sha(__file__), "payload_equals_source": src["aggregate"] == pay["aggregate"],
                             "payload_files": file_hashes(payload / "skills")}
    state["sessions_supported"] = "--session-id" in help_text and "--resume" in help_text
    state["sessions"] = {"fg": str(uuid.uuid4()), "h": str(uuid.uuid4())}
    write(res, "00-setup.json", {"wrapper_version": WRAPPER_VERSION, "claude_version": version, "start": start, "deadline": state["deadline"],
                                 "loading": "claude -p --plugin-dir <isolated payload copy> --setting-sources project --strict-mcp-config; native skill loading, "
                                            "no skill text in prompts; F --session-id X, G --resume X", "fingerprints": state["fingerprints"],
                                 "sessions_supported_by_cli_help": state["sessions_supported"], "tmp": str(tmp), "project": str(project)})
    log, ok = [], True
    proj = str(project)

    def step(*a):
        rc, out, err = runtime(state, *a)
        log.append({"args": [str(x) for x in a], "rc": rc, "stdout": out, "stderr": err})
        if rc != 0:
            raise RuntimeError(f"fixture step failed: {a[0]} rc={rc} {err[:200]}")
        return json.loads(out) if out.strip().startswith(("{", "[")) else out

    try:
        step("project-init", "--project", proj, "--storage", "local", "--path", state["ws"])
        step("set-language", "--project", proj, "--interface", "de")
        state["candidate"] = step("candidate-create", "--project", proj, "--name", "Erika Beispiel")["candidate_id"]
        step("set-interview-language", "--project", proj, "--candidate", state["candidate"], "--language", "de")
        step("cv-import", "--project", proj, "--candidate", state["candidate"], "--file", str(project / "files/cv.md"))
        step("profile-save", "--project", proj, "--candidate", state["candidate"], "--file", str(project / "files/profile.md"), "--status", "confirmed",
             "--origin", "cv", "--cv-source", "cv-001", "--user-confirmed", "--acknowledge-gaps")
        step("candidate-list", "--project", proj)
    except Exception as exc:   # noqa: BLE001 - logged; every phase BLOCKED
        log.append({"error": str(exc)})
        ok = False
    write(res, "01-fixture.json", {"note": "Deterministic fixture via the runtime; NOT a host acceptance of setup/CV/profile confirmation. Profile: backend "
                                           "2019-2024, skills Python/Go/SQL, no Python duration, nothing on cloud/Kubernetes/mentoring.", "ok": ok, "steps": log})
    if not (ok and state["sessions_supported"] and state["fingerprints"]["payload_equals_source"]):
        why = "fixture failed" if not ok else "CLI lacks --session-id/--resume" if not state["sessions_supported"] else "payload differs from source"
        for ph in ("E", "F", "G"):
            set_phase(state, ph, "BLOCKED", "NOT RUN", why)
        write_state(res, state)
        print(json.dumps({"prepare": "BLOCKED", "why": why}))
        return 2
    write_state(res, state)
    print(json.dumps({"prepare": "OK", "tmp": str(tmp), "deadline": state["deadline"], "candidate": state["candidate"]}))
    return 0


def budget(state, limit):
    return Deadline(state["start"], reserve=state["reserve_s"]).phase_timeout(limit, time.time())


def host_phase(state, name, prompt, session):
    res = Path(state["res"])
    timeout = budget(state, LIMITS[name])
    if timeout is None:
        set_phase(state, name, "NOT RUN", "NOT RUN", "deadline budget exhausted")
        write(res, f"{name}/NOT_RUN.txt", "deadline budget exhausted")
        return None
    current = tree_fingerprint(state["payload"])["aggregate"]
    if current != state["fingerprints"]["payload_skills"]["aggregate"]:
        set_phase(state, name, "BLOCKED", "NOT RUN", "payload changed after prepare")
        return None
    d = res / name
    d.mkdir(exist_ok=True)
    (d / "prompt.txt").write_text(prompt)
    ws = Path(state["ws"])
    before = file_hashes(ws)
    write(res, f"{name}/artifacts-before.json", before)
    env = dict(os.environ, XDG_CONFIG_HOME=state["cfg"])
    meta = run_process(build_command(state["claude"], prompt, state["payload"], session), state["project"], env, timeout, d, name)
    info = parse_events((d / f"{name}.stdout.jsonl").read_text())
    after = file_hashes(ws)
    write(res, f"{name}/artifacts-after.json", after)
    write(res, f"{name}/artifacts-diff.json", diff_hashes(before, after))
    write(res, f"{name}/tools.json", info["calls"])
    write(res, f"{name}/reply.md", info["text"])
    meta.update({"session": {"mode": session[0], "id": session[1], "seen_in_events": info["session_ids"]}, "skills_seen": info["skills"],
                 "web_tool_calls": [c["tool"] for c in info["calls"] if c["tool"] in ("WebFetch", "WebSearch")], "result_event": info["result"],
                 "payload_fingerprint": current, "source_fingerprint_at_run": tree_fingerprint(ROOT)["aggregate"]})
    write(res, f"{name}/meta.json", meta)
    state.setdefault("host_runs", {})[name] = {"payload_fingerprint": current, "source_fingerprint": meta["source_fingerprint_at_run"], "end": meta["end"]}
    return meta, info, before, after


def dependency_block(state, name, needs):
    for need, what in needs:
        ph = state["phases"].get(need, {})
        value = ph.get(what)
        if value != "PASS":
            set_phase(state, name, "BLOCKED", "NOT RUN", f"{need}.{what} is {value}")
            return True
    return False


def stage_evidence(res):
    state = read_state(res)
    if state["phases"].get("E", {}).get("automatic") in ("PASS", "FAIL"):
        raise SystemExit("E already ran; no repetition")
    project, cand = state["project"], state["candidate"]
    prompt = (f"/interview-coach:job-create Bereite die Stelle aus {project}/files/posting.md für Erika Beispiel vor. Das Unternehmen ist die "
              f"Beispiel AG. Die Interviewer sind unbekannt. Recherchiere nicht im Web, vermerke das als offen.")
    out = host_phase(state, "E", prompt, ("new", str(uuid.uuid4())))
    if not out:
        return report(res, state, "E")
    meta, info, before, after = out
    ws = Path(state["ws"])
    jobs = jobs_of(ws)
    checks = [check("host exit 0 in time", meta["exit_code"] == 0 and not meta["timed_out"], {k: meta[k] for k in ("exit_code", "timed_out", "duration_s")}),
              check("no web tool used", not meta["web_tool_calls"], meta["web_tool_calls"]),
              check("exactly one job created", len(jobs) == 1, [j.name for j in jobs])]
    material = {"reply": info["text"], "profile": (ws / "candidates" / cand / "profile.md").read_text() if (ws / "candidates" / cand / "profile.md").is_file() else ""}
    job_id = None
    if len(jobs) == 1:
        job = jobs[0]
        job_id = job.name
        state["job_id"] = job_id
        meta_job = json.loads((job / "job.json").read_text())
        posting_orig = sorted((job / "postings").glob("*.original.*"))
        for kind in ("postings", "research", "match", "preparation"):
            material[kind] = "\n\n".join(f"### {p.name}\n{p.read_text()}" for p in sorted((job / kind).glob("*.md"))) if (job / kind).is_dir() else ""
        kinds = {k: len(list((job / k).glob("*.md"))) for k in ("postings", "research", "match", "preparation")}
        checks += [check("job belongs to the fixture candidate", meta_job["candidate_id"] == cand and job.parent.parent.name == cand, meta_job["candidate_id"]),
                   check("posting original byte-identical", bool(posting_orig) and sha(posting_orig[0]) == sha(Path(project) / "files/posting.md"), [p.name for p in posting_orig]),
                   check("participants status unknown", meta_job["participants"]["status"] == "unknown", meta_job["participants"]),
                   check("match and preparation snapshots exist", kinds["match"] >= 1 and kinds["preparation"] >= 1, kinds),
                   check("job-create succeeded for project+candidate", bool(ok_identity(info, "job-create", project, candidate=cand)), None)]
        for kind in ("research", "match", "preparation"):
            hits = [c for c, p in ok_identity(info, "job-add", project, candidate=cand, job=job_id) if p["options"].get("kind") == kind]
            checks.append(check(f"job-add --kind {kind} succeeded for project+candidate+job", bool(hits), len(hits)))
    write(res, "E/review-material.json", material)
    state["phases"].setdefault("E", {})["material_sha256"] = hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()
    write(res, "E/checks.json", {"checks": checks, "note": "automatic structure checks only; content is judged separately (review-evidence)"})
    set_phase(state, "E", auto_verdict(checks), "NOT REVIEWED", "automatic done; domain review of match/preparation/reply required")
    return report(res, state, "E")


def stage_review(res, name, review_path, required, material_file):
    state = read_state(res)
    material = json.loads((Path(res) / material_file).read_text())
    ph = state["phases"].get(name, {})
    if ph.get("automatic") != "PASS":
        set_phase(state, name, domain="NOT RUN", note=f"automatic is {ph.get('automatic')}; no domain review")
        return report(res, state, name)
    if time.time() > state["deadline"]:
        set_phase(state, name, domain="BLOCKED", note="deadline exceeded before the review")
        return report(res, state, name)
    review = json.loads(Path(review_path).read_text())
    write(res, f"{name}/domain-review.json", review)
    try:
        verdict, per = validate_review(review, material, required)
        set_phase(state, name, domain=verdict, note=f"domain review {verdict}: {per}")
    except ReviewError as exc:
        set_phase(state, name, domain="BLOCKED", note=f"review unusable: {exc}")
    return report(res, state, name)


def stage_ask(res):
    state = read_state(res)
    if dependency_block(state, "F", (("E", "automatic"), ("E", "domain"))):
        return report(res, state, "F")
    project, cand, job_id, sid = state["project"], state["candidate"], state["job_id"], state["sessions"]["fg"]
    prompt = ("/interview-coach:job-training Starte das Training für die gespeicherte Stelle bei der Beispiel AG für Erika Beispiel. "
              "Stelle nur die erste Interviewfrage.")
    out = host_phase(state, "F", prompt, ("new", sid))
    if not out:
        return report(res, state, "F")
    meta, info, before, after = out
    q = extract_question(info["text"])
    checks = [check("host exit 0 in time", meta["exit_code"] == 0 and not meta["timed_out"], {k: meta[k] for k in ("exit_code", "timed_out", "duration_s")}),
              check("session id is the requested one", session_identity_ok(sid, meta["session"]["seen_in_events"]), meta["session"]),
              check("project-show succeeded for the expected project", bool(ok_identity(info, "project-show", project)), None),
              check("job-show succeeded for project+candidate+job together", bool(ok_identity(info, "job-show", project, candidate=cand, job=job_id)),
                    [p["options"] for _, p in runtime_calls(info, "job-show")]),
              check("status succeeded for project+candidate", bool(ok_identity(info, "status", project, candidate=cand) or ok_identity(info, "candidate-status", project, candidate=cand)), None),
              check("no run written yet", not list(Path(state["ws"]).glob("candidates/*/runs/*.md")), None),
              check("question block extracted and unambiguous", bool(q["block"]) and not q["ambiguous"], q)]
    write(res, "F/question.json", {"reply": info["text"], "block": q["block"], "ambiguous": q["ambiguous"],
                                   "block_sha256": hashlib.sha256(q["block"].encode()).hexdigest() if q["block"] else None})
    set_phase(state, "F", auto_verdict(checks), "NOT REVIEWED", "preparation for G; question suitability is judged in check-answer")
    write(res, "F/checks.json", {"checks": checks})
    return report(res, state, "F")


def stage_check_answer(res, answer_path, review_path):
    state = read_state(res)
    if time.time() > state["deadline"]:
        state["answer"] = {"verdict": "BLOCKED", "reasons": ["deadline exceeded"]}
        write_state(res, state)
        print(json.dumps(state["answer"]))
        return 2
    question = json.loads((Path(res) / "F/question.json").read_text())
    if state["phases"].get("F", {}).get("automatic") != "PASS" or question["ambiguous"]:
        verdict, reasons = "BLOCKED", ["F did not produce one clear question"]
    else:
        answer = Path(answer_path).read_text().strip()
        review = json.loads(Path(review_path).read_text())
        write(res, "B/answer.txt", answer)
        write(res, "B/answer-fit-review.json", review)
        verdict, reasons = validate_answer_fit(question["block"], answer, review)
        state["answer"] = {"answer_sha256": hashlib.sha256(answer.encode()).hexdigest()}
    state.setdefault("answer", {}).update({"verdict": verdict, "reasons": reasons, "checked_at": time.time()})
    write(res, "B/answer-fit-result.json", state["answer"])
    set_phase(state, "F", domain="PASS" if verdict == "PASS" else "BLOCKED", note="question/answer fit " + verdict)
    if verdict != "PASS":
        set_phase(state, "G", "BLOCKED", "NOT RUN", "answer fit not established: " + "; ".join(reasons)[:300])
    write_state(res, state)
    print(json.dumps({"answer_fit": verdict, "reasons": reasons}, ensure_ascii=False))
    return 0 if verdict == "PASS" else 2


def promotion_lines(lines):
    """Lines that SET a competency status to improving/stable ("C08 name: improving — ..."). The bare word elsewhere (for example "more answers
    are needed before a competency counts as improving") is not a promotion; the first wrapper version matched the bare word."""
    return [x for x in lines if re.search(r":\s*(improving|stable)\b", x, re.I)]


def stage_answer(res):
    state = read_state(res)
    ans = state.get("answer", {})
    answer_file = Path(res) / "B/answer.txt"
    if ans.get("verdict") != "PASS" or not answer_file.is_file() or hashlib.sha256(answer_file.read_text().encode()).hexdigest() != ans.get("answer_sha256"):
        set_phase(state, "G", "BLOCKED", "NOT RUN", "answer fit not established or answer changed after the check")
        return report(res, state, "G")
    if dependency_block(state, "G", (("F", "automatic"),)):
        return report(res, state, "G")
    project, cand, job_id, sid = state["project"], state["candidate"], state["job_id"], state["sessions"]["fg"]
    ws = Path(state["ws"])
    runs_before = set(map(str, ws.glob("candidates/*/runs/*.md")))
    sp = ws / "candidates" / cand / "state.md"
    state_before = sp.read_text() if sp.is_file() else ""
    write(res, "G/state-before.md", state_before)
    prompt = f"Meine Antwort: {answer_file.read_text().strip()}\n\nBewerte meine Antwort und beende das Training mit stop."
    out = host_phase(state, "G", prompt, ("resume", sid))
    if not out:
        return report(res, state, "G")
    meta, info, before, after = out
    new_runs = sorted(set(map(str, ws.glob("candidates/*/runs/*.md"))) - runs_before)
    fin = ok_identity(info, "finish", project, candidate=cand, job=job_id, job_keys=("job-id",))
    run_text = Path(new_runs[0]).read_text() if len(new_runs) == 1 else ""
    state_text = sp.read_text() if sp.is_file() else ""
    added = [x for x in state_text.splitlines() if x not in set(state_before.splitlines())]
    promoted = promotion_lines(added)
    checks = [check("host exit 0 in time", meta["exit_code"] == 0 and not meta["timed_out"], {k: meta[k] for k in ("exit_code", "timed_out", "duration_s")}),
              check("same host session as F (requested id only)", session_identity_ok(sid, meta["session"]["seen_in_events"]) and meta["session"]["mode"] == "resume", meta["session"]),
              check("finish succeeded for project+candidate+job together", len(fin) >= 1, [p["options"] for _, p in runtime_calls(info, "finish")]),
              check("finish status stopped_early with answered-count 1", any(p["options"].get("status") == "stopped_early" and p["options"].get("answered-count") == "1" for _, p in fin), None),
              check("exactly one new immutable run", len(new_runs) == 1, new_runs),
              check("run header names candidate, job and stopped_early", bool(run_text) and cand in run_text and job_id in run_text and "stopped_early" in run_text, None),
              check("no invented full plan (no planned-count)", all("planned-count" not in p["options"] for _, p in fin), None),
              check("state.md changed and adds no improving/stable line", state_text != state_before and not promoted, {"added_lines": added, "promoted": promoted}),
              check("reply names the real run id", bool(new_runs) and Path(new_runs[0]).stem in info["text"], Path(new_runs[0]).stem if new_runs else None)]
    material = {"reply": info["text"], "run": run_text, "state_added_lines": "\n".join(added), "state": state_text,
                "answer": answer_file.read_text(), "question": json.loads((Path(res) / "F/question.json").read_text())["block"] or ""}
    write(res, "G/review-material.json", material)
    write(res, "G/checks.json", {"checks": checks, "new_runs": new_runs, "note": "automatic only; content judged in review-answer"})
    state["run_id"] = Path(new_runs[0]).stem if len(new_runs) == 1 else None
    set_phase(state, "G", auto_verdict(checks), "NOT REVIEWED", "automatic done; domain review required")
    return report(res, state, "G")


def stage_reload(res):
    """H (not part of the targeted window): new session reads the stored run. Kept for completeness; identity of the new session is enforced."""
    state = read_state(res)
    if dependency_block(state, "H", (("G", "automatic"), ("G", "domain"))):
        return report(res, state, "H")
    sid_h, sid_fg, rid = state["sessions"]["h"], state["sessions"]["fg"], state.get("run_id")
    ws = Path(state["ws"])
    before_all = file_hashes(ws, skip_parts=(".journal",))
    prompt = ("/interview-coach:interview-coach Welche Bewerberin, Stelle und Trainingsläufe gibt es in diesem Projekt? Nenne Namen und Run-IDs, "
              "gib das Ergebnis des Trainings und den Lernstand wieder und nenne offene Recherchepunkte. Lege nichts neu an und ändere nichts.")
    out = host_phase(state, "H", prompt, ("new", sid_h))
    if not out:
        return report(res, state, "H")
    meta, info, _, _ = out
    diff = diff_hashes(before_all, file_hashes(ws, skip_parts=(".journal",)))
    read_run = bool(rid) and any(c["ok"] and ((c["tool"] == "Read" and rid in c["input"].get("file_path", "")) or (c["tool"] == "Bash" and any(rid in r["content"] for r in c["results"]))) for c in info["calls"])
    checks = [check("host exit 0 in time", meta["exit_code"] == 0 and not meta["timed_out"], {k: meta[k] for k in ("exit_code", "timed_out", "duration_s")}),
              check("requested new session id appears in host events and differs from F/G", check_h_session(sid_h, sid_fg, meta["session"]["seen_in_events"]), meta["session"]),
              check("no workspace data changed (SHA-256, .journal excluded)", not any(diff.values()), diff),
              check("host read the stored run (successful tool result)", read_run, rid),
              check("reply names the run id", bool(rid) and rid in info["text"], rid)]
    set_phase(state, "H", auto_verdict(checks), "NOT REVIEWED", "automatic done; domain review required")
    write(res, "H/checks.json", {"checks": checks})
    return report(res, state, "H")


def stage_status(res):
    state = read_state(res)
    current = tree_fingerprint(ROOT)["aggregate"]
    out = {"phases": {k: {x: v.get(x) for x in ("automatic", "domain", "final", "note")} for k, v in state["phases"].items()},
           "elapsed_s": round(time.time() - state["start"], 1), "deadline_exceeded": time.time() > state["deadline"],
           "host_runs": {k: {"source_fingerprint": v["source_fingerprint"], "source_unchanged_since": evidence_current(v["source_fingerprint"], current)}
                         for k, v in state.get("host_runs", {}).items()}}
    write(res, "99-status.json", out)
    print(json.dumps(out, indent=1, ensure_ascii=False))
    finals = [v["final"] for v in state["phases"].values() if "final" in v]
    return 0 if finals and all(f == "PASS" for f in finals) else max([exit_code(f) for f in finals] or [2])


def jobs_of(ws):
    return sorted((Path(ws) / "candidates").glob("*/jobs/*")) if (Path(ws) / "candidates").is_dir() else []


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="stage", required=True)
    for name in ("prepare", "evidence", "review-evidence", "ask", "check-answer", "answer", "review-answer", "reload", "status"):
        p = sub.add_parser(name)
        p.add_argument("--results", required=True, help="results directory under .tmp/tests/ (prepare: new directory)")
        if name == "prepare":
            p.add_argument("--claude", default="claude")
        if name in ("review-evidence", "review-answer", "check-answer"):
            p.add_argument("--review", required=True)
        if name == "check-answer":
            p.add_argument("--answer", required=True)
    args = parser.parse_args(argv)
    res = args.results
    if args.stage == "prepare":
        return prepare(res, args.claude)
    if args.stage == "evidence":
        return stage_evidence(res)
    if args.stage == "review-evidence":
        return stage_review(res, "E", args.review, EVIDENCE_CRITERIA, "E/review-material.json")
    if args.stage == "ask":
        return stage_ask(res)
    if args.stage == "check-answer":
        return stage_check_answer(res, args.answer, args.review)
    if args.stage == "answer":
        return stage_answer(res)
    if args.stage == "review-answer":
        return stage_review(res, "G", args.review, ANSWER_CRITERIA, "G/review-material.json")
    if args.stage == "reload":
        return stage_reload(res)
    return stage_status(res)


if __name__ == "__main__":
    sys.exit(main())
