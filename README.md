# Job Command Center

Local-first job-search command center. Phase 1 builds sponsor intelligence from official public H-1B/PERM data and local sample fixtures.

## Phase 1: Sponsor Intelligence

This phase creates a SQLite sponsor database, imports LCA/PERM/USCIS employer data, computes sponsor scores, and shows the results in Streamlit. It does not call Anthropic, Gmail, Playwright, LinkedIn, Indeed, or Wellfound.

Official data sources:

- DOL OFLC performance disclosure files: <https://www.dol.gov/agencies/eta/foreign-labor/performance>
- USCIS H-1B Employer Data Hub: <https://www.uscis.gov/tools/reports-and-studies/h-1b-employer-data-hub>

## Quickstart

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m job_command_center.cli init-db
python -m job_command_center.cli ingest-sample
streamlit run src/job_command_center/dashboard.py
```

Import a real CSV/XLSX disclosure file:

```bash
python -m job_command_center.cli ingest-file lca data/source_cache/LCA_Disclosure_Data_FY2026_Q3.xlsx --fiscal-year 2026 --partial-year
python -m job_command_center.cli ingest-file perm data/source_cache/PERM_Disclosure_Data_FY2026_Q3.xlsx --fiscal-year 2026 --partial-year
python -m job_command_center.cli ingest-file uscis data/source_cache/FY2026_H1B_Employer_Data.csv --fiscal-year 2026 --partial-year
```

## Scoring

Sponsor Score is weighted toward recent PERM activity, then H-1B filing volume, USCIS approval rate, target-role filings, and target-metro wage evidence. Employers with sparse filing history are marked `Unverified` rather than automatically penalized, which keeps AI startups eligible for manual review.

## Privacy

All data stays local in `data/job_command_center.sqlite3`. Phase 1 does not require secrets. Future API keys should live in `.env`, never in git.
