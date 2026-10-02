from __future__ import annotations

import argparse
from pathlib import Path

from .config import ROOT, get_settings
from .dashboard_data import ranked_employers, ranked_jobs
from .db import init_db
from .importers import ingest_lca, ingest_perm, ingest_uscis, refresh_wage_summaries
from .jobs import create_outreach_drafts, generate_application_assets, generate_interview_prep, import_jobs_csv, score_jobs
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


def ingest_jobs_sample(args: argparse.Namespace) -> None:
    settings = get_settings()
    init_db(settings.db_path)
    count = import_jobs_csv(settings.db_path, SAMPLE_DIR / "sample_jobs.csv")
    scored = score_jobs(settings.db_path)
    print(f"Loaded {count} sample jobs and scored {scored}.")
    for row in ranked_jobs(settings.db_path, limit=10):
        print(
            f"{row['company_name']} - {row['title']}: stage={row['stage']} "
            f"match={row['match_score']} priority={row['final_priority']} "
            f"sponsor={row['sponsorship_flag']} excluded={bool(row['excluded'])}"
        )


def score_jobs_command(args: argparse.Namespace) -> None:
    settings = get_settings()
    scored = score_jobs(settings.db_path, threshold=args.threshold)
    print(f"Scored {scored} jobs.")


def generate_assets_command(args: argparse.Namespace) -> None:
    settings = get_settings()
    generate_application_assets(settings.db_path, args.job_id)
    create_outreach_drafts(settings.db_path, args.job_id)
    print(f"Generated resume plan, cover letter, and outreach drafts for job {args.job_id}.")


def generate_prep_command(args: argparse.Namespace) -> None:
    settings = get_settings()
    content = generate_interview_prep(settings.db_path, args.job_id)
    print(content)


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

    jobs_sample_parser = subparsers.add_parser("ingest-jobs-sample", help="Load bundled sample jobs and score them.")
    jobs_sample_parser.set_defaults(func=ingest_jobs_sample)

    ingest_parser = subparsers.add_parser("ingest-file", help="Import a CSV/XLSX disclosure file.")
    ingest_parser.add_argument("source", choices=["lca", "perm", "uscis"])
    ingest_parser.add_argument("path")
    ingest_parser.add_argument("--fiscal-year", type=int, required=True)
    ingest_parser.add_argument("--partial-year", action="store_true")
    ingest_parser.set_defaults(func=ingest_file)

    score_parser = subparsers.add_parser("score-jobs", help="Score imported jobs.")
    score_parser.add_argument("--threshold", type=float, default=70.0)
    score_parser.set_defaults(func=score_jobs_command)

    assets_parser = subparsers.add_parser("generate-assets", help="Generate local tailoring and outreach drafts for a job.")
    assets_parser.add_argument("job_id", type=int)
    assets_parser.set_defaults(func=generate_assets_command)

    prep_parser = subparsers.add_parser("generate-prep", help="Generate an interview prep pack for a job.")
    prep_parser.add_argument("job_id", type=int)
    prep_parser.set_defaults(func=generate_prep_command)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
