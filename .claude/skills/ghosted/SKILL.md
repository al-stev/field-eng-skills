---
name: ghosted
description: "Track customer silence on Slack threads. Use when the user wants to track a thread
  they're waiting on a customer reply for, or check which customers have gone silent. Trigger for
  /ghosted, 'who ghosted me', 'waiting on customer reply', 'customer hasn't responded',
  or 'check for ghosting'."
argument-hint: "[track <slack-url>] | [customer-name] | (no args = all customers)"
requires-credentials: ASANA_TOKEN, SLACK_TOKEN, SLACK_COOKIE
---

# Customer Silence Tracker

Tracks threads where you're waiting on a customer reply. Two modes:

- **Track mode**: Low-friction capture -- paste a Slack thread URL, creates an Asana task in "Waiting on Customer" so it's tracked.
- **Scan mode**: Checks all "Waiting on Customer" tasks that have Slack thread URLs. Reads each thread back. If the customer hasn't replied since the task was created/moved to Waiting, surfaces it. "GResearch has ghosted you on 3 threads."

## Track Mode (`/ghosted track <URL>`)

Pipeline:

### Step 1: Parse Slack URL

Extract `channel_id` and `thread_ts` from the pasted URL:

- URL format: `https://coreweave.slack.com/archives/C0ABC1234/p1709123456789012`
- `channel_id`: segment after `/archives/` (e.g., `C0ABC1234`)
- `thread_ts`: drop `p` prefix, insert `.` before last 6 digits (e.g., `1709123456.789012`)

If the URL doesn't match the expected pattern, ask the user to confirm it's a valid Slack thread URL.

### Step 2: Read the thread via Slack skill

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/channels.py thread \
  --channel-id <channel_id> --thread-ts <thread_ts> --pretty
```

### Step 3: Auto-resolve customer

Match `channel_id` against `templates/customers.yaml` `slack_channels[].id` to find the customer. If not found, ask the user which customer this is for.

### Step 4: Summarize thread context

Summarize the thread in 1-2 sentences: what was discussed, what response is expected from the customer.

### Step 5: Propose Asana task

Present the proposed task to the user for confirmation:

- **Project**: customer's `asana_project_gid` from `templates/customers.yaml`
- **Section**: "Waiting on Customer"
- **Name**: concise summary of what you're waiting for, with Jira ref if found (e.g., "Customer to provide repro steps (WB-1234)")
- **Notes**: Source Slack URL, thread summary, what response is expected
- **Priority**: P2 default (adjustable)
- **Due**: 7 days from now (reminder to follow up if still ghosted)

### Step 6: Create task (after user confirms)

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/mutate.py create \
  --project-gid <asana_project_gid> \
  --name "<task name>" \
  --section "Waiting on Customer" --assignee me --due <YYYY-MM-DD> --priority P2 \
  --notes "Source: <Slack thread URL>\n\nContext: <thread summary>\nWaiting for: <what response is expected>" \
  --pretty
```

### Step 7: Confirm creation

Output the task URL and remind: "Will check for reply when you run /ghosted"

## Scan Mode (`/ghosted` or `/ghosted GResearch`)

Pipeline:

### Step 1: Determine scope

- `/ghosted` (no args): scan all customers in `templates/customers.yaml` where `asana_project_gid` is not `PLACEHOLDER`
- `/ghosted GResearch`: scan only that customer (fuzzy-match against customers.yaml names)

### Step 2: Fetch "Waiting on Customer" tasks

For each customer in scope, fetch tasks:

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/query.py tasks \
  --project-gid <asana_project_gid> --limit 100 --pretty
```

Filter to tasks in the "Waiting on Customer" section (check `memberships[].section.name`).

### Step 3: Check each task for Slack URL

For each "Waiting on Customer" task that has a Slack URL in its notes:

1. Extract the Slack URL from the notes field using regex: `https://coreweave\.slack\.com/archives/[A-Z0-9]+/p\d+`
2. Parse `channel_id` and `thread_ts` from the URL
3. Read the thread:
   ```bash
   uv run --project .claude/skills/slack python .claude/skills/slack/scripts/channels.py thread \
     --channel-id <channel_id> --thread-ts <thread_ts> --pretty
   ```

### Step 4: Detect customer replies

Check if there's a customer reply AFTER the task's `created_at` (or `modified_at` if it was moved to Waiting later).

A "customer reply" is any message from a non-W&B user. Heuristic: user not in the SE's org, or user ID not matching known internal users.

- If **NO customer reply**: this thread is "ghosted" -- add to results
- If **customer HAS replied**: this thread is "alive" -- skip (optionally note that the task can be moved out of Waiting)

### Step 5: Sort and format output

Sort ghosted threads by days waiting (oldest first = most urgent). Format:

```
Ghosted Threads -- [date]

GResearch (3 ghosted):
- [12 days] Customer to provide repro steps (WB-1234)
  Thread: <URL> | Last W&B message: [date] | No customer reply since
- [8 days] Confirm migration timeline
  Thread: <URL> | Last W&B message: [date] | No customer reply since
- [3 days] Review SDK upgrade path
  Thread: <URL> | Last W&B message: [date] | No customer reply since

Suggested actions:
- Consider following up on threads older than 7 days
- Move tasks with customer replies to "In Progress" or "To Do"
```

If no ghosted threads found: "No ghosted threads. All Waiting on Customer items have received replies."

## Limitations

- Only checks tasks that have a Slack URL in the notes field. Tasks created without a Slack URL won't be scanned.
- Customer reply detection is heuristic -- it assumes non-internal users are customer users. May need refinement for shared channels with multiple external parties.
- Future enhancement: Slack emoji reaction (ghost emoji) bot for zero-friction capture.

## Safety Rules

- **Track mode**: user confirms before task creation. Never auto-create.
- **Scan mode**: read-only, no modifications.
- **Never post in Slack channels or threads.**

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No tasks found in Waiting on Customer | Check that tasks were created with `/ghosted track` or moved to the section manually |
| Slack thread returns empty | Thread may have been deleted or channel archived |
| Customer reply not detected | Reply detection is heuristic; check if the reply was from an internal user |
| `asana_project_gid` is PLACEHOLDER | Run `/asana setup-project` for the customer first |

## Related Skills

- `/asana` -- base skill for task CRUD
- `/nag` -- complementary: /ghosted watches customer silence, /nag watches your own stale tasks
- `/raid` -- ghosted threads may indicate a Risk worth adding to the RAID log
