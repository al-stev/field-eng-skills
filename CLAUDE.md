# W&B Field Engineering Skills

Claude Code skills for W&B Solutions Engineers. Integrates with W&B Jira (coreweave.atlassian.net), CoreWeave Slack, and CoreWeave Confluence (coreweave.atlassian.net).

## Context

- User is a Solutions Engineer at W&B (Weights & Biases), which is by CoreWeave
- The CoreWeave Slack workspace IS the user's Slack workspace
- Skills are invoked via `/skill-name` in Claude Code

## Preferences

- Narrate before acting — explain what you're about to do so user can validate
- Don't over-adapt source material — copy as-is when already correct
- Be additive, not subtractive with existing context

## Project Structure

```
.claude/
  skills/                   -- Claude Code skills (invoked via /skill-name)
    3p-update/              -- 3P (Progress/Plans/Problems) update generation from Asana + Jira + Slack
    asana/                  -- Asana project/task queries and mutations (SE action tracking)
    asana-setup/            -- One-time Asana PAT setup
    atlassian-setup/        -- One-time Atlassian API token setup (Jira + Confluence)
    bigquery/               -- BigQuery usage data queries (wandb-production.analytics) with product area mapping
    bigquery-setup/         -- One-time BigQuery ADC connectivity verification
    cadence-prep/           -- Customer cadence call preparation
    confluence/             -- CoreWeave Confluence pages, spaces (coreweave.atlassian.net)
    credential-reference/   -- Reference table for all API credential keys
    credential-status/      -- Check health of all configured credentials
    customer-setup/         -- Interactive customer onboarding (SFDC + SE overlays -> customers.yaml)
    customer-snapshot/      -- Customer intelligence dashboard from Jira + Slack data
    deep-analytics/         -- Deep analytics HTML pages from BigQuery data (user journey, cohort, decay, velocity, team, risk, correlation, SDK, performance)
    gcalendar/              -- Google Calendar via Apps Script + Chrome CDP (Okta SSO)
    gcalendar-setup/        -- One-time Google Calendar Apps Script setup
    gdocs/                  -- Google Docs via Apps Script + Chrome CDP (Okta SSO)
    gdocs-setup/            -- One-time Google Docs Apps Script setup
    ghosted/                -- Customer silence tracker (Waiting on Customer thread monitoring)
    gmail/                  -- Gmail via Apps Script + Chrome CDP (Okta SSO, read-only)
    gmail-setup/            -- One-time Gmail Apps Script setup
    gong/                   -- Gong call recordings, transcripts, AI summaries (cookie-based + CDP)
    gong-setup/             -- One-time Gong credential setup
    jira/                   -- W&B Jira queries, issue creation, FE-UPDATE (coreweave.atlassian.net)
    jira-check/             -- Jira issue triage and FE-UPDATE pipeline
    lattice/                -- Weekly Lattice update generator mapped to IC5 growth areas
    maction/                -- Meeting notes to Asana actions + RAID items
    nag/                    -- Stale/overdue task scanner across customer projects
    pre-read/               -- Meeting pre-read document generation
    raid/                   -- RAID log management (Risks, Assumptions, Issues, Dependencies)
    rats/                   -- Roses & Thorns biweekly update
    salesforce/             -- Salesforce account queries (read-only: accounts, team members, field discovery)
    salesforce-setup/       -- One-time Salesforce credential setup
    slack/                  -- CoreWeave Slack channel history, search, threads
    slack-setup/            -- One-time Slack credential setup
    usage-report/           -- Standalone usage visualization (external QBR-ready + internal SE prep reports with ECharts)
    gcalendar/              -- Google Calendar via Apps Script + Chrome CDP (Okta SSO)
    gcalendar-setup/        -- One-time Google Calendar Apps Script setup
    gdocs/                  -- Google Docs via Apps Script + Chrome CDP (Okta SSO)
    gdocs-setup/            -- One-time Google Docs Apps Script setup
    gmail/                  -- Gmail via Apps Script + Chrome CDP (Okta SSO, read-only)
    gmail-setup/            -- One-time Gmail Apps Script setup
    gong/                   -- Gong call recordings, transcripts, AI summaries (cookie-based + CDP)
    gong-setup/             -- One-time Gong credential setup
  rules/                    -- Auto-loaded project rules
    asana.md                -- Asana workspace conventions (sections, custom fields, RAID, portfolio, staleness rules)
    atlassian.md            -- Atlassian workspace conventions
    slack.md                -- Slack workspace conventions
    skill-composition.md    -- Multi-skill workflow patterns
customers/                  -- Per-customer output directory (gitignored)
templates/                  -- Agent and output templates
scripts/                    -- Shared shell scripts
```

