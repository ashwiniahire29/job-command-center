from __future__ import annotations

import re


TITLE_FAMILIES = {
    "strategy_ops": [r"strategy", r"\boperations?\b", r"business operations", r"bizops", r"chief of staff"],
    "program_management": [r"program manager", r"project manager", r"operations manager"],
    "business_analytics": [r"business analyst", r"data analyst", r"analytics", r"insights"],
    "revenue_ops": [r"revenue operations", r"revops", r"sales operations", r"renewal"],
    "gtm": [r"go[\s-]?to[\s-]?market", r"\bgtm\b", r"market strategy"],
    "cs_ops": [r"customer success", r"\bcs\b", r"customer experience", r"\bcx\b"],
    "ai_ops": [r"\bai\b", r"artificial intelligence", r"\bllm\b", r"\bnlp\b"],
    "consulting": [r"consultant", r"consulting", r"transformation"],
}

TARGET_METROS = {
    "chicago": {("CHICAGO", "IL")},
    "new_york": {("NEW YORK", "NY")},
    "sf_bay_area": {
        ("SAN FRANCISCO", "CA"),
        ("MOUNTAIN VIEW", "CA"),
        ("PALO ALTO", "CA"),
        ("SUNNYVALE", "CA"),
        ("SAN JOSE", "CA"),
        ("SANTA CLARA", "CA"),
    },
    "miami": {("MIAMI", "FL")},
}


def title_families_for(title: str) -> set[str]:
    title_lower = title.lower()
    matches: set[str] = set()
    for family, patterns in TITLE_FAMILIES.items():
        if any(re.search(pattern, title_lower) for pattern in patterns):
            matches.add(family)
    return matches


def is_relevant_title(title: str) -> bool:
    return bool(title_families_for(title))


def metro_for(city: str | None, state: str | None) -> str | None:
    if not city or not state:
        return None
    key = (city.strip().upper(), state.strip().upper())
    for metro, members in TARGET_METROS.items():
        if key in members:
            return metro
    return None
