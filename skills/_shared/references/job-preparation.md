# Job preparation

Owner: `job-create`; reused by `job-training`. Research rules: `research.md`.

1. Select the candidate (`candidate-selection.md`).
2. Ask for the job link or an upload. Secure the posting text and its origin (`job-create`: link needs its retrieval date;
   uploads keep the original bytes). Link not accessible → ask for the pasted text or a file. Never invent a posting.
3. Company missing or ambiguous → ask. `job-create` accepts a missing company as an open point; fill it with `job-update`.
4. Ask who conducts the interview (names and functions). "Unbekannt" is a valid answer: `job-update --participants-status
   unknown`; it never blocks preparation or training. Several people with the same name stay separate (`p-1`, `p-2`) and
   unverified until the user or a source disambiguates them (`--verify-person`).
5. Research public, professional information about the company and the named people: position and evidenced fields of
   expertise. Clarify same-name ambiguity **before** attributing anything. No psychological profiles, private information
   or unevidenced skills.
6. Save with `job-add --kind research` (sources + retrieval date required). Separate in the text: **Fakten** (with
   source), **Schlussfolgerungen**, **Unbekannt**.
7. Compare each material requirement with candidate evidence. This needs a **confirmed** profile (`profile_reliable` in
   `status`): with a draft, first read the facts back and ask for confirmation; the runtime refuses `match` snapshots
   otherwise. Steps 1–6 do not depend on it. Use exactly these classes (a requirement is its full wording: skill, duration,
   scope, level):
   - **direct** (direkt belegt): the confirmed profile evidences the requirement itself, including any duration or scope it names.
   - **transferable** (übertragbar): adjacent evidence only. Years in a role plus a skill listed in the profile do **not** prove
     the same number of years with that skill, or its share of the work: classify as transferable or unsupported and name what is
     missing ("Python als Skill belegt, Dauer/Anteil nicht belegt → zu klären").
   - **unsupported** (unbelegt / zu klären): the profile does not mention it. Not mentioned is not "absent": say "im Profil nicht
     belegt", never "fehlende Erfahrung", "kein X" or "Defizit".
   - **gap** (bestätigte Lücke): only when the candidate has confirmed in the conversation or profile that the experience is
     missing. Keep **capability gap** (confirmed) and **evidence gap** (not documented) visibly apart in match, preparation and
     the final report; never merge them under one "Lücke" or "größte Lücke".
   Preparation may prioritize an unsupported topic (e.g. because the posting stresses it) but must state the reason as
   "Klärungsbedarf: Nachweis fehlt", not as a proven weakness. Facts in profile, match, preparation and the final answer must not
   contradict each other (same class for the same requirement everywhere); never reinterpret the confirmed scope and never add
   candidate facts that profile or the candidate did not state. Save as `job-add --kind match`, then topics, likely questions
   and open questions as `job-add --kind preparation`.
8. Updates add a new snapshot; earlier snapshots and the original posting stay.
9. Report: candidate, job ID, what was saved, open points, storage location, remote status in Git mode. Open points have two
   separate sources: **record gaps** (`job-show` → `open_points`: missing company, participants not yet asked, unverified people —
   required fields only) and **research gaps** (what the latest `research`/`preparation` snapshot lists as unknown, not yet
   researched or skipped, e.g. no web research, unknown interviewers). An empty `open_points` list means the job record is
   complete, not that research is done; never describe such a job as "ohne offene Punkte" or fully researched while research gaps exist.
