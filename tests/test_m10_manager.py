"""Milestone 10 tests: artwork context, plain-language evidence wording, suggested follow-ups and the daily
briefing. Presentation only: no API call, the analysis, validation rules, approved guided answers and the demo
recording are unchanged, and every new sentence is checked before display (fail closed)."""

import ast
import contextlib
import copy
import dataclasses
import hashlib
import inspect
import json
import re

import pytest

from evals import m8_cases as m8
from gia import actions, briefing, catalog, data, evidence, explain, guided, presentation, snapshot, tools
from scripts import make_artwork_thumbnails as thumbs
from tests import fixtures as fx
from tests.test_m9_ux import LIVE, app, offline  # noqa: F401 - offline is a fixture

LOCK = json.loads((m8.ROOT / "tests" / "data" / "m10_manager_approved.json").read_text())
RULES = {"A1": "monitor_continuation", "A2": "cautious_monitoring", "B1": "recurrence_watch",
         "C1": "context_only", "C2": "insufficient_evidence", "F1": "await_later_day", "F2": "insufficient_evidence"}
KINDS = {"C2": "no_specific", "F2": "no_specific"}                    # every other case is a suggestion
PATTERNS_CSV = m8.ROOT / "tests" / "data" / "m10_followup_patterns.csv"
# Words that would imply statistical certainty, probability or commercial meaning in the new wording.
OVERCLAIM = re.compile(r"\b(likely|likelihood|probab\w*|significan\w*|certain\w*|guarantee\w*|predict\w*|"
                       r"collector\w*|buyer\w*|purchas\w*|sales?|sell\w*|pric\w*|discount\w*|contact\w*|"
                       r"caus\w*|because of)\b", re.IGNORECASE)
RECORDING_SHA256 = "fe706823aa16d0ccc3a047e25e639bd94d5df2e2a8de23d844baa180164077ec"


def entry(case):
    row = next(r for r in m8.ROWS if r.case == case)
    with m8.source_for(row):
        return row, m8.entry_for(row)


def build_briefing(result):
    o = tools.get_processed_data()
    return briefing.build(result, o["processed_dates"], [e["date"] for e in o["excluded_dates"]])


# --- Artwork catalog and thumbnails --------------------------------------------------------------------

def test_catalog_covers_every_source_artwork_and_artist_without_changing_ids():
    df = data.load_processed_data().artwork_daily
    assert set(df["artwork_id"]) == set(catalog.ARTWORKS)
    assert set(df["artist_id"]) == set(catalog.ARTISTS)
    for artwork_id, artist_id in df[["artwork_id", "artist_id"]].drop_duplicates().itertuples(index=False):
        assert catalog.ARTWORKS[artwork_id]["artist_id"] == artist_id


def test_catalog_titles_and_names_contain_no_digits_and_are_distinct():
    names = [a["title"] for a in catalog.ARTWORKS.values()] + list(catalog.ARTISTS.values())
    assert not any(re.search(r"\d", n) for n in names)          # never read as a figure by the grounding check
    assert len(set(names)) == len(names)


def test_unknown_artwork_falls_back_to_source_label():
    assert catalog.title("Z999", "Artwork Z9") == "Artwork Z9"
    assert catalog.artist("AR99", "Artist Z") == "Artist Z"
    assert catalog.thumbnail_svg("Z999") is None and catalog.medium("Z999") is None


@pytest.mark.parametrize("artwork_id", sorted(catalog.ARTWORKS))
def test_thumbnail_is_a_local_accessible_svg_identical_to_the_generator(artwork_id):
    svg = catalog.thumbnail_svg(artwork_id)
    assert svg is not None and svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    title = catalog.ARTWORKS[artwork_id]["title"]
    assert f"<title>{title}: abstract thumbnail, fictional sample artwork</title>" in svg
    assert 'role="img"' in svg and "aria-label=" in svg
    assert not re.search(r"(href|src)\s*=|https?:", svg.split("\n", 1)[1])   # no external references
    assert svg == thumbs.svg(artwork_id)                                     # deterministic, regenerable
    assert len(svg.encode()) < 4000


