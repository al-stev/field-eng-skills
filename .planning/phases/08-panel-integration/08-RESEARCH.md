# Phase 8: Panel Integration - Research

**Researched:** 2026-04-03
**Domain:** Dashboard V2 panel architecture, ECharts integration, cross-skill Python imports
**Confidence:** HIGH

## Summary

Phase 8 integrates 9 deep-analytics page types (user journey, cohort analysis, engagement decay, feature velocity, team detection, risk scoring, SDK versions, usage correlation, performance) as dashboard panels following the existing V2 panel contract. The codebase is well-structured for this: PanelRegistry provides a clean registration contract, compose.py handles data-gated panel inclusion via panels.yaml, and 9 Transform classes already produce complete data dicts ready for consumption.

The primary technical challenges are: (1) the data pipeline wiring -- assemble.py must import transforms from a different skill (deep-analytics) with different Python dependencies, requiring careful sys.path and dependency management; (2) converting standalone page chart code (~3100 lines in base-template.html) into 9 panel JS files each under 800 lines while maintaining full visualization fidelity; and (3) the D-09 "always show" requirement needs stub data in INTELLIGENCE_DATA even when BQ data is unavailable, requiring assemble.py to always populate `analytics.*` keys.

**Primary recommendation:** Work in three waves: (1) data pipeline (assemble.py + panels.yaml), (2) panel JS files (9 panels following support.js as the reference), (3) integration (overview.js updates, shell.html icons, empty states). Use the deep-analytics project venv for running assemble.py since transforms require pandas.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Extend assemble.py to call all 9 deep-analytics transforms inline, merging results into INTELLIGENCE_DATA. Single skill boundary, single BQ client session. No new orchestration step or separate invocations.
- **D-02:** Always fetch analytics data if the customer has sfdc_account_id in customers.yaml. No opt-in flag needed. Panels with no data get graceful empty states.
- **D-03:** assemble.py imports transforms from deep-analytics/scripts/transforms/ directly (cross-skill import). Keeps transforms in one place with no duplication.
- **D-04:** Analytics data nested under `analytics.*` keys in INTELLIGENCE_DATA (e.g., `data.analytics.cohort`, `data.analytics.risk`, `data.analytics.journey`). Panel data_key in panels.yaml uses dot-path like `analytics.cohort`.
- **D-05:** Port ALL charts and visualizations from each standalone analytics page into its panel JS file. The dashboard IS the analytics tool -- no separate standalone pages needed for analytics that are now panels.
- **D-06:** Retire standalone deep-analytics HTML page generation for the 9 page types that become panels. The deep-analytics skill's generate.py and transforms remain available but standalone page output is superseded by the dashboard.
- **D-07:** Two new sidebar groups for analytics panels: **User Intelligence** (User Journey, Cohort Analysis, Engagement Decay, Team Detection) and **Product Intelligence** (Feature Velocity, SDK Versions, Usage Correlation, Risk Scoring, Performance).
- **D-08:** Existing 3 groups (Intelligence, Usage & Analytics, Activity & Comms) remain unchanged. Seats & Adoption stays in its current group.
- **D-09:** Panels always appear in the sidebar regardless of data availability. When data is unavailable, the panel body shows a styled empty state explaining WHY. Consistent navigation -- SE always sees all 15 panels.
- **D-10:** For partially available data, show what's available and render "Data not available" placeholders for missing sections.

