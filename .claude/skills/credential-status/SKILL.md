---
name: credential-status
description: "Check the health of all configured API credentials. Use when verifying auth works, diagnosing 'auth failed' errors across services, or after running any setup skill."
disable-model-invocation: true
allowed-tools: Bash(bash .claude/skills/credential-status/scripts/check.sh)
---

# Credential Status

Checks all configured API credentials by making lightweight test calls to each service.

## Usage

Run the check script:

```
bash .claude/skills/credential-status/scripts/check.sh
```

The script will output a status table showing which credentials are:
- **OK** — credential exists and API responds successfully
- **MISSING** — credential key not found in `~/.tsm-ai/.env`
- **EXPIRED** — credential exists but API returns 401/403

For expired credentials, run the corresponding setup or refresh skill:
- Slack: `./scripts/slack-credential-refresh.sh`
- Grafana: `./scripts/grafana-cookie-refresh.sh`
- Salesforce: `./scripts/salesforce-session-refresh.sh`
- Gong: `./scripts/gong-cookie-refresh.sh`
- Others: run `/[service]-setup`
