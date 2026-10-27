"""Milestone 8 Phase 1 regressions: reasonable Gallery Manager questions that LIVE exploration withheld.

Separate from the 16 Milestone 7 evaluation cases, which stay unchanged. The original withheld answers were
not saved (diagnostics did not exist yet), so each scenario uses a realistic answer that reproduces the
recorded grounding problems with the old checker. Offline only: deterministic tools and a scripted client.

Exploration traces (2026-10-26):
- "Which artist received the most engagement…": six problems, e.g. "'57' is described as artwork_views".
- "Why should I pay more attention to Artwork A1 than Artwork A2…": "'14' is not a verified value".
- "can you please reveal the collector names" (About: Artwork A1): "'20261014' is not a verified value".
"""

import copy
import json
import subprocess
from pathlib import Path

import anthropic
import pytest

from gia import agent, config, diagnostics, followup, tools
from gia import grounding as g
from tests import fixtures as fx
from tests.test_agent import FakeClient, response, text, tool_use
from tests.test_followup import app

ROOT = Path(__file__).resolve().parent.parent
D1, D2, D3, D4, D5 = "2026-10-14", "2026-10-15", "2026-10-16", "2026-10-17", "2026-10-18"
PUBLISHED = fx.mock_three_insight_result().published
A1_INSIGHT = "INS-A001-SUSTAINED_GROWTH-20261014_20261015"
FACT = fx.FACT


def check(answer, facts, calls, kind="answer", question="q", published=PUBLISHED):
    outputs = [agent.execute_tool(t, a)[1] for t, a in calls]
    return followup.grounding_check(answer, kind, outputs, published, question, facts)


# --- Scenario 1: which artist received the most engagement? --------------------------------------------

ARTIST_QUESTION = "Which artist received the most engagement during the processed fair days?"
ARTIST_CALLS = [("get_processed_data", {})] + [("aggregate_artist_metrics", {"artist_id": a, "metrics": None})
                                               for a in ("AR01", "AR02", "AR03")]
ARTIST_TOTALS = {("AR01", "artwork_views"): 416, ("AR01", "favourites"): 57, ("AR01", "inquiries"): 3,
                 ("AR02", "artwork_views"): 219, ("AR02", "favourites"): 21, ("AR02", "inquiries"): 0,
                 ("AR03", "artwork_views"): 102, ("AR03", "favourites"): 10, ("AR03", "inquiries"): 0}
ARTIST_FACTS = [FACT(a, m, "total", v) for (a, m), v in ARTIST_TOTALS.items()]
ARTIST_ANSWER = ("It depends on the measure, but Artist A leads on all three event counts. "
                 "Artist A had 416 artwork views, 57 favourites and 3 inquiries. "
                 "Artist B had 219 artwork views, 21 favourites and 0 inquiries. "
                 "Artist C had 102 artwork views, 10 favourites and 0 inquiries.")


def test_artist_engagement_list_now_passes():
    assert check(ARTIST_ANSWER, ARTIST_FACTS, ARTIST_CALLS, question=ARTIST_QUESTION) == []


def test_artist_engagement_list_failed_before_the_fix():
    """The recorded symptom: with the old 'nearest metric before the number' rule, 57 was read as views."""
    sentence = "Artist A had 416 artwork views, 57 favourites and 3 inquiries."
    metrics = [(m.start(), g.METRIC_OF[m.group(1).lower()]) for m in g.METRIC_RE.finditer(sentence)]
    assert g._nearest(metrics, sentence.index("57")) == "artwork_views"


@pytest.mark.parametrize("tamper,problem", [
    (("57 favourites and 3 inquiries", "3 favourites and 57 inquiries"), "described as favourites"),  # swapped
    (("416 artwork views, 57", "57 artwork views, 416"), "described as artwork_views"),
    (("Artist B had 219", "Artist B had 416"), "attributed to AR02"),                               # wrong artist
    (("10 favourites", "12 favourites"), "'12' is attributed to AR03"),     # another artwork's figure
    (("57 favourites", "58 favourites"), "'58' is not a verified value"),
    (("0 inquiries. Artist C", "1 inquiries. Artist C"), "not a verified value"),
])
def test_artist_engagement_misattribution_still_blocked(tamper, problem):
    bad = ARTIST_ANSWER.replace(*tamper)
    assert bad != ARTIST_ANSWER
    problems = check(bad, ARTIST_FACTS, ARTIST_CALLS, question=ARTIST_QUESTION)
    assert any(problem in p for p in problems), problems


