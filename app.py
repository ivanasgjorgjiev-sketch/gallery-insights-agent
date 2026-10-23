"""Gallery Insights Agent — Streamlit entry point.

Milestone 3: data status, the LLM-driven investigation loop, its trace and a simple
display of validated findings. (Insight cards, evidence review, feedback and chat
come in later milestones.)
"""

import datetime as dt

import anthropic
import pandas as pd
import streamlit as st

from gia import agent, config
from gia.data import DataValidationError, load_processed_data
from gia.display_names import edition_label, gallery_name

GALLERY_ID = "G001"
EDITION_IDS = ["E001"]
STEP_ICONS = {"model_turn": "🧠", "tool_call": "🛠️", "tool_error": "⚠️", "limit": "⛔",
              "final": "📋", "gate": "✅", "error": "❌"}


def format_date(iso: str) -> str:
    return dt.date.fromisoformat(iso).strftime("%b %d, %Y")


def step_line(step: agent.TraceStep) -> str:
    line = f"{STEP_ICONS.get(step.kind, '•')} **{step.step}. {step.title}**"
    if step.kind in ("tool_call", "tool_error", "limit") and step.arguments is not None:
        args = ", ".join(f"{k}={v!r}" for k, v in step.arguments.items() if v is not None
                         and k != "insight") or ("insight=" + step.arguments["insight"]["artwork_id"]
                                                 if "insight" in step.arguments else "")
        line += f"({args})"
    if step.detail:
        line += f" — {step.detail}"
    return line


st.set_page_config(page_title="Gallery Insights Agent", page_icon="🖼️", layout="wide")

st.info(
    "**Demonstration prototype using synthetic data.** All galleries, artists, "
    "artworks and engagement figures are fictional."
)

st.title("Gallery Insights Agent")
st.subheader(gallery_name(GALLERY_ID))

edition_id = st.selectbox("Fair edition", EDITION_IDS, format_func=edition_label)

st.caption("🔒 Nothing is sent or changed by this agent. It does not contact anyone or modify business data.")

# --- Data status --------------------------------------------------------------------

st.markdown("#### Data status")
try:
    data = load_processed_data(gallery_id=GALLERY_ID, edition_id=edition_id)
except DataValidationError as err:
    st.error("The engagement data failed validation, so analysis is unavailable.")
    for issue in err.issues:
        st.markdown(f"- {issue}")
    st.stop()

included = ", ".join(format_date(d) for d in data.processed_dates)
st.success(f"Data checks passed. **{len(data.processed_dates)} processed fair days** included: {included}.")
if data.excluded_dates:
    excluded = ", ".join(format_date(d) for d in data.excluded_dates)
    st.warning(f"Excluded from all analysis (not yet processed): {excluded}.")
for note in data.notes:
    st.caption(f"ℹ️ {note}")

with st.expander("View eligible source records"):
    st.caption(f"Source: `{data.source_file}` · {data.eligible_rows} eligible of {data.total_rows} rows")
    st.markdown("**Gallery-profile views (view events)**")
    st.dataframe(data.gallery_daily, hide_index=True)
    st.markdown("**Artwork engagement (daily event counts; blank unique viewers = unknown)**")
    shown = data.artwork_daily.copy()
    shown["unique_artwork_viewers"] = [
        "unknown" if v is pd.NA else str(v) for v in shown["unique_artwork_viewers"]
    ]
    st.dataframe(shown, hide_index=True)

# --- Analysis -------------------------------------------------------------------------

st.divider()
st.markdown("#### Daily engagement analysis")

key = config.api_key()
model = config.model()
runs = st.session_state.get("analyses_run", 0)
limit = config.max_analyses_per_session()

disabled_reason = None
if not key:
    disabled_reason = "The Anthropic API key is not configured, so the agent cannot run yet."
elif runs >= limit:
    disabled_reason = f"This session has reached its limit of {limit} analyses (cost protection)."

clicked = st.button("Analyze Daily Engagement", type="primary", disabled=disabled_reason is not None)
if disabled_reason:
    st.caption(disabled_reason)
else:
    st.caption(f"Model: `{model}` · up to {config.max_tool_calls()} tool calls · "
               f"analysis {runs + 1} of {limit} this session")

if clicked:
    client = anthropic.Anthropic(api_key=key, max_retries=2, timeout=180)
    if st.session_state.get("verified_model") != model:
        try:
            agent.verify_model(client, model)
            st.session_state["verified_model"] = model
        except anthropic.NotFoundError:
            st.error(f"Model `{model}` is not available to this API key. No analysis was run; "
                     "the model is never switched automatically.")
            st.stop()
        except anthropic.APIError as e:
            st.error(f"Could not verify the model ({type(e).__name__}). No analysis was run.")
            st.stop()
    st.session_state["analyses_run"] = runs + 1
    with st.status("The agent is investigating…", expanded=True) as status:
        result = agent.run_analysis(client, model, effort=config.effort(),
                                    max_tool_calls=config.max_tool_calls(),
                                    on_step=lambda s: status.markdown(step_line(s)))
        status.update(label=f"Investigation {result.status.replace('_', ' ')}",
                      state="complete" if result.status == "completed" else "error", expanded=False)
    st.session_state["analysis"] = result

result: agent.AnalysisResult | None = st.session_state.get("analysis")
if result:
    if result.error:
        st.error(f"Analysis {result.status}: {result.error} No unverified findings are shown.")
    elif result.status == "limit_reached":
        st.warning("The tool-call limit was reached; findings are based only on evidence gathered so far.")
    if result.summary:
        st.markdown(f"**Agent summary:** {result.summary}")

    st.markdown(f"**Validated findings ({len(result.published)})**")
    if not result.published and not result.error:
        st.info("No finding met the evidence bar. Nothing is presented rather than inventing an insight.")
    for entry in result.published:
        ins = entry["insight"]
        with st.container(border=True):
            st.markdown(f"**{ins['title']}**  \n`{entry['insight_id']}` · {ins['confidence']}")
            st.markdown(ins["observed_signal"])
            st.markdown(f"*Why it may matter:* {ins['why_it_may_matter']}")
            if ins.get("suggested_next_step"):
                st.markdown(f"*For your consideration:* {ins['suggested_next_step']}")
            st.markdown("*Limitations:* " + " ".join(ins["limitations"]))

    if result.withheld:
        with st.expander(f"Withheld by validation ({len(result.withheld)})"):
            for w in result.withheld:
                st.markdown(f"**{w['insight_id']}**")
                for e in w["errors"]:
                    st.markdown(f"- {e}")
    if result.not_surfaced:
        with st.expander(f"Not surfaced as insights ({len(result.not_surfaced)})"):
            st.dataframe(pd.DataFrame(result.not_surfaced), hide_index=True)

    with st.expander(f"Investigation trace ({result.tool_calls} tool calls, {result.model_turns} model turns)"):
        for s in result.trace:
            st.markdown(step_line(s))
            if s.result is not None:
                st.json(s.result, expanded=False)
    cost = result.estimated_cost_usd
    st.caption(f"Usage: {result.usage['input_tokens']:,} input + {result.usage['cache_read_input_tokens']:,} "
               f"cached + {result.usage['output_tokens']:,} output tokens"
               + (f" · estimated cost ${cost:.3f}" if cost is not None else ""))
