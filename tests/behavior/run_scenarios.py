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
            if spec.get("interview_language"):
                iw.set_interview_language(self.workspace, cid, spec["interview_language"])
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
                      expected_state_sha256=state, status="completed", answered_count=1, planned_count=1, job_id=self.ids.get("JOB0") if spec.get("job") else None,
                      dialogue=spec.get("dialogue", [{"key": "q-1", "question": "Frühere Frage?", "initial_answer": "Frühere Antwort.",
                                                      "initial_assessment": "Erstantwort: solide.", "block_assessment": "Frageblock: solide.",
                                                      "followups": [], "retries": [], "other_open_gaps": []}]))
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
    "followup_deadline_pressure": "The reply asks exactly ONE concrete follow-up about how the fixed deadline / schedule pressure affects the decision or approach (the aspect the candidate's answer left open). It stays on the same main question, is not a request to repeat the whole answer and is not a new main question or a list of questions.",
    "no_leak_before_followup": "The reply contains no model answer, no hint about how the open aspect should be handled, no score or rating (x/10), no strengths or improvement list and no claim that the answer was wrong. At most one short neutral acknowledgement precedes the single follow-up question.",
    "clarify_motivation_neutral": "The reply asks ONE neutral clarification question about the ambiguous statement and nothing else of substance. Both an OPEN question ('What do you mean by it?') and a NEUTRAL choice ('Do you mean A or B?') are fine; naming possible meanings is NOT required. It fails if the question is suggestive (contains a premise or a valuation such as 'Do you shy away from responsibility?', 'Do you rather want to work than lead?'), derives a weakness or a fit verdict before the clarification, asks for two things, or already reveals a rating, hint or model answer.",
    "no_unasked_example_deduction": "No score, criterion, score reason or required improvement is justified by a missing example (or other detail) that the question did not ask for. Recommending an optional example is fine when phrased as optional ('optional: ...') and not as a lack or a deduction. 'Konkretheit 5/10, es fehlt ein Beispiel' for a question that asked for no example fails.",
    "role_fit_job_specific": "The reply treats the candidate's confirmed wish for hands-on technical implementation as a job-specific fit point regarding the Product role (preference/fit) and does NOT present it as a general communication or competence weakness. It must keep answer quality and role fit apart in the scores AND in the reasons given for them: no overall score, criterion score or improvement item may be justified by the candidate's missing enthusiasm for, interest in, reasons for, or 'what appeals' in the role the candidate declined (for example 'Substanz der Begründung 4/10, because the candidate does not say what attracts them to this role' or 'otherwise the answer reads like a rejection' fails). Answer quality means clarity, honesty and specificity of what the candidate actually said. A heading like 'Passung ohne Punktzahl' does not rescue a score whose reason is the preference.",
    "no_false_missing": "Every statement in the reply that something is missing, not said, not mentioned or open is checked against the CANDIDATE lines: it must not be contradicted by anything the candidate said. A brief statement counts (for example 'mit beiden Teams durchgehen' says the teams are involved, so 'you do not say how you involve the teams' is false). Recommending additional depth ('additionally possible: how positions are heard') is fine when phrased as a recommendation; claiming it is absent when it was said, or dropping what was said, fails. Also fails: treating an aspect only the coach raised in an add-on question as an unanswered gap.",
    "no_artificial_completion": "The reply does not ask a completion question for an aspect the answer already covered and does not claim missing essentials that the answer actually contains; it evaluates the answer or at most asks one deepening question.",
    "deepening_or_close": "The answer covers every essential requirement. The reply therefore does NOT ask a completion or clarification question and does not withhold or postpone the rating because something essential is missing (improvement suggestions inside a rating are normal and fine). It does exactly one of two things: (a) asks ONE meaningful deepening question about an additional dimension (one question mark) with no rating, score, hint, model answer or solution before it and without implying a flaw in the answer, or (b) closes the block and rates it (strengths/improvements). It never does both a deepening question and a rating in the same reply.",
    "no_deduction_optional_example": "The reply does not criticize or deduct for the absence of a real-life example and does not demand one (offering it as optional is fine); the hypothetical answer is rated on its merits.",
    "gap_honest_no_loop": "The reply closes the follow-up block because the candidate does not know more: it does not ask the same or another follow-up about the same gap, states honestly that the aspect stayed open, and offers coaching or the next main question.",
    "natural_followup_no_feedback": "The reply continues like a natural interviewer (one follow-up or the next question) and contains no score, no strengths/improvements, no hint and no model answer.",
    "reasks_open_followup": "The reply picks up the previously unanswered follow-up question (it does not start a new main question and does not repeat parts the candidate already answered).",
    "script_fits_question": "The CANDIDATE message is a plausible, direct answer to the question the COACH asked last (it addresses what was asked; it may be brief). It does not answer a different question.",
    "reuses_research": "The reply makes clear that stored research/preparation is reused rather than starting from scratch.",
}
SCORE = re.compile(r"(?<![\d.,])(\d{1,2}(?:[.,]\d)?)\s*/\s*10\b")


