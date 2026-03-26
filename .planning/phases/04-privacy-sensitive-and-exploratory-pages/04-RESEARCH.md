# Phase 4: Privacy-Sensitive and Exploratory Pages - Research

**Researched:** 2026-03-26
**Domain:** Cross-account correlation with privacy controls (Usage Correlation), application performance metrics from low-confidence BQ tables (Performance Deep Dive), ECharts heatmap/scatter/gauge/histogram chart types, 9-page navigation completion
**Confidence:** MEDIUM (overall -- driven by cross-account query novelty and performance table data availability uncertainty)

## Summary

Phase 4 delivers the final two pages in the 9-page deep analytics suite: Usage Correlation (SE-internal cross-account intelligence) and Performance Deep Dive (application performance signals). These pages are the highest-complexity and lowest-confidence pages in the project, which is why they were deliberately sequenced last.

The Usage Correlation page is architecturally unique in the project: it is the ONLY page that queries data across multiple accounts. Every other page (Phases 1-3) uses a single `@account_id` parameter. The correlation page needs aggregate product-area co-occurrence data across all accounts to produce a correlation matrix, peer benchmarking percentiles, and ARR-usage scatter data. The critical privacy constraint is that no individual account names or IDs may appear in the output HTML -- the page must use pre-aggregated data with a minimum 10-account cohort enforcement. The UI-SPEC defines a non-dismissible "SE-INTERNAL ONLY" privacy badge that must be the first element in the chart section and visible in print output.

The Performance Deep Dive page has an explicit go/no-go gate: if `fct_application_performance` and `fct_onscreen_loader_latencies` tables do not contain sufficient data for the target account, the page generates with `available: false` and displays a graceful descoped state instead of charts. This page has been flagged since the ROADMAP as LOW data confidence. The research confirms these tables exist in BQ schema but their data freshness, coverage across customer types, and account-level population are unvalidated. The phase must include a schema validation + data availability check before any Performance renderer work begins.

**Primary recommendation:** Build in 3 plans: (1) BQ queries + schema validation + privacy enforcement utilities for both pages, (2) Usage Correlation page (transform + handler + renderer -- the heavier lift with cross-account queries and privacy controls), (3) Performance Deep Dive page with go/no-go gate + 9-page navigation completion integration test. The cross-account query is the highest-risk item and should be developed first to flush out any IAM or data availability issues.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CORR-01 | Product combination matrix (heatmap) showing which product combos co-occur across accounts with retention rates | Cross-account query on `ext_daily_user_event_usage` grouped by product area presence per account; ECharts `type: 'heatmap'` with `visualMap` continuous gradient (red-amber-green); 440px container per UI-SPEC |
| CORR-02 | Current account positioning showing their product mix against aggregate patterns | Single-account product areas query (reuses existing `product_areas_query()` pattern) compared to cross-account aggregate; text block with match patterns |
| CORR-03 | Next-best-action recommendation based on correlation data | Python transform computes retention lift per missing product area; sorted list with blue badges per UI-SPEC |
| CORR-04 | "SE-Internal Only" privacy badge and aggregate-only queries (no individual account names) | Non-dismissible privacy badge component (JS rendering spec in UI-SPEC); minimum 10-account cohort enforcement in transform; all cross-account queries return aggregates only |
| CORR-05 | AI narrative interpreting correlation patterns with account-specific recommendations | `_build_narrative()` pattern from existing transforms; enriched with correlation context |
| CORR-06 | Expansion signal indicators (flag usage approaching contract limits for upsell) | Compare current usage to SFDC entitlement fields from `account_health_query()` and `dim_opportunities`; green badges per UI-SPEC |
| CORR-07 | Anonymized peer benchmarking (percentile ranking vs similar-tier accounts) | Cross-account query grouped by `cs_tier` from `stg_salesforce_accounts`; percentile computation in pandas; horizontal bar chart with anonymized labels |
| CORR-08 | ARR-usage scatter overlay (product breadth vs ARR across accounts, SE-internal) | Cross-account query joining product area count with ARR from `stg_salesforce_accounts`; ECharts scatter with accent diamond for current account, tertiary circles for peers |
| PERF-01 | Performance index gauge chart (application_performance_index from fct_application_performance) | ECharts `type: 'gauge'` with 3-zone color (green/amber/red); reuses Phase 3 gauge pattern; go/no-go gate on table accessibility |
| PERF-02 | Per-feature slowness breakdown bar chart (slow_charts, slow_project_search, etc.) | Horizontal bar chart from `fct_application_performance` slow_* columns; ECharts `type: 'bar'` |
| PERF-03 | Error metrics KPI cards (users_facing_errors_ct, error_count) with trend | Inline stat row reusing KPI pattern; trend computed from 30d rolling comparison |
| PERF-04 | Chart load latency distribution from fct_onscreen_loader_latencies | ECharts `type: 'bar'` histogram with fixed bins (0-1s, 1-2s, 2-5s, 5-10s, 10s+); P95 markLine as dashed red vertical |
| PERF-05 | AI narrative with performance assessment and flagged areas of concern | `_build_narrative()` pattern; flags slowest features and error trends |
| PERF-06 | Slow chart load user breakdown from agg_daily_team_members_slow_chart_loads | Scrollable data table (max-height 400px); sorted by slow % descending; color-coded by severity |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| google-cloud-bigquery | >=3.39.0 | BQ query execution | Already in pyproject.toml; all queries use parameterized @account_id; cross-account queries use no parameter |
| pandas | >=2.0.0 | Data transformation | Correlation matrix computation, percentile calculations, histogram binning |
| Apache ECharts | 5.x (5.6.0) | Chart rendering (heatmap, scatter, gauge, bar/histogram) | CDN-loaded; all chart types in core bundle; locked in Phase 1 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | (via pandas) | Statistical calculations | Percentile computation for peer benchmarking |

