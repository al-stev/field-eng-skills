# Phase 1: Foundation and Template System - Research

**Researched:** 2026-03-24
**Domain:** Skill scaffolding, BQ cost guardrails, schema validation, W&B design system extraction, HTML template foundation
**Confidence:** HIGH

## Summary

Phase 1 builds the `deep-analytics` skill scaffolding and cross-cutting infrastructure that every subsequent page depends on. The deliverables are: (1) a new uv-isolated skill directory with CLI orchestrator, (2) shared identity resolution and schema validation utilities, (3) cost-guarded BQ query execution with `maximum_bytes_billed` and bytes-processed logging, (4) a documented W&B design system extracted from the three existing templates, and (5) a foundation HTML template that demonstrates all XCUT requirements (AI narrative, KPI row, date range header, dark/light mode, empty states, tooltips, saveAsImage, copy-to-clipboard, linked navigation) with sample data.

The key insight from codebase inspection is that this is NOT a greenfield build. Three production HTML templates already define the design system, and the `bigquery` skill already defines query patterns. Phase 1 must follow these established patterns exactly -- the new skill extends them rather than inventing alternatives. The most important pattern decisions are already locked by the existing codebase: self-contained HTML with inline data injection, ECharts v5 with `wandb` registered theme, `sys.path` for cross-skill Python imports, and `customers.yaml` as the routing registry.

**Primary recommendation:** Build the `deep-analytics` skill as a thin orchestrator that imports directly from `bigquery/scripts/` via `sys.path`, adds `maximum_bytes_billed` to the existing `run_query()` function, creates a reusable identity resolution CTE in `queries.py`, and produces a single foundation HTML template that exercises every XCUT requirement with hardcoded sample data -- ready for real data injection in Phase 2.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FOUND-01 | New `deep-analytics` skill directory with uv project, orchestrator (generate.py), and CLI entry point | Exact directory structure, pyproject.toml, sys.path import pattern, CLI arg pattern all documented from existing bigquery/usage-report skills |
| FOUND-02 | Shared identity resolution CTE utility for dim_users JOIN (server deployment support) | Existing `power_users_query()` lines 216-262 provide the exact JOIN pattern; needs extraction into reusable CTE function in queries.py |
| FOUND-03 | BQ cost guardrails: maximum_bytes_billed on every new query, bytes-processed logging | `bq_client.py` `run_query()` needs enhancement -- currently no `maximum_bytes_billed` or logging; google-cloud-bigquery QueryJobConfig pattern documented |
| FOUND-04 | Schema validation utility that checks table existence and required columns before querying | New utility needed; pattern: `SELECT column_name FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name = @table` before query execution |
| FOUND-05 | Shared W&B design system (CSS tokens, ECharts wandb theme, fonts, dark/light mode) documented and extractable | All three existing templates inspected; exact CSS custom properties, ECharts registerTheme config, and Google Fonts import extracted verbatim below |
| XCUT-01 | AI narrative summary section with SE talk-track text generated at build time | Pattern exists in usage-report SKILL.md -- `AI_NARRATIVE` JS constant with executive_summary, recommendations, highlights; injected alongside PAGE_DATA |
| XCUT-02 | KPI headline row (2-4 top-level numbers) above charts | External template has inline stats pattern (value + label pairs, flex layout); NOT KPI cards (anti-pattern per design-system.md) |
| XCUT-03 | Date range context header showing analysis period | External template header-meta shows period; `PAGE_DATA.period.start` / `PAGE_DATA.period.end` pattern |
| XCUT-04 | W&B branding (Instrument Serif, Outfit, JetBrains Mono, gold accent, noise texture) | Exact font imports, CSS tokens, noise SVG pattern extracted from usage-report-external.html |
| XCUT-05 | Self-contained HTML (single file, ECharts CDN, inline CSS/JS, no server) | Locked pattern from all 3 existing templates; CDN URL: `https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js` |
| XCUT-06 | Dark/light mode via prefers-color-scheme CSS media query | Full CSS custom property set for both modes extracted from usage-report-external.html lines 13-74 |
| XCUT-07 | Graceful empty states when customer lacks data for a dimension | `renderEmptyState()` pattern from external template; `.empty-state` CSS class; config_error/no_data/api_error handling |
| XCUT-08 | Interactive tooltips on all chart data points | ECharts wandb theme includes tooltip config: `trigger: 'axis'` for time-series, `trigger: 'item'` for individual; Outfit font, 6px radius |
| XCUT-09 | Print/screenshot readiness (ECharts saveAsImage toolbox) | NEW: Not in any existing template; ECharts `toolbox: { feature: { saveAsImage: {} } }` pattern from ECharts docs |
| XCUT-10 | Copy-to-clipboard for AI narrative text | NEW: Not in any existing template; `navigator.clipboard.writeText()` API; needs button with visual feedback |
| XCUT-11 | Linked navigation between related pages | NEW: Not in any existing template; simple `<a>` links in a nav bar pointing to sibling analytics pages by filename convention |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| google-cloud-bigquery | >=3.39.0 (current 3.40.1) | BQ query execution with ADC | Already in bigquery pyproject.toml; parameterized queries, Arrow transfer |
| google-cloud-bigquery-storage | >=2.36.0 | Fast DataFrame transfer | Required for `to_dataframe()` performance; already a dependency |
| pandas | >=2.0.0 | Data transformation | DataFrame output from BQ, aggregation, pivot; already a dependency |
| pyarrow | >=17.0.0 | Arrow format transfer | Required by BQ storage API; already a dependency |
| db-dtypes | >=1.5.0 | BQ date/time dtypes | Required for DATE/TIME columns in pandas; already a dependency |
| pyyaml | >=6.0 | Customer registry | Reading customers.yaml; already a dependency |
| Apache ECharts | 5.x (5.6.0) | Chart rendering | CDN-loaded; wandb theme registered; all needed chart types in core bundle |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=9.0 | Testing | Dev dependency for unit tests on transforms, validation, and data_utils |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| sys.path import | subprocess JSON boundary | Need raw DataFrames for transforms, not pre-aggregated JSON; subprocess adds overhead for 2-4 queries per page |
| Shared pyproject.toml | Separate uv project | deep-analytics needs identical deps to bigquery; sharing avoids dependency drift but creates coupling |
| ECharts v5 | ECharts v6 | v6 has breaking theme changes; existing 3 templates all use v5; no v6 features needed |

