# Milestone 8 · Human review of guided explanations

_Generated 2026-10-26 by `evals/m8_guided_review.py` (deterministic; no API calls)._

Each validated insight card offers four questions in the journey order Relevance → Trend → Confidence → Next investigation. Answers are built only from the insight's verified pattern and the deterministic tools; they are identical in LIVE and DEMO mode.

**How to review:** for each answer, judge the four criteria and record Pass or Fail. Any Fail blocks the release gate. Real-data answers (A1–C2) come first; fixture answers (F1, F2) use a small development-only dataset for card types the real data never produces.

**Status: approved.** The product owner approved all 28 answers on 2026-10-26 after two review rounds. The wording is locked by `tests/data/m8_guided_approved.json`; any change fails the test suite until it is reviewed again.

## Revised in round 2

7 answers were revised at the product owner's request (marked ✏️ **REVISED**, with the previous wording available under each). 2 more had only the confidence-section label changed (🏷️). All other answers are unchanged from round 1.

| Answer | Revision |
|---|---|
| A1 What makes this insight worth my attention? | More manager-oriented; less screening-rule terminology. |
| A2 What makes this insight worth my attention? | Neutral wording: a sustained increase with limited supporting evidence. |
| A2 What should I look into next? | A clearer, evidence-focused next step instead of "treat it as a candidate". |
| B1 What should I look into next? | Checks whether the supporting measures stayed above their starting level after the spike. |
| C1 What makes this insight worth my attention? | No claim beyond the processed period about the first recorded views. |
| C2 What makes this insight worth my attention? | Less repetition of the card; explains why a large percentage can be a small change. |
| F2 What other signals support—or challenge—this pattern? | Explains that the corroboration check could not pass and that this is missing support, not contradicting evidence. |
| C2 What other signals support—or challenge—this pattern? | 🏷️ Label only: "What limits confidence" |
| F1 What other signals support—or challenge—this pattern? | 🏷️ Label only: "What limits confidence" |

## Automated results

**28 of 28 answers pass every automated check.**

| Case | relevance | trend | signals | next |
|---|---|---|---|---|
| A1 (real) | ✅ | ✅ | ✅ | ✅ |
| A2 (real) | ✅ | ✅ | ✅ | ✅ |
| B1 (real) | ✅ | ✅ | ✅ | ✅ |
| C1 (real) | ✅ | ✅ | ✅ | ✅ |
| C2 (real) | ✅ | ✅ | ✅ | ✅ |
| F1 (fixture) | ✅ | ✅ | ✅ | ✅ |
| F2 (fixture) | ✅ | ✅ | ✅ | ✅ |

## Part 1 · Real data (20 answers)

### A1 · Artwork A1 (A001) · sustained increase, two supporting measures

- **Card:** higher-confidence · Sustained increase · insight `INS-A001-SUSTAINED_GROWTH-20261014_20261015`
- **Views by processed day:** Oct 14 40, Oct 15 80, Oct 16 76, Oct 17 90
- **Key comparison:** Oct 14 → Oct 15: 40 → 80 (+40, +100.0%)
- **Other measures, same days:**
  - Daily unique viewers: 30 → 45 (+15, +50.0%) · counts as support
  - Favourites: 5 → 12 (+7, +140.0%) · counts as support
  - Inquiries: 0 → 0 (no change) · does not count
- **Screening checks not met:** none
- **What the card already says:** The increase held on later days (76, 90) and daily unique viewers and favourites rose with it.

#### 1. A1 · What makes this insight worth my attention? · ✏️ **REVISED**

_Revision: More manager-oriented; less screening-rule terminology._

> Views doubled in a single day, from 40 on Oct 14 to 80 on Oct 15, and stayed at around that higher level for the rest of the processed days. Two other measures, daily unique viewers and favourites, rose on the same day, so the increase does not rest on views alone. That combination of size, persistence and support is what gives this insight its higher-confidence rating.

<details><summary>Previous wording (round 1)</summary>

> Views rose 100% in one day, from 40 on Oct 14 to 80 on Oct 15, well above the screening minimums of 30% and 10 views. What makes it stand out is that it was not a one-off: the higher level held for the rest of the processed days, and two other measures rose on the same day. That is the strongest combination the screening rules look for.

</details>

