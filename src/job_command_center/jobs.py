from __future__ import annotations

import csv
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from .db import connect
from .normalization import display_name_from_normalized, normalize_employer_name
from .roles import title_families_for


TRACK_LABELS = {
    "strategy_ops": "Strategy & Operations / BizOps",
    "program_management": "Senior Program Manager",
    "business_analytics": "Business/Data Analyst",
    "revenue_ops": "Revenue Operations",
    "gtm": "GTM Strategy",
    "cs_ops": "CS Strategy & Ops",
    "ai_ops": "AI Strategy / AI Operations",
    "consulting": "Senior Consultant",
}

TARGET_TOOLS = {"sql", "python", "power bi", "tableau", "snowflake", "salesforce", "servicenow", "qualtrics", "llm", "nlp"}
EXCLUSION_PATTERNS = [
    r"no sponsorship",
    r"without sponsorship",
    r"must be a us citizen",
    r"u\.s\. citizens only",
    r"security clearance required",
    r"active clearance",
]
SPONSOR_POSITIVE_PATTERNS = [r"h-?1b", r"visa sponsorship", r"transfer sponsorship", r"immigration support"]


def _employer_id(conn, company_name: str) -> int:
    normalized = normalize_employer_name(company_name)
    display = display_name_from_normalized(normalized)
    conn.execute(
        """
        INSERT INTO employers(normalized_name, display_name)
        VALUES (?, ?)
        ON CONFLICT(normalized_name) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
        """,
        (normalized, display),
    )
    return conn.execute("SELECT id FROM employers WHERE normalized_name = ?", (normalized,)).fetchone()["id"]


def _salary_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(str(value).replace("$", "").replace(",", ""))
    except ValueError:
        return None


def sponsorship_status(jd_text: str) -> tuple[str, bool, str | None]:
    lower = jd_text.lower()
    for pattern in EXCLUSION_PATTERNS:
        if re.search(pattern, lower):
            return "No Sponsorship", True, f"Posting matched exclusion pattern: {pattern}"
    if any(re.search(pattern, lower) for pattern in SPONSOR_POSITIVE_PATTERNS):
        return "Supports Sponsorship", False, None
    return "Unknown", False, None