### No New Dependencies

Phase 4 adds ZERO new Python or JS dependencies. All required chart types (heatmap, scatter, gauge, bar) are in ECharts v5 core. All data processing uses pandas already in pyproject.toml.

## Architecture Patterns

### Established Page Pipeline (from Phase 1-3)

Each page follows this exact flow, and Phase 4 MUST follow it:

```
1. generate.py handler function
   -> imports query function(s) from queries module
   -> calls bq_client.run_query() with maximum_bytes_billed
   -> instantiates Transform class
   -> returns PAGE_DATA dict with 'narrative' key

2. Transform class (extends BaseTransform in transforms/base.py)
   -> transform(**dataframes) -> dict
   -> _build_narrative() -> dict with executive_summary, highlights, recommendations
   -> empty_result(reason) for no-data cases

3. generate.py write_output()
   -> reads base-template.html
   -> inject_page_data() replaces PAGE_DATA sentinel
   -> inject_ai_narrative() replaces AI_NARRATIVE sentinel
   -> writes to customers/<name>/analytics/YYYY-MM-DD-<page-type>.html

4. base-template.html PAGE_RENDERERS
   -> page-specific render function added to PAGE_RENDERERS dict
   -> function creates DOM elements and initializes ECharts instances
   -> window resize handler for all chart instances
```

### Recommended File Structure for Phase 4

```
.claude/skills/deep-analytics/
  scripts/
    transforms/
      usage_correlation.py    # UsageCorrelationTransform
      performance.py           # PerformanceTransform
  templates/
    base-template.html         # Add renderUsageCorrelation, renderPerformance to PAGE_RENDERERS

.claude/skills/bigquery/scripts/
    queries.py                 # Add cross-account and performance query functions
```

### Cross-Account Query Pattern (NEW for Phase 4)

This is the single biggest architectural novelty in Phase 4. All prior queries use `WHERE account_id = @account_id`. The correlation page requires aggregate data across ALL accounts.

**Approach: Pre-aggregated cross-account queries with privacy enforcement in the transform layer.**

```python
def cross_account_product_areas_query() -> str:
    """
    Cross-account product area presence matrix.

    Returns per-account product area flags WITHOUT account names/IDs.
    The transform layer aggregates this into co-occurrence statistics
    and enforces minimum cohort sizes.

    PRIVACY: This query intentionally omits account_name. Only account_id
    is returned for JOIN purposes, and it is NEVER passed to the output HTML.
    """
    daily_usage = _ref("ext_daily_user_event_usage")
    return f"""
    WITH account_product_areas AS (
        SELECT
            account_id,
            CASE
                WHEN event IN (...) THEN 'Experiments'
                WHEN event IN (...) THEN 'Artifacts'
                -- same product area CASE as product_areas_query()
            END AS product_area,
            COUNT(DISTINCT universal_user_id) AS users,
            SUM(event_count) AS events
        FROM {daily_usage}
        WHERE date_day >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
            AND event_count > 0
        GROUP BY account_id, product_area
    )
    SELECT
        account_id,
        product_area,
        users,
        events
    FROM account_product_areas
    WHERE product_area IS NOT NULL
        AND product_area != 'Other'
    """
```

