---
name: 3p-update
description: "Generate 3P (Progress, Plans, Problems) updates for customer engagements. Use when the user mentions 3P, programme update, status update, progress report, or asks 'what's happening with CustomerName'. Trigger for /3p-update with or without a customer name."
argument-hint: "[customer-name] (optional -- omit for portfolio view)"
---

# 3P Update Generator

Generate concise, data-driven Progress / Plans / Problems updates by synthesizing data from Asana (SE actions), Jira (engineering status), and Slack (customer signals). Supports per-customer and cross-customer portfolio modes.

Refer to `.claude/rules/asana.md` for Asana conventions and `.claude/rules/atlassian.md` for Jira/FE-UPDATE conventions.

## Prerequisites

- **Asana** -- `ASANA_TOKEN` in `~/.fe-skills/.env` (run `/asana-setup` if not configured)
- **Jira** -- `ATLASSIAN_EMAIL` and `ATLASSIAN_TOKEN` in `~/.fe-skills/.env` (run `/atlassian-setup` if not configured)
- **Slack** -- `SLACK_TOKEN` and `SLACK_COOKIE` in `~/.fe-skills/.env` (run `/slack-setup` if not configured)
- **Customer registry** -- Customer must exist in `templates/customers.yaml`

Not all sources are required. The skill produces output from whatever sources are available and notes gaps.

## Output Modes

| Mode | Trigger | Output |
|---|---|---|
| **Per-customer** | `/3p-update GResearch` | Single customer 3P with detailed citations |
| **Cross-customer (portfolio)** | `/3p-update` (no name) | All customers summary with cross-cutting themes |

## Optional Flags

| Flag | Effect |
|---|---|
| `--confluence` | Also publish the 3P as a Confluence page |

## Pipeline

### Step 1: Parse input and determine mode

- If a customer name is provided: **per-customer mode** (single customer 3P)
- If no customer name: **cross-customer mode** (portfolio 3P covering all customers in the registry)
- Check for `--confluence` flag

### Step 2: Load customer registry

Read `templates/customers.yaml` to resolve customer data.

- **Per-customer mode:** Find the matching customer entry by `name` (case-insensitive)
- **Cross-customer mode:** Collect all customers where `action_tracker_id` is not `"PLACEHOLDER"`

If per-customer mode and the customer is not found in the registry, tell the user and stop.

### Step 3: Gather data from three sources

For each customer in scope, gather data from all available sources. Skip sources that are not configured (PLACEHOLDER GIDs/IDs) and note the gap in the output.

#### 3a. Asana tasks (Progress + Plans)

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/query.py tasks \
  --project-gid <action_tracker_id> --limit 100 --pretty
```

Process the response:
- **Recently completed** (last 7 days, `completed_at` within range): feed into **Progress**
- **In Progress section** (active work): feed into **Progress**
- **To Do / Scheduled/Future sections** (upcoming work): feed into **Plans**
- **Overdue tasks** (past `due_on`, not completed): feed into **Problems**
- **Stale tasks** (In Progress or To Do, `modified_at` > 7 days ago): feed into **Problems**

If `action_tracker_id` is `"PLACEHOLDER"`: skip Asana, note "Asana not configured" in output.

#### 3b. Jira activity (Progress + Problems)

```bash
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py list \
  --customer "<jira_customer>" --max-results 50 --with-comments
```

Process the response:
- **Recently resolved issues** (status = Resolved/Closed/Done, updated in last 7 days): feed into **Progress**
- **Issues with recent engineering comments** (non-FE-UPDATE comments in last 7 days): feed into **Progress**
- **Stale/blocked issues** (no updates 14+ days, still open): feed into **Problems**
- **New P0/P1 issues** (created in last 7 days): feed into **Problems**

Note: FE-UPDATE comments from SEs do NOT count as engineering activity (prevents gaming staleness).

#### 3c. Slack signals (Problems + Progress)

For each channel in the customer's `slack_channels` where `id` is not `"PLACEHOLDER"`:

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/channels.py history \
  --channel <channel_id> --limit 50 --oldest <7_days_ago_unix_timestamp>
```

Process the response:
- **Frustration signals** (escalation language, mentions of alternatives, repeated asks): feed into **Problems**
- **Positive signals** (thanks, appreciation, successful outcomes, shipped features): feed into **Progress**

If no Slack channels are configured (all IDs are PLACEHOLDER): skip Slack, note "Slack channels not configured" in output.

