---
name: jira
description: "Use when creating, viewing, searching, or transitioning Jira issues in the W&B project. Activate for WB- ticket references, customer bug/FR tracking, FE-UPDATE comments, or per-customer queries."
argument-hint: "[subcommand] [args...]"
allowed-tools: Bash(uv run --project .claude/skills/jira python .claude/skills/jira/scripts/*.py *)
requires-credentials:
  - ATLASSIAN_EMAIL
  - ATLASSIAN_TOKEN
setup-skill: atlassian-setup
service-url: https://wandb.atlassian.net
auto-refresh: false
---

# Jira Issue Management

Manage issues in the W&B Jira instance (wandb.atlassian.net) using Python tools with the `jira` SDK.

Refer to `.claude/rules/atlassian.md` for shared Atlassian constants and FE-UPDATE convention.

## Defaults

| Property | Value |
|---|---|
| Project | `WB` (W&B Eng) |
| Instance | `wandb.atlassian.net` |

## Prerequisites

- `ATLASSIAN_EMAIL` and `ATLASSIAN_TOKEN` configured in `~/.tsm-ai/.env`
- Python dependencies installed: `cd .claude/skills/jira && uv sync`
- Verify with: `uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py list --max-results 1 --pretty`

## Python Tools

All Python tools output JSON to stdout and errors to stderr. Use `--pretty` for human-readable output.

**Invocation pattern:**
```bash
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/<tool>.py <command> [options]
```

## Valid Issue Types (WB Project)

| Type | Use for |
|---|---|
| `Bug` | Customer-reported bugs, regressions, broken behavior |
| `Feature Request` | Customer feature asks, enhancement requests |
| `Story` | General work items |
| `Sub-task` | Subtask of a Story or other issue |

## Customer Queries

The `--customer` flag filters issues by the Customer field (customfield_10083). This is the key SE workflow for finding all tickets for a specific customer.

```bash
# All bugs for GResearch
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py list --customer GResearch --type Bug --pretty

# All issues for a customer
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py list --customer GResearch --pretty

# JQL search with customer filter
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py search --jql "project = WB ORDER BY updated DESC" --customer GResearch --pretty
```

## Creating Issues

Only 3 required fields: Project (WB), Issue Type, Summary. Additional fields enhance triage.

### Bug creation

```bash
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py create \
  --type Bug --summary "SDK crash on large artifact upload" \
  --customer GResearch --priority P1 \
  --eng-team "SDK Team" --pretty
```

### Feature Request creation

```bash
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py create \
  --type "Feature Request" --summary "Support custom metric aggregation" \
  --customer GResearch --priority P2 --pretty
```

### Available create options

| Option | Description |
|---|---|
| `--type` | Issue type: Bug, "Feature Request", Story, Sub-task (required) |
| `--summary` | Issue summary (required) |
| `--description` | Detailed description |
| `--priority` | P0, P1, P2, P3, P4 |
| `--customer` | Customer name (sets customfield_10083) |
| `--eng-team` | Eng Team name (sets customfield_10084) |
| `--labels` | Space-separated labels |
| `--parent` | Parent issue key |
| `--project` | Project key (default: WB) |

## FE-UPDATE Convention

Structured comment format for tracking SE progress on customer tickets. See `.claude/rules/atlassian.md` for full convention details.

### Adding an FE-UPDATE (WRITE -- requires user confirmation)

```bash
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py fe-update \
  --key WB-123 --status waiting-on-prod-eng \
  --next-update 2026-03-20 --notes "Waiting on SDK team fix in v0.18.3" --pretty
```

### Statuses

| Status | Meaning |
|---|---|
| `waiting-on-prod-eng` | Blocked on product/engineering |
| `waiting-on-customer` | Ball is in customer's court |
| `resolved` | Done -- fix shipped, workaround provided, or satisfied |

### Reading FE-UPDATEs (READ -- auto-approved)

```bash
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py fe-updates --key WB-123 --pretty
```

Returns all FE-UPDATE comments with parsed status, next-update date, and notes. The `current_status` field shows the latest state.

## Read Operations

Safe to execute freely without user confirmation.

### issues.py

**Subcommands:**
- `view` -- View a single issue
- `list` -- List issues with filters (--assignee, --status, --type, --label, --customer)
- `search` -- Full JQL search with optional --customer filter
- `transitions` -- List available transitions for an issue
- `fe-updates` -- Retrieve FE-UPDATE comments from an issue

**Examples:**

```bash
# View an issue
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py view --key WB-123 --pretty

# List my issues in progress
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py list --assignee "allan.stevenson@wandb.com" --status "In Progress" --pretty

# List bugs for a customer
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py list --customer GResearch --type Bug --pretty

# Full JQL search
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py search --jql "project = WB AND status = 'Open' ORDER BY updated DESC" --max-results 20 --pretty

# List available transitions
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py transitions --key WB-123 --pretty
```

## Write Operations (Require Explicit User Confirmation)

**IMPORTANT: Never execute write operations without explicit user confirmation.** Before running any create, edit, transition, or assignment command, show the user exactly what will change and get their approval.

### issues.py (write subcommands)

**Subcommands:**
- `create` -- Create an issue (Bug, Feature Request, Story, Sub-task)
- `create-epic` -- Create an Epic (two-step: create, then update parent/priority/labels)
- `edit` -- Update fields on an existing issue
- `transition` -- Transition issue to a new status
- `assign` -- Assign or unassign an issue
- `comment` -- Add a comment
- `link` -- Link two issues
- `flag` -- Flag or unflag an issue
- `fe-update` -- Add a structured FE-UPDATE comment

## Common W&B SE Workflows

### Customer ticket review

```bash
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py list --customer GResearch --pretty
```

### File a customer bug

```bash
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py create --type Bug --summary "Customer bug: ..." --customer GResearch --priority P2 --pretty
```

### Check FE-UPDATE status on a ticket

```bash
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py fe-updates --key WB-123 --pretty
```

### Post an FE-UPDATE

```bash
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py fe-update --key WB-123 --status waiting-on-prod-eng --next-update 2026-03-20 --notes "Details here" --pretty
```

### Open issue in browser

```
https://wandb.atlassian.net/browse/WB-123
```

## Multi-Project Support

All examples default to the WB project. To target a different project, pass `--project`:

```bash
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py list --project FIELD --pretty
```

Issue keys like `FIELD-123` auto-resolve to their project -- no `--project` needed for view, edit, or transition commands.

## Troubleshooting

| Problem | Fix |
|---|---|
| `credentials_not_found` error | Ensure `ATLASSIAN_EMAIL`/`ATLASSIAN_TOKEN` are set in `~/.tsm-ai/.env` |
| `jira_error_401` | Check `ATLASSIAN_EMAIL` and `ATLASSIAN_TOKEN` in `~/.tsm-ai/.env` |
| `jira_error_403` | Check your Jira project permissions |
| `jira_error_404` | Verify the issue key or project exists |
| `invalid_transition` | Run `transitions --key` to see available status changes |
| `ModuleNotFoundError` | Run `cd .claude/skills/jira && uv sync` |

## Related Skills

- `/slack` -- Thread permalinks for issue descriptions and context gathering

## Safety Rules

- **Default to read-only.** All read operations (view, list, search, transitions, fe-updates) can be executed without asking.
- **Never write without confirmation.** Create, edit, transition, assign, comment, link, and fe-update operations must be explicitly approved by the user before execution.
- **Show what will change.** Before a write operation, display the issue key, field(s) being changed, and new value(s).
- **Use `--pretty` for user-facing output.** Makes JSON readable.
