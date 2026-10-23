"""Milestone 3 tests: the agent loop, using a scripted fake Claude client (no API calls, no cost)."""

import json
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from gia import agent

D1, D2, D5 = "2026-10-14", "2026-10-15", "2026-10-18"


# --- A fake Anthropic client that replays scripted responses -----------------------

def tool_use(name, args, id_):
    return SimpleNamespace(type="tool_use", id=id_, name=name, input=args)


def text(t):
    return SimpleNamespace(type="text", text=t)


def response(stop_reason, *content):
    usage = SimpleNamespace(input_tokens=1000, output_tokens=200,
                            cache_read_input_tokens=0, cache_creation_input_tokens=0)
    return SimpleNamespace(stop_reason=stop_reason, content=list(content), usage=usage)


class FakeClient:
    def __init__(self, script):
        self.script = list(script)
        self.requests = []
        self.messages = SimpleNamespace(create=self._create)
        self.models = SimpleNamespace(retrieve=lambda model: SimpleNamespace(id=model))

    def _create(self, **request):
        self.requests.append(json.loads(json.dumps(request, default=lambda o: vars(o))))
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def a1_insight(**overrides):
    insight = {
        "signal_type": "sustained_growth", "artwork_id": "A001", "artist_id": "AR01",
        "title": "Artwork A1 engagement rose and stayed higher",
        "observed_signal": "Artwork views rose from 40 to 80 (+100%) between 2026-10-14 and 2026-10-15, with "
                           "daily unique viewers 30 to 45 (+50%) and favourites 5 to 12 (+140%).",
        "why_it_may_matter": "Several engagement signals rose together and views stayed higher afterwards.",
        "suggested_next_step": "Consider reviewing Artwork A1 in the next internal sales discussion.",
        "confidence": "higher-confidence",
        "limitations": ["Engagement does not show purchase intent.", "Inquiries stayed at 0."],
        "metric_changes": [
            {"artwork_id": "A001", "metric": m, "old_date": D1, "new_date": D2, "old_value": o,
             "new_value": n, "absolute_change": n - o, "percentage_change": p}
            for m, o, n, p in [("artwork_views", 40, 80, 100.0), ("unique_artwork_viewers", 30, 45, 50.0),
                               ("favourites", 5, 12, 140.0), ("inquiries", 0, 0, None)]],
        "metric_totals": [],
    }
    insight.update(overrides)
    return insight


def final(insights, not_surfaced=()):
    return response("end_turn", text(json.dumps(
        {"summary": "Test summary.", "insights": insights, "not_surfaced": list(not_surfaced)})))


def happy_script():
    return [
        response("tool_use", tool_use("get_processed_data", {}, "t1")),
        response("tool_use", tool_use("detect_engagement_patterns", {"metric": "artwork_views", "artwork_ids": None}, "t2")),
        response("tool_use", tool_use("compare_daily_metrics",
                                      {"artwork_id": "A001", "old_date": D1, "new_date": D2, "metrics": None}, "t3"),
                 tool_use("validate_evidence", {"insight": a1_insight()}, "t4")),
        final([a1_insight()], [{"artwork_id": "B002", "category": "stable", "reason": "Stable."}]),
    ]


def run(script, **kw):
    client = FakeClient(script)
    return agent.run_analysis(client, "claude-sonnet-5-5", **kw), client


# --- Tool definitions -------------------------------------------------------------

def test_exactly_six_approved_tools_and_all_strict():
    names = [t["name"] for t in agent.TOOL_DEFINITIONS]
    assert names == ["get_processed_data", "get_artwork_metrics", "compare_daily_metrics",
                     "aggregate_artist_metrics", "detect_engagement_patterns", "validate_evidence"]
    assert all(t["strict"] for t in agent.TOOL_DEFINITIONS)


def test_no_commercial_action_tools():
    text_blob = json.dumps(agent.TOOL_DEFINITIONS).lower()
    for word in ("send", "email", "contact", "price", "discount", "update_listing", "notify"):
        assert f'"name": "{word}' not in text_blob


# --- Happy path -----------------------------------------------------------------

def test_happy_path_runs_real_tools_and_publishes_validated_insight():
    result, client = run(happy_script())
    assert result.status == "completed"
    assert result.tool_calls == 4
    assert [s.tool for s in result.trace if s.kind == "tool_call"] == [
        "get_processed_data", "detect_engagement_patterns", "compare_daily_metrics", "validate_evidence"]
    assert [p["insight_id"] for p in result.published] == ["INS-A001-SUSTAINED_GROWTH-20261014_20261015"]
    assert result.withheld == []
    # The real tool output (not anything the model wrote) was returned to Claude.
    tool_result = client.requests[1]["messages"][-1]["content"][0]
    assert tool_result["tool_use_id"] == "t1" and not tool_result["is_error"]
    assert json.loads(tool_result["content"])["gallery_profile_views"]["total"] == 615


def test_both_parallel_tool_results_returned_in_one_message():
    _, client = run(happy_script())
    results = client.requests[3]["messages"][-1]["content"]
    assert [r["tool_use_id"] for r in results] == ["t3", "t4"]


