# Phase 9: BigQuery Usage Visualization — Ambitious Expansion Handoff

**Date:** 2026-03-24
**From:** productivity repo session
**To:** field-eng-skills repo (new home for this work going forward)

## What's Done

Phase 9 Plans 01-04 are complete. The foundation is solid:

- **Query factory** (`bigquery/scripts/queries.py`): product area mapping (40+ event types → ~12 W&B areas), power user queries with dim_users JOIN for server deployment identity resolution, account health with SFDC entitlement fields
- **External report** (`usage-report/templates/usage-report-external.html`): ECharts charts, W&B branding, positive AI narrative, customer-safe
- **Internal report** (`usage-report/templates/usage-report-internal.html`): power users with real names, account health grid, churn risk, candid AI narrative
- **Dashboard integration** (`customer-snapshot/templates/intelligence-dashboard.html`): ECharts Usage panel replacing CSS bars, wandb theme
- **Ecosystem wiring**: CLAUDE.md, skill-composition.md, credential-status, bigquery SKILL.md all updated

### Pipeline fixes applied (last session)
- Removed trend % arrows from KPI cards (misleading for complex usage shapes)
- Tracked hours: weekly sum not mean
- Radar normalized by unique_users (adoption breadth) not total_events
- Power users JOIN dim_users for server deployment identity resolution
- Collaboration/Weave area filtering for non-Weave customers
- SFDC entitlement enrichment (contracted seats override, Weave suppression, product family)

## What's Remaining (Plan 05 Task 2)

Visual verification checkpoint — open all three HTML templates in browser and confirm rendering. Minor template bugs may remain (see Known Issues below).

## Known Template Issues (from last verification pass)

1. Internal seat chart is bar chart, external is line — should be consistent
2. External radar shape may look odd for accounts with extreme Artifacts adoption
3. Product area radar doesn't indicate its time period

## The Ambitious Expansion

Current reports are "a fancier spreadsheet" — aggregate charts barely touching the BQ data. The `ext_daily_user_event_usage` table alone has 96 columns with per-user, per-event, per-day granularity across 100+ tables.

### 8 Expansion Directions

1. **User journey analysis** — adoption ladder from first-run to multi-product. `dim_users` has `first_run_at`, `first_sweep_at`, `first_artifact_created_date`, `first_report_created_date`, `first_table_created_at`. Build Sankey or funnel showing how users progress through product adoption stages.

2. **Cohort analysis** — new vs established user adoption speed. Retention tables exist: `agg_weekly_user_retention_features`, `agg_weekly_user_returning_active_status`, `fct_user_activity_dates`. Compare how quickly new users adopt features vs established users.

3. **Engagement decay** — named users going cold, week-over-week drop-offs. Per-user daily data means we can detect individual disengagement before account-level metrics show it. Alert on "this person used to be active and stopped."

4. **Feature velocity** — per-product-area acceleration/deceleration. Time-series of product area adoption rates. Are Experiments growing while Sweeps decline? Which products are gaining momentum?

5. **Team/cluster detection** — which teams use what. `ext_daily_user_event_usage` has `is_part_of_team`, `count_teams`, `org_name`. Group users into teams and show per-team product adoption patterns.

6. **Per-user risk scoring** — individual engagement signals beyond account-level churn. `renewal_predictions` table has ML-scored churn probability at 3mo and 5mo horizons. Revenue signals: `is_churn`, `is_contraction`, `arr_walk`, `mrr_walk`.

7. **Usage correlation** — which product combos predict retention/expansion. If users who adopt Artifacts + Sweeps have 90% retention vs 60% for Artifacts-only, that's actionable intelligence for SEs.

8. **Operational/performance layer** — API latency, chart load, artifact perf, SDK versions. Datadog weekly/monthly instance reports exist (PDF samples seen). `cli_version`, `local_version` per user per day in BQ. May also be BQ tables with perf data.

### Key Data Already Discovered

| Table | What it has |
|-------|-------------|
| `dim_users` | Adoption timeline (`first_run_at`, `first_sweep_at`, etc.), `local_username`, `local_user_email`, `universal_user_id` |
| `ext_daily_user_event_usage` | Per-user per-day events, team fields (`is_part_of_team`, `count_teams`, `org_name`), SDK versions (`cli_version`, `local_version`) |
| `agg_weekly_user_retention_features` | Weekly retention metrics |
| `agg_weekly_user_returning_active_status` | Returning/active status per user |
| `fct_user_activity_dates` | User activity date ranges |
| `renewal_predictions` | ML churn scores at 3mo/5mo (in `landing_development` dataset) |
| `stg_salesforce_accounts` | Revenue signals: `is_churn`, `is_contraction`, `arr_walk`, `mrr_walk`, entitlements |

### Architecture Decision Needed

How to chunk this: each direction could be a new query module in `bigquery/scripts/` and a new report section/page. Options:
- **A. Extend existing reports** — add sections to external/internal templates
- **B. New report types** — separate "deep dive" reports per direction
- **C. Interactive dashboard** — single page with tabs/drill-down per direction
- **Hybrid** — key KPIs in existing reports, deep dives as separate artifacts

### Technical Notes

- BigQuery job project: `wandb-sa-sandbox` (user doesn't have serviceUsageConsumer on wandb-production)
- ADC quota project must be set: `gcloud auth application-default set-quota-project wandb-sa-sandbox`
- Server deployments (e.g. Isomorphic Labs, GResearch) need dim_users JOIN for identity — no cloud usernames in BQ
- Weave suppression: when `weave_customer=False`, filter out Weave sections and product areas

## How to Continue

Start a new GSD project or discussion in this repo:

```
/gsd:discuss-phase 9
```

Or freeform — the 8 directions above are the starting point for scoping which to prototype first.

## Repo Relationship

- **field-eng-skills** (`~/gitstuff/field-eng-skills`): Now the primary home for all W&B SE skills. Do new work here.
- **productivity** (`~/gitstuff/productivity`): Personal productivity wrapper. Has GSD planning state, personal memory, demo files. Skills here may go stale — field-eng-skills is source of truth going forward.
- Credentials remain at `~/.tsm-ai/.env` (shared by both repos).
