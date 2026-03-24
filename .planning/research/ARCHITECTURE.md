# Architecture Patterns

**Domain:** BQ Deep Analytics -- 9 standalone HTML pages for usage intelligence
**Researched:** 2026-03-24
**Confidence:** HIGH (based on direct codebase inspection of existing patterns)

## Recommended Architecture

### Decision: New Skill (`deep-analytics`) That Extends the Existing `bigquery` Query Layer

Do NOT add 9 new pages into the `usage-report` skill. Do NOT create query modules inside `bigquery/scripts/`. Instead, create a new `deep-analytics` skill that:

1. **Adds new query functions** to the existing `bigquery/scripts/queries.py` (query layer stays centralized)
2. **Owns its own data transformation scripts** (one per analytical page)
3. **Owns its own HTML templates** (one per analytical page)
4. **Shares the W&B design system** via a reference document, not shared code (because HTML templates are self-contained)

**Rationale:**
- The existing `usage-report` skill serves a specific purpose (aggregate overview for QBR) and its SKILL.md is tightly scoped. Dumping 9 new pages into it would overload the skill boundary.
- The existing `bigquery` skill is correctly positioned as the shared query layer. New SQL queries belong there. But data transformation and HTML rendering do NOT belong in `bigquery/` -- that skill outputs JSON at its CLI boundary.
- A new skill gives each analytical direction its own SKILL.md, argument-hint, and allowed-tools pattern, consistent with the project's skill-per-capability architecture.

### Architecture Diagram

