# BQ Deep Analytics — Usage Intelligence Expansion

## What This Is

A suite of 9 standalone deep-analytics HTML pages that transform raw BigQuery usage data into actionable intelligence for W&B Solutions Engineers. Each page targets a specific analytical dimension — from user adoption journeys to churn risk scoring — going far beyond the aggregate charts in the existing usage reports. Built on top of the existing BQ query factory and ECharts report ecosystem in field-eng-skills.

## Core Value

Give SEs named-user, team-level, and trend-aware intelligence so they can have specific, data-driven conversations with customers instead of generic "usage is growing/declining" narratives.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] User Journey Analysis — adoption funnel/Sankey from dim_users first_*_at fields showing per-user progression through W&B product stages
- [ ] Cohort Analysis — new vs established user retention comparison using retention tables, cohort heatmaps
- [ ] Engagement Decay — individual user cold-detection with week-over-week drop-off alerting from daily event data
- [ ] Feature Velocity — per-product-area time-series showing acceleration/deceleration trends with sparklines and momentum indicators
- [ ] Team/Cluster Detection — group users by team fields (is_part_of_team, count_teams, org_name) and show per-team adoption patterns
- [ ] Per-User Risk Scoring — combine renewal_predictions ML churn scores with engagement signals and revenue trends (arr_walk, mrr_walk)
- [ ] Usage Correlation — cross-account analysis of which product combos predict retention/expansion, "next best action" recommendations
- [ ] SDK Version Distribution — cli_version and local_version distribution per customer, version freshness, upgrade recommendations
- [ ] Performance Deep Dive — Datadog-sourced performance signals, narrative-driven analysis of API latency, chart load, artifact perf

### Out of Scope

- Modifying existing external/internal report templates — these pages are additive, not replacement
- Real-time dashboards or live-updating pages — these are point-in-time reports generated on demand
- Cross-customer benchmarking visible to customers — correlation analysis is SE-internal only
- Automated alerting or notification systems — these are visualization artifacts, not monitoring tools

## Context

### Existing Foundation (Phase 9, Plans 01-04 complete)

- **Query factory** (`bigquery/scripts/queries.py`): product area mapping (40+ event types → ~12 W&B areas), power user queries with dim_users JOIN, account health with SFDC entitlement fields
- **External report** (`usage-report/templates/usage-report-external.html`): ECharts, W&B branding, positive AI narrative
- **Internal report** (`usage-report/templates/usage-report-internal.html`): power users with real names, churn risk, candid AI narrative
- **Dashboard integration** (`customer-snapshot/templates/intelligence-dashboard.html`): ECharts Usage panel
- **Ecosystem wiring**: CLAUDE.md, skill-composition.md, credential-status, bigquery SKILL.md all updated

### Key BQ Tables

| Table | Dataset | What it has |
|-------|---------|-------------|
| `dim_users` | analytics | Adoption timeline (first_run_at, first_sweep_at, etc.), local_username, local_user_email, universal_user_id |
| `ext_daily_user_event_usage` | analytics | Per-user per-day events, team fields (is_part_of_team, count_teams, org_name), SDK versions (cli_version, local_version) |
| `agg_weekly_user_retention_features` | analytics | Weekly retention metrics |
| `agg_weekly_user_returning_active_status` | analytics | Returning/active status per user |
| `fct_user_activity_dates` | analytics | User activity date ranges |
| `renewal_predictions` | landing_development | ML churn scores at 3mo/5mo |
| `stg_salesforce_accounts` | analytics | Revenue signals: is_churn, is_contraction, arr_walk, mrr_walk, entitlements |

### Technical Environment

- BigQuery job project: `wandb-sa-sandbox` (no serviceUsageConsumer on wandb-production)
- ADC quota project: `gcloud auth application-default set-quota-project wandb-sa-sandbox`
- Server deployments need dim_users JOIN for identity — no cloud usernames in BQ
- Weave suppression: when weave_customer=False, filter out Weave sections
- Python skills use `uv run --project .claude/skills/<skill>` for dependency isolation
- HTML reports are self-contained, ECharts via CDN, W&B branding conventions from existing templates

### Data Confidence by Direction

| Direction | Data Confidence | Notes |
|-----------|----------------|-------|
| User Journey | High | dim_users first_*_at fields confirmed |
| Cohort | Medium | Retention tables exist, schema needs exploration |
| Engagement Decay | High | ext_daily_user_event_usage per-user daily data |
| Feature Velocity | High | Extension of existing product area queries |
| Team Detection | Medium | Team fields may not be populated for all accounts |
| Risk Scoring | Medium | renewal_predictions in different dataset (landing_development) |
| Usage Correlation | Medium | Cross-account queries, privacy considerations |
| SDK Versions | High | cli_version, local_version in BQ confirmed |
| Performance | Low | Datadog PDFs not queryable, BQ perf tables unknown |

## Constraints

- **BQ Access**: Job project is wandb-sa-sandbox, not wandb-production — query permissions may differ per dataset
- **Data Availability**: renewal_predictions (landing_development dataset) and team fields may not exist for all accounts
- **Server Deployments**: No cloud usernames — must use dim_users JOIN for identity resolution
- **Self-contained HTML**: Each page must work as a standalone file (ECharts CDN, inline CSS/JS, no server)
- **Privacy**: Cross-account correlation data must remain SE-internal, never customer-facing

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Separate pages per direction (not tabs in existing reports) | Enables parallel prototyping with subagents, each page is independently deployable and testable | — Pending |
| All 9 directions in scope for v1 | User wants full query + render pipeline for all directions | — Pending |
| Split direction 8 into SDK Versions (8a) + Performance (8b) | SDK versions are high-confidence BQ data, performance is exploratory Datadog territory | — Pending |
| Self-contained HTML with ECharts | Consistent with existing report ecosystem, no server dependency | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-24 after initialization*
