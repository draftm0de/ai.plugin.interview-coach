# Setup and onboarding contract

Invoked by `/zyris-interview-coach setup` (Claude) or "zyris-interview-coach setup" in a ChatGPT conversation with skill instructions loaded.

## When to run

On explicit setup request or when the workspace cannot be resolved. Do not silently select a default private repository or create folders without permission. If a valid existing workspace is already configured, report its location and ask whether to keep it or switch.

## Storage choice: selection first, details second

For first-time setup, **offer a storage-type choice before requesting a path or repository URL**. Prefer the host's native single-choice UI (radio/select or equivalent) and a conditional editable field. Do not demand a path in the initial question. Present these choices in the user's interface language:

- **Lokales Verzeichnis** — suggest `~/ai/interview-workspace` only as an editable example, never as an observed folder. If the agent is hosted, immediately explain that a hosted filesystem is not automatically the user's computer; check for genuine local persistent access before offering automatic writes.
- **Privates Git-Repository** — GitHub or GitLab, request repository URL or identifier only after selection; verify authenticated read/write access.
- **Dateien selbst verwalten** — downloadable workspace files and manual re-upload on return, without implying automatic persistence.
- **Nicht speichern** — start an ephemeral interview without creating, updating, exporting or requesting workspace files. The coach can still give feedback and adapt questions **within the current conversation**, but does not retain training history, research or progress for future sessions. Each new chat starts from scratch unless the user independently supplies prior information.

If native controls are unavailable, state the four choices briefly in natural language and accept the option name as a reply; use numbered choices only if the host has no selection UI and numbering genuinely helps. **Do not require a path in the first reply**. After selection, propose/ask for the concrete location and close that decision with a clear confirmation. For **Nicht speichern**, no path or repository is requested; briefly confirm that the session is temporary and begin coaching. Do not ask for CV upload unless it is needed for the requested interview type; never persist an uploaded CV in this mode. If a workspace is already connected, first offer **Vorhandenen Workspace verwenden / Speicherort wechseln**, rather than repeating setup. Never assume the UI can render custom controls merely because the skill requests them.

## Interaction pattern: prefer real choices, not simulated buttons

When a proposed value or an existing workspace needs confirmation, **use the host's native choice/question tool if actually available**. Present clear labels such as "Bestehenden Workspace verwenden" and "Anderen Speicherort auswählen"; allow a different path or repository only when that option is selected. The skill itself cannot create native controls if the host has no such tool.

If no native choice tool is available, ask a short natural-language question and accept replies such as "weiterverwenden" or "anderen wählen" without requiring numeric input. Do not claim a native control was displayed. Avoid rigid scripted lists, mandatory "1/2" answers, or statements like "the setup guide requires this selection". Only ask one decision at a time.

For a known existing workspace, show its verified path and the fact that it contains existing data, then ask whether to reuse it. Never silently replace the pointer or delete existing data. Wait for permission before writing. For a new location, suggest an editable path but do not pretend it exists until checked. Apply the same interaction principles to CV choice and interview mode.

## Bundled local workspace tool and persistence boundaries

The distributed ZIP and Claude Code installation include `scripts/interview_workspace.py` **inside the skill package**, alongside `SKILL.md` and `references/`. The canonical runtime implementation is `scripts/interview_workspace.py` inside this skill directory; installers and packagers include it directly. Locate the script relative to the installed skill folder, not relative to the user's current working directory.

When the host provides an authorized **persistent local filesystem and Python runtime**, execute `python3 <skill-directory>/scripts/interview_workspace.py init --path <confirmed-path>` and verify with `status` and `validate`. The CLI writes a machine-local pointer; only claim future-session reuse when the same persistent filesystem is actually available.

**Claude Chat / hosted execution:** A tool-visible path such as `~/ai/interview-workspace` might be a temporary container path, **not the user's Mac**. Do not claim access to the Mac, a durable home-directory pointer or cross-chat persistence unless an explicit persistent integration verifies it. If the host has no durable writable storage, offer a private connected repository or downloadable workspace files. Even when Python runs, do not equate execution with persistent storage. State this limitation before accepting the storage choice.

When a workspace was created before the script was available, never recreate or overwrite its contents. After permission and confirmation, use `init --path <existing-path>` to register the pointer in an actually persistent local environment; otherwise explain why the pointer cannot be durable.

## Language during setup

At the first setup, infer a suggested interface language from the user's own messages, then confirm it in the user's language before storing it. Ask independently whether the interview itself should use the same language; default to the confirmed interface language unless the user chooses another. When a persistent local workspace is available, execute `python3 <skill-directory>/scripts/interview_workspace.py set-language --interface de --interview de` (replace `de` with confirmed BCP-47 codes). This writes private `preferences.json` and never modifies the public skill. For Git or hosted storage, write the same schema using the authorized storage adapter; do not pretend local CLI settings synchronize automatically. See `references/session-control.md`.

## Conversation flow

Ask **one question at a time** (do not dump a questionnaire):

1. **Storage:** Present the three storage-type choices from the section above, preferably as native options. Ask for the exact local path or Git repository **only after** the user selects that type; never request tokens/passwords.
2. **Access verification:** For local, check directory read/write authorization before creating files. For Git, check authenticated repository read and permitted write capabilities; do not make a test commit without approval. For ChatGPT files, verify attached/Project files are readable and clearly state whether writes are supported. If inaccessible, stop and offer a different storage mode.
3. **Initialize or reuse:** If existing `state.md` and `runs/` exist, **reuse**, never overwrite. For local, after permission use `python3 <skill-directory>/scripts/interview_workspace.py init --path PATH`; for Git use available authorized connector or Git CLI and `workspace.yaml` as reference. Never claim a local pointer is a universal ChatGPT setting.
4. **CV:** Ask "Bitte lade deinen aktuellen Lebenslauf (PDF/DOCX/Markdown) hoch oder gib mir den Pfad zu einer bereits zugänglichen Datei." Verify file is actually readable. Store original **only with user permission** in private workspace; otherwise store a provenance-aware reference and a derived, user-confirmed profile. If CV is missing, allow general practice but mark targeted preparation as blocked.
5. **Optional target job:** Ask for job ad text/link or existing application record. Company/interviewer research only when a concrete target exists; preserve source provenance.
6. **Confirm:** Show storage location and write capability, CV source/version, existing training state, missing inputs and next action. Ask whether to begin `general` or `targeted` training.

## First-run reference persistence

- Local: `~/.config/zyris/zyris-interview-coach/config.json` or `$XDG_CONFIG_HOME` via CLI. This is a local machine pointer, not synced across hosts.
- Git: use workspace's `workspace.yaml` plus a user-provided repo identifier. Do not store access tokens in YAML. An optional local pointer may be used when authorized, but is not available to arbitrary ChatGPT sessions.
- ChatGPT: the user must provide workspace attachment/Project access or an accessible connected repository. A ZIP package does not install itself into ChatGPT and cannot silently persist a personal pointer.

## Future LinkedIn support

Optional future **user-authorized** import from a profile export, user-provided file or an available permitted connector. Do not scrape behind login, bypass access restrictions or assume a LinkedIn connector exists. Imported claims are provisional until checked against the approved CV; the CV remains the canonical source unless the user explicitly approves an update.
