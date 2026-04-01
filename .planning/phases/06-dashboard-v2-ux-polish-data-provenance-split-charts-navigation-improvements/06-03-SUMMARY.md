---
phase: 06-dashboard-v2-ux-polish-data-provenance-split-charts-navigation-improvements
plan: 03
subsystem: ui
tags: [echarts, bigquery, clipboard-api, toast, compose, dashboard-v2]

# Dependency graph
requires:
  - phase: 06-01
    provides: split radar charts, time period labels, breadcrumb navigation
  - phase: 06-02
    provides: support panel charts, overview panel, chart clipping fixes
  - phase: 05
    provides: v2 folder-based dashboard architecture with compose.py
provides:
  - BQ SQL copy buttons on every data section for query provenance
  - Toast notification system in shell.html
  - bq_queries dict in usage.py JSON output
  - SKILL.md pipeline updated to produce v2 dashboards via compose.py
affects: [customer-snapshot, bigquery, usage-report]

# Tech tracking
tech-stack:
  added: []
  patterns: [sql-copy-btn pattern with data-query-key attribute, showToast global function, bq_queries passthrough from Python to JS]

key-files:
  created: []
  modified:
    - .claude/skills/bigquery/scripts/usage.py
    - .claude/skills/customer-snapshot/templates/shell.html
    - .claude/skills/customer-snapshot/templates/panels/usage.js
    - .claude/skills/customer-snapshot/templates/panels/support.js
    - .claude/skills/customer-snapshot/SKILL.md

key-decisions:
  - "SQL icon uses database cylinder SVG for recognizable BQ association"
  - "bq_queries gated behind include_queries=True to avoid bloating non-dashboard JSON output"
  - "v1 intelligence-dashboard.html preserved as fallback reference, not deleted"
  - "ECharts noted as locally bundled in v2 (not CDN) in SKILL.md Visualization section"

patterns-established:
  - "SQL copy button pattern: sqlCopyBtn(queryKey) helper + data-query-key attribute + clipboard API"
  - "Toast notification: showToast() global in shell.html, called by panel click handlers"

requirements-completed: [UX-01, UX-07]

# Metrics
duration: 2min
completed: 2026-04-01
---

# Phase 06 Plan 03: Data Provenance & V2 Pipeline Summary

**BQ SQL copy buttons on all data sections with toast notifications, plus SKILL.md pipeline rewired for v2 folder-based dashboard output via compose.py**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-01T12:37:49Z
- **Completed:** 2026-04-01T12:40:02Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Every data section (seat utilization, product adoption, Weave, tracked hours, account health, support tickets) has a SQL icon that copies the underlying BQ query to clipboard
- Toast notification system ("Copied!") wired into shell.html with CSS transitions
- SKILL.md Step 8 now instructs agents to use compose.py for v2 folder-based dashboard output instead of the v1 monolithic HTML

## Task Commits

Each task was committed atomically:

1. **Task 1: Embed BQ query strings in usage.py output and add SQL buttons + toast to panels** - `4159c01` (feat)
2. **Task 2: Wire compose.py into SKILL.md for v2 dashboard output** - `ef3e889` (docs)

## Files Created/Modified
- `.claude/skills/bigquery/scripts/usage.py` - Added include_queries param and bq_queries dict to build_usage_json output
- `.claude/skills/customer-snapshot/templates/shell.html` - Added .toast CSS, toast HTML element, showToast() global function
- `.claude/skills/customer-snapshot/templates/panels/usage.js` - Added .sql-copy-btn CSS, SQL_ICON svg, sqlCopyBtn() helper, SQL buttons on 6 chart labels, click handlers with clipboard API
- `.claude/skills/customer-snapshot/templates/panels/support.js` - Added .sql-copy-btn CSS, SQL_ICON svg, sqlCopyBtn() helper, SQL button on support section header, click handler
- `.claude/skills/customer-snapshot/SKILL.md` - Rewired Step 8 for compose.py, updated description/visualization/anti-patterns for v2

## Decisions Made
- SQL icon uses a database cylinder SVG (stroke-only, 14x14px) -- recognizable as "database/query" without being heavy
- bq_queries parameter is opt-in (include_queries=True) so existing callers of build_usage_json are unaffected
- v1 intelligence-dashboard.html preserved as fallback reference in SKILL.md language
- Removed "Chart.js or any external JS charting library" from anti-patterns since ECharts IS used; replaced with v1 monolithic generation anti-pattern

## Deviations from Plan

None - plan executed exactly as written. Task 1 implementation was already present from parallel execution; this plan committed and verified the work.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all data sources wired end-to-end.

## Next Phase Readiness
- Phase 06 is now complete (all 3 plans executed)
- v2 dashboard has full UX polish: split radar charts, time period labels, breadcrumb navigation, support panel charts, SQL copy buttons, toast notifications
- SKILL.md pipeline produces v2 folder-based dashboards via compose.py

## Self-Check: PASSED

All 5 modified files verified present. Both commit hashes (4159c01, ef3e889) verified in git log.

---
*Phase: 06-dashboard-v2-ux-polish-data-provenance-split-charts-navigation-improvements*
*Completed: 2026-04-01*
