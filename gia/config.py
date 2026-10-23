"""Runtime configuration: API key, model and limits.

Values come from environment variables or Streamlit secrets (.streamlit/secrets.toml
locally, the app's Secrets settings on Streamlit Community Cloud). The API key is
never logged, displayed or written into traces.
"""

from __future__ import annotations

import os

MODES = ("demo", "live")
DEFAULT_MODE = "demo"               # safe default: no API calls unless GIA_MODE=live is set server-side
DEFAULT_MODEL = "claude-sonnet-5-5"
DEFAULT_EFFORT = "medium"
DEFAULT_MAX_TOOL_CALLS = 15
DEFAULT_MAX_ANALYSES_PER_SESSION = 5
DEFAULT_MAX_OUTPUT_TOKENS = 8000    # hard cap per API response (includes thinking)
DEFAULT_MAX_COST_PER_ANALYSIS_USD = 0.75  # analysis stops if estimated spend passes this

# Published per-million-token prices (USD) used only for the cost estimate shown in the app.
PRICES_PER_MTOK = {
    "claude-sonnet-5-5": {"input": 2.00, "output": 10.00, "cache_read": 0.20, "cache_write": 2.50},
}


def _setting(name: str) -> str | None:
    value = os.environ.get(name)
    if value:
        return value
    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:  # no secrets file, or not running under Streamlit
        pass
    return None


def mode() -> str:
    """'live' only when explicitly configured; anything else (unset, typo) is 'demo'.

    GIA_FORCE_DEMO=1 always wins. Streamlit copies root-level secrets into os.environ at startup
    (overwriting a GIA_MODE set in the shell), so a kill switch with its own name is needed to
    guarantee demo mode, e.g. for local previews or as a second lock on the public deployment."""
    if (_setting("GIA_FORCE_DEMO") or "").strip() == "1":
        return "demo"
    value = (_setting("GIA_MODE") or DEFAULT_MODE).strip().lower()
    return value if value in MODES else DEFAULT_MODE


def max_output_tokens() -> int:
    return int(_setting("GIA_MAX_OUTPUT_TOKENS") or DEFAULT_MAX_OUTPUT_TOKENS)


def max_cost_per_analysis_usd() -> float:
    return float(_setting("GIA_MAX_COST_PER_ANALYSIS_USD") or DEFAULT_MAX_COST_PER_ANALYSIS_USD)


def demo_snapshot_path() -> str | None:
    """Optional server-side override for the DEMO recording file (used for local previews)."""
    return _setting("GIA_DEMO_SNAPSHOT")


def api_key() -> str | None:
    return _setting("ANTHROPIC_API_KEY")


def model() -> str:
    return _setting("GIA_MODEL") or DEFAULT_MODEL


def effort() -> str:
    return _setting("GIA_EFFORT") or DEFAULT_EFFORT


def max_tool_calls() -> int:
    return int(_setting("GIA_MAX_TOOL_CALLS") or DEFAULT_MAX_TOOL_CALLS)


def max_analyses_per_session() -> int:
    return int(_setting("GIA_MAX_ANALYSES_PER_SESSION") or DEFAULT_MAX_ANALYSES_PER_SESSION)
