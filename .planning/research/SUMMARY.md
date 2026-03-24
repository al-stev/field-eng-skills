# Project Research Summary

**Project:** BQ Deep Analytics — Usage Intelligence Expansion
**Domain:** SE-facing product analytics — 9 standalone deep-dive HTML pages extending the existing BigQuery skill
**Researched:** 2026-03-24
**Confidence:** HIGH (existing codebase fully inspected, established patterns, verified BQ schema)

## Executive Summary

This project extends the existing W&B field engineering analytics toolchain with 9 per-customer deep-dive pages covering User Journey, Cohort Analysis, Engagement Decay, Feature Velocity, Team Detection, Risk Scoring, Usage Correlation, SDK Version Distribution, and Performance. The correct approach is a new `deep-analytics` Claude Code skill that adds analytical query functions to the existing centralized `bigquery/scripts/queries.py`, owns its own data transformation layer (one module per page), and produces self-contained ECharts v5 HTML files following the established design system. No new Python dependencies are needed. ECharts v6 should be explicitly avoided — all required chart types (Sankey, heatmap, funnel, gauge, treemap, radar, scatter) exist in v5, and upgrading would break the existing `wandb` theme across three production templates.

The recommended build approach is a 4-phase progression ordered by data confidence and dependency complexity. A foundation phase (new skill scaffolding, shared utilities, orchestrator, cost guardrails) enables four high-confidence pages in parallel (Feature Velocity, Engagement Decay, User Journey, SDK Versions), then medium-confidence pages with more complex data needs (Cohort Analysis, Team Detection, Risk Scoring), and finally the two highest-risk pages last (Usage Correlation for privacy reasons, Performance for uncertain data availability). The MVP is Feature Velocity + Engagement Decay — these deliver immediate SE value, have the highest data confidence, and establish the template pattern reused by all subsequent pages.

The five critical risks that must be managed from the very first implementation are: (1) BigQuery query cost from unscoped wide-table scans on the 100+ column `ext_daily_user_event_usage` table; (2) schema assumptions on 7+ BQ tables not yet validated with real customer data; (3) silent identity resolution failures for server deployments where username and email are NULL without the `dim_users` JOIN; (4) cross-account data privacy in the Usage Correlation page requiring an air-gap pre-aggregation approach; and (5) HTML file size explosion from inlining per-user daily data that must be aggressively pre-aggregated in Python before injection.

## Key Findings

### Recommended Stack

The project requires zero new dependencies. The existing `bigquery-skill/pyproject.toml` provides everything needed: `google-cloud-bigquery>=3.39.0` for BQ execution, `pandas>=2.0.0` for data transformation, `pyarrow>=17.0.0` for Arrow transfer, and `pyyaml>=6.0` for customer registry. The visualization layer is ECharts v5 via CDN (`echarts@5`) with the already-defined `wandb` custom theme and Google Fonts (Instrument Serif, Outfit, JetBrains Mono). The generation infrastructure uses the existing `uv run --project` isolation pattern and gcloud ADC for BQ authentication.

**Core technologies:**
- Apache ECharts 5.x (latest 5.6.0): All chart rendering — stay on v5, not v6; all required series types present in core bundle; `wandb` theme already defined
- google-cloud-bigquery 3.40.1: BQ execution with ADC auth — already a dependency, parameterized queries, partition-aware, `maximum_bytes_billed` safety net to add
- pandas 2.0+: Data transformation layer — DataFrame output from BQ, pivot tables, cohort aggregation, weekly resampling
- uv: Dependency isolation — `uv run --project .claude/skills/deep-analytics` pattern consistent with all other skills
- Self-contained HTML with inline JSON: Deployment model — single file, ECharts CDN, no server, data injected as `const PAGE_DATA = {...}`

### Expected Features

**Must have (table stakes — applies to all 9 pages):**
- AI narrative summary — SEs need talk-track text; expectation set by existing reports; generated at build time
- KPI headline row — 2-4 top-level numbers above charts; SEs scan headlines first
- Dark/light mode — CSS `prefers-color-scheme`; breaking this is a regression against existing reports
- Interactive tooltips — exact values on hover; static charts are unacceptable for data exploration
- Graceful empty states — not every customer has data for every dimension; "No data available" cards required
- Self-contained HTML — non-negotiable architectural constraint; single file, ECharts CDN only
- ECharts toolbox — zoom and save-as-PNG; free interactivity directly useful in SE workflows