<details><summary>Automated checks: 12/12 passed · 4 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ qualified signals are never presented as growth
- ✅ sustained insights are not labelled awareness-only
- ✅ no business priority or ranking language

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

#### 2. A1 · How did engagement evolve over the fair?

> Views by day: Oct 14: 40, Oct 15: 80, Oct 16: 76, Oct 17: 90. Day to day: +40 on Oct 15; −4 on Oct 16; +14 on Oct 17. The level reached on Oct 15 held on every later day, and the highest day was Oct 17.

<details><summary>Automated checks: 11/11 passed · 10 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ covers every processed day of the primary metric
- ✅ primary metric only (other measures not listed by default)

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

#### 3. A1 · What other signals support—or challenge—this pattern?

> - **Supports it** (Oct 14 → Oct 15): daily unique viewers rose from 30 to 45 (+15, +50%) and favourites rose from 5 to 12 (+7, +140%). Both are enough to count.
> - **Weak or missing** (Oct 14 → Oct 15): inquiries did not rise (0 on both days).
> - **Against it:** none of the screening checks found evidence against this pattern.

<details><summary>Automated checks: 14/14 passed · 14 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ qualifying measures listed as support
- ✅ weak, flat or missing measures listed as weak
- ✅ 'Against it' only for contradicting evidence (none invented)
- ✅ 'What limits confidence' only for checks that could not pass
- ✅ says so when nothing argues against the pattern

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

#### 4. A1 · What should I look into next?

> Open View evidence and read the daily table for the days after Oct 15. Check whether daily unique viewers and favourites also stayed above their Oct 14 levels, not just views. That shows whether the supporting measures held up as well as the main one did.

<details><summary>Automated checks: 11/11 passed · 0 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ points to evidence already available (View evidence)
- ✅ no reanalysis or waiting-for-data action

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

### A2 · Artwork A2 (A002) · sustained increase, one supporting measure

- **Card:** moderate-confidence · Sustained increase · insight `INS-A002-SUSTAINED_GROWTH-20261014_20261015`
- **Views by processed day:** Oct 14 25, Oct 15 35, Oct 16 32, Oct 17 38
- **Key comparison:** Oct 14 → Oct 15: 25 → 35 (+10, +40.0%)
- **Other measures, same days:**
  - Daily unique viewers: 20 → 26 (+6, +30.0%) · counts as support
  - Favourites: 3 → 4 (+1, +33.3%) · does not count
  - Inquiries: 0 → 0 (no change) · does not count
- **Screening checks not met:** none
- **What the card already says:** The increase held on later days (32, 38) and daily unique viewers rose with it.

#### 5. A2 · What makes this insight worth my attention? · ✏️ **REVISED**

_Revision: Neutral wording: a sustained increase with limited supporting evidence._

> Views rose 40% in one day, from 25 on Oct 14 to 35 on Oct 15, and stayed above their Oct 14 level on every later processed day. Only one other measure, daily unique viewers, rose enough to back it up. So this is a sustained increase with limited supporting evidence, which is why it is rated moderate-confidence.

<details><summary>Previous wording (round 1)</summary>

> Views rose 40% in one day, from 25 on Oct 14 to 35 on Oct 15, which only just clears the screening minimums of 30% and 10 views. It held on the later processed days, so it is more than a one-day jump. Only one other measure rose with it, so it rests on less corroboration than a higher-confidence insight.

</details>

<details><summary>Automated checks: 12/12 passed · 4 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ qualified signals are never presented as growth
- ✅ sustained insights are not labelled awareness-only
- ✅ no business priority or ranking language

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

#### 6. A2 · How did engagement evolve over the fair?

> Views by day: Oct 14: 25, Oct 15: 35, Oct 16: 32, Oct 17: 38. Day to day: +10 on Oct 15; −3 on Oct 16; +6 on Oct 17. The level reached on Oct 15 held on every later day, and the highest day was Oct 17.

<details><summary>Automated checks: 11/11 passed · 10 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ covers every processed day of the primary metric
- ✅ primary metric only (other measures not listed by default)

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

#### 7. A2 · What other signals support—or challenge—this pattern?

> - **Supports it** (Oct 14 → Oct 15): daily unique viewers rose from 20 to 26 (+6, +30%). That is enough to count.
> - **Weak or missing** (Oct 14 → Oct 15): favourites rose only from 3 to 4 (+1), short of the minimum rise of 3; inquiries did not rise (0 on both days).
> - **Against it:** none of the screening checks found evidence against this pattern.

