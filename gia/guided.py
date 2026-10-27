"""Guided insight exploration (Milestone 8): four deterministic questions for each validated insight.

Relevance → Trend → Confidence → Next investigation. Every answer is built from the insight's
deterministic pattern (recomputed by the tools, never taken from model text), so it is identical in
LIVE and DEMO mode and needs no API call. Before display each answer is checked like any other text:
its figures are recomputed with the tools and checked in context, and it must contain no prohibited
claim, commercial action or cause-seeking step. An answer that fails is not shown ("fail closed").
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from gia import explain, grounding, tools

QUESTIONS = [
    ("relevance", "What makes this insight worth my attention?"),
    ("trend", "How did engagement evolve over the fair?"),
    ("signals", "What other signals support—or challenge—this pattern?"),
    ("next", "What should I look into next?"),
]
UNAVAILABLE = "This explanation is unavailable because it could not be verified against the source data."
COUNT_WORDS = {0: "no", 1: "one", 2: "two", 3: "three"}
METRIC_TEXT = {"artwork_views": "views", "unique_artwork_viewers": "daily unique viewers",
               "favourites": "favourites", "inquiries": "inquiries"}


@dataclass
class GuidedAnswer:
    question_id: str
    question: str
    text: str = ""
    facts: list[grounding.Fact] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def shown(self) -> bool:
        return bool(self.text) and not self.problems


# --- Small formatting helpers -----------------------------------------------------------

def _d(iso: str) -> str:
    return explain.fmt_date(iso)


def _signed(n: int) -> str:
    return f"{n:+d}".replace("-", "−")


def _pct(p: float) -> str:
    return f"{p:+.0f}%" if p == int(p) else f"{p:+.1f}%"


def _rise_pct(p: float) -> str:
    return f"{p:.0f}%" if p == int(p) else f"{p:.1f}%"


def _change(cmp: dict) -> str:
    """"+15, +50%" (no percentage from zero)."""
    if cmp["status"] == "ok":
        return f"{_signed(cmp['absolute_change'])}, {_pct(cmp['percentage_change'])}"
    return _signed(cmp["absolute_change"])


class _Ctx:
    """Everything one insight's answers draw on, plus the facts they state (checked before display)."""

    def __init__(self, entry: dict):
        self.pattern = entry["pattern"]
        self.metric = self.pattern["metric"]
        self.name = METRIC_TEXT[self.metric]
        self.subject = self.pattern["artwork_id"]
        self.daily = [(d["date"], d["value"]) for d in self.pattern["daily"]]
        self.kc = self.pattern.get("key_comparison")
        self.category = self.pattern["category"]
        self.failed = {c["rule"] for c in self.pattern["criteria"] if not c["passed"]}
        self.support = self.pattern.get("supporting_metrics", [])
        self.rules = tools.PATTERN_RULES
        self.facts: list[grounding.Fact] = []

    def fact(self, metric: str, measure: str, value: float, start: str, end: str = "") -> None:
        self.facts.append(grounding.Fact(self.subject, metric, measure, value, start, end))

    def value(self, metric: str, date: str, value: int | None) -> None:
        if value is None:
            self.fact(metric, "missing", 0, date)
        else:
            self.fact(metric, "value", value, date)

    def comparison(self, metric: str, old_date: str, new_date: str, cmp: dict) -> None:
        if cmp["status"] == "unavailable":
            return
        self.fact(metric, "change", cmp["absolute_change"], old_date, new_date)
        if cmp["percentage_change"] is not None:
            self.fact(metric, "percent_change", cmp["percentage_change"], old_date, new_date)

    def key(self) -> tuple[str, str, int, int, dict]:
        kc = self.kc
        self.value(self.metric, kc["old_date"], kc["old_value"])
        self.value(self.metric, kc["new_date"], kc["new_value"])
        self.comparison(self.metric, kc["old_date"], kc["new_date"], kc)
        return kc["old_date"], kc["new_date"], kc["old_value"], kc["new_value"], kc

    def later(self) -> list[tuple[str, int | None]]:
        i = next(n for n, (d, _) in enumerate(self.daily) if d == self.kc["new_date"])
        return self.daily[i + 1:]

    def minimum(self) -> int:
        return self.rules["min_absolute_change"][self.metric]

    def grouped_support(self) -> dict[str, list[dict]]:
        groups = {"qualifying": [], "too_small": [], "flat": [], "unknown": []}
        for s in self.support:
            if s["qualifies_as_support"] is True:
                groups["qualifying"].append(s)
            elif s["qualifies_as_support"] is None:
                groups["unknown"].append(s)
            elif s["new_value"] > s["old_value"]:
                groups["too_small"].append(s)
            else:
                groups["flat"].append(s)
        return groups


