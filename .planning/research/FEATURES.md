# Feature Landscape

**Domain:** SE-facing product usage analytics deep-dive pages (9 analytical dimensions)
**Researched:** 2026-03-24
**Confidence:** HIGH (existing codebase + BQ schema fully inspected, web research verified)

---

## Cross-Cutting Features (Apply to All 9 Pages)

### Table Stakes

Every deep-dive page must have these or it fails the "is this useful in a customer conversation?" test.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| AI narrative summary | SEs need talk-track text, not just charts. The existing reports already set this expectation. | Med | Claude generates at report-build time. Already proven in usage-report-internal.html |
| Date range context | "Last 12 months" header with period start/end. Without this, every chart is ambiguous. | Low | Already in existing usage.py output schema |
| KPI headline row | 2-4 top-level numbers above the charts. SEs scan headlines first, drill into charts second. | Low | Established pattern in existing reports (kpi-row CSS) |
| Dark/light mode | Existing reports support both via CSS custom properties. Breaking this convention = regression. | Low | Copy design tokens from usage-report-internal.html |
| W&B branding | Instrument Serif + Outfit + JetBrains Mono. Gold accent. Noise texture. Must match existing reports. | Low | Design system already defined in templates |
| Self-contained HTML | Single file, ECharts via CDN, no server. This is the deployment model -- non-negotiable. | Low | Architectural constraint from PROJECT.md |
| Print/screenshot readiness | SEs paste charts into Slack and slide decks. Charts must render cleanly at static sizes. | Low | ECharts has built-in `saveAsImage` toolbox feature |
| Responsive layout | SEs use laptops (1440px) and occasionally share on projectors. Must not break at common widths. | Low | Existing CSS uses clamp() and media queries |
| Graceful empty states | Not every customer has data for every dimension. Missing data must show a clear message, not a broken chart. | Low | Conditional rendering: "No data available for this dimension" card |
| Interactive tooltips | Hovering over data points must show exact values. Static charts are unacceptable for data exploration. | Low | ECharts built-in tooltip component, already standard |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Contextual "so what?" callouts | Inline annotations on charts: "This is where Weave adoption started" or "3 power users went cold here". Goes beyond raw visualization. | Med | AI-generated at build time, injected as ECharts markLine/markPoint or HTML callouts |
| Copy-to-clipboard for key insights | One-click copy of AI narrative text or KPI row as formatted text. SEs paste into Slack/email constantly. | Low | `navigator.clipboard.writeText()` with a small copy icon. Zero dependencies. |
| ECharts toolbox (zoom, save image) | Native ECharts toolbox gives zoom-to-region, save-as-PNG, data view toggle. Free interactivity. | Low | `toolbox: { feature: { saveAsImage: {}, dataZoom: {} } }` in chart config |
| Linked navigation between pages | "See also: Risk Scoring" link from Engagement Decay page. Cross-references between related dimensions. | Low | Simple `<a>` links at page bottom. File naming convention enables this. |

### Anti-Features (Cross-Cutting)

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Real-time updating / live WebSocket | These are point-in-time reports, not monitoring dashboards. Adds complexity for zero SE value. | Generate fresh report on demand via CLI |
| User-configurable date ranges (date picker) | Self-contained HTML cannot re-query BQ. Date pickers create expectation of dynamic data. | Fixed 12-month lookback, configurable at generation time via `--months` CLI arg |
| Complex filter UI (dropdowns, multi-select) | Overengineered for single-customer pages. SEs view one customer at a time. | Hardcode account_id at generation time. ECharts DataZoom for time-axis zoom only. |
| Database/API connection from browser | Violates self-contained HTML constraint. Requires auth, CORS, credential management. | Python CLI generates HTML with embedded JSON data |
| Dark mode toggle button | `prefers-color-scheme` media query handles this automatically. Manual toggle adds JS complexity. | CSS-only via media query (existing pattern) |
| PDF export button | Browser print-to-PDF works. Building a PDF renderer adds weight for marginal value. | CSS `@media print` rules for clean printing |
| Cross-customer comparison visible to customers | Privacy violation. Correlation data must stay SE-internal. | Anonymized aggregates only, "SE Internal" badge on sensitive pages |
| Multi-customer dashboard | Each page is single-customer. Cross-customer views belong in a separate tool. | Generate per-customer reports. Cross-account correlation uses aggregates. |
| Mobile-first design | SEs use laptops. Mobile is not a use case for internal analytics tools. | Desktop-first with responsive down to ~1024px |
| Authentication / login | Self-contained HTML files. Auth adds server requirement. | Files are gitignored, stored locally in customers/ directory |
| Automated email/Slack alerting | Reports are artifacts, not monitoring. Alerting belongs elsewhere. | AI narrative flags urgent items. SE reads report and decides action. |
| Editable data / writeback | Reports are read-only artifacts. Editability implies a backend. | Re-run generation with corrected queries if data is wrong. |
| Automated scheduling (cron) | Reports are generated on demand, not on a schedule. Scheduling adds infra that doesn't exist. | SE runs generation command when preparing for a meeting. |

