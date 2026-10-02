from job_command_center.scoring import compute_score


def test_score_bounds_and_perm_weighting() -> None:
    h1b_heavy = compute_score(1, h1b_filings_3y=10, perm_filings_3y=0, approval_rate=0.95, relevant_role_filings=4, median_target_metro_wage=150000, newest_year_count=5, oldest_year_count=2)
    perm_active = compute_score(2, h1b_filings_3y=4, perm_filings_3y=3, approval_rate=0.95, relevant_role_filings=4, median_target_metro_wage=150000, newest_year_count=3, oldest_year_count=2)
    assert 0 <= (h1b_heavy.sponsor_score or 0) <= 100
    assert 0 <= (perm_active.sponsor_score or 0) <= 100
    assert (perm_active.sponsor_score or 0) > (h1b_heavy.sponsor_score or 0)


def test_sparse_startup_is_unverified() -> None:
    score = compute_score(1, h1b_filings_3y=1, perm_filings_3y=0, approval_rate=1.0, relevant_role_filings=1, median_target_metro_wage=125000, newest_year_count=1, oldest_year_count=0)
    assert score.sponsor_status == "Unverified"
