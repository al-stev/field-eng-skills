# Phase 8: Panel Integration - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Integrate 9 deep-analytics page types as dashboard panels following the v2 panel contract. Each panel implements PanelRegistry.register() with render(), getHeadlineStats(), getAttentionItems(). The dashboard goes from 6 panels to 15, giving SEs a single-pane view of customer health across operational AND analytical dimensions.

</domain>

<decisions>
## Implementation Decisions

### Data pipeline wiring
- **D-01:** Extend assemble.py to call all 9 deep-analytics transforms inline, merging results into INTELLIGENCE_DATA. Single skill boundary, single BQ client session. No new orchestration step or separate invocations.
- **D-02:** Always fetch analytics data if the customer has sfdc_account_id in customers.yaml. No opt-in flag needed. Panels with no data get graceful empty states.
- **D-03:** assemble.py imports transforms from deep-analytics/scripts/transforms/ directly (cross-skill import). Keeps transforms in one place with no duplication.
- **D-04:** Analytics data nested under `analytics.*` keys in INTELLIGENCE_DATA (e.g., `data.analytics.cohort`, `data.analytics.risk`, `data.analytics.journey`). Panel data_key in panels.yaml uses dot-path like `analytics.cohort`.

### Panel density
- **D-05:** Port ALL charts and visualizations from each standalone analytics page into its panel JS file. The dashboard IS the analytics tool — no separate standalone pages needed for analytics that are now panels.
- **D-06:** Retire standalone deep-analytics HTML page generation for the 9 page types that become panels. The deep-analytics skill's generate.py and transforms remain available but standalone page output is superseded by the dashboard.

### Sidebar organization
- **D-07:** Two new sidebar groups for analytics panels:
  - **User Intelligence**: User Journey, Cohort Analysis, Engagement Decay, Team Detection
  - **Product Intelligence**: Feature Velocity, SDK Versions, Usage Correlation, Risk Scoring, Performance
- **D-08:** Existing 3 groups (Intelligence, Usage & Analytics, Activity & Comms) remain unchanged. Seats & Adoption stays in its current group.

### Empty state strategy
- **D-09:** Panels always appear in the sidebar regardless of data availability. When data is unavailable, the panel body shows a styled empty state explaining WHY (e.g., "Team data not available for dedicated cloud deployments"). Consistent navigation — SE always sees all 15 panels.
- **D-10:** For partially available data, show what's available and render "Data not available" placeholders for missing sections. This matches the existing transform behavior from standalone pages.

### Claude's Discretion
- Panel order within each new sidebar group
- Specific icon choices for each new panel in panels.yaml
- Whether to extract common CSS patterns shared across analytics panels into chart-helpers.js or keep them panel-local
- The 800-line limit per panel — Claude decides if any pages need chart trimming to meet it
- Badge key choices for sidebar notification indicators on analytics panels

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Dashboard V2 architecture
- `.claude/skills/customer-snapshot/templates/lib/panel-registry.js` — Panel contract: register(), render(), getHeadlineStats(), getAttentionItems(), dataKey resolution, CSS scoping
- `.claude/skills/customer-snapshot/templates/panels.yaml` — Panel manifest with groups, data_key, badge_key, order
- `.claude/skills/customer-snapshot/templates/compose.py` — Dashboard composition pipeline: panels.yaml → active panel detection → folder output
- `.claude/skills/customer-snapshot/templates/shell.html` — Dashboard shell with sidebar, design tokens, panel rendering loop
- `.claude/skills/customer-snapshot/templates/lib/chart-helpers.js` — Shared ECharts helpers (createChart, theme, resize)

### Existing panel examples (follow these patterns)
- `.claude/skills/customer-snapshot/templates/panels/support.js` — Best reference: 5 ECharts charts, PANEL_CSS, headline stats, attention items
- `.claude/skills/customer-snapshot/templates/panels/usage.js` — BQ-derived panel with KPI row, 4 charts, account health grid
- `.claude/skills/customer-snapshot/templates/panels/overview.js` — Aggregates stats from all panels

### Data pipeline
- `.claude/skills/customer-snapshot/templates/assemble.py` — Deterministic data assembler. This is where analytics transforms will be called.
- `.claude/skills/customer-snapshot/SKILL.md` — Customer snapshot skill entry point documentation