**Privacy enforcement is in the transform, not the query.** The query returns `account_id` so the transform can group and aggregate, but `account_id` is NEVER included in the PAGE_DATA output. The transform computes:
- Co-occurrence matrix: for each pair of product areas, count how many accounts have BOTH active
- Retention overlay: for accounts with a given product combo, what % are still active after 6 months
- Peer benchmarking: group by `cs_tier`, compute product breadth percentiles
- All outputs use aggregate statistics only (counts, percentages, percentiles)

### Go/No-Go Gate Pattern (Performance Deep Dive)

```python
def _performance_handler(client, account_id, customer_name):
    from schema_validator import validate_table_schema

    # Gate 1: Do the tables exist?
    perf_validation = validate_table_schema(
        client,
        "`wandb-production.analytics.fct_application_performance`",
        ["account_id", "date_day", "application_performance_index",
         "slow_charts", "users_facing_errors_ct", "error_count"]
    )

    if not perf_validation["valid"]:
        return _descoped_performance_result(customer_name, "schema_error")

    # Gate 2: Does the account have data?
    from bq_client import run_query
    check_sql = """
    SELECT COUNT(*) AS row_count
    FROM `wandb-production.analytics.fct_application_performance`
    WHERE account_id = @account_id
        AND date_day >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
    """
    check_df = run_query(client, check_sql, account_id=account_id,
                          maximum_bytes_billed=1_000_000_000)

    if check_df.empty or check_df.iloc[0]["row_count"] == 0:
        return _descoped_performance_result(customer_name, "performance_descoped")

    # Proceed with full performance pipeline
    ...
```

### Anti-Patterns to Avoid

- **Including account_id in PAGE_DATA for correlation page:** account_id is used for JOIN/grouping in Python but MUST be stripped before JSON serialization. The transform must explicitly exclude it.
- **Running cross-account queries at O(N^2) cost:** The product area co-occurrence matrix should use a single cross-account query with pandas pivot, NOT N separate queries per account pair.
- **Creating separate HTML templates:** All pages use the SAME `base-template.html`. Chart rendering via JS functions registered in `PAGE_RENDERERS`. Do NOT create separate template files.
- **Hard-coding the product area CASE statement a third time:** The product area mapping already exists in `product_areas_query()`. Extract the CASE statement into a reusable SQL fragment or Python constant to avoid drift.
- **Showing performance data without deployment context:** Always display `deployment_type` in page metadata per UI-SPEC anti-pattern list.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Co-occurrence matrix computation | Nested Python loops comparing account pairs | pandas `crosstab()` or `pivot_table()` + matrix multiplication | pandas handles the O(accounts x product_areas) computation efficiently; manual loops are error-prone and slow |
| Percentile ranking | Manual sorting + position calculation | `scipy.stats.percentileofscore()` or `pandas.Series.rank(pct=True)` | Edge cases around ties and empty cohorts |
| Heatmap color gradient | CSS color interpolation in JS | ECharts `visualMap: { type: 'continuous', inRange: { color: [...] } }` | Built-in interpolation, legend, interactive range selection |
| Gauge dial rendering | SVG/Canvas gauge from scratch | ECharts `type: 'gauge'` | Built-in pointer, axis labels, color zones, count-up animation |
| Histogram binning | Manual bin-edge logic | pandas `pd.cut()` for fixed bins | Handles edge cases, labeling, and zero-count bins correctly |
| Privacy badge UI | Custom CSS component | Follow exact JS rendering spec from UI-SPEC | The badge spec is already fully specified with inline styles in the UI-SPEC |

## Common Pitfalls

### Pitfall 1: Cross-Account Query Leaks Customer Data into Output HTML

**What goes wrong:** The Usage Correlation page queries data across multiple accounts. If `account_id`, `account_name`, or any identifiable field leaks into the PAGE_DATA JSON embedded in the output HTML, it is a privacy violation. Even anonymized data can be de-anonymized if cohort sizes are too small.
**Why it happens:** The transform receives a DataFrame with `account_id` for grouping. A careless `to_dict()` or `to_json()` on the raw DataFrame includes all columns including `account_id`.
**How to avoid:** (1) The transform must explicitly select only aggregate output columns. (2) Add a post-serialization check: scan the final PAGE_DATA JSON string for any 18-character SFDC account ID pattern (`0018[A-Za-z0-9]{14}`). (3) Enforce minimum 10-account cohort size -- any group smaller than 10 is suppressed entirely.
**Warning signs:** SFDC account IDs appearing in the output HTML source; peer scatter tooltip showing anything other than "Peer account".

### Pitfall 2: fct_application_performance Has No Data for Target Account