### Claude's Discretion
- Panel order within each new sidebar group
- Specific icon choices for each new panel in panels.yaml
- Whether to extract common CSS patterns shared across analytics panels into chart-helpers.js or keep them panel-local
- The 800-line limit per panel -- Claude decides if any pages need chart trimming to meet it
- Badge key choices for sidebar notification indicators on analytics panels

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PANEL-01 | SE can view cohort retention heatmap as a dashboard panel showing new vs established user retention by cohort month | CohortAnalysisTransform already produces cohort_matrix, retention_curve, lifecycle data. Panel uses ECharts heatmap + visualMap continuous gradient. |
| PANEL-02 | SE can view risk scoring as a dashboard panel showing composite churn risk gauge, factor breakdown, and trend line | RiskScoringTransform produces risk score, factors, risk_trend, risk_radar. Panel uses gauge + radar/bar + line. Handles missing renewal_predictions gracefully. |
| PANEL-03 | SE can view team detection as a dashboard panel showing team breakdown, per-team activity, and adoption patterns | TeamDetectionTransform produces teams list, team_activity, team_product_heatmap. Three-tier status (available/names_unavailable/unavailable) maps to empty state variants. |
| PANEL-04 | SE can view user journey as a dashboard panel showing adoption funnel/Sankey from first activity through product stages | UserJourneyTransform produces Sankey nodes/links, funnel counts. Panel uses ECharts sankey + funnel. |
| PANEL-05 | SE can view engagement decay as a dashboard panel showing cold-detection table ranking users by activity decline | EngagementDecayTransform produces per-user decay status, sparkline data, ranked table. Panel renders table + inline sparklines. |
| PANEL-06 | SE can view feature velocity as a dashboard panel showing sparkline grid of monthly events per product area with momentum indicators | FeatureVelocityTransform produces area_series with monthly events and momentum. Panel uses small ECharts instances for sparklines. |
| PANEL-07 | SE can view SDK version distribution as a dashboard panel showing version freshness, distribution donut, and upgrade recommendations | SdkVersionsTransform produces version distribution, freshness classification, timeline. Panel uses pie/donut + stacked bar + table. |
| PANEL-08 | SE can view usage correlation as a dashboard panel showing product combination heatmap with SE-internal privacy controls | UsageCorrelationTransform produces correlation matrix, peer comparison, expansion signals. Panel uses heatmap + scatter. Privacy badge required. |
| PANEL-09 | SE can view performance metrics as a dashboard panel showing performance index and latency breakdown (graceful empty state if data unavailable) | PerformanceTransform has go/no-go gate and descoped_result() for unavailable data. Panel renders gauge + bar + line or full empty state. |
| PANEL-10 | All 9 new panels follow the existing panel contract (PanelRegistry.register, getHeadlineStats, getAttentionItems) and render in the v2 dashboard shell | PanelRegistry contract is clear: register() with id, render(), getHeadlineStats(), getAttentionItems(). All panels use ChartHelpers.createChart(), PANEL_CSS, isDark(). |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Apache ECharts | 5.6.0 (v5 locked) | All chart rendering | Already in use, custom wandb theme registered, CDN-loaded as local file. Project explicitly decided NOT to upgrade to v6. |
| PanelRegistry | custom (panel-registry.js) | Panel registration contract | Existing dashboard architecture. register(), renderPanel(), injectCSS() with auto-scoping. |
| ChartHelpers | custom (chart-helpers.js) | Theme-aware chart creation | All panels must use ChartHelpers.createChart() -- never raw echarts.init(). Handles wandb theme registration and resize tracking. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pandas | >=2.0.0 | Transform data processing | Required by all 9 transforms. Already in deep-analytics pyproject.toml. |
| google-cloud-bigquery | >=3.39.0 | BQ query execution | Required when assemble.py runs BQ queries via transform handlers. Already in deep-analytics pyproject.toml. |
| pyyaml | >=6.0 | Customer registry reading | Already in both skill pyproject.toml files. |

### No Additions Needed
All required dependencies already exist in the deep-analytics skill's pyproject.toml. No new packages to install.

## Architecture Patterns

