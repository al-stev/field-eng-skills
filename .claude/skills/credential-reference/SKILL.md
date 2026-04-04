---
name: credential-reference
description: "Reference table for all API credential keys and their setup skills. Use when asking 'which key does X use', 'what credentials exist', or looking up env var names."
disable-model-invocation: true
---

# Credential Reference

All API credentials are stored in `~/.fe-skills/.env` (directory permissions `700`, file permissions `600`). Format is flat `KEY=value`, one per line.

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