**What goes wrong:** The schema validator confirms the table exists and has the required columns, but the table contains no rows for the specific customer's `account_id`. The Performance page renders empty charts instead of the graceful descoped state.
**Why it happens:** `fct_application_performance` may only have data for cloud/SaaS deployments, not server deployments. Coverage varies by account. Schema validation (dry-run) only checks column existence, not data population.
**How to avoid:** The go/no-go gate must include a row-count check (not just schema validation) for the specific `account_id`. If zero rows, return `available: false, reason: "performance_descoped"` which triggers the descoped layout.
**Warning signs:** Performance page showing all "--" KPIs but still attempting to render charts.

### Pitfall 3: Cross-Account Query Scans Entire Table (Cost Explosion)

**What goes wrong:** `ext_daily_user_event_usage` has 100+ columns and data for ALL W&B accounts. A cross-account query without column pruning and date filtering scans terabytes of data, exceeding the `maximum_bytes_billed` limit and failing.
**Why it happens:** Unlike single-account queries which filter by `account_id` (hitting the partition), cross-account queries scan all partitions within the date range.
**How to avoid:** (1) Select ONLY needed columns (account_id, event, event_count, date_day). (2) Use a tight date range (6 months, not 12). (3) Set `maximum_bytes_billed` to 100GB for cross-account queries (higher than single-account). (4) Pre-aggregate in BQ (GROUP BY account_id, product_area) before transferring to Python.
**Warning signs:** `google.api_core.exceptions.InternalServerError: 400 Query exceeded limit for bytes billed`.

### Pitfall 4: Product Area CASE Statement Drift Between Queries

**What goes wrong:** The product area mapping (event -> product area) is defined inline in `product_areas_query()`. The cross-account query needs the SAME mapping. If they drift, the correlation matrix computes co-occurrences with a different product area taxonomy than what the current account page shows.
**Why it happens:** Copy-pasting the CASE statement into a new query function. One gets updated, the other doesn't.
**How to avoid:** Extract the CASE statement into a Python constant or helper function that both queries reference. For example: `PRODUCT_AREA_CASE = "CASE WHEN event IN (...) THEN 'Experiments' ..."` used in both single-account and cross-account queries.
**Warning signs:** Correlation matrix showing product areas that don't appear on the Feature Velocity page, or vice versa.

### Pitfall 5: Retention Rate Computation Requires User-Level Retention Data

**What goes wrong:** CORR-01 requires "retention rates" alongside co-occurrence percentages in the heatmap. Computing retention for each product combo requires knowing which accounts are still active after N months. The cross-account query only has activity data -- it doesn't directly tell you "this account churned."
**Why it happens:** Retention is a time-series concept; co-occurrence is a point-in-time concept. Mixing them requires comparing activity data across two time windows.
**How to avoid:** Define "retained" as "account had activity in the most recent 30 days." For each product combo, compute: (accounts with combo AND recent activity) / (accounts with combo). This is a simplification of true retention but is computable from `ext_daily_user_event_usage` without needing `renewal_predictions`.
**Warning signs:** Retention percentages that don't make intuitive sense (e.g., all combos showing 100% retention because the query only includes currently-active accounts).

### Pitfall 6: Expansion Signals Require SFDC Entitlement Data

**What goes wrong:** CORR-06 needs to flag product areas approaching contract limits. This requires knowing the contract limits (e.g., contracted seats, Weave ingestion cap). If the `account_health_query()` or `dim_opportunities` doesn't have entitlement data for the target account, expansion signals cannot be computed.
**Why it happens:** Not all accounts have entitlement fields populated in Salesforce. Server deployment customers may have different contract structures.
**How to avoid:** Treat expansion signals as best-effort. If entitlement data is unavailable, return an empty `expansion_signals` array and show the section-level empty state. The transform must handle missing entitlement fields gracefully (check for NULL/None before computing percentages).
**Warning signs:** Division by zero when computing `usage_pct` against a NULL contract limit.

## Code Examples

### ECharts Heatmap for Product Combination Matrix (CORR-01)