```
.claude/skills/
  bigquery/
    scripts/
      queries.py          <-- ADD new query functions here (query layer)
      bq_client.py         -- unchanged (shared BQ client)
      usage.py             -- unchanged (aggregate usage pipeline)
      account.py           -- unchanged (account health lookup)

  deep-analytics/          <-- NEW SKILL
    SKILL.md               -- skill definition, argument-hint, pipeline docs
    pyproject.toml         -- uv project (depends on bigquery skill indirectly via subprocess)
    scripts/
      generate.py          -- CLI entry point: orchestrates query + transform + render
      transforms/
        __init__.py
        user_journey.py    -- transform: BQ rows -> UserJourney JSON structure
        cohort.py          -- transform: BQ rows -> CohortAnalysis JSON structure
        engagement_decay.py
        feature_velocity.py
        team_detection.py
        risk_scoring.py
        usage_correlation.py
        sdk_versions.py
        performance.py     -- transform: Datadog/BQ -> PerformanceDeepDive JSON structure
      common/
        __init__.py
        data_utils.py      -- shared transform helpers (date bucketing, trend math, zone classification)
    templates/
      user-journey.html
      cohort-analysis.html
      engagement-decay.html
      feature-velocity.html
      team-detection.html
      risk-scoring.html
      usage-correlation.html
      sdk-versions.html
      performance.html

  usage-report/            -- UNCHANGED (existing aggregate reports)
    templates/
      usage-report-external.html
      usage-report-internal.html

  customer-snapshot/       -- UNCHANGED (existing intelligence dashboard)
    templates/
      intelligence-dashboard.html
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `bigquery/scripts/queries.py` | SQL query factory -- all BQ queries live here | Called by `bigquery/scripts/usage.py`, called by `deep-analytics/scripts/generate.py` |
| `bigquery/scripts/bq_client.py` | BQ authentication, parameterized query execution, customer registry lookup | Called by any script that needs BQ data |
| `bigquery/scripts/usage.py` | Aggregate usage pipeline (existing) -- runs 7 queries, builds JSON | CLI consumer of queries.py, produces JSON for usage-report templates |
| `deep-analytics/scripts/generate.py` | Orchestrator -- routes to correct transform + template per page type | CLI entry point, calls BQ via subprocess or direct import |
| `deep-analytics/scripts/transforms/*` | Data transformation -- BQ DataFrames -> page-specific JSON structures | One transform per page, imports from common/ |
| `deep-analytics/scripts/common/` | Shared transform utilities (date math, trend computation, zone classification) | Imported by all transforms |
| `deep-analytics/templates/*.html` | Self-contained HTML pages with ECharts, W&B design system | Receives JSON data injected at `const PAGE_DATA = {...}` |

### Why NOT Share Code Between HTML Templates

The existing codebase has a clear pattern: each HTML template is **fully self-contained**. The design system CSS tokens, ECharts theme registration, and utility functions are **duplicated** across all three existing templates (usage-report-external, usage-report-internal, intelligence-dashboard). This is intentional:

1. **Self-contained HTML files can be opened by anyone** -- no build step, no asset server, no dependency resolution
2. **Templates are generated artifacts** -- Claude Code reads a template, injects data constants, writes the output file. Shared includes would require a build/concatenation step that doesn't exist.
3. **Each template evolves independently** -- the intelligence-dashboard ECharts theme already differs slightly from usage-report-external's version (color-scheme detection approach, radar config)

**Keep this pattern for the 9 new pages.** Each template will duplicate the design tokens and ECharts theme registration. The duplication cost is ~80 lines of CSS + ~30 lines of JS per template -- trivial for generated artifacts that are never manually maintained.

**What IS shared:** The design system is documented in `customer-snapshot/references/design-system.md`. All templates follow this reference document. That is the shared contract -- not shared code.

## Data Flow

### Per-Page Generation Pipeline

```
                    Query Layer              Transform Layer           Presentation Layer
                    ───────────              ───────────────           ──────────────────

templates/         bigquery/scripts/        deep-analytics/           deep-analytics/
customers.yaml ──> bq_client.py             scripts/transforms/       templates/
                   (customer lookup +        (Python)                  (HTML + ECharts)
                    BQ auth)
                       |
                       v
                   queries.py ──────────> generate.py ──────────> [page-type].html
                   (SQL factory)          (orchestrator)
                       |                      |                        |
                       v                      v                        v
                   BigQuery               Transform module         Template with
                   (wandb-production)     produces JSON            PAGE_DATA injected
                       |                  structure                     |
                       v                      |                        v
                   pandas DataFrame           v                   Output HTML file in
                                         JSON dict matching       customers/<name>/
                                         template contract        analytics/
```

### Detailed Data Flow (Single Page)

```
1. CLI invocation:
   uv run --project .claude/skills/deep-analytics \
     python .claude/skills/deep-analytics/scripts/generate.py \
     --customer GResearch --page user-journey

2. generate.py:
   a. Looks up sfdc_account_id via bq_client.get_sfdc_account_id()
   b. Creates BQ client via bq_client.get_client()
   c. Runs page-specific queries from queries.py
   d. Passes DataFrames to transforms/user_journey.py
   e. Gets back a PAGE_DATA dict
   f. Reads templates/user-journey.html
   g. Replaces `const PAGE_DATA = {...};` with real JSON
   h. Writes to customers/g-research/analytics/2026-03-24-user-journey.html

3. Output: self-contained HTML file opened with `open <path>`
```

### Data Contract Between Layers

Each analytical page has a well-defined JSON contract between its transform module and HTML template:

```python
# Transform module outputs:
{
    "customer": "GResearch",
    "generated": "2026-03-24",
    "period": {"start": "2025-03-24", "end": "2026-03-24"},
    "available": True,
    # Page-specific data follows...
    "stages": [...],       # e.g., user-journey
    "cohorts": [...],      # e.g., cohort-analysis
    "users": [...],        # e.g., engagement-decay
}

# Template reads:
const PAGE_DATA = { /* injected by generate.py */ };
```

The template's JavaScript handles all rendering: conditional section display, empty states, ECharts initialization, and responsive behavior. The generating agent only injects the data constants -- same pattern as existing usage-report and customer-snapshot templates.

### Query Reuse Map

Shows which existing and new queries feed which pages. Critical for understanding dependencies.

| Page | Existing Queries (reuse) | New Queries Needed |
|------|-------------------------|--------------------|
| User Journey | `power_users_query()` (partial) | `user_journey_query()` -- dim_users first_*_at fields, adoption stage progression |
| Cohort Analysis | -- | `cohort_retention_query()` -- agg_weekly_user_retention_features, returning_active_status |
| Engagement Decay | -- | `engagement_decay_query()` -- ext_daily_user_event_usage per-user weekly aggregation |
| Feature Velocity | `product_areas_query()` (extend) | `feature_velocity_query()` -- weekly time-series per product area with momentum calc |
| Team Detection | -- | `team_detection_query()` -- ext_daily_user_event_usage team fields grouped |
| Risk Scoring | `account_health_query()` (reuse) | `risk_scoring_query()` -- renewal_predictions + engagement + revenue signals combined |
| Usage Correlation | `product_areas_query()` (partial) | `usage_correlation_query()` -- cross-account product combo analysis |
| SDK Versions | -- | `sdk_version_query()` -- cli_version, local_version distribution |
| Performance | -- | `performance_query()` -- TBD, depends on what BQ perf tables exist |

## Patterns to Follow

### Pattern 1: Subprocess CLI Boundary (Existing Pattern)

**What:** Skills call other skills via `subprocess.run()` + JSON stdout, not direct Python imports.
**When:** Cross-skill communication.
**Why:** Each skill has its own `uv run --project` isolation. Direct imports across skill boundaries break dependency isolation.

```python
# How usage-report calls bigquery today:
result = subprocess.run(
    ["uv", "run", "--project", ".claude/skills/bigquery",
     "python", ".claude/skills/bigquery/scripts/usage.py",
     "--customer", customer_name],
    capture_output=True, text=True
)
usage_data = json.loads(result.stdout)
```

**For deep-analytics:** The new skill should call `bigquery` queries directly via Python import (not subprocess) because deep-analytics needs raw DataFrames, not pre-aggregated JSON. This means deep-analytics must include `bigquery/scripts/` in its Python path or share the same `uv` project.

**Recommended approach:** deep-analytics uses the same uv project as bigquery (shared `pyproject.toml`) OR adds `bigquery/scripts/` to `sys.path`. The simpler option: add bigquery's scripts directory to `sys.path` in generate.py, mirroring how `usage.py` already does sibling imports. This avoids subprocess overhead for 2-4 BQ queries per page.

```python
# In deep-analytics/scripts/generate.py:
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "bigquery" / "scripts"))
from bq_client import get_client, run_query, get_sfdc_account_id
from queries import user_journey_query, cohort_retention_query  # etc.
```

### Pattern 2: Graceful Degradation Per Section

**What:** Each data section independently handles missing data. Null sections are omitted from the page, not shown as errors.
**When:** Always -- BQ tables may be empty or inaccessible for any given customer.
**Example from existing code:**

```python
# From usage.py -- each sub-section degrades independently:
if all(s is None for s in [seat_util, weave, tracked, health]):
    return {"available": False, "reason": "no_data"}
