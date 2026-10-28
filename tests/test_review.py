"""Milestone 5 tests: evidence-view tracking, usefulness feedback and the completion condition."""

import copy
from pathlib import Path

import anthropic
import pytest
from streamlit.testing.v1 import AppTest

from gia import config, review, snapshot
from tests.fixtures import mock_three_insight_result
from tests.test_agent import final, run

APP = str(Path(__file__).resolve().parent.parent / "app.py")
A1 = "INS-A001-SUSTAINED_GROWTH-20261014_20261015"
A2 = "INS-A002-SUSTAINED_GROWTH-20261014_20261015"
B1 = "INS-B001-TEMPORARY_SPIKE-20261014_20261015"


@pytest.fixture
def state():
    return review.start_review(mock_three_insight_result())


# --- Review state (pure logic) ------------------------------------------------------------

def test_insight_ids_are_stable_across_runs():
    first = [p["insight_id"] for p in mock_three_insight_result().published]
    second = [p["insight_id"] for p in mock_three_insight_result().published]
    assert first == second == [A1, A2, B1]


def test_happy_path_completes_on_same_insight(state):
    state.record_evidence_view(A1)
    assert not state.complete
    state.record_feedback(A1, "useful")
    assert state.complete and state.completed_ids() == [A1]


def test_not_useful_also_completes(state):
    state.record_evidence_view(B1)
    state.record_feedback(B1, "not_useful")
    assert state.complete


def test_evidence_alone_or_feedback_alone_does_not_complete(state):
    state.record_evidence_view(A1)
    state.record_feedback(A2, "useful")
    assert not state.complete                     # different insights
    p = state.progress()
    assert (p["evidence_viewed"], p["rated"], p["complete"]) == (1, 1, False)


def test_feedback_before_evidence_completes_once_evidence_is_viewed(state):
    state.record_feedback(A2, "useful")
    assert not state.complete
    state.record_evidence_view(A2)
    assert state.completed_ids() == [A2]


def test_latest_feedback_counts(state):
    state.record_feedback(A1, "useful")
    state.record_feedback(A1, "not_useful")
    assert state.reviews[A1].feedback == "not_useful"
    assert state.progress()["useful"] == 0


def test_feedback_is_tied_to_the_right_insight(state):
    state.record_feedback(A2, "useful")
    assert state.reviews[A2].feedback == "useful"
    assert state.reviews[A1].feedback is None and state.reviews[B1].feedback is None


@pytest.mark.parametrize("insight_id", ["INS-B002-STABLE", "INS-Z999-SUSTAINED_GROWTH-20261014_20261015", ""])
def test_feedback_only_for_validated_insights(state, insight_id):
    with pytest.raises(review.ReviewError):
        state.record_feedback(insight_id, "useful")
    with pytest.raises(review.ReviewError):
        state.record_evidence_view(insight_id)


@pytest.mark.parametrize("option", ["approve", "Useful", "contact_collectors", ""])
def test_only_two_feedback_options(state, option):
    with pytest.raises(review.ReviewError):
        state.record_feedback(A1, option)


def test_no_validated_insights_can_never_complete():
    result, _ = run([final([])])
    state = review.start_review(result)
    assert state.insight_ids == [] and not state.complete


def test_feedback_note_states_it_is_not_authorisation():
    assert "does not approve, authorise or trigger any action" in review.NOT_AUTHORISATION_NOTE
    assert "not saved permanently" in review.SESSION_ONLY_NOTE


# --- The app, in LIVE and DEMO, with no API calls ------------------------------------------

def app_for(monkeypatch, mode, result):
    settings = {"GIA_MODE": mode, "ANTHROPIC_API_KEY": "sk-ant-test-0000"}
    monkeypatch.setattr(config, "_setting", lambda name: settings.get(name))
    monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **k: pytest.fail("API client created"))
    at = AppTest.from_file(APP)
    at.session_state["analysis"] = result
    return at.run(timeout=30)


def results_for(tmp_path):
    live = mock_three_insight_result()
    demo = snapshot.load_snapshot(snapshot.save_snapshot(copy.deepcopy(live), tmp_path / "snap.json"))
    return {"live": live, "demo": demo}


def click(at, key):
    at.button(key=key).click().run(timeout=30)
    assert not at.exception, at.exception


def messages(at):
    return [m.value for m in at.success] + [m.value for m in at.info]


@pytest.mark.parametrize("mode", ["live", "demo"])
def test_full_journey_in_app(monkeypatch, tmp_path, mode):
    at = app_for(monkeypatch, mode, results_for(tmp_path)[mode])
    assert any("Review progress" in m for m in messages(at))
    click(at, f"evidence-{A1}")
    click(at, f"feedback-useful-{A1}")
    done = next(m for m in at.success if "review complete" in m.value)
    assert "Harbour at First Light" in done.value and "Nothing has been sent or changed" in done.value
    for word in ("approved", "authorised", "contacted", "sent to", "will"):
        assert word not in done.value.lower().replace("nothing has been sent", "")
    saved = next(m for m in at.success if m.value.startswith("Feedback saved for the Harbour at First Light insight"))
    assert "Useful / Worth investigating" in saved.value and "does not approve" in saved.value
    state = at.session_state["review"]
    assert state.reviews[A1].feedback == "useful" and state.reviews[A1].evidence_viewed


@pytest.mark.parametrize("mode", ["live", "demo"])
def test_feedback_on_a_different_insight_does_not_complete(monkeypatch, tmp_path, mode):
    at = app_for(monkeypatch, mode, results_for(tmp_path)[mode])
    click(at, f"evidence-{A1}")
    click(at, f"feedback-not_useful-{A2}")
    assert not any("review complete" in m.value for m in at.success)
    assert any("evidence viewed for 1 of 3" in m and "feedback recorded for 1 of 3" in m for m in messages(at))
    assert any("also open its evidence" in c.value for c in at.caption)


def test_live_and_demo_journeys_are_identical(monkeypatch, tmp_path):
    texts = {}
    for mode, result in results_for(tmp_path).items():
        at = app_for(monkeypatch, mode, result)
        click(at, f"evidence-{B1}")
        click(at, f"feedback-not_useful-{B1}")
        texts[mode] = [m.value for m in at.success]
    assert texts["live"] == texts["demo"]


def test_changing_feedback_updates_the_record(monkeypatch, tmp_path):
    at = app_for(monkeypatch, "demo", results_for(tmp_path)["demo"])
    click(at, f"feedback-useful-{A1}")
    click(at, f"feedback-not_useful-{A1}")
    assert at.session_state["review"].reviews[A1].feedback == "not_useful"
    assert at.button(key=f"feedback-not_useful-{A1}").label.startswith("✓")


def test_new_analysis_starts_a_fresh_review(monkeypatch, tmp_path):
    path = snapshot.save_snapshot(mock_three_insight_result(), tmp_path / "snap.json")
    settings = {"GIA_DEMO_SNAPSHOT": str(path)}
    monkeypatch.setattr(config, "_setting", lambda name: settings.get(name))
    monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **k: pytest.fail("API client created"))
    at = AppTest.from_file(APP).run(timeout=30)
    at.button[0].click().run(timeout=30)                 # Analyze (replay)
    click(at, f"evidence-{A1}")
    click(at, f"feedback-useful-{A1}")
    assert at.session_state["review"].complete
    at.button[0].click().run(timeout=30)                 # Analyze again
    assert not at.session_state["review"].complete
    assert at.session_state["review"].progress()["rated"] == 0