def judge_prompt(items, user, reply, history=(), evidence=""):
    """Judge input: released fictional sources, the dialogue so far (candidate lines and coach lines kept apart), the rules."""
    rules = "\n".join(f"- {key}: {RUBRIC[key]}" for key in items)
    dialogue = "\n".join(f"{'CANDIDATE (scripted test user)' if role == 'user' else 'COACH'}: {message}" for role, message in history) or "(none)"
    return ("You are a strict grader of a fictional interview-coaching test. Judge ONLY the final COACH REPLY against each rule, using the "
            "dialogue for context. Only CANDIDATE lines and the RELEASED FICTIONAL SOURCES are candidate evidence; earlier COACH lines, "
            "suggestions and model answers are NOT evidence of anything the candidate did. "
            "Answer with one JSON object mapping every rule key to true or false and nothing else. If you answer false for no_invention, add a key "
            "\"invented\": a list of objects {\"quote\": EXACT quote from the final COACH REPLY, \"source\": \"candidate_fact\" (the reply states "
            "something as something the candidate did/said/has) or \"coach_suggestion\" (a proposal, advice or example wording offered by the coach)}. "
            "Statements about the COURSE of this dialogue (that the candidate answered after the follow-up, independently, without a hint from the coach, in the first or the second answer) are supported by the DIALOGUE SO FAR and are NOT inventions. A characterization of how the candidate works, thinks or behaves that no CANDIDATE line states (for example 'denkt den Termindruck von Anfang an mit', 'immer', 'proaktiv', 'konsequent') is an invention (candidate_fact, in_evidence false) even when the topic itself was mentioned. "
            "For candidate_fact add \"in_evidence\": true only if a CANDIDATE line or the RELEASED FICTIONAL SOURCES say the same thing with the same "
            "numbers, negation, actors and responsibilities, and then add \"evidence_quote\": the EXACT supporting text from there; a paraphrase is "
            "supported, similar words with a changed meaning are not. For coach_suggestion add \"suggestion_kind\": \"recommendation\" (advice what "
            "the candidate could do or consider) or \"first_person_answer\" (wording the candidate should say as I/we, as if it had happened), and for "
            "first_person_answer add \"invents_experience\": true if it presents experiences, actions or results the candidate has not stated. "
            "If you answer false for no_false_missing, add a key \"false_missing\": a list of objects {\"quote\": EXACT quote from the final COACH REPLY that claims "
            "something is missing, not said or open, \"candidate_quote\": EXACT quote from a CANDIDATE line or the RELEASED FICTIONAL SOURCES that says it}.\n\n"
            f"RELEASED FICTIONAL SOURCES:\n{evidence or '(none)'}\n\nDIALOGUE SO FAR:\n{dialogue}\n\nRULES:\n{rules}"
            f"\n\nLATEST CANDIDATE MESSAGE:\n{user}\n\nFINAL COACH REPLY:\n{reply}\n")


def run_judge(judge, items, user, reply, history=(), evidence="", detail=None):
    """Return ({item: True|False|None}, [problems]).

    Problem prefixes: `rubric failed:` = a verified negative verdict; `rubric unclear:` = no reliable verdict (invalid JSON, missing or
    non-boolean verdict, accusation without a verifiable quote, contradicting evidence claim); `semantic rubric not checked` = no judge.
    Only `True` verdicts (and a no_invention accusation shown to be unfounded) count as passed; unclear is never a pass.
    """
    if not items:
        return {}, []
    if judge is None:
        return {}, [f"semantic rubric not checked (no judge available): {', '.join(items)}"]
    raw = judge(judge_prompt(items, user, reply, history, evidence))
    if detail is not None:
        detail["raw"] = raw
    match = re.search(r"\{.*\}", raw, re.S)
    try:
        verdict = json.loads(match.group(0)) if match else None
    except ValueError:
        verdict = None
    if not isinstance(verdict, dict):
        return {key: None for key in items}, [f"rubric unclear: {key} (judge output is not a JSON object)" for key in items]
    verdicts, problems = {}, []
    evidence_text = evidence + " " + " ".join(m for role, m in history if role == "user") + " " + user
    for key in items:
        value = verdict.get(key)
        if type(value) is not bool:
            verdicts[key] = None
            problems.append(f"rubric unclear: {key} (verdict missing or not true/false)")
        elif value:
            verdicts[key] = True
        elif key == "no_invention":
            verdicts[key], problem = invention_verdict(verdict.get("invented"), reply, evidence_text, detail)
            if problem:
                problems.append(problem)
        elif key == "no_false_missing":
            verdicts[key], problem = false_missing_verdict(verdict.get("false_missing"), reply, evidence_text, detail)
            if problem:
                problems.append(problem)
        else:
            verdicts[key] = False
            problems.append(f"rubric failed: {key}")
    return verdicts, problems


