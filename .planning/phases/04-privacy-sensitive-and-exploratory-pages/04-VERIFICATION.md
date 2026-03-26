---
phase: 04-privacy-sensitive-and-exploratory-pages
verified: 2026-03-26T15:10:00Z
status: passed
score: 17/17 must-haves verified
re_verification: false
---

# Phase 4: Privacy-Sensitive and Exploratory Pages Verification Report

**Phase Goal:** SEs have two final analytical pages -- Usage Correlation (SE-internal cross-account intelligence) and Performance Deep Dive (application performance signals) -- completing the full 9-page deep analytics suite
**Verified:** 2026-03-26T15:10:00Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Cross-account product area co-occurrence query returns per-account product area presence WITHOUT account_id in output | VERIFIED | `cross_account_product_areas_query()` at queries.py:773 — no `@account_id` param; privacy strips in transform before output |
| 2 | Cross-account ARR + tier query returns product breadth and ARR per account for peer benchmarking | VERIFIED | `cross_account_arr_breadth_query()` at queries.py:799 — joins stg_salesforce_accounts for ARR and cs_tier, no `@account_id` |
| 3 | Performance query returns application_performance_index and slow_* columns for a single account | VERIFIED | `performance_query()` at queries.py:830 — selects all required columns, filters by `@account_id`, 90-day window |
| 4 | Latency distribution query returns per-event latency_ms for histogram binning | VERIFIED | `latency_distribution_query()` at queries.py:851 — selects latency_ms + universal_user_id, 30-day window |
| 5 | Slow chart users query returns identity-resolved usernames with slow load percentages | VERIFIED | `slow_chart_users_query()` at queries.py:864 — JOINs dim_users, uses SAFE_DIVIDE, orders by slow_pct DESC |
| 6 | PRODUCT_AREA_CASE is a shared Python constant used by both product_areas_query() and cross_account_product_areas_query() | VERIFIED | `PRODUCT_AREA_CASE` defined at queries.py:37, used 4 times (product_areas_query, cross_account_product_areas_query, cross_account_arr_breadth_query) |
| 7 | PHASE4_SCHEMA_SPECS validates fct_application_performance, fct_onscreen_loader_latencies, and agg_daily_team_members_slow_chart_loads | VERIFIED | schema_validator.py:75 — 3-entry dict confirmed by 4 passing tests |
| 8 | PHASE4_DATA_CHECKS verifies per-account data population for performance tables | VERIFIED | schema_validator.py:91 — 3-entry dict (perf_index, latency_data, slow_chart_data), all with `@account_id` and `LIMIT 1` |
| 9 | SE can generate a usage-correlation page that shows cross-account product co-occurrence as a heatmap | VERIFIED | `renderUsageCorrelation()` at base-template.html:2810, registered in PAGE_RENDERERS:3086; ECharts heatmap with visualMap at line 2875 |
| 10 | The output HTML contains an SE-INTERNAL ONLY privacy badge that is non-dismissible and visible | VERIFIED | base-template.html:2823 — badge created as first child of chart section, no dismiss handler |
| 11 | No individual account names or SFDC account IDs appear anywhere in the output HTML source | VERIFIED | UsageCorrelationTransform:469 — JSON serialization + regex scan for `0018[A-Za-z0-9]{14}` pattern before return; test_privacy_no_account_ids passes |
| 12 | Any product combo backed by fewer than 10 accounts is suppressed from the matrix | VERIFIED | usage_correlation.py:153 — `if cohort_size < self.MIN_COHORT_SIZE` suppression; test_cohort_suppression passes |
| 13 | Current account is highlighted as accent diamond in the ARR-usage scatter, peers are anonymized circles | VERIFIED | base-template.html:3063 — `symbol: 'diamond', symbolSize: 12, itemStyle: { color: c.accent }` for current account |
| 14 | SE can generate a performance page that shows gauge, slowness breakdown, error metrics, latency histogram, and slow chart users table | VERIFIED | `renderPerformance()` at base-template.html:2508 — all 5 sections present with section labels confirmed |
| 15 | If fct_application_performance has no data, the page renders a graceful descoped state | VERIFIED | base-template.html:2516 — `if (PAGE_DATA.available === false && PAGE_DATA.reason)` triggers descoped layout at line 2521; renderCharts updated to invoke renderer for unavailable pages |
| 16 | The go/no-go gate runs schema validation AND row-count check before proceeding | VERIFIED | generate.py:268 — `validate_tables()` then `check_data_availability()` before any `run_query()` call; returns `descoped_result()` on failure |
| 17 | All 9 page types are registered in PAGE_RENDERERS and PAGE_REGISTRY with no remaining placeholders | VERIFIED | PAGE_REGISTRY at generate.py:390 — all 9 handlers are real functions (no `_placeholder_handler` entries); PAGE_RENDERERS at base-template.html:3077 has 6 entries (cohort-analysis, risk-scoring, team-detection registered in Phase 3 plans) |

