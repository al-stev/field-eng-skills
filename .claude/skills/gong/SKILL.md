---
name: gong
description: "Use when searching call recordings, reading transcripts, or reviewing conversation summaries. Activate for Gong call IDs, meeting recordings, customer call history, or call intelligence data."
allowed-tools: Bash(uv run --project .claude/skills/gong python .claude/skills/gong/scripts/*.py *), Bash(./scripts/gong-cookie-refresh.sh)
requires-credentials:
  - GONG_COOKIE
setup-skill: gong-setup
service-url: https://app.gong.io
auto-refresh: true
refresh-script: ./scripts/gong-cookie-refresh.sh
---

# Gong Call Operations

Access Gong for call recordings, transcripts, and conversation intelligence using Python tools with automatic credential refresh.

## Prerequisites

- `GONG_COOKIE` configured in `~/.tsm-ai/.env` (run `/gong-setup` if not done)
- Chrome debug instance running (`./scripts/chrome-debug.sh start`) for cookie auto-refresh
- Python dependencies installed: `cd .claude/skills/gong && uv sync`

## Credential Refresh

Session cookies expire when the Okta session ends. Python tools **automatically detect auth failures and refresh credentials** without user intervention. The refresh process:

1. Detects authentication failure (HTTP 401/403 or empty response)
2. Calls `./scripts/gong-cookie-refresh.sh` to extract fresh cookies from Chrome
3. Retries the request with the new session cookies
4. Returns the result transparently

## Python Tools

All Python tools output JSON to stdout and errors to stderr. Use `--pretty` for human-readable output.

**Invocation pattern:**
```bash
uv run --project .claude/skills/gong python .claude/skills/gong/scripts/<tool>.py <command> [options]
```

### calls.py

Call listing, details, transcripts, summaries, and search.

**Subcommands:**
- `list` - List recent calls (my calls)
- `view` - View call details (collaborators + AI summary)
- `transcript` - Get full call transcript with word-level timing (JSON)
- `transcript-text` - Get call transcript as plain text (speaker: text format)
- `spotlight` - Get AI-generated call summary (brief, key points, next steps)
- `search` - Search calls by keyword in title/owner
- `explore-cookies` - Debug: list cookies for the Gong domain
- `explore-api` - Debug: fetch any Gong URL via CDP (Chrome navigation)

**Examples:**
```bash
# List recent calls
uv run --project .claude/skills/gong python .claude/skills/gong/scripts/calls.py list --limit 10 --pretty

# View call details (collaborators + summary)
uv run --project .claude/skills/gong python .claude/skills/gong/scripts/calls.py view --call-id 8714105745982611438 --pretty

# Get full transcript as JSON (with word-level timing)
uv run --project .claude/skills/gong python .claude/skills/gong/scripts/calls.py transcript --call-id 8714105745982611438 --pretty

# Get transcript as readable text
uv run --project .claude/skills/gong python .claude/skills/gong/scripts/calls.py transcript-text --call-id 8714105745982611438

# Get AI summary with key points and next steps
uv run --project .claude/skills/gong python .claude/skills/gong/scripts/calls.py spotlight --call-id 8714105745982611438 --pretty

# Search calls by keyword
uv run --project .claude/skills/gong python .claude/skills/gong/scripts/calls.py search --query "mercado" --limit 5 --pretty
```

## Salesforce Cross-Reference

Gong calls are synced to Salesforce as `Gong__Gong_Call__c` objects. To find Gong call IDs:

```sql
SELECT Id, Gong__Call_ID__c, Gong__Title__c, Gong__Call_Start__c,
       Gong__Call_Brief__c, Gong__View_call__c
FROM Gong__Gong_Call__c
WHERE Gong__Primary_Account__c = '<account_id>'
ORDER BY Gong__Call_Start__c DESC
```

The `Gong__Call_ID__c` field contains the 19-digit Gong call ID used with the `--call-id` parameter.

## All Operations are Read-Only

All Python tools perform read-only operations and require no user confirmation.

## API Reference

### URLs

- **Web app**: `https://app.gong.io` (redirects to region-specific subdomain)
- **Region-specific base**: `https://<region>.app.gong.io`
- **Public API** (requires API key): `https://api.gong.io/v2/`

### W&B Instance

| Property | Value |
|---|---|
| Workspace ID | `315301294163453491` (`GONG_WORKSPACE_ID` in `~/.tsm-ai/.env`) |
| Company ID | `4819131706209630954` (appears in profile image URLs, stored as `ajs_group_id` cookie) |
| Base URL | `https://us-39259.app.gong.io` (`GONG_BASE_URL` in `~/.tsm-ai/.env`) |
| Company name | W&B |

**Discovery notes:** The workspace ID is found in the `workspace-id=` query param of network requests in DevTools (NOT the `ajs_group_id` cookie, which is the company ID). The base URL region (`us-39259`) is in the `cell` JWT cookie. The `gong-cookie-refresh.sh` script auto-discovers the base URL from the cookie, but the workspace ID must be set manually.

### Cookie Details

Cookie format is full header string (`name1=val1; name2=val2`). Python clients parse into individual cookies for the `requests` session.

| Cookie | Purpose |
|---|---|
| `g-session` | Main Gong session token (base64) |
| `cell` | JWT with user/company context |
| `AWSALB` / `AWSALBCORS` | AWS ALB sticky session |
| `cf_clearance` | Cloudflare bot clearance |

### Internal API Endpoints

All endpoints use the region-specific base URL. Query parameters use `call-id` (not `callId`).

**Call Listing:**

| Endpoint | Method | Purpose |
|---|---|---|
| `/ajax/home/calls/my-calls?workspace-id=<ws_id>` | GET | List my recent calls |
| `/ajax/home/inbox/?workspace-id=<ws_id>` | GET | Inbox items |
| `/ajax/home/calls/listen-later-counter?workspace-id=<ws_id>` | GET | Listen later count |

**Call Details:**

| Endpoint | Method | Purpose |
|---|---|---|
| `/call/detailed-transcript?call-id=<id>` | GET | Full transcript with word-level timing |
| `/ajax/get-call-spotlight?call-id=<id>&token&should-regenerate=false` | GET | AI summary, key points, next steps |
| `/json/call/get-collaborators?call-id=<id>` | GET | Call participants with roles |
| `/json/call/filler-terms?call-id=<id>` | GET | Filler word analytics |
| `/json/call/get-potential-internal-shares?call-id=<id>` | GET | Internal share options |
| `/json/call/get-current-external-shares?call-id=<id>` | GET | Current external shares |
| `/ajax/call-feedback?call-id=<id>` | GET | Call feedback/scoring |
| `/ajax/get-call-translation-preferences?call-id=<id>` | GET | Translation preferences |
| `/ajax/ask-me-anything/get-call-data?call-id=<id>&tkn=` | GET | AMA call data |

**Account / Opportunity:**

| Endpoint | Method | Purpose |
|---|---|---|
| `/ajax/account/opportunities?account-id=<id>&workspace-id=<ws_id>` | GET | Account opportunities |

**Search:**

| Endpoint | Method | Purpose |
|---|---|---|
| `/search-box/ajax/read-recent-searches?workspace-id=<ws_id>` | GET | Recent searches |

**Common / Utility:**

| Endpoint | Method | Purpose |
|---|---|---|
| `/ajax/common/rtkn` | GET | CSRF token (JWT, use as `X-CSRF-TOKEN` header) |
| `/ajax/common/ksa` | GET | Unknown utility endpoint |
| `/v2/company/product-catalog` | GET | Product catalog |

### Public API Reference (for future use with API key)

If an API key becomes available, the public API provides:

| Endpoint | Method | Purpose |
|---|---|---|
| `/v2/calls` | GET | List calls by date range |
| `/v2/calls/{id}` | GET | Get specific call details |
| `/v2/calls/extensive` | POST | Detailed call data with filters |
| `/v2/calls/transcript` | POST | Get call transcripts |

Auth: Basic Auth with `base64(access_key:access_secret)`.

### CDP Fetch Fallback

When direct cookie-based HTTP calls fail, use the CDP fetch pattern (same as Gmail/GCalendar). This navigates Chrome to the URL and extracts page content:

```python
from gong_client import cdp_fetch
body = cdp_fetch("https://<region>.app.gong.io/call?id=12345")
```

Chrome handles Okta SSO transparently. The response may be JSON (if hitting an API endpoint) or HTML (if hitting a web page).

## Related Skills

- `/salesforce` — Account and opportunity context for call participants
- `/slack` — Follow-up threads and action items from calls