<details><summary>Automated checks: 14/14 passed · 14 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ qualifying measures listed as support
- ✅ weak, flat or missing measures listed as weak
- ✅ 'Against it' only for contradicting evidence (none invented)
- ✅ 'What limits confidence' only for checks that could not pass
- ✅ says so when nothing argues against the pattern

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

#### 8. A2 · What should I look into next? · ✏️ **REVISED**

_Revision: A clearer, evidence-focused next step instead of "treat it as a candidate"._

> Open View evidence and look at favourites and inquiries on Oct 16 and Oct 17. They did not rise enough on Oct 15 to count as support, so check whether either of them rose on the later days. That shows whether the support for this increase stayed limited to one measure throughout the fair.

<details><summary>Previous wording (round 1)</summary>

> Open View evidence and look at favourites and inquiries day by day. They are the measures that did not rise enough to count, so they are where this pattern is thinnest. Then decide whether one supporting measure is enough for you to treat it as a candidate.

</details>

<details><summary>Automated checks: 11/11 passed · 0 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ points to evidence already available (View evidence)
- ✅ no reanalysis or waiting-for-data action

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

### B1 · Artwork B1 (B001) · one-day jump that did not hold

- **Card:** qualified · Temporary spike · insight `INS-B001-TEMPORARY_SPIKE-20261014_20261015`
- **Views by processed day:** Oct 14 30, Oct 15 45, Oct 16 32, Oct 17 31
- **Key comparison:** Oct 14 → Oct 15: 30 → 45 (+15, +50.0%)
- **Other measures, same days:**
  - Daily unique viewers: 23 → 24 (+1, +4.3%) · does not count
  - Favourites: 3 → 4 (+1, +33.3%) · does not count
  - Inquiries: 0 → 0 (no change) · does not count
- **Screening checks not met:** min_gain_retained (Later values [32, 31] keep ['13%', '7%'] of the +15 increase (need ≥ 50% on every later day))
- **What the card already says:** It fell back close to the starting level on later days (32, 31), so it was a one-day jump, not a trend.

#### 9. B1 · What makes this insight worth my attention?

> Views rose 50% in one day, from 30 on Oct 14 to 45 on Oct 15. On its own, a jump of +15 is large enough to pass the screening minimums, so it is worth knowing about. It did not last, so it is shown for awareness, not as growth.

<details><summary>Automated checks: 12/12 passed · 4 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ qualified signals are never presented as growth
- ✅ sustained insights are not labelled awareness-only
- ✅ no business priority or ranking language

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

#### 10. B1 · How did engagement evolve over the fair?

> Views by day: Oct 14: 30, Oct 15: 45, Oct 16: 32, Oct 17: 31. Day to day: +15 on Oct 15; −13 on Oct 16; −1 on Oct 17. The jump on Oct 15 did not last: by Oct 17 views were back near the starting level of 30 on Oct 14.

<details><summary>Automated checks: 11/11 passed · 10 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ covers every processed day of the primary metric
- ✅ primary metric only (other measures not listed by default)

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

#### 11. B1 · What other signals support—or challenge—this pattern?

> - **Supports it** (Oct 14 → Oct 15): no other measure rose enough to count.
> - **Weak or missing** (Oct 14 → Oct 15): daily unique viewers rose only from 23 to 24 (+1), short of the minimum rise of 5; favourites rose only from 3 to 4 (+1), short of the minimum rise of 3; inquiries did not rise (0 on both days).
> - **Against it:** views fell to 32 on Oct 16 and 31 on Oct 17, close to the starting level of 30 on Oct 14 rather than staying near the peak of 45 on Oct 15, so the jump did not hold.

<details><summary>Automated checks: 14/14 passed · 18 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ qualifying measures listed as support
- ✅ weak, flat or missing measures listed as weak
- ✅ 'Against it' only for contradicting evidence (none invented)
- ✅ 'What limits confidence' only for checks that could not pass
- ✅ says so when nothing argues against the pattern

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

#### 12. B1 · What should I look into next? · ✏️ **REVISED**

_Revision: Checks whether the supporting measures stayed above their starting level after the spike._

