# W&B Field Engineering Skills

## What This Is

A comprehensive toolkit of Claude Code skills that help W&B Solutions Engineers manage customer relationships, track engineering issues, generate data-driven intelligence dashboards, and prepare for customer meetings. Includes a modular customer intelligence dashboard with BQ analytics, Jira/Slack/Asana integration, and 35 specialized skills.

## Core Value

Give SEs named-user, team-level, and trend-aware intelligence so they can have specific, data-driven conversations with customers instead of generic "usage is growing/declining" narratives — while automating the operational overhead of customer management.

## Current State

**Shipped:** v1.0 BQ Deep Analytics (2026-04-01), v2.0 Dashboard Integration + Skill Consolidation (2026-04-04)

The repo is usable by any W&B SE. All 9 analytics dimensions are integrated as dashboard panels, 35 skills are documented with consistent SKILL.md format, Jira migrated to coreweave.atlassian.net, credential storage standardized at `~/.fe-skills/.env`, and README.md serves as a single getting-started guide with architecture overview.

## Requirements

### Validated (v1.0 + v2.0)

- [x] 9 deep-analytics page types — transforms, BQ queries, and handlers for all 9 analytical dimensions — v1.0
- [x] Modular dashboard — shell + panel registry + compose.py producing folder-based dashboards — v1.0
- [x] 15 dashboard panels — 6 operational + 9 analytics, all following PanelRegistry contract — v2.0
- [x] Deterministic pipeline — assemble.py → compose.py → dashboard folder — v1.0
- [x] BQ usage data — seat utilization, product adoption, Weave ingestion, tracked hours, account health — v1.0
- [x] Jira integration — migrated to coreweave.atlassian.net, issue analysis with health buckets — v2.0
- [x] Slack sentiment analysis — channel history fetch and structured scoring — v1.0
- [x] Asana action tracking — portfolio structure with Actions + RAID projects per customer — v1.0
- [x] 35 skills documented — SKILL-INVENTORY.md, standardized SKILL.md format, no hardcoded values — v2.0
- [x] Composition rules — 15 multi-skill workflows in skill-composition.md — v2.0
- [x] Documentation — README.md as single front door (Quick Start, Skills, Onboarding, Architecture) — v2.0

### Active

(No active milestone — run `/gsd:new-milestone` to start one)

### Out of Scope

- Real-time dashboards or live-updating pages — point-in-time reports generated on demand
- Automated alerting or notification systems — visualization artifacts, not monitoring
- Cross-customer benchmarking visible to customers — correlation analysis is SE-internal only

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
| Separate pages per direction (not tabs in existing reports) | Enables parallel prototyping with subagents, each page is independently deployable and testable | ✓ Good |
| All 9 directions in scope for v1 | User wants full query + render pipeline for all directions | ✓ Good |
| Split direction 8 into SDK Versions (8a) + Performance (8b) | SDK versions are high-confidence BQ data, performance is exploratory Datadog territory | ✓ Good |
| Self-contained HTML with ECharts | Consistent with existing report ecosystem, no server dependency | ✓ Good |
| Credential path ~/.fe-skills/.env | Replaced legacy ~/.tsm-ai/ — meaningful name for new SEs | ✓ Good — v2.0 |
| Single README as front door | All docs in one file, no docs/ folder scatter | ✓ Good — v2.0 |
| assemble.py uses deep-analytics venv | Only venv with pandas + BQ deps needed for transforms | ✓ Good — v2.0 |

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
*Last updated: 2026-04-04 — v2.0 milestone completed*
