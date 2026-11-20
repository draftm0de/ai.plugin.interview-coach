#!/usr/bin/env python3
"""Native host acceptance in an isolated temporary project (explicit, consumes model credits).

Claude Code: the payload copy is loaded with --plugin-dir (nothing is installed, no personal settings are changed).
Codex: the payload `skills/` tree is copied to <project>/.agents/skills (project-scoped skill discovery; a marketplace
plugin installation would change personal host configuration and is NOT performed). Both hosts use the user's own
existing sign-in through their normal CLI; no credentials are read or copied. Every phase is a NEW chat (no session
persistence). Fictional data only; the runtime pointer directory is redirected into the temporary project.
Results are observations of these runs; the dialogue checks are structural, not a proof of quality.
"""
import argparse
import hashlib
import re
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills/_shared/scripts"))
import interview_workspace as iw  # noqa: E402

SKILLS = ("interview-coach", "candidate-create", "candidate-training", "job-create", "job-training")
CV = "# Erika Beispiel\n\n## Berufserfahrung\n- Backend-Entwicklerin, Muster GmbH, 2019-2024\n\n## Skills\nPython, Go, SQL\n"
POSTING = "# Senior Backend Engineer (m/w/d)\nBeispiel AG, Zürich\nAufgaben: Python-APIs, Kubernetes-Betrieb, Mentoring.\nAnforderungen: 5+ Jahre Python, Cloud-Betrieb.\n"
ANSWER = ("Bei einem Zahlungsausfall in Produktion habe ich die Ursache in der Retry-Logik gefunden, einen Fix mit Regressionstest "
          "gebaut und den Support informiert. Danach sank die Fehlerrate von 40 auf 2 Fälle pro Tag.")


class Host:
    def __init__(self, name, project, payload, config, timeout, web=False):
        self.name, self.project, self.payload, self.config, self.timeout, self.web = name, project, payload, config, timeout, web
        if name == "codex":
            shutil.copytree(payload / "skills", project / ".agents/skills")

    def invoke(self, skill, text):
        prefix = f"/interview-coach:{skill} " if self.name == "claude" else f"${skill} "
        env = dict(os.environ, XDG_CONFIG_HOME=str(self.config))
        if self.name == "claude":
            cmd = ["claude", "-p", prefix + text, "--plugin-dir", str(self.payload), "--no-session-persistence", "--setting-sources", "project",
                   "--permission-mode", "acceptEdits", "--allowedTools", "Skill", "Bash(python3 *)", "Read", "Write",
                   *(["WebFetch", "WebSearch"] if self.web else []),
                   "--output-format", "stream-json", "--verbose"]
        else:
            cmd = ["codex", *(["--search"] if self.web else []), "exec", "--json", "--skip-git-repo-check", "--ephemeral", "--ignore-user-config", "--ignore-rules",
                   "--sandbox", "workspace-write", "-C", str(self.project), prefix + text]
        done = subprocess.run(cmd, cwd=self.project, env=env, capture_output=True, text=True, timeout=self.timeout)
        return self.parse(done)

    def parse(self, done):
        """Normalize host events. Each command gets `exit` ONLY if its results are unambiguous.

        Claude reports no numeric exit code: `exit` is DERIVED from the tool_result flag (is_error -> 1, else 0) and marked
        `exit_source: derived-from-is_error`. Codex reports `exit_code` itself (`exit_source: host-exit_code`). All results of one
        tool call are collected; differing results (error then success, or success then error, in any order) make the call
        `conflict` with `exit` None - nothing is overwritten, "last result wins" does not exist. Identical repeated results are
        consistent. Results without a usable id never mark any call; calls without a result stay unknown (None). Duplicate tool ids
        across calls make all of them `ambiguous` (exit None).
        """
        result = {"exit": done.returncode, "text": "", "commands": [], "skills": [], "web": [], "stderr": done.stderr[-300:]}
        pending = {}   # claude: tool_use_id -> list of derived statuses
        for line in done.stdout.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if self.name == "claude":
                if event.get("type") == "system" and event.get("subtype") == "init":
                    result["skills"] = [s for s in event.get("skills", []) if s.startswith("interview-coach")]
                elif event.get("type") == "assistant":
                    for part in event["message"]["content"]:
                        if part["type"] == "tool_use" and part["name"] == "Bash":
                            result["commands"].append({"command": part["input"].get("command", ""), "id": part.get("id"), "results": [],
                                                       "exit_source": "derived-from-is_error"})
                        elif part["type"] == "tool_use" and part["name"] in ("WebFetch", "WebSearch"):
                            result["web"].append({"tool": part["name"], "input": part["input"]})
                        elif part["type"] == "text":
                            result["text"] = part["text"]
                elif event.get("type") == "user" and isinstance(event.get("message", {}).get("content"), list):
                    for part in event["message"]["content"]:
                        if isinstance(part, dict) and part.get("type") == "tool_result" and part.get("tool_use_id"):
                            pending.setdefault(part["tool_use_id"], []).append(1 if part.get("is_error") else 0)
                elif event.get("type") == "result":
                    result["text"] = event.get("result") or result["text"]
            else:
                item = event.get("item", {})
                if event.get("type") == "item.completed" and item.get("type") == "command_execution":
                    known = next((c for c in result["commands"] if item.get("id") and c.get("id") == item["id"]), None)
                    if known is not None:
                        known["results"].append(item.get("exit_code"))
                    else:
                        result["commands"].append({"command": item["command"], "id": item.get("id"), "results": [item.get("exit_code")],
                                                   "exit_source": "host-exit_code"})
                elif event.get("type") == "item.completed" and item.get("type") == "web_search":
                    result["web"].append({"tool": "web_search", "input": {k: item.get(k) for k in ("query", "action") if item.get(k)}})
                elif event.get("type") == "item.completed" and item.get("type") == "agent_message":
                    result["text"] = item["text"]
        for command in result["commands"]:
            if self.name == "claude" and command.get("id"):
                command["results"] = list(pending.get(command["id"], []))
        ids = [c["id"] for c in result["commands"] if c.get("id")]
        for command in result["commands"]:
            outcomes = command["results"]
            command["ambiguous"] = bool(command.get("id")) and ids.count(command["id"]) > 1
            command["conflict"] = len(set(outcomes)) > 1
            single = outcomes[0] if len(set(outcomes)) == 1 else None
            command["exit"] = None if (command["ambiguous"] or command["conflict"]) else single
        return result


