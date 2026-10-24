"""Milestone 7: claim-level grounding, tested with deliberately misleading statements that reuse
valid numbers in the wrong context, plus boundary cases (Day 5, missing values, zero baselines,
events vs people, prohibited actions)."""

import pytest

from gia import grounding as g
from gia import tools
from tests import fixtures as fx

F, D1, D2, D3, D4, D5 = g.Fact, "2026-10-14", "2026-10-15", "2026-10-16", "2026-10-17", "2026-10-18"

FACTS = g.facts_from_insight(fx.A1) + [
    F("A001", "artwork_views", "total", 286), F("A002", "artwork_views", "total", 130),
    F("AR01", "artwork_views", "total", 416), F("C002", "unique_artwork_viewers", "missing", 0, D2),
    F("C002", "unique_artwork_viewers", "value", 12, D1), F("C001", "artwork_views", "change", 10, D1, D2),
    F("G001", "gallery_views", "total", 615),
]


def test_reference_facts_all_verify():
    assert [g.verify_fact(f) for f in FACTS] == [None] * len(FACTS)


# --- Step 1: facts are recomputed from the data ---------------------------------------------------

@pytest.mark.parametrize("fact,reason", [
    (F("A001", "artwork_views", "total", 436), "source total is 286"),                 # Day 5 included
    (F("A001", "artwork_views", "value", 150, D5), "excluded"),                         # Day 5 value
    (F("A001", "artwork_views", "value", 80, D3), "source gives 76"),                   # wrong date
    (F("A002", "artwork_views", "total", 286), "source total is 130"),                  # wrong artwork
    (F("A001", "favourites", "total", 286), "source total is 41"),                      # wrong metric
    (F("C002", "unique_artwork_viewers", "value", 0, D2), "not recorded"),              # missing treated as 0
    (F("C002", "unique_artwork_viewers", "change", -12, D1, D2), "unavailable"),        # comparison with missing
    (F("C001", "artwork_views", "percent_change", 100, D1, D2), "undefined from a zero baseline"),
    (F("AR01", "unique_artwork_viewers", "total", 416), "cannot be totalled"),           # people from events
    (F("A001", "unique_artwork_viewers", "total", 185), "cannot be totalled"),
    (F("AR01", "artwork_views", "value", 65, D1), "artist-level facts can only be totals"),
    (F("Z999", "artwork_views", "total", 1), "unknown subject"),
    (F("A001", "artwork_views", "change", 40, D2, D1), "two processed dates in order"),
    (F("A001", "artwork_views", "value", 40, "2025-10-14"), "not a processed fair date"),
])
def test_wrong_facts_are_rejected(fact, reason):
    assert reason in (g.verify_fact(fact) or "")


# --- Step 2: valid numbers reused in the wrong context are caught ------------------------------------

GOOD = [
    fx.A1["observed_signal"],
    "Artist A's two artworks received 416 artwork-view events (Artwork A1: 286, Artwork A2: 130; 286 + 130 = 416).",
    "A001 had 286 and A002 had 130 view events: 416 combined view events.",
    "Daily unique viewers for Artwork C2 on 2026-10-15 is not recorded, so the comparison with 2026-10-14 (12) "
    "is unavailable.",
    "Artwork C1's views rose by 10 between Oct 14 and Oct 15; a percentage can't be calculated from zero.",
    "Gallery-profile views totalled 615 across the 4 processed days.",
    "B1 did not meet the rule of at least 30% that was held on later days.",
    "On Day 2, Artwork A1's views reached 80.",
]


@pytest.mark.parametrize("text", GOOD)
def test_correct_statements_pass(text):
    assert g.check_text(text, FACTS) == []