**Should have (differentiators):**
- Contextual "so what?" callouts — AI-generated `markLine`/`markPoint` annotations beyond raw charts
- Copy-to-clipboard for key insights — `navigator.clipboard.writeText()` for pasting into Slack and email
- Linked navigation between pages — cross-references between related dimensions via `<a>` links
- Per-user engagement sparklines — mini ECharts instances in user tables for Engagement Decay

**Defer to v2+:**
- Behavioral cohort comparison within Cohort Analysis — high complexity, niche use case
- Cross-area time-series correlation within Feature Velocity — statistical complexity not justified for v1
- Version-to-issues correlation within SDK Versions — unclear data quality at the join
- Historical risk snapshots within Risk Scoring — requires score storage or historical recomputation

**Anti-features (never build):**
- Real-time updating, date pickers, or dynamic API calls from the browser — violates self-contained HTML
- Dark mode toggle button — CSS-only via `prefers-color-scheme` already handles this
- PDF export button — browser print-to-PDF works; building a renderer adds weight for marginal value
- Cross-customer data visible to customers — privacy violation; correlation data is SE-internal only
- Any npm build step, React/Vue/Svelte, server-side rendering, or Jinja2 templating

### Architecture Approach

The correct structure is a new `deep-analytics` Claude Code skill that extends (not duplicates) the existing query layer. New SQL query functions are added to `bigquery/scripts/queries.py` (keeping the query factory centralized). The `deep-analytics` skill owns the orchestrator (`generate.py`), one transform module per analytical page (`transforms/user_journey.py`, etc.), shared utilities (`common/data_utils.py`), and one HTML template per page. Cross-skill Python imports use `sys.path.insert` to access `bigquery/scripts/` directly rather than subprocess — needed because transform modules require raw DataFrames, not pre-aggregated JSON. Output files go to `customers/<name>/analytics/YYYY-MM-DD-<type>.html`.

**Major components:**
1. `bigquery/scripts/queries.py` — Centralized SQL factory; all new query functions added here; no SQL in transform modules
2. `deep-analytics/scripts/generate.py` — Orchestrator; routes `--customer` and `--page` args, runs queries, invokes transforms, injects data, writes output HTML
3. `deep-analytics/scripts/transforms/<page>.py` — One transform module per page; converts BQ DataFrames to page-specific JSON structure matching the template contract
4. `deep-analytics/scripts/common/data_utils.py` — Shared helpers: date bucketing, trend math, engagement zone classification, product area mapping, `safe_divide`
5. `deep-analytics/templates/<page>.html` — Self-contained HTML with ECharts, W&B design system tokens, and sample `PAGE_DATA` for development; real data injected at generation time

### Critical Pitfalls

1. **Uncontrolled BQ query cost from wide-table scans** — Column pruning is mandatory on every query; ban `SELECT *`; set `maximum_bytes_billed` on `QueryJobConfig`; add bytes-processed logging after each `client.query()` call; use early `WHERE account_id` + `date_day` filtering before any aggregation. Must be built-in during Phase 1, not retrofitted.

2. **Schema assumptions on unvalidated BQ tables** — Only 4 of 7+ required tables have been query-tested against real customer data. `agg_weekly_user_retention_features`, `renewal_predictions` (in the `landing_development` dataset), `fct_application_performance`, and team fields in `ext_daily_user_event_usage` all need validation before building their respective pages. Run a validation script at the start of each phase that introduces a new table.

3. **Silent identity resolution failures for server deployments** — Server customers do not populate `username` or `email` in `ext_daily_user_event_usage`; the `dim_users` LEFT JOIN is mandatory for all per-user pages. Create a shared user-resolution CTE in `queries.py`; every user-level query must use it; test against a server-deployment customer before shipping any per-user page.

4. **Cross-account data privacy in Usage Correlation** — Any query that does NOT filter by `@account_id` requires privacy review. Benchmark data must use pre-computed aggregates with minimum 10-account cohorts; never embed account names or IDs in output HTML; the correlation page must be labeled "SE INTERNAL ONLY."

