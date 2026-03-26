# Dashboard V2 Architecture Spec

**Status:** Design complete, ready for implementation
**Author:** Claude Opus 4.6 + Allan Stevenson
**Date:** 2026-03-26
**Context:** This document captures all architecture decisions from the Phase 10 session. It is written for agent execution — a fresh Claude session should be able to implement this end-to-end.

## Goal

Replace the monolithic 3700-line `intelligence-dashboard.html` with a modular, folder-based dashboard that:
- Scales to 15-20+ panels without becoming unwieldy
- Supports rich visualizations per panel (prototype quality, not basic bars)
- Can live on Google Drive for multi-user access
- Can be refreshed by a Claude Code loop task
- Links to canonical systems (Asana, Jira, Slack) rather than storing its own state
- Is delightful to use during cadence calls and QBR screenshares

## Architecture: Folder-Based Report (Approach D)

### Why not a single HTML file?

The current dashboard is one self-contained HTML file. This worked at 4 panels but breaks at 8+:
- 10K-20K lines for 15 panels
- Browser performance degrades with 20+ ECharts instances
- Agents need massive context to edit one panel
- Every regeneration rebuilds everything

### Output Structure

Each customer dashboard is a folder:

```
customers/<name>/dashboard/
  index.html          -- Shell: sidebar, nav, CSS tokens, router (~500 lines)
  data.js             -- INTELLIGENCE_DATA as JS module (generated per refresh)
  panels/
    overview.js       -- Overview panel (~300 lines)
    issues.js         -- Jira issues panel (~600 lines, extracted from v1)
    support.js        -- Support tickets panel (~800 lines, from prototypes)
    usage.js          -- Usage panel (~500 lines, extracted from v1)
    actions.js        -- SE Actions panel (~300 lines, extracted from v1)
    slack.js          -- Slack sentiment panel (~300 lines, extracted from v1)
  lib/
    echarts.min.js    -- Bundled locally (no CDN dependency)
    chart-helpers.js  -- Shared chart utilities (tooltips, colors, resize)
    panel-registry.js -- Panel contract + registration
```

### Why this works

- **Each file is small** (300-800 lines) — agents only read what they're editing
- **Only `data.js` changes** on each refresh — index.html and panel JS are stable
- **Panels load on demand** — `<script>` tags inserted on first navigation
- **Works on file:// protocol** — no server needed, open from filesystem
- **Google Drive compatible** — sync folder, multiple users see same dashboard
- **`zip dashboard/`** for sharing — one command

### Source Templates

The generation pipeline uses template files in the skills directory:

```
.claude/skills/customer-snapshot/
  templates/
    shell.html                  -- index.html template (sidebar, nav, router)
    panels/
      overview.js               -- Overview panel template
      issues.js                 -- Issues panel template (extract from v1 monolith)
      support-tickets.js        -- Support panel template (build from prototypes)
      usage.js                  -- Usage panel template (extract from v1 monolith)
      actions.js                -- Actions panel template (extract from v1 monolith)
      slack.js                  -- Slack panel template (extract from v1 monolith)
    lib/
      chart-helpers.js          -- Shared chart utilities
      panel-registry.js         -- Panel contract implementation
    panels.yaml                 -- Declarative panel manifest
    compose.py                  -- Assembles templates + data → dashboard folder
  prototypes/
    support-tickets/            -- 6 reference HTML files (committed)
```

## Panel Contract

Every panel JS file must export a registration call:

```javascript
PanelRegistry.register({
  id: 'support',
  group: 'intelligence',
  label: 'Support',
  icon: 'headset',            // SVG icon name
  badgeKey: 'usage.support_tickets.total',  // dot-path into INTELLIGENCE_DATA
  dataKey: 'usage.support_tickets',         // null = hide panel from nav

  render(container, data, config) {
    // Build DOM inside container using data
    // Return { charts: [...echarts instances] } for resize handling
  },

  getHeadlineStats(data) {
    // Return array of { label, value, color } for Overview panel
    return [
      { label: 'Support Tickets', value: '30 (12mo)', color: 'var(--text-primary)' },
      { label: 'Active', value: '8', color: 'var(--amber)' }
    ];
  },

  getAttentionItems(data) {
    // Return array of { severity, text, action } for Overview attention callouts
    return [
      { severity: 'amber', text: '3 tickets stale for 90+ days', action: { panel: 'support', filter: 'stale' } }
    ];
  }
});
```

## panels.yaml Manifest

