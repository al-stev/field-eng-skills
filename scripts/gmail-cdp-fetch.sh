#!/usr/bin/env bash
# Fetch a URL through the Chrome debug instance via CDP.
# Chrome handles all auth (Okta SSO, Google SAML) transparently.
# Outputs the page body (expected JSON) to stdout.
#
# Usage: gmail-cdp-fetch.sh "<full_url>"
# Requires: chrome-debug.sh running, jq, node v22+

set -euo pipefail

CDP_PORT=9222

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <url>" >&2
  exit 1
fi

FETCH_URL="$1"

# --- Preflight checks ---

if ! command -v jq &>/dev/null; then
  echo "Error: jq is required but not installed." >&2
  exit 1
fi

if ! command -v node &>/dev/null; then
  echo "Error: node is required but not installed." >&2
  exit 1
fi

if ! curl -s "http://localhost:$CDP_PORT/json/version" &>/dev/null; then
  echo "Error: Chrome debug instance not running on port $CDP_PORT." >&2
  echo "Run: ./scripts/chrome-debug.sh start" >&2
  exit 1
fi

# --- Create a new blank tab ---

TAB_INFO=$(curl -s -X PUT "http://localhost:$CDP_PORT/json/new")
TAB_ID=$(echo "$TAB_INFO" | jq -r '.id')
WS_URL=$(echo "$TAB_INFO" | jq -r '.webSocketDebuggerUrl')

if [[ -z "$TAB_ID" || "$TAB_ID" == "null" ]]; then
  echo "Error: failed to create new Chrome tab." >&2
  exit 1
fi

if [[ -z "$WS_URL" || "$WS_URL" == "null" ]]; then
  echo "Error: no WebSocket URL for new tab." >&2
  curl -s -X PUT "http://localhost:$CDP_PORT/json/close/$TAB_ID" > /dev/null 2>&1 || true
  exit 1
fi

# Ensure tab is closed on exit (cleanup)
cleanup() {
  curl -s -X PUT "http://localhost:$CDP_PORT/json/close/$TAB_ID" > /dev/null 2>&1 || true
}
trap cleanup EXIT

# --- Navigate and extract response via CDP ---

FETCH_URL="$FETCH_URL" WS_URL="$WS_URL" node -e "
const url = process.env.FETCH_URL;
const wsUrl = process.env.WS_URL;

const ws = new WebSocket(wsUrl);
const timeout = setTimeout(() => {
  console.error('Timeout: page did not return JSON within 60s.');
  console.error('Ensure you are signed into Okta in the Chrome debug instance.');
  process.exit(1);
}, 60000);

ws.addEventListener('open', () => {
  ws.send(JSON.stringify({ id: 1, method: 'Page.navigate', params: { url } }));
});

let pollId = 2;
function poll() {
  ws.send(JSON.stringify({
    id: pollId++,
    method: 'Runtime.evaluate',
    params: { expression: 'document.body?.innerText || \"\"', returnByValue: true }
  }));
}

ws.addEventListener('message', (event) => {
  const msg = JSON.parse(event.data);

  if (msg.id === 1) {
    // Navigation initiated — wait for redirects then start polling
    setTimeout(poll, 2000);
    return;
  }

  if (msg.id >= 2) {
    const text = (msg.result?.result?.value || '').trim();
    if (text) {
      try {
        JSON.parse(text); // Validate it's JSON
        clearTimeout(timeout);
        process.stdout.write(text);
        ws.close();
        process.exit(0);
      } catch {}
    }
    // Not valid JSON yet (still redirecting), poll again
    setTimeout(poll, 1000);
  }
});

ws.addEventListener('error', (err) => {
  console.error('WebSocket error:', err.message);
  process.exit(1);
});
"
