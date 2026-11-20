# Candidate and job selection

Applies to every candidate- or job-related action.

1. Resolve the storage first (`project-show`). No storage decision and no **Nicht speichern** choice yet → run setup
   (`setup.md`). In **Nicht speichern** mode keep candidates and jobs apart inside the conversation (label each context
   with name and a chat-local number) and call no runtime command.
2. `candidate-list`. Exactly one active candidate and the user's request names nobody else → reuse it and say whom you use.
   Otherwise ask which candidate (show display name, profile status, creation date; same names are legal and are
   distinguished by ID and date). Never choose by guessing; never merge data between candidates.
3. A candidate with status `creating` or profile status `missing`/`draft` is announced as incomplete. Offer to complete it
   (`candidate-create` flow / `candidate-recover`) and, for a draft, to confirm the facts. A draft is not reliable evidence:
   personal comparison and profile-based training wait for the confirmation; posting intake, company research and general
   training from the candidate's own statements do not.
4. For job actions: `job-list --candidate ID`; one match → confirm it, several → ask. Pass the owning candidate with every
   job command. Never apply a job to another candidate.
5. Load only what is needed: `status` (state + hash), `profile.md`, the job's latest artifacts, the last relevant runs.
6. Learning state is per candidate. Update only the selected candidate's `state.md`. Job-specific gaps go to `match`.