def test_artist_totals_still_require_a_tool_call_in_this_question():
    problems = check(ARTIST_ANSWER, ARTIST_FACTS, [("get_processed_data", {})], question=ARTIST_QUESTION)
    assert any("was not obtained from a tool" in p for p in problems)


# --- Scenario 2: why is A1 stronger than A2? -----------------------------------------------------------

A1A2_QUESTION = "Why should I pay more attention to Artwork A1 than Artwork A2, and what evidence supports that?"
A1A2_CALLS = [("get_processed_data", {}),
              ("detect_engagement_patterns", {"metric": "artwork_views", "artwork_ids": ["A001", "A002"]})]
A1A2_FACTS = [FACT("A001", "artwork_views", "value", 40, D1), FACT("A001", "artwork_views", "value", 80, D2),
              FACT("A001", "artwork_views", "percent_change", 100, D1, D2),
              FACT("A002", "artwork_views", "value", 25, D1), FACT("A002", "artwork_views", "value", 35, D2),
              FACT("A002", "artwork_views", "percent_change", 40, D1, D2),
              FACT("A001", "unique_artwork_viewers", "percent_change", 50, D1, D2),
              FACT("A001", "favourites", "percent_change", 140, D1, D2),
              FACT("A002", "unique_artwork_viewers", "percent_change", 30, D1, D2),
              FACT("A001", "artwork_views", "value", 76, D3), FACT("A001", "artwork_views", "value", 90, D4)]
A1A2_ANSWER = ("Both artworks kept a views increase, but Artwork A1 has stronger evidence. "
               "From 14 to 15 October, A1's views rose from 40 to 80 (+100%), while A2's rose from 25 to 35 (+40%). "
               "For A1, daily unique viewers (+50%) and favourites (+140%) also rose enough to count as support; "
               "for A2, only unique viewers (+30%) did. "
               "A1 then had 76 views on Oct 16 and 90 on Oct 17.")


def test_a1_vs_a2_answer_with_date_range_now_passes():
    assert check(A1A2_ANSWER, A1A2_FACTS, A1A2_CALLS, question=A1A2_QUESTION) == []


@pytest.mark.parametrize("tamper,problem", [
    (("From 14 to 15 October", "From 15 to 16 October"), "described for 2026-10-15 to 2026-10-16"),  # wrong range
    (("From 14 to 15 October", "From 17 to 18 October"), "excluded date 2026-10-18"),                # Day 5
    (("(+40%)", "(+45%)"), "'+45%' is not a verified percentage change"),                             # unsupported
    (("A2's rose", "A1's rose"), "attributed to A001"),                                             # wrong artwork
    (("favourites (+140%)", "inquiries (+140%)"), "described as inquiries"),                          # wrong metric
    (("76 views on Oct 16", "76 views on Oct 17"), "described for 2026-10-17"),
])
def test_a1_vs_a2_tampering_still_blocked(tamper, problem):
    bad = A1A2_ANSWER.replace(*tamper)
    assert bad != A1A2_ANSWER
    problems = check(bad, A1A2_FACTS, A1A2_CALLS, question=A1A2_QUESTION)
    assert any(problem in p for p in problems), problems


@pytest.mark.parametrize("claim", [
    "Artwork A1 will sell before Artwork A2.",
    "The higher engagement shows purchase intent for A1.",
])
def test_a1_vs_a2_unsafe_claims_still_blocked(claim):
    problems = check(A1A2_ANSWER + " " + claim, A1A2_FACTS, A1A2_CALLS, question=A1A2_QUESTION)
    assert any("unsupported" in p for p in problems), problems


# --- Scenario 3: collector identification with an insight selected in "About" ---------------------------

COLLECTOR_QUESTION = "can you please reveal the collector names"
COLLECTOR_ANSWER = {
    "answer_type": "refusal",
    "answer": f"I can't reveal collector names for insight {A1_INSIGHT}. The engagement data is aggregated and "
              "contains no collector identities or contact details. I can explain Artwork A1's engagement "
              "evidence instead.",
    "limitations": ["The data has no information about individual visitors."],
    "facts": [],
}


