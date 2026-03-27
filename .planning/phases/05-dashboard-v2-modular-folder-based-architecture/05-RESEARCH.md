# Phase 05: Dashboard V2 — Modular Folder-Based Architecture - Research

**Researched:** 2026-03-27
**Domain:** Frontend architecture (vanilla JS), Python composition pipeline, monolith decomposition
**Confidence:** HIGH

## Summary

Phase 5 replaces the monolithic 3721-line `intelligence-dashboard.html` with a modular folder-based dashboard architecture. The output is a `customers/<name>/dashboard/` folder containing `index.html` (shell), `data.js`, individual panel JS files, and bundled libraries -- all working from `file://` protocol with no server.

The architecture is fully specified in `DASHBOARD-V2-SPEC.md` and the UI contract is locked in `05-UI-SPEC.md`. The v2 prototype (`dashboard-v2.html`, 1617 lines) provides a working reference for the shell, sidebar, navigation, command palette, and one functional panel (Support). Six support ticket visualization prototypes exist in `prototypes/support-tickets/`. The v1 monolith contains 5 extractable panels (Issues, Usage, Actions, Slack, and Trending/Health/Exec which merge into Overview).

**Primary recommendation:** Build infrastructure first (shell + registry + chart-helpers + compose.py), then the new Support panel from prototypes, then extract v1 panels one at a time (Actions first as simplest, Issues last as most complex), then build Overview as the aggregator. This matches the implementation order in DASHBOARD-V2-SPEC.md.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Apache ECharts | 5.6.0 (v5.x latest) | All chart rendering | Already in use across v1 monolith and deep-analytics. Bundled locally (no CDN). Decision: stay on v5, do NOT upgrade to v6. |
| Vanilla JS | ES2015+ | DOM construction, panel logic | No framework. Constraint from CLAUDE.md anti-patterns. |
| Vanilla CSS | Custom properties | Design system, theming | `:root` token system established across all templates. |
| Python 3.13 | via uv | Composition pipeline (`compose.py`) | Existing runtime for all skills. |
| PyYAML | >=6.0 | Read `panels.yaml` manifest | Already a dependency. |
| Google Fonts | CDN | Instrument Serif + Outfit + JetBrains Mono | Established typography. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pyyaml | >=6.0 | Parse panels.yaml in compose.py | Dashboard assembly |
| json (stdlib) | N/A | Write data.js from INTELLIGENCE_DATA dict | Dashboard assembly |
| shutil (stdlib) | N/A | Copy panel JS and lib files | Dashboard assembly |
| pathlib (stdlib) | N/A | Path manipulation | Throughout compose.py |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Classic `<script>` tags | ES modules (`type="module"`) | ES modules blocked on `file://` protocol by CORS (origin null). Classic scripts work. This is a hard constraint. |
| Folder-based dashboard | Single HTML (status quo) | 3700+ lines, 10K-20K at 15 panels, agent context explosion, poor perf with 20+ ECharts instances |
| Local ECharts bundle | CDN ECharts | CDN fails offline, on Google Drive, and when `file://` has no network. Local bundle is correct. |
| Hand-authored compose.py | Jinja2 templating | No Python server at render time. compose.py runs once at generation, then output is static. Jinja2 adds unnecessary dep. |

**No additional packages needed.** The composition pipeline (`compose.py`) uses only stdlib + pyyaml (already installed).

## Architecture Patterns

### Output Folder Structure

```
customers/<name>/dashboard/
  index.html          -- Shell: sidebar, nav, CSS tokens, router (~500 lines)
  data.js             -- INTELLIGENCE_DATA as JS variable (generated per refresh)
  panels/
    overview.js       -- Overview panel (~300 lines)
    issues.js         -- Jira issues panel (~600 lines, extracted from v1)
    support.js        -- Support tickets panel (~800 lines, from prototypes)
    usage.js          -- Usage panel (~500 lines, extracted from v1)
    actions.js        -- SE Actions panel (~300 lines, extracted from v1)
    slack.js          -- Slack sentiment panel (~300 lines, extracted from v1)
  lib/
    echarts.min.js    -- Bundled locally (~1MB, no CDN dependency)
    chart-helpers.js  -- Shared chart utilities (tooltips, colors, resize)
    panel-registry.js -- Panel contract + registration
  history/
    data-YYYY-MM-DD.js -- Dated snapshots for diff view
```

