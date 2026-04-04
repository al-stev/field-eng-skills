# Skill Inventory

All Claude Code skills available in this repository. Each skill is invoked via `/skill-name` in Claude Code. Skills are classified as:

- **entry-point** -- SE invokes directly via `/skill-name` (standalone use case)
- **building-block** -- consumed by other skills or composition workflows only
- **setup** -- one-time credential/infrastructure configuration (entry-point but infrequently invoked)

## Inventory

| Skill Name | Description | Type | Required Credentials | Invocation |
|------------|-------------|------|---------------------|------------|
| 3p-update | Generate 3P (Progress/Plans/Problems) updates for customer engagements | entry-point | ASANA_TOKEN, ATLASSIAN_EMAIL, ATLASSIAN_TOKEN, SLACK_TOKEN, SLACK_COOKIE | `/3p-update [customer-name]` |
| asana | Asana project/task queries and mutations for SE action tracking | entry-point | ASANA_TOKEN | `/asana [subcommand] [args...]` |
| asana-setup | One-time Asana PAT setup | setup | -- | `/asana-setup` |
| atlassian-setup | One-time Atlassian API token setup for Jira and Confluence | setup | -- | `/atlassian-setup` |
| bigquery | BigQuery usage data queries (seat utilization, Weave, tracked hours, account health) | building-block | ADC (gcloud) | `/bigquery [subcommand] [args...]` |
| bigquery-setup | One-time BigQuery ADC connectivity verification | setup | -- | `/bigquery-setup` |
| cadence-prep | Prepare structured meeting agendas from Jira issues and Slack history | entry-point | ATLASSIAN_EMAIL, ATLASSIAN_TOKEN, SLACK_TOKEN, SLACK_COOKIE, ASANA_TOKEN | `/cadence-prep [customer-name]` |
| confluence | CoreWeave Confluence page and blog post operations | entry-point | ATLASSIAN_EMAIL, ATLASSIAN_TOKEN | `/confluence [get/create/update] [args...]` |
| credential-reference | Reference table for all API credential keys and setup skills | entry-point | -- | `/credential-reference` |
| credential-status | Check health of all configured API credentials | entry-point | -- | `/credential-status` |
| customer-setup | Interactive customer onboarding from Salesforce data with SE overlays | entry-point | SFDC_SESSION_ID, SFDC_INSTANCE, ATLASSIAN_EMAIL, ATLASSIAN_TOKEN, SLACK_TOKEN, SLACK_COOKIE | `/customer-setup <customer-name>` |
| customer-snapshot | Generate interactive intelligence dashboards from Jira, Slack, Asana, and BigQuery data | entry-point | ATLASSIAN_EMAIL, ATLASSIAN_TOKEN, SLACK_TOKEN, SLACK_COOKIE, ASANA_TOKEN | `/customer-snapshot <customer-name>` |
| deep-analytics | Deep analytics HTML pages from BigQuery data (user journey, cohort, decay, velocity, team, risk, correlation, SDK, performance) | entry-point | ADC (gcloud) | `/deep-analytics --customer <name> --page <type>` |
| gcalendar | Google Calendar event listing, creation, and management via Apps Script + CDP | entry-point | GCALENDAR_APPSCRIPT_URL, GCALENDAR_APPSCRIPT_KEY | `/gcalendar [subcommand] [args...]` |
| gcalendar-setup | One-time Google Calendar Apps Script setup | setup | -- | `/gcalendar-setup` |
| gdocs | Google Docs read and write operations via Apps Script + CDP | entry-point | GDOCS_APPSCRIPT_URL, GDOCS_APPSCRIPT_KEY | `/gdocs [subcommand] [args...]` |
| gdocs-setup | One-time Google Docs Apps Script setup | setup | -- | `/gdocs-setup` |
| ghosted | Track customer silence on Slack threads in Waiting on Customer tasks | entry-point | ASANA_TOKEN, SLACK_TOKEN, SLACK_COOKIE | `/ghosted [track <URL>] [customer-name]` |
| gmail | Gmail read-only access for searching emails and reading threads via Apps Script + CDP | entry-point | GMAIL_APPSCRIPT_URL, GMAIL_APPSCRIPT_KEY | `/gmail [subcommand] [args...]` |
| gmail-setup | One-time Gmail Apps Script setup for read-only access | setup | -- | `/gmail-setup` |
| gong | Gong call recordings, transcripts, and AI summaries via cookie-based auth + CDP | entry-point | GONG_COOKIE, GONG_BASE_URL, GONG_WORKSPACE_ID | `/gong [subcommand] [args...]` |
| gong-setup | One-time Gong session cookie setup | setup | -- | `/gong-setup` |
| jira | W&B Jira issue queries, creation, FE-UPDATE comments | entry-point | ATLASSIAN_EMAIL, ATLASSIAN_TOKEN | `/jira [subcommand] [args...]` |
| jira-check | Jira issue triage and FE-UPDATE maintenance pipeline | entry-point | ATLASSIAN_EMAIL, ATLASSIAN_TOKEN, SLACK_TOKEN, SLACK_COOKIE | `/jira-check [customer-name]` |
| lattice | Weekly Lattice update generator mapped to IC5 growth areas | entry-point | SLACK_TOKEN, SLACK_COOKIE, ASANA_TOKEN, ATLASSIAN_EMAIL, ATLASSIAN_TOKEN, GCALENDAR_APPSCRIPT_URL, GCALENDAR_APPSCRIPT_KEY | `/lattice [--days N]` |
| maction | Extract action items and RAID items from meeting notes into Asana tasks | entry-point | ASANA_TOKEN | `/maction <customer-name> <notes>` |
| nag | Scan Asana tasks for overdue and stale items across customer projects | entry-point | ASANA_TOKEN | `/nag [customer-name]` |
| pre-read | Generate structured pre-read documents for customer meetings from Slack + Jira | entry-point | ATLASSIAN_EMAIL, ATLASSIAN_TOKEN, SLACK_TOKEN, SLACK_COOKIE | `/pre-read [customer-name]` |
| raid | RAID log management (Risks, Assumptions, Issues, Dependencies) via Asana | entry-point | ASANA_TOKEN, ATLASSIAN_EMAIL, ATLASSIAN_TOKEN, SLACK_TOKEN, SLACK_COOKIE | `/raid [view/scan/add] [customer-name]` |
| rats | Roses & Thorns biweekly update from Slack activity | entry-point | SLACK_TOKEN, SLACK_COOKIE | `/rats [--days N]` |
| salesforce | Salesforce account queries (read-only: accounts, team members, field discovery) | entry-point | SFDC_SESSION_ID, SFDC_INSTANCE | `/salesforce <subcommand> [options]` |
| salesforce-setup | One-time Salesforce credential setup | setup | -- | `/salesforce-setup` |
| slack | CoreWeave Slack channel history, search, threads, and user lookups | entry-point | SLACK_TOKEN, SLACK_COOKIE | `/slack [search query or channel action]` |
| slack-setup | One-time Slack session token setup | setup | -- | `/slack-setup` |
| usage-report | Standalone usage visualization reports from BigQuery (external QBR-ready + internal SE prep) | entry-point | ADC (gcloud) | `/usage-report <customer-name> [--internal]` |

