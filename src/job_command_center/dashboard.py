from __future__ import annotations

import pandas as pd
import streamlit as st

from job_command_center.config import get_settings
from job_command_center.dashboard_data import generated_assets, employer_trend, ingest_history, pipeline_summary, ranked_employers, ranked_jobs
from job_command_center.jobs import create_outreach_drafts, generate_application_assets, generate_interview_prep


settings = get_settings()

st.set_page_config(page_title="Job Command Center", layout="wide")
st.title("Job Command Center")

st.caption("Local-first sponsor intelligence, job scoring, application queue, outreach, and prep. No external AI calls in this MVP.")

sponsor_tab, jobs_tab, pipeline_tab, assets_tab, logs_tab = st.tabs(["Sponsors", "Jobs", "Pipeline", "Assets", "Logs"])

with sponsor_tab:
    search = st.text_input("Employer search", placeholder="Google, OpenAI, Salesforce...")
    limit = st.slider("Sponsor rows", min_value=10, max_value=100, value=25, step=5)
    rows = ranked_employers(settings.db_path, search=search, limit=limit)
    if not rows:
        st.info("No sponsor records found yet. Run `python -m job_command_center.cli ingest-sample` or import disclosure files.")
    else:
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

with jobs_tab:
    jobs = ranked_jobs(settings.db_path)
    if not jobs:
        st.info("No jobs loaded yet. Run `python -m job_command_center.cli ingest-jobs-sample` or import a CSV.")
    else:
        jobs_df = pd.DataFrame(jobs)
        st.dataframe(
            jobs_df[
                [
                    "id",
                    "company_name",
                    "title",
                    "stage",
                    "track",
                    "match_score",
                    "final_priority",
                    "sponsorship_flag",
                    "location_fit",
                    "salary_fit",
                    "risk_note",
                ]
            ],
            hide_index=True,
            use_container_width=True,
        )
        job_id = st.number_input("Job ID for local actions", min_value=1, step=1)
        col1, col2 = st.columns(2)
        if col1.button("Generate Assets"):
            generate_application_assets(settings.db_path, int(job_id))
            create_outreach_drafts(settings.db_path, int(job_id))
            st.success(f"Generated local assets for job {job_id}.")
        if col2.button("Generate Prep Pack"):
            prep = generate_interview_prep(settings.db_path, int(job_id))
            st.text_area("Prep pack", prep, height=320)

with pipeline_tab:
    summary = pipeline_summary(settings.db_path)
    if summary:
        summary_df = pd.DataFrame(summary)
        st.bar_chart(summary_df.set_index("stage"))
        st.dataframe(summary_df, hide_index=True, use_container_width=True)
    else:
        st.info("No application records yet.")

with assets_tab:
    assets = generated_assets(settings.db_path)
    if assets:
        st.dataframe(pd.DataFrame(assets), hide_index=True, use_container_width=True)
    else:
        st.info("No generated assets yet.")

with logs_tab:
    history = ingest_history(settings.db_path)
    if history:
        st.dataframe(pd.DataFrame(history), hide_index=True, use_container_width=True)
    else:
        st.info("No ingest logs yet.")
