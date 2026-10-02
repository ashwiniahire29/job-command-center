from __future__ import annotations

import re


PROTECTED_METRIC_PATTERNS = [
    r"\d+%",
    r"CSAT \+\d+%",
    r"FCR \+\d+%",
    r"manual effort [−-]\d+%",
]


def extract_protected_claims(master_text: str) -> set[str]:
    claims: set[str] = set()
    for pattern in PROTECTED_METRIC_PATTERNS:
        claims.update(match.group(0) for match in re.finditer(pattern, master_text))
    for title in [
        "Strategy & Business Operations Program Manager",
        "Senior Analyst",
        "CX Analyst",
        "PM Operations",
    ]:
        if title in master_text:
            claims.add(title)
    for tool in ["SQL", "Python", "R", "Power BI", "Tableau", "Snowflake", "Salesforce", "ServiceNow", "Qualtrics", "NLP", "LLM"]:
        if tool.lower() in master_text.lower():
            claims.add(tool)
    return claims


def validate_tailored_output(master_text: str, output_text: str) -> tuple[bool, list[str]]:
    allowed = extract_protected_claims(master_text)
    notes: list[str] = []
    for match in re.finditer(r"\d+%", output_text):
        metric = match.group(0)
        if metric not in allowed and f"+{metric}" not in allowed:
            notes.append(f"Metric not found in master resume: {metric}")
    official_titles = ["Strategy & Business Operations Program Manager", "Senior Analyst", "CX Analyst", "PM Operations"]
    if "Business Operations Program Manager" in output_text and official_titles[0] not in output_text:
        notes.append("Official current title was altered or omitted.")
    for tool in ["SQL", "Python", "R", "Power BI", "Tableau", "Snowflake", "Salesforce", "ServiceNow", "Qualtrics", "NLP", "LLM", "Kubernetes", "Java"]:
        if re.search(rf"\b{re.escape(tool)}\b", output_text, re.IGNORECASE) and tool not in allowed:
            notes.append(f"Tool not found in master resume: {tool}")
    return not notes, notes
