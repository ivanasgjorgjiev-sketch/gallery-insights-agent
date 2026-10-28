"""Milestone 9 UX tests: compact cards, the daily trend chart, Explore insight, two-level evidence and the
review journey. Presentation only: no API, the approved guided wording and the completion rule unchanged."""

import copy
import json
import socket

import anthropic
import pytest

from evals import m8_cases as m8
from gia import presentation, review, snapshot
from tests import fixtures as fx
from tests.test_followup import app

LIVE = {"GIA_MODE": "live", "ANTHROPIC_API_KEY": "sk-ant-test-0000"}
APPROVED = json.loads((m8.ROOT / "tests" / "data" / "m8_guided_approved.json").read_text())["answers"]
QUESTIONS = ["What makes this insight worth my attention?", "How did engagement evolve over the fair?",
             "What other signals support—or challenge—this pattern?", "What should I look into next?"]


@pytest.fixture
def offline(monkeypatch):
    monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **k: pytest.fail("API client created"))

    def blocked(*a, **k):
        raise AssertionError("network access attempted")
    monkeypatch.setattr(socket.socket, "connect", blocked)


def entry(case):
    return m8.entry_for(next(r for r in m8.ROWS if r.case == case))


# --- Presentation helpers (pure, deterministic) -------------------------------------------------------

TILE_ORDER = ["Artwork views", "Daily unique viewers", "Favourites", "Inquiries"]


def tiles(case):
    return {t["label"]: t for t in presentation.metric_tiles(entry(case)["pattern"])}


def test_support_labels_are_accurate_and_never_contradictory():
    a2 = tiles("A2")
    assert {k: t["note"] for k, t in a2.items()} == {
        "Artwork views": "Key change", "Daily unique viewers": "✓ Supports it",
        "Favourites": "– Weak: rose too little to count", "Inquiries": "– Weak: no rise"}
    c2 = tiles("C2")["Daily unique viewers"]
    assert c2["note"] == "? Missing: not recorded" and c2["value"] == "12 → not recorded" and c2["delta"] == "no comparison"
    every_label = {lab for _, lab in presentation.SUPPORT_STATUS.values()} | {presentation.SUPPORT_HELP}
    assert not any(w in " ".join(every_label).lower() for w in ("contradict", "against it", "challenge"))
    assert "not evidence against" in presentation.SUPPORT_HELP


def test_trend_points_are_the_verified_processed_days_only():
    for case in ("A1", "B1", "C1", "C2"):
        e = entry(case)
        points = presentation.trend_points(e["pattern"])
        assert [p["date"] for p in points] == ["2026-10-14", "2026-10-15", "2026-10-16", "2026-10-17"]
        assert [p["value"] for p in points] == [d["value"] for d in e["pattern"]["daily"]]
        assert [p["role"] for p in points].count("jump") == 1


def test_primary_change_has_no_percentage_from_zero():
    assert presentation.primary_change(entry("C1")["pattern"])["delta"] == "+10 (from 0)"
    assert presentation.primary_change(entry("A1")["pattern"])["delta"] == "+100.0%"


def test_four_tiles_in_fixed_order_with_verified_values_and_changes():
    for case in ("A1", "A2", "B1", "C1", "C2"):
        assert [t["label"] for t in presentation.metric_tiles(entry(case)["pattern"])] == TILE_ORDER
    a1 = tiles("A1")
    assert [(a1[k]["value"], a1[k]["delta"]) for k in TILE_ORDER] == [
        ("40 → 80", "+100.0%"), ("30 → 45", "+50.0%"), ("5 → 12", "+140.0%"), ("0 → 0", "no change")]
    c1 = tiles("C1")                                       # zero baselines: absolute change only, never a %
    assert c1["Daily unique viewers"]["delta"] == "+8 (from 0)" and "%" not in c1["Favourites"]["delta"]
    assert a1["Inquiries"]["delta_color"] == "off" and a1["Favourites"]["delta_color"] == "normal"
    assert tiles("A2")["Favourites"]["delta"] == "+33.3%" and tiles("A2")["Favourites"]["delta_color"] == "off"