# --- Q1: relevance ----------------------------------------------------------------------------

def _relevance(c: _Ctx) -> str:
    old_d, new_d, old, new, kc = c.key()
    min_pct, min_abs = c.rules["min_increase_pct"], c.minimum()
    qualifying = len(c.grouped_support()["qualifying"])
    if c.category == "zero_baseline_change":
        first = c.daily[0][0]
        return (f"{c.name.capitalize()} went from {old} on {_d(old_d)}"
                + (", the first processed day," if old_d == first else "") + f" to {new} on {_d(new_d)}. "
                f"Because it started at zero, a percentage would be meaningless, so the change is judged by its "
                f"absolute size alone. Within the processed days this is a move from zero {c.name} to a small "
                f"number, which is why it is shown for awareness rather than as growth.")
    rise = (f"{c.name.capitalize()} rose {_rise_pct(kc['percentage_change'])} in one day, from {old} on {_d(old_d)} "
            f"to {new} on {_d(new_d)}")
    if c.category == "sustained_growth":
        backers = explain._list([METRIC_TEXT[s["metric"]] for s in c.grouped_support()["qualifying"]])
        if qualifying >= 2:
            doubled = kc["new_value"] == 2 * kc["old_value"]
            return (f"{c.name.capitalize()} {'doubled' if doubled else 'rose sharply'} in a single day, from {old} "
                    f"on {_d(old_d)} to {new} on {_d(new_d)}, and stayed at around that higher level for the rest "
                    f"of the processed days. {COUNT_WORDS[qualifying].capitalize()} other measures, {backers}, rose "
                    f"on the same day, so the increase does not rest on {c.name} alone. That combination of size, "
                    f"persistence and support is what gives this insight its higher-confidence rating.")
        return (f"{rise}, and stayed above their {_d(old_d)} level on every later processed day. Only one other "
                f"measure, {backers}, rose enough to back it up. So this is a sustained increase with limited "
                f"supporting evidence, which is why it is rated moderate-confidence.")
    if c.category == "temporary_spike":
        return (f"{rise}. On its own, a jump of {_signed(kc['absolute_change'])} is large enough to pass the "
                f"screening minimums, so it is worth knowing about. It did not last, so it is shown for awareness, "
                f"not as growth.")
    if c.category == "emerging_increase":
        return (f"{rise}, enough to pass the screening minimums. It happened on the latest processed day, so "
                f"there is no later day yet to show whether it holds. That is why it is shown as an early, "
                f"unconfirmed signal rather than as growth.")
    if c.category == "insufficient_evidence":
        unknown = c.grouped_support()["unknown"]
        names = explain._list([METRIC_TEXT[s["metric"]] for s in unknown])
        day = new_d if unknown and unknown[0]["new_value"] is None else old_d
        for s in unknown:
            c.value(s["metric"], day, None)
        return (f"{rise}, and the higher level held on the later processed days. That would normally make it a "
                f"candidate, but {names} are not recorded for {_d(day)}, so the rules cannot check whether other "
                f"measures back it up. It is shown for awareness only.")
    # weak_signal
    if "min_absolute_change" in c.failed:
        return (f"A {_rise_pct(kc['percentage_change'])} rise sounds large, but a percentage depends on the starting "
                f"point: with only {old} {c.name} on {_d(old_d)}, a handful more on {_d(new_d)} is already a big "
                f"share. That is why the rules also require a rise of at least {min_abs} {c.name}, so small numbers "
                f"do not look like big trends. This change is shown for awareness, not as a pattern.")
    if "min_gain_retained" in c.failed:
        return (f"{rise}, but the higher level held on some later days and not others. An uneven pattern like "
                f"this is shown for awareness, not as growth.")
    return (f"{rise} and held on later days, but no other measure rose enough to back it up, so it is shown "
            f"for awareness rather than as growth.")


