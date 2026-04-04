---
name: credential-reference
description: "Reference table for all API credential keys and their setup skills. Use when asking 'which key does X use', 'what credentials exist', or looking up env var names."
disable-model-invocation: true
---

# Credential Reference

All API credentials are stored in `~/.tsm-ai/.env` (directory permissions `700`, file permissions `600`). Format is flat `KEY=value`, one per line.

| Key | Service | Set by |
|---|---|---|
| `SLACK_TOKEN` | Slack (`xoxc-`) | `/slack-setup` or `slack-credential-refresh.sh` |
| `SLACK_COOKIE` | Slack (`xoxd-`) | `/slack-setup` or `slack-credential-refresh.sh` |
| `ATLASSIAN_EMAIL` | Jira/Confluence | `/atlassian-setup` |
| `ATLASSIAN_TOKEN` | Jira/Confluence | `/atlassian-setup` |
| `ASANA_TOKEN` | Asana | `/asana-setup` |
| `SFDC_SESSION_ID` | Salesforce (SSO auth -- primary) | `/salesforce-setup` via `sf org login web` |
| `SFDC_INSTANCE` | Salesforce (SSO auth -- primary) | `/salesforce-setup` (`wandb.my.salesforce.com`) |
| `SFDC_USERNAME` | Salesforce (password auth -- alternative) | `/salesforce-setup` |
| `SFDC_PASSWORD` | Salesforce (password auth -- alternative) | `/salesforce-setup` |
| `SFDC_SECURITY_TOKEN` | Salesforce (password auth -- alternative) | `/salesforce-setup` |
| `GCALENDAR_APPSCRIPT_URL` | Google Calendar Apps Script endpoint | `/gcalendar-setup` |
| `GCALENDAR_APPSCRIPT_KEY` | Google Calendar Apps Script API key | `/gcalendar-setup` |
| `GDOCS_APPSCRIPT_URL` | Google Docs Apps Script endpoint | `/gdocs-setup` |
| `GDOCS_APPSCRIPT_KEY` | Google Docs Apps Script API key | `/gdocs-setup` |
| `GMAIL_APPSCRIPT_URL` | Gmail Apps Script endpoint | `/gmail-setup` |
| `GMAIL_APPSCRIPT_KEY` | Gmail Apps Script API key | `/gmail-setup` |
| `GONG_COOKIE` | Gong session cookie (`g-session`, `cell`, etc.) | `/gong-setup` or `gong-cookie-refresh.sh` |
| `GONG_BASE_URL` | Gong region-specific URL | `/gong-setup` |
| `GONG_WORKSPACE_ID` | Gong workspace ID | `/gong-setup` |
