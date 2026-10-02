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