def runtime_calls(result):
    return [c for c in result["commands"] if "interview_workspace.py" in c["command"]]


_SHELLS = {"sh", "bash", "zsh", "dash"}
_PUNCT = set("();<>|&")


def parse_runtime_call(command, _depth=0):
    """Parse ONE plain runtime invocation, or return None if it cannot be proven to be exactly that.

    Accepts `python3 <...>/interview_workspace.py [--config-dir X] SUBCOMMAND --flag value ...`, optionally wrapped once or twice
    in `sh|bash|zsh -c|-lc '<command>'`. Anything compound or ambiguous (`;`, `&&`, `||`, pipes, redirects, subshells, variable
    prefixes) yields None, so a succeeding shell cannot vouch for the runtime call inside it. Values containing `$` or backticks are
    unresolved and are reported as such. Quoting is honored (shlex). This is deliberately not a shell interpreter.
    """
    import shlex
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return None
    if not tokens or any(t and set(t) <= _PUNCT for t in tokens):
        return None
    if Path(tokens[0]).name in _SHELLS and len(tokens) == 3 and tokens[1] in ("-c", "-lc", "-ic") and _depth < 2:
        return parse_runtime_call(tokens[2], _depth + 1)
    if Path(tokens[0]).name not in ("python3", "python") or len(tokens) < 3:
        return None
    index = 1
    while index < len(tokens) and tokens[index].startswith("-") and tokens[index] != "-":
        index += 2 if tokens[index] in ("-W", "-X") else 1
    if index >= len(tokens) or Path(tokens[index]).name != "interview_workspace.py":
        return None
    rest = tokens[index + 1:]
    options, subcommand, position = {}, None, 0
    while position < len(rest):
        token = rest[position]
        if token.startswith("--"):
            key, equals, value = token[2:].partition("=")
            if not equals:
                nxt = rest[position + 1] if position + 1 < len(rest) and not rest[position + 1].startswith("--") else None
                value = nxt if nxt is not None else ""
                position += 2 if nxt is not None else 1
            else:
                position += 1
            if subcommand is None and key != "config-dir":
                return None
            options[key] = value
        elif subcommand is None:
            subcommand = token
            position += 1
        else:
            return None  # unexpected positional argument: not a call shape this runner can vouch for
    if subcommand is None:
        return None
    return {"subcommand": subcommand, "options": options, "unresolved": any("$" in v or "`" in v for v in options.values())}


