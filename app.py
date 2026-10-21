"""Gallery Insights Agent — Streamlit entry point.

Milestone 1: data loading and validation. No analysis or LLM calls yet.
"""

import datetime as dt

import pandas as pd
import streamlit as st

from gia.data import DataValidationError, load_processed_data
from gia.display_names import edition_label, gallery_name


def format_date(iso: str) -> str:
    return dt.date.fromisoformat(iso).strftime("%b %d, %Y")

GALLERY_ID = "G001"
EDITION_IDS = ["E001"]

st.set_page_config(page_title="Gallery Insights Agent", page_icon="🖼️", layout="wide")

st.info(
    "**Demonstration prototype using synthetic data.** All galleries, artists, "
    "artworks and engagement figures are fictional."
)

st.title("Gallery Insights Agent")
st.subheader(gallery_name(GALLERY_ID))

edition_id = st.selectbox("Fair edition", EDITION_IDS, format_func=edition_label)

st.caption("🔒 Nothing is sent or changed by this agent. It does not contact anyone or modify business data.")

st.button("Analyze Daily Engagement", type="primary", disabled=True,
          help="Available from Milestone 3.")

st.divider()
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