**Installation:**
```bash
# No new packages needed. The deep-analytics skill reuses bigquery's dependency set.
# pyproject.toml mirrors bigquery-skill/pyproject.toml exactly.
```

**Version verification:** Python 3.13.12 confirmed in bigquery uv venv. uv 0.10.9, gcloud SDK 561.0.0 confirmed on host.

## Architecture Patterns

### Recommended Project Structure

```
.claude/skills/
  deep-analytics/                    # NEW SKILL
    SKILL.md                         # Skill definition, CLI usage, pipeline docs
    pyproject.toml                   # uv project (same deps as bigquery)
    scripts/
      generate.py                    # CLI orchestrator: --customer X --page Y
      schema_validator.py            # Table existence + column validation
      transforms/
        __init__.py
        base.py                      # Base transform class / contract
      common/
        __init__.py
        data_utils.py                # Shared transform helpers
    templates/
      base-template.html             # Foundation template with all XCUT features
    tests/
      __init__.py
      conftest.py                    # Shared fixtures
      test_generate.py               # Orchestrator routing tests
      test_schema_validator.py        # Validation utility tests
      test_data_utils.py             # Shared helpers tests

  bigquery/scripts/
    bq_client.py                     # MODIFY: add maximum_bytes_billed, bytes logging
    queries.py                       # MODIFY: add identity_resolution_cte() utility
```

### Pattern 1: Cross-Skill Python Import via sys.path

**What:** deep-analytics imports from bigquery/scripts/ by inserting the path at runtime.
**When:** Always -- generate.py needs bq_client and queries directly.
**Why:** Need raw DataFrames for transformation, not pre-aggregated JSON from subprocess.
**Source:** Existing pattern in usage.py line 23-24.

```python
# In deep-analytics/scripts/generate.py:
import sys
from pathlib import Path

# Add bigquery scripts to path (same pattern as usage.py)
SKILLS_DIR = Path(__file__).resolve().parents[2]  # .claude/skills/
sys.path.insert(0, str(SKILLS_DIR / "bigquery" / "scripts"))

from bq_client import get_client, run_query, get_sfdc_account_id
from queries import identity_resolution_cte  # new utility
```

### Pattern 2: CLI Orchestrator with Page Routing

**What:** generate.py accepts `--customer` and `--page` args, routes to the correct query + transform + template.
**When:** Every page generation.
**Source:** Modeled on usage.py main() argparse pattern.

```python
# generate.py CLI interface:
def main():
    parser = argparse.ArgumentParser(
        description="Generate deep analytics pages from BigQuery data"
    )
    parser.add_argument("--customer", required=True, help="Customer name")
    parser.add_argument("--page", required=True,
        choices=["user-journey", "cohort-analysis", "engagement-decay",
                 "feature-velocity", "team-detection", "risk-scoring",
                 "usage-correlation", "sdk-versions", "performance"],
        help="Analytics page type")
    parser.add_argument("--output-dir", default=None,
        help="Override output directory (default: customers/<name>/analytics/)")
    args = parser.parse_args()

    # 1. Look up customer
    account_id = get_sfdc_account_id(args.customer)
    client = get_client()

    # 2. Route to page-specific pipeline
    page_func = PAGE_REGISTRY[args.page]
    result = page_func(client, account_id, args.customer)

    # 3. Inject into template and write output
    output_path = write_output(args.customer, args.page, result, args.output_dir)
    print(json.dumps({"success": True, "path": str(output_path)}, indent=2))
```

