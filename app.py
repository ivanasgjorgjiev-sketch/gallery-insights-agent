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

from gia import agent, config, diagnostics, evidence, explain, followup, guided, presentation, review, snapshot
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


SERIES_COLOR = "#2a78d6"   # single series: one hue; the key jump is emphasised by size and a label, not a new colour


def render_key_metrics(pattern: dict) -> None:
    """Four tiles in one row: the primary metric's key change, then each supporting measure with its verified
    values, change and support classification (values from the tools, not the model). Measures that did not add
    support are labelled as such, never as contradictions. Columns stack on narrow screens."""
    tiles = presentation.metric_tiles(pattern)
    if not tiles:
        return
    for col, t in zip(st.columns(len(tiles)), tiles):
        with col:
            st.metric(t["label"], t["value"], delta=t["delta"], delta_color=t["delta_color"], help=t["help"],
                      delta_arrow="auto" if t["delta"][:1] in "+-" else "off")
            st.caption(t["note"])


def render_trend_chart(pattern: dict) -> None:
    """Daily values of the primary metric on the processed days only, with the key jump emphasised."""
    import altair as alt

    points = presentation.trend_points(pattern)
    name = explain.METRIC_NAMES[pattern["metric"]]
    data = pd.DataFrame(points)
    base = alt.Chart(data).encode(
        x=alt.X("day:N", sort=None, title=None, axis=alt.Axis(labelAngle=0, ticks=False, domain=False)),
        y=alt.Y("value:Q", title=None, scale=alt.Scale(zero=True), axis=alt.Axis(tickCount=3, domain=False)))
    tooltip = [alt.Tooltip("day:N", title="Day"), alt.Tooltip("value:Q", title=name)]
    chart = (base.mark_line(strokeWidth=2, color=SERIES_COLOR)
             + base.mark_point(filled=True, size=64, color=SERIES_COLOR, opacity=1).encode(tooltip=tooltip)
             + base.transform_filter("datum.role == 'jump'").mark_point(
                 filled=True, size=160, color=SERIES_COLOR, opacity=1).encode(tooltip=tooltip)
             + base.transform_filter("datum.role != 'day' || datum.day == '" + points[-1]["day"] + "'")
             .mark_text(dy=-12, fontSize=12).encode(text="value:Q"))
    values = ", ".join(f"{p['day']}: {explain.fmt_value(p['value'])}" for p in points)
    st.altair_chart(chart.properties(height=115), width="stretch",
                    alt=f"{name} by processed day: {values}.")
    st.caption(f"Daily {name.lower()} · larger dot = the key change")


def render_evidence(entry: dict) -> None:
    """Two levels: a short, manager-friendly summary first, then calculations, checks and sources on demand."""
    ev = evidence.build_evidence(entry)
    summary = presentation.evidence_summary(entry, ev)
    with st.container(border=True):
        st.markdown("##### Evidence")
        st.markdown("\n".join(f"- {line}" for line in summary["lines"]))
        for note in summary["notes"]:
            st.caption(f"ℹ️ {note}")
        st.markdown(f"**Agent's description** (validated against the source)  \n{summary['agent_description']}")
        if summary["next_step"]:
            st.markdown(f"**For your consideration** (the agent takes no action)  \n{summary['next_step']}")
            if summary["next_step_replaced"]:
                st.caption("ℹ️ The agent's own suggestion did not meet the neutral-action policy, so it was "
                           "replaced with this standard wording.")
        with st.expander("Calculations, screening checks and source records"):
            st.dataframe([{"": k, "Value": v} for k, v in ev["context"].items()]
                         + [{"": "Insight ID", "Value": summary["insight_id"]}], hide_index=True)
            st.markdown("**Daily source records**")
            st.dataframe(ev["daily"], hide_index=True)
            if ev["comparison"]:
                old, new = ev["comparison_dates"]
                st.markdown(f"**Key comparison: {explain.fmt_date_long(old)} → {explain.fmt_date_long(new)}**")
                st.dataframe(ev["comparison"], hide_index=True)
            st.markdown(f"**Pattern found: {ev['pattern_label']}.** {ev['why_highlighted']}")
            st.markdown("**Screening checks** (transparent rules, applied the same way to every artwork)")
            st.dataframe(ev["checks"], hide_index=True)
            st.markdown("**Validation of this insight's numbers**")
            st.dataframe(ev["verified_claims"], hide_index=True)
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
    st.session_state["explore_open"] = set()
    st.session_state["followups"] = []          # follow-ups belong to the analysis on screen


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


