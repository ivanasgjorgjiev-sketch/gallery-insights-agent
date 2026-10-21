# Gallery Insights Agent — Data Dictionary

## Purpose and scope
This document defines the single runtime dataset `daily_data.csv` for the fictional Gallery Insights Agent MVP. All records are synthetic and anonymous. The application analyzes **G001 / E001 only**. Fair-local dates are 2026-10-14 through 2026-10-18. Days 1–4 are processed; Day 5 is not processed and **must be excluded from all analytical calculations, insights and follow-up answers**. The fair-local timezone is a configuration concept; the dataset contains dates, not timestamps, so no timezone conversion is performed.

## Schema
| Field | Type | Level / definition | Missing and validity |
|---|---|---|---|
| `record_type` | enum | `gallery` or `artwork` | Required |
| `gallery_id` | string | Fictional gallery ID; `G001` | Required |
| `edition_id` | string | Fictional fair edition ID; `E001` | Required |
| `fair_date` | ISO date | Fair-local calendar day | Required |
| `day_processed` | boolean text | `true` = finalized/eligible; `false` = excluded | Required; parse explicitly |
| `artist_id` | string | Artist ID on artwork rows only | Blank for gallery rows |
| `artist_name` | string | Fictional artist display name | Blank for gallery rows |
| `artwork_id` | string | Unique artwork identifier within edition | Blank for gallery rows |
| `artwork_title` | string | Fictional artwork display name | Blank for gallery rows |
| `gallery_views` | nonnegative integer | Daily gallery-profile **view events** on gallery rows only | Blank on artwork rows |
| `artwork_views` | nonnegative integer | Daily artwork **view events**, including repeat views | Blank on gallery rows |
| `unique_artwork_viewers` | nonnegative integer or null | Distinct viewers of **one artwork on one day** | Blank means unknown; never replace with 0 |
| `favourites` | nonnegative integer | Daily artwork favourite events | Blank on gallery rows |
| `inquiries` | nonnegative integer | Daily artwork inquiry events | Blank on gallery rows |

**Blank is not zero.** Non-applicable fields are blank. For processed artwork records, `artwork_views`, `favourites`, and `inquiries` must contain valid nonnegative integers; `unique_artwork_viewers` may be blank to represent unknown. For processed gallery records, `gallery_views` must contain a valid nonnegative integer. A measured `0` is a genuine zero. Do not sum gallery and artwork views together: they measure different events. One gallery row and one row per artwork per fair date are expected. Reject duplicate `(record_type, gallery_id, edition_id, fair_date, artwork_id)` keys, inconsistent artist metadata, negative counts, invalid dates or unrecognized boolean strings.

## Calculation rules
1. Filter to `gallery_id=G001`, `edition_id=E001`, `day_processed=true` **before** aggregating, comparing, ranking or selecting evidence. Do not treat the fifth day's counts as eligible even if present.
2. Sum `artwork_views`, `favourites` and `inquiries` across eligible artwork rows when an aggregate event count is requested; use `gallery` rows only for `gallery_views` totals.
3. Artist totals sum the processed artwork-level event counts for all artworks belonging to that artist. **Artist A = A001 (286) + A002 (130) = 416 artwork-view events** across four processed days.
4. `unique_artwork_viewers` counts unique people **per artwork per day only**. Do not sum across days or artworks to claim distinct people, gallery reach or fair-wide unique visitors. Day-level comparisons for the same artwork are valid if both days have values.
5. Daily difference = `new - old`. Percentage change = `(new - old) / old * 100` **only if old > 0 and both values are known**. When old = 0, report the absolute change and state that percentage growth is undefined; never show infinity or an invented percentage. When either value is missing, comparison is unavailable.
6. All findings must cite the underlying artwork/gallery ID, fair-local date(s), metric names, source values, calculations and limitations. Observations are not evidence of causality, purchase intent, sales or future outcomes.
7. Candidate signal detection can use transparent, configurable heuristics, but should not hardcode an A1 insight. Multi-metric corroboration and persistence matter. A single-day spike is not sustained growth. No invented global 'best artwork' score.

## Seven deliberately seeded scenarios
| Scenario | Required reference values / interpretation |
|---|---|
| A1 strong increase | A001 views D1–D4: 40,80,76,90; daily uniques 30,45,50,60; favourites 5,12,11,13. D1→D2: +100% views, +50% daily uniques, +140% favourites. A001 total views = 286. |
| Artist A total | A002 views D1–D4: 25,35,32,38 = 130; A001+A002 = 416 **events**, not distinct people. |
| B1 temporary spike | B001 views 30,45,32,31; do not claim sustained growth. |
| B2 stable | B002 views 20,21,20,20; favourites 2/day; inquiries 0/day. Suppress manufactured trends. |
| C1 zero baseline | C001 views D1→D2: 0→10; +10 absolute, percentage undefined. |
| C2 missing metric | C002 Day 1: 15 views and 12 daily unique viewers; Day 2: 20 views and **blank** daily unique viewers. Do not infer 0. |
| Day 5 excluded | 2026-10-18 is `false`. A001 has 150 views, 95 daily uniques, 20 favourites and 4 inquiries that must never affect eligible results. |

## Synthetic assumptions introduced to complete the CSV
The PRD specifies only selected fields and daily sequences. The remaining counts for A002, B001, B002, C001, C002, A001 inquiries, and all unprocessed Day 5 records (except A001) are **invented test fixtures**, not original PRD facts. The gallery Day 5 value of 210 is also invented. They support a complete rectangular dataset and must not be represented as observed real-world engagement. All records are fictional; there is no collector-level or sales information.

## Expected integrity checks
- 35 total rows: 5 gallery rows + 6 artworks × 5 days; 28 processed rows (4 gallery + 24 artwork).
- Processed gallery views: 120 + 165 + 158 + 172 = **615**.
- A001 processed artwork views: **286**, not **436**.
- A002 processed artwork views: **130**.
- Artist A processed artwork views: **416**.
- C002 Day 2 `unique_artwork_viewers` is null, not zero.