# --- Plain-language evidence wording -------------------------------------------------------------------

def test_plain_labels_cover_every_classification_and_keep_the_technical_terms():
    assert set(presentation.STRENGTH_PLAIN) == set(explain.STRENGTH_LABELS)
    assert set(presentation.CATEGORY_PLAIN) == set(explain.CATEGORY_LABELS)
    for strength in explain.STRENGTH_LABELS:
        for category in explain.CATEGORY_LABELS:
            help_text = presentation.rating_help(strength, category)
            assert f"technical rating: {strength}" in help_text
            assert explain.CATEGORY_LABELS[category] in help_text
            assert "not from statistical tests or probabilities" in help_text


def test_plain_wording_implies_no_probability_or_certainty():
    texts = [*presentation.STRENGTH_PLAIN.values(), *presentation.CATEGORY_PLAIN.values(),
             *(lab for _, lab in presentation.SUPPORT_STATUS.values()), presentation.SUPPORT_HELP,
             presentation.SUPPORT_LEGEND, presentation.SUPPORT_LEGEND_HELP, actions.NOTE, actions.NO_SPECIFIC,
             actions.SPIKE_TEXT, actions.RECENT_TEXT, actions.ZERO_TEXT, *(t for _, t in actions.WEAK_REASONS),
             *(f["text"] for f in LOCK["followups"].values()), catalog.CATALOG_HELP]
    assert not [t for t in texts if OVERCLAIM.search(t)]
    assert not any("%" in t for t in texts)


def test_support_legend_distinguishes_support_weak_and_against():
    legend = presentation.SUPPORT_LEGEND_HELP
    assert "**Supports it:**" in legend and "**Weak or missing:**" in legend and "**Against it:**" in legend
    assert "not evidence against the pattern" in legend


def test_evidence_summary_states_plain_rating_and_technical_classification():
    _, e = entry("A2")
    summary = presentation.evidence_summary(e, evidence.build_evidence(e))
    rating = summary["lines"][0]
    assert rating.startswith("**Evidence rating:** Partly supported · Sustained increase")
    assert "technical: moderate-confidence, sustained increase" in rating
    assert "shown as *Salt Study, Grey* (fictional sample catalog)" in summary["lines"][1]


# --- Suggested follow-ups: rule-based and evidence-driven ------------------------------------------------

@contextlib.contextmanager
def pattern_fixture():
    """Equivalent and varied evidence patterns under new artwork IDs (X001–X006), development only."""
    original = tools.load_processed_data
    tools.load_processed_data = lambda *a, **k: data.load_processed_data(PATTERNS_CSV)
    try:
        yield {e["pattern"]["artwork_id"]: e for e in m8.published_entries()}
    finally:
        tools.load_processed_data = original


def fake_evidence(category, strength, qualifying=(), weak=(), missing=(), failed=(), both_missing=False, slight=()):
    ev = actions._Evidence.__new__(actions._Evidence)
    ev.category, ev.strength, ev.metric = category, strength, "views"
    ev.qualifying, ev.missing, ev.failed = list(qualifying), list(missing), set(failed)
    ev.rose_slightly, ev.no_rise = list(slight), list(weak)
    ev.weak = ev.rose_slightly + ev.no_rise
    ev.missing_when = "on both comparison days" if both_missing else "on one of the comparison days"
    return ev


def rule_for(ev):
    return next((r[0] for r in actions.RULES if r[2](ev)), None)


@pytest.mark.parametrize("row", m8.ROWS, ids=[r.case for r in m8.ROWS])
def test_every_publishable_pattern_gets_a_checked_rule_based_followup(row):
    with m8.source_for(row):
        e = m8.entry_for(row)
        f = actions.suggest(e)
        assert f.shown, f.problems
        assert (f.rule, f.kind) == (RULES[row.case], KINDS.get(row.case, "suggestion"))
        assert guided.check(f.text, [], "next") == []                  # same checks as the guided answers
    assert f.text == LOCK["followups"][row.case]["text"]                # locked wording
    assert not OVERCLAIM.search(f.text)
    assert not re.search(r"\d", f.text)                                 # no figure or date is ever stated