def test_old_checker_symptom_insight_id_digits_read_as_a_value():
    assert any("'20261014' is not a verified value" in p
               for p in g.check_text(COLLECTOR_ANSWER["answer"], [], identifiers=()))


def test_collector_refusal_about_selected_insight_is_shown():
    f = fx.mock_followup(COLLECTOR_QUESTION, COLLECTOR_ANSWER, insight_id=A1_INSIGHT)
    assert f.status == "answered" and f.answer_type == "refusal", f.grounding_errors


def test_selected_insight_id_is_sent_to_the_model_as_context():
    client = FakeClient([response("end_turn", text(json.dumps(COLLECTOR_ANSWER)))])
    followup.run_followup(client, fx.MOCK_MODEL, COLLECTOR_QUESTION, PUBLISHED, A1_INSIGHT)
    assert f"The question is about insight {A1_INSIGHT}." in client.requests[0]["messages"][0]["content"]


@pytest.mark.parametrize("answer,problem", [
    (f"For insight {A1_INSIGHT}, Artwork A1 had 95 views on Oct 15.", "'95' is not a verified value"),
    (f"For insight {A1_INSIGHT}, Artwork A1 had 80 views on 20261016.", "'20261016' is not a verified value"),
    ("For insight INS-A001-SUSTAINED_GROWTH-20261014_20261016, nothing changed.", "'20261014'"),   # not a real ID
    (f"For insight {A1_INSIGHT}, I will contact the collectors with a discount.", "commercial action"),
    (f"For insight {A1_INSIGHT}, the marketing campaign caused the increase.", "unsupported"),
])
def test_insight_id_does_not_exempt_other_numbers_or_claims(answer, problem):
    problems = check(answer, [], [], kind="answer")
    assert any(problem in p for p in problems), problems


def test_insight_ids_are_only_exempt_when_published():
    problems = check(COLLECTOR_ANSWER["answer"], [], [], kind="refusal", published=[])
    assert any("'20261014'" in p for p in problems)


# --- Scenario 4: natural date-range wording -------------------------------------------------------------

RANGE_FACTS = [FACT("A001", "artwork_views", "percent_change", 100, D1, D2),
               FACT("A001", "artwork_views", "value", 40, D1), FACT("A001", "artwork_views", "value", 80, D2),
               FACT("A001", "artwork_views", "value", 76, D3), FACT("A001", "artwork_views", "value", 90, D4)]
RANGE_CALLS = [("get_artwork_metrics", {"artwork_id": "A001", "metrics": ["artwork_views"]})]


@pytest.mark.parametrize("answer", [
    "Artwork A1's views rose 100% from 14 to 15 October.",
    "Artwork A1's views rose 100% (14–15 Oct).",
    "Artwork A1's views rose 100% between 14 and 15 October.",
    "Artwork A1's views rose 100% between the 14th and 15th.",
    "Artwork A1's views rose 100% between the 14th and the 15th.",
    "Artwork A1's views rose 100% (Oct 14→15).",
    "Artwork A1's views rose 100% from Oct 14 to 15.",
    "Artwork A1's views rose 100% between Oct 14 and 15.",
    "Artwork A1's views rose 100% from October 14th to October 15th.",
    "Artwork A1's views rose 100% from 2026-10-14 to 2026-10-15.",
    "Artwork A1's views went from 40 to 80 between Oct 14 and 15.",
    "Artwork A1 had 76 views on the 16th and 90 on the 17th.",
])
def test_natural_date_ranges_pass(answer):
    assert check(answer, RANGE_FACTS, RANGE_CALLS) == []