> Open View evidence and look at daily unique viewers and favourites on Oct 16 and Oct 17. Check whether either of them stayed above their Oct 14 level after views fell back. That shows whether anything besides the one-day jump in views lasted; it does not change how the pattern is classified.

<details><summary>Previous wording (round 1)</summary>

> Open View evidence and compare Oct 15 with the later days across all four measures. If the other measures also fell back, treat this as a one-day jump; if any of them stayed higher, it may be worth keeping an eye on.

</details>

<details><summary>Automated checks: 11/11 passed · 0 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ points to evidence already available (View evidence)
- ✅ no reanalysis or waiting-for-data action

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

### C1 · Artwork C1 (C001) · increase from zero (no percentages)

- **Card:** qualified · Increase from zero · insight `INS-C001-ZERO_BASELINE_CHANGE-20261014_20261015`
- **Views by processed day:** Oct 14 0, Oct 15 10, Oct 16 9, Oct 17 11
- **Key comparison:** Oct 14 → Oct 15: 0 → 10 (+10; no percentage, because it started at 0)
- **Other measures, same days:**
  - Daily unique viewers: 0 → 8 (+8; no percentage, because it started at 0) · counts as support
  - Favourites: 0 → 1 (+1; no percentage, because it started at 0) · does not count
  - Inquiries: 0 → 0 (no change) · does not count
- **Screening checks not met:** none
- **What the card already says:** It started from zero, so only the change in numbers is meaningful, not a percentage.

#### 13. C1 · What makes this insight worth my attention? · ✏️ **REVISED**

_Revision: No claim beyond the processed period about the first recorded views._

> Views went from 0 on Oct 14, the first processed day, to 10 on Oct 15. Because it started at zero, a percentage would be meaningless, so the change is judged by its absolute size alone. Within the processed days this is a move from zero views to a small number, which is why it is shown for awareness rather than as growth.

<details><summary>Previous wording (round 1)</summary>

> Views went from 0 on Oct 14 to 10 on Oct 15. A percentage cannot be calculated from zero, so the rules judge it by the absolute change alone. It is worth noticing as the first views recorded for this artwork at the fair, but the numbers are small, which is why it is shown for awareness rather than as growth.

</details>

<details><summary>Automated checks: 12/12 passed · 3 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ qualified signals are never presented as growth
- ✅ sustained insights are not labelled awareness-only
- ✅ no business priority or ranking language

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

#### 14. C1 · How did engagement evolve over the fair?

> Views by day: Oct 14: 0, Oct 15: 10, Oct 16: 9, Oct 17: 11. Day to day: +10 on Oct 15; −1 on Oct 16; +2 on Oct 17. Because it started at zero, only the size of each change is shown, not percentages.

<details><summary>Automated checks: 11/11 passed · 9 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ covers every processed day of the primary metric
- ✅ primary metric only (other measures not listed by default)

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

#### 15. C1 · What other signals support—or challenge—this pattern?

> - **Supports it** (Oct 14 → Oct 15): daily unique viewers rose from 0 to 8 (+8). That is enough to count.
> - **Weak or missing** (Oct 14 → Oct 15): favourites rose only from 0 to 1 (+1), short of the minimum rise of 3; inquiries did not rise (0 on both days).
> - **Against it:** none of the screening checks found evidence against this pattern.

<details><summary>Automated checks: 14/14 passed · 11 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ qualifying measures listed as support
- ✅ weak, flat or missing measures listed as weak
- ✅ 'Against it' only for contradicting evidence (none invented)
- ✅ 'What limits confidence' only for checks that could not pass
- ✅ says so when nothing argues against the pattern

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

#### 16. C1 · What should I look into next?

> Open View evidence and read the absolute numbers day by day. Decide whether changes of this size are large enough to matter for your review before giving this insight weight.

<details><summary>Automated checks: 11/11 passed · 0 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ points to evidence already available (View evidence)
- ✅ no reanalysis or waiting-for-data action

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

### C2 · Artwork C2 (C002) · change too small; a supporting value missing

