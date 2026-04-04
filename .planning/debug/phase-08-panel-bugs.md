---
status: awaiting_human_verify
trigger: "Multiple new analytics panels broken after Phase 8 panel integration. 5 distinct issues across 9 new dashboard panels."
created: 2026-04-03T00:00:00Z
updated: 2026-04-03T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED — systematic data shape mismatch between panel JS files and transform output, plus missing dataKey in journey.js and cohort.js
test: All fixes applied and verified via syntax check + data access simulation
expecting: User confirms all panels render correctly in browser
next_action: Await human verification

## Symptoms

expected: All 9 new analytics panels render their charts and data in the v2 dashboard.
actual: (1) journey.js and cohort.js missing dataKey. (2) decay, team panels crash silently due to wrong field names. (3) cohort data is objects not arrays. (4) correlation heatmap clipped. (5) Performance shows schema_error correctly (this is expected behavior).
errors: Silent failures via try/catch in PanelRegistry.renderPanel.
reproduction: Generate dashboard for Isomorphic Labs. Open. Click each analytics panel.
started: Phase 8, first time testing with real data.

## Eliminated

- hypothesis: Performance panel has a code bug
  evidence: Performance data has available:false, reason:schema_error. Panel correctly shows schema_error empty state. This is a data issue, not a panel bug.
  timestamp: 2026-04-03

## Evidence

- timestamp: 2026-04-03
  checked: journey.js registration (line 222)
  found: Missing dataKey field — receives full INTELLIGENCE_DATA instead of analytics.journey slice
  implication: Panel gets wrong data shape, shows empty/placeholder

- timestamp: 2026-04-03
  checked: cohort.js registration (line 149)
  found: Missing dataKey field — same issue as journey.js
  implication: Panel gets wrong data shape, shows empty/placeholder

- timestamp: 2026-04-03
  checked: journey.js funnel rendering (line 442)
  found: Code reads f.stage but actual data uses f.label for funnel items
  implication: Funnel chart shows empty names

- timestamp: 2026-04-03
  checked: decay data shape vs panel expectations
  found: Panel expects cold_users/engagement_trend/decay_distribution/cold_users_count with user fields decay_pct/display_name/is_champion/days_inactive. Actual data has users/weeks/status_counts with fields ratio/trend_pct/weeks_inactive/sparkline.
  implication: Panel renders empty — all data accessors return undefined

- timestamp: 2026-04-03
  checked: cohort data shape
  found: cohort_matrix is an object {cohort_labels, cohort_sizes, period_labels, matrix} not an array. retention_curve is {periods, values} not an array. lifecycle is {months, new_users, retained, resurrected, churned} not an array.
  implication: Panel code treats them as arrays, gets no data

- timestamp: 2026-04-03
  checked: team data shape
  found: teams[].top_product_areas is undefined (actual: top_product). teams[].active_days is undefined (actual: last_active). team_activity is {team_names, events, users} not an array. team_product_heatmap is {team_names, product_areas, matrix} not an array.
  implication: Table renders but with missing data, charts fail

- timestamp: 2026-04-03
  checked: correlation heatmap grid config
  found: grid top:40 with xAxis position:'top' and rotate:45 for 11 long product area names — insufficient space
  implication: Rotated labels clip above chart container

- timestamp: 2026-04-03
  checked: risk data shape
  found: All expected fields present and matching
  implication: Risk panel works correctly

- timestamp: 2026-04-03
  checked: velocity data shape
  found: All expected fields present and matching
  implication: Velocity panel works correctly

- timestamp: 2026-04-03
  checked: sdk_versions data shape
  found: All expected fields present; 13 versions in legend cause crowding
  implication: Added scrollable legend and adjusted spacing

- timestamp: 2026-04-03
  checked: All fixes applied — syntax check + data access simulation
  found: All 6 files pass node --check. Simulated data normalization produces correct output for cohort (18 matrix rows, retention curve 4 points), decay (159 cold/cooling users), team (26 teams with parallel array normalization).
  implication: Fixes are correct

## Resolution

root_cause: Panel JS files were written with assumed data shapes that don't match the actual transform output. Two categories of bugs — (A) missing dataKey in registration for journey.js and cohort.js causing them to receive full INTELLIGENCE_DATA instead of their analytics slice, and (B) data shape mismatches where panels expect arrays but transforms produce parallel-array objects, or field names differ (cold_users vs users, f.stage vs f.label, top_product_areas vs top_product, active_days vs last_active).
fix: |
  1. journey.js: Added dataKey:'analytics.journey', group, label, icon. Fixed funnel f.stage -> f.label||f.stage.
  2. cohort.js: Added dataKey:'analytics.cohort', group, label, icon. Added normalization layer to convert object-based cohort_matrix/retention_curve/lifecycle to array format expected by rendering code. Fixed getHeadlineStats/getAttentionItems to handle both data shapes.
  3. decay.js: Rewrote data access to use data.users (not cold_users), compute decay_pct from ratio field, use weeks_inactive, status_counts for distribution chart. Graceful fallback when engagement_trend is unavailable.
  4. team.js: Fixed top_product_areas -> top_product fallback, active_days -> last_active, normalized team_activity from parallel arrays to chart-ready format, normalized team_product_heatmap from {team_names,product_areas,matrix} to ECharts-ready format.
  5. correlation.js: Increased grid.top from 40 to 100 for rotated labels, increased container height from 400 to 500px.
  6. sdk-versions.js: Added type:'scroll' to legend for 13+ versions, increased chart container height and adjusted grid/legend spacing for dataZoom compatibility.
verification: Syntax check passed for all 6 files. Data access simulation confirms correct field resolution. Browser verification pending.
files_changed:
  - .claude/skills/customer-snapshot/templates/panels/journey.js
  - .claude/skills/customer-snapshot/templates/panels/cohort.js
  - .claude/skills/customer-snapshot/templates/panels/decay.js
  - .claude/skills/customer-snapshot/templates/panels/team.js
  - .claude/skills/customer-snapshot/templates/panels/correlation.js
  - .claude/skills/customer-snapshot/templates/panels/sdk-versions.js
