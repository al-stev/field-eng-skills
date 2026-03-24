# Requirements: BQ Deep Analytics

**Defined:** 2026-03-24
**Core Value:** Give SEs named-user, team-level, and trend-aware intelligence so they can have specific, data-driven conversations with customers.

## v1 Requirements

### Foundation

- [ ] **FOUND-01**: New `deep-analytics` skill directory with uv project, orchestrator (generate.py), and CLI entry point
- [ ] **FOUND-02**: Shared identity resolution CTE utility for dim_users JOIN (server deployment support)
- [ ] **FOUND-03**: BQ cost guardrails: maximum_bytes_billed on every new query, bytes-processed logging
- [ ] **FOUND-04**: Schema validation utility that checks table existence and required columns before querying
- [ ] **FOUND-05**: Shared W&B design system (CSS tokens, ECharts wandb theme, fonts, dark/light mode) documented and extractable from existing templates

### Cross-Cutting (Every Page)

- [ ] **XCUT-01**: AI narrative summary section with SE talk-track text generated at build time
- [ ] **XCUT-02**: KPI headline row (2-4 top-level numbers) above charts
- [ ] **XCUT-03**: Date range context header showing analysis period
- [ ] **XCUT-04**: W&B branding (Instrument Serif, Outfit, JetBrains Mono, gold accent, noise texture)
- [ ] **XCUT-05**: Self-contained HTML (single file, ECharts CDN, inline CSS/JS, no server)
- [ ] **XCUT-06**: Dark/light mode via prefers-color-scheme CSS media query
- [ ] **XCUT-07**: Graceful empty states when customer lacks data for a dimension
- [ ] **XCUT-08**: Interactive tooltips on all chart data points
- [ ] **XCUT-09**: Print/screenshot readiness (ECharts saveAsImage toolbox)
- [ ] **XCUT-10**: Copy-to-clipboard for AI narrative text
- [ ] **XCUT-11**: Linked navigation between related pages

### User Journey

- [ ] **JOUR-01**: Sankey diagram showing user flow through W&B product adoption stages (Experiments → Artifacts → Registry → Weave etc.)
- [ ] **JOUR-02**: Stage completion counts (how many users reached each product stage)
- [ ] **JOUR-03**: Median time-between-stages showing adoption velocity
- [ ] **JOUR-04**: "Never reached" breakdown highlighting zero-adoption stages as enablement opportunities
- [ ] **JOUR-05**: AI narrative interpreting journey patterns with actionable SE recommendations
- [ ] **JOUR-06**: Timeline view showing feature discovery chronology (Gantt-style horizontal bars)
- [ ] **JOUR-07**: Per-user journey drill-down table with individual stage timestamps
- [ ] **JOUR-08**: ML maturity model scoring (L1-L5 scale based on product stage adoption)

### Cohort Analysis

- [ ] **CHRT-01**: Retention heatmap (rows=monthly signup cohorts, columns=months since signup, cells=retention %)
- [ ] **CHRT-02**: Cohort size labels on each row showing starting cohort size
- [ ] **CHRT-03**: Overall retention curve (aggregate % active after 1mo, 3mo, 6mo, 12mo)
- [ ] **CHRT-04**: AI narrative interpreting cohort health vs historical averages
- [ ] **CHRT-05**: New/Retained/Resurrected/Churned stacked area lifecycle chart
- [ ] **CHRT-06**: Cohort-over-cohort trend line overlay (last 4 cohorts)
- [ ] **CHRT-07**: Behavioral cohort comparison (group by first action type, compare retention)

### Engagement Decay

- [ ] **DCAY-01**: User cold-detection table ranking users by activity decline severity (>50% WoW decline or >14 days silent after weekly activity)
- [ ] **DCAY-02**: Days-since-last-activity distribution histogram (0-7d, 8-14d, 15-30d, 31-60d, 60+d)
- [ ] **DCAY-03**: Account-level engagement score trend line over time
- [ ] **DCAY-04**: AI narrative identifying cold users with context on their importance (power user flagging)
- [ ] **DCAY-05**: Per-user inline engagement sparklines in cold-detection table (12-week activity)
- [ ] **DCAY-06**: Decay severity color coding (green=active, amber=declining, red=cold, grey=churned)
- [ ] **DCAY-07**: Champion risk flagging — badge on declining users who are top-10 power users

### Feature Velocity

- [ ] **VELC-01**: Sparkline grid showing monthly event counts per product area (all areas at a glance)
- [ ] **VELC-02**: Momentum indicators (up/down/flat arrows) per product area based on recent vs prior 3 months
- [ ] **VELC-03**: Unique users trend per product area alongside event volume
- [ ] **VELC-04**: AI narrative summarizing acceleration/deceleration patterns with SE action items
- [ ] **VELC-05**: Acceleration/deceleration heatmap (rate of change over time per product area)
- [ ] **VELC-06**: Create-vs-view ratio per product area (producers vs consumers)
- [ ] **VELC-07**: Cross-area correlation showing adoption chains between product areas

### Team Detection

