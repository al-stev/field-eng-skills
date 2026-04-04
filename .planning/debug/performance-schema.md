---
status: awaiting_human_verify
trigger: "Performance deep-analytics transform returns available: false, reason: schema_error for Isomorphic Labs"
created: 2026-04-03T00:00:00Z
updated: 2026-04-03T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED -- All 3 performance tables have completely different schemas from what the code expects. Column names are wrong across the board.
test: BQ dry-run queries returned actual schemas
expecting: N/A -- root cause confirmed
next_action: Fix schema_validator.py PHASE4_SCHEMA_SPECS, queries.py performance queries, and performance.py transform to match real BQ schemas

## Symptoms

expected: Performance panel shows performance index gauge, latency breakdown, error metrics for Isomorphic Labs
actual: Performance transform returns {available: false, reason: 'schema_error'} -- the schema_validator gate is rejecting the table
errors: Schema validation failure before any data query runs
reproduction: Run `uv run --project .claude/skills/deep-analytics python .claude/skills/deep-analytics/scripts/generate.py --customer "Isomorphic Labs" --page performance --dry-run`
started: User says performance data has always been there in BQ

## Eliminated

## Evidence

- timestamp: 2026-04-03T00:01:00Z
  checked: schema_validator.py PHASE4_SCHEMA_SPECS
  found: Expects fct_application_performance to have columns: account_id, date_day, application_performance_index, slow_charts, slow_project_search, slow_artifact_creating, slow_run_sidebar, slow_workspace_settings, users_facing_errors_ct, error_count
  implication: If ANY of these 10 columns is missing or renamed, schema validation fails and returns schema_error

- timestamp: 2026-04-03T00:01:30Z
  checked: generate.py _performance_handler (lines 275-351)
  found: Gate 1 validates ONLY fct_application_performance schema. If schema fails, immediately returns descoped_result("schema_error") -- never queries data.
  implication: The failure happens at schema validation, not data availability. The table exists but columns don't match.

- timestamp: 2026-04-03T00:02:00Z
  checked: performance_query() in queries.py
  found: Query SELECTs the same column names as schema spec -- slow_charts, slow_project_search, slow_artifact_creating, slow_run_sidebar, slow_workspace_settings, users_facing_errors_ct, error_count
  implication: If schema spec is wrong, the query is wrong too -- both need fixing

- timestamp: 2026-04-03T00:03:00Z
  checked: BQ dry-run query on all 3 performance tables
  found: |
    TABLE 1: fct_application_performance (44 columns)
    - NO date_day column (table has no date column at all -- rows are per team_name/entity, not per day)
    - NO slow_charts -- real name is slow_charts_user_ct
    - NO slow_project_search -- real name is slow_project_search_user_ct
    - NO slow_artifact_creating -- real name is slow_artifact_creating_user_ct
    - NO slow_run_sidebar -- column does not exist at all
    - NO slow_workspace_settings -- column does not exist at all
    - HAS users_facing_errors_ct (correct)
    - HAS error_count (correct)
    - HAS application_performance_index (correct)
    - HAS account_id (correct)
    - Additional slow_* columns: slow_adag_lineage_user_ct, slow_artifact_manifests_user_ct, slow_project_page_user_ct, slow_report_metadata_user_ct, slow_run_groups_query_user_ct, slow_runs_query_user_ct
    - Has team_name, organization_name, entity_id -- this is a per-team/entity breakdown, not daily time series
    
    TABLE 2: fct_onscreen_loader_latencies (16 columns)
    - NO date_day -- real name is date_measured
    - NO latency_ms -- real name is duration (INTEGER)
    - HAS universal_user_id (correct)
    - HAS account_id (correct)
    - Has component_id (what was loaded)
    
    TABLE 3: agg_daily_team_members_slow_chart_loads (15 columns)
    - HAS date_day (correct)
    - HAS account_id (correct)
    - NO universal_user_id -- has username instead
    - NO slow_chart_loads -- has user_with_slow_charts (STRING, not int)
    - NO total_chart_loads -- column does not exist
    - Has team, querying_team, querying_username, org_with_slow_charts
  implication: CONFIRMED ROOT CAUSE -- all 3 tables have fundamentally different schemas than assumed. The code was written against a hypothetical/outdated schema.

## Resolution

root_cause: PHASE4_SCHEMA_SPECS, performance queries, and transform were written against hypothetical column names that don't match the real BQ tables. Key mismatches: (1) fct_application_performance has no date_day column and slow_* columns are named *_user_ct (9 columns, not 5), (2) fct_onscreen_loader_latencies uses date_measured instead of date_day and duration instead of latency_ms, (3) agg_daily_team_members_slow_chart_loads has completely different structure (string flags, no numeric slow/total counts). Additionally, check_data_availability had a hardcoded 1GB byte limit that was too low for the slow chart table.
fix: |
  1. schema_validator.py: Updated PHASE4_SCHEMA_SPECS to match real column names for all 3 tables. Updated PHASE4_DATA_CHECKS to remove date_day filter from perf_index (snapshot table), use date_measured for latency, and keep date_day for slow charts. Increased check_data_availability default maximum_bytes_billed from 1GB to 10GB.
  2. queries.py: Rewrote performance_query() for snapshot table (no date filter, real column names). Rewrote latency_distribution_query() using date_measured/duration with 12-month window. Rewrote slow_chart_users_query() to use username/team/user_with_slow_charts flag counting.
  3. transforms/performance.py: Complete rewrite to handle snapshot data (no time series), 9 slowness features, component latency breakdown, team breakdown, and new slow chart user structure.
  4. generate.py: Updated slow_chart_users_query() call to remove deployment_type param, increased bytes limit to 200GB.
verification: Dry-run produces available:true with performance_index=91.0, 5745 latency measurements across 20 components, 13 slow chart users across 4 teams. All 3 schema validations pass. All 3 data availability checks pass.
files_changed:
  - .claude/skills/deep-analytics/scripts/schema_validator.py
  - .claude/skills/bigquery/scripts/queries.py
  - .claude/skills/deep-analytics/scripts/transforms/performance.py
  - .claude/skills/deep-analytics/scripts/generate.py
