# Milestone 10 · Human review of manager-experience wording

_Generated 2026-10-28 by `evals/m10_manager_review.py` (deterministic; no API calls)._

Everything below is built from the validated insights and the deterministic tools, and passes the same checks as the guided answers (pattern recomputed from the source, figures, prohibited claims, commercial actions, cause-seeking). Text that fails a check is not shown in the app.

## 1. Suggested follow-ups (rule-based)

A rule is chosen only from the validated evidence: pattern category, evidence strength, which supporting measures qualified, were weak or are missing, and which screening criteria failed. Artwork IDs, titles and artists never select a rule. Outcomes: **suggestion**; **no specific suggestion** (valid evidence that supports nothing specific, shown as a neutral explanation); **unavailable** (a check failed, nothing shown).

| Rule | Applies when (validated evidence) | Outcome |
|---|---|---|
| `monitor_continuation` | sustained increase · well supported · two or more measures support it | suggestion |
| `cautious_monitoring` | sustained increase · partly supported · exactly one measure supports it (each other measure described as it is: small rise, no rise or not recorded) | suggestion |
| `recurrence_watch` | temporary spike · for awareness only | suggestion |
| `await_later_day` | recent increase · for awareness only · no later processed day yet (min_later_days failed) | suggestion |
| `context_only` | rose from zero · for awareness only | suggestion |
| `insufficient_evidence` | small or unsupported change, or not enough data · for awareness only (the failed criterion or missing measure is named) | no specific |
| `no_rule` | any other combination | neutral: “The available evidence does not support a specific follow-up suggestion.” |
| (inconsistent) | a sustained increase whose support does not match its rating | unavailable |

### A1 · Harbour at First Light · Sustained increase · Well supported

Rule `monitor_continuation` · suggestion · ✅ passes all checks · 36 words

> **Suggested follow-up** · No action taken automatically  
> Consider keeping this artwork in view during the remaining fair days. Views increased and stayed elevated, with supporting increases in daily unique viewers and favourites. Review the next processed day to see whether that pattern continues.

For comparison, the guided answer *What should I look into next?* (unchanged): Open View evidence and read the daily table for the days after Oct 15. Check whether daily unique viewers and favourites also stayed above their Oct 14 levels, not just views. That shows whether the supporting measures held up as well as the main one did.

Verdict: ☐ Pass ☐ Revise — notes:

### A2 · Salt Study, Grey · Sustained increase · Partly supported

Rule `cautious_monitoring` · suggestion · ✅ passes all checks · 36 words

> **Suggested follow-up** · No action taken automatically  
> Keep this artwork on your watch list as a possible sustained increase. Daily unique viewers support the pattern, while favourites provide limited additional support and inquiries did not increase. Reassess when more daily data is available.

For comparison, the guided answer *What should I look into next?* (unchanged): Open View evidence and look at favourites and inquiries on Oct 16 and Oct 17. They did not rise enough on Oct 15 to count as support, so check whether either of them rose on the later days. That shows whether the support for this increase stayed limited to one measure throughout the fair.

Verdict: ☐ Pass ☐ Revise — notes:

### B1 · Red Interval · One-day spike · For awareness only

Rule `recurrence_watch` · suggestion · ✅ passes all checks · 21 words

> **Suggested follow-up** · No action taken automatically  
> No immediate follow-up is suggested based on this temporary spike. Revisit the pattern if a new increase appears in subsequent data.

For comparison, the guided answer *What should I look into next?* (unchanged): Open View evidence and look at daily unique viewers and favourites on Oct 16 and Oct 17. Check whether either of them stayed above their Oct 14 level after views fell back. That shows whether anything besides the one-day jump in views lasted; it does not change how the pattern is classified.

Verdict: ☐ Pass ☐ Revise — notes:

### C1 · Paper Moon · Rose from zero (small numbers) · For awareness only

Rule `context_only` · suggestion · ✅ passes all checks · 24 words

> **Suggested follow-up** · No action taken automatically  
> Treat this as context rather than a trend, because it started from zero. Revisit it only if the increase continues in later processed data.

For comparison, the guided answer *What should I look into next?* (unchanged): Open View evidence and read the absolute numbers day by day. Decide whether changes of this size are large enough to matter for your review before giving this insight weight.

