# Setup and onboarding contract

Shared by all Interview Coach skills. Entry points: `interview-coach` (setup), or the first use of any skill when
the current project has no storage decision. Setup is **not** triggered automatically when a project is opened;
no host feature for that is relied upon. Setup happens on first use or on explicit `setup`.

## Decision order

1. **Storage type first, details second.** Offer exactly three options, then ask for the concrete target.
2. Never ask for a path or repository in the first question. The current project folder may be *suggested* as an
   editable example; it never becomes the storage target without the user's explicit confirmation.
3. One decision per turn. Use the host's native single-choice tool if it really exists; otherwise ask in natural
   language and accept the option name as the reply. Never claim a control was displayed that was not.

## The three storage options (exactly three)

- **Lokal** — a durable local directory the user names. Verify read/write access first. A hosted sandbox or
  container path is not automatically the user's computer; say so and do not claim cross-chat persistence unless a
  persistent integration verifies it.
- **Git** — a *private* GitHub or GitLab repository the user names explicitly. Details in `storage.md`.
- **Nicht speichern** — nothing is persisted: no workspace, files, pointers, locks, journals or exports; no CV copies,
  jobs, runs or learning state. Profile building, research and training stay in this conversation, and several
  candidate contexts and jobs may be kept apart *inside the chat*. Do not promise availability in a later chat.
  `stop` returns an in-chat summary only. Never call the runtime in this mode.

"Dateien selbst verwalten" is not a storage option and not a fallback. If a save fails, show the error and offer
recovery or a new storage choice; never export files or switch the mode unasked.

## Flow

1. If the project already has a storage decision (`project-show --project <folder>` succeeds): show the verified
   target and ask whether to keep it or switch (switching needs the explicit `--switch`). Existing data is never
   deleted or overwritten.
2. Otherwise ask for the storage type (three options above). For **Nicht speichern** confirm briefly and continue
   without any runtime call.
3. Ask for the concrete path (Lokal) or repository (Git). Then confirm the target and the actions that follow:
   for Git state plainly that saving means committing and pushing changes in that private repository.
4. Run `project-init` (see `runtime.md`). It checks access, the workspace format and (Git) privacy, write ability and
   remote reachability. Report what was verified, what was reused and any warning. Do not report setup as done
   when it failed.
5. Language: infer a proposal from the user's messages, confirm interface and interview language separately, then
   `set-language`. In Git mode publish afterwards.
6. Offer the next step: `candidate-create`, or select an existing candidate.

## Unsupported content

Directories containing older layouts or unrelated files are rejected with a concrete reason before anything is written.
No migration, no alias, no search for old pointers. Tell the user the old data is untouched and that a new, empty
target is needed (or manual reconciliation).

## Credentials

Never ask for tokens or passwords and never write them anywhere. Git access uses the user's existing git/`gh`/`glab`
authentication or an authorized host connector. If neither exists, say what is missing and stop.
