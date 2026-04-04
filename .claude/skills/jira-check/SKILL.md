---
name: jira-check
description: "Check on customer Jira issues and maintain FE-UPDATE comments. Use this skill when the user wants to check on stale issues, update FE-UPDATE comments, triage customer tickets, or review issue status. Activate for 'jira check', 'check on GResearch', 'update jira', 'update WB-', 'stale tickets', 'FE-UPDATE maintenance', or any Jira URL containing coreweave.atlassian.net. When invoked without a customer name, runs a sweep across ALL customers in the registry. If the user pastes a URL like https://coreweave.atlassian.net/browse/WB-123, extract the WB-XXX key and use this skill."
argument-hint: "[customer-name or WB-XXX key] (omit for all-customer sweep)"
---

# Jira Check

Check on customer Jira issues and keep FE-UPDATE comments current. The workflow is triage-then-drill: fetch issues, classify by staleness, gather Slack context for selected issues, draft FE-UPDATE comments with source citations, and post only after SE approval.

The SE drives every decision. You draft, they review, enrich, and approve. This matters because the SE has context from calls, hallway conversations, and gut feel that no API can surface.

## Defaults

| Property | Value |
|---|---|
| Jira project | `WB` |
| Jira instance | `coreweave.atlassian.net` |
| Customer registry | `templates/customers.yaml` |
| FE-UPDATE convention | `.claude/rules/atlassian.md` |

## Prerequisites

- **Jira** -- `ATLASSIAN_EMAIL` and `ATLASSIAN_TOKEN` in `~/.fe-skills/.env`
- **Slack** -- `SLACK_TOKEN` and `SLACK_COOKIE` in `~/.fe-skills/.env`

Verify Jira connectivity:
```bash
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py list --max-results 1 --pretty
```

Not all tools are required for every operation. If Slack credentials are missing, you can still process issues using Jira data alone -- note the gap to the SE.

## Workflow

### Step 1: Identify Scope

Determine scope from the user's request. Four modes:

**All-customer sweep** (no argument): `/jira-check` with no customer name. Read `templates/customers.yaml`, iterate through every customer entry, and run Steps 2-6 for each. Present a cross-customer triage dashboard first:

```
Jira Check -- All Customers
  GResearch:  12 issues (3 stale, 2 need initial)
  Acme Corp:   8 issues (1 stale, 0 need initial)
  BigCo:       5 issues (0 stale, 1 need initial)

5 issues need attention across 3 customers. Which customer do you want to start with?
```

The SE picks a customer (or says "all"), then you proceed through the normal per-customer flow for each.

**Per-customer** (primary): "check on GResearch" or "jira-check GResearch" -- fetch all issues for the customer.
```bash
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py list --customer "<CustomerName>" --with-comments --max-results 100 --pretty
```

**Specific keys**: "check WB-123" or "update WB-123, WB-456" -- fetch named issues.
```bash
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py view --key WB-XXX --pretty
```

**URL-based**: extract the `WB-XXX` key from `coreweave.atlassian.net` URLs and treat as specific-key mode.

Validate every key starts with `WB-`. Refuse non-WB keys and explain that this skill only operates on the WB project.

### Step 2: Build Triage Summary

For each issue, determine its FE-UPDATE status:
```bash
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py fe-updates --key WB-XXX --pretty
```

Classify each issue into buckets:

| Bucket | Condition |
|---|---|
| **Stale** | Has FE-UPDATE where today > next-update date |
| **Needs initial FE-UPDATE** | Zero FE-UPDATE comments on the issue |
| **Current** | Has FE-UPDATE with next-update date still in the future |
| **Resolved** | Latest FE-UPDATE status is "resolved" (skip from update candidates) |

Present the triage summary to the SE:

```
GResearch: 12 issues
  - 3 stale (past next-update date)
  - 2 need initial FE-UPDATE
  - 5 current
  - 2 resolved (skipping)
```

List the stale and needs-initial issues with key, summary, and staleness info (e.g., "WB-123: SDK crash on large datasets -- stale by 12 days, last next-update was 05-MAR-2026"). Ask the SE which issues to work on.