## Credentials

All API credentials stored in `~/.fe-skills/.env`. Run `/credential-status` to check health.

| Variable | Service | Instance |
|----------|---------|----------|
| `ATLASSIAN_EMAIL` | W&B Jira | coreweave.atlassian.net |
| `ATLASSIAN_TOKEN` | W&B Jira | coreweave.atlassian.net |
| `CONFLUENCE_EMAIL` | CoreWeave Confluence | coreweave.atlassian.net |
| `CONFLUENCE_TOKEN` | CoreWeave Confluence | coreweave.atlassian.net |
| `SLACK_TOKEN` | CoreWeave Slack | coreweave.slack.com |
| `SLACK_COOKIE` | CoreWeave Slack | coreweave.slack.com |
| `ASANA_TOKEN` | Asana | app.asana.com |
| `SFDC_SESSION_ID` | W&B Salesforce (session auth) | wandb.my.salesforce.com |
| `SFDC_INSTANCE` | W&B Salesforce (session auth) | wandb.my.salesforce.com |
| `GCALENDAR_APPSCRIPT_URL` | Google Calendar | script.google.com |
| `GCALENDAR_APPSCRIPT_KEY` | Google Calendar | script.google.com |
| `GDOCS_APPSCRIPT_URL` | Google Docs | script.google.com |
| `GDOCS_APPSCRIPT_KEY` | Google Docs | script.google.com |
| `GMAIL_APPSCRIPT_URL` | Gmail | script.google.com |
| `GMAIL_APPSCRIPT_KEY` | Gmail | script.google.com |
| `GONG_COOKIE` | Gong | us-54638.app.gong.io |

BigQuery uses Application Default Credentials (ADC) -- no token in ~/.fe-skills/.env. Run `gcloud auth application-default login` to configure. Verify with `/bigquery-setup`.

Asana PAT (`ASANA_TOKEN`) for SE action tracking. Asana uses a two-project model per customer: Actions project (day-to-day SE work, safe to share) and RAID Portfolio project (internal strategic view). Run `/raid` to manage RAID logs. Master portfolio holds all customer portfolios. Run `setup-customer` to onboard new customers into the portfolio structure.

## Python Skills

Python skills use `uv run --project .claude/skills/<skill>` for dependency isolation. uv is installed at `~/.local/bin/uv`.

<!-- GSD:project-start source:PROJECT.md -->
## Project

**BQ Deep Analytics — Usage Intelligence Expansion**

A suite of 9 standalone deep-analytics HTML pages that transform raw BigQuery usage data into actionable intelligence for W&B Solutions Engineers. Each page targets a specific analytical dimension — from user adoption journeys to churn risk scoring — going far beyond the aggregate charts in the existing usage reports. Built on top of the existing BQ query factory and ECharts report ecosystem in field-eng-skills.

**Core Value:** Give SEs named-user, team-level, and trend-aware intelligence so they can have specific, data-driven conversations with customers instead of generic "usage is growing/declining" narratives.

### Constraints

