---
phase: 08-panel-integration
plan: 01
subsystem: dashboard
tags: [bigquery, pandas, deep-analytics, panels, echarts, customer-snapshot]

# Dependency graph
requires:
  - phase: 05-dashboard-v2-modular-folder-based-architecture
    provides: Panel registry, compose.py, shell.html, panels.yaml framework
  - phase: 03-medium-confidence-pages
    provides: 9 deep-analytics transforms (user journey, cohort, decay, velocity, team, risk, sdk, correlation, performance)
provides:
  - Analytics data pipeline in assemble.py (fetch_analytics_data for all 9 transforms)
  - Panel manifest with 15 entries across 5 groups (intelligence, usage, user-intel, product-intel, activity)
  - 9 new SVG icons in shell.html ICON_MAP
  - Cross-skill import pattern (customer-snapshot -> deep-analytics transforms via sys.path)
affects: [08-02, 08-03, 08-04, 08-05, 08-06]

# Tech tracking
tech-stack:
  added: []
  patterns: [cross-skill sys.path import for transforms, analytics.* dot-path data_key convention, _analytics_stubs pattern for graceful unavailability]

key-files:
  created: []
  modified:
    - .claude/skills/customer-snapshot/templates/assemble.py
    - .claude/skills/customer-snapshot/templates/panels.yaml
    - .claude/skills/customer-snapshot/templates/shell.html
    - .claude/skills/customer-snapshot/SKILL.md

key-decisions:
  - "Use deep-analytics venv for running assemble.py -- ensures pandas and all BQ dependencies available"
  - "Cross-skill import via sys.path.insert(0, ...) matching generate.py order -- deep-analytics/scripts then bigquery/scripts"
  - "Each transform wrapped in individual try/except so one failure does not block others"
  - "analytics.* dot-path convention in panels.yaml data_key for compose.py resolve_key() compatibility"

patterns-established:
  - "Cross-skill import: SKILLS_DIR = Path(__file__).resolve().parent.parent.parent with sys.path inserts"
  - "Analytics stubs: _analytics_stubs(reason) returns all 9 keys as {available: False, reason: ...}"
  - "Per-transform isolation: each of 9 transforms in its own try/except block"
  - "Panel sidebar groups: user-intel (journey, cohort, decay, team) and product-intel (velocity, sdk-versions, correlation, risk, performance)"

requirements-completed: [PANEL-10]

# Metrics
duration: 15min
completed: 2026-04-03
---

# Phase 8 Plan 01: Panel Integration Foundation Summary

**Analytics data pipeline wiring with 9 deep-analytics transforms in assemble.py, 15-panel manifest across 5 sidebar groups, and 9 new feather-style SVG icons in the dashboard shell**

## Performance

- **Duration:** 15 min
- **Started:** 2026-04-03T15:20:29Z
- **Completed:** 2026-04-03T15:36:13Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- assemble.py now imports and calls all 9 deep-analytics transforms (user journey, cohort analysis, engagement decay, feature velocity, team detection, risk scoring, SDK versions, usage correlation, performance) with per-transform error isolation
- panels.yaml expanded from 6 panels in 3 groups to 15 panels in 5 groups, with all 9 new analytics panels using analytics.* dot-path data_keys
- shell.html ICON_MAP extended with 9 new feather-style SVG icons matching each analytics panel
- SKILL.md pipeline updated to use deep-analytics venv so pandas and BQ dependencies are available during assembly

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend assemble.py with analytics data pipeline and update SKILL.md venv** - `fcda9c1` (feat)
2. **Task 2: Update panels.yaml manifest and shell.html ICON_MAP for all 15 panels** - `3408932` (feat)

## Files Created/Modified
- `.claude/skills/customer-snapshot/templates/assemble.py` - Added fetch_analytics_data(), _analytics_stubs(), _get_deployment_type(), cross-skill sys.path setup, analytics integration in assemble_intelligence_data(), --analytics/--no-analytics CLI flag
- `.claude/skills/customer-snapshot/templates/panels.yaml` - Expanded to 5 groups (added user-intel, product-intel) and 15 panels (added 9 analytics panels with data_key/badge_key)
- `.claude/skills/customer-snapshot/templates/shell.html` - Added 9 SVG icons to ICON_MAP (git-branch, calendar, trending-down, users, zap, package, link-2, shield, activity), updated command palette footer to 1-9
- `.claude/skills/customer-snapshot/SKILL.md` - Changed assemble.py invocation venv from customer-snapshot to deep-analytics

## Decisions Made
- Used deep-analytics venv for assemble.py invocation (ensures pandas + BQ deps available for transforms)
- Each transform wrapped in individual try/except so one failure produces a stub without blocking others
- Shared health/deployment-type query done once and reused across transforms that need it
- Badge keys chosen for decay (cold_users_count) and sdk-versions (stale_count) as the most actionable sidebar indicators

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 9 analytics panels now discoverable in the sidebar via panels.yaml
- Data pipeline wired: assemble.py produces analytics.* keys that compose.py can resolve via dot-path
- Panel JS files (plans 02-05) can now be created -- they will register with PanelRegistry and consume analytics.* data
- Overview.js updates (plan 06) can aggregate headline stats from the new analytics keys

---
*Phase: 08-panel-integration*
*Completed: 2026-04-03*
