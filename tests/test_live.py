"""Optional live end-to-end test against the real Anthropic API (costs money).

Skipped unless GIA_LIVE_TEST=1 and an API key is configured. Run with:
    GIA_LIVE_TEST=1 .venv/bin/python -m pytest tests/test_live.py -s
"""

import json
import os
from pathlib import Path

import anthropic
import pytest

from gia import agent, config

pytestmark = pytest.mark.skipif(
    os.environ.get("GIA_LIVE_TEST") != "1" or not config.api_key(),
    reason="live API test: set GIA_LIVE_TEST=1 and configure ANTHROPIC_API_KEY",
)


def test_live_analysis_end_to_end():
    client = anthropic.Anthropic(api_key=config.api_key())
    model = config.model()
    assert agent.verify_model(client, model) == model

    result = agent.run_analysis(client, model, effort=config.effort(), max_tool_calls=config.max_tool_calls())

    out = Path(__file__).resolve().parent.parent / "evals" / "results" / "live_m3_run.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "status": result.status, "model": result.model, "summary": result.summary,
        "tool_calls": result.tool_calls, "model_turns": result.model_turns, "usage": result.usage,
        "estimated_cost_usd": result.estimated_cost_usd,
        "trace": [vars(s) for s in result.trace],
        "published": result.published, "withheld": result.withheld, "not_surfaced": result.not_surfaced,
    }, indent=2, default=str))

    assert result.status == "completed", result.error
    tools_used = [s.tool for s in result.trace if s.kind == "tool_call"]
    assert "detect_engagement_patterns" in tools_used
    assert all(t in agent.TOOL_FUNCTIONS for t in tools_used)
    # Every published insight passed the deterministic gate; Day 5 never appears.
    assert "2026-10-18" not in json.dumps(result.published)
    assert "INS-A001-SUSTAINED_GROWTH-20261014_20261015" in [p["insight_id"] for p in result.published]
