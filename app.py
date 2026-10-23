"""Gallery Insights Agent — Streamlit entry point.

Milestone 3: data status, the LLM-driven investigation loop, its trace and a simple
display of validated findings. (Insight cards, evidence review, feedback and chat
come in later milestones.)

GIA_MODE (server-side setting, default "demo"):
- demo: replays a recorded live investigation; never creates an Anthropic client.
- live: real Claude tool calling, with per-response, per-analysis and per-session limits.
"""

import datetime as dt

import anthropic
import pandas as pd
import streamlit as st

from gia import agent, config, evidence, explain, review, snapshot
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
        parts = []
        for k, v in step.arguments.items():
            if v is None:
                continue
            if k == "insight":  # a full draft insight (live) or a short label (recorded)
                v = f"draft for {v.get('artwork_id', '?')}" if isinstance(v, dict) else v
                parts.append(f"insight: {v}")
            else:
                parts.append(f"{k}={v!r}")
        line += f"({', '.join(parts)})"
    if step.detail:
        line += f" — {step.detail}"
    return line


STRENGTH_BADGES = {
    "higher-confidence": ":green-badge[Higher-confidence]",
    "moderate-confidence": ":blue-badge[Moderate-confidence]",
    "qualified": ":orange-badge[Qualified signal]",
}


def render_key_metrics(pattern: dict) -> None:
    """Deterministic metric tiles for the key comparison (values from the tools, not the model)."""
    kc = pattern["key_comparison"]
    if not kc:
        return
    rows = [{"metric": pattern["metric"], **kc}] + pattern["supporting_metrics"]
    cols = st.columns(len(rows))
    for col, r in zip(cols, rows):
        counts = r.get("qualifies_as_support", True)  # the key metric itself always counts
        if r["status"] == "unavailable":
            delta, color = None, "off"
        elif r["status"] == "zero_baseline":
            delta, color = ("no change" if r["absolute_change"] == 0 else f"{r['absolute_change']:+d} (from 0)"), \
                ("off" if r["absolute_change"] == 0 else "normal")
        else:
            delta, color = f"{r['percentage_change']:+.1f}%", "normal"
        if r["absolute_change"] == 0:
            delta = None  # no arrow for "no change"
        if counts is False:
            color = "off"  # grey: changed, but not enough to count as support
        col.metric(explain.METRIC_NAMES[r["metric"]],
                   f"{explain.fmt_value(r['old_value'])} → {explain.fmt_value(r['new_value'])}",
                   delta=delta, delta_color=color,
                   help=explain.MISSING_NOTE if r["status"] == "unavailable"
                   else explain.ZERO_NOTE if r["status"] == "zero_baseline"
                   else "Changed, but not enough to count as support." if counts is False else None)
    st.caption(f"Comparison: {explain.fmt_date_long(kc['old_date'])} → {explain.fmt_date_long(kc['new_date'])}. "
               "Grey changes did not count as supporting evidence.")


def render_evidence(ev: dict) -> None:
    with st.container(border=True):
        st.markdown("##### Evidence")
        st.dataframe([{"": k, "Value": v} for k, v in ev["context"].items()], hide_index=True)
        st.markdown("**Daily source records**")
        st.dataframe(ev["daily"], hide_index=True)
        if ev["comparison"]:
            old, new = ev["comparison_dates"]
            st.markdown(f"**Key comparison: {explain.fmt_date_long(old)} → {explain.fmt_date_long(new)}**")
            st.dataframe(ev["comparison"], hide_index=True)
        with st.expander("Technical details: screening checks, validation and notes"):
            st.markdown(f"**Pattern found: {ev['pattern_label']}.** {ev['why_highlighted']}")
            st.markdown("**Screening checks** (transparent rules, applied the same way to every artwork)")
            st.dataframe(ev["checks"], hide_index=True)
            st.markdown("**Validation of this insight's numbers**")
            st.dataframe(ev["verified_claims"], hide_index=True)
            st.markdown(f"**Agent's description** (validated against the source)  \n{ev['agent_description']}")
            st.caption(ev["artist_context"])
            st.markdown("**How to read this evidence**")
            for note in ev["notes"]:
                st.markdown(f"- {note}")


def current_review() -> review.ReviewState | None:
    """The review state for the analysis on screen (created if missing or out of date)."""
    result = st.session_state.get("analysis")
    if result is None:
        return None
    state = st.session_state.get("review")
    if state is None or state.insight_ids != [p["insight_id"] for p in result.published]:
        state = st.session_state["review"] = review.start_review(result)
    return state


