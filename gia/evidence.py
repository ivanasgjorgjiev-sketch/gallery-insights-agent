"""Build the "View evidence" content for a published insight.

Everything is recomputed from the deterministic tools at display time (never taken from
LLM text), so LIVE and DEMO modes show identical, source-grounded evidence.
"""

from __future__ import annotations

from gia import explain, tools
from gia.display_names import edition_label, gallery_name

RULE_LABELS = {
    "complete_series": "No missing values in the series",
    "zero_baseline": "Started from zero (percentage not calculable)",
    "min_increase_pct": "Day-over-day increase of at least {min_increase_pct:.0f}%",
    "min_absolute_change": "Increase large enough in absolute terms",
    "min_later_days": "At least {min_later_days} later days to check it held",
    "min_gain_retained": "Kept at least {retained:.0f}% of the increase on every later day",
    "corroboration": "At least one other measure rose enough to support it",
    "stable_tolerance": "Every day within {stable:.0f}% of the average",
}


def _rule_label(rule: str) -> str:
    r = tools.PATTERN_RULES
    return RULE_LABELS.get(rule, rule).format(
        min_increase_pct=r["min_increase_pct"], min_later_days=r["min_later_days"],
        retained=r["min_gain_retained"] * 100, stable=r["stable_tolerance"] * 100)


def build_evidence(entry: dict) -> dict:
    """entry: a published insight from the publication gate ({insight_id, insight, checked_claims, pattern})."""
    insight, pattern = entry["insight"], entry["pattern"]
    artwork_id = insight["artwork_id"]
    overview = tools.get_processed_data()
    metrics = tools.get_artwork_metrics(artwork_id)
    kc = pattern["key_comparison"]

    daily = []
    for i, date in enumerate(metrics["processed_dates"]):
        row = {"Date": explain.fmt_date_long(date)}
        for m, name in explain.METRIC_NAMES.items():
            row[name] = explain.fmt_value(metrics["metrics"][m]["daily"][i]["value"])
        row["Source (CSV line)"] = metrics["metrics"]["artwork_views"]["daily"][i]["source_line"]
        row["Status"] = "Processed · used"
        daily.append(row)
    for e in overview["excluded_dates"]:
        daily.append({"Date": explain.fmt_date_long(e["date"]),
                      **{name: "—" for name in explain.METRIC_NAMES.values()},
                      "Source (CSV line)": "—", "Status": "Excluded (not processed yet)"})

    comparison = []
    if kc:
        cmp = tools.compare_daily_metrics(artwork_id, kc["old_date"], kc["new_date"])
        for c in cmp["comparisons"]:
            comparison.append({
                "Measure": explain.METRIC_NAMES[c["metric"]],
                explain.fmt_date_long(kc["old_date"]): explain.fmt_value(c["old_value"]),
                explain.fmt_date_long(kc["new_date"]): explain.fmt_value(c["new_value"]),
                "Change": explain.change_text(c),
                "Calculation": c["calculation"],
            })

    checks = [{"Screening check": _rule_label(c["rule"]), "Result": "✅ met" if c["passed"] else "❌ not met",
               "Detail": c["detail"]} for c in pattern["criteria"]]

    artist = tools.aggregate_artist_metrics(metrics["artist_id"], ["artwork_views"])
    artist_views = artist["totals"]["artwork_views"]

    has_missing = any(d["value"] is None for m in metrics["metrics"].values() for d in m["daily"])
    has_zero = any(r["Change"].endswith("started at 0") for r in comparison)
    notes = []
    if overview["excluded_dates"]:
        days = [explain.fmt_date_long(e["date"]) for e in overview["excluded_dates"]]
        notes.append(f"{', '.join(days)} is excluded: that day's data has not been finalised (processed) yet, "
                     "so none of its values are used anywhere in this analysis.")
    if has_missing:
        notes.append(explain.MISSING_NOTE)
    if has_zero:
        notes.append(explain.ZERO_NOTE)
    notes += [explain.EVENTS_NOTE, explain.NOT_CAUSAL_NOTE, explain.HEURISTIC_NOTE, explain.STRENGTH_NOTE]

    return {
        "insight_id": entry["insight_id"],
        "context": {
            "Gallery": f"{gallery_name(overview['gallery_id'])} ({overview['gallery_id']})",
            "Fair edition": f"{edition_label(overview['edition_id']).replace(' (', ' · ').rstrip(')')} "
                            f"({overview['edition_id']})",
            "Artwork": f"{metrics['artwork_title']} ({artwork_id})",
            "Artist": f"{metrics['artist_name']} ({metrics['artist_id']})",
            "Days analysed": ", ".join(explain.fmt_date_long(d) for d in overview["processed_dates"]),
            "Data source": f"{overview['source_file']} (validation {overview['validation']})",
        },
        "pattern_label": explain.CATEGORY_LABELS[pattern["category"]],
        "why_highlighted": explain.explain_pattern(pattern),
        "strength": insight["confidence"],
        "strength_text": explain.STRENGTH_TEXT[insight["confidence"]],
        "daily": daily,
        "comparison_dates": (kc["old_date"], kc["new_date"]) if kc else None,
        "comparison": comparison,
        "checks": checks,
        "verified_claims": [{"Claim checked": c["claim"], "Result": "✅ matches source" if c["verified"]
                             else "❌ mismatch"} for c in entry["checked_claims"]],
        "artist_context": (f"All artworks by {artist['artist_name']}: {artist_views['calculation']} artwork-view "
                           "events across the processed days (events, not people)."),
        "notes": notes,
    }