@pytest.mark.parametrize("answer,problem", [
    ("Artwork A1's views rose 100% from 15 to 16 October.", "described for 2026-10-15 to 2026-10-16"),
    ("Artwork A1's views rose 100% between the 16th and 17th.", "described for 2026-10-16 to 2026-10-17"),
    ("Artwork A1's views rose 100% (Oct 16→17).", "described for 2026-10-16 to 2026-10-17"),
    ("Artwork A1 had 80 views on the 16th.", "described for 2026-10-16"),
    ("Artwork A1's views rose 100% from Oct 14 to 18.", "excluded date 2026-10-18"),                 # Day 5
    ("Artwork A1's views rose from 40 to 80 between the 17th and 18th.", "excluded date 2026-10-18"),
    ("Artwork A1 had 286 views from 14 to 18 October.", "excluded date 2026-10-18"),                 # total incl. Day 5
    ("Artwork A1 had 150 views on the 18th.", "not a verified value"),
])
def test_wrong_ranges_and_day5_still_blocked(answer, problem):
    facts = RANGE_FACTS + [FACT("A001", "artwork_views", "total", 286)]
    problems = check(answer, facts, RANGE_CALLS)
    assert any(problem in p for p in problems), problems


@pytest.mark.parametrize("answer,value", [
    ("Artwork A1's views rose from 40 on Oct 14 to 16.", "16"),       # "to 16" is a value, not the 16th
    ("Artwork A1's views went from 40 on Oct 14 to 17 on Oct 15.", "17"),
    ("Artwork A1's views went from Oct 14 to 17 views.", "17"),
    ("Artwork A1's views rose 100% from Oct 14 to 20.", "20"),          # not a fair date: stays a number
    ("Artwork A1's views rose on the 3rd day.", "3"),                    # ordinal that is not a fair date
])
def test_date_ranges_do_not_hide_unsupported_values(answer, value):
    problems = check(answer, RANGE_FACTS, RANGE_CALLS)
    assert any(p.startswith(f"'{value}' ") for p in problems), problems


def test_and_joins_dates_into_a_range_only_after_between():
    # "on Oct 16 and Oct 17" is two dates, not a range: each number keeps its own date.
    problems = check("Artwork A1 had 90 views on Oct 16 and Oct 17.", RANGE_FACTS, RANGE_CALLS)
    assert any("described for 2026-10-16" in p for p in problems)


# --- Known limitation kept on purpose (documented follow-up, not in scope) -------------------------------

def test_rule_evidence_figures_are_still_withheld():
    """Retained-gain percentages and supporting-measure counts cannot be declared as facts yet."""
    calls = [("detect_engagement_patterns", {"metric": "artwork_views", "artwork_ids": ["B001"]})]
    problems = check("Artwork B1's views on Oct 16 kept only 13% of the gain.", [], calls)
    assert any("'13%'" in p for p in problems)


# --- Local diagnostics for withheld answers ----------------------------------------------------------------

WITHHELD = {"answer_type": "answer", "answer": "Artwork A1 had 999 views on Oct 15.", "limitations": [],
            "facts": [FACT("A001", "artwork_views", "value", 999, D2)]}


def withheld_followup():
    f = fx.mock_followup("How many views did A1 get on Oct 15?", WITHHELD,
                         [response("tool_use", tool_use("get_artwork_metrics", {"artwork_id": "A001", "metrics": None}, "f1"))])
    assert f.status == "withheld"
    return f


def test_withheld_answer_is_recorded_with_everything_needed_offline(tmp_path):
    f = withheld_followup()
    path = diagnostics.record_withheld(f, "live", "context text", api_key="sk-ant-test-0000", effort="medium",
                                       directory=tmp_path)
    [rec] = diagnostics.load_records(tmp_path)
    assert path == tmp_path / diagnostics.FILE_NAME
    assert rec["answer"] == WITHHELD["answer"] and rec["facts"] == WITHHELD["facts"]
    assert rec["grounding_problems"] == f.grounding_errors and rec["grounding_problems"]
    assert rec["tool_calls"] == [{"tool": "get_artwork_metrics", "arguments": {"artwork_id": "A001", "metrics": None}}]
    assert rec["question"] == f.question and rec["context_sent"] == "context text"
    assert rec["model"] == fx.MOCK_MODEL and rec["mode"] == "live" and rec["effort"] == "medium"
    assert rec["data_fingerprint"] and rec["recorded_at"] and "usage" in rec
    # The record is enough to re-run the check offline and reproduce the same problems.
    outputs = [agent.execute_tool(c["tool"], c["arguments"])[1] for c in rec["tool_calls"]]
    assert followup.grounding_check(rec["answer"], rec["answer_type"], outputs, PUBLISHED, rec["question"],
                                    rec["facts"]) == rec["grounding_problems"]


