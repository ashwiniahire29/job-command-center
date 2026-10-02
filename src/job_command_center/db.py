from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS raw_import_files (
    id INTEGER PRIMARY KEY,
    source_type TEXT NOT NULL,
    fiscal_year INTEGER NOT NULL,
    path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    partial_year INTEGER NOT NULL DEFAULT 0,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_type, fiscal_year, path)
);

CREATE TABLE IF NOT EXISTS employers (
    id INTEGER PRIMARY KEY,
    normalized_name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    sponsor_status TEXT NOT NULL DEFAULT 'Unknown',
    startup_sponsor_likelihood REAL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS employer_aliases (
    id INTEGER PRIMARY KEY,
    employer_id INTEGER NOT NULL REFERENCES employers(id) ON DELETE CASCADE,
    alias TEXT NOT NULL UNIQUE,
    normalized_alias TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'system'
);

CREATE TABLE IF NOT EXISTS lca_filings (
    id INTEGER PRIMARY KEY,
    employer_id INTEGER NOT NULL REFERENCES employers(id) ON DELETE CASCADE,
    fiscal_year INTEGER NOT NULL,
    case_status TEXT NOT NULL,
    job_title TEXT NOT NULL,
    soc_code TEXT,
    worksite_city TEXT,
    worksite_state TEXT,
    wage REAL,
    wage_unit TEXT,
    source_file_id INTEGER REFERENCES raw_import_files(id)
);

CREATE TABLE IF NOT EXISTS perm_filings (
    id INTEGER PRIMARY KEY,
    employer_id INTEGER NOT NULL REFERENCES employers(id) ON DELETE CASCADE,
    fiscal_year INTEGER NOT NULL,
    case_status TEXT NOT NULL,
    job_title TEXT NOT NULL,
    worksite_city TEXT,
    worksite_state TEXT,
    wage REAL,
    source_file_id INTEGER REFERENCES raw_import_files(id)
);

CREATE TABLE IF NOT EXISTS uscis_employer_stats (
    id INTEGER PRIMARY KEY,
    employer_id INTEGER NOT NULL REFERENCES employers(id) ON DELETE CASCADE,
    fiscal_year INTEGER NOT NULL,
    initial_approvals INTEGER NOT NULL DEFAULT 0,
    initial_denials INTEGER NOT NULL DEFAULT 0,
    continuing_approvals INTEGER NOT NULL DEFAULT 0,
    continuing_denials INTEGER NOT NULL DEFAULT 0,
    source_file_id INTEGER REFERENCES raw_import_files(id),
    UNIQUE(employer_id, fiscal_year)
);

CREATE TABLE IF NOT EXISTS metro_wage_summaries (
    id INTEGER PRIMARY KEY,
    employer_id INTEGER NOT NULL REFERENCES employers(id) ON DELETE CASCADE,
    metro TEXT NOT NULL,
    title_family TEXT NOT NULL,
    median_wage REAL NOT NULL,
    filing_count INTEGER NOT NULL,
    UNIQUE(employer_id, metro, title_family)
);

CREATE TABLE IF NOT EXISTS sponsor_score_snapshots (
    id INTEGER PRIMARY KEY,
    employer_id INTEGER NOT NULL REFERENCES employers(id) ON DELETE CASCADE,
    sponsor_score REAL,
    sponsor_status TEXT NOT NULL,
    h1b_filings_3y INTEGER NOT NULL,
    perm_filings_3y INTEGER NOT NULL,
    approval_rate REAL,
    relevant_role_filings INTEGER NOT NULL,
    median_target_metro_wage REAL,
    trend TEXT NOT NULL,
    risk_note TEXT NOT NULL,
    computed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ingest_logs (
    id INTEGER PRIMARY KEY,
    action TEXT NOT NULL,
    source_type TEXT,
    rows_processed INTEGER NOT NULL DEFAULT 0,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY,
    employer_id INTEGER REFERENCES employers(id) ON DELETE SET NULL,
    company_name TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    ats_type TEXT,
    posted_date TEXT,
    location TEXT,
    remote_status TEXT,
    salary_min REAL,
    salary_max REAL,
    company_stage TEXT,
    company_type TEXT,
    jd_text TEXT NOT NULL,
    sponsorship_flag TEXT NOT NULL DEFAULT 'Unknown',
    excluded INTEGER NOT NULL DEFAULT 0,
    exclusion_reason TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS job_match_scores (
    id INTEGER PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    track TEXT NOT NULL,
    match_score REAL NOT NULL,
    final_priority REAL NOT NULL,
    skills_overlap TEXT NOT NULL,
    hard_gaps TEXT NOT NULL,
    location_fit TEXT NOT NULL,
    salary_fit TEXT NOT NULL,
    risk_note TEXT NOT NULL,
    computed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(job_id)
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    stage TEXT NOT NULL DEFAULT 'Discovered',
    referral_status TEXT NOT NULL DEFAULT 'Cold',
    applied_at TEXT,
    last_response_at TEXT,
    follow_up_due_at TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(job_id)
);

CREATE TABLE IF NOT EXISTS tailored_documents (
    id INTEGER PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    document_type TEXT NOT NULL,
    path TEXT,
    content TEXT NOT NULL,
    validation_status TEXT NOT NULL,
    validation_notes TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS outreach_drafts (
    id INTEGER PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    channel TEXT NOT NULL,
    audience TEXT NOT NULL,
    draft_text TEXT NOT NULL,
    follow_up_days INTEGER NOT NULL DEFAULT 7,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS email_events (
    id INTEGER PRIMARY KEY,
    application_id INTEGER REFERENCES applications(id) ON DELETE SET NULL,
    sender TEXT NOT NULL,
    subject TEXT NOT NULL,
    snippet TEXT NOT NULL,
    classified_stage TEXT NOT NULL,
    confidence REAL NOT NULL,
    recruiter_name TEXT,
    interview_datetime TEXT,
    received_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS interview_prep_packs (
    id INTEGER PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS action_logs (
    id INTEGER PRIMARY KEY,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