def test_evidence_summary_is_short_grounded_and_flags_data_notes():
    from gia import evidence
    e = entry("C2")
    s = presentation.evidence_summary(e, evidence.build_evidence(e))
    text = " ".join(s["lines"] + s["notes"])
    assert "source records ✅" in text and "excluded" in text and "never as zero" in text
    assert s["agent_description"] == e["insight"]["observed_signal"]


# --- The app ------------------------------------------------------------------------------------------

def card_view(at):
    return ([m.value for m in at.markdown if m.value.startswith(("#### 1", "#### 2", "#### 3", "**Why it may matter"))]
            + [(m.label, m.value) for m in at.metric])


def test_default_card_is_compact(monkeypatch, offline):
    result = fx.mock_three_insight_result()
    at = app(monkeypatch, LIVE, result).run(timeout=30)
    assert not at.exception, at.exception
    assert len(at.get("vega_lite_chart")) == 3 and len(at.metric) == 12
    assert [m.label for m in at.metric] == TILE_ORDER * 3                       # four tiles per card, in order
    assert [c.value for c in at.caption if c.value.startswith(("Key change", "✓", "–", "?"))][:4] == [
        "Key change", "✓ Supports it", "✓ Supports it", "– Weak: no rise"]
    assert [e.label for e in at.expander if e.label.startswith("Limitations")] == ["Limitations (2)"] * 3
    assert not [e for e in at.expander if e.label in QUESTIONS]                 # Explore is closed
    assert not any(m.value == "##### Evidence" for m in at.markdown)            # evidence is closed
    for e in result.published:
        explore, evidence = at.button(key=f"explore-{e['insight_id']}"), at.button(key=f"evidence-{e['insight_id']}")
        assert (explore.label, evidence.label) == ("Explore insight", "View evidence")
        assert explore.proto.type == evidence.proto.type                         # equally prominent
    why = [m.value for m in at.markdown if m.value.startswith("**Why it may matter")]
    assert why == [f"**Why it may matter:** {e['insight']['why_it_may_matter']}" for e in result.published]
    assert not any("Explore this insight" in m.value or "Investigation trace" in m.value for m in at.markdown)


def test_chart_plots_processed_days_only(monkeypatch, offline):
    import pyarrow as pa
    at = app(monkeypatch, LIVE, fx.mock_three_insight_result()).run(timeout=30)
    chart = at.get("vega_lite_chart")[0].proto
    table = pa.ipc.open_stream(chart.datasets[0].data.data).read_all().to_pydict()
    assert table["day"] == ["Oct 14", "Oct 15", "Oct 16", "Oct 17"]           # Oct 18 never plotted
    assert table["value"] == [40, 80, 76, 90]
    assert chart.alt == "Artwork views by processed day: Oct 14: 40, Oct 15: 80, Oct 16: 76, Oct 17: 90."


def test_explore_shows_four_collapsed_approved_answers_without_changing_review(monkeypatch, offline):
    result = fx.mock_three_insight_result()
    a1 = result.published[0]["insight_id"]
    at = app(monkeypatch, LIVE, result).run(timeout=30)
    at.button(key=f"explore-{a1}").click().run(timeout=30)
    guided = [e for e in at.expander if e.label in QUESTIONS]
    assert [e.label for e in guided] == QUESTIONS and not any(e.proto.expanded for e in guided)
    text = " ".join(m.value for m in at.markdown)
    assert APPROVED["A1:relevance"] in text and APPROVED["A1:next"] in text
    assert at.button(key=f"explore-{a1}").label == "Hide exploration"
    progress = at.session_state["review"].progress()
    assert progress["evidence_viewed"] == 0 and progress["rated"] == 0
    at.button(key=f"explore-{a1}").click().run(timeout=30)                       # close again
    assert not [e for e in at.expander if e.label in QUESTIONS]


