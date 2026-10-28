"""Daily engagement briefing (Milestone 10): a compact summary above the insight cards.

Built only from the analysis result (the validated published insights, the deterministic not-surfaced list and
the count of drafts withheld by validation), never from new model text, so it is identical in LIVE and DEMO and
makes no API call. Published insights, artworks not surfaced and validation-withheld drafts are kept apart.
Every sentence goes through the same checks as the guided answers; a sentence that fails is left out.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from gia import catalog, explain, guided, presentation

NUMBER_WORDS = {0: "no", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
                8: "eight", 9: "nine", 10: "ten"}
ORDER_HELP = ("Insights are ordered by evidence strength: well supported first, signals for awareness last. "
              + explain.STRENGTH_NOTE + " The briefing is built from the validated results; no AI request is made.")
NOT_PRIORITISED_REASON = {
    "stable": "steady",
    "zero_baseline_change": "rose from zero on small numbers",
    "weak_signal": "change too small or not supported",
    "temporary_spike": "one-day jump that did not hold",
    "emerging_increase": "too recent to confirm",
    "insufficient_evidence": "missing values",
    "no_clear_pattern": "no clear pattern",
}
UNVERIFIED_LINE = "One briefing line could not be verified against the source data and is not shown."


@dataclass
class Briefing:
    period: str
    chips: list[tuple[str, str]] = field(default_factory=list)      # (label, badge colour)
    lines: list[str] = field(default_factory=list)                  # verified sentences about published insights
    not_prioritised: str = ""
    not_published: str = ""
    withheld: str = ""
    dropped: int = 0                                                # sentences left out because a check failed


def _count(n: int, singular: str, plural: str) -> str:
    return f"{NUMBER_WORDS.get(n, str(n))} {singular if n == 1 else plural}".capitalize()


def _insight_line(entry: dict, strongest: bool) -> tuple[str, list[str]]:
    c = guided._Ctx(entry)
    old_d, new_d, old, new, _ = c.key()
    d = guided._d
    if c.category == "sustained_growth":
        backers = len(c.grouped_support()["qualifying"])
        what = (f"{c.name} rose from {old} on {d(old_d)} to {new} on {d(new_d)} and stayed higher on every later "
                f"processed day, with {NUMBER_WORDS[backers]} other measure{'s' if backers != 1 else ''} rising too")
    elif c.category == "temporary_spike":
        last_d, last_v = c.daily[-1]
        c.value(c.metric, last_d, last_v)
        what = (f"{c.name} jumped from {old} on {d(old_d)} to {new} on {d(new_d)}, then fell back to {last_v} "
                f"on {d(last_d)}")
    else:
        what = f"{c.name} went from {old} on {d(old_d)} to {new} on {d(new_d)}"
    name = catalog.title(entry["pattern"]["artwork_id"], entry["pattern"]["artwork_title"])
    label = (f"{presentation.CATEGORY_PLAIN[c.category]} · "
             f"{presentation.STRENGTH_PLAIN[entry['insight']['confidence']]}")
    lead = "Strongest evidence: " if strongest else ""
    text = f"{lead}**{name}** ({label}): {what}."
    return text, guided.check(text, c.facts, "briefing")


def build(result, processed_dates: list[str], excluded_dates: list[str]) -> Briefing:
    published = result.published
    withheld = len(result.withheld) if not result.replayed else (result.withheld_count or 0)
    days = len(processed_dates)
    period = (f"{explain.fmt_date(processed_dates[0])}–{explain.fmt_date(processed_dates[-1])} · "
              f"{NUMBER_WORDS.get(days, str(days))} processed fair days")
    if excluded_dates:
        period += f" · {explain._list([explain.fmt_date(x) for x in excluded_dates])} excluded (not processed yet)"
    b = Briefing(period)

    by_category: dict[str, int] = {}
    for e in published:
        by_category[e["pattern"]["category"]] = by_category.get(e["pattern"]["category"], 0) + 1
    if by_category.get("sustained_growth"):
        b.chips.append((_count(by_category["sustained_growth"], "sustained increase", "sustained increases"), "green"))
    if by_category.get("temporary_spike"):
        b.chips.append((_count(by_category["temporary_spike"], "temporary spike", "temporary spikes"), "orange"))
    others = sum(n for cat, n in by_category.items() if cat not in ("sustained_growth", "temporary_spike"))
    if others:
        b.chips.append((_count(others, "other signal for awareness", "other signals for awareness"), "blue"))

    for i, entry in enumerate(published):
        try:
            text, problems = _insight_line(entry, strongest=i == 0 and len(published) > 1
                                           and entry["insight"]["confidence"] == "higher-confidence")
        except Exception as e:   # malformed pattern: fail closed
            text, problems = "", [type(e).__name__]
        if problems or not guided._matches_source(entry["pattern"]):
            b.dropped += 1
        else:
            b.lines.append(text)

    # Not surfaced: kept apart from the published insights. A reportable pattern that has no published insight
    # (e.g. its draft failed validation) is "not published", never "not prioritised".
    reportable = [n for n in result.not_surfaced if n["category"] not in NOT_PRIORITISED_REASON]
    quiet = [n for n in result.not_surfaced if n["category"] in NOT_PRIORITISED_REASON]
    if quiet:
        b.chips.append((_count(len(quiet), "artwork not prioritised", "artworks not prioritised"), "gray"))
        b.not_prioritised = "; ".join(f"{catalog.title(n['artwork_id'], n['artwork_title'])} "
                                      f"({NOT_PRIORITISED_REASON[n['category']]})" for n in quiet)
    if reportable:
        b.not_published = explain._list([catalog.title(n["artwork_id"], n["artwork_title"]) for n in reportable])
    if withheld:
        b.chips.append((_count(withheld, "draft withheld by validation", "drafts withheld by validation"), "red"))
        b.withheld = (f"{_count(withheld, 'draft finding', 'draft findings')} did not pass the "
                      f"evidence checks and {'is' if withheld == 1 else 'are'} not shown.")
    for text in (b.period, b.not_prioritised, b.not_published, b.withheld, *(label for label, _ in b.chips)):
        if text and guided.check(text, [], "briefing"):
            raise ValueError(f"briefing text failed its checks: {text!r}")
    return b
