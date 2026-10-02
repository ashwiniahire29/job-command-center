from job_command_center.normalization import normalize_employer_name


def test_google_aliases_merge() -> None:
    assert normalize_employer_name("Google LLC") == "google"
    assert normalize_employer_name("Google Inc.") == "google"