def render_guided(entry: dict) -> None:
    """Four deterministic questions about this insight, shown only after "Explore insight" and collapsed at
    first. Opening them makes no AI request and does not change the review."""
    with st.container(border=True):
        st.markdown("##### Explore this insight")
        for a in guided.answers(entry):
            with st.expander(a.question, expanded=False):
                if a.shown:
                    st.markdown(a.text)
                else:
                    st.warning(guided.UNAVAILABLE)
        st.caption("These explanations are generated from this insight's verified data. No AI request is made.")


def toggle(name: str, insight_id: str) -> None:
    st.session_state.setdefault(name, set()).symmetric_difference_update({insight_id})


def render_insight_card(rank: int, entry: dict, state: review.ReviewState) -> None:
    ins, pattern, insight_id = entry["insight"], entry["pattern"], entry["insight_id"]
    evidence_open = insight_id in st.session_state.setdefault("evidence_open", set())
    explore_open = insight_id in st.session_state.setdefault("explore_open", set())
    progress = state.reviews[insight_id]
    with st.container(border=True):
        st.markdown(f"#### {rank}. {ins['title']}")
        status = []
        if progress.evidence_viewed and progress.feedback:
            status.append(":green-badge[✓ Reviewed]")
        else:
            if progress.evidence_viewed:
                status.append(":violet-badge[Evidence viewed]")
            if progress.feedback:
                status.append(f":violet-badge[Rated: {review.FEEDBACK_OPTIONS[progress.feedback]}]")
        st.markdown(" ".join([STRENGTH_BADGES[ins["confidence"]],
                              f":gray-badge[{explain.CATEGORY_LABELS[pattern['category']]}]"] + status))
        st.caption(f"{pattern['artwork_title']} ({pattern['artwork_id']}) · {pattern['artist_name']}")
        render_key_metrics(pattern)
        render_trend_chart(pattern)
        st.markdown(f"**Why it may matter:** {ins['why_it_may_matter']}")
        with st.expander(f"Limitations ({len(ins['limitations'])})"):
            st.markdown("\n".join(f"- {lim}" for lim in ins["limitations"]))
        explore_col, evidence_col, _ = st.columns([1, 1, 2])
        if explore_col.button("Hide exploration" if explore_open else "Explore insight", key=f"explore-{insight_id}",
                              icon=":material/travel_explore:", width="stretch"):
            toggle("explore_open", insight_id)
            st.rerun()
        if evidence_col.button("Hide evidence" if evidence_open else "View evidence", key=f"evidence-{insight_id}",
                               icon=":material/fact_check:", width="stretch"):
            toggle("evidence_open", insight_id)
            if not evidence_open:
                state.record_evidence_view(insight_id)
            st.rerun()
        if explore_open:
            render_guided(entry)
        if evidence_open:
            render_evidence(entry)
        render_feedback(entry, state)


ANSWER_BADGES = {"answer": ":green-badge[Answer]", "clarification": ":blue-badge[Clarifying question]",
                 "refusal": ":orange-badge[Declined: outside the agent's data or authority]"}


def render_followup(f: followup.FollowUpResult, titles: dict) -> None:
    with st.container(border=True):
        about = f" · about: {titles[f.insight_id]}" if f.insight_id in titles else ""
        st.markdown(f"**You asked:** {f.question}{about}")
        if f.recorded_at:
            st.caption("🎬 Recorded answer from the live session, re-checked against the source data. "
                       "It was not generated now.")
        if f.shown:
            st.markdown(ANSWER_BADGES.get(f.answer_type, ""))
            st.markdown(f.answer)
            if f.limitations:
                st.caption("Limitations: " + " ".join(f.limitations))
        elif f.status == "withheld":
            st.warning("The agent's answer could not be verified against the tool results, so it is not shown.")
        else:
            st.error(f"No answer: {f.error}")
        with st.expander(f"How this was answered ({len(f.tool_calls)} tool call(s))"):
            for s in f.trace:
                st.markdown(step_line(s))
            if f.grounding_errors:
                st.markdown("**Grounding problems:**")
                for e in f.grounding_errors:
                    st.markdown(f"- {e}")
            if f.estimated_cost_usd is not None:
                st.caption(f"Estimated cost of this question: ${f.estimated_cost_usd:.3f}")