```

**For deep-analytics:** Each page transform should return `{"available": False, "reason": "..."}` when its primary data source is empty. Templates should have an empty state for this case.

### Pattern 3: Template Data Injection via Constant Replacement

**What:** Templates contain a JavaScript constant with sample data. The generating agent reads the template, replaces the sample data with real data, and writes the output file.
**When:** Every report generation.
**Why:** No templating engine needed. The HTML file is valid with sample data (useful for template development/testing) and valid with real data.

```javascript
// In template (sample data for development):
const PAGE_DATA = {
    customer: "Sample Corp",
    generated: "2026-01-01",
    available: true,
    // ... sample data
};

// After generation (real data injected):
const PAGE_DATA = {
    customer: "GResearch",
    generated: "2026-03-24",
    available: true,
    // ... real BigQuery data
};
```

### Pattern 4: ECharts Theme via `registerTheme('wandb', ...)`

**What:** All ECharts charts use a registered 'wandb' theme for consistent styling.
**When:** Every chart initialization.
**Why:** Matches the design system (JetBrains Mono axis labels, Outfit tooltips, gold/blue/green palette, transparent background).

Three existing implementations exist with slight variations. For new pages, use the external-report version (most complete, supports light/dark mode detection via `getThemeColors()`).

```javascript
// Pattern: detect theme, register once, init all charts with 'wandb'
function getThemeColors() {
    const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    return { /* colors from CSS vars or hardcoded */ };
}
function registerWandbTheme() {
    const c = getThemeColors();
    echarts.registerTheme('wandb', { /* theme config */ });
}
// Then:
const chart = echarts.init(el, 'wandb');
```

### Pattern 5: Output Path Convention

**What:** Generated files go to `customers/<kebab-case-name>/<category>/YYYY-MM-DD-<type>.html`.
**When:** Every generated artifact.

```
# Existing:
customers/g-research/usage/2026-03-24-usage-report.html
customers/g-research/usage/2026-03-24-usage-report-internal.html

