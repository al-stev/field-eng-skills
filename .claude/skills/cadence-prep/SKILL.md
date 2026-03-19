---
name: cadence-prep
description: "Prepare for a customer cadence call by gathering Jira issues and Slack history into a structured meeting agenda. Use this skill whenever the user mentions cadence prep, meeting prep, prepping the agenda, getting ready for a customer call, building a QBR doc, or any request to prepare for an upcoming customer meeting. Also trigger when the user says 'prep the cadence', 'get ready for the call', 'build the agenda', or references a customer name alongside words like 'call', 'meeting', 'sync', 'cadence', or 'QBR'."
argument-hint: "[customer-name] [--dry-run] [--html] [--weekly|--biweekly|--monthly|--qbr]"
requires-credentials:
  - ATLASSIAN_EMAIL
  - ATLASSIAN_TOKEN
  - SLACK_TOKEN
  - SLACK_COOKIE
setup-skill: atlassian-setup
service-url: https://wandb.atlassian.net
auto-refresh: false
---

# Cadence Prep

Gather context from Jira and Slack, populate a structured agenda using the cadence review template, and save it as a markdown file ready for the SE to review and customize before their customer meeting.

## Design Principles

- **Gather everything, present once** -- collect all data from Jira and Slack before generating the document. Do not show incremental results.
- **Facts only, never fabricate** -- every item in the agenda must come from a verifiable source (Jira issue, Slack message). If a section has no data, write "No data available" rather than guessing.
- **Link everything** -- every Jira issue includes its `wandb.atlassian.net/browse/WB-XXX` URL. Every Slack reference includes its `coreweave.slack.com/archives/` permalink.
- **Previous docs are immutable** -- never modify previous cadence files. Always create a new file with today's date.
- **Template-driven** -- output follows `templates/cadence-review.md` structure exactly. All sections are always generated; the SE decides what to present.

## Defaults

| Property | Value |
|---|---|
| Output directory | `customers/<name>/calls/` |
| Template | `templates/cadence-review.md` |
| Customer registry | `templates/customers.yaml` |
| Jira instance | `wandb.atlassian.net` |
| Default max results | 200 |

## Prerequisites

The following credentials must be configured before use:

- **Jira** -- `ATLASSIAN_EMAIL` and `ATLASSIAN_TOKEN` in `~/.tsm-ai/.env`
- **Slack** -- `SLACK_TOKEN` and `SLACK_COOKIE` in `~/.tsm-ai/.env`

Verify Jira connectivity:
```bash
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py list --max-results 1 --pretty
```

Not all sources are required. If Slack credentials are missing, build the agenda from Jira data alone -- note which sections are incomplete.

## Workflow

### Step 1: Parse Invocation

Parse the user's request to determine:

- **Customer name** (required): fuzzy-match against `templates/customers.yaml` keys. Check both the `name` field and `jira_customer_variants` for alternative spellings. If ambiguous, ask the user to confirm. If customer not found, follow the Unknown Customer procedure below.
- **Cadence type** (optional override): `--weekly`, `--biweekly`, `--monthly`, `--qbr`. If not specified, use the customer's `cadence.type` from customers.yaml.
- **Date** (optional): defaults to today. Used for the document filename and header.
- **Dry-run** flag: if `--dry-run` is specified, preview the agenda in chat without saving to disk or publishing to Confluence.
- **HTML** flag: if `--html` is specified, also generate a styled HTML version for screen-sharing (in addition to Confluence + local markdown).

Read the customer entry from `templates/customers.yaml` to get: `jira_customer`, `slack_channels`, `cadence` schedule, `contacts`.

Compute the lookback window from cadence type:

| Cadence Type | Lookback |
|---|---|
| weekly | 7 days |
| biweekly | 14 days |
| monthly | 30 days |
| qbr | 90 days |

Calculate the Unix timestamp for the `--oldest` parameter: `current_time - (lookback_days * 86400)`.

### Step 2: Gather Jira Data

Run these data-gathering operations:

**Open issues:**
```bash
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py list \
  --customer "<jira_customer>" --with-comments --max-results 200 --pretty
```

**Recently closed (within lookback window or last 30 days, whichever is greater):**
```bash
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py search \
  --jql "project = WB AND status IN (Done, Closed, Resolved) AND updated >= -30d ORDER BY updated DESC" \
  --customer "<jira_customer>" --max-results 50 --pretty
```