def render_followup_area(result: agent.AnalysisResult, mode: str) -> None:
    st.markdown("#### Follow-up questions")
    titles = {p["insight_id"]: p["insight"]["title"] for p in result.published}
    if result.replayed or mode != "live":
        st.caption("🎬 Demo mode: free-form questions are available only in the live version. These are recorded "
                   "examples from the live session; each answer was re-checked against the source data, and "
                   "nothing is generated now.")
        if not result.followup_examples:
            st.info("This recording includes no example questions.")
        for f in result.followup_examples:
            render_followup(f, titles)
        return

    st.caption("Ask about this gallery's processed engagement data: artworks, artists, metrics and comparisons. "
               "Every number comes from the analytical tools. The agent cannot see collector, sales or pricing "
               "information and takes no actions. Questions do not affect your review or feedback.")
    history: list = st.session_state.setdefault("followups", [])
    for f in history:
        render_followup(f, titles)
    asked = st.session_state.get("followups_asked", 0)
    limit = config.max_followups_per_session()
    key = config.api_key()
    if not key:
        st.caption("Follow-up questions need the Anthropic API key, which is not configured.")
        return
    if asked >= limit:
        st.caption(f"This session has reached its limit of {limit} follow-up questions (cost protection).")
        return
    with st.form("followup-form", clear_on_submit=True):
        about = st.selectbox("About (optional)", [None] + list(titles),
                             format_func=lambda i: "The data in general" if i is None else titles[i])
        question = st.text_area("Your question", max_chars=config.MAX_QUESTION_CHARS,
                                placeholder="e.g. Was Artwork A1's increase sustained, or driven by one day?")
        submitted = st.form_submit_button("Ask")
    st.caption(f"Question {asked + 1} of {limit} this session · up to {config.followup_max_tool_calls()} tool calls, "
               f"{config.followup_max_output_tokens():,} output tokens and ${config.followup_max_cost_usd():.2f} "
               "per question.")
    if submitted and question.strip():
        st.session_state["followups_asked"] = asked + 1
        client = anthropic.Anthropic(api_key=key, max_retries=2, timeout=120)
        with st.status("The agent is investigating your question…", expanded=True) as status:
            f = followup.run_followup(client, config.model(), question, result.published, about, history,
                                      effort=config.effort(), max_tool_calls=config.followup_max_tool_calls(),
                                      max_output_tokens=config.followup_max_output_tokens(),
                                      max_cost_usd=config.followup_max_cost_usd(),
                                      max_question_chars=config.MAX_QUESTION_CHARS,
                                      on_step=lambda s: status.markdown(step_line(s)))
            status.update(label="Answered" if f.shown else "No verified answer",
                          state="complete" if f.shown else "error", expanded=False)
        # Local, git-ignored record of a withheld answer for offline investigation; never shown in the app.
        diagnostics.record_withheld(f, mode, followup.build_context(result.published, about, history),
                                    api_key=key, effort=config.effort(), directory=config.diagnostics_dir())
        history.append(f)
        st.rerun()


st.set_page_config(page_title="Gallery Insights Agent", page_icon="🖼️", layout="wide")

st.info(
    "**Demonstration prototype using synthetic data.** All galleries, artists, "
    "artworks and engagement figures are fictional."
)

title_col, edition_col = st.columns([3, 2], vertical_alignment="bottom")
with title_col:
    st.markdown(f"## Gallery Insights Agent\n**{gallery_name(GALLERY_ID)}**")
with edition_col:
    edition_id = st.selectbox("Fair edition", EDITION_IDS, format_func=edition_label)
st.caption("🔒 Nothing is sent or changed by this agent. It does not contact anyone or modify business data.")

# --- Data status --------------------------------------------------------------------

try:
    data = load_processed_data(gallery_id=GALLERY_ID, edition_id=edition_id)
except DataValidationError as err:
    st.error("The engagement data failed validation, so analysis is unavailable.")
    for issue in err.issues:
        st.markdown(f"- {issue}")
    st.stop()

missing = data.artwork_daily[data.artwork_daily["unique_artwork_viewers"].isna()]
status = [f"✅ Data checks passed · **{len(data.processed_dates)} processed fair days** "
          f"({explain.fmt_date(data.processed_dates[0])}–{explain.fmt_date(data.processed_dates[-1])})"]
if data.excluded_dates:
    status.append(f"{', '.join(explain.fmt_date(d) for d in data.excluded_dates)} excluded (not processed yet)")
if len(missing):
    status.append(f"{len(missing)} value{'s' if len(missing) > 1 else ''} not recorded")
