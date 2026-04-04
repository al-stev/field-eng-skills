---
name: gcalendar
description: "Use when checking calendar events, scheduling meetings, or managing calendar entries. Activate for meeting scheduling, availability checks, or calendar event references."
allowed-tools: Bash(uv run --project .claude/skills/gcalendar python .claude/skills/gcalendar/scripts/*.py *), Bash(./scripts/gmail-cdp-fetch.sh *)
requires-credentials:
  - GCALENDAR_APPSCRIPT_URL
  - GCALENDAR_APPSCRIPT_KEY
setup-skill: gcalendar-setup
auto-refresh: false
---

# Google Calendar API Operations

Read and write access to Google Calendar for listing calendars, viewing events, and creating/updating/deleting events. Uses a Google Apps Script web app as the backend, with requests routed through the Chrome debug instance (CDP) for Okta SSO authentication.

## Prerequisites

- `GCALENDAR_APPSCRIPT_URL` and `GCALENDAR_APPSCRIPT_KEY` configured in `~/.tsm-ai/.env` (run `/gcalendar-setup` if not done)
- Chrome debug instance running: `./scripts/chrome-debug.sh start`
- Signed into Okta in the Chrome debug instance
- Python dependencies installed: `cd .claude/skills/gcalendar && uv sync`

## Python Tools

All Python tools output JSON to stdout and errors to stderr. Use `--pretty` for human-readable output.

**Invocation pattern:**
```bash
uv run --project .claude/skills/gcalendar python .claude/skills/gcalendar/scripts/<tool>.py <command> [options]
```

### calendars.py

List all calendars.

**Subcommands:**
- `list` - List all calendars (name, ID, access role, color, timezone)

**Examples:**
```bash
# List all calendars
uv run --project .claude/skills/gcalendar python .claude/skills/gcalendar/scripts/calendars.py list --pretty
```

### events.py

Event operations — read and write.

**Read subcommands:**
- `list` - List events in a date range
- `get` - Get event details by ID
- `today` - List today's events
- `upcoming` - List events in next N days (default 7)

**Write subcommands:**
- `create` - Create a new event
- `create-all-day` - Create an all-day event
- `update` - Update event fields
- `delete` - Delete an event

**Examples:**
```bash
# List today's events
uv run --project .claude/skills/gcalendar python .claude/skills/gcalendar/scripts/events.py today --pretty

# List upcoming events (next 7 days)
uv run --project .claude/skills/gcalendar python .claude/skills/gcalendar/scripts/events.py upcoming --days 7

# List events in a date range
uv run --project .claude/skills/gcalendar python .claude/skills/gcalendar/scripts/events.py list --start-date 2026-02-13 --end-date 2026-02-20

# Search events in a date range
uv run --project .claude/skills/gcalendar python .claude/skills/gcalendar/scripts/events.py list --start-date 2026-02-01 --end-date 2026-02-28 --query "standup"

# List events from a specific calendar
uv run --project .claude/skills/gcalendar python .claude/skills/gcalendar/scripts/events.py today --calendar-id "someone@wandb.com"

# Get a specific event
uv run --project .claude/skills/gcalendar python .claude/skills/gcalendar/scripts/events.py get --id EVENT_ID

# Create an event
uv run --project .claude/skills/gcalendar python .claude/skills/gcalendar/scripts/events.py create \
  --title "Team Standup" \
  --start "2026-02-14T10:00:00" \
  --end "2026-02-14T10:30:00" \
  --description "Daily sync" \
  --location "Zoom"

# Create an event with guests
uv run --project .claude/skills/gcalendar python .claude/skills/gcalendar/scripts/events.py create \
  --title "1:1 with Manager" \
  --start "2026-02-14T14:00:00" \
  --end "2026-02-14T14:30:00" \
  --guests "manager@wandb.com"

# Create an all-day event
uv run --project .claude/skills/gcalendar python .claude/skills/gcalendar/scripts/events.py create-all-day \
  --title "PTO" \
  --date "2026-02-14"

# Create a multi-day all-day event
uv run --project .claude/skills/gcalendar python .claude/skills/gcalendar/scripts/events.py create-all-day \
  --title "Conference" \
  --date "2026-03-10" \
  --end-date "2026-03-13" \
  --location "San Francisco"

# Update an event
uv run --project .claude/skills/gcalendar python .claude/skills/gcalendar/scripts/events.py update \
  --id EVENT_ID \
  --title "Updated Title" \
  --location "New Room"

# Reschedule an event
uv run --project .claude/skills/gcalendar python .claude/skills/gcalendar/scripts/events.py update \
  --id EVENT_ID \
  --start "2026-02-14T11:00:00" \
  --end "2026-02-14T11:30:00"

# Delete an event
uv run --project .claude/skills/gcalendar python .claude/skills/gcalendar/scripts/events.py delete --id EVENT_ID
```

## Common TSM Workflows

**Check today's schedule:**
```bash
uv run --project .claude/skills/gcalendar python .claude/skills/gcalendar/scripts/events.py today --pretty
```

**Check the week ahead:**
```bash
uv run --project .claude/skills/gcalendar python .claude/skills/gcalendar/scripts/events.py upcoming --days 7 --pretty
```

**Find meetings with a specific person:**
```bash
uv run --project .claude/skills/gcalendar python .claude/skills/gcalendar/scripts/events.py list \
  --start-date 2026-02-01 --end-date 2026-02-28 --query "person name"
```

**Block time for focused work:**
```bash
uv run --project .claude/skills/gcalendar python .claude/skills/gcalendar/scripts/events.py create \
  --title "Focus Time - Do Not Disturb" \
  --start "2026-02-14T09:00:00" \
  --end "2026-02-14T12:00:00"
```

**Schedule PTO:**
```bash
uv run --project .claude/skills/gcalendar python .claude/skills/gcalendar/scripts/events.py create-all-day \
  --title "PTO" --date "2026-03-01" --end-date "2026-03-03"
```

## Error Checking

Common errors:
- **`unauthorized`**: API key mismatch — check `GCALENDAR_APPSCRIPT_KEY` in `~/.tsm-ai/.env` matches the key in your Apps Script
- **`not_found`**: Event or calendar ID not found — verify the ID
- **Chrome not running**: Start with `./scripts/chrome-debug.sh start`
- **Timeout**: Okta session may have expired — sign in again in the Chrome debug instance
- **`internal`**: Apps Script execution error — check the Executions log in the Apps Script editor

## Safety Rules

- **Read operations execute without asking.** List, get, today, and upcoming can run freely.
- **Write operations require user confirmation.** Always confirm with the user before creating, updating, or deleting events. Display the event details being changed before proceeding.
- **Prefer the default calendar** unless the user specifies a different one.
- **Display event details before writes.** Show what will be created/changed/deleted and get explicit approval.
- **Be careful with guest invitations.** Adding guests sends email invitations — always confirm guest lists with the user.
- **Respect privacy.** Only access calendar data relevant to the user's request.