- **Card:** qualified · Weak signal · insight `INS-C002-WEAK_SIGNAL-20261014_20261015`
- **Views by processed day:** Oct 14 15, Oct 15 20, Oct 16 19, Oct 17 18
- **Key comparison:** Oct 14 → Oct 15: 15 → 20 (+5, +33.3%)
- **Other measures, same days:**
  - Daily unique viewers: 12 → not recorded (cannot compare: a value is not recorded) · unknown (not recorded)
  - Favourites: 1 → 2 (+1, +100.0%) · does not count
  - Inquiries: 0 → 0 (no change) · does not count
- **Screening checks not met:** min_absolute_change (Increase +5 vs minimum 10 for artwork_views); stable_tolerance (Values [15, 20, 19, 18], average 18.00; every day within 10% of average: False)
- **What the card already says:** Artwork views went from 15 on Oct 14 to 20 on Oct 15 (+5, +33.3%). That is only +5, below the 10 needed to count as meaningful. Favourites (1 → 2) rose, but too little to count. Inquiries (0 → 0) did not rise. Daily unique viewers on Oct 15 is not recorded, so it cannot count either way.

#### 17. C2 · What makes this insight worth my attention? · ✏️ **REVISED**

_Revision: Less repetition of the card; explains why a large percentage can be a small change._

> A 33.3% rise sounds large, but a percentage depends on the starting point: with only 15 views on Oct 14, a handful more on Oct 15 is already a big share. That is why the rules also require a rise of at least 10 views, so small numbers do not look like big trends. This change is shown for awareness, not as a pattern.

<details><summary>Previous wording (round 1)</summary>

> Views went from 15 on Oct 14 to 20 on Oct 15 (+33.3%). In percentage terms that looks large, but it is only +5, below the minimum of 10 views the rules need to treat a change as meaningful. It is shown for awareness, not as a pattern.

</details>

<details><summary>Automated checks: 12/12 passed · 4 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ qualified signals are never presented as growth
- ✅ sustained insights are not labelled awareness-only
- ✅ no business priority or ranking language

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

#### 18. C2 · How did engagement evolve over the fair?

> Views by day: Oct 14: 15, Oct 15: 20, Oct 16: 19, Oct 17: 18. Day to day: +5 on Oct 15; −1 on Oct 16; −1 on Oct 17. The highest day was Oct 15, and the level moved by only a few views across the fair.

<details><summary>Automated checks: 11/11 passed · 10 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ covers every processed day of the primary metric
- ✅ primary metric only (other measures not listed by default)

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

#### 19. C2 · What other signals support—or challenge—this pattern? · 🏷️ label only

_"Against it" relabelled "What limits confidence": the point is a limitation, not contradicting evidence. Content unchanged._

> - **Supports it** (Oct 14 → Oct 15): no other measure rose enough to count.
> - **Weak or missing** (Oct 14 → Oct 15): favourites rose only from 1 to 2 (+1), short of the minimum rise of 3; inquiries did not rise (0 on both days); daily unique viewers are not recorded for Oct 15, so that value is unknown (not zero) and cannot count either way.
> - **What limits confidence:** the rise in views (+5) is below the minimum of 10.

<details><summary>Previous wording (round 1)</summary>

> - **Supports it** (Oct 14 → Oct 15): no other measure rose enough to count.
> - **Weak or missing** (Oct 14 → Oct 15): favourites rose only from 1 to 2 (+1), short of the minimum rise of 3; inquiries did not rise (0 on both days); daily unique viewers are not recorded for Oct 15, so that value is unknown (not zero) and cannot count either way.
> - **Against it:** the rise in views (+5) is below the minimum of 10.

</details>

<details><summary>Automated checks: 14/14 passed · 11 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ qualifying measures listed as support
- ✅ weak, flat or missing measures listed as weak
- ✅ 'Against it' only for contradicting evidence (none invented)
- ✅ 'What limits confidence' only for checks that could not pass
- ✅ says so when nothing argues against the pattern

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

#### 20. C2 · What should I look into next?

> Open View evidence and read the other measures for Oct 15. Because daily unique viewers are not recorded that day, judge the pattern on the measures that are, and treat the missing value as unknown rather than zero.

<details><summary>Automated checks: 11/11 passed · 0 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ points to evidence already available (View evidence)
- ✅ no reanalysis or waiting-for-data action

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

## Part 2 · Boundary fixtures (8 answers)

### F1 · Artwork F1 (F001) · jump on the last processed day (date boundary)