def subcommands(result, ok_only=False):
    """Runtime subcommands of a host result.

    Default: every mention (lenient, for "was the runtime touched at all" checks).
    ok_only: only calls that are ONE provable runtime invocation whose own tool result had exit code 0 (None/unknown is not success).
    """
    out = []
    for call in runtime_calls(result):
        if ok_only:
            parsed = parse_runtime_call(call["command"])
            if parsed is None or call.get("exit") != 0 or call.get("conflict") or call.get("ambiguous"):
                continue
            out.append(parsed["subcommand"])
        else:
            words = call["command"].split("interview_workspace.py", 1)[1].split()
            out.append(next((w for w in words if not w.startswith("-") and "/" not in w), ""))
    return out


def successful_calls(result, subcommand, **expected):
    """Proven successful single calls of `subcommand` whose options equal `expected` (project compares as resolved path)."""
    found = []
    for call in runtime_calls(result):
        parsed = parse_runtime_call(call["command"])
        if (parsed is None or call.get("exit") != 0 or call.get("conflict") or call.get("ambiguous")
                or parsed["subcommand"] != subcommand or parsed["unresolved"]):
            continue
        ok = True
        for key, want in expected.items():
            have = parsed["options"].get(key)
            if key == "project":
                ok = ok and have is not None and Path(have).resolve() == Path(want).resolve()
            else:
                ok = ok and have == want
        if ok:
            found.append(parsed)
    return found


# Clarification = a question about WHO/WHAT DATA (candidate choice, profile confirmation, missing preparation), not about the job.
# General question words ("welche", "zwei", "korrekt") are NOT clarifications on their own; they need a meta object or a meta phrase.
META_OBJECT = re.compile(r"(?i)\b(kandidat\w*|bewerber\w*|profil\w*|angaben|lebenslauf|workspace|speicher\w*|stellenvorbereitung|vorbereitung|id)\b|\berika\b|\bmax\b")
META_ACT = re.compile(r"(?i)\b(welche[rsnm]?|meinst|gemeint|auswähl\w*|wähle|bestätig\w*|korrekt|stimm\w*|vollständig|anleg\w*|angelegt|fortfahren|verwenden|soll|sollen|möchtest|willst)\b")
META_PHRASE = re.compile(r"(?i)\b(meinst du|ist (?:damit )?gemeint|soll ich|sollen wir)\b")
JOB_TERMS = ("python", "kubernetes", "api", "cloud", "mentoring", "backend", "beispiel ag")


def is_clarification(sentence):
    return bool(META_PHRASE.search(sentence) or (META_OBJECT.search(sentence) and META_ACT.search(sentence)))


_ORD = r"((erste|zweite|dritte|nächste)\s+)?(interview)?frage(\s*\d+(\s*(von|/)\s*\d+)?)?"
HEADING_ONLY = re.compile(r"(?i)^[\s*_#>\-]*" + _ORD + r"[\s*_:.\-]*$|^[\s*_#>\-]*\d+[.)][\s*_]*$")
HEADING_PREFIX = re.compile(r"(?i)^[\s*_#>\-]*" + _ORD + r"[\s*_]*:[\s*_]*")
IMPERATIVE = re.compile(r"(?i)^[*_\s]*(erzähl|beschreib|nenn|stell|erkläre|erläuter|schilder|berichte|skizzier|zeig|gib |wie |was |warum |welche|wann |woran |wodurch |womit |inwiefern|kannst du|könntest du)")


