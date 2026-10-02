from pathlib import Path

from job_command_center.db import init_db
from job_command_center.importers import ingest_lca, ingest_perm, ingest_uscis, refresh_wage_summaries
from job_command_center.jobs import classify_email, import_jobs_csv, score_jobs
from job_command_center.scoring import refresh_sponsor_scores


FIXTURES = Path(__file__).parent / "fixtures"


def test_job_import_scoring_and_exclusions(tmp_path: Path) -> None:
    db_path = tmp_path / "jcc.sqlite3"
    init_db(db_path)
    ingest_lca(db_path, FIXTURES / "sample_lca.csv", 2026, partial_year=True)
    ingest_perm(db_path, FIXTURES / "sample_perm.csv", 2026, partial_year=True)
    ingest_uscis(db_path, FIXTURES / "sample_uscis.csv", 2026, partial_year=True)
    refresh_wage_summaries(db_path)
    refresh_sponsor_scores(db_path)
    assert import_jobs_csv(db_path, FIXTURES / "sample_jobs.csv") == 4
    assert score_jobs(db_path) == 4


def test_email_classification() -> None:
    assert classify_email("Schedule interview", "Meet with the hiring manager")[0] == "Interviewing"
    assert classify_email("Application update", "Unfortunately we are not moving forward")[0] == "Rejected"