```javascript
// Source: ECharts v5 docs + ai-docs/apache-echarts.md + Phase 3 cohort heatmap pattern
function renderCorrelationHeatmap(productAreas, matrixData) {
  var c = getThemeColors();
  var chart = echarts.init(document.getElementById('correlationHeatmap'), 'wandb');
  chart.setOption({
    tooltip: {
      position: 'top',
      formatter: function(p) {
        // matrixData: [row_idx, col_idx, co_occurrence_pct, retention_pct, cohort_size]
        var d = p.value;
        return productAreas[d[0]] + ' + ' + productAreas[d[1]] + ': ' +
               d[2] + '% of accounts using both have ' + d[3] + '% 6-month retention' +
               ' (n=' + d[4] + ' accounts)';
      }
    },
    toolbox: { feature: { saveAsImage: { title: 'Save', pixelRatio: 2, backgroundColor: c.bgElevated } },
               right: 16, top: 8, iconStyle: { borderColor: c.textTertiary } },
    grid: { left: 140, right: 80, top: 40, bottom: 80 },
    xAxis: { type: 'category', data: productAreas, position: 'top',
             axisLabel: { color: c.textTertiary, fontSize: 11, rotate: 45 } },
    yAxis: { type: 'category', data: productAreas,
             axisLabel: { color: c.textTertiary, fontSize: 11 } },
    visualMap: {
      type: 'continuous', min: 0, max: 100, calculable: true,
      orient: 'horizontal', left: 'center', bottom: 10,
      inRange: { color: [c.red, c.amber, c.green] },
      textStyle: { color: c.textTertiary, fontSize: 11 }
    },
    series: [{
      type: 'heatmap',
      data: matrixData.map(function(d) { return [d[0], d[1], d[2]]; }),
      label: { show: true, color: c.textPrimary, fontSize: 11,
               formatter: function(p) { return p.value[2] + '%'; } },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.3)' } }
    }]
  });
  return chart;
}
```

### ECharts Scatter for ARR-Usage (CORR-08)

```javascript
// Source: UI-SPEC scatter spec + ECharts scatter docs
function renderArrScatter(currentAccount, peers) {
  var c = getThemeColors();
  var chart = echarts.init(document.getElementById('arrScatter'), 'wandb');
  chart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: function(p) {
        if (p.seriesIndex === 0) {
          return 'Peer account: ' + p.value[0] + ' product areas, $' +
                 Math.round(p.value[1] / 1000) + 'K ARR';
        }
        return PAGE_DATA.customer + ': ' + p.value[0] + ' product areas, $' +
               Math.round(p.value[1] / 1000) + 'K ARR';
      }
    },
    xAxis: { type: 'value', name: 'Product Areas', nameLocation: 'center', nameGap: 30,
             axisLabel: { color: c.textTertiary } },
    yAxis: { type: 'value', name: 'ARR ($)', nameLocation: 'center', nameGap: 60,
             axisLabel: { color: c.textTertiary, formatter: function(v) { return '$' + Math.round(v/1000) + 'K'; } } },
    series: [
      {
        name: 'Peers', type: 'scatter', z: 5,
        symbolSize: 6, symbol: 'circle',
        itemStyle: { color: c.textTertiary, opacity: 0.4 },
        data: peers.map(function(p) { return [p.breadth, p.arr]; })
      },
      {
        name: 'Current', type: 'scatter', z: 10,
        symbolSize: 12, symbol: 'diamond',
        itemStyle: { color: c.accent },
        data: [[currentAccount.breadth, currentAccount.arr]]
      }
    ]
  });
  return chart;
}
```

### Performance Gauge (PERF-01, reuses Phase 3 pattern)

```javascript
// Source: Phase 3 risk scoring gauge pattern + UI-SPEC performance spec
function renderPerformanceGauge(score, tier) {
  var c = getThemeColors();
  var chart = echarts.init(document.getElementById('perfGauge'), 'wandb');
  chart.setOption({
    series: [{
      type: 'gauge',
      startAngle: 200, endAngle: -20, min: 0, max: 100,
      axisLine: {
        lineStyle: {
          width: 20,
          color: [[0.49, c.red], [0.79, c.amber], [1, c.green]]
        }
      },
      pointer: { itemStyle: { color: 'auto' }, width: 4 },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false },
      detail: {
        valueAnimation: true,
        fontSize: 36,
        fontFamily: "'Instrument Serif', Georgia, serif",
        offsetCenter: [0, '60%'],
        formatter: '{value}',
        color: c.textPrimary
      },
      data: [{ value: score }]
    }]
  });
  return chart;
}
```

### Latency Histogram with P95 MarkLine (PERF-04)

```javascript
// Source: ECharts bar + markLine docs + UI-SPEC latency spec
function renderLatencyHistogram(bins, p95) {
  var c = getThemeColors();
  var chart = echarts.init(document.getElementById('latencyChart'), 'wandb');
  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: function(params) {
        var d = params[0];
        return d.name + ': ' + d.value + ' chart loads (' +
               bins[d.dataIndex].pct + '% of total)';
      }
    },
    xAxis: { type: 'category', data: bins.map(function(b) { return b.label; }),
             axisLabel: { color: c.textTertiary } },
    yAxis: { type: 'value', name: 'Count',
             axisLabel: { color: c.textTertiary } },
    series: [{
      type: 'bar', data: bins.map(function(b) { return b.count; }),
      itemStyle: { color: c.blue, borderRadius: [3, 3, 0, 0] },
      markLine: {
        silent: true,
        symbol: 'none',
        data: [{ name: 'P95', xAxis: findP95Bin(bins, p95) }],
        lineStyle: { type: 'dashed', color: c.red, width: 2 },
        label: { formatter: 'P95: ' + p95 + 'ms', color: c.red }
      }
    }]
  });
  return chart;
}
```