def training_question(text):
    """Deterministic, bounded heuristic: did a job-related interview question start the training?

    Accepts a reply that (1) refers to the stored job (posting vocabulary) and (2) contains a question or task that is not a
    clarification (candidate choice, profile confirmation, missing preparation). A stand-alone heading ("**Erste Frage:**",
    "Frage 2 von 4:", "1.") is not a question: it is dropped, and the remaining content (next line, or the text after the heading
    on the same line) must itself end with "?" or start like a task ("Nenne …", "Beschreibe …"); a heading never makes arbitrary
    text such as "Einen Moment bitte." count. Limits: only the listed heading styles
    are recognized; a regex cannot understand meaning; an unusual clarification wording may pass, an interview question that names
    a candidate/profile object together with a meta verb may be rejected, and the job reference is checked on the whole reply, not
    per question. It is no proof of interview quality.
    """
    sentences = []
    for raw in text.splitlines():
        line = raw.strip()
        if line:
            sentences += re.split(r"(?<=[?!.])\s+", line)
    items = []
    for sentence in (x.strip() for x in sentences if x.strip()):
        if HEADING_ONLY.match(sentence):
            continue                      # empty heading or bare numbering: carries no question itself
        prefix = HEADING_PREFIX.match(sentence)
        if prefix:
            sentence = sentence[prefix.end():].strip()   # same-line heading: only the remaining content counts
            if not sentence:
                continue
        items.append(sentence)
    # The remaining content must itself be a recognizable question or task; a heading never turns arbitrary text into one.
    asks = [x for x in items if x.endswith("?") or IMPERATIVE.match(x)]
    interview = [x for x in asks if not is_clarification(x)]
    if not any(t in text.lower() for t in JOB_TERMS):
        return False, "reply does not refer to the stored job"
    if not interview:
        return False, "no job-related interview question (only clarification, headings, other text, or none)"
    return True, ""


import re  # noqa: E402


class Run:
    def __init__(self, host_name, timeout, keep=False):
        self.tmp = Path(tempfile.mkdtemp(prefix=f"coach-native-{host_name}-")).resolve()
        self.payload = self.tmp / "plugin"
        for name in ("skills", "assets", ".claude-plugin", ".codex-plugin"):
            shutil.copytree(ROOT / name, self.payload / name)
        (self.payload / "README.md").write_text("Interview Coach payload copy for native acceptance.\n")
        self.project = self.tmp / "project"
        self.project.mkdir()
        self.config = self.project / ".cfg"
        self.files = self.project / "files"
        self.files.mkdir()
        (self.files / "cv.md").write_text(CV)
        (self.files / "posting.md").write_text(POSTING)
        self.host = Host(host_name, self.project, self.payload, self.config, timeout)
        self.ws = self.project / "storage"
        self.results = []
        self.keep = keep

    def rt(self, *args):
        done = subprocess.run([sys.executable, "-B", str(self.payload / "skills/_shared/scripts/interview_workspace.py"),
                               "--config-dir", str(self.config / "zyris/interview-coach/projects"), *map(str, args)],
                              capture_output=True, text=True)
        return done.returncode, done.stdout, done.stderr

    def candidates(self):
        return json.loads(self.rt("candidate-list", "--project", self.project)[1] or "[]")

    def phase(self, name, skill, text, check):
        try:
            result = self.host.invoke(skill, text)
            problems = check(result) or []
            problems = ([f"host exit code {result['exit']}"] if result["exit"] else []) + problems
        except subprocess.TimeoutExpired:
            result, problems = {"text": "", "commands": []}, ["timeout"]
        self.results.append({"phase": name, "passed": not problems, "problems": problems, "subcommands": subcommands(result),
                             "reply_excerpt": result["text"][:400], "skills_seen": result.get("skills", []),
                             "web_tools": result.get("web", [])})
        print(("PASS " if not problems else "FAIL ") + name + "".join("\n  - " + p for p in problems), flush=True)

    def cleanup(self):
        if not self.keep:
            shutil.rmtree(self.tmp, ignore_errors=True)


