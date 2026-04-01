---
phase: 05-dashboard-v2-modular-folder-based-architecture
plan: 05
subsystem: ui
tags: [dashboard-v2, panel-extraction, issues, jira, filters, echarts-free, css-charts]

# Dependency graph
requires:
  - phase: 05-01
    provides: "Shell, panel-registry.js, chart-helpers.js, compose.py"
  - phase: 05-03
    provides: "Support panel reference pattern for Wave 2 panel contract"
provides:
  - "Issues panel (panels/issues.js) with full filter system, health analytics, and Asana cross-linking"
  - "Most complex panel extraction — validates the entire modular extraction strategy"
affects: [05-06-overview-panel]

# Tech tracking
tech-stack:
  added: []
  patterns: [multi-dimension-filter-state, bucket-click-to-filter, css-bar-charts, collapsible-theme-sections, asana-badge-cross-linking]

key-files:
  created:
    - ".claude/skills/customer-snapshot/templates/panels/issues.js"
  modified: []

key-decisions:
  - "Named bucket filters instead of function references for serializable filter state"
  - "Health legend items are clickable to filter by bucket (additive UX over v1)"
  - "COMPONENT_NORMALIZE and PARENT_NORMALIZE maps included even though v1 does not use them yet -- forward-compatible"
  - "All v1 issue functions consolidated into single IIFE with module-scoped filter state"

patterns-established:
  - "Bucket filter pattern: attention callouts and health legend items set _filterState.bucket, reRender() applies"
  - "reRender() partial re-render: only filter bar, attention callouts, theme chart, and theme sections refresh on filter change"
  - "data-attribute-based DOM targeting for sub-renderer elements (data-issues-health, data-issues-themes, etc.)"

requirements-completed: [DASH-09]

# Metrics
duration: 53min
completed: 2026-04-01
---

# Phase 05 Plan 05: Issues Panel Extraction Summary

**Extracted the most complex v1 panel -- Issues -- into a 1631-line standalone JS file with multi-dimension filter system, health analytics (velocity/cadence), attention callouts with click-to-filter, collapsible themed issue table, and Asana badge cross-linking**

## Performance

- **Duration:** 53 min
- **Started:** 2026-04-01T08:33:18Z
- **Completed:** 2026-04-01T09:26:55Z
- **Tasks:** 1
- **Files created:** 1

## Accomplishments

- Extracted all 12+ v1 functions (classifyIssue, getFiltered, buildFilters, filterByBucket, render, renderThemeChart, renderThemes, renderHealthBuckets, renderAttentionCallouts, renderVelocityChart, renderCadenceMetrics, addAsanaBadgesToJiraIssues) into a single self-contained IIFE
- Built multi-dimension filter system with status pills (All/Active/Waiting/Resolved/Triage), type pills (All/Bugs/Features), theme dropdown, search input with 300ms debounce, and active filter badge with clear-all
- Implemented attention callout cards (never commented, no eng 60d+, unassigned, recently opened) that are clickable to filter the issue list, with toggle-off on re-click
- Health summary bar with 4 colored segments (triage/active/stale/resolved) and clickable legend items
- Velocity chart showing opened vs resolved by month (CSS bars, last 6 months) with net change summary
- Response cadence metrics: median first comment time, % within 7 days, zero-comment count
- Collapsible theme sections with full issue tables (key, summary, type, priority, status, last activity, assignee) and expand/collapse all button
- Asana badge cross-linking from INTELLIGENCE_DATA.actions -- gold "A" badges on Jira issues that have linked Asana tasks
- FE-UPDATE count badges on issues with SE comments

## Task Commits

Each task was committed atomically:

1. **Task 1: Issues panel -- filters, theme chart, health summary, velocity, and themed issue table** - `86bf47a` (feat)

**Plan metadata:** (pending)

## Files Created/Modified

- `.claude/skills/customer-snapshot/templates/panels/issues.js` - Issues panel: 1631 lines with filter system, health analytics, attention callouts, velocity/cadence metrics, CSS theme chart, collapsible themed issue table, Asana badge cross-linking

## Decisions Made

- Used named bucket strings (e.g., 'never_commented', 'no_eng_60d') instead of function references for filter state -- enables serializable state and simpler toggle-off logic
- Made health legend items clickable to filter by health bucket -- additive UX improvement over v1 where only the health bucket bars were clickable
- Included COMPONENT_NORMALIZE and PARENT_NORMALIZE maps even though v1 does not currently use them -- they are referenced in the plan and provide forward compatibility for theme normalization
- Used data-attribute-based DOM targeting (data-issues-health, data-issues-filters, etc.) instead of getElementById -- works within the panel container scope without global ID conflicts

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 5 extraction panels now complete (actions, usage, support, slack, issues)
- Ready for Plan 06 (Overview panel) which will aggregate headline stats and attention items from all registered panels
- The Issues panel's getHeadlineStats and getAttentionItems are registered and ready for overview consumption

---
*Phase: 05-dashboard-v2-modular-folder-based-architecture*
*Completed: 2026-04-01*
