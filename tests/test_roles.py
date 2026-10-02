from job_command_center.roles import is_relevant_title, title_families_for


def test_target_role_filters_cover_requested_tracks() -> None:
    titles = [
        "Strategy and Operations Lead",
        "Revenue Operations Manager",
        "GTM Strategy Manager",
        "Customer Success Operations Analyst",
        "AI Operations Program Manager",
        "Senior Business Analyst",
        "Senior Consultant, Transformation",
    ]
    assert all(is_relevant_title(title) for title in titles)
    assert "ai_ops" in title_families_for("LLM AI Operations Lead")
