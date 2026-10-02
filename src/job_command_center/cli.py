from __future__ import annotations

import argparse
from pathlib import Path

from .config import ROOT, get_settings
from .dashboard_data import ranked_employers
from .db import init_db
from .importers import ingest_lca, ingest_perm, ingest_uscis, refresh_wage_summaries
from .scoring import refresh_sponsor_scores


SAMPLE_DIR = ROOT / "tests" / "fixtures"


def init_database(args: argparse.Namespace) -> None:
    settings = get_settings()
    init_db(settings.db_path)
    print(f"Initialized SQLite database at {settings.db_path}")


def ingest_sample(args: argparse.Namespace) -> None:
    settings = get_settings()
    init_db(settings.db_path)
    ingest_lca(settings.db_path, SAMPLE_DIR / "sample_lca.csv", fiscal_year=2026, partial_year=True)
    ingest_perm(settings.db_path, SAMPLE_DIR / "sample_perm.csv", fiscal_year=2026, partial_year=True)
    ingest_uscis(settings.db_path, SAMPLE_DIR / "sample_uscis.csv", fiscal_year=2026, partial_year=True)
    refresh_wage_summaries(settings.db_path)
    refresh_sponsor_scores(settings.db_path)
    print("Loaded sample sponsor intelligence.")
    for row in ranked_employers(settings.db_path, limit=10):
        score = "n/a" if row["sponsor_score"] is None else row["sponsor_score"]
        print(
            f"{row['display_name']}: status={row['sponsor_status']} score={score} "
            f"h1b={row['h1b_filings_3y']} perm={row['perm_filings_3y']} "
            f"approval={row['approval_rate']} relevant={row['relevant_role_filings']} "
            f"wage={row['median_target_metro_wage']} trend={row['trend']}"
        )


def ingest_file(args: argparse.Namespace) -> None:
    settings = get_settings()
    init_db(settings.db_path)
    path = Path(args.path)
    if args.source == "lca":
        count = ingest_lca(settings.db_path, path, args.fiscal_year, args.partial_year)
    elif args.source == "perm":
        count = ingest_perm(settings.db_path, path, args.fiscal_year, args.partial_year)
    else:
        count = ingest_uscis(settings.db_path, path, args.fiscal_year, args.partial_year)
    refresh_wage_summaries(settings.db_path)
    refresh_sponsor_scores(settings.db_path)
    print(f"Imported {count} rows from {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="job-command-center")
    subparsers = parser.add_subparsers(required=True)

    init_parser = subparsers.add_parser("init-db", help="Create or upgrade the local SQLite database.")
    init_parser.set_defaults(func=init_database)

    sample_parser = subparsers.add_parser("ingest-sample", help="Load bundled sample sponsor data.")
    sample_parser.set_defaults(func=ingest_sample)

    ingest_parser = subparsers.add_parser("ingest-file", help="Import a CSV/XLSX disclosure file.")
    ingest_parser.add_argument("source", choices=["lca", "perm", "uscis"])
    ingest_parser.add_argument("path")
    ingest_parser.add_argument("--fiscal-year", type=int, required=True)
    ingest_parser.add_argument("--partial-year", action="store_true")
    ingest_parser.set_defaults(func=ingest_file)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
