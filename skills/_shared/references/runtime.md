# Runtime reference

`RUNTIME` = `skills/_shared/scripts/interview_workspace.py` inside the installed plugin. From a skill folder it is
`../_shared/scripts/interview_workspace.py`. Use it with `python3`. Do not assume a developer checkout.
`PROJECT` = absolute path of the current project folder. Every command except `validate --path` needs
`--project PROJECT`; the pointer is stored per project outside the plugin and workspace, so projects never switch each other.
Output is JSON; failures print `ERROR: ...` (exit 1) or, for ambiguous selections, JSON choices (exit 2).
Never claim success unless the command exited with 0.

| Task | Command |
| --- | --- |
| Storage setup | `project-init --project P --storage local --path DIR` |
| Show / validate | `project-show`, `validate` |
| Languages | `set-language --interface de` (project interface only); `set-interview-language --candidate ID --language de` (candidate default); `set-interview-language --candidate ID --job J --language en` (job override); `set-interview-language --candidate ID --job J --inherit` (use candidate default) |
| Candidates | `candidate-create --name N`, `candidate-list`, `candidate-resolve [--id ID \| --name N]`, `candidate-status --candidate ID`, `candidate-recover --candidate ID` |
| CV | `cv-import --candidate ID --file F [--transcription-file T]`, `cv-draft-save --candidate ID --file F` |
| Profile | `profile-save --candidate ID --file F --status draft\|confirmed --origin cv\|interview [--cv-source cv-001] [--user-confirmed] [--acknowledge-gaps]` |
| Jobs | `job-create --candidate ID --title T [--company C] (--posting-file F \| --posting-text-file F) [--source-url U --retrieved-at YYYY-MM-DD]`, `job-list`, `job-show --job J`, `job-add --job J --kind research\|match\|preparation\|posting --file F [--source U]... [--retrieved-at D]`, `job-update --job J [--company] [--title] [--participants-status pending\|provided\|unknown] [--person "Name::Role"]... [--verify-person p-1]...` |
| Runs | `status --candidate ID`, `resume --candidate ID --run-id R`, `finish --candidate ID --run-id R --run-file F --state-file S --expected-state-sha256 H --status completed\|paused\|stopped_early --answered-count N [--planned-count M] [--resume-from R0] [--job-id J] --dialogue-file D`, `recover --candidate ID` |

## Rules

- Run every runtime command as ONE direct call: `python3 /absolute/path/interview_workspace.py SUBCOMMAND --project /absolute/project ...`. No shell variables, `cd`, pipes, `&&`/`;` chains or wrappers: hosts may refuse compound calls, and a refused call is not a result. Read reference files with the Read tool.

- Candidate and job identifiers come from the runtime; display names are data and never paths.
- Resolve candidates with `candidate-resolve`; exit 2 means ambiguous or unknown: ask the user, never guess.
- A job belongs to exactly one candidate. Pass the `--candidate` that owns it; foreign IDs are rejected.
- Read `status` (or `resume`) before preparing a new `state.md`; pass its `state_sha256` unchanged. A stale hash is a
  hard error: re-read and reconcile, do not refresh the hash blindly.
- Failed saves: follow the error text (recover, retry same run ID, or inspect). Do not create a second run ID as a workaround.
- Extraction tools are never installed. If the runtime reports a missing capability, tell the user exactly what is missing.
- `job-add --kind match` is refused unless the candidate's profile is `confirmed` (`profile_reliable` in `status`).
- `--dialogue-file` (required) is strict JSON: a list of blocks `{key:"q-N", question, initial_answer|null, initial_assessment|null, block_assessment|null, followups:[{id:"q-N-fM", kind:clarification|completion|deepening, reason, text, answer|null, hints_before:bool, gap|null, resolution:pending|closed|open}], retries:[{answer, after_coaching:bool}], other_open_gaps:[text]}` (`[]` when no question was asked). `answered_count` must equal the main questions with `initial_answer`; the runtime derives `followup_count`, `followup_answered_count`, `retry_count`. Only the last follow-up (or the last main question) of a paused/stopped run may be unanswered; `gap` is mandatory text for `clarification` and `completion` (the open requirement or ambiguity); `deepening` has `gap: null` and never `open`. Rules: `followup.md`. `resume` additionally returns `open_followup` and `dialogue_evidence`.
- Runs in run format 3 (without dialogue) are unsupported: operations on that candidate are refused before writes; nothing is migrated or deleted.
- In **Nicht speichern** mode none of these commands may be run.
