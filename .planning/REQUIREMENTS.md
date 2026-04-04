# Requirements: v2.0 Dashboard Integration + Skill Consolidation

**Defined:** 2026-04-03
**Core Value:** Give SEs named-user, team-level, and trend-aware intelligence for specific, data-driven customer conversations -- and make this toolkit usable by any W&B SE.

## Panel Integration

- [x] **PANEL-01**: SE can view cohort retention heatmap as a dashboard panel showing new vs established user retention by cohort month
- [x] **PANEL-02**: SE can view risk scoring as a dashboard panel showing composite churn risk gauge, factor breakdown, and trend line
- [x] **PANEL-03**: SE can view team detection as a dashboard panel showing team breakdown, per-team activity, and adoption patterns
- [x] **PANEL-04**: SE can view user journey as a dashboard panel showing adoption funnel/Sankey from first activity through product stages
- [x] **PANEL-05**: SE can view engagement decay as a dashboard panel showing cold-detection table ranking users by activity decline
- [x] **PANEL-06**: SE can view feature velocity as a dashboard panel showing sparkline grid of monthly events per product area with momentum indicators
- [x] **PANEL-07**: SE can view SDK version distribution as a dashboard panel showing version freshness, distribution donut, and upgrade recommendations
- [x] **PANEL-08**: SE can view usage correlation as a dashboard panel showing product combination heatmap with SE-internal privacy controls
- [x] **PANEL-09**: SE can view performance metrics as a dashboard panel showing performance index and latency breakdown (graceful empty state if data unavailable)
- [x] **PANEL-10**: All 9 new panels follow the existing panel contract (PanelRegistry.register, getHeadlineStats, getAttentionItems) and render in the v2 dashboard shell

## Jira Migration

- [x] **JIRA-01**: All Jira skill scripts connect to coreweave.atlassian.net instead of wandb.atlassian.net
- [ ] **JIRA-02**: Existing JQL filters and customer queries return correct results on the new instance
- [x] **JIRA-03**: Issue URLs in dashboards and FE-UPDATE comments point to coreweave.atlassian.net/browse/WB-XXXX
- [x] **JIRA-04**: CLAUDE.md, atlassian.md rules, and credential table updated to reference new instance
- [x] **JIRA-05**: All downstream skills that consume Jira data (customer-snapshot, jira-check, cadence-prep, pre-read, 3p-update) produce correct output after migration

## Skill Audit

- [x] **AUDIT-01**: Skill inventory published -- complete list of all skills with one-line descriptions, entry-point vs building-block classification, and dependency graph
- [x] **AUDIT-02**: No hardcoded user-specific values (GIDs, channel IDs, email addresses) exist in committed skill code -- all user-specific config lives in customers.yaml or ~/.tsm-ai/.env
- [x] **AUDIT-03**: Every skill's SKILL.md has accurate, up-to-date documentation that matches current behavior
- [x] **AUDIT-04**: Skill composition rules (skill-composition.md) are complete and cover all multi-skill workflows

## Documentation

- [ ] **DOCS-01**: Getting-started guide exists in the repo explaining: what this repo is, how to install, how to set up credentials, and how to run first skill
- [ ] **DOCS-02**: Skill reference page lists all skills grouped by category (data sources, dashboards, workflows, utilities) with usage examples
- [ ] **DOCS-03**: Customer onboarding guide explains how to add a new customer (customers.yaml, Asana setup, Slack channels, SFDC mapping)
- [ ] **DOCS-04**: Architecture overview explains the dashboard pipeline (fetch -> assemble -> compose -> open) and how panels work

## Future Requirements (deferred beyond v2.0)

- Automated scheduling of dashboard refreshes
- Slack bot integration for on-demand snapshots
- Cross-customer portfolio dashboard view
- Weave-specific analytics panel

## Out of Scope

- Merging setup skills into parent skills -- keeps context lean, setup is rarely invoked
- Rewriting existing BQ transforms -- they work, just need panel wrappers
- Building new analytics dimensions beyond the existing 9

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| JIRA-01 | Phase 7 | Complete |
| JIRA-02 | Phase 7 | Pending |
| JIRA-03 | Phase 7 | Complete |
| JIRA-04 | Phase 7 | Complete |
| JIRA-05 | Phase 7 | Complete |
| PANEL-01 | Phase 8 | Complete |
| PANEL-02 | Phase 8 | Complete |
| PANEL-03 | Phase 8 | Complete |
| PANEL-04 | Phase 8 | Complete |
| PANEL-05 | Phase 8 | Complete |
| PANEL-06 | Phase 8 | Complete |
| PANEL-07 | Phase 8 | Complete |
| PANEL-08 | Phase 8 | Complete |
| PANEL-09 | Phase 8 | Complete |
| PANEL-10 | Phase 8 | Complete |
| AUDIT-01 | Phase 9 | Complete |
| AUDIT-02 | Phase 9 | Complete |
| AUDIT-03 | Phase 9 | Complete |
| AUDIT-04 | Phase 9 | Complete |
| DOCS-01 | Phase 10 | Pending |
| DOCS-02 | Phase 10 | Pending |
| DOCS-03 | Phase 10 | Pending |
| DOCS-04 | Phase 10 | Pending |
