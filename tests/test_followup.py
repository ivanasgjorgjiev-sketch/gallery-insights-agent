"""Milestone 6 tests: grounded follow-up questions (mocked API, no cost)."""

import copy
import json
from pathlib import Path

import anthropic
import httpx2
import pytest
from streamlit.testing.v1 import AppTest

from gia import agent, config, followup, snapshot
from tests import fixtures as fx
from tests.test_agent import FakeClient, response, text, tool_use

APP = str(Path(__file__).resolve().parent.parent / "app.py")
PUBLISHED = fx.mock_three_insight_result().published


def answer_with(answer, tool_script=(), question="q"):
    return fx.mock_followup(question, answer, list(tool_script))


ARTIST_TOOL = [response("tool_use", tool_use("aggregate_artist_metrics",
                                             {"artist_id": "AR01", "metrics": ["artwork_views"]}, "f1"))]
A1_TOOL = [response("tool_use", tool_use("get_artwork_metrics", {"artwork_id": "A001", "metrics": None}, "f1"))]


# --- Grounded answers -------------------------------------------------------------------

def test_tc03_grounded_answer_uses_tool_and_is_shown():
    f = fx.mock_tc03_followup()
    assert f.status == "answered" and f.answer_type == "answer"
    assert f.tool_calls == [{"tool": "aggregate_artist_metrics",
                             "arguments": {"artist_id": "AR01", "metrics": ["artwork_views"]}}]
    assert "416" in f.answer and "not of 416 different people" in f.answer
    assert [s.kind for s in f.trace][-1] == "gate"


def test_number_not_in_tool_output_is_withheld():
    f = answer_with({"answer_type": "answer", "answer": "Artist A received 420 view events.", "limitations": []},
                    ARTIST_TOOL)
    assert f.status == "withheld" and "'420' is not a verified value" in f.grounding_errors[0]


def test_quantitative_answer_without_a_tool_call_is_withheld():
    f = answer_with({"answer_type": "answer", "answer": "Artwork A1 had 286 views in total.", "limitations": []})
    assert f.tool_calls == [] and f.status == "withheld"


def test_numbers_from_verified_insights_may_be_reused_without_new_tool_call():
    f = answer_with({"answer_type": "answer", "answer": "A1's views went from 40 to 80 (+100.0%) on Oct 15.",
                     "limitations": []})
    assert f.status == "answered"


def test_day5_values_can_never_be_grounded():
    f = answer_with({"answer_type": "answer", "answer": "On 2026-10-18 Artwork A1 had 150 views.",
                     "limitations": []}, A1_TOOL)
    assert f.status == "withheld" and any("150" in e for e in f.grounding_errors)


def test_missing_value_answer_says_unknown():
    f = fx.mock_c2_followup()
    assert f.status == "answered" and "not recorded" in f.answer and "unavailable" in f.answer


def test_limitations_are_checked_too():
    f = answer_with({"answer_type": "answer", "answer": "Artist A received 416 view events.",
                     "limitations": ["About 999 visitors were involved."]}, ARTIST_TOOL)
    assert f.status == "withheld"


@pytest.mark.parametrize("bad,problem", [
    ("416 different people viewed Artist A's artworks.", "distinct-people"),
    ("The marketing campaign caused the increase.", "causal claim"),
    ("This shows purchase intent for Artwork A1.", "purchase intent"),
    ("I recommend a discount on Artwork A1.", "commercial action"),
])
def test_prohibited_claims_in_answers_are_withheld(bad, problem):
    f = answer_with({"answer_type": "answer", "answer": bad, "limitations": []}, ARTIST_TOOL)
    assert f.status == "withheld" and any(problem in e for e in f.grounding_errors)


@pytest.mark.parametrize("ok", [
    "There is no campaign data, so I can't say whether a campaign caused the increase.",
    "416 is a count of view events, not 416 different people.",
])
def test_negated_boundaries_are_allowed(ok):
    f = answer_with({"answer_type": "answer", "answer": ok, "limitations": [],
                     "facts": [fx.FACT("AR01", "artwork_views", "total", 416)]}, ARTIST_TOOL)
    assert f.status == "answered", f.grounding_errors


# --- Refusals and clarifications ---------------------------------------------------------

