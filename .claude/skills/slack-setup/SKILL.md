---
name: slack-setup
description: One-time Slack session token setup for reading messages, searching channels, and posting from Claude Code.
disable-model-invocation: true
allowed-tools: Bash(chmod *), Bash(curl -s "https://slack.com/api/*" *), Bash(./scripts/chrome-debug.sh *), Bash(./scripts/slack-credential-refresh.sh)
---

# Slack Setup

One-time setup for Slack API access used by the `/slack` skill.

## Prerequisites

- A CoreWeave Slack account (`coreweave.slack.com`)
- Signed in to Slack in your browser

## Method 1: Automated via Chrome Debug Instance (Recommended)

Uses a dedicated Chrome instance with remote debugging to programmatically extract the session token and cookie — no manual DevTools required.

**Requirements:** `jq`, `node` v22+ (both pre-installed).

### Step 1: Start the Chrome Debug Instance

```bash
./scripts/chrome-debug.sh start
```

This launches an isolated Chrome window with Grafana and Slack pre-loaded. If it's your first time, sign in to the CoreWeave workspace in the Slack tab.

### Step 2: Extract the Credentials

```bash
./scripts/slack-credential-refresh.sh
```

This extracts the `xoxc-` token and `d` cookie via CDP, saves them as `SLACK_TOKEN` and `SLACK_COOKIE` in `~/.tsm-ai/.env`, and verifies API access automatically.

### Step 3: Verify (optional)

The script runs verification automatically. To manually confirm:

```bash
curl -s "https://slack.com/api/auth.test" -H "Authorization: Bearer $(grep '^SLACK_TOKEN=' ~/.tsm-ai/.env | cut -d= -f2-)" -b "d=$(grep '^SLACK_COOKIE=' ~/.tsm-ai/.env | cut -d= -f2-)" | python3 -m json.tool
```

## Method 2: Manual Extraction (Fallback)

Use this if the automated method isn't available or isn't working.

### Overview

The CoreWeave workspace requires admin approval for Slack apps, so we use a session token (`xoxc-`) extracted from the browser instead. This token requires a companion `d` cookie for authentication.

### Step 1: Extract the Token and Cookie

1. Open https://app.slack.com in your browser (make sure you're signed in to the CoreWeave workspace)
2. Open DevTools (**F12** or **Cmd+Option+I**)
3. Go to the **Network** tab
4. Filter by `api/` in the filter bar
5. Perform any action in Slack (e.g., switch channels) to trigger an API request
6. Click any request to `https://edgeapi.slack.com/cache/...` or similar
7. In the **Payload** tab, find the `token` parameter — it starts with `xoxc-`
8. In the **Headers** tab under **Request Headers**, find the `Cookie` header and locate the `d=xoxd-...` value

Alternatively, try the browser console:

```js
JSON.parse(localStorage.localConfig_v2).teams[Object.keys(JSON.parse(localStorage.localConfig_v2).teams)[0]].token
```

For the cookie: go to **Application** tab → **Cookies** → `https://app.slack.com` → find the cookie named `d` (value starts with `xoxd-`).

### Step 2: Save the Credentials

Add the token and cookie to `~/.tsm-ai/.env`:

```bash
mkdir -p ~/.tsm-ai && chmod 700 ~/.tsm-ai
cat >> ~/.tsm-ai/.env << 'EOF'
SLACK_TOKEN=xoxc-YOUR-TOKEN-HERE
SLACK_COOKIE=xoxd-YOUR-COOKIE-HERE
EOF
chmod 600 ~/.tsm-ai/.env
```

Replace the placeholder values with the actual token and cookie from Step 1.

### Step 3: Verify

```bash
curl -s "https://slack.com/api/auth.test" -H "Authorization: Bearer $(grep '^SLACK_TOKEN=' ~/.tsm-ai/.env | cut -d= -f2-)" -b "d=$(grep '^SLACK_COOKIE=' ~/.tsm-ai/.env | cut -d= -f2-)" | python3 -m json.tool
```

Should return JSON with `"ok": true` and your user info.

Then test search:

```bash
curl -s "https://slack.com/api/search.messages?query=hello&count=1" -H "Authorization: Bearer $(grep '^SLACK_TOKEN=' ~/.tsm-ai/.env | cut -d= -f2-)" -b "d=$(grep '^SLACK_COOKIE=' ~/.tsm-ai/.env | cut -d= -f2-)" | python3 -m json.tool
```

Should return `"ok": true` with search results.

## Token Renewal

Session tokens expire when you sign out of Slack in your browser or after extended inactivity. To refresh:

- **Automated:** Re-run `./scripts/slack-credential-refresh.sh` (Chrome debug instance must be running)
- **Manual:** Repeat Method 2 Steps 1-2

## Troubleshooting

### `"ok": false, "error": "invalid_auth"`

- The token or cookie may have expired — refresh them using the method above
- Verify `SLACK_TOKEN` in `~/.tsm-ai/.env` starts with `xoxc-` and `SLACK_COOKIE` starts with `xoxd-`
- Make sure there's no trailing whitespace in the values

### `"ok": false, "error": "not_authed"`

- The `Authorization` header or `d` cookie is missing
- `xoxc-` tokens **require** both the token and the cookie — check that both `SLACK_TOKEN` and `SLACK_COOKIE` are set in `~/.tsm-ai/.env`

### `"ok": false, "error": "missing_scope"`

- Session tokens inherit your user's full permissions, so this is uncommon
- If it occurs, the `needed` field in the response shows which scope is missing

### Search returns no results

- Make sure you're searching terms that exist in channels you have access to
- Try a broader query like `hello` to confirm search works at all

### Chrome debug: no Slack tab found

- You need a tab open to `app.slack.com` in the debug Chrome window. Open it, sign in, and re-run the refresh script.
- If you closed the tab, navigate to `https://app.slack.com` in the debug Chrome instance.

### Chrome debug: xoxc- token not found

- Make sure you're fully signed in to the CoreWeave workspace (not just the Slack landing page).
- Try refreshing the Slack tab in Chrome, wait a few seconds, then re-run the script.

### Chrome debug: port 9222 already in use

- Another process is using the CDP port. Run `lsof -i :9222` to identify it.
- Stop the conflicting process or use `./scripts/chrome-debug.sh stop` if it's a stale instance.

### Chrome debug: CDP endpoint not responding

- Chrome may still be loading. Wait a few seconds and try `./scripts/chrome-debug.sh status`.
- If persistent, stop and restart: `./scripts/chrome-debug.sh stop && ./scripts/chrome-debug.sh start`
