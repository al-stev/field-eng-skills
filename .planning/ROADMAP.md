# Roadmap: BQ Deep Analytics

## Overview

Deliver 9 standalone deep-analytics HTML pages that give W&B Solutions Engineers named-user, team-level, and trend-aware intelligence from BigQuery data. The build progresses from shared infrastructure through high-confidence pages (proving the pipeline), medium-confidence pages (validating new data sources), and finally privacy-sensitive and exploratory pages. Each page is independently deployable as self-contained HTML with ECharts, following the established W&B design system.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation and Template System** - Skill scaffolding, shared utilities, cost guardrails, design system, and the cross-cutting HTML template contract that all 9 pages inherit
- [ ] **Phase 2: High-Confidence Pages** - Four pages with proven data sources (User Journey, Engagement Decay, Feature Velocity, SDK Versions) built in parallel to validate the full generation pipeline
- [ ] **Phase 3: Medium-Confidence Pages** - Three pages requiring schema validation before development (Cohort Analysis, Team Detection, Risk Scoring)
- [ ] **Phase 4: Privacy-Sensitive and Exploratory Pages** - Cross-account correlation with privacy controls (Usage Correlation) and low-confidence data exploration (Performance Deep Dive)
- [ ] **Phase 5: Dashboard V2 — Modular Folder-Based Architecture** - Replace the monolithic intelligence-dashboard.html with a folder-based dashboard (shell + panel JS files + data.js) that scales to 15-20+ panels with per-panel agent editing, Google Drive multi-user access, and prototype-quality visualizations

## Phase Details

### Phase 1: Foundation and Template System
**Goal**: SE can run the deep-analytics skill and it produces a valid, empty-state HTML page with the full W&B design system, cost-guarded BQ queries, and schema validation -- ready for page-specific content
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05, XCUT-01, XCUT-02, XCUT-03, XCUT-04, XCUT-05, XCUT-06, XCUT-07, XCUT-08, XCUT-09, XCUT-10, XCUT-11
**Success Criteria** (what must be TRUE):
  1. SE can run `uv run --project .claude/skills/deep-analytics python .claude/skills/deep-analytics/scripts/generate.py --customer <name> --page <type>` and it produces a self-contained HTML file in `customers/<name>/analytics/`
  2. Generated HTML displays W&B branding (Instrument Serif, Outfit, JetBrains Mono, gold accent, noise texture), respects dark/light mode via CSS media query, and includes ECharts CDN -- matching existing report design language
  3. Every BQ query executed has `maximum_bytes_billed` set, bytes-processed is logged to stdout, and the schema validation utility confirms table existence and required columns before any query runs
  4. The shared identity resolution CTE for dim_users JOIN is available as a reusable utility and handles NULL username/email for server deployments
  5. Template includes all cross-cutting elements: AI narrative section, KPI headline row, date range header, interactive tooltips, print readiness (saveAsImage toolbox), copy-to-clipboard for narrative text, and linked navigation placeholder -- all rendering graceful empty states when no data is present
**Plans**: 4 plans
Plans:
- [x] 01-01-PLAN.md -- BQ cost guardrails and identity resolution CTE
- [x] 01-02-PLAN.md -- Skill directory scaffolding, CLI orchestrator, schema validator
- [x] 01-03-PLAN.md -- Foundation HTML template with all XCUT features
- [ ] 01-04-PLAN.md -- End-to-end wiring, integration tests, visual verification
**UI hint**: yes