def _tokens(text):
    return {t for t in re.findall(r"[A-Za-zÄÖÜäöüß0-9][A-Za-zÄÖÜäöüß0-9\-]{3,}", text.casefold())}


NEGATION = re.compile(r"(?i)\b(?:nicht|nie|niemals|nirgends|ohne|kein\w*|niemand\w*|not|no|never|without|none|nobody|cannot|can't|don't|didn't|wasn't)\b|n't\b")
NUMBER_WORDS = {"null": "0", "ein": "1", "eine": "1", "einen": "1", "eins": "1", "zwei": "2", "drei": "3", "vier": "4", "fünf": "5", "sechs": "6",
                "sieben": "7", "acht": "8", "neun": "9", "zehn": "10", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
                "seven": "7", "eight": "8", "nine": "9", "ten": "10"}
FIRST_PERSON_CLAIM = re.compile(r"(?i)\b(?:ich|wir|i|we)\s+(?:habe|haben|hatte|hatten|konnte|konnten|bin|war|waren|have|had|was|were|led|built|reduced|increased)\b")


def _numbers(text):
    found = {n.replace(",", ".") for n in re.findall(r"\d+(?:[.,]\d+)?", text)}
    return found | {NUMBER_WORDS[w] for w in re.findall(r"[a-zäöüß]+", text.casefold()) if w in NUMBER_WORDS}


def _negated(text):
    return bool(NEGATION.search(text))


def _stems(text):
    return {t[:5] for t in _tokens(text)}


def semantic_divergence(statement, anchor):
    """Deterministic meaning checks between a coach statement and its claimed evidence: changed numbers or a flipped negation.
    Equal vocabulary proves nothing; this only finds differences it can see. Swapped actors need the judge (stay UNCLEAR)."""
    problems = []
    if _numbers(statement) != _numbers(anchor):
        problems.append(f"numbers differ ({sorted(_numbers(statement))} vs {sorted(_numbers(anchor))})")
    if _negated(statement) != _negated(anchor):
        problems.append("negation differs")
    return problems


def invention_verdict(items, reply, evidence_text, detail=None):
    """no_invention=false from the judge -> (True|False|None, problem|None).

    A candidate fact counts as supported only if the judge names an `evidence_quote` that really occurs in the candidate evidence
    (released sources, candidate lines), shares content with the statement and agrees on numbers and negation. Shared vocabulary
    alone never overrules a negative verdict: an unsupported statement without visible differences stays UNCLEAR.
    A coach suggestion is released only as a recommendation; a proposed first-person answer must not invent experience or results.
    """
    if not isinstance(items, list) or not items:
        return None, "rubric unclear: no_invention (accusation without a quote)"
    evidence_tokens, evidence_folded = _tokens(evidence_text), evidence_text.casefold()
    findings, unclear = [], []
    for item in items:
        quote = item.get("quote") if isinstance(item, dict) else None
        if not isinstance(quote, str) or quote.casefold() not in reply.casefold():
            unclear.append("quote not found in the reply")
            continue
        label, source = quote[:70], item.get("source")
        novel = sorted(_tokens(quote) - evidence_tokens)
        if source == "coach_suggestion":
            kind = item.get("suggestion_kind")
            if FIRST_PERSON_CLAIM.search(quote) and kind == "recommendation":
                kind = "first_person_answer"  # wording decides, not the label
            if kind == "recommendation":
                continue
            if kind != "first_person_answer":
                unclear.append(f"coach suggestion without suggestion_kind recommendation|first_person_answer: {label!r}")
                continue
            invented = item.get("invents_experience")
            new_numbers = sorted(_numbers(quote) - _numbers(evidence_text))
            if invented is True or new_numbers:
                findings.append(f"proposed first-person answer invents experience or results: {label!r}" + (f" (new numbers {new_numbers})" if new_numbers else ""))
            elif type(invented) is not bool:
                unclear.append(f"first-person suggestion without invents_experience verdict: {label!r}")
            elif FIRST_PERSON_CLAIM.search(quote) and novel:
                unclear.append(f"first-person claim with content absent from the evidence {novel[:3]}: {label!r}")
            continue
        supported = item.get("in_evidence")
        if source != "candidate_fact" or type(supported) is not bool:
            unclear.append(f"unclassified statement {label!r}")
            continue
        anchor = item.get("evidence_quote")
        anchored = isinstance(anchor, str) and len(anchor.strip()) > 3 and anchor.casefold() in evidence_folded
        if supported:
            if not anchored:
                unclear.append(f"judge claims evidence without a verifiable evidence_quote: {label!r}")
            elif not _stems(quote) & _stems(anchor):
                unclear.append(f"evidence_quote shares no content with the statement: {label!r}")
            else:
                diff = semantic_divergence(quote, anchor)
                if diff:
                    findings.append(f"{label!r} differs from the evidence {anchor[:60]!r}: {'; '.join(diff)}")
        elif novel or _numbers(quote) - _numbers(evidence_text):
            findings.append(f"{label!r} (new: {novel[:4] or sorted(_numbers(quote) - _numbers(evidence_text))})")
        else:
            unclear.append(f"judge calls {label!r} unsupported although the vocabulary occurs in the evidence; meaning not established (changed actor, negation or relation?)")
    if detail is not None:
        detail["invention"] = {"findings": findings, "unclear": unclear}
    if findings:
        return False, "rubric failed: no_invention " + "; ".join(findings)
    if unclear:
        return None, "rubric unclear: no_invention (" + "; ".join(unclear) + ")"
    return True, None