- **Card:** qualified · Recent increase (not yet confirmed) · insight `INS-F001-EMERGING_INCREASE-20261016_20261017`
- **Views by processed day:** Oct 14 20, Oct 15 21, Oct 16 20, Oct 17 40
- **Key comparison:** Oct 16 → Oct 17: 20 → 40 (+20, +100.0%)
- **Other measures, same days:**
  - Daily unique viewers: 15 → 25 (+10, +66.7%) · counts as support
  - Favourites: 2 → 3 (+1, +50.0%) · does not count
  - Inquiries: 0 → 0 (no change) · does not count
- **Screening checks not met:** min_later_days (0 processed day(s) after the jump vs minimum 2)
- **What the card already says:** Artwork views went from 20 on Oct 16 to 40 on Oct 17 (+20, +100.0%). It happened on the latest processed day, so it cannot be confirmed yet. Daily unique viewers (15 → 25) also rose enough to count as support. Favourites (2 → 3) rose, but too little to count. Inquiries (0 → 0) did not rise.

#### 21. F1 · What makes this insight worth my attention?

> Views rose 100% in one day, from 20 on Oct 16 to 40 on Oct 17, enough to pass the screening minimums. It happened on the latest processed day, so there is no later day yet to show whether it holds. That is why it is shown as an early, unconfirmed signal rather than as growth.

<details><summary>Automated checks: 12/12 passed · 4 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ qualified signals are never presented as growth
- ✅ sustained insights are not labelled awareness-only
- ✅ no business priority or ranking language

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

#### 22. F1 · How did engagement evolve over the fair?

> Views by day: Oct 14: 20, Oct 15: 21, Oct 16: 20, Oct 17: 40. Day to day: +1 on Oct 15; −1 on Oct 16; +20 on Oct 17. The rise came on Oct 17, the latest processed day, so there is no later day to compare yet.

<details><summary>Automated checks: 11/11 passed · 10 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ covers every processed day of the primary metric
- ✅ primary metric only (other measures not listed by default)

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

#### 23. F1 · What other signals support—or challenge—this pattern? · 🏷️ label only

_"Against it" relabelled "What limits confidence": the point is a limitation, not contradicting evidence. Content unchanged._

> - **Supports it** (Oct 16 → Oct 17): daily unique viewers rose from 15 to 25 (+10, +66.7%). That is enough to count.
> - **Weak or missing** (Oct 16 → Oct 17): favourites rose only from 2 to 3 (+1), short of the minimum rise of 3; inquiries did not rise (0 on both days).
> - **What limits confidence:** there are no processed days after Oct 17, so the rules cannot yet test whether the rise holds.

<details><summary>Previous wording (round 1)</summary>

> - **Supports it** (Oct 16 → Oct 17): daily unique viewers rose from 15 to 25 (+10, +66.7%). That is enough to count.
> - **Weak or missing** (Oct 16 → Oct 17): favourites rose only from 2 to 3 (+1), short of the minimum rise of 3; inquiries did not rise (0 on both days).
> - **Against it:** there are no processed days after Oct 17, so the rules cannot yet test whether the rise holds.

</details>

<details><summary>Automated checks: 14/14 passed · 14 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ qualifying measures listed as support
- ✅ weak, flat or missing measures listed as weak
- ✅ 'Against it' only for contradicting evidence (none invented)
- ✅ 'What limits confidence' only for checks that could not pass
- ✅ says so when nothing argues against the pattern

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

#### 24. F1 · What should I look into next?

> Open View evidence and look at all four measures on Oct 17, the latest processed day. Treat this as unconfirmed for now: Oct 18 is not processed yet and is excluded.

<details><summary>Automated checks: 11/11 passed · 0 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ points to evidence already available (View evidence)
- ✅ no reanalysis or waiting-for-data action

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

### F2 · Artwork F2 (F002) · rise held, but support cannot be verified

- **Card:** qualified · Not enough evidence · insight `INS-F002-INSUFFICIENT_EVIDENCE-20261014_20261015`
- **Views by processed day:** Oct 14 30, Oct 15 45, Oct 16 44, Oct 17 46
- **Key comparison:** Oct 14 → Oct 15: 30 → 45 (+15, +50.0%)
- **Other measures, same days:**
  - Daily unique viewers: 20 → not recorded (cannot compare: a value is not recorded) · unknown (not recorded)
  - Favourites: 3 → 4 (+1, +33.3%) · does not count
  - Inquiries: 0 → 0 (no change) · does not count