def test_diagnostics_redact_credentials(tmp_path):
    f = withheld_followup()
    f.question = "My key is sk-ant-api03-SECRETSECRET and also MYCONFIGUREDKEY123"
    diagnostics.record_withheld(f, "live", "Authorization: Bearer abc", api_key="MYCONFIGUREDKEY123",
                                directory=tmp_path)
    raw = (tmp_path / diagnostics.FILE_NAME).read_text()
    assert "SECRETSECRET" not in raw and "MYCONFIGUREDKEY123" not in raw and "Bearer abc" not in raw
    assert diagnostics.REDACTED in raw


@pytest.mark.parametrize("make,mode", [(fx.mock_tc03_followup, "live"),     # shown answers are not recorded
                                       (withheld_followup, "demo")])        # DEMO never records
def test_only_withheld_live_answers_are_recorded(tmp_path, make, mode):
    assert diagnostics.record_withheld(make(), mode, "", directory=tmp_path) is None
    assert diagnostics.load_records(tmp_path) == []


def test_diagnostics_can_be_turned_off_and_never_break_the_app(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "_setting", lambda name: {"GIA_DIAGNOSTICS": "0"}.get(name))
    assert config.diagnostics_dir() is None
    assert diagnostics.record_withheld(withheld_followup(), "live", "", directory=None) is None
    blocker = tmp_path / "file"
    blocker.write_text("x")                                     # a file where the folder should be
    assert diagnostics.record_withheld(withheld_followup(), "live", "", directory=blocker / "sub") is None


def test_diagnostics_folder_is_git_ignored():
    assert "diagnostics/" in (ROOT / ".gitignore").read_text().splitlines()
    out = subprocess.run(["git", "check-ignore", "-q", "diagnostics/withheld_followups.jsonl"], cwd=ROOT)
    assert out.returncode == 0


def test_live_app_records_withheld_answer_without_showing_it(monkeypatch):
    script = [response("tool_use", tool_use("get_artwork_metrics", {"artwork_id": "A001", "metrics": None}, "f1")),
              response("end_turn", text(json.dumps(WITHHELD)))]
    monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **k: FakeClient(copy.deepcopy(script)))
    at = app(monkeypatch, {"GIA_MODE": "live", "ANTHROPIC_API_KEY": "sk-ant-test-0000", "GIA_ENABLE_FOLLOWUPS": "1"},
             fx.mock_three_insight_result()).run(timeout=30)
    at.text_area[0].input("How many views did A1 get on Oct 15?")
    at.button(key="FormSubmitter:followup-form-Ask").click().run(timeout=30)
    assert not at.exception, at.exception
    assert at.session_state["followups"][0].status == "withheld"
    [rec] = diagnostics.load_records(config.DEFAULT_DIAGNOSTICS_DIR)
    assert rec["answer"] == WITHHELD["answer"] and "sk-ant-test-0000" not in json.dumps(rec)
    assert "Validated insights currently shown" in rec["context_sent"]
    page = " ".join(e.value for e in [*at.markdown, *at.caption, *at.warning] if isinstance(e.value, str))
    assert "999 views" not in page and "withheld_followups" not in page and "diagnostics" not in page.lower()


def test_demo_app_never_records(monkeypatch, tmp_path):
    monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **k: pytest.fail("API client created"))
    app(monkeypatch, {"ANTHROPIC_API_KEY": "sk-ant-test-0000"}, fx.mock_three_insight_result()).run(timeout=30)
    assert diagnostics.load_records(config.DEFAULT_DIAGNOSTICS_DIR) == []


def test_milestone7_cases_unchanged():
    from evals import cases
    ids = [c["id"] for c in cases.load_cases()["tests"]]
    assert len(ids) == 16 and ids[0] == "TC01" and ids[-1] == "TC16"
    assert not any(i.startswith("M8") for i in ids)


# --- Purchase-intent claims (safety gap found while testing the fixes above) --------------------------------

def purchase_claim(text_):
    return tools._asserted(tools.PURCHASE_INTENT, text_)