---

## Per-Dimension Feature Specifications

### 1. User Journey Analysis

**Purpose:** Show per-user progression through W&B product stages using dim_users first_*_at fields.
**Data confidence:** HIGH (dim_users first_*_at fields confirmed)
**Primary BQ source:** `dim_users`

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Sankey diagram: product stage flow | The core visualization. Shows how users flow from first Experiments to Artifacts to Model Registry to Weave. Without this, the page has no reason to exist. | High | ECharts sankey series. Nodes = product stages, flows = user transitions. Data from dim_users first_*_at timestamps. |
| Stage completion counts | Bar or KPI showing how many users reached each product stage (e.g., "142 users tried Experiments, 38 used Artifacts, 12 reached Model Registry"). | Low | Simple COUNT from dim_users WHERE first_X_at IS NOT NULL |
| Median time-between-stages | "Median 23 days from first run to first artifact." Critical for SE to understand adoption velocity. | Med | DATEDIFF between successive first_*_at fields, aggregated |
| "Never reached" breakdown | Highlight stages with 0 adoption (e.g., "0 users have tried Launch"). These are SE enablement opportunities. | Low | COUNT WHERE first_X_at IS NULL. Red badge styling. |
| AI narrative: journey interpretation | "67% of users plateau at Experiments without adopting Artifacts. Recommend: Artifacts workshop targeting the 38 users who have >100 runs." | Med | AI prompt with stage counts and transition rates |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Timeline view: feature discovery chronology | Gantt-style horizontal bars showing WHEN the account first used each product area. Shows adoption pace over calendar time. | Med | ECharts custom series or bar chart with time axis. Data: MIN(first_*_at) per product area. |
| Per-user journey table (drill-down) | Table listing individual users with their journey stage and timestamps. "Click to see who's stuck at Experiments." | Med | Sortable HTML table populated from dim_users data |
| Maturity model scoring | Score the account on a 1-5 ML maturity scale based on which stages have active users. Visual step diagram. | Med | Derived metric: L1=Experiments only, L2=+Artifacts/Registry, L3=+Reports/Sweeps, L4=+Launch/Automations, L5=+Weave |

---

### 2. Cohort Analysis

**Purpose:** Compare retention of new vs established user cohorts using retention tables and heatmaps.
**Data confidence:** MEDIUM (retention tables exist, schema needs exploration)
**Primary BQ source:** `agg_weekly_user_retention_features`, `ext_daily_user_event_usage` (user_*_accounting fields)

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Retention heatmap | Grid: rows = monthly signup cohorts, columns = months since signup, cells = retention %. Color gradient green (high) to red (low). THE canonical cohort visualization. | High | ECharts heatmap series with visualMap. Keep under 12x12 for readability. |
| Cohort size labels | Each row must show the starting cohort size (e.g., "Jan 2025: 24 users"). Without this, percentages are meaningless. | Low | Inline labels on heatmap Y-axis or side column |
| Overall retention curve | Line chart showing aggregate retention: what % of all users still active after 1mo, 3mo, 6mo, 12mo. | Med | Aggregated from cohort data |
| AI narrative: cohort health | "Your newest cohort (Feb 2026) is retaining at 72% after month 1, which is above your historical average of 58%." | Med | AI interprets heatmap patterns |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| New/Retained/Resurrected/Churned stacked area | User lifecycle composition over time. Shows whether user base is growing from new users or shrinking from churn. | Med | Data directly from user_*_accounting fields in agg_daily_user_activity |
| Cohort-over-cohort trend line | Overlay retention curves for last 4 cohorts. Quick visual: "Are newer cohorts retaining better or worse?" | Med | Multiple line series on same ECharts axis |
| Behavioral cohort comparison | Group users by first action (e.g., "started with Sweeps" vs "started with plain runs") and compare retention. | High | Requires custom cohort definition logic beyond time-based. Defer to v2. |

