# Milestone 8 evaluation: Guided Insight Exploration

The revised MVP replaces open-ended follow-ups with four deterministic, insight-specific guided questions
(see `M8_DECISIONS.md`). This suite is **separate** from the 16 Milestone 7 cases: `eval_cases.json`,
`evals/cases.py`, `evals/run_evals.py` and every report under `evals/reports/` (other than `reports/m8/`)
are unchanged.

| Part | File |
|---|---|
| Case matrix, data sources and checks | `evals/m8_cases.py` |
| Automated suite (pytest) | `tests/test_m8_guided.py` |
| Development-only boundary data | `tests/data/m8_boundary.csv` |
| Human-review document generator | `evals/m8_guided_review.py` → `evals/reports/m8/HUMAN_REVIEW_guided.md` |

Run everything offline (no API calls):

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m evals.m8_guided_review
```

## 1. Case matrix: 7 card types × 4 questions = 28 cases

Every pattern type that can become an insight card is covered. Stable / no-clear-pattern artworks are
suppressed and never get a card (checked separately with B2).

| Row | Data | Pattern type · card label | Must show |
|---|---|---|---|
| A1 | real | sustained increase · higher-confidence | Q1 +100% well above the minimums, held, two measures; Q2 40, 80, 76, 90; Q3 unique viewers and favourites qualify, inquiries flat, nothing against; Q4 check the supporting measures on later days |
| A2 | real | sustained increase · moderate-confidence | Q1 +40% only just clears the minimums, one measure; Q3 favourites too small, inquiries flat; Q4 look at the thin measures |
| B1 | real | temporary spike · qualified | Q1 awareness, not growth; Q2 back near the start by Oct 17; Q3 no support, did not hold (verified daily values, no retained-gain %) |
| C1 | real | increase from zero · qualified | No percentages in Q1/Q2; Q3 unique viewers qualify from zero |
| C2 | real | weak signal · qualified | Q1 +5 below the minimum of 10; Q3 Oct 15 unique viewers not recorded (unknown, not zero) |
| F1 | fixture | recent increase · qualified | Jump on Oct 17 (last processed day); Oct 18 only as excluded; no reanalysis step |
| F2 | fixture | not enough evidence · qualified | Rise held but support unknown because a value is not recorded |

**Checks on every answer** (all must pass): shown after the runtime grounding and safety checks; processed
dates only, excluded day only as excluded; missing values as "not recorded"; no percentage from zero;
daily unique viewers never summed; isolation (only the selected artwork); deterministic; at most 110 words;
no sentence repeated from the card. **Per question:** Q1 qualified signals never presented as growth and no
priority language; Q2 every processed day of the primary metric and no other metrics; Q3 qualifying vs weak
groups match the pattern, "Against it" appears only for contradicting evidence (a failed retention check) and
"What limits confidence" only for checks that could not pass (too small, no later days, corroboration), with an
explicit statement when neither applies; Q4 points to View evidence and contains no reanalysis or
waiting-for-data step.

**Also tested:** answers for an insight do not depend on other insights; altered patterns (daily value, key
comparison, supporting value, category, strength, missing comparison) are never explained; unsafe text
(unverified figure, purchase intent, contact, cause-seeking, excluded day as data) is rejected; DEMO replay
answers equal LIVE answers.

## 2. App-level checks

- Every published card shows the four questions in journey order; no free-text box by default.
- No Anthropic client is created and no network connection is attempted while cards and answers are shown
  and re-rendered, in LIVE and in DEMO; no analysis is started and no follow-up is counted.
- Guided answers do not change evidence-viewed or feedback state. Evidence on one insight plus feedback on
  another stays incomplete; evidence plus feedback on the same insight completes the review; the "not
  authorisation" note is shown.
- A failed answer shows the "unavailable" message, never the text.
- Follow-ups appear only with `GIA_ENABLE_FOLLOWUPS=1` (their preserved tests switch it on).

## 3. Milestone 7 cases for the M8 MVP (files and results unchanged)

| Status | Case IDs (exact) |
|---|---|
| **Applicable**: agentic analysis, validation, evidence, safety and journey | TC01, TC02, TC04, TC06, TC09, TC010, TC011, TC15 |
| **Partly applicable**: initial-analysis part applies; follow-up part superseded | TC05 |
| **Historical / superseded**: test open-ended follow-ups, which the MVP no longer shows | TC03, TC07, TC08, TC12, TC13, TC14, TC16 |

The intent of the superseded cases is re-covered by the M8 checks: no causal or commercial claims (TC08,
TC13, TC16), daily unique viewers never summed (TC12), G001/E001 only and no free-text input in which
out-of-scope or ambiguous requests could be typed (TC07, TC14), artist context only when labelled (TC03).
They still run (`--mock`, `--regrade`) as historical coverage and are not scored for the M8 gate.

## 4. Release gate for the revised MVP

All must pass; any failure blocks:

1. Full automated suite passes (only the opt-in paid live test skipped).
2. All 28 matrix cases and the app-level checks pass.
3. Applicable Milestone 7 cases pass on `run_evals --mock`; the saved Stage B re-grade stays 16/16 (historical).
4. Human review: every one of the 28 answers in `HUMAN_REVIEW_guided.md` is approved. **Met 2026-10-26**
   (two rounds); the wording is locked by `tests/data/m8_guided_approved.json` and
   `test_guided_wording_matches_the_approved_reference`.
5. Free local DEMO preview shows the four questions on each card, no free-text box, no API calls.
6. Phase 3 (separate approval, paid): one LIVE analysis smoke test in which every published card's four
   answers pass the runtime checks; then the recording, the public DEMO replay check and deployment
   (`GIA_FORCE_DEMO = "1"`, no API key on Streamlit Cloud).
