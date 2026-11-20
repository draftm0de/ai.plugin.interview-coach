# Setup and onboarding contract

Shared by all Interview Coach skills. Entry points: `interview-coach` (setup), or the first use of any skill when
the current project has no storage decision. Setup is **not** triggered automatically when a project is opened;
no host feature for that is relied upon. Setup happens on first use or on explicit `setup`.

## Decision order

1. **Storage type first, details second.** Offer exactly two options, then ask for the concrete target.
2. Never ask for a local path in the first question. The current project folder may be *suggested* as an
   editable example; it never becomes the storage target without the user's explicit confirmation.
3. One decision per turn. Use the host's native single-choice tool if it really exists; otherwise ask in natural
   language and accept the option name as the reply. Never claim a control was displayed that was not.

Ask each setup question only once: do not repeat it in both a progress message and the final reply,
or repeat a native choice prompt in prose.

## The two storage options (exactly two)

- **Lokal** — a durable local directory the user confirms or names. Verify read/write access first. A hosted sandbox or
  container path is not automatically the user's computer; say so and do not claim cross-chat persistence unless a
  persistent integration verifies it.
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
2. Otherwise ask for the storage type (two options above). For **Nicht speichern** confirm briefly and continue
   without any runtime call.
3. For **Lokal**, when the current project folder is known, propose its `interview-data` subfolder as an absolute
   path for confirmation instead of asking the user to type a path. Explain its purpose and the setup action:

   > Sollen die Interviewdaten im Unterordner `interview-data` deines aktuellen Projekts gespeichert werden?
   > Speicherort: `<absolute project path>/interview-data`
   > Bei Zustimmung richte ich diesen Speicherort ein und prüfe den Zugriff.
   > **Ja, hier speichern** · **Nein, anderen Ordner wählen**

   Localize the question and options to the interface language. A plain **Ja** confirms the displayed target
   and authorizes setup; do not request the path again or ask for a second identical confirmation. **Nein**
   means ask for a different absolute path on the next turn; do not create the suggested directory or pointer.
   If the user explicitly names and confirms a different target, use that target instead. Ask for a path directly
   only when no project path is known or the user chooses a different location. Never invent an absolute path.
   A proposal is not proof that a directory is empty, writable or supported: retain all runtime checks and
   preserve existing data. Never propose storage inside the installed plugin; ask for an external target instead.
4. Run `project-init` (see `runtime.md`). It checks local access and the workspace format. Report what was verified, what was reused and any warning. Do not report setup as done
   when it failed.
5. Confirm only the interface language, using the user's messages as a proposal, then `set-language --interface`.
   Do not ask for a project-wide interview language. That belongs to candidate creation and individual jobs.
6. Offer the next step: `candidate-create`, or select an existing candidate.

## Unsupported content

Directories containing older layouts or unrelated files are rejected with a concrete reason before anything is written.
No migration, no alias, no search for old pointers. Tell the user the old data is untouched and that a new, empty
target is needed (or manual reconciliation).

## Removed storage mode

Git storage is not available. Never offer repository setup, commits, pushes or connector-based storage.
Existing Git configurations are rejected unchanged; do not convert them to local storage or remove their pointers.