st.markdown(" · ".join(status))

with st.expander("Data details and eligible source records"):
    st.markdown(f"**Processed fair days used:** {', '.join(format_date(d) for d in data.processed_dates)}.")
    if data.excluded_dates:
        excluded = ", ".join(format_date(d) for d in data.excluded_dates)
        st.markdown(f"**Excluded from all analysis (not yet processed):** {excluded}.")
    for _, row in missing.iterrows():
        st.caption(f"ℹ️ {row['artwork_title']} ({row['artwork_id']}) on {explain.fmt_date_long(row['fair_date'])}: "
                   "daily unique viewers not recorded. Treated as unknown, never as zero.")
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
        st.markdown(f"**Analysis overview.** {explain.overview(result.published, data.processed_dates, data.excluded_dates)}",
                    help="Insights are ordered by evidence strength: higher-confidence first, qualified signals last. "
                         + explain.STRENGTH_NOTE)
        if not result.published:
            st.info("No finding met the evidence bar. Nothing is presented rather than inventing an insight.")
        state = current_review()
        if result.published:
            p = state.progress()
            useful = (f"Rated useful so far: {p['useful']} of {p['insights']} (this session only).")
            if p["complete"]:
                titles = ", ".join(e["pattern"]["artwork_title"] for e in result.published
                                   if e["insight_id"] in p["completed_ids"])
                st.success(f"✅ **Daily analysis review complete.** You viewed the evidence and recorded your "
                           f"feedback for: {titles}. Nothing has been sent or changed; any follow-up action is "
                           f"your own decision, outside this prototype. {useful}")
            else:
                # The evidence-before-feedback guidance is given once here, not under every card.
                st.info(f"**Review progress:** evidence viewed for {p['evidence_viewed']} of {p['insights']} "
                        f"insights · feedback recorded for {p['rated']} of {p['insights']}. To complete the review, "
                        f"open **View evidence** and then rate the same insight (any one is enough). {useful}")
        for rank, entry in enumerate(result.published, start=1):
            render_insight_card(rank, entry, state)

    if not result.error and config.followups_enabled():   # not part of the M8 MVP; kept behind a setting
        render_followup_area(result, mode)

    # Agent-process details, grouped and collapsed: the evidence of agentic work without crowding the cards.
    withheld = len(result.withheld) if not result.replayed else (result.withheld_count or 0)
    with st.expander(f"How the agent worked · {presentation.run_summary(result)}"):
        names = ["Investigation trace", f"Not surfaced ({len(result.not_surfaced)})",
                 f"Withheld by validation ({withheld})", "Usage"]
        trace_tab, hidden_tab, withheld_tab, usage_tab = st.tabs(names)
        with trace_tab:
            st.caption(f"{result.tool_calls} tool calls, {result.model_turns} model turns. Claude chose the tools; "
                       "Python ran them.")
            for s in result.trace:
                st.markdown(step_line(s))
                if s.result is not None:
                    st.json(s.result, expanded=False)
        with hidden_tab:
            if not result.not_surfaced:
                st.caption("Every artwork with a reportable pattern was surfaced.")
            for n in result.not_surfaced:
                st.markdown(f"**{n['artwork_title']} ({n['artwork_id']})** · {n['label']}  \n"
                            f"{n['explanation']}  \n*{n['why_not_shown']}*")
        with withheld_tab:
            st.caption("Drafts that fail validation are never shown as findings."
                       + (" They are not kept in recordings." if result.replayed else ""))
            for w in result.withheld:
                st.markdown(f"**{w['insight_id']}**")
                for e in w["errors"]:
                    st.markdown(f"- {e}")
        with usage_tab:
            cost = result.estimated_cost_usd
            st.caption(("Original live run usage: " if result.replayed else "Usage: ")
                       + f"{result.usage['input_tokens']:,} input + {result.usage['cache_read_input_tokens']:,} "
                       f"cached + {result.usage['output_tokens']:,} output tokens"
                       + (f" · estimated cost ${cost:.3f}" if cost is not None else ""))

    if mode == "live" and not result.replayed and result.status == "completed":
        if st.button("Save this run as the demo recording"):
            try:
                path = snapshot.save_snapshot(result, api_key=config.api_key(),
                                              followups=st.session_state.get("followups", []))
                st.success(f"Saved to `{path.relative_to(path.parent.parent)}`. Commit it to publish the demo.")
            except snapshot.SnapshotError as e:
                st.error(str(e))
