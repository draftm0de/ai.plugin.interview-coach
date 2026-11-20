# Follow-up dialogue (Nachfragen)

Owner: all training skills. A realistic interviewer first checks whether an essential requirement of the question just asked is open,
ambiguous or contradictory. This file defines when to ask, how to rate, what to persist. Terms: **main question** (Hauptfrage),
**follow-up** (Nachfrage), **retry** (Wiederholungsversuch = the candidate speaks a whole answer again). The three are counted separately.

## Flow after an answer

1. Check only what the question actually asked for (explicitly requested or essential aspects). A "wenn möglich" example is optional: a
   concrete answer to a hypothetical scenario is complete without a real example, and a missing optional example is never a deduction and never becomes a mandatory follow-up later in the block.
2. Essential requirement open, ambiguous or contradictory → ask **exactly one concrete follow-up in this turn** — one question about one open aspect, in one sentence, no chain of sub-questions: exactly one question mark, and no second question joined by "und" / "and" / a comma (wrong: "Wie wirkt sich der Termin aus, und bis wann entscheiden Sie?"; right: "Wie wirkt sich der Termin auf Ihr Vorgehen aus?"; also wrong: two sentences with two questions, or one question with an "oder"/"und"-alternative, or a second question after "Und wie …", e.g. "Wie gehen Sie vor, damit die Entscheidung rechtzeitig fällt? Und wie sorgen Sie dafür, dass das unterlegene Team sie mitträgt?" or "Wie gehen Sie konkret mit dem Termin um? Was tun Sie, wenn die Teams weiter uneinig sind oder der Aufwand den Termin gefährdet?" — pick the one most important open aspect, ask only that, and leave the rest unasked) — and stay on the current main question.
   Before it only a neutral one-sentence acknowledgement without evaluative words (no "gut", no restating strengths). Before it: no model answer, no solution hint, no detailed rating, no improvement list, no hint at what is missing beyond the question itself.
   Wait for the candidate's own reply. Never move to the next main question merely because an answer has arrived.
3. A follow-up is not a retry: do not ask the candidate to repeat the whole answer; ask only for the missing piece.
4. Close the block (no endless loop, no fixed quota) when evidence suffices, no further useful clarification is expected, or the candidate does not know more.
   Then, in coached modes: rate first answer and additions visibly apart (section below), then offer coaching or go to the next main question.
5. Complete, good answer (every essential requirement covered) → **no** `completion` or `clarification` follow-up. Before closing the block one meaningful `deepening` follow-up stays allowed — it asks for one more dimension, causes no deduction, anticipates no rating and reveals no solution or hint; it is never required and there is no quota. If no deepening is useful, close the block at once and rate it (coached modes). After a deepening answer the block closes unless an essential requirement became open.
6. `mock`: natural follow-ups are allowed; rating, hints and model answers come only at the very end. `briefing`: no answer rating.
7. **STOP always wins**: no further question, no second confirmation. An open follow-up stays unanswered; it is neither an answer nor a failed answer.
8. Resuming a `paused` checkpoint: re-ask only the open follow-up, one question mark. Recall the main question's context as a statement ("Es ging um den Architekturkonflikt vor dem Release"), not as a repeated question.

## Kinds

- `clarification`: resolve ambiguity or misunderstanding; neutral wording first (e.g. "Meinen Sie damit A oder B?").
- `completion`: an essential requirement that was actually asked is missing. Only for aspects the question explicitly asked or that are essential to it. An aspect the question did not ask for (e.g. decision criteria, tools, escalation paths, a second scenario) is never a `completion` and never becomes a mandatory gap.
- `deepening`: one more dimension; never treated as a flaw of the original answer; no gap is recorded for it. This is the only kind for an aspect that was not asked: word it as optional (e.g. "Wenn Sie mögen: …"), store it with `kind: deepening` and `gap: null`, never list its topic in `other_open_gaps`, never call it "fehlt"/"offen" in the rating, and if the candidate declines or has nothing to add, close the block without any deduction. A question the coach added on top of the follow-up (a second question) is not asked and therefore can never be rated as unanswered.