### Step 3: Build Issue Briefing

When the SE selects an issue to work on, build a **full briefing** before drafting anything. Complex issues accumulate months of history across Jira comments and Slack threads — the SE needs the complete picture to write an informed update.

**Presentation rule:** Always show channel **names** to the SE, never raw channel IDs. The API calls use IDs internally, but the SE should never see `C01234ABCDE` in output. Look up the channel name from `customers.yaml` or from the Slack API response's `name` field. Slack thread URLs naturally contain IDs — that's fine in URLs, but when citing a source in prose, write the `#channel-name` not the ID.

#### 3a: Read Full Jira History

Fetch the issue with all comments (already available from Step 1 if `--with-comments` was used). Read:

- **Description** in full — the original report and any edits
- **All comments** chronologically — not just the latest, ALL of them
- **FE-UPDATE history** — trace how status, targets, and next-update dates have evolved over time. Note any drift (e.g., target slipped from March to June).
- **Status changes** — current status vs. created date gives a sense of age and movement
- **Assignee** — who owns it on the eng side

```bash
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py view --key WB-XXX --pretty
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py fe-updates --key WB-XXX --pretty
```

#### 3b: Follow ALL Embedded Slack URLs

Extract every Slack URL from the issue's description AND all comments (not just recent ones). Match the pattern:
```
https://coreweave.slack.com/archives/([A-Z0-9]+)(?:/p(\d+))?
```

For each URL, fetch the full thread:

**Thread URLs** (with timestamp): strip the `p` prefix, insert a dot before the last 6 digits to get thread TS:
```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/threads.py replies --channel <CHANNEL_ID> --ts <THREAD_TS> --limit 50 --pretty
```

**Channel URLs** (no timestamp): read recent history around the link context:
```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/channels.py history --channel <CHANNEL_ID> --limit 30 --pretty
```

Summarize each thread: who said what, when, and what was the outcome or open question.

#### 3c: Fallback Channel Search

If the issue has no embedded Slack URLs, look up the customer in `templates/customers.yaml` and search for the issue key across **all** of their listed channels (there will typically be at least an internal and external channel, sometimes more):
```bash
# Search each channel listed in the customer's YAML entry
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/search.py --query "WB-XXX in:#<channel-name>" --count 10 --sort timestamp --sort-dir desc --pretty
```

Run a search per channel and merge the results. If any channel entry has `PLACEHOLDER` as the ID, skip it and tell the SE: "The channel [name] for [customer] has a placeholder ID. Please update templates/customers.yaml with the real channel ID for future use."

#### 3d: No Sources Found

If neither strategy yields Slack context, tell the SE clearly: "No Slack activity found for WB-XXX. No embedded URLs in the issue and no results from channel search."

#### 3e: Present the Briefing

Synthesize everything into a structured briefing:

```
WB-28835: SDK crash on large artifact upload
  Priority: P1 | Status: In Progress | Assignee: Jane Doe
  Filed: 2025-09-12 (6 months ago) | Last activity: 2026-03-10

  TIMELINE
  - 2025-09-12: Filed by customer after repeated crashes during training runs
  - 2025-10-01: Eng confirmed root cause — memory leak in chunked upload path
  - 2025-11-15: Fix attempted in v0.17.1, customer reported still failing
  - 2026-01-20: Escalated to P1, SDK team assigned dedicated sprint
  - 2026-03-10: Eng says fix landing in v0.18.3 (mid-April)

  FE-UPDATE HISTORY (3 updates)
  - 2025-10-05: waiting-on-prod-eng, target 15-NOV-2025
  - 2025-12-01: waiting-on-prod-eng, target 31-JAN-2026 (slipped)
  - 2026-01-25: waiting-on-prod-eng, target 28-FEB-2026 (slipped again)

  SLACK THREADS (2 found)
  - #<channel-name> 2026-01-18: Customer frustrated about repeated delays,
    asked for exec escalation path (12 messages, 4 participants)
  - #<channel-name> 2026-03-10: Eng confirmed v0.18.3 fix, customer cautiously
    optimistic but wants confirmation when it ships

  CURRENT STATE
  Target has slipped 3 times. Customer tone has shifted from patient to
  frustrated. Latest eng signal is positive (v0.18.3) but credibility is low
  given prior misses.
```