def phases(run):
    c = {"ws": run.ws, "p": run.project, "f": run.files}

    def discovery(r):
        if run.host.name == "claude":
            return [] if sorted(r["skills"]) == sorted(f"interview-coach:{s}" for s in SKILLS) else [f"skills seen: {r['skills']}"]
        text = r["text"]
        return [f"missing skill name {s}" for s in SKILLS if s not in text] + (
            [] if any("_shared/scripts/interview_workspace.py" in x["command"] for x in r["commands"]) else ["runtime was not run from the payload layout"])

    def three(r):
        t = r["text"]
        p = [f"option missing: {o}" for o in ("Lokal", "Git", "Nicht speichern") if o not in t]
        p += ["offers a fourth mode" for _ in [0] if "selbst verwalten" in t.lower() and "nicht" not in t.lower()]
        p += ["runtime changed state before the decision" for _ in [0] if set(subcommands(r)) & {"project-init", "candidate-create"}]
        p += ["files created before the decision" for _ in [0] if any(run.project.glob("storage")) or any(run.config.glob("zyris"))]
        return p

    def setup(r):
        ok = (run.ws / "workspace.json").is_file() and "project-init" in subcommands(r)
        code = run.rt("validate", "--project", run.project)[0]
        return ([] if ok else ["workspace was not created via project-init"]) + ([] if code == 0 else ["workspace invalid"])

    def with_cv(r):
        found = run.candidates()
        if len(found) != 1:
            return [f"expected one candidate, found {len(found)}"]
        original = next((run.ws / "candidates" / found[0]["candidate_id"] / "cv").glob("cv-001/original.md"), None)
        want = hashlib.sha256((run.files / "cv.md").read_bytes()).hexdigest()
        return [] if original and hashlib.sha256(original.read_bytes()).hexdigest() == want else ["CV original missing or not byte-exact"]

    def unconfirmed(r):
        found = [x for x in run.candidates() if x["display_name"] == "Max Muster"]
        p = [] if len(found) == 1 else ["Max Muster not created exactly once"]
        if found and found[0]["profile_status"] == "confirmed":
            p.append("profile confirmed without the user's confirmation")
        return p + ([] if "?" in r["text"] else ["no confirmation question"])

    def confirmed(r):
        found = [x for x in run.candidates() if x["display_name"] == "Max Muster"]
        return [] if found and found[0]["profile_status"] == "confirmed" else ["profile not confirmed after the user's confirmation"]

    def same_name(r):
        p = [] if r["text"].count("?") >= 1 else ["no clarifying question"]
        return p + (["saved a run although the candidate was ambiguous"] if "finish" in subcommands(r) else [])

    def erika():
        found = [x for x in run.candidates() if x["display_name"] == "Erika Beispiel"]
        return found

    def erika_confirmed(r):
        found = erika()
        p = [] if len(found) == 1 else [f"expected exactly one Erika Beispiel, found {len(found)}"]
        if len(found) == 1 and found[0]["profile_status"] != "confirmed":
            p.append("Erika's profile is not confirmed")
        return p + ([] if "profile-save" in subcommands(r, ok_only=True) else ["no successful profile-save"])

    def job(r):
        found = erika()
        if len(found) != 1:
            return [f"expected exactly one Erika Beispiel, found {len(found)}"]
        jobs = json.loads(run.rt("job-list", "--project", run.project, "--candidate", found[0]["candidate_id"])[1] or "[]")
        p = [] if jobs and jobs[0]["company"] else ["no job with company was created for this candidate"]
        return p + ([] if "job-create" in subcommands(r, ok_only=True) else ["no successful job-create"])

    def job_training(r):
        found = erika()
        if len(found) != 1 or found[0]["profile_status"] != "confirmed":
            return ["precondition missing: exactly one Erika with a confirmed profile"]
        cid = found[0]["candidate_id"]
        jobs = json.loads(run.rt("job-list", "--project", run.project, "--candidate", cid)[1] or "[]")
        if len(jobs) != 1:
            return [f"expected one stored job for this candidate, found {len(jobs)}"]
        p = []
        if not successful_calls(r, "job-show", project=str(run.project), candidate=cid, job=jobs[0]["job_id"]):
            p.append("no proven successful job-show for this project, candidate and job (single call, exit 0, matching IDs)")
        asked, why = training_question(r["text"])
        return p + ([] if asked else [why])

    def training_saved(r):
        runs = list(run.ws.glob("candidates/*/runs/*.md"))
        return [] if runs and "finish" in subcommands(r, ok_only=True) and any('"stopped_early"' in p.read_text() for p in runs) else ["run not saved as stopped_early"]

    def reload(r):
        names = [p.stem for p in run.ws.glob("candidates/*/runs/*.md")]
        return [] if names and any(n in r["text"] for n in names) else ["new chat did not find the saved run"]

    return [
        ("discovery", "interview-coach", "status. Nenne außerdem alle Skills dieses Plugins (nur Namen).", discovery),
        ("three_options", "interview-coach", "Ich möchte ein Interview üben. (Noch keine Speicherentscheidung; stelle nur den ersten Einrichtungsschritt.)", three),
        ("setup_local", "interview-coach", f"setup: Speicherart Lokal, Ziel {c['ws']}, ich bestätige das Ziel. Sprache Deutsch für Bedienung und Interview.", setup),
        ("candidate_with_cv", "candidate-create", f"Bewerber: Erika Beispiel. Ja, ein Lebenslauf liegt vor: {c['f']}/cv.md", with_cv),
        ("candidate_without_cv_unconfirmed", "candidate-create", "Bewerber: Max Muster, kein Lebenslauf. Meine Angaben: 5 Jahre Backend-Entwickler bei Beispiel GmbH (Python, Go), BSc Informatik, Projekt Zahlungs-API, Ziel Team Lead. Speichere sie als Entwurf und frage mich danach zur Bestätigung, bevor sie als verifiziert gelten.", unconfirmed),
        ("candidate_confirm_new_chat", "candidate-create", "Für Max Muster: Ja, die Angaben (5 Jahre Backend, Python/Go, BSc Informatik, Zahlungs-API, Ziel Team Lead) stimmen alle. Bitte bestätigen.", confirmed),
        ("candidate_confirm_erika", "candidate-create", "Für Erika Beispiel (die mit dem Lebenslauf cv.md): Ja, die aus dem Lebenslauf übernommenen Angaben stimmen alle, auch die Lücken sind akzeptiert. Bitte als bestätigt speichern.", erika_confirmed),
        ("job_create", "job-create", f"Bereite die Stelle aus {c['f']}/posting.md für Erika Beispiel vor. Das Unternehmen ist die Beispiel AG. Die Interviewer sind unbekannt. Recherchiere nicht im Web, vermerke das als offen.", job),
        ("job_training", "job-training", "Starte das Training für die gespeicherte Stelle bei der Beispiel AG für Erika Beispiel. Stelle nur die erste Interviewfrage.", job_training),
        ("same_name_selection", "candidate-training", "__SAME_NAME__", same_name),
        ("training_saved", "candidate-training", f"Allgemeines Training für Max Muster. Deine Frage war: 'Beschreibe einen Produktionsfehler, den du gelöst hast.' Meine Antwort: {ANSWER} Bewerte sie kurz und beende dann mit stop.", training_saved),
        ("reload_new_chat", "interview-coach", "Welche Trainingsläufe gibt es für Max Muster? Nenne die Run-IDs.", reload),
    ]


