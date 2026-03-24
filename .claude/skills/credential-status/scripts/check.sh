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
    "https://wandb.atlassian.net/rest/api/3/myself" 2>/dev/null || echo "000")
  # Test against CoreWeave Confluence instance
  HTTP_CODE_CONF=$(curl -s -o /dev/null -w "%{http_code}" \
    -u "${ATLASSIAN_EMAIL}:${ATLASSIAN_TOKEN}" \
    "https://coreweave.atlassian.net/rest/api/3/myself" 2>/dev/null || echo "000")
  if [ "$HTTP_CODE_JIRA" = "200" ]; then
    ok "Jira (wandb.atlassian.net)"
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
    ok "Asana (app.asana.com)"
  else
    expired "Asana" "HTTP $HTTP_CODE_ASANA — run /asana-setup"
  fi
else
  missing "Asana (ASANA_TOKEN)"
fi

echo ""
echo "Done."
