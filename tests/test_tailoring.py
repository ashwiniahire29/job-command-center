from job_command_center.tailoring import validate_tailored_output


MASTER = """
Strategy & Business Operations Program Manager
SQL, Python, Power BI, Tableau, Snowflake, Salesforce, ServiceNow, Qualtrics, NLP/LLM tooling
90% manual review reduction; 73% renewal cycle time reduction; CSAT +15% in 6 months
"""


def test_tailoring_allows_master_claims() -> None:
    ok, notes = validate_tailored_output(MASTER, "Strategy & Business Operations Program Manager with SQL and 90% manual review reduction")
    assert ok, notes


def test_tailoring_rejects_new_metrics_or_tools() -> None:
    ok, notes = validate_tailored_output(MASTER, "Strategy & Business Operations Program Manager with Kubernetes and 99% cost reduction")
    assert not ok
    assert any("Kubernetes" in note for note in notes)
    assert any("99%" in note for note in notes)
