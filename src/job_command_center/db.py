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
