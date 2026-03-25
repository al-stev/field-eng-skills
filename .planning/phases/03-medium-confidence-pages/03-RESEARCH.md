# Phase 3: Medium-Confidence Pages - Research

**Researched:** 2026-03-25
**Domain:** Cohort retention analysis, team detection from BQ fields, composite risk scoring, ECharts heatmap/gauge/radar/treemap chart types
**Confidence:** MEDIUM (overall -- driven by data availability uncertainty)

## Summary

Phase 3 delivers three analytical pages -- Cohort Analysis, Team Detection, and Risk Scoring -- that depend on BQ data sources NOT yet validated at query time. The phase's defining characteristic is that schema validation MUST run before any page development begins. Unlike Phase 2 (which used proven tables like `ext_daily_user_event_usage` and `dim_users`), Phase 3 introduces `agg_weekly_user_retention_features` (cohort retention), team fields in `ext_daily_user_event_usage` (which may be sparsely populated), and `renewal_predictions` from the `landing_development` dataset (a different BQ dataset with potentially different IAM permissions).

The established codebase pattern from Phase 1-2 is clear: each page needs (1) a query function in a queries module, (2) a Transform class extending `BaseTransform`, (3) a handler function wired into `generate.py`'s `PAGE_REGISTRY`, and (4) a renderer function added to `PAGE_RENDERERS` in `base-template.html`. Phase 3 follows this same pattern but adds new ECharts chart types not yet used in the template: heatmap (cohort retention matrix), gauge (risk score), radar (risk factor breakdown), and treemap (team hierarchy). These are all built into ECharts v5 core bundle -- no extensions needed.

The critical risk is data availability. The `renewal_predictions` table in `landing_development` has been flagged as potentially inaccessible from `wandb-sa-sandbox`. Team fields (`org_name`, `is_part_of_team`, `count_teams`) exist in `ext_daily_user_event_usage` but may be NULL for many accounts. Each page MUST have a graceful fallback when data is unavailable: Cohort Analysis falls back to computing cohorts from raw `ext_daily_user_event_usage` activity dates, Team Detection shows "Team data unavailable" (TEAM-04 is an explicit requirement), and Risk Scoring computes a behavioral-only score when `renewal_predictions` is inaccessible.

**Primary recommendation:** Start with schema validation of all three data sources as a prerequisite task. Build pages sequentially (Cohort -> Team -> Risk) since Risk Scoring is the most complex data integration and benefits from patterns established by the simpler pages. Each page follows the exact handler + transform + renderer pattern from Phase 2.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CHRT-01 | Retention heatmap (rows=monthly signup cohorts, columns=months since signup, cells=retention %) | ECharts `type: 'heatmap'` with `visualMap` continuous gradient; data from `agg_weekly_user_retention_features` or computed from raw activity |
| CHRT-02 | Cohort size labels on each row showing starting cohort size | Heatmap `label` config or parallel text annotations; cohort sizes from COUNT DISTINCT per cohort month |
| CHRT-03 | Overall retention curve (aggregate % active after 1mo, 3mo, 6mo, 12mo) | ECharts `type: 'line'` series overlaid or in separate chart; computed from same cohort data |
| CHRT-04 | AI narrative interpreting cohort health vs historical averages | Follows existing `_build_narrative()` pattern in FeatureVelocityTransform and SdkVersionsTransform |
| CHRT-05 | New/Retained/Resurrected/Churned stacked area lifecycle chart | ECharts `type: 'line'` with `areaStyle` and `stack`; user accounting fields from `agg_daily_user_activity` |
| CHRT-06 | Cohort-over-cohort trend line overlay (last 4 cohorts) | Multiple line series on same chart, one per cohort; data from same cohort matrix |
| CHRT-07 | Behavioral cohort comparison (group by first action type, compare retention) | Query `dim_users` first_*_at fields to determine first action type, then compute retention per behavioral group |
| TEAM-01 | Team breakdown table listing teams, member counts, total activity, top product areas | GROUP BY `org_name` on `ext_daily_user_event_usage`; product area mapping reuses existing CASE from `product_areas_query()` |
| TEAM-02 | Per-team activity bar chart comparing total activity and unique users | ECharts `type: 'bar'` horizontal bars; data from same team aggregation |
| TEAM-03 | Team x product area heatmap showing which teams use which products | ECharts `type: 'heatmap'` with team rows x product area columns; pivot of team-by-area activity |
| TEAM-04 | Clear "Team data unavailable" message when fields are not populated | Existing `renderEmptyState()` pattern in base-template.html; schema validator checks team field population |
| TEAM-05 | AI narrative identifying team patterns and per-team enablement opportunities | Same `_build_narrative()` pattern; team-specific analysis |
| TEAM-06 | Team adoption timeline showing when each team started using W&B | MIN(date_day) per org_name; ECharts `type: 'bar'` horizontal timeline or scatter |
| TEAM-07 | Per-team champion identification (most active user per team) | MAX(total_events) per team, JOIN with identity resolution; identity_resolution_cte() already available |
| TEAM-08 | Team growth/contraction trend (new users joining vs dropping off per team) | COUNT DISTINCT users per team per month; ECharts `type: 'line'` with `areaStyle` stacked |
| RISK-01 | Composite risk score (0-100) combining ML churn probability, engagement trend, seat utilization, support ticket velocity -- displayed as gauge chart | ECharts `type: 'gauge'` with `axisLine.lineStyle.color` for red/amber/green zones; weighted composite from 4 sources |
| RISK-02 | Risk factor breakdown showing which factors contribute most to the score | Bar chart or detail table below gauge; decomposed weighted components |
| RISK-03 | Risk trend line showing score evolution over last 6 months | Requires recomputing composite score at historical points; ECharts `type: 'line'` |
| RISK-04 | Renewal context (days to renewal, ARR, contract details) alongside risk score | Already available from existing `account_health_query()` in queries.py |
| RISK-05 | AI narrative with actionable risk assessment and recommended SE interventions | `_build_narrative()` pattern with risk-specific analysis |
| RISK-06 | Risk radar chart (multi-dimensional radar showing risk shape at a glance) | ECharts `type: 'radar'` with 5-6 indicator dimensions normalized to 0-100 |
| RISK-07 | AI-generated action recommendations (schedule QBR, run workshop, engage champion) | Part of narrative generation, enriched with full risk context |
| RISK-08 | Historical risk snapshot comparison (now vs 3mo ago vs 6mo ago) | Multiple radar series overlaid (current + historical); requires score recomputation |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| google-cloud-bigquery | >=3.39.0 | BQ query execution | Already in pyproject.toml; all queries use parameterized @account_id |
| pandas | >=2.0.0 | Data transformation | Pivot tables for heatmaps, groupby for teams, rolling windows for risk trends |
| Apache ECharts | 5.x (5.6.0) | Chart rendering (heatmap, gauge, radar, treemap, bar, line) | CDN-loaded; all chart types built into core bundle |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | (via pandas) | Statistical calculations | Correlation coefficients in risk scoring composite |