### Recommended File Structure
```
.claude/skills/customer-snapshot/templates/
  panels/
    overview.js          # Existing - will auto-aggregate new panel stats
    issues.js            # Existing
    support.js           # Existing
    usage.js             # Existing
    actions.js           # Existing
    slack.js             # Existing
    journey.js           # NEW - User Journey (PANEL-04)
    cohort.js            # NEW - Cohort Analysis (PANEL-01)
    decay.js             # NEW - Engagement Decay (PANEL-05)
    team.js              # NEW - Team Detection (PANEL-03)
    velocity.js          # NEW - Feature Velocity (PANEL-06)
    sdk-versions.js      # NEW - SDK Versions (PANEL-07)
    correlation.js       # NEW - Usage Correlation (PANEL-08)
    risk.js              # NEW - Risk Scoring (PANEL-02)
    performance.js       # NEW - Performance (PANEL-09)
  panels.yaml            # MODIFY - add 9 entries + 2 new groups
  shell.html             # MODIFY - add 9 icon entries to ICON_MAP
  compose.py             # NO CHANGES NEEDED (data_key resolution already handles nested paths)
  assemble.py            # MODIFY - add analytics data fetching pipeline
  lib/
    panel-registry.js    # NO CHANGES NEEDED
    chart-helpers.js     # NO CHANGES NEEDED (or minimal -- discretion area)
```

### Pattern 1: Panel IIFE Registration
**What:** Every panel is a self-contained IIFE that registers with PanelRegistry.
**When to use:** All 9 new panels must follow this pattern exactly.
**Example (from support.js):**
```javascript
(function() {
  'use strict';

  function isDark() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  var PANEL_CSS = '...';

  PanelRegistry.register({
    id: 'cohort',
    group: 'user-intel',
    label: 'Cohort Analysis',
    icon: '<svg viewBox="0 0 24 24" ...></svg>',
    dataKey: 'analytics.cohort',
    badgeKey: null,

    render: function(container, data, config) {
      if (!document.querySelector('style[data-panel="cohort"]')) {
        PanelRegistry.injectCSS('cohort', PANEL_CSS);
      }
      // Check data.available for empty state
      if (!data || !data.available) {
        container.innerHTML = '...empty state...';
        return { charts: [] };
      }
      var charts = [];
      // Build HTML, create ECharts instances
      return { charts: charts };
    },

    getHeadlineStats: function(data) {
      if (!data || !data.available) return [];
      return [
        { label: 'Metric', value: '42%', color: 'var(--green)' }
      ];
    },

    getAttentionItems: function(data) {
      if (!data || !data.available) return [];
      return [];
    }
  });
})();
```

### Pattern 2: Data Pipeline -- assemble.py Analytics Integration
**What:** assemble.py imports transforms from deep-analytics and calls them with BQ data.
**When to use:** The assemble.py modification for D-01 and D-03.
**Critical constraint:** assemble.py must run under deep-analytics venv (not customer-snapshot) because transforms require pandas. The SKILL.md invocation pattern changes from `uv run --project .claude/skills/customer-snapshot` to `uv run --project .claude/skills/deep-analytics` for the assemble step, OR customer-snapshot's pyproject.toml gains the BQ dependencies.

**Recommended approach:** The customer-snapshot SKILL.md pipeline already invokes `uv run --project .claude/skills/bigquery` for BQ data. assemble.py should be runnable under the deep-analytics project (which has all needed deps). The SKILL.md step 7 invocation changes to:
```bash
uv run --project .claude/skills/deep-analytics python \
    .claude/skills/customer-snapshot/templates/assemble.py \
    --customer "<CustomerName>" \
    --jira /tmp/snapshot-jira.json \
    --bq /tmp/snapshot-bq.json \
    --asana /tmp/snapshot-asana.json \
    --sentiment /tmp/snapshot-sentiment.json \
    --output /tmp/customer-snapshot-data.json
```

**Alternative:** Add BQ dependencies to customer-snapshot's pyproject.toml. This is simpler but duplicates dependency declarations. Given D-03 explicitly says "cross-skill import", changing the venv is the expected approach.