### Pattern 3: Template Data Injection via Constant Replacement

**What:** Templates contain `const PAGE_DATA = {...};` with sample data. generate.py reads template, replaces the constant, writes output.
**When:** Every report generation.
**Source:** Exact pattern from usage-report (uses `USAGE_DATA`) and customer-snapshot (uses `INTELLIGENCE_DATA`).

```python
# In generate.py:
def write_output(customer_name, page_type, data_dict, output_dir=None):
    """Read template, inject PAGE_DATA and AI_NARRATIVE, write to output."""
    template_path = TEMPLATES_DIR / f"base-template.html"  # later: per-page templates
    template = template_path.read_text()

    # Replace sample data with real data
    data_json = json.dumps(data_dict, indent=2, default=str)
    # Find and replace the const PAGE_DATA = {...}; block
    import re
    template = re.sub(
        r'const PAGE_DATA = \{[^}]*(?:\{[^}]*\}[^}]*)*\};',
        f'const PAGE_DATA = {data_json};',
        template,
        count=1,
        flags=re.DOTALL,
    )

    # Write output
    if output_dir is None:
        slug = re.sub(r'[^a-z0-9]+', '-', customer_name.lower()).strip('-')
        output_dir = PROJECT_ROOT / "customers" / slug / "analytics"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    output_path = output_dir / f"{today}-{page_type}.html"
    output_path.write_text(template)
    return output_path
```

### Pattern 4: Graceful Degradation per Section

**What:** Each data section independently handles missing data. Transform returns `{"available": False, "reason": "..."}` when primary data source is empty.
**When:** Always -- BQ tables may be empty or inaccessible for any customer.
**Source:** usage.py `_is_empty()` pattern, `build_usage_json()` lines 478-480.

```python
# In each transform module:
def transform(df: pd.DataFrame, ...) -> dict:
    if df is None or df.empty:
        return {"available": False, "reason": "no_data"}
    # ... transformation logic ...
    return {"available": True, "period": {...}, ...data...}
```

### Pattern 5: Output Path Convention

**What:** Generated files go to `customers/<kebab-case-name>/analytics/YYYY-MM-DD-<type>.html`.
**When:** Every generation.
**Source:** Existing pattern from usage-report: `customers/g-research/usage/YYYY-MM-DD-usage-report.html`.

```
# New deep-analytics pages use analytics/ subdirectory:
customers/g-research/analytics/2026-03-24-user-journey.html
customers/g-research/analytics/2026-03-24-engagement-decay.html
```

### Anti-Patterns to Avoid

- **Shared CSS/JS include files:** Breaks self-contained HTML. Each template duplicates design tokens (~80 lines CSS + ~30 lines JS). The canonical source is design-system.md.
- **SQL in transform modules:** All SQL lives in `queries.py`. Transforms receive DataFrames, produce JSON.
- **Templating engine (Jinja, Mako):** The constant-replacement pattern is simpler, and templates are valid HTML with sample data for development.
- **Monolithic transform module:** One transform per page. Common utilities in `common/data_utils.py`.
- **KPI cards:** Forbidden by design-system.md. Use inline stat rows (value + label pairs).
- **Chart.js/D3/Plotly:** ECharts v5 is the only permitted charting library.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| BQ authentication | Custom OAuth flow | `gcloud auth application-default login` + ADC | Already working in bq_client.py; no stored secrets |
| BQ parameterized queries | f-string SQL injection | `bigquery.ScalarQueryParameter` | Already established in bq_client.py; prevents injection |
| Weekly aggregation | Custom date bucketing | `queries.aggregate_weekly()` | Already tested and used in usage.py |
| Customer name lookup | Custom YAML parser | `bq_client.get_sfdc_account_id()` | Case-insensitive, hyphen-tolerant, PLACEHOLDER detection |
| Dark/light mode detection | JS toggle button | CSS `prefers-color-scheme` media query | Automatic; out of scope per REQUIREMENTS.md |
| ECharts theme | Per-chart styling | `echarts.registerTheme('wandb', {...})` | Single registration, all charts inherit; 3 existing implementations to copy from |
| Date formatting | Custom format functions | Existing `formatDate()`, `formatWeekLabel()`, `formatMonthLabel()` from external template | Already tested in production |

**Key insight:** Phase 1 is mostly about assembling existing patterns, not inventing new ones. The BQ client, query factory, design system, and template injection pattern are all established. The new work is: (a) wiring them together in a new skill, (b) adding cost guardrails to the existing BQ client, (c) creating schema validation, and (d) building a foundation template that exercises all XCUT features.