**FE-UPDATE status** for each open issue:
```bash
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py fe-updates \
  --key WB-XXX --pretty
```

From the gathered data, compute:

- **Open issue table**: key, summary, type, priority, status, last activity date, latest FE-UPDATE status
- **Recently resolved (within cadence window)**: issues that moved to Done/Closed/Resolved/Merged since the last cadence. These are wins to highlight — for each one, write a brief customer-facing summary of what was fixed or delivered and why it matters to them. These feed into the "What's New" section as good news to share.
- **Recently closed (broader, last 30 days)**: key, summary, resolved date — for the support tickets summary table
- **Stale issues**: open issues where the most recent comment (excluding SE's own FE-UPDATE comments) is older than 30 days
- Issue URLs: `https://wandb.atlassian.net/browse/WB-XXX`

### Step 3: Gather Slack Data

Read channel history for each of the customer's Slack channels (from customers.yaml `slack_channels`):

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/channels.py history \
  --channel <channel_id> --limit 50 --oldest <lookback_timestamp> --pretty
```

For threads with `reply_count > 0`, fetch the full thread to get context:
```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/threads.py replies \
  --channel <channel_id> --ts <thread_ts> --limit 50 --pretty
```

From the gathered data, produce:

- **What's New summary**: group notable threads by topic, summarize each in 1-2 sentences
- **Slack permalinks**: construct from channel_id + message timestamp: `https://coreweave.slack.com/archives/{channel_id}/p{ts_without_dot}`
- Filter out low-signal messages (bot messages, join/leave notifications, reactions-only)

**Resolve Slack identities:** Slack messages contain user IDs in the format `<@UXXXXXXXX>`. Before writing any output, resolve these to real names using the Slack skill:

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/users.py info --user UXXXXXXXX --pretty
```

Cache resolved names for the session to avoid repeated lookups. Replace all `<@UXXXX>` references with the person's display name in the final output.

**Handling edge cases:**
- If a channel ID is `PLACEHOLDER`, skip it and note: "Slack channel ID for [channel name] is a placeholder. Update templates/customers.yaml with the real channel ID."
- If no Slack channels are configured or all return empty, note: "No Slack activity found in the lookback window."
- If Slack credentials fail, note which sections are incomplete and continue with Jira data.
- If a user ID cannot be resolved, leave it as `<@UXXXX>` rather than guessing.

### Step 4: Carry Forward from Previous Docs

Look for existing cadence docs:
```bash
ls -1 customers/<customer>/calls/*.md 2>/dev/null | sort | tail -1
```

If a previous doc exists, read it and extract:

- **Attendees table**: carry forward as-is (SE edits at presentation time)
- **Action Items**: items with Status = "Open" or "In Progress". Cross-reference with current Jira data: if an action item references a WB-XXX key that is now in Done/Closed/Resolved status, mark it "Resolved" in the new doc. Items without Jira links carry forward unchanged.
- **RAID Log**: carry forward items with Status != "Closed" or "Resolved"
- **Key Initiatives**: carry forward entire section as-is

If no previous doc exists (first run for this customer), note: "First cadence doc for [Customer]. No carry-forward data."

**Resolution heuristics:**
- An action item is "resolved" if its linked Jira issue is in Done/Closed/Resolved status
- An action item without a Jira link carries forward unless marked "Done" in the previous doc
- If parsing the previous doc fails (user may have manually edited it), carry forward nothing rather than corrupt data -- note "Could not parse previous doc -- starting fresh for carried items."

### Step 5: Gather Product Updates

Gather product updates from the lookback window, then filter by the customer's `deployment_type` from customers.yaml.

**Source 1: W&B Release Notes (docs.wandb.ai)**

Fetch SDK and server release notes via WebFetch:
```
https://docs.wandb.ai/release-notes/sdk-releases
https://docs.wandb.ai/release-notes/server-releases
```

Extract entries within the lookback window. SDK releases are relevant to all deployment types. Server releases are relevant to `dedicated-cloud` and `server` customers only.

**Source 2: Beamer Changelog (app.getbeamer.com/wandb/en)**

Beamer loads content dynamically via a POST endpoint:
```
POST https://app.getbeamer.com/loadMoreNews
Content-Type: application/x-www-form-urlencoded
Body: app_id=iTpiKrhl12143&language=EN&publicPage=true&post=false
```

If the POST fails or returns HTML instead of data, fall back to WebFetch on the page URL and extract what's available from the static HTML. Each entry has categories (models, weave, agents, inference, etc.) and a date. Filter to the lookback window.

**Source 3: Slack channels**

Read recent messages from these channels for product announcements:
```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/channels.py history \
  --channel C05MEBCNM9S --limit 30 --oldest <lookback_timestamp> --pretty
```
```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/channels.py history \
  --channel C04521MA98X --limit 30 --oldest <lookback_timestamp> --pretty
```

Channel IDs: `C05MEBCNM9S` (#product-releases), `C04521MA98X` (#announcements).

**Filtering by deployment type:**

| Customer deployment_type | SDK releases | Server releases | Beamer (SaaS features) |
|--------------------------|-------------|-----------------|----------------------|
| saas | Yes | No | Yes |
| dedicated-cloud | Yes | Yes (relevant subset) | Some (check if feature applies) |
| server | Yes | Yes | No (SaaS-only features don't apply) |

**Deduplication:** The same release may appear across Beamer, Slack, and docs. Deduplicate by matching version numbers or feature names. Present each update once with the most informative description.

### Step 6: Populate Template

Read `templates/cadence-review.md` as the structural blueprint. The agenda follows a meeting-driven structure, not a data-source-driven structure:

| Agenda Section | Source |
|----------------|--------|
| **1. What's New** | Lead with wins: recently resolved Jira issues (from Step 2) framed as "we fixed X" or "Y is now available". Then key highlights from Slack threads (Step 3) and notable product updates (Step 5). Frame everything from the customer's perspective — what changed for them, not what W&B shipped internally. |
| **2. Ongoing Actions and Updates** | Carry-forward action items from Step 4 + new items from Slack threads. Cross-reference with Jira status for resolution. |
| **3. Summary of Recent Events** | Recent Slack Threads (Step 3 summaries) + Support Tickets (Step 2 open/closed/stale tables) |
| **4. Product Updates and Announcements** | Filtered product updates from Step 5, relevant to customer's deployment type |
| **5. Usage and Initiatives** | Key Initiatives carry-forward from Step 4. Usage data placeholder for future BigQuery integration. |
| **6. Any Other Business** | Open floor — empty placeholder for live discussion |

All agenda sections must appear in the output. If a section has no data, use a brief placeholder (e.g., "No new product updates in this period.", "No open action items.").

### Step 6: Save or Preview

If `--dry-run` was specified, display the populated agenda in the chat response. Do not write any files or publish to Confluence.

Otherwise, produce outputs in this order:

#### 6a: Publish to Confluence (primary output)

Create a Confluence page in the customer's cadence folder using the Confluence skill. The page uses markdown format — Confluence converts it to native XHTML with proper tables, headings, and links.

```bash
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/pages.py create \
  --title "<Customer> : W&B <Cadence Type> — YYYY-MM-DD" \
  --body "<markdown content>" \
  --parent-id <CUSTOMER_CADENCE_FOLDER_ID> \
  --pretty
```

The Confluence page is the shareable, persistent record. Team members and the customer can view it directly.

**Confluence credentials**: The Confluence skill uses `CONFLUENCE_EMAIL`/`CONFLUENCE_TOKEN` from `~/.tsm-ai/.env` (CoreWeave Confluence instance). These are separate from the Jira credentials (`ATLASSIAN_EMAIL`/`ATLASSIAN_TOKEN`).

If Confluence publishing fails (credentials missing, permission error), fall back to local markdown and note the failure. Do not block the entire workflow on Confluence.

#### 6b: Save local markdown (always)

Save the agenda locally as a markdown file for carry-forward and local reference:
```
customers/<customer>/calls/YYYY-MM-DD-<cadence-type>.md
```

Create the directory if it doesn't exist:
```bash
mkdir -p customers/<customer>/calls/
```

This local file is the carry-forward source for Step 4 in the next cadence run.

#### 6c: Generate HTML (optional, `--html` flag)

If `--html` was specified, generate a styled HTML version using the customer-snapshot design system (Instrument Serif + Outfit + JetBrains Mono, gold accent, pill badges, stat counters, light/dark mode, internal/external audience toggle).

Save to: `customers/<customer>/calls/YYYY-MM-DD-<cadence-type>.html`

Open in browser: `open <path>`

The HTML version is for screen-sharing and presentation — it's the same data as the Confluence page, just visually polished.

### Step 7: Summary

After saving (or previewing), show what was gathered:

```
Cadence Prep Summary for [Customer] ([type])
  Jira: [N] open issues, [M] recently closed, [K] stale
  Slack: [N] notable threads from [channels]
  Carry-forward: [N] action items, [M] RAID items from [previous doc date]
  Confluence: <page URL>
  Local: customers/<customer>/calls/YYYY-MM-DD-<type>.md
  HTML: customers/<customer>/calls/YYYY-MM-DD-<type>.html (if --html)
```

If any data sources were unavailable or returned gaps, list them here so the SE knows what to fill manually.

## Handling Unknown Customers

When a customer is not in `templates/customers.yaml`:

1. Search Jira with fuzzy match: `issues.py list --customer "<name>" --max-results 5 --pretty` to confirm the customer name exists in Jira
2. Search Slack channels: `channels.py list --types public_channel --limit 500` and filter for `ext-` or `wandb-` channels matching the customer name
3. Present findings to the SE for confirmation
4. If confirmed, offer to add the customer entry to customers.yaml with the discovered details
5. Proceed with whatever data is available (Jira may work without a YAML entry; Slack needs channel IDs)

## Safety Rules

1. **Read-only data gathering.** All Jira and Slack operations are read-only. Never create, modify, or transition Jira issues. Never post Slack messages.
2. **No fabrication.** Every fact in the agenda must come from Jira or Slack data fetched in this session. If a section has no data, write "No data available" -- never guess ticket IDs, statuses, or Slack conversations.
3. **Previous docs are immutable.** Never modify, edit, or overwrite previous cadence files. Always create a new file with today's date.
4. **Link everything.** Every Jira issue reference must include the full `https://wandb.atlassian.net/browse/WB-XXX` URL. Every Slack reference must include the full `https://coreweave.slack.com/archives/` permalink.
5. **Respect the template.** Generate all sections from `templates/cadence-review.md`. Do not add custom sections or remove template sections. The SE decides what to present.
6. **Handle failures gracefully.** If Jira returns no issues, note it. If Slack credentials fail, note which sections are incomplete. If carry-forward parsing fails, start fresh. Never block on a single data source failure.

## Link Construction Reference

### Jira Issue URLs

Format: `https://wandb.atlassian.net/browse/WB-XXX`

Every issue key in every table and mention must be a clickable markdown link:
```markdown
[WB-123](https://wandb.atlassian.net/browse/WB-123)
```

### Slack Permalinks

Format: `https://coreweave.slack.com/archives/{channel_id}/p{ts_without_dot}`

Convert the Slack message timestamp to a permalink:
- Message ts: `1706123456.789012`
- Strip the dot: `1706123456789012`
- Permalink: `https://coreweave.slack.com/archives/C01234ABCDE/p1706123456789012`

```markdown
[thread](https://coreweave.slack.com/archives/C01234ABCDE/p1706123456789012)
```

## Context References

These files provide customer-specific data needed during preparation:

- `templates/customers.yaml` -- customer registry with Jira names, Slack channels, cadence schedule, contacts
- `templates/cadence-review.md` -- output document template (9 sections)
- `.claude/rules/atlassian.md` -- FE-UPDATE comment convention and Jira workspace rules
- `.claude/rules/slack.md` -- Slack workspace conventions and channel naming patterns
- `customers/<customer>/calls/` -- previous cadence documents for carry-forward

## Confluence Integration

The skill publishes cadence documents to CoreWeave Confluence (coreweave.atlassian.net) as the primary persistent output. This uses separate credentials from Jira:

- **Jira** (wandb.atlassian.net): `ATLASSIAN_EMAIL` / `ATLASSIAN_TOKEN`
- **Confluence** (coreweave.atlassian.net): `CONFLUENCE_EMAIL` / `CONFLUENCE_TOKEN`

Both are stored in `~/.tsm-ai/.env`. The Confluence skill falls back to `ATLASSIAN_*` if `CONFLUENCE_*` vars are not set.

Each customer should have a cadence folder in Confluence where dated pages are created as children. Store the Confluence parent folder ID in `templates/customers.yaml` under `confluence.cadence_folder_id` for each customer.
