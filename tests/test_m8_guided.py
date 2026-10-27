"""Milestone 8 evaluation suite: guided insight exploration. Offline, deterministic, no API.

The case matrix and checks live in evals/m8_cases.py (shared with the human-review document).
The 16 Milestone 7 cases are separate and unchanged."""

import copy
import json
import socket

import anthropic
import pytest

from evals import m8_cases as m8
from gia import agent, config, guided, review, snapshot, tools
from tests import fixtures as fx
from tests.test_followup import app

CASES = [(row, q) for row in m8.ROWS for q in m8.QUESTION_IDS]


# --- The case matrix: every publishable pattern type x four questions -------------------------------

@pytest.mark.parametrize("row,question_id", CASES, ids=[f"{r.case}-{q}" for r, q in CASES])
def test_guided_answer_passes_all_checks(row, question_id):
    with m8.source_for(row):
        entry = m8.entry_for(row)
        assert entry["pattern"]["category"] == row.category
        assert entry["insight"]["confidence"] == row.strength
        ans = guided.answer(entry, question_id)
        failed = [f"{c.name}: {c.detail}" for c in m8.check_answer(row, entry, ans) if not c.passed]
    assert not failed, (ans.text, failed)


def test_matrix_covers_every_publishable_pattern_type():
    publishable = {c for c, handling in tools.HANDLING.items() if handling != "suppress"}
    assert {r.category for r in m8.ROWS} == publishable
    assert len(CASES) == 28 and sum(r.source == "real" for r in m8.ROWS) * 4 == 20


def test_suppressed_patterns_never_get_a_card_or_questions():
    ids = {e["insight"]["artwork_id"] for e in m8.published_entries()}
    assert not ids & {artwork for _, artwork, _ in m8.SUPPRESSED}


def test_answers_do_not_depend_on_other_insights():
    alone = m8.published_entries(["A001"])[0]
    together = next(e for e in m8.published_entries() if e["insight_id"] == alone["insight_id"])
    assert [a.text for a in guided.answers(alone)] == [a.text for a in guided.answers(together)]


# --- Fail closed: altered or inconsistent data is never explained -------------------------------------

def _tampered(change):
    entry = copy.deepcopy(m8.entry_for(m8.ROWS[0]))
    change(entry["pattern"])
    return entry


@pytest.mark.parametrize("change", [
    lambda p: p["daily"][1].update(value=85),                                   # wrong daily value
    lambda p: p["key_comparison"].update(new_value=85),                         # wrong key comparison
    lambda p: p["supporting_metrics"][0].update(new_value=50),                  # wrong supporting value
    lambda p: p.update(category="temporary_spike"),                             # wrong classification
    lambda p: p.update(evidence_strength="moderate-confidence"),                # wrong strength
    lambda p: p.update(key_comparison=None),                                    # no comparison at all
], ids=["daily", "key", "support", "category", "strength", "no-comparison"])
def test_tampered_pattern_is_not_explained(change):
    for ans in guided.answers(_tampered(change)):
        assert not ans.shown and ans.problems


@pytest.mark.parametrize("text,question_id,problem", [
    ("Views rose to 95 on Oct 15.", "trend", "'95'"),
    ("Collectors intend to buy this artwork.", "relevance", "purchase intent"),
    ("Contact the collectors who viewed it.", "next", "commercial action"),
    ("Find out what caused the jump.", "next", "cause-seeking"),
    ("Views on Oct 18 were higher.", "trend", "excluded date 2026-10-18 is used as data"),
    ("Views on Oct 18 were higher than ever, though Oct 18 is excluded.", "trend", None),   # named as excluded
])
def test_unsafe_or_unsupported_text_is_rejected(text, question_id, problem):
    problems = guided.check(text, [], question_id)
    if problem is None:      # the date rule alone allows a sentence that calls the day excluded
        assert not guided.date_problems(text)
    else:
        assert any(problem in p for p in problems), problems


# --- DEMO and LIVE show the same answers ------------------------------------------------------------

def test_demo_replay_answers_match_live(tmp_path):
    live = fx.mock_three_insight_result()
    path = snapshot.save_snapshot(live, path=tmp_path / "rec.json")
    demo = snapshot.load_snapshot(path)
    for a, b in zip(live.published, demo.published):
        assert [x.text for x in guided.answers(a)] == [x.text for x in guided.answers(b)]


# --- The app: four questions per card, no free text, no API, review journey intact --------------------

LIVE = {"GIA_MODE": "live", "ANTHROPIC_API_KEY": "sk-ant-test-0000"}


@pytest.fixture
def no_api_no_network(monkeypatch):
    monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **k: pytest.fail("API client created"))

    def blocked(*a, **k):
        raise AssertionError("network access attempted")
    monkeypatch.setattr(socket.socket, "connect", blocked)


def guided_expanders(at):
    labels = [q for _, q in guided.QUESTIONS]
    return [e for e in at.expander if e.label in labels]


def explore_all(at, result):
    """M9: the guided questions appear only after "Explore insight" is clicked on a card."""
    for entry in result.published:
        at.button(key=f"explore-{entry['insight_id']}").click().run(timeout=30)
    return at