### Privacy Badge Component (CORR-04)

```javascript
// Source: UI-SPEC Privacy Badge Component Specification (exact spec)
function renderPrivacyBadge() {
  var c = getThemeColors();
  var container = document.getElementById('chartSection');
  var badge = document.createElement('div');
  badge.style.cssText = 'background:rgba(248,113,113,0.10); border:1px solid rgba(248,113,113,0.22); border-radius:6px; padding:8px 16px; margin-bottom:16px; display:flex; align-items:center; gap:12px;';

  var label = document.createElement('span');
  label.style.cssText = 'font-family:JetBrains Mono,monospace; font-size:11px; font-weight:600; letter-spacing:1.5px; text-transform:uppercase; color:' + c.red + '; white-space:nowrap;';
  label.textContent = 'SE-INTERNAL ONLY';

  var desc = document.createElement('span');
  desc.style.cssText = 'font-family:Outfit,sans-serif; font-size:14px; color:' + c.textSecondary + ';';
  desc.textContent = 'Cross-account analysis uses anonymized, pre-aggregated data. Minimum 10-account cohort enforcement. Never share this page with customers.';

  badge.appendChild(label);
  badge.appendChild(desc);
  container.insertBefore(badge, container.firstChild);
}
```

## BQ Query Architecture for Phase 4

### Usage Correlation Queries (Cross-Account)

Phase 4 introduces 3-4 new query functions in `queries.py`. The cross-account queries are architecturally distinct from all prior queries:

| Query | Scope | Privacy | BQ Cost Estimate |
|-------|-------|---------|------------------|
| `cross_account_product_areas_query()` | ALL accounts, 6 months | Returns account_id for grouping; stripped in transform | HIGH -- full table scan with date filter. Set maximum_bytes_billed=100GB |
| `cross_account_retention_query()` | ALL accounts, 6 months | Same as above | HIGH -- same table, different aggregation |
| `cross_account_arr_breadth_query()` | ALL accounts | Joins `stg_salesforce_accounts` for ARR + tier | MEDIUM -- SFDC table is smaller |
| `performance_query()` | Single account | Standard @account_id filter | LOW -- small table |
| `latency_distribution_query()` | Single account | Standard @account_id filter | LOW -- small table |
| `slow_chart_users_query()` | Single account | Standard @account_id filter with identity resolution | LOW |

### Key Consideration: Reusing the Product Area CASE Statement

The product area mapping CASE statement exists in `product_areas_query()` (lines 207-228 of queries.py). The cross-account query needs the IDENTICAL mapping. Two options:

**Option A (recommended): Extract CASE as Python constant**
```python
PRODUCT_AREA_CASE = """
CASE
    WHEN event IN ('run_created', 'run_viewed', 'project_created', 'project_viewed') THEN 'Experiments'
    WHEN event IN ('artifact_created', 'artifact_used', 'artifact_viewed') THEN 'Artifacts'
    ...
    ELSE 'Other'
END
"""

def product_areas_query() -> str:
    return f"... {PRODUCT_AREA_CASE} AS product_area ..."

def cross_account_product_areas_query() -> str:
    return f"... {PRODUCT_AREA_CASE} AS product_area ..."
```

**Option B: Keep inline but document the coupling.** Simpler but risks drift.

### Performance Page Queries (Single Account with Go/No-Go Gate)