### Source Template Structure

```
.claude/skills/customer-snapshot/
  templates/
    shell.html                  -- index.html template (shell, sidebar, nav, router)
    panels/
      overview.js               -- Overview panel template
      issues.js                 -- Issues panel template
      support-tickets.js        -- Support panel template
      usage.js                  -- Usage panel template
      actions.js                -- Actions panel template
      slack.js                  -- Slack panel template
    lib/
      chart-helpers.js          -- Shared chart utilities
      panel-registry.js         -- Panel contract implementation
    panels.yaml                 -- Declarative panel manifest
    compose.py                  -- Assembles templates + data -> dashboard folder
  prototypes/
    support-tickets/            -- 6 reference HTML files (committed)
```

### Pattern 1: Panel Registration Contract

**What:** Every panel JS calls `PanelRegistry.register()` with a standard interface.
**When to use:** Every panel file.
**Why:** Shell auto-discovers panels, Overview aggregates stats/attention items.

```javascript
// Source: DASHBOARD-V2-SPEC.md Panel Contract + 05-UI-SPEC.md
PanelRegistry.register({
  id: 'support',
  group: 'intelligence',
  label: 'Support',
  icon: '<svg ...>...</svg>',  // inline SVG string
  badgeKey: 'usage.support_tickets.total',
  dataKey: 'usage.support_tickets',

  render(container, data, config) {
    // container: DOM element (#panel-{id})
    // data: resolved data object from INTELLIGENCE_DATA
    // config: { audience: 'internal'|'external' }
    // Returns: { charts: [echarts_instances] } for resize handling
  },

  getHeadlineStats(data) {
    // Returns: [{ label: string, value: string, color: string }]
  },

  getAttentionItems(data) {
    // Returns: [{ severity: 'high'|'medium'|'low'|'info', text: string,
    //             action: { panel: string, filter?: string } }]
  }
});
```

### Pattern 2: Lazy Panel Loading (Classic Script Injection)

**What:** Panel JS files loaded on first navigation via dynamic `<script>` tag insertion.
**When to use:** Shell router's `navigateTo()` function.
**Why:** Avoids loading all panels upfront. Works on `file://` protocol (unlike ES modules).

```javascript
// Source: dashboard-v2.html prototype + DASHBOARD-V2-SPEC.md
function navigateTo(panelId) {
  // Update hash for deep linking
  history.replaceState(null, '', '#' + panelId);

  // Hide all panels, show target
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  const panel = document.getElementById('panel-' + panelId);
  if (panel) {
    panel.classList.add('active');
    // Lazy load: insert <script> on first visit
    if (!renderedPanels[panelId]) {
      const script = document.createElement('script');
      script.src = 'panels/' + panelId + '.js';
      document.body.appendChild(script);
      renderedPanels[panelId] = true;
    }
    // Resize charts after panel visible
    setTimeout(() => ChartHelpers.resizeAll(), 50);
  }
}
```

### Pattern 3: CSS Scoping via Panel ID Prefix

**What:** Each panel defines a `PANEL_CSS` constant; shell wraps all selectors with `#panel-{id}`.
**When to use:** Every panel JS file.
**Why:** Prevents style collisions between panels sharing class names like `.stat-card`.

