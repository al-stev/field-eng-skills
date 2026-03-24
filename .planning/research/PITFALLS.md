# Domain Pitfalls

**Domain:** BigQuery deep analytics -- per-user dashboards, cohort analysis, churn visualization, cross-account correlation
**Project:** BQ Deep Analytics -- Usage Intelligence Expansion
**Researched:** 2026-03-24

---

## Critical Pitfalls

Mistakes that cause rewrites, data integrity failures, or uncontrolled BQ spend.

### Pitfall 1: Uncontrolled Query Cost from Wide Table Scans

**What goes wrong:** The primary data source (`ext_daily_user_event_usage`) has 100+ columns. Each new analytics page adds queries against this table. With BQ on-demand pricing, every query that touches this table scans ALL referenced columns across the full date range. Nine new pages each running 2-3 queries = 18-27 full-width scans per report generation. At scale, this becomes a meaningful cost problem on the `wandb-sa-sandbox` project.

**Why it happens:** Developers copy existing query patterns (like `seat_utilization_query()`) that already SELECT specific columns but fail to apply the same discipline in new, exploratory queries. During development, `SELECT *` creeps in for debugging. `LIMIT 100` gives a false sense of cost safety -- BQ scans the full table first, then limits rows returned. The 100+ column mega-table tempts grabbing "everything we might need."

**Consequences:**
- BQ bills for bytes scanned, not rows returned. A single `SELECT *` on a multi-TB table costs the same whether you read 100 rows or 10M.
- Sandbox project quota exhaustion blocks ALL SE BQ operations, not just this tool.
- No per-query cost visibility in the current `bq_client.py` -- failures are silent until the monthly bill arrives.

**Prevention:**
1. **Column pruning is mandatory**: Every query function must explicitly name columns. Ban `SELECT *` in query factory functions. Code review gate.
2. **Add bytes-processed logging**: After each `client.query()` call, log `job.total_bytes_processed` and `job.total_bytes_billed`. Add a warning threshold (e.g., >500MB per query).
3. **Set `maximum_bytes_billed`** on `QueryJobConfig` as a safety net. Start with 1GB per query; raise only with justification. BQ will abort queries that exceed this.
4. **Pre-aggregate with CTEs**: The existing `product_areas_query()` pattern is correct -- use CTEs to filter rows early (by `account_id` and `date_day` range) before any aggregation. Never aggregate first, filter later.
5. **Consider materialized views** for the most expensive repeated patterns (e.g., user journey milestones from `dim_users`) if generation frequency justifies it.

**Detection:** Add a `--dry-run` flag to query functions that calls `client.query(sql, job_config=config).dry_run` to report bytes scanned without executing. Run this in CI or before committing new query functions.

**Phase impact:** ALL phases. Must be addressed in the very first query implementation.

**Confidence:** HIGH -- verified against BQ pricing docs and existing codebase patterns.

---

### Pitfall 2: Schema Assumptions on Unvalidated Tables

**What goes wrong:** The project plan lists 7+ BQ tables across two datasets (`analytics` and `landing_development`). The existing query factory validates only 4 tables (`ext_daily_user_event_usage`, `agg_daily_company_usage`, `stg_salesforce_accounts`, `dim_users`). The remaining tables -- `agg_weekly_user_retention_features`, `agg_weekly_user_returning_active_status`, `fct_user_activity_dates`, `renewal_predictions`, `fct_application_performance`, `agg_daily_team_members_slow_chart_loads` -- have schemas documented from `INFORMATION_SCHEMA` discovery but NOT validated with actual query execution against real customer data.

**Why it happens:** Schema discovery via `INFORMATION_SCHEMA.COLUMNS` tells you column names and types but NOT: whether columns are actually populated (vs. all NULL), whether partition/clustering matches your query patterns, whether the table has data for your specific customer's account_id, or whether computed columns (like `churn_probability`) contain stale/outdated model outputs.