def test_request_shape():
    _, client = run(happy_script())
    req = client.requests[0]
    assert req["model"] == "claude-sonnet-5-5"
    assert req["output_config"]["format"]["type"] == "json_schema"
    assert "fallbacks" not in req and "betas" not in req   # no automatic model fallback
    assert "tool_choice" not in req                       # auto; forced tool use is not supported


def test_usage_and_cost_are_tracked():
    result, _ = run(happy_script())
    assert result.usage["input_tokens"] == 4000 and result.usage["output_tokens"] == 800
    assert result.estimated_cost_usd == pytest.approx((4000 * 2 + 800 * 10) / 1_000_000)


# --- Validation of tool calls -------------------------------------------------------

def test_unknown_tool_is_rejected_and_reported_to_claude():
    result, client = run([response("tool_use", tool_use("send_email", {"to": "x"}, "t1")), final([])])
    assert result.trace[1].kind == "tool_error"
    returned = client.requests[1]["messages"][-1]["content"][0]
    assert returned["is_error"] and "Only these approved tools exist" in returned["content"]


def test_invalid_arguments_are_rejected():
    result, _ = run([response("tool_use", tool_use("compare_daily_metrics", {"artwork_id": "A001"}, "t1")),
                     final([])])
    assert "Missing argument" in result.trace[1].detail


def test_day5_request_returns_tool_error_not_data():
    result, client = run([response("tool_use", tool_use(
        "compare_daily_metrics", {"artwork_id": "A001", "old_date": D2, "new_date": D5, "metrics": None}, "t1")),
        final([])])
    returned = client.requests[1]["messages"][-1]["content"][0]
    assert returned["is_error"] and "day_processed=false" in returned["content"]


# --- Bounds and failures ---------------------------------------------------------------

def test_tool_call_limit_is_enforced():
    script = [response("tool_use", tool_use("get_processed_data", {}, f"t{i}")) for i in range(3)]
    script.append(final([]))
    result, client = run(script, max_tool_calls=2)
    assert result.tool_calls == 2
    assert result.status == "limit_reached"
    assert any(s.kind == "limit" for s in result.trace)
    assert client.requests[-1]["tool_choice"] == {"type": "none"}


def test_api_connection_error_is_reported_cleanly():
    err = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))
    result, _ = run([err])
    assert result.status == "failed"
    assert "Could not reach" in result.error
    assert result.published == []


def test_refusal_publishes_nothing():
    result, _ = run([response("refusal")])
    assert result.status == "refused" and result.published == []


def test_unreadable_final_answer_publishes_nothing():
    result, _ = run([response("end_turn", text("not json"))])
    assert result.status == "failed" and result.published == []


# --- Mandatory publication gate --------------------------------------------------------

def test_gate_withholds_wrong_number_even_if_model_proposes_it():
    bad = a1_insight()
    bad["metric_changes"][0]["percentage_change"] = 90.0
    result, _ = run([final([bad])])
    assert result.published == [] and len(result.withheld) == 1


def test_gate_withholds_relabelled_spike():
    spike_as_growth = a1_insight(
        artwork_id="B001", artist_id="AR02", title="Artwork B1 grew",
        observed_signal="Artwork views rose from 30 to 45 (+50%).",
        why_it_may_matter="Views increased.", suggested_next_step=None,
        limitations=["Single comparison."],
        metric_changes=[{"artwork_id": "B001", "metric": "artwork_views", "old_date": D1, "new_date": D2,
                         "old_value": 30, "new_value": 45, "absolute_change": 15, "percentage_change": 50.0}])
    result, _ = run([final([spike_as_growth])])
    assert result.published == []
    assert any("does not match the deterministic classification 'temporary_spike'" in e
               for e in result.withheld[0]["errors"])


def test_gate_requires_matching_confidence_label():
    result, _ = run([final([a1_insight(confidence="moderate-confidence")])])
    assert result.published == []


def test_gate_withholds_suppressed_stable_pattern():
    stable = a1_insight(
        signal_type="stable", artwork_id="B002", artist_id="AR02", confidence="qualified",
        title="Artwork B2 stable", observed_signal="Views went from 20 to 21.", why_it_may_matter="Stable.",
        suggested_next_step=None, limitations=["Stable."],
        metric_changes=[{"artwork_id": "B002", "metric": "artwork_views", "old_date": D1, "new_date": D2,
                         "old_value": 20, "new_value": 21, "absolute_change": 1, "percentage_change": 5.0}])
    result, _ = run([final([stable])])
    assert result.published == []


def test_gate_withholds_purchase_intent_language():
    result, _ = run([final([a1_insight(why_it_may_matter="This shows strong purchase intent.")])])
    assert result.published == []


def test_no_insight_is_a_valid_outcome():
    result, _ = run([final([], [{"artwork_id": "B002", "category": "stable", "reason": "Stable."}])])
    assert result.status == "completed"
    assert result.published == [] and result.not_surfaced


def test_trace_never_contains_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-secret-value")
    result, client = run(happy_script())
    blob = json.dumps([vars(s) for s in result.trace], default=str) + json.dumps(client.requests)
    assert "sk-ant-test-secret-value" not in blob