### Phase 2: High-Confidence Pages
**Goal**: SEs have four fully functional analytical pages -- User Journey, Engagement Decay, Feature Velocity, and SDK Versions -- each delivering actionable per-user and per-feature intelligence from proven BQ data sources
**Depends on**: Phase 1
**Requirements**: JOUR-01, JOUR-02, JOUR-03, JOUR-04, JOUR-05, JOUR-06, JOUR-07, JOUR-08, DCAY-01, DCAY-02, DCAY-03, DCAY-04, DCAY-05, DCAY-06, DCAY-07, VELC-01, VELC-02, VELC-03, VELC-04, VELC-05, VELC-06, VELC-07, SDKV-01, SDKV-02, SDKV-03, SDKV-04, SDKV-05, SDKV-06, SDKV-07
**Success Criteria** (what must be TRUE):
  1. User Journey page shows a Sankey diagram of product adoption flow, stage completion counts, median time-between-stages, never-reached breakdown, per-user drill-down table, timeline view, and ML maturity score -- with AI narrative interpreting the patterns
  2. Engagement Decay page shows a cold-detection table ranking users by activity decline, days-since-last-activity histogram, account engagement trend line, per-user sparklines, decay severity color coding, and champion risk badges -- with AI narrative identifying cold users and their importance
  3. Feature Velocity page shows a sparkline grid of monthly events per product area, momentum indicators, unique users trend alongside event volume, acceleration heatmap, create-vs-view ratios, and cross-area correlation -- with AI narrative on acceleration/deceleration patterns
  4. SDK Versions page shows a version distribution donut, freshness assessment, user-to-version table, version trend stacked area, library usage breakdown, and exportable upgrade list -- with AI narrative and upgrade recommendations
  5. All four pages render correctly for a real customer, handle server deployments (identity resolution), and produce HTML files under 2MB
**Plans**: TBD
**UI hint**: yes

### Phase 3: Medium-Confidence Pages
**Goal**: SEs have three analytical pages -- Cohort Analysis, Team Detection, and Risk Scoring -- that unlock retention intelligence, organizational structure visibility, and composite churn risk assessment from data sources validated during this phase
**Depends on**: Phase 2
**Requirements**: CHRT-01, CHRT-02, CHRT-03, CHRT-04, CHRT-05, CHRT-06, CHRT-07, TEAM-01, TEAM-02, TEAM-03, TEAM-04, TEAM-05, TEAM-06, TEAM-07, TEAM-08, RISK-01, RISK-02, RISK-03, RISK-04, RISK-05, RISK-06, RISK-07, RISK-08
**Success Criteria** (what must be TRUE):
  1. Cohort Analysis page shows a retention heatmap with cohort size labels, overall retention curve, new/retained/resurrected/churned stacked area lifecycle chart, and cohort-over-cohort trend overlay -- with AI narrative on cohort health
  2. Team Detection page shows team breakdown table with member counts and activity, per-team activity bar chart, team-by-product-area heatmap, team adoption timeline, per-team champion identification, and team growth/contraction trend -- gracefully displaying "Team data unavailable" when fields are not populated
  3. Risk Scoring page shows composite risk gauge (0-100), risk factor breakdown, risk trend line over 6 months, renewal context alongside score, risk radar chart, and AI-generated action recommendations -- with staleness banner when churn model data is old
  4. Schema validation runs successfully for `agg_weekly_user_retention_features`, team fields in `ext_daily_user_event_usage`, and `renewal_predictions` in `landing_development` before page development begins
**Plans**: 4 plans
Plans:
- [x] 03-01-PLAN.md -- Phase 3 BQ queries and schema validation specs
- [x] 03-02-PLAN.md -- Cohort Analysis page (transform + handler + renderer)
- [x] 03-03-PLAN.md -- Team Detection page (transform + handler + renderer)
- [x] 03-04-PLAN.md -- Risk Scoring page (transform + handler + renderer)
**UI hint**: yes

### Phase 4: Privacy-Sensitive and Exploratory Pages
**Goal**: SEs have two final analytical pages -- Usage Correlation (SE-internal cross-account intelligence) and Performance Deep Dive (application performance signals) -- completing the full 9-page deep analytics suite
**Depends on**: Phase 3
**Requirements**: CORR-01, CORR-02, CORR-03, CORR-04, CORR-05, CORR-06, CORR-07, CORR-08, PERF-01, PERF-02, PERF-03, PERF-04, PERF-05, PERF-06
**Success Criteria** (what must be TRUE):
  1. Usage Correlation page shows product combination heatmap with retention rates, current account positioning against aggregate patterns, next-best-action recommendations, expansion signal indicators, anonymized peer benchmarking, and ARR-usage scatter -- all from pre-aggregated data with minimum 10-account cohort enforcement
  2. Usage Correlation page displays a prominent "SE-Internal Only" privacy badge and never embeds individual account names or IDs in the output HTML
  3. Performance Deep Dive page shows performance index gauge, per-feature slowness breakdown, error metrics KPI cards, chart load latency distribution, and slow chart load user breakdown -- with AI narrative flagging areas of concern (or the page is gracefully descoped if `fct_application_performance` data proves insufficient)
  4. All 9 deep analytics pages are discoverable via linked navigation between related pages, and the full suite generates successfully for at least one real customer
