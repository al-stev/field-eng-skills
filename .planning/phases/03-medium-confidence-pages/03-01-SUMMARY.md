---
phase: 03-medium-confidence-pages
plan: 01
subsystem: database
tags: [bigquery, sql, schema-validation, cohort-analysis, team-detection, risk-scoring]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "schema_validator.py with validate_table_schema/validate_tables, queries.py with _ref() pattern and identity_resolution_cte"
provides:
  - "6 new BQ query functions for Phase 3 pages (cohort, lifecycle, team, engagement, risk)"
  - "PHASE3_SCHEMA_SPECS dict with 5 table validation specs"
  - "PHASE3_DATA_CHECKS dict with 5 data availability SQL checks"
  - "check_data_availability() function for per-account data population verification"
affects: [03-02-PLAN, 03-03-PLAN, 03-04-PLAN]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Data availability checks after schema validation (Pitfall 1 mitigation)"
    - "Risk support tickets query joins through stg_salesforce_accounts for account_id filtering"
    - "Team detection via COALESCE(org_name) with is_part_of_team as supplementary signal"

key-files:
  created: []
  modified:
    - ".claude/skills/bigquery/scripts/queries.py"
    - ".claude/skills/bigquery/tests/test_queries.py"
    - ".claude/skills/deep-analytics/scripts/schema_validator.py"
    - ".claude/skills/deep-analytics/tests/test_schema_validator.py"

key-decisions:
  - "Used Strategy B (raw activity cohort computation) as the default cohort query -- always available, unlike agg_weekly_user_retention_features"
  - "team_champions_query uses ROW_NUMBER + LEFT JOIN dim_users rather than identity_resolution_cte() for cleaner single-query pattern"
  - "risk_support_tickets_query joins through stg_salesforce_accounts (same pattern as existing support_tickets_query) for account_id filtering"
  - "check_data_availability uses maximum_bytes_billed=1GB guardrail on each count query"

patterns-established:
  - "Data availability check pattern: schema validation (column existence) then data check (per-account population)"
  - "Phase-scoped schema specs: PHASE3_SCHEMA_SPECS dict grouping all table requirements for a phase"

requirements-completed: [CHRT-01, CHRT-05, CHRT-07, TEAM-01, TEAM-04, RISK-01, RISK-03, RISK-04]

# Metrics
duration: 14min
completed: 2026-03-26
---

# Phase 03 Plan 01: Data Layer Foundation Summary

**6 BQ query functions (cohort retention, user lifecycle, team detection, team champions, engagement trend, risk support tickets) plus Phase 3 schema validation specs and per-account data availability checker**

## Performance

- **Duration:** 14 min
- **Started:** 2026-03-26T13:41:33Z
- **Completed:** 2026-03-26T13:55:44Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added 6 parameterized query functions to queries.py covering all data needs for Cohort Analysis, Team Detection, and Risk Scoring pages
- Extended schema_validator.py with PHASE3_SCHEMA_SPECS (5 tables), PHASE3_DATA_CHECKS (5 availability queries), and check_data_availability() function
- 47 new tests across both modules (34 query tests + 13 schema validator tests), all passing with zero regressions
- All queries use _ref() for table references, @account_id parameter, column-pruned SELECTs (no SELECT *)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add 6 Phase 3 query functions to queries.py** - `d61e3d3` (feat) -- TDD: tests written first, then implementation
2. **Task 2: Extend schema_validator with Phase 3 specs and data-availability check** - `48a754c` (feat)

## Files Created/Modified
- `.claude/skills/bigquery/scripts/queries.py` - 6 new query functions: cohort_retention_query, user_lifecycle_query, team_detection_query, team_champions_query, engagement_trend_query, risk_support_tickets_query
- `.claude/skills/bigquery/tests/test_queries.py` - 34 new tests across 6 test classes (56 total)
- `.claude/skills/deep-analytics/scripts/schema_validator.py` - PHASE3_SCHEMA_SPECS, PHASE3_DATA_CHECKS, check_data_availability()
- `.claude/skills/deep-analytics/tests/test_schema_validator.py` - 13 new tests across 4 test classes (18 total)

## Decisions Made
- Used Strategy B (raw ext_daily_user_event_usage cohort computation) as the default cohort query rather than attempting agg_weekly_user_retention_features first -- the fallback is always available and avoids runtime branching
- team_champions_query uses explicit CTE + ROW_NUMBER + LEFT JOIN dim_users pattern rather than identity_resolution_cte() -- cleaner for the per-team top-user use case where we need the window function before identity resolution
- risk_support_tickets_query joins through stg_salesforce_accounts (matching existing support_tickets_query pattern) since dim_helpdesk_tickets uses account_name not account_id
- check_data_availability applies maximum_bytes_billed=1GB guardrail on each count query to prevent runaway costs

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all functions return complete SQL strings, all specs are fully populated.

## Next Phase Readiness
- All 6 query functions ready for use by Phase 3 page plans (03-02 Cohort Analysis, 03-03 Team Detection, 03-04 Risk Scoring)
- Schema validation specs ready for runtime validation before page generation
- Data availability checks ready for per-account population verification (addressing team field and renewal_predictions uncertainty)

## Self-Check: PASSED

- All 4 modified files exist on disk
- Both task commits verified (d61e3d3, 48a754c)
- 16 query functions in queries.py (10 existing + 6 new)
- PHASE3_SCHEMA_SPECS and PHASE3_DATA_CHECKS present in schema_validator.py

---
*Phase: 03-medium-confidence-pages*
*Completed: 2026-03-26*