### Pattern 3: D-09 Always-Show via Stub Data
**What:** assemble.py always populates `analytics.*` keys even when BQ is unavailable.
**When to use:** Satisfying D-09 (panels always appear in sidebar).
**How it works:**
1. assemble.py writes stub entries like `analytics.cohort: { available: false, reason: "no_bq_data" }` when sfdc_account_id is missing or BQ fails
2. compose.py's `resolve_key(data, 'analytics.cohort')` returns the stub dict (truthy) -- panel JS file gets included
3. shell.html's `resolveKey(INTELLIGENCE_DATA, 'analytics.cohort')` returns the stub dict (truthy) -- sidebar item shows
4. Panel's render() checks `data.available` and renders empty state
5. Panel's getHeadlineStats() and getAttentionItems() return `[]` when `data.available` is false -- overview excludes them

This exactly matches the existing pattern for usage panel: `usage: { available: false, reason: "not_provided" }`.

### Pattern 4: Data Key Mapping (D-04)
**What:** Maps transform output to INTELLIGENCE_DATA analytics namespace.
**Panel data_key -> transform output:**

| Panel ID | data_key | Transform Class | Output key in analytics.* |
|----------|----------|-----------------|---------------------------|
| journey | analytics.journey | UserJourneyTransform | analytics.journey |
| cohort | analytics.cohort | CohortAnalysisTransform | analytics.cohort |
| decay | analytics.decay | EngagementDecayTransform | analytics.decay |
| team | analytics.team | TeamDetectionTransform | analytics.team |
| velocity | analytics.velocity | FeatureVelocityTransform | analytics.velocity |
| sdk-versions | analytics.sdk_versions | SdkVersionsTransform | analytics.sdk_versions |
| correlation | analytics.correlation | UsageCorrelationTransform | analytics.correlation |
| risk | analytics.risk | RiskScoringTransform | analytics.risk |
| performance | analytics.performance | PerformanceTransform | analytics.performance |

### Anti-Patterns to Avoid
- **Direct echarts.init():** Always use ChartHelpers.createChart(). Skipping this breaks theme registration and resize tracking.
- **Hardcoded colors:** Use CSS custom properties (--green, --red, etc.) and the wandb theme palette. Never hardcode hex colors in JS.
- **ES module syntax:** All panel JS uses IIFE pattern. `import/export` breaks on file:// protocol.
- **External dependencies:** No new CDN links, npm packages, or build steps. Everything is self-contained.
- **Duplicating transforms:** D-03 says import from deep-analytics, not copy. Do not duplicate transform code into customer-snapshot.
- **Large PANEL_CSS strings:** Keep CSS minimal and reuse standard classes (.stats-strip, .stat-card, .panel-card, .section-label, .two-col). Don't reinvent layout classes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Chart theming | Custom ECharts theme per panel | ChartHelpers.createChart() with wandb theme | Theme already registered with brand colors, fonts, axis styles |
| CSS scoping | Manual ID prefixing | PanelRegistry.injectCSS(id, css) | Auto-prepends #panel-{id} to all selectors |
| Data resolution | Manual nested dict traversal | compose.py resolve_key() / shell.html resolveKey() | Already handles dot-path, .length suffix, null safety |
| Panel aggregation | Custom overview stats collection | overview.js auto-iterates PanelRegistry.getAll() | Existing overview automatically picks up new panels via getHeadlineStats() and getAttentionItems() |
| Resize handling | Per-panel resize listeners | ChartHelpers._instances[] + resizeAll() | All charts tracked automatically by createChart() |
| Dark/light detection | Complex theme detection | isDark() helper (duplicated per panel) | Simple, established pattern -- one-liner |
| Data transforms | Re-querying BQ in panel JS | Transform classes in deep-analytics/scripts/transforms/ | All data processing happens in Python, JS only renders |
| Empty states | Custom empty state HTML per panel | shell.html .placeholder-panel pattern | Consistent styling with existing panels |

**Key insight:** The existing dashboard architecture handles almost everything automatically. The new panels just need to follow the established patterns.

## Common Pitfalls