### Deep analytics transforms (to be imported by assemble.py)
- `.claude/skills/deep-analytics/scripts/generate.py` — Page registry + handler functions showing BQ query → transform → data dict pipeline
- `.claude/skills/deep-analytics/scripts/transforms/user_journey.py` — UserJourneyTransform
- `.claude/skills/deep-analytics/scripts/transforms/cohort_analysis.py` — CohortAnalysisTransform
- `.claude/skills/deep-analytics/scripts/transforms/engagement_decay.py` — EngagementDecayTransform
- `.claude/skills/deep-analytics/scripts/transforms/feature_velocity.py` — FeatureVelocityTransform
- `.claude/skills/deep-analytics/scripts/transforms/team_detection.py` — TeamDetectionTransform
- `.claude/skills/deep-analytics/scripts/transforms/risk_scoring.py` — RiskScoringTransform
- `.claude/skills/deep-analytics/scripts/transforms/sdk_versions.py` — SdkVersionsTransform
- `.claude/skills/deep-analytics/scripts/transforms/usage_correlation.py` — UsageCorrelationTransform
- `.claude/skills/deep-analytics/scripts/transforms/performance.py` — PerformanceTransform

### BQ queries (used by transforms)
- `.claude/skills/bigquery/scripts/queries.py` — All BQ query functions (product_areas_query, user_journey_query, etc.)
- `.claude/skills/bigquery/scripts/bq_client.py` — BQ client, run_query(), get_sfdc_account_id()
- `.claude/skills/deep-analytics/scripts/schema_validator.py` — Schema validation and data availability checks

### Deep analytics standalone template (for chart conversion reference)
- `.claude/skills/deep-analytics/templates/base-template.html` — Standalone page template showing chart layouts, CSS, and ECharts configs to port into panel JS

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **PanelRegistry**: Full panel contract with register(), renderPanel(), injectCSS(), dataKey resolution — all new panels follow this
- **ChartHelpers**: createChart() wrapper around echarts.init() with theme and resize handling — all ECharts in panels must use this
- **Design tokens**: CSS custom properties in shell.html (:root variables) — all panel CSS uses these, no hardcoded colors
- **9 Transform classes**: Each already produces a complete data dict with KPIs, chart data, and narrative — these become the data source for panels
- **generate.py handler functions**: Show the exact BQ query → transform pipeline for each page type — assemble.py will replicate this pattern
- **schema_validator.py**: PHASE3_DATA_CHECKS and PHASE4_DATA_CHECKS dicts for runtime data availability detection

### Established Patterns
- **Panel IIFE pattern**: `(function() { 'use strict'; ... PanelRegistry.register({...}); })()` — no ES modules (file:// CORS)
- **PANEL_CSS string**: CSS injected via PanelRegistry.injectCSS() with auto-scoping to #panel-{id}
- **isDark() helper**: Duplicated per panel for dark/light mode detection — pattern to follow
- **compose.py data gating**: `resolve_key(data, panel.data_key)` determines if panel has data → included or skipped
- **Existing data flow**: assemble.py → JSON → compose.py → data.js + panel JS files → dashboard folder

### Integration Points
- **assemble.py**: Add analytics data fetching (import transforms, call handlers, merge under analytics.* keys)
- **panels.yaml**: Add 9 new panel entries with group, data_key, badge_key, order across 2 new groups
- **compose.py**: Should work as-is if panels.yaml is updated (data_key resolution already handles nested paths)
- **overview.js**: Must aggregate getHeadlineStats() and getAttentionItems() from all 15 panels (currently handles 6)
- **shell.html**: May need the 2 new group IDs added if groups are hardcoded (check if dynamic from panels.yaml)

</code_context>

<specifics>
## Specific Ideas

- Support panel (support.js) is the best reference for new panel complexity — 5 ECharts charts, ~700 lines, full panel contract
- The existing transforms already handle partial data gracefully (e.g., RiskScoringTransform returns scores even without renewal_predictions) — this behavior should carry through to panels
- Team detection on dedicated cloud is a known data gap (anonymized telemetry, no team/entity/username) — panel empty state should explain this specifically
- Analytics panels replace standalone pages — after this phase, `/customer-snapshot` is the single entry point for all intelligence

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-panel-integration*
*Context gathered: 2026-04-03*