**Total: 35 skills** (25 entry-point, 1 building-block, 9 setup)

## Dependency Graph

Skills that are consumed by other skills as data sources or building blocks.

### bigquery
  consumed by: customer-snapshot, usage-report, deep-analytics, lattice

### jira
  consumed by: customer-snapshot, jira-check, cadence-prep, pre-read, 3p-update, lattice, raid

### slack
  consumed by: customer-snapshot, ghosted, cadence-prep, pre-read, 3p-update, lattice, rats, raid, jira-check

### asana
  consumed by: customer-snapshot, ghosted, nag, maction, raid, 3p-update, lattice, cadence-prep

### confluence
  consumed by: cadence-prep, 3p-update

### salesforce
  consumed by: customer-setup

### gcalendar
  consumed by: lattice

### gong
  consumed by: lattice

### gmail
  consumed by: lattice

## Composition Workflows

Named multi-skill workflows are documented in `.claude/rules/skill-composition.md`. These workflows orchestrate multiple skills for common SE operations:

| Workflow | Skills Used |
|----------|-------------|
| Issue Triage | slack, jira |
| Customer Lookup | salesforce, jira, slack, confluence |
| Customer Snapshot | jira, asana, bigquery, customer-snapshot |
| Communication Prep | slack, jira, confluence, bigquery, gcalendar, gmail, gong |
| FE-UPDATE Workflow | jira, slack |
| Action Tracking | slack, jira, asana |
| Programme Update | 3p-update (orchestrates asana, jira, slack) |
| RAID Management | raid (orchestrates asana, jira, slack) |
| Usage Report | bigquery, usage-report |
| Customer Onboarding | asana, salesforce, jira, slack |
| Customer Silence Check | ghosted (orchestrates asana, slack) |
| Meeting Follow-Up | maction, asana, raid |
| Task Hygiene | nag, asana, ghosted |

## Hardcoded Value Audit

Scan of all committed `.py` and `.sh` source files under `.claude/skills/` for user-specific hardcoded values (Asana GIDs, Slack channel IDs, email addresses, user-specific URLs).

### Fixed

| File | Line | Value | Issue | Fix |
|------|------|-------|-------|-----|
| `gong/scripts/gong_client.py` | 44 | `'https://us-39259.app.gong.io'` | Hardcoded W&B Gong base URL as silent fallback | Removed fallback; now requires `GONG_BASE_URL` in `~/.fe-skills/.env` |
| `gong/scripts/gong_client.py` | 45 | `'315301294163453491'` | Hardcoded W&B Gong workspace ID as silent fallback | Removed fallback; now requires `GONG_WORKSPACE_ID` in `~/.fe-skills/.env` |

### Accepted (workspace-level constants, not user-specific)

| File | Line | Value | Rationale |
|------|------|-------|-----------|
| `asana/scripts/asana_client.py` | 22 | `_ASANA_WORKSPACE_GID_DEFAULT = "1208076155392173"` | W&B workspace GID -- same for all W&B SEs. Has env var override (`ASANA_WORKSPACE_GID`). Documented in `.claude/rules/asana.md`. |
| `asana/scripts/mutate.py` | 47-55 | Priority field GIDs, `DEFAULT_TEAM_GID` | W&B Asana workspace-level constants -- same for all SEs in the same workspace. Documented in `.claude/rules/asana.md`. |
| `cadence-prep/SKILL.md` | 234-235 | Channel IDs `C05MEBCNM9S`, `C04521MA98X` | Product-releases and announcements channels -- org-wide, not user-specific. In SKILL.md (documentation), not committed source. |

### Out of scope

| Category | Rationale |
|----------|-----------|
| GIDs in `SKILL.md` files | Documentation and example values -- acceptable per D-04 |
| GIDs in `asana.md` rules file | Workspace-level constants documented for all SEs |
| Email patterns in `customer-setup/SKILL.md` | Example/template patterns, not real user emails |
| Test fixtures (`conftest.py`, `test_*.py`) | Example GIDs/emails for testing -- acceptable per D-04 |
