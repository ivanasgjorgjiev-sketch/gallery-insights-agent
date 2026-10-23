"""Plain-language, deterministic explanations for a nontechnical Gallery Manager.

Everything here is generated from the deterministic tool outputs, never from LLM text,
so it is safe to show as fact in both LIVE and DEMO modes.
"""

from __future__ import annotations

import datetime as dt

from gia import tools

METRIC_NAMES = {
    "artwork_views": "Artwork views",
    "unique_artwork_viewers": "Daily unique viewers",
    "favourites": "Favourites",
    "inquiries": "Inquiries",
}

CATEGORY_LABELS = {
    "sustained_growth": "Sustained increase",
    "temporary_spike": "Temporary spike",
    "weak_signal": "Weak signal",
    "emerging_increase": "Recent increase (not yet confirmed)",
    "zero_baseline_change": "Increase from zero",
    "insufficient_evidence": "Not enough evidence",
    "stable": "Stable",
    "no_clear_pattern": "No clear pattern",
}

STRENGTH_LABELS = ["higher-confidence", "moderate-confidence", "qualified"]
STRENGTH_TEXT = {
    "higher-confidence": "The increase held on later days and at least two other measures rose with it.",
    "moderate-confidence": "The increase held on later days and one other measure rose with it.",
    "qualified": "Shown for awareness only. It does not meet the bar for sustained growth.",
}
STRENGTH_NOTE = ("Evidence strength is a qualitative screening assessment based on transparent rules, "
                 "not a statistical probability or confidence level.")

MISSING_NOTE = ("“Not recorded” means the value is blank in the source data. It is treated as unknown, "
                "never as zero, so any comparison that needs it is shown as unavailable.")
ZERO_NOTE = ("When a value starts at 0, a percentage increase cannot be calculated (it would be infinite), "
             "so only the change in numbers is shown.")
EVENTS_NOTE = ("Views, favourites and inquiries count actions, not people: one visitor can view an artwork "
               "several times. Daily unique viewers count people for one artwork on one day only and are "
               "never added up across days or artworks.")
NOT_CAUSAL_NOTE = ("The data shows what happened, not why. It does not show purchase intent, predict sales "
                   "or explain what caused a change.")
HEURISTIC_NOTE = "Patterns come from transparent screening rules, not statistical significance tests."

NOT_SURFACED_REASON = {
    "temporary_spike": "Not prioritised: a one-day jump that did not hold.",
    "weak_signal": "Not prioritised: the change is too small or not supported by other measures.",
    "emerging_increase": "Not prioritised yet: the increase is too recent to confirm.",
    "zero_baseline_change": "Not prioritised: a change from zero on small numbers is context, not a headline.",
    "insufficient_evidence": "Not prioritised: missing values prevent the pattern from being verified.",
    "stable": "Not an insight: engagement stayed steady.",
    "no_clear_pattern": "Not an insight: no screening rule was met.",
    "sustained_growth": "Not presented: no validated insight was produced for it in this analysis.",
}


def fmt_date(iso: str) -> str:
    d = dt.date.fromisoformat(iso)
    return f"{d.strftime('%b')} {d.day}"


def fmt_date_long(iso: str) -> str:
    d = dt.date.fromisoformat(iso)
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def fmt_value(v: int | None) -> str:
    return "not recorded" if v is None else str(v)


def change_text(cmp: dict) -> str:
    """Plain wording for a compare_values()-style result."""
    if cmp["status"] == "unavailable":
        return "cannot compare: a value is not recorded"
    if cmp["status"] == "zero_baseline":
        if cmp["absolute_change"] == 0:
            return "no change"
        return f"{cmp['absolute_change']:+d}; no percentage, because it started at 0"
    return f"{cmp['absolute_change']:+d}, {cmp['percentage_change']:+.1f}%"


def _cap(text: str) -> str:
    return text[:1].upper() + text[1:]


