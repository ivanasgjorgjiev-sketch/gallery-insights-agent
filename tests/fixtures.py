"""Mocked investigation results for development and tests (no API calls).

These mirror the shape of the Milestone 3 live run (A1, A2, B1 insights) but are written by hand
and replayed through the scripted FakeClient, so they are clearly labelled as mocks.
"""

from gia import agent
from tests.test_agent import FakeClient, final, response, tool_use

D1, D2 = "2026-10-14", "2026-10-15"
MOCK_MODEL = "claude-sonnet-5-5"


def _changes(artwork_id, rows):
    return [{"artwork_id": artwork_id, "metric": m, "old_date": D1, "new_date": D2, "old_value": o,
             "new_value": n, "absolute_change": n - o, "percentage_change": p} for m, o, n, p in rows]


A1 = {
    "signal_type": "sustained_growth", "artwork_id": "A001", "confidence": "higher-confidence",
    "title": "Artwork A1: views doubled on Oct 15 and stayed higher",
    "observed_signal": "Artwork views rose from 40 on 2026-10-14 to 80 on 2026-10-15 (+100.0%) and stayed above "
                       "the starting level on both later processed days. Daily unique viewers rose from 30 to 45 "
                       "(+50.0%) and favourites from 5 to 12 (+140.0%).",
    "why_it_may_matter": "Several engagement measures rose together and held, so this is a well-corroborated "
                         "increase in attention.",
    "suggested_next_step": "Review the engagement evidence and decide whether further investigation is worthwhile.",
    "limitations": ["Engagement counts do not show purchase intent or predict sales.",
                    "Inquiries did not increase."],
    "metric_changes": _changes("A001", [("artwork_views", 40, 80, 100.0),
                                        ("unique_artwork_viewers", 30, 45, 50.0),
                                        ("favourites", 5, 12, 140.0)]),
    "metric_totals": [],
}
A2 = {
    "signal_type": "sustained_growth", "artwork_id": "A002", "confidence": "moderate-confidence",
    "title": "Artwork A2: views up on Oct 15 and maintained",
    "observed_signal": "Artwork views rose from 25 to 35 (+40.0%) between 2026-10-14 and 2026-10-15 and stayed "
                       "above the starting level afterwards. Daily unique viewers rose from 20 to 26 (+30.0%).",
    "why_it_may_matter": "A modest increase that held, supported by one other measure.",
    "suggested_next_step": "Review the engagement evidence and decide whether further investigation is worthwhile.",
    "limitations": ["The increase is small in absolute terms.", "Only one other measure supports it."],
    "metric_changes": _changes("A002", [("artwork_views", 25, 35, 40.0),
                                        ("unique_artwork_viewers", 20, 26, 30.0)]),
    "metric_totals": [],
}
B1 = {
    "signal_type": "temporary_spike", "artwork_id": "B001", "confidence": "qualified",
    "title": "Artwork B1: one-day spike that did not hold",
    "observed_signal": "Artwork views rose from 30 to 45 (+50.0%) on 2026-10-15, then fell back close to the "
                       "starting level on the later processed days.",
    "why_it_may_matter": "Worth knowing about, but it should not be read as a trend.",
    "suggested_next_step": "",
    "limitations": ["A single-day increase that was not maintained; this is not sustained growth.",
                    "No other measure rose enough to support it."],
    "metric_changes": _changes("B001", [("artwork_views", 30, 45, 50.0)]),
    "metric_totals": [],
}


def mock_three_insight_result() -> agent.AnalysisResult:
    script = [
        response("tool_use", tool_use("get_processed_data", {}, "t1")),
        response("tool_use", tool_use("detect_engagement_patterns",
                                      {"metric": "artwork_views", "artwork_ids": None}, "t2")),
        response("tool_use", *[tool_use("validate_evidence", {"insight": i}, f"v{n}")
                               for n, i in enumerate((A1, A2, B1))]),
        final([B1, A2, A1]),   # deliberately unordered: the app must prioritise by strength
    ]
    return agent.run_analysis(FakeClient(script), MOCK_MODEL)
