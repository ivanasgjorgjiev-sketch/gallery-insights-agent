"""Write the Milestone 8 human-review document for the guided explanations (no API calls).

    .venv/bin/python -m evals.m8_guided_review

Output: evals/reports/m8/HUMAN_REVIEW_guided.md: the 20 real-data answers first, then the eight
fixture answers, each with the question, the generated answer, the evidence it is built from and the
automated check results, plus blank verdict fields for the reviewer.
"""

from __future__ import annotations

import datetime as dt
import json

from evals import m8_cases as m8
from gia import explain, guided

OUT = m8.ROOT / "evals" / "reports" / "m8" / "HUMAN_REVIEW_guided.md"
APPROVED = m8.ROOT / "tests" / "data" / "m8_guided_approved.json"   # locked after human review
ROUND1 = OUT.parent / "guided_answers_round1.json"     # wording reviewed in round 1, for comparison
# Round 2: answers revised at the product owner's request (2026-10-26).
REVISED = {
    ("A1", "relevance"): "More manager-oriented; less screening-rule terminology.",
    ("A2", "relevance"): "Neutral wording: a sustained increase with limited supporting evidence.",
    ("A2", "next"): "A clearer, evidence-focused next step instead of \"treat it as a candidate\".",
    ("B1", "next"): "Checks whether the supporting measures stayed above their starting level after the spike.",
    ("C1", "relevance"): "No claim beyond the processed period about the first recorded views.",
    ("C2", "relevance"): "Less repetition of the card; explains why a large percentage can be a small change.",
    ("F2", "signals"): "Explains that the corroboration check could not pass and that this is missing support, "
                       "not contradicting evidence.",
}
LABEL_ONLY = {("C2", "signals"), ("F1", "signals")}   # "Against it" relabelled "What limits confidence"
CRITERIA = ("Correct (matches the evidence)", "Useful for a Gallery Operations Manager",
            "Clear and concise; adds to the card", "Safe (no prediction, priority, cause or action)")


def _evidence(entry: dict) -> list[str]:
    p = entry["pattern"]
    kc = p["key_comparison"]
    lines = [f"- **Card:** {entry['insight']['confidence']} · {explain.CATEGORY_LABELS[p['category']]} · "
             f"insight `{entry['insight_id']}`",
             "- **Views by processed day:** " + ", ".join(f"{explain.fmt_date(d['date'])} {explain.fmt_value(d['value'])}"
                                                         for d in p["daily"]),
             f"- **Key comparison:** {explain.fmt_date(kc['old_date'])} → {explain.fmt_date(kc['new_date'])}: "
             f"{kc['old_value']} → {kc['new_value']} ({explain.change_text(kc)})",
             "- **Other measures, same days:**"]
    for s in p["supporting_metrics"]:
        verdict = {True: "counts as support", False: "does not count", None: "unknown (not recorded)"}[
            s["qualifies_as_support"]]
        lines.append(f"  - {explain.METRIC_NAMES[s['metric']]}: {explain.fmt_value(s['old_value'])} → "
                     f"{explain.fmt_value(s['new_value'])} ({explain.change_text(s)}) · {verdict}")
    failed = [c for c in p["criteria"] if not c["passed"]]
    lines.append("- **Screening checks not met:** " + ("; ".join(f"{c['rule']} ({c['detail']})" for c in failed)
                                                      if failed else "none"))
    lines.append(f"- **What the card already says:** {explain.short_rationale(p)}")
    return lines


def _answer(n: int, row: m8.Row, ans: guided.GuidedAnswer, checks: list[m8.Check], round1: dict,
            approved: dict) -> list[str]:
    passed = sum(c.passed for c in checks)
    key = (row.case, ans.question_id)
    mark = " · ✏️ **REVISED**" if key in REVISED else " · 🏷️ label only" if key in LABEL_ONLY else ""
    lines = [f"#### {n}. {row.case} · {ans.question}{mark}", ""]
    if key in REVISED:
        lines += [f"_Revision: {REVISED[key]}_", ""]
    elif key in LABEL_ONLY:
        lines += ["_\"Against it\" relabelled \"What limits confidence\": the point is a limitation, not "
                  "contradicting evidence. Content unchanged._", ""]
    lines += [*(f"> {line}" if line else ">" for line in (ans.text or guided.UNAVAILABLE).splitlines()), ""]
    previous = round1.get(f"{row.case}:{ans.question_id}")
    if mark and previous and previous != ans.text:
        lines += ["<details><summary>Previous wording (round 1)</summary>", "",
                  *(f"> {line}" if line else ">" for line in previous.splitlines()), "", "</details>", ""]
    lines += [
             f"<details><summary>Automated checks: {passed}/{len(checks)} passed · "
             f"{len(ans.facts)} stated facts recomputed with the tools</summary>", ""]
    lines += [f"- {'✅' if c.passed else '❌'} {c.name}" + (f" ({c.detail})" if c.detail and not c.passed else "")
              for c in checks]
    lines += ["", "</details>", "", "| Criterion | Verdict (Pass / Fail) | Notes |", "|---|---|---|"]
    lines += [f"| {c} | | |" for c in CRITERIA]
    locked = approved.get("answers", {}).get(f"{row.case}:{ans.question_id}")
    verdict = (f"**Pass**: approved by the product owner on {approved['approved']}; wording locked"
               if locked == ans.text else "_Pending_ (differs from the approved wording)" if locked else "_Pending_")
    lines += ["", f"**Overall verdict:** {verdict}", ""]
    return lines


