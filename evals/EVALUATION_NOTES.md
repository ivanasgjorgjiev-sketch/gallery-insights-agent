# Evaluation notes (Milestone 7)

## Reports (preserved)

| Report | Location | What it is |
|---|---|---|
| Stage B baseline | `evals/reports/stage_b_baseline/` | The one approved live run (1 analysis + 8 follow-ups, `claude-sonnet-5-5`, ≈ $0.25). Unchanged. 5 Pass · 5 Pending human review · 6 Fail. |
| Post-fix re-check | `evals/reports/stage_b_postfix/` | The **same saved answers** re-checked after the approved fixes, with no API calls. 6 Pass · 10 Pending human review · 0 Fail. `comparison.md` shows before/after per case. |
| Human review | `evals/reports/HUMAN_REVIEW_stage_b.md` | Full verbatim responses, limitations, figures, evidence, safety interventions, checks and suggested assessments for the 10 judgment cases. **All human verdicts: Pending.** |

Raw run data (`raw_run.pkl`) stays local in `evals/results/` (git-ignored) so the runs can be re-scored
with `--reuse` or `--regrade` without API calls.

## Remaining risks

1. **Heuristic grounding.** Numbers are checked against verified facts using the nearest artwork/artist,
   metric and date in the same sentence, the kind of figure (value, change, percentage, total) and exact
   sum components. This is transparent and deterministic but not natural-language understanding:
   - unusual phrasing can be withheld (fails safe), as happened five times in Stage B before the fixes;
   - statements without numbers (tone, emphasis, completeness) rely on keyword checks and human review.
2. **Repeat-run consistency is unmeasured.** Each case ran once. A single run shows the agent *can*
   behave correctly, not how often it does.
3. **Future model wording may vary.** The fixes were verified on the exact Stage B wording plus
   adversarial variants. A new run may phrase answers differently and trigger new false positives
   (withheld answers) or reveal gaps not yet covered by the patterns.
4. **Minor observations from Stage B:** TC08 describes A1's increase in words without quoting the verified
   figures; TC03 called `get_processed_data` three times (redundant but harmless, small extra cost).

## Milestone 8 plan: targeted smoke test during the demo recording

The LIVE demo-recording session will double as a targeted smoke test of the follow-up types that failed
in Stage B, using the five approved demo questions:

| Demo question | Covers the Stage B failure type |
|---|---|
| TC03 — Artist A's total artwork views | Written sums / breakdowns (component verification) |
| TC05 — C2's missing unique viewers | Date attribution ("X on DATE"), missing values |
| TC07 — Ambiguous "best" artwork | Negated statements ("don't … overall score") |
| TC08 — Campaign causality | Causal / sales boundaries |
| TC13 — Collector contact and discount | Refusals that mention prohibited topics |

Plan: run the session locally in LIVE mode (1 analysis + these 5 questions), confirm each answer is
displayed and grounded, then re-score the session for free with the harness before saving it as the
DEMO recording. Any withheld answer or failure is reported, not hidden; the recording is only saved
with the reviewer's approval. No full paid re-evaluation is planned.