def import_jobs_csv(db_path: Path, path: Path, source: str = "manual_csv") -> int:
    with path.open(newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))
    with connect(db_path) as conn:
        for row in rows:
            company = row["company_name"].strip()
            sponsor_flag, excluded, reason = sponsorship_status(row.get("jd_text", ""))
            employer_id = _employer_id(conn, company)
            conn.execute(
                """
                INSERT INTO jobs(
                    employer_id, company_name, title, url, source, ats_type, posted_date,
                    location, remote_status, salary_min, salary_max, company_stage,
                    company_type, jd_text, sponsorship_flag, excluded, exclusion_reason
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    employer_id = excluded.employer_id,
                    company_name = excluded.company_name,
                    title = excluded.title,
                    source = excluded.source,
                    ats_type = excluded.ats_type,
                    posted_date = excluded.posted_date,
                    location = excluded.location,
                    remote_status = excluded.remote_status,
                    salary_min = excluded.salary_min,
                    salary_max = excluded.salary_max,
                    company_stage = excluded.company_stage,
                    company_type = excluded.company_type,
                    jd_text = excluded.jd_text,
                    sponsorship_flag = excluded.sponsorship_flag,
                    excluded = excluded.excluded,
                    exclusion_reason = excluded.exclusion_reason,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    employer_id,
                    company,
                    row["title"].strip(),
                    row["url"].strip(),
                    source,
                    row.get("ats_type"),
                    row.get("posted_date"),
                    row.get("location"),
                    row.get("remote_status"),
                    _salary_float(row.get("salary_min")),
                    _salary_float(row.get("salary_max")),
                    row.get("company_stage"),
                    row.get("company_type"),
                    row.get("jd_text", ""),
                    sponsor_flag,
                    int(excluded),
                    reason,
                ),
            )
            job_id = conn.execute("SELECT id FROM jobs WHERE url = ?", (row["url"].strip(),)).fetchone()["id"]
            conn.execute("INSERT OR IGNORE INTO applications(job_id) VALUES (?)", (job_id,))
        conn.execute(
            "INSERT INTO action_logs(action, entity_type, message) VALUES (?, ?, ?)",
            ("import_jobs", "job", f"Imported {len(rows)} jobs from {path.name}"),
        )
    return len(rows)


def classify_track(title: str, jd_text: str) -> str:
    families = title_families_for(f"{title} {jd_text}")
    for preferred in ["ai_ops", "revenue_ops", "strategy_ops", "gtm", "cs_ops", "program_management", "business_analytics", "consulting"]:
        if preferred in families:
            return TRACK_LABELS[preferred]
    return "Strategy & Operations / BizOps"


def _freshness_multiplier(posted_date: str | None) -> float:
    if not posted_date:
        return 0.9
    try:
        posted = datetime.strptime(posted_date, "%Y-%m-%d").date()
    except ValueError:
        return 0.9
    age_days = max(0, (date.today() - posted).days)
    if age_days <= 7:
        return 1.1
    if age_days <= 30:
        return 1.0
    return 0.85


def _location_multiplier(location: str | None, remote_status: str | None) -> tuple[float, str]:
    text = f"{location or ''} {remote_status or ''}".lower()
    if "chicago" in text:
        return 1.15, "Top preference: Chicago"
    if "remote" in text:
        return 1.12, "Top preference: US remote"
    if any(city in text for city in ["new york", "san francisco", "mountain view", "palo alto", "sunnyvale", "san jose", "santa clara", "miami"]):
        return 1.05, "Target metro"
    return 0.9, "Lower-priority US metro"


def score_jobs(db_path: Path, threshold: float = 70.0) -> int:
    with connect(db_path) as conn:
        jobs = conn.execute(
            """
            SELECT j.*, s.sponsor_score, s.sponsor_status
            FROM jobs j
            LEFT JOIN sponsor_score_snapshots s ON s.employer_id = j.employer_id
            """
        ).fetchall()
        for job in jobs:
            jd = job["jd_text"].lower()
            title = job["title"]
            track = classify_track(title, job["jd_text"])
            tools = sorted(tool for tool in TARGET_TOOLS if tool in jd)
            match = 45.0 + min(20.0, len(tools) * 3.0)
            if any(term in jd for term in ["strategy", "operations", "program", "analytics", "revenue", "gtm", "customer success", "ai"]):
                match += 18.0
            if re.search(r"\b(senior|lead|manager)\b", title.lower()):
                match += 10.0
            if job["salary_max"] is not None and job["salary_max"] < 120000:
                match -= 35.0
            if job["excluded"]:
                match = min(match, 35.0)
            match = round(max(0.0, min(100.0, match)), 1)

            sponsor_score = job["sponsor_score"] if job["sponsor_score"] is not None else 35.0
            sponsor_multiplier = 0.75 + (float(sponsor_score) / 100.0) * 0.5
            location_multiplier, location_fit = _location_multiplier(job["location"], job["remote_status"])
            company_multiplier = 1.12 if (job["company_type"] or "").lower() == "ai startup" and "series b" in (job["company_stage"] or "").lower() else 1.0
            final_priority = round(match * sponsor_multiplier * _freshness_multiplier(job["posted_date"]) * location_multiplier * company_multiplier, 1)
            salary_fit = "No salary listed" if job["salary_max"] is None else ("Target range" if job["salary_max"] >= 120000 else "Below floor")
            gaps = []
            if "sql" not in jd and "analytics" in jd:
                gaps.append("SQL not explicit in JD")
            if job["sponsorship_flag"] == "Unknown":
                gaps.append("Sponsorship not explicit")
            risk = f"{track}; sponsor status {job['sponsor_status'] or 'Unknown'}; {job['sponsorship_flag']}."
            conn.execute(
                """
                INSERT INTO job_match_scores(
                    job_id, track, match_score, final_priority, skills_overlap,
                    hard_gaps, location_fit, salary_fit, risk_note
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    track = excluded.track,
                    match_score = excluded.match_score,
                    final_priority = excluded.final_priority,
                    skills_overlap = excluded.skills_overlap,
                    hard_gaps = excluded.hard_gaps,
                    location_fit = excluded.location_fit,
                    salary_fit = excluded.salary_fit,
                    risk_note = excluded.risk_note,
                    computed_at = CURRENT_TIMESTAMP
                """,
                (job["id"], track, match, final_priority, ", ".join(tools) or "No direct tool match", "; ".join(gaps) or "No hard gaps found", location_fit, salary_fit, risk),
            )
            if match >= threshold and not job["excluded"]:
                conn.execute("UPDATE applications SET stage = 'Shortlisted', updated_at = CURRENT_TIMESTAMP WHERE job_id = ?", (job["id"],))
        conn.execute(
            "INSERT INTO action_logs(action, entity_type, message) VALUES (?, ?, ?)",
            ("score_jobs", "job", f"Scored {len(jobs)} jobs with threshold {threshold}"),
        )
    return len(jobs)


def generate_application_assets(db_path: Path, job_id: int) -> None:
    with connect(db_path) as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        score = conn.execute("SELECT * FROM job_match_scores WHERE job_id = ?", (job_id,)).fetchone()
        if not job or not score:
            raise ValueError("Job must exist and be scored before generating assets.")
        resume_stub = (
            f"ASHWINI AHIRE\n"
            f"Strategy & Business Operations Program Manager ({score['track']})\n\n"
            f"Selected focus for {job['title']} at {job['company_name']}:\n"
            f"- Use master resume bullets for {score['track']}.\n"
            f"- Surface keywords: {score['skills_overlap']}.\n"
            f"- Keep official titles and approved metrics unchanged.\n"
        )
        cover_letter = (
            f"Hi {job['company_name']} team,\n\n"
            f"I am interested in the {job['title']} role because it aligns with my work across strategy, operations, analytics, and AI-enabled execution. "
            f"I would bring structured problem solving, cross-functional operating cadence, and data-driven execution to the team.\n\n"
            f"Best,\nAshwini Ahire"
        )
        for doc_type, content in [("resume_plan", resume_stub), ("cover_letter", cover_letter)]:
            conn.execute(
                """
                INSERT INTO tailored_documents(job_id, document_type, content, validation_status, validation_notes)
                VALUES (?, ?, ?, 'Needs master resume render', 'Phase 4 guardrail stub: render DOCX/PDF after master resume parser is enabled.')
                """,
                (job_id, doc_type, content),
            )
        conn.execute("UPDATE applications SET stage = 'Tailored', updated_at = CURRENT_TIMESTAMP WHERE job_id = ?", (job_id,))


def create_outreach_drafts(db_path: Path, job_id: int) -> None:
    with connect(db_path) as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not job:
            raise ValueError("Job not found.")
        drafts = [
            ("linkedin", "referral", f"Hi, I saw an opening for {job['title']} at {job['company_name']} and would love to learn whether the team is open to referrals for strategy/ops candidates with AI operations and analytics experience."),
            ("email", "hiring_manager", f"Hi, I’m Ashwini Ahire, a Strategy & Business Operations Program Manager in Chicago. I’m excited about {job['company_name']}’s {job['title']} role and would value the chance to share how my background in AI strategy, RevOps, and CX analytics could help the team."),
        ]
        if (job["company_type"] or "").lower() == "ai startup":
            drafts.append(("email", "founder", f"Hi, I’m Ashwini Ahire. I’m following {job['company_name']} and noticed the {job['title']} role. My background sits at the intersection of AI operations, GTM execution, and analytics, and I’d be excited to help an early team scale operating discipline."))
        for channel, audience, text in drafts:
            conn.execute(
                "INSERT INTO outreach_drafts(job_id, channel, audience, draft_text) VALUES (?, ?, ?, ?)",
                (job_id, channel, audience, text),
            )


def classify_email(subject: str, snippet: str) -> tuple[str, float]:
    text = f"{subject} {snippet}".lower()
    checks = [
        ("Interviewing", 0.9, ["interview", "meet with", "schedule a time"]),
        ("Recruiter Screen", 0.9, ["recruiter screen", "phone screen", "intro call"]),
        ("Assessment", 0.88, ["assessment", "case study", "take-home", "coding challenge"]),
        ("Rejected", 0.92, ["not moving forward", "unfortunately", "decided to proceed with other candidates"]),
        ("Offer", 0.95, ["offer", "congratulations"]),
        ("In Review", 0.75, ["reviewing", "under review"]),
        ("Application Received", 0.8, ["received your application", "application has been received", "thank you for applying"]),
    ]
    for stage, confidence, phrases in checks:
        if any(phrase in text for phrase in phrases):
            return stage, confidence
    return "Other", 0.45


def record_email_event(db_path: Path, sender: str, subject: str, snippet: str, received_at: str, application_id: int | None = None) -> str:
    stage, confidence = classify_email(subject, snippet)
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO email_events(application_id, sender, subject, snippet, classified_stage, confidence, received_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (application_id, sender, subject, snippet, stage, confidence, received_at),
        )
        if application_id and stage not in {"Other", "Application Received"}:
            conn.execute(
                "UPDATE applications SET stage = ?, last_response_at = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (stage, received_at, application_id),
            )
    return stage


def mark_followups(db_path: Path) -> int:
    due = (date.today() + timedelta(days=7)).isoformat()
    with connect(db_path) as conn:
        conn.execute(
            """
            UPDATE applications
            SET follow_up_due_at = ?
            WHERE stage IN ('Applied', 'In Review') AND follow_up_due_at IS NULL
            """,
            (due,),
        )
        changed = conn.total_changes
    return changed


def generate_interview_prep(db_path: Path, job_id: int) -> str:
    with connect(db_path) as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        score = conn.execute("SELECT * FROM job_match_scores WHERE job_id = ?", (job_id,)).fetchone()
        if not job:
            raise ValueError("Job not found.")
        content = (
            f"# Prep Pack: {job['company_name']} - {job['title']}\n\n"
            f"## Company / Role\n{job['company_name']} is tracked as {job['company_type'] or 'Unknown'}"
            f" ({job['company_stage'] or 'stage unknown'}). Role track: {score['track'] if score else 'Unscored'}.\n\n"
            "## Likely Questions\n"
            "- Walk me through a strategy/operations program you led.\n"
            "- How do you prioritize ambiguous cross-functional work?\n"
            "- How have you used analytics or AI tooling to improve an operating process?\n\n"
            "## STAR Stories To Prepare\n"
            "- 90% manual review reduction\n"
            "- 73% renewal cycle time reduction\n"
            "- CSAT +15% in 6 months\n\n"
            "## Sponsorship Talking Points\n"
            "- Confirm H-1B transfer support and immigration counsel timeline.\n"
            "- Ask whether the company has a green-card/PERM track record.\n"
        )
        conn.execute("INSERT INTO interview_prep_packs(job_id, content) VALUES (?, ?)", (job_id, content))
    return content
