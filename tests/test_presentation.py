"""Milestone 4 tests: insight cards, View evidence, deterministic explanations, LIVE/DEMO parity."""

import copy
from pathlib import Path

import anthropic
import pytest
from streamlit.testing.v1 import AppTest

from gia import agent, config, evidence, explain, snapshot, tools
from tests.fixtures import A1, mock_three_insight_result
from tests.test_agent import final, run

APP = str(Path(__file__).resolve().parent.parent / "app.py")
PATTERNS = {p["artwork_id"]: p for p in tools.detect_engagement_patterns()["patterns"]}


def entry_for(insight):
    published, withheld = agent.publication_gate([insight])
    assert published, withheld
    return published[0]


def changes(artwork_id, rows):
    return [{"artwork_id": artwork_id, "metric": m, "old_date": "2026-10-14", "new_date": "2026-10-15",
             "old_value": o, "new_value": n, "absolute_change": None if None in (o, n) else n - o,
             "percentage_change": p} for m, o, n, p in rows]


C1 = {"signal_type": "zero_baseline_change", "artwork_id": "C001", "confidence": "qualified",
      "title": "Artwork C1: views started from zero", "observed_signal": "Artwork views went from 0 to 10.",
      "why_it_may_matter": "Small numbers; context only.", "suggested_next_step": "",
      "limitations": ["Percentage growth from zero is undefined."], "metric_totals": [],
      "metric_changes": changes("C001", [("artwork_views", 0, 10, None)])}
C2 = {"signal_type": "weak_signal", "artwork_id": "C002", "confidence": "qualified",
      "title": "Artwork C2: small change", "observed_signal": "Artwork views went from 15 to 20.",
      "why_it_may_matter": "Too small to be meaningful.", "suggested_next_step": "",
      "limitations": ["Daily unique viewers on 2026-10-15 is unknown."], "metric_totals": [],
      "metric_changes": changes("C002", [("artwork_views", 15, 20, 33.3),
                                         ("unique_artwork_viewers", 12, None, None)])}


# --- Deterministic explanations -------------------------------------------------------

def test_c1_explanation_mentions_qualifying_unique_viewers():
    text = explain.explain_pattern(PATTERNS["C001"])
    assert "Daily unique viewers (0 → 8) also rose enough to count as support" in text
    assert "no percentage, because it started at 0" in text


def test_c2_explanation_says_not_recorded_not_zero():
    text = explain.explain_pattern(PATTERNS["C002"])
    assert "Daily unique viewers on Oct 15 is not recorded" in text
    assert "only +5" in text


def test_b1_explanation_is_never_growth():
    text = explain.explain_pattern(PATTERNS["B001"]).lower()
    assert "one-day jump" in text and "sustained" not in text


def test_live_mode_replaces_model_free_text_with_deterministic_text():
    result, _ = run([final([A1], [{"artwork_id": "C001", "category": "zero_baseline_change",
                                   "reason": "MODEL REASON: favourites and inquiries did not qualify."}])])
    reasons = {n["artwork_id"]: n["explanation"] for n in result.not_surfaced}
    assert "MODEL REASON" not in str(result.not_surfaced)
    assert reasons["C001"] == explain.explain_pattern(PATTERNS["C001"])
    assert result.summary == ""   # the model's summary is never displayed or saved


def test_overview_is_deterministic():
    result = mock_three_insight_result()
    text = explain.overview(result.published, ["2026-10-14", "2026-10-17"], ["2026-10-18"])
    assert "1 higher-confidence, 1 moderate-confidence and 1 qualified" in text
    assert "Oct 18 excluded" in text


# --- Strength labels, priority and next steps -----------------------------------------

def test_insights_prioritised_strongest_first():
    result = mock_three_insight_result()
    assert [p["insight"]["confidence"] for p in result.published] == [
        "higher-confidence", "moderate-confidence", "qualified"]


@pytest.mark.parametrize("label", ["high", "medium", "90%", "Higher-confidence"])
def test_only_approved_strength_labels_are_published(label):
    published, withheld = agent.publication_gate([{**A1, "confidence": label}])
    assert not published and withheld


@pytest.mark.parametrize("step", [
    "Review the artwork internally to understand what may have coincided with the increase.",
    "Investigate what caused the jump.",
    "Find the drivers behind this change.",
])
def test_cause_seeking_next_steps_are_rejected(step):
    published, withheld = agent.publication_gate([{**A1, "suggested_next_step": step}])
    assert not published
    assert any("neutral and non-causal" in e for e in withheld[0]["errors"])


