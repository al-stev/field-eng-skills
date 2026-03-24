---
name: gong-setup
description: "One-time Gong session cookie setup. Run before first use of /gong, when GONG_COOKIE is missing or expired, or on 'set up Gong' or 'configure call recordings'."
disable-model-invocation: true
allowed-tools: Bash(chmod *), Bash(./scripts/chrome-debug.sh *), Bash(./scripts/gong-cookie-refresh.sh), Bash(uv run --project .claude/skills/gong python .claude/skills/gong/scripts/*.py *)
---

# Gong Setup

One-time setup for Gong access used by the `/gong` skill.

## Prerequisites

- Access to `https://app.gong.io` (requires Gong login via Okta SSO)
- Signed in to Gong in your browser

## Which method to use

Use Method 1 if you have Chrome debug running. Use Method 2 for one-off access.

## Method 1: Auto-refresh (Recommended)

Uses a dedicated Chrome instance with remote debugging to programmatically extract session cookies — no manual DevTools required.

**Requirements:** `jq`, `node` v22+ (both pre-installed).

### Step 1: Start the Chrome Debug Instance

```bash
./scripts/chrome-debug.sh start
```

This launches an isolated Chrome window with Gong pre-loaded. If it's your first time, sign in to Gong via Okta in the Chrome window that opens.

### Step 2: Extract Session Cookies

```bash
./scripts/gong-cookie-refresh.sh
```

This extracts all cookies for `app.gong.io` via CDP, saves them as `GONG_COOKIE` in `~/.tsm-ai/.env`, and verifies access automatically.

### Step 3: Install Python Dependencies

```bash
cd .claude/skills/gong && uv sync
```

### Step 4: Verify

The refresh script runs verification automatically. To manually confirm:

```bash
uv run --project .claude/skills/gong python .claude/skills/gong/scripts/calls.py list --limit 5 --pretty
```

## Method 2: Manual Cookie (Fallback)

Use this if auto-refresh isn't available or isn't working.

### Step 1: Extract Cookies

1. Open https://app.gong.io in your browser (make sure you're signed in)
2. Open DevTools (**F12** or **Cmd+Option+I**)
3. Go to the **Network** tab
4. Reload the page
5. Click on any request to `app.gong.io`
6. In the **Headers** tab, find the `Cookie` request header
7. Copy the entire cookie string value

### Step 2: Save the Cookies

Add the cookie string to `~/.tsm-ai/.env`:

```bash
mkdir -p ~/.tsm-ai && chmod 700 ~/.tsm-ai
echo 'GONG_COOKIE=YOUR-COOKIE-STRING-HERE' >> ~/.tsm-ai/.env
chmod 600 ~/.tsm-ai/.env
```

Replace `YOUR-COOKIE-STRING-HERE` with the full cookie string from Step 1.

### Step 3: Install Python Dependencies

```bash
cd .claude/skills/gong && uv sync
```

### Step 4: Verify

```bash
uv run --project .claude/skills/gong python .claude/skills/gong/scripts/calls.py list --limit 5 --pretty
```

## Session Renewal

Session cookies expire when your Okta session ends or after extended inactivity. To refresh:

- **Automated:** Re-run `./scripts/gong-cookie-refresh.sh` (Chrome debug instance must be running)
- **Manual:** Repeat Method 2 Steps 1-2
- **Automatic:** The `/gong` skill auto-detects expired sessions and runs the refresh script transparently

## Troubleshooting

### Authentication errors or empty responses

- The session cookies may have expired — refresh using the method above
- Make sure you are signed in to Gong in the Chrome debug instance
- Gong uses Okta SSO — ensure your Okta session is active

### Chrome debug: no cookies found

- You may not be signed in to Gong in the debug Chrome window. Open it and sign in via Okta, then re-run the refresh script.
- The Chrome debug instance may need to be restarted: `./scripts/chrome-debug.sh stop && ./scripts/chrome-debug.sh start`

### Chrome debug: port 9222 already in use

- Another process is using the CDP port. Run `lsof -i :9222` to identify it.
- Stop the conflicting process or use `./scripts/chrome-debug.sh stop` if it's a stale instance.

### ModuleNotFoundError

- Run `cd .claude/skills/gong && uv sync` to install Python dependencies.