**Consequences:**
- Queries succeed but return empty DataFrames. Pages render with "No data available" for specific customers.
- Worse: queries return data but key columns are NULL for certain deployment types (e.g., `is_part_of_team` might be NULL for server deployments, `org_name` populated only for cloud).
- `renewal_predictions` is in `landing_development` dataset -- different access permissions than `analytics`. Query may fail with 403 if sandbox project lacks cross-dataset read permission.

**Prevention:**
1. **Schema validation phase FIRST**: Before building any visualization, run each new table through a validation script: `SELECT column_name, COUNT(*) as non_null_count, COUNT(DISTINCT value) as cardinality FROM table WHERE account_id = @test_account LIMIT 1000`. Document which columns are reliably populated.
2. **Test with multiple customer types**: At minimum, test against one SaaS customer, one dedicated-cloud customer, and one server customer. The `customers.yaml` already has deployment_type metadata to drive this.
3. **Defensive query patterns**: Every query function must handle empty results gracefully. The existing `_is_empty()` pattern in `usage.py` is the right model -- extend it to every new builder function.
4. **Verify `landing_development` access early**: Run a simple `SELECT 1 FROM landing_development.renewal_predictions LIMIT 1` from `wandb-sa-sandbox` before writing any churn prediction queries. If it fails, the entire Risk Scoring page needs a fallback strategy.

**Detection:** Schema validation failures manifest as empty charts, not errors. Add data quality assertions to the pipeline: if a query returns 0 rows for a customer known to have activity, emit a warning, not silent success.

**Phase impact:** Must be the FIRST task in every phase that introduces a new BQ table. The Cohort Analysis, Risk Scoring, and Performance Deep Dive phases are highest risk because they use previously untested tables.

**Confidence:** HIGH -- based on direct codebase analysis showing only 4 of 7+ tables have been query-tested.

---

### Pitfall 3: Identity Resolution Fails Silently for Server Deployments

**What goes wrong:** Server deployments (self-hosted W&B) do not populate `username` or `email` in `ext_daily_user_event_usage`. The existing `power_users_query()` correctly handles this with a `LEFT JOIN dim_users` to resolve `local_username` and `local_user_email`. But 9 new analytics pages will each need user-level data, and every single one must implement this same JOIN pattern. Missing the JOIN on even one page means server customers see "user-a3f7b2c1" instead of "jane.smith@company.com" in their per-user analytics.

