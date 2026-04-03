# Roadmap: W&B Field Engineering Skills

## Milestones

- v1.0 BQ Deep Analytics -- Phases 1-6 (shipped 2026-04-01)
- v2.0 Dashboard Integration + Skill Consolidation -- Phases 7-10 (in progress)

## Phases

<details>
<summary>v1.0 BQ Deep Analytics (Phases 1-6) -- SHIPPED 2026-04-01</summary>

- [x] **Phase 1: Foundation and Template System** - Skill scaffolding, shared utilities, cost guardrails, design system, and the cross-cutting HTML template contract that all 9 pages inherit (completed 2026-03-25)
- [x] **Phase 2: High-Confidence Pages** - Four page types (User Journey, Engagement Decay, Feature Velocity, SDK Versions) -- transforms and handlers built across phases 1, 3, 4; no separate execution phase needed (completed 2026-03-26)
- [x] **Phase 3: Medium-Confidence Pages** - Three pages requiring schema validation before development (Cohort Analysis, Team Detection, Risk Scoring) (completed 2026-03-26)
- [x] **Phase 4: Privacy-Sensitive and Exploratory Pages** - Cross-account correlation with privacy controls (Usage Correlation) and low-confidence data exploration (Performance Deep Dive) (completed 2026-03-27)
- [x] **Phase 5: Dashboard V2 -- Modular Folder-Based Architecture** - Replace the monolithic intelligence-dashboard.html with a folder-based dashboard (shell + panel JS files + data.js) that scales to 15-20+ panels (completed 2026-04-01)
- [x] **Phase 6: Dashboard V2 UX Polish** - Data provenance, split charts, navigation improvements, compose.py wiring (completed 2026-04-01)

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
- [x] 01-04-PLAN.md -- End-to-end wiring, integration tests, visual verification

### Phase 2: High-Confidence Pages
**Goal**: SEs have four fully functional analytical pages -- User Journey, Engagement Decay, Feature Velocity, and SDK Versions -- each delivering actionable per-user and per-feature intelligence from proven BQ data sources
**Depends on**: Phase 1
**Requirements**: JOUR-01 through JOUR-08, DCAY-01 through DCAY-07, VELC-01 through VELC-07, SDKV-01 through SDKV-07
**Success Criteria** (what must be TRUE):
  1. User Journey page shows a Sankey diagram of product adoption flow, stage completion counts, median time-between-stages, never-reached breakdown, per-user drill-down table, timeline view, and ML maturity score -- with AI narrative interpreting the patterns
  2. Engagement Decay page shows a cold-detection table ranking users by activity decline, days-since-last-activity histogram, account engagement trend line, per-user sparklines, decay severity color coding, and champion risk badges -- with AI narrative identifying cold users and their importance
  3. Feature Velocity page shows a sparkline grid of monthly events per product area, momentum indicators, unique users trend alongside event volume, acceleration heatmap, create-vs-view ratios, and cross-area correlation -- with AI narrative on acceleration/deceleration patterns
  4. SDK Versions page shows a version distribution donut, freshness assessment, user-to-version table, version trend stacked area, library usage breakdown, and exportable upgrade list -- with AI narrative and upgrade recommendations
  5. All four pages render correctly for a real customer, handle server deployments (identity resolution), and produce HTML files under 2MB
**Plans**: -- (merged into phases 1, 3, 4)

### Phase 3: Medium-Confidence Pages
**Goal**: SEs have three analytical pages -- Cohort Analysis, Team Detection, and Risk Scoring -- that unlock retention intelligence, organizational structure visibility, and composite churn risk assessment from data sources validated during this phase
**Depends on**: Phase 2
**Requirements**: CHRT-01 through CHRT-07, TEAM-01 through TEAM-08, RISK-01 through RISK-08
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

### Phase 4: Privacy-Sensitive and Exploratory Pages
**Goal**: SEs have two final analytical pages -- Usage Correlation (SE-internal cross-account intelligence) and Performance Deep Dive (application performance signals) -- completing the full 9-page deep analytics suite
**Depends on**: Phase 3
**Requirements**: CORR-01 through CORR-08, PERF-01 through PERF-06
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

