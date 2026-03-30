---
phase: 05-dashboard-v2-modular-folder-based-architecture
plan: 03
subsystem: ui
tags: [vanilla-js, panel-extraction, asana, slack, sentiment, css-custom-properties]

# Dependency graph
requires:
  - phase: 05-01
    provides: "PanelRegistry with register/injectCSS API, ChartHelpers, panels.yaml manifest, compose.py pipeline"
provides:
  - "Actions panel JS with scope toggle, priority sorting, section grouping, overdue/stale flags, Jira/Asana cross-links"
  - "Slack sentiment panel JS with score display, hot threads, internal risk signals, recommended actions"
affects: [05-05, 05-06]

# Tech tracking
tech-stack:
  added: []
  patterns: [panel-iife-extraction, scope-toggle-closure, audience-gated-internal-section]

key-files:
  created:
    - ".claude/skills/customer-snapshot/templates/panels/actions.js"
    - ".claude/skills/customer-snapshot/templates/panels/slack.js"
  modified: []

key-decisions:
  - "Copied v1 ACTIONS_SECTION_COLORS with full section-to-color mapping (including Done, Scheduled/Future) for forward compatibility"
  - "Scope toggle uses closure-based re-render pattern (renderInner) rather than full PanelRegistry re-render"
  - "Slack internal section gated on config.audience === 'internal' matching shell's audience toggle"
  - "Used escapeHtml() for all user-supplied content (task names, channel names, summaries) to prevent XSS"

patterns-established:
  - "Panel IIFE structure: constants, PANEL_CSS string, ICON_SVG, helpers, PanelRegistry.register()"
  - "CSS injection guard: if (!document.querySelector('style[data-panel=\"id\"]')) PanelRegistry.injectCSS()"
  - "Scope toggle closure: local variable + renderInner() function for stateful re-renders without external state"
  - "Graceful degradation: check data.available, provide reason-specific messages with setup hints"

requirements-completed: [DASH-06, DASH-08]

# Metrics
duration: 5min
completed: 2026-03-30
---

# Phase 05 Plan 03: Actions + Slack Panel Extraction Summary

**Actions panel with scope toggle, priority sorting, and Jira cross-links plus Slack sentiment panel with hot threads and internal risk signals -- both extracted from v1 monolith into standalone PanelRegistry modules**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-30T15:08:48Z
- **Completed:** 2026-03-30T15:15:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Actions panel (540 lines) with scope toggle (my_tasks/team), priority sorting (overdue-first then P0-P3), section grouping (In Progress/Waiting/To Do/Other), expand/collapse for 10+ tasks, Jira cross-links, Asana links, and overdue/stale flagging
- Slack sentiment panel (348 lines) with category-colored score display, hot threads list (up to 5) with Slack deep links, audience-gated internal section with risk signals and recommended actions
- Both panels register with PanelRegistry providing getHeadlineStats and getAttentionItems for Overview aggregation
- Both handle graceful degradation with reason-specific messages when data is unavailable or unconfigured

## Task Commits

Each task was committed atomically:

1. **Task 1: Actions panel extraction from v1 monolith** - `68b17ae` (feat)
2. **Task 2: Slack sentiment panel extraction from v1 monolith** - `803c6bb` (feat)

## Files Created/Modified
- `.claude/skills/customer-snapshot/templates/panels/actions.js` - SE Actions panel with scope toggle, priority sorting, section grouping, overdue/stale flags, Jira/Asana cross-links
- `.claude/skills/customer-snapshot/templates/panels/slack.js` - Slack sentiment panel with score display, hot threads, internal risk signals, recommended actions

## Decisions Made
- Copied v1 ACTIONS_SECTION_COLORS with full section-to-color mapping (6 sections including Done, Scheduled/Future) for forward compatibility even though v1 only renders 4 groups
- Used closure-based renderInner() for scope toggle re-render rather than calling PanelRegistry.renderPanel() again, keeping panel state (scope, expanded) encapsulated
- Gated internal section on `config.audience === 'internal'` to match shell's audience toggle pattern
- Added escapeHtml() helper in both panels for XSS prevention on user-supplied content (task names, channel names, thread summaries)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None. Both panels are fully functional with real data rendering. Empty states handled gracefully when data is unavailable.

## Next Phase Readiness
- Two of four panel extractions complete (Actions + Slack from Plan 03, Issues from Plan 02)
- Usage panel extraction remains (Plan 04, Wave 2) -- the most complex extraction with ECharts charts
- Overview panel (Plan 05, Wave 3) depends on all other panels being registered for aggregation
- compose.py pipeline can now assemble dashboards with actions.js and slack.js panel files

## Self-Check: PASSED

All 2 created files verified present on disk. All 2 task commit hashes verified in git log.

---
*Phase: 05-dashboard-v2-modular-folder-based-architecture*
*Completed: 2026-03-30*
