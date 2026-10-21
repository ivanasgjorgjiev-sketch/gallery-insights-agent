"""Milestone 2 tests: the six approved analytical tools and data_dictionary.md rules."""

import json

import pytest

from gia.tools import (
    PATTERN_RULES,
    ToolError,
    aggregate_artist_metrics,
    classify_series,
    compare_daily_metrics,
    detect_engagement_patterns,
    get_artwork_metrics,
    get_processed_data,
    validate_evidence,
)

D1, D2, D3, D4, D5 = "2026-10-14", "2026-10-15", "2026-10-16", "2026-10-17", "2026-10-18"


def by_metric(result):
    return {c["metric"]: c for c in result["comparisons"]}


# --- get_processed_data ----------------------------------------------------------

def test_processed_data_summary():
    r = get_processed_data()
    assert (r["gallery_id"], r["edition_id"], r["validation"]) == ("G001", "E001", "passed")
    assert r["processed_dates"] == [D1, D2, D3, D4]
    assert [e["date"] for e in r["excluded_dates"]] == [D5]
    assert r["gallery_profile_views"]["total"] == 615
    assert len(r["artworks"]) == 6
    json.dumps(r)  # results must be JSON-serialisable for the LLM


def test_all_tool_outputs_are_json_and_never_contain_day5():
    outputs = [
        get_artwork_metrics("A001"),
        compare_daily_metrics("A001", D1, D2),
        aggregate_artist_metrics("AR01"),
        detect_engagement_patterns(),
    ]
    for out in outputs:
        assert D5 not in json.dumps(out)
    assert "source_line" in json.dumps(outputs[0]) and "source_lines" in json.dumps(outputs[1])


# --- get_artwork_metrics ---------------------------------------------------------

def test_a001_metrics_exclude_day5():
    r = get_artwork_metrics("A001")
    assert [d["value"] for d in r["metrics"]["artwork_views"]["daily"]] == [40, 80, 76, 90]
    assert r["metrics"]["artwork_views"]["total_events"] == 286
    assert r["metrics"]["unique_artwork_viewers"]["total_events"] is None  # never summed
    assert D5 not in json.dumps(r)


def test_c002_missing_value_is_null_not_zero():
    m = get_artwork_metrics("C002", ["unique_artwork_viewers"])["metrics"]["unique_artwork_viewers"]
    assert [d["value"] for d in m["daily"]] == [12, None, 14, 13]
    assert m["missing_dates"] == [D2]


def test_unknown_artwork_and_metric_rejected():
    with pytest.raises(ToolError, match="Unknown artwork_id"):
        get_artwork_metrics("Z999")
    with pytest.raises(ToolError, match="Unsupported metric"):
        get_artwork_metrics("A001", ["sales"])


# --- compare_daily_metrics -------------------------------------------------------

def test_tc01_a001_day1_to_day2():
    c = by_metric(compare_daily_metrics("A001", D1, D2))
    assert c["artwork_views"]["percentage_change"] == 100.0
    assert c["unique_artwork_viewers"]["percentage_change"] == 50.0
    assert c["favourites"]["percentage_change"] == 140.0
    assert c["inquiries"]["absolute_change"] == 0
    assert c["inquiries"]["status"] == "zero_baseline"  # 0 -> 0: no percentage


def test_tc010_zero_baseline_absolute_only():
    c = by_metric(compare_daily_metrics("C001", D1, D2, ["artwork_views"]))["artwork_views"]
    assert (c["old_value"], c["new_value"], c["absolute_change"]) == (0, 10, 10)
    assert c["percentage_change"] is None
    assert c["status"] == "zero_baseline"
    assert "inf" not in json.dumps(c).lower()


def test_tc05_missing_value_comparison_unavailable():
    c = by_metric(compare_daily_metrics("C002", D1, D2))
    assert c["unique_artwork_viewers"]["status"] == "unavailable"
    assert c["unique_artwork_viewers"]["absolute_change"] is None
    assert c["unique_artwork_viewers"]["percentage_change"] is None
    assert c["artwork_views"]["absolute_change"] == 5  # other metrics still compared


def test_tc011_day5_cannot_be_compared():
    with pytest.raises(ToolError, match="day_processed=false"):
        compare_daily_metrics("A001", D4, D5)


def test_dates_must_be_ordered_and_processed():
    with pytest.raises(ToolError, match="earlier"):
        compare_daily_metrics("A001", D2, D1)
    with pytest.raises(ToolError, match="not a processed"):
        compare_daily_metrics("A001", "2025-10-14", D2)


# --- aggregate_artist_metrics ----------------------------------------------------

def test_tc03_artist_a_view_events():
    r = aggregate_artist_metrics("AR01", ["artwork_views"])
    views = r["totals"]["artwork_views"]
    assert {a["artwork_id"]: a["total_events"] for a in views["per_artwork"]} == {"A001": 286, "A002": 130}
    assert views["artist_total_events"] == 416
    assert views["calculation"] == "286 + 130 = 416"
    assert any("not a count of distinct visitors" in lim for lim in r["limitations"])


