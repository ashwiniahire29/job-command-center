from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from statistics import median

from .db import connect
from .roles import is_relevant_title, metro_for


@dataclass(frozen=True)
class SponsorScore:
    employer_id: int
    sponsor_score: float | None
    sponsor_status: str
    h1b_filings_3y: int
    perm_filings_3y: int
    approval_rate: float | None
    relevant_role_filings: int
    median_target_metro_wage: float | None
    trend: str
    risk_note: str


def _approval_rate(approvals: int, denials: int) -> float | None:
    total = approvals + denials
    if total == 0:
        return None
    return approvals / total


def compute_score(
    employer_id: int,
    h1b_filings_3y: int,
    perm_filings_3y: int,
    approval_rate: float | None,
    relevant_role_filings: int,
    median_target_metro_wage: float | None,
    newest_year_count: int,
    oldest_year_count: int,
) -> SponsorScore:
    if h1b_filings_3y < 2 and perm_filings_3y == 0:
        likelihood = 35.0 if h1b_filings_3y else None
        note = "Sparse public filing history; verify sponsorship language before prioritizing."
        return SponsorScore(
            employer_id,
            likelihood,
            "Unverified",
            h1b_filings_3y,
            perm_filings_3y,
            approval_rate,
            relevant_role_filings,
            median_target_metro_wage,
            "insufficient_history",
            note,
        )

    perm_component = min(45.0, perm_filings_3y * 28.0)
    h1b_component = min(20.0, h1b_filings_3y * 3.0)
    approval_component = 0.0 if approval_rate is None else max(0.0, min(20.0, approval_rate * 20.0))
    relevant_component = min(10.0, relevant_role_filings * 2.0)
    wage_component = 5.0 if median_target_metro_wage and median_target_metro_wage >= 120_000 else 0.0
    score = round(min(100.0, perm_component + h1b_component + approval_component + relevant_component + wage_component), 1)

    if newest_year_count > oldest_year_count:
        trend = "increasing"
    elif newest_year_count < oldest_year_count:
        trend = "decreasing"
    else:
        trend = "stable"

    if perm_filings_3y > 0 and approval_rate and approval_rate >= 0.85:
        status = "Strong"
        note = "Recent PERM activity and strong USCIS approval history indicate a lower sponsorship risk."
    elif score >= 50:
        status = "Verified"
        note = "Meaningful H-1B activity, but validate role-specific transfer support in the posting."
    else:
        status = "Limited"
        note = "Some filing history exists, but sponsorship confidence is moderate."

    return SponsorScore(
        employer_id,
        score,
        status,
        h1b_filings_3y,
        perm_filings_3y,
        approval_rate,
        relevant_role_filings,
        median_target_metro_wage,
        trend,
        note,
    )


def refresh_sponsor_scores(db_path: Path) -> list[SponsorScore]:
    scores: list[SponsorScore] = []
    with connect(db_path) as conn:
        conn.execute("DELETE FROM sponsor_score_snapshots")
        years = [row["fiscal_year"] for row in conn.execute("SELECT DISTINCT fiscal_year FROM lca_filings ORDER BY fiscal_year DESC LIMIT 3")]
        if not years:
            years = [row["fiscal_year"] for row in conn.execute("SELECT DISTINCT fiscal_year FROM uscis_employer_stats ORDER BY fiscal_year DESC LIMIT 3")]
        newest_year = max(years) if years else None
        oldest_year = min(years) if years else None
        for employer in conn.execute("SELECT id FROM employers ORDER BY id"):
            employer_id = employer["id"]
            h1b_rows = conn.execute(
                "SELECT fiscal_year, job_title FROM lca_filings WHERE employer_id = ?",
                (employer_id,),
            ).fetchall()
            h1b_filings_3y = sum(1 for row in h1b_rows if not years or row["fiscal_year"] in years)
            relevant_role_filings = sum(1 for row in h1b_rows if (not years or row["fiscal_year"] in years) and is_relevant_title(row["job_title"]))
            perm_filings_3y = conn.execute(
                "SELECT COUNT(*) AS count FROM perm_filings WHERE employer_id = ? AND case_status LIKE '%CERT%'",
                (employer_id,),
            ).fetchone()["count"]
            stats = conn.execute(
                """
                SELECT SUM(initial_approvals + continuing_approvals) AS approvals,
                       SUM(initial_denials + continuing_denials) AS denials
                FROM uscis_employer_stats
                WHERE employer_id = ?
                """,
                (employer_id,),
            ).fetchone()
            approval_rate = _approval_rate(int(stats["approvals"] or 0), int(stats["denials"] or 0))
            target_metro_wages = [
                float(row["wage"])
                for row in conn.execute(
                    """
                    SELECT worksite_city, worksite_state, wage
                    FROM lca_filings
                    WHERE employer_id = ? AND wage IS NOT NULL
                    """,
                    (employer_id,),
                )
                if metro_for(row["worksite_city"], row["worksite_state"])
            ]
            median_wage = median(target_metro_wages) if target_metro_wages else None
            newest_count = sum(1 for row in h1b_rows if row["fiscal_year"] == newest_year)
            oldest_count = sum(1 for row in h1b_rows if row["fiscal_year"] == oldest_year)
            score = compute_score(
                employer_id,
                h1b_filings_3y,
                perm_filings_3y,
                approval_rate,
                relevant_role_filings,
                median_wage,
                newest_count,
                oldest_count,
            )
            conn.execute(
                """
                INSERT INTO sponsor_score_snapshots(
                    employer_id, sponsor_score, sponsor_status, h1b_filings_3y,
                    perm_filings_3y, approval_rate, relevant_role_filings,
                    median_target_metro_wage, trend, risk_note
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    score.employer_id,
                    score.sponsor_score,
                    score.sponsor_status,
                    score.h1b_filings_3y,
                    score.perm_filings_3y,
                    score.approval_rate,
                    score.relevant_role_filings,
                    score.median_target_metro_wage,
                    score.trend,
                    score.risk_note,
                ),
            )
            conn.execute(
                "UPDATE employers SET sponsor_status = ?, startup_sponsor_likelihood = ? WHERE id = ?",
                (
                    score.sponsor_status,
                    score.sponsor_score if score.sponsor_status == "Unverified" else None,
                    employer_id,
                ),
            )
            scores.append(score)
        conn.execute(
            "INSERT INTO ingest_logs(action, rows_processed, message) VALUES (?, ?, ?)",
            ("refresh_sponsor_scores", len(scores), "Recomputed sponsor score snapshots"),
        )
    return scores