# New deep-analytics pages:
customers/g-research/analytics/2026-03-24-user-journey.html
customers/g-research/analytics/2026-03-24-cohort-analysis.html
customers/g-research/analytics/2026-03-24-engagement-decay.html
# ...etc
```

Note: use `analytics/` subdirectory (not `usage/`) to distinguish deep-analytics pages from the existing usage reports.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Shared CSS/JS Include Files
**What:** Extracting design tokens or ECharts theme into a shared `.css` or `.js` file and linking it from templates.
**Why bad:** Breaks the self-contained HTML contract. Output files would depend on an external asset that must be co-located. Cannot be emailed, opened from Downloads folder, or shared via Slack.
**Instead:** Duplicate design tokens and ECharts theme registration in each template. Document the canonical version in design-system.md.

### Anti-Pattern 2: Query Logic in Transform Modules
**What:** Writing SQL strings inside `transforms/user_journey.py` or any transform module.
**Why bad:** Scatters SQL across the codebase. The centralized query factory (`queries.py`) is the single source of truth for all BQ queries. Other skills may need the same queries.
**Instead:** All SQL lives in `queries.py`. Transform modules receive DataFrames and produce JSON.

### Anti-Pattern 3: Templating Engine (Jinja, Mako, etc.)
**What:** Using a Python templating engine to render HTML.
**Why bad:** Adds a dependency, changes the generation pattern (template now needs compilation), and makes templates harder to preview/edit in a browser. The existing pattern of "valid HTML with sample data, constant replacement for real data" is simpler and works.
**Instead:** Keep the JavaScript constant injection pattern.

### Anti-Pattern 4: Monolithic Transform Module
**What:** One giant `analytics.py` that handles all 9 page types with a big switch statement.
**Why bad:** 9 pages with different data shapes, different BQ queries, different aggregation logic. A monolith would be untestable and unmaintainable.
**Instead:** One transform module per page. Common utilities in `common/data_utils.py`.

### Anti-Pattern 5: Cross-Account Queries Without Scoping
**What:** Running Usage Correlation queries that scan all accounts without explicit authorization.
**Why bad:** Privacy risk. The correlation page needs cross-account data, but should only be generated for SE-internal use.
**Instead:** Usage Correlation template must be marked internal-only. The transform module should document the cross-account nature. Never generate for customer sharing.

## Shared Utilities (`common/data_utils.py`)

Functions that will be reused across multiple transform modules:

```python
# Date/time helpers
def bucket_weekly(df, date_col='date_day') -> pd.DataFrame
def bucket_monthly(df, date_col='date_day') -> pd.DataFrame
def compute_trend(current, previous) -> float  # percent change
def days_since(date_val) -> int

# Engagement math
def classify_engagement_zone(days_inactive) -> str  # active/cooling/cold/dormant
def compute_momentum(time_series, window=4) -> float  # acceleration/deceleration

# Product area mapping (extracted from existing queries.py CASE statement)
PRODUCT_AREA_MAP = {
    'run_created': 'Experiments',
    'artifact_created': 'Artifacts',
    # ... full mapping
}
def map_product_area(event: str) -> str

# Zone classification (reused from usage.py)
def classify_utilization_zone(percent: float) -> str