Verdict: ☐ Pass ☐ Revise — notes:

### C2 · Field Notes in Blue · Small or unsupported change · For awareness only

Rule `insufficient_evidence` · no specific · ✅ passes all checks · 21 words

> **Suggested follow-up** · No action taken automatically  
> The available evidence does not support a specific follow-up suggestion: the change is too small to count under the screening rules.

For comparison, the guided answer *What should I look into next?* (unchanged): Open View evidence and read the other measures for Oct 15. Because daily unique viewers are not recorded that day, judge the pattern on the measures that are, and treat the missing value as unknown rather than zero.

Verdict: ☐ Pass ☐ Revise — notes:

### F1 · Artwork F1 · Recent increase (not yet confirmed) · For awareness only

Rule `await_later_day` · suggestion · ✅ passes all checks · 19 words

> **Suggested follow-up** · No action taken automatically  
> This increase is worth monitoring, but there is not yet enough processed data to determine whether it will continue.

For comparison, the guided answer *What should I look into next?* (unchanged): Open View evidence and look at all four measures on Oct 17, the latest processed day. Treat this as unconfirmed for now: Oct 18 is not processed yet and is excluded.

Verdict: ☐ Pass ☐ Revise — notes:

### F2 · Artwork F2 · Not enough data to confirm · For awareness only

Rule `insufficient_evidence` · no specific · ✅ passes all checks · 23 words

> **Suggested follow-up** · No action taken automatically  
> The available evidence does not support a specific follow-up suggestion, because daily unique viewers are not recorded on one of the comparison days.

For comparison, the guided answer *What should I look into next?* (unchanged): Open View evidence and read the other measures for Oct 15. Because daily unique viewers are not recorded that day, judge the pattern on the measures that are, and treat the missing value as unknown rather than zero.

Verdict: ☐ Pass ☐ Revise — notes:

### Same evidence, other artworks (test fixture `tests/data/m10_followup_patterns.csv`)

| Artwork | Evidence | Rule | Follow-up |
|---|---|---|---|
| X001 | Sustained increase, Well supported; daily unique viewers ✓, favourites ✓, inquiries – | `monitor_continuation` | Consider keeping this artwork in view during the remaining fair days. Views increased and stayed elevated, with supporting increases in daily unique viewers and favourites. Review the next processed day to see whether that pattern continues. |
| X002 | Sustained increase, Well supported; daily unique viewers –, favourites ✓, inquiries ✓ | `monitor_continuation` | Consider keeping this artwork in view during the remaining fair days. Views increased and stayed elevated, with supporting increases in favourites and inquiries. Review the next processed day to see whether that pattern continues. |
| X003 | Sustained increase, Partly supported; daily unique viewers –, favourites ✓, inquiries – | `cautious_monitoring` | Keep this artwork on your watch list as a possible sustained increase. Favourites support the pattern, while daily unique viewers and inquiries did not increase. Reassess when more daily data is available. |
| X004 | Sustained increase, Partly supported; daily unique viewers ?, favourites ✓, inquiries – | `cautious_monitoring` | Keep this artwork on your watch list as a possible sustained increase. Favourites support the pattern, while inquiries did not increase and daily unique viewers are not recorded on one of the comparison days. Reassess when more daily data is available. |
| X006 | Sustained increase, Partly supported; daily unique viewers ✓, favourites –, inquiries – | `cautious_monitoring` | Keep this artwork on your watch list as a possible sustained increase. Daily unique viewers support the pattern, while favourites provide limited additional support and inquiries did not increase. Reassess when more daily data is available. |
| X005 | One-day spike, For awareness only; daily unique viewers ✓, favourites –, inquiries – | `recurrence_watch` | No immediate follow-up is suggested based on this temporary spike. Revisit the pattern if a new increase appears in subsequent data. |

Verdict: ☐ Pass ☐ Revise — notes:

## 2. Daily briefing

### The three-insight analysis (as in the demo recording)

