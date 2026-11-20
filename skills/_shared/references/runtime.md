# Runtime reference

`RUNTIME` = `skills/_shared/scripts/interview_workspace.py` inside the installed plugin. From a skill folder it is
`../_shared/scripts/interview_workspace.py`. Use it with `python3`. Do not assume a developer checkout.
`PROJECT` = absolute path of the current project folder. Every command except `validate --path` needs
`--project PROJECT`; the pointer is stored per project outside the plugin and workspace, so projects never switch each other.
Output is JSON; failures print `ERROR: ...` (exit 1) or, for ambiguous selections, JSON choices (exit 2).
Never claim success unless the command exited with 0.

| Task | Command |
| --- | --- |
| Storage setup | `project-init --project P --storage local --path DIR` / `--storage git --path CLONE_DIR --remote URL [ATTEST] [--switch]` |
| Show / validate | `project-show`, `validate` |
| Languages | `set-language --interface de --interview de` |
| Candidates | `candidate-create --name N`, `candidate-list`, `candidate-resolve [--id ID \| --name N]`, `candidate-status --candidate ID`, `candidate-recover --candidate ID` |
| CV | `cv-import --candidate ID --file F [--transcription-file T]`, `cv-draft-save --candidate ID --file F` |
| Profile | `profile-save --candidate ID --file F --status draft\|confirmed --origin cv\|interview [--cv-source cv-001] [--user-confirmed] [--acknowledge-gaps]` |
| Jobs | `job-create --candidate ID --title T [--company C] (--posting-file F \| --posting-text-file F) [--source-url U --retrieved-at YYYY-MM-DD]`, `job-list`, `job-show --job J`, `job-add --job J --kind research\|match\|preparation\|posting --file F [--source U]... [--retrieved-at D]`, `job-update --job J [--company] [--title] [--participants-status pending\|provided\|unknown] [--person "Name::Role"]... [--verify-person p-1]...` |
| Runs | `status --candidate ID`, `resume --candidate ID --run-id R`, `finish --candidate ID --run-id R --run-file F --state-file S --expected-state-sha256 H --status completed\|paused\|stopped_early --answered-count N [--planned-count M] [--resume-from R0] [--job-id J]`, `recover --candidate ID` |
| Git | `git-status`, `git-pull`, `git-publish [--message M] [ATTEST]` |

## Rules

- Run every runtime command as ONE direct call: `python3 /absolute/path/interview_workspace.py SUBCOMMAND --project /absolute/project ...`. No shell variables, `cd`, pipes, `&&`/`;` chains or wrappers: hosts may refuse compound calls, and a refused call is not a result. Read reference files with the Read tool.

- Candidate and job identifiers come from the runtime; display names are data and never paths.
- Resolve candidates with `candidate-resolve`; exit 2 means ambiguous or unknown: ask the user, never guess.
- A job belongs to exactly one candidate. Pass the `--candidate` that owns it; foreign IDs are rejected.
- Read `status` (or `resume`) before preparing a new `state.md`; pass its `state_sha256` unchanged. A stale hash is a
  hard error: re-read and reconcile, do not refresh the hash blindly.
- Failed saves: follow the error text (recover, retry same run ID, or inspect). Do not create a second run ID as a workaround.
- Extraction tools are never installed. If the runtime reports a missing capability, tell the user exactly what is missing.
- `ATTEST` = `--attest-private --attest-write --attest-source NAME --attest-repository OWNER/REPO --attest-user-confirmed`. Use it only when
  `gh`/`glab` cannot answer and only after the user saw the connector's answer for exactly that repository. It is never stored as
  proof: supply it again for every `project-init`/`git-publish`. A made-up value is not evidence — never set it without the connector call.
- Git storage: every saving command first requires a clean Git working tree (no staged, edited or foreign files; otherwise it aborts and
  touches nothing) and commits its own changes locally afterwards. `git-publish` never stages; it checks the real fetch/push target, pushes
  without force and verifies the remote head. Local commit ≠ remote saved.
- `job-add --kind match` is refused unless the candidate's profile is `confirmed` (`profile_reliable` in `status`).
- In **Nicht speichern** mode none of these commands may be run.
