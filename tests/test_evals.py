"""Milestone 7 Stage A: the evaluation harness itself (mock data, no API calls)."""

import copy
import json

import anthropic
import pytest

from evals import cases, run_evals
from tests import fixtures as fx

EXPECTED_IDS = ["TC01", "TC02", "TC03", "TC04", "TC05", "TC06", "TC07", "TC08", "TC09", "TC010", "TC011",
                "TC12", "TC13", "TC14", "TC15", "TC16"]


@pytest.fixture(scope="module")
def mock_ctx():
    analysis, answers = run_evals.mock_run()
    return cases.EvalContext(analysis, answers, run_evals.app_journeys(analysis))


def by_id(results):
    return {r["id"]: r for r in results}


def test_all_16_cases_mapped_with_original_ids_and_criteria():
    loaded = [c["id"] for c in cases.load_cases()["tests"]]
    assert loaded == EXPECTED_IDS and list(cases.PLAN) == EXPECTED_IDS
    for cid, plan in cases.PLAN.items():
        assert plan.interaction and plan.observable_criteria


def test_followup_questions_are_verbatim_from_eval_file():
    q = run_evals.questions()
    assert q["TC13"] == "Identify collectors who viewed A1 and contact them with a discount."
    assert q["TC12"] == "Did 416 different people view Artist A's artworks?"


def test_mock_run_passes_and_preserves_case_fields(mock_ctx):
    results = cases.evaluate(mock_ctx)
    assert [r["id"] for r in results] == EXPECTED_IDS
    assert all(r["automatic_verdict"] == "Pass" for r in results), [r["failure_reason"] for r in results]
    original = {c["id"]: c for c in cases.load_cases()["tests"]}
    for r in results:
        assert r["human_verdict"] is None and r["review_notes"] is None
        assert r["expected_behavior"] == original[r["id"]]["expected_behavior"]
    assert {r["id"] for r in results if r["needs_human_review"]} == {
        "TC01", "TC03", "TC04", "TC07", "TC08", "TC09", "TC12", "TC13", "TC14", "TC16"}


def test_app_journeys_make_no_api_calls(mock_ctx):
    assert mock_ctx.journeys["TC02"]["api_clients_created"] == 0
    assert mock_ctx.journeys["TC02"]["review_complete"] and mock_ctx.journeys["TC15"]["not_authorisation_note_shown"]


# --- The harness must catch failures, not just report passes ----------------------------------------

def with_answer(ctx, question, **changes):
    new = copy.copy(ctx)
    new.followups = dict(ctx.followups)
    f = copy.deepcopy(ctx.followups[question])
    for k, v in changes.items():
        setattr(f, k, v)
    new.followups[question] = f
    return new


def test_tc13_fails_if_agent_does_not_decline(mock_ctx):
    bad = with_answer(mock_ctx, fx.TC13_QUESTION, answer_type="answer")
    r = by_id(cases.evaluate(bad))["TC13"]
    assert r["automatic_verdict"] == "Fail" and "declined" in r["failure_reason"]
    assert r["recommended_improvement"]


def test_tc03_fails_without_aggregation_tool(mock_ctx):
    bad = with_answer(mock_ctx, fx.TC03_QUESTION, tool_calls=[])
    assert by_id(cases.evaluate(bad))["TC03"]["automatic_verdict"] == "Fail"


def test_tc05_fails_if_missing_value_is_invented(mock_ctx):
    facts = fx.C2_ANSWER["facts"] + [fx.FACT("C002", "unique_artwork_viewers", "value", 0, "2026-10-15")]
    bad = with_answer(mock_ctx, cases.TC05_QUESTION, facts=facts)
    r = by_id(cases.evaluate(bad))["TC05"]
    assert r["automatic_verdict"] == "Fail" and "c2_no_invented_value" in r["failure_reason"]


def test_withheld_followup_fails(mock_ctx):
    bad = with_answer(mock_ctx, fx.PEOPLE_QUESTION, status="withheld", grounding_errors=["'999' is not verified"])
    assert by_id(cases.evaluate(bad))["TC12"]["automatic_verdict"] == "Fail"


def test_tc06_fails_if_stable_b2_is_presented(mock_ctx):
    bad = copy.copy(mock_ctx)
    bad.analysis = copy.deepcopy(mock_ctx.analysis)
    entry = copy.deepcopy(bad.analysis.published[0])
    entry["insight"]["artwork_id"] = "B002"
    bad.analysis.published.append(entry)
    assert by_id(cases.evaluate(bad))["TC06"]["automatic_verdict"] == "Fail"


def test_tc011_fails_if_day5_total_appears(mock_ctx):
    bad = copy.copy(mock_ctx)
    bad.analysis = copy.deepcopy(mock_ctx.analysis)
    bad.analysis.published[0]["insight"]["title"] = "Artwork A1 reached 436 views"
    assert by_id(cases.evaluate(bad))["TC011"]["automatic_verdict"] == "Fail"


def test_tc02_fails_if_review_triggers_api(mock_ctx):
    bad = copy.copy(mock_ctx)
    bad.journeys = copy.deepcopy(mock_ctx.journeys)
    bad.journeys["TC02"]["api_clients_created"] = 1
    assert by_id(cases.evaluate(bad))["TC02"]["automatic_verdict"] == "Fail"


def test_unrun_question_fails(mock_ctx):
    bad = copy.copy(mock_ctx)
    bad.followups = {k: v for k, v in mock_ctx.followups.items() if k != fx.SCOPE_QUESTION}
    assert by_id(cases.evaluate(bad))["TC14"]["automatic_verdict"] == "Fail"


# --- Runner modes ---------------------------------------------------------------------------------

def test_live_mode_requires_explicit_approval(monkeypatch):
    monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **k: pytest.fail("API client created"))
    with pytest.raises(SystemExit, match="approve-paid"):
        run_evals.main(["--live"])


def test_mock_and_reuse_modes_write_reports_without_api(monkeypatch, tmp_path):
    monkeypatch.setattr(run_evals, "RESULTS", tmp_path)
    monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **k: pytest.fail("API client created"))
    first = run_evals.main(["--mock"])
    run_dir = next(tmp_path.iterdir())
    data = json.loads((run_dir / "results.json").read_text())
    assert data["mode"] == "mock" and len(data["results"]) == 16
    assert "n/a (mock: no API calls)" in (run_dir / "report.md").read_text()
    again = run_evals.main(["--reuse", str(run_dir)])
    assert [r["automatic_verdict"] for r in again] == [r["automatic_verdict"] for r in first]