def _list(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def support_sentence(pattern: dict) -> str:
    """Which other measures did (or did not) support the key change, including unknown values."""
    qualifying, too_small, flat, unknown = [], [], [], []
    kc = pattern.get("key_comparison") or {}
    for s in pattern.get("supporting_metrics", []):
        name = METRIC_NAMES[s["metric"]]
        values = f"{fmt_value(s['old_value'])} → {fmt_value(s['new_value'])}"
        if s["qualifies_as_support"] is True:
            qualifying.append(f"{name.lower()} ({values})")
        elif s["qualifies_as_support"] is None:
            missing_day = kc.get("new_date") if s["new_value"] is None else kc.get("old_date")
            unknown.append(name.lower() + (f" on {fmt_date(missing_day)}" if missing_day else ""))
        elif s["new_value"] > s["old_value"]:
            too_small.append(f"{name.lower()} ({values})")
        else:
            flat.append(f"{name.lower()} ({values})")
    parts = []
    if qualifying:
        parts.append(f"{_cap(_list(qualifying))} also rose enough to count as support.")
    if too_small:
        parts.append(f"{_cap(_list(too_small))} rose, but too little to count.")
    if flat:
        parts.append(f"{_cap(_list(flat))} did not rise.")
    if unknown:
        parts.append(f"{_cap(_list(unknown))} is not recorded, so it cannot count either way.")
    return " ".join(parts)


def explain_pattern(pattern: dict) -> str:
    """One or two plain sentences describing what the screening rules found for an artwork."""
    cat = pattern["category"]
    values = [d["value"] for d in pattern["daily"]]
    series = ", ".join(fmt_value(v) for v in values)
    metric = METRIC_NAMES[pattern["metric"]].lower()
    kc = pattern.get("key_comparison")
    if cat == "stable":
        return f"{_cap(metric)} stayed steady ({series}): every day within 10% of the average."
    if cat == "no_clear_pattern":
        return f"{_cap(metric)} ({series}) did not meet any of the screening rules."
    if cat == "insufficient_evidence" and not kc:
        return f"Some {metric} values are not recorded ({series}), so a pattern cannot be verified."

    i = next(n for n, d in enumerate(pattern["daily"]) if d["date"] == kc["new_date"])
    later = ", ".join(fmt_value(v) for v in values[i + 1:])
    text = (f"{_cap(metric)} went from {fmt_value(kc['old_value'])} on {fmt_date(kc['old_date'])} to "
            f"{fmt_value(kc['new_value'])} on {fmt_date(kc['new_date'])} ({change_text(kc)}). ")
    failed = {c["rule"] for c in pattern["criteria"] if not c["passed"]}
    if cat == "sustained_growth":
        text += f"Later days ({later}) kept most of that increase. "
    elif cat == "temporary_spike":
        text += f"On later days it fell back close to the starting level ({later}), so it was a one-day jump. "
    elif cat == "zero_baseline_change":
        text += f"Later days: {later}. "
    elif cat == "emerging_increase":
        text += "It happened on the latest processed day, so it cannot be confirmed yet. "
    elif cat == "weak_signal":
        if "min_absolute_change" in failed:
            minimum = tools.PATTERN_RULES["min_absolute_change"][pattern["metric"]]
            text += f"That is only {kc['absolute_change']:+d}, below the {minimum} needed to count as meaningful. "
        elif "min_gain_retained" in failed:
            text += f"The increase held on some later days but not others ({later}). "
        else:
            text += "No other measure rose enough to support it. "
    elif cat == "insufficient_evidence":
        text += "Other measures needed to confirm it are not recorded. "
    return (text + support_sentence(pattern)).strip()


def short_rationale(pattern: dict) -> str:
    """A concise, deterministic reason for a card. The tiles already show the numbers, so this avoids
    repeating them and only says what makes the pattern notable (or not)."""
    cat = pattern["category"]
    kc = pattern.get("key_comparison")
    values = [d["value"] for d in pattern["daily"]]
    later = ""
    if kc:
        i = next(n for n, d in enumerate(pattern["daily"]) if d["date"] == kc["new_date"])
        later = ", ".join(fmt_value(v) for v in values[i + 1:])
    supports = [METRIC_NAMES[s["metric"]].lower() for s in pattern.get("supporting_metrics", [])
                if s["qualifies_as_support"]]
    if cat == "sustained_growth":
        return (f"The increase held on later days ({later})"
                + (f" and {_list(supports)} rose with it." if supports else "."))
    if cat == "temporary_spike":
        return f"It fell back close to the starting level on later days ({later}), so it was a one-day jump, not a trend."
    if cat == "zero_baseline_change":
        return "It started from zero, so only the change in numbers is meaningful, not a percentage."
    return explain_pattern(pattern)


def not_surfaced(published_artworks: set[str]) -> list[dict]:
    """Deterministic explanation for every artwork that is not a published insight."""
    out = []
    for p in tools.detect_engagement_patterns()["patterns"]:
        if p["artwork_id"] in published_artworks:
            continue
        out.append({"artwork_id": p["artwork_id"], "artwork_title": p["artwork_title"],
                    "category": p["category"], "label": CATEGORY_LABELS[p["category"]],
                    "explanation": explain_pattern(p), "why_not_shown": NOT_SURFACED_REASON[p["category"]]})
    return out


def overview(published: list[dict], processed_dates: list[str], excluded_dates: list[str]) -> str:
    """Deterministic one-paragraph summary of an analysis (replaces the model's free-text summary)."""
    counts = {s: sum(1 for p in published if p["insight"]["confidence"] == s) for s in STRENGTH_LABELS}
    found = [f"{counts[s]} {s}" for s in STRENGTH_LABELS if counts[s]]
    text = (f"Analysed {len(processed_dates)} processed fair days "
            f"({fmt_date(processed_dates[0])}–{fmt_date(processed_dates[-1])}). ")
    if excluded_dates:
        text += f"{_list([fmt_date(d) for d in excluded_dates])} excluded because it is not processed yet. "
    text += (f"Validated insights: {_list(found)}." if found else "No finding met the evidence bar.")
    return text
