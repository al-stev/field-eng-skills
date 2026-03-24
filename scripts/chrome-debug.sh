#!/usr/bin/env bash
# Manage a dedicated Chrome instance with remote debugging (CDP) on port 9222.
# Used by gong-cookie-refresh.sh and slack-credential-refresh.sh to
# programmatically extract session credentials.

set -euo pipefail

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PROFILE_DIR="$HOME/.chrome-debug"
PID_FILE="$HOME/.chrome-debug.pid"
CDP_PORT=9222

usage() {
  echo "Usage: $0 {start|stop|status}"
  exit 1
}

is_running() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid=$(<"$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
  fi
  return 1
}

port_in_use() {
  lsof -i :"$CDP_PORT" -sTCP:LISTEN >/dev/null 2>&1
}

cmd_start() {
  if is_running; then
    local pid=$(<"$PID_FILE")
    echo "Chrome debug instance already running (PID $pid) on port $CDP_PORT."
    return 0
  fi

  if port_in_use; then
    echo "Error: port $CDP_PORT is already in use by another process." >&2
    lsof -i :"$CDP_PORT" -sTCP:LISTEN 2>/dev/null | head -5 >&2
    exit 1
  fi

  if [[ ! -x "$CHROME" ]]; then
    echo "Error: Chrome not found at $CHROME" >&2
    exit 1
  fi

  mkdir -p "$PROFILE_DIR"

  "$CHROME" \
    --remote-debugging-port="$CDP_PORT" \
    --user-data-dir="$PROFILE_DIR" \
    --no-first-run \
    --no-default-browser-check \
    --disable-default-apps \
    "https://app.gong.io" &

  local pid=$!
  echo "$pid" > "$PID_FILE"

  # Wait briefly for Chrome to start listening
  for i in {1..20}; do
    if curl -s "http://localhost:$CDP_PORT/json/version" >/dev/null 2>&1; then
      echo "Chrome debug instance started (PID $pid) on port $CDP_PORT."
      return 0
    fi
    sleep 0.5
  done

  echo "Chrome started (PID $pid) but CDP port $CDP_PORT not responding yet."
  echo "It may still be loading — try again in a few seconds."
}

cmd_stop() {
  if ! is_running; then
    echo "Chrome debug instance is not running."
    rm -f "$PID_FILE"
    return 0
  fi

  local pid=$(<"$PID_FILE")
  kill "$pid" 2>/dev/null || true
  rm -f "$PID_FILE"
  echo "Chrome debug instance stopped (PID $pid)."
}

cmd_status() {
  if is_running; then
    local pid=$(<"$PID_FILE")
    echo "Chrome debug instance is running (PID $pid) on port $CDP_PORT."
    if curl -s "http://localhost:$CDP_PORT/json/version" >/dev/null 2>&1; then
      echo "CDP endpoint responding."
    else
      echo "Warning: CDP endpoint not responding."
    fi
  else
    echo "Chrome debug instance is not running."
    rm -f "$PID_FILE" 2>/dev/null || true
  fi
}

case "${1:-}" in
  start)  cmd_start ;;
  stop)   cmd_stop ;;
  status) cmd_status ;;
  *)      usage ;;
esac
