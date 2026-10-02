from __future__ import annotations

from pathlib import Path

from .db import connect


def ranked_employers(db_path: Path, search: str = "", limit: int = 50) -> list[dict]:
    query = """
        SELECT e.display_name,
               e.normalized_name,
               s.sponsor_status,
               s.sponsor_score,
               s.h1b_filings_3y,
               s.perm_filings_3y,
               s.approval_rate,
               s.relevant_role_filings,
               s.median_target_metro_wage,
               s.trend,
               s.risk_note,
               s.computed_at
        FROM sponsor_score_snapshots s
        JOIN employers e ON e.id = s.employer_id
        WHERE e.normalized_name LIKE ? OR e.display_name LIKE ?
        ORDER BY COALESCE(s.sponsor_score, -1) DESC, s.h1b_filings_3y DESC
        LIMIT ?
    """
    like = f"%{search}%"
    with connect(db_path) as conn:
        return [dict(row) for row in conn.execute(query, (like, like, limit))]


def employer_trend(db_path: Path, normalized_name: str) -> list[dict]:
    query = """
        SELECT fiscal_year,
               SUM(h1b_count) AS h1b_filings,
               SUM(perm_count) AS perm_filings
        FROM (
            SELECT e.normalized_name, l.fiscal_year, COUNT(*) AS h1b_count, 0 AS perm_count
            FROM lca_filings l
            JOIN employers e ON e.id = l.employer_id
            GROUP BY e.normalized_name, l.fiscal_year
            UNION ALL
            SELECT e.normalized_name, p.fiscal_year, 0 AS h1b_count, COUNT(*) AS perm_count
            FROM perm_filings p
            JOIN employers e ON e.id = p.employer_id
            GROUP BY e.normalized_name, p.fiscal_year
        )
        WHERE normalized_name = ?
        GROUP BY fiscal_year
        ORDER BY fiscal_year
    """
    with connect(db_path) as conn:
        return [dict(row) for row in conn.execute(query, (normalized_name,))]


def ingest_history(db_path: Path, limit: int = 20) -> list[dict]:
    with connect(db_path) as conn:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT action, source_type, rows_processed, message, created_at FROM ingest_logs ORDER BY id DESC LIMIT ?",
                (limit,),
            )
        ]


def ranked_jobs(db_path: Path, limit: int = 50) -> list[dict]:
    with connect(db_path) as conn:
        return [
            dict(row)
            for row in conn.execute(
                """
                SELECT j.id,
                       j.company_name,
                       j.title,
                       j.location,
                       j.remote_status,
                       j.sponsorship_flag,
                       j.excluded,
                       j.exclusion_reason,
                       a.stage,
                       s.track,
                       s.match_score,
                       s.final_priority,
                       s.skills_overlap,
                       s.hard_gaps,
                       s.location_fit,
                       s.salary_fit,
                       s.risk_note
                FROM jobs j
                LEFT JOIN job_match_scores s ON s.job_id = j.id
                LEFT JOIN applications a ON a.job_id = j.id
                ORDER BY COALESCE(s.final_priority, -1) DESC, j.created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
        ]


def pipeline_summary(db_path: Path) -> list[dict]:
    with connect(db_path) as conn:
        return [
            dict(row)
            for row in conn.execute(
                """
                SELECT stage, COUNT(*) AS count
                FROM applications
                GROUP BY stage
                ORDER BY CASE stage
                    WHEN 'Discovered' THEN 1
                    WHEN 'Shortlisted' THEN 2
                    WHEN 'Tailored' THEN 3
                    WHEN 'Applied' THEN 4
                    WHEN 'In Review' THEN 5
                    WHEN 'Assessment' THEN 6
                    WHEN 'Recruiter Screen' THEN 7
                    WHEN 'Interviewing' THEN 8
                    WHEN 'Offer' THEN 9
                    WHEN 'Rejected' THEN 10
                    WHEN 'Ghosted' THEN 11
                    ELSE 99
                END
                """
            )
        ]


def generated_assets(db_path: Path, limit: int = 20) -> list[dict]:
    with connect(db_path) as conn:
        return [
            dict(row)
            for row in conn.execute(
                """
                SELECT j.company_name, j.title, d.document_type, d.validation_status, d.validation_notes, d.created_at
                FROM tailored_documents d
                JOIN jobs j ON j.id = d.job_id
                ORDER BY d.id DESC
                LIMIT ?
                """,
                (limit,),
            )
        ]