# --- Q2: trend of the primary metric -------------------------------------------------------------

def _trend(c: _Ctx) -> str:
    for d, v in c.daily:
        c.value(c.metric, d, v)
    series = ", ".join(f"{_d(d)}: {explain.fmt_value(v)}" for d, v in c.daily)
    steps = []
    for (d0, v0), (d1, v1) in zip(c.daily, c.daily[1:]):
        cmp = tools.compare_values(v0, v1)
        if cmp["status"] == "unavailable":
            steps.append(f"no comparison for {_d(d1)} (a value is not recorded)")
            continue
        c.comparison(c.metric, d0, d1, cmp)
        steps.append("no change on " + _d(d1) if cmp["absolute_change"] == 0
                     else f"{_signed(cmp['absolute_change'])} on {_d(d1)}")
    text = f"{c.name.capitalize()} by day: {series}. Day to day: {'; '.join(steps)}."
    known = [(d, v) for d, v in c.daily if v is not None]
    top_d, top_v = max(known, key=lambda x: x[1])
    old_d, new_d = c.kc["old_date"], c.kc["new_date"]
    if c.category in ("sustained_growth", "insufficient_evidence"):
        text += f" The level reached on {_d(new_d)} held on every later day, and the highest day was {_d(top_d)}."
    elif c.category == "temporary_spike":
        last_d, last_v = c.daily[-1]
        text += (f" The jump on {_d(new_d)} did not last: by {_d(last_d)} {c.name} were back near the "
                 f"starting level of {c.kc['old_value']} on {_d(old_d)}.")
    elif c.category == "zero_baseline_change":
        text += " Because it started at zero, only the size of each change is shown, not percentages."
    elif c.category == "emerging_increase":
        text += f" The rise came on {_d(new_d)}, the latest processed day, so there is no later day to compare yet."
    elif "min_absolute_change" in c.failed:
        text += f" The highest day was {_d(top_d)}, and the level moved by only a few {c.name} across the fair."
    else:
        text += f" The highest day was {_d(top_d)}."
    return text


# --- Q3: supporting and challenging signals -------------------------------------------------------

def _signals(c: _Ctx) -> str:
    old_d, new_d, old, new, kc = c.key()
    groups = c.grouped_support()
    lines = []

    def described(s: dict) -> str:
        c.value(s["metric"], old_d, s["old_value"])
        c.value(s["metric"], new_d, s["new_value"])
        c.comparison(s["metric"], old_d, new_d, s)
        return f"{METRIC_TEXT[s['metric']]} rose from {s['old_value']} to {s['new_value']} ({_change(s)})"

    period = f"({_d(old_d)} → {_d(new_d)})"
    if groups["qualifying"]:
        parts = explain._list([described(s) for s in groups["qualifying"]])
        lines.append(f"- **Supports it** {period}: {parts}. "
                     f"{'Both are' if len(groups['qualifying']) > 1 else 'That is'} enough to count.")
    else:
        lines.append(f"- **Supports it** {period}: no other measure rose enough to count.")
    weak = []
    for s in groups["too_small"]:
        c.value(s["metric"], old_d, s["old_value"])
        c.value(s["metric"], new_d, s["new_value"])
        c.comparison(s["metric"], old_d, new_d, s)
        minimum = c.rules["min_absolute_change"][s["metric"]]
        weak.append(f"{METRIC_TEXT[s['metric']]} rose only from {s['old_value']} to {s['new_value']} "
                    f"({_signed(s['absolute_change'])}), short of the minimum rise of {minimum}")
    for s in groups["flat"]:
        c.value(s["metric"], old_d, s["old_value"])
        c.value(s["metric"], new_d, s["new_value"])
        weak.append(f"{METRIC_TEXT[s['metric']]} did not rise ({s['old_value']} on both days)"
                    if s["old_value"] == s["new_value"] else
                    f"{METRIC_TEXT[s['metric']]} did not rise ({s['old_value']} to {s['new_value']})")
    for s in groups["unknown"]:
        day = new_d if s["new_value"] is None else old_d
        c.value(s["metric"], day, None)
        weak.append(f"{METRIC_TEXT[s['metric']]} are not recorded for {_d(day)}, so that value is unknown "
                    f"(not zero) and cannot count either way")
    if weak:
        lines.append(f"- **Weak or missing** {period}: " + "; ".join(weak) + ".")

    # "Against it" is evidence that contradicts the pattern; "What limits confidence" is a check that could not
    # pass because evidence is small, missing or not yet available. Neither is ever invented.
    against, limits = [], []
    if "min_gain_retained" in c.failed:
        later = c.later()
        for d, v in later:
            c.value(c.metric, d, v)
        c.value(c.metric, old_d, old)
        c.value(c.metric, new_d, new)
        vals = " and ".join(f"{v} on {_d(d)}" for d, v in later)
        against.append(f"{c.name} fell to {vals}, close to the starting level of {old} on {_d(old_d)} rather "
                       f"than staying near the peak of {new} on {_d(new_d)}, so the jump did not hold")
    if "min_absolute_change" in c.failed:
        limits.append(f"the rise in {c.name} ({_signed(kc['absolute_change'])}) is below the minimum of "
                      f"{c.minimum()}")
    if "min_later_days" in c.failed:
        limits.append(f"there are no processed days after {_d(new_d)}, so the rules cannot yet test whether "
                      f"the rise holds")
    if "corroboration" in c.failed:
        outcome = "none did or could be checked" if groups["unknown"] else "none did"
        limits.append(f"the corroboration check could not pass: it needs at least one other measure to rise "
                      f"enough on the same day, and {outcome}. This is missing or insufficient support, not "
                      f"evidence against the pattern")
    if against:
        lines.append("- **Against it:** " + "; ".join(against) + ".")
    if limits:
        lines.append("- **What limits confidence:** " + "; ".join(limits) + ".")
    if not against and not limits:
        lines.append("- **Against it:** none of the screening checks found evidence against this pattern.")
    return "\n".join(lines)