## Common Pitfalls

### Pitfall 1: Missing maximum_bytes_billed Causes Uncontrolled Costs

**What goes wrong:** The current `bq_client.run_query()` does NOT set `maximum_bytes_billed`. Every new query added for deep analytics pages risks scanning the full 100+ column `ext_daily_user_event_usage` table at full cost.
**Why it happens:** The existing 7 queries are well-scoped with column pruning, so cost hasn't been a problem yet. But 9 new pages with 15-25 additional queries changes the risk profile.
**How to avoid:** Add `maximum_bytes_billed` parameter to `run_query()` with a default of 1GB (1_000_000_000 bytes). Log `job.total_bytes_processed` and `job.total_bytes_billed` after every query execution. Add a `--dry-run` flag.
**Warning signs:** Monthly BQ bill spikes; queries returning successfully but scanning gigabytes.

### Pitfall 2: sys.path Import Order Conflicts

**What goes wrong:** deep-analytics inserts `bigquery/scripts/` into `sys.path`, but if deep-analytics also has a module named `queries.py` or `bq_client.py`, Python imports the wrong one based on path order.
**Why it happens:** `sys.path.insert(0, ...)` puts the foreign path FIRST, so its modules shadow local ones.
**How to avoid:** deep-analytics must NOT have any module names that collide with bigquery/scripts/ modules. Use distinct names: `generate.py`, `schema_validator.py`, `transforms/`, `common/`. Never create a local `queries.py` or `bq_client.py` in deep-analytics.
**Warning signs:** ImportError or unexpected behavior in generate.py; wrong function signatures.

### Pitfall 3: Identity Resolution CTE Not Tested Against Server Customers

**What goes wrong:** The CTE works for cloud customers but server customers have NULL username/email in `ext_daily_user_event_usage`. The `dim_users` LEFT JOIN resolves `local_username` and `local_user_email`, but only if the `universal_user_id` match exists in `dim_users` for that account.
**Why it happens:** Testing against cloud customers shows full resolution; server deployment edge cases are invisible without explicit testing.
**How to avoid:** The identity resolution CTE must be tested against at least one server deployment customer. GResearch in `customers.yaml` has `deployment_type: server` -- use it as the validation target.
**Warning signs:** User tables showing "user-a3f7b2c1" instead of real names for server customers.

### Pitfall 4: Template Regex Replacement Breaks on Nested Objects

**What goes wrong:** The regex `const PAGE_DATA = \{[^}]*\};` fails when PAGE_DATA contains nested objects (which it always will). The `[^}]` character class stops at the first closing brace inside a nested object.
**Why it happens:** Naive regex that doesn't account for JSON nesting depth.
**How to avoid:** Use a more robust replacement strategy: find the line starting with `const PAGE_DATA = `, then count brace depth to find the matching closing brace, or use a known sentinel comment to delimit the replacement zone.
**Warning signs:** Truncated JSON in generated HTML; JavaScript syntax errors when opening the page.

**Recommended approach for data injection:**
```python
# Use a sentinel comment pair instead of regex:
# In template: /* PAGE_DATA_START */ const PAGE_DATA = {...}; /* PAGE_DATA_END */
# In generate.py:
START = '/* PAGE_DATA_START */'
END = '/* PAGE_DATA_END */'
before = template[:template.index(START) + len(START)]
after = template[template.index(END):]
template = before + f'\nconst PAGE_DATA = {data_json};\n' + after
```

### Pitfall 5: Schema Validator Queries INFORMATION_SCHEMA Across Projects

**What goes wrong:** The schema validator needs to check tables in `wandb-production.analytics` and `wandb-production.landing_development`, but `INFORMATION_SCHEMA` queries run in the job project (`wandb-sa-sandbox`). Cross-project INFORMATION_SCHEMA access requires `bigquery.tables.list` permission on the target project, which the sandbox account may not have.
**Why it happens:** `INFORMATION_SCHEMA.COLUMNS` only works within the same project unless explicit cross-project grants exist.
**How to avoid:** Instead of INFORMATION_SCHEMA, use a `SELECT * FROM table LIMIT 0` dry-run approach. This tests both access permissions AND returns the schema (column names and types) from the query job metadata without scanning any data.
**Warning signs:** 403 errors from INFORMATION_SCHEMA queries; validator always returning "table not found" for cross-project tables.

```python
# Robust schema validation via dry-run:
def validate_table(client, table_ref, required_columns):
    """Check table exists and has required columns without scanning data."""
    query = f"SELECT * FROM {table_ref} LIMIT 0"
    job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    try:
        job = client.query(query, job_config=job_config)
        available_cols = {f.name for f in job.schema}
        missing = set(required_columns) - available_cols
        return {"valid": len(missing) == 0, "missing": list(missing),
                "bytes_estimate": job.total_bytes_processed}
    except Exception as e:
        return {"valid": False, "error": str(e)}
```