def test_rule_selection_never_uses_artwork_identity():
    tree = ast.parse(inspect.getsource(actions))
    tree.body = tree.body[1:]                                           # the code only, not the module docstring
    code = ast.unparse(tree)
    for word in ("artwork_id", "artwork_title", "artist", "catalog", "A001", "B001"):
        assert word not in code


def test_equivalent_evidence_under_other_artwork_ids_gets_the_same_followup():
    _, a1 = entry("A1")
    _, a2 = entry("A2")
    _, b1 = entry("B1")
    with pattern_fixture() as found:
        same_as_a1, same_as_a2, spike = (actions.suggest(found[i]) for i in ("X001", "X006", "X005"))
    assert (same_as_a1.rule, same_as_a1.text) == (actions.suggest(a1).rule, actions.suggest(a1).text)
    assert (same_as_a2.rule, same_as_a2.text) == (actions.suggest(a2).rule, actions.suggest(a2).text)
    assert spike.rule == "recurrence_watch" and spike.text == actions.suggest(b1).text   # support does not matter


def test_followup_names_the_actual_supporting_weak_and_missing_measures():
    with pattern_fixture() as found:
        out = {i: actions.suggest(e) for i, e in found.items()}
    assert {i: f.rule for i, f in out.items()} == {
        "X001": "monitor_continuation", "X002": "monitor_continuation", "X003": "cautious_monitoring",
        "X004": "cautious_monitoring", "X005": "recurrence_watch", "X006": "cautious_monitoring"}
    assert all(f.shown for f in out.values())
    assert "supporting increases in favourites and inquiries" in out["X002"].text
    assert "Favourites support the pattern, while daily unique viewers and inquiries did not increase." \
        in out["X003"].text                                            # no rise at all: never "limited support"
    assert ("Favourites support the pattern, while inquiries did not increase and daily unique viewers are not "
            "recorded on one of the comparison days.") in out["X004"].text
    assert ("Daily unique viewers support the pattern, while favourites provide limited additional support and "
            "inquiries did not increase.") in out["X006"].text           # a small rise vs no rise, told apart


@pytest.mark.parametrize("ev,rule", [
    (fake_evidence("sustained_growth", "higher-confidence", ["a", "b"]), "monitor_continuation"),
    (fake_evidence("sustained_growth", "higher-confidence", ["a", "b", "c"]), "monitor_continuation"),
    (fake_evidence("sustained_growth", "moderate-confidence", ["a"], ["b", "c"]), "cautious_monitoring"),
    (fake_evidence("sustained_growth", "moderate-confidence", ["a"], [], ["b"]), "cautious_monitoring"),
    (fake_evidence("temporary_spike", "qualified", ["a"]), "recurrence_watch"),
    (fake_evidence("emerging_increase", "qualified", failed=["min_later_days"]), "await_later_day"),
    (fake_evidence("zero_baseline_change", "qualified"), "context_only"),
    (fake_evidence("weak_signal", "qualified", failed=["corroboration"]), "insufficient_evidence"),
    (fake_evidence("insufficient_evidence", "qualified", missing=["b"]), "insufficient_evidence"),
    # combinations no rule covers: never a generic suggestion
    (fake_evidence("sustained_growth", "higher-confidence", ["a"]), None),
    (fake_evidence("sustained_growth", "moderate-confidence", ["a", "b"]), None),
    (fake_evidence("emerging_increase", "qualified"), None),
    (fake_evidence("temporary_spike", "moderate-confidence"), None),
    (fake_evidence("a_future_category", "qualified"), None),
])
def test_rule_matrix(ev, rule):
    assert rule_for(ev) == rule


