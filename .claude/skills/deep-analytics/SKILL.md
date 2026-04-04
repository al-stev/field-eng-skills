---
name: deep-analytics
description: "Generate deep analytics HTML pages from BigQuery data -- user journey, cohort analysis, engagement decay, feature velocity, team detection, risk scoring, usage correlation, SDK versions, performance. Use when the user mentions deep analytics, analytics pages, user journey, cohort analysis, engagement decay, feature velocity, team detection, risk scoring, usage correlation, SDK versions, or wants detailed per-user/per-team intelligence beyond the standard usage report."
argument-hint: "--customer <name> --page <type>"
allowed-tools: Bash(~/.local/bin/uv run --project .claude/skills/deep-analytics python .claude/skills/deep-analytics/scripts/*.py *)
requires-credentials: []
setup-skill: bigquery-setup
service-url: https://console.cloud.google.com/bigquery?project=wandb-production
auto-refresh: false
---

# Deep Analytics

Generate deep analytics HTML pages from BigQuery data. Each page targets a specific analytical dimension -- from user adoption journeys to churn risk scoring -- going beyond the aggregate charts in the standard usage report.

## Prerequisites

- **ADC configured:** Run `gcloud auth application-default login` (one-time setup)
- **No stored secrets:** BigQuery uses Application Default Credentials -- nothing in `~/.fe-skills/.env`
- **Customer registered:** Customer must have `sfdc_account_id` set in `templates/customers.yaml`
- **Verify setup:** Run `/bigquery-setup` to check connectivity

## CLI Usage

```bash
uv run --project .claude/skills/deep-analytics python \
    .claude/skills/deep-analytics/scripts/generate.py \
    --customer <name> --page <type>
```

### Available Page Types

| Page Type | What It Shows |
|-----------|---------------|
| `user-journey` | Adoption funnel/Sankey from dim_users first_*_at fields showing per-user progression through W&B product stages |
| `cohort-analysis` | New vs established user retention comparison using retention tables, cohort heatmaps |
| `engagement-decay` | Individual user cold-detection with week-over-week drop-off alerting from daily event data |
| `feature-velocity` | Per-product-area time-series showing acceleration/deceleration trends with sparklines and momentum indicators |
| `team-detection` | Group users by team fields and show per-team adoption patterns |
| `risk-scoring` | Combine renewal_predictions ML churn scores with engagement signals and revenue trends |
| `usage-correlation` | Cross-account analysis of which product combos predict retention/expansion |
| `sdk-versions` | cli_version and local_version distribution per customer, version freshness, upgrade recommendations |
| `performance` | Performance signals, narrative-driven analysis of API latency, chart load, artifact perf |

### Options

| Flag | Description |
|------|-------------|
| `--customer` | Customer name (must exist in templates/customers.yaml) |
| `--page` | Analytics page type to generate (see table above) |
| `--output-dir` | Override output directory (default: customers/<name>/analytics/) |
| `--dry-run` | Validate schema and estimate cost without generating |

## Output Path Convention

```
customers/<kebab-case-name>/analytics/YYYY-MM-DD-<page-type>.html
```

Examples:
- `customers/g-research/analytics/2026-03-24-user-journey.html`
- `customers/acme-corp/analytics/2026-03-24-cohort-analysis.html`

## Design Rules

- **ECharts v5 from CDN** -- loaded from `https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js`
- **Custom 'wandb' ECharts theme** -- registered via `echarts.registerTheme('wandb', ...)` matching the project design system
- **Self-contained HTML** -- single .html file, no external JS/CSS beyond CDN
- **Dark mode default**, light mode via `prefers-color-scheme: light` media query
- **W&B branding** -- Instrument Serif + Outfit + JetBrains Mono typography, gold accent
- **Responsive** -- max-width 1160px, fluid spacing, single-column for screen-sharing

## Dedicated Cloud Customers

Dedicated cloud customers have a different BQ data model. See the bigquery skill's SKILL.md for full details (`Dedicated Cloud Data Model` section). Key points for deep analytics:

- **Identity resolution**: `dim_users` returns NULLs. Use `intermediate_local_users` (JOIN on `local_user_id`) for real usernames and emails
- **Team detection**: Entity/team names are hashed to numeric IDs (e.g., `1707861832` not `pythia`). Team structure is recoverable from `fct_local_runs` grouped by hashed entity_name + JOIN `intermediate_local_users`. Display teams as anonymous groupings with real member names.
- **Detection**: Check `hosting_type` in `ext_daily_user_event_usage` — `local` = dedicated cloud or server, `cloud` = SaaS
- **All other pages work** (cohort analysis, engagement decay, risk scoring, etc.) as long as identity resolution uses `intermediate_local_users` instead of `dim_users`

## Anti-Patterns

- Chart.js or any non-ECharts charting library
- KPI cards (big number + small label in identical card grid)
- Jinja2 or any server-side templating
- Shared CSS/JS files -- everything inline in the HTML
- Gradient text, glassmorphism, neon accents
- External JSON data files -- data goes inline as JS object literal
- npm build steps (webpack, vite, rollup)

## Related Skills

- `/bigquery` -- Base data access skill (queries BigQuery tables)
- `/bigquery-setup` -- Verify ADC and BigQuery connectivity
- `/usage-report` -- Standalone usage visualization (aggregate charts)
- `/customer-snapshot` -- Intelligence dashboard (Jira + Slack + usage data)