def false_missing_verdict(items, reply, candidate_text, detail=None):
    """no_false_missing=false from the judge -> (False|None, problem). A bare 'false' proves nothing: the judge must quote the claim in the
    reply AND the candidate sentence that contradicts it (verified verbatim, sharing content); otherwise the finding stays UNCLEAR."""
    if not isinstance(items, list) or not items:
        return None, "rubric unclear: no_false_missing (accusation without quotes)"
    folded_reply, folded_candidate = reply.casefold(), candidate_text.casefold()
    findings, unclear = [], []
    for item in items:
        quote = item.get("quote") if isinstance(item, dict) else None
        proof = item.get("candidate_quote") if isinstance(item, dict) else None
        if not isinstance(quote, str) or not isinstance(proof, str) or len(quote.strip()) < 4 or len(proof.strip()) < 4:
            unclear.append("quotes missing")
        elif quote.casefold() not in folded_reply:
            unclear.append("claim quote not found in the reply")
        elif proof.casefold() not in folded_candidate:
            unclear.append(f"candidate quote not found in the candidate evidence: {proof[:50]!r}")
        elif not _stems(quote) & _stems(proof):
            unclear.append(f"claim {quote[:50]!r} and candidate quote {proof[:50]!r} share no content")
        else:
            findings.append(f"{quote[:80]!r} although the candidate said {proof[:80]!r}")
    if detail is not None:
        detail["false_missing"] = {"findings": findings, "unclear": unclear}
    if findings:
        return False, "rubric failed: no_false_missing " + "; ".join(findings)
    return None, "rubric unclear: no_false_missing (" + "; ".join(unclear) + ")"


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


SAVED = re.compile(r"(?i)(?<!nicht )(?<!kein )(?<!nichts )(?:wurde|wurden|ist|sind|habe|haben|was|were|has been|have been)\b[^.\n]{0,60}\b(?:gespeichert|abgelegt|verifiziert|gesichert|archiviert|persistiert|saved|stored|archived)\b"
                   r"|(?:^|[\s>*_\u2705\u2713\u2714:-])(?:gespeichert|abgelegt|gesichert|archiviert|saved|stored)(?:\s+(?:unter|in|als|at|to)\b|[\s.!*_]*$)")
NEGATED = re.compile(r"(?i)\b(?:nicht|nichts|kein|keine|konnte nicht|fehlgeschlagen|ohne|not|nothing|no)\b[^.\n]{0,40}\b(?:gespeichert|abgelegt|persistiert|gesichert|archiviert|saved|stored)\b|\b(?:gespeichert|abgelegt|persistiert)\b[^.\n]{0,40}\b(?:nicht|nichts|kein)\b|\b(?:gespeichert|abgelegt)\b[^.\n]{0,20}\bwurde\s+nicht\b")


def claims_saved(reply):
    """True if the reply asserts a successful save (negated statements do not count)."""
    return any(not NEGATED.search(sentence) and SAVED.search(sentence) for sentence in re.split(r"(?<=[.!?\n])\s+", reply))