```python
def performance_query() -> str:
    """Performance index and slowness metrics from fct_application_performance."""
    perf = _ref("fct_application_performance")
    return f"""
    SELECT
        date_day,
        application_performance_index,
        slow_charts,
        slow_project_search,
        slow_artifact_creating,
        slow_run_sidebar,
        slow_workspace_settings,
        users_facing_errors_ct,
        error_count
    FROM {perf}
    WHERE account_id = @account_id
        AND date_day >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
    ORDER BY date_day
    """

def latency_distribution_query() -> str:
    """Chart load latency data from fct_onscreen_loader_latencies."""
    latency = _ref("fct_onscreen_loader_latencies")
    return f"""
    SELECT
        latency_ms,
        universal_user_id
    FROM {latency}
    WHERE account_id = @account_id
        AND date_day >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    """

def slow_chart_users_query() -> str:
    """Slow chart load breakdown per user from agg_daily_team_members_slow_chart_loads."""
    slow = _ref("agg_daily_team_members_slow_chart_loads")
    dim_users = _ref("dim_users")
    return f"""
    WITH user_slow AS (
        SELECT
            universal_user_id,
            SUM(slow_chart_loads) AS slow_loads,
            SUM(total_chart_loads) AS total_loads,
            MAX(date_day) AS last_seen
        FROM {slow}
        WHERE account_id = @account_id
            AND date_day >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
        GROUP BY universal_user_id
    )
    SELECT
        us.universal_user_id,
        COALESCE(du.local_username, 'unknown') AS username,
        us.slow_loads,
        us.total_loads,
        SAFE_DIVIDE(us.slow_loads, us.total_loads) * 100 AS slow_pct,
        us.last_seen
    FROM user_slow us
    LEFT JOIN {dim_users} du
        ON us.universal_user_id = du.universal_user_id
        AND du.account_id = @account_id
    WHERE us.total_loads > 0
    ORDER BY slow_pct DESC
    """
```

**Note:** The exact column names for `fct_application_performance`, `fct_onscreen_loader_latencies`, and `agg_daily_team_members_slow_chart_loads` are based on schema discovery research and REQUIREMENTS.md references. Schema validation MUST run before queries execute to confirm these columns exist. If columns are missing, the go/no-go gate triggers descoped state.

## Transform Architecture

### UsageCorrelationTransform

The most complex transform in the project. Key responsibilities:

1. **Co-occurrence matrix computation:** For each pair of product areas, count how many accounts have both active. Convert to percentage.
2. **Retention overlay:** For each product combo, compute what % of accounts with that combo had activity in the last 30 days.
3. **Cohort size enforcement:** Any cell in the matrix backed by fewer than 10 accounts is suppressed (set to null/hidden).
4. **Current account positioning:** Match the target account's active product areas against the aggregate patterns.
5. **Next-best-action:** For each product area the target account does NOT use, compute the retention lift if they added it (based on co-occurrence retention data).
6. **Expansion signals:** Compare current usage against SFDC entitlement fields (contracted seats, Weave ingestion cap).
7. **Peer benchmarking:** Group accounts by `cs_tier`, compute product breadth percentiles, rank target account.
8. **ARR-usage scatter:** Extract product breadth + ARR for all accounts in the same tier. Anonymize all peers.
9. **Privacy enforcement:** Strip all account_ids and names before returning PAGE_DATA.

```python
class UsageCorrelationTransform(BaseTransform):
    MIN_COHORT_SIZE = 10

    def transform(self, cross_account: pd.DataFrame,
                  arr_data: pd.DataFrame,
                  current_account_areas: list[str],
                  account_health: dict,
                  **kwargs) -> dict:
        customer_name = kwargs.get("customer_name", "Unknown")

        if cross_account.empty:
            return self.empty_result("cross_account_unavailable")

        # Count unique accounts
        total_accounts = cross_account["account_id"].nunique()
        if total_accounts < self.MIN_COHORT_SIZE:
            return self.empty_result("insufficient_cohort")

        # Build co-occurrence matrix
        # ... (pandas pivot + matrix multiplication)

        # Privacy enforcement: strip account_id from all output structures
        # NEVER include account_id in returned dict

        return {
            "available": True,
            "page_type": "usage-correlation",
            "privacy": {"badge_visible": True, "min_cohort_size": 10, "anonymized": True},
            "correlation_matrix": {...},
            "account_positioning": {...},
            "next_best_action": [...],
            "expansion_signals": [...],
            "peer_benchmarking": {...},
            "arr_scatter": {...},  # peers array has NO account_id or names
            "narrative": self._build_narrative(...),
        }
```

### PerformanceTransform

Simpler than correlation. Key responsibilities:

1. **Performance index:** Average `application_performance_index` over the period, classify into tier (good/fair/poor).
2. **Slowness breakdown:** Sum each `slow_*` column, compute percentages.
3. **Error metrics:** Latest `users_facing_errors_ct` and `error_count`, compute 30d trend.
4. **Latency distribution:** Bin raw latency values into fixed buckets (0-1s, 1-2s, 2-5s, 5-10s, 10s+), compute P50/P95/P99.
5. **Slow chart users:** Identity-resolved user list with slow percentage, sorted descending.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Datadog-sourced performance data | BQ-native `fct_application_performance` | Discovered during schema discovery (2026-03-24) | Eliminates Datadog dependency; all data from BQ |
| Per-account queries only | Cross-account aggregate queries (Phase 4) | Phase 4 (now) | First cross-account query pattern in the project |
| Privacy as afterthought | Privacy as architectural constraint (min cohort, no IDs in output) | Phase 4 (now) | New pattern specific to correlation page |