## Code Examples

### Exact CSS Design Tokens (from usage-report-external.html lines 13-74)

These MUST be copied verbatim into every new template. This is the authoritative dark/light mode token set.

```css
/* Dark mode (default) */
:root {
  --bg-primary: #0c0f14;
  --bg-elevated: #141820;
  --bg-surface: #1a1f2b;
  --bg-hover: #222838;
  --border: #2a3040;
  --border-subtle: #1e2430;
  --text-primary: #e8eaed;
  --text-secondary: #8b92a0;
  --text-tertiary: #5c6370;
  --accent: #d4a853;
  --accent-dim: rgba(212, 168, 83, 0.12);
  --accent-border: rgba(212, 168, 83, 0.25);
  --green: #4ade80;
  --green-dim: rgba(74, 222, 128, 0.10);
  --green-border: rgba(74, 222, 128, 0.22);
  --blue: #60a5fa;
  --blue-dim: rgba(96, 165, 250, 0.10);
  --blue-border: rgba(96, 165, 250, 0.22);
  --amber: #fbbf24;
  --amber-dim: rgba(251, 191, 36, 0.10);
  --amber-border: rgba(251, 191, 36, 0.22);
  --red: #f87171;
  --red-dim: rgba(248, 113, 113, 0.10);
  --red-border: rgba(248, 113, 113, 0.22);
  --font-display: 'Instrument Serif', Georgia, serif;
  --font-body: 'Outfit', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
  --radius: 6px;
  --noise-opacity: 0.025;
  --mode: dark;
}

/* Light mode */
@media (prefers-color-scheme: light) {
  :root {
    --bg-primary: #f6f4f0;
    --bg-elevated: #ffffff;
    --bg-surface: #eeece8;
    --bg-hover: #e6e4e0;
    --border: #d4d2ce;
    --border-subtle: #e0ded9;
    --text-primary: #1a1a1a;
    --text-secondary: #5c5c5c;
    --text-tertiary: #8c8c8c;
    --accent: #b8922e;
    --accent-dim: rgba(184, 146, 46, 0.10);
    --accent-border: rgba(184, 146, 46, 0.25);
    --green: #1a7a4c;
    --green-dim: rgba(26, 122, 76, 0.08);
    --green-border: rgba(26, 122, 76, 0.20);
    --blue: #1565a0;
    --blue-dim: rgba(96, 165, 250, 0.08);
    --blue-border: rgba(21, 101, 160, 0.20);
    --amber: #9a6e08;
    --amber-dim: rgba(154, 110, 8, 0.08);
    --amber-border: rgba(154, 110, 8, 0.20);
    --red: #dc2626;
    --red-dim: rgba(220, 38, 38, 0.08);
    --red-border: rgba(220, 38, 38, 0.20);
    --noise-opacity: 0;
    --mode: light;
  }
}
```

### Exact ECharts Theme Registration (from usage-report-external.html lines 733-801)

This is the most complete of the 3 existing implementations -- supports dark/light mode detection. Use this version as the canonical reference for all deep-analytics templates.

```javascript
function isDarkMode() {
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
}

function getThemeColors() {
  const dark = isDarkMode();
  return {
    bg: 'transparent',
    textPrimary: dark ? '#e8eaed' : '#1a1a1a',
    textSecondary: dark ? '#8b92a0' : '#5c5c5c',
    textTertiary: dark ? '#5c6370' : '#8c8c8c',
    accent: dark ? '#d4a853' : '#b8922e',
    blue: dark ? '#60a5fa' : '#1565a0',
    green: dark ? '#4ade80' : '#1a7a4c',
    amber: dark ? '#fbbf24' : '#9a6e08',
    red: dark ? '#f87171' : '#dc2626',
    borderSubtle: dark ? '#1e2430' : '#e0ded9',
    bgElevated: dark ? '#141820' : '#ffffff',
    bgSurface: dark ? '#1a1f2b' : '#eeece8'
  };
}

function registerWandbTheme() {
  const c = getThemeColors();
  echarts.registerTheme('wandb', {
    backgroundColor: c.bg,
    textStyle: {
      fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
      fontSize: 11,
      color: c.textSecondary
    },
    title: {
      textStyle: { color: c.textPrimary, fontFamily: "'Outfit', system-ui, sans-serif" }
    },
    legend: {
      textStyle: { color: c.textSecondary, fontFamily: "'Outfit', system-ui, sans-serif", fontSize: 12 }
    },
    tooltip: {
      backgroundColor: c.bgElevated,
      borderColor: c.borderSubtle,
      borderWidth: 1,
      textStyle: {
        color: c.textPrimary,
        fontFamily: "'Outfit', system-ui, sans-serif",
        fontSize: 13
      },
      extraCssText: 'border-radius: 6px; box-shadow: 0 4px 16px rgba(0,0,0,0.2);'
    },
    categoryAxis: {
      axisLine: { lineStyle: { color: c.borderSubtle } },
      axisTick: { show: false },
      axisLabel: {
        color: c.textTertiary,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11
      },
      splitLine: { lineStyle: { color: c.borderSubtle, type: 'dashed' } }
    },
    valueAxis: {
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: c.textTertiary,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11
      },
      splitLine: { lineStyle: { color: c.borderSubtle, type: 'dashed' } }
    },
    color: [c.blue, c.accent, c.green, c.amber, c.red],
    animationDuration: 600,
    animationEasing: 'cubicOut'
  });
}
```