def show_analysis(result: agent.AnalysisResult) -> None:
    """Put a new analysis on screen and start a fresh review for it."""
    st.session_state["analysis"] = result
    st.session_state["review"] = review.start_review(result)
    st.session_state["evidence_open"] = set()


def render_feedback(entry: dict, state: review.ReviewState) -> None:
    insight_id, title = entry["insight_id"], entry["pattern"]["artwork_title"]
    current = state.reviews[insight_id]
    st.markdown("**Was this insight useful?**")
    cols = st.columns([3, 2, 3])
    for col, (option, label) in zip(cols, review.FEEDBACK_OPTIONS.items()):
        chosen = current.feedback == option
        if col.button(("✓ " if chosen else "") + label, key=f"feedback-{option}-{insight_id}",
                      type="primary" if chosen else "secondary"):
            state.record_feedback(insight_id, option)
            st.rerun()
    if current.feedback:
        st.success(f"Feedback saved for the {title} insight: **{review.FEEDBACK_OPTIONS[current.feedback]}** "
                   f"(this session only). {review.NOT_AUTHORISATION_NOTE}")
        if not current.evidence_viewed:
            st.caption("To complete the review of this insight, also open its evidence.")
    elif not current.evidence_viewed:
        st.caption("Tip: view the evidence before rating. The review is complete once you have viewed the "
                   "evidence and given feedback on the same insight.")


def render_insight_card(rank: int, entry: dict, state: review.ReviewState) -> None:
    ins, pattern, insight_id = entry["insight"], entry["pattern"], entry["insight_id"]
    opened = st.session_state.setdefault("evidence_open", set())
    progress = state.reviews[insight_id]
    with st.container(border=True):
        st.markdown(f"#### {rank}. {ins['title']}")
        status = []
        if progress.evidence_viewed:
            status.append(":violet-badge[Evidence viewed]")
        if progress.feedback:
            status.append(f":violet-badge[Rated: {review.FEEDBACK_OPTIONS[progress.feedback]}]")
        st.markdown(" ".join([STRENGTH_BADGES[ins["confidence"]],
                              f":gray-badge[{explain.CATEGORY_LABELS[pattern['category']]}]"] + status))
        st.caption(f"{pattern['artwork_title']} ({pattern['artwork_id']}) · {pattern['artist_name']} · "
                   f"Insight ID `{insight_id}`")
        render_key_metrics(pattern)
        st.markdown(f"**Why this matters**  \n{explain.short_rationale(pattern)} {ins['why_it_may_matter']}")
        st.markdown(f"**Evidence strength: {ins['confidence']}.** {explain.STRENGTH_TEXT[ins['confidence']]}")
        st.markdown("**Limitations**  \n" + "\n".join(f"- {lim}" for lim in ins["limitations"]))
        if ins.get("suggested_next_step"):
            st.markdown(f"**For your consideration** (the agent takes no action)  \n{ins['suggested_next_step']}")
            if entry.get("next_step_substitution"):
                st.caption("ℹ️ The agent's own suggestion did not meet the neutral-action policy, so it was "
                           "replaced with this standard wording.")
        is_open = insight_id in opened
        if st.button("Hide evidence" if is_open else "View evidence", key=f"evidence-{insight_id}"):
            opened.symmetric_difference_update({insight_id})
            if not is_open:
                state.record_evidence_view(insight_id)
            st.rerun()
        if is_open:
            render_evidence(evidence.build_evidence(entry))
        render_feedback(entry, state)


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
for _, row in data.artwork_daily[data.artwork_daily["unique_artwork_viewers"].isna()].iterrows():
    st.caption(f"ℹ️ {row['artwork_title']} ({row['artwork_id']}) on {explain.fmt_date_long(row['fair_date'])}: "
               "daily unique viewers not recorded. Treated as unknown, never as zero.")

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

mode = config.mode()

if mode == "demo":
    # DEMO mode: replay a recorded live investigation. No API client is ever created.
    try:
        recording = snapshot.load_snapshot()
        demo_problem = None
    except snapshot.SnapshotError as e:
        recording, demo_problem = None, str(e)
    clicked = st.button("Analyze Daily Engagement", type="primary", disabled=recording is None)
    st.caption("🎬 Demo mode: shows a recorded live AI investigation. No new AI analysis is run and no "
               "AI requests are made." if recording else f"Demo mode: {demo_problem}")
    if clicked and recording:
        show_analysis(recording)