5. **HTML file size explosion** — Per-user daily data for a large enterprise customer can produce 5-10MB of inline JSON. Pre-aggregate aggressively in Python (weekly rollups minimum, one row per user for journey, one cell per cohort-week for retention). Target under 2MB per HTML file. Add a post-generation size check that warns when exceeded.

## Implications for Roadmap

Based on combined research, the natural phase structure is driven by three constraints: data confidence tiers from FEATURES.md, architectural dependencies identified in ARCHITECTURE.md, and the phase-specific risk warnings from PITFALLS.md.

### Phase 1: Foundation + Infrastructure
**Rationale:** Everything else depends on this. No analytical page can be built without the skill scaffolding, the orchestrator, shared utilities, and the cost and safety guardrails on query execution.
**Delivers:** New `deep-analytics` skill directory with `pyproject.toml` and `SKILL.md`, `generate.py` orchestrator with `--customer`/`--page` routing, `common/data_utils.py` with shared helpers (date bucketing, trend math, engagement zone classification, product area mapping), `bq_client.py` extension with `maximum_bytes_billed` safety net and bytes-processed logging, and a permission validation script covering all 7+ BQ tables across both datasets (`analytics` and `landing_development`).
**Avoids:** Pitfall 1 (query cost — built-in from day one), Pitfall 9 (permission asymmetry — caught early before pages are built around inaccessible tables).
**Research flag:** Skip — standard `uv` skill scaffolding and `QueryJobConfig` patterns are well-documented in the existing codebase.

### Phase 2: High-Confidence Pages (parallel after Phase 1)
**Rationale:** Four pages with HIGH data confidence, minimal cross-page dependencies, and immediate SE value. Prove the template pattern, validate the full generation pipeline, and establish conventions for all subsequent pages. Can be built by parallel subagents.
**Delivers:** Feature Velocity page (sparkline grid + momentum indicators, extending existing `product_areas_query()`), Engagement Decay page (user cold-detection table + engagement score trend), User Journey page (Sankey diagram + stage completion + maturity scoring), SDK Version Distribution page (donut chart + freshness assessment + user-version table).
**Implements:** ECharts Sankey, line with markArea, stacked bar, gauge; `dim_users` first_*_at fields; `ext_daily_user_event_usage` weekly aggregation; user-resolution CTE first defined here for reuse in all later phases.
**Avoids:** Pitfall 3 (identity resolution — user-resolution CTE required for User Journey and Engagement Decay), Pitfall 6 (ECharts performance — pre-aggregate to weekly, limit to top-N users), Pitfall 10 (HTML size — weekly rollups only, one row per user for journey), Pitfall 12 (Weave suppression — centralize `weave_enabled` flag in `generate.py`), Pitfall 14 (product area mapping drift — audit unmapped events before Feature Velocity ships).
**Research flag:** Skip for Feature Velocity and SDK Versions (straightforward column reads, established patterns). Identity resolution CTE needs validation against a server-deployment customer during User Journey and Engagement Decay development.

### Phase 3: Medium-Confidence Pages
**Rationale:** These pages depend on tables not yet validated with real customer data, have higher query complexity, or have uncertain field population rates. Building after Phase 2 means the generation pipeline is proven, the validation script exists, and the identity resolution CTE is established.
**Delivers:** Cohort Analysis page (retention heatmap + cohort size labels + overall retention curve + new/retained/resurrected stacked area), Team/Cluster Detection page (team breakdown table + product area heatmap + graceful degradation for sparse data + behavioral clustering fallback), Per-User Risk Scoring page (composite gauge + risk factor breakdown + renewal context + AI narrative with traffic-light bucketing).
**Avoids:** Pitfall 2 (schema validation — run before each new table), Pitfall 5 (churn score context — traffic-light bucketing, confidence ranges, staleness banner when `inference_timestamp` is >60 days old), Pitfall 7 (team field sparsity — pre-check team coverage threshold before rendering, suppress page if <20% covered), Pitfall 8 (cohort date alignment — tenure-based `DATE_DIFF` not calendar grouping, filter inactive users, suppress cohorts with <5 members), Pitfall 9 (`landing_development` permissions — validate `renewal_predictions` access before Risk Scoring begins).
**Research flag:** Cohort Analysis needs schema validation of `agg_weekly_user_retention_features` and `returning_active_status` semantics before writing the query. Risk Scoring needs validation of `landing_development` dataset access and `renewal_predictions` model freshness before designing the composite score.

