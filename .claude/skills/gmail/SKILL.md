---
name: gmail
description: "Use when searching emails, reading message threads, or checking inbox content. Activate for email references, Gmail searches, or when gathering context from email conversations."
allowed-tools: Bash(uv run --project .claude/skills/gmail python .claude/skills/gmail/scripts/*.py *), Bash(./scripts/gmail-cdp-fetch.sh *)
requires-credentials:
  - GMAIL_APPSCRIPT_URL
  - GMAIL_APPSCRIPT_KEY
setup-skill: gmail-setup
auto-refresh: false
---

# Gmail API Operations

Read-only access to Gmail for searching messages, reading emails and threads, and listing labels. Uses a Google Apps Script web app as the backend, with requests routed through the Chrome debug instance (CDP) for Okta SSO authentication.

## Prerequisites

- `GMAIL_APPSCRIPT_URL` and `GMAIL_APPSCRIPT_KEY` configured in `~/.fe-skills/.env` (run `/gmail-setup` if not done)
- Chrome debug instance running: `./scripts/chrome-debug.sh start`
- Signed into Okta in the Chrome debug instance
- Python dependencies installed: `cd .claude/skills/gmail && uv sync`

## Python Tools

All Python tools output JSON to stdout and errors to stderr. Use `--pretty` for human-readable output.

**Invocation pattern:**
```bash
uv run --project .claude/skills/gmail python .claude/skills/gmail/scripts/<tool>.py <command> [options]
```

### messages.py

Search and read individual messages.

**Subcommands:**
- `search` - Search messages with Gmail query syntax
- `get` - Get a specific message by ID

**Examples:**
```bash
# Search for messages
uv run --project .claude/skills/gmail python .claude/skills/gmail/scripts/messages.py search --query "from:user@example.com" --max-results 20

# Search unread messages
uv run --project .claude/skills/gmail python .claude/skills/gmail/scripts/messages.py search --query "is:unread" --max-results 10

# Search with multiple operators
uv run --project .claude/skills/gmail python .claude/skills/gmail/scripts/messages.py search --query "from:@wandb.com newer_than:7d has:attachment"

# Get a specific message (full content with body)
uv run --project .claude/skills/gmail python .claude/skills/gmail/scripts/messages.py get --id MESSAGE_ID

# Get message metadata only (headers, no body)
uv run --project .claude/skills/gmail python .claude/skills/gmail/scripts/messages.py get --id MESSAGE_ID --format metadata

# Get minimal message info (ID and status only)
uv run --project .claude/skills/gmail python .claude/skills/gmail/scripts/messages.py get --id MESSAGE_ID --format minimal
```

### threads.py

List and read full email threads (conversations).

**Subcommands:**
- `list` - List threads matching a query
- `get` - Get all messages in a thread

**Examples:**
```bash
# List threads matching a query
uv run --project .claude/skills/gmail python .claude/skills/gmail/scripts/threads.py list --query "subject:meeting newer_than:30d" --max-results 10

# Get full thread (all messages with bodies)
uv run --project .claude/skills/gmail python .claude/skills/gmail/scripts/threads.py get --id THREAD_ID

# Get thread metadata only
uv run --project .claude/skills/gmail python .claude/skills/gmail/scripts/threads.py get --id THREAD_ID --format metadata
```

### labels.py

List labels and get label details.

**Subcommands:**
- `list` - List all labels (system + custom)
- `get` - Get a specific label by name

**Examples:**
```bash
# List all labels
uv run --project .claude/skills/gmail python .claude/skills/gmail/scripts/labels.py list

# Get label details (includes unread count)
uv run --project .claude/skills/gmail python .claude/skills/gmail/scripts/labels.py get --name "Work"
```

## Gmail Search Query Syntax

Use these operators in the `--query` parameter for `messages.py search` and `threads.py list`:

| Operator | Example | Purpose |
|---|---|---|
| `from:` | `from:user@example.com` | Messages from a sender |
| `to:` | `to:me` | Messages sent to you |
| `subject:` | `subject:meeting` | Subject line contains term |
| `is:unread` | `is:unread` | Unread messages |
| `is:starred` | `is:starred` | Starred messages |
| `label:` | `label:INBOX` | Messages with a label |
| `has:attachment` | `has:attachment` | Messages with attachments |
| `after:` | `after:2026/01/01` | Messages after a date |
| `before:` | `before:2026/02/01` | Messages before a date |
| `newer_than:` | `newer_than:7d` | Messages newer than N days |
| `older_than:` | `older_than:30d` | Messages older than N days |
| `filename:` | `filename:pdf` | Attachments by filename |
| `in:` | `in:anywhere` | Search in all mail including spam/trash |

Combine operators: `from:user@example.com after:2026/01/01 has:attachment`

## Message Format Options

| Format | Contents | Use case |
|---|---|---|
| `minimal` | Message ID, date, read/starred status | Fastest; checking status |
| `metadata` | Headers (From, To, Subject, Date) + snippet | Scanning messages without bodies |
| `full` | Complete message with plain text and HTML body | Reading full email content (default) |

## Pagination

> **Results are NOT auto-paginated.** Gmail returns a limited number of results per call. Check the `nextStart` field in the response — if present, use `--start <nextStart>` to get the next page. Continue until `nextStart` is absent or `hasMore` is false.

- Use `--max-results N` to control page size (default 20)
- Use `--start N` for the next page offset

### Paginating through all results

```bash
# First page
uv run --project .claude/skills/gmail python .claude/skills/gmail/scripts/messages.py search --query "from:@customer.com" --max-results 20

# If response contains "nextStart": 20, get next page
uv run --project .claude/skills/gmail python .claude/skills/gmail/scripts/messages.py search --query "from:@customer.com" --max-results 20 --start 20

# Continue until "hasMore" is false or "nextStart" is absent
```

## Common Workflows

**Search for customer emails:**
```bash
uv run --project .claude/skills/gmail python .claude/skills/gmail/scripts/messages.py search --query "from:@customer.com newer_than:30d"
```

**Find escalation emails:**
```bash
uv run --project .claude/skills/gmail python .claude/skills/gmail/scripts/messages.py search --query "subject:escalation OR subject:urgent newer_than:7d"
```

**Read unread inbox:**
```bash
uv run --project .claude/skills/gmail python .claude/skills/gmail/scripts/messages.py search --query "is:unread label:INBOX"
```

**Get full conversation from a message:**
1. Search to find a message — note the `threadId` from the result
2. Use `threads.py get --id THREAD_ID` to read the full conversation

## All Operations are Read-Only

All Python tools perform read-only operations and require no user confirmation. The Apps Script only uses `GmailApp` read methods — no messages can be sent, modified, or deleted.

## Error Checking

Common errors:
- **`unauthorized`**: API key mismatch — check `GMAIL_APPSCRIPT_KEY` in `~/.fe-skills/.env` matches the key in your Apps Script
- **`not_found`**: Message or thread ID not found — verify the ID
- **Chrome not running**: Start with `./scripts/chrome-debug.sh start`
- **Timeout**: Okta session may have expired — sign in again in the Chrome debug instance
- **`internal`**: Apps Script execution error — check the Executions log in the Apps Script editor

## Safety Rules

- **Default to read-only.** All operations can be executed without asking.
- **The Apps Script uses only read methods** — no write operations are possible.
- **Prefer search over browsing.** Use `messages.py search` with targeted queries rather than listing all messages.
- **Respect privacy.** Only access emails relevant to the user's request.
