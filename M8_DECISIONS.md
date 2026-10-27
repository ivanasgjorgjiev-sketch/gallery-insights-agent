# Milestone 8 decisions: Guided Insight Exploration

_Approved by the product owner on 2026-10-26. This note records the revised MVP scope. The source
documents (`PRD.md`, `agent_policy.md`, `daily_data.csv`, `data_dictionary.md`, `eval_cases.json`) are
unchanged; where they mention conversational follow-ups, this note takes precedence for the M8 MVP._

## What changed

Each validated insight card now offers four predefined, insight-specific questions, in the journey order
**Relevance → Trend → Confidence → Next investigation**:

1. What makes this insight worth my attention?
2. How did engagement evolve over the fair?
3. What other signals support—or challenge—this pattern?
4. What should I look into next?

Answers are **deterministic**. They are built only from the insight's validated pattern (recomputed by the
analytical tools) and are identical in LIVE and DEMO mode. Opening, closing or switching them makes **no
Anthropic API call** and never restarts the analysis. The daily analysis itself stays agentic: Claude chooses
the tools and proposes insights, and every insight still passes the publication gate.

Why: open-ended follow-ups were the main source of withheld answers during exploration, needed paid calls,
and could not be shown in the public DEMO. Guided questions keep the PRD's intent ("explore specific findings
before deciding what to do next") with verified, repeatable answers.

## Decisions

| # | Decision |
|---|---|
| D1 | Open-ended follow-ups are **removed from the MVP interface**. The implementation (`gia/followup.py`, diagnostics) and the Milestone 7 evaluations are preserved as historical coverage; the follow-up area can be shown again only with the server-side setting `GIA_ENABLE_FOLLOWUPS=1`, which is never set on the public deployment. |
| D2 | Opening guided questions **does not count as viewing evidence**. The review is complete only when the manager has viewed the evidence **and** recorded usefulness feedback for the same validated insight. |
| D3 | Answers stay **focused on the selected insight**. Artist-level context is allowed only when relevant and clearly labelled; another artwork's individual figures are never included. |
| D4 | For temporary spikes, answers use **verified daily values** to show why the increase was not sustained. No new retained-gain percentages are calculated. |
| D5 | Oct 18 (unprocessed) may be mentioned **only as excluded / not processed**, never as a suggested reanalysis action. |

## Content rules for the four answers

- **Q1 Relevance** explains why the observed pattern is noteworthy under the screening rules. No commercial
  prediction and no business priority; qualified signals are never presented as growth.
- **Q2 Trend** covers the primary metric (artwork views) on every processed day, with day-to-day changes.
- **Q3 Confidence** separates qualifying support from weak, flat or missing measures. "Against it" is used only
  for evidence that contradicts the pattern (a jump that did not hold); "What limits confidence" is used for a
  check that could not pass because evidence is too small, missing or not yet available (for example, missing
  corroboration is not contradicting evidence). When neither applies, the answer says so. Nothing is invented.
- **Q4 Next investigation** is one specific, human-controlled step using evidence already in View evidence.
  No collector outreach, pricing, causal search or autonomous action.
- Answers are concise (at most about 110 words), in plain language, and do not repeat the card's sentences.

## Safeguards

- Every answer is checked before display with the same checks as any shown text: each stated figure is
  recomputed with the tools and checked in context (metric, date, artwork), plus the prohibited-claim,
  commercial-action and (for Q4) cause-seeking checks. An excluded day may appear only where it is called
  excluded or not processed.
- The insight's pattern must still match what the tools compute now; stale or altered data is not explained.
- Any failure shows "This explanation is unavailable…" instead of the text (fail closed).

## Evaluation

A separate Milestone 8 suite covers every publishable pattern type (see `evals/M8_EVALUATION.md`). The
original 16 Milestone 7 cases and their historical results are unchanged; the cases that test open-ended
follow-ups are reported as historical for the M8 MVP.

## Not changed

Agent prompts, the six approved tools, screening thresholds, tool-call and cost limits, model settings,
the publication gate, View evidence, usefulness feedback and the review completion rule.

## Deferred (documented follow-ups)

- Rule-evidence facts (retained-gain percentages, supporting-measure counts) in the grounding checker.
- Display of withheld refusals (follow-ups only).
- Repeated `get_processed_data` calls in follow-up questions.