RESUME_WORDS = re.compile(
    # the ASSISTANT promises or offers to pick the stopped session / open follow-up up again (advice to the user is not a promise)
    r"(?i)\b(?:ich|wir)\b[^.\n]{0,60}\b(?:fortsetz|weitermach|weiterführ|wiederaufnehm|wieder aufnehm|resum|continu)\w*"
    r"|\bgreife\b[^.\n]{0,60}\b(?:Nachfrage|Frage|Sitzung|Session|Training|Antwort)\b[^.\n]{0,30}\bauf\b"
    r"|\b(?:beim|zum|nach dem|bei der|bei einer)\s+(?:fortsetz|weitermach|wiederaufnehm|wieder aufnehm)\w*"
    r"|\b(?:kann|können|wird|werden|lässt sich|lassen sich)\b[^.\n]{0,50}\b(?:fortgesetzt|weitergeführt|wiederaufgenommen|wieder aufgenommen|aufgegriffen)\b"
    r"|\b(?:stelle|frage)\s+ich\b[^.\n]{0,60}\b(?:erneut|nochmals|noch einmal|wieder)\b|\b(?:erneut|nochmals|noch einmal|wieder)\b[^.\n]{0,40}\b(?:stelle|frage)\s+ich\b"
    r"|\b(?:i|we)\b[^.\n]{0,50}\b(?:resume|continue|pick up|ask)\b[^.\n]{0,40}\b(?:later|again|next time)\b|\bcan (?:be )?(?:resumed|continued)\b")
NOT_A_PROMISE = re.compile(r"(?i)\b(?:nicht|nichts|kein\w*|nur\b|ohne|not|cannot|only|never|unmöglich)\b|\bpause\b|\bpausier\w*"
                           r"|\bneu(?:e|en|er|es|em)?\s+(?:session|sitzung|training|lauf|runde|übung|interview|durchlauf|versuch)|\bnew\s+(?:session|training|run)\b"
                           r"|\bfortsetzung\s+von\b|\bcontinuation\s+of\b")


def promises_resume(reply):
    """True if a (STOP) reply promises or offers to pick up the open follow-up or the session later.
    A stopped run is final; only `pause` keeps a checkpoint. Negated statements and sentences that name `pause` are not promises."""
    def promise(sentence):
        # code spans (`pause`) must stay visible to the exemptions; file names and links are data, not promises
        words = re.sub(r"\[[^\]]*\]\([^)]*\)|`[^`]*(?:\.md|/)[^`]*`", " ", sentence)
        return bool(RESUME_WORDS.search(words)) and not NOT_A_PROMISE.search(sentence)
    return any(promise(sentence) for sentence in re.split(r"(?<=[.!?\n])\s+", reply))


PREFERENCE_REASON = re.compile(r"(?i)woher der Wunsch|Beweggründe|keine Situation|Substanz der Begründung[^.\n]{0,60}(?:fehl|nicht|kein)|reizt|anspricht|ansprechen|begeister\w*|Interesse (?:an|für)|Motivation für (?:die|diese|den)|Grund\w* für (?:die|diese|den)"
                               r"|was (?:dich|Sie|ihn|sie) (?:an|bei) (?:dieser|der|dem|diesem)|nicht[^.\n]{0,40}\b(?:an dieser Rolle|an der Rolle|an der Aufgabe|an Beispiel AG)\b")
ABSAGE = re.compile(r"(?i)wirkt[^.\n]{0,40}wie eine Absage")
SCORE_LINE = re.compile(r"(?<![\d.,])(\d{1,2})(?:[.,]\d)?\s*/\s*10\b")


def preference_penalty_lines(reply):
    """Lines that justify a low score (<= 6/10) with missing enthusiasm for / reasons for the declined role (the line itself or, for the
    overall score, the justification line right below it), or call the answer a rejection. A heading 'ohne Punktzahl' changes nothing."""
    lines, found = [line.strip() for line in reply.splitlines()], []
    for i, line in enumerate(lines):
        scores = [int(n) for n in SCORE_LINE.findall(line)]
        if scores and min(scores) <= 6:
            following = next((x for x in lines[i + 1:i + 3] if x), "")
            for text in (line, following):
                if PREFERENCE_REASON.search(text):
                    found.append(text[:200])
        if ABSAGE.search(line):
            found.append(line[:200])
    return sorted(set(found))


EXAMPLE_LACK = re.compile(r"(?i)\b(?:fehlt|fehlen|kein\w*|ohne|nicht genannt|nicht gesagt)\b[^.\n]{0,60}\bBeispiel\w*|\bBeispiel\w*[^.\n]{0,40}\b(?:fehlt|fehlen|fehlend)\b|mit einem Beispiel (?:belegen|stützen)")


def example_penalty_lines(reply):
    """Score lines (<= 6/10, or the justification right below an overall score) that blame a missing example. Optional recommendations are not found."""
    lines, found = [line.strip() for line in reply.splitlines()], []
    for i, line in enumerate(lines):
        scores = [int(n) for n in SCORE_LINE.findall(line)]
        if scores and min(scores) <= 6:
            following = next((x for x in lines[i + 1:i + 3] if x), "")
            for text in (line, following):
                if EXAMPLE_LACK.search(text) and not re.search(r"(?i)\boptional\b|kein Abzug|keinen Abzug|ohne Abzug", text):
                    found.append(text[:200])
    return sorted(set(found))