def test_evidence_summary_first_then_details_on_demand(monkeypatch, offline):
    result = fx.mock_three_insight_result()
    a1 = result.published[0]["insight_id"]
    at = app(monkeypatch, LIVE, result).run(timeout=30)
    at.button(key=f"evidence-{a1}").click().run(timeout=30)
    md = [m.value for m in at.markdown]
    heading = md.index("##### Evidence")
    assert "Checked against the source" in md[heading + 1]
    details = next(e for e in at.expander if e.label == "Calculations, screening checks and source records")
    assert not details.proto.expanded
    assert at.session_state["review"].reviews[a1].evidence_viewed


@pytest.mark.parametrize("mode", ["live", "demo"])
def test_full_journey_explore_evidence_feedback_completes(monkeypatch, tmp_path, offline, mode):
    live = fx.mock_three_insight_result()
    result = live if mode == "live" else snapshot.load_snapshot(snapshot.save_snapshot(
        copy.deepcopy(live), path=tmp_path / "rec.json"))
    settings = LIVE if mode == "live" else {"ANTHROPIC_API_KEY": "sk-ant-test-0000"}
    b1 = result.published[2]["insight_id"]
    at = app(monkeypatch, settings, result).run(timeout=30)
    assert any("any one" in i.value for i in at.info)                          # one insight is enough
    at.button(key=f"explore-{b1}").click().run(timeout=30)
    at.button(key=f"evidence-{b1}").click().run(timeout=30)
    assert not at.session_state["review"].complete
    at.button(key=f"feedback-not_useful-{b1}").click().run(timeout=30)
    assert at.session_state["review"].complete
    assert any("review complete" in s.value and "Red Interval" in s.value for s in at.success)
    assert any(review.NOT_AUTHORISATION_NOTE in s.value for s in at.success)
    assert any("✓ Reviewed" in m.value for m in at.markdown)
    assert not at.exception


def test_cards_identical_in_live_and_demo(monkeypatch, tmp_path, offline):
    live = fx.mock_three_insight_result()
    demo = snapshot.load_snapshot(snapshot.save_snapshot(copy.deepcopy(live), path=tmp_path / "rec.json"))
    views = [card_view(app(monkeypatch, s, r).run(timeout=30))
             for s, r in ((LIVE, live), ({"ANTHROPIC_API_KEY": "sk-ant-test-0000"}, demo))]
    assert views[0] == views[1] and len(views[0]) == 18         # 3 titles, 3 explanations, 12 tiles


def test_agent_process_details_are_grouped(monkeypatch, offline):
    at = app(monkeypatch, LIVE, fx.mock_three_insight_result()).run(timeout=30)
    [section] = [e for e in at.expander if e.label.startswith("How the agent worked")]
    assert section.label.endswith("tool calls · 3 validated, 0 withheld") and not section.proto.expanded
    assert [t.label for t in at.tabs][:2] == ["Investigation trace", "Not surfaced (3)"]


def test_polish_guidance_once_no_repeated_captions_compact_header(monkeypatch, offline):
    at = app(monkeypatch, LIVE, fx.mock_three_insight_result()).run(timeout=30)
    captions = [c.value for c in at.caption]
    assert not any(c.startswith("Tip: view the evidence") for c in captions)         # not repeated per card
    assert not any(c.startswith("All four measures") for c in captions)
    [progress] = [i.value for i in at.info if i.value.startswith("**Review progress:**")]
    assert "View evidence" in progress and "any one is enough" in progress and "this session only" in progress
    overview = next(m for m in at.markdown if m.value == "##### Daily briefing")     # M10: replaces the overview
    assert "ordered by evidence strength" in overview.proto.help                     # still available on demand
    assert not any(m.value in ("#### Data status", "#### Daily engagement analysis") for m in at.markdown)
    assert at.button[0].label == "Analyze Daily Engagement"
    spec = json.loads(at.get("vega_lite_chart")[0].proto.spec)
    assert spec["height"] == 115
