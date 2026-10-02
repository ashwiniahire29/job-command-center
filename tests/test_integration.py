from pathlib import Path

from job_command_center.dashboard_data import ranked_employers
from job_command_center.db import init_db
from job_command_center.importers import ingest_lca, ingest_perm, ingest_uscis, refresh_wage_summaries
from job_command_center.scoring import refresh_sponsor_scores


FIXTURES = Path(__file__).parent / "fixtures"


def test_sample_ingest_and_dashboard_query(tmp_path: Path) -> None:
    db_path = tmp_path / "jcc.sqlite3"
    init_db(db_path)
    assert ingest_lca(db_path, FIXTURES / "sample_lca.csv", 2026, partial_year=True) == 7
    assert ingest_perm(db_path, FIXTURES / "sample_perm.csv", 2026, partial_year=True) == 4
    assert ingest_uscis(db_path, FIXTURES / "sample_uscis.csv", 2026, partial_year=True) == 6
    assert refresh_wage_summaries(db_path) > 0
    scores = refresh_sponsor_scores(db_path)
    rows = ranked_employers(db_path, limit=10)
    assert len(scores) >= 5
    assert rows
    assert rows[0]["sponsor_score"] <= 100
    assert any(row["sponsor_status"] == "Unverified" for row in rows)