CHARACTERIZATION = re.compile(r"(?i)\b(?:(?:nicht|statt|anstatt) erst|von Anfang an|stets|immer|durchgängig|konsequent|proaktiv|grundsätzlich|routiniert|systematisch)\b")
RECOMMENDING = re.compile(r"(?i)könnt\w*|sollt\w*|würde\w*|empfehl\w*|wäre\w*|optional|zusätzlich|besser|stärker|\bsag\w*|nenne\w*|ergänz\w*|\bwenn\b|\bso\b")


def unstated_characterizations(reply, candidate_text):
    """Sentences that attribute a habit or degree to the candidate ('Du denkst den Termindruck von Anfang an mit') which no candidate line
    or released source states. Recommendations and wording that the candidate used themselves are not found."""
    own, found = candidate_text.casefold(), []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", reply):
        contrast = re.search(r"(?i)\b(?:nicht|statt|anstatt) erst\b", sentence)
        if (not contrast and not re.search(r"(?i)\b(?:du|sie|dein\w*|ihr\w*|dich|dir)\b", sentence)) or RECOMMENDING.search(sentence):
            continue
        for match in CHARACTERIZATION.finditer(sentence):
            if match.group(0).casefold() not in own:
                found.append(sentence.strip()[:200])
                break
    return found


def question_marks(reply):
    return reply.count("?")


def preserve_artifacts(sandbox, target):
    """Copy the fictional artifacts a model run really stored (workspace without the protected control folder, plus the files the
    model prepared: run/state/match/dialogue drafts) so they stay independently reviewable after the sandbox is removed."""
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    if sandbox.workspace.exists():
        shutil.copytree(sandbox.workspace, target / "ws", ignore=shutil.ignore_patterns(".journal"), dirs_exist_ok=True)
    if sandbox.files.exists():
        shutil.copytree(sandbox.files, target / "files", dirs_exist_ok=True)
    return target


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


def dialogue_matches(header, spec):
    """Structural check of a saved run's follow-up dialogue (keys: followup_kinds, open_followup, retry_after_coaching, open_gap)."""
    blocks = header.get("dialogue", [])
    followups = [f for b in blocks for f in b["followups"]]
    if "followup_kinds" in spec and sorted(f["kind"] for f in followups) != sorted(spec["followup_kinds"]):
        return False
    if "min_followups" in spec and len(followups) < spec["min_followups"]:
        return False
    if "first_followup_kind" in spec and (not followups or followups[0]["kind"] != spec["first_followup_kind"]):
        return False
    if spec.get("no_gaps") and (any(f.get("gap") or f["resolution"] == "open" for f in followups) or any(b["other_open_gaps"] for b in blocks)):
        return False
    if "allowed_kinds" in spec and any(f["kind"] not in spec["allowed_kinds"] for f in followups):
        return False
    if "open_followup" in spec and any(f["answer"] is None for f in followups) != spec["open_followup"]:
        return False
    if spec.get("retry_after_coaching") and not any(r["after_coaching"] for b in blocks for r in b["retries"]):
        return False
    if spec.get("open_gap") and not any(f["resolution"] == "open" for f in followups) and not any(b["other_open_gaps"] for b in blocks):
        return False
    return True


