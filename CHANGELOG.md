# Changelog

## [Unreleased] — Claude Code and Codex, several candidates, Git storage

### Added

- Realistic follow-up dialogue (`skills/_shared/references/followup.md`): one concrete follow-up per turn on the same main question (clarification, completion, deepening), no hints or rating before it, no blanket deduction, role-fit clarification, STOP first. Run format 4 stores main questions, follow-ups and retries with separate counters; `finish` requires `--dialogue-file`; run format 3 is refused without migration.

- Skills `candidate-create`, `candidate-training`, `job-create`, `job-training` next to the `interview-coach` entry point.
- Several candidates per project with stable IDs (equal names allowed), CV import (PDF, DOCX, Markdown) with byte-exact originals, Markdown and provenance, and profile building without a CV with confirmation status.
- Candidate-owned jobs with append-only posting, research, match and preparation snapshots; runs carry candidate and job assignment.
- Functional Git storage for private GitHub/GitLab repositories (private/write checks, publish without force, remote-saved only after verification).
- Per-project storage resolution; shared runtime and references under `skills/_shared/`.
- Tests for the new runtime, local-bare-repository Git flows, and 13 multi-step model scenarios; `docs/acceptance.md`.

### Fixed (review follow-up, same unreleased state)

- Storage switch/setup decision (target, storage type, repository) and invalid pointers are rejected before any mutation; setup is serialized per project.
- Git: the real fetch and push targets (origin, pushurl, several targets, URL rewriting) are bound to the authorized private repository before and during publication; privacy/write evidence is re-collected for exactly that repository; a connector attestation must name the repository, carries the user's confirmation and is never persisted as proof; remote verification reads the described target.
- Git: no blanket `git add -A` at publication. Saving commands require a clean tree and commit only their own changes; staged, edited or foreign files abort without touching them.
- Fresh clones of an empty workspace stay valid (`candidates/.gitkeep`).
- A profile draft is no reliable evidence: `job-add --kind match` is refused until the profile is confirmed; documentation and skills no longer contradict this.
- PDF extraction additionally uses macOS PDFKit via the system `swift` (nothing installed) when no other tool exists.
- Model scenarios: structural + rubric-judge checks instead of word lists; failed tool calls cannot count as success; pause/resume now verifies a further answer, the new run and the unchanged checkpoint.

### Fixed (second review follow-up)

- Git: the remote head is verified at the push target (not the fetch target); a URL rewrite is accepted only when both effective targets provably identify the authorized repository — `--allow-url-rewrite` removed.
- Git: saves stage only their own recorded paths (explicit pathspecs, no `git add -A`); interrupted-save journal v2 with SHA-256 (changed leftovers and unknown formats are never resumed); one Git-workspace lock for saves and publishes.
- Native Claude test: Erika's profile is confirmed before training, the training check requires a successful `job-show` and a job-related interview question (not a clarification). Corrected, not re-run.

### Fixed (third review follow-up)

- Git: staged control files (`.zyris/`, any staged change kind) are no longer hidden, abort save and publish with the paths, and unpublished commits containing control files are not pushed; `git-pull`/`git-status` take the shared Git-workspace lock.
- Native test logic: runtime success needs one provable call with its own exit code 0 and matching project/candidate/job; the question check no longer rejects general question words.

### Fixed (fourth review follow-up)

- Git: control files are recognized by complete `.zyris` path segments (nested too) in every unpublished commit incl. intermediate ones; failing history queries abort before the push.
- Native test logic: stand-alone question headings are not questions; conflicting tool results of one tool id are no success evidence.

### Changed (format)

- Workspace format 3: the internal control folder is `.journal` (was `.zyris`). Old `.zyris` layouts (workspace or candidate level, folder/file/symlink, mixed) are refused before any change and never migrated, read or touched; the Git protection treats `.journal` and `.zyris` as complete path segments. `.journal` is protected recovery data, not a cache.

### Changed

- Exactly three storage options: Lokal, Git, Nicht speichern. "Dateien selbst verwalten" is removed as mode and fallback.
- Workspace format 2 replaces format 1. Run metadata is schema 2 (adds `candidate_id`, `job_id`).
- The runtime moved from `skills/interview-coach/scripts/` to `skills/_shared/scripts/`; references moved to `skills/_shared/references/`.
- ChatGPT is no longer a documented host.

### Removed

- The single-candidate/global-pointer model and the format-1 tests. Format 1 workspaces are rejected explicitly; there is no migration or compatibility alias.

### Upgrade

- Existing format-1 workspaces stay untouched and are not read by this version. Choose an empty storage target for new data or reconcile manually; nothing is converted or deleted.

## [0.1.0] — publication pending

### Added

- Versioned plugin bundles, checksums and generated Claude/Codex catalogs.
- DE/EN installation guidance and reviewed Claude Desktop dialog screenshots.

### Changed

- Shared tooling is maintained by ZYRIS Skill Manager. Publication is an approval-gated plugin workflow rather than a release Action.
- Release notes derive from this changelog; plugin.json remains the product version source.

### Limitations

- No public release/catalog has been published. Local native CLI tests do not establish graphical or public-channel acceptance.

### Upgrade

- First public release is pending. Existing development catalog installations are separate. Verify the released plugin before removing an old development copy; preserve private training data outside plugin caches.
