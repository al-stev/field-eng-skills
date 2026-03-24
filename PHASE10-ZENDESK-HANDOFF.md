# Phase 10: Zendesk Integration — Handoff

**Date:** 2026-03-24
**Status:** Not started — context gathered, no code written

## Goal

Pull Zendesk support tickets into the intelligence dashboard alongside Jira issues for a complete customer health view. Jira captures engineering-tracked issues; Zendesk captures support interactions. Some customer pain points only surface in Zendesk.

## Success Criteria

1. Zendesk API credentials configured and connectivity verified
2. Skill for querying Zendesk tickets by customer name
3. Dashboard template renders support ticket data alongside Jira data

## What Exists Today

- **Customer snapshot dashboard** (`customer-snapshot/templates/intelligence-dashboard.html`): Jira issues, Slack sentiment, Asana actions, BigQuery usage, trending, exec summary. Zendesk would be a new panel in this dashboard.
- **Jira skill pattern** (`jira/`): Client module + query script + argparse + JSON output. Zendesk skill should follow the same pattern.
- **Credential infrastructure**: `~/.tsm-ai/.env` for secrets, `/credential-status` for health checks, `/atlassian-setup` pattern for setup skills.
- **Customer registry** (`templates/customers.yaml`): Would need a `zendesk_org_id` or `zendesk_org_name` field per customer for querying.

## Research Needed

### Zendesk API Access
- W&B likely has a Zendesk instance — need to confirm URL (e.g., `wandb.zendesk.com`)
- API authentication options: API token, OAuth, or session auth
- Check if SE role has API access or if it needs requesting
- Rate limits and pagination approach

### Data Model
- How are customers identified in Zendesk? Organization name, org ID, domain?
- Ticket fields: status, priority, type, tags, assignee, created/updated dates
- Are there custom fields specific to W&B's Zendesk setup?
- Relationship between Zendesk organizations and Jira customer names — is there a mapping?

### Integration Points
- Can Zendesk tickets be linked to Jira issues? (some orgs use Zendesk-Jira sync)
- Are there existing Zendesk views or macros that SEs use?
- What ticket statuses map to "open/resolved" for dashboard health metrics?

## Suggested Approach

### Skill Architecture (follows jira/slack/asana pattern)

```
.claude/skills/
  zendesk/
    SKILL.md              -- Skill definition with frontmatter
    pyproject.toml        -- Dependencies (zenpy or requests)
    scripts/
      __init__.py
      zendesk_client.py   -- Auth, client init, error handling
      tickets.py          -- Query tickets by customer, search, get ticket details
    tests/
      test_tickets.py     -- Unit tests with mocked responses
  zendesk-setup/
    SKILL.md              -- One-time credential setup skill
```

### Dashboard Integration

Add a "Support Tickets" panel to the intelligence dashboard, similar to how the Jira issues panel works:
- Ticket count by status (open/pending/solved)
- Recent tickets with age indicators
- Staleness signals (old open tickets)
- Severity/priority distribution
- Link to Zendesk ticket URL

### Customer Registry Extension

```yaml
# templates/customers.yaml — new field per customer
  zendesk_org_id: "12345678"        # or zendesk_org_name
```

### Ecosystem Wiring

- `skill-composition.md`: Update "Customer Snapshot" and "Customer Lookup" workflows
- `credential-status`: Add Zendesk health check
- `credential-reference`: Add Zendesk credential keys
- `CLAUDE.md`: Add zendesk/ and zendesk-setup/ to project structure

## Library Options

| Library | Notes |
|---------|-------|
| **zenpy** | Python Zendesk wrapper, mature, pip-installable. Handles pagination. |
| **requests** | Direct REST API calls. Simpler, no extra dependency, matches jira skill pattern. |

The jira and salesforce skills both use direct REST/library calls rather than generic wrappers, so either approach fits the project pattern.

## Open Questions

1. What's the W&B Zendesk instance URL?
2. Does SE role have API access?
3. How are customers mapped in Zendesk (org name, domain, custom field)?
4. Is there an existing Zendesk-Jira integration that creates cross-links?
5. Which ticket types/views matter most for SE health assessment?

## How to Continue

```
/gsd:discuss-phase 10
```

Or start with research — answer the open questions above, then scope the build.