def test_live_cards_show_four_questions_in_order_without_api(monkeypatch, no_api_no_network):
    result = fx.mock_three_insight_result()
    at = explore_all(app(monkeypatch, LIVE, result).run(timeout=30), result)
    assert not at.exception, at.exception
    found = [e.label for e in guided_expanders(at)]
    assert found == [q for _, q in guided.QUESTIONS] * len(result.published)
    text = " ".join(m.value for m in at.markdown)
    assert "Views by day: Oct 14: 40, Oct 15: 80, Oct 16: 76, Oct 17: 90." in text
    assert guided.UNAVAILABLE not in " ".join(w.value for w in at.warning)
    assert len(at.text_area) == 0                                        # no free-text follow-ups
    assert "analyses_run" not in at.session_state                      # no new analysis was started
    assert "followups_asked" not in at.session_state


def test_demo_cards_show_four_questions_without_api(monkeypatch, tmp_path, no_api_no_network):
    path = snapshot.save_snapshot(fx.mock_three_insight_result(), path=tmp_path / "rec.json")
    demo = snapshot.load_snapshot(path)
    at = explore_all(app(monkeypatch, {"ANTHROPIC_API_KEY": "sk-ant-test-0000"}, demo).run(timeout=30), demo)
    assert not at.exception, at.exception
    assert len(guided_expanders(at)) == 12 and len(at.text_area) == 0


def test_guided_answers_do_not_change_review_and_completion_rule_holds(monkeypatch, no_api_no_network):
    result = fx.mock_three_insight_result()
    at = app(monkeypatch, LIVE, result).run(timeout=30)
    a1, a2 = (e["insight_id"] for e in result.published[:2])
    state = at.session_state["review"]
    assert state.progress()["evidence_viewed"] == 0 and state.progress()["rated"] == 0
    for _ in range(3):                                              # re-render (opening/closing/switching)
        at.run(timeout=30)
    assert at.session_state["review"].progress()["evidence_viewed"] == 0
    option = next(iter(review.FEEDBACK_OPTIONS))
    at.button(key=f"evidence-{a1}").click().run(timeout=30)            # evidence on A1 ...
    at.button(key=f"feedback-{option}-{a2}").click().run(timeout=30)   # ... feedback on A2
    assert not at.session_state["review"].complete
    at.button(key=f"feedback-{option}-{a1}").click().run(timeout=30)  # same insight -> complete
    assert at.session_state["review"].complete
    assert any(review.NOT_AUTHORISATION_NOTE in s.value for s in at.success)
    assert not at.exception


def test_failed_answer_is_not_shown_in_the_app(monkeypatch, no_api_no_network):
    monkeypatch.setattr(guided, "check", lambda *a, **k: ["forced failure"])
    result = fx.mock_three_insight_result()
    at = explore_all(app(monkeypatch, LIVE, result).run(timeout=30), result)
    assert sum(guided.UNAVAILABLE in w.value for w in at.warning) == 12
    assert "Views by day" not in " ".join(m.value for m in at.markdown)


def test_followups_hidden_by_default_and_setting_is_explicit(monkeypatch):
    monkeypatch.setattr(config, "_setting", lambda name: {}.get(name))
    assert config.followups_enabled() is False
    monkeypatch.setattr(config, "_setting", lambda name: {"GIA_ENABLE_FOLLOWUPS": "1"}.get(name))
    assert config.followups_enabled() is True


# --- Approved wording lock (human review, 2026-10-26) -------------------------------------------------

APPROVED = json.loads((m8.ROOT / "tests" / "data" / "m8_guided_approved.json").read_text())["answers"]


def test_approved_reference_covers_exactly_the_matrix():
    assert sorted(APPROVED) == sorted(f"{r.case}:{q}" for r, q in CASES)


@pytest.mark.parametrize("row,question_id", CASES, ids=[f"{r.case}-{q}" for r, q in CASES])
def test_guided_wording_matches_the_approved_reference(row, question_id):
    """Any change to an approved explanation fails here; update the reference only after a new human review."""
    with m8.source_for(row):
        ans = guided.answer(m8.entry_for(row), question_id)
    assert ans.shown
    assert ans.text == APPROVED[f"{row.case}:{question_id}"]


def test_wording_lock_detects_a_change(monkeypatch):
    original = guided.BUILDERS["relevance"]
    monkeypatch.setitem(guided.BUILDERS, "relevance", lambda c: original(c).replace("doubled", "rose sharply"))
    ans = guided.answer(m8.entry_for(m8.ROWS[0]), "relevance")
    assert ans.text != APPROVED["A1:relevance"]


def test_boundary_case_f1_offers_all_four_questions():
    with m8.source_for(m8.ROWS[5]):
        assert m8.ROWS[5].case == "F1"
        answers = guided.answers(m8.entry_for(m8.ROWS[5]))
    assert [a.question for a in answers] == [q for _, q in guided.QUESTIONS] and all(a.shown for a in answers)
