# Milestone 9 decisions: UX refinement

_Approved by the product owner on 2026-10-26 (proposal decisions D1–D9 plus four refinements).
Presentation-layer changes only: the agentic analysis, deterministic tools, thresholds, validation rules,
source data, the 28 locked guided answers, the demo recording and the evaluation history are unchanged._

## Goal

Make the app more intuitive, visual and less text-heavy for a Gallery Operations Manager: a compact first
view of each insight, a visual trend, and detail only when the manager asks for it.

## Decisions

| # | Decision |
|---|---|
| D1 | The card's one-line explanation is the agent's own validated "why it may matter" sentence (short, evidence-grounded, non-causal; already checked by the publication gate). |
| D2 | Limitations sit in a collapsed "Limitations (n)" on the card. |
| D3 | The suggested next step ("For your consideration") and the note when it was replaced with the standard wording move into the evidence summary. |
| D4 | A line chart of daily artwork views on the processed days only, **below the metric tiles and spanning the card** (y-axis from 0, the key change as a larger dot, start/key/last values labelled, tooltip on every point, text alternative). |
| D5 | **Revised after review:** the M8 four-tile row is restored (Artwork views, Daily unique viewers, Favourites, Inquiries) with each tile's verified start → comparison values, its change (a percentage only where defined; "+n (from 0)" for zero baselines; "no change" / "no comparison" otherwise) and the existing classification label: Key change, ✓ Supports, – Rose, too little to count, – No rise, ? Not recorded. Tiles stack on narrow screens. |
| D6 | Explore insight and View evidence are independent toggles, side by side and equally prominent. |
| D7 | Agent-process details (trace, not surfaced, withheld, usage) are grouped in one collapsed "How the agent worked" section with a one-line summary. |
| D8 | Before the analysis: one data-status line plus a "Data details" expander; the synthetic-data notice stays. |
| D9 | Three existing app tests were adjusted to open "Explore insight" first (their assertions are unchanged). The two `test_presentation.py` adjustments were not needed. |

## Refinements

1. **Completion rule unchanged:** viewing the evidence and giving feedback on **any one** validated insight
   completes the review. The progress message says so; per-card "✓ Reviewed" chips show progress.
2. **Evidence is as easy to find as exploration:** both buttons sit side by side with the same style and icons.
3. **Supporting-measure labels:** "Supports", "Rose, too little to count", "No rise" and "Not recorded". The help
   text states that a measure that did not add support is not evidence against the pattern.
4. **Concise explanation:** one validated sentence; the underlying claims and the locked guided answers are
   unchanged.

## What is visible by default vs on demand

| Default | On demand |
|---|---|
| Title, strength and pattern badges, review chip | The four guided questions (Explore insight), all collapsed |
| Primary metric key change and labelled supporting measures | Evidence summary (View evidence) |
| Daily-views chart (processed days only) | Calculations, screening checks, source records, insight ID |
| One-line explanation, feedback buttons | Limitations; data details; how the agent worked |

## Final polish pass (approved 2026-10-26)

- Trend chart height reduced to 115 px; all four points, the start/key/last labels and tooltips stay readable.
- Repeated per-card captions removed: the comparison dates moved into each metric tile's help text, the chart
  caption was shortened, and the generic "view the evidence before rating" tip is no longer shown under every
  card. The targeted prompt "To complete the review of this insight, also open its evidence" (after feedback
  without evidence) remains.
- The evidence-before-feedback guidance and the useful-insight rate (session only) now sit once in the review
  progress message; the completion rule (evidence and feedback on any one insight) is unchanged.
- The analysis overview is one line; the ordering explanation and the evidence-strength note are behind its
  help icon.
- Compact header: title, gallery and edition share one row; the separate "Data status" and "Daily engagement
  analysis" headings and the divider were removed. The synthetic-data notice and "Nothing is sent or changed"
  statement stay.
- Not done (by decision): the custom-CSS 2×2 mobile tile layout. Tiles keep Streamlit's responsive stacking.