---

### 3. Engagement Decay

**Purpose:** Detect individual user cold-going with week-over-week drop-off alerting.
**Data confidence:** HIGH (ext_daily_user_event_usage per-user daily data)
**Primary BQ source:** `ext_daily_user_event_usage`, `agg_daily_customer_engagement_score`

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| User cold-detection table | Ranked list of users whose activity dropped significantly (>50% WoW decline, or >14 days since last activity after being weekly-active). Names, last activity date, decline severity. | Med | Compare recent 2-week window vs prior 2-week window per user |
| Days-since-last-activity distribution | Histogram: how many users last active 0-7d ago, 8-14d, 15-30d, 31-60d, 60+d. Quick health check. | Low | Simple bucketing from MAX(date_day) per user |
| Engagement score trend (account-level) | Line chart of engagement score aggregated to account level over time. Shows trajectory. | Med | Direct query from agg_daily_customer_engagement_score |
| AI narrative: decay signals | "5 users who were active weekly have gone silent in the last 3 weeks. 2 of these are power users representing 40% of total activity." | Med | AI analyzes cold-detection output |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Per-user engagement sparklines | Tiny inline sparklines next to each user in the cold-detection table showing their activity over last 12 weeks. Instant visual of gradual vs sudden drop. | Med | ECharts mini charts or inline SVG sparklines |
| Decay severity color coding | Traffic light system: green (active), amber (declining), red (cold), grey (churned). Applied to user rows. | Low | CSS classes based on computed decay metrics |
| Champion risk flagging | Cross-reference with power_users: if a declining user is in the top-10 by activity, flag as "champion at risk" with special badge. | Med | JOIN between decay data and power user ranking |

---

### 4. Feature Velocity

**Purpose:** Per-product-area time-series showing acceleration/deceleration trends.
**Data confidence:** HIGH (extension of existing product area queries)
**Primary BQ source:** `ext_daily_user_event_usage` via existing `product_areas_query()`

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Sparkline grid: all product areas | Grid of small time-series charts (one per product area) showing monthly event counts. At-a-glance view of which areas are growing vs declining. | Med | ECharts grid layout with multiple small line series. Data from existing product_areas_query(). |
| Momentum indicators (arrows/badges) | Each product area gets an up/down/flat arrow based on recent trend (last 3 months vs prior 3 months). | Low | Simple percentage change calculation |
| Unique users trend (not just event volume) | Show unique users per product area over time alongside event counts. Breadth matters more than volume from power users. | Med | Already available in product_areas_query output (unique_users field) |
| AI narrative: velocity summary | "Weave Tracing is accelerating (+45% MoM in users), while Sweeps usage has been flat for 6 months. Artifacts showing deceleration: -12% over last quarter." | Med | AI interprets trend data |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Acceleration/deceleration heatmap | 2D heatmap: rows = product areas, columns = months, color = rate of change (green = accelerating, red = decelerating). Shows momentum shifts over time. | Med | Second-derivative calculation on monthly data. ECharts heatmap with diverging colormap. |
| Create-vs-view ratio per area | Split events into creation (artifact_created) vs consumption (artifact_viewed). High view/low create = dependent users; high create = producers. | Med | Already mapped in product_areas_query CASE statement. Needs event-level split. |
| Cross-area correlation | "When Experiments usage goes up, Artifacts follows 2 weeks later." Shows product area adoption chains. | High | Time-series cross-correlation. Defer to v2 -- statistical complexity not justified for v1. |

