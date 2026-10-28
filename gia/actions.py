"""Suggested follow-up for each validated insight (Milestone 10): rule-based and evidence-driven.

One short, human-consideration-only suggestion per published insight: what the manager might do with the
insight, not what to check in the data (that is the guided "What should I look into next?" answer). A rule is
chosen only from the validated evidence: the pattern category, the evidence strength, which supporting measures
qualified, rose too little, did not rise or are missing, and which screening criteria failed. Artwork IDs, titles
and artist names never select a rule, so the same evidence always leads to the same kind of suggestion. Metric
names in the text come from the pattern; no figure or date is stated.

Three outcomes, kept apart:
- "suggestion": a contextual follow-up the evidence supports;
- "no_specific": the evidence is valid but does not support a specific follow-up (a neutral explanation);
- "unavailable": a validation check failed, so nothing is shown (fail closed).
Everything shown passes the same checks as the guided answers (pattern recomputed from the source, prohibited
claims, commercial actions, cause-seeking). No API call is made.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from gia import explain, guided

HEADING = "Suggested follow-up"
NOTE = "No action taken automatically"
UNAVAILABLE = "A suggested follow-up is unavailable because it could not be verified against the source data."
NO_SPECIFIC = "The available evidence does not support a specific follow-up suggestion"

SPIKE_TEXT = ("No immediate follow-up is suggested based on this temporary spike. Revisit the pattern if a new "
              "increase appears in subsequent data.")
RECENT_TEXT = ("This increase is worth monitoring, but there is not yet enough processed data to determine "
               "whether it will continue.")
ZERO_TEXT = ("Treat this as context rather than a trend, because it started from zero. Revisit it only if the "
             "increase continues in later processed data.")
# Why a weak signal supports no specific follow-up, by the first failed screening criterion.
WEAK_REASONS = [
    ("min_absolute_change", "the change is too small to count under the screening rules"),
    ("min_gain_retained", "the higher level held on some later days and not others"),
    ("corroboration", "no other measure rose enough to back it up"),
]


@dataclass
class FollowUp:
    text: str = ""
    rule: str = ""
    kind: str = ""                     # suggestion | no_specific | unavailable
    problems: list[str] = field(default_factory=list)

    @property
    def shown(self) -> bool:
        return bool(self.text) and not self.problems


class _Evidence:
    """The validated evidence a rule may use: category, strength, support groups and failed criteria."""

    def __init__(self, c: guided._Ctx, strength: str):
        groups = c.grouped_support()
        self.category, self.strength, self.metric = c.category, strength, c.name
        self.qualifying = [guided.METRIC_TEXT[s["metric"]] for s in groups["qualifying"]]
        self.rose_slightly = [guided.METRIC_TEXT[s["metric"]] for s in groups["too_small"]]   # rose, below minimum
        self.no_rise = [guided.METRIC_TEXT[s["metric"]] for s in groups["flat"]]               # did not increase
        self.weak = self.rose_slightly + self.no_rise
        self.missing = [guided.METRIC_TEXT[s["metric"]] for s in groups["unknown"]]
        both = all(s["old_value"] is None and s["new_value"] is None for s in groups["unknown"])
        self.missing_when = "on both comparison days" if both else "on one of the comparison days"
        self.failed = c.failed


def _names(items: list[str]) -> str:
    return explain._list(items)


def _monitor_continuation(ev: _Evidence) -> str:
    return (f"Consider keeping this artwork in view during the remaining fair days. {ev.metric.capitalize()} "
            f"increased and stayed elevated, with supporting increases in {_names(ev.qualifying)}. Review the next "
            f"processed day to see whether that pattern continues.")


def _cautious_monitoring(ev: _Evidence) -> str:
    # Each other measure is described as it is: a small rise is "limited additional support", no rise is "did not
    # increase", and a missing value is "not recorded" (never zero).
    limits = []
    if ev.rose_slightly:
        limits.append(f"{_names(ev.rose_slightly)} provide limited additional support")
    if ev.no_rise:
        limits.append(f"{_names(ev.no_rise)} did not increase")
    if ev.missing:
        limits.append(f"{_names(ev.missing)} are not recorded {ev.missing_when}")
    limit = _names(limits) if limits else "no other measure adds support"
    backer = _names(ev.qualifying)
    return (f"Keep this artwork on your watch list as a possible sustained increase. {backer[:1].upper()}"
            f"{backer[1:]} support the pattern, while {limit}. Reassess when more daily data is available.")


def _no_specific(ev: _Evidence) -> str:
    if ev.category == "insufficient_evidence" and ev.missing:
        return f"{NO_SPECIFIC}, because {_names(ev.missing)} are not recorded {ev.missing_when}."
    reason = next((text for rule, text in WEAK_REASONS if rule in ev.failed), None)
    return f"{NO_SPECIFIC}: {reason}." if reason else f"{NO_SPECIFIC}."


# The rule matrix: (name, kind, applies-to-the-evidence, wording). The first matching rule wins.
RULES = [
    ("monitor_continuation", "suggestion",
     lambda ev: ev.category == "sustained_growth" and ev.strength == "higher-confidence" and len(ev.qualifying) >= 2,
     _monitor_continuation),
    ("cautious_monitoring", "suggestion",
     lambda ev: ev.category == "sustained_growth" and ev.strength == "moderate-confidence" and len(ev.qualifying) == 1,
     _cautious_monitoring),
    ("recurrence_watch", "suggestion",
     lambda ev: ev.category == "temporary_spike" and ev.strength == "qualified",
     lambda ev: SPIKE_TEXT),
    ("await_later_day", "suggestion",
     lambda ev: ev.category == "emerging_increase" and ev.strength == "qualified" and "min_later_days" in ev.failed,
     lambda ev: RECENT_TEXT),
    ("context_only", "suggestion",
     lambda ev: ev.category == "zero_baseline_change" and ev.strength == "qualified",
     lambda ev: ZERO_TEXT),
    ("insufficient_evidence", "no_specific",
     lambda ev: ev.category in ("insufficient_evidence", "weak_signal") and ev.strength == "qualified",
     _no_specific),
]
# A sustained increase whose support does not match its rating is inconsistent evidence, not a gap in the rules.
INCONSISTENT = {"sustained_growth"}


def suggest(entry: dict, data=None) -> FollowUp:
    """The suggested follow-up for one validated insight. Never raises: a problem means it is not shown."""
    try:
        pattern = entry["pattern"]
        if not guided._matches_source(pattern):
            return FollowUp(kind="unavailable", problems=["the insight's pattern does not match the source data"])
        strength = entry["insight"]["confidence"]
        if strength != (pattern["evidence_strength"] or "qualified"):
            return FollowUp(kind="unavailable", problems=["the insight's evidence rating does not match its pattern"])
        c = guided._Ctx(entry)
        ev = _Evidence(c, strength)
    except Exception as e:   # malformed pattern: fail closed
        return FollowUp(kind="unavailable", problems=[f"could not be checked ({type(e).__name__})"])
    rule = next((r for r in RULES if r[2](ev)), None)
    if rule is None:
        if ev.category in INCONSISTENT:
            return FollowUp(kind="unavailable",
                            problems=[f"the supporting evidence does not match a {strength} {ev.category} pattern"])
        name, kind, text = "no_rule", "no_specific", f"{NO_SPECIFIC}."   # unknown combination: neutral, not generic
    else:
        name, kind, _, wording = rule
        text = wording(ev)
    problems = guided.check(text, c.facts, "next", data)
    return FollowUp(text, name, "unavailable" if problems else kind, problems)