### Phase 5: Dashboard V2 -- Modular Folder-Based Architecture
**Goal**: Replace the monolithic 3700-line intelligence-dashboard.html with a modular, folder-based dashboard that scales to 15-20+ panels, supports Google Drive multi-user access, enables per-panel agent editing, and is delightful during cadence calls and QBR screenshares
**Depends on**: Phase 4
**Requirements**: DASH-01 through DASH-12
**Success Criteria** (what must be TRUE):
  1. Running `/customer-snapshot CustomerName` produces a `customers/<name>/dashboard/` folder with `index.html` shell, `data.js`, panel JS files, and bundled lib/ -- all working from file:// protocol with no server
  2. Shell provides sidebar navigation (56px icon-only default, 220px expanded), URL hash routing (#overview, #issues, etc.), panel-on-demand loading, keyboard shortcuts (1-6 panel jump), and CSS crossfade transitions
  3. Panel registry enforces a contract: every panel JS calls `PanelRegistry.register()` with `id`, `render()`, `getHeadlineStats()`, and `getAttentionItems()` -- shell auto-discovers and renders panels from manifest
  4. Support Tickets panel matches prototype quality: headline stats strip, monthly volume trend, concern treemap, age scatter plot with Jira links, submitter stacked bars with sparklines and heatmap -- not basic bars
  5. Actions, Usage, Slack, and Issues panels extracted from v1 monolith into individual JS files, each under 800 lines, rendering identically to v1 within the v2 shell
  6. Overview panel aggregates `getHeadlineStats()` and `getAttentionItems()` from all panels, shows changes-since-last-generation diff, and agent-generated narrative insights
  7. `compose.py` assembles templates + data into dashboard folder, only including panels that have data, writing `data.js` with dated history snapshots
  8. Delight features: ambient tab indicators (customer name + stale count), contextual right-click (open in Jira/Slack), panel transitions
**Plans**: 6 plans
Plans:
- [x] 05-01-PLAN.md -- Infrastructure: shell.html, panel-registry.js, chart-helpers.js, panels.yaml, compose.py
- [x] 05-02-PLAN.md -- Support Tickets panel (new, from prototypes, 5 ECharts visualizations)
- [x] 05-03-PLAN.md -- Actions + Slack panel extraction from v1 monolith
- [x] 05-04-PLAN.md -- Usage panel extraction from v1 monolith (4 ECharts charts + health grid)
- [x] 05-05-PLAN.md -- Issues panel extraction from v1 monolith (filters, themes, analytics)
- [x] 05-06-PLAN.md -- Overview panel + delight features + final verification

### Phase 6: Dashboard V2 UX Polish
**Goal**: Polish the v2 modular dashboard based on user testing feedback -- data transparency, chart readability, navigation UX, and compose.py wiring into SKILL.md
**Depends on**: Phase 5
**Requirements**: UX-01 through UX-07
**Success Criteria** (what must be TRUE):
  1. Each data section in the dashboard has a small SQL icon -- clicking copies the BigQuery query that produced that data to the clipboard, with a toast notification confirming
  2. Product adoption radar is split into two separate charts (Events and Users) that are independently readable
  3. Every chart section displays its time period (e.g., "Last 12 months", "Last 30 days")
  4. Clicking a key metric card on Overview navigates to the relevant panel AND shows a "back to Overview" breadcrumb for easy return
  5. Sweeps data distinguishes between created and viewed in product adoption
  6. Seat utilization and tracked hours charts render without any label clipping
  7. Running `/customer-snapshot CustomerName` produces the v2 folder-based dashboard via compose.py integration into SKILL.md
**Plans**: 3 plans
Plans:
- [x] 06-01-PLAN.md -- Split sweeps in BQ, fix chart clipping, split radar into two charts
- [x] 06-02-PLAN.md -- Time period labels on all chart sections, overview breadcrumb navigation
- [x] 06-03-PLAN.md -- SQL copy buttons with toast, wire compose.py into SKILL.md for v2 output

</details>

### v2.0 Dashboard Integration + Skill Consolidation (In Progress)

**Milestone Goal:** Make the repo usable by any W&B SE -- integrate all analytics into the dashboard, migrate to the new Jira instance, consolidate skills, and document everything.

- [ ] **Phase 7: Jira Instance Migration** - Migrate all Jira skills and downstream consumers from wandb.atlassian.net to coreweave.atlassian.net
- [ ] **Phase 8: Panel Integration** - Integrate 9 deep-analytics page types as dashboard panels following the v2 panel contract
- [ ] **Phase 9: Skill Audit and Consolidation** - Inventory all 35 skills, remove hardcoded user-specific values, update SKILL.md docs, complete composition rules
- [ ] **Phase 10: Documentation** - Getting-started guide, skill reference, customer onboarding guide, architecture overview

## Phase Details

### Phase 7: Jira Instance Migration
**Goal**: All Jira-dependent skills and dashboards work correctly against coreweave.atlassian.net, with no references to the old wandb.atlassian.net instance remaining in code or documentation
**Depends on**: Phase 6 (v1.0 complete)
**Requirements**: JIRA-01, JIRA-02, JIRA-03, JIRA-04, JIRA-05
**Success Criteria** (what must be TRUE):
  1. SE can run any Jira skill command (search, create issue, add comment, transition) and it connects to coreweave.atlassian.net successfully
  2. Existing JQL filters for customer queries (e.g., `"Customer" = "GResearch"`) return correct results on the new instance -- no silent empty results from broken field mappings
  3. Issue URLs in dashboard HTML output and FE-UPDATE comments link to coreweave.atlassian.net/browse/WB-XXXX (not wandb.atlassian.net)
  4. All downstream skills that consume Jira data (customer-snapshot, jira-check, cadence-prep, pre-read, 3p-update) produce correct output when run end-to-end against the new instance
  5. CLAUDE.md, atlassian.md rules, credential table, and skill-composition.md all reference coreweave.atlassian.net -- no stale wandb.atlassian.net references in committed code
**Plans**: 3 plans
Plans:
- [x] 07-01-PLAN.md -- Core migration: Jira API client, health checker, rules, project docs
- [x] 07-02-PLAN.md -- Dashboard templates, downstream skill docs, test fixtures
- [ ] 07-03-PLAN.md -- Live validation, custom field discovery, worktree cleanup

### Phase 8: Panel Integration
**Goal**: SE can generate a v2 dashboard with all 15 panels (6 existing + 9 new analytics) and each new panel surfaces its analytical dimension inline alongside operational data, giving a single-pane view of customer health
**Depends on**: Phase 7
**Requirements**: PANEL-01, PANEL-02, PANEL-03, PANEL-04, PANEL-05, PANEL-06, PANEL-07, PANEL-08, PANEL-09, PANEL-10
**Success Criteria** (what must be TRUE):
  1. SE can run `/customer-snapshot CustomerName` and the generated dashboard folder contains panel JS files for all 9 new analytics dimensions (cohort, risk, team, journey, decay, velocity, SDK versions, correlation, performance)
  2. Each new panel implements the full PanelRegistry contract -- `register()`, `render()`, `getHeadlineStats()`, `getAttentionItems()` -- and appears in the sidebar navigation alongside existing panels
  3. Overview panel aggregates headline stats and attention items from all 15 panels, giving SE a single glance at customer health across operational AND analytical dimensions
  4. Panels with unavailable data (e.g., no team fields, no renewal_predictions) render a graceful empty state with explanation rather than erroring or showing blank content
  5. Dashboard with all 15 panels loads in under 5 seconds on a standard laptop and each panel JS file stays under 800 lines
**Plans**: TBD
**UI hint**: yes

### Phase 9: Skill Audit and Consolidation
**Goal**: Any W&B SE can discover, understand, and use the full skill suite without tribal knowledge -- every skill is documented, no user-specific values are hardcoded, and composition patterns are complete
**Depends on**: Phase 8
**Requirements**: AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04
**Success Criteria** (what must be TRUE):
  1. A published skill inventory lists all skills with one-line descriptions, classifies each as entry-point (SE invokes directly) vs building-block (consumed by other skills), and shows the dependency graph between skills
  2. Running `grep -r` for known user-specific patterns (GIDs, channel IDs, email addresses) in committed skill code returns zero matches -- all such values live in customers.yaml or ~/.tsm-ai/.env
  3. Every skill directory contains a SKILL.md that accurately describes current behavior, parameters, output format, and example usage -- verified by spot-checking 5+ skills against actual behavior
  4. skill-composition.md covers all multi-skill workflows including the new dashboard generation pipeline and Jira migration changes
**Plans**: TBD

### Phase 10: Documentation
**Goal**: A new W&B SE can go from zero to running their first skill and generating a customer dashboard by following the repo's documentation, without needing to ask the original author
**Depends on**: Phase 9
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04
**Success Criteria** (what must be TRUE):
  1. A getting-started guide in the repo explains what field-eng-skills is, how to clone and install, how to set up each credential (with links to setup skills), and walks through running a first skill -- testable by following it on a fresh machine
  2. A skill reference page lists all skills grouped by category (data sources, dashboards, workflows, utilities) with one-liner descriptions, required credentials, and usage examples
  3. A customer onboarding guide explains the full flow: customers.yaml entry, Asana setup (portfolio + Actions + RAID), Slack channel lookup, SFDC mapping, and first dashboard generation
  4. An architecture overview explains the dashboard pipeline (assemble -> compose -> open), panel contract, data flow from BQ/Jira/Slack through to HTML output, and how to add a new panel
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 7 -> 8 -> 9 -> 10

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation and Template System | v1.0 | 4/4 | Complete | 2026-03-25 |
| 2. High-Confidence Pages | v1.0 | -- | Complete | 2026-03-26 |
| 3. Medium-Confidence Pages | v1.0 | 4/4 | Complete | 2026-03-26 |
| 4. Privacy-Sensitive and Exploratory Pages | v1.0 | 3/3 | Complete | 2026-03-27 |
| 5. Dashboard V2 -- Modular Folder-Based Architecture | v1.0 | 6/6 | Complete | 2026-04-01 |
| 6. Dashboard V2 UX Polish | v1.0 | 3/3 | Complete | 2026-04-01 |
| 7. Jira Instance Migration | v2.0 | 0/3 | Planned | - |
| 8. Panel Integration | v2.0 | 0/? | Not started | - |
| 9. Skill Audit and Consolidation | v2.0 | 0/? | Not started | - |
| 10. Documentation | v2.0 | 0/? | Not started | - |
