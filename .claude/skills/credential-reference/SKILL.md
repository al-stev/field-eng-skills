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
| `SFDC_SESSION_ID` | Salesforce (session auth) | `/salesforce-setup` |
| `SFDC_INSTANCE` | Salesforce (session auth) | `/salesforce-setup` |
| `SFDC_USERNAME` | Salesforce (password auth) | `/salesforce-setup` |
| `SFDC_PASSWORD` | Salesforce (password auth) | `/salesforce-setup` |
| `SFDC_SECURITY_TOKEN` | Salesforce (password auth) | `/salesforce-setup` |
