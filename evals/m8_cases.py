"""Milestone 8 evaluation suite: guided insight exploration (separate from the 16 Milestone 7 cases).

Case matrix: every publishable pattern type x the four guided questions. Five rows use the real
source data (A1, A2, B1, C1, C2); two use a small development-only fixture
(tests/data/m8_boundary.csv) for the types the real data never produces. Everything here is
deterministic and offline: no API client is ever created.
"""

from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass
from pathlib import Path

from gia import agent, data, explain, grounding, guided, tools

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_CSV = ROOT / "tests" / "data" / "m8_boundary.csv"


@dataclass(frozen=True)
class Row:
    case: str            # A1, A2, ... (artwork short name)
    artwork_id: str
    source: str          # "real" or "fixture"
    category: str
    strength: str        # evidence-strength label shown on the card
    description: str


ROWS = [
    Row("A1", "A001", "real", "sustained_growth", "higher-confidence", "sustained increase, two supporting measures"),
    Row("A2", "A002", "real", "sustained_growth", "moderate-confidence", "sustained increase, one supporting measure"),
    Row("B1", "B001", "real", "temporary_spike", "qualified", "one-day jump that did not hold"),
    Row("C1", "C001", "real", "zero_baseline_change", "qualified", "increase from zero (no percentages)"),
    Row("C2", "C002", "real", "weak_signal", "qualified", "change too small; a supporting value missing"),
    Row("F1", "F001", "fixture", "emerging_increase", "qualified", "jump on the last processed day (date boundary)"),
    Row("F2", "F002", "fixture", "insufficient_evidence", "qualified", "rise held, but support cannot be verified"),
]
SUPPRESSED = [("B2", "B002", "stable")]        # never a card, so never asked
QUESTION_IDS = [q for q, _ in guided.QUESTIONS]
MAX_WORDS = 110
REANALYSIS = re.compile(r"\b(re-?analy[sz]|re-?run|wait (for|until)|once .* processed|after .* is processed)",
                        re.IGNORECASE)


@contextlib.contextmanager
def fixture_data():
    """Point the tools at the boundary fixture (development only), then restore the real source data."""
    original = tools.load_processed_data
    tools.load_processed_data = lambda *a, **k: data.load_processed_data(FIXTURE_CSV)
    try:
        yield
    finally:
        tools.load_processed_data = original


def source_for(row: Row):
    return fixture_data() if row.source == "fixture" else contextlib.nullcontext()


def insight_for(pattern: dict) -> dict:
    """A minimal, neutral insight for a pattern, as the agent would propose it (numbers from the tools)."""
    kc = pattern["key_comparison"]
    cmp = tools.compare_daily_metrics(pattern["artwork_id"], kc["old_date"], kc["new_date"],
                                      [pattern["metric"]])["comparisons"][0]
    return {"signal_type": pattern["category"], "artwork_id": pattern["artwork_id"],
            "title": f"{pattern['artwork_title']} engagement pattern",
            "observed_signal": "Artwork views changed between the comparison days.",
            "why_it_may_matter": "It may be worth reviewing alongside the evidence.",
            "confidence": pattern["evidence_strength"] or "qualified",
            "limitations": ["The data shows what happened, not why."],
            "metric_changes": [{"artwork_id": pattern["artwork_id"], "metric": pattern["metric"],
                                "old_date": kc["old_date"], "new_date": kc["new_date"],
                                "old_value": cmp["old_value"], "new_value": cmp["new_value"],
                                "absolute_change": cmp["absolute_change"],
                                "percentage_change": cmp["percentage_change"]}]}


def published_entries(artwork_ids: list[str] | None = None) -> list[dict]:
    """Validated insight entries via the real publication gate, for every publishable pattern."""
    patterns = [p for p in tools.detect_engagement_patterns()["patterns"]
                if tools.HANDLING[p["category"]] != "suppress"
                and (artwork_ids is None or p["artwork_id"] in artwork_ids)]
    published, withheld = agent.publication_gate([insight_for(p) for p in patterns])
    assert not withheld, [w["errors"] for w in withheld]
    return published


def entry_for(row: Row) -> dict:
    with source_for(row):
        [entry] = published_entries([row.artwork_id])
    return entry


# --- Checks on one answer -------------------------------------------------------------------------------

@dataclass
class Check:
    name: str
    passed: bool
    detail: str = ""


def _sentences_of_card(entry: dict) -> set[str]:
    pattern, insight = entry["pattern"], entry["insight"]
    texts = [explain.short_rationale(pattern), explain.explain_pattern(pattern), insight["why_it_may_matter"],
             explain.STRENGTH_TEXT[insight["confidence"]], insight["observed_signal"]]
    return {s.strip().lower() for t in texts for s in grounding.SENTENCE_SPLIT.split(t) if len(s.strip()) > 20}


def check_answer(row: Row, entry: dict, ans: guided.GuidedAnswer) -> list[Check]:
    """Automated checks for one guided answer (run with the row's data source active)."""
    pattern, text = entry["pattern"], ans.text
    checks = [Check("shown (grounding and safety checks pass)", ans.shown, "; ".join(ans.problems))]
    bad_dates = guided.date_problems(text)
    checks.append(Check("dates: processed days only; excluded day only as excluded", not bad_dates,
                        "; ".join(bad_dates)))

    # Missing values and zero baselines.
    missing = [f for f in ans.facts if f.measure == "missing"]
    checks.append(Check("missing values shown as not recorded (never zero)",
                        not missing or "not recorded" in text))
    zero_pct = pattern["category"] == "zero_baseline_change" and ans.question_id in ("relevance", "trend") \
        and "%" in text
    checks.append(Check("no percentage from a zero baseline", not zero_pct))
    summed = re.search(r"(total|in all|altogether|combined)[^.]*unique viewers|unique viewers[^.]*(total|in all)",
                       text, re.IGNORECASE)
    checks.append(Check("daily unique viewers never summed", not summed))

    # Isolation: only the selected artwork's data, no other artwork or artist named.
    others = [p for p in tools.detect_engagement_patterns()["patterns"] if p["artwork_id"] != row.artwork_id]
    named = [p["artwork_id"] for p in others
             if re.search(rf"\b({p['artwork_id']}|{re.escape(p['artwork_title'])})\b", text)]
    foreign_facts = [f for f in ans.facts if f.subject != row.artwork_id]
    checks.append(Check("isolation: only this insight's artwork", not named and not foreign_facts,
                        ", ".join(named + [f.subject for f in foreign_facts])))

    # Determinism.
    again = guided.answer(entry, ans.question_id)
    checks.append(Check("deterministic (identical on repeat)", again.text == text and again.problems == ans.problems))

    # Concise and not a repeat of the card.
    words = len(re.findall(r"\b\w[\w'’-]*\b", text))
    checks.append(Check(f"concise (≤ {MAX_WORDS} words)", words <= MAX_WORDS, f"{words} words"))
    repeated = [s for s in grounding.SENTENCE_SPLIT.split(text) if s.strip().lower() in _sentences_of_card(entry)]
    checks.append(Check("does not repeat the card's sentences", not repeated, " | ".join(repeated)))

    checks += _question_checks(row, entry, ans)
    return checks


def _question_checks(row: Row, entry: dict, ans: guided.GuidedAnswer) -> list[Check]:
    pattern, text, q = entry["pattern"], ans.text, ans.question_id
    lower = text.lower()
    qualified = row.strength == "qualified"
    if q == "relevance":
        return [Check("qualified signals are never presented as growth",
                      not qualified or ("awareness" in lower or "unconfirmed" in lower or "not as growth" in lower)),
                Check("sustained insights are not labelled awareness-only",
                      qualified or "awareness" not in lower),
                Check("no business priority or ranking language",
                      not re.search(r"\b(priorit|most important|top pick|focus on|best)\b", lower))]
    if q == "trend":
        days = [explain.fmt_date(d["date"]) for d in pattern["daily"]]
        values = [explain.fmt_value(d["value"]) for d in pattern["daily"]]
        return [Check("covers every processed day of the primary metric",
                      all(f"{d}: {v}" in text for d, v in zip(days, values))),
                Check("primary metric only (other measures not listed by default)",
                      not re.search(r"unique viewers|favourites|inquiries", lower))]
    if q == "signals":
        groups = {"qualifying": [], "weak": []}
        for s in pattern["supporting_metrics"]:
            groups["qualifying" if s["qualifies_as_support"] else "weak"].append(guided.METRIC_TEXT[s["metric"]])
        lines = {line.split("**")[1].strip().rstrip(":"): line for line in text.splitlines() if "**" in line}
        supports, weak = lines.get("Supports it", ""), lines.get("Weak or missing", "")
        against, limits = lines.get("Against it", ""), lines.get("What limits confidence", "")
        failed = {c["rule"] for c in pattern["criteria"] if not c["passed"]}
        contradicts = "min_gain_retained" in failed
        limited = bool(failed & {"min_absolute_change", "min_later_days", "corroboration"})
        stated_against = bool(against) and "none of the screening checks" not in against
        return [Check("qualifying measures listed as support", all(m in supports for m in groups["qualifying"])),
                Check("weak, flat or missing measures listed as weak", all(m in weak for m in groups["weak"])),
                Check("'Against it' only for contradicting evidence (none invented)", stated_against == contradicts),
                Check("'What limits confidence' only for checks that could not pass", bool(limits) == limited),
                Check("says so when nothing argues against the pattern",
                      contradicts or limited or "none of the screening checks" in against)]
    # next
    return [Check("points to evidence already available (View evidence)", text.startswith("Open View evidence")),
            Check("no reanalysis or waiting-for-data action", not REANALYSIS.search(text))]


def evaluate(row: Row) -> list[tuple[guided.GuidedAnswer, list[Check]]]:
    with source_for(row):
        entry = entry_for(row)
        return [(a, check_answer(row, entry, a)) for a in guided.answers(entry)]
