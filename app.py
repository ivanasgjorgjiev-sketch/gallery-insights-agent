"""Gallery Insights Agent — Streamlit entry point.

Milestone 0: application shell only. No data analysis or LLM calls yet.
"""

import streamlit as st

from gia.display_names import edition_label, gallery_name

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
st.write("✅ Milestone 0: the app shell is running.")