### Pitfall 1: Python Dependency Mismatch
**What goes wrong:** assemble.py imports transforms that need pandas, but customer-snapshot venv only has pyyaml.
**Why it happens:** Two skills with different pyproject.toml files. Transforms live in deep-analytics (which has pandas), assemble.py lives in customer-snapshot (which doesn't).
**How to avoid:** Run assemble.py under deep-analytics venv: `uv run --project .claude/skills/deep-analytics python .claude/skills/customer-snapshot/templates/assemble.py ...`. Add sys.path entries for both deep-analytics/scripts and bigquery/scripts so imports resolve.
**Warning signs:** `ModuleNotFoundError: No module named 'pandas'` or `No module named 'transforms'`.

### Pitfall 2: compose.py Skipping Analytics Panels
**What goes wrong:** New panels don't appear because resolve_key returns None for analytics.* paths.
**Why it happens:** assemble.py didn't populate analytics.* stubs when BQ data was unavailable.
**How to avoid:** assemble.py must ALWAYS write analytics.* keys, even as `{ available: false, reason: "..." }`. Test with a customer that has no sfdc_account_id.
**Warning signs:** Panel JS files not copied to output folder. Dashboard sidebar shows fewer panels than expected.

### Pitfall 3: shell.html JS-Side Data Gating Hides Panels
**What goes wrong:** Even with compose.py including panel files, shell.html's buildSidebar() skips panels because their dataKey resolves to falsy.
**Why it happens:** shell.html line 730 checks `if (panel.dataKey && !resolveKey(INTELLIGENCE_DATA, panel.dataKey))` -- skips panels with no data.
**How to avoid:** The stub data approach (Pattern 3 above) ensures analytics.* keys always resolve to truthy objects. The panel's render() function handles the empty state.
**Warning signs:** Panel JS file exists in output folder but no sidebar entry appears.

### Pitfall 4: 800-Line Budget Exceeded
**What goes wrong:** Panel JS files exceed 800 lines, violating success criteria 5.
**Why it happens:** Porting ALL charts from standalone pages (D-05) into a panel IIFE with PANEL_CSS adds up fast. base-template.html has ~3100 lines total across 9 page types.
**How to avoid:** Budget is ~345 lines per page from base-template.html (3100/9), plus ~100 lines for PANEL_CSS, ~50 for registration boilerplate, ~100 for getHeadlineStats/getAttentionItems = ~595 baseline. Stay disciplined: use compact CSS, shared class names, minimal comments. If a panel exceeds 800 lines, trim verbose ECharts configs (use spread patterns, default tooltips).
**Warning signs:** Any panel source file crossing 700 lines during development.

### Pitfall 5: Overview Panel Stat/Attention Overload
**What goes wrong:** Overview panel becomes cluttered with 15 panels contributing stats and attention items.
**Why it happens:** Each panel can return up to 4 headline stats and unlimited attention items. 15 panels x 3 stats = 45 stat cards.
**How to avoid:** Analytics panels should return 2-3 headline stats each (not the maximum 4). Attention items should be limited to genuinely actionable signals (high/medium severity only). Low-severity informational items should be in-panel only.
**Warning signs:** Overview panel takes too long to scroll, stat cards wrap to 4+ rows.

### Pitfall 6: ECharts Instances Accumulate, Causing Memory/Performance Issues
**What goes wrong:** Dashboard with 15 panels becomes slow. Each panel creates 3-5 ECharts instances. 15 panels x 4 charts = 60 instances.
**Why it happens:** Panels render on-demand (good), but instances aren't disposed when navigating away.
**How to avoid:** The shell already uses on-demand rendering (only renders on first navigation). Charts are not disposed on navigate-away -- this is the existing pattern and prevents re-render cost. The 5-second load target applies to initial page load + first panel render, not all panels at once.
**Warning signs:** Browser DevTools showing >50 ECharts instances in memory.

### Pitfall 7: Cross-Skill sys.path Import Order
**What goes wrong:** Wrong module gets imported when multiple skills have same-named modules.
**Why it happens:** sys.path has entries from multiple skill directories. If deep-analytics/scripts/ and bigquery/scripts/ both have a `queries.py`, the first one found wins.
**How to avoid:** Use explicit relative imports within transforms (e.g., `from transforms.base import BaseTransform`). For BQ queries, the generate.py pattern adds bigquery/scripts FIRST, then deep-analytics/scripts. Follow this exact order in assemble.py.
**Warning signs:** ImportError for module that definitely exists, or wrong function signatures.

## Code Examples

### panels.yaml Updated Manifest
```yaml
groups:
  - id: intelligence
    label: Intelligence
  - id: usage
    label: Usage & Analytics
  - id: user-intel
    label: User Intelligence
  - id: product-intel
    label: Product Intelligence
  - id: activity
    label: Activity & Comms

panels:
  # Existing panels (unchanged)
  - id: overview
    group: intelligence
    label: Overview
    icon: grid
    always_show: true
    order: 1
  - id: issues
    group: intelligence
    label: Issues
    icon: alert-circle
    data_key: issues
    badge_key: issues.length
    order: 2
  - id: support
    group: intelligence
    label: Support
    icon: headset
    data_key: usage.support_tickets
    badge_key: usage.support_tickets.total
    order: 3
  - id: usage
    group: usage
    label: Seats & Adoption
    icon: trending-up
    data_key: usage
    order: 4
  # New: User Intelligence group
  - id: journey
    group: user-intel
    label: User Journey
    icon: git-branch
    data_key: analytics.journey
    order: 7
  - id: cohort
    group: user-intel
    label: Cohort Analysis
    icon: calendar
    data_key: analytics.cohort
    order: 8
  - id: decay
    group: user-intel
    label: Engagement Decay
    icon: trending-down
    data_key: analytics.decay
    badge_key: analytics.decay.cold_users_count
    order: 9
  - id: team
    group: user-intel
    label: Team Detection
    icon: users
    data_key: analytics.team
    order: 10
  # New: Product Intelligence group
  - id: velocity
    group: product-intel
    label: Feature Velocity
    icon: zap
    data_key: analytics.velocity
    order: 11
  - id: sdk-versions
    group: product-intel
    label: SDK Versions
    icon: package
    data_key: analytics.sdk_versions
    badge_key: analytics.sdk_versions.stale_count
    order: 12
  - id: correlation
    group: product-intel
    label: Usage Correlation
    icon: link-2
    data_key: analytics.correlation
    order: 13
  - id: risk
    group: product-intel
    label: Risk Scoring
    icon: shield
    data_key: analytics.risk
    order: 14
  - id: performance
    group: product-intel
    label: Performance
    icon: activity
    data_key: analytics.performance
    order: 15
  # Existing panels (unchanged)
  - id: actions
    group: activity
    label: SE Actions
    icon: check-square
    data_key: actions
    badge_key: actions.tasks.length
    order: 5
  - id: slack
    group: activity
    label: Slack
    icon: message-circle
    data_key: sentiment
    order: 6
```

### assemble.py Analytics Integration (D-01, D-03, D-04)
```python
import sys
from pathlib import Path

# Add deep-analytics scripts to sys.path for transform imports
SKILLS_DIR = Path(__file__).resolve().parent.parent  # .claude/skills/
sys.path.insert(0, str(SKILLS_DIR / "deep-analytics" / "scripts"))
sys.path.insert(0, str(SKILLS_DIR / "bigquery" / "scripts"))

def fetch_analytics_data(customer_name, bq_client, account_id):
    """Fetch all 9 analytics transforms, return dict keyed by analytics namespace.

    Always returns a dict with all 9 keys populated.
    Missing/failed transforms get { available: false, reason: "..." }.
    """
    analytics = {}

    # Import all transform classes
    from transforms.user_journey import UserJourneyTransform
    from transforms.cohort_analysis import CohortAnalysisTransform
    # ... etc for all 9

    # For each transform: try query + transform, catch and stub on failure
    try:
        from queries import user_journey_query
        from bq_client import run_query
        df = run_query(bq_client, user_journey_query(), account_id=account_id, ...)
        transform = UserJourneyTransform()
        analytics["journey"] = transform.transform(user_journey=df, customer_name=customer_name)
    except Exception as e:
        analytics["journey"] = {"available": False, "reason": str(e)}

    # ... repeat for all 9 transforms

    return analytics
```

### Empty State Rendering (D-09, D-10)
```javascript
render: function(container, data, config) {
  if (!document.querySelector('style[data-panel="cohort"]')) {
    PanelRegistry.injectCSS('cohort', PANEL_CSS);
  }

  // Full empty state when no data
  if (!data || !data.available) {
    container.innerHTML =
      '<div class="placeholder-panel">' +
        '<div class="placeholder-icon" style="border-color:var(--border-subtle);background:var(--bg-surface)">' +
          '<svg viewBox="0 0 24 24" width="24" height="24" ...>...</svg>' +
        '</div>' +
        '<div class="placeholder-title">Cohort Analysis</div>' +
        '<div class="placeholder-desc">' +
          (data && data.reason === 'no_data'
            ? 'No retention cohort data available. This requires at least 2 months of user activity data in BigQuery.'
            : 'Analytics data not available. Ensure the customer has an sfdc_account_id configured in customers.yaml.') +
        '</div>' +
      '</div>';
    return { charts: [] };
  }

  // Normal rendering when data.available is true
  var charts = [];
  // ... build charts
  return { charts: charts };
}
```

### getHeadlineStats Example (Risk Scoring)
```javascript
getHeadlineStats: function(data) {
  if (!data || !data.available) return [];
  var score = data.risk ? data.risk.score : null;
  if (score === null) return [];

  var color = score >= 70 ? 'var(--red)' : score >= 40 ? 'var(--amber)' : 'var(--green)';
  var tier = score >= 70 ? 'High' : score >= 40 ? 'Medium' : 'Low';

  return [
    { label: 'Churn Risk', value: Math.round(score) + '/100', color: color },
    { label: 'Risk Tier', value: tier, color: color }
  ];
}
```

### getAttentionItems Example (Engagement Decay)
```javascript
getAttentionItems: function(data) {
  if (!data || !data.available) return [];
  var items = [];
  var coldCount = data.cold_users_count || 0;

  if (coldCount > 0) {
    items.push({
      severity: coldCount >= 5 ? 'high' : 'medium',
      text: coldCount + ' user' + (coldCount !== 1 ? 's' : '') + ' showing engagement decay (cold)',
      action: { panel: 'decay' }
    });
  }
  return items;
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Standalone HTML analytics pages | Dashboard panels via PanelRegistry | Phase 8 (this phase) | Single-pane view replaces 9 separate files |
| Separate deep-analytics invocation | Inline transforms in assemble.py | Phase 8 (this phase) | Single BQ session, no orchestration complexity |
| CDN-loaded ECharts | Local lib/echarts.min.js bundle | Phase 5 (v1.0) | Offline reliability for file:// dashboards |
| Monolithic intelligence-dashboard.html | Folder-based panels + compose.py | Phase 5 (v1.0) | Modular, maintainable panel architecture |

## Open Questions

1. **assemble.py venv strategy**
   - What we know: customer-snapshot pyproject.toml has only pyyaml; deep-analytics has all BQ + pandas deps. Transforms need pandas.
   - What's unclear: Should we add deps to customer-snapshot's pyproject.toml, or change the SKILL.md to invoke assemble.py under deep-analytics venv?
   - Recommendation: Change SKILL.md invocation to use deep-analytics venv (aligns with D-03 cross-skill import intent). This is the least invasive change.

2. **cold_users_count field for badge_key**
   - What we know: UI-SPEC proposes `analytics.decay.cold_users_count` as badge_key. The EngagementDecayTransform would need to include this as a top-level field in its output.
   - What's unclear: Whether the transform currently outputs this field at the top level.
   - Recommendation: Add a `cold_users_count` integer field to the transform output dict alongside `available`. Same for `sdk_versions.stale_count`.

3. **overview.js modification scope**
   - What we know: overview.js already auto-aggregates from PanelRegistry.getAll(). New panels will be included automatically.
   - What's unclear: Whether 15 panels' worth of stats will overflow the stats-strip layout or create UX clutter.
   - Recommendation: Keep analytics panels' getHeadlineStats to 2 items max. Test with all 15 panels active and verify layout. Consider adding a "show more" toggle if stats exceed 12.

## Project Constraints (from CLAUDE.md)

- **Python execution:** Use `uv run --project .claude/skills/<skill>` for dependency isolation
- **Self-contained HTML:** Dashboard must work as standalone file:// pages (no server, no ES modules)
- **ECharts v5 locked:** Do NOT upgrade to v6. Use CDN URL `echarts@5` resolving to 5.6.0.
- **No build step:** No webpack, vite, rollup. CDN + inline JS/CSS only.
- **GSD workflow:** All changes must go through GSD execution commands.
- **Narrate before acting:** Explain what you're about to do so user can validate.
- **Test-driven development:** Use TDD for code changes.
- **Real data only:** Never use fake data for previews/testing (from project memory).
- **Deterministic pipeline:** Customer snapshot uses deterministic assemble.py, not ad-hoc scripts (from project memory).
- **Dedicated cloud data gap:** Team detection on dedicated cloud has anonymized telemetry -- no team/entity/username (from project memory).

## Sources

### Primary (HIGH confidence)
- **panel-registry.js** -- Full panel contract (register, renderPanel, injectCSS, _resolveKey)
- **compose.py** -- Dashboard composition pipeline (panels.yaml manifest, resolve_key, panel inclusion logic)
- **shell.html** -- Sidebar construction (buildSidebar, navigateTo, ICON_MAP, data gating at line 730)
- **support.js** -- Best reference panel (1091 lines, 5 ECharts charts, full contract implementation)
- **overview.js** -- Aggregation pattern (iterates PanelRegistry.getAll(), collects stats + attention items)
- **assemble.py** -- Data assembly pipeline (transform_jira_issues, compute_trending, transform_asana_tasks)
- **generate.py** -- Deep analytics page registry (9 handler functions showing BQ query -> transform pipeline)
- **All 9 transforms** -- Data shapes verified (user_journey, cohort_analysis, engagement_decay, feature_velocity, team_detection, risk_scoring, sdk_versions, usage_correlation, performance)
- **panels.yaml** -- Current manifest (3 groups, 6 panels)
- **08-CONTEXT.md** -- All decisions D-01 through D-10
- **08-UI-SPEC.md** -- Full visual contract (spacing, typography, color, component inventory, sidebar organization)
- **base-template.html** -- Standalone chart code to port (3116 lines, all 9 page renderers)
- **~/Documents/gitstuff/ai-docs/apache-echarts.md** -- ECharts v5 API reference

### Secondary (MEDIUM confidence)
- **SKILL.md (customer-snapshot)** -- Pipeline steps 1-9, INTELLIGENCE_DATA schema reference
- **SKILL.md (deep-analytics)** -- CLI usage, page type registry, prerequisites

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all components verified in codebase, no new dependencies needed
- Architecture: HIGH - existing panel contract is well-defined with 6 working examples
- Pitfalls: HIGH - identified from direct code analysis of compose.py data gating, sys.path patterns, and dependency mismatch
- Data pipeline: HIGH - all 9 transforms verified, output shapes match panel data_key expectations

**Research date:** 2026-04-03
**Valid until:** 2026-05-03 (stable -- no external dependency version risk)
