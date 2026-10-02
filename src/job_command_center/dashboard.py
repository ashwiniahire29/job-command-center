from __future__ import annotations

import pandas as pd
import streamlit as st

from job_command_center.config import get_settings
from job_command_center.dashboard_data import employer_trend, ingest_history, ranked_employers


settings = get_settings()

st.set_page_config(page_title="Job Command Center", layout="wide")
st.title("Sponsor Intelligence")

st.caption("Phase 1: local H-1B, PERM, and USCIS sponsor evidence. No external AI calls.")

search = st.text_input("Employer search", placeholder="Google, OpenAI, Salesforce...")
limit = st.slider("Rows", min_value=10, max_value=100, value=25, step=5)

rows = ranked_employers(settings.db_path, search=search, limit=limit)
if not rows:
    st.info("No sponsor records found yet. Run `python -m job_command_center.cli ingest-sample` or import disclosure files.")
    st.stop()

df = pd.DataFrame(rows)
st.dataframe(
    df[
        [
            "display_name",
            "sponsor_status",
            "sponsor_score",
            "h1b_filings_3y",
            "perm_filings_3y",
            "approval_rate",
            "relevant_role_filings",
            "median_target_metro_wage",
            "trend",
            "risk_note",
        ]
    ],
    hide_index=True,
    use_container_width=True,
)

selected = st.selectbox("Trend detail", [row["normalized_name"] for row in rows], format_func=lambda value: next(row["display_name"] for row in rows if row["normalized_name"] == value))
trend = employer_trend(settings.db_path, selected)
if trend:
    st.subheader("H-1B / PERM Trend")
    st.bar_chart(pd.DataFrame(trend).set_index("fiscal_year"))

with st.expander("Recent automated actions"):
    history = ingest_history(settings.db_path)
    st.dataframe(pd.DataFrame(history), hide_index=True, use_container_width=True)
