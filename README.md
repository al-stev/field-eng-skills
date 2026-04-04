# W&B Field Engineering Skills

Claude Code skills for W&B Solutions Engineers. Integrates with W&B Jira, CoreWeave Slack, and CoreWeave Confluence to automate customer engagement workflows.

> **Note:** These skills access live systems (Jira, Slack, Confluence). Write operations require explicit user confirmation. Read operations are safe to run freely.

## Quick Start

1. **Clone this repo:**
   ```bash
   git clone https://github.com/wandb/field-eng-skills.git
   ```

2. **Configure credentials** in `~/.fe-skills/.env`:
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

   # Asana (SE action tracking)
   ASANA_TOKEN=your-personal-access-token

   # W&B Salesforce (session auth via sf CLI OAuth)
   SFDC_SESSION_ID=your-access-token
   SFDC_INSTANCE=wandb.my.salesforce.com
   ```
   Run `/credential-status` to verify. Run `/atlassian-setup`, `/slack-setup`, `/asana-setup`, or `/salesforce-setup` for guided configuration.

3. **Install Python dependencies** (per-skill, using uv):
   ```bash
   cd .claude/skills/jira && uv sync
   cd .claude/skills/slack && uv sync
   cd .claude/skills/confluence && uv sync
   cd .claude/skills/asana && uv sync
   cd .claude/skills/salesforce && uv sync
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
| **cadence-prep** | `/cadence-prep GResearch` | Prepares a customer cadence call agenda. Gathers Jira issues, Slack threads, Asana actions, product updates, and carry-forward items. Publishes to Confluence and optionally generates styled HTML. |
| **customer-snapshot** | `/customer-snapshot GResearch` | Generates an interactive intelligence dashboard from Jira + Slack + Asana data. Shows health buckets, sentiment analysis, trending metrics, and executive summary. |
| **jira-check** | `/jira-check GResearch` | Reviews customer Jira issues for staleness, drafts FE-UPDATE comments, and identifies issues needing attention. Runs across all customers when invoked without a name. |
| **pre-read** | `/pre-read GResearch` | Generates a structured pre-read document for a customer meeting by synthesizing Slack threads, Jira issues, and manual context. |
| **rats** | `/rats` | Searches your recent Slack posts and produces categorized output (Highlights, Lowlights, Learnings, Risks) for the team Roses & Thorns page. |

### Asana Action Tracking

| Skill | Invocation | What it does |
|-------|-----------|--------------|
| **asana** | `/asana tasks --project-gid GID` | Query and manage SE action items in Asana. Supports projects, tasks, sections, search, and write operations (create, update, move, complete). |
| **raid** | `/raid GResearch` | View, scan for, or add RAID items (Risks, Assumptions, Issues, Dependencies). Manages Asana-native RAID logs with portfolio visibility across accounts. |
| **ghosted** | `/ghosted` | Track customer silence on Slack threads. Monitors "Waiting on Customer" tasks for unresponsive threads. |
| **nag** | `/nag` | Scan your Asana tasks for overdue and stale items across all customers. Your personal task hygiene scanner. |
| **maction** | `/maction GResearch <notes>` | Extract action items and RAID signals from meeting notes or transcripts. Creates tracked Asana tasks from Granola summaries or pasted text. |

### Data Sources

| Skill | Invocation | What it does |
|-------|-----------|--------------|
| **jira** | `/jira list --customer GResearch` | Query, create, edit, and transition issues in W&B Jira (wandb.atlassian.net). Supports FE-UPDATE comments, customer filtering, and JQL search. |
| **slack** | `/slack search "keyword"` | Search messages, read channel history, fetch threads, and look up users in the CoreWeave Slack workspace. |
| **confluence** | `/confluence search --title "Meeting Notes"` | Read, create, and update pages in CoreWeave Confluence (coreweave.atlassian.net). Supports CQL search, folders, attachments, and labels. |
| **salesforce** | `/salesforce account-detail --account-id ID` | Read-only Salesforce queries for account data (ARR, contract dates, team members, field discovery). Supports SSO/session auth for W&B's org. |

### Setup & Diagnostics

| Skill | What it does |
|-------|--------------|
| **atlassian-setup** | Guided setup for Jira and Confluence API tokens |
| **slack-setup** | Guided setup for Slack credentials (token + cookie) |
| **asana-setup** | Guided setup for Asana Personal Access Token (PAT) |
| **salesforce-setup** | Guided setup for Salesforce credentials (sf CLI OAuth for SSO/2FA) |
| **customer-setup** | Interactive customer registry onboarding from Salesforce data with SE overlays |
| **credential-status** | Health check for all configured credentials |
| **credential-reference** | Reference table of all API credential keys and where they're used |

## Workflow Patterns

Skills are designed to compose. Common patterns are documented in `.claude/rules/skill-composition.md`:

- **Cadence Prep** — cadence-prep orchestrates jira + slack + asana + confluence in sequence
- **Customer Lookup** — salesforce + jira + slack + confluence to build a customer picture
- **Customer Snapshot** — jira + slack + asana + customer-snapshot for an intelligence dashboard
- **FE-UPDATE Workflow** — jira-check identifies stale issues, slack gathers context, jira posts updates
- **Communication Prep** — slack + jira + confluence to prepare for meetings
- **RAID Management** — raid + asana + jira + slack for risk register maintenance
- **Action Tracking** — slack + jira + asana to capture and track SE actions
- **Meeting Follow-Up** — maction + asana + raid to turn meeting notes into tracked work
- **Task Hygiene** — nag + asana + ghosted to keep backlog clean

## Asana Structure: RAID Two-Project Model

Each customer in Asana has two projects, organized inside a customer portfolio within a master portfolio:

```
Portfolio: "W&B EMEA Customers"              <- master portfolio
  |-- Portfolio: "GResearch"                 <- one per customer
  |    |-- GResearch Actions (project)       <- day-to-day SE work (safe to share)
  |    |-- GResearch RAID Log (project)      <- internal risk register (NEVER shared)
  |-- Portfolio: "GSK"
  |    |-- GSK Actions (project)
  |    |-- GSK RAID Log (project)
```

- **Actions project** (6 sections: To Do, In Progress, Waiting on Customer, Waiting on Eng, Scheduled/Future, Done) -- tracks SE action items. Customers can see this.
- **RAID project** (4 sections: Risks, Assumptions, Issues, Dependencies) -- internal strategic view with honest risk assessments. Never shared with customers.
- **Multi-homing**: Action tasks can appear in both projects via Asana's native multi-homing. An action task blocked on engineering lives in both the Actions project ("Waiting on Eng") and the RAID project ("Dependencies").

Run `/asana setup-customer --name "CustomerName" --master-portfolio-gid GID` to create the full structure for a new customer. See `.claude/rules/asana.md` for workspace constants and conventions.

## Project Structure

```
.claude/
  skills/           -- 21 Claude Code skills (invoked via /skill-name)
  rules/            -- Auto-loaded project rules
    atlassian.md    -- Jira/Confluence workspace conventions, FE-UPDATE format
    asana.md        -- Asana workspace conventions, RAID model, staleness rules
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
| app.asana.com | Asana (SE action tracking, RAID logs, portfolios) | `ASANA_TOKEN` |
| wandb.my.salesforce.com | W&B Salesforce (account data, team members) | `SFDC_SESSION_ID` / `SFDC_INSTANCE` |

Slack uses the CoreWeave workspace: `SLACK_TOKEN` / `SLACK_COOKIE`.

Asana uses a Personal Access Token (PAT) generated at [app.asana.com/0/my-apps](https://app.asana.com/0/my-apps). PATs do not expire. Run `/asana-setup` for guided configuration.

Salesforce uses session-based auth via `sf` CLI OAuth (W&B uses SSO, so password auth doesn't work). Run `/salesforce-setup` for guided configuration. Tokens expire periodically and need re-auth via `sf org login web`.

All stored in `~/.fe-skills/.env`. API tokens are generated at [id.atlassian.com](https://id.atlassian.com/manage-profile/security/api-tokens) — make sure you're logged in as the correct account for each instance.

## Customer Registry

`templates/customers.yaml` is a routing table — thin pointers to external systems, not a data store. Each system owns its own data; this file just tells skills WHERE to look. SFDC is the source of truth for business data (ARR, contracts, account team).

Each customer entry has:

- `name` / `jira_customer` / `jira_customer_variants` — for Jira queries and fuzzy matching
- `sfdc_account_id` — 18-char Salesforce Account ID (business data pulled at runtime via `/salesforce`)
- `slack_channels` — channel IDs for Slack data (id, name, type)
- `action_tracker` / `action_tracker_id` — system and GID for SE actions ("asana" + Asana project GID)
- `raid_tracker` / `raid_tracker_id` — system and GID for RAID log ("asana" + Asana RAID project GID)
- `portfolio_id` — Asana customer portfolio GID (from `/asana setup-customer`)
- `deployment_type` — saas / dedicated-cloud / server (filters product updates)
- `cadence` — meeting schedule (type/day/time drives lookback window)
- `contacts` — key contacts with org and role (SE-managed, built up over time)

Business data fields (ARR, contract dates, account team, CS tier) are no longer stored here — they are pulled from SFDC at runtime via the `/salesforce` skill.

## Python Skills

Skills with Python scripts use [uv](https://docs.astral.sh/uv/) for per-skill dependency isolation:

```bash
uv run --project .claude/skills/<skill> python .claude/skills/<skill>/scripts/<script>.py <command> [options]
```

Each skill with Python has its own `pyproject.toml` and `uv.lock`. Run `uv sync` in the skill directory on first use.