### No New Dependencies

Phase 3 adds ZERO new Python or JS dependencies. All required chart types (heatmap, gauge, radar, treemap) are in the ECharts v5 core bundle. All data processing uses pandas already in pyproject.toml.

## Architecture Patterns

### Established Page Pipeline (from Phase 1-2)

Each page follows this exact flow:

```
1. generate.py handler function
   -> imports query function from queries module
   -> calls bq_client.run_query() with maximum_bytes_billed
   -> instantiates Transform class
   -> returns PAGE_DATA dict with 'narrative' key

2. Transform class (extends BaseTransform)
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

### Recommended File Structure for Phase 3

```
.claude/skills/deep-analytics/
  scripts/
    transforms/
      cohort_analysis.py       # CohortAnalysisTransform
      team_detection.py        # TeamDetectionTransform
      risk_scoring.py          # RiskScoringTransform
    queries_phase3.py          # New queries (or extend queries.py pattern)
  templates/
    base-template.html         # Add renderCohortAnalysis, renderTeamDetection, renderRiskScoring
```

**Key decision:** New queries can either be added to the existing `bigquery/scripts/queries.py` (following the `_ref()` + `_query()` pattern) or to a new module within deep-analytics. The existing pattern uses `bigquery/scripts/queries.py` for all queries. Follow this pattern -- add new query functions to the same file.

### Handler Pattern (from generate.py)

```python
def _cohort_analysis_handler(client, account_id, customer_name):
    """Cohort Analysis -- retention heatmap from user activity data."""
    from queries import cohort_retention_query, user_lifecycle_query
    from bq_client import run_query
    from transforms.cohort_analysis import CohortAnalysisTransform

    # Schema validation first
    from schema_validator import validate_table_schema
    validation = validate_table_schema(
        client,
        "`wandb-production.analytics.agg_weekly_user_retention_features`",
        ["universal_user_id", "account_id", "study_period", "prediction_period",
         "recency", "frequency", "age"]
    )

    # Query with cost guardrail
    retention_df = run_query(client, cohort_retention_query(),
                             account_id=account_id,
                             maximum_bytes_billed=50_000_000_000)

    transform = CohortAnalysisTransform()
    return transform.transform(retention=retention_df, customer_name=customer_name)
```

### Transform Pattern (from existing transforms)

```python
class CohortAnalysisTransform(BaseTransform):
    def transform(self, retention: pd.DataFrame, **kwargs) -> dict:
        if retention.empty:
            return self.empty_result("no_data")

        customer_name = kwargs.get("customer_name", "Unknown")
        # ... compute cohort matrix, lifecycle states, retention curves
        narrative = self._build_narrative(...)
        return {
            "available": True,
            "reason": None,
            "customer": customer_name,
            "generated": date.today().isoformat(),
            "period": {...},
            "page_type": "cohort-analysis",
            "kpis": [...],
            # page-specific data
            "cohort_matrix": [...],
            "lifecycle": [...],
            "retention_curve": [...],
            "narrative": narrative,
        }