- **BQ Access**: Job project is wandb-sa-sandbox, not wandb-production — query permissions may differ per dataset
- **Data Availability**: renewal_predictions (landing_development dataset) and team fields may not exist for all accounts
- **Server Deployments**: No cloud usernames — must use dim_users JOIN for identity resolution
- **Self-contained HTML**: Each page must work as a standalone file (ECharts CDN, inline CSS/JS, no server)
- **Privacy**: Cross-account correlation data must remain SE-internal, never customer-facing
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Decision: Stay on ECharts v5, Do NOT Upgrade to v6
### Visualization Layer (Frontend — Inline in HTML)
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Apache ECharts | 5.x (latest 5.6.0) | All chart rendering | Already in use across 3 templates. Supports every chart type needed. Custom `wandb` theme already registered. CDN-loaded, no build step. |
| ECharts CDN | `https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js` | Script loading | Consistent with existing templates. ~1MB gzipped. Resolves to latest 5.x. |
| Google Fonts | Instrument Serif + Outfit + JetBrains Mono | Typography | Already loaded in all existing templates. W&B brand-aligned. |
### ECharts Chart Types by Analytical Dimension
| Page | Primary Chart Type | ECharts Series | Secondary Charts | Notes |
|------|-------------------|----------------|-----------------|-------|
| **User Journey** | Sankey diagram | `type: 'sankey'` | Funnel (`type: 'funnel'`) for conversion rates | Sankey shows flow between adoption stages (first_run -> first_sweep -> first_artifact -> etc). Funnel shows drop-off at each stage. Both built-in to ECharts v5. |
| **Cohort Analysis** | Heatmap | `type: 'heatmap'` + `visualMap` | None needed | Rows = cohort month, columns = period offset (week 1, 2, 3...), cell color = retention %. Use `visualMap` continuous component for color gradient (green = high retention, red = low). |
| **Engagement Decay** | Line with markArea | `type: 'line'` + `markArea` + `markLine` | Scatter for individual user drop-offs | Decay curves as line series. `markArea` for danger zones (e.g., <20% engagement). `markLine` for threshold indicators. Multiple series overlay for per-user vs. aggregate. |
| **Feature Velocity** | Sparkline grid + line | `type: 'line'` (small multiples) | Bar for momentum indicators | No native sparkline in ECharts. Use small `echarts.init()` instances per product area (~50x20px containers) for inline sparklines. Main view uses full line charts with `areaStyle` gradient fill. |
| **Team Detection** | Treemap | `type: 'treemap'` | Bar for per-team comparison | Treemap shows hierarchical team -> user -> product area breakdown. Size = total events, color = growth rate. Alternative: nested pie/sunburst for org -> team hierarchy. |
| **Risk Scoring** | Gauge + scatter | `type: 'gauge'` + `type: 'scatter'` | Radar for multi-factor risk profile | Gauge for composite risk score (0-100). Scatter plot with size/color encoding for risk matrix (x = engagement trend, y = churn probability, size = ARR). Radar for breakdown by factor. |
| **Usage Correlation** | Scatter matrix | `type: 'scatter'` (multiple series) | Heatmap for correlation coefficients | Scatter plots showing product-pair correlations (x = Experiments usage, y = Artifacts usage). Heatmap for correlation coefficient matrix. Use ECharts `grid` array for multi-panel layout. |
| **SDK Version** | Bar + treemap | `type: 'bar'` (stacked) + `type: 'treemap'` | Pie for version distribution snapshot | Stacked bar over time shows version migration. Treemap for current distribution. Color-code by version freshness (current = green, stale = amber, ancient = red). |
| **Performance** | Line + bar combo | `type: 'line'` + `type: 'bar'` | Gauge for performance index | Dual-axis chart: line for latency trends, bar for error counts. Gauge for application_performance_index. Use `markArea` for incident windows. |
### ECharts Configuration Patterns to Standardize
| Pattern | ECharts Feature | How to Use |
|---------|----------------|------------|
| **Color gradient heatmaps** | `visualMap: { type: 'continuous', inRange: { color: [...] } }` | For cohort retention, correlation matrices. Use W&B brand colors: `['#f87171', '#fbbf24', '#4ade80']` (red-amber-green). |
| **Responsive resize** | `window.addEventListener('resize', () => chart.resize())` | Already used in existing templates. Must be on every page. |
| **Dark/light theming** | CSS `prefers-color-scheme` media query + `getThemeColors()` | Existing pattern: design tokens in CSS `:root`, JS reads computed styles. All 9 pages must follow this. |
| **Tooltip formatting** | `tooltip: { trigger: 'axis', formatter: function }` | Custom formatters per chart type. Axis trigger for time series, item trigger for heatmaps/scatter. |
| **Multi-chart grid** | `grid: [{...}, {...}]` with matching `xAxis`/`yAxis` arrays | For correlation matrix (NxN scatter grid) and sparkline grids. Each grid gets its own axis pair. |
| **Data zoom** | `dataZoom: [{ type: 'inside' }, { type: 'slider' }]` | For time-series charts with 12+ months of data. Slider for visible control, inside for scroll-zoom. |
| **W&B theme registration** | `echarts.registerTheme('wandb', {...})` | Already defined in existing templates. Extract into a shared pattern for all 9 pages. |
### Data Layer (Python — BQ Queries)
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| google-cloud-bigquery | >=3.39.0 (current: 3.40.1) | BQ query execution | Already in pyproject.toml. ADC auth, parameterized queries, Arrow transfer. |
| google-cloud-bigquery-storage | >=2.36.0 | Fast data transfer | Required for `to_dataframe()` performance. Already a dependency. |
| pandas | >=2.0.0 | Data manipulation | DataFrame output from BQ, aggregation, pivot tables, resampling. Already a dependency. |
| pyarrow | >=17.0.0 | Arrow format transfer | Required by BQ storage API. Already a dependency. |
| db-dtypes | >=1.5.0 | BQ date/time dtypes | Required for DATE/TIME columns in pandas. Already a dependency. |
| pyyaml | >=6.0 | Customer registry | For reading customers.yaml. Already a dependency. |
### Data Processing Patterns for New Queries
| Analytical Dimension | BQ Query Strategy | Python Post-Processing |
|---------------------|-------------------|----------------------|
| **User Journey** | Query `dim_users` first_*_at fields, pivot to per-user journey stages | pandas: compute stage transitions, aggregate to flow volumes for Sankey nodes/links |
| **Cohort Analysis** | Query `ext_daily_user_event_usage` grouped by first-activity month + week offset | pandas: pivot to cohort x period matrix, compute retention percentages |
| **Engagement Decay** | Query `agg_daily_customer_engagement_score` per user, compute WoW deltas | pandas: rolling window (7d), detect drop-off thresholds, flag cold users |
| **Feature Velocity** | Extend existing `product_areas_query()` with weekly granularity + momentum calc | pandas: resample to weekly, compute rolling slope (acceleration/deceleration) |
| **Team Detection** | Query `ext_daily_user_event_usage` team fields (org_name, is_part_of_team, count_teams) | pandas: groupby org_name, aggregate event counts, compute per-team adoption profiles |
| **Risk Scoring** | JOIN `renewal_predictions` + `agg_daily_customer_engagement_score` + `stg_salesforce_accounts` | pandas: normalize scores, compute composite weighted risk, classify into tiers |
| **Usage Correlation** | Query `ext_daily_user_event_usage` product area pivot per account (cross-account) | pandas: compute pairwise correlation matrix, identify significant correlations |
| **SDK Version** | Query `ext_daily_user_event_usage` cli_version + local_version fields | pandas: parse semver, classify freshness, aggregate distribution over time |
| **Performance** | Query `fct_application_performance` + `fct_onscreen_loader_latencies` | pandas: aggregate performance metrics, compute trends, identify degradation |
### BQ Query Optimization Practices
| Practice | Implementation | Impact |
|----------|---------------|--------|
| **Column selection** | SELECT only needed columns, never `SELECT *` | Reduces bytes scanned (BQ charges per byte) |
| **Early WHERE filtering** | Filter by `account_id` and date range before JOINs | Minimizes data processed |
| **Parameterized queries** | Use `@account_id` parameter (already established pattern) | Prevents SQL injection, enables query caching |
| **Date partitioning** | Filter on `date_day` which is the partition column on most tables | Scans only relevant partitions |
| **Approximate functions** | Use `APPROX_COUNT_DISTINCT()` for cross-account correlation queries | 10x faster for large cardinality counts |
| **24h query caching** | Identical queries within 24h are free from cache | Run same customer multiple times at no cost |
| **Weekly aggregation in Python** | Use existing `aggregate_weekly()` function in queries.py | Reduces data transfer, already proven pattern |
### HTML Template Architecture
| Component | Pattern | Source |
|-----------|---------|--------|
| **Data injection** | `const PAGE_DATA = { ... };` JS object literal at top of `<script>` block | Matches existing `USAGE_DATA` and `INTELLIGENCE_DATA` patterns |
| **Self-contained HTML** | Single .html file, no external JS/CSS beyond CDN | Constraint from PROJECT.md. Portable, screen-share ready. |
| **CSS design tokens** | `:root { --bg-primary: ...; }` with `@media (prefers-color-scheme: light)` override | Copy from existing templates. Established W&B brand tokens. |
| **Font loading** | Google Fonts preconnect + Instrument Serif, Outfit, JetBrains Mono | Identical to existing templates. |
| **Chart container pattern** | `<div id="chartName" style="width:100%;height:400px;"></div>` | Standard ECharts container. Height varies by chart type. |
| **Render-on-load** | `document.addEventListener('DOMContentLoaded', function() { ... })` | Initialize all charts after DOM ready. Handle missing data gracefully. |
### Infrastructure
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| uv | latest | Python dependency management | Already used for all skills. `uv run --project .claude/skills/bigquery` pattern. |
| gcloud ADC | N/A | BigQuery authentication | Application Default Credentials. No stored secrets. Quota project: wandb-sa-sandbox. |
## Alternatives Considered
| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Charting library | ECharts v5 | ECharts v6 | Breaking theme changes, no needed new features, inconsistent with existing templates |
| Charting library | ECharts v5 | D3.js | Too much code for each chart. ECharts provides Sankey, heatmap, funnel, gauge out of box. D3 requires building everything from primitives. |
| Charting library | ECharts v5 | Plotly.js | Larger bundle size (~3.5MB vs ~1MB). Dated visual style. Less customizable themes. |
| Charting library | ECharts v5 | Chart.js | Missing Sankey, heatmap, treemap, gauge, funnel. Would need plugins for most chart types. |
| Charting library | ECharts v5 | Highcharts | Commercial license required. Cannot use in this context. |
| Python viz | Raw JSON output | pyecharts | Adds unnecessary abstraction. We need JSON data, not Python-generated chart configs. The HTML templates own the visualization logic. |
| Python viz | pandas | numpy only | pandas is already a dependency and provides resampling, pivot, groupby. No reason to drop down to numpy for data manipulation. |
| Data format | JSON object literal in HTML | External JSON file | Self-contained HTML constraint. Data must be inline. Agent replaces placeholder data at generation time. |
| Template engine | String replacement by agent | Jinja2 | No Python server at render time. The agent populates data, the HTML is static after that. Adding Jinja2 adds complexity without benefit. |
| Sparklines | Small ECharts instances | SVG sparkline library | Extra dependency for one use case. ECharts mini-instances work fine with minimal config. |
| Correlation matrix | ECharts multi-grid scatter | Separate library (e.g., d3-array) | Correlation coefficient computation is trivial in pandas. Only the visualization needs ECharts. |
## What NOT to Use
| Anti-Choice | Why Avoid |
|-------------|-----------|
| **Any npm build step** | Pages are self-contained HTML. No webpack, vite, rollup. CDN only. |
| **React/Vue/Svelte** | No framework needed. Vanilla JS with ECharts. Adding a framework for static reports is overengineering. |
| **Tailwind CSS** | The existing design token system (CSS custom properties) is more maintainable for this use case. Tailwind's utility classes would diverge from the established patterns. |
| **Server-side rendering** | Reports are generated once, opened in browser. No server. No SSR. |
| **pyecharts** | Generates chart configs in Python. We want the HTML template to own chart configuration so the agent can reason about layout, theming, and interactivity in one place. |
| **Matplotlib/Seaborn** | Static image output. We need interactive charts with tooltips, zoom, and responsive layout. |
| **External JSON data files** | Breaks self-contained HTML constraint. Data goes inline as JS object literal. |
| **ECharts GL extension** | 3D/WebGL charts. Unnecessary complexity. All our charts are 2D. |
| **ECharts map extension** | Geographic maps. We have no geo data to visualize. |
## CDN Dependencies (Complete List)
## Python Dependencies (No Changes)
# Existing bigquery-skill/pyproject.toml — no additions needed
## Sources
- ECharts v6 feature list: https://echarts.apache.org/handbook/en/basics/release-note/v6-feature/ (verified 2026-03-24)
- ECharts v5->v6 migration guide: https://echarts.apache.org/handbook/en/basics/release-note/v6-upgrade-guide/ (verified 2026-03-24)
- ECharts GitHub releases: https://github.com/apache/echarts/releases (verified 2026-03-24)
- ECharts examples gallery: https://echarts.apache.org/examples/en/index.html
- ECharts documentation: https://echarts.apache.org/en/option.html
- BigQuery optimization guide: https://docs.cloud.google.com/bigquery/docs/best-practices-performance-compute
- BigQuery cost optimization: https://www.e6data.com/query-and-cost-optimization-hub/how-to-optimize-bigquery-costs
- Existing codebase: `usage-report-internal.html`, `usage-report-external.html`, `intelligence-dashboard.html`, `queries.py`, `bq_client.py`, `usage.py`
- AI docs: `~/Documents/gitstuff/ai-docs/wandb-usage-visualization.md`, `google-cloud-bigquery.md`, `wandb-bigquery-schema-discovery.md`
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