### Phase 4: High-Complexity and Privacy-Sensitive Pages
**Rationale:** Usage Correlation requires cross-account query architecture new to this codebase and significant privacy controls. Performance Deep Dive has LOW data confidence for its primary BQ tables. Both belong last after simpler patterns are proven and the team has full context on the data landscape.
**Delivers:** Usage Correlation page (product combination matrix + current account positioning + anonymized peer benchmarking — SE internal only), Performance Deep Dive page (performance index gauge + per-feature slowness breakdown + NPS overlay — BQ-only if `fct_application_performance` validates, descoped if not).
**Avoids:** Pitfall 4 (privacy leaks — pre-computed benchmarks with air gap from per-customer reports, minimum 10-account cohort size, no account identifiers anywhere), Pitfall 1 (query cost — cross-account queries are the most expensive; use `APPROX_COUNT_DISTINCT` and CTEs), Pitfall 13 (Datadog data availability — validate `fct_application_performance` coverage and freshness first; descope entirely if the table lacks useful data rather than building toward an unknown).
**Research flag:** Usage Correlation needs a privacy architecture design review before implementation. Performance Deep Dive requires an explicit go/no-go validation gate on `fct_application_performance` data quality — do not start building until the gate passes.

### Phase Ordering Rationale

- **Foundation before pages:** The orchestrator, shared utilities, and cost guardrails are prerequisites for every page — this is not optional scaffolding.
- **Confidence cascade:** Tier 1 HIGH-confidence pages (Phase 2) prove the pipeline before investing effort in Tier 3 and 4 pages whose data sources are unvalidated.
- **Quick wins front-loaded:** Feature Velocity and SDK Versions deliver immediate SE value with minimal query complexity, proving the tool's value before tackling complex pages.
- **Privacy isolation last:** Usage Correlation is deliberately last so privacy controls are never rushed to meet earlier milestones, and the team has full experience with the codebase before introducing cross-account queries.
- **Pitfall mitigation sequencing:** Cost guardrails are built in Phase 1; the user-resolution CTE is defined in Phase 2 and reused in Phases 3 and 4 — both are solved once, not re-solved per page.
- **Validation gates before medium/low-confidence phases:** Schema validation scripts from Phase 1 are run at the start of Phases 3 and 4 before any code is written for the new tables.

### Research Flags

