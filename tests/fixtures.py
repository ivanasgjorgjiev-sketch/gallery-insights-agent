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


# --- Mocked follow-up questions (scripted FakeClient, no API) -------------------------

import json  # noqa: E402


def FACT(subject, metric, measure, value, start="", end=""):  # noqa: N802 - reads like a record literal
    return {"subject": subject, "metric": metric, "measure": measure, "value": value,
            "start_date": start, "end_date": end}


from gia import followup  # noqa: E402
from tests.test_agent import text  # noqa: E402

TC03_QUESTION = "How many artwork views did Artist A receive during the processed fair days?"
TC03_ANSWER = {
    "answer_type": "answer",
    "answer": "Artist A's two artworks received 416 artwork-view events across the four processed days "
              "(Artwork A1: 286, Artwork A2: 130; 286 + 130 = 416). This is a count of views, not of "
              "416 different people.",
    "limitations": ["Daily unique viewers cannot be added up across days or artworks to count people."],
    "facts": [FACT("AR01", "artwork_views", "total", 416), FACT("A001", "artwork_views", "total", 286),
              FACT("A002", "artwork_views", "total", 130)],
}
C2_QUESTION = "Did Artwork C2's unique viewers go up on Oct 15?"
C2_ANSWER = {
    "answer_type": "answer",
    "answer": "We can't tell. Daily unique viewers for Artwork C2 on 2026-10-15 is not recorded, so the "
              "comparison with 2026-10-14 (12) is unavailable. Artwork views did rise from 15 to 20.",
    "limitations": ["A missing value is unknown, not zero."],
    "facts": [FACT("C002", "unique_artwork_viewers", "missing", 0, D2),
              FACT("C002", "unique_artwork_viewers", "value", 12, D1),
              FACT("C002", "artwork_views", "value", 15, D1), FACT("C002", "artwork_views", "value", 20, D2)],
}
REFUSAL_QUESTION = "Identify collectors who viewed A1 and contact them with a 10% discount."
REFUSAL_ANSWER = {
    "answer_type": "refusal",
    "answer": "I can't do that. The data contains no collector identities or contact details, and I can't "
              "contact anyone, change prices or offer a 10% discount. I can summarise Artwork A1's aggregated "
              "engagement for your own review.",
    "limitations": ["Engagement data does not show who viewed an artwork or whether they would buy."],
    "facts": [],
}
BEST_QUESTION = "Which artwork performed best?"
BEST_ANSWER = {
    "answer_type": "clarification",
    "answer": "\"Best\" depends on the measure. Do you mean artwork views, favourites or inquiries? I can "
              "compare the artworks on any of these, but there is no single overall score.",
    "limitations": [],
    "facts": [],
}
CAUSAL_QUESTION = "Did our marketing campaign cause A1's engagement increase, and does this mean it will sell?"
CAUSAL_ANSWER = {
    "answer_type": "answer",
    "answer": "Artwork A1's views did rise, from 40 on 2026-10-14 to 80 on 2026-10-15 (+100.0%), and stayed higher. "
              "But there is no campaign data, so I can't tell whether a campaign caused it, and there is no sales "
              "data, so this does not show whether it will sell.",
    "limitations": ["Engagement data shows what happened, not why, and does not predict sales."],
    "facts": [FACT("A001", "artwork_views", "value", 40, D1), FACT("A001", "artwork_views", "value", 80, D2),
              FACT("A001", "artwork_views", "percent_change", 100.0, D1, D2)],
}
PEOPLE_QUESTION = "Did 416 different people view Artist A's artworks?"
PEOPLE_ANSWER = {
    "answer_type": "answer",
    "answer": "No. 416 is the number of artwork-view events for Artist A (286 + 130 = 416), including repeat views. "
              "Daily unique viewers can't be added up across days or artworks, so the number of different people "
              "is not known.",
    "limitations": ["The data has no fair-wide count of distinct visitors."],
    "facts": [FACT("AR01", "artwork_views", "total", 416), FACT("A001", "artwork_views", "total", 286),
              FACT("A002", "artwork_views", "total", 130)],
}
SCOPE_QUESTION = "Compare our engagement with another gallery or last year's fair."
SCOPE_ANSWER = {
    "answer_type": "refusal",
    "answer": "I can't make that comparison. This prototype only contains engagement data for this gallery "
              "and this edition (G001 / E001), with no other galleries or previous fairs. I can compare artworks "
              "or days within this edition instead.",
    "limitations": ["No other gallery, edition or historical data is available."],
    "facts": [],
}
DISCOUNT_QUESTION = "Based on these engagement signals, decide which artwork we should discount and by how much."
DISCOUNT_ANSWER = {
    "answer_type": "refusal",
    "answer": "I can't make pricing decisions. Engagement counts alone can't justify a discount, and pricing is "
              "for you and your sales team to decide. I can summarise the engagement evidence for each artwork "
              "to support your own review.",
    "limitations": ["There is no sales or pricing data in this prototype."],
    "facts": [],
}


def mock_followup(question, answer, tool_script=(), insight_id=None, published=None, **kw):
    script = [r for r in tool_script] + [response("end_turn", text(json.dumps(answer)))]
    published = published if published is not None else mock_three_insight_result().published
    return followup.run_followup(FakeClient(script), MOCK_MODEL, question, published, insight_id, **kw)


def mock_tc03_followup(**kw):
    return mock_followup(TC03_QUESTION, TC03_ANSWER, [response("tool_use", tool_use(
        "aggregate_artist_metrics", {"artist_id": "AR01", "metrics": ["artwork_views"]}, "f1"))], **kw)


def mock_c2_followup(**kw):
    return mock_followup(C2_QUESTION, C2_ANSWER, [response("tool_use", tool_use(
        "compare_daily_metrics", {"artwork_id": "C002", "old_date": D1, "new_date": D2,
                                  "metrics": ["artwork_views", "unique_artwork_viewers"]}, "f1"))], **kw)


def mock_refusal_followup(**kw):
    return mock_followup(REFUSAL_QUESTION, REFUSAL_ANSWER, **kw)


def mock_best_followup(**kw):
    return mock_followup(BEST_QUESTION, BEST_ANSWER, **kw)


def mock_causal_followup(**kw):
    return mock_followup(CAUSAL_QUESTION, CAUSAL_ANSWER, [response("tool_use", tool_use(
        "compare_daily_metrics", {"artwork_id": "A001", "old_date": D1, "new_date": D2,
                                  "metrics": ["artwork_views"]}, "f1"))], **kw)


def mock_people_followup(**kw):
    return mock_followup(PEOPLE_QUESTION, PEOPLE_ANSWER, [response("tool_use", tool_use(
        "aggregate_artist_metrics", {"artist_id": "AR01", "metrics": ["artwork_views"]}, "f1"))], **kw)


def mock_scope_followup(**kw):
    return mock_followup(SCOPE_QUESTION, SCOPE_ANSWER, **kw)


def mock_discount_followup(**kw):
    return mock_followup(DISCOUNT_QUESTION, DISCOUNT_ANSWER, **kw)


TC13_QUESTION = "Identify collectors who viewed A1 and contact them with a discount."
TC13_ANSWER = {
    "answer_type": "refusal",
    "answer": "I can't do that. The data contains no collector identities or contact details, and I can't "
              "contact anyone, change prices or offer discounts. I can summarise Artwork A1's aggregated "
              "engagement so you can decide on any follow-up yourself.",
    "limitations": ["Engagement data is aggregated and anonymous."],
    "facts": [],
}


def mock_tc13_followup(**kw):
    return mock_followup(TC13_QUESTION, TC13_ANSWER, **kw)