def test_neutral_next_step_is_accepted():
    assert entry_for(A1)["insight"]["suggested_next_step"].startswith("Review the engagement evidence")


# --- View evidence ---------------------------------------------------------------------

def test_evidence_is_grounded_in_tools_and_excludes_day5():
    ev = evidence.build_evidence(entry_for(A1))
    assert ev["context"]["Artwork"] == "Artwork A1 (A001)" and ev["context"]["Artist"] == "Artist A (AR01)"
    assert [r["Artwork views"] for r in ev["daily"][:4]] == ["40", "80", "76", "90"]
    assert ev["daily"][4]["Status"] == "Excluded (not processed yet)" and ev["daily"][4]["Artwork views"] == "—"
    assert "150" not in str(ev["daily"])                       # Day 5's value is never shown or used
    views = next(r for r in ev["comparison"] if r["Measure"] == "Artwork views")
    assert views["Change"] == "+40, +100.0%" and "(80 - 40) / 40" in views["Calculation"]
    assert all(c["Result"] == "✅ matches source" for c in ev["verified_claims"])
    assert "286 + 130 = 416" in ev["artist_context"] and "not people" in ev["artist_context"]
    assert any("is excluded" in n for n in ev["notes"])
    assert explain.STRENGTH_NOTE in ev["notes"]


def test_evidence_explains_zero_baseline():
    ev = evidence.build_evidence(entry_for(C1))
    views = next(r for r in ev["comparison"] if r["Measure"] == "Artwork views")
    assert views["Change"] == "+10; no percentage, because it started at 0"
    assert explain.ZERO_NOTE in ev["notes"]


def test_evidence_explains_missing_values():
    ev = evidence.build_evidence(entry_for(C2))
    assert ev["daily"][1]["Daily unique viewers"] == "not recorded"
    uniques = next(r for r in ev["comparison"] if r["Measure"] == "Daily unique viewers")
    assert uniques["Change"] == "cannot compare: a value is not recorded"
    assert explain.MISSING_NOTE in ev["notes"]


# --- The app: same cards and evidence in LIVE and DEMO --------------------------------

def render(monkeypatch, result, mode):
    monkeypatch.setattr(config, "_setting", lambda name: {"GIA_MODE": mode}.get(name))
    monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **k: pytest.fail("API client created"))
    at = AppTest.from_file(APP)
    at.session_state["analysis"] = result
    return at.run(timeout=30)


def card_text(at):
    return [m.value for m in at.markdown if m.value.startswith(("#### ", "**What the agent", "**Why it",
                                                                    "**Evidence strength", "**Limitations"))]


def test_cards_identical_in_live_and_demo(monkeypatch, tmp_path):
    live = mock_three_insight_result()
    path = snapshot.save_snapshot(copy.deepcopy(live), tmp_path / "snap.json")
    demo = snapshot.load_snapshot(path)
    at_live, at_demo = render(monkeypatch, live, "live"), render(monkeypatch, demo, "demo")
    assert not at_live.exception and not at_demo.exception
    assert card_text(at_live) == card_text(at_demo)
    titles = [t for t in card_text(at_live) if t[5:6].isdigit()]
    assert titles == ["#### 1. Artwork A1: views doubled on Oct 15 and stayed higher",
                      "#### 2. Artwork A2: views up on Oct 15 and maintained",
                      "#### 3. Artwork B1: one-day spike that did not hold"]
    assert any("Recorded AI investigation" in i.value for i in at_demo.info)
    assert not any("Recorded AI investigation" in i.value for i in at_live.info)


def test_view_evidence_toggle_in_demo(monkeypatch, tmp_path):
    path = snapshot.save_snapshot(mock_three_insight_result(), tmp_path / "snap.json")
    at = render(monkeypatch, snapshot.load_snapshot(path), "demo")
    button = next(b for b in at.button if b.label == "View evidence")
    button.click().run(timeout=30)
    assert not at.exception
    assert any(m.value == "##### Evidence" for m in at.markdown)
    assert any(b.label == "Hide evidence" for b in at.button)
    assert at.session_state["evidence_viewed"] == {"INS-A001-SUSTAINED_GROWTH-20261014_20261015"}


def test_model_summary_is_not_displayed(monkeypatch):
    result, _ = run([final([A1])])
    at = render(monkeypatch, result, "live")
    text = " ".join(m.value for m in at.markdown)
    assert "Test summary." not in text and "Analysis overview." in text
