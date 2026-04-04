---
name: asana
description: "Use when tracking SE actions, customer task management, action items, programme tracking, or Asana project/task queries."
argument-hint: "[subcommand] [args...]"
allowed-tools: Bash(uv run --project .claude/skills/asana python .claude/skills/asana/scripts/*.py *)
requires-credentials:
  - ASANA_TOKEN
setup-skill: asana-setup
service-url: https://app.asana.com
auto-refresh: false
---

# Asana Task Management

Manage SE action items and customer task tracking in Asana using the official Python SDK. Asana is the SE's action-tracking layer above Jira -- Jira tracks engineering work, Asana tracks what the SE needs to do.

Refer to `.claude/rules/asana.md` for shared constants (workspace GID, project GIDs, section names, custom field mappings).

## Defaults

| Property | Value |
|---|---|
| Workspace GID | See `.claude/rules/asana.md` (configured during /asana-setup) |
| Default limit | `100` |
| SE Team project | See `.claude/rules/asana.md` (shared project for internal/cross-cutting work) |

## Prerequisites

- `ASANA_TOKEN` configured in `~/.fe-skills/.env` (run `/asana-setup` if not done)
- Python dependencies installed: `cd .claude/skills/asana && uv sync`
- Verify with: `uv run --project .claude/skills/asana python .claude/skills/asana/scripts/query.py projects --limit 3 --pretty`

## Python Tools

All Python tools output JSON to stdout and errors to stderr. Use `--pretty` for human-readable output.

**Invocation pattern:**
```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/<tool>.py <command> [options]
```

## Read Operations

All operations are read-only and can be executed without asking.

### query.py -- Read operations

**Subcommands:**

### projects -- List projects in workspace

```bash
# List projects (default limit 100)
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/query.py projects --pretty

# Filter by team
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/query.py projects --team-gid 1234567890 --limit 20 --pretty

# Exclude archived projects
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/query.py projects --archived false --pretty
```

### project -- Get project details

```bash
# By GID
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/query.py project --gid PROJECT_GID --pretty

# By URL
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/query.py project --url "https://app.asana.com/0/PROJECT_GID" --pretty
```

### sections -- List sections in a project

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/query.py sections --project-gid PROJECT_GID --pretty
```

### tasks -- List tasks in a project or section

```bash
# All tasks in a project
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/query.py tasks --project-gid PROJECT_GID --pretty

# Tasks in a specific section
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/query.py tasks --section-gid SECTION_GID --limit 50 --pretty

# By URL
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/query.py tasks --url "https://app.asana.com/0/PROJECT_GID" --limit 50 --pretty
```

### view -- Get task details

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/query.py view --gid TASK_GID --pretty
```

### subtasks -- List subtasks of a task

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/query.py subtasks --gid TASK_GID --pretty
```

### search -- Search tasks (Premium)

```bash
# Text search across workspace
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/query.py search --text "SDK crash" --pretty

# Search within a project
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/query.py search --text "follow up" --project-gid PROJECT_GID --pretty

# Search for incomplete tasks assigned to someone
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/query.py search --assignee 1234567890 --completed false --limit 50 --pretty
```

## Write Operations (Require Explicit User Confirmation)

**IMPORTANT: Never execute write operations without explicit user confirmation.** Before running any create, update, complete, move, or setup-project command, show the user exactly what will change and get their approval.

### mutate.py -- Write operations

### create -- Create a new task

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/mutate.py create \
  --project-gid PROJECT_GID --name "Follow up on SDK crash (WB-1234)" \
  --section "In Progress" --assignee me --due 2026-03-28 \
  --priority P1 --notes "Context from Slack thread..." --pretty
```

| Option | Description |
|---|---|
| `--project-gid` | Project GID (required) |
| `--name` | Task name (required) |
| `--section` | Section name (e.g., "In Progress") -- resolved by name |
| `--assignee` | `"me"` or user GID |
| `--due` | Due date (YYYY-MM-DD) |
| `--priority` | P0, P1, P2, P3 (custom field or name prefix fallback) |
| `--notes` | Task description text |

### update -- Update an existing task

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/mutate.py update \
  --gid TASK_GID --due 2026-04-01 --priority P0 --pretty
```

### complete -- Mark a task as completed

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/mutate.py complete --gid TASK_GID --pretty
```

### move -- Move a task to a different section

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/mutate.py move \
  --gid TASK_GID --section "Waiting on Eng" --project-gid PROJECT_GID --pretty
```

### setup-project -- Create a customer project with standard sections

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/mutate.py setup-project \
  --name "CustomerName" --pretty
```

Creates a project with 6 standard sections: To Do, In Progress, Waiting on Customer, Waiting on Eng, Scheduled/Future, Done. Attempts to create and attach a Priority custom field (requires Asana Starter plan).

## Common W&B SE Workflows

### Create a customer project (one-time per customer)

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/mutate.py setup-project --name "GResearch" --pretty
# Copy the project_gid to customers.yaml
```

### Track a new action item

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/mutate.py create \
  --project-gid PROJECT_GID --name "Chase SDK fix status (WB-1234)" \
  --section "To Do" --assignee me --due 2026-03-28 --priority P1 --pretty
```

### Move task when status changes

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/mutate.py move \
  --gid TASK_GID --section "Waiting on Eng" --project-gid PROJECT_GID --pretty
```

### Complete a task

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/mutate.py complete --gid TASK_GID --pretty
```

### Slack to Asana Quick Capture Workflow

When a user pastes a Slack thread URL and asks to create an Asana task, follow this 6-step workflow. The goal is zero-friction capture: paste a URL, confirm the suggested metadata, and get a fully-contextualized Asana task.

#### Step 1: Parse Slack URL

Extract `channel_id` and `thread_ts` from the pasted URL:

- URL format: `https://coreweave.slack.com/archives/C0ABC1234/p1709123456789012`
- `channel_id`: segment after `/archives/` (e.g., `C0ABC1234`)
- `thread_ts`: drop `p` prefix, insert `.` before last 6 digits (e.g., `1709123456.789012`)

If the URL doesn't match the expected pattern, ask the user to confirm it's a valid Slack thread URL.

#### Step 2: Read thread via Slack skill

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/channels.py thread \
  --channel-id <channel_id> --thread-ts <thread_ts> --pretty
```

Summarize the thread: what was discussed, who participated, what needs to happen.

#### Step 3: Detect Jira references

Scan thread text for `WB-\d+` patterns. For each match, optionally fetch the Jira issue summary:

```bash
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py get --key WB-XXXX --pretty
```

This provides richer task context and confirms the Jira issue exists.

#### Step 4: Auto-resolve customer project

Look up the `channel_id` in `templates/customers.yaml` under `slack_channels[].id` to find the matching customer. From that customer entry, read `action_tracker_id` (the Asana project GID when `action_tracker` is `"asana"`).

- If the channel is not in customers.yaml, ask the user which customer project to use.
- If `action_tracker_id` is `PLACEHOLDER`, warn the user and ask for the project GID or offer to run `setup-project`.

#### Step 5: Infer metadata

From the thread context and Jira references, suggest:

- **Task name**: concise action item with Jira suffix if applicable (e.g., "Follow up on SDK stability (WB-1234)")
- **Priority**: P0-P3 based on urgency signals (escalation language = P1+, routine follow-up = P2-P3)
- **Due date**: suggest based on context (urgent = 3 days, normal = 7 days, low = 14 days)
- **Section**: default "To Do", but "Waiting on Customer" if thread ends with a question to the customer, "Waiting on Eng" if waiting on a Jira fix
- **Assignee**: default "me"

Present the suggested metadata to the user for confirmation/adjustment.

#### Step 6: Create task with user confirmation

Show the full task details and get user approval, then create:

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/mutate.py create \
  --project-gid <PROJECT_GID> \
  --name "<task name>" \
  --section "<section>" --assignee me --due <YYYY-MM-DD> --priority <P0-P3> \
  --notes "Source: <Slack thread URL>\n\nContext: <thread summary>\nLinked Jira: <WB-XXXX if applicable>\nParticipants: <@names>" \
  --pretty
```

Confirm creation with the task URL.

This workflow converts ephemeral Slack conversations into tracked, actionable Asana tasks with full context preserved.

## Jira Cross-Linking Convention

Tasks that relate to a Jira issue include the issue key in parentheses at the end of the task name:
```
Follow up on SDK crash (WB-1234)
```

This is parsed with regex `\(WB-\d+\)` for bidirectional cross-linking in the customer dashboard.

## Troubleshooting

| Problem | Fix |
|---|---|
| `credentials_not_found` error | Run `/asana-setup` to configure PAT in `~/.fe-skills/.env` |
| `asana_api_error` with 401 | PAT may be revoked. Generate a new one via `/asana-setup` |
| `asana_api_error` with 403 | You don't have access to this resource. Check project permissions in Asana |
| `asana_api_error` with 404 | GID not found. Verify the GID or URL is correct |
| `invalid_input` for URL | Check URL matches `https://app.asana.com/1/...` or `https://app.asana.com/0/...` pattern |
| Search returns no results | Search is eventually consistent (10-60s delay). Also requires Premium Asana |
| `ModuleNotFoundError` | Run `cd .claude/skills/asana && uv sync` |
| Rate limit (429) | Wait for `Retry-After` seconds. Search has stricter limit (60/min) |
| Priority custom field fails (403) | Asana Starter plan required for custom fields. Skill falls back to name prefix `[P0]` |
| Workspace GID not configured | Run `/asana-setup` to auto-discover and set workspace GID |

## Safety Rules

- **Default to read-only.** All read operations (projects, project, sections, tasks, view, subtasks, search) can be executed without asking.
- **Never write without confirmation.** Create, update, complete, move, and setup-project operations must be explicitly approved by the user before execution.
- **Show what will change.** Before a write operation, display the task/project name, field(s) being changed, and new value(s).
- **Use `--pretty` for user-facing output.** Makes JSON readable.
- **Prefer targeted queries over bulk retrieval.** Use `--project-gid` or `--section-gid` to narrow results. Use `--limit` to cap large result sets.

## Related Skills

- `/slack` -- Thread context for Slack-to-Asana task creation
- `/jira` -- Engineering issue tracking (Asana tracks SE actions, Jira tracks eng work)
- `/customer-snapshot` -- Intelligence dashboard consumes Asana task data for SE Actions panel

## API Reference

### API Conventions

- **SDK**: `asana` -- official Asana Python SDK (auto-generated from OpenAPI spec).
- **Pagination**: Cursor-based. `limit` (1-100) and `offset` (opaque token). SDK handles pagination automatically via generators.
- **Field selection**: `opt_fields` parameter to request specific fields. Minimizing fields improves performance and avoids cost-based rate limits.
- **Rate limits**: 1,500 requests/minute (paid), 150 requests/minute (free). Search endpoint: 60 requests/minute. HTTP 429 with `Retry-After` header.
- **Response format**: `{"data": [...]}` for lists, `{"data": {...}}` for single objects. SDK unwraps `data` automatically.
- **GIDs**: All Asana resource IDs are numeric strings (16-19 digits), called `gid` in the API.