POSTING_URL = "https://www.python.org/jobs/8211/"


def research_phases(run):
    """Real public posting + fictional candidate. Needs web access; checks the saved artifacts against what the host really fetched."""
    import re
    import datetime
    today = datetime.date.today().isoformat()
    rc, out, err = run.rt("project-init", "--project", run.project, "--storage", "local", "--path", run.ws)
    cid = json.loads(run.rt("candidate-create", "--project", run.project, "--name", "Erika Beispiel")[1])["candidate_id"]
    (run.files / "profile.md").write_text("# Profil Erika Beispiel (fiktiv)\n- Backend-Entwicklerin, 5 Jahre Python (Quelle: Nutzerangabe)\n- FastAPI, PostgreSQL (Quelle: Nutzerangabe)\n")
    iw.save_profile(run.ws, cid, run.files / "profile.md", status="confirmed", origin="interview", user_confirmed=True)

    def created(r):
        p = []
        jobs = json.loads(run.rt("job-list", "--project", run.project, "--candidate", cid)[1] or "[]")
        if len(jobs) != 1:
            return [f"expected one job, found {len(jobs)}"]
        shown = json.loads(run.rt("job-show", "--project", run.project, "--candidate", cid, "--job", jobs[0]["job_id"])[1])
        posting = shown["latest"].get("posting")
        research = shown["latest"].get("research")
        match = shown["latest"].get("match")
        if not posting or "TGScope" not in posting["content"] or "FastAPI" not in posting["content"]:
            p.append("posting text does not contain the real page content")
        elif POSTING_URL not in posting["meta"]["sources"] or posting["meta"]["retrieved_at"] != today:
            p.append("posting origin/date not recorded")
        if shown["job"]["participants"]["status"] != "unknown":
            p.append("participants not recorded as unknown")
        if not research:
            p.append("no research snapshot")
        else:
            fetched = {w["input"].get("url") for w in r["web"] if w["tool"] == "WebFetch"}
            searched = bool([w for w in r["web"] if w["tool"] in ("WebSearch", "web_search")])
            if not research["meta"]["sources"]:
                p.append("research without sources")
            for src in research["meta"]["sources"]:
                url = src if isinstance(src, str) else src.get("url")
                if url not in fetched and not (searched and run.host.name == "codex"):
                    p.append(f"source never fetched by the host: {url}")
            if research["meta"]["retrieved_at"] != today:
                p.append("research retrieval date missing/wrong")
            text = research["content"].lower()
            for label, pattern in (("facts", r"fakten|facts"), ("inference", r"schlussfolgerung|ableitung|inference"), ("unknown", r"unbekannt|unknown|offen")):
                if not re.search(pattern, text):
                    p.append(f"research does not separate {label}")
        if not match:
            p.append("no profile/job comparison saved")
        if not r["web"]:
            p.append("host used no web tool at all")
        return p

    def reused(r):
        jobs = json.loads(run.rt("job-list", "--project", run.project, "--candidate", cid)[1] or "[]")
        p = [] if "job-show" in subcommands(r, ok_only=True) else ["stored preparation was not loaded"]
        if jobs and jobs[0]["artifacts"]["research"] != 1:
            p.append("research was redundantly duplicated instead of reused")
        return p + ([] if "?" in r["text"] else ["no interview question"])

    return [
        ("research_job_create_live", "job-create", f"Bereite die Stelle {POSTING_URL} für Erika Beispiel vor (Profil ist bestätigt). Lies die Anzeige tatsächlich aus dem Web, das Unternehmen ist TGScope. Die Interviewer sind unbekannt. Recherchiere öffentlich zum Unternehmen, speichere Anzeige, Recherche (mit Quellen und Abrufdatum; trenne Fakten, Schlussfolgerungen, Unbekanntes) und den Abgleich mit dem Profil.", created),
        ("research_job_training_reuse", "job-training", "Training für die TGScope-Stelle von Erika Beispiel. Stelle nur die erste Frage und nutze die vorhandene Vorbereitung.", reused),
    ]