# --- Q4: a specific, human-controlled next investigation -------------------------------------------

def _next(c: _Ctx) -> str:
    old_d, new_d = c.kc["old_date"], c.kc["new_date"]
    groups = c.grouped_support()
    qualifying = explain._list([METRIC_TEXT[s["metric"]] for s in groups["qualifying"]]) if groups["qualifying"] \
        else ""
    thin = explain._list([METRIC_TEXT[s["metric"]] for s in groups["too_small"] + groups["flat"]]) \
        if groups["too_small"] + groups["flat"] else ""
    if c.category == "sustained_growth" and len(groups["qualifying"]) >= 2:
        return (f"Open View evidence and read the daily table for the days after {_d(new_d)}. Check whether "
                f"{qualifying} also stayed above their {_d(old_d)} levels, not just {c.name}. That shows whether "
                f"the supporting measures held up as well as the main one did.")
    later_days = explain._list([_d(d) for d, _ in c.later()]) if c.later() else ""
    if c.category == "sustained_growth":
        return (f"Open View evidence and look at {thin} on {later_days}. They did not rise enough on {_d(new_d)} "
                f"to count as support, so check whether either of them rose on the later days. That shows whether "
                f"the support for this increase stayed limited to one measure throughout the fair.")
    if c.category == "temporary_spike":
        rose = [METRIC_TEXT[s["metric"]] for s in c.support
                if s["old_value"] is not None and s["new_value"] is not None and s["new_value"] > s["old_value"]]
        measures = explain._list(rose) if rose else "the other measures"
        return (f"Open View evidence and look at {measures} on {later_days}. Check whether "
                f"{'either' if len(rose) == 2 else 'any'} of them stayed above {'its' if len(rose) == 1 else 'their'} "
                f"{_d(old_d)} level after {c.name} fell back. That shows whether anything besides the one-day jump "
                f"in {c.name} lasted; it does not change how the pattern is classified.")
    if c.category == "zero_baseline_change":
        return ("Open View evidence and read the absolute numbers day by day. Decide whether changes of this size "
                "are large enough to matter for your review before giving this insight weight.")
    if c.category == "emerging_increase":
        excluded = _excluded()
        text = (f"Open View evidence and look at all four measures on {_d(new_d)}, the latest processed day. "
                f"Treat this as unconfirmed for now")
        if excluded:   # mentioned only as excluded, never as something to reanalyse
            return text + f": {explain._list([_d(d) for d in excluded])} is not processed yet and is excluded."
        return text + "."
    unknown = groups["unknown"]
    if unknown:
        names = explain._list([METRIC_TEXT[s["metric"]] for s in unknown])
        day = new_d if unknown[0]["new_value"] is None else old_d
        return (f"Open View evidence and read the other measures for {_d(day)}. Because {names} are not "
                f"recorded that day, judge the pattern on the measures that are, and treat the missing value as "
                f"unknown rather than zero.")
    return (f"Open View evidence and check whether any other measure moved more clearly than {c.name} did. If "
            f"none did, this is unlikely to need more of your time.")