### Exact CDN and Font Imports (from usage-report-external.html lines 7-10)

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif&family=JetBrains+Mono:wght@400;500;600&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
```

### Identity Resolution CTE Pattern (from existing queries.py power_users_query lines 249-261)

Extract into a reusable function:

```python
def identity_resolution_cte(table_alias: str = "src") -> str:
    """
    Returns a SQL CTE that resolves user identity for server deployments.

    Server deployments do not populate username/email in ext_daily_user_event_usage.
    This CTE LEFT JOINs dim_users to resolve local_username and local_user_email.

    Args:
        table_alias: Alias for the source table that has universal_user_id

    Returns:
        SQL string for a CTE named 'resolved_users' with columns:
        universal_user_id, resolved_username, resolved_email
    """
    dim_users = _ref("dim_users")
    return f"""
    resolved_users AS (
        SELECT
            {table_alias}.universal_user_id,
            COALESCE({table_alias}.username, du.local_username) AS resolved_username,
            COALESCE({table_alias}.email, du.local_user_email) AS resolved_email
        FROM {table_alias}
        LEFT JOIN {dim_users} du
            ON {table_alias}.universal_user_id = du.universal_user_id
            AND du.account_id = @account_id
    )
    """
```

### Cost-Guarded run_query Enhancement (for bq_client.py)

```python
def run_query(
    client: bigquery.Client,
    query: str,
    account_id: Optional[str] = None,
    maximum_bytes_billed: int = 1_000_000_000,  # 1 GB default
    dry_run: bool = False,
) -> pd.DataFrame:
    """Execute a BigQuery query with cost guardrails."""
    job_config = bigquery.QueryJobConfig(
        maximum_bytes_billed=maximum_bytes_billed,
        dry_run=dry_run,
        use_query_cache=not dry_run,
    )
    if account_id is not None:
        job_config.query_parameters = [
            bigquery.ScalarQueryParameter("account_id", "STRING", account_id)
        ]

    job = client.query(query, job_config=job_config)

    if dry_run:
        return pd.DataFrame()  # dry-run returns no data

    df = job.to_dataframe()

    # Log bytes processed
    bytes_processed = job.total_bytes_processed or 0
    bytes_billed = job.total_bytes_billed or 0
    if bytes_processed > 500_000_000:  # warn above 500MB
        import sys
        print(f"[BQ COST WARNING] Query processed {bytes_processed / 1e9:.2f} GB, "
              f"billed {bytes_billed / 1e9:.2f} GB", file=sys.stderr)

    return df
```

### Schema Validator (new utility)

```python
def validate_table_schema(
    client: bigquery.Client,
    table_ref: str,
    required_columns: list[str],
) -> dict:
    """
    Validate table exists and has required columns using dry-run.

    Uses LIMIT 0 dry-run instead of INFORMATION_SCHEMA to avoid
    cross-project permission issues.

    Returns:
        {"valid": True/False, "missing": [...], "bytes_estimate": int}
    """
    query = f"SELECT * FROM {table_ref} LIMIT 0"
    job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    try:
        job = client.query(query, job_config=job_config)
        available_cols = {f.name for f in job.schema}
        missing = sorted(set(required_columns) - available_cols)
        return {
            "valid": len(missing) == 0,
            "missing": missing,
            "available_columns": sorted(available_cols),
            "bytes_estimate": job.total_bytes_processed,
        }
    except Exception as e:
        return {"valid": False, "error": str(e), "missing": required_columns}
