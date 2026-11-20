# Repository architecture / Repository-Struktur

- `SCOPE.md`: confirmed goals, non-goals and acceptance criteria; draft until agreed.
- `skills/<name>/SKILL.md`: public skill entry points for plugins.
- `skills/<name>/scripts/`: distributed runtime; no imports from a developer checkout.
- `skills/_shared/`: optional shared runtime/rules, no extra SKILL.md.
- `scripts/`: development, validation and distribution helpers only.
- `tests/unit/`, `tests/integration/`, `tests/contracts/`: deterministic tests.
- `tests/behavior/`, `tests/native/`: explicit model/isolated-host tests only.
- `tests/fixtures/`, `tests/support/`: fictional data and shared helpers.
- `docs/`: maintained documentation. Do not duplicate authoritative product facts.
- `.local/marketplace.json`: ignored machine-local associations, never committed.

Plugin repositories have plugin.json and derived host manifests, never marketplace
catalogs. Marketplace repositories have marketplace.json and derived host catalogs,
never new embedded plugins. GitHub repository creation is outside these tools.

Root scripts are not shipped runtime. Keep runtime dependencies inside the plugin
payload. Do not store user state in the installed plugin. Use only needed directories.
Before claiming completion, compare implementation against each confirmed requirement
and distinguish missing evidence from verified contradictions. Files existing and
structural checks passing do not prove domain behavior or host acceptance.

Die Struktur ist eine Entwicklungsregel, keine Garantie für LLM-Verhalten. Das
bestätigte Zielbild bleibt maßgeblich. Fehlende Belege und tatsächliche Widersprüche
getrennt berichten; fachliche Erfüllung braucht Source-Review und passende Tests.

Interview Coach (Claude Code and Codex): five public skills (`interview-coach` entry/setup, `candidate-create`,
`candidate-training`, `job-create`, `job-training`) share `skills/_shared/`:

- `scripts/interview_workspace.py` CLI and domain logic (projects, candidates, CV, profile, jobs, runs, recovery);
  `coach_core.py` safe paths/locks/atomic writes/identifiers; `coach_extract.py` Markdown/DOCX/PDF extraction. Local runtime only; no network client of its own.
- `references/` shared dialog and storage contracts. Coaching/research behavior is defined by SKILL.md and
  references, not by a Python dialogue engine.

Boundaries. Own storage coordination: layout, formats, locks, journals, verified local saves. External tools: extraction tools (`pdftotext`, `mutool`, `pypdf`).
No provider SDK, no credential handling, no installation of tools.

Resolution is per project: `project-init` stores a pointer for exactly one project folder under the machine-local
config directory; there is no global pointer and no discovery of old pointers. Private state lives in the chosen
storage target (workspace format 3, see `skills/_shared/references/storage.md`), never in the installed plugin.
Format 1 and any other layout are rejected before writes, never migrated. "Nicht speichern" calls no runtime command.

Storage is local only. Former Git pointers are refused without mutation or migration.

Evidence: `docs/acceptance.md` holds the requirement-to-source-to-test matrix with actual results and open gaps.

The internal control folder is `.journal` (single constant `CONTROL` in `coach_core.py`). The previous `.zyris` is recognized only to be refused; it is never migrated or read.