def test_refusal_may_repeat_the_managers_own_numbers():
    f = fx.mock_refusal_followup()
    assert f.status == "answered" and f.answer_type == "refusal" and "10% discount" in f.answer


def test_ambiguous_best_question_gets_clarification():
    f = fx.mock_best_followup()
    assert f.answer_type == "clarification" and "no single overall score" in f.answer


def test_answer_numbers_from_the_question_are_not_grounded_for_answers():
    f = fx.mock_followup("Did 999 people view A1?", {"answer_type": "answer", "answer": "Yes, 999 people did.",
                                                      "limitations": []})
    assert f.status == "withheld"


def test_prompt_states_every_boundary():
    prompt = followup.SYSTEM_PROMPT.lower()
    for phrase in ("collector identities", "contacting anyone", "sales predictions", "causes",
                   "pricing or discounts", "other galleries", "last year", "unknown, never zero",
                   "never summed", "processed fair days only"):
        assert phrase in prompt


# --- Bounds, errors and cost protection ------------------------------------------------------

def test_requests_have_explicit_output_cap_and_only_approved_tools():
    client = FakeClient(ARTIST_TOOL + [response("end_turn", text(json.dumps(fx.TC03_ANSWER)))])
    followup.run_followup(client, fx.MOCK_MODEL, "q", PUBLISHED, max_output_tokens=4000)
    req = client.requests[0]
    assert req["max_tokens"] == 4000
    assert [t["name"] for t in req["tools"]] == list(agent.TOOL_FUNCTIONS)
    assert "fallbacks" not in req and "tool_choice" not in req


def test_tool_call_limit_forces_an_answer():
    script = [response("tool_use", tool_use("get_processed_data", {}, f"t{i}")) for i in range(3)]
    script.append(response("end_turn", text(json.dumps(fx.BEST_ANSWER))))
    client = FakeClient(script)
    f = followup.run_followup(client, fx.MOCK_MODEL, "q", PUBLISHED, max_tool_calls=2)
    assert len(f.tool_calls) == 2 and any(s.kind == "limit" for s in f.trace)
    assert client.requests[-1]["tool_choice"] == {"type": "none"}


def test_cost_cap_stops_the_question():
    client = FakeClient(ARTIST_TOOL * 3 + [response("end_turn", text(json.dumps(fx.TC03_ANSWER)))])
    f = followup.run_followup(client, fx.MOCK_MODEL, "q", PUBLISHED, max_cost_usd=0.005)
    assert f.status == "budget_exceeded" and not f.shown and len(client.requests) == 2


@pytest.mark.parametrize("question", ["", "   ", "x" * 501])
def test_invalid_questions_make_no_api_call(question):
    client = FakeClient([])
    f = followup.run_followup(client, fx.MOCK_MODEL, question, PUBLISHED)
    assert f.status == "failed" and client.requests == []


def test_api_error_is_reported_cleanly():
    err = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))
    f = followup.run_followup(FakeClient([err]), fx.MOCK_MODEL, "q", PUBLISHED)
    assert f.status == "failed" and "Could not reach" in f.error


def test_unknown_tool_is_rejected():
    client = FakeClient([response("tool_use", tool_use("update_price", {"artwork_id": "A001"}, "t1")),
                         response("end_turn", text(json.dumps(fx.REFUSAL_ANSWER)))])
    f = followup.run_followup(client, fx.MOCK_MODEL, fx.REFUSAL_QUESTION, PUBLISHED)
    assert f.tool_calls == [] and any(s.kind == "tool_error" for s in f.trace)


def test_context_includes_insights_selection_and_recent_answers():
    prior = fx.mock_tc03_followup()
    ctx = followup.build_context(PUBLISHED, "INS-A001-SUSTAINED_GROWTH-20261014_20261015", [prior])
    assert "INS-A002-SUSTAINED_GROWTH" in ctx and "about insight INS-A001" in ctx
    assert fx.TC03_QUESTION in ctx and "re-check numbers with tools" in ctx


# --- Recorded examples for DEMO mode ------------------------------------------------------------

def recording_with_followups(tmp_path, followups):
    return snapshot.save_snapshot(fx.mock_three_insight_result(), tmp_path / "snap.json", followups=followups)