@pytest.mark.parametrize("failed,reason", [
    (["min_absolute_change", "stable_tolerance"], "the change is too small to count under the screening rules"),
    (["min_gain_retained"], "the higher level held on some later days and not others"),
    (["corroboration"], "no other measure rose enough to back it up"),
    ([], None),
])
def test_weak_signal_explains_why_no_specific_followup_is_suggested(failed, reason):
    text = actions._no_specific(fake_evidence("weak_signal", "qualified", failed=failed))
    assert text == (f"{actions.NO_SPECIFIC}: {reason}." if reason else f"{actions.NO_SPECIFIC}.")
    assert guided.check(text, [], "next") == []


@pytest.mark.parametrize("slight,flat,expected", [
    (["favourites"], ["inquiries"], "favourites provide limited additional support and inquiries did not increase"),
    (["favourites", "inquiries"], [], "favourites and inquiries provide limited additional support"),
    ([], ["favourites", "inquiries"], "favourites and inquiries did not increase"),
    ([], [], "no other measure adds support"),
])
def test_cautious_wording_separates_a_small_rise_from_no_rise(slight, flat, expected):
    text = actions._cautious_monitoring(fake_evidence("sustained_growth", "moderate-confidence",
                                                      ["daily unique viewers"], flat, slight=slight))
    assert f"Daily unique viewers support the pattern, while {expected}." in text
    assert guided.check(text, [], "next") == []


def test_missing_measures_are_described_as_they_are():
    one = actions._no_specific(fake_evidence("insufficient_evidence", "qualified", missing=["daily unique viewers"]))
    both = actions._no_specific(fake_evidence("insufficient_evidence", "qualified", missing=["daily unique viewers"],
                                              both_missing=True))
    assert one.endswith("daily unique viewers are not recorded on one of the comparison days.")
    assert both.endswith("daily unique viewers are not recorded on both comparison days.")


def test_unknown_combination_gets_a_neutral_explanation_not_a_generic_suggestion(monkeypatch):
    _, e = entry("C1")
    unknown = copy.deepcopy(e)
    unknown["pattern"]["category"] = "a_future_category"
    monkeypatch.setattr(guided, "_matches_source", lambda pattern: True)
    monkeypatch.setitem(guided.explain.CATEGORY_LABELS, "a_future_category", "A future category")
    f = actions.suggest(unknown)
    assert (f.rule, f.kind, f.text) == ("no_rule", "no_specific", f"{actions.NO_SPECIFIC}.") and f.shown


def test_inconsistent_sustained_evidence_is_a_validation_failure_not_a_gap(monkeypatch):
    _, e = entry("A1")
    inconsistent = copy.deepcopy(e)
    inconsistent["pattern"]["supporting_metrics"][1]["qualifies_as_support"] = False   # only one backer left
    monkeypatch.setattr(guided, "_matches_source", lambda pattern: True)
    f = actions.suggest(inconsistent)
    assert f.kind == "unavailable" and not f.shown and "does not match" in f.problems[0]


@pytest.mark.parametrize("row", m8.ROWS, ids=[r.case for r in m8.ROWS])
def test_followup_does_not_repeat_the_guided_next_step_or_agent_next_step(row):
    with m8.source_for(row):
        e = m8.entry_for(row)
        text = actions.suggest(e).text
        nxt = guided.answer(e, "next").text
    sentences = {s.strip() for s in guided.grounding.SENTENCE_SPLIT.split(text) if s.strip()}
    assert not sentences & {s.strip() for s in guided.grounding.SENTENCE_SPLIT.split(nxt)}
    assert "View evidence" not in text                                 # Q4 says what to check; this does not
    assert text != tools.SAFE_NEXT_STEP and text != e["insight"].get("suggested_next_step")


def test_followup_fails_closed_when_the_pattern_no_longer_matches_the_source():
    _, e = entry("A1")
    altered = copy.deepcopy(e)
    altered["pattern"]["key_comparison"]["new_value"] = 99
    f = actions.suggest(altered)
    assert f.kind == "unavailable" and not f.shown and "does not match the source data" in f.problems[0]