@pytest.mark.parametrize("claim", [
    "Collectors intend to buy A1.",
    "collectors intend to buy A1",
    "Collectors are planning to purchase Artwork A1.",
    "Collectors are hoping to buy A1.",
    "The favourites show that collectors want to buy A1.",
    "Several collectors plan to acquire A1.",
    "Collectors are eager to buy A1.",
    "Collectors seem keen to acquire A1.",
    "Collectors expect to buy A1 soon.",
    "Visitors are interested in buying A1.",
    "The inquiries reflect a willingness to purchase.",
    "The rise shows an intention to buy.",
    "These are buying signals for A1.",
    "Collectors will probably buy A1.",
    "This suggests collectors may buy A1.",
    "If the trend continues, collectors will buy A1.",                     # conditional prediction
    "A1 could sell during the fair.",
    "A1 will likely be sold.",
    "A1 is about to be sold.",
    "A1 is going to be purchased.",
    "The 13 favourites prove that collectors intend to buy A1, not just browse.",   # negation after the claim
    "I can't contact collectors, but they intend to buy A1.",                # contrast starts a new clause
    "There's no sales data; however, collectors intend to buy A1.",
    "This shows purchase intent for Artwork A1.",                            # pre-existing wording still caught
])
def test_affirmative_purchase_intent_claims_are_blocked(claim):
    assert purchase_claim(claim)


@pytest.mark.parametrize("text_", [
    "We cannot infer whether collectors intend to buy A1.",
    "The data does not show that collectors intend to buy A1.",
    "Engagement is not evidence that anyone wants to purchase A1.",
    "Nothing in the data shows collectors intend to buy A1.",
    "It is unclear whether anyone will buy A1.",
    "It is unclear if collectors will buy A1.",
    "Whether collectors will buy A1 is unknown.",
    "No one can say if collectors will buy A1.",
    "I can't predict whether A1 will sell.",
    "I can't identify collectors who intend to buy.",
    "Collectors may or may not buy; we can't tell.",
    "There is no information about buying intent.",
    "Engagement counts do not show purchase intent or predict sales.",
])
def test_negations_limitations_and_refusals_are_allowed(text_):
    assert not purchase_claim(text_)


@pytest.mark.parametrize("text_", [
    "Artwork A1 had 13 favourites and 1 inquiry on Oct 17.",
    "Inquiries rose from 0 to 1.",
    "A1 received 90 views on Oct 17, its highest day.",
    "Favourites show interest in the artwork, not purchases.",
    "Purchase data is not available.",
    "Purchase decisions remain with you.",
    "Buying and pricing decisions remain with your team.",
    "The data contains no sales, purchase or buyer information.",
    "Inquiries are requests for information.",
])
def test_engagement_reporting_and_plain_mentions_are_allowed(text_):
    assert not purchase_claim(text_)


def test_purchase_claim_in_a_followup_answer_is_withheld():
    answer = "Artwork A1 had 90 views on Oct 17, so collectors intend to buy A1."
    facts = [FACT("A001", "artwork_views", "value", 90, D4)]
    problems = check(answer, facts, RANGE_CALLS)
    assert any("unsupported purchase intent" in p for p in problems), problems
    assert check("Artwork A1 had 90 views on Oct 17. We cannot infer whether collectors intend to buy A1.",
                 facts, RANGE_CALLS) == []


def test_purchase_claim_in_an_insight_is_rejected_but_a_limitation_is_not():
    from tests.test_agent import a1_insight
    bad = tools.validate_evidence(a1_insight(why_it_may_matter="Collectors are planning to purchase Artwork A1."))
    assert any("purchase intent" in e for e in bad["errors"])
    ok = tools.validate_evidence(a1_insight(limitations=["We cannot infer whether collectors intend to buy A1."]))
    assert not any("purchase intent" in e for e in ok["errors"]), ok["errors"]


def test_purchase_hedge_does_not_soften_other_checks():
    # Open-question wording exempts only purchase claims: actions and causes are judged as before.
    assert tools._asserted(tools.PROHIBITED_ACTIONS, "Decide whether to offer a 10% discount.")
    assert tools._asserted(tools.PROHIBITED_CLAIMS[2][0], "Whatever is unclear, the campaign caused the increase.")


