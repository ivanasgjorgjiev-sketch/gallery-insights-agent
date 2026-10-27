"""Presentation helpers for the M9 interface: compact cards, the daily trend chart and the evidence summary.

Everything is derived from the insight's validated pattern and the deterministic tool output (the same
data View evidence uses), never from new model text, so LIVE and DEMO show identical content and nothing
here makes an API call. These helpers only reshape verified values for display; they change no claim.
"""

from __future__ import annotations

from gia import explain, tools

# Supporting-measure labels: what each validated status means, without implying contradiction.
SUPPORT_STATUS = {
    "supports": ("✓", "Supports"),                 # rose enough on the same day to count
    "insufficient": ("–", "Rose, too little to count"),
    "no_rise": ("–", "No rise"),
    "missing": ("?", "Not recorded"),
}
SUPPORT_HELP = ("Other measures on the same two days. “Supports” means it rose enough to count under the "
                "screening rules; “too little” and “no rise” mean it did not add support (this is not evidence "
                "against the pattern); “not recorded” means the value is unknown, never zero.")


def _status(s: dict) -> str:
    if s["qualifies_as_support"] is True:
        return "supports"
    if s["qualifies_as_support"] is None:
        return "missing"
    return "insufficient" if s["new_value"] > s["old_value"] else "no_rise"


def _delta(cmp: dict) -> str | None:
    """The verified change as tile text: a percentage only where it is defined (no percentage from zero,
    nothing when a value is missing or nothing changed)."""
    if cmp["status"] == "unavailable" or cmp["absolute_change"] == 0:
        return None
    if cmp["status"] == "zero_baseline":
        return f"{cmp['absolute_change']:+d} (from 0)"
    return f"{cmp['percentage_change']:+.1f}%"


def primary_change(pattern: dict) -> dict | None:
    """The key comparison of the primary metric, ready for a metric tile."""
    kc = pattern.get("key_comparison")
    if not kc:
        return None
    return {"label": explain.METRIC_NAMES[pattern["metric"]],
            "value": f"{explain.fmt_value(kc['old_value'])} → {explain.fmt_value(kc['new_value'])}",
            "delta": _delta(kc),
            "period": f"{explain.fmt_date(kc['old_date'])} → {explain.fmt_date(kc['new_date'])}"}


def metric_tiles(pattern: dict) -> list[dict]:
    """Four tiles in a fixed order (the primary metric first, then each supporting measure) with the verified
    values on the key-comparison days, the change, and the existing support classification. Every tile shows a
    change line ("no change" / "no comparison" when there is no figure) so the tiles stay aligned."""
    main = primary_change(pattern)
    if not main:
        return []
    tiles = [{**main, "delta": main["delta"] or "no change", "status": "key", "note": "Key change",
              "delta_color": "normal",
              "help": f"The change the insight is about ({main['period']})."}]
    for s in pattern.get("supporting_metrics", []):
        status = _status(s)
        icon, label = SUPPORT_STATUS[status]
        tiles.append({"label": explain.METRIC_NAMES[s["metric"]],
                      "value": f"{explain.fmt_value(s['old_value'])} → {explain.fmt_value(s['new_value'])}",
                      "delta": _delta(s) or ("no comparison" if status == "missing" else "no change"),
                      "delta_color": "normal" if status == "supports" else "off",
                      "status": status, "note": f"{icon} {label}",
                      "help": (explain.MISSING_NOTE if status == "missing" else
                               explain.ZERO_NOTE if s["status"] == "zero_baseline" and s["absolute_change"] else
                               SUPPORT_HELP) + f" Compared on the same days as the key change ({main['period']})."})
    return tiles


def trend_points(pattern: dict) -> list[dict]:
    """Daily values of the primary metric for the processed days only (the pattern never contains an
    excluded day). A missing value stays None so the chart shows a gap, never a zero."""
    kc = pattern.get("key_comparison") or {}
    points = []
    for d in pattern["daily"]:
        role = "jump" if d["date"] == kc.get("new_date") else "start" if d["date"] == kc.get("old_date") else "day"
        points.append({"date": d["date"], "day": explain.fmt_date(d["date"]), "value": d["value"], "role": role})
    return points


def evidence_summary(entry: dict, ev: dict) -> dict:
    """The manager-friendly first level of View evidence, built from the same evidence as the details."""
    insight, pattern = entry["insight"], entry["pattern"]
    kc = pattern.get("key_comparison")
    overview = tools.get_processed_data()
    days = overview["processed_dates"]
    lines = [f"**Source:** {ev['context']['Data source']} · {len(days)} processed days "
             f"({explain.fmt_date(days[0])}–{explain.fmt_date(days[-1])}) · {ev['context']['Artwork']} · "
             f"{ev['context']['Artist']}"]
    if kc:
        lines.append(f"**Key change:** {explain.METRIC_NAMES[pattern['metric']].lower()} went from "
                     f"{explain.fmt_value(kc['old_value'])} on {explain.fmt_date_long(kc['old_date'])} to "
                     f"{explain.fmt_value(kc['new_value'])} on {explain.fmt_date_long(kc['new_date'])} "
                     f"({explain.change_text(kc)}).")
    checked = entry.get("checked_claims", [])
    verified = sum(1 for c in checked if c["verified"])
    lines.append(f"**Checked against the source:** {'the' if len(checked) == 1 else f'all {len(checked)}'} "
                 f"figure{' in this insight matches' if len(checked) == 1 else 's in this insight match'} "
                 "the source records ✅"
                 if checked and verified == len(checked) else
                 f"**Checked against the source:** {verified} of {len(checked)} figures match.")
    notes = []
    excluded = [explain.fmt_date_long(e["date"]) for e in overview["excluded_dates"]]
    if excluded:
        notes.append(f"{', '.join(excluded)} is excluded because it is not processed yet; none of its values are used.")
    if any(c.get("status") == "unavailable" for c in [kc or {}, *pattern.get("supporting_metrics", [])]):
        notes.append(explain.MISSING_NOTE)
    if any(c.get("status") == "zero_baseline" and c.get("absolute_change") for c in
           [kc or {}, *pattern.get("supporting_metrics", [])]):
        notes.append(explain.ZERO_NOTE)
    return {"lines": lines, "notes": notes, "agent_description": insight["observed_signal"],
            "next_step": insight.get("suggested_next_step") or "",
            "next_step_replaced": bool(entry.get("next_step_substitution")),
            "insight_id": entry["insight_id"]}


def run_summary(result) -> str:
    """One line describing how the agent worked, for the collapsed process section."""
    withheld = len(result.withheld) if not result.replayed else (result.withheld_count or 0)
    return (f"{result.model_turns} Claude turns · {result.tool_calls} tool calls · "
            f"{len(result.published)} validated, {withheld} withheld")