Role fit: clarify ambiguous motivation statements **before** deriving weaknesses. Example: "Ich möchte wieder echte Realisierung." →
"Meinen Sie damit eigene technische Umsetzung oder die Verantwortung für ein Produkt vom Kundenproblem bis zur Wirkung?" A confirmed
preference for hands-on implementation can argue against a Product role; this is a **job-specific fit point** (`match`/`preparation`),
not a general communication weakness and not part of the cross-job `state.md`. In `job-training` it is **saved as a new `match` snapshot** (`job-add --kind match`, which carries over the earlier match content, names the stated preference in the candidate's words, the posting requirement it argues against, the date and that it was stated in the training; interpretation marked as such) at the latest when the session ends (`stop`, `finish`, `pause`), before the closing answer; the run's dialogue alone is not enough. Without a job (`candidate-training`) there is no job-specific artifact: the statement stays in the run's dialogue and the chat. If the save fails (e.g. unconfirmed profile), say concretely that the fit point was **not** saved. Separate posting facts from interpretation: a leadership
focus does not automatically mean "no technical work at all".

## Rating without a blanket penalty

Grades and the reasons given for them follow the same separation: never justify a score, a criterion or an improvement item with missing enthusiasm for, interest in, reasons for or "what appeals in" the role the candidate declined (not in the overall justification, not in "Substanz der Begründung", not as "wirkt wie eine Absage"). Rate the clarity, honesty and specificity of what the candidate actually said. A heading such as "Passung (ohne Punktzahl)" does not make up for a score whose reason is the preference. A confirmed role preference gets **no numeric score and no criterion row** (no "Bezug zur Rolle: 2/10", no lowered overall score because of it): state it as a job-specific fit point without a number, and rate the quality of the answer itself (clarity, honesty, substance of the stated motivation) on its own. An ambiguous first statement that a `clarification` resolves is not a deduction. A confirmed preference that argues against the role is a fit point for the job, not a low answer score and not a competence rating; rate the quality of the answer itself separately.

The number of follow-ups never lowers a score by itself. Assess instead: what was answered spontaneously; what was concretized independently
only after a follow-up; what stayed open; where solution hints or coaching were needed. Example: "Termindruck in der Erstantwort nicht
behandelt; nach einer gezielten Nachfrage selbstständig konkretisiert."

Evidence classes (derived, see `runtime.md` → `dialogue_evidence`):

- first answer = spontaneous evidence; a complete first answer is the only "spontaneously complete" one.
- answer to a neutral follow-up (`hints_before: false`) = the candidate's own evidence, **not** a spontaneously complete first answer.
- answer after content hints or coaching (`hints_before: true`, or a retry with `after_coaching: true`) = **supported**.
- unanswered follow-up = no evidence. Model answers are never candidate evidence.

improving/stable rules (`evaluation.md`) are unchanged: follow-ups and retries within one main question do not count as additional
independent scenarios.

## Persistence (run format 4)

Per main question the run records (`finish --dialogue-file`, validated; see `runtime.md`): stable key `q-N`; the main question and the original
answer verbatim; each follow-up (`q-N-fM`) with verbatim `text`, `kind`, concrete `reason` (trigger), `gap`, the candidate's `answer`
(null while open), `hints_before` and `resolution` (`pending|closed|open`); retries (`answer`, `after_coaching`); `other_open_gaps`; and
separate `initial_assessment` (first answer) and `block_assessment` (whole block). `answered_count` counts main questions only; the runtime
derives `followup_count`, `followup_answered_count`, `retry_count` and rejects mismatching counts before writing. Continuations keep all
answered content and never repeat answered follow-ups. Allowed changes in a continuation (everything else is rejected before writing): a pending follow-up gets its answer and resolution; `hints_before` of a pending follow-up may only change false→true (a documented hint is never removed); new follow-ups, retries, main questions may be appended (earlier closed blocks stay unchanged); `block_assessment` may be replaced only when the block received new evidence (a newly answered follow-up or a retry), `initial_assessment` only filled when it was null; an `other_open_gaps` entry may disappear only when the block received new evidence; an open gap documented on an answered follow-up (`resolution: open`) stays. An open follow-up (`resume` → `open_followup`) is re-asked once.

## Nicht speichern

Same dialogue logic in the chat only: no runtime call, no file, no dialogue record.
