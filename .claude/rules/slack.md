# Slack Workspace Rules

## Workspace

- User is a Solutions Engineer at W&B (Weights & Biases), which is by CoreWeave
- The Slack workspace is the CoreWeave Slack workspace (coreweave.slack.com)
- Channel naming varies — common prefixes include wandb-*, ext-*, internal-*, supp-* but there is NO universal convention. Always look up actual channel names from customers.yaml or Slack API. Never assume a channel name based on a prefix pattern.

## Conventions

- Always use the TSM Slack skill scripts (uv run) for read operations
- Never use MCP Slack tools -- use the TSM skill exclusively
- Write operations use curl fallbacks and require user approval
- Do not hard-code channel IDs in committed files
- Channel IDs belong in user-scoped rules at ~/.claude/projects/<project>/rules/slack-channels.md

## Credential Location

- Credentials stored in ~/.tsm-ai/.env (SLACK_TOKEN, SLACK_COOKIE)
- Chrome debug instance on port 9222 required for credential refresh
- Run /slack-setup if credentials are not configured