def job_artifact_errors(sandbox, spec):
    """A stored job artifact (e.g. match) of the right kind, assigned to the candidate/job of the saved run(s), containing every
    pattern, while the cross-job state.md of that candidate contains none of `not_in_state`."""
    errors, kind = [], spec["kind"]
    paths = sorted(glob.glob(str(sandbox.tmp / f"ws/candidates/*/jobs/*/{kind}/*.md")))
    if not paths:
        return [f"no stored {kind} snapshot under any job"]
    runs = [h for _, h in run_headers(sandbox).values()]
    texts = []
    for path in paths:
        text = Path(path).read_text(encoding="utf-8")
        first, _, body = text.partition("\n")
        try:
            meta = json.loads(first.split(": ", 1)[1].rsplit(" -->", 1)[0])
        except (IndexError, ValueError):
            errors.append(f"{kind} snapshot has no valid header: {Path(path).name}")
            continue
        job_dir, cand_dir = Path(path).parents[1].name, Path(path).parents[3].name
        if (meta.get("kind"), meta.get("job_id"), meta.get("candidate_id")) != (kind, job_dir, cand_dir):
            errors.append(f"{kind} snapshot header does not match its candidate/job folder")
        if spec.get("same_job_as_runs", True) and not any(h.get("candidate_id") == cand_dir and h.get("job_id") == job_dir for h in runs):
            errors.append(f"{kind} snapshot belongs to a candidate/job without a saved run")
        texts.append(body)
    joined = "\n".join(texts)
    for pattern in spec.get("patterns", []):
        if not re.search(pattern, joined, re.S):
            errors.append(f"stored {kind} snapshot lacks /{pattern}/")
    for state in glob.glob(str(sandbox.tmp / "ws/candidates/*/state.md")):
        content = Path(state).read_text(encoding="utf-8")
        for pattern in spec.get("not_in_state", []):
            hit = re.search(pattern, content)
            if hit:
                line = content[:hit.start()].count("\n")
                errors.append(f"cross-job state.md contains the job-specific fit point /{pattern}/: {content.splitlines()[line][:160]!r}")
    return errors


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
                grew = (nxt["answered_count"] > previous["answered_count"]
                        or (item.get("followup_may_close") and nxt["followup_answered_count"] > previous["followup_answered_count"]))
                if not grew:
                    errors.append("continuation: answered_count did not grow (no further answer was saved)")
                if nxt["answered_count"] < previous["answered_count"] or nxt["followup_answered_count"] < previous["followup_answered_count"]:
                    errors.append("continuation: counters decreased")
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
        elif kind == "run_dialogue":
            if not any(dialogue_matches(h, item) for _, h in run_headers(sandbox).values()):
                errors.append(f"no run with dialogue {item}")
        elif kind == "stored_text_absent":
            texts = [Path(x).read_text(encoding="utf-8") for g in ("ws/candidates/*/runs/*.md", "ws/candidates/*/state.md", "ws/candidates/*/jobs/*/*/*.md")
                     for x in glob.glob(str(sandbox.tmp / g))]
            for pattern in item["patterns"]:
                for text in texts:
                    hit = re.search(pattern, text)
                    if hit:
                        errors.append(f"stored text contains /{pattern}/: {text[max(0, hit.start() - 40):hit.end() + 40]!r}")
                        break
        elif kind == "job_artifact":
            errors += job_artifact_errors(sandbox, item)
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


def fictional_sources(scenario):
    """Everything the test released as fictional candidate/job background (the only non-dialogue evidence for no_invention)."""
    preset, parts = scenario.get("preset", {}), []
    for spec in preset.get("candidates", []):
        parts += [spec.get("cv", ""), spec.get("profile", "")]
    for spec in preset.get("jobs", []):
        parts += [spec.get("posting", ""), spec.get("research", "")]
    parts += list(scenario.get("files", {}).values())
    return "\n\n".join(p for p in parts if p)