def no_storage(run, results):
    project = run.tmp / "project-nostorage"
    project.mkdir()
    host = Host(run.host.name, project, run.payload, project / ".cfg", run.host.timeout)
    before = sorted(p.name for p in project.rglob("*"))
    r = host.invoke("candidate-training", "Nicht speichern. Allgemeines Training für eine Team-Lead-Rolle. Frage war: 'Wie priorisierst du?' Meine Antwort: Nach Risiko und Nutzen, abgestimmt mit dem Product Owner. Bewerte kurz und beende mit stop.")
    after = sorted(p.name for p in project.rglob("*"))
    created = [n for n in after if n not in before and n != ".agents" and not n.startswith("skills") and n not in ("_shared",)]
    problems = []
    if runtime_calls(r):
        problems.append("runtime was called in Nicht speichern mode")
    if [n for n in created if n not in (".cfg",)]:
        problems.append(f"files created: {created[:5]}")
    results.append({"phase": "no_storage", "passed": not problems, "problems": problems, "subcommands": subcommands(r), "reply_excerpt": r["text"][:300]})
    print(("PASS " if not problems else "FAIL ") + "no_storage" + "".join("\n  - " + p for p in problems), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", choices=("claude", "codex"), required=True)
    p.add_argument("--timeout", type=int, default=420)
    p.add_argument("--only", help="comma separated phase names")
    p.add_argument("--output", type=Path)
    p.add_argument("--keep", action="store_true")
    p.add_argument("--research", action="store_true", help="run only the live-web research acceptance (real public posting)")
    args = p.parse_args()
    if not shutil.which(args.host):
        print(f"NOT RUN: {args.host} CLI not available")
        return 2
    run = Run(args.host, args.timeout, args.keep)
    if args.research:
        run.host.web = True
    try:
        for name, skill, text, check in (research_phases(run) if args.research else phases(run)):
            if args.only and name not in args.only.split(","):
                continue
            if text == "__SAME_NAME__":
                run.rt("candidate-create", "--project", run.project, "--name", "Erika Beispiel")
                text = "Allgemeines Training für Erika Beispiel."
            run.phase(name, skill, text, check)
        if not args.research and (not args.only or "no_storage" in args.only.split(",")):
            no_storage(run, run.results)
    finally:
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps({"host": args.host, "results": run.results}, ensure_ascii=False, indent=1))
        run.cleanup()
    failed = [r for r in run.results if not r["passed"]]
    print(f"{len(run.results) - len(failed)}/{len(run.results)} native phases passed (observations of one run each).")
    return int(bool(failed))


if __name__ == "__main__":
    sys.exit(main())
