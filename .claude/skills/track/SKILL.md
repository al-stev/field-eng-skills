---
name: track
description: "Quick-capture a Slack thread as an Asana task. Replaces Slack's 'Save for later' with something that actually surfaces. Use when you see something in Slack you need to come back to. Trigger for /track, 'track this', 'save this thread', 'remind me about this'."
argument-hint: "<slack-url> [one-liner description]"
requires-credentials:
  - ASANA_TOKEN
  - SLACK_TOKEN
  - SLACK_COOKIE
---

# Quick Track: Slack → Asana

Capture a Slack thread as an Asana task in one step. No extraction, no RAID, no Confluence — just a task with a link back to the thread. Due tomorrow by default.

## Usage

```
/track <slack-thread-url>
/track <slack-thread-url> Follow up on SDK issue
/track <slack-thread-url> --due friday
```

## Pipeline

### Step 1: Parse input

- **Slack URL** (required): Extract channel ID and thread timestamp from the URL
- **Description** (optional): One-liner for the task name. If omitted, Claude reads the thread and generates a short summary as the task name.
- **Due date** (optional): `--due <date>`. Default: tomorrow.

### Step 2: Resolve customer from channel

Extract the channel ID from the Slack URL. Look it up in `templates/customers.yaml`:

```python
# For each customer in customers.yaml:
#   For each slack_channel:
#     If channel.id matches the URL's channel ID → that's the customer
```

If the channel maps to a customer → use their `action_tracker_id` as the target Asana project.

If no match → ask the user which customer this is for, or create in the SE Team project (`1213787150415828`).

### Step 3: Fetch thread context

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/threads.py --url "<slack_url>" --pretty
```

Read the first few messages to understand context. If no description was provided, generate a concise task name (max 80 chars) from the thread content.

### Step 4: Create Asana task

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/mutate.py create \
  --project-gid <action_tracker_id> \
  --name "<description or generated summary>" \
  --section "To Do" \
  --assignee me \
  --due <tomorrow or specified date> \
  --priority P3 \
  --notes "Slack thread: <slack_url>" \
  --pretty
```

### Step 5: Confirm

```
Tracked: "<task name>"
Customer: <customer>
Due: <date>
Asana: <task URL>
Slack: <thread URL>
```

## Edge Cases

- **Channel not in customers.yaml**: Ask user for customer name, or default to SE Team project
- **Thread URL is a channel message, not a thread**: Still works — just captures the single message context
- **No Slack credentials**: Error with suggestion to run `/slack-setup`
- **No Asana credentials**: Error with suggestion to run `/asana-setup`

## Safety

- Creates tasks only — no modifications, no deletions
- Default priority P3 (low) — this is a reminder, not an escalation
- Always shows what will be created before creating it
