# [Customer] : W&B [Cadence Type] -- [Date]

**Time:** [Day], [Date], [Start] - [End] [TZ]
**Cadence:** [Type] ([schedule])
**Prepared by:** cadence-prep agent ([generated date])

---

## Attendees

<!-- Seeded from customers.yaml contacts. Agent carries forward from previous cadence doc. -->

| Name | Org | Role |
|------|-----|------|
| Allan Stevenson | W&B | Solutions Engineer |
| [Contact] | [Customer] | [Role] |

## What's New (Slack Summary)

<!-- Agent gathers from Slack channel history using lookback window matched to cadence type. -->
<!-- Permalinks use https://coreweave.slack.com/archives/{channel_id}/p{ts} -->

Key activity from [channel names] in the last [N] days:

- [Summary of notable thread] -- [permalink](https://coreweave.slack.com/archives/CHANNEL_ID/pTIMESTAMP)
- [Summary of notable thread] -- [permalink](https://coreweave.slack.com/archives/CHANNEL_ID/pTIMESTAMP)

*No notable Slack activity in the lookback window.* <!-- Agent uses this if no results -->

## Support Ticket Stats (Jira)

<!-- Agent gathers from Jira via: issues.py list --customer "CustomerName" --with-comments --max-results 200 -->
<!-- Issue URLs use https://wandb.atlassian.net/browse/WB-XXX -->

### Open Issues ([N] total)

| Key | Summary | Type | Priority | Status | Last Activity | FE-UPDATE |
|-----|---------|------|----------|--------|---------------|-----------|
| [WB-XXX](https://wandb.atlassian.net/browse/WB-XXX) | [summary] | Bug | P1 | In Progress | [date] | [status from latest FE-UPDATE] |

### Recently Closed (Last 30 Days)

<!-- Agent gathers via: issues.py search --jql "status IN (Done, Closed, Resolved) AND updated >= -30d" --customer "CustomerName" -->

| Key | Summary | Resolved Date |
|-----|---------|---------------|
| [WB-YYY](https://wandb.atlassian.net/browse/WB-YYY) | [summary] | [date] |

*No issues closed in the last 30 days.* <!-- Agent uses this if no results -->

### Stale Issues (no activity 30+ days)

<!-- Derived from comment dates in --with-comments output. FE-UPDATE (SE) comments excluded from activity calculation. -->

| Key | Summary | Priority | Last Activity |
|-----|---------|----------|---------------|
| [WB-ZZZ](https://wandb.atlassian.net/browse/WB-ZZZ) | [summary] | P2 | [date] |

*No stale issues.* <!-- Agent uses this if no results -->

## Action Items

<!-- Carried forward from previous cadence doc. New items added from Slack threads and Jira activity. -->

| # | Action | Owner | Due | Status | Source |
|---|--------|-------|-----|--------|--------|
| 1 | [carried forward item] | [name] | [date] | Open | Previous cadence |
| 2 | [new item from Slack] | [name] | [date] | New | [permalink] |

*No action items.* <!-- Agent uses this if no items carried forward and none discovered -->

## RAID Log

<!-- Carried forward from previous cadence doc. Agent updates status based on current Jira/Slack state. -->

| Type | Item | Owner | Status |
|------|------|-------|--------|
| Risk | [description] | [name] | [status] |
| Action | [description] | [name] | [status] |
| Issue | [description] | [name] | [status] |
| Decision | [description] | [name] | [date] |

*No RAID items.* <!-- Agent uses this if empty -->

## Usage Stats

*Data not yet available for v1. Placeholder for future BigQuery integration (Phase 8).*

## Product Updates

*Relevant W&B product updates since last cadence. Agent populates from knowledge if available.*

## Key Initiatives

*Customer's key initiatives and how W&B supports them. Carried forward from previous docs.*
