# CV import and profile building

## With a CV

1. Ask for an upload or a reachable file path (PDF, DOCX or Markdown). Check that it is readable.
2. `cv-import`. The original is stored byte-exact (SHA-256 recorded); Markdown is a faithful content transfer, not a
   layout copy. The result lists `extraction_status` and `warnings`.
3. Missing capability (for example no PDF tool): report exactly what is missing; nothing is installed. If you can read the
   document yourself, offer a model transcription via `--transcription-file`; it is stored as **partial/unverified**.
   Never invent an extraction.
4. `partial` means gaps (images, unreadable pages, headers/footers, no text layer). Show every warning, ask the user to
   check the Markdown against the CV, and do **not** call the import finished. A repeated import of identical bytes is
   reported as already imported; a different file is kept next to the earlier one.
5. Build the structured profile from `extracted.md`. Keep three kinds of statements distinguishable in `profile.md`:
   `[Quelle: CV]`, `[Quelle: Nutzerangabe]`, `[Quelle: Modellvorschlag]`. Never add experience that is not in a source.
6. `profile-save --status draft`. Use `--status confirmed --user-confirmed` only after the user confirmed the factual
   content in this conversation; with a partial CV also `--acknowledge-gaps` after the user accepted the gaps.

## Without a CV

Ask exactly one question per turn and wait for the answer: work experience → education → skills → projects → career goals.
Do not fill gaps. Then:

1. Write a clearly labeled **CV draft** in Markdown (`# CV-Entwurf — nicht bestätigt`), only from the user's statements,
   and save it with `cv-draft-save`.
2. Write the profile (`origin interview`) and save it as `draft`.
3. Read the facts back and ask the user to confirm or correct. Only after confirmation save as `confirmed`
   (`--user-confirmed --acknowledge-gaps`). A draft is never silently upgraded to `confirmed`.

## What an unconfirmed profile may be used for

A `draft` profile may be saved and shown. It is **not reliable candidate evidence**: labeling it "unbestätigt" does not replace the
confirmation. Before any personal comparison (`job-add --kind match`) or training that uses profile statements as facts,
ask the user to confirm them (read the facts back, then `profile-save --status confirmed --user-confirmed`). The runtime
refuses `match` snapshots for unconfirmed profiles. Independent work stays possible without confirmation: securing a posting,
general company research, and general training that relies only on what the candidate states in the conversation.

## Result report

Show: candidate name and ID, what was imported or drafted, extraction status and warnings, profile status, open
points, and the actual storage location. In Git mode say whether the change is **remote gespeichert**.
In **Nicht speichern** mode nothing is stored; say so and keep the profile in the conversation only.