```yaml
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
    badge_filter: "status not in ['Done', 'Merged', 'Closed']"
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

## Navigation

### Sidebar Design

- **Default: 56px wide (icon-only)**. Click toggle button to expand to 220px with labels.
- **Group headers** visible when expanded, collapse/expand their items
- **Badge counts** visible in both modes (small dot in icon mode, pill in expanded mode)
- **Active item**: accent-colored left border + accent icon/text
- **Hidden when no data**: if `data_key` resolves to null/undefined, nav item not rendered
- **Keyboard**: `1-6` jump to panels, `Cmd+K` opens command palette

### Two-Tier Navigation (future scale)

When panel count exceeds ~8, groups become collapsible sections:
```
Intelligence      [v]     <- click to collapse
  Overview
  Issues (5)
  Support (8)
Usage             [v]
  Seats & Adoption
  Product Areas
  Deep Dive
Activity          [>]     <- collapsed, click to expand
```

This pattern scales to 20+ panels without overwhelming the sidebar.

### URL Hash Routing

- `#support`, `#issues`, `#usage`, etc.
- Default: `#overview`
- Deep links work — shareable URLs to specific panels
- Hash changes trigger panel navigation (back/forward button works)

## Support Tickets Panel — Build from Prototypes

The Support panel in dashboard-v2.html is basic. It MUST be rebuilt to match prototype quality. Use the committed prototypes as reference:

### Reference prototypes (`.claude/skills/customer-snapshot/prototypes/support-tickets/`)

| File | What to incorporate |
|------|-------------------|
| `1-resolution-health.html` | Nested donut chart for resolution rate. Use as a compact viz in the headline stats area. |
| `2-monthly-volume-trend.html` | Bar chart concept is good but fix the backlog line bug. Use clean bars only. Annotate peak months. |
| `3-concern-treemap.html` | Grouped treemap with severity coloring. Use this instead of the basic horizontal bar chart. |
| `4-ticket-age-scatter.html` | Color-zone scatter plot with clickable Jira links. Use this instead of the plain table. Keep the table as a detail view below the scatter. |
| `5-submitter-activity.html` | Stacked bar + sparklines + heatmap. Use real per-submitter monthly data. This is the richest prototype — use the full layout. |
| `6-escalation-sankey.html` | Sankey is cool but low info density for dashboard space. Consider as an expandable "deep dive" section or drop. |

### Recommended Support panel layout

```
┌─────────────────────────────────────────────────────────┐
│ HEADLINE STATS STRIP                                     │
│ [30 tickets] [8 active] [73% resolved] [2.5/mo avg]    │
├────────────────────────────┬────────────────────────────┤
│ MONTHLY VOLUME TREND       │ CONCERN TREEMAP            │
│ (bar chart, peak annotated)│ (grouped, severity-colored)│
├────────────────────────────┴────────────────────────────┤
│ ACTIVE TICKETS                                          │
│ (scatter plot with age/priority color zones)             │
│ (expandable detail table below)                         │
├────────────────────────────┬────────────────────────────┤
│ TOP SUBMITTERS             │ SUBMITTER × CONCERN        │
│ (stacked bars with         │ HEATMAP                    │
│  sparklines per person)    │                            │
└────────────────────────────┴────────────────────────────┘
```

### Data contract (from `usage.py` builder output)

```javascript
INTELLIGENCE_DATA.usage.support_tickets = {
  total: 30,
  by_status: { closed: 21, hold: 8, solved: 1 },
  by_priority: { high: 28, urgent: 2 },
  escalated_to_jira: 0,
  csat: { offered: 18, unoffered: 10 },
  top_concerns: [{ concern: "workspace", count: 6 }, ...],
  monthly_volume: [{ month: "2025-03", count: 1 }, ...],
  recent_tickets: [{ id: 113975, subject: "...", status: "hold", priority: "high", created_at: "2026-03-17", jira_id: "WB-32236", concern: "workspace", ... }],
  top_submitters: [{ name: "Nikitas Rontsis", count: 19, concerns: [...] }, ...]
}
```

## Extracting Existing Panels from V1 Monolith

The current `intelligence-dashboard.html` (3700 lines) contains these panels that need extraction:

| Panel | V1 Lines (approx) | V1 Functions | Notes |
|-------|-------------------|--------------|-------|
| Exec Summary | 2537-2800 | `renderExecSummary()` | Becomes the Overview panel |
| Issues | 1645-1686 + 1873-1970 + 3031-3220 | `render()`, `renderThemes()`, `renderThemeChart()` | Largest extraction — filters, theme chart, issue table |
| Usage | 1593-1643 + 3337-3690 | `renderUsagePanel()`, `renderSeatChart()`, `renderRadarChart()`, `renderWeaveChart()`, `renderHoursChart()`, `renderAccountHealthGrid()` | 6 sub-charts + KPIs |
| Actions | 1978-2236 | `renderActionsPanel()` | Asana tasks, cross-linked Jira badges |
| Slack | 2238-2430 | `renderSentimentPanel()` | Sentiment, hot threads |
| Trending | 2431-2536 | `renderTrendingCharts()` | Merge into Overview or Issues |
| Health/Attention | 2801-2923 | `renderHealthBuckets()`, `renderAttentionCallouts()` | Merge into Overview |

**Strategy:** Extract one panel at a time. After each extraction, verify the composed dashboard still works. Start with the simplest (Actions), end with the most complex (Issues).

## Composition Pipeline (compose.py)

```python
# Pseudocode
def generate_dashboard(customer_name, data, output_dir):
    """Generate a dashboard folder for a customer."""

    # 1. Read manifest
    manifest = yaml.safe_load(read('panels.yaml'))

    # 2. Determine which panels have data
    active_panels = [p for p in manifest['panels']
                     if p.get('always_show') or resolve_key(data, p['data_key'])]

    # 3. Write index.html
    shell = read('shell.html')
    shell = inject_nav(shell, active_panels, manifest['groups'])
    shell = inject_panel_scripts(shell, active_panels)
    write(f'{output_dir}/index.html', shell)

    # 4. Write data.js
    write(f'{output_dir}/data.js', f'const INTELLIGENCE_DATA = {json.dumps(data)};')

    # 5. Copy panel JS files (only active ones)
    for panel in active_panels:
        copy(f'panels/{panel["id"]}.js', f'{output_dir}/panels/{panel["id"]}.js')

    # 6. Copy lib files
    copy_dir('lib/', f'{output_dir}/lib/')
```

## Internal/External Mode

Handled at **generation time**, not with a toggle:

- `/customer-snapshot CustomerName` — internal mode (default). Includes submitter names, CSAT, internal annotations.
- `/customer-snapshot CustomerName --external` — external mode. Strips: submitter names, CSAT breakdown, internal-only attention items. The `data.js` simply doesn't contain this data.

No visible toggle in the UI. No risk of accidentally showing internal data during screenshare.

## Shared Folder / Google Drive Deployment

The folder structure is inherently Drive-friendly:

1. Dashboard folder lives at `customers/<name>/dashboard/` (already gitignored)
2. This folder can be symlinked or moved to Google Drive
3. `index.html` + panel JS files = static, rarely change
4. `data.js` = changes on each refresh
5. A Claude Code loop task refreshes `data.js`:
   ```
   /loop 30m /customer-snapshot CustomerName --refresh-only
   ```
6. Multiple users open `index.html` from Drive — each sees latest data on panel navigation

### Time Travel / Diff View

Each generation writes a dated snapshot:
```
customers/<name>/dashboard/
  data.js                    -- current (symlink or latest copy)
  history/
    data-2026-03-25.js
    data-2026-03-11.js
    data-2026-02-28.js
```

The Overview panel can show a "Changes since last generation" section:
- New tickets since last snapshot
- Resolved tickets since last snapshot
- Issues that are still open and have aged
- Trends that changed direction

This is computed at generation time by `compose.py` diffing current vs previous `data.js`.

## Delight Features

### Phase 1 (build with v2)
- **Panel transitions** — CSS crossfade/slide when switching panels (~20 lines CSS)
- **Ambient tab indicators** — Browser tab shows `Isomorphic (3 stale)` with colored favicon (~10 lines JS)
- **Agent-generated "So what?" annotations** — Computed at generation time, injected into `data.js` as `insights` array. Each panel reads its relevant insights.
- **Contextual right-click** — Right-click Jira key: "Open in Jira", "Copy key", "Find in Issues panel". Right-click submitter: "Search Slack". Links to canonical systems.

### Phase 2 (after core is stable)
- **Cmd+K command palette** — Search across all data, jump to panels
- **Sparkline badges in sidebar** — Mini trend per nav item
- **Print stylesheet** — `@media print` for current panel, or dedicated PDF generation

### Phase 3 (after usage feedback)
- **Live refresh mode** — WebSocket from `serve.py` pushes `data.js` updates
- **Time travel** — Date picker loads historical data snapshots
- **Agent automation** — Loop tasks that act on attention items (create Asana tasks for stale tickets, post Slack reminders)