---

### 5. Team/Cluster Detection

**Purpose:** Group users by team fields and show per-team adoption patterns.
**Data confidence:** MEDIUM (team fields may not be populated for all accounts)
**Primary BQ source:** `ext_daily_user_event_usage` (org_name, is_part_of_team, count_teams)

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Team breakdown table | List teams (from org_name, is_part_of_team fields), member count, total activity, top product areas per team. | Med | GROUP BY org_name. Team fields may be sparse -- must handle gracefully. |
| Per-team activity bar chart | Horizontal bar chart comparing team total activity and unique users. Which team is the heaviest user? | Low | ECharts bar series |
| Team product area heatmap | Grid: rows = teams, columns = product areas, cells = usage intensity. Shows which teams use which products. | Med | Pivot of team x product area from daily usage data |
| Data availability warning | Clear message when team fields are not populated: "Team data unavailable for this account." | Low | Conditional rendering based on NULL check. Non-negotiable for MEDIUM confidence data. |
| AI narrative: team patterns | "The ML Platform team (12 users) accounts for 65% of all activity. The NLP team is Weave-heavy with no Experiments usage." | Med | AI interprets team breakdown data |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Team adoption timeline | When did each team start using W&B? Shows organizational spread over time. | Med | MIN(date_day) per org_name/team |
| Champion identification per team | Flag the most active user per team. SE knows who to contact for each team. | Low | MAX(total_events) per group, JOIN with user identity |
| Team growth trend | Is the team expanding (new users joining) or contracting (users dropping off)? | Med | COUNT DISTINCT users per team per month, stacked area |

---

### 6. Per-User Risk Scoring

**Purpose:** Composite risk score combining ML churn predictions, engagement signals, and revenue trends.
**Data confidence:** MEDIUM (renewal_predictions in different dataset -- landing_development)
**Primary BQ source:** `renewal_predictions`, `agg_daily_customer_engagement_score`, `stg_salesforce_accounts`, `dim_helpdesk_tickets`

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Composite risk score (account-level) | Single 0-100 score combining: ML churn probability, engagement trend slope, seat utilization rate, support ticket velocity. Displayed as gauge chart. | High | Weighted composite from 4+ data sources. Heaviest data integration of all 9 pages. |
| Risk factor breakdown | Show which factors contribute most to the risk score. "Churn model: 72%. Engagement: declining. Seats: 45% util. Support: 3 escalations." | Med | Decomposed display of composite score components |
| Risk trend line | How has the risk score changed over time? Line chart showing last 6 months. | Med | Requires historical composite score computation (recompute from historical data) |
| Renewal context | Days to renewal, ARR, contract details alongside risk score. Risk is meaningless without renewal timeline. | Low | Already available from account_health_query() |
| AI narrative: risk assessment | "HIGH RISK: 72% ML churn probability, declining engagement, 3 escalated tickets. Renewal in 47 days. Recommended: executive sponsor meeting." | Med | AI synthesizes risk factors into actionable assessment |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Risk radar chart | Radar chart with axes for each risk dimension (churn model, engagement, utilization, support, revenue trend). Shows risk shape at a glance. | Med | ECharts radar series. 5-6 dimensions normalized to 0-100. |
| Action recommendations | AI-generated next-best-actions: "Schedule QBR", "Run enablement workshop", "Engage champion X who has gone cold." | Med | AI prompt enriched with full risk context |
| Historical risk snapshots | Compare risk profile now vs 3 months ago vs 6 months ago. Shows whether interventions are working. | High | Requires score recomputation at historical points |

---

### 7. Usage Correlation