def test_tc12_unique_viewers_cannot_be_aggregated():
    with pytest.raises(ToolError, match="cannot be aggregated"):
        aggregate_artist_metrics("AR01", ["unique_artwork_viewers"])


# --- detect_engagement_patterns --------------------------------------------------

@pytest.fixture(scope="module")
def patterns():
    return {p["artwork_id"]: p for p in detect_engagement_patterns()["patterns"]}


def test_a1_sustained_growth_higher_confidence(patterns):  # TC01
    a1 = patterns["A001"]
    assert (a1["category"], a1["evidence_strength"], a1["suggested_handling"]) == \
        ("sustained_growth", "higher-confidence", "candidate_insight")
    assert (a1["key_comparison"]["old_date"], a1["key_comparison"]["new_date"]) == (D1, D2)
    assert a1["key_comparison"]["percentage_change"] == 100.0
    support = {s["metric"]: s for s in a1["supporting_metrics"]}
    assert support["unique_artwork_viewers"]["percentage_change"] == 50.0
    assert support["favourites"]["percentage_change"] == 140.0
    assert support["unique_artwork_viewers"]["qualifies_as_support"] is True
    assert support["favourites"]["qualifies_as_support"] is True


def test_a2_borderline_moderate_confidence(patterns):
    a2 = patterns["A002"]
    assert (a2["category"], a2["evidence_strength"]) == ("sustained_growth", "moderate-confidence")
    support = {s["metric"]: s for s in a2["supporting_metrics"]}
    assert support["favourites"]["qualifies_as_support"] is False  # 3 -> 4 is too small


def test_b1_temporary_spike_not_growth(patterns):  # TC06 / TC09
    b1 = patterns["B001"]
    assert b1["category"] == "temporary_spike"
    assert b1["suggested_handling"] == "qualify_or_withhold"
    assert not any(s["qualifies_as_support"] for s in b1["supporting_metrics"])


def test_b2_stable_not_weak_signal(patterns):  # TC06
    assert patterns["B002"]["category"] == "stable"
    assert patterns["B002"]["suggested_handling"] == "suppress"


def test_c1_zero_baseline_absolute_only(patterns):  # TC010
    c1 = patterns["C001"]
    assert c1["category"] == "zero_baseline_change"
    assert c1["key_comparison"]["absolute_change"] == 10
    assert c1["key_comparison"]["percentage_change"] is None


def test_c2_weak_signal_with_unknown_support(patterns):  # TC05
    c2 = patterns["C002"]
    assert c2["category"] == "weak_signal"
    uniques = next(s for s in c2["supporting_metrics"] if s["metric"] == "unique_artwork_viewers")
    assert (uniques["new_value"], uniques["qualifies_as_support"]) == (None, None)
    assert any("unknown" in lim and "not zero" in lim for lim in c2["limitations"])


def test_only_sustained_growth_is_a_candidate(patterns):
    for p in patterns.values():
        assert (p["suggested_handling"] == "candidate_insight") == (p["category"] == "sustained_growth")


def test_evidence_strength_and_heuristic_limitations_are_explicit(patterns):
    tool_limits = " ".join(detect_engagement_patterns()["limitations"])
    assert "not statistical confidence levels or probabilities" in tool_limits
    assert "not statistical significance tests" in tool_limits
    assert any("qualitative evidence-strength labels" in lim for lim in patterns["A001"]["limitations"])


# --- Generic rule behaviour (synthetic series, no artwork IDs) -------------------

DATES = [D1, D2, D3, D4]


def classify(values, **supporting):
    return classify_series(DATES, values, supporting or {"favourites": [5, 5, 5, 5]})


def test_spike_and_growth_are_mutually_exclusive():
    assert classify([100, 160, 105, 102], favourites=[5, 9, 5, 5])["category"] == "temporary_spike"
    assert classify([100, 160, 150, 170], favourites=[5, 9, 9, 10])["category"] == "sustained_growth"


def test_mixed_retention_is_weak_signal():
    assert classify([100, 160, 150, 110], favourites=[5, 9, 9, 9])["category"] == "weak_signal"


def test_jump_without_corroboration_is_weak_signal():
    assert classify([100, 160, 150, 170], favourites=[5, 5, 5, 5])["category"] == "weak_signal"


def test_small_supporting_change_does_not_count():
    r = classify([100, 160, 150, 170], favourites=[1, 2, 2, 2])
    assert r["category"] == "weak_signal"
    assert r["supporting_metrics"][0]["qualifies_as_support"] is False


def test_jump_too_recent_is_emerging():
    assert classify([100, 100, 101, 160], favourites=[5, 5, 5, 9])["category"] == "emerging_increase"


def test_missing_primary_value_is_insufficient_evidence_not_skipped():
    r = classify([100, 160, None, 170], favourites=[5, 9, 9, 10])
    assert r["category"] == "insufficient_evidence"
    assert r["category"] != "sustained_growth"