def test_followup_fails_closed_on_a_rating_mismatch_or_malformed_entry():
    _, e = entry("A1")
    mismatch = copy.deepcopy(e)
    mismatch["insight"]["confidence"] = "qualified"
    assert actions.suggest(mismatch).kind == "unavailable"
    _, a2 = entry("A2")
    odd = copy.deepcopy(a2)                                            # a sustained increase must never get
    odd["insight"]["confidence"] = odd["pattern"]["evidence_strength"] = "higher-confidence"   # the wrong text
    assert not actions.suggest(odd).shown
    assert actions.suggest({"pattern": {}, "insight": {}}).kind == "unavailable"


@pytest.mark.parametrize("case", ["B1", "C2"])
def test_followup_fails_closed_when_a_check_finds_a_problem(monkeypatch, case):
    _, e = entry(case)
    monkeypatch.setattr(guided, "check", lambda *a, **k: ["commercial action ('test')"])
    f = actions.suggest(e)
    assert f.kind == "unavailable" and not f.shown and f.problems == ["commercial action ('test')"]


# --- Daily briefing ------------------------------------------------------------------------------------

def test_briefing_for_the_three_insight_run_matches_the_locked_wording():
    b = build_briefing(fx.mock_three_insight_result())
    locked = LOCK["briefing"]
    assert b.period == locked["period"] and [list(c) for c in b.chips] == locked["chips"]
    assert b.lines == locked["lines"] and b.not_prioritised == locked["not_prioritised"]
    assert b.dropped == 0 and not b.withheld and not b.not_published


def test_briefing_counts_and_keeps_published_not_surfaced_and_withheld_apart():
    b = build_briefing(fx.mock_three_insight_result())
    assert [label for label, _ in b.chips] == ["Two sustained increases", "One temporary spike",
                                               "Three artworks not prioritised"]
    published = " ".join(b.lines)
    for name in ("Harbour at First Light", "Salt Study, Grey", "Red Interval"):
        assert name in published and name not in b.not_prioritised
    for name in ("Quiet Grid", "Paper Moon", "Field Notes in Blue"):
        assert name in b.not_prioritised and name not in published
    assert b.lines[0].startswith("Strongest evidence: **Harbour at First Light**")


def test_briefing_reports_validation_withheld_drafts_and_unpublished_patterns_separately():
    result = fx.mock_three_insight_result()
    a2 = next(e for e in result.published if e["pattern"]["artwork_id"] == "A002")
    result = dataclasses.replace(
        result, published=[e for e in result.published if e is not a2],
        withheld=[{**a2, "errors": ["test"]}],
        not_surfaced=explain.not_surfaced({"A001", "B001"}))
    b = build_briefing(result)
    assert ("One draft withheld by validation", "red") in b.chips
    assert b.withheld == "One draft finding did not pass the evidence checks and is not shown."
    assert b.not_published == "Salt Study, Grey"                       # a sustained increase: never "not prioritised"
    assert "Salt Study, Grey" not in b.not_prioritised and "Salt Study, Grey" not in " ".join(b.lines)
    assert ("One sustained increase", "green") in b.chips


def test_briefing_with_no_published_insights_has_no_lines():
    result = dataclasses.replace(fx.mock_three_insight_result(), published=[],
                                 not_surfaced=explain.not_surfaced(set()))
    b = build_briefing(result)
    assert not b.lines and b.not_published and b.not_prioritised


def test_briefing_drops_a_line_that_fails_its_checks(monkeypatch):
    real = guided.check
    monkeypatch.setattr(guided, "check", lambda text, *a, **k:
                        ["test problem"] if "Red Interval" in text else real(text, *a, **k))
    b = build_briefing(fx.mock_three_insight_result())
    assert b.dropped == 1 and len(b.lines) == 2 and not any("Red Interval" in line for line in b.lines)


def test_briefing_sentences_pass_the_guided_checks_and_avoid_overclaiming():
    b = build_briefing(fx.mock_three_insight_result())
    for text in [b.period, b.not_prioritised, *b.lines, *(label for label, _ in b.chips)]:
        assert not OVERCLAIM.search(text), text
    assert "Oct 18 excluded (not processed yet)" in b.period


