# W&B Field Engineering Skills

Claude Code skills for W&B Solutions Engineers. Integrates with W&B Jira (wandb.atlassian.net), CoreWeave Slack, and CoreWeave Confluence (coreweave.atlassian.net).

## Context

- User is a Solutions Engineer at W&B (Weights & Biases), which is by CoreWeave
- The CoreWeave Slack workspace IS the user's Slack workspace
- Skills are invoked via `/skill-name` in Claude Code

## Project Structure

```
.claude/
  skills/                   -- Claude Code skills
    jira/                   -- W&B Jira queries, issue creation, FE-UPDATE
    slack/                  -- CoreWeave Slack channel history, search, threads
    confluence/             -- CoreWeave Confluence pages, spaces
    asana/                  -- Asana task management (SE actions, RAID, portfolios)
    asana-setup/            -- One-time Asana PAT setup
    salesforce/             -- Read-only Salesforce account queries (W&B SFDC)
    salesforce-setup/       -- One-time Salesforce credential setup
    customer-setup/         -- Interactive customer registry onboarding from SFDC
    cadence-prep/           -- Customer cadence call preparation
    customer-snapshot/      -- Customer intelligence dashboard
    jira-check/             -- FE-UPDATE maintenance and stale issue review
    pre-read/               -- Meeting pre-read document generation
    raid/                   -- RAID log management (Risks, Assumptions, Issues, Dependencies)
    ghosted/                -- Customer silence tracking on Slack threads
    nag/                    -- Overdue and stale task scanner
    maction/                -- Meeting notes to Asana actions + RAID pipeline
    rats/                   -- Roses & Thorns biweekly update
    atlassian-setup/        -- One-time Atlassian credential setup
    slack-setup/            -- One-time Slack credential setup
    credential-reference/   -- Reference table for all API credential keys
    credential-status/      -- Check health of all configured credentials
  rules/                    -- Auto-loaded project rules
    atlassian.md            -- Atlassian workspace conventions
    slack.md                -- Slack workspace conventions
    skill-composition.md    -- Multi-skill workflow patterns
templates/                  -- Shared templates (customers.yaml, cadence-review.md, etc.)
customers/                  -- Per-customer output directory (gitignored)
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

## Python Skills

Python skills use `uv run --project .claude/skills/<skill>` for dependency isolation. uv is installed at `~/.local/bin/uv`.

## Preferences

- Narrate before acting — explain what you're about to do so user can validate
- Don't over-adapt source material — copy as-is when already correct
- Be additive, not subtractive with existing context