**Purpose:** Cross-account analysis of which product combos predict retention/expansion.
**Data confidence:** MEDIUM (cross-account queries, privacy considerations)
**Primary BQ source:** `ext_daily_user_event_usage` (cross-account), `stg_salesforce_accounts`

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Product combination matrix | Heatmap showing which product area combinations co-occur across accounts. "Accounts using Experiments + Artifacts retain 2x better." | High | Cross-account query. Aggregate only, no account names. |
| Current account positioning | "Your account uses: Experiments, Artifacts, Weave. Accounts with this combo have 85% retention rate." | Med | Match current account's product mix to correlation data |
| Next-best-action recommendation | "Accounts that added Model Registry after your current mix saw 23% higher expansion rates." | Med | AI-generated from correlation patterns |
| Privacy guard | Explicit "SE-Internal Only" badge. No individual account names in correlation data. | Low | CSS badge (already exists as internal-badge) + aggregate-only queries |
| AI narrative: correlation insights | "Your account matches the 'Platform Builder' archetype. These accounts expand at 2.1x the rate of Experiments-only accounts." | Med | AI interprets correlation patterns and archetypes |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Expansion signal indicators | Flag product areas approaching contract limits (Weave ingestion near cap, seats near contract). Predict upsell. | Med | Compare current usage to SFDC entitlement fields |
| Peer benchmarking (anonymized) | "Compared to similar-tier accounts, your Weave adoption is in the top quartile." | High | Cross-account percentile computation |
| ARR-usage overlay | Scatter plot: x = product breadth, y = ARR. Shows usage-revenue correlation across accounts. | Med | JOIN usage data with SFDC ARR. SE-internal only. |

---

### 8. SDK Version Distribution

**Purpose:** CLI/SDK version distribution per customer with version freshness and upgrade recommendations.
**Data confidence:** HIGH (cli_version, local_version in BQ confirmed)
**Primary BQ source:** `ext_daily_user_event_usage` (cli_version, local_version), `ext_weekly_library_usage`

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Version distribution donut chart | What versions are users running? Donut chart with version segments. Most common version highlighted. | Low | GROUP BY cli_version. ECharts pie series. |
| Version freshness assessment | Compare customer's versions against latest released version. "68% of users are 2+ major versions behind." | Med | Requires knowing current latest version (hardcoded at generation time or fetched from PyPI) |
| User-to-version mapping table | Table: username, cli_version, local_version, last_activity. Shows who needs to upgrade. | Low | Direct query with dim_users JOIN for identity resolution |
| Version trend over time | Stacked area chart showing version distribution shifts month-over-month. Are users upgrading? | Med | Monthly GROUP BY cli_version, pivoted to stacked area |
| AI narrative: version assessment | "78% on SDK 0.16.x (current). 15% on 0.14.x (2 major behind). Recommend: targeted upgrade comms to 8 users on 0.14.x." | Med | AI interprets distribution data |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Library usage breakdown | Which integrations are in use? (PyTorch, TensorFlow, HuggingFace, etc.) from ext_weekly_library_usage. | Med | Separate BQ table. Complementary to SDK versions. |
| Upgrade recommendation with user list | Exportable list of users who need upgrades, with contact info. SE can forward to customer champion. | Low | Copy-to-clipboard of user + version + email table |
| Version-to-issues correlation | Do users on older versions file more support tickets? | High | Complex JOIN. Defer to v2 -- unclear data quality at the join. |

---

### 9. Performance Deep Dive

**Purpose:** Application performance signals, narrative-driven analysis of latency, chart load, artifact perf.
**Data confidence:** LOW for Datadog, HIGH for BQ perf tables (fct_application_performance confirmed)
**Primary BQ source:** `fct_application_performance`, `fct_onscreen_loader_latencies`, `agg_daily_team_members_slow_chart_loads`

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Performance index gauge | Overall application_performance_index as gauge chart. Quick health indicator. | Low | fct_application_performance has this field. ECharts gauge series. |
| Per-feature slowness breakdown | Bar chart of slow_charts, slow_project_search, slow_artifact_creating, etc. Which areas have perf issues? | Med | Multiple slow_* columns from fct_application_performance |
| Error metrics | users_facing_errors_ct, error_count as KPI cards with trend. | Low | Direct from fct_application_performance |
| Chart load latency distribution | Histogram or box plot of chart load times from fct_onscreen_loader_latencies. | Med | Data confirmed in BQ schema doc |
| AI narrative: performance assessment | "Performance GOOD overall (index: 82/100). Chart loads slow for 3 teams (avg 4.2s vs target <2s). Artifact creation latency spiked 3x last week." | Med | AI interprets performance metrics |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Performance trend over time | Line chart of performance_index over weeks/months. Is experience improving or degrading? | Med | Time-series from fct_application_performance |
| Team-level performance comparison | Which teams experience worst performance? | Med | Per-team aggregation from agg_daily_team_members_slow_chart_loads |
| Support ticket correlation | Overlay ticket volume with performance dips. "Perf degradation on Mar 10 = 5 new tickets." | High | Complex JOIN across data sources. Defer if data quality unclear. |
| NPS correlation | Display NPS scores alongside performance metrics. Low perf = low NPS? | Low | min_nps_score field available in fct_application_performance |