def _excluded() -> list[str]:
    return [e["date"] for e in tools.get_processed_data()["excluded_dates"]]


BUILDERS = {"relevance": _relevance, "trend": _trend, "signals": _signals, "next": _next}


# --- Checking and the public API ------------------------------------------------------------------

EXCLUDED_CONTEXT = re.compile(r"excluded|not processed", re.IGNORECASE)


def date_problems(text: str, data: grounding._Data | None = None) -> list[str]:
    """Dates must be processed fair days; an excluded day may appear only where it is called excluded or
    not processed, even without a number next to it ("Views on Oct 18 were higher" is rejected)."""
    data = data or grounding._Data()
    processed = data.overview["processed_dates"]
    excluded = [e["date"] for e in data.overview["excluded_dates"]]
    problems = []
    for sentence in grounding.SENTENCE_SPLIT.split(text):
        for _, iso, _ in grounding._dates_in(sentence, processed[0][:4], frozenset(processed) | frozenset(excluded)):
            if iso in excluded and not EXCLUDED_CONTEXT.search(sentence):
                problems.append(f"the excluded date {iso} is used as data")
            elif iso not in processed and iso not in excluded:
                problems.append(f"{iso} is not a processed fair date")
    return problems


def check(text: str, facts: list[grounding.Fact], question_id: str,
          data: grounding._Data | None = None) -> list[str]:
    """The same checks as any shown text: every stated fact recomputed with the tools, every number in
    context, no prohibited claims or commercial actions, and no cause-seeking in the next investigation."""
    data = data or grounding._Data()
    problems = [f"fact does not match the data: {r}" for r in
                (grounding.verify_fact(f, data) for f in facts) if r]
    problems += grounding.check_text(text, facts, data=data)
    problems += date_problems(text, data)
    for pattern, label in tools.PROHIBITED_CLAIMS:
        problems += [f"unsupported {label} ('{h}')" for h in tools._asserted(pattern, text)]
    problems += [f"commercial action ('{h}')" for h in tools._asserted(tools.PROHIBITED_ACTIONS, text)]
    if question_id == "next":
        problems += [f"cause-seeking step ('{h}')" for h in tools._asserted(tools.CAUSE_SEEKING_STEP, text)]
    return problems


PATTERN_FIELDS = ("category", "evidence_strength", "metric", "daily", "key_comparison", "supporting_metrics",
                  "criteria")


def _matches_source(pattern: dict) -> bool:
    """The wording depends on the classification, so the insight's pattern must still be exactly what the
    tools compute now (guards against stale or altered data, not just wrong numbers)."""
    fresh = tools.detect_engagement_patterns(pattern["metric"], [pattern["artwork_id"]])["patterns"][0]
    return all(fresh.get(k) == pattern.get(k) for k in PATTERN_FIELDS)


def answer(entry: dict, question_id: str, data: grounding._Data | None = None) -> GuidedAnswer:
    """One guided answer for a validated insight. Never raises: a problem means the answer is not shown."""
    question = dict(QUESTIONS)[question_id]
    try:
        ctx = _Ctx(entry)
        if not ctx.kc:
            return GuidedAnswer(question_id, question, problems=["the insight has no key comparison"])
        if not _matches_source(entry["pattern"]):
            return GuidedAnswer(question_id, question,
                                problems=["the insight's pattern does not match the source data"])
        text = BUILDERS[question_id](ctx)
    except Exception as e:   # malformed pattern: fail closed
        return GuidedAnswer(question_id, question, problems=[f"could not be generated ({type(e).__name__})"])
    return GuidedAnswer(question_id, question, text, ctx.facts, check(text, ctx.facts, question_id, data))


def answers(entry: dict) -> list[GuidedAnswer]:
    data = grounding._Data()
    return [answer(entry, qid, data) for qid, _ in QUESTIONS]
