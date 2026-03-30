---
phase: 05-dashboard-v2-modular-folder-based-architecture
plan: 04
subsystem: ui
tags: [echarts, vanilla-js, css-custom-properties, dashboard, usage-panel, chart-helpers]

# Dependency graph
requires:
  - phase: 05-01
    provides: "PanelRegistry, ChartHelpers, panels.yaml manifest, shell.html, compose.py pipeline"
provides:
  - "Usage panel (panels/usage.js) with 4 ECharts charts + KPI row + account health grid"
  - "Validated ChartHelpers.createChart() handles multi-chart panels correctly"
affects: [05-06]

# Tech tracking
tech-stack:
  added: []
  patterns: [multi-chart-panel-pattern, internal-audience-gating, kpi-trend-arrows, zone-class-coloring]

key-files:
  created:
    - ".claude/skills/customer-snapshot/templates/panels/usage.js"
  modified: []

key-decisions:
  - "Local helper functions (isDark, formatNumber, formatTrendHTML, zoneClass) duplicated inside IIFE for panel isolation rather than shared globally"
  - "Radar chart capped at top 8 product areas sorted by total_events to avoid visual clutter"
  - "Two-column layout for radar + Weave charts, full-width for seat and hours charts"
  - "Account health grid uses card-based layout (not v1 two-column grid) for responsive behavior"

patterns-established:
  - "Multi-chart panel: render() builds layout HTML, then calls sub-renderers sequentially, collecting chart instances"
  - "Internal-audience gating: config.audience === 'internal' && data.account_health checks at both HTML build and render stages"
  - "KPI row pattern: flexbox with clamp() gap, zone-class coloring for utilization percentages, trend arrows via formatTrendHTML"
  - "Chart sub-renderer contract: function(chartEl, data) returns ECharts instance or null"

requirements-completed: [DASH-07]

# Metrics
duration: 5min
completed: 2026-03-30
---

# Phase 05 Plan 04: Usage Panel Extraction Summary

**Usage panel with 4 ECharts charts (seat line, product radar, Weave bar, tracked hours bar), KPI summary row with trend arrows, and internal-only account health card grid, all via ChartHelpers.createChart()**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-30T15:08:53Z
- **Completed:** 2026-03-30T15:14:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Extracted all 6 sub-renderers from v1 monolith (lines 3337-3690) into isolated panel file
- Migrated all 4 ECharts instances from direct echarts.init() to ChartHelpers.createChart() with shared tooltipConfig/axisLabelConfig/gridLine helpers
- Account health grid with 7 cards (renewal, ARR, CS tier, health badge, churn risk, plan, deployment) gated on internal audience
- getHeadlineStats (seat %, Weave GB, run count) and getAttentionItems (low utilization, declining trend, elevated churn) for Overview panel integration

## Task Commits

Each task was committed atomically:

1. **Task 1: Usage panel -- KPIs, seat chart, radar chart, Weave chart, hours chart** - `45ee4a8` (feat)

## Files Created/Modified
- `.claude/skills/customer-snapshot/templates/panels/usage.js` - Usage panel with 4 ECharts charts, KPI row, account health grid, PanelRegistry.register() integration (870 lines)

## Decisions Made
- Local helper functions (isDark, formatNumber, formatTrendHTML, zoneClass) duplicated inside IIFE -- these exist in v1 global scope but panels need isolation since they load independently
- Radar chart capped at top 8 product areas (sorted by total_events descending) to prevent visual clutter on accounts with many product areas
- Two-column grid layout for radar + Weave charts, responsive to single column at 700px breakpoint
- Account health grid uses card-based layout with auto-fill grid (minmax 200px, 1fr) rather than v1's simpler two-column grid, for better responsive behavior
- Health badge uses pill-style colored badges (green-dim/amber-dim/red-dim backgrounds) instead of v1's dot indicator

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None. All chart renderers are fully functional with real data paths. No placeholder data or TODO markers.

## Next Phase Readiness
- Usage panel ready for integration into v2 dashboard via compose.py
- Validates that ChartHelpers handles multi-chart panels (4 ECharts instances) correctly
- Pattern established for future chart-heavy panels: sub-renderer contract returns instance, render() collects into charts array

## Self-Check: PASSED

All 1 created file verified present on disk. Task commit hash 45ee4a8 verified in git log.

---
*Phase: 05-dashboard-v2-modular-folder-based-architecture*
*Completed: 2026-03-30*