MISLEADING = [
    ("Artwork A2 received 286 artwork views.", "attributed to A002"),                     # wrong artwork
    ("A2 had 286 views and A1 had 130 views.", "attributed to A002"),                     # swapped
    ("Artwork A1 received 286 favourites.", "described as favourites"),                  # wrong metric
    ("Artwork A1's views rose 100% on Oct 17.", "described for 2026-10-17"),             # wrong date
    ("Artwork A1's views rose 100% between 2026-10-16 and 2026-10-17.", "described for 2026-10-16"),
    ("Artist A had 416 unique viewers.", "described as unique_artwork_viewers"),         # events as people
    ("Artist A received 286 views.", "attributed to AR01"),                               # part as whole
    ("Artwork C1 views rose 10%.", "not a verified percentage change"),                   # abs change as %
    ("Artwork C2 had 0 unique viewers on Oct 15.", "not a verified value"),               # missing as zero
    ("Artwork C2's unique viewers fell from 12 to 0.", "not a verified value"),
    ("Artist A: 286 + 130 = 426 views.", "incorrect arithmetic"),
    ("On Oct 18 Artwork A1 had 150 views.", "not a verified value"),                      # Day 5 value
    ("Artwork A1 reached 80 views on 2026-10-18.", "excluded date"),                      # valid number, Day 5 date
    ("Artwork A1's favourites rose 50.0%.", "described as favourites"),                   # % of another metric
    ("Artwork A1 had 615 views.", "verified figure is for gallery_views"),                # gallery figure as artwork
]


@pytest.mark.parametrize("text,problem", MISLEADING)
def test_misleading_statements_are_caught(text, problem):
    problems = g.check_text(text, FACTS)
    assert any(problem in p for p in problems), problems


# --- The same checks protect insights and follow-up answers ------------------------------------------

@pytest.mark.parametrize("field,text", [
    ("observed_signal", "Artwork views rose from 40 on 2026-10-14 to 80 on 2026-10-16 (+100.0%)."),   # wrong date
    ("observed_signal", "Favourites rose from 40 to 80 (+100.0%)."),                                  # wrong metric
    ("why_it_may_matter", "Artwork A2 shows the same 100.0% jump."),                                  # wrong artwork
])
def test_insight_with_misplaced_number_is_withheld(field, text):
    report = tools.validate_evidence({**fx.A1, field: text})
    assert not report["valid"] and report["factual_errors"]


def test_followup_fact_must_come_from_a_tool_in_this_question():
    # A true fact (A001 favourites total 41) that no tool returned in this question is still withheld.
    f = fx.mock_followup("q", {"answer_type": "answer", "answer": "Artwork A1 received 41 favourites in total.",
                               "limitations": [], "facts": [fx.FACT("A001", "favourites", "total", 41)]})
    assert f.status == "withheld" and any("not obtained from a tool" in e for e in f.grounding_errors)


def test_followup_misattribution_with_valid_fact_is_withheld():
    f = fx.mock_followup(fx.TC03_QUESTION, {**fx.TC03_ANSWER, "answer": "Artwork A2 received 286 artwork-view events."},
                         [fx.response("tool_use", fx.tool_use("aggregate_artist_metrics",
                                                              {"artist_id": "AR01", "metrics": ["artwork_views"]}, "f1"))])
    assert f.status == "withheld" and any("attributed to A002" in e for e in f.grounding_errors)


def test_followup_false_fact_is_withheld_even_if_text_matches_it():
    f = fx.mock_followup("q", {"answer_type": "answer", "answer": "Artwork A1 had 436 views in total.",
                               "limitations": [], "facts": [fx.FACT("A001", "artwork_views", "total", 436)]})
    assert f.status == "withheld" and any("source total is 286" in e for e in f.grounding_errors)


@pytest.mark.parametrize("answer", [
    "Offer Artwork A1 a 10% discount to convert interested collectors.",
    "I have contacted the collectors for you.",
    "Raise the price of Artwork A1.",
])
def test_prohibited_actions_in_answers_are_withheld(answer):
    f = fx.mock_followup(fx.REFUSAL_QUESTION, {"answer_type": "refusal", "answer": answer, "limitations": [],
                                               "facts": []})
    assert f.status == "withheld"