```

### Anti-Patterns to Avoid

- **SELECT * on 100+ column tables:** Column-prune every query. BQ charges by bytes scanned.
- **Assuming team fields are populated:** `org_name`, `is_part_of_team`, `count_teams` may be NULL for many accounts. ALWAYS check and fall back gracefully.
- **Single template per page:** All pages use the SAME `base-template.html`. Chart rendering is done by JS functions registered in `PAGE_RENDERERS`. Do NOT create separate HTML template files per page.
- **Ignoring `renewal_predictions` access failure:** The `landing_development` dataset may not be accessible from `wandb-sa-sandbox`. Risk Scoring MUST have a behavioral-only fallback.
- **Computing risk scores without normalization:** All risk factors must be normalized to 0-100 before weighting. Raw churn probability (0-1), engagement score (varies), seat utilization (0-1), and ticket count (unbounded) are on incompatible scales.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retention cohort computation | Custom SQL window functions | pandas groupby + pivot_table | Cohort computation is a groupby-then-pivot operation. pandas handles missing months, zero-fill, and percentage computation more readably than nested SQL CTEs |
| Heatmap color gradient | Manual CSS color interpolation | ECharts `visualMap` component | `visualMap: { type: 'continuous', inRange: { color: [...] } }` handles interpolation, legend, and interactivity |
| Gauge dial rendering | SVG/Canvas gauge from scratch | ECharts `type: 'gauge'` | Built-in pointer, axis labels, color zones, progress bar, detail text |
| Radar chart geometry | Custom polar coordinate math | ECharts `type: 'radar'` | Handles indicator placement, axis scaling, area fill, multi-series overlay |
| Date bucketing | Manual month/week boundary logic | `pandas.Grouper(freq='ME')` or `FORMAT_DATE('%Y-%m', date_day)` in SQL | Edge cases around month boundaries, partial periods |
| Risk score weighting | Ad-hoc multiplication | Explicit weight dict + normalization function | Weights need to be documented, adjustable, and auditable |

## Common Pitfalls

### Pitfall 1: Schema Validation Confirms Column Exists But Data Is NULL

**What goes wrong:** The schema validator (`validate_table_schema`) uses `SELECT * FROM table LIMIT 0` dry-run to check column existence. This confirms the column is in the schema but tells you NOTHING about whether it contains data for your customer's account_id. Team fields (`org_name`, `is_part_of_team`) may exist as columns but be NULL for 80% of accounts.
**Why it happens:** BQ schema is global per table. Column existence is table-level, data population is account-level.
**How to avoid:** After schema validation succeeds, run a lightweight "data availability" check: `SELECT COUNT(DISTINCT org_name) FROM ext_daily_user_event_usage WHERE account_id = @account_id AND org_name IS NOT NULL LIMIT 1`. If result is 0, render "Team data unavailable" immediately.
**Warning signs:** Transform receives a non-empty DataFrame but all relevant columns are NULL.

### Pitfall 2: `landing_development` Dataset Access Denied

**What goes wrong:** All existing queries target `wandb-production.analytics.*`. The `renewal_predictions` table is in `wandb-production.landing_development.*` which has separate IAM policies. The `wandb-sa-sandbox` project may not have read access to this dataset.
**Why it happens:** BQ IAM is per-dataset, not per-project. Having access to `analytics` does not grant access to `landing_development`.
**How to avoid:** Run schema validation on `renewal_predictions` FIRST, before any risk scoring development. If it fails, implement behavioral-only risk scoring (engagement trend + seat utilization + support tickets, without ML churn probability). The verify.sh script in bigquery-setup already tests this -- check its output.
**Warning signs:** `google.api_core.exceptions.Forbidden: 403` when querying `landing_development.renewal_predictions`.

### Pitfall 3: Cohort Retention Percentages Exceed 100%

**What goes wrong:** If a user appears in multiple "first activity" months (e.g., due to account migration or data backfill), they get double-counted in cohort computation. This produces retention rates >100%.
**Why it happens:** The "first activity" date may not be unique per user if the underlying data has duplicates or the user was active across multiple organizations within the same account.
**How to avoid:** Deduplicate users by `universal_user_id` and take `MIN(date_day)` as the true first activity date. Cap retention percentages at 100% as a safety clamp.
**Warning signs:** Cohort matrix cells with values >100% or retention curves that go up over time.

### Pitfall 4: Risk Score Composite Weights Producing Misleading Results

**What goes wrong:** Naive equal weighting (25% each for 4 factors) produces misleading composites. A customer with 99% churn probability but excellent engagement, utilization, and support gets a moderate risk score (50-60), when they should be flagged as HIGH risk.
**Why it happens:** Churn probability from the ML model may be the single strongest signal, but equal weighting dilutes it.
**How to avoid:** Use asymmetric weighting: churn probability 40%, engagement trend 25%, seat utilization 20%, support velocity 15%. Additionally, apply a "veto" rule: if ANY single factor exceeds a critical threshold (e.g., churn_probability > 0.8), the composite score is floored at 70 regardless of other factors.
**Warning signs:** Customers with known churn risk getting "moderate" composite scores.

### Pitfall 5: Stale `renewal_predictions` Model Output

**What goes wrong:** The `renewal_predictions` table has an `inference_timestamp` column. If the ML model hasn't been retrained recently, churn probabilities may be based on stale features. Displaying a 6-month-old churn prediction as current is misleading.
**Why it happens:** The ML model runs on an unknown schedule. There's no SLA on refresh frequency.
**How to avoid:** Query `MAX(inference_timestamp)` from `renewal_predictions` for the account. If it's older than 30 days, display a staleness banner: "Churn model data is X days old -- interpret with caution." The Risk Scoring page's success criteria explicitly requires this staleness banner.
**Warning signs:** All accounts showing identical or near-identical churn probabilities (suggests stale batch inference).

## Code Examples

### ECharts Heatmap for Cohort Retention Matrix

```javascript
// Source: ECharts v5 docs + ai-docs/apache-echarts.md
// Data format: [[cohortIndex, periodIndex, retentionPct], ...]
function renderCohortHeatmap(cohortLabels, periodLabels, data) {
  var c = getThemeColors();
  var chart = echarts.init(document.getElementById('cohortHeatmap'), 'wandb');
  chart.setOption({
    tooltip: {
      position: 'top',
      formatter: function(p) {
        return cohortLabels[p.value[0]] + ', Month ' + periodLabels[p.value[1]] +
               ': ' + p.value[2] + '% retained';
      }
    },
    toolbox: { feature: { saveAsImage: { title: 'Save', pixelRatio: 2, backgroundColor: c.bgElevated } },
               right: 16, top: 8, iconStyle: { borderColor: c.textTertiary } },
    grid: { left: 120, right: 60, top: 40, bottom: 60 },
    xAxis: { type: 'category', data: periodLabels, position: 'top',
             axisLabel: { color: c.textTertiary, fontSize: 11 } },
    yAxis: { type: 'category', data: cohortLabels,
             axisLabel: { color: c.textTertiary, fontSize: 11 } },
    visualMap: {
      type: 'continuous', min: 0, max: 100, calculable: true,
      orient: 'horizontal', left: 'center', bottom: 10,
      inRange: { color: [c.red, c.amber, c.green] },  // 0%=red, 50%=amber, 100%=green
      textStyle: { color: c.textTertiary }
    },
    series: [{
      type: 'heatmap', data: data,
      label: { show: true, color: c.textPrimary, fontSize: 10,
               formatter: function(p) { return p.value[2] + '%'; } },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } }
    }]
  });
  window.addEventListener('resize', function() { chart.resize(); });
  return chart;
}
```

### ECharts Gauge for Risk Score

```javascript
// Source: ECharts v5 docs + ai-docs/apache-echarts.md
function renderRiskGauge(score, label) {
  var c = getThemeColors();
  var chart = echarts.init(document.getElementById('riskGauge'), 'wandb');
  chart.setOption({
    series: [{
      type: 'gauge',
      min: 0, max: 100,
      startAngle: 200, endAngle: -20,
      axisLine: {
        lineStyle: {
          width: 20,
          color: [
            [0.3, c.green],   // 0-30: low risk
            [0.6, c.amber],   // 30-60: medium risk
            [1, c.red]        // 60-100: high risk
          ]
        }
      },
      pointer: { length: '60%', width: 6, itemStyle: { color: c.textPrimary } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { color: c.textTertiary, fontSize: 11,
                   formatter: function(v) { return v === 0 ? 'Low' : v === 50 ? 'Med' : v === 100 ? 'High' : ''; } },
      detail: {
        valueAnimation: true, fontSize: 36,
        fontFamily: "'Instrument Serif', Georgia, serif",
        color: c.textPrimary, offsetCenter: [0, '70%'],
        formatter: function(v) { return Math.round(v); }
      },
      title: { offsetCenter: [0, '90%'], fontSize: 14,
               fontFamily: "'Outfit', sans-serif", color: c.textSecondary },
      data: [{ value: score, name: label }]
    }]
  });
  window.addEventListener('resize', function() { chart.resize(); });
  return chart;
}
```

### ECharts Radar for Risk Factor Breakdown

```javascript
// Source: ECharts v5 docs + ai-docs/apache-echarts.md
function renderRiskRadar(indicators, currentData, historicalData) {
  var c = getThemeColors();
  var chart = echarts.init(document.getElementById('riskRadar'), 'wandb');
  chart.setOption({
    tooltip: { trigger: 'item' },
    radar: {
      indicator: indicators.map(function(ind) {
        return { name: ind.name, max: 100 };
      }),
      shape: 'circle',
      axisName: { color: c.textSecondary, fontSize: 11,
                  fontFamily: "'Outfit', sans-serif" },
      splitArea: { areaStyle: { color: ['transparent'] } },
      splitLine: { lineStyle: { color: c.borderSubtle } },
      axisLine: { lineStyle: { color: c.borderSubtle } }
    },
    series: [{
      type: 'radar',
      data: [
        { value: currentData, name: 'Current',
          areaStyle: { color: 'rgba(248,113,113,0.2)' },
          lineStyle: { color: c.red, width: 2 } },
        historicalData ? {
          value: historicalData, name: '3 months ago',
          areaStyle: { color: 'rgba(96,165,250,0.1)' },
          lineStyle: { color: c.blue, width: 1, type: 'dashed' }
        } : null
      ].filter(Boolean)
    }]
  });
  window.addEventListener('resize', function() { chart.resize(); });
  return chart;
}
```

### ECharts Stacked Area for User Lifecycle (New/Retained/Resurrected/Churned)

```javascript
// Source: ECharts v5 docs
function renderLifecycleChart(months, newUsers, retained, resurrected, churned) {
  var c = getThemeColors();
  var chart = echarts.init(document.getElementById('lifecycleChart'), 'wandb');
  chart.setOption({
    tooltip: { trigger: 'axis' },
    toolbox: { feature: { saveAsImage: { title: 'Save', pixelRatio: 2, backgroundColor: c.bgElevated } },
               right: 16, top: 8, iconStyle: { borderColor: c.textTertiary } },
    legend: { data: ['New', 'Retained', 'Resurrected', 'Churned'], bottom: 0 },
    grid: { left: 60, right: 40, top: 40, bottom: 60 },
    xAxis: { type: 'category', data: months, boundaryGap: false },
    yAxis: { type: 'value' },
    series: [
      { name: 'Retained', type: 'line', stack: 'total', areaStyle: { color: c.green + '33' },
        lineStyle: { color: c.green }, data: retained },
      { name: 'New', type: 'line', stack: 'total', areaStyle: { color: c.blue + '33' },
        lineStyle: { color: c.blue }, data: newUsers },
      { name: 'Resurrected', type: 'line', stack: 'total', areaStyle: { color: c.amber + '33' },
        lineStyle: { color: c.amber }, data: resurrected },
      { name: 'Churned', type: 'line', stack: 'total', areaStyle: { color: c.red + '33' },
        lineStyle: { color: c.red }, data: churned }
    ]
  });
  window.addEventListener('resize', function() { chart.resize(); });
  return chart;
}
```

### Python: Cohort Retention Matrix Computation

```python
# Source: Standard pandas cohort analysis pattern
def compute_cohort_matrix(df: pd.DataFrame) -> dict:
    """
    Compute retention cohort matrix from user activity data.

    Input DataFrame needs: universal_user_id, date_day (or month)
    Output: dict with cohort_labels, period_labels, matrix (list of [row, col, pct])
    """
    df = df.copy()
    df["month"] = pd.to_datetime(df["date_day"]).dt.to_period("M")

    # First activity month per user = their cohort
    first_activity = df.groupby("universal_user_id")["month"].min().rename("cohort")
    df = df.merge(first_activity, on="universal_user_id")

    # Period offset = months since cohort month
    df["period"] = (df["month"] - df["cohort"]).apply(lambda x: x.n)

    # Active users per cohort per period
    cohort_counts = (
        df.groupby(["cohort", "period"])["universal_user_id"]
        .nunique()
        .reset_index(name="active_users")
    )

    # Cohort sizes (period 0)
    cohort_sizes = cohort_counts[cohort_counts["period"] == 0][["cohort", "active_users"]].rename(
        columns={"active_users": "cohort_size"}
    )

    # Merge and compute retention %
    cohort_counts = cohort_counts.merge(cohort_sizes, on="cohort")
    cohort_counts["retention_pct"] = (
        (cohort_counts["active_users"] / cohort_counts["cohort_size"] * 100)
        .clip(upper=100)  # Safety clamp
        .round(1)
    )

    # Build heatmap data: [[cohort_idx, period_idx, retention_pct], ...]
    cohort_labels = sorted(cohort_counts["cohort"].unique())
    max_period = cohort_counts["period"].max()
    period_labels = [f"M+{i}" for i in range(max_period + 1)]

    matrix = []
    for _, row in cohort_counts.iterrows():
        ci = cohort_labels.index(row["cohort"])
        matrix.append([ci, row["period"], row["retention_pct"]])

    return {
        "cohort_labels": [str(c) for c in cohort_labels],
        "cohort_sizes": {str(c): int(s) for c, s in zip(cohort_sizes["cohort"], cohort_sizes["cohort_size"])},
        "period_labels": period_labels,
        "matrix": matrix,
    }
```

### Python: Composite Risk Score Computation

```python
# Source: Risk scoring research, weighted composite pattern
RISK_WEIGHTS = {
    "churn_model": 0.40,
    "engagement_trend": 0.25,
    "seat_utilization": 0.20,
    "support_velocity": 0.15,
}

CRITICAL_THRESHOLDS = {
    "churn_model": 0.80,       # ML churn probability > 80%
    "engagement_trend": -30,    # Engagement dropped >30% in 3 months
    "seat_utilization": 0.20,   # <20% seat utilization
}

def compute_composite_risk(
    churn_probability: float | None,
    engagement_trend_pct: float,
    seat_utilization_pct: float,
    support_ticket_count_90d: int,
) -> dict:
    """
    Compute composite risk score 0-100 (higher = riskier).

    Returns dict with score, factors, and flags.
    """
    factors = {}

    # Normalize each factor to 0-100 (higher = riskier)
    if churn_probability is not None:
        factors["churn_model"] = min(100, churn_probability * 100)
    else:
        # Redistribute weight when churn model unavailable
        factors["churn_model"] = None

    # Engagement: negative trend = higher risk
    factors["engagement_trend"] = min(100, max(0, 50 - engagement_trend_pct))

    # Seat utilization: lower = higher risk
    factors["seat_utilization"] = min(100, max(0, 100 - seat_utilization_pct * 100))

    # Support velocity: more tickets = higher risk (cap at 10 for normalization)
    factors["support_velocity"] = min(100, support_ticket_count_90d * 10)

    # Compute weighted score
    active_weights = {k: v for k, v in RISK_WEIGHTS.items() if factors.get(k) is not None}
    weight_sum = sum(active_weights.values())
    # Re-normalize weights to sum to 1.0
    normalized_weights = {k: v / weight_sum for k, v in active_weights.items()}

    score = sum(factors[k] * normalized_weights[k] for k in normalized_weights)

    # Veto rule: if any critical threshold exceeded, floor at 70
    veto = False
    if factors.get("churn_model") is not None and churn_probability > CRITICAL_THRESHOLDS["churn_model"]:
        score = max(score, 70)
        veto = True

    return {
        "score": round(score, 1),
        "factors": factors,
        "weights": normalized_weights,
        "veto_applied": veto,
        "churn_model_available": churn_probability is not None,
    }
```

### BQ Query: Cohort Retention from Raw Activity Data

```sql
-- Fallback query when agg_weekly_user_retention_features is unavailable
-- Computes cohorts from raw ext_daily_user_event_usage activity dates
WITH user_first_activity AS (
    SELECT
        universal_user_id,
        FORMAT_DATE('%Y-%m', MIN(date_day)) AS cohort_month
    FROM `wandb-production.analytics.ext_daily_user_event_usage`
    WHERE account_id = @account_id
        AND date_day >= DATE_SUB(CURRENT_DATE(), INTERVAL 18 MONTH)
        AND event_count > 0
    GROUP BY universal_user_id
),
user_monthly_activity AS (
    SELECT DISTINCT
        u.universal_user_id,
        u.cohort_month,
        FORMAT_DATE('%Y-%m', e.date_day) AS active_month
    FROM user_first_activity u
    JOIN `wandb-production.analytics.ext_daily_user_event_usage` e
        ON u.universal_user_id = e.universal_user_id
    WHERE e.account_id = @account_id
        AND e.event_count > 0
)
SELECT
    cohort_month,
    active_month,
    COUNT(DISTINCT universal_user_id) AS active_users
FROM user_monthly_activity
GROUP BY cohort_month, active_month
ORDER BY cohort_month, active_month
```

### BQ Query: Team Detection

```sql
-- Team activity breakdown from org_name field
-- Gracefully handles NULL org_name with COALESCE
SELECT
    COALESCE(org_name, 'Unknown Team') AS team_name,
    COUNT(DISTINCT universal_user_id) AS member_count,
    SUM(event_count) AS total_events,
    COUNT(DISTINCT DATE_TRUNC(date_day, MONTH)) AS active_months,
    MIN(date_day) AS first_activity,
    MAX(date_day) AS last_activity,
    CASE
        WHEN event IN ('run_created', 'run_viewed', 'project_created', 'project_viewed') THEN 'Experiments'
        WHEN event IN ('artifact_created', 'artifact_used', 'artifact_viewed') THEN 'Artifacts'
        WHEN event LIKE 'weave_%' THEN 'Weave'
        ELSE 'Other'
    END AS product_area
FROM `wandb-production.analytics.ext_daily_user_event_usage`
WHERE account_id = @account_id
    AND date_day >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
    AND event_count > 0
GROUP BY team_name, product_area
ORDER BY total_events DESC
```

## Data Modeling Decisions

### Cohort Analysis: Two Query Strategies

**Strategy A (preferred):** Query `agg_weekly_user_retention_features` which has pre-computed recency/frequency/age features. This table is purpose-built for retention analysis and avoids scanning the 100+ column mega-table.

**Strategy B (fallback):** Compute cohorts directly from `ext_daily_user_event_usage` by grouping users by their first activity month and tracking which subsequent months they were active. Heavier query but works if the retention features table is inaccessible.

**Decision:** Attempt Strategy A first. If schema validation fails, fall back to Strategy B. Both should produce the same PAGE_DATA shape so the transform and renderer work identically.

### User Lifecycle States (CHRT-05)

The `agg_daily_user_activity` table has accounting fields with `_accounting` suffix that track user state transitions: New, Retained, Resurrected, Churned per event type. These are the canonical definitions:

| State | Definition |
|-------|-----------|
| **New** | User's first event ever for this account |
| **Retained** | User was active in the prior period AND this period |
| **Resurrected** | User was inactive for 1+ periods, now active again |
| **Churned** | User was active in a prior period, inactive in this period |

Query the `user_*_accounting` fields from `agg_daily_user_activity` aggregated monthly for the lifecycle chart.

### Team Detection: Field Availability

The `ext_daily_user_event_usage` table has these team-relevant fields:
- `org_name` -- organization name (most reliable team proxy)
- `is_part_of_team` -- boolean flag
- `count_teams` -- number of teams user belongs to
- `organization_id` -- org identifier

**Key insight:** `org_name` is the best field for team grouping. It represents the W&B organization, which maps roughly to a team or department. However, it may be NULL for server deployments or accounts without organization structure. The `is_part_of_team` boolean and `count_teams` integer provide supplementary signals.

**Fallback logic:**
1. If `org_name` has >1 distinct non-NULL value for the account: use org_name as team identifier
2. If `org_name` is all NULL but `is_part_of_team` has TRUE values: show "Teams detected but names unavailable"
3. If both are NULL: show "Team data unavailable" (TEAM-04)

### Risk Scoring: Composite Formula

Risk score = weighted sum of 4 normalized factors (each 0-100, higher = riskier):

| Factor | Source | Normalization | Weight |
|--------|--------|---------------|--------|
| Churn model | `renewal_predictions.churn_probability` (0-1) | Multiply by 100 | 40% |
| Engagement trend | `agg_daily_customer_engagement_score` slope over 90 days | 50 - slope_pct (declining = higher risk) | 25% |
| Seat utilization | Existing seat_utilization_query() (active/contracted) | 100 - utilization_pct (lower usage = higher risk) | 20% |
| Support velocity | `dim_helpdesk_tickets` count last 90 days | tickets * 10, capped at 100 | 15% |

**Veto rule:** If `churn_probability > 0.80`, composite score is floored at 70 regardless of other factors.

**When churn model unavailable:** Redistribute 40% weight proportionally among remaining 3 factors. Flag on page: "Risk score excludes ML churn model (data unavailable)."

### Risk Trend (RISK-03, RISK-08)

Computing historical risk scores requires querying historical data for each component at monthly snapshots. This means 6 separate historical queries (one per month, 6 months back) for the engagement and utilization factors. To avoid excessive BQ cost:

- Query engagement score and seat utilization at monthly snapshots using `DATE_TRUNC(date_day, MONTH)` aggregation in a single query each
- Churn model history: query `renewal_predictions` with `inference_timestamp` to get historical predictions
- Support tickets: count per month from `dim_helpdesk_tickets.ticket_created_date_day`
- Recompute composite score at each monthly point

## Schema Validation Specifications

Schema validation MUST run before any page development begins (Success Criteria #4).

### Tables to Validate

```python
PHASE3_SCHEMA_SPECS = {
    # Cohort Analysis
    "`wandb-production.analytics.agg_weekly_user_retention_features`": [
        "universal_user_id", "account_id", "study_period",
        "prediction_period", "recency", "frequency", "age"
    ],
    # Team Detection (team fields in existing table)
    "`wandb-production.analytics.ext_daily_user_event_usage`": [
        "org_name", "is_part_of_team", "count_teams",
        "organization_id", "universal_user_id", "event_count", "date_day"
    ],
    # Risk Scoring
    "`wandb-production.landing_development.renewal_predictions`": [
        "account_id", "churn_probability", "horizon", "inference_timestamp"
    ],
    # User lifecycle states
    "`wandb-production.analytics.agg_daily_user_activity`": [
        "universal_user_id", "account_id", "date_day",
        "user_run_created_accounting", "user_has_any_event_accounting"
    ],
    # Engagement score (for risk scoring)
    "`wandb-production.analytics.agg_daily_customer_engagement_score`": [
        "universal_user_id", "account_id", "date_day",
        "customer_engagement_score"
    ],
}
```

### Validation Procedure

Use the existing `schema_validator.validate_tables()` function. Run all 5 validations. Classify results:

| Validation Result | Action |
|-------------------|--------|
| All pass | Proceed with development using preferred query strategies |
| `agg_weekly_user_retention_features` fails | Use fallback Strategy B (raw activity cohort computation) |
| Team fields pass but data check shows NULLs | Proceed but ensure TEAM-04 empty state works |
| `renewal_predictions` fails | Implement behavioral-only risk scoring (without ML churn) |
| `agg_daily_user_activity` accounting fields fail | Compute lifecycle from raw activity (more complex but feasible) |
| `agg_daily_customer_engagement_score` fails | Use seat utilization as engagement proxy in risk score |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate HTML templates per page | Single base-template.html with PAGE_RENDERERS dispatch | Phase 2 | All pages share one template; chart logic in JS functions |
| Direct SQL for cohort computation | Pre-computed retention features table | Unknown | `agg_weekly_user_retention_features` exists but needs validation |
| Manual risk assessment | ML churn probability model | Pre-existing | `renewal_predictions` table provides 3mo/5mo churn probabilities |

**Deprecated/outdated:**
- The `agg_weekly_user_returning_active_status` table referenced in PROJECT.md: likely a companion to retention features but not confirmed -- validate schema before using

## Open Questions

1. **`agg_weekly_user_retention_features` actual schema**
   - What we know: Table exists in analytics dataset. Has recency/frequency/age columns per schema discovery.
   - What's unclear: Whether the data is per-user or per-account, whether it's updated weekly, whether it covers all accounts or only a subset.
   - Recommendation: Schema validation task will answer this definitively. Have fallback Strategy B ready.

2. **Churn model refresh cadence**
   - What we know: `renewal_predictions` has `inference_timestamp` column. Model outputs 3mo and 5mo horizon predictions.
   - What's unclear: How often the model reruns. Could be daily, weekly, or ad-hoc.
   - Recommendation: Query `MAX(inference_timestamp)` to determine freshness. Display staleness banner per success criteria.

3. **User lifecycle accounting field completeness**
   - What we know: `agg_daily_user_activity` has `user_*_accounting` fields documenting New/Retained/Resurrected/Churned states.
   - What's unclear: Whether these fields are populated for all accounts or only cloud deployments.
   - Recommendation: Include in schema validation. If unavailable, compute lifecycle states manually from presence/absence in monthly activity data.

4. **Team field population rate across customer base**
   - What we know: `org_name`, `is_part_of_team`, `count_teams` exist as columns in `ext_daily_user_event_usage`.
   - What's unclear: What percentage of accounts have non-NULL team data. The CLAUDE.md says "team fields may not exist for all accounts."
   - Recommendation: The data availability check (not just schema check) in the first plan task will answer this. TEAM-04 empty state is mandatory regardless.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| BigQuery ADC | All queries | Assumed (Phase 1 verified) | -- | Run `/bigquery-setup` |
| ECharts CDN | All chart rendering | Yes (CDN) | 5.6.0 | -- |
| uv | Python execution | Yes | 0.10.9 | -- |
| Python | All scripts | Yes | 3.13.12 | -- |
| `wandb-production.landing_development` access | Risk Scoring | Unknown | -- | Behavioral-only risk score |

**Missing dependencies with no fallback:**
- None (all have fallbacks)

**Missing dependencies with fallback:**
- `landing_development` dataset access: behavioral-only risk scoring without ML churn probability

## Project Constraints (from CLAUDE.md)

- **ECharts v5 only** -- do NOT upgrade to v6. CDN: `https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js`
- **Self-contained HTML** -- single file, no external JS/CSS beyond CDN, no build steps
- **BQ cost guardrails** -- `maximum_bytes_billed` on every query, column-pruned SELECTs
- **Identity resolution** -- use `identity_resolution_cte()` for server deployments
- **W&B branding** -- Instrument Serif, Outfit, JetBrains Mono, gold accent, dark/light mode
- **uv run** -- all Python execution via `uv run --project .claude/skills/deep-analytics`
- **No fake data** -- always query real BQ data (per user feedback memory)
- **Graceful empty states** -- every page handles missing data with clear messages
- **Data provenance** -- analytics pages must show deployment type and data source

## Sources

### Primary (HIGH confidence)
- Existing codebase: `generate.py`, `base-template.html`, `feature_velocity.py`, `sdk_versions.py`, `schema_validator.py` -- establishes exact patterns for Phase 3
- Existing codebase: `queries.py`, `bq_client.py` -- query factory and execution patterns
- `~/Documents/gitstuff/ai-docs/apache-echarts.md` -- ECharts v5 chart type configurations (heatmap, gauge, radar, treemap)
- `~/Documents/gitstuff/ai-docs/wandb-bigquery-schema-discovery.md` -- BQ table schemas including team tables, retention features, renewal predictions

### Secondary (MEDIUM confidence)
- `~/Documents/gitstuff/ai-docs/wandb-usage-visualization.md` -- Design vision and product area mappings
- `.planning/research/FEATURES.md` -- Feature specifications for Team Detection, Risk Scoring
- `.planning/research/PITFALLS.md` -- BQ access pitfalls and schema validation requirements
- [Apache ECharts examples](https://echarts.apache.org/examples/en/) -- Heatmap, gauge, radar chart patterns
- [ECharts visual mapping handbook](https://apache.github.io/echarts-handbook/en/concepts/visual-map/) -- visualMap configuration

### Tertiary (LOW confidence)
- `agg_weekly_user_retention_features` actual data population -- needs live validation
- `renewal_predictions` accessibility from `wandb-sa-sandbox` -- needs live validation
- Team field (`org_name`) population rates across customer base -- needs live validation
- User lifecycle accounting field completeness -- needs live validation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- identical to Phase 1-2, no new dependencies
- Architecture: HIGH -- follows exact patterns established in Phase 1-2 codebase
- Data modeling (Cohort): MEDIUM -- retention table schema needs live validation
- Data modeling (Team): MEDIUM -- field population is customer-dependent
- Data modeling (Risk): MEDIUM -- `landing_development` access uncertain, composite formula is research-informed but untested
- ECharts chart types: HIGH -- all types (heatmap, gauge, radar) confirmed in v5 core bundle via ai-docs
- Pitfalls: HIGH -- drawn from codebase analysis and existing pitfalls research

**Research date:** 2026-03-25
**Valid until:** 2026-04-08 (14 days -- medium confidence data sources may change status after validation)
