# Skill Composition Workflows

Named multi-skill workflows for common W&B SE operations. Each workflow lists skills in recommended order. Steps can be skipped or reordered based on context — these are starting patterns, not rigid scripts.

## Issue Triage

Investigate a customer-reported issue from initial report through resolution tracking.

1. **slack** — Search channel history for the complaint or thread context. Read the full thread if referenced.
2. **jira** — Search for related issues in the WB project by customer name or keyword. Check for existing bugs or feature requests.
3. **slack** — Post findings in the customer's channel (internal or external). Reply in the original thread.
4. **jira** — Create or update a Bug/Feature Request with FE-UPDATE comment to track the issue.

## Customer Lookup

Build a picture of a customer's issue landscape and current engagement state.

0. **salesforce** — Query SFDC for account-level data (ARR, tier, contract dates, account team). Use `accounts.py account-detail --account-id <ID>` for full account context before diving into issues and channels.
1. **jira** — Search WB project issues by customer name (`"Customer" = "CustomerName"`). List open bugs and feature requests to understand current workstreams.
2. **slack** — Search `#ext-*` and `#supp-*` channels for recent customer activity. Look for unresolved threads.
3. **confluence** — Check for existing customer documentation or knowledge base articles.

## Customer Snapshot

Generate a v2 modular intelligence dashboard summarizing a customer's Jira issues, Slack sentiment, Asana actions, BigQuery usage metrics, deep-analytics panels, and executive summary. Triggered by `/customer-snapshot CustomerName`.

1. **jira** — Pull all open issues for the customer with comment metadata (`issues.py list --customer X --with-comments`). Provides issue health buckets, attention callouts, response cadence, and FE-UPDATE tracking.
2. **asana** — Fetch SE action tasks from the customer's Asana project (if configured). Computes overdue, stale, and section-based summary counts.
3. **bigquery** — Fetch usage data from BigQuery if sfdc_account_id is configured. Provides seat utilization, Weave ingestion, tracked hours, account health, product areas, and power users.
4. **slack** — Fetch channel history for sentiment analysis. Claude scores overall tone, identifies hot threads, and produces structured sentiment JSON.
5. **customer-snapshot (assemble.py)** — Deterministic assembler: accepts Jira, BQ, Asana, and sentiment JSON files, applies component/parent normalization, theme clustering, trending metrics computation, Asana task transformation, and runs all 9 deep-analytics transforms (cohort, risk, team, journey, decay, velocity, SDK, correlation, performance) via BigQuery.
6. **customer-snapshot (compose.py)** — Reads panels.yaml manifest, determines active panels based on data availability, assembles dashboard folder: copies shell.html template, generates panel JS files, writes data.js with INTELLIGENCE_DATA, archives previous snapshots to history/, bundles lib/ (ECharts, chart-helpers, panel-registry).
7. Output: `customers/<name>/dashboard/` folder with index.html, data.js, panels/ JS files, lib/, history/ — opens in browser from file:// protocol. Includes up to 15 panels (6 operational + 9 analytics) when BQ data is available.

## Communication Prep

Prepare for a customer meeting or email update by gathering current context.

1. **slack** — Read recent messages in the customer's `#ext-*` and `#supp-*` channels. Look for unresolved threads or new issues since the last meeting.
2. **jira** — Check the customer's open issues for status updates to report. Note any blocked or overdue items. Review recent FE-UPDATE comments.
3. **confluence** — Check for relevant documentation or meeting notes.
4. **bigquery** — Optionally pull usage stats for data-driven talking points (seat adoption trends, Weave ingestion).
5. **gcalendar** — Check upcoming calendar events for the customer (meeting times, attendees, recurrence).
6. **gmail** — Search for recent email threads with the customer for additional context.
7. **gong** — Review recent call recordings and AI summaries for conversation continuity.

## FE-UPDATE Workflow

The "pull view, notice stale, trigger update" pattern for keeping Jira issues current.

1. **jira** — Pull customer issues, identify those with stale or missing FE-UPDATE comments.
2. **slack** — Follow linked Slack thread URLs from Jira issues. Summarize new activity since last update.
3. **jira** — Post FE-UPDATE formatted comments with source citations and updated status/dates.

## Action Tracking

Manage SE actions for a customer -- create tasks from Slack conversations, track progress, update status.

1. **slack** — Read the Slack thread or conversation that needs action tracking.
2. **jira** — Check if there's a related Jira issue (search by keywords or issue key mentioned in thread).
3. **asana** — Create a task in the customer's Asana project with:
   - Description populated from Slack thread context
   - Linked Jira issue key in task name suffix (WB-XXXX)
   - Slack source URL in description
   - Priority and due date based on urgency
4. **asana** — Update task status as work progresses (move between sections).

## Programme Update

Generate a 3P (Progress, Plans, Problems) update for a customer or across all customers.

1. **3p-update** — Run the 3P generation skill which automatically:
   - Fetches Asana tasks (progress/plans)
   - Fetches Jira activity (progress/problems)
   - Fetches Slack signals (problems)
   - Synthesizes a concise 3P update
2. Optional: add `--confluence` flag to publish as a Confluence page.

## RAID Management

Manage RAID logs (Risks, Assumptions, Issues, Dependencies) across customer accounts. RAID is the management-visibility layer that sits above day-to-day SE actions.

1. **raid** — View current RAID log for a customer, scan for new items, or manually add items.
2. **asana** — Base operations: create/update/move/complete RAID tasks, multi-home between customer and RAID projects.
3. **jira** — Scan mode data source: open issues, stale items, FE-UPDATE status for Issue and Dependency detection.
4. **slack** — Scan mode data source: customer channel sentiment for Risk detection.

## Usage Report

Generate a standalone usage visualization for a customer from BigQuery data. Two report types available.