---

## Feature Dependencies

```
Account Health Query ----------------> Risk Scoring (needs churn predictions, ARR, renewal)
                     ----------------> Usage Correlation (needs SFDC entitlements for expansion signals)

Product Areas Query -----------------> Feature Velocity (extends product area monthly data)
                    -----------------> Team Detection (product area x team matrix)
                    -----------------> User Journey (product stages from same mapping)

Power Users Query -------------------> Engagement Decay (cold-detection on same user set)
                  -------------------> Team Detection (champion identification per team)

dim_users table ---------------------> User Journey (first_*_at fields = primary data)
                ---------------------> Cohort Analysis (signup date for cohort definition)
                ---------------------> SDK Versions (user identity resolution)

ext_daily_user_event_usage ----------> Engagement Decay (per-user daily data)
                           ----------> Team Detection (team/org fields)
                           ----------> SDK Versions (cli_version, local_version)
                           ----------> Feature Velocity (daily events by product area)

renewal_predictions -----------------> Risk Scoring (ML churn probability)

fct_application_performance ---------> Performance (standalone, minimal dependencies)

Cross-account queries ---------------> Usage Correlation (multiple accounts, privacy-sensitive)
```

### Build Order Implications

| Tier | Pages | Rationale |
|------|-------|-----------|
| **Tier 1: No/low dependencies, high confidence** | SDK Versions, Feature Velocity, Performance | Standalone data sources, proven query patterns, quick wins |
| **Tier 2: Single primary table, high confidence** | User Journey, Engagement Decay | dim_users and daily usage are well-understood, moderate query complexity |
| **Tier 3: Multiple sources, medium confidence** | Cohort Analysis, Team Detection | Retention tables need exploration, team fields may be sparse |
| **Tier 4: Heavy integration, highest risk** | Risk Scoring, Usage Correlation | 3+ data sources, cross-account queries, privacy review needed |

---

## Interaction Patterns (All Pages)

### Must Have

| Pattern | Implementation | Rationale |
|---------|---------------|-----------|
| ECharts tooltip on hover | Default ECharts tooltip with formatted values | SEs need exact numbers, not just visual trends |
| ECharts DataZoom (time axis) | Slider zoom on time-series charts | "Zoom into Q4" without regenerating the report |
| Save chart as PNG | ECharts toolbox saveAsImage | SEs paste charts into Slack and slide decks daily |
| Copy AI narrative text | Small clipboard icon next to AI summary sections | SEs copy/paste insights into emails and Jira comments |
| Sortable tables | Client-side JS sort on table headers | Power user table, version table, team table all need sorting |

### Nice to Have

| Pattern | Implementation | Rationale |
|---------|---------------|-----------|
| Click-to-highlight in charts | ECharts series emphasis on click | Focus on one product area or team in busy charts |
| ECharts brush/select | Brush tool for selecting regions of scatter plots | Useful in Usage Correlation scatter, Performance distribution |
| Expand/collapse sections | Accordion-style sections with initial state: expanded | Long pages benefit from collapsible sections |
| Jump-to-section nav | Fixed sidebar or top nav with anchor links | Pages with 4+ sections need navigation |
| Print-optimized CSS | `@media print` rules hiding interactive controls | Clean printout for offline review |

---

## MVP Recommendation

### Prioritize (Build First)