## Open Questions

1. **Cross-account query BQ cost**
   - What we know: `ext_daily_user_event_usage` is the mega-join table (100+ columns). A cross-account query without `account_id` filter scans all accounts.
   - What's unclear: The actual bytes scanned for a 6-month cross-account product area query. It could be 10GB or 100GB depending on table size.
   - Recommendation: Run a dry-run query first (`dry_run=True` in `run_query()`) to estimate bytes. Set `maximum_bytes_billed=100_000_000_000` (100GB) as the ceiling. If the dry-run estimate exceeds this, reduce the date range to 3 months.

2. **fct_application_performance column names**
   - What we know: The table exists in BQ schema. REQUIREMENTS.md references `application_performance_index`, `slow_charts`, `slow_project_search`, `slow_artifact_creating`, `users_facing_errors_ct`, `error_count`.
   - What's unclear: Whether these exact column names match the actual schema. The schema discovery doc mentions the table but doesn't list every column.
   - Recommendation: Run schema validation with `validate_table_schema()` as the first task. If columns are missing, check `available_columns` in the validation result to find the actual names.

3. **fct_onscreen_loader_latencies granularity**
   - What we know: The table exists and is referenced in the schema discovery doc.
   - What's unclear: Whether it stores individual latency events (one row per chart load) or daily aggregates. This affects how we compute the histogram and P95.
   - Recommendation: Schema validate first. If per-event, use `pd.cut()` for histogram binning. If pre-aggregated, the bins may already be computed.

4. **agg_daily_team_members_slow_chart_loads column names**
   - What we know: Table exists in schema discovery as a per-team performance table.
   - What's unclear: Exact column names (`slow_chart_loads`, `total_chart_loads` are assumed based on table name).
   - Recommendation: Schema validate. The go/no-go gate covers this -- if the table is inaccessible or columns are wrong, the slow chart users section is omitted (not the entire page).

5. **Cross-account retention computation accuracy**
   - What we know: CORR-01 requires retention rates alongside co-occurrence percentages.
   - What's unclear: The best proxy for "retained" using only `ext_daily_user_event_usage` data. True retention requires knowing contract end dates.
   - Recommendation: Use "active in last 30 days" as a simple retention proxy. This is imperfect but computationally feasible and directionally correct.

## Sources

### Primary (HIGH confidence)
- Existing codebase: `queries.py` (all query patterns), `generate.py` (handler/pipeline pattern), `base-template.html` (renderer pattern, PAGE_RENDERERS registry, PAGE_TYPES nav, getThemeColors/registerWandbTheme)
- Existing transforms: `engagement_decay.py`, `feature_velocity.py`, `sdk_versions.py`, `user_journey.py` (all follow identical BaseTransform pattern)
- Phase 3 research (`03-RESEARCH.md`): schema validation patterns, fallback strategies, ECharts chart type configurations
- Phase 4 UI-SPEC (`04-UI-SPEC.md`): complete layout contracts, PAGE_DATA shapes, privacy badge spec, descoped state spec, all copywriting
- ai-docs: `apache-echarts.md` (v5 chart types, heatmap/scatter/gauge config), `wandb-bigquery-schema-discovery.md` (table inventory)

### Secondary (MEDIUM confidence)
- Research docs: `FEATURES.md` (Usage Correlation section -- cross-account query patterns, privacy considerations), `PITFALLS.md` (Pitfall 4: cross-account data leaks, Pitfall 13: performance data availability)
- CLAUDE.md Technology Stack (data processing patterns per analytical dimension)

### Tertiary (LOW confidence)
- `fct_application_performance` column names and data coverage -- based on schema discovery table name and REQUIREMENTS.md references, not direct schema validation
- `fct_onscreen_loader_latencies` granularity -- table existence confirmed but row structure unknown
- `agg_daily_team_members_slow_chart_loads` column names -- inferred from table name

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- zero new dependencies, all chart types proven in prior phases
- Architecture: HIGH for pipeline pattern (identical to Phases 1-3), MEDIUM for cross-account query pattern (novel to this project)
- Pitfalls: HIGH for privacy concerns (well-documented in research), MEDIUM for performance table data availability (needs direct validation)
- BQ queries: MEDIUM for cross-account (novel pattern, cost unknown), LOW for performance tables (column names unvalidated)

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (stable patterns; cross-account query cost may need re-evaluation after first execution)