### Step 4: Synthesize 3P update

Read all gathered data and produce the 3P output.

**Tone guidance:**
- Concise, data-driven, factual
- 1-3 sentences per section
- Reference specific Jira issues (WB-XXXX) and Asana tasks by name
- No filler or generic statements
- If a section has nothing noteworthy, say "No significant updates this period" rather than fabricating content

#### Per-customer format

```
[emoji] [CustomerName] -- [date]

**Progress**
[1-3 sentences: what happened this week. Cite Jira issues resolved, Asana tasks completed, positive Slack signals.]

**Plans**
[1-3 sentences: what's coming next. Cite Asana tasks in To Do/In Progress with upcoming due dates.]

**Problems**
[1-3 sentences: what's blocked or at risk. Cite overdue Asana tasks, stale Jira issues, negative Slack signals. If nothing: "No blockers identified."]
```

**Emoji selection:**
- Rocket for momentum (lots of progress, things moving fast)
- Construction for heavy work (large active workload)
- Warning for problems (blockers, escalations)
- Checkmark for smooth sailing (no issues, steady progress)

#### Cross-customer (portfolio) format

```
[clipboard emoji] SE Portfolio Update -- [date]

[For each customer with data:]

**[CustomerName]**
- Progress: [1 sentence]
- Plans: [1 sentence]
- Problems: [1 sentence or "None"]

[End with:]

**Cross-cutting**
- [Any themes across customers: common blockers, shared wins, resource constraints]
```

### Step 5: Output

**Default:** Print the 3P text to the user as Slack-ready output (copy-paste into Slack).

**If `--confluence` flag is set:**

Convert the 3P text to simple HTML (paragraphs, bold, links) and create a Confluence page:

```bash
uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/pages.py create \
  --space "~PERSONAL_SPACE" --title "3P Update -- [CustomerName] -- [date]" \
  --body "<html-content>"
```

Print both the text output and the Confluence page URL.

### Step 6: Present to user

Show the 3P update text. Include a brief footer noting:
- **Data sources used:** which sources returned data (Asana, Jira, Slack)
- **Data gaps:** which sources were skipped and why (not configured, no data, PLACEHOLDER)
- **Confluence URL:** if `--confluence` was used, include the page link

## Anti-patterns

- Do NOT fabricate data or connections. If a source returns nothing, say so.
- Do NOT include generic filler ("The team continues to make progress..."). Every sentence must reference specific data.
- Do NOT include internal Slack sentiment details in the output (that belongs in the intelligence dashboard via `/customer-snapshot`).
- Do NOT attempt to read Gong, email, or other sources not listed above.
- Do NOT attribute one customer's data to another customer (in portfolio mode, keep data strictly separated).

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No Asana data | Check `action_tracker_id` in `templates/customers.yaml`, run `/asana-setup` |
| No Jira data | Check `jira_customer` name spelling in `templates/customers.yaml` |
| No Slack data | Check `slack_channels[].id` is not `"PLACEHOLDER"` |
| Confluence publish fails | Check Confluence credentials via `/credential-status` |
| Empty 3P sections | Normal if no recent activity; skill notes "No significant updates this period" |
| Customer not found | Add the customer to `templates/customers.yaml` with required fields |

## Data Source Reference

| Source | Skill | Feeds into | Key fields |
|--------|-------|-----------|------------|
| Asana tasks | `.claude/skills/asana/scripts/query.py tasks` | Progress, Plans, Problems | `completed_at`, `due_on`, `modified_at`, `memberships` (section) |
| Jira issues | `.claude/skills/jira/scripts/issues.py list` | Progress, Problems | `status`, `priority`, `updated`, `comments` |
| Slack messages | `.claude/skills/slack/scripts/channels.py history` | Progress, Problems | `text`, `ts`, `user` |
| Customer registry | `templates/customers.yaml` | All (customer lookup) | `action_tracker_id`, `jira_customer`, `slack_channels` |

## Related Skills

- `/asana` -- Base skill for Asana task queries and mutations
- `/jira` -- Base skill for Jira issue queries and FE-UPDATE management
- `/slack` -- Base skill for Slack channel history and search
- `/confluence` -- Publishing target for `--confluence` flag
- `/customer-snapshot` -- Full intelligence dashboard (deeper analysis than 3P)
- `/cadence-prep` -- Meeting prep (complementary to 3P -- agenda vs status update)