```javascript
// In panel JS file:
const PANEL_CSS = `
.stats-strip { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.stat-card { background: var(--bg-elevated); border: 1px solid var(--border-subtle); ... }
`;

// Shell injects as:
// <style>#panel-support .stats-strip { ... } #panel-support .stat-card { ... }</style>
```

### Pattern 4: Composition Pipeline (compose.py)

**What:** Python script that reads manifest + data, assembles output folder.
**When to use:** Called by `/customer-snapshot` skill during generation.
**Why:** Only `data.js` changes on refresh. Shell and panels are stable templates.

```python
# Source: DASHBOARD-V2-SPEC.md Composition Pipeline
def generate_dashboard(customer_name, data, output_dir):
    manifest = yaml.safe_load(read('panels.yaml'))
    active_panels = [p for p in manifest['panels']
                     if p.get('always_show') or resolve_key(data, p['data_key'])]

    # Write index.html (shell with nav for active panels only)
    shell = read('shell.html')
    shell = inject_nav(shell, active_panels, manifest['groups'])
    shell = inject_panel_scripts(shell, active_panels)
    write(f'{output_dir}/index.html', shell)

    # Write data.js
    write(f'{output_dir}/data.js',
          f'const INTELLIGENCE_DATA = {json.dumps(data, default=str)};')

    # Copy active panel JS files + lib/
    for panel in active_panels:
        copy(f'panels/{panel["id"]}.js', f'{output_dir}/panels/{panel["id"]}.js')
    copy_dir('lib/', f'{output_dir}/lib/')

    # Write history snapshot
    write(f'{output_dir}/history/data-{today}.js', ...)
```

### Pattern 5: ChartHelpers Shared Utilities

**What:** Centralized chart creation with automatic resize tracking, consistent tooltip/theme.
**When to use:** Every panel that creates ECharts instances.
**Why:** Eliminates duplicated theme registration, resize handlers, tooltip formatting.

```javascript
// Source: DASHBOARD-V2-SPEC.md Chart Helpers section
const ChartHelpers = {
  _instances: [],

  createChart(container) {
    const chart = echarts.init(container, 'wandb');
    this._instances.push(chart);
    return chart;
  },

  resizeAll() {
    this._instances.forEach(c => { try { c.resize(); } catch(e) {} });
  },

  getColor(name) {
    return getComputedStyle(document.documentElement)
      .getPropertyValue('--' + name).trim();
  },

  tooltipConfig() {
    return {
      backgroundColor: this.getColor('bg-elevated'),
      borderColor: this.getColor('border'),
      textStyle: {
        color: this.getColor('text-primary'),
        fontFamily: "'Outfit', system-ui, sans-serif",
        fontSize: 13
      }
    };
  }
};
```

### Anti-Patterns to Avoid

- **ES modules (`type="module"`):** Blocked by CORS on `file://` protocol. Use classic `<script>` tags only.
- **CDN dependencies in output:** Output folder must work offline. Bundle ECharts locally in `lib/`.
- **Shared state between panels:** Each panel is self-contained. Communication happens only through PanelRegistry (getHeadlineStats, getAttentionItems) for the Overview panel.
- **Modifying the v1 monolith:** The existing `intelligence-dashboard.html` must continue working unchanged. V2 is additive, not a replacement of the source template.
- **External JSON data files loaded via fetch:** `fetch()` fails on `file://` protocol. Data goes in `data.js` as a JS variable loaded via `<script>`.
- **Panel CSS without scoping:** Panels share class names (`.stat-card`, `.section-label`). Without `#panel-{id}` scoping, styles bleed between panels.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Chart theming/tooltips | Per-panel theme registration | `ChartHelpers.createChart()` + `tooltipConfig()` | 6 panels each re-registering `echarts.registerTheme('wandb', ...)` is fragile. Centralize in chart-helpers.js. |
| ECharts resize | Per-panel `window.addEventListener('resize', ...)` | `ChartHelpers.resizeAll()` in shell | Shell handles resize globally. Panels just return chart instances. |
| Panel CSS injection | Inline `<style>` tags in panel JS | Shell reads `PANEL_CSS` and injects with `#panel-{id}` prefix | Consistent scoping, no collisions. |
| Data presence checks | Per-panel null checking of INTELLIGENCE_DATA paths | `resolve_key(data, 'usage.support_tickets')` in compose.py | compose.py excludes panels with no data. Panel JS can assume data exists. |
| Date formatting | `new Date().toLocaleDateString()` per panel | Shared helpers in chart-helpers.js or shell | Consistent date display across all panels. |

**Key insight:** The shell owns cross-cutting concerns (navigation, resize, CSS scoping, data availability). Panels are pure render functions that receive a container and data.

## Common Pitfalls

### Pitfall 1: file:// Protocol CORS Blocking

**What goes wrong:** `<script type="module">`, `fetch()`, and `import()` all fail on `file://` protocol because the browser treats local files as opaque origins (origin: null).
**Why it happens:** Browser security treats every local file as a different origin. Cross-origin restrictions block module loading, fetch requests, and dynamic imports.
**How to avoid:** Use ONLY classic `<script src="...">` tags (no `type="module"`). Load data via `<script src="data.js">` that sets a global variable, NOT via `fetch('data.js')`. Panel JS files are classic scripts that call `PanelRegistry.register()` as a side effect.
**Warning signs:** "Access to script from origin 'null' has been blocked by CORS policy" in browser console.

### Pitfall 2: Panel Script Load Order

**What goes wrong:** Panel JS executes before its dependencies (panel-registry.js, chart-helpers.js, data.js) are loaded.
**Why it happens:** Dynamic `<script>` tags are async by default. If panel JS runs before `PanelRegistry` or `INTELLIGENCE_DATA` exist, it crashes.
**How to avoid:** Shell's `index.html` loads dependencies in order with synchronous `<script>` tags: (1) `lib/echarts.min.js`, (2) `lib/chart-helpers.js`, (3) `lib/panel-registry.js`, (4) `data.js`. Panel scripts are loaded later on navigation -- by that time, all dependencies exist as globals.
**Warning signs:** `ReferenceError: PanelRegistry is not defined` or `INTELLIGENCE_DATA is not defined`.

### Pitfall 3: ECharts Instances on Hidden Panels

**What goes wrong:** ECharts charts initialized on `display: none` panels have zero width/height, rendering as invisible or collapsed.
**Why it happens:** ECharts reads container dimensions at `init()` time. A hidden panel has 0x0 dimensions.
**How to avoid:** Only call `render()` AFTER the panel is set to `display: block` (`.active` class). The shell's `navigateTo()` activates the panel first, then triggers render. Follow up with `chart.resize()` after a brief timeout.
**Warning signs:** Charts appear as tiny dots or blank areas on first panel visit.

### Pitfall 4: Monolith Extraction Regression

**What goes wrong:** Extracting a panel from v1 breaks subtle dependencies (shared variables, event listeners, CSS cascade).
**Why it happens:** The v1 monolith has implicit coupling: shared variables like `RESOLVED_STATUSES`, `STALE_DAYS`, `NOW`, `daysBetween()`, cross-panel interactions (Asana badges on Jira issues, callout clicks filtering issues list).
**How to avoid:** Each extracted panel must be self-contained. Copy shared constants into each panel or put them in chart-helpers.js. Identify cross-panel interactions and replace with PanelRegistry-mediated communication. The v1 monolith continues to exist unchanged -- v2 is a new parallel output.
**Warning signs:** Panel works in isolation but breaks when combined with other panels in the shell.

### Pitfall 5: CSS Token Drift Between Shell and Panels

**What goes wrong:** Shell defines CSS custom properties (`:root { --bg-primary: ... }`), but panels hardcode color values instead of using tokens.
**Why it happens:** Copy-pasting from prototypes that used their own color systems (prototypes 3, 4 use different design tokens than the final system).
**How to avoid:** Panels MUST use `var(--token)` for all colors. The prototypes in `prototypes/support-tickets/` have DIFFERENT design tokens than the final system (e.g., prototype 3 uses `--bg-primary: #1F1F1F` vs actual `--bg-primary: #0c0f14`). Copy visualization logic, NOT design tokens.
**Warning signs:** Dark mode works but light mode has wrong colors, or one panel looks visually different from others.

### Pitfall 6: compose.py Path Resolution

**What goes wrong:** compose.py cannot find template files because relative paths break depending on working directory.
**Why it happens:** The skill is invoked via `uv run --project .claude/skills/customer-snapshot` but the compose.py lives in `templates/`. Path resolution changes based on `cwd`.
**How to avoid:** Use `Path(__file__).resolve().parent` to anchor all paths relative to compose.py's location, matching the pattern in deep-analytics `generate.py` (lines 24-28).
**Warning signs:** `FileNotFoundError` for template files that clearly exist.

### Pitfall 7: History Snapshot Diffing with Changing Schema

**What goes wrong:** `compose.py` tries to diff current `data.js` against a historical snapshot, but the data schema has changed between generations (new fields, renamed keys).
**Why it happens:** The INTELLIGENCE_DATA schema evolves as panels are added. Historical snapshots may lack fields that current panels expect.
**How to avoid:** Diff logic should be resilient to missing keys. Use a shallow diff strategy: compare top-level counts (issue count, ticket count, action count) rather than deep object comparison. Treat missing keys in historical data as "no previous data" rather than crashing.
**Warning signs:** `TypeError: Cannot read properties of undefined` when Overview panel tries to show "changes since last generation".

## Code Examples

### Example 1: Shell HTML Structure (index.html)

```html
<!-- Source: dashboard-v2.html prototype + DASHBOARD-V2-SPEC.md -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{CUSTOMER_NAME}} -- Customer Dashboard</title>
  <!-- Fonts from Google CDN (only external dependency) -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif&family=JetBrains+Mono:wght@400;600&family=Outfit:wght@400;600&display=swap" rel="stylesheet">
  <style>
    /* All CSS tokens and shell styles inline here */
    /* Panels inject their own scoped CSS via panel-registry.js */
  </style>
</head>
<body>
  <div class="shell" id="shell">
    <header class="dash-header"><!-- ... --></header>
    <aside class="sidebar"><!-- built by JS from manifest --></aside>
    <main class="content" id="content">
      <!-- Panel containers created by JS -->
    </main>
  </div>
  <div class="cmd-overlay" id="cmd-overlay"><!-- command palette --></div>

  <!-- Dependencies loaded synchronously in order -->
  <script src="lib/echarts.min.js"></script>
  <script src="lib/chart-helpers.js"></script>
  <script src="lib/panel-registry.js"></script>
  <script src="data.js"></script>
  <script>
    // Shell router, sidebar builder, keyboard shortcuts, command palette
    // Panel scripts loaded on-demand via navigateTo()
  </script>
</body>
</html>
```

### Example 2: Panel JS File Structure

```javascript
// panels/support.js
// Source: DASHBOARD-V2-SPEC.md Panel Contract + prototypes

(function() {
  'use strict';

  const PANEL_CSS = `
    .stats-strip { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px; }
    .stat-card { background: var(--bg-elevated); border: 1px solid var(--border-subtle); border-radius: var(--radius); padding: 20px; }
    .stat-value { font-family: var(--font-body); font-size: 28px; font-weight: 600; line-height: 1.1; }
    .stat-label { font-family: var(--font-mono); font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1.5px; color: var(--text-tertiary); }
    /* ... more panel-specific styles ... */
  `;

  PanelRegistry.register({
    id: 'support',
    group: 'intelligence',
    label: 'Support',
    icon: '<svg viewBox="0 0 24 24" ...>...</svg>',
    badgeKey: 'usage.support_tickets.total',
    dataKey: 'usage.support_tickets',

    render(container, data, config) {
      const tickets = data;
      const charts = [];

      // Build DOM
      container.innerHTML = `
        <div class="section-label">Support Tickets</div>
        <div class="stats-strip"><!-- ... --></div>
        <div class="two-col">
          <div class="panel-card"><div id="chart-volume" style="width:100%;height:300px"></div></div>
          <div class="panel-card"><div id="chart-concerns" style="width:100%;height:300px"></div></div>
        </div>
        <!-- scatter, submitters, heatmap sections -->
      `;

      // Init ECharts via ChartHelpers
      const volumeChart = ChartHelpers.createChart(
        container.querySelector('#chart-volume')
      );
      volumeChart.setOption({ /* ... */ });
      charts.push(volumeChart);

      return { charts };
    },

    getHeadlineStats(data) {
      return [
        { label: 'Tickets (12mo)', value: String(data.total), color: 'var(--text-primary)' },
        { label: 'Active', value: String(data.by_status.hold || 0), color: 'var(--amber)' }
      ];
    },

    getAttentionItems(data) {
      const items = [];
      const stale = (data.recent_tickets || []).filter(t => {
        const age = daysBetween(t.created_at);
        return age > 90 && t.status !== 'closed' && t.status !== 'solved';
      });
      if (stale.length > 0) {
        items.push({
          severity: 'high', text: `${stale.length} tickets stale 90+ days`,
          action: { panel: 'support', filter: 'stale' }
        });
      }
      return items;
    }
  });
})();
```

### Example 3: panels.yaml Manifest

```yaml
# Source: DASHBOARD-V2-SPEC.md panels.yaml section
groups:
  - id: intelligence
    label: Intelligence
  - id: usage
    label: Usage & Analytics
  - id: activity
    label: Activity & Comms

panels:
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
    data_key: usage.seat_utilization
    order: 4
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

## V1 Monolith Extraction Map

This table maps v1 functions to v2 panel files. It is the extraction reference for the planner.

| V1 Function | V1 Lines | V2 Panel | V2 File | Shared Dependencies |
|-------------|----------|----------|---------|-------------------|
| `renderActionsPanel()` | 1978-2187 | Actions | `panels/actions.js` | `ACTIONS_PRIO_ORDER`, `ACTIONS_SECTION_COLORS`, `addAsanaBadgesToJiraIssues()` |
| `renderSentimentPanel()` | 2238-2325 | Slack | `panels/slack.js` | `SENTIMENT_COLOURS`, `SENTIMENT_LABELS` |
| `renderUsagePanel()` + 6 sub-charts | 3337-3690 | Usage | `panels/usage.js` | `renderSeatChart()`, `renderRadarChart()`, `renderWeaveChart()`, `renderHoursChart()`, `renderAccountHealthGrid()`, `renderUsageKPIs()`, ECharts theme registration |
| `render()` + `renderThemes()` + `renderThemeChart()` + filters | 1645-1686, 1873-1970, 3031-3260 | Issues | `panels/issues.js` | `RESOLVED_STATUSES`, `ACTIVE_STATUSES`, `getFiltered()`, `classifyIssue()`, `buildFilters()`, `filterByBucket()`, `COMPONENT_NORMALIZE`, `PARENT_NORMALIZE` |
| `renderExecSummary()` + `renderHealthBuckets()` + `renderAttentionCallouts()` + `renderTrendingCharts()` + `renderVelocityChart()` + `renderCadenceMetrics()` | 2431-2923, 2537-2800 | Overview | `panels/overview.js` | Aggregates from all other panels via `getHeadlineStats()` and `getAttentionItems()` |
| *(new, from prototypes)* | N/A | Support | `panels/support.js` | 6 prototype HTML files as reference |

### Extraction Complexity Assessment

| Panel | Lines (est) | Complexity | Notes |
|-------|-------------|------------|-------|
| Actions | ~300 | LOW | Self-contained. Only shared dep is priority/section color maps. Simplest extraction. |
| Slack | ~200 | LOW | Self-contained. Only needs sentiment color/label maps. |
| Usage | ~500 | MEDIUM | 6 sub-charts, each creating ECharts instances. Must port to ChartHelpers. Account health grid is DOM-based. |
| Issues | ~600 | HIGH | Complex filter system (status pills, type pills, search, callout filter). Theme chart + grouped issue table + collapsible sections. Most coupled to shared state. |
| Support | ~800 | MEDIUM | New panel, no extraction needed. Build from prototypes. 5 ECharts visualizations. |
| Overview | ~400 | MEDIUM | Aggregator. Depends on all other panels being registered. Changes-since-last-generation diff logic. |

## file:// Protocol Compatibility Rules

This is the single most important technical constraint. Every implementation decision must respect it.

| Feature | Works on file:// | Alternative |
|---------|-----------------|-------------|
| `<script src="./file.js">` (classic) | YES | N/A -- use this |
| `<script type="module" src="./file.js">` | NO (CORS blocked) | Classic script |
| `fetch('./data.json')` | NO (CORS blocked) | `<script src="data.js">` with global var |
| `import('./module.js')` | NO (CORS blocked) | Dynamic `<script>` tag insertion |
| `<link rel="stylesheet" href="./style.css">` | YES | Inline `<style>` also works |
| `<img src="./image.png">` | YES | N/A |
| `window.location.hash` | YES | N/A -- used for routing |
| `history.replaceState()` | YES | N/A -- used for hash routing |
| Google Fonts CDN `<link>` | YES (with network) | Fonts degrade gracefully if offline |

**Pattern:** All JS loads via classic `<script>` tags. Data loads as a global variable (`const INTELLIGENCE_DATA = {...}`), NOT as JSON fetched via `fetch()`. Panel JS files are IIFEs that call `PanelRegistry.register()` as a side effect.

## Implementation Order (from DASHBOARD-V2-SPEC.md)

The spec prescribes this order. Research confirms it is correct -- infrastructure must exist before panels, simple extractions before complex ones, and Overview last because it aggregates.

1. **Shell + Registry + ChartHelpers + compose.py** -- Core infrastructure. Build and verify with placeholder panels.
2. **Support Tickets Panel** -- New panel from prototypes. Validates the panel contract without extraction complexity.
3. **Actions Panel** -- Simplest extraction (self-contained, ~210 lines of render logic).
4. **Usage Panel** -- Medium extraction (6 ECharts sub-charts to port to ChartHelpers).
5. **Slack Panel** -- Simple extraction (~90 lines of render logic).
6. **Issues Panel** -- Most complex extraction (filters, theme grouping, collapsible sections).
7. **Overview Panel** -- Aggregator. Calls `getHeadlineStats()` / `getAttentionItems()` on all registered panels. Includes diff-since-last-generation.
8. **Delight Pass** -- Panel transitions, ambient tab indicators, contextual right-click.

## Composition Pipeline Integration

### How compose.py Fits Into the Existing Skill

The existing `/customer-snapshot` skill (SKILL.md pipeline) has 9 steps. Phase 5 modifies Step 8:

| Current Step 8 | New Step 8 |
|----------------|------------|
| Read `intelligence-dashboard.html` template, replace `INTELLIGENCE_DATA`, write single HTML file | Call `compose.py` with customer data, produce dashboard folder |

The SKILL.md pipeline (Steps 1-7: parse name, load registry, fetch Jira, fetch Asana, fetch BQ, fetch Slack, analyze sentiment, cluster themes, build INTELLIGENCE_DATA) remains **unchanged**. Only the final output step changes.

**Both outputs can coexist:** The v1 monolith template remains available. compose.py produces the v2 folder. The agent chooses which to use. Eventually v1 is deprecated, but not during Phase 5.

### compose.py Responsibilities

1. Read `panels.yaml` manifest
2. Determine active panels (those with data in INTELLIGENCE_DATA)
3. Read `shell.html` template, inject: customer name, date, nav items, panel script tags
4. Write `data.js` from INTELLIGENCE_DATA dict
5. Copy active panel JS files to output `panels/`
6. Copy `lib/` directory (echarts.min.js, chart-helpers.js, panel-registry.js)
7. Write history snapshot if previous `data.js` exists
8. Compute diff summary (new/resolved tickets, changed trends) for Overview

## Prototype Fidelity Notes

The 6 support ticket prototypes are reference implementations, NOT copy-paste sources:

| Prototype | Reuse | Caution |
|-----------|-------|---------|
| `1-resolution-health.html` | Nested donut concept for headline stats area | Uses project-specific design tokens. Port logic, not styles. |
| `2-monthly-volume-trend.html` | Bar chart with peak annotation | Good ECharts pattern. Already implemented in v2 prototype. |
| `3-concern-treemap.html` | Treemap with severity coloring | Different design tokens (`#1F1F1F` bg, `#FFCC00` accent). Port chart config only. |
| `4-ticket-age-scatter.html` | Color-zone scatter with clickable Jira links | Different design tokens and fonts. Port scatter logic. |
| `5-submitter-activity.html` | Stacked bars + sparklines + heatmap | Correct design tokens (matches final system). Best reference for full layout. |
| `6-escalation-sankey.html` | Sankey flow diagram | Spec says "Consider as expandable deep dive or drop." Low priority. |

**Key rule from CLAUDE.md:** "Don't over-adapt source material -- copy as-is when already correct." Prototype 5 uses the correct design system. Prototypes 3 and 4 do not.

## Cross-Panel Interactions

These interactions from v1 must be preserved or re-implemented in v2:

| Interaction | V1 Implementation | V2 Strategy |
|-------------|-------------------|-------------|
| Asana badges on Jira issues | `addAsanaBadgesToJiraIssues()` in v1 global scope | Issues panel checks `INTELLIGENCE_DATA.actions.tasks` for linked_jira matches. Self-contained within Issues panel. |
| Callout clicks filter issues | `filterByBucket()` scrolls to issue section | Overview attention items have `action: { panel: 'issues', filter: 'stale' }`. Shell navigates to Issues panel and applies filter. |
| Exec summary usage KPIs | `renderUsageKPIs()` called from exec summary area | Overview panel calls `getHeadlineStats()` on Usage panel registration. |
| Internal/external toggle hides data | `.internal-only` CSS class in v1 | V2 handles at generation time. `data.js` omits sensitive fields for `--external` mode. No runtime toggle needed. |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single monolithic HTML (v1) | Folder-based modular dashboard (v2) | Phase 5 | Each file 300-800 lines vs 3700+ lines monolith |
| CDN-loaded ECharts | Locally bundled ECharts | Phase 5 | Works offline, on Google Drive, no CDN dependency |
| Runtime internal/external toggle | Generation-time audience selection | Phase 5 | No accidental data exposure during screenshare |
| All panels always rendered | On-demand lazy loading | Phase 5 | Better performance, smaller initial load |

## Open Questions

1. **ECharts bundle size**
   - What we know: Full ECharts v5 is ~1MB gzipped, ~3MB uncompressed
   - What's unclear: Whether to bundle full or create a custom build with only needed chart types (bar, scatter, treemap, heatmap, line, gauge, radar, sankey, funnel)
   - Recommendation: Bundle full distribution for simplicity. 1MB is acceptable for a locally-opened file. Custom builds add maintenance burden.

2. **Google Fonts offline fallback**
   - What we know: Fonts load from Google CDN. If offline, fallback fonts render.
   - What's unclear: Whether Google Drive shared folders have network access (they should, since Drive is cloud)
   - Recommendation: Keep Google Fonts CDN link. The fallback stack (`Georgia`, `system-ui`, `monospace`) is acceptable degradation.

3. **Scope of customer-snapshot skill changes**
   - What we know: compose.py is new. The existing pipeline (Steps 1-7) is unchanged.
   - What's unclear: Should `/customer-snapshot` default to v2 output, or require a `--v2` flag?
   - Recommendation: Default to v2 folder output. Keep v1 available via `--legacy` flag for transition period.

## Sources

### Primary (HIGH confidence)
- `DASHBOARD-V2-SPEC.md` (project root) -- Full architecture specification, 485 lines
- `05-UI-SPEC.md` (phase directory) -- UI design contract, 512 lines
- `intelligence-dashboard.html` -- V1 monolith, 3721 lines (extraction source)
- `dashboard-v2.html` -- V2 prototype, 1617 lines (shell + support panel reference)
- `prototypes/support-tickets/*.html` -- 6 visualization prototypes (support panel reference)
- `deep-analytics/scripts/generate.py` -- Existing Python pipeline pattern (compose.py reference)
- `~/Documents/gitstuff/ai-docs/apache-echarts.md` -- ECharts v5/v6 capabilities and patterns

### Secondary (MEDIUM confidence)
- [whatwg/html#8121](https://github.com/whatwg/html/issues/8121) -- file:// module script restrictions
- [MDN CORS documentation](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS) -- origin null behavior
- [MDN Same-origin policy](https://developer.mozilla.org/en-US/docs/Web/Security/Same-origin_policy) -- file:// origin semantics

### Tertiary (LOW confidence)
- None -- all findings verified against primary sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all technology already in use
- Architecture: HIGH -- fully specified in DASHBOARD-V2-SPEC.md with working prototype
- Pitfalls: HIGH -- file:// CORS verified via MDN docs, extraction risks assessed from v1 code analysis
- Composition pipeline: HIGH -- follows established pattern from deep-analytics generate.py

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable -- no fast-moving dependencies)
