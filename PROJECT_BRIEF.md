You are helping me build a personal job-search command center. The goal: land interviews at strong companies (big tech and well-funded startups, especially AI startups) that sponsor H-1B transfers and ideally green cards, within the next 90 days starting today. Build this incrementally, in phases, testing each phase before moving on. Ask me for any inputs you need (API keys, settings) before building the part that depends on them.

## About me
- Name: Ashwini Ahire, based in Chicago, IL
- Official current title: Strategy & Business Operations Program Manager, Motorola Solutions (Global Services / AI Strategy), Jul 2025–present; previously Senior Analyst, Customer Experience at Motorola Solutions (Jan 2024–Jul 2025), CX Analyst co-op (2023), PM Operations at L&T Infotech/LTIMindtree (2018–2021)
- Education: MS Engineering Management, Northeastern University (2023); BE Electronics & Telecommunication, University of Mumbai (2018)
- Experience: 6+ years across strategy & operations, RevOps, CX analytics, AI operations, and cross-functional program management
- Stack: SQL, Python, R, Power BI (DAX), Tableau, Snowflake, Salesforce, ServiceNow, Qualtrics, NLP/LLM tooling, prompt engineering, n8n, Cursor
- Headline metrics (use exactly as written, never alter): 90% manual review reduction; 73% renewal cycle time reduction; CSAT +15% in 6 months; adoption +28%; CSAT +20% and FCR +10% (co-op); retention +25%; 95% SLA adherence; profitability +18%; manual effort −30%
- Target role tracks: Strategy & Operations / BizOps, Revenue Operations, GTM Strategy, CS Strategy & Ops, AI Strategy / AI Operations, Senior Program Manager, Business/Data Analyst (senior), Senior Consultant (strategy/operations/GBS)
- Seniority: Senior / Lead / Manager level. Flag (don't auto-reject) Associate-level roles as possible downlevels.
- Locations, in priority order: Chicago (top preference); New York City; SF Bay Area (San Francisco, Mountain View, Palo Alto, Sunnyvale, San Jose, Santa Clara, and nearby); Miami; plus US-remote roles. Treat other major US metros as lower priority, not excluded. Boost Chicago and remote in ranking.
- Salary: target base $130K–$200K. Exclude postings whose listed max is below $120K. Flag postings with no salary listed rather than excluding them, and estimate range from LCA wage data where possible.
- Sponsorship: must support H-1B transfer; strongly prefer employers with a green card (PERM) track record
- Company focus: big tech and venture-backed startups (prioritize AI startups, Series B+ highest, then Series A), plus established tech companies with strong sponsorship history

## Master resume
- Source file: data/master_resume.docx (exported from my Google Doc). Parse it on startup and re-parse when the file changes.
- It is a SUPERSET resume: each role has a "core" bullet plus labeled variants (S&O, RevOps, GTM, BA, CS, Condensed), several summary variants, and a "Title variants and keyword bank" table mapping each target track to: the title to use, which Motorola bullets to lead with, and keywords to surface.
- The tailoring engine must use that table: classify each job into a track, pick that track's summary, lead bullets, bullet variants, and keywords, and select from existing bullets rather than writing new claims.
- Title rule: always show my official title "Strategy & Business Operations Program Manager" as the primary title; a track-specific descriptor may go in parentheses, e.g., "(AI Strategy & Revenue Operations)". Same rule for the Senior Analyst role. Never replace an official title outright.
- Output resumes must be one page for roles under Manager level, up to two pages otherwise.

## Tech stack
Python 3.11+, SQLite (upgradeable to Postgres), Streamlit for the dashboard, Anthropic API (Claude) for scoring/tailoring/classification, Playwright for form-filling, python-docx + PDF export for resumes, Gmail API (read-only scope) for email tracking. Use a .env file for secrets. Runnable locally with one command.

## Phase 1 — Sponsor intelligence database
- Download and ingest DOL OFLC H-1B LCA disclosure data (last 3 fiscal years), PERM disclosure data, and the USCIS H-1B Employer Data Hub.
- Employer table: normalized company name (handle "Google LLC" vs "Google Inc", subsidiaries, d/b/a names), H-1B filings per year, PERM filings per year, approval rates, filings for strategy/ops/program/analyst SOC codes, median wage for titles similar to my targets in my target metros, trend.
- Sponsor Score (0–100): heavy weight on recent PERM activity, then H-1B volume, approval rate, relevant-role filings.
- Startup handling: companies with no or little filing history (common for new AI startups) get Sponsor Status = "Unverified" instead of a low score. For these, compute a Startup Sponsor Likelihood from funding stage, total raised, headcount, any LCA filings at all, JD sponsorship language, and visa-friendly signals I import. Never auto-exclude Unverified companies.

## Phase 2 — Company and job discovery
Use only official, public, or permitted sources. Do NOT scrape LinkedIn, Indeed, or Wellfound, and do not log into any site on my behalf.

Company universe:
- Big tech list (seed manually, editable): Google, Meta, Apple, Amazon, Microsoft, NVIDIA, Salesforce, Adobe, Uber, Airbnb, Stripe, Databricks, Snowflake, ServiceNow, LinkedIn, Netflix, Intuit, Oracle, Cisco, Workday, etc.
- AI startups: Y Combinator public company directory (ycombinator.com/companies; filter to active/hiring companies, recent batches weighted higher, AI-tagged weighted higher); public VC portfolio job boards (e.g., a16z, Sequoia, Greylock, General Catalyst, Accel, Index boards that are publicly accessible); curated AI lists I add (e.g., Forbes AI 50).
- All employers with Sponsor Score ≥ 50 from Phase 1.

Job sources:
- For each company, auto-detect its ATS and pull from public job-board APIs: Greenhouse, Lever, Ashby, SmartRecruiters, Workable, Rippling, Getro/Consider-powered boards.
- Big tech: use their public careers search pages or APIs where permitted, politely rate-limited and respecting robots.txt; if blocked, fall back to listing the company with a direct search link for me.
- Hacker News monthly "Who is hiring" threads via the public HN Algolia API; parse for my target roles, locations, and visa mentions.
- Aggregator APIs where I provide keys (e.g., Adzuna, JSearch).
- Manual import: a "Paste links" box and CSV upload so I can add jobs I find on Wellfound (using its visa sponsorship filter), LinkedIn, or referrals; the tool fetches the posting from the company's own site/ATS where possible and scores it like any other job.
- Run daily; dedupe across sources; store full JD text, URL, ATS type, posted date, location, remote status, salary range, company stage/funding.
- Auto-exclude postings that state no sponsorship, require existing work authorization without sponsorship, are US-citizens-only, or require security clearance.

## Phase 3 — Match scoring
For each job, Claude returns structured JSON against the master resume:
- Track classification (which keyword-bank track fits), skills/tools overlap, domain fit, seniority fit, responsibilities overlap, hard-requirement gaps listed explicitly, location fit, salary fit
- Match Score 0–100. Show jobs with Match ≥ 70 by default; adjustable threshold in the UI.
- Final Priority = Match × sponsor weighting (Sponsor Score, or Startup Sponsor Likelihood for Unverified) × freshness × location boost (Chicago and remote highest) × company tier (big tech and Series B+ AI startups boosted).
- One-paragraph "why this fits / what's the risk" per job, including a sponsorship risk note.

## Phase 4 — Resume and cover letter tailoring
- For each shortlisted job, generate a tailored resume (DOCX + PDF) and a short cover letter, built by SELECTING from the master resume per the keyword-bank table.
- STRICT RULE: never add skills, tools, titles, employers, dates, or metrics not present in the master resume. Allowed: choosing variants, reordering, light rephrasing, mirroring JD terminology where it truthfully describes existing experience. Metrics stay exactly as written.
- Diff view showing every change versus the source bullets; flag any line that may overstate.
- ATS-friendly formatting: single column, standard headings, no tables/graphics.
- Version-control every tailored resume and link it to the application record.

## Phase 5 — Application assist (human-in-the-loop)
- "Apply Queue" in the dashboard: each card shows job, scores, sponsor status, tailored resume, cover letter, and Approve / Edit / Skip.
- On Approve: Playwright opens the application, pre-fills from a stored profile (contact info, links, work authorization answers, EEO answers I configure once), attaches the tailored resume, and pauses for my final review before submit.
- Optional auto-submit only for Greenhouse/Lever/Ashby, only for jobs I approved, only after I enable it in settings.
- Big tech portals and Workday-style sites: pre-fill only, never auto-submit.
- Never create accounts, solve CAPTCHAs, or submit without my approval.
- Pre-draft answers to screening questions ("Why this company?", sponsorship questions, salary expectations within $130K–$200K) for my review.
- Daily cap configurable (default 15). Max 2 applications per company per 30 days; for big tech, recommend the single best-fit role and warn me that some companies limit applications per period.

## Phase 6 — Referral and outreach layer
- For each high-priority job, suggest likely hiring-team roles to look for and draft a short personalized LinkedIn/email note for a referral or hiring manager (drafts only; I send them myself). For startups, include a founder-outreach draft variant.
- Flag Northeastern University and Motorola Solutions alumni connections as an angle when I add contacts.
- Track outreach status and follow-up dates.

## Phase 7 — Email tracking
- Gmail OAuth, read-only scope.
- Poll for emails from ATS domains and company domains in my applications.
- Claude classifies each: Application Received, In Review, Assessment, Recruiter Screen Request, Interview Scheduled, Rejection, Offer, Other.
- Auto-update the matching application's stage; surface low-confidence matches for me to confirm.
- Extract interview dates/times and recruiter names.

## Phase 8 — Pipeline dashboard
Stages: Discovered → Shortlisted → Tailored → Applied → In Review → Assessment → Recruiter Screen → Interviewing → Offer / Rejected / Ghosted (auto-mark Ghosted after 21 days of silence).
Show:
- Funnel with conversion rates between stages
- Applications per week vs. goal; response rate; interview rate
- Response-rate breakdowns by role track, company type (big tech / startup stage / established), Sponsor Score band vs. Unverified, location, source, and referral vs. cold, so I can see what works and double down
- Follow-up reminders (7 days after applying with no response; thank-you notes after interviews)
- 90-day countdown with weekly targets

## Phase 9 — Interview prep
When a job reaches Recruiter Screen or Interviewing, generate a prep pack: company summary (for startups: funding, investors, product, stage), likely questions for the role track, STAR stories mapped from my master-resume bullets and metrics, sponsorship conversation talking points (H-1B transfer timing, green card questions to ask), and salary data from LCA wage records for that company, title, and metro.

## Working rules
- Build Phase 1 first and show me sample output before continuing.
- Write tests for scoring, tailoring (including a test that fails if any metric, title, or tool not in the master resume appears in output), and email classification.
- Log every automated action.
- Keep all my data local; never send resume or email data anywhere except the Anthropic API calls needed for scoring, tailoring, and classification.