def build() -> str:
    out = ["# Milestone 8 · Human review of guided explanations", "",
           f"_Generated {dt.date.today().isoformat()} by `evals/m8_guided_review.py` (deterministic; no API calls)._", "",
           "Each validated insight card offers four questions in the journey order Relevance → Trend → Confidence → "
           "Next investigation. Answers are built only from the insight's verified pattern and the deterministic "
           "tools; they are identical in LIVE and DEMO mode.", "",
           "**How to review:** for each answer, judge the four criteria and record Pass or Fail. Any Fail blocks the "
           "release gate. Real-data answers (A1–C2) come first; fixture answers (F1, F2) use a small "
           "development-only dataset for card types the real data never produces.", ""]
    round1 = json.loads(ROUND1.read_text()) if ROUND1.exists() else {}
    approved = json.loads(APPROVED.read_text()) if APPROVED.exists() else {}
    if approved:
        out += [f"**Status: approved.** The product owner approved all 28 answers on {approved['approved']} after "
                "two review rounds. The wording is locked by `tests/data/m8_guided_approved.json`; any change fails "
                "the test suite until it is reviewed again.", ""]
    out += ["## Revised in round 2", "",
            f"{len(REVISED)} answers were revised at the product owner's request (marked ✏️ **REVISED**, with the "
            f"previous wording available under each). {len(LABEL_ONLY)} more had only the confidence-section label "
            "changed (🏷️). All other answers are unchanged from round 1.", "",
            "| Answer | Revision |", "|---|---|"]
    out += [f"| {case} {dict(guided.QUESTIONS)[q]} | {note} |" for (case, q), note in REVISED.items()]
    out += [f"| {case} {dict(guided.QUESTIONS)[q]} | 🏷️ Label only: \"What limits confidence\" |"
            for case, q in sorted(LABEL_ONLY)]
    out += [""]
    n = 0
    summary = []
    sections = [("Part 1 · Real data (20 answers)", [r for r in m8.ROWS if r.source == "real"]),
                ("Part 2 · Boundary fixtures (8 answers)", [r for r in m8.ROWS if r.source == "fixture"])]
    body = []
    for title, rows in sections:
        body += [f"## {title}", ""]
        for row in rows:
            with m8.source_for(row):
                entry = m8.entry_for(row)
                results = [(a, m8.check_answer(row, entry, a)) for a in guided.answers(entry)]
                body += [f"### {row.case} · {entry['pattern']['artwork_title']} ({row.artwork_id}) · {row.description}",
                         "", *_evidence(entry), ""]
            for ans, checks in results:
                n += 1
                body += _answer(n, row, ans, checks, round1, approved)
                summary.append((row.case, ans.question_id, all(c.passed for c in checks)))
    ok = sum(s[2] for s in summary)
    out += ["## Automated results", "", f"**{ok} of {len(summary)} answers pass every automated check.**", "",
            "| Case | " + " | ".join(q for q in m8.QUESTION_IDS) + " |",
            "|---|" + "---|" * len(m8.QUESTION_IDS)]
    for row in m8.ROWS:
        cells = ["✅" if next(s[2] for s in summary if s[0] == row.case and s[1] == q) else "❌"
                 for q in m8.QUESTION_IDS]
        out.append(f"| {row.case} ({row.source}) | " + " | ".join(cells) + " |")
    return "\n".join(out + [""] + body)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build())
    print(f"Wrote {OUT.relative_to(m8.ROOT)}")


if __name__ == "__main__":
    main()