```

### Empty State HTML Pattern (from usage-report-external.html)

```css
.empty-state {
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 400;
  color: var(--text-tertiary);
  padding: 32px;
  text-align: center;
  border: 1px dashed var(--border);
  border-radius: var(--radius);
  margin-top: 16px;
}
```

```javascript
function renderEmptyState(section, reason) {
  const messages = {
    config_error: 'Customer not configured for BigQuery access. Add sfdc_account_id to templates/customers.yaml.',
    no_data: `No data available for this section. The customer may not have activity in this dimension.`,
    api_error: 'BigQuery data unavailable -- check ADC credentials with /bigquery-setup.',
    schema_error: 'Required data tables are not accessible. Contact the analytics team.',
  };
  const msg = messages[reason] || 'No data available.';
  return `<div class="empty-state">${msg}</div>`;
}
```

### Copy-to-Clipboard Pattern (NEW -- XCUT-10)

```javascript
function copyNarrative() {
  const text = AI_NARRATIVE.executive_summary +
    '\n\nKey Highlights:\n' +
    AI_NARRATIVE.highlights.map(h => '- ' + h).join('\n') +
    '\n\nRecommendations:\n' +
    AI_NARRATIVE.recommendations.map(r => '- ' + r).join('\n');

  navigator.clipboard.writeText(text).then(() => {
    const btn = document.getElementById('copyNarrativeBtn');
    const original = btn.textContent;
    btn.textContent = 'Copied!';
    btn.style.color = 'var(--green)';
    setTimeout(() => {
      btn.textContent = original;
      btn.style.color = '';
    }, 2000);
  });
}
```

```html
<button id="copyNarrativeBtn" onclick="copyNarrative()"
  style="font-family:var(--font-mono);font-size:11px;color:var(--text-tertiary);
         background:none;border:1px solid var(--border);border-radius:var(--radius);
         padding:4px 10px;cursor:pointer;letter-spacing:0.5px;">
  COPY TO CLIPBOARD
</button>
```

### SaveAsImage Toolbox Pattern (NEW -- XCUT-09)

```javascript
// Add to every chart initialization:
chart.setOption({
  toolbox: {
    feature: {
      saveAsImage: {
        title: 'Save as PNG',
        pixelRatio: 2,
        backgroundColor: getThemeColors().bgElevated
      }
    },
    right: 16,
    top: 8,
    iconStyle: {
      borderColor: getThemeColors().textTertiary
    }
  },
  // ... rest of chart options
});
```

### Linked Navigation Pattern (NEW -- XCUT-11)

```html
<nav class="page-nav" style="display:flex;gap:16px;flex-wrap:wrap;
     padding:12px 0;border-bottom:1px solid var(--border);margin-bottom:24px;">
  <span style="font-family:var(--font-mono);font-size:11px;color:var(--text-tertiary);
        text-transform:uppercase;letter-spacing:1.5px;align-self:center;">ANALYTICS</span>
  <!-- Active page gets accent color, others get text-tertiary -->
  <a href="#" class="nav-link active" style="font-family:var(--font-body);font-size:13px;
     color:var(--accent);text-decoration:none;">User Journey</a>
  <a href="./2026-03-24-cohort-analysis.html" class="nav-link"
     style="font-family:var(--font-body);font-size:13px;color:var(--text-tertiary);
     text-decoration:none;">Cohort Analysis</a>
  <!-- ...more pages... -->
</nav>
```

Navigation links use relative paths and the same date prefix, since all pages for a customer are generated on the same date into the same directory.

### pyproject.toml for deep-analytics

```toml
[project]
name = "deep-analytics-skill"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "google-cloud-bigquery>=3.39.0",
    "google-cloud-bigquery-storage>=2.36.0",
    "pandas>=2.0.0",
    "db-dtypes>=1.5.0",
    "pyarrow>=17.0.0",
    "pyyaml>=6.0",
]