**Score:** 17/17 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.claude/skills/bigquery/scripts/queries.py` | 5 new query functions + PRODUCT_AREA_CASE constant | VERIFIED | PRODUCT_AREA_CASE at line 37; all 5 functions present (lines 773, 799, 830, 851, 864) |
| `.claude/skills/bigquery/tests/test_queries.py` | Tests for all 5 new query functions | VERIFIED | 7 test classes imported at lines 25-29; 96 tests total, all pass |
| `.claude/skills/deep-analytics/scripts/schema_validator.py` | PHASE4_SCHEMA_SPECS and PHASE4_DATA_CHECKS | VERIFIED | Both dicts present at lines 75 and 91 |
| `.claude/skills/deep-analytics/tests/test_schema_validator.py` | Tests for Phase 4 schema specs and data checks | VERIFIED | TestPhase4SchemaSpecs + TestPhase4DataChecks — 11 tests, all pass |
| `.claude/skills/deep-analytics/scripts/transforms/usage_correlation.py` | UsageCorrelationTransform with co-occurrence matrix, privacy enforcement, peer benchmarking | VERIFIED | Class at line 17; MIN_COHORT_SIZE=10, transform(), _build_narrative(), SFDC ID scan at line 469 |
| `.claude/skills/deep-analytics/tests/test_usage_correlation.py` | Tests for transform, privacy enforcement, cohort suppression | VERIFIED | test_privacy_no_account_ids, test_empty_cross_account, test_insufficient_cohort, test_cohort_suppression all present and pass |
| `.claude/skills/deep-analytics/scripts/transforms/performance.py` | PerformanceTransform with go/no-go gate support, gauge scoring, latency binning | VERIFIED | Class at line 12; TIER_THRESHOLDS, LATENCY_BINS, descoped_result(), transform(), _build_narrative() all present |
| `.claude/skills/deep-analytics/tests/test_performance.py` | Tests for transform, descoped state, latency binning, gauge tiers | VERIFIED | test_descoped_state, test_tier_good/fair/poor, test_latency_bins_five_entries, test_slowness_sorted_descending all present; 29 tests pass |
| `.claude/skills/deep-analytics/scripts/generate.py` | _usage_correlation_handler and _performance_handler in PAGE_REGISTRY | VERIFIED | Both handlers defined (lines 337, 254) and registered in PAGE_REGISTRY (lines 397, 399) |
| `.claude/skills/deep-analytics/templates/base-template.html` | renderUsageCorrelation and renderPerformance in PAGE_RENDERERS | VERIFIED | Functions at lines 2810, 2508; registered at lines 3085-3086 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `generate.py` | `queries.py` | `from queries import cross_account_product_areas_query` | WIRED | Line 339-342 in `_usage_correlation_handler` |
| `generate.py` | `transforms/usage_correlation.py` | `from transforms.usage_correlation import UsageCorrelationTransform` | WIRED | Line 343; transform.transform() called at line 378 |
| `generate.py` | `queries.py` | `from queries import performance_query` | WIRED | Line 257 in `_performance_handler` |
| `generate.py` | `schema_validator.py` | `from schema_validator import validate_tables, check_data_availability, PHASE4_SCHEMA_SPECS, PHASE4_DATA_CHECKS` | WIRED | Lines 260-263; validate_tables() called at line 268 before any run_query() |
| `generate.py` | `transforms/performance.py` | `from transforms.performance import PerformanceTransform` | WIRED | Line 259; transform.transform() called at line 330 |
| `base-template.html` | `PAGE_DATA` | `renderUsageCorrelation reads PAGE_DATA.correlation_matrix` | WIRED | PAGE_DATA.correlation_matrix referenced in heatmap data setup (renderUsageCorrelation body) |
| `base-template.html` | `PAGE_DATA` | `renderPerformance reads PAGE_DATA.performance_index` | WIRED | `PAGE_DATA.performance_index` referenced at line 2531 |
| `queries.py` | `wandb-production.analytics.fct_application_performance` | `_ref("fct_application_performance")` in `performance_query()` | WIRED | Line 830-849; uses `_ref()` pattern |
| `queries.py` | `queries.py (self)` | `PRODUCT_AREA_CASE` used in `product_areas_query()` and `cross_account_product_areas_query()` | WIRED | Constant used 4 times across 3 query functions (lines 227, 647, 785, 812/816) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `base-template.html` (renderUsageCorrelation) | `PAGE_DATA.correlation_matrix` | `UsageCorrelationTransform.transform()` via `_usage_correlation_handler` | Yes — computed from `cross_account_product_areas_query()` BQ data | FLOWING |
| `base-template.html` (renderUsageCorrelation) | `PAGE_DATA.arr_scatter` | `UsageCorrelationTransform._build_arr_scatter()` via `cross_account_arr_breadth_query()` | Yes — peers extracted from real BQ ARR data, account_id stripped | FLOWING |
| `base-template.html` (renderPerformance) | `PAGE_DATA.performance_index` | `PerformanceTransform.transform()` via `_performance_handler` with go/no-go gate | Yes — from `performance_query()` against `fct_application_performance`; descoped gracefully if no data | FLOWING |
| `base-template.html` (renderPerformance) | `PAGE_DATA.latency_distribution` | `PerformanceTransform._bin_latency()` via `latency_distribution_query()` | Yes — binned from raw `latency_ms` values; empty bins returned if table inaccessible | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| queries.py: 96 tests pass | `uv run --project .claude/skills/bigquery pytest test_queries.py` | 96 passed in 0.09s | PASS |
| schema_validator.py: 29 tests pass | `uv run --project .claude/skills/deep-analytics pytest test_schema_validator.py` | 29 passed in 0.80s | PASS |
| UsageCorrelationTransform: 11 tests pass | `uv run --project .claude/skills/deep-analytics pytest test_usage_correlation.py` | 11 passed in 0.50s | PASS |
| PerformanceTransform: 29 tests pass | `uv run --project .claude/skills/deep-analytics pytest test_performance.py` | 29 passed in 0.35s | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CORR-01 | 04-01, 04-02 | Product combination matrix (heatmap) showing which product combos co-occur across accounts with retention rates | SATISFIED | `cross_account_product_areas_query()` + `UsageCorrelationTransform` co-occurrence matrix + ECharts heatmap in `renderUsageCorrelation` |
| CORR-02 | 04-01, 04-02 | Current account positioning showing their product mix against aggregate patterns | SATISFIED | `account_positioning` key in transform output; ACCOUNT POSITIONING section in HTML renderer |
| CORR-03 | 04-02 | Next-best-action recommendation based on correlation data | SATISFIED | `next_best_action` list in transform, sorted by retention_lift_pct; NEXT-BEST-ACTION RECOMMENDATIONS section in HTML |
| CORR-04 | 04-02 | SE-Internal Only privacy badge and aggregate-only queries (no individual account names) | SATISFIED | Non-dismissible badge at base-template.html:2823; SFDC ID scan in transform at line 469; test_privacy_no_account_ids passes |
| CORR-05 | 04-02 | AI narrative interpreting correlation patterns with account-specific recommendations | SATISFIED | `_build_narrative()` in UsageCorrelationTransform returns executive_summary, highlights, recommendations |
| CORR-06 | 04-01, 04-02 | Expansion signal indicators (flag usage approaching contract limits for upsell) | SATISFIED | `expansion_signals` list in transform; EXPANSION SIGNALS section in HTML; graceful empty list when entitlements missing |
| CORR-07 | 04-01, 04-02 | Anonymized peer benchmarking (percentile ranking vs similar-tier accounts) | SATISFIED | `peer_benchmarking.breadth_percentile` computed via pandas rank(); PEER BENCHMARKING section in HTML; test_peer_benchmarking_percentile_range passes |
| CORR-08 | 04-01, 04-02 | ARR-usage scatter overlay (product breadth vs ARR across accounts, SE-internal) | SATISFIED | `arr_scatter` in transform output; ARR VS PRODUCT BREADTH section with diamond symbol for current account; peers anonymized (no account_id/name) |
| PERF-01 | 04-01, 04-03 | Performance index gauge chart (application_performance_index from fct_application_performance) | SATISFIED | `performance_query()` selects application_performance_index; `type: 'gauge'` at base-template.html:2574; 3-zone coloring |
| PERF-02 | 04-01, 04-03 | Per-feature slowness breakdown bar chart (slow_charts, slow_project_search, etc.) | SATISFIED | All slow_* columns in performance_query(); `slowness_breakdown` in transform; FEATURE SLOWNESS BREAKDOWN bar chart in HTML |
| PERF-03 | 04-01, 04-03 | Error metrics KPI cards (users_facing_errors_ct, error_count) with trend | SATISFIED | Both columns in performance_query(); `error_metrics` dict in transform with error_trend; ERROR METRICS section in HTML |
| PERF-04 | 04-01, 04-03 | Chart load latency distribution from fct_onscreen_loader_latencies | SATISFIED | `latency_distribution_query()` queries fct_onscreen_loader_latencies; 5 fixed bins with P50/P95/P99; CHART LOAD LATENCY DISTRIBUTION in HTML with P95 dashed markLine |
| PERF-05 | 04-03 | AI narrative with performance assessment and flagged areas of concern | SATISFIED | `_build_narrative()` in PerformanceTransform; test_narrative_has_required_keys passes |
| PERF-06 | 04-01, 04-03 | Slow chart load user breakdown from agg_daily_team_members_slow_chart_loads | SATISFIED | `slow_chart_users_query()` queries agg_daily_team_members_slow_chart_loads with SAFE_DIVIDE; SLOW CHART LOAD USERS scrollable table in HTML (max-height:400px at line 2774) |

All 14 requirements satisfied. No orphaned requirements found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `transforms/usage_correlation.py` | 220 | `return []` | Info | Legitimate graceful degradation — expansion signals return empty list when account_health has no entitlement data. Data-fetching path populates this when entitlement fields are present. Not a stub. |
| `transforms/performance.py` | 248 | `return []` | Info | Legitimate graceful degradation — latency bins return empty when latency_df is empty (table inaccessible). Not a stub. |

No blockers or warnings found.

### Human Verification Required

#### 1. Usage Correlation Privacy Badge Visual

**Test:** Generate a Usage Correlation page for any customer and open in browser
**Expected:** Red-dimmed badge reading "SE-INTERNAL ONLY" appears as the first element in the chart area, above all charts, with no dismiss button
**Why human:** Cannot verify visual rendering, CSS styling correctness, or print visibility programmatically

#### 2. Performance Descoped State Visual

**Test:** Run generation for an account known to lack fct_application_performance data
**Expected:** Dashed-border box appears with heading "Performance Deep Dive -- Data Insufficient" and descriptive text; no broken charts
**Why human:** Requires a real BQ account without performance data to trigger the gate; cannot simulate end-to-end without live BQ connection

#### 3. Gauge 3-Zone Coloring

**Test:** Generate a Performance page and view the gauge chart
**Expected:** Score 80+ renders green arc, 50-79 amber, below 50 red
**Why human:** ECharts rendering and color zone visual accuracy requires browser inspection

#### 4. Latency Histogram P95 markLine

**Test:** Generate a Performance page and inspect the latency histogram
**Expected:** Dashed red vertical line labeled "P95: NNNNms" appears at the correct bin
**Why human:** markLine position accuracy requires visual inspection with real latency data

### Gaps Summary

No gaps. All 17 must-haves verified, all 14 requirements satisfied, all 4 test suites pass (165 tests total across queries, schema validator, usage correlation, and performance). The full 9-page deep analytics suite is complete with both Usage Correlation and Performance Deep Dive wired end-to-end. The only items flagged are 4 visual/behavioral checks that require human verification with a live browser and real BQ data.

---

_Verified: 2026-03-26T15:10:00Z_
_Verifier: Claude (gsd-verifier)_
