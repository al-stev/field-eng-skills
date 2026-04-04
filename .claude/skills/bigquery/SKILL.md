---
name: bigquery
description: "Use when querying customer usage data from BigQuery -- seat utilization, Weave ingestion, tracked hours, account health. Activate for usage reports, usage charts, QBR data, customer usage stats, or BigQuery queries."
argument-hint: "[subcommand] [args...]"
allowed-tools: Bash(~/.local/bin/uv run --project .claude/skills/bigquery python .claude/skills/bigquery/scripts/*.py *)
requires-credentials: []
setup-skill: bigquery-setup
service-url: https://console.cloud.google.com/bigquery?project=wandb-production
auto-refresh: false
---

# BigQuery Usage Data

Query customer usage data from W&B's BigQuery (`wandb-production`) for dashboards, usage reports, and QBR preparation.

## Prerequisites

- **ADC configured:** Run `gcloud auth application-default login` (one-time setup)
- **No stored secrets:** BigQuery uses Application Default Credentials -- nothing in `~/.fe-skills/.env`
- **Customer registered:** Customer must have `sfdc_account_id` set in `templates/customers.yaml`
- **Verify setup:** Run `/bigquery-setup` to check connectivity

## Scripts

### usage.py -- Full usage pipeline

Fetches all 4 metric categories and outputs JSON matching the `INTELLIGENCE_DATA.usage` schema.

```bash
# Full usage data as JSON
uv run --project .claude/skills/bigquery python .claude/skills/bigquery/scripts/usage.py --customer GResearch

# Human-readable text output
uv run --project .claude/skills/bigquery python .claude/skills/bigquery/scripts/usage.py --customer GResearch --format text
```

**Output schema (INTELLIGENCE_DATA.usage):**

```json
{
  "available": true,
  "period": { "start": "2025-03-24", "end": "2026-03-24" },
  "seat_utilization": {
    "contracted": 50, "claimed": 42, "active": 35,
    "utilization_percent": 70.0, "zone": "at_risk",
    "history": [{ "week": "2025-04-07", "contracted": 50, "active": 28 }]
  },
  "weave": {
    "ingestion_gb": 156.3, "limit_gb": 500.0, "utilization_percent": 31.3,
    "unique_users_last_90d": 12,
    "history": [{ "month": "2025-04", "ingestion_gb": 8.2, "unique_users": 5 }]
  },
  "tracked_hours": {
    "last_30d_hours": 1250.0, "last_30d_run_count": 342,
    "history": [{ "week": "2025-04-07", "tracked_hours": 180.5 }]
  },
  "account_health": {
    "renewal_date": "2026-09-15", "arr": 250000.0, "cs_tier": "Strategic",
    "customer_health": "Green", "churn_probability_3mo": 0.05,
    "churn_probability_5mo": 0.08, "subscription_plan": "Enterprise",
    "deployment_type": "dedicated-cloud"
  },
  "trends": {
    "seat_utilization_change": 12.5, "weave_ingestion_change": -3.2,
    "tracked_hours_change": 8.7, "run_count_change": null
  }
}
```

### product_areas.py -- Product area mapping and power user queries

Maps 40+ BigQuery event types to ~12 W&B marketecture product areas. Also provides per-user activity queries for power user identification.

**Product Areas:** Experiments, Artifacts, Model Registry, Sweeps, Reports, Launch, Automations, Weave Tracing, Weave Evaluation, Weave Data, Tables, Collaboration

Usage (product areas and power users are included in the standard usage.py output):
```bash
# Full usage data including product areas (external -- anonymized)
uv run --project .claude/skills/bigquery python .claude/skills/bigquery/scripts/usage.py --customer GResearch --format json

# Full usage data with real names (internal only)
uv run --project .claude/skills/bigquery python .claude/skills/bigquery/scripts/usage.py --customer GResearch --format json --internal
```

### account.py -- Account health only

Lighter-weight query for quick account lookups (renewal, ARR, CS tier, churn).

```bash
uv run --project .claude/skills/bigquery python .claude/skills/bigquery/scripts/account.py --customer GResearch
uv run --project .claude/skills/bigquery python .claude/skills/bigquery/scripts/account.py --customer GResearch --format text
```

## Consumer Pattern

Other skills call bigquery/ during their pipelines. The pattern follows the same approach as jira/, slack/, and asana/:

```python
# In a consumer skill (e.g., customer-snapshot, usage-report):
import subprocess, json

result = subprocess.run(
    ["uv", "run", "--project", ".claude/skills/bigquery",
     "python", ".claude/skills/bigquery/scripts/usage.py",
     "--customer", customer_name],
    capture_output=True, text=True
)
usage_data = json.loads(result.stdout)

if usage_data["available"]:
    # Inject into template
    ...
```

DataFrames are internal to the skill. JSON is the boundary format at the CLI level.

## Graceful Degradation

Each sub-section independently handles missing data:
- If seat data is absent, `seat_utilization` is `null` but other sections still populate
- If ALL sections are empty, output is `{"available": false, "reason": "no_data"}`
- If BigQuery connection fails, output is `{"available": false, "reason": "api_error", "detail": "..."}`
- If customer has no `sfdc_account_id`, output is `{"available": false, "reason": "config_error", "detail": "..."}`

## Utilization Zones

| Zone | Threshold | Meaning |
|------|-----------|---------|
| healthy | >= 80% | Good adoption |
| at_risk | 50-79% | Needs attention |
| critical | < 50% | Under-utilized |

## Data Sources

| Metric | BigQuery Table | Dataset |
|--------|----------------|---------|
| Seat utilization | `ext_daily_user_event_usage` | analytics |
| Weave ingestion | `fct_weave_project_storage` | analytics |
| Tracked hours | `agg_daily_company_usage` | analytics |
| Account health | `stg_salesforce_accounts` | analytics |
| Churn predictions | `renewal_predictions` | landing_development |

## Dedicated Cloud Data Model

Dedicated cloud customers (`hosting_type = 'local'`, `local_deployment_type = 'W&B-Dedicated Cloud (BYOB)'` in `ext_daily_user_event_usage`) have a different data model than SaaS customers. The dedicated cloud instance hashes entity/team/org names before sending telemetry to BQ.

### What IS available from BQ

| Data | Table | Join Key | Notes |
|------|-------|----------|-------|
| User names + emails | `intermediate_local_users` | `local_user_id` | Real usernames and emails |
| Per-user event counts | `ext_daily_user_event_usage` | `universal_user_id` / `local_user_id` | Same events as SaaS but `username`/`email` columns are NULL |
| Team membership structure | `fct_local_runs` | `local_user_id` + `entity_name` | Group by hashed entity_name, JOIN intermediate_local_users for member names |
| Deployment metadata | `dim_local_deployments` | `local_deployment_id` | Instance name, type, cloud provider, max_users, max_teams |
| Weave trace data | `clickhouse_managed_<customer>` dataset | `project_id` (base64 internal IDs) | Calls, objects, files, feedback only |

### What is NOT available (hashed)

| Data | Appears As | Example |
|------|-----------|---------|
| Entity/team names | Numeric hash | e.g., `1234567890` instead of the real team name |
| Organization names | Numeric hash | e.g., `9876543210` instead of the real org name |
| Project names | Numeric hash | Hashed in `fct_local_runs.name` |

The hashing happens at the W&B server telemetry emission layer. Not CRC32 — algorithm unknown, not reversible from BQ.

### Identity Resolution

`dim_users` does NOT work for dedicated cloud (returns NULLs for username/email/default_entity_id). Use `intermediate_local_users` instead:

```sql
-- WRONG for dedicated cloud:
JOIN `wandb-production.analytics.dim_users` d ON e.universal_user_id = d.universal_user_id

-- CORRECT for dedicated cloud:
JOIN `wandb-production.analytics.intermediate_local_users` lu ON e.local_user_id = lu.local_user_id
-- lu.local_username and lu.local_user_email have real values
```

### Team Detection

Entity names are hashed but team structure is recoverable:

```sql
SELECT r.entity_name AS team_hash,
       lu.local_username,
       COUNT(*) AS runs
FROM `wandb-production.analytics.fct_local_runs` r
JOIN `wandb-production.analytics.intermediate_local_users` lu
  ON r.local_user_id = lu.local_user_id
WHERE r.account_id = @account_id
  AND r.created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
GROUP BY r.entity_name, lu.local_username
ORDER BY r.entity_name, runs DESC
```

This produces anonymous team groupings with real member names. SEs recognize teams by their members.

### Detecting Deployment Type

```sql
SELECT DISTINCT hosting_type, local_deployment_type
FROM `wandb-production.analytics.ext_daily_user_event_usage`
WHERE account_id = @account_id AND date_day >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
```

| hosting_type | local_deployment_type | Meaning |
|---|---|---|
| `cloud` | NULL | SaaS (full identity resolution via dim_users) |
| `local` | `W&B-Dedicated Cloud (BYOB)` | Dedicated cloud (use intermediate_local_users) |
| `local` | NULL or other | Self-hosted server (use intermediate_local_users) |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `config_error` | Add `sfdc_account_id` to `templates/customers.yaml` for this customer |
| `api_error` | Run `/bigquery-setup` to verify ADC and BQ connectivity |
| All sections null | Customer may have no data in BigQuery -- verify account_id is correct |
| `ModuleNotFoundError` | Run `cd .claude/skills/bigquery && uv sync` |

## Related Skills

- `/bigquery-setup` -- Verify ADC and BigQuery connectivity
- `/customer-snapshot` -- Intelligence dashboard (consumes usage data)
- `/usage-report` -- Standalone usage visualization (consumes usage data)