[dependency-groups]
dev = ["pytest>=9.0"]
```

This mirrors `bigquery-skill/pyproject.toml` exactly. The deep-analytics skill needs the same BQ and pandas dependencies because it imports from bigquery/scripts/ and runs query results through its own transforms.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hex dashboards (static, internal) | Self-contained HTML with ECharts (portable, polished) | 2026 Q1 | SEs can share reports directly; no Hex dependency |
| Subprocess JSON boundary between skills | sys.path direct import for DataFrame access | Phase 1 decision | Enables raw DataFrame transforms without serialization overhead |
| No BQ cost guardrails | maximum_bytes_billed + bytes logging | Phase 1 addition | Prevents runaway query costs from 15-25 new queries |
| Per-query identity resolution | Shared CTE utility function | Phase 1 addition | Consistent server deployment handling across all 9 pages |

## Open Questions

1. **Template data injection: regex vs sentinel comments**
   - What we know: Regex replacement is fragile with nested JSON objects
   - What's unclear: Whether the existing usage-report SKILL.md's agent-based replacement relies on regex or Claude's text understanding
   - Recommendation: Use sentinel comment pair (`/* PAGE_DATA_START */` / `/* PAGE_DATA_END */`) for machine-readable boundaries. More robust than regex, simpler than brace-counting.

2. **Should bq_client.py changes be backwards-compatible?**
   - What we know: `run_query()` is called by `usage.py` with `(client, query, account_id)` -- no keyword args for `maximum_bytes_billed`
   - What's unclear: Whether adding new parameters with defaults could break existing callers
   - Recommendation: Add new parameters with defaults (`maximum_bytes_billed=None` meaning unlimited, preserving current behavior). Only deep-analytics callers explicitly set the limit. Existing callers are unaffected.

3. **Should deep-analytics share bigquery's uv project or have its own?**
   - What we know: Both need identical dependencies. Separate projects mean separate .venv directories (~200MB each).
   - What's unclear: Whether uv supports workspace-style dependency sharing
   - Recommendation: Separate pyproject.toml (own uv project). The dependency duplication is ~200MB disk, which is acceptable. Separate projects maintain the skill-per-capability boundary and allow deep-analytics to add dependencies later (e.g., scipy for correlation analysis) without affecting the bigquery skill.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv | Dependency isolation | Yes | 0.10.9 | -- |
| Python 3.13 | pyproject.toml requires-python | Yes | 3.13.12 (in bigquery venv) | -- |
| gcloud CLI | ADC authentication | Yes | 561.0.0 | -- |
| gcloud ADC | BigQuery access | Assumed yes (existing skills work) | -- | Run `gcloud auth application-default login` |
| Internet | ECharts CDN, Google Fonts | Yes | -- | Offline fallback not supported (by design) |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

## Project Constraints (from CLAUDE.md)

### Coding Conventions
- Python skills use `uv run --project .claude/skills/<skill>` for dependency isolation
- uv is installed at `~/.local/bin/uv`
- Credentials stored in `~/.tsm-ai/.env` (BQ uses ADC, not env vars)
- Channel IDs belong in user-scoped rules, not committed files
- Customer registry is `templates/customers.yaml`

### Skill Patterns
- Each skill has SKILL.md with name, description, argument-hint, allowed-tools
- Self-contained HTML is the output format for reports (single file, CDN only, no server)
- Design system reference at `customer-snapshot/references/design-system.md`
- Anti-patterns: KPI cards, Chart.js, gradient text, glassmorphism, sidebar navigation, Inter/Roboto fonts

### Testing
- bigquery skill has pytest test suite in `tests/` with conftest.py fixtures
- Tests use sys.path insertion for importing from scripts/
- Test patterns: query factory verification (parameterization, no legacy residue), builder output schema validation, edge cases with empty DataFrames

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection:
  - `bigquery/scripts/bq_client.py` (125 lines) -- ADC auth, run_query, get_sfdc_account_id
  - `bigquery/scripts/queries.py` (449 lines) -- 7 query functions, aggregate_weekly, power_users_query identity resolution
  - `bigquery/scripts/usage.py` (583 lines) -- 7-query pipeline, build_usage_json, graceful degradation
  - `bigquery/pyproject.toml` -- dependency list (6 packages)
  - `bigquery/tests/` (4 test files) -- conftest fixtures, query tests, usage tests
  - `usage-report/templates/usage-report-external.html` (1360 lines) -- CSS tokens, ECharts theme, empty state
  - `usage-report/templates/usage-report-internal.html` (1653 lines) -- simpler ECharts theme variant
  - `customer-snapshot/templates/intelligence-dashboard.html` (3721 lines) -- third ECharts theme variant
  - `customer-snapshot/references/design-system.md` -- authoritative design rules
  - `usage-report/SKILL.md` -- full pipeline documentation, AI narrative guidelines
  - `bigquery/SKILL.md` -- consumer pattern, data sources table
  - `templates/customers.yaml` -- customer routing table schema, deployment_type field

### Secondary (MEDIUM confidence)
- `~/Documents/gitstuff/ai-docs/apache-echarts.md` -- ECharts v5/v6 comparison, chart types, theme patterns
- `~/Documents/gitstuff/ai-docs/google-cloud-bigquery.md` -- BQ SDK patterns, ADC auth, parameterized queries
- `~/Documents/gitstuff/ai-docs/wandb-bigquery-schema-discovery.md` -- BQ table inventory, column documentation
- `~/Documents/gitstuff/ai-docs/wandb-usage-visualization.md` -- product area mapping, visualization vision

### Tertiary (LOW confidence)
- None -- all findings verified against codebase or official docs.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- zero new dependencies; all verified in existing pyproject.toml and production templates
- Architecture: HIGH -- every pattern extracted from direct codebase inspection of 6+ production files
- Pitfalls: HIGH -- cost guardrails, identity resolution, template injection all verified against existing code gaps
- Design system: HIGH -- exact CSS tokens and ECharts theme config extracted verbatim from production HTML

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable -- no external dependency changes expected)
