---
phase: 03-medium-confidence-pages
plan: 04
subsystem: analytics
tags: [risk-scoring, echarts-gauge, echarts-radar, bigquery, churn-model, composite-score]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: base-template.html, generate.py pipeline, BaseTransform, queries.py with engagement_trend_query/risk_support_tickets_query/account_health_query/seat_utilization_query, schema_validator
  - phase: 03-medium-confidence-pages plan 01
    provides: schema_validator PHASE3_DATA_CHECKS, engagement_trend_query, risk_support_tickets_query
  - phase: 03-medium-confidence-pages plan 02
    provides: renderCohortAnalysis in base-template.html, _cohort_analysis_handler in generate.py
  - phase: 03-medium-confidence-pages plan 03
    provides: renderTeamDetection in base-template.html, _team_detection_handler in generate.py
provides:
  - RiskScoringTransform with composite risk formula (4-factor weighted, veto rule, behavioral fallback)
  - compute_composite_risk() pure function with RISK_WEIGHTS and CRITICAL_THRESHOLDS constants
  - _risk_scoring_handler in generate.py wired to PAGE_REGISTRY
  - renderRiskScoring in base-template.html with gauge, radar, factor table, trend, renewal card, evolution, recommendations
  - renderStalenessBanner helper function for churn model staleness/unavailability/veto banners
affects: [phase-04-low-confidence-pages]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Composite risk scoring with asymmetric weights and veto rule"
    - "renderStalenessBanner reusable banner component for data quality warnings"
    - "Multi-radar evolution overlay (current vs 3mo vs 6mo)"
    - "Risk factor normalization: each factor to 0-100 scale before weighting"

key-files:
  created:
    - .claude/skills/deep-analytics/scripts/transforms/risk_scoring.py
    - .claude/skills/deep-analytics/tests/test_risk_scoring.py
  modified:
    - .claude/skills/deep-analytics/scripts/generate.py
    - .claude/skills/deep-analytics/templates/base-template.html

key-decisions:
  - "Asymmetric risk weights: churn_model 40%, engagement 25%, utilization 20%, support 15% -- ML signal gets most weight"
  - "Veto rule floors composite at 70 when churn_probability > 0.80 -- prevents false moderate scores for high-risk accounts"
  - "Behavioral-only fallback: when renewal_predictions unavailable, weights redistribute among 3 remaining factors"
  - "Risk trend uses per-month recomputation of composite score from engagement data points"

patterns-established:
  - "renderStalenessBanner(type, data) reusable pattern for data quality banners across pages"
  - "compute_composite_risk() as standalone pure function for independent testability"
  - "Factor normalization: all inputs to 0-100 (higher=riskier) before weighted combination"

requirements-completed: [RISK-01, RISK-02, RISK-03, RISK-04, RISK-05, RISK-06, RISK-07, RISK-08]

# Metrics
duration: 6min
completed: 2026-03-26
---

# Phase 03 Plan 04: Risk Scoring Summary

**Composite churn risk scoring with 4-factor weighted formula, veto rule, ECharts gauge/radar visualization, factor breakdown table, trend line, renewal context, and AI-driven action recommendations**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-26T14:08:33Z
- **Completed:** 2026-03-26T14:14:09Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- RiskScoringTransform computes composite risk (0-100) from churn probability, engagement trend, seat utilization, and support ticket velocity with asymmetric weighting
- Veto rule automatically floors score at 70 when any critical threshold exceeded, preventing false moderate scores
- Behavioral-only fallback when ML churn model is unavailable -- weights redistribute among remaining 3 factors
- Full renderer with gauge dial (animated pointer, G/A/R color zones), risk radar (circle shape, current + historical overlays), factor breakdown table with inline bars, 6-month risk trend with colored zone markAreas, renewal context card, risk evolution multi-radar, and recommended actions list
- Staleness banner system for stale churn model (>30 days), missing churn model, and veto trigger notifications
- 34 new tests covering compute_composite_risk pure function and full transform output; 114 total tests passing with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: RiskScoringTransform with composite formula** - `9be8bdd` (test: RED), `83db237` (feat: GREEN)
2. **Task 2: Wire handler and renderer** - `02e0a51` (feat)

## Files Created/Modified

- `.claude/skills/deep-analytics/scripts/transforms/risk_scoring.py` - RiskScoringTransform class with compute_composite_risk(), RISK_WEIGHTS, CRITICAL_THRESHOLDS, risk trend computation, renewal context extraction, risk radar with historical overlays, and narrative builder
- `.claude/skills/deep-analytics/tests/test_risk_scoring.py` - 34 test functions covering composite risk function normalization/veto/fallback and full transform output shape
- `.claude/skills/deep-analytics/scripts/generate.py` - Added _risk_scoring_handler querying engagement, health, seats, tickets; updated PAGE_REGISTRY entry from placeholder to real handler
- `.claude/skills/deep-analytics/templates/base-template.html` - Added renderStalenessBanner helper, renderRiskScoring with gauge/radar/factor-table/trend/renewal-card/evolution/recommendations, updated PAGE_RENDERERS

## Decisions Made

- Asymmetric risk weights (40/25/20/15) based on research Pitfall 4 guidance -- ML churn signal gets highest weight to prevent dilution
- Veto rule threshold at 0.80 churn probability -- accounts above this are automatically HIGH risk regardless of other factors
- Risk trend uses per-month recomputation from engagement data with seat utilization overlay where available -- since historical churn model snapshots are not available, engagement serves as trend proxy
- Factor table sorted by weight descending (churn_model first) for visual importance hierarchy

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 03 (medium-confidence-pages) is now complete with all 4 plans (queries, cohort-analysis, team-detection, risk-scoring) delivered
- Risk scoring page is the most complex data integration in the suite, combining 4 data sources with fallback paths
- renderStalenessBanner pattern is available for reuse by any future page needing data quality warnings
- Ready for Phase 04 (low-confidence-pages) which covers usage-correlation, performance deep dive

## Self-Check: PASSED

All files verified present. All commit hashes verified in git log.

---
*Phase: 03-medium-confidence-pages*
*Completed: 2026-03-26*