1. **Feature Velocity** -- extends existing product_areas_query() directly. Highest confidence data. Immediately useful: "which product areas are growing vs declining" is the top SE question. Also establishes the sparkline-grid pattern reusable by other pages.
2. **Engagement Decay** -- cold-user detection is the highest-urgency SE need. "Who stopped using the product?" drives immediate action. Directly actionable output.
3. **User Journey** -- Sankey visualization is the most visually compelling differentiator vs existing Hex dashboards. dim_users data is high confidence. The "wow factor" page for customer conversations.
4. **SDK Version Distribution** -- simplest to build (donut chart + table), high confidence data, immediately actionable ("tell customer to upgrade"). Quick win that proves the template pattern.

### Build Second

5. **Performance Deep Dive** -- standalone data source, low dependency. Proactive performance conversation is a differentiator vs reactive support.
6. **Team Detection** -- valuable but team field population is uncertain (MEDIUM confidence). Build with graceful degradation for missing data.
7. **Cohort Analysis** -- retention heatmap is powerful but requires more complex data pipeline. Retention table schema exploration needed before build.

### Build Last (Highest Complexity/Risk)

8. **Risk Scoring** -- requires 3+ data sources (churn model, engagement, SFDC, support). Most complex composite calculation. Build after individual data sources are proven by other pages.
9. **Usage Correlation** -- cross-account queries are privacy-sensitive and computationally expensive. Requires careful aggregation strategy. Build after all single-account pages are solid.

### Defer Entirely (v2+)

- **Behavioral cohort comparison** (within Cohort Analysis): High complexity, niche use case
- **Cross-area correlation** (within Feature Velocity): Statistical complexity not justified for v1
- **Version-to-issues correlation** (within SDK Versions): Complex JOIN, unclear data quality
- **Historical risk snapshots** (within Risk Scoring): Requires score storage or recomputation

---

## Sources

- Existing codebase: `queries.py`, `usage.py`, `usage-report-internal.html`, `usage-report-external.html` (HIGH confidence -- direct inspection)
- [W&B BigQuery Schema Discovery](~/Documents/gitstuff/ai-docs/wandb-bigquery-schema-discovery.md) (local ai-doc, 2026-03-24)
- [W&B Usage Visualization Discovery](~/Documents/gitstuff/ai-docs/wandb-usage-visualization.md) (local ai-doc, 2026-03-24)
- PROJECT.md constraints and data confidence ratings
- [Cohort Analysis Guide for SaaS](https://userpilot.medium.com/cohort-analysis-comprehensive-guide-for-saas-0e66278e1b9d) (MEDIUM confidence)
- [Heatmap Visualization Guide 2025](https://chartgen.ai/resources/blog/heatmap-data-visualization-complete-guide-examples) (MEDIUM confidence)
- [Visualizing Customer Journey Using A Sankey Diagram](https://www.expressanalytics.com/blog/visualizing-customer-journey-using-sankey-diagram) (MEDIUM confidence)
- [Churn Prediction Model: Spot Risk Before It's Too Late](https://www.june.so/blog/churn-prediction-model) (MEDIUM confidence)
- [User Engagement Scoring: Frameworks for B2B SaaS](https://www.wudpecker.io/blog/user-engagement-scoring-frameworks-for-b2b-saas) (MEDIUM confidence)
- [Apache ECharts Cheat Sheet](https://echarts.apache.org/en/cheat-sheet.html) (HIGH confidence -- official docs)
- [Best Product Analytics Tools 2026](https://visionlabs.com/blog/best-product-analytics-tools/) (LOW confidence -- vendor comparison)
- [Customer Health Score Guide](https://www.custify.com/blog/customer-health-score-guide/) (MEDIUM confidence)
- [Drill Down Reports Guide](https://improvado.io/blog/drill-down-reports-guide) (MEDIUM confidence)
- [Best Analytics Tools for SaaS 2026](https://www.mitzu.io/post/top-5-analytics-tools-for-saas-in-2025) (LOW confidence)
- [Customer Health Tracking Software 2026](https://www.vitally.io/post/the-best-customer-health-tracking-software) (LOW confidence)