else:
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
        st.caption(f"🔴 Live mode · model `{model}` · up to {config.max_tool_calls()} tool calls, "
                   f"{config.max_output_tokens():,} output tokens per response, "
                   f"${config.max_cost_per_analysis_usd():.2f} per analysis · analysis {runs + 1} of {limit}")

if mode == "live" and clicked:
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
                                    max_output_tokens=config.max_output_tokens(),
                                    max_cost_usd=config.max_cost_per_analysis_usd(),
                                    on_step=lambda s: status.markdown(step_line(s)))
        status.update(label=f"Investigation {result.status.replace('_', ' ')}",
                      state="complete" if result.status == "completed" else "error", expanded=False)
    show_analysis(result)

result: agent.AnalysisResult | None = st.session_state.get("analysis")
if result:
    if result.replayed:
        recorded = dt.datetime.fromisoformat(result.recorded_at).strftime("%b %d, %Y %H:%M UTC")
        st.info(f"🎬 **Recorded AI investigation.** This is a replay of a live Claude investigation "
                f"(`{result.model}`) recorded on {recorded}, not a fresh analysis. The tool calls and results "
                "below are the real ones from that run; every insight was re-checked against the source data "
                "before display.")
    if result.error:
        st.error(f"Analysis {result.status.replace('_', ' ')}: {result.error} No unverified findings are shown.")
    elif result.status == "limit_reached":
        st.warning("The tool-call limit was reached; findings are based only on evidence gathered so far.")

    if not result.error:
        st.markdown(f"**Analysis overview.** {explain.overview(result.published, data.processed_dates, data.excluded_dates)}")
        st.caption("Insights are ordered by evidence strength: higher-confidence first, qualified signals last. "
                   + explain.STRENGTH_NOTE)
        if not result.published:
            st.info("No finding met the evidence bar. Nothing is presented rather than inventing an insight.")
        state = current_review()
        if result.published:
            p = state.progress()
            if p["complete"]:
                titles = ", ".join(e["pattern"]["artwork_title"] for e in result.published
                                   if e["insight_id"] in p["completed_ids"])
                st.success(f"✅ **Daily analysis review complete.** You viewed the evidence and recorded your "
                           f"feedback for: {titles}. Nothing has been sent or changed; any follow-up action is "
                           "your own decision, outside this prototype.")
            else:
                st.info(f"**Review progress:** evidence viewed for {p['evidence_viewed']} of {p['insights']} "
                        f"insights · feedback recorded for {p['rated']} of {p['insights']}. The review is complete "
                        "once you have viewed the evidence and given feedback on the same insight.")
            st.caption(f"Useful-insight rate this session: {p['useful']} of {p['insights']} validated insights "
                       f"rated useful. {review.SESSION_ONLY_NOTE}")
        for rank, entry in enumerate(result.published, start=1):
            render_insight_card(rank, entry, state)

        if result.not_surfaced:
            with st.expander(f"Not surfaced as insights ({len(result.not_surfaced)}): why"):
                for n in result.not_surfaced:
                    st.markdown(f"**{n['artwork_title']} ({n['artwork_id']})** · {n['label']}  \n"
                                f"{n['explanation']}  \n*{n['why_not_shown']}*")

    withheld = len(result.withheld) if not result.replayed else (result.withheld_count or 0)
    if withheld:
        with st.expander(f"Withheld by validation ({withheld}): never shown as findings"):
            if result.replayed:
                st.caption("Drafts that failed validation are not kept in recordings.")
            for w in result.withheld:
                st.markdown(f"**{w['insight_id']}**")
                for e in w["errors"]:
                    st.markdown(f"- {e}")

    with st.expander(f"Investigation trace ({result.tool_calls} tool calls, {result.model_turns} model turns)"):
        for s in result.trace:
            st.markdown(step_line(s))
            if s.result is not None:
                st.json(s.result, expanded=False)
    cost = result.estimated_cost_usd
    st.caption(("Original live run usage: " if result.replayed else "Usage: ")
               + f"{result.usage['input_tokens']:,} input + {result.usage['cache_read_input_tokens']:,} "
               f"cached + {result.usage['output_tokens']:,} output tokens"
               + (f" · estimated cost ${cost:.3f}" if cost is not None else ""))

    if mode == "live" and not result.replayed and result.status == "completed":
        if st.button("Save this run as the demo recording"):
            try:
                path = snapshot.save_snapshot(result, api_key=config.api_key())
                st.success(f"Saved to `{path.relative_to(path.parent.parent)}`. Commit it to publish the demo.")
            except snapshot.SnapshotError as e:
                st.error(str(e))
