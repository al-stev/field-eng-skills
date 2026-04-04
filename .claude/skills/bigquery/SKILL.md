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