def test_only_shown_answers_are_recorded_and_replay_reverifies(tmp_path):
    withheld = answer_with({"answer_type": "answer", "answer": "Artist A had 999 views.", "limitations": []},
                           ARTIST_TOOL, question="Withheld question")
    path = recording_with_followups(tmp_path, [fx.mock_tc03_followup(), fx.mock_refusal_followup(), withheld])
    assert "Withheld question" not in path.read_text()
    replay = snapshot.load_snapshot(path)
    assert [f.question for f in replay.followup_examples] == [fx.TC03_QUESTION, fx.REFUSAL_QUESTION]
    assert all(f.recorded_at for f in replay.followup_examples)
    assert replay.followup_examples[0].trace[0].tool == "aggregate_artist_metrics"   # re-run, not copied


def test_tampered_recorded_answer_is_dropped(tmp_path):
    path = recording_with_followups(tmp_path, [fx.mock_tc03_followup()])
    snap = json.loads(path.read_text())
    snap["followups"][0]["answer"] = snap["followups"][0]["answer"].replace("416", "461")
    path.write_text(json.dumps(snap))
    assert snapshot.load_snapshot(path).followup_examples == []


# --- The app: LIVE and DEMO separation, review state untouched ------------------------------------
# Open-ended follow-ups are hidden in the M8 MVP; these tests switch them back on to keep the preserved
# implementation covered.
FOLLOWUPS_ON = {"GIA_ENABLE_FOLLOWUPS": "1"}


def app(monkeypatch, settings, result):
    monkeypatch.setattr(config, "_setting", lambda name: settings.get(name))
    at = AppTest.from_file(APP)
    at.session_state["analysis"] = result
    return at


def test_demo_shows_recorded_examples_without_input_or_api(monkeypatch, tmp_path):
    path = recording_with_followups(tmp_path, [fx.mock_tc03_followup(), fx.mock_best_followup()])
    monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **k: pytest.fail("API client created"))
    at = app(monkeypatch, {"ANTHROPIC_API_KEY": "sk-ant-test-0000", **FOLLOWUPS_ON},
             snapshot.load_snapshot(path)).run(timeout=30)
    assert not at.exception
    assert len(at.text_area) == 0                                         # no free-form questions in DEMO
    assert any("free-form questions are available only in the live version" in c.value for c in at.caption)
    assert sum("Recorded answer from the live session" in c.value for c in at.caption) == 2
    assert any(fx.TC03_QUESTION in m.value for m in at.markdown)


def test_live_question_runs_tools_and_leaves_review_unchanged(monkeypatch):
    script = ARTIST_TOOL + [response("end_turn", text(json.dumps(fx.TC03_ANSWER)))]
    monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **k: FakeClient(copy.deepcopy(script)))
    result = fx.mock_three_insight_result()
    at = app(monkeypatch, {"GIA_MODE": "live", "ANTHROPIC_API_KEY": "sk-ant-test-0000", **FOLLOWUPS_ON},
             result).run(timeout=30)
    before = copy.deepcopy(at.session_state["review"].progress())
    at.text_area[0].input(fx.TC03_QUESTION)
    at.button(key="FormSubmitter:followup-form-Ask").click().run(timeout=30)
    assert not at.exception, at.exception
    asked = at.session_state["followups"]
    assert len(asked) == 1 and asked[0].status == "answered"
    assert at.session_state["review"].progress() == before               # questions never change review
    assert any("not of 416 different people" in m.value for m in at.markdown)


def test_live_followup_session_limit(monkeypatch):
    monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **k: pytest.fail("API client created"))
    at = app(monkeypatch, {"GIA_MODE": "live", "ANTHROPIC_API_KEY": "sk-ant-test-0000",
                           "GIA_MAX_FOLLOWUPS_PER_SESSION": "2", **FOLLOWUPS_ON}, fx.mock_three_insight_result())
    at.session_state["followups_asked"] = 2
    at.run(timeout=30)
    assert len(at.text_area) == 0
    assert any("limit of 2 follow-up questions" in c.value for c in at.caption)


def test_live_without_key_has_no_question_box(monkeypatch):
    at = app(monkeypatch, {"GIA_MODE": "live", **FOLLOWUPS_ON}, fx.mock_three_insight_result()).run(timeout=30)
    assert len(at.text_area) == 0
