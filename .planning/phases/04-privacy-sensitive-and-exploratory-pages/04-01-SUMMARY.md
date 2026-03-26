---
phase: 04-privacy-sensitive-and-exploratory-pages
plan: 01
subsystem: database
tags: [bigquery, sql, schema-validation, cross-account, performance, product-areas]

# Dependency graph
requires:
  - phase: 01-foundation-and-template-system
    provides: "queries.py query factory with _ref() and identity_resolution_cte(), schema_validator.py with validate_table_schema()"
  - phase: 03-medium-confidence-pages
    provides: "PHASE3_SCHEMA_SPECS/DATA_CHECKS pattern, team_detection_query, engagement_trend_query"
provides:
  - "PRODUCT_AREA_CASE shared constant preventing drift between single-account and cross-account queries"
  - "cross_account_product_areas_query() for Usage Correlation page co-occurrence matrix"
  - "cross_account_arr_breadth_query() for peer benchmarking scatter/percentiles"
  - "performance_query() for Performance Deep Dive gauge and slow_* breakdown"
  - "latency_distribution_query() for chart load latency histogram"
  - "slow_chart_users_query() for per-user slow chart load table"
  - "PHASE4_SCHEMA_SPECS for go/no-go gate on performance tables"
  - "PHASE4_DATA_CHECKS for per-account data availability verification"
affects: [04-02-PLAN, 04-03-PLAN]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cross-account queries (no @account_id) for privacy-sensitive aggregation"
    - "PRODUCT_AREA_CASE shared SQL constant to prevent mapping drift"
    - "PHASE4_SCHEMA_SPECS/DATA_CHECKS pattern extending Phase 3 validation approach"

key-files:
  created: []
  modified:
    - ".claude/skills/bigquery/scripts/queries.py"
    - ".claude/skills/bigquery/tests/test_queries.py"
    - ".claude/skills/deep-analytics/scripts/schema_validator.py"
    - ".claude/skills/deep-analytics/tests/test_schema_validator.py"

key-decisions:
  - "Used renewal_arr__c and cs_tier column names from existing account_health_query() instead of plan-specified arr_c/cs_tier_c/account_id_c which were incorrect"
  - "PRODUCT_AREA_CASE used 5 times in queries.py (1 definition + 4 usages across product_areas_query, cross_account_product_areas_query, cross_account_arr_breadth_query)"

patterns-established:
  - "Cross-account query pattern: no @account_id parameter, account_id returned for transform-layer aggregation but stripped before HTML output"
  - "Shared SQL constant pattern: PRODUCT_AREA_CASE extracted to prevent drift between queries"

requirements-completed: [CORR-01, CORR-02, CORR-06, CORR-07, CORR-08, PERF-01, PERF-02, PERF-03, PERF-04, PERF-06]

# Metrics
duration: 20min
completed: 2026-03-26
---

# Phase 04 Plan 01: Phase 4 BQ Queries and Schema Validation Summary

**5 new BQ query functions (cross-account product areas, ARR breadth, performance, latency, slow charts) with PRODUCT_AREA_CASE shared constant and Phase 4 schema validation specs**

## Performance

- **Duration:** 20 min
- **Started:** 2026-03-26T14:15:22Z
- **Completed:** 2026-03-26T14:36:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Extracted PRODUCT_AREA_CASE as shared constant eliminating CASE statement duplication risk (Pitfall 4 from research)
- Added first cross-account queries in the project (no @account_id) for Usage Correlation page data layer
- Added performance table queries (fct_application_performance, fct_onscreen_loader_latencies, agg_daily_team_members_slow_chart_loads) for Performance Deep Dive
- Extended schema validator with PHASE4_SCHEMA_SPECS (3 tables) and PHASE4_DATA_CHECKS (3 per-account checks) for go/no-go gate
- 96 queries.py tests + 29 schema_validator tests all pass with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add 5 Phase 4 query functions and PRODUCT_AREA_CASE constant** (TDD)
   - `0bedc97` (test) - RED: failing tests for all new functions
   - `a431fc2` (feat) - GREEN: implement PRODUCT_AREA_CASE, refactor product_areas_query, add 5 new queries
2. **Task 2: Extend schema_validator with Phase 4 specs and data-availability checks** (TDD)
   - `55cf052` (test) - RED: failing tests for PHASE4_SCHEMA_SPECS and PHASE4_DATA_CHECKS
   - `bd3486a` (feat) - GREEN: implement PHASE4_SCHEMA_SPECS and PHASE4_DATA_CHECKS

## Files Created/Modified
- `.claude/skills/bigquery/scripts/queries.py` - Added PRODUCT_AREA_CASE constant, refactored product_areas_query(), added 5 new query functions
- `.claude/skills/bigquery/tests/test_queries.py` - Added 40 new tests (7 test classes) for Phase 4 queries
- `.claude/skills/deep-analytics/scripts/schema_validator.py` - Added PHASE4_SCHEMA_SPECS (3 tables) and PHASE4_DATA_CHECKS (3 checks)
- `.claude/skills/deep-analytics/tests/test_schema_validator.py` - Added 11 new tests (2 test classes) for Phase 4 schema specs

## Decisions Made
- Used `renewal_arr__c` and `cs_tier` column names from existing `account_health_query()` instead of plan-specified `arr_c`/`cs_tier_c`/`account_id_c` which were incorrect for `stg_salesforce_accounts`
- `cross_account_arr_breadth_query()` uses `COUNT(DISTINCT CASE...END)` for product_breadth computation with PRODUCT_AREA_CASE inlined in the COUNT expression

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected column names in cross_account_arr_breadth_query()**
- **Found during:** Task 1 (query implementation)
- **Issue:** Plan specified `arr_c`, `cs_tier_c`, and `account_id_c` for stg_salesforce_accounts columns, but existing account_health_query() uses `renewal_arr__c`, `cs_tier`, and `account_id`
- **Fix:** Used the correct column names matching the established pattern in account_health_query()
- **Files modified:** .claude/skills/bigquery/scripts/queries.py
- **Verification:** All tests pass, column names consistent with existing queries
- **Committed in:** a431fc2

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Column name correction necessary for correctness. No scope creep.

## Issues Encountered
- Worktree was behind main repo HEAD (missing Phase 1-3 work). Fast-forward merged to bring worktree up to date before starting.

## Known Stubs
None -- all queries return complete SQL, no placeholder data.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 5 query functions ready for Phase 4 Plan 02 (Usage Correlation transform + handler + renderer)
- PHASE4_SCHEMA_SPECS ready for go/no-go gate in Phase 4 Plan 03 (Performance Deep Dive)
- PHASE4_DATA_CHECKS ready for per-account data availability verification

## Self-Check: PASSED

All files found: queries.py, test_queries.py, schema_validator.py, test_schema_validator.py, 04-01-SUMMARY.md
All commits found: 0bedc97, a431fc2, 55cf052, bd3486a

---
*Phase: 04-privacy-sensitive-and-exploratory-pages*
*Completed: 2026-03-26*