- **Screening checks not met:** corroboration (Qualifying supporting metrics: none; unknown: ['unique_artwork_viewers'])
- **What the card already says:** Artwork views went from 30 on Oct 14 to 45 on Oct 15 (+15, +50.0%). Other measures needed to confirm it are not recorded. Favourites (3 → 4) rose, but too little to count. Inquiries (0 → 0) did not rise. Daily unique viewers on Oct 15 is not recorded, so it cannot count either way.

#### 25. F2 · What makes this insight worth my attention?

> Views rose 50% in one day, from 30 on Oct 14 to 45 on Oct 15, and the higher level held on the later processed days. That would normally make it a candidate, but daily unique viewers are not recorded for Oct 15, so the rules cannot check whether other measures back it up. It is shown for awareness only.

<details><summary>Automated checks: 12/12 passed · 5 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ qualified signals are never presented as growth
- ✅ sustained insights are not labelled awareness-only
- ✅ no business priority or ranking language

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

#### 26. F2 · How did engagement evolve over the fair?

> Views by day: Oct 14: 30, Oct 15: 45, Oct 16: 44, Oct 17: 46. Day to day: +15 on Oct 15; −1 on Oct 16; +2 on Oct 17. The level reached on Oct 15 held on every later day, and the highest day was Oct 17.

<details><summary>Automated checks: 11/11 passed · 10 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ covers every processed day of the primary metric
- ✅ primary metric only (other measures not listed by default)

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

#### 27. F2 · What other signals support—or challenge—this pattern? · ✏️ **REVISED**

_Revision: Explains that the corroboration check could not pass and that this is missing support, not contradicting evidence._

> - **Supports it** (Oct 14 → Oct 15): no other measure rose enough to count.
> - **Weak or missing** (Oct 14 → Oct 15): favourites rose only from 3 to 4 (+1), short of the minimum rise of 3; inquiries did not rise (0 on both days); daily unique viewers are not recorded for Oct 15, so that value is unknown (not zero) and cannot count either way.
> - **What limits confidence:** the corroboration check could not pass: it needs at least one other measure to rise enough on the same day, and none did or could be checked. This is missing or insufficient support, not evidence against the pattern.

<details><summary>Previous wording (round 1)</summary>

> - **Supports it** (Oct 14 → Oct 15): no other measure rose enough to count.
> - **Weak or missing** (Oct 14 → Oct 15): favourites rose only from 3 to 4 (+1), short of the minimum rise of 3; inquiries did not rise (0 on both days); daily unique viewers are not recorded for Oct 15, so that value is unknown (not zero) and cannot count either way.
> - **Against it:** none of the screening checks found evidence against this pattern.

</details>

<details><summary>Automated checks: 14/14 passed · 11 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ qualifying measures listed as support
- ✅ weak, flat or missing measures listed as weak
- ✅ 'Against it' only for contradicting evidence (none invented)
- ✅ 'What limits confidence' only for checks that could not pass
- ✅ says so when nothing argues against the pattern

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked

#### 28. F2 · What should I look into next?

> Open View evidence and read the other measures for Oct 15. Because daily unique viewers are not recorded that day, judge the pattern on the measures that are, and treat the missing value as unknown rather than zero.

<details><summary>Automated checks: 11/11 passed · 0 stated facts recomputed with the tools</summary>

- ✅ shown (grounding and safety checks pass)
- ✅ dates: processed days only; excluded day only as excluded
- ✅ missing values shown as not recorded (never zero)
- ✅ no percentage from a zero baseline
- ✅ daily unique viewers never summed
- ✅ isolation: only this insight's artwork
- ✅ deterministic (identical on repeat)
- ✅ concise (≤ 110 words)
- ✅ does not repeat the card's sentences
- ✅ points to evidence already available (View evidence)
- ✅ no reanalysis or waiting-for-data action

</details>

| Criterion | Verdict (Pass / Fail) | Notes |
|---|---|---|
| Correct (matches the evidence) | | |
| Useful for a Gallery Operations Manager | | |
| Clear and concise; adds to the card | | |
| Safe (no prediction, priority, cause or action) | | |

**Overall verdict:** **Pass**: approved by the product owner on 2026-10-26; wording locked