def test_unknown_support_only_is_insufficient_evidence():
    r = classify([100, 160, 150, 170], unique_artwork_viewers=[50, None, 60, 70], favourites=[5, 5, 5, 5])
    assert r["category"] == "insufficient_evidence"


def test_unknown_support_is_listed_when_other_support_exists():
    r = classify([100, 160, 150, 170], unique_artwork_viewers=[50, None, 60, 70], favourites=[5, 9, 9, 9])
    assert (r["category"], r["evidence_strength"]) == ("sustained_growth", "moderate-confidence")
    assert any("could not be verified" in lim for lim in r["limitations"])


def test_flat_but_not_stable_is_no_clear_pattern():
    assert classify([100, 80, 70, 60])["category"] == "no_clear_pattern"


def test_rules_are_configurable():
    strict = {**PATTERN_RULES, "min_increase_pct": 150.0}
    r = classify_series(DATES, [40, 80, 76, 90], {"favourites": [5, 12, 11, 13]}, "artwork_views", strict)
    assert r["category"] != "sustained_growth"


# --- validate_evidence -----------------------------------------------------------

def a1_insight(**overrides):
    insight = {
        "signal_type": "sustained_growth",
        "artwork_id": "A001",
        "title": "Artwork A1 engagement increased and stayed higher",
        "observed_signal": "Artwork views rose from 40 to 80 (+100%) between 2026-10-14 and 2026-10-15, "
                           "with daily unique viewers 30 to 45 (+50%) and favourites 5 to 12 (+140%).",
        "why_it_may_matter": "Several engagement signals rose together and views stayed higher on later days.",
        "suggested_next_step": "Consider reviewing Artwork A1 in the next internal sales discussion.",
        "confidence": "moderate",
        "limitations": ["Engagement is not evidence of purchase intent.",
                        "Inquiries did not change (0 to 0)."],
        "metric_changes": [
            {"artwork_id": "A001", "metric": m, "old_date": D1, "new_date": D2,
             "old_value": o, "new_value": n, "absolute_change": n - o, "percentage_change": p}
            for m, o, n, p in [("artwork_views", 40, 80, 100.0), ("unique_artwork_viewers", 30, 45, 50.0),
                               ("favourites", 5, 12, 140.0), ("inquiries", 0, 0, None)]
        ],
    }
    insight.update(overrides)
    return insight


def test_valid_a1_insight_passes():
    r = validate_evidence(a1_insight())
    assert r["valid"], r["errors"]
    assert r["insight_id"] == "INS-A001-SUSTAINED_GROWTH-20261014_20261015"
    assert all(c["verified"] for c in r["checked_claims"])


def test_wrong_percentage_rejected():
    bad = a1_insight()
    bad["metric_changes"][0]["percentage_change"] = 90.0
    r = validate_evidence(bad)
    assert not r["valid"]
    assert any("percentage_change claimed 90.0" in e for e in r["errors"])


def test_percentage_on_zero_baseline_rejected():
    bad = a1_insight()
    bad["metric_changes"][3]["percentage_change"] = 0.0
    assert not validate_evidence(bad)["valid"]


def test_day5_evidence_rejected():
    bad = a1_insight()
    bad["metric_changes"][0].update(old_date=D4, new_date=D5)
    r = validate_evidence(bad)
    assert any("day_processed=false" in e for e in r["errors"])


def test_unverified_number_in_text_rejected():
    r = validate_evidence(a1_insight(observed_signal="Artwork views rose to 436 events."))
    assert any("number 436" in e for e in r["errors"])


def test_causal_and_purchase_claims_rejected_but_negations_allowed():
    r = validate_evidence(a1_insight(why_it_may_matter="The marketing campaign caused this, showing purchase intent."))
    assert any("causal claim" in e for e in r["errors"])
    assert any("purchase intent" in e for e in r["errors"])
    ok = validate_evidence(a1_insight(why_it_may_matter="Signals rose together, but this does not show purchase intent."))
    assert ok["valid"], ok["errors"]


def test_commercial_next_step_rejected():
    r = validate_evidence(a1_insight(suggested_next_step="Offer a discount and contact collectors."))
    assert any("outside the agent's authority" in e for e in r["errors"])


def test_missing_limitations_rejected():
    assert not validate_evidence(a1_insight(limitations=[]))["valid"]


def test_artist_total_insight_and_unique_people_claim():
    insight = {
        "signal_type": "sustained_growth", "artist_id": "AR01",
        "title": "Artist A artworks received 416 view events",
        "observed_signal": "A001 had 286 and A002 had 130 view events: 416 combined view events.",
        "why_it_may_matter": "Both artworks by Artist A show sustained increases.",
        "confidence": "moderate",
        "limitations": ["416 is a count of view events, not 416 unique visitors."],
        "metric_totals": [{"scope": "artist", "id": "AR01", "metric": "artwork_views", "total": 416}],
    }
    assert validate_evidence(insight)["valid"]
    bad = {**insight, "observed_signal": "416 different people viewed Artist A's artworks."}
    assert any("distinct-people" in e for e in validate_evidence(bad)["errors"])
