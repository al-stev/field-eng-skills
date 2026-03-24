---
name: nag
description: "Scan your Asana tasks for overdue and stale items across all customers. Use when the
  user wants to check their backlog, asks 'what am I behind on', 'what's overdue', 'nag me',
  or wants a task hygiene check."
argument-hint: "[customer-name] (optional -- omit for all customers)"
requires-credentials: ASANA_TOKEN
---

# Stale & Overdue Actions Scanner

Your personal task hygiene scanner. Finds overdue and stale tasks across all your customer Asana projects. "You have 4 overdue items across 3 customers." This watches YOUR tasks, not the customer's silence (that's /ghosted).

## Pipeline

### Step 1: Determine scope

- `/nag` (no args): scan all customers in `templates/customers.yaml` where `asana_project_gid` is not `PLACEHOLDER`
- `/nag GResearch`: scan only that customer (fuzzy-match against customers.yaml names)

### Step 2: Fetch tasks for each customer

For each customer in scope, fetch tasks:

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/query.py tasks \
  --project-gid <asana_project_gid> --limit 100 --pretty
```

### Step 3: Scan the SE Team project

Also scan the SE Team project for internal/cross-cutting work:

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/query.py tasks \
  --project-gid 1213787150415828 --limit 100 --pretty
```

### Step 4: Filter to incomplete tasks

Only consider tasks where `completed` = `false`.

### Step 5: Classify each task

Apply staleness rules from `.claude/rules/asana.md`:

- **Overdue**: `due_on` is in the past and task is not completed. Red flag.
- **Stale**: task is in "To Do" or "In Progress" section AND `modified_at` is older than 7 days. Amber flag.
- **Exempt**: tasks in "Waiting on Customer", "Waiting on Eng", "Scheduled/Future" are not flagged for staleness (you're waiting on someone else or it's not yet actionable).

Note: a task can be both overdue AND stale. In that case, classify it as overdue (the more urgent signal).

### Step 6: Sort by urgency

Sort results in this priority order:
1. Overdue P0/P1 first (most urgent)
2. Overdue P2/P3 next
3. Stale P0/P1 next
4. Stale P2/P3 last

Within each group, sort by days overdue/stale (worst first).

### Step 7: Format output

```
Nag Report -- [date]

OVERDUE (4 items):
[P1] Chase SDK fix status (WB-1234) -- GResearch
  Due: 2026-03-15 (9 days overdue) | Section: In Progress
[P2] Prepare QBR deck -- GResearch
  Due: 2026-03-20 (4 days overdue) | Section: To Do
[P1] Update deployment docs -- SE Team
  Due: 2026-03-18 (6 days overdue) | Section: In Progress
[P3] Follow up on licensing question -- Acme Corp
  Due: 2026-03-22 (2 days overdue) | Section: To Do

STALE (2 items, 7+ days no update):
[P2] Review customer's architecture diagram -- GResearch
  Last updated: 2026-03-10 (14 days ago) | Section: In Progress
[P3] Draft migration guide -- SE Team
  Last updated: 2026-03-12 (12 days ago) | Section: To Do

Summary: 4 overdue + 2 stale across 3 projects
Suggested: Address overdue P0/P1 items first
```

If nothing is overdue or stale: "Clean slate! No overdue or stale tasks. You're on top of things."

## Priority Detection

Priority is read from the task's custom fields. If the Priority custom field is configured, use it directly. Otherwise, check for `[P0]`-`[P3]` prefix in the task name as a fallback.

Tasks without any priority signal are treated as P3 (lowest urgency) for sorting purposes.

## Safety Rules

- **Entirely read-only.** No task modifications.
- Respects staleness exemptions from `asana.md` rules (Waiting/Scheduled sections exempt).

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No tasks found | Check `asana_project_gid` in `templates/customers.yaml` is not `PLACEHOLDER` |
| Tasks without due dates | These can't be overdue, only stale. Consider adding due dates. |
| False stale flags | Task may have been updated in Asana UI but not via the skill. Check `modified_at`. |

## Related Skills

- `/ghosted` -- complementary: /nag watches your tasks, /ghosted watches customer silence
- `/asana` -- base skill for task queries
- `/raid` -- overdue items may indicate a Risk worth tracking
