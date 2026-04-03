#!/bin/bash
# Check the health of all configured API credentials
set -euo pipefail

ENV_FILE="$HOME/.tsm-ai/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: $ENV_FILE not found. Run setup skills first."
  exit 1
fi

# Load env file safely (line-by-line to handle unquoted values)
while IFS= read -r line || [ -n "$line" ]; do
  [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
  export "$line" 2>/dev/null || true
done < "$ENV_FILE"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

ok() { echo -e "  ${GREEN}OK${NC}      $1"; }
missing() { echo -e "  ${RED}MISSING${NC} $1"; }
expired() { echo -e "  ${YELLOW}EXPIRED${NC} $1 — $2"; }

echo "Credential Status Check"
echo "========================"
echo ""

# Atlassian (Jira/Confluence)
if [ -n "${ATLASSIAN_TOKEN:-}" ] && [ -n "${ATLASSIAN_EMAIL:-}" ]; then
  # Test against W&B Jira instance
  HTTP_CODE_JIRA=$(curl -s -o /dev/null -w "%{http_code}" \
    -u "${ATLASSIAN_EMAIL}:${ATLASSIAN_TOKEN}" \
    "https://coreweave.atlassian.net/rest/api/3/myself" 2>/dev/null || echo "000")
  # Test against CoreWeave Confluence instance
  HTTP_CODE_CONF=$(curl -s -o /dev/null -w "%{http_code}" \
    -u "${ATLASSIAN_EMAIL}:${ATLASSIAN_TOKEN}" \
    "https://coreweave.atlassian.net/rest/api/3/myself" 2>/dev/null || echo "000")
  if [ "$HTTP_CODE_JIRA" = "200" ]; then
    ok "Jira (coreweave.atlassian.net)"
  else
    expired "Jira" "HTTP $HTTP_CODE_JIRA — run /atlassian-setup"
  fi
  if [ "$HTTP_CODE_CONF" = "200" ]; then
    ok "Confluence (coreweave.atlassian.net)"
  else
    expired "Confluence" "HTTP $HTTP_CODE_CONF — run /atlassian-setup"
  fi
else
  missing "Atlassian (ATLASSIAN_EMAIL / ATLASSIAN_TOKEN)"
fi

# Slack
if [ -n "${SLACK_TOKEN:-}" ] && [ -n "${SLACK_COOKIE:-}" ]; then
  RESP=$(curl -s -H "Authorization: Bearer ${SLACK_TOKEN}" \
    -H "Cookie: d=${SLACK_COOKIE}" \
    "https://slack.com/api/auth.test" 2>/dev/null || echo '{"ok":false}')
  if echo "$RESP" | grep -q '"ok":true'; then
    ok "Slack"
  else
    expired "Slack" "auth.test failed — run ./scripts/slack-credential-refresh.sh"
  fi
else
  missing "Slack (SLACK_TOKEN / SLACK_COOKIE)"
fi

# Asana
if [ -n "${ASANA_TOKEN:-}" ]; then
  HTTP_CODE_ASANA=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer ${ASANA_TOKEN}" \
    "https://app.asana.com/api/1.0/users/me" 2>/dev/null || echo "000")
  if [ "$HTTP_CODE_ASANA" = "200" ]; then
    ok "Asana"
  else
    expired "Asana" "HTTP $HTTP_CODE_ASANA — run /asana-setup"
  fi
else
  missing "Asana (ASANA_TOKEN)"
fi

# Salesforce (supports session auth OR password auth)
if [ -n "${SFDC_SESSION_ID:-}" ] && [ -n "${SFDC_INSTANCE:-}" ] || \
   [ -n "${SFDC_USERNAME:-}" ] && [ -n "${SFDC_PASSWORD:-}" ] && [ -n "${SFDC_SECURITY_TOKEN:-}" ]; then
  SFDC_CHECK=$(uv run --project .claude/skills/salesforce python -c "
import sys
sys.path.insert(0, '.claude/skills/salesforce/scripts')
from sfdc_client import get_client
try:
    sf = get_client()
    sf.query('SELECT Id FROM User LIMIT 1')
    print('OK')
except Exception as e:
    print('FAIL', file=sys.stderr)
    print('FAIL')
" 2>/dev/null)
  if [ "$SFDC_CHECK" = "OK" ]; then
    ok "Salesforce"
  else
    expired "Salesforce" "auth failed -- run /salesforce-setup"
  fi
else
  missing "Salesforce (SFDC_SESSION_ID + SFDC_INSTANCE or SFDC_USERNAME + SFDC_PASSWORD + SFDC_SECURITY_TOKEN)"
fi

# Google Calendar (Apps Script)
if [ -n "${GCALENDAR_APPSCRIPT_URL:-}" ] && [ -n "${GCALENDAR_APPSCRIPT_KEY:-}" ]; then
  ok "Google Calendar (Apps Script URL + key configured)"
else
  missing "Google Calendar (GCALENDAR_APPSCRIPT_URL / GCALENDAR_APPSCRIPT_KEY)"
fi

# Google Docs (Apps Script)
if [ -n "${GDOCS_APPSCRIPT_URL:-}" ] && [ -n "${GDOCS_APPSCRIPT_KEY:-}" ]; then
  ok "Google Docs (Apps Script URL + key configured)"
else
  missing "Google Docs (GDOCS_APPSCRIPT_URL / GDOCS_APPSCRIPT_KEY)"
fi

# Gmail (Apps Script)
if [ -n "${GMAIL_APPSCRIPT_URL:-}" ] && [ -n "${GMAIL_APPSCRIPT_KEY:-}" ]; then
  ok "Gmail (Apps Script URL + key configured)"
else
  missing "Gmail (GMAIL_APPSCRIPT_URL / GMAIL_APPSCRIPT_KEY)"
fi

# Gong
if [ -n "${GONG_COOKIE:-}" ]; then
  ok "Gong (cookie configured)"
else
  missing "Gong (GONG_COOKIE)"
fi

echo ""
echo "Done."