# --- In the app (offline, LIVE and DEMO identical) -----------------------------------------------------

def card_view(at):
    """Everything M10 adds to the screen, in order (thumbnails, headings, captions, follow-ups, briefing)."""
    return [m.value for m in at.markdown if m.value.startswith(("<img", "#### ", "**Suggested follow-up**",
                                                                "Consider keeping", "Keep this", "No immediate",
                                                                "- Strongest", ":green-badge", ":blue-badge",
                                                                ":orange-badge"))]


def test_cards_show_artwork_context_followups_and_briefing(monkeypatch, offline):  # noqa: F811
    at = app(monkeypatch, LIVE, fx.mock_three_insight_result()).run(timeout=30)
    assert not at.exception, at.exception
    md = [m.value for m in at.markdown]
    briefing_at = md.index("##### Daily briefing")
    first_card = md.index("#### 1. Harbour at First Light")
    assert briefing_at < first_card                                               # briefing above the cards
    imgs = [m for m in md if m.startswith('<img src="data:image/svg+xml;base64,')]
    assert len(imgs) == 3 and all('alt="' in m and "fictional sample artwork" in m for m in imgs)
    captions = [c.value for c in at.caption]
    assert any(c.startswith("Ines Halvorsen · Oil on linen · Fictional sample artwork · source: Artwork A1 (A001)")
               for c in captions)
    assert md.count(f"**{actions.HEADING}** :gray[· {actions.NOTE}]") == 3
    assert LOCK["followups"]["A1"]["text"] in md and LOCK["followups"]["B1"]["text"] in md
    badges = [m for m in md if m.startswith(":green-badge[Well supported]")]
    assert len(badges) == 1 and ":gray-badge[Sustained increase]" in badges[0]
    assert any(m.startswith(":orange-badge[For awareness only] :gray-badge[One-day spike]") for m in md)


def test_m9_elements_and_review_rule_unchanged(monkeypatch, offline):  # noqa: F811
    at = app(monkeypatch, LIVE, fx.mock_three_insight_result()).run(timeout=30)
    assert len(at.metric) == 12 and len(at.get("vega_lite_chart")) == 3
    labels = [b.label for b in at.button]
    assert labels.count("Explore insight") == 3 and labels.count("View evidence") == 3
    [progress] = [i.value for i in at.info if i.value.startswith("**Review progress:**")]
    assert "any one is enough" in progress


def test_live_and_demo_show_identical_m10_content(monkeypatch, tmp_path, offline):  # noqa: F811
    live = fx.mock_three_insight_result()
    demo = snapshot.load_snapshot(snapshot.save_snapshot(copy.deepcopy(live), path=tmp_path / "rec.json"))
    views = [card_view(app(monkeypatch, s, r).run(timeout=30))
             for s, r in ((LIVE, live), ({"ANTHROPIC_API_KEY": "sk-ant-test-0000"}, demo))]
    assert views[0] == views[1] and len(views[0]) > 10


def test_unverified_followup_is_replaced_by_a_notice(monkeypatch, offline):  # noqa: F811
    monkeypatch.setattr(actions, "suggest", lambda entry, data=None: actions.FollowUp(problems=["test"]))
    at = app(monkeypatch, LIVE, fx.mock_three_insight_result()).run(timeout=30)
    assert not at.exception
    assert sum(c.value == actions.UNAVAILABLE for c in at.caption) == 3


def test_briefing_failure_falls_back_to_the_overview(monkeypatch, offline):  # noqa: F811
    def broken(*a, **k):
        raise ValueError("test")
    monkeypatch.setattr(briefing, "build", broken)
    at = app(monkeypatch, LIVE, fx.mock_three_insight_result()).run(timeout=30)
    assert not at.exception
    assert any(m.value.startswith("**Analysis overview.**") for m in at.markdown)


def test_approved_demo_recording_is_unchanged():
    path = m8.ROOT / "demo" / "recorded_investigation.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == RECORDING_SHA256