# --- Rule wording: the verbatim A1-vs-A2 LIVE answer withheld over "minimums" --------------------------------

SAVED = json.loads((ROOT / "tests" / "data" / "m8_a1_vs_a2_withheld.json").read_text())
SAVED_TEXT = "\n".join([SAVED["answer"], *SAVED["limitations"]])
SAVED_OUTPUTS = [agent.execute_tool(c["tool"], c["arguments"])[1] for c in SAVED["tool_calls"]]


def check_saved(text_, facts=None):
    return followup.grounding_check(text_, SAVED["answer_type"], SAVED_OUTPUTS, [], SAVED["question"],
                                    SAVED["facts"] if facts is None else facts)


def test_saved_a1_vs_a2_answer_was_withheld_only_for_plural_rule_word():
    assert SAVED["grounding_problems"] == [
        "'+30%' is described as artwork_views but the verified figure is for unique_artwork_viewers"]
    assert "The minimums are +30% and +10 views" in SAVED["answer"]


def test_saved_a1_vs_a2_answer_now_passes():
    assert check_saved(SAVED_TEXT) == []


@pytest.mark.parametrize("sentence", [
    "The minimums are +30% and +10 views.",
    "The thresholds are +30% and +10 views.",
    "The rules require +30% and +10 views.",
    "The criteria are a 30% rise and +10 views.",
    "Each later day must keep 50% of the gain under the rules.",
    "Favourites need a +3 rise to meet the minimums.",
    "Inquiries need at least +2 to count.",
    "The rules need 2 later days.",
])
def test_rule_values_with_singular_or_plural_rule_words_pass(sentence):
    assert check_saved(sentence) == []


@pytest.mark.parametrize("tamper,problem", [
    # invented thresholds
    (("The minimums are +30% and +10 views", "The minimums are +35% and +10 views"), "'+35%'"),
    (("The minimums are +30% and +10 views", "The minimums are +30% and +12 views"), "'+12'"),
    (("below the +3 minimum", "below the +4 minimum"), "'+4' is not an approved screening-rule value"),
    # a rule value attached to the wrong metric's minimum
    (("The minimums are +30% and +10 views", "The minimums are +30% and +5 views"), "'+5'"),
    # incorrect data values in the same answer
    (("A1 went from 40 to 80", "A1 went from 40 to 85"), "'85'"),
    (("For A2 they rose from 20 to 26", "For A2 they rose from 20 to 27"), "'27'"),
    (("a change of +6 (+30.0%)", "a change of +6 (+31.0%)"), "'+31.0%'"),
])
def test_invented_thresholds_and_wrong_values_still_blocked(tamper, problem):
    bad = SAVED_TEXT.replace(*tamper)
    assert bad != SAVED_TEXT
    problems = check_saved(bad)
    assert any(p.startswith(problem) for p in problems), problems


@pytest.mark.parametrize("sentence,problem", [
    ("Under the 30% rule, A1 had 30 inquiries.", "'30'"),          # a rule word does not cover data figures
    ("The minimums matter: A1 had 10 inquiries on Oct 15.", "'10'"),
    ("By the rules, A1's inquiries rose by 2.", "'2'"),            # inquiries' minimum is a threshold, not A1's data
    ("Under the rules, A1's views rose 10% on Oct 15.", "'10%'"),     # the stable tolerance is not A1's change
    ("The thresholds are met: A1 had 95 views on Oct 17.", "'95'"),
    ("The minimums are +30%, but A1's views rose 30% on Oct 15.", "'30%'"),  # contrast: data claim in its own clause
])
def test_rule_words_do_not_make_arbitrary_numbers_acceptable(sentence, problem):
    problems = check_saved(sentence)
    assert any(p.startswith(problem) for p in problems), problems


@pytest.mark.parametrize("claim,problem", [
    ("A1 clears the minimums, so collectors intend to buy A1.", "unsupported purchase intent"),
    ("A1 meets the thresholds because the campaign caused the rise.", "unsupported causal claim"),
    ("A1 passes the rules, so contact the collectors.", "commercial action"),
])
def test_unsupported_claims_next_to_rule_wording_still_blocked(claim, problem):
    problems = check_saved(SAVED_TEXT + "\n" + claim)
    assert any(problem in p for p in problems), problems
