# Atlassian Workspace Rules

## Instances

- Jira: coreweave.atlassian.net (W&B project WB -- customer bugs, feature requests, escalations)
- Confluence: coreweave.atlassian.net (CoreWeave instance -- available via MCP tools, skill deferred)
- User is a Solutions Engineer at W&B (Weights & Biases), which is by CoreWeave

## Jira Conventions

- Use the Jira skill scripts (uv run) for Jira operations
- MCP Atlassian tools (mcp__atlassian-wandb) may be used as complement for operations the skill doesn't cover
- Primary project: WB (W&B Eng) -- customer bugs and feature requests
- Customer field (customfield_16678, "Customer (WB)"): used for per-customer queries ("Customer" = "CustomerName")
- Eng Team field (customfield_16680, "Eng Team"): engineering team assignment
- Write operations (create issue, add comment, transition) require user approval
- Destructive operations (delete issues) are blocked entirely

## FE-UPDATE Convention

Structured comment format for tracking SE progress on customer tickets.

Format:
```
[FE-UPDATE] [status:waiting-on-prod-eng] [next-update:20-MAR-2026] [target:15-APR-2026]
Free text notes -- next steps, context, impact.
```

Date format: DD-MMM-YYYY (e.g. 20-MAR-2026) -- avoids US/EU ambiguity.

Statuses:
- waiting-on-prod-eng: Blocked on product/engineering
- waiting-on-customer: Ball is in customer's court
- resolved: Done -- fix shipped, workaround provided, or satisfied

Tags:
- [FE-UPDATE] marks comment as structured update
- [status:X] current state from SE perspective
- [next-update:DD-MMM-YYYY] when to check back
- [target:DD-MMM-YYYY] expected delivery/resolution date (tracks drift over time)
- Latest FE-UPDATE comment = current state (supersedes older ones)

## Credential Location

- Credentials stored in ~/.tsm-ai/.env (ATLASSIAN_EMAIL, ATLASSIAN_TOKEN)
- API tokens do not expire -- no auto-refresh needed (unlike Slack)
