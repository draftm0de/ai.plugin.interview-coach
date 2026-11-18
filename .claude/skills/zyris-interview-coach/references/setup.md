# Setup and onboarding contract

Invoked by `/zyris-interview-coach setup` (Claude) or "zyris-interview-coach setup" in a ChatGPT conversation with skill instructions loaded.

## When to run

On explicit setup request or when the workspace cannot be resolved. Do not silently select a default private repository or create folders without permission. If a valid existing workspace is already configured, report its location and ask whether to keep it or switch.

## Storage choice: selection first, details second

For first-time setup, **offer a storage-type choice before requesting a path or repository URL**. Prefer the host's native single-choice UI (radio/select or equivalent) and a conditional editable field. Do not demand a path in the initial question. Present these choices in the user's interface language:

- **Lokales Verzeichnis** — suggest `~/ai/interview-workspace` only as an editable example, never as an observed folder. If the agent is hosted, immediately explain that a hosted filesystem is not automatically the user's computer; check for genuine local persistent access before offering automatic writes.
- **Privates Git-Repository** — GitHub or GitLab, request repository URL or identifier only after selection; verify authenticated read/write access.
- **Dateien selbst verwalten** — downloadable workspace files and manual re-upload on return, without implying automatic persistence.

If native controls are unavailable, show the same three options as a short numbered selection, **without requiring a path in that first reply**. After selection, propose/ask for the concrete location and close that decision with a clear confirmation. If a workspace is already connected, first offer **Vorhandenen Workspace verwenden / Speicherort wechseln**, rather than repeating setup. Never assume the UI can render custom controls merely because the skill requests them.

## Interaction pattern: confirm a proposed value

When a storage option, folder, repository, CV source or training mode has a sensible proposed value, **close the decision in the same message**. Do not merely suggest a value and leave the user to guess how to respond.

- Ask **one decision per turn**, with a concise question, a concrete proposed value and two explicit choices: **"Ja, verwenden"** and **"Nein, anderen Wert angeben"**.
- When supported by the host, use a native selection control with an optional text input for the alternative. Never promise that a skill can force UI widgets to appear.
- In plain text chat, use a compact fallback such as:
  ```text
  Soll ich diesen Ordner für deine privaten Interviewdaten verwenden?
  ~/ai/interview-workspace

  1. Ja, diesen Ordner verwenden
  2. Nein, anderen Ordner angeben (bitte Pfad nennen)
  ```
- Only show an input field or request an alternative value **after** "Nein" is chosen, unless the host offers a compact conditional input.
- Do not claim to know the user's folder structure, permissions or file contents unless they were actually inspected with an authorized tool. A proposed folder is only a suggestion.
- **Wait for confirmation before creating folders, changing a storage pointer, writing files or requesting access**. Then verify access and continue to the CV step without re-asking the same question.
- If the user already gave an exact folder or repository, do not propose a different default. Confirm the supplied location only when authorization or ambiguity requires it.
- Apply the same decision pattern to an existing workspace ("Weiterverwenden / Anderen auswählen"), a known CV ("Vorhandenen verwenden / Neuen hochladen") and interview mode ("Allgemein / Stellenbezogen"), with wording suited to the choice.
- Keep explanations of access and persistence brief, and provide additional detail only if requested or necessary for informed consent.

## Bundled local workspace tool and persistence boundaries

The distributed ZIP and Claude Code installation include `scripts/interview_workspace.py` **inside the skill package**, alongside `SKILL.md` and `references/`. The source of truth in the development repository is `scripts/interview_workspace.py`; the installer and packager copy it during distribution. Locate the script relative to the installed skill folder, not relative to the user's current working directory.

When the host provides an authorized **persistent local filesystem and Python runtime**, execute `python3 <skill-directory>/scripts/interview_workspace.py init --path <confirmed-path>` and verify with `status` and `validate`. The CLI writes a machine-local pointer; only claim future-session reuse when the same persistent filesystem is actually available.

**Claude Chat / hosted execution:** A tool-visible path such as `~/ai/interview-workspace` might be a temporary container path, **not the user's Mac**. Do not claim access to the Mac, a durable home-directory pointer or cross-chat persistence unless an explicit persistent integration verifies it. If the host has no durable writable storage, offer a private connected repository or downloadable workspace files. Even when Python runs, do not equate execution with persistent storage. State this limitation before accepting the storage choice.

When a workspace was created before the script was available, never recreate or overwrite its contents. After permission and confirmation, use `init --path <existing-path>` to register the pointer in an actually persistent local environment; otherwise explain why the pointer cannot be durable.

## Language during setup

At the first setup, infer a suggested interface language from the user's own messages, then confirm it in the user's language before storing it. Ask independently whether the interview itself should use the same language; default to the confirmed interface language unless the user chooses another. When a persistent local workspace is available, execute `python3 <skill-directory>/scripts/interview_workspace.py set-language --interface de --interview de` (replace `de` with confirmed BCP-47 codes). This writes private `preferences.json` and never modifies the public skill. For Git or hosted storage, write the same schema using the authorized storage adapter; do not pretend local CLI settings synchronize automatically. See `references/session-control.md`.

## Conversation flow

Ask **one question at a time** (do not dump a questionnaire):

1. **Storage:** Present the three storage-type choices from the section above, preferably as native options. Ask for the exact local path or Git repository **only after** the user selects that type; never request tokens/passwords.
2. **Access verification:** For local, check directory read/write authorization before creating files. For Git, check authenticated repository read and permitted write capabilities; do not make a test commit without approval. For ChatGPT files, verify attached/Project files are readable and clearly state whether writes are supported. If inaccessible, stop and offer a different storage mode.
3. **Initialize or reuse:** If existing `state.md` and `runs/` exist, **reuse**, never overwrite. For local, after permission use `python scripts/interview_workspace.py init --path PATH`; for Git use available authorized connector or Git CLI and `workspace.yaml` as reference. Never claim a local pointer is a universal ChatGPT setting.
4. **CV:** Ask "Bitte lade deinen aktuellen Lebenslauf (PDF/DOCX/Markdown) hoch oder gib mir den Pfad zu einer bereits zugänglichen Datei." Verify file is actually readable. Store original **only with user permission** in private workspace; otherwise store a provenance-aware reference and a derived, user-confirmed profile. If CV is missing, allow general practice but mark targeted preparation as blocked.
5. **Optional target job:** Ask for job ad text/link or existing application record. Company/interviewer research only when a concrete target exists; preserve source provenance.
6. **Confirm:** Show storage location and write capability, CV source/version, existing training state, missing inputs and next action. Ask whether to begin `general` or `targeted` training.

## First-run reference persistence

- Local: `~/.config/zyris/zyris-interview-coach/config.json` or `$XDG_CONFIG_HOME` via CLI. This is a local machine pointer, not synced across hosts.
- Git: use workspace's `workspace.yaml` plus a user-provided repo identifier. Do not store access tokens in YAML. An optional local pointer may be used when authorized, but is not available to arbitrary ChatGPT sessions.
- ChatGPT: the user must provide workspace attachment/Project access or an accessible connected repository. A ZIP package does not install itself into ChatGPT and cannot silently persist a personal pointer.

## Future LinkedIn support

Optional future **user-authorized** import from a profile export, user-provided file or an available permitted connector. Do not scrape behind login, bypass access restrictions or assume a LinkedIn connector exists. Imported claims are provisional until checked against the approved CV; the CV remains the canonical source unless the user explicitly approves an update.