**Plans**: 3 plans
Plans:
- [x] 04-01-PLAN.md -- BQ queries (cross-account + performance), PRODUCT_AREA_CASE extraction, schema validation specs
- [x] 04-02-PLAN.md -- Usage Correlation page (transform + handler + renderer with privacy controls)
- [x] 04-03-PLAN.md -- Performance Deep Dive page (transform + handler + renderer with go/no-go gate)
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation and Template System | 0/4 | Planning complete | - |
| 2. High-Confidence Pages | 0/TBD | Not started | - |
| 3. Medium-Confidence Pages | 0/4 | Planning complete | - |
| 4. Privacy-Sensitive and Exploratory Pages | 0/3 | Planning complete | - |
| 5. Dashboard V2 — Modular Folder-Based Architecture | 0/6 | Planning complete | - |

### Phase 5: Dashboard V2 — Modular Folder-Based Architecture
**Goal**: Replace the monolithic 3700-line intelligence-dashboard.html with a modular, folder-based dashboard that scales to 15-20+ panels, supports Google Drive multi-user access, enables per-panel agent editing, and is delightful during cadence calls and QBR screenshares
**Depends on**: Phase 4
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06, DASH-07, DASH-08, DASH-09, DASH-10, DASH-11, DASH-12
**Success Criteria** (what must be TRUE):
  1. Running `/customer-snapshot CustomerName` produces a `customers/<name>/dashboard/` folder with `index.html` shell, `data.js`, panel JS files, and bundled lib/ — all working from file:// protocol with no server
  2. Shell provides sidebar navigation (56px icon-only default, 220px expanded), URL hash routing (#overview, #issues, etc.), panel-on-demand loading, keyboard shortcuts (1-6 panel jump), and CSS crossfade transitions
  3. Panel registry enforces a contract: every panel JS calls `PanelRegistry.register()` with `id`, `render()`, `getHeadlineStats()`, and `getAttentionItems()` — shell auto-discovers and renders panels from manifest
  4. Support Tickets panel matches prototype quality: headline stats strip, monthly volume trend, concern treemap, age scatter plot with Jira links, submitter stacked bars with sparklines and heatmap — not basic bars
  5. Actions, Usage, Slack, and Issues panels extracted from v1 monolith into individual JS files, each under 800 lines, rendering identically to v1 within the v2 shell
  6. Overview panel aggregates `getHeadlineStats()` and `getAttentionItems()` from all panels, shows changes-since-last-generation diff, and agent-generated narrative insights
  7. `compose.py` assembles templates + data into dashboard folder, only including panels that have data, writing `data.js` with dated history snapshots
  8. Delight features: ambient tab indicators (customer name + stale count), contextual right-click (open in Jira/Slack), panel transitions
**Plans**: 6 plans
Plans:
- [ ] 05-01-PLAN.md -- Infrastructure: shell.html, panel-registry.js, chart-helpers.js, panels.yaml, compose.py
- [ ] 05-02-PLAN.md -- Support Tickets panel (new, from prototypes, 5 ECharts visualizations)
- [ ] 05-03-PLAN.md -- Actions + Slack panel extraction from v1 monolith
- [ ] 05-04-PLAN.md -- Usage panel extraction from v1 monolith (4 ECharts charts + health grid)
- [ ] 05-05-PLAN.md -- Issues panel extraction from v1 monolith (filters, themes, analytics)
- [ ] 05-06-PLAN.md -- Overview panel + delight features + final verification
**UI hint**: yes