- [ ] **TEAM-01**: Team breakdown table listing teams (from org_name/is_part_of_team), member counts, total activity, top product areas
- [ ] **TEAM-02**: Per-team activity bar chart comparing total activity and unique users
- [ ] **TEAM-03**: Team x product area heatmap showing which teams use which products
- [ ] **TEAM-04**: Clear "Team data unavailable" message when fields are not populated
- [ ] **TEAM-05**: AI narrative identifying team patterns and per-team enablement opportunities
- [ ] **TEAM-06**: Team adoption timeline showing when each team started using W&B
- [ ] **TEAM-07**: Per-team champion identification (most active user per team)
- [ ] **TEAM-08**: Team growth/contraction trend (new users joining vs dropping off per team)

### Risk Scoring

- [ ] **RISK-01**: Composite risk score (0-100) combining ML churn probability, engagement trend, seat utilization, support ticket velocity — displayed as gauge chart
- [ ] **RISK-02**: Risk factor breakdown showing which factors contribute most to the score
- [ ] **RISK-03**: Risk trend line showing score evolution over last 6 months
- [ ] **RISK-04**: Renewal context (days to renewal, ARR, contract details) alongside risk score
- [ ] **RISK-05**: AI narrative with actionable risk assessment and recommended SE interventions
- [ ] **RISK-06**: Risk radar chart (multi-dimensional radar showing risk shape at a glance)
- [ ] **RISK-07**: AI-generated action recommendations (schedule QBR, run workshop, engage champion)
- [ ] **RISK-08**: Historical risk snapshot comparison (now vs 3mo ago vs 6mo ago)

### Usage Correlation

- [ ] **CORR-01**: Product combination matrix (heatmap) showing which product combos co-occur across accounts with retention rates
- [ ] **CORR-02**: Current account positioning showing their product mix against aggregate patterns
- [ ] **CORR-03**: Next-best-action recommendation based on correlation data
- [ ] **CORR-04**: "SE-Internal Only" privacy badge and aggregate-only queries (no individual account names)
- [ ] **CORR-05**: AI narrative interpreting correlation patterns with account-specific recommendations
- [ ] **CORR-06**: Expansion signal indicators (flag usage approaching contract limits for upsell)
- [ ] **CORR-07**: Anonymized peer benchmarking (percentile ranking vs similar-tier accounts)
- [ ] **CORR-08**: ARR-usage scatter overlay (product breadth vs ARR across accounts, SE-internal)

### SDK Versions

- [ ] **SDKV-01**: Version distribution donut chart showing cli_version breakdown
- [ ] **SDKV-02**: Version freshness assessment comparing customer versions against latest release
- [ ] **SDKV-03**: User-to-version mapping table (username, cli_version, local_version, last_activity)
- [ ] **SDKV-04**: Version trend over time (stacked area chart showing distribution shifts month-over-month)
- [ ] **SDKV-05**: AI narrative with version assessment and upgrade recommendations
- [ ] **SDKV-06**: Library usage breakdown (PyTorch, TensorFlow, HuggingFace integrations from ext_weekly_library_usage)
- [ ] **SDKV-07**: Exportable upgrade recommendation list with user contact info (copy-to-clipboard)

### Performance

- [ ] **PERF-01**: Performance index gauge chart (application_performance_index from fct_application_performance)
- [ ] **PERF-02**: Per-feature slowness breakdown bar chart (slow_charts, slow_project_search, slow_artifact_creating, etc.)
- [ ] **PERF-03**: Error metrics KPI cards (users_facing_errors_ct, error_count) with trend
- [ ] **PERF-04**: Chart load latency distribution from fct_onscreen_loader_latencies
- [ ] **PERF-05**: AI narrative with performance assessment and flagged areas of concern
- [ ] **PERF-06**: Slow chart load user breakdown from agg_daily_team_members_slow_chart_loads

## v2 Requirements

(All differentiators promoted to v1)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time updating / WebSocket | Point-in-time reports, not monitoring dashboards |
| User-configurable date picker | Self-contained HTML cannot re-query BQ |
| Complex filter UI (dropdowns, multi-select) | Single-customer pages; account_id hardcoded at generation |
| Browser-to-BQ/API connection | Violates self-contained HTML constraint |
| Dark mode toggle button | CSS prefers-color-scheme handles automatically |
| PDF export button | Browser print-to-PDF works; CSS @media print rules |
| Cross-customer comparison visible to customers | Privacy violation; correlation data is SE-internal only |
| Multi-customer dashboard | Each page is single-customer; cross-customer in separate tool |
| Mobile-first design | SEs use laptops; desktop-first with responsive to ~1024px |
| Authentication / login | Self-contained HTML files; gitignored, stored locally |
| Automated email/Slack alerting | Reports are artifacts, not monitoring |
| Editable data / writeback | Read-only artifacts; re-generate if data is wrong |
| Automated cron scheduling | On-demand generation when SE prepares for meeting |

## Traceability

Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| (populated by roadmapper) | | |

**Coverage:**
- v1 requirements: 72 total
- Mapped to phases: 0
- Unmapped: 72 ⚠️

---
*Requirements defined: 2026-03-24*
*Last updated: 2026-03-24 after initial definition*