**Why it happens:** Cloud deployment data is complete -- username and email are populated directly. Developers test against cloud customers first (because they're easier), see working results, and ship. Server customer identity resolution is invisible until someone runs the tool against a server deployment and notices anonymous UUIDs everywhere.

**Consequences:**
- Per-user analytics pages (User Journey, Engagement Decay, Per-User Risk Scoring) become useless for server customers -- SEs cannot identify which specific users are at risk or disengaged.
- Cohort analysis groups "unknown" users together, creating misleading cohort sizes.
- Team detection relies on `is_part_of_team` and `org_name` fields that may also be NULL for server deployments.

**Prevention:**
1. **Create a shared user-resolution CTE**: Extract the `dim_users` JOIN pattern into a reusable CTE or subquery function in `queries.py`. Every user-level query must use this CTE rather than reimplementing the JOIN.
2. **Add a `deployment_type` parameter to query functions**: When deployment_type is "server", automatically include the `dim_users` JOIN and additional identity resolution logic. Pull deployment_type from `customers.yaml` at pipeline entry.
3. **Test matrix must include server customers**: Before any user-level page is considered complete, it must be tested against a server deployment customer. If no server customer exists in `customers.yaml`, add one or create a test fixture.
4. **Fallback display**: When identity cannot be resolved even after the JOIN, display the `universal_user_id` prefix with a clear "(server user -- identity unavailable)" label rather than a cryptic truncated UUID.

**Detection:** Add an assertion in the rendering layer: if >50% of users in a result set have NULL username AND NULL email after the JOIN, emit a warning that identity resolution may be incomplete for this deployment type.

**Phase impact:** Every phase that includes per-user visualizations: User Journey, Engagement Decay, Team Detection, Per-User Risk Scoring.

**Confidence:** HIGH -- directly observed in existing `power_users_query()` code and `PROJECT.md` constraint documentation.

---

### Pitfall 4: Cross-Account Correlation Leaks Customer Data

**What goes wrong:** The Usage Correlation page (Direction 7) involves cross-account analysis -- comparing product adoption patterns across customers to find "which product combos predict retention." This requires querying data for multiple accounts in a single query or combining results. If the output HTML file accidentally includes other customers' data (even anonymized), or if benchmark comparisons can be reverse-engineered to identify specific accounts, you have a data privacy breach.

**Why it happens:** The temptation is to run a single BQ query with `WHERE account_id IN (list_of_accounts)` to build correlation models. The resulting dataset, even after aggregation, may contain enough specificity (e.g., "an Enterprise server customer in financial services with 200 seats and Weave adoption") to identify individual accounts. The existing codebase has no cross-account query patterns -- every query is parameterized to a single `@account_id`.

**Consequences:**
- SE accidentally shares a correlation page with a customer that reveals competitive intelligence.
- Internal compliance violation if customer data is combined without data governance review.
- Reputational risk -- W&B customers trust that their usage data is not benchmarked against competitors without consent.

**Prevention:**
1. **Never include raw cross-account data in output HTML**: The correlation page should show only the CURRENT customer's position relative to anonymized, pre-aggregated benchmarks. Benchmarks should be computed separately and stored as static reference data, not computed at report generation time.
2. **Minimum cohort size for benchmarks**: Any benchmark group must contain at least 10 accounts. If fewer than 10 accounts match the comparison criteria, suppress the benchmark entirely rather than showing a small-n comparison that could be de-anonymized.
3. **Separate the correlation pipeline**: Cross-account queries should run as a separate, periodic batch job (not at report generation time). The output is a static benchmark file (e.g., `benchmarks.json`) that individual customer reports reference. This creates an air gap between cross-account analysis and per-customer reporting.
4. **Label everything SE-INTERNAL**: The correlation page must include prominent "INTERNAL USE ONLY -- NOT FOR CUSTOMER DISTRIBUTION" watermarking. This is already the pattern for internal reports (the `internal` flag in `build_usage_json()`).
5. **No customer names in benchmark data**: Benchmark data must use only aggregated statistics (median, p25, p75) with cohort labels like "Enterprise SaaS, 100-500 seats" -- never account names, account IDs, or identifiable characteristics.

**Detection:** Code review gate: any query function that does NOT filter by `@account_id` must be flagged for privacy review. Add a lint check in the query factory.

**Phase impact:** Primarily the Usage Correlation phase. Also relevant to Per-User Risk Scoring if it references cross-account churn model training data.

**Confidence:** HIGH -- this is a well-known data governance risk in multi-tenant analytics.

---

### Pitfall 5: Churn Prediction Scores Presented Without Context Mislead SEs

**What goes wrong:** The `renewal_predictions` table contains ML model outputs (`churn_probability` at 3-month and 5-month horizons). Displaying these as "45% churn risk" in a dashboard without context leads SEs to either panic unnecessarily or dismiss the signal entirely. The model's calibration, training data recency, and feature importance are opaque to the consumer.

**Why it happens:** ML churn scores are point estimates from a model trained on historical data. The model may be stale (last trained months ago), biased toward certain deployment types, or miscalibrated (a "45% churn probability" might actually mean "this account looks similar to accounts that churned 20% of the time"). The existing `account_health_query()` already pulls these scores but doesn't contextualize them.

**Consequences:**
- SE takes drastic action (emergency QBR, executive escalation) based on a high churn score that's actually a model artifact.
- SE ignores legitimately concerning churn score because previous false positives eroded trust.
- Customer receives inappropriate messaging ("we noticed your usage declining...") when the ML signal was wrong.
- Revenue team makes incorrect forecasts based on dashboard-surfaced churn probabilities.

**Prevention:**
1. **Show confidence intervals, not point estimates**: Display churn probability as a range (e.g., "35-55% risk") rather than a precise number. If the model doesn't provide confidence intervals, display a qualifier like "MODEL ESTIMATE -- verify with engagement data."
2. **Combine ML score with behavioral signals**: The Per-User Risk Scoring page should show the ML churn score alongside corroborating evidence: seat utilization trend, power user activity decline, support ticket volume. When signals agree, confidence is higher. When they disagree, flag the discrepancy.
3. **Display model freshness**: Show when the `inference_timestamp` was for the churn prediction. If it's older than 30 days, dim the score and label it "STALE MODEL OUTPUT." The existing query uses `QUALIFY ROW_NUMBER() OVER (... ORDER BY inference_timestamp DESC)` which gets the latest, but "latest" might still be months old.
4. **Use traffic-light bucketing, not raw percentages**: Map churn probabilities to actionable categories: Green (<25%), Amber (25-50%), Red (>50%). This reduces false precision and encourages appropriate response levels.
5. **Document model limitations in the page itself**: Include a small "About this score" expandable section explaining what the model does and does not account for.

**Detection:** Track the `inference_timestamp` from `renewal_predictions`. If the most recent prediction is older than 60 days, the entire Risk Scoring page should show a prominent "CHURN MODEL DATA IS STALE" banner.

**Phase impact:** Per-User Risk Scoring phase. Also affects the AI narrative generation if it references churn scores.

**Confidence:** MEDIUM -- the `renewal_predictions` table structure is confirmed via schema discovery, but model calibration quality and refresh frequency are unknown. Needs validation.

---

## Moderate Pitfalls

### Pitfall 6: ECharts Rendering Bottleneck with Per-User Daily Data

**What goes wrong:** Per-user daily event data for a large enterprise customer can easily produce 50,000+ data points (500 users x 365 days x multiple event types). ECharts performance degrades significantly above 10,000 data points, causing browser freezes, slow initial renders, and zoom/pan interactions that crash the page.

**Why it happens:** The existing reports aggregate data to weekly or monthly granularity before charting. But deep analytics pages (Engagement Decay, User Journey) need daily or even per-event granularity to show individual user trajectories. Dumping all this data into a single ECharts series without pre-aggregation overwhelms the Canvas renderer.

**Prevention:**
1. **Pre-aggregate in SQL, not JavaScript**: Compute weekly rollups in the BQ query using `DATE_TRUNC(date_day, WEEK)` or `DATE_TRUNC(date_day, MONTH)` depending on the time range. The existing `aggregate_weekly()` in `queries.py` is the right pattern -- use it consistently.
2. **Progressive detail loading**: Show monthly aggregates by default. Add a "zoom to weekly" interaction that re-renders with finer granularity only for the selected time window.
3. **Limit series count**: For per-user charts, show only the top N users (20-30) with an "Others" aggregate line. The existing `power_users_query()` LIMIT 20 pattern is correct.
4. **Use ECharts `large` mode**: For scatter plots and line charts with >5,000 points, enable `large: true` and `largeThreshold: 2000` in the series config. This switches to a GPU-accelerated rendering path.
5. **Downsample for overview, full resolution for focus**: Implement a two-tier data strategy where the initial render uses sampled data and drill-down requests the full dataset.

**Detection:** Test each page with the largest customer in `customers.yaml`. If initial render takes >3 seconds or zoom causes a visible lag, the page needs data reduction.

**Phase impact:** Engagement Decay, User Journey, and Team Detection pages are highest risk due to per-user daily granularity requirements.

**Confidence:** HIGH -- verified via ECharts GitHub issues (#15332, #14033) documenting performance degradation above 10K points.

---

### Pitfall 7: Team Field Sparsity Makes Team Detection Unreliable

**What goes wrong:** The Team/Cluster Detection page (Direction 5) relies on `is_part_of_team`, `count_teams`, and `org_name` fields in `ext_daily_user_event_usage`. These fields are populated by W&B's cloud infrastructure. For server deployments, these fields may be NULL or contain default values. Even for cloud customers, team creation is optional -- many organizations use W&B without formally creating teams, meaning all users appear as "no team."

**Why it happens:** Teams in W&B are an organizational feature, not a technical requirement. Small or ad-hoc deployments may never create teams. Server deployments may not sync team metadata to BQ. The field `org_name` refers to the W&B organization, not the customer's internal team structure -- conflating these creates misleading groupings.

**Prevention:**
1. **Validate team field population before rendering**: Query `SELECT COUNT(DISTINCT universal_user_id) as total_users, COUNTIF(is_part_of_team = TRUE) as team_users FROM ext_daily_user_event_usage WHERE account_id = @account_id` as a pre-check. If <20% of users have team data, suppress the Team Detection page entirely and show a message explaining why.
2. **Fallback to behavioral clustering**: When team fields are sparse, offer an alternative view that clusters users by product area usage patterns (users who use Experiments + Artifacts vs. users who use Weave + Evaluations) rather than organizational team assignment.
3. **Distinguish "org" from "team"**: `org_name` is the W&B organization, which typically maps to a deployment instance, not an internal team. A customer with one organization but 50 teams has useful team data; a customer with 5 organizations and no teams has useful org data. Handle both cases.
4. **Document the limitation**: The Team Detection page should include a data quality indicator showing "Team data available for X% of users."

**Detection:** If the pre-check query returns <20% team coverage, the pipeline should flag this and either suppress the page or switch to the behavioral clustering fallback.

**Phase impact:** Team/Cluster Detection phase. Also affects any page that tries to show "per-team" breakdowns.

**Confidence:** MEDIUM -- team field existence confirmed via schema discovery, but population rates per customer are unknown. Needs per-customer validation.

---

### Pitfall 8: Cohort Date Alignment Errors Distort Retention

**What goes wrong:** Cohort retention analysis requires aligning users by their "Day 0" (first activity date), then measuring retention at Day 7, Day 30, Day 90, etc. A common mistake is aligning by calendar date instead of tenure, which groups users at different lifecycle stages together and produces meaningless retention curves. Another mistake is using `first_run_at` from `dim_users` as Day 0 when the actual first activity might be an Artifact view or Weave call that predates the first run.

**Why it happens:** `dim_users` has multiple "first" fields: `first_run_at`, `first_sweep_at`, `first_artifact_at`, etc. Choosing the wrong "first" field as the cohort anchor produces cohorts where some users "started" months before their actual first meaningful activity. Additionally, users who were created but never activated (claimed seats with no activity) pollute the cohort if not filtered out.

**Prevention:**
1. **Define "Day 0" explicitly per analysis type**: For product adoption cohorts, use the EARLIEST of all `first_*_at` fields as Day 0. For feature-specific cohorts (e.g., "Weave adoption"), use the feature-specific first date.
2. **Filter inactive users**: Exclude users with zero total events from cohort analysis. A claimed seat with no activity is not a "churned user" -- it's a never-activated seat. These are different signals.
3. **Use `DATE_DIFF` for tenure, not calendar subtraction**: `DATE_DIFF(activity_date, first_activity_date, WEEK)` gives correct tenure-aligned weeks. Never group by `FORMAT_DATE('%Y-%W', date_day)` for retention -- that's calendar alignment.
4. **Validate cohort sizes**: If a cohort has <5 users, suppress that cohort row in the heatmap. Small cohorts produce noisy retention rates (one user returning = 100% retention).

**Detection:** Cross-check: the sum of all cohort sizes should approximately equal the total distinct users for the account. If it's significantly different, users are being double-counted or dropped.

**Phase impact:** Cohort Analysis phase.

**Confidence:** HIGH -- well-documented retention analysis pitfall verified across multiple data engineering sources.

---

### Pitfall 9: `wandb-sa-sandbox` vs `wandb-production` Permission Asymmetry

**What goes wrong:** BQ queries run in `wandb-sa-sandbox` (the job project) but read data from `wandb-production` datasets. This works for the `analytics` dataset because the sandbox service account has read access. But `landing_development.renewal_predictions` is in a DIFFERENT dataset that may have different IAM policies. Additionally, `INFORMATION_SCHEMA` queries behave differently when run from a cross-project context -- some metadata views require `bigquery.tables.list` permission on the target project, which the sandbox account may not have.

**Why it happens:** The existing 4 queries all target `wandb-production.analytics.*` tables. The expansion introduces queries against `landing_development` (churn predictions), `fct_application_performance` (performance metrics), and potentially other datasets. Each dataset has independent IAM policies. "It worked for analytics" does not mean "it works for every dataset in wandb-production."

**Prevention:**
1. **Permission validation script**: Create a validation function that attempts a `SELECT 1 FROM [table] LIMIT 1` for every table the deep analytics pages will use. Run this once during setup and on demand when adding new tables.
2. **Graceful degradation per table**: If `renewal_predictions` is inaccessible, the Risk Scoring page should still render using behavioral signals only, with a note that "ML churn scores unavailable -- insufficient BQ permissions."
3. **Document required permissions**: Add a section to the BigQuery SKILL.md listing every dataset and table required, with the minimum IAM roles needed.
4. **Test INFORMATION_SCHEMA access**: Some new tables may need schema exploration. Verify that `SELECT * FROM wandb-production.landing_development.INFORMATION_SCHEMA.COLUMNS WHERE table_name = 'renewal_predictions'` works from the sandbox project.

**Detection:** Wrap each query execution in a try/except that specifically catches `google.api_core.exceptions.Forbidden` (403) errors and reports which table/dataset failed, distinct from other error types.

**Phase impact:** Risk Scoring phase (landing_development access), Performance Deep Dive phase (fct_application_performance access). Must be validated before those phases begin.

**Confidence:** MEDIUM -- the access split is documented in PROJECT.md and bq_client.py, but actual permission boundaries for non-analytics datasets are untested.

---

### Pitfall 10: Self-Contained HTML File Size Explosion

**What goes wrong:** Each analytics page embeds its data as inline JSON in the HTML file. For a large enterprise customer, per-user daily data for 12 months can produce 5-10MB of JSON. Nine pages times 5MB = 45MB of HTML files per customer. These files become slow to open, impossible to email, and strain version control if accidentally committed.

**Why it happens:** The existing usage reports work with small, pre-aggregated datasets (weekly seat counts, monthly Weave ingestion). The deep analytics pages need much more granular data. The self-contained HTML requirement (no server, ECharts CDN only) means all data must be inlined.

**Prevention:**
1. **Aggressive server-side aggregation**: Never embed raw per-user-per-day data. Pre-aggregate in the Python pipeline to the minimum granularity needed for each chart. For user journey: one row per user (not per day). For cohort heatmap: one cell per cohort-week combination. For engagement decay: weekly rollups per user.
2. **Set a file size budget**: Target <2MB per HTML page. If the JSON payload exceeds 1MB, the aggregation is too fine-grained.
3. **Compress embedded data**: Use a simple JavaScript decompression (e.g., base64-encoded gzip) for the data payload if aggregation alone doesn't bring size under budget.
4. **Add to `.gitignore`**: The `customers/` directory is already gitignored. Ensure all generated HTML output goes there, never into tracked directories.

**Detection:** Add a post-generation check: if any HTML file exceeds 2MB, warn the user and suggest reducing the time range or user count.

**Phase impact:** All phases. Most acute for Engagement Decay (per-user daily data) and Cohort Analysis (large heatmap matrices).

**Confidence:** HIGH -- based on data volume estimates from existing query results and the self-contained HTML constraint.

---

## Minor Pitfalls

### Pitfall 11: Timezone Inconsistency in Date Fields

**What goes wrong:** BQ tables store dates as `DATE` (no timezone) or `TIMESTAMP` (UTC). `ext_daily_user_event_usage.date_day` is a DATE. `renewal_predictions.inference_timestamp` is a TIMESTAMP. When combining data from different tables, naive date comparisons can be off by one day depending on the customer's timezone.

**Prevention:** Always use `DATE()` to truncate timestamps before comparison. Document that all analytics are in UTC. Do not attempt per-customer timezone conversion -- the complexity is not worth the marginal accuracy gain for weekly/monthly aggregations.

**Phase impact:** Any phase combining data from multiple tables.

**Confidence:** HIGH.

---

### Pitfall 12: Weave Suppression Logic Not Propagated to New Pages

**What goes wrong:** The existing pipeline suppresses Weave sections when `weave_customer=False` (from `stg_salesforce_accounts`). New analytics pages that show Weave-related data (Feature Velocity for Weave product areas, SDK versions for Weave SDK) must also implement this suppression. Missing it means non-Weave customers see empty Weave sections that suggest they should be using a product they haven't purchased.

**Prevention:** Centralize the Weave suppression check in the pipeline entry point, not in each page template. Pass a `weave_enabled` flag to all rendering functions. The existing pattern in `build_usage_json()` (lines 441-445) is correct but needs to be replicated in whatever pipeline feeds the new pages.

**Detection:** Test with a non-Weave customer. Any Weave-labeled section that appears is a bug.

**Phase impact:** Feature Velocity, SDK Version Distribution, and any page that includes Weave-specific product areas.

**Confidence:** HIGH -- directly observed in existing codebase.

---

### Pitfall 13: Datadog Performance Data May Not Exist in BQ

**What goes wrong:** The Performance Deep Dive (Direction 9) was originally scoped as requiring Datadog data. The schema discovery found `fct_application_performance` in BQ which has performance metrics (slow_charts, slow_project_search, application_performance_index, etc.), potentially eliminating the Datadog dependency. But this table's data freshness, coverage across customer types, and actual utility for SE conversations is unvalidated.

**Prevention:** Validate `fct_application_performance` early in the project. If it contains useful data, the Performance Deep Dive can proceed as a BQ-only page. If not, either descope Direction 9 or defer it to a later milestone that addresses Datadog integration.

**Detection:** Run `SELECT DISTINCT account_id, MAX(date_day) as latest FROM fct_application_performance GROUP BY 1 ORDER BY 2 DESC LIMIT 10` to check data freshness and coverage.

**Phase impact:** Performance Deep Dive phase. This is the lowest-confidence direction in the project.

**Confidence:** LOW -- table existence confirmed but data quality and coverage unknown. Needs direct validation.

---

### Pitfall 14: Product Area Mapping Drift

**What goes wrong:** The product area mapping in `product_areas_query()` maps event type strings to W&B marketecture areas. When W&B adds new event types (e.g., new Weave features, new automation types), they appear in BQ as new event strings but fall into the "Other" bucket because the mapping is hardcoded. The analytics pages silently under-report adoption of new features.

**Prevention:** Periodically audit unmapped events by running `SELECT DISTINCT event FROM ext_daily_user_event_usage WHERE event NOT IN ([mapped_events]) ORDER BY 1` and updating the CASE statement. Consider adding a "Recently added events" section to the Feature Velocity page that highlights events not yet mapped.

**Detection:** If the "Other" category in product area breakdowns exceeds 10% of total events, new event types likely need mapping.

**Phase impact:** Feature Velocity and Product Area pages. Should be checked quarterly.

**Confidence:** MEDIUM -- the mapping exists and works today, but W&B ships new features regularly that add event types.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation | Severity |
|-------------|---------------|------------|----------|
| User Journey Analysis | Cohort date alignment (#8), Identity resolution (#3) | Define Day 0 explicitly; use shared user-resolution CTE | High |
| Cohort Analysis | Date alignment (#8), Schema validation (#2) for retention tables | Validate `agg_weekly_user_retention_features` schema before coding | High |
| Engagement Decay | ECharts performance (#6), HTML file size (#10) | Pre-aggregate to weekly; limit to top N users | Medium |
| Feature Velocity | Product area mapping drift (#14), Weave suppression (#12) | Audit unmapped events; centralize weave_enabled flag | Low |
| Team/Cluster Detection | Team field sparsity (#7), Identity resolution (#3) | Pre-check team coverage; offer behavioral clustering fallback | High |
| Per-User Risk Scoring | Churn score context (#5), landing_development access (#9) | Show ranges not points; verify BQ permissions first | High |
| Usage Correlation | Privacy leaks (#4), Query cost (#1) | Pre-computed benchmarks; minimum cohort size; air gap | Critical |
| SDK Version Distribution | Low risk -- straightforward column reads | Standard column pruning discipline | Low |
| Performance Deep Dive | Datadog data availability (#13), Schema validation (#2) | Validate `fct_application_performance` early; have fallback plan | High |

---

## Sources

### BigQuery Cost & Optimization
- [BigQuery Pricing Explained 2026](https://bix-tech.com/bigquery-pricing-explained-2026-how-to-avoid-unexpected-costs-and-keep-queries-under-control/) -- on-demand pricing, LIMIT not reducing scan cost
- [BigQuery Cost Optimization Guide](https://medium.com/@cocamatias/bigquery-cost-optimization-the-complete-guide-for-growing-companies-9951bd46a64c) -- column pruning, partitioning, materialized views
- [Estimate and control costs - BQ docs](https://docs.cloud.google.com/bigquery/docs/best-practices-costs) -- maximum_bytes_billed, dry-run estimates
- [Reducing BigQuery Costs - Shopify](https://shopify.engineering/reducing-bigquery-costs) -- real-world cost optimization case study

### Schema Discovery & Validation
- [INFORMATION_SCHEMA introduction - BQ docs](https://docs.cloud.google.com/bigquery/docs/information-schema-intro) -- metadata views, cross-project access
- [BigQuery INFORMATION_SCHEMA: Using Metadata Like A Pro](https://medium.com/@zach.mortenson7/bigquery-information-schema-using-metadata-like-a-pro-9503ddfdeae6) -- schema change delays, validation patterns

### Cohort Analysis
- [Cohort Retention SQL Templates: Snowflake & BigQuery](https://stellans.io/cohort-retention-sql-templates-snowflake-bigquery/) -- tenure alignment vs calendar alignment
- [How to Measure Cohort Retention in BigQuery](https://popsql.com/learn-sql/bigquery/how-to-measure-cohort-retention-using-bigquery) -- DATE_DIFF patterns
- [Cohort Analysis using BigQuery and Looker Studio](https://towardsdatascience.com/a-complete-guide-to-cohort-analysis-using-bigquery-and-looker-studio-1cd18c0edd79/) -- end-to-end pipeline patterns

### Churn Prediction Visualization
- [Customer Churn Prediction: A Systematic Review](https://www.mdpi.com/2504-4990/7/3/105) -- model calibration, imbalanced datasets, metric selection
- [How to Address Churn With Predictive Analytics](https://blog.dataiku.com/how-to-address-churn-with-predictive-analytics) -- presenting predictions without misleading

### ECharts Performance
- [ECharts: X-range plot very slow with >10,000 data (GitHub #15332)](https://github.com/apache/echarts/issues/15332) -- confirmed performance degradation
- [Series for visualizing large datasets >100k (GitHub #14033)](https://github.com/apache/echarts/issues/14033) -- large mode, appendData pattern
- [ECharts Features](https://echarts.apache.org/en/feature.html) -- streaming, progressive rendering capabilities

### Privacy & Cross-Account Analysis
- [BigQuery Data Governance](https://cloud.google.com/bigquery/docs/data-governance) -- column-level security, data masking
- [BigQuery Privacy Controls](https://www.owox.com/glossary/data-privacy-for-bigquery) -- k-anonymity, re-identification risk

### Codebase Analysis (primary source for project-specific pitfalls)
- `bq_client.py` -- JOB_PROJECT vs DATA_PROJECT split, parameterized queries
- `queries.py` -- existing query factory patterns, product area mapping, dim_users JOIN
- `usage.py` -- graceful degradation patterns, weave suppression, SFDC enrichment
- `PROJECT.md` -- data confidence ratings, constraints, deployment type considerations
- `wandb-bigquery-schema-discovery.md` -- table inventory, column documentation