1. **bigquery** — Fetch all usage metrics (seats, Weave, tracked hours, account health, product areas, power users) for the customer.
2. **usage-report** — Generate self-contained HTML usage report with ECharts charts.
   - Default: external report (customer-facing, QBR-ready, W&B branded, positive AI narrative)
   - With `--internal`: full SE prep report (power users with real names, churn risk, candid AI narrative)
3. Output saved to `customers/<name>/usage/YYYY-MM-DD-usage-report.html` (external) or `customers/<name>/usage/YYYY-MM-DD-usage-report-internal.html` (internal).

## Weave Forecast

Project a customer's Weave ingestion forward against their contracted limit. Use when a customer's Weave usage is approaching the limit and you need to gauge whether a mid-term upsell is justified.

1. **bigquery** — Source layer. Provides `weave_daily_by_project_query`, `weave_monthly_query`, `weave_limit_query`, and `account_health_query` (the four queries the forecast script runs).
2. **salesforce** — Optional cross-check. Use to verify the contract end date, find in-flight Weave upsell opportunities, and surface the renewal opportunity for the year-after dialogue.
3. **weave-forecast** — Run `/weave-forecast <CustomerName>` (or `weave forecast for <CustomerName>`). Pulls daily Weave ingestion from `fct_weave_project_storage`, fits 3 mean-rate scenarios (180d / 90d / 30d windows), auto-detects stale-spike projects (≥5 GB lifetime, ≥7 days silent), computes limit-crossing dates per scenario, renders a self-contained ECharts HTML page with a "include all / exclude stale spikes" toggle.
4. Output saved to `customers/<name>/weave/YYYY-MM-DD-weave-forecast.html`. Internal-only — has an "INTERNAL · SE only" badge.

## Customer Onboarding

Set up a new customer's full structure across Asana, Confluence, and the customer registry.

1. **customer-setup** — Run `/customer-setup CustomerName` to orchestrate the full onboarding flow:
   - Queries Salesforce for account data
   - Prompts for Slack channels, cadence schedule, deployment type
   - Verifies Jira customer name mapping
   - Creates Asana portfolio + Actions project + RAID project
   - Creates Confluence pages (Meeting Notes, Ongoing Issues with live Jira macros, Feedback) under W&B EMEA Account Management
   - Writes everything to `templates/customers.yaml` including `confluence_pages` IDs
2. **asana** — Review created portfolio structure, adjust custom fields if needed.
3. **jira** — Verify issues appear correctly with the customer name mapping.
4. **customer-snapshot** — Generate first dashboard to verify all integrations work.

## Customer Silence Check

Monitor customer responsiveness on tracked threads.

1. **ghosted** — Scan "Waiting on Customer" tasks for unresponsive Slack threads (`/ghosted` or `/ghosted GResearch`).
2. **ghosted** — Track new threads: `/ghosted track <URL>` to start monitoring a thread.
3. **asana** — Move tasks back to active sections when customer responds.

## Meeting Follow-Up

Turn meeting notes into tracked actions, RAID items, Confluence meeting notes, and customer feedback — all from a single transcript paste.

1. **maction** — Extract action items, RAID signals, customer feedback, and meeting summary from notes (`/maction GResearch <notes>`). Creates Asana tasks, publishes meeting notes to Confluence, and captures feedback. All in one pass.
2. **asana** — Review and adjust created tasks (move sections, update priority, add details).
3. **raid** — Review RAID log after maction additions (`/raid GResearch`).
4. **confluence** — Meeting notes and feedback are published automatically by maction if `confluence_pages` is configured in customers.yaml. Manual edits via `/confluence`.

## Task Hygiene

Keep SE task backlog clean and current.

1. **nag** — Scan for overdue and stale tasks (`/nag`).
2. **asana** — Address flagged items: complete, reschedule, or move sections.
3. **ghosted** — Check customer silence on waiting items (`/ghosted`).

## Dashboard Generation

Generate a v2 modular dashboard for a customer with all available data panels. This is the deterministic pipeline behind `/customer-snapshot`.

1. **jira** — Fetch all open issues with comment metadata: `issues.py list --customer CustomerName --max-results 200 --with-comments`. Save JSON to temp file.
2. **bigquery** — Fetch usage metrics: `usage.py --customer CustomerName --format json`. Save JSON to temp file.
3. **asana** — Fetch SE action tasks from the customer's Asana project: `query.py tasks --project-gid <action_tracker_id> --limit 100 --pretty`. Save JSON to temp file.
4. **slack** — Fetch channel history for each configured channel. Claude analyzes messages and produces structured sentiment JSON. Save to temp file.
5. **customer-snapshot (assemble.py)** — Deterministic assembler that accepts `--jira`, `--bq`, `--asana`, `--sentiment` JSON file paths plus `--customer`, `--days`, `--months`, `--audience` flags. Applies component/parent normalization, theme clustering, trending metrics, Asana task transformation. Runs all 9 deep-analytics BigQuery transforms (user journey, cohort, engagement decay, team detection, feature velocity, SDK versions, usage correlation, risk scoring, performance). Outputs complete INTELLIGENCE_DATA JSON.
6. **customer-snapshot (compose.py)** — Dashboard folder composer that accepts `--customer`, `--data` (INTELLIGENCE_DATA JSON path), `--output` (target directory). Reads `panels.yaml` manifest to determine active panels based on data availability. Copies `shell.html` template, writes `data.js`, copies active panel JS files to `panels/`, bundles `lib/` (ECharts, chart-helpers, panel-registry), archives previous data.js to `history/`, computes diff against previous snapshot.
7. Output: `customers/<name>/dashboard/` folder with `index.html`, `data.js`, `panels/*.js`, `lib/`, `history/` — opens in browser from `file://` protocol.

