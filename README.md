# W&B Field Engineering Skills

Claude Code skills for W&B Solutions Engineers. Integrates with W&B Jira, CoreWeave Slack, and CoreWeave Confluence to automate customer engagement workflows.

> **Note:** These skills access live systems (Jira, Slack, Confluence). Write operations require explicit user confirmation. Read operations are safe to run freely.

## Quick Start

1. **Clone this repo:**
   ```bash
   git clone https://github.com/wandb/field-eng-skills.git
   ```

2. **Configure credentials** in `~/.tsm-ai/.env`:
   ```bash
   # W&B Jira (wandb.atlassian.net)
   ATLASSIAN_EMAIL=your.email@wandb.com
   ATLASSIAN_TOKEN=your-api-token

   # CoreWeave Confluence (coreweave.atlassian.net)
   CONFLUENCE_EMAIL=your.email@coreweave.com
   CONFLUENCE_TOKEN=your-api-token

   # CoreWeave Slack
   SLACK_TOKEN=xoxc-...
   SLACK_COOKIE=xoxd-...
   ```
   Run `/credential-status` to verify. Run `/atlassian-setup` or `/slack-setup` for guided configuration.

3. **Install Python dependencies** (per-skill, using uv):
   ```bash
   cd .claude/skills/jira && uv sync
   cd .claude/skills/slack && uv sync
   cd .claude/skills/confluence && uv sync
   ```

4. **Install globally** (available in any project):
   ```bash
   # Symlink skills to global Claude Code skills directory
   ln -s $(pwd)/.claude/skills/* ~/.claude/skills/
   # Symlink rules
   ln -s $(pwd)/.claude/rules/* ~/.claude/rules/
   ```

## Skills

### Customer Engagement

| Skill | Invocation | What it does |
|-------|-----------|--------------|
| **cadence-prep** | `/cadence-prep GResearch` | Prepares a customer cadence call agenda. Gathers Jira issues, Slack threads, product updates, and carry-forward items. Publishes to Confluence and optionally generates styled HTML. |
| **customer-snapshot** | `/customer-snapshot GResearch` | Generates an interactive intelligence dashboard from Jira + Slack data. Shows health buckets, sentiment analysis, trending metrics, and executive summary. |
| **jira-check** | `/jira-check GResearch` | Reviews customer Jira issues for staleness, drafts FE-UPDATE comments, and identifies issues needing attention. Runs across all customers when invoked without a name. |
| **pre-read** | `/pre-read GResearch` | Generates a structured pre-read document for a customer meeting by synthesizing Slack threads, Jira issues, and manual context. |
| **rats** | `/rats` | Searches your recent Slack posts and produces categorized output (Highlights, Lowlights, Learnings, Risks) for the team Roses & Thorns page. |

### Data Sources

| Skill | Invocation | What it does |
|-------|-----------|--------------|
| **jira** | `/jira list --customer GResearch` | Query, create, edit, and transition issues in W&B Jira (wandb.atlassian.net). Supports FE-UPDATE comments, customer filtering, and JQL search. |
| **slack** | `/slack search "keyword"` | Search messages, read channel history, fetch threads, and look up users in the CoreWeave Slack workspace. |
| **confluence** | `/confluence search --title "Meeting Notes"` | Read, create, and update pages in CoreWeave Confluence (coreweave.atlassian.net). Supports CQL search, folders, attachments, and labels. |

### Setup & Diagnostics

| Skill | What it does |
|-------|--------------|
| **atlassian-setup** | Guided setup for Jira and Confluence API tokens |
| **slack-setup** | Guided setup for Slack credentials (token + cookie) |
| **credential-status** | Health check for all configured credentials |
| **credential-reference** | Reference table of all API credential keys and where they're used |

## Workflow Patterns

Skills are designed to compose. Common patterns are documented in `.claude/rules/skill-composition.md`:

- **Cadence Prep** — cadence-prep orchestrates jira + slack + confluence in sequence
- **Customer Lookup** — jira + slack + confluence to build a customer picture
- **Customer Snapshot** — jira + slack + customer-snapshot for an intelligence dashboard
- **FE-UPDATE Workflow** — jira-check identifies stale issues, slack gathers context, jira posts updates
- **Communication Prep** — slack + jira + confluence to prepare for meetings

## Project Structure

```
.claude/
  skills/           -- 12 Claude Code skills (invoked via /skill-name)
  rules/            -- Auto-loaded project rules
    atlassian.md    -- Jira/Confluence workspace conventions, FE-UPDATE format
    slack.md        -- Slack workspace conventions, channel naming
    skill-composition.md -- Multi-skill workflow patterns
templates/
  customers.yaml    -- Customer registry (Jira names, Slack channels, cadence schedule, deployment type)
  cadence-review.md -- Cadence call template (9 agenda sections)
```

## Credentials

Two separate Atlassian instances require separate credentials:

| Instance | Purpose | Credentials |
|----------|---------|-------------|
| wandb.atlassian.net | W&B Jira (customer bugs, feature requests) | `ATLASSIAN_EMAIL` / `ATLASSIAN_TOKEN` |
| coreweave.atlassian.net | CoreWeave Confluence (team wiki, cadence docs) | `CONFLUENCE_EMAIL` / `CONFLUENCE_TOKEN` |

Slack uses the CoreWeave workspace: `SLACK_TOKEN` / `SLACK_COOKIE`.

All stored in `~/.tsm-ai/.env`. API tokens are generated at [id.atlassian.com](https://id.atlassian.com/manage-profile/security/api-tokens) — make sure you're logged in as the correct account for each instance.

## Customer Registry

`templates/customers.yaml` is the shared customer registry used by cadence-prep, customer-snapshot, and jira-check. Each customer entry has:

- `name` / `jira_customer` — for Jira queries
- `slack_channels` — channel IDs for Slack data
- `cadence` — meeting schedule (type/day/time drives lookback window)
- `deployment_type` — saas / dedicated-cloud / server (filters product updates)
- `contacts` — key contacts with org and role

## Python Skills

Skills with Python scripts use [uv](https://docs.astral.sh/uv/) for per-skill dependency isolation:

```bash
uv run --project .claude/skills/<skill> python .claude/skills/<skill>/scripts/<script>.py <command> [options]
```

Each skill with Python has its own `pyproject.toml` and `uv.lock`. Run `uv sync` in the skill directory on first use.