# Formatting
def format_date_label(date_val) -> str  # "15 Mar" format for chart labels
def safe_divide(numerator, denominator, default=0) -> float
```

## Build Order Implications

The following order respects dependencies and maximizes parallel work after the foundation is laid.

### Phase 1: Foundation (must be first)
1. Create `deep-analytics` skill directory structure, `pyproject.toml`, `SKILL.md`
2. Create `scripts/generate.py` orchestrator with routing to page types
3. Create `scripts/common/data_utils.py` with shared utilities
4. Add first batch of query functions to `bigquery/scripts/queries.py`

**Why first:** Everything else depends on the skill structure, the orchestrator, and the shared utilities.

### Phase 2: High-Confidence Pages (parallel after foundation)
These pages have HIGH data confidence and can be built in parallel by subagents:

| Page | Why First | Query Dependency |
|------|-----------|-----------------|
| Feature Velocity | Extends existing `product_areas_query()` -- smallest delta | `feature_velocity_query()` |
| SDK Versions | Simple aggregation, HIGH confidence data | `sdk_version_query()` |
| Engagement Decay | Straightforward per-user weekly aggregation | `engagement_decay_query()` |
| User Journey | dim_users first_*_at fields confirmed available | `user_journey_query()` |

### Phase 3: Medium-Confidence Pages (after Phase 2 proves the pattern)
| Page | Why Later | Query Dependency |
|------|-----------|-----------------|
| Cohort Analysis | Retention tables need schema exploration | `cohort_retention_query()` |
| Team Detection | Team fields may not be populated for all accounts | `team_detection_query()` |
| Risk Scoring | renewal_predictions in different dataset | `risk_scoring_query()` |

### Phase 4: Complex/Low-Confidence Pages (last)
| Page | Why Last | Query Dependency |
|------|----------|-----------------|
| Usage Correlation | Cross-account queries, privacy considerations, complex analysis | `usage_correlation_query()` |
| Performance | LOW data confidence, Datadog PDFs not queryable, BQ perf tables unknown | `performance_query()` |

### Parallel Build Pattern (within each phase)

After the foundation is complete, each page is independent:
```
Page build = new query function + transform module + HTML template
```

Each page has zero code-level dependencies on other pages. A subagent can build "SDK Versions" in complete isolation from a subagent building "User Journey". The only shared resources are:
- `queries.py` (add functions, don't modify existing ones)
- `common/data_utils.py` (import shared helpers)
- Design system reference (documented, not code-shared)

## Scalability Considerations

| Concern | At 1 page | At 9 pages | Mitigation |
|---------|-----------|------------|------------|
| BQ query count per customer | 2-3 queries | 15-25 queries (if generating all pages) | generate.py should support `--page` flag to generate one page at a time, not all 9 |
| Template maintenance | Trivial | 9 files with duplicated CSS/JS tokens | design-system.md is the source of truth. Changes propagate via regeneration, not manual edits |
| Query factory size | ~300 lines | ~600-700 lines | Group query functions by analytical direction with clear docstrings. Consider splitting into `queries.py` (existing) + `analytics_queries.py` (new) if it gets unwieldy |
| Transform module count | 1 file | 9 files + common/ | Each module is independent and testable. common/ prevents drift in shared logic |

## Sources

- Direct codebase inspection of:
  - `bigquery/scripts/queries.py` (449 lines, 7 query functions + aggregate helper)
  - `bigquery/scripts/usage.py` (559 lines, 7-query pipeline + JSON builders)
  - `bigquery/scripts/bq_client.py` (125 lines, ADC auth + parameterized execution)
  - `usage-report/SKILL.md` (full pipeline documentation)
  - `usage-report/templates/usage-report-external.html` (1360 lines)
  - `usage-report/templates/usage-report-internal.html` (1653 lines)
  - `customer-snapshot/templates/intelligence-dashboard.html` (3721 lines)
  - `customer-snapshot/references/design-system.md` (authoritative design rules)
- `bigquery/pyproject.toml` (dependency list)
- `bigquery/SKILL.md` (consumer pattern documentation)
