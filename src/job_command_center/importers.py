from __future__ import annotations

import csv
import hashlib
from collections.abc import Iterable
from pathlib import Path
from statistics import median
from typing import Any

from .db import connect
from .normalization import display_name_from_normalized, normalize_employer_name
from .roles import metro_for, title_families_for


SOURCE_LCA = "dol_lca"
SOURCE_PERM = "dol_perm"
SOURCE_USCIS = "uscis_h1b_employer_hub"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as file:
            return list(csv.DictReader(file))
    if path.suffix.lower() in {".xlsx", ".xls"}:
        import pandas as pd

        return pd.read_excel(path).fillna("").to_dict("records")
    raise ValueError(f"Unsupported source file: {path}")


def _pick(row: dict[str, Any], names: Iterable[str], default: Any = "") -> Any:
    normalized = {str(key).strip().lower().replace(" ", "_"): value for key, value in row.items()}
    for name in names:
        key = name.strip().lower().replace(" ", "_")
        if key in normalized and normalized[key] not in {None, ""}:
            return normalized[key]
    return default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _float(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", "").replace("$", ""))
    except (TypeError, ValueError):
        return None


def _employer_id(conn, employer_name: str) -> int:
    normalized = normalize_employer_name(employer_name)
    display_name = display_name_from_normalized(normalized)
    conn.execute(
        """
        INSERT INTO employers(normalized_name, display_name)
        VALUES (?, ?)
        ON CONFLICT(normalized_name) DO UPDATE SET
            display_name = excluded.display_name,
            updated_at = CURRENT_TIMESTAMP
        """,
        (normalized, display_name),
    )
    employer_id = conn.execute(
        "SELECT id FROM employers WHERE normalized_name = ?", (normalized,)
    ).fetchone()["id"]
    conn.execute(
        """
        INSERT OR IGNORE INTO employer_aliases(employer_id, alias, normalized_alias, source)
        VALUES (?, ?, ?, 'import')
        """,
        (employer_id, employer_name, normalized),
    )
    return employer_id


def register_source_file(conn, path: Path, source_type: str, fiscal_year: int, partial_year: bool = False) -> int:
    conn.execute(
        """
        INSERT OR IGNORE INTO raw_import_files(source_type, fiscal_year, path, sha256, partial_year)
        VALUES (?, ?, ?, ?, ?)
        """,
        (source_type, fiscal_year, str(path), _sha256(path), int(partial_year)),
    )
    return conn.execute(
        """
        SELECT id FROM raw_import_files
        WHERE source_type = ? AND fiscal_year = ? AND path = ?
        """,
        (source_type, fiscal_year, str(path)),
    ).fetchone()["id"]


def ingest_lca(db_path: Path, path: Path, fiscal_year: int, partial_year: bool = False) -> int:
    rows = _read_rows(path)
    with connect(db_path) as conn:
        source_file_id = register_source_file(conn, path, SOURCE_LCA, fiscal_year, partial_year)
        for row in rows:
            employer_id = _employer_id(conn, str(_pick(row, ["employer_name", "employer"])))
            conn.execute(
                """
                INSERT INTO lca_filings(
                    employer_id, fiscal_year, case_status, job_title, soc_code,
                    worksite_city, worksite_state, wage, wage_unit, source_file_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    employer_id,
                    fiscal_year,
                    str(_pick(row, ["case_status", "status"], "UNKNOWN")),
                    str(_pick(row, ["job_title", "job_title_text", "position_title"], "")),
                    str(_pick(row, ["soc_code", "soc"], "")),
                    str(_pick(row, ["worksite_city", "city"], "")),
                    str(_pick(row, ["worksite_state", "state"], "")),
                    _float(_pick(row, ["wage_rate_of_pay_from", "wage", "prevailing_wage"])),
                    str(_pick(row, ["wage_unit_of_pay", "wage_unit"], "")),
                    source_file_id,
                ),
            )
        conn.execute(
            "INSERT INTO ingest_logs(action, source_type, rows_processed, message) VALUES (?, ?, ?, ?)",
            ("ingest", SOURCE_LCA, len(rows), f"Imported {path.name}"),
        )
    return len(rows)


def ingest_perm(db_path: Path, path: Path, fiscal_year: int, partial_year: bool = False) -> int:
    rows = _read_rows(path)
    with connect(db_path) as conn:
        source_file_id = register_source_file(conn, path, SOURCE_PERM, fiscal_year, partial_year)
        for row in rows:
            employer_id = _employer_id(conn, str(_pick(row, ["employer_name", "employer"])))
            conn.execute(
                """
                INSERT INTO perm_filings(
                    employer_id, fiscal_year, case_status, job_title,
                    worksite_city, worksite_state, wage, source_file_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    employer_id,
                    fiscal_year,
                    str(_pick(row, ["case_status", "status"], "UNKNOWN")),
                    str(_pick(row, ["job_title", "job_title_text", "position_title"], "")),
                    str(_pick(row, ["worksite_city", "city"], "")),
                    str(_pick(row, ["worksite_state", "state"], "")),
                    _float(_pick(row, ["wage", "wage_offer_from", "prevailing_wage"])),
                    source_file_id,
                ),
            )
        conn.execute(
            "INSERT INTO ingest_logs(action, source_type, rows_processed, message) VALUES (?, ?, ?, ?)",
            ("ingest", SOURCE_PERM, len(rows), f"Imported {path.name}"),
        )
    return len(rows)


def ingest_uscis(db_path: Path, path: Path, fiscal_year: int, partial_year: bool = False) -> int:
    rows = _read_rows(path)
    with connect(db_path) as conn:
        source_file_id = register_source_file(conn, path, SOURCE_USCIS, fiscal_year, partial_year)
        for row in rows:
            employer_id = _employer_id(conn, str(_pick(row, ["employer_name", "employer", "petitioner"])))
            conn.execute(
                """
                INSERT INTO uscis_employer_stats(
                    employer_id, fiscal_year, initial_approvals, initial_denials,
                    continuing_approvals, continuing_denials, source_file_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(employer_id, fiscal_year) DO UPDATE SET
                    initial_approvals = excluded.initial_approvals,
                    initial_denials = excluded.initial_denials,
                    continuing_approvals = excluded.continuing_approvals,
                    continuing_denials = excluded.continuing_denials,
                    source_file_id = excluded.source_file_id
                """,
                (
                    employer_id,
                    fiscal_year,
                    _int(_pick(row, ["initial_approvals", "initial_approval"])),
                    _int(_pick(row, ["initial_denials", "initial_denial"])),
                    _int(_pick(row, ["continuing_approvals", "continuing_approval"])),
                    _int(_pick(row, ["continuing_denials", "continuing_denial"])),
                    source_file_id,
                ),
            )
        conn.execute(
            "INSERT INTO ingest_logs(action, source_type, rows_processed, message) VALUES (?, ?, ?, ?)",
            ("ingest", SOURCE_USCIS, len(rows), f"Imported {path.name}"),
        )
    return len(rows)


def refresh_wage_summaries(db_path: Path) -> int:
    with connect(db_path) as conn:
        conn.execute("DELETE FROM metro_wage_summaries")
        wages: dict[tuple[int, str, str], list[float]] = {}
        for row in conn.execute("SELECT employer_id, job_title, worksite_city, worksite_state, wage FROM lca_filings WHERE wage IS NOT NULL"):
            metro = metro_for(row["worksite_city"], row["worksite_state"])
            if not metro:
                continue
            for family in title_families_for(row["job_title"]):
                wages.setdefault((row["employer_id"], metro, family), []).append(float(row["wage"]))
        for (employer_id, metro, family), values in wages.items():
            conn.execute(
                """
                INSERT INTO metro_wage_summaries(employer_id, metro, title_family, median_wage, filing_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                (employer_id, metro, family, median(values), len(values)),
            )
        conn.execute(
            "INSERT INTO ingest_logs(action, rows_processed, message) VALUES (?, ?, ?)",
            ("refresh_wage_summaries", len(wages), "Rebuilt target-metro wage summaries"),
        )
    return len(wages)

