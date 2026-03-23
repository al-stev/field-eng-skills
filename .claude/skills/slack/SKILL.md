---
name: slack
description: "Use when searching Slack messages, reading channel history or threads, looking up users, or posting messages. Activate for any reference to Slack channels (#ext-*, #internal-*, #standup-*), message links, or user lookups in the CoreWeave workspace."
argument-hint: "[search query or channel action]"
allowed-tools: Bash(uv run --project .claude/skills/slack python .claude/skills/slack/scripts/*.py *), Bash(./scripts/slack-credential-refresh.sh)
---

# Slack API Operations

Interact with the CoreWeave Slack workspace via the Slack Web API.

Refer to `.claude/rules/coreweave-slack.md` for shared constants (API base URL, token path, channel IDs).

## Prerequisites

- `SLACK_TOKEN` and `SLACK_COOKIE` configured in `~/.tsm-ai/.env` (run `/slack-setup` if not done)
- Chrome debug instance running (`./scripts/chrome-debug.sh start`) for credential auto-refresh
- Python dependencies installed: `cd .claude/skills/slack && uv sync`

## Credential Refresh

Session tokens and cookies expire periodically. The Python tools automatically detect auth failures and refresh credentials transparently. You do not need to manually refresh — the tools handle this automatically by:

1. Detecting `"ok": false` with `"error": "invalid_auth"` or `"error": "token_expired"`
2. Running `./scripts/slack-credential-refresh.sh` to extract fresh credentials
3. Retrying the request once with the new credentials

If the tool exits with an error about credentials, ensure the Chrome debug instance is running: `./scripts/chrome-debug.sh start`

## Authentication

All Python tools automatically read credentials from `~/.tsm-ai/.env` (`SLACK_TOKEN` and `SLACK_COOKIE`). The custom WebClient implementation injects the cookie into every HTTP request, allowing the official Slack SDK to work with browser-based authentication.

## Tool Invocation

All tools are invoked using `uv run` with the skill's project directory:

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/TOOL.py [args]
```

The `--project` flag tells uv to use the skill's `pyproject.toml` and virtual environment. All tools:
- Output JSON to stdout
- Output errors to stderr
- Exit with code 0 on success, 1 on error
- Support `--pretty` flag for human-readable JSON

## Error Checking

**Slack always returns HTTP 200**, even on errors. You must check the `ok` field in the JSON response body:

```json
{"ok": true, ...}   // success
{"ok": false, "error": "channel_not_found"}  // error
```

After every API call, check that `"ok": true` before processing results. Common errors:

- **`invalid_auth`** / **`token_expired`**: Credentials expired. **Auto-refresh**: run `./scripts/slack-credential-refresh.sh` and retry the request
- **`missing_scope`**: Token lacks a required scope — the `needed` field shows which one
- **`channel_not_found`**: Bad channel ID — use `conversations.list` to look it up
- **`not_in_channel`**: You need to join the channel first
- **`ratelimited`**: Back off and retry; the `Retry-After` header indicates seconds to wait

## Read Operations (Default)

These operations are safe and do not modify any content. Use them freely.

### Search messages

The most powerful read operation. Searches across all channels the user has access to.

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/search.py --query "SEARCH_TERMS" --count 20 --sort timestamp --sort-dir desc
```

**Search modifiers** (include in the `query` parameter):

| Modifier | Example | Purpose |
|---|---|---|
| `in:#channel` | `in:#tsm-team` | Limit to a specific channel |
| `from:@user` | `from:@flabat` | Messages from a specific user |
| `before:YYYY-MM-DD` | `before:2026-01-01` | Messages before a date |
| `after:YYYY-MM-DD` | `after:2025-12-01` | Messages after a date |
| `during:YYYY-MM` | `during:2026-01` | Messages during a month |
| `has:link` | `has:link` | Messages containing a URL |
| `has:reaction` | `has:reaction` | Messages with emoji reactions |

Combine modifiers: `customer-name in:#tsm-team after:2026-01-01`

**Pagination**: Search uses page-based pagination. Use `--page N` (1-indexed):

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/search.py --query "TERMS" --count 20 --page 2
```

Check `messages.paging.pages` in the JSON response for total page count.

### List channels

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/channels.py list --types public_channel,private_channel --limit 200
```

To find a channel by name, add `exclude_archived=true` and search the results. Or filter by type:

| `types` value | What it returns |
|---|---|
| `public_channel` | Public channels only |
| `private_channel` | Private channels you belong to |
| `public_channel,private_channel` | Both (default for most use cases) |

### Get channel info

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/channels.py info --channel CHANNEL_ID
```

### Read channel history

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/channels.py history --channel CHANNEL_ID --limit 20
```

Optional parameters:
- `--oldest TIMESTAMP` — only messages after this Unix timestamp
- `--latest TIMESTAMP` — only messages before this Unix timestamp
- `--inclusive true` — include messages with the exact oldest/latest timestamps

### Read thread replies

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/threads.py replies --channel CHANNEL_ID --ts THREAD_TS --limit 100
```

The `--ts` parameter is the timestamp of the parent message (the thread root).

### Look up users

**List all users:**

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/users.py list --limit 200
```

**Get a specific user by ID:**

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/users.py info --user USER_ID
```

**Search for users by name:**

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/users.py search-name --name "David Silverio"
```

## Resolving Names to IDs

Slack API methods require IDs, not names. Use these patterns to resolve them.

### Channel name → Channel ID

Use `channels.py list` and search the results for the channel name, or parse the JSON output with `jq`:

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/channels.py list --limit 500 | jq -r '.channels[] | select(.name=="tsm-team") | .id'
```

Once you find a channel ID, save it to `slack-channels.md` (see "Remembering Channels and DMs" below).

### User display name → User ID

Use `users.py search-name` to find users by name:

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/users.py search-name --name "David"
```

This searches `real_name`, `display_name`, and `username` fields and returns all matches.

### User ID → DM channel ID

**Note:** DM channel creation is not yet implemented in the Python tools. Use the curl fallback for now:

```bash
curl -s "https://slack.com/api/conversations.open" -H "Authorization: Bearer $(grep '^SLACK_TOKEN=' ~/.tsm-ai/.env | cut -d= -f2-)" -b "d=$(grep '^SLACK_COOKIE=' ~/.tsm-ai/.env | cut -d= -f2-)" -H "Content-Type: application/json" -d '{"users": "USER_ID"}'
```

The response contains `channel.id` — this is the DM channel ID needed for history and messaging operations.

## Remembering Channels and DMs

When you discover a new channel ID or DM, save it to the user's `slack-channels.md` rule file. This file lives in the user-scoped project rules directory (`~/.claude/projects/<project>/rules/slack-channels.md`) — it is auto-loaded into context and not checked into git. See `.claude/rules/coreweave-slack.md` for details.

Add a row to the table:
- **Channels**: `| #channel-name | CHANNEL_ID | description |`
- **DMs**: `| DM (Person Name) | DM_CHANNEL_ID | username |`

Also save the person's details (Slack ID, username, email, title, timezone) to auto memory (`~/.claude/projects/<project>/memory/MEMORY.md`) under a `## People` section for future reference.

## Pagination (Cursor-Based)

Most endpoints (except search) use cursor-based pagination. The Python tools handle pagination automatically:

- **`users.py list`**: Automatically fetches all pages unless `--max-pages` is specified
- **`channels.py list`**: Single page only (increase `--limit` if needed)
- **Search**: Use `--page N` for page-based pagination

Check the JSON response for `response_metadata.next_cursor` to determine if more pages exist.

## Timestamps

Slack uses Unix timestamps with microsecond precision as unique message IDs (e.g., `1706123456.789012`). These are:
- Used as `ts` parameter to identify specific messages
- Used as `thread_ts` to identify thread parents
- Returned in `latest` / `oldest` fields for time ranges
- **Not human-readable** — convert to dates for display to the user

## Permalinks and Slack Connect Channels

**IMPORTANT:** Many customer channels (e.g. `#wandb-gresearch`) are **Slack Connect** channels shared across multiple workspaces. When building message links for the user:

- **Do NOT construct links manually** using `coreweave.slack.com/archives/...` — they will 404 on Slack Connect channels.
- **Always use the `permalink` field** returned by the search API (`data['messages']['matches'][N]['permalink']`). The API returns the correct domain automatically (often `weightsandbiases.slack.com` for W&B shared channels, or `gresearch.enterprise.slack.com` for GR-hosted channels).
- Search results include `permalink` — extract it alongside `ts`, `username`, and `text`.
- If a channel's `is_ext_shared` is `true`, it is a Slack Connect channel and manual link construction will not work.

## Write Operations (Require Explicit User Confirmation)

**IMPORTANT: Never execute write operations without explicit user confirmation.** Before running any write command, describe exactly what will be posted and where, and get the user's approval.

Write operations (posting, reactions, saved items) use curl fallbacks — see [`references/write-operations.md`](references/write-operations.md) for details.

## Common TSM Workflows

### Search for a customer across all channels

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/search.py --query "CUSTOMER_NAME" --count 20 --sort timestamp --sort-dir desc
```

### Read the latest messages in a team channel

First resolve the channel name to an ID, then:

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/channels.py history --channel CHANNEL_ID --limit 20
```

### Get full thread context

When a search result or channel message has `reply_count > 0` or a `thread_ts`, fetch the full thread:

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/threads.py replies --channel CHANNEL_ID --ts THREAD_TS --limit 100
```

### Find messages from a specific person about a topic

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/search.py --query "TOPIC from:@USERNAME" --count 20 --sort timestamp --sort-dir desc
```

## Safety Rules

- **Default to read-only.** All read operations (search, list, history, replies, user info) can be executed without asking.
- **Never write without confirmation.** `chat.postMessage` and `reactions.add` must be explicitly approved by the user before execution.
- **Show what will be sent.** Before a write operation, display the target channel, thread (if any), and full message text.
- **Prefer search over browsing.** Use `search.py` to find relevant messages rather than paging through channel history.
- **Never pipe output through `python3 -c` for JSON parsing.** Use `--pretty` on the tool itself, save output to a file and use the Read tool, or use smaller `--limit` values with `--oldest`/`--latest` to scope the API response. Ad-hoc inline scripts are error-prone and hard to debug.

## Related Skills

- `/freshdesk` — support tickets cross-referenced from Slack threads (`#supp-XXXXX` channels, `:ticket:` reactions)
- `/jira` — track work items originating from Slack conversations
- `/confluence` — write up findings from Slack discussions

## References

- **Write Operations** — curl fallbacks for posting messages, reactions, and saved items: [`references/write-operations.md`](references/write-operations.md)