Phases likely needing `/gsd:research-phase` during planning:
- **Phase 3 (Cohort Analysis):** `agg_weekly_user_retention_features` schema not yet query-tested; retention table structure and `returning_active_status` field semantics need validation against real customer data before writing the heatmap query.
- **Phase 3 (Risk Scoring):** `landing_development.renewal_predictions` is in a separate BQ dataset with unknown IAM; model calibration, refresh cadence, and `inference_timestamp` behavior need validation before the composite score logic is designed.
- **Phase 4 (Usage Correlation):** Cross-account query architecture and privacy controls are entirely new to this codebase; the pre-computed benchmarks approach and minimum cohort size enforcement need design before implementation.
- **Phase 4 (Performance Deep Dive):** `fct_application_performance` data quality, coverage across customer types, and data freshness are LOW confidence; a validation gate should block this page if the table proves insufficient.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation):** `uv` skill scaffolding, `sys.path` cross-skill import, and `QueryJobConfig.maximum_bytes_billed` are well-documented patterns in the existing codebase.
- **Phase 2 (Feature Velocity, SDK Versions):** Direct extensions of existing `product_areas_query()` and straightforward column reads; no novel patterns needed.
- **Phase 2 (User Journey, Engagement Decay):** ECharts Sankey and engagement scoring are well-documented in official ECharts docs; identity resolution CTE pattern is already established in `power_users_query()`.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | ECharts v5 and all Python dependencies verified against existing codebase and official ECharts v5/v6 migration guide; v6 upgrade decision is unambiguous |
| Features | HIGH | Existing codebase and BQ schema fully inspected; 4 of 9 pages have HIGH data confidence; feature tiers derive directly from codebase observation and PROJECT.md |
| Architecture | HIGH | Based on direct inspection of 6 existing files totaling 6,000+ lines; patterns are explicit, established, and internally consistent |
| Pitfalls (critical #1-5) | HIGH | BQ cost, schema validation, identity resolution, privacy leaks, HTML size — all verified from codebase inspection or official documentation |
| Pitfalls (moderate #6-10) | HIGH/MEDIUM | ECharts performance and file size verified via ECharts GitHub issues; team field sparsity and sandbox permissions are MEDIUM (existence confirmed, per-customer rates unknown) |
| Pitfalls (minor #11-14) | MEDIUM/LOW | Performance data availability (Pitfall 13) is LOW — table exists but data quality is unconfirmed |

**Overall confidence:** HIGH

### Gaps to Address

- **`landing_development.renewal_predictions` access:** Validate IAM permissions from `wandb-sa-sandbox` before Phase 3 Risk Scoring begins. Have a fallback plan (behavioral-only risk scoring without the ML churn score) if cross-dataset access fails.
- **`fct_application_performance` data quality:** Run a coverage query (`SELECT DISTINCT account_id, MAX(date_day) FROM fct_application_performance GROUP BY 1`) before starting Phase 4. Descope Performance Deep Dive if data is stale or missing for test customers.
- **`agg_weekly_user_retention_features` schema:** Column-level validation needed to confirm `returning_active_status` semantics and whether data exists across a range of customer types before designing the cohort heatmap query.
- **Team field population rates:** No per-customer baseline exists for `is_part_of_team` coverage. The 20% suppression threshold is a reasonable starting point but may need tuning after validation against real customers with different deployment types.
- **Churn model recency:** `inference_timestamp` recency and model refresh cadence are undocumented. If predictions are consistently older than 60 days, the Risk Scoring page's ML signal should be labeled stale and weighted lower in the composite score.
- **Large customer ECharts performance:** The threshold for switching to `large: true` mode needs empirical testing with the largest customer's data volume before the Engagement Decay and Cohort Analysis pages ship.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `bigquery/scripts/queries.py` (449 lines), `usage.py` (559 lines), `bq_client.py` (125 lines), `usage-report/templates/usage-report-external.html` (1360 lines), `usage-report/templates/usage-report-internal.html` (1653 lines), `customer-snapshot/templates/intelligence-dashboard.html` (3721 lines)
- `~/Documents/gitstuff/ai-docs/wandb-usage-visualization.md` — existing visualization patterns and design system
- `~/Documents/gitstuff/ai-docs/wandb-bigquery-schema-discovery.md` — BQ table inventory and column documentation
- `~/Documents/gitstuff/ai-docs/google-cloud-bigquery.md` — BQ client patterns and ADC auth
- https://echarts.apache.org/handbook/en/basics/release-note/v6-upgrade-guide/ — verified v5 to v6 breaking changes (theme, legend, axis overflow)
- https://echarts.apache.org/handbook/en/basics/release-note/v6-feature/ — v6 feature list (confirmed no new chart types needed)
- https://docs.cloud.google.com/bigquery/docs/best-practices-costs — `maximum_bytes_billed`, dry-run estimation, partition filtering

### Secondary (MEDIUM confidence)
- https://stellans.io/cohort-retention-sql-templates-snowflake-bigquery/ — tenure alignment vs calendar alignment for cohort analysis
- https://popsql.com/learn-sql/bigquery/how-to-measure-cohort-retention-using-bigquery — `DATE_DIFF` patterns for retention
- https://medium.com/@cocamatias/bigquery-cost-optimization — column pruning, partitioning, materialized views
- ECharts GitHub issues #15332 and #14033 — confirmed performance degradation above 10,000 data points; `large: true` mode recommendation
- https://cloud.google.com/bigquery/docs/information-schema-intro — INFORMATION_SCHEMA cross-project access rules and permission requirements
- https://blog.dataiku.com/how-to-address-churn-with-predictive-analytics — presenting ML churn predictions without misleading SEs

### Tertiary (LOW confidence)
- https://visionlabs.com/blog/best-product-analytics-tools/ — vendor comparison for analytics tool patterns
- https://www.custify.com/blog/customer-health-score-guide/ — customer health scoring frameworks
- https://www.june.so/blog/churn-prediction-model — churn model calibration and presentation patterns

---
*Research completed: 2026-03-24*
*Ready for roadmap: yes*