## Design System

### CSS Custom Properties (theme tokens)

All panels use these — never hardcode colors:

```css
/* Semantic tokens that panels should use */
--color-positive: var(--green);
--color-warning: var(--amber);
--color-danger: var(--red);
--color-info: var(--blue);
--color-accent: var(--accent);
--color-muted: var(--text-tertiary);

/* Chart-specific tokens */
--chart-grid: var(--border-subtle);
--chart-axis-label: var(--text-tertiary);
--chart-tooltip-bg: var(--bg-elevated);
--chart-tooltip-border: var(--border);
```

### Chart Helpers (lib/chart-helpers.js)

Shared utilities so panels don't reinvent:

```javascript
ChartHelpers.createChart(container, options)  // wraps echarts.init + theme
ChartHelpers.horizontalBar(container, data)   // standard horizontal bar
ChartHelpers.timeSeries(container, data)      // standard time series
ChartHelpers.tooltip(params)                  // consistent tooltip format
ChartHelpers.colors                           // palette array
ChartHelpers.resizeAll()                      // resize all tracked instances
```

### Panel CSS Scoping

Each panel's CSS is automatically scoped by the shell:
```css
/* Panel JS file contains: */
const PANEL_CSS = `
.stats-strip { display: grid; ... }
.ticket-row:hover { background: var(--bg-hover); }
`;

// Shell wraps it as:
// #panel-support .stats-strip { ... }
// #panel-support .ticket-row:hover { ... }
```

## Implementation Order

### Step 1: Shell + Registry + Compose Pipeline
- Build `shell.html` with sidebar, router, panel loading
- Build `panel-registry.js` with contract enforcement
- Build `chart-helpers.js` with shared utilities
- Build `compose.py` that assembles a working dashboard folder
- Verify with placeholder panels

### Step 2: Support Tickets Panel (new, from prototypes)
- Build `support-tickets.js` matching prototype quality
- Use all 5 selected visualizations at prototype fidelity
- Wire real data from `usage.py` support_tickets output
- Test with Isomorphic Labs data

### Step 3: Extract Actions Panel (simplest existing)
- Extract from v1 monolith into `actions.js`
- Verify works in v2 shell
- Verify v1 still works unchanged (don't break existing dashboard)

### Step 4: Extract Usage Panel
- Extract 6 sub-charts into `usage.js`
- Port ECharts instances to use chart-helpers

### Step 5: Extract Slack Panel
- Extract sentiment + hot threads into `slack.js`

### Step 6: Extract Issues Panel (most complex)
- Filters, theme chart, grouped issue table
- This is the biggest extraction

### Step 7: Build Overview Panel
- Calls `getHeadlineStats()` on all panels
- Calls `getAttentionItems()` on all panels
- Shows diff-since-last-generation if history exists
- Agent-generated narrative insights

### Step 8: Delight Pass
- Panel transitions
- Ambient tab indicators
- Contextual right-click actions
- Visual polish

## Open Questions for Future Sessions

1. Should deep-analytics sub-pages become panels or stay as linked-out reports?
2. How should the generation pipeline handle partial data (e.g., BQ available but Slack not)?
3. Should there be a "portfolio view" that shows all customers in one dashboard?
4. What's the right refresh interval for the loop task? 30 minutes? Hourly?

## Files Changed / Created This Session

### Committed
- `.claude/skills/bigquery/scripts/queries.py` — `support_tickets_query()` (5971593)
- `.claude/skills/bigquery/scripts/usage.py` — `_build_support_tickets()`, `top_submitters` (5971593)
- `.claude/skills/bigquery/tests/conftest.py` — test fixture (5971593)
- `.claude/skills/bigquery/tests/test_usage.py` — 14 new tests (5971593)
- `.claude/skills/customer-snapshot/templates/dashboard-v2.html` — v2 shell prototype (81e4eab)
- `.claude/skills/customer-snapshot/prototypes/support-tickets/1-6*.html` — 6 viz prototypes (4165365)

### Key Facts
- `dim_helpdesk_tickets` in BigQuery has Zendesk data (no direct API needed)
- Customer matching: `account_name` joins to `stg_salesforce_accounts.name` via `@account_id`
- `TIMESTAMP_SUB` needs `INTERVAL 365 DAY` not `INTERVAL 12 MONTH` for TIMESTAMP columns
- 47 BigQuery skill tests pass
- Isomorphic Labs: 30 tickets, 8 active (all hold), Nikitas Rontsis files 63%
