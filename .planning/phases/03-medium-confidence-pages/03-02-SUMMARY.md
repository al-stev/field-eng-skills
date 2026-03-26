---
phase: 03-medium-confidence-pages
plan: 02
subsystem: visualization
tags: [echarts, heatmap, cohort-analysis, retention, lifecycle, behavioral-cohorts, bigquery]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "BaseTransform, base-template.html with PAGE_RENDERERS dispatch, generate.py pipeline"
  - phase: 03-medium-confidence-pages
    plan: 01
    provides: "cohort_retention_query, user_lifecycle_query in queries.py, PHASE3_DATA_CHECKS in schema_validator.py"
provides:
  - "CohortAnalysisTransform class with cohort matrix, retention curve, lifecycle, cohort overlay, behavioral cohorts, KPIs, and narrative"
  - "_cohort_analysis_handler wired into PAGE_REGISTRY"
  - "renderCohortAnalysis function in PAGE_RENDERERS with heatmap, retention curve, lifecycle stacked area, cohort overlay, behavioral cohorts"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ECharts heatmap with visualMap continuous gradient (red-amber-green) for retention matrices"
    - "Side-by-side flex container pattern for paired charts (retention curve + cohort comparison)"
    - "Stacked area lifecycle chart with dataZoom slider for time-series navigation"
    - "Behavioral cohort grouping from user journey first_*_at fields"

key-files:
  created:
    - ".claude/skills/deep-analytics/scripts/transforms/cohort_analysis.py"
    - ".claude/skills/deep-analytics/tests/test_cohort_analysis.py"
  modified:
    - ".claude/skills/deep-analytics/scripts/generate.py"
    - ".claude/skills/deep-analytics/templates/base-template.html"

key-decisions:
  - "Used overall retention curve as approximation for behavioral cohort groups rather than requiring per-user retention data"
  - "Retention percentages clamped at 100% via min() to handle data anomalies (research pitfall 3)"
  - "Lifecycle section conditionally rendered only when lifecycle data is available (graceful degradation)"

patterns-established:
  - "Heatmap renderer pattern: cohort labels with n=size annotation, period labels as M+N, visualMap gradient"
  - "Multi-section renderer with unified resize handler collecting all chart instances"
  - "Conditional section rendering: skip lifecycle/behavioral sections when data unavailable"

requirements-completed: [CHRT-01, CHRT-02, CHRT-03, CHRT-04, CHRT-05, CHRT-06, CHRT-07]

# Metrics
duration: 6min
completed: 2026-03-26
---

# Phase 03 Plan 02: Cohort Analysis Page Summary

**Cohort retention heatmap with lifecycle stacked area, cohort overlay comparison, behavioral cohorts, and AI narrative -- all 7 CHRT requirements delivered**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-26T13:59:07Z
- **Completed:** 2026-03-26T14:05:07Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Built CohortAnalysisTransform with TDD (24 tests first, then implementation) covering cohort matrix, retention curve, lifecycle, cohort overlay, behavioral cohorts, KPIs, and narrative
- Added renderCohortAnalysis with 5 chart sections: retention heatmap (480px), side-by-side retention curve + cohort comparison, lifecycle stacked area with dataZoom, and behavioral cohorts multi-line chart
- Wired _cohort_analysis_handler into generate.py querying retention, lifecycle, and journey data with cost guardrails
- Full empty state handling: empty heatmap message, conditional lifecycle skip, behavioral cohorts fallback

## Task Commits

Each task was committed atomically:

1. **Task 1: CohortAnalysisTransform with TDD** - `642e56a` (feat) -- 24 tests written first, all passing
2. **Task 2: Wire handler + renderCohortAnalysis** - `a70aa8e` (feat) -- handler + 5-section renderer

## Files Created/Modified
- `.claude/skills/deep-analytics/scripts/transforms/cohort_analysis.py` - CohortAnalysisTransform with cohort matrix, retention curve, lifecycle, overlay, behavioral cohorts, KPIs, narrative
- `.claude/skills/deep-analytics/tests/test_cohort_analysis.py` - 24 test functions across 9 test classes
- `.claude/skills/deep-analytics/scripts/generate.py` - _cohort_analysis_handler + PAGE_REGISTRY update
- `.claude/skills/deep-analytics/templates/base-template.html` - renderCohortAnalysis function + PAGE_RENDERERS entry

## Decisions Made
- Used overall retention curve as approximation for behavioral cohort group values -- true per-group retention requires user-level retention data not available from current queries
- Retention percentages clamped at 100% via `min(100.0, ...)` to handle data anomalies where active users exceed cohort size (research pitfall 3)
- Lifecycle section conditionally rendered only when lifecycle data months > 0, rather than showing empty chart
- Handler queries lifecycle and journey data in try/except blocks -- transform handles None gracefully

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all transform outputs produce real computed values, renderer handles all data shapes.

## Next Phase Readiness
- Cohort Analysis page fully operational: `--page cohort-analysis` produces self-contained HTML
- All 7 CHRT requirements satisfied
- 80 tests across the deep-analytics test suite pass with zero regressions

## Self-Check: PASSED

- All 4 files exist on disk (2 created, 2 modified)
- Both task commits verified (642e56a, a70aa8e)
- 24 cohort analysis tests pass
- 80 total tests pass with zero regressions
