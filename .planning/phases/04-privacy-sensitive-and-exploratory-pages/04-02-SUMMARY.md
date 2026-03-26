---
phase: 04-privacy-sensitive-and-exploratory-pages
plan: 02
subsystem: analytics
tags: [bigquery, echarts, privacy, cross-account, heatmap, scatter, correlation]

# Dependency graph
requires:
  - phase: 04-01
    provides: "cross_account_product_areas_query, cross_account_arr_breadth_query, PHASE4_SCHEMA_SPECS"
  - phase: 01
    provides: "BaseTransform, base-template.html, generate.py pipeline, PAGE_RENDERERS pattern"
provides:
  - "UsageCorrelationTransform with co-occurrence matrix, privacy enforcement, peer benchmarking"
  - "_usage_correlation_handler in generate.py PAGE_REGISTRY"
  - "renderUsageCorrelation in base-template.html PAGE_RENDERERS"
  - "Privacy badge component (SE-INTERNAL ONLY) reusable for future internal-only pages"
affects: [04-03, verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cross-account transform pattern: queries without @account_id, 100GB bytes limit"
    - "Privacy enforcement: SFDC ID regex scan on serialized JSON output"
    - "Cohort suppression: MIN_COHORT_SIZE=10 filtering on co-occurrence matrix entries"
    - "Non-dismissible privacy badge with red-dim background and SE-INTERNAL ONLY label"

key-files:
  created:
    - ".claude/skills/deep-analytics/scripts/transforms/usage_correlation.py"
    - ".claude/skills/deep-analytics/tests/test_usage_correlation.py"
  modified:
    - ".claude/skills/deep-analytics/scripts/generate.py"
    - ".claude/skills/deep-analytics/templates/base-template.html"

key-decisions:
  - "Retention proxy: used median event mass as proxy for recent activity (true contract retention not computable from BQ activity data alone)"
  - "Cross-account queries use 100GB maximum_bytes_billed limit vs 50GB for single-account"
  - "Privacy enforcement in transform layer (not query layer) — query returns account_id for grouping, transform strips before output"

patterns-established:
  - "Cross-account handler pattern: omit account_id kwarg in run_query() for full-table scans"
  - "Privacy badge: inline JS creation with exact UI-SPEC styling, data-print='visible' attribute"
  - "Expansion signals: compare entitlement fields to current usage, graceful empty list when entitlements missing"

requirements-completed: [CORR-01, CORR-02, CORR-03, CORR-04, CORR-05, CORR-06, CORR-07, CORR-08]

# Metrics
duration: 5min
completed: 2026-03-26
---

# Phase 4 Plan 2: Usage Correlation Summary

**Cross-account product co-occurrence heatmap with privacy-enforced peer benchmarking, next-best-action recommendations, and ARR-usage scatter**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-26T14:40:41Z
- **Completed:** 2026-03-26T14:45:59Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- UsageCorrelationTransform with full co-occurrence matrix, retention overlay, cohort suppression (MIN_COHORT_SIZE=10), and SFDC ID privacy scan
- Privacy badge rendering as non-dismissible first element in chart section with exact UI-SPEC styling
- Handler wired in generate.py with cross-account queries (no account_id parameter, 100GB limit) and single-account product areas + health queries
- HTML renderer with all 6 sections: heatmap, account positioning, peer benchmarking, NBA recommendations, expansion signals, ARR scatter
- 11 comprehensive tests covering privacy enforcement, cohort suppression, sort ordering, graceful degradation, and narrative structure

## Task Commits

Each task was committed atomically:

1. **Task 1: UsageCorrelationTransform (TDD)** - `29a886e` (test: RED), `74d30f8` (feat: GREEN)
2. **Task 2: Handler + HTML renderer** - `23aaff9` (feat)

## Files Created/Modified
- `.claude/skills/deep-analytics/scripts/transforms/usage_correlation.py` - UsageCorrelationTransform with co-occurrence matrix, privacy enforcement, peer benchmarking, NBA, expansion signals
- `.claude/skills/deep-analytics/tests/test_usage_correlation.py` - 11 tests covering all transform behaviors
- `.claude/skills/deep-analytics/scripts/generate.py` - Added _usage_correlation_handler and registered in PAGE_REGISTRY
- `.claude/skills/deep-analytics/templates/base-template.html` - Added renderUsageCorrelation with privacy badge, heatmap, scatter, and all 6 sections

## Decisions Made
- Used median event mass as proxy for "retained" accounts (true contract retention not computable from activity data alone)
- Cross-account queries use 100GB maximum_bytes_billed (2x normal) since they scan all accounts
- Privacy enforcement implemented in transform layer, not query layer — account_id needed for grouping/aggregation but stripped before output
- Expansion signals gracefully return empty list when entitlement data missing (covers accounts without SFDC entitlement fields)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None - all data paths are wired to real transform output. The cross-account queries will execute against real BQ data when run with `--page usage-correlation`.

## Next Phase Readiness
- Usage Correlation page complete — 8 of 9 deep analytics pages now implemented
- Performance Deep Dive (04-03) is the last remaining page with its go/no-go gate on BQ table accessibility
- The privacy badge pattern established here can be reused if future pages need SE-internal-only marking

## Self-Check: PASSED

All 4 files verified on disk. All 3 commit hashes found in git history.

---
*Phase: 04-privacy-sensitive-and-exploratory-pages*
*Completed: 2026-03-26*
