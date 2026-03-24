# W&B Field Engineering Skills

Claude Code skills for W&B Solutions Engineers. Integrates with W&B Jira (wandb.atlassian.net), CoreWeave Slack, and CoreWeave Confluence (coreweave.atlassian.net).

## Context

- User is a Solutions Engineer at W&B (Weights & Biases), which is by CoreWeave
- The CoreWeave Slack workspace IS the user's Slack workspace
- Skills are invoked via `/skill-name` in Claude Code

## Preferences

- Narrate before acting — explain what you're about to do so user can validate
- Don't over-adapt source material — copy as-is when already correct
- Be additive, not subtractive with existing context

## Project Structure

```
.claude/
  skills/                   -- Claude Code skills (invoked via /skill-name)
    3p-update/              -- 3P (Progress/Plans/Problems) update generation from Asana + Jira + Slack
    asana/                  -- Asana project/task queries and mutations (SE action tracking)
    asana-setup/            -- One-time Asana PAT setup
    atlassian-setup/        -- One-time Atlassian API token setup (Jira + Confluence)
    bigquery/               -- BigQuery usage data queries (wandb-production.analytics) with product area mapping
    bigquery-setup/         -- One-time BigQuery ADC connectivity verification
    cadence-prep/           -- Customer cadence call preparation
    confluence/             -- CoreWeave Confluence pages, spaces (coreweave.atlassian.net)
    credential-reference/   -- Reference table for all API credential keys
    credential-status/      -- Check health of all configured credentials
    customer-setup/         -- Interactive customer onboarding (SFDC + SE overlays -> customers.yaml)
    customer-snapshot/      -- Customer intelligence dashboard from Jira + Slack data
    ghosted/                -- Customer silence tracker (Waiting on Customer thread monitoring)
    jira/                   -- W&B Jira queries, issue creation, FE-UPDATE (wandb.atlassian.net)
    jira-check/             -- Jira issue triage and FE-UPDATE pipeline
    maction/                -- Meeting notes to Asana actions + RAID items
    nag/                    -- Stale/overdue task scanner across customer projects
    pre-read/               -- Meeting pre-read document generation
    raid/                   -- RAID log management (Risks, Assumptions, Issues, Dependencies)
    rats/                   -- Roses & Thorns biweekly update
    salesforce/             -- Salesforce account queries (read-only: accounts, team members, field discovery)
    salesforce-setup/       -- One-time Salesforce credential setup
    slack/                  -- CoreWeave Slack channel history, search, threads
    slack-setup/            -- One-time Slack credential setup
    usage-report/           -- Standalone usage visualization (external QBR-ready + internal SE prep reports with ECharts)
  rules/                    -- Auto-loaded project rules
    asana.md                -- Asana workspace conventions (sections, custom fields, RAID, portfolio, staleness rules)
    atlassian.md            -- Atlassian workspace conventions
    slack.md                -- Slack workspace conventions
    skill-composition.md    -- Multi-skill workflow patterns
customers/                  -- Per-customer output directory (gitignored)
templates/                  -- Agent and output templates
scripts/                    -- Shared shell scripts
```

## Credentials

All API credentials stored in `~/.tsm-ai/.env`. Run `/credential-status` to check health.

| Variable | Service | Instance |
|----------|---------|----------|
| `ATLASSIAN_EMAIL` | W&B Jira | wandb.atlassian.net |
| `ATLASSIAN_TOKEN` | W&B Jira | wandb.atlassian.net |
| `CONFLUENCE_EMAIL` | CoreWeave Confluence | coreweave.atlassian.net |
| `CONFLUENCE_TOKEN` | CoreWeave Confluence | coreweave.atlassian.net |
| `SLACK_TOKEN` | CoreWeave Slack | coreweave.slack.com |
| `SLACK_COOKIE` | CoreWeave Slack | coreweave.slack.com |
| `ASANA_TOKEN` | Asana | app.asana.com |
| `SFDC_SESSION_ID` | W&B Salesforce (session auth) | wandb.my.salesforce.com |
| `SFDC_INSTANCE` | W&B Salesforce (session auth) | wandb.my.salesforce.com |

BigQuery uses Application Default Credentials (ADC) -- no token in ~/.tsm-ai/.env. Run `gcloud auth application-default login` to configure. Verify with `/bigquery-setup`.

Asana PAT (`ASANA_TOKEN`) for SE action tracking. Asana uses a two-project model per customer: Actions project (day-to-day SE work, safe to share) and RAID Portfolio project (internal strategic view). Run `/raid` to manage RAID logs. Master portfolio holds all customer portfolios. Run `setup-customer` to onboard new customers into the portfolio structure.

## Python Skills

Python skills use `uv run --project .claude/skills/<skill>` for dependency isolation. uv is installed at `~/.local/bin/uv`.
