---
name: rats
description: "Use when the user mentions RATS, roses and thorns, biweekly update, R&T page, biweekly retrospective, highlights and lowlights, what did I do last two weeks, confluence contribution, biweekly retro, or preparing their section for the team Roses & Thorns page. Searches Slack for the user's recent posts and produces copy-ready categorized output (Highlights, Lowlights, Learnings, Risks) matching the team R&T page format."
argument-hint: "[--days N]"
allowed-tools: Bash(uv run --project .claude/skills/slack python .claude/skills/slack/scripts/*.py *)
---

# Roses & Thorns -- Biweekly Contribution Automator

Search Slack for your recent posts, auto-categorize them into Highlights / Lowlights / Learnings / Risks, rewrite them in your voice, and present copy-ready output for pasting into the team Roses & Thorns Confluence page.

This is a **composition skill** -- it uses the existing `/slack` skill for search, then applies AI categorization and rewriting.

**Output:** Formatted text displayed in the terminal. You copy/paste your section into the shared team Live Doc on Confluence.

## Prerequisites

- Slack credentials configured (`SLACK_TOKEN`, `SLACK_COOKIE` in `~/.fe-skills/.env`). Run `/slack-setup` if not done.
- Dependencies installed: `cd .claude/skills/slack && uv sync`

## Pipeline

### Step 1: Parse arguments

Extract the `--days N` flag from user input. Default to **14** days if not specified.

Calculate the search start date:

```
START_DATE = today minus N days, formatted as YYYY-MM-DD
```

For example, if today is 2026-03-16 and `--days 14`, then `START_DATE = 2026-03-02`.

Common invocations:
- `/roses-and-thorns` -- last 14 days (default)
- `/roses-and-thorns --days 21` -- last 3 weeks (useful when the biweekly cadence slips)
- `/roses-and-thorns --days 7` -- just last week

### Step 2: Identify the current user

Look up the authenticated Slack user so the search is scoped to whoever is running the skill:

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/users.py whoami --pretty
```

Extract the `user` field from the response (e.g., `astevenson`). Store as `USERNAME`.

### Step 3: Search Slack for user's posts

Use the Slack skill's search.py to find all posts by the user in the time period:

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/search.py \
  --query "from:@USERNAME after:YYYY-MM-DD" --count 100 --sort timestamp --sort-dir desc
```

Replace `USERNAME` with the value from Step 2 and `YYYY-MM-DD` with the calculated `START_DATE`.

**Pagination:** Check `messages.paging.pages` in the response. If there are multiple pages, fetch each additional page:

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/search.py \
  --query "from:@USERNAME after:YYYY-MM-DD" --count 100 --sort timestamp --sort-dir desc --page N
```

**For each message, extract:**
- `text` -- the message content
- `channel.name` -- which channel it was posted in
- `ts` -- timestamp (convert to human-readable date for display)
- `permalink` -- Slack link to the message
- `reply_count` -- whether the message started a thread

**Thread handling:** If a message has `reply_count > 0`, note it but do NOT fetch the full thread by default. The top-level post captures the user's contribution. Thread replies are often responses from others and add noise.

**Deduplication:** If the same text appears in multiple channels (cross-posts), keep only the first occurrence by timestamp.

**Filtering:** Skip purely administrative messages:
- Standup bot responses or form submissions
- Emoji-only messages
- Link-only shares without any accompanying text/context
- Automated workflow messages

### Step 4: Categorize posts

Using your own judgment, assign each post to one or more of these categories:

| Category | What belongs here |
|----------|-------------------|
| **Highlights** | Customer wins, progress, positive engagement, successful deliveries, commitments fulfilled, hackweek demos, team achievements |
| **Lowlights** | Customer frustrations, outages, near-misses, time sinks, churn signals, blocked work, things that went wrong |
| **Learnings** | Process insights, tool discoveries, productivity improvements, "TIL" moments, workflow optimizations |
| **Risks** | Renewal concerns, escalation patterns, items with forward-looking negative impact, things that could go wrong |

**Consolidation rules (CRITICAL — this is not a post-by-post listing):**

**ACCURACY IS NON-NEGOTIABLE:**
- NEVER fabricate connections between unrelated posts. Two posts mentioning the same customer does NOT mean they are about the same topic.
- NEVER attribute actions to the user that they didn't do. Sharing news about a feature ≠ shipping that feature. Discussing an issue ≠ fixing it. Read each post carefully for what the user ACTUALLY DID.
- NEVER merge posts unless they are genuinely about the exact same specific topic (e.g., multiple updates on the same parquet backfill). Same customer is NOT enough — same customer + same issue is required.
- When in doubt, keep items separate rather than merge incorrectly.

**Consolidation approach:**
- Only merge posts that are clearly sequential updates on the SAME specific issue or task.
- Target **3-5 items per category**, but categories DO NOT need to be equal. If the period had more lowlights than highlights, show more lowlights. Reflect reality, not a balanced template.
- Do NOT bias toward optimism. SEs often have more lowlights and risks than highlights — that's the nature of post-sales work. If the raw posts skew negative, the output should too.
- Achieve the target count by PRIORITIZING the most impactful items, not by aggressively merging unrelated ones.
- Drop low-signal items (routine updates, minor admin, chat banter, link-only shares) to reduce count.
- A consolidated item CAN appear in multiple categories (e.g., "Both my lowlights are also risks").
- Other Activities should have 1-3 items max — only genuinely notable things (hackweek, events, initiatives).

**What the user DID vs what the user SAW (this is the #1 failure mode — get it right):**

Claude has a strong tendency to use heroic/inflated verbs. Fight this actively. Default to MODEST verbs unless the post CLEARLY shows the user personally did the work.

| What the post shows | WRONG verb | RIGHT verb |
|---------------------|------------|------------|
| Shared a product release in channels | "Shipped", "Launched", "Delivered" | "Shared", "Announced", "Highlighted to customers" |
| Coordinated getting something built | "Built", "Drove", "Engineered" | "Coordinated", "Pushed for", "Got X built" |
| Posted about a customer issue | "Fixed", "Resolved", "Solved" | "Tracked", "Investigated", "Raised" |
| Escalated to eng | "Drove resolution", "Led the fix" | "Escalated", "Raised priority" |
| Shouted someone out | "Delivered the work" | "Recognised X's work" |
| Discussed in a meeting | "Drove alignment", "Led the strategy" | "Discussed", "Proposed", "Raised" |

When in doubt, use the less heroic verb. The user can always upgrade it during review.

**IMPORTANT -- User review checkpoint:**

Present the categorized list to the user for review BEFORE proceeding to Step 5. Format as:

```
## Categorized Posts (N posts from M Slack messages)

### Highlights (X items)
1. [summary] -- #channel-name, YYYY-MM-DD [permalink]
2. ...

### Lowlights (X items)
1. [summary] -- #channel-name, YYYY-MM-DD [permalink]
2. ...

### Learnings (X items)
1. ...

### Risks (X items)
1. ...

### Skipped (X messages)
- [reason]: [brief description]

### Other Activities (X items)
1. [items that don't fit the 4 main categories but represent notable work]
```

Ask the user:
- "Should I move, remove, or edit any items before I write these up?"
- "Any items to add to Other Activities?"

Wait for user confirmation before proceeding.

### Step 5: Write up and present final output

Rewrite the approved items as polished bullet points ready to paste into the Confluence page.

**Writing style (match user's established tone from the team page):**
- Each bullet: 1-2 sentences, direct and specific
- Name customers and people where relevant
- Include context on WHY something matters (renewal risk, time impact, etc.)
- Rewrite raw Slack messages into polished prose -- do not copy/paste Slack verbatim
- Do NOT prefix with `[Al]` -- the user adds their own name toggle/expand on the page

**Present the final output in a clear, copy-pasteable format:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ROSES & THORNS -- Ready to paste
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Post-sales

### Highlights
- Bullet point one about a customer win
- Bullet point two about positive engagement

### Lowlights
- Bullet point about a frustration or setback

### Learnings
- Bullet point about something learned

### Risks
- Bullet point about a forward-looking concern

## Other Activities (if any)

### Highlights
- Hackweek project, event, internal initiative
```

After displaying, remind the user:
- "Copy your section above into the team Roses & Thorns page"
- Link to the current R&T page if known

### Step 6: Present summary

Show a brief summary of what was gathered:

```
## Summary

- **Period:** YYYY-MM-DD to YYYY-MM-DD (N days)
- **Slack posts found:** X total
- **Posts used:** Y (Z skipped)
- **Breakdown:**
  - Highlights: N items
  - Lowlights: N items
  - Learnings: N items
  - Risks: N items
  - Other Activities: N items
```

## Other Activities

The team Roses & Thorns page also has an "Other Activities" section for notable work that doesn't fit the 4 main categories. Examples:
- Hackweek projects or demos
- Conference attendance or talks
- Internal tooling contributions
- Team events or offsites
- Cross-team collaboration initiatives

During categorization (Step 3), if posts don't fit Highlights/Lowlights/Learnings/Risks but represent notable work, suggest them for Other Activities.

## Safety Rules

- **Slack operations are read-only.** The skill only uses `search.py` -- no messages are sent or modified.
- **No Confluence writes.** Output is displayed in terminal only. The user pastes into the Live Doc manually.
- **User review checkpoint.** Categorized posts are reviewed in Step 3 before the final write-up.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No Slack results | Check date range -- try `--days 21` for a wider window. Verify Slack credentials with `/credential-status`. |
| Too many results | The default `from:@astevenson` searches all channels. If overwhelmed, narrow the search period with a smaller `--days` value. |
| Missing categories | Some periods may have no Lowlights or Risks -- that's fine. Only include categories that have items. |
| Duplicate content | The deduplication in Step 2 handles cross-posts. If you see duplicates, they may be similar but distinct messages. |
