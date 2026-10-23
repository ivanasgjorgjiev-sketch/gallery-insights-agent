"""The six approved analytical tools (agent_policy.md, "APPROVED ANALYTICAL CAPABILITIES").

Every tool:
- works only on validated, processed G001/E001 records (via gia.data),
- validates its arguments and raises ToolError with a clear message on bad input,
- returns plain JSON-serialisable dicts with source dates, values, CSV line numbers,
  calculations and limitations, so results are auditable and can be shown as evidence.

Calculation rules follow data_dictionary.md. The LLM never computes numbers itself.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from gia.data import ProcessedData, load_processed_data

# --- Configurable pattern-detection rules ---------------------------------------
# Approved screening heuristics (Milestone 2). They are transparent rules of thumb,
# not statistical significance tests. Thresholds are per metric, never per artwork.
PATTERN_RULES = {
    "min_increase_pct": 30.0,     # key jump: day-over-day increase of at least 30% ...
    "min_absolute_change": {      # ... and at least this many events (also used for supporting metrics)
        "artwork_views": 10,
        "unique_artwork_viewers": 5,
        "favourites": 3,
        "inquiries": 2,
    },
    "min_later_days": 2,          # persistence must be observed on at least 2 later processed days
    "min_gain_retained": 0.5,     # every later day keeps >= 50% of the increase
    "support_min_pct": 30.0,      # a supporting metric counts only if it rises >= 30% and meets its minimum
    "stable_tolerance": 0.10,     # stable: every day within 10% of the average
}

ARTWORK_METRICS = ["artwork_views", "unique_artwork_viewers", "favourites", "inquiries"]
SUMMABLE_METRICS = ["artwork_views", "favourites", "inquiries"]
SUPPORTING_METRICS = {
    "artwork_views": ["unique_artwork_viewers", "favourites", "inquiries"],
    "unique_artwork_viewers": ["artwork_views", "favourites", "inquiries"],
    "favourites": ["artwork_views", "unique_artwork_viewers", "inquiries"],
    "inquiries": ["artwork_views", "unique_artwork_viewers", "favourites"],
}
UNIQUE_VIEWER_NOTE = (
    "unique_artwork_viewers counts distinct viewers of one artwork on one day only; "
    "it cannot be summed across days or artworks to count distinct people."
)
EVENTS_NOTE = "Counts are engagement events (repeat views included), not distinct people."
HEURISTIC_NOTE = (
    "Patterns come from configurable screening heuristics, not statistical significance tests."
)
EVIDENCE_STRENGTH_NOTE = (
    "'higher-confidence' and 'moderate-confidence' are qualitative evidence-strength labels "
    "(how many metrics corroborate the pattern), not statistical confidence levels or probabilities."
)
NOT_CAUSAL_NOTE = (
    "Engagement data shows what happened, not why; it does not establish causality, "
    "purchase intent or sales outcomes."
)


class ToolError(Exception):
    """A tool could not run because of invalid arguments or unavailable data."""


# --- Helpers ---------------------------------------------------------------------

def _value(v: Any) -> int | None:
    return None if v is pd.NA or pd.isna(v) else int(v)


def _artwork_rows(data: ProcessedData, artwork_id: str) -> pd.DataFrame:
    rows = data.artwork_daily[data.artwork_daily["artwork_id"] == artwork_id]
    if rows.empty:
        valid = sorted(data.artwork_daily["artwork_id"].unique())
        raise ToolError(f"Unknown artwork_id '{artwork_id}'. Valid IDs for "
                        f"{data.gallery_id}/{data.edition_id}: {valid}")
    return rows.sort_values("fair_date")


def _check_metrics(metrics: list[str] | None, allowed: list[str]) -> list[str]:
    if metrics is None:
        return list(allowed)
    if not isinstance(metrics, list) or not metrics:
        raise ToolError(f"metrics must be a non-empty list drawn from {allowed}")
    bad = [m for m in metrics if m not in allowed]
    if bad:
        raise ToolError(f"Unsupported metric(s) {bad}. Allowed: {allowed}")
    return metrics


def _check_date(data: ProcessedData, date: str) -> None:
    if date in data.excluded_dates:
        raise ToolError(f"{date} is excluded because day_processed=false; it cannot be "
                        f"used in any calculation. Processed dates: {data.processed_dates}")
    if date not in data.processed_dates:
        raise ToolError(f"{date} is not a processed fair date. Processed dates: {data.processed_dates}")


def compare_values(old: int | None, new: int | None) -> dict:
    """Daily difference and percentage change per data_dictionary.md rule 5."""
    if old is None or new is None:
        return {"absolute_change": None, "percentage_change": None, "status": "unavailable",
                "calculation": "Comparison unavailable: at least one value is missing (unknown, not zero)."}
    delta = new - old
    if old == 0:
        return {"absolute_change": delta, "percentage_change": None, "status": "zero_baseline",
                "calculation": f"{new} - {old} = {delta:+d}; percentage change undefined because the "
                               f"baseline is 0, so only the absolute change is reported."}
    pct = round(delta / old * 100, 1)
    return {"absolute_change": delta, "percentage_change": pct, "status": "ok",
            "calculation": f"{new} - {old} = {delta:+d}; ({new} - {old}) / {old} × 100 = {pct:+.1f}%"}


def _artwork_info(rows: pd.DataFrame) -> dict:
    first = rows.iloc[0]
    return {"artwork_id": first["artwork_id"], "artwork_title": first["artwork_title"],
            "artist_id": first["artist_id"], "artist_name": first["artist_name"]}


# --- Tool 1 ----------------------------------------------------------------------

def get_processed_data() -> dict:
    """Validate the CSV and summarise the eligible G001/E001 processed records."""
    data = load_processed_data()
    artworks = (data.artwork_daily[["artwork_id", "artwork_title", "artist_id", "artist_name"]]
                .drop_duplicates().sort_values("artwork_id"))
    gallery = data.gallery_daily
    gallery_total = int(gallery["gallery_views"].sum())
    return {
        "gallery_id": data.gallery_id,
        "edition_id": data.edition_id,
        "source_file": data.source_file,
        "validation": "passed",
        "processed_dates": data.processed_dates,
        "excluded_dates": [{"date": d, "reason": "day_processed=false; excluded from all analysis"}
                           for d in data.excluded_dates],
        "eligible_rows": data.eligible_rows,
        "total_rows": data.total_rows,
        "artworks": artworks.to_dict("records"),
        "gallery_profile_views": {
            "daily": [{"date": r.fair_date, "gallery_views": int(r.gallery_views), "source_line": int(r.source_line)}
                      for r in gallery.itertuples()],
            "total": gallery_total,
            "calculation": " + ".join(str(v) for v in gallery["gallery_views"]) + f" = {gallery_total}",
            "note": "Gallery-profile view events; a different event type from artwork views, never combined with them.",
        },
        "data_notes": data.notes,
        "available_metrics": ARTWORK_METRICS,
    }


# --- Tool 2 ----------------------------------------------------------------------

def get_artwork_metrics(artwork_id: str, metrics: list[str] | None = None) -> dict:
    """Daily values for one artwork across all processed days. Missing stays null."""
    data = load_processed_data()
    rows = _artwork_rows(data, artwork_id)
    metrics = _check_metrics(metrics, ARTWORK_METRICS)
    result = {**_artwork_info(rows), "processed_dates": data.processed_dates, "metrics": {}}
    for m in metrics:
        daily = [{"date": r["fair_date"], "value": _value(r[m]), "source_line": int(r["source_line"])}
                 for _, r in rows.iterrows()]
        entry: dict[str, Any] = {"daily": daily}
        missing = [d["date"] for d in daily if d["value"] is None]
        if missing:
            entry["missing_dates"] = missing
            entry["missing_note"] = "Blank in source: unknown, not zero."
        if m in SUMMABLE_METRICS:
            values = [d["value"] for d in daily]
            entry["total_events"] = sum(values)
            entry["total_calculation"] = " + ".join(map(str, values)) + f" = {sum(values)}"
        else:
            entry["total_events"] = None
            entry["total_note"] = UNIQUE_VIEWER_NOTE
        result["metrics"][m] = entry
    result["limitations"] = [EVENTS_NOTE, NOT_CAUSAL_NOTE]
    return result


# --- Tool 3 ----------------------------------------------------------------------

def compare_daily_metrics(artwork_id: str, old_date: str, new_date: str,
                          metrics: list[str] | None = None) -> dict:
    """Absolute and valid percentage changes for one artwork between two processed days."""
    data = load_processed_data()
    rows = _artwork_rows(data, artwork_id)
    metrics = _check_metrics(metrics, ARTWORK_METRICS)
    _check_date(data, old_date)
    _check_date(data, new_date)
    if old_date >= new_date:
        raise ToolError("old_date must be earlier than new_date")
    old_row = rows[rows["fair_date"] == old_date].iloc[0]
    new_row = rows[rows["fair_date"] == new_date].iloc[0]
    comparisons = []
    for m in metrics:
        old, new = _value(old_row[m]), _value(new_row[m])
        comparisons.append({"metric": m, "old_value": old, "new_value": new, **compare_values(old, new)})
    limitations = [EVENTS_NOTE, NOT_CAUSAL_NOTE]
    if any(c["status"] == "unavailable" for c in comparisons):
        limitations.append("Some comparisons are unavailable because a value is missing (unknown, not zero).")
    if any(c["status"] == "zero_baseline" for c in comparisons):
        limitations.append("Percentage growth from a zero baseline is undefined; only absolute change is reported.")
    return {
        **_artwork_info(rows),
        "old_date": old_date, "new_date": new_date,
        "source_lines": {old_date: int(old_row["source_line"]), new_date: int(new_row["source_line"])},
        "comparisons": comparisons,
        "limitations": limitations,
    }


# --- Tool 4 ----------------------------------------------------------------------

def aggregate_artist_metrics(artist_id: str, metrics: list[str] | None = None) -> dict:
    """Sum processed artwork-level event counts for all artworks of one artist."""
    if metrics and "unique_artwork_viewers" in metrics:
        raise ToolError("unique_artwork_viewers cannot be aggregated. " + UNIQUE_VIEWER_NOTE)
    metrics = _check_metrics(metrics, SUMMABLE_METRICS)
    data = load_processed_data()
    rows = data.artwork_daily[data.artwork_daily["artist_id"] == artist_id]
    if rows.empty:
        valid = sorted(data.artwork_daily["artist_id"].unique())
        raise ToolError(f"Unknown artist_id '{artist_id}'. Valid IDs: {valid}")
    totals = {}
    for m in metrics:
        per_artwork = []
        for artwork_id, art_rows in rows.groupby("artwork_id"):
            values = [int(v) for v in art_rows.sort_values("fair_date")[m]]
            per_artwork.append({"artwork_id": artwork_id, "artwork_title": art_rows.iloc[0]["artwork_title"],
                                "daily_values": values, "total_events": sum(values),
                                "calculation": " + ".join(map(str, values)) + f" = {sum(values)}"})
        total = sum(a["total_events"] for a in per_artwork)
        totals[m] = {"per_artwork": per_artwork, "artist_total_events": total,
                     "calculation": " + ".join(str(a["total_events"]) for a in per_artwork) + f" = {total}"}
    return {
        "artist_id": artist_id, "artist_name": rows.iloc[0]["artist_name"],
        "processed_dates": data.processed_dates,
        "source_lines": sorted(int(x) for x in rows["source_line"]),
        "totals": totals,
        "limitations": [EVENTS_NOTE + " A total is not a count of distinct visitors.",
                        UNIQUE_VIEWER_NOTE, NOT_CAUSAL_NOTE],
    }


# --- Tool 5 ----------------------------------------------------------------------

HANDLING = {
    "sustained_growth": "candidate_insight",
    "temporary_spike": "qualify_or_withhold",
    "weak_signal": "qualify_or_withhold",
    "emerging_increase": "qualify_or_withhold",
    "zero_baseline_change": "qualify_or_withhold",
    "insufficient_evidence": "qualify_or_withhold",
    "stable": "suppress",
    "no_clear_pattern": "suppress",
}


def _support(supporting: dict[str, list[int | None]], i: int, rules: dict) -> list[dict]:
    """Assess each supporting metric on the same two days as the key jump (i-1 -> i)."""
    out = []
    for m, series in supporting.items():
        old, new = series[i - 1], series[i]
        cmp = compare_values(old, new)
        minimum = rules["min_absolute_change"][m]
        if cmp["status"] == "unavailable":
            qualifies, reason = None, "unknown: value missing, so support cannot be verified"
        elif new <= old:
            qualifies, reason = False, "did not increase"
        elif cmp["absolute_change"] < minimum:
            qualifies, reason = False, f"increase +{cmp['absolute_change']} below minimum {minimum}"
        elif cmp["status"] == "ok" and cmp["percentage_change"] < rules["support_min_pct"]:
            qualifies, reason = False, f"increase {cmp['percentage_change']:+.1f}% below {rules['support_min_pct']}%"
        else:
            qualifies = True
            reason = ("meets absolute minimum (percentage undefined from zero baseline)"
                      if cmp["status"] == "zero_baseline" else "meets percentage and absolute minimums")
        out.append({"metric": m, "old_value": old, "new_value": new, **cmp,
                    "qualifies_as_support": qualifies, "reason": reason})
    return out


def classify_series(dates: list[str], values: list[int | None],
                    supporting: dict[str, list[int | None]],
                    metric: str = "artwork_views", rules: dict = PATTERN_RULES) -> dict:
    """Classify one daily series with the approved PATTERN_RULES. Pure and deterministic.

    Decision order (first match wins, so each series gets exactly one category):
    1. missing value in the series -> insufficient_evidence
    2. first value 0 and later increase -> zero_baseline_change
    3. no meaningful jump (>= min % AND >= min absolute) -> stable / weak_signal / no_clear_pattern
    4. fewer than min_later_days after the jump -> emerging_increase
    5. retention on later days: all keep >= half -> continue; all lose > half -> temporary_spike;
       mixed -> weak_signal
    6. corroboration: >= 2 qualifying metrics -> sustained_growth (higher-confidence);
       1 -> sustained_growth (moderate-confidence); 0 with unknowns -> insufficient_evidence;
       0 -> weak_signal
    """
    criteria: list[dict] = []
    limitations: list[str] = []
    min_abs = rules["min_absolute_change"][metric]

    def result(category, explanation, key=None, support=None, strength=None):
        unknown = [s["metric"] for s in (support or []) if s["qualifies_as_support"] is None]
        if unknown:
            limitations.append(f"{', '.join(unknown)} unknown on the comparison days; "
                               "its support could not be verified (missing is not zero).")
        if strength:
            limitations.append(EVIDENCE_STRENGTH_NOTE)
        return {"category": category, "evidence_strength": strength, "explanation": explanation,
                "key_comparison": key, "supporting_metrics": support or [],
                "criteria": criteria, "limitations": limitations}

    def key_comparison(i):
        return {"old_date": dates[i - 1], "new_date": dates[i], "old_value": values[i - 1],
                "new_value": values[i], **compare_values(values[i - 1], values[i])}

    # 1. Missing values are never skipped: they prevent verification.
    missing = [d for d, v in zip(dates, values) if v is None]
    criteria.append({"rule": "complete_series", "passed": not missing and len(values) >= 2,
                     "detail": f"{metric} unknown on {missing}" if missing else
                               f"{len(values)} processed days, no missing values"})
    if missing or len(values) < 2:
        limitations.append("Missing values are unknown, not zero; trends and persistence cannot be verified.")
        return result("insufficient_evidence",
                      f"{metric} is unknown on {missing}; the pattern cannot be verified." if missing
                      else "Fewer than two processed days; no comparison possible.")

    # 2. Zero baseline: absolute change only.
    if values[0] == 0 and any(v > 0 for v in values[1:]):
        i = next(i for i, v in enumerate(values) if v > 0)
        criteria.append({"rule": "zero_baseline", "passed": True,
                         "detail": "Starting value is 0, so percentage growth is undefined."})
        limitations.append("Percentage growth from a zero baseline is undefined; absolute change only.")
        return result("zero_baseline_change",
                      f"Increase from 0 to {values[i]} ({values[i]:+d} absolute) between {dates[i - 1]} and "
                      f"{dates[i]}; percentage undefined. All processed values: {values}.",
                      key_comparison(i), _support(supporting, i, rules))

    # 3. Find the key jump: the largest day-over-day percentage increase.
    pct_steps = [(i, (values[i] - values[i - 1]) / values[i - 1] * 100)
                 for i in range(1, len(values)) if values[i - 1] > 0]
    best_i, best_pct = max(pct_steps, key=lambda s: s[1]) if pct_steps else (None, None)
    pct_ok = best_pct is not None and best_pct >= rules["min_increase_pct"]
    gain = values[best_i] - values[best_i - 1] if best_i else 0
    abs_ok = pct_ok and gain >= min_abs
    if best_i:
        criteria.append({"rule": "min_increase_pct", "passed": pct_ok,
                         "detail": f"Largest day-over-day increase {dates[best_i - 1]}→{dates[best_i]}: "
                                   f"{values[best_i - 1]}→{values[best_i]} ({best_pct:+.1f}%) vs "
                                   f"minimum {rules['min_increase_pct']}%"})
    if pct_ok:
        criteria.append({"rule": "min_absolute_change", "passed": abs_ok,
                         "detail": f"Increase +{gain} vs minimum {min_abs} for {metric}"})

    if not abs_ok:
        mean = sum(values) / len(values)
        stable = mean > 0 and all(abs(v - mean) / mean <= rules["stable_tolerance"] for v in values)
        criteria.append({"rule": "stable_tolerance", "passed": stable,
                         "detail": f"Values {values}, average {mean:.2f}; every day within "
                                   f"{rules['stable_tolerance']:.0%} of average: {stable}"})
        if stable:
            return result("stable", f"Stable engagement {values}; no trend to report.")
        if pct_ok:
            return result("weak_signal",
                          f"Increase {values[best_i - 1]}→{values[best_i]} ({best_pct:+.1f}%) is only +{gain} "
                          f"events, below the minimum of {min_abs}. Too small to treat as meaningful.",
                          key_comparison(best_i), _support(supporting, best_i, rules))
        return result("no_clear_pattern", f"No pattern meets the configured criteria for {values}.")

    i, base, peak = best_i, values[best_i - 1], values[best_i]
    key, support = key_comparison(i), _support(supporting, i, rules)

    # 4. Persistence needs enough later days.
    later = values[i + 1:]
    enough = len(later) >= rules["min_later_days"]
    criteria.append({"rule": "min_later_days", "passed": enough,
                     "detail": f"{len(later)} processed day(s) after the jump vs minimum {rules['min_later_days']}"})
    if not enough:
        return result("emerging_increase",
                      f"Increase {base}→{peak} ({best_pct:+.1f}%) is too recent to confirm persistence.",
                      key, support)

    # 5. Retention decides sustained vs spike (mutually exclusive).
    retained = [(v - base) / gain for v in later]
    kept = [r >= rules["min_gain_retained"] for r in retained]
    criteria.append({"rule": "min_gain_retained", "passed": all(kept),
                     "detail": f"Later values {later} keep {[f'{r:.0%}' for r in retained]} of the +{gain} "
                               f"increase (need ≥ {rules['min_gain_retained']:.0%} on every later day)"})
    if not any(kept):
        return result("temporary_spike",
                      f"One-day increase {base}→{peak} ({best_pct:+.1f}%) was not maintained: later values "
                      f"{later} gave back more than half of it. Not sustained growth.", key, support)
    if not all(kept):
        return result("weak_signal",
                      f"Increase {base}→{peak} ({best_pct:+.1f}%) was maintained on some later days but "
                      f"not others ({later}); inconsistent.", key, support)

    # 6. Corroboration by other metrics on the same days.
    qualifying = [s["metric"] for s in support if s["qualifies_as_support"]]
    unknown = [s["metric"] for s in support if s["qualifies_as_support"] is None]
    criteria.append({"rule": "corroboration", "passed": bool(qualifying),
                     "detail": f"Qualifying supporting metrics: {qualifying or 'none'}"
                               + (f"; unknown: {unknown}" if unknown else "")})
    summary = f"Increase {base}→{peak} ({best_pct:+.1f}%) maintained on later days {later}"
    if len(qualifying) >= 2:
        return result("sustained_growth", f"{summary}, corroborated by {qualifying}.", key, support,
                      "higher-confidence")
    if len(qualifying) == 1:
        return result("sustained_growth", f"{summary}, corroborated by {qualifying[0]} only.", key, support,
                      "moderate-confidence")
    if unknown:
        return result("insufficient_evidence",
                      f"{summary}, but corroboration cannot be verified because {unknown} is unknown.",
                      key, support)
    return result("weak_signal", f"{summary}, but no other metric corroborates it.", key, support)


def detect_engagement_patterns(metric: str = "artwork_views", artwork_ids: list[str] | None = None) -> dict:
    """Evidence-linked candidate patterns for each artwork, using PATTERN_RULES."""
    _check_metrics([metric], ARTWORK_METRICS)
    data = load_processed_data()
    ids = artwork_ids or sorted(data.artwork_daily["artwork_id"].unique())
    results = []
    for artwork_id in ids:
        rows = _artwork_rows(data, artwork_id)
        dates = rows["fair_date"].tolist()
        series = {m: [_value(v) for v in rows[m]] for m in ARTWORK_METRICS}
        outcome = classify_series(dates, series[metric],
                                  {m: series[m] for m in SUPPORTING_METRICS[metric]}, metric)
        results.append({
            **_artwork_info(rows), "metric": metric,
            "daily": [{"date": d, "value": v, "source_line": int(l)}
                      for d, v, l in zip(dates, series[metric], rows["source_line"])],
            **outcome,
            "suggested_handling": HANDLING[outcome["category"]],
        })
    return {
        "gallery_id": data.gallery_id, "edition_id": data.edition_id,
        "processed_dates": data.processed_dates, "metric": metric,
        "rules": PATTERN_RULES, "patterns": results,
        "limitations": [HEURISTIC_NOTE, EVIDENCE_STRENGTH_NOTE, NOT_CAUSAL_NOTE],
    }


# --- Tool 6 ----------------------------------------------------------------------

SIGNAL_TYPES = set(HANDLING)
TEXT_FIELDS = ["title", "observed_signal", "why_it_may_matter", "suggested_next_step"]

PROHIBITED_CLAIMS = [
    (r"purchase intent|intent to (buy|purchase)|(likely|going|ready) to (buy|purchase|sell)|will sell|"
     r"(sales|purchase) (forecast|prediction)", "purchase intent or sales prediction"),
    (r"guarantee", "guarantee"),
    (r"\b(caused|causes|driven by (the|our|a) (campaign|marketing|promotion)|because of (the|our) "
     r"(campaign|marketing|promotion)|due to (the|our) (campaign|marketing|promotion))", "causal claim"),
    (r"(unique|distinct|different) (people|persons|visitors|individuals)|\bvisitors\b", "distinct-people claim"),
    (r"\bcollector[s]? (name|identity|identities|contact)", "collector identity"),
]
PROHIBITED_ACTIONS = r"discount|reduce (the )?price|change (the )?price|raise (the )?price|pricing decision|" \
                     r"contact (the )?collectors|email (the )?collectors|send (a )?message"
SAFE_NEXT_STEP = "Review the engagement evidence and decide whether further investigation is worthwhile."
CAUSE_SEEKING_STEP = (r"coincid|what (may |might |could )?(have )?(caused|driven|drove|triggered|explains?)|"
                      r"why (the |this |it |views |engagement )|reasons? (for|behind)|\bdrivers?\b|attribut")
NEGATION = re.compile(r"\b(not|no|never|without|cannot|can't|doesn't|does not|isn't|is not|nor|neither)\b[^.;]*$",
                      re.IGNORECASE)


def _asserted(pattern: str, text: str) -> list[str]:
    """Matches of `pattern` in `text` that are not negated earlier in the same clause."""
    hits = []
    for m in re.finditer(pattern, text, re.IGNORECASE):
        clause_start = max(text.rfind(".", 0, m.start()), text.rfind(";", 0, m.start())) + 1
        if not NEGATION.search(text[clause_start:m.start()]):
            hits.append(m.group(0))
    return hits


def build_insight_id(insight: dict) -> str:
    subject = insight.get("artwork_id") or insight.get("artist_id") or "GALLERY"
    signal = str(insight.get("signal_type", "insight")).upper()
    changes = insight.get("metric_changes") or []
    if changes:
        span = f"{changes[0]['old_date']}_{changes[0]['new_date']}".replace("-", "")
        return f"INS-{subject}-{signal}-{span}"
    return f"INS-{subject}-{signal}"


def validate_evidence(insight: dict) -> dict:
    """Deterministically check a proposed insight before it can be shown.

    Expected insight fields: signal_type, artwork_id and/or artist_id, title, observed_signal,
    why_it_may_matter, optional suggested_next_step, confidence, limitations (list),
    metric_changes (list of {artwork_id, metric, old_date, new_date, old_value, new_value,
    absolute_change, percentage_change}) and/or metric_totals (list of {scope: artwork|artist,
    id, metric, total}).
    """
    if not isinstance(insight, dict):
        raise ToolError("insight must be an object")
    data = load_processed_data()
    errors: list[str] = []
    checked: list[dict] = []
    allowed_numbers: set[float] = set()

    signal = insight.get("signal_type")
    if signal not in SIGNAL_TYPES:
        errors.append(f"signal_type must be one of {sorted(SIGNAL_TYPES)}")
    for field in ("title", "observed_signal", "why_it_may_matter", "confidence"):
        if not str(insight.get(field) or "").strip():
            errors.append(f"missing {field}")
    limitations = insight.get("limitations")
    if not isinstance(limitations, list) or not any(str(x).strip() for x in limitations):
        errors.append("at least one limitation is required")
        limitations = []

    artworks = set(data.artwork_daily["artwork_id"])
    artists = set(data.artwork_daily["artist_id"])
    if insight.get("artwork_id") and insight["artwork_id"] not in artworks:
        errors.append(f"unknown artwork_id {insight['artwork_id']}")
    if insight.get("artist_id") and insight["artist_id"] not in artists:
        errors.append(f"unknown artist_id {insight['artist_id']}")

    changes = insight.get("metric_changes") or []
    totals = insight.get("metric_totals") or []
    if not changes and not totals:
        errors.append("an insight needs at least one metric_change or metric_total as evidence")

    for c in changes:
        label = f"{c.get('artwork_id')} {c.get('metric')} {c.get('old_date')}→{c.get('new_date')}"
        try:
            actual = compare_daily_metrics(c.get("artwork_id"), c.get("old_date"), c.get("new_date"),
                                           [c.get("metric")])
        except ToolError as e:
            errors.append(f"{label}: {e}")
            continue
        truth = actual["comparisons"][0]
        problems = []
        for key in ("old_value", "new_value", "absolute_change"):
            if c.get(key) != truth[key]:
                problems.append(f"{key} claimed {c.get(key)}, source gives {truth[key]}")
        claimed_pct, true_pct = c.get("percentage_change"), truth["percentage_change"]
        if true_pct is None and claimed_pct is not None:
            problems.append(f"percentage_change must be null ({truth['status']}), claimed {claimed_pct}")
        elif true_pct is not None and (claimed_pct is None or abs(float(claimed_pct) - true_pct) > 0.1):
            problems.append(f"percentage_change claimed {claimed_pct}, source gives {true_pct}")
        errors.extend(f"{label}: {p}" for p in problems)
        checked.append({"claim": label, "verified": not problems, "source": truth,
                        "source_lines": actual["source_lines"]})
        for v in (truth["old_value"], truth["new_value"], truth["absolute_change"], true_pct):
            if v is not None:
                allowed_numbers.update({abs(float(v)), round(abs(float(v)))})

    for t in totals:
        label = f"{t.get('scope')} {t.get('id')} {t.get('metric')} total"
        try:
            if t.get("scope") == "artist":
                agg = aggregate_artist_metrics(t.get("id"), [t.get("metric")])["totals"][t.get("metric")]
                true_total = agg["artist_total_events"]
                parts = [a["total_events"] for a in agg["per_artwork"]]
            elif t.get("scope") == "artwork":
                if t.get("metric") not in SUMMABLE_METRICS:
                    raise ToolError(f"{t.get('metric')} cannot be totalled. " + UNIQUE_VIEWER_NOTE)
                m = get_artwork_metrics(t.get("id"), [t.get("metric")])["metrics"][t.get("metric")]
                true_total, parts = m["total_events"], [d["value"] for d in m["daily"]]
            else:
                raise ToolError("scope must be 'artwork' or 'artist'")
        except ToolError as e:
            errors.append(f"{label}: {e}")
            continue
        ok = t.get("total") == true_total
        if not ok:
            errors.append(f"{label}: claimed {t.get('total')}, source gives {true_total}")
        checked.append({"claim": label, "verified": ok, "source": {"total": true_total, "parts": parts}})
        allowed_numbers.update(float(x) for x in [true_total, *parts])

    # Every number written in the text must come from verified evidence.
    allowed_numbers.update(float(n) for n in range(1, len(data.processed_dates) + len(data.excluded_dates) + 1))
    for d in data.processed_dates:
        allowed_numbers.update(float(p) for p in d.split("-"))
    text_parts = {f: str(insight.get(f) or "") for f in TEXT_FIELDS}
    text_parts["limitations"] = " ".join(str(x) for x in limitations)
    for field, text in text_parts.items():
        for iso in re.findall(r"\d{4}-\d{2}-\d{2}", text):
            if iso not in data.processed_dates and not (field == "limitations" and iso in data.excluded_dates):
                errors.append(f"{field}: date {iso} is not a processed fair date")
        cleaned = re.sub(r"\d{4}-\d{2}-\d{2}|\b[A-Z]+\d+\b", " ", text)
        for num in re.findall(r"\d+(?:\.\d+)?", cleaned):
            if float(num) not in allowed_numbers:
                errors.append(f"{field}: number {num} is not supported by the verified evidence")

    # Next-step *action policy* is checked separately from factual validity: the publication gate may
    # replace a non-compliant next step with SAFE_NEXT_STEP, but never repairs factual errors.
    next_step_errors: list[str] = []
    for field in TEXT_FIELDS:
        for pattern, label in PROHIBITED_CLAIMS:
            for hit in _asserted(pattern, text_parts[field]):
                if field == "suggested_next_step" and label == "causal claim":
                    # In a next step, "what caused..." is a cause-seeking action, not a factual claim.
                    next_step_errors.append(f"suggested_next_step: must be neutral and non-causal, "
                                            f"not a search for causes ('{hit}')")
                else:
                    errors.append(f"{field}: unsupported {label} ('{hit}')")
    for hit in _asserted(PROHIBITED_ACTIONS, text_parts["suggested_next_step"]):
        next_step_errors.append(f"suggested_next_step: commercial action outside the agent's authority ('{hit}')")
    for hit in _asserted(CAUSE_SEEKING_STEP, text_parts["suggested_next_step"]):
        next_step_errors.append(f"suggested_next_step: must be neutral and non-causal, not a search for causes ('{hit}')")

    return {
        "valid": not errors and not next_step_errors,
        "insight_id": build_insight_id(insight),
        "errors": errors + next_step_errors,
        "factual_errors": errors,
        "next_step_errors": next_step_errors,
        "checked_claims": checked,
        "scope": {"gallery_id": data.gallery_id, "edition_id": data.edition_id,
                  "processed_dates": data.processed_dates, "excluded_dates": data.excluded_dates},
    }
