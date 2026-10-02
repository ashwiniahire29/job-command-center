from __future__ import annotations

import re


LEGAL_SUFFIXES = {
    "co",
    "company",
    "corp",
    "corporation",
    "inc",
    "incorporated",
    "llc",
    "ltd",
    "limited",
    "lp",
    "plc",
}

KNOWN_ALIASES = {
    "google": "google",
    "google llc": "google",
    "google inc": "google",
    "alphabet inc": "alphabet",
    "meta platforms": "meta",
    "facebook": "meta",
    "microsoft corporation": "microsoft",
    "amazon com services": "amazon",
    "salesforce com": "salesforce",
}


def normalize_employer_name(name: str) -> str:
    cleaned = name.lower().replace("&", " and ")
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if cleaned in KNOWN_ALIASES:
        return KNOWN_ALIASES[cleaned]
    tokens = [token for token in cleaned.split() if token not in LEGAL_SUFFIXES]
    normalized = " ".join(tokens).strip()
    return KNOWN_ALIASES.get(normalized, normalized)


def display_name_from_normalized(normalized: str) -> str:
    special = {"ibm": "IBM", "nvidia": "NVIDIA"}
    return special.get(normalized, normalized.title())
