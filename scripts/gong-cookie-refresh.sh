#!/usr/bin/env bash
# Extract session cookies from the Chrome debug instance for Gong via CDP.
# Requires: chrome-debug.sh running, jq, node v22+

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/tsm-env.sh"

CDP_PORT=9222
GONG_URL="https://app.gong.io"

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

# --- Get WebSocket URL ---

# Prefer a page target; fall back to browser-level endpoint
WS_URL=$(curl -s "http://localhost:$CDP_PORT/json" | jq -r '
  (map(select(.type == "page")) | first // empty) .webSocketDebuggerUrl
  // empty
')

if [[ -z "$WS_URL" ]]; then
  WS_URL=$(curl -s "http://localhost:$CDP_PORT/json/version" | jq -r '.webSocketDebuggerUrl // empty')
fi

if [[ -z "$WS_URL" ]]; then
  echo "Error: could not obtain CDP WebSocket URL." >&2
  exit 1
fi

# --- Extract all cookies for Gong domain via CDP ---

COOKIE_JSON=$(node -e "
const ws = new WebSocket('$WS_URL');
const timeout = setTimeout(() => { console.error('Timeout waiting for CDP response'); process.exit(1); }, 10000);
ws.addEventListener('open', () => {
  ws.send(JSON.stringify({ id: 1, method: 'Network.getCookies', params: { urls: ['$GONG_URL'] } }));
});
ws.addEventListener('message', (event) => {
  const msg = JSON.parse(event.data);
  if (msg.id === 1) {
    clearTimeout(timeout);
    const cookies = (msg.result?.cookies || []);
    if (cookies.length === 0) {
      console.error('No cookies found for $GONG_URL. Are you signed in to Gong?');
      ws.close();
      process.exit(1);
    }
    // Output all cookies as JSON array
    process.stdout.write(JSON.stringify(cookies));
    ws.close();
    process.exit(0);
  }
});
ws.addEventListener('error', (err) => { console.error('WebSocket error:', err.message); process.exit(1); });
")

if [[ -z "$COOKIE_JSON" ]]; then
  echo "Error: failed to extract Gong cookies." >&2
  exit 1
fi

# --- Build cookie header string from all cookies ---

COOKIE_HEADER=$(echo "$COOKIE_JSON" | jq -r '[.[] | "\(.name)=\(.value)"] | join("; ")')

if [[ -z "$COOKIE_HEADER" ]]; then
  echo "Error: could not build cookie header from Gong cookies." >&2
  exit 1
fi

# --- Save cookie header ---
# Cookie header is too long for sed substitution in tsm_save, so handle directly.

mkdir -p "$(dirname "$TSM_ENV")" && chmod 700 "$(dirname "$TSM_ENV")"
if grep -q "^GONG_COOKIE=" "$TSM_ENV" 2>/dev/null; then
  grep -v "^GONG_COOKIE=" "$TSM_ENV" > "$TSM_ENV.tmp" && mv "$TSM_ENV.tmp" "$TSM_ENV"
fi
echo "GONG_COOKIE=$COOKIE_HEADER" >> "$TSM_ENV"
chmod 600 "$TSM_ENV"
echo "Saved GONG_COOKIE to $TSM_ENV ($(echo "$COOKIE_JSON" | jq 'length') cookies)"

# --- Verify by fetching Gong homepage ---

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -L --max-redirs 5 "$GONG_URL" -H "Cookie: $COOKIE_HEADER")

if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "302" || "$HTTP_CODE" == "307" ]]; then
  echo "Verification passed: Gong returned HTTP $HTTP_CODE."
else
  echo "Warning: Gong returned HTTP $HTTP_CODE." >&2
  echo "The cookies were saved but may be expired or invalid." >&2
  exit 1
fi