def run_scenario(scenario, model, context=None, judge=None, keep_dir=None):
    context = context if context is not None else skill_context()
    sandbox = Sandbox(scenario)
    log, history, results, snapshots = [], [], [], {}
    sources = fictional_sources(scenario)
    try:
        for index, step in enumerate(scenario["steps"], 1):
            user = fill(step["user"], sandbox.env)
            start = len(log)
            script_problems = []
            if step.get("answers_previous_question") and history:
                last_coach = next((m for role, m in reversed(history) if role == "assistant"), "")
                _, script_problems = run_judge(judge, ["script_fits_question"], user, last_coach, history[:-1] if history else (), sources)
                script_problems = [f"scenario script: {p}" for p in script_problems]
            reply, activity = run_turn(model, sandbox, context, scenario, history, user, log)
            expect = json.loads(fill(json.dumps({"must_contain_any": step.get("must_contain_any", [""]),
                                                 "must_not_contain": step.get("must_not_contain", []),
                                                 "required_groups": step.get("required_groups", [])}), {k: json.dumps(str(v))[1:-1] for k, v in sandbox.env.items()}))
            errors = check(expect, reply)
            saves = [e for e in log[start:] if "subcommand" in e and e["subcommand"] in SAVE_COMMANDS]
            failed_save = bool(saves) and saves[-1]["rc"] not in OK_EXIT.get(saves[-1]["subcommand"], (0,))  # a retried save that finally succeeded is no failure
            judge_items = list(step.get("judge", [])) + (list(step.get("judge_if_rated", [])) if SCORE.search(reply) else []) + (["no_success_claim"] if failed_save and judge is not None and "no_success_claim" not in step.get("judge", []) else [])
            errors += evaluate_tools(step, log, start, reply, judged=judge is not None)
            if step.get("no_preference_penalty"):
                errors += [f"score justified by the declined role preference: {line!r}" for line in preference_penalty_lines(reply)]
            if step.get("no_unstated_characterization"):
                errors += [f"characterization the candidate did not state: {x!r}" for x in unstated_characterizations(reply, sources + " " + " ".join(m for r, m in history if r == "user") + " " + user)]
            if step.get("no_example_deduction"):
                errors += [f"score blamed on a missing example the question did not ask for: {line!r}" for line in example_penalty_lines(reply)]
            if "max_question_marks" in step and question_marks(reply) > step["max_question_marks"]:
                errors.append(f"reply has {question_marks(reply)} question marks, at most {step['max_question_marks']} allowed (one question per turn)")
            if step.get("no_resume_promise") and promises_resume(reply):
                errors.append("stop reply promises to resume the open follow-up or session although a stopped run is final (only pause keeps a checkpoint)")
            if step.get("evaluable_over"):   # the block evaluation may already have been given in earlier steps of the same block
                earlier = "\n".join(results[i - 1]["reply"] for i in step["evaluable_over"] if 0 < i < index)
                errors += structural_errors(dict(step, evaluable=True), earlier + "\n" + reply)
            errors += structural_errors(step, reply)
            detail = {}
            judged_reply = reply
            if step.get("evaluable_over"):   # the block evaluation may have been given in earlier replies of the same block: the judge sees all of it
                judged_reply = "\n\n".join(results[i - 1]["reply"] for i in step["evaluable_over"] if 0 < i < index) + "\n\n" + reply
            _, judge_problems = run_judge(judge, judge_items, user, judged_reply, list(history), sources, detail)
            errors += judge_problems + script_problems
            results.append({"step": index, "errors": errors, "reply": reply, "judge_detail": detail, "tools": [e.get("line") or e.get("rejected") for e in log[start:]]})
            snapshots[index] = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
                                for p in glob.glob(str(sandbox.tmp / "ws/candidates/*/runs/*.md"))}
            history.append(("user", user))
            history.append(("assistant", ("\n".join(activity) + "\n" if activity else "") + reply))
        final = check_artifacts(sandbox, scenario.get("artifacts", []), snapshots)
        every = [e for r in results for e in r["errors"]] + final
        unclear = [e for e in every if e.startswith(("rubric unclear", "scenario script", "semantic rubric not checked"))]
        failed = [e for e in every if e not in unclear]
        status = "FAIL" if failed else "UNCLEAR" if unclear else "PASS"
        return {"id": scenario["id"], "steps": results, "artifact_errors": final, "tool_log": log, "judge": judge is not None,
                "status": status, "unclear": unclear, "passed": status == "PASS"}
    finally:
        if keep_dir:
            preserve_artifacts(sandbox, keep_dir)
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


CALIBRATION = ROOT / "tests/fixtures/behavior/judge_cases"


def calibration_cases():
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(CALIBRATION.glob("*.json"))]


def run_calibration(judge, cases=None):
    """Ask the REAL judge about stored fictional replies with a known correct verdict. Returns [(case id, key, expected, got, ok)]."""
    results = []
    for case in cases if cases is not None else calibration_cases():
        verdicts, _ = run_judge(judge, list(case["expect"]), case["user"], case["reply"], [tuple(x) for x in case.get("history", [])], case.get("evidence", ""))
        for key, expected in case["expect"].items():
            results.append((case["id"], key, expected, verdicts.get(key), verdicts.get(key) is expected))
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cli", choices=("claude", "codex"))
    p.add_argument("--scenario", help="single scenario id")
    p.add_argument("--timeout", type=int, default=240)
    p.add_argument("--output-dir", type=Path)
    p.add_argument("--list", action="store_true")
    p.add_argument("--judge-calibration", action="store_true", help="run the real judge on stored replies with known verdicts (overlooked product errors)")
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
    if args.judge_calibration:
        with tempfile.TemporaryDirectory(prefix="coach-model-cwd-") as workdir:
            rows = run_calibration(cli_model(args.cli, args.timeout, workdir, args.codex_sandbox))
        for case, key, expected, got, ok in rows:
            print(("PASS " if ok else "FAIL ") + f"{case} {key}: expected {expected}, judge said {got}")
        return int(not all(r[4] for r in rows))
    out.mkdir(parents=True, exist_ok=True)
    failures = 0
    with tempfile.TemporaryDirectory(prefix="coach-model-cwd-") as workdir:
        model = cli_model(args.cli, args.timeout, workdir, args.codex_sandbox)
        judge = None if args.no_judge else model
        for name in ids:
            try:
                result = run_scenario(load(name), model, judge=judge, keep_dir=out / "artifacts" / name)
            except (RuntimeError, subprocess.TimeoutExpired) as exc:
                result = {"id": name, "passed": False, "error": str(exc), "steps": [], "artifact_errors": [], "tool_log": []}
            (out / f"{name}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
            print(result.get("status", "PASS" if result["passed"] else "FAIL") + " " + name)
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