> **Daily briefing** · Oct 14–Oct 17 · four processed fair days · Oct 18 excluded (not processed yet)  
> [Two sustained increases] · [One temporary spike] · [Three artworks not prioritised]
> - Strongest evidence: **Harbour at First Light** (Sustained increase · Well supported): views rose from 40 on Oct 14 to 80 on Oct 15 and stayed higher on every later processed day, with two other measures rising too.
> - **Salt Study, Grey** (Sustained increase · Partly supported): views rose from 25 on Oct 14 to 35 on Oct 15 and stayed higher on every later processed day, with one other measure rising too.
> - **Red Interval** (One-day spike · For awareness only): views jumped from 30 on Oct 14 to 45 on Oct 15, then fell back to 31 on Oct 17.
> **Not prioritised (not published):** Quiet Grid (steady); Paper Moon (rose from zero on small numbers); Field Notes in Blue (change too small or not supported).

Verdict: ☐ Pass ☐ Revise — notes:

### Variant: one draft withheld by validation (possible in a LIVE run)

> **Daily briefing** · Oct 14–Oct 17 · four processed fair days · Oct 18 excluded (not processed yet)  
> [One sustained increase] · [One temporary spike] · [Three artworks not prioritised] · [One draft withheld by validation]
> - Strongest evidence: **Harbour at First Light** (Sustained increase · Well supported): views rose from 40 on Oct 14 to 80 on Oct 15 and stayed higher on every later processed day, with two other measures rising too.
> - **Red Interval** (One-day spike · For awareness only): views jumped from 30 on Oct 14 to 45 on Oct 15, then fell back to 31 on Oct 17.
> **Not prioritised (not published):** Quiet Grid (steady); Paper Moon (rose from zero on small numbers); Field Notes in Blue (change too small or not supported).
> **Found but not published in this analysis:** Salt Study, Grey.
> **Withheld by validation:** One draft finding did not pass the evidence checks and is not shown.

Verdict: ☐ Pass ☐ Revise — notes:

## 3. Plain-language labels

The technical terms stay in tooltips and in the detailed evidence.

| Technical | Shown to the manager |
|---|---|
| higher-confidence | Well supported |
| moderate-confidence | Partly supported |
| qualified | For awareness only |
| Sustained increase | Sustained increase |
| Temporary spike | One-day spike |
| Weak signal | Small or unsupported change |
| Recent increase (not yet confirmed) | Recent increase (not yet confirmed) |
| Increase from zero | Rose from zero (small numbers) |
| Not enough evidence | Not enough data to confirm |
| Stable | Steady |
| No clear pattern | No clear pattern |
| support: supports | ✓ Supports it |
| support: insufficient | – Weak: rose too little to count |
| support: no_rise | – Weak: no rise |
| support: missing | ? Missing: not recorded |

Legend under the tiles: `✓ Supports it · – Weak · ? Missing`; its help text:

**Supports it:** another measure rose enough on the same day to count as support.  
**Weak or missing:** another measure rose too little, did not rise, or is not recorded. It adds no support, but it is not evidence against the pattern.  
**Against it:** evidence that contradicts the pattern, such as a jump that fell back on later days. It is listed under Explore insight when the screening checks find it.

Verdict: ☐ Pass ☐ Revise — notes:

## 4. Fictional artwork catalog

Titles, artists, media and images are fictional sample data for this prototype. The analysis uses only the source IDs and engagement figures.

| Source ID | Source label | Fictional title | Artist | Medium | Thumbnail |
|---|---|---|---|---|---|
| A001 | Artwork A1 | Harbour at First Light | Ines Halvorsen | Oil on linen | `assets/artworks/A001.svg` |
| A002 | Artwork A2 | Salt Study, Grey | Ines Halvorsen | Oil on panel | `assets/artworks/A002.svg` |
| B001 | Artwork B1 | Red Interval | Tomas Reyland | Acrylic on canvas | `assets/artworks/B001.svg` |
| B002 | Artwork B2 | Quiet Grid | Tomas Reyland | Acrylic on canvas | `assets/artworks/B002.svg` |
| C001 | Artwork C1 | Paper Moon | Noor Castellane | Ink on paper | `assets/artworks/C001.svg` |
| C002 | Artwork C2 | Field Notes in Blue | Noor Castellane | Watercolour | `assets/artworks/C002.svg` |

Verdict: ☐ Pass ☐ Revise — notes:
