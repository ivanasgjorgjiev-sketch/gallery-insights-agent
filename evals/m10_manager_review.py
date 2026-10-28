"""Milestone 10 human review: suggested follow-ups, the daily briefing, plain-language labels and the fictional
artwork catalog, written to evals/reports/m10/HUMAN_REVIEW_m10.md. Deterministic; no API calls.

    .venv/bin/python -m evals.m10_manager_review
"""

from __future__ import annotations

import dataclasses
import datetime as dt

from evals import m8_cases as m8
from gia import actions, briefing, catalog, data, explain, guided, presentation, tools
from tests import fixtures as fx

OUT = m8.ROOT / "evals" / "reports" / "m10" / "HUMAN_REVIEW_m10.md"
VERDICT = "Verdict: ☐ Pass ☐ Revise — notes:"
PATTERNS_CSV = m8.ROOT / "tests" / "data" / "m10_followup_patterns.csv"
RULE_CONDITIONS = {
    "monitor_continuation": "sustained increase · well supported · two or more measures support it",
    "cautious_monitoring": "sustained increase · partly supported · exactly one measure supports it (each other "
                           "measure described as it is: small rise, no rise or not recorded)",
    "recurrence_watch": "temporary spike · for awareness only",
    "await_later_day": "recent increase · for awareness only · no later processed day yet (min_later_days failed)",
    "context_only": "rose from zero · for awareness only",
    "insufficient_evidence": "small or unsupported change, or not enough data · for awareness only (the failed "
                             "criterion or missing measure is named)",
}


def _briefing_md(b: briefing.Briefing) -> list[str]:
    out = [f"> **Daily briefing** · {b.period}  ", "> " + " · ".join(f"[{label}]" for label, _ in b.chips)]
    out += [f"> - {line}" for line in b.lines]
    if b.dropped:
        out.append(f"> _{briefing.UNVERIFIED_LINE}_")
    if b.not_prioritised:
        out.append(f"> **Not prioritised (not published):** {b.not_prioritised}.")
    if b.not_published:
        out.append(f"> **Found but not published in this analysis:** {b.not_published}.")
    if b.withheld:
        out.append(f"> **Withheld by validation:** {b.withheld}")
    return out


def build() -> str:
    o = tools.get_processed_data()
    days, excluded = o["processed_dates"], [e["date"] for e in o["excluded_dates"]]
    lines = ["# Milestone 10 · Human review of manager-experience wording", "",
             f"_Generated {dt.date.today().isoformat()} by `evals/m10_manager_review.py` (deterministic; no API "
             "calls)._", "",
             "Everything below is built from the validated insights and the deterministic tools, and passes the same "
             "checks as the guided answers (pattern recomputed from the source, figures, prohibited claims, "
             "commercial actions, cause-seeking). Text that fails a check is not shown in the app.", "",
             "## 1. Suggested follow-ups (rule-based)", "",
             "A rule is chosen only from the validated evidence: pattern category, evidence strength, which supporting "
             "measures qualified, were weak or are missing, and which screening criteria failed. Artwork IDs, titles "
             "and artists never select a rule. Outcomes: **suggestion**; **no specific suggestion** (valid evidence "
             "that supports nothing specific, shown as a neutral explanation); **unavailable** (a check failed, "
             "nothing shown).", "",
             "| Rule | Applies when (validated evidence) | Outcome |", "|---|---|---|"]
    lines += [f"| `{name}` | {RULE_CONDITIONS[name]} | {kind.replace('_', ' ')} |" for name, kind, *_ in actions.RULES]
    lines += ["| `no_rule` | any other combination | neutral: " + f"“{actions.NO_SPECIFIC}.” |",
              "| (inconsistent) | a sustained increase whose support does not match its rating | unavailable |", ""]
    for row in m8.ROWS:
        with m8.source_for(row):
            e = m8.entry_for(row)
            f = actions.suggest(e)
            nxt = guided.answer(e, "next")
        status = "✅ passes all checks" if f.shown else f"❌ not shown: {'; '.join(f.problems)}"
        lines += [f"### {row.case} · {catalog.title(row.artwork_id, e['pattern']['artwork_title'])} · "
                  f"{presentation.CATEGORY_PLAIN[row.category]} · {presentation.STRENGTH_PLAIN[row.strength]}", "",
                  f"Rule `{f.rule}` · {f.kind.replace('_', ' ')} · {status} · {len(f.text.split())} words", "",
                  f"> **{actions.HEADING}** · {actions.NOTE}  ", f"> {f.text}", "",
                  f"For comparison, the guided answer *What should I look into next?* (unchanged): {nxt.text}", "",
                  VERDICT, ""]
    lines += ["### Same evidence, other artworks (test fixture `tests/data/m10_followup_patterns.csv`)", "",
              "| Artwork | Evidence | Rule | Follow-up |", "|---|---|---|---|"]
    original = tools.load_processed_data
    tools.load_processed_data = lambda *a, **k: data.load_processed_data(PATTERNS_CSV)
    try:
        for e in m8.published_entries():
            p, f = e["pattern"], actions.suggest(e)
            support = ", ".join(f"{guided.METRIC_TEXT[s['metric']]} "
                                f"{'✓' if s['qualifies_as_support'] else '?' if s['qualifies_as_support'] is None else '–'}"
                                for s in p["supporting_metrics"])
            lines.append(f"| {p['artwork_id']} | {presentation.CATEGORY_PLAIN[p['category']]}, "
                         f"{presentation.STRENGTH_PLAIN[e['insight']['confidence']]}; {support} | `{f.rule}` | {f.text} |")
    finally:
        tools.load_processed_data = original
    lines += ["", VERDICT, ""]

    lines += ["## 2. Daily briefing", "", "### The three-insight analysis (as in the demo recording)", ""]
    result = fx.mock_three_insight_result()
    lines += _briefing_md(briefing.build(result, days, excluded)) + ["", VERDICT, ""]
    a2 = next(e for e in result.published if e["pattern"]["artwork_id"] == "A002")
    variant = dataclasses.replace(result, published=[e for e in result.published if e is not a2],
                                  withheld=[{**a2, "errors": ["example"]}],
                                  not_surfaced=explain.not_surfaced({"A001", "B001"}))
    lines += ["### Variant: one draft withheld by validation (possible in a LIVE run)", ""]
    lines += _briefing_md(briefing.build(variant, days, excluded)) + ["", VERDICT, ""]

    lines += ["## 3. Plain-language labels", "", "The technical terms stay in tooltips and in the detailed evidence.",
              "", "| Technical | Shown to the manager |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in presentation.STRENGTH_PLAIN.items()]
    lines += [f"| {explain.CATEGORY_LABELS[k]} | {v} |" for k, v in presentation.CATEGORY_PLAIN.items()]
    lines += [f"| support: {k} | {icon} {label} |" for k, (icon, label) in presentation.SUPPORT_STATUS.items()]
    lines += ["", f"Legend under the tiles: `{presentation.SUPPORT_LEGEND}`; its help text:", "",
              presentation.SUPPORT_LEGEND_HELP, "", VERDICT, ""]

    lines += ["## 4. Fictional artwork catalog", "", catalog.CATALOG_HELP, "",
              "| Source ID | Source label | Fictional title | Artist | Medium | Thumbnail |", "|---|---|---|---|---|---|"]
    labels = {p["artwork_id"]: p["artwork_title"] for p in tools.detect_engagement_patterns()["patterns"]}
    for aid, a in catalog.ARTWORKS.items():
        lines.append(f"| {aid} | {labels.get(aid, '')} | {a['title']} | {catalog.artist(a['artist_id'])} | "
                     f"{a['medium']} | `assets/artworks/{aid}.svg` |")
    lines += ["", VERDICT, ""]
    return "\n".join(lines)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(m8.ROOT)}")


if __name__ == "__main__":
    main()