The briefing should be proportional to the issue's complexity. A simple, recently-filed issue with one comment needs 3-4 lines, not a full timeline. A 6-month issue with 20 comments and multiple Slack threads needs the full treatment above.

After presenting the briefing, ask: "Ready to draft an FE-UPDATE, or do you want to dig into any of these threads?"

### Step 4: Draft FE-UPDATE

Once the SE has the briefing and is ready, present a pre-filled FE-UPDATE draft with TODO markers for SE judgment:

```
FE-UPDATE Draft for WB-XXX:
  Status: [SE: confirm -- waiting-on-prod-eng / waiting-on-customer / resolved]
  Next Update: [SE: set date, format DD-MMM-YYYY]
  Target: [SE: set if known, format DD-MMM-YYYY]
  Notes:
    <synthesized notes from briefing with source citations>
    (Source: #<channel-name> YYYY-MM-DD, thread <slack-url>)
    [SE: add any context from calls or conversations]
```

The SE can:
- **Approve as-is** (after filling TODO markers)
- **Edit inline** (change status, dates, add their own notes)
- **Skip** this issue
- **Post a general comment instead** (not FE-UPDATE format, for tagging people or general notes)

### Step 5: Execute Approved Updates

For each approved FE-UPDATE, post using the fe-update command:
```bash
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py fe-update \
  --key WB-XXX --status <status> \
  --next-update <DD-MMM-YYYY> \
  --target <DD-MMM-YYYY> \
  --notes "<notes with source citations>" \
  --pretty
```

For general comments (secondary path):
```bash
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py comment \
  --key WB-XXX --body "<comment text>" --pretty
```

**WRITE operations -- always show the SE exactly what will be posted and get explicit approval before executing.** This is non-negotiable. The SE must see the final text and confirm before any write operation.

### Step 6: Summary

After all updates are processed, show the session summary:

```
Session Summary
  Issues reviewed: N
  FE-UPDATEs posted: N (WB-123, WB-456)
  General comments posted: N (WB-789)
  Issues skipped: N (WB-101 -- SE skipped, WB-102 -- no Slack context)
  Stale issues remaining: N not addressed this session
```

## Handling Unknown Customers

When a customer is not in `templates/customers.yaml`:

- Tell the SE: "[CustomerName] is not in customers.yaml. I can still process their issues using embedded Slack URLs, but channel fallback search won't work."
- Process the issues using embedded URLs only (primary source strategy still works).
- After the session, suggest adding the customer to `templates/customers.yaml` with their channel info.
- Never block on a missing YAML entry -- embedded URLs are the primary source.

## Safety Rules

1. **WB-only.** Only operate on issues with `WB-` prefixed keys. Validate every key before any action. Refuse all others.
2. **Confirm before every write.** Never post an FE-UPDATE or comment without SE approval. Show the exact text that will be posted.
3. **No fabrication.** Every fact in an FE-UPDATE must come from a Slack source fetched in Step 3 for that specific issue. Never insert information from other issues, from memory, or from general knowledge. If no Slack context was found, say so.
4. **No broad searches.** Do not search all of Slack for a customer name. Follow embedded URLs first, then search only the customer's known channels from customers.yaml.
5. **No status transitions.** This skill focuses on FE-UPDATE comments and general comments only. Do not propose or execute Jira status transitions, priority changes, or field edits.
6. **No custom labels.** Do not create or apply labels. FE-UPDATE comments are the tracking record.
7. **Preserve existing content.** Never overwrite issue descriptions or delete comments. Only add new comments.
8. **Time-bound Slack queries.** Always use `--oldest` with the last Jira comment timestamp to avoid over-fetching Slack data.

## Memory

Record useful patterns in `.claude/agent-memory/jira-check/MEMORY.md` as you work:

- Customer names and their Jira Customer field values (if they differ from display name)
- Slack channel IDs discovered during sessions (update customers.yaml too)
- Common FE-UPDATE patterns that work well for specific issue types
- JQL patterns for batch scopes
