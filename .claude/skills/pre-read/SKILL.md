---
name: pre-read
description: "Generate a structured pre-read document for a customer meeting by gathering and synthesizing Slack threads, Jira issues, and manual context. Use this skill whenever the user mentions pre-read, meeting prep, customer briefing, account summary, customer deep-dive, QBR prep document, or wants to compile Slack + Jira history into a concise summary for a specific customer. Also trigger when the user pastes multiple Slack thread URLs and asks for a summary or synthesis."
argument-hint: "[customer name] [--threads URL1 URL2 ...] [--threads-file path/to/file.txt] [--channels #chan1 #chan2 ...] [--since YYYY-MM-DD] [--goal 'text or URL']"
---

# Pre-Read Generator

Produce a concise, detail-rich pre-read document for a customer meeting. The pre-read synthesizes information from three sources: Slack threads, Jira issues, and manual context you provide. The output is a single Markdown file that distills potentially hundreds of messages into a structured briefing.

## Why This Exists

Customer accounts accumulate history across many Slack threads (external channels, internal channels, engineering discussions) and Jira tickets. Before a meeting, an SE needs a single document that captures the full picture: what happened, what's configured, what's broken, what's pending. Reading all the threads manually takes hours. This skill does the reading and produces the briefing.

## Prerequisites

- Slack skill configured (`/slack-setup` done, credentials in `~/.tsm-ai/.env`)
- Jira skill configured (`/atlassian-setup` done, credentials in `~/.tsm-ai/.env`)
- Both skills' dependencies installed (`uv sync` in each skill directory)

## Input Gathering

When the user invokes this skill, collect three categories of input. Not all are required — the skill works with whatever is available.

### 1. Customer Name (required)

Used to:
- Query Jira for all customer issues (`--customer CustomerName`)
- Scope Slack searches (`"CustomerName" in:#channel`)
- Name the output file

### 2. Slack Threads (optional, but this is where the value is)

Accept threads in two ways:

**Pasted URLs** — the user gives specific thread links:
```
https://coreweave.slack.com/archives/C0ABC1234/p1709123456789012
https://coreweave.slack.com/archives/C0DEF5678/p1709234567890123
```

Parse each URL to extract `channel_id` and `thread_ts`:
- Channel ID: the `C...` segment after `/archives/`
- Thread TS: the `p...` segment, converted to Slack timestamp format (insert `.` before last 6 digits, drop the `p` prefix)
  - Example: `p1709123456789012` → `1709123456.789012`

**Thread file** — a text file with one URL per line. Useful when you have a curated list of threads (e.g., saved from a previous run, or compiled over time):
```
--threads-file ~/Documents/g-research-threads.txt
```

The file should contain one Slack thread URL per line. Blank lines and lines starting with `#` are ignored (so you can annotate the file):
```
# G-Research key threads - March 2026
https://weightsandbiases.slack.com/archives/C06NX624Q9G/p1771925928003129
https://weightsandbiases.slack.com/archives/C06KJEHH960/p1771953979998409
# ... more URLs
```

Can be combined with `--threads` (inline URLs) and `--channels` — all sources are merged and deduplicated.

**Channel + date range** — the user names channels and a time window:
```
Channels: #wandb-customername, #internal-customername
Since: 2025-01-01
```

For channel-based input, search each channel for messages in the date range, identify threads with replies (`reply_count > 0`), and add them to the fetch list.

### 3. Briefing Goal (optional, but strongly recommended)

A short framing statement that tells the synthesis agent what lens to read everything through. This shapes what gets prioritised in the Executive Summary, which themes get the most depth, and how Actions Required are framed.

Accept in three forms:
- **Freeform text** — a paragraph the user types or pastes, e.g., "Renewal is 30th April. The customer's top concerns are charting trust, SDK reliability, and observability. We need to show progress on all three."
- **Slack post URL** — a single message URL (not a thread) containing current priorities or meeting agenda. Fetch it, extract the text, and use it as the framing.
- **File path** — a local file containing the briefing context.

If provided, the synthesis agent should:
- Open the Executive Summary by addressing the briefing goal directly
- Weight Issue Themes and Actions Required toward the goal's priorities
- Flag any source material that contradicts or complicates the stated goal

If not provided, the skill still works — the synthesis agent frames around what it finds (biggest open issues, most recent activity, highest-priority Jira items).

### 4. Manual Context (optional)

Additional context the user provides beyond Slack and Jira. Accept multiple types:

**Meeting transcripts (Granola, Otter, etc.):**
- Pasted text directly into the conversation
- File path to a `.md`, `.txt`, or `.pdf` export (e.g., `~/Documents/granola/g-research-2026-03-05.md`)
- Multiple transcripts are fine — label each with meeting date and attendees if the user provides them

Meeting transcripts often contain the decisions that explain actions seen in Slack threads. The synthesis agent should cross-reference transcript content with thread timelines — if a thread references "the decision from Monday's call" and a transcript covers that call, connect them.

**Spreadsheets and priority lists:**
- CSV or Excel file path (e.g., `~/Documents/g-research-priority-bugs.csv`)
- Pasted table data

When a customer-maintained priority list is provided, the synthesis agent should:
- Cross-reference it against the Jira pull — flag items on the customer's list that don't have a matching Jira issue (or where Jira status disagrees with the customer's stated priority)
- Flag Jira issues the customer hasn't listed — these may be resolved, deprioritised, or simply missing from their tracking
- Note any priority ordering differences (e.g., customer ranks item X as #1 but Jira has it as P2)
- Include a "Priority Alignment" subsection in Issue Themes or a standalone section if there are significant discrepancies

**Other context:**
- Pasted text: notes, email excerpts, internal docs
- File paths: `~/Documents/customer-notes.md` or similar

Store all manual context with its type label for the synthesis phase.

## Execution Pipeline

### Phase 1: Parallel Thread Fetching + Summarization

For each Slack thread (from URLs or channel search), spawn a sub-agent that:

1. **Fetches the full thread** using the Slack skill:
   ```bash
   uv run --project .claude/skills/slack python .claude/skills/slack/scripts/threads.py replies --channel CHANNEL_ID --ts THREAD_TS --limit 200
   ```

2. **Extracts linked threads** — scan message text for Slack thread URLs matching the pattern `https://*.slack.com/archives/C[A-Z0-9]+/p[0-9]+`. These are cross-references to related discussions (e.g., a customer thread linking to an internal engineering discussion). Collect these as "discovered threads."

3. **Produces a structured thread summary** with these fields:
   - **Thread URL**: full clickable URL to the thread root message (reconstruct from channel ID + thread TS)
   - **Channel**: which channel this was in and its apparent role (e.g., customer-facing, internal SE discussion, engineering team). Infer from channel name and participants — don't assume a fixed naming convention.
   - **Date range**: first message to last message
   - **Participants**: who was involved (names, not IDs — resolve via users.py if needed)
   - **Topic**: one-line description of what this thread is about
   - **Key facts**: specific details mentioned — settings, configurations, versions, error messages, metrics, timelines. Be precise, not vague. Include exact values.
   - **Configuration changes**: any setting, env var, rate limit, DB parameter, or infrastructure change mentioned — capture the before value (if stated), after value, date, and who made or requested the change. These feed the Configuration Drift analysis in synthesis.
   - **Actions taken**: what anyone did or committed to doing, with who and when
   - **Outcome/Status**: how the thread ended — resolved, pending, escalated, unclear
   - **Linked threads**: any discovered thread URLs for Phase 1b
   - **Impact** (if incident/outage): duration of impact, severity (full outage / degraded / blocked workflow / intermittent), number of users or teams affected if mentioned, and how it was resolved. Use the thread's own language — if they say "down for 2 hours" record that; if timing is ambiguous, note the bounds (e.g., "between 1-3 hours based on timestamps"). If not an incident thread, omit this field.
   - **Notable quotes**: 1-2 verbatim quotes that capture something important (attribute them). For each quote, include the **specific message URL** (channel ID + message TS) so the synthesis can link directly to it, not just the thread root.
   - **Key message URLs**: for any message containing a decision, commitment, config change, or notable quote, record the specific message URL (reconstruct from channel ID + message TS, using the message's `ts` field). These allow the synthesis to link to the exact point in a thread, not just the thread root.

**Sub-agent prompt template:**

```
You are summarizing a Slack thread for a customer pre-read document. Your job is to extract maximum useful detail in minimum words. Think of yourself as a court reporter, not a novelist.

Rules:
- Be SPECIFIC. "Changed a setting" is useless. "Enabled `wandb.init(settings=wandb.Settings(x_disable_stats=True))` on 2025-02-15" is useful.
- Include exact error messages, config values, version numbers, metric values.
- Attribute actions to people and include dates (use unambiguous format to avoid confusion between US and International date formats): "Sarah (W&B eng) deployed fix in v0.18.3 on 4th March" not "a fix was deployed."
- Distinguish between customer-side actions and W&B-side actions.
- Note any Slack thread URLs that appear in messages — these are cross-references we need to follow.
- If the thread is long and meandering, focus on: decisions made, settings changed, issues identified, commitments given.
- The audience is an SE preparing for a customer meeting. They need facts they can reference, not summaries they have to verify.
- CONFIGURATION CHANGES: When any setting, env var, rate limit, DB parameter, version, or infrastructure detail is mentioned, capture it explicitly in the "Configuration changes" field. Record: setting name, before value (if stated), after value, date, who changed it. This is critical — the synthesis phase tracks how settings drift over time.
- MESSAGE URLS: For any message containing a decision, commitment, config change, or notable quote, record its specific URL. Reconstruct from the channel ID and the message's `ts` field: `https://weightsandbiases.slack.com/archives/{channel_id}/p{ts_without_dot}`. This lets the final document link to the exact message, not just a thread with hundreds of replies.

Thread data (JSON):
{thread_json}

Produce your summary in the structured format described above.
```

### Phase 1b: Follow Discovered Thread Links (depth-limited)

After Phase 1 completes, collect all "discovered threads" from the summaries. These are threads referenced *within* the seed threads — typically engineering discussions, escalation threads, or related customer conversations.

- Deduplicate against already-fetched threads
- Fetch and summarize each discovered thread using the same sub-agent pattern
- For these second-level threads, also extract any linked thread URLs
- Tag these summaries as "referenced thread (depth 1)"

### Phase 1c: Follow Second-Hop Links (depth 2)

After Phase 1b completes, collect any newly discovered thread URLs from the depth-1 summaries.

- Deduplicate against all already-fetched threads
- Fetch and summarize each discovered thread
- Do NOT follow links found in these third-level threads (depth limit = 2)
- Tag these summaries as "referenced thread (depth 2)" so the synthesis knows they're tertiary context

### Phase 2: Jira Issue Pull (parallel with Phase 1)

Spawn a sub-agent that:

1. **Pulls all customer issues with comments**:
   ```bash
   uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py list --customer CUSTOMER_NAME --with-comments --max-results 200 --pretty
   ```

   The default `--max-results` is 50, which truncates customers with many issues (G-Research has 84+). Always use 200 to avoid silently missing issues. If the customer has more than 200, increase further.

2. **Produces a Jira summary** with:
   - Total issue count by type (Bug, Feature Request, Story)
   - Total issue count by status (Open, In Progress, Resolved, Closed)
   - For each issue: key, summary, status, priority, last FE-UPDATE status (if any), last activity date, linked Slack threads
   - Highlight stale issues (no activity in 30+ days)
   - Highlight P0/P1 issues regardless of status

### Phase 3: Synthesis

Once all thread summaries, Jira data, and manual context are gathered, synthesize into the pre-read document. This is where the real intelligence lives — the synthesis agent must connect dots across threads, identify patterns, and produce something an SE can scan in 5 minutes and walk into a meeting feeling prepared.

**Synthesis agent instructions:**

You are writing a pre-read briefing for a Solutions Engineer at W&B (Weights & Biases) who is about to meet with a customer. You have thread summaries, Jira data, and possibly manual notes. Your job is to produce a document that answers: "What do I need to know about this account right now?"

**Briefing Goal Framing:**

If a briefing goal was provided, use it as the lens for the entire document:
- Open the Executive Summary by addressing the goal directly — "The current priorities are X, Y, Z. Here's where each stands."
- Weight Issue Themes toward the goal's priorities — themes that align with the stated goal get more depth; others are still included but concise.
- Frame Actions Required around the goal — what needs to happen to achieve it.
- Flag source material that contradicts or complicates the goal — e.g., if the goal says "demonstrate progress on charting" but threads show no progress, say that.

If no briefing goal was provided, frame around what the data reveals: biggest open issues, most recent activity, highest-priority Jira items.

**Cross-Thread Correlation:**

Multiple threads often discuss the same underlying issue from different angles — a customer reports a problem in #wandb-customer, the SE discusses it in #internal-customer, and engineering debugs it in their own channel. These are not three issues; they're three perspectives on one issue. The synthesis must correlate them. Note that channel names do not 100% match that trend but normally customer channels will include wandb in the name and internal channels will include internal. 

How to identify that threads are about the same issue:
- **Shared identifiers**: Jira keys (WB-123), PR numbers, error messages, feature names mentioned across threads
- **Shared participants**: The same engineer appearing in both the internal and eng thread
- **Temporal proximity + topic overlap**: Two threads starting within days of each other about the same symptom
- **Explicit cross-references**: Thread summaries will note linked threads — if Thread A linked to Thread B, they're related

How to handle correlated threads:
- **Merge into a single theme** in the Issue Themes section, not separate entries per thread
- **Unify the timeline** — present one chronological sequence with source attribution (e.g., "2025-01-15: Customer reported OOM errors [#wandb-acme] → 2025-01-17: Eng identified artifact cache leak [#internal-acme] → 2025-02-01: Fix shipped in v0.18.3 [eng team channel]")
- **Pull the best detail from each source** — the customer thread has the impact/urgency, the internal thread has the SE strategy, the eng thread has the technical root cause. Don't repeat the same event three times; synthesize the most useful detail from each.
- **Flag contradictions** — if one thread says "resolved" and another says "still investigating," or if Jira status conflicts with Slack discussion, call it out explicitly. These are exactly the things an SE needs to know before a meeting.
- **Preserve provenance** — after merging, the Source Index still lists each thread individually so the SE can drill into any specific conversation.

**Temporal Weighting:**

When source threads span many months, the pre-read must balance recency with historical context. Recent events drive the meeting; older events explain why things are the way they are.

- **Executive Summary**: Heavily weighted toward the last 30-60 days. Lead with what's active now.
- **Timeline**: Cover the full span, but increase density toward the present. Older events get concise one-liners; recent events get more detail. Think logarithmic — the last month might have 10 entries, the prior 6 months might have 5. If an older event is the root cause of a current issue, call that out explicitly (e.g., "First reported Jun 2025 — see Theme: SDK Crashes below").
- **Issue Themes**: This is where historical context earns its place. A theme should tell the full arc when it matters: "First reported Jun 2025, workaround applied Aug 2025, resurfaced Feb 2026 after upgrade to v0.19." The current status always leads, with history as supporting context that explains recurrence or root cause.
- **Impact Summary**: Include all incidents for cumulative totals (that's the whole point of quantifying), but group or annotate by time period so the reader sees recent vs. historical at a glance.
- **Open Items**: Recent only. If something from 9 months ago is still genuinely open, it belongs here — but stale items that nobody is actioning should be in Issue Themes as historical context, not Open Items.

The goal: a reader should be able to skim the top sections and know what matters *today*, then drill into themes for the backstory if they need it.

**Version and State Accuracy:**

Never infer current state by extrapolating from a sequence of changes. Only state a version, setting value, or infrastructure detail as "current" if the most recent source explicitly confirms it.
- WRONG: "Server version v0.77 (upgraded from v0.74.1 → v0.77)" when the latest thread only confirms v0.74.1 was deployed.
- RIGHT: "Server version v0.74.1 as of {date of most recent explicit mention}. Upgrade path: v0.52.2 → ... → v0.74.1."
- If uncertain, say "as of {date}, {value} — current state unconfirmed in sources" rather than guessing.

This rule applies to: server versions, SDK versions, DB configurations, rate limit values, infrastructure details (pod count, DB specs), and any other stateful setting.

**Configuration Drift Analysis:**

Thread summaries include a "Configuration changes" field that captures every setting change mentioned across all threads. The synthesis agent must aggregate these into a coherent picture:

1. **Build a change log per setting** — for any setting that was changed more than once, build a chronological list: date, old value → new value, who changed it, why (link to specific Slack message where available).

2. **Flag contentious settings** — if a setting was changed 3+ times, or changed back and forth, or was the subject of disagreement, flag it explicitly. These are the settings that are likely to come up in meetings because they represent unresolved tension (e.g., rate limits being bumped up repeatedly suggests they still aren't right).

3. **Flag settings correlated with incidents** — if a config change was made during or immediately after an incident, note the correlation. This helps the SE understand which settings are reactive (changed to fix problems) vs. proactive (changed to improve performance).

4. **Present in the Configuration & Settings section** — the current-state table should show the most recent confirmed value with a note like "changed 5 times since Feb 2025 — see drift history below." Below the current-state table, include a "Configuration History" subsection for settings with notable drift.

This analysis is valuable because it surfaces patterns that no single thread reveals — e.g., "rate limits have been adjusted 8 times in 6 months, always upward, suggesting the baseline is still wrong."

**Jira Health in Executive Summary:**

The Executive Summary must include a one-line assessment of Jira issue health. Calculate and state:
- Total open issues and staleness rate (e.g., "75% of 84 issues have no update in 30+ days")
- Number of P0/P1 issues in Triage (unassigned) — this signals dropped balls
- Any disconnect between Jira status and Slack reality (e.g., Jira says "Active" but last thread activity was 6 months ago)

This belongs in the exec summary because stale Jira is a leading indicator of account drift — if nobody is updating tickets, nobody is tracking progress.

**Priority Alignment (when customer priority list is provided):**

If the user provided a customer-maintained spreadsheet or priority list, cross-reference it with Jira:
- Items on the customer list with no matching Jira issue → flag as "not tracked in Jira"
- Items where customer priority disagrees with Jira priority (e.g., customer says #1, Jira says P2) → flag the gap
- Jira issues not on the customer list → may be resolved, deprioritised, or unknown to the customer
- Present as a "Priority Alignment" subsection within Issue Themes, or as a standalone section if discrepancies are significant

**Gaps, Inconsistencies, and Missing Context:**

Actively look for and flag:
- **Contradictions across sources** — thread A says one thing, thread B or Jira says another. Surface these prominently, don't silently pick one version.
- **Confusion or miscommunication** — cases where people talked past each other, assumptions were wrong, or actions were taken based on incorrect understanding. These are exactly the kind of things that recur in meetings.
- **Missing context** — if threads reference a meeting, a call, a decision made offline, or context that isn't in any of the sources, flag it. The reader needs to know what they *don't* have.
- **Meeting references** — if any thread mentions a meeting, call, or sync where decisions were made or context was shared, flag it and ask the user if they have a transcript or Granola notes for that meeting. Meeting context often fills the gaps between Slack threads. Add a section near the end of the pre-read:

```markdown
## Suggested Additional Context

The following meetings or calls were referenced in threads but no transcript was provided. If you have Granola notes or recordings, they may fill gaps in this pre-read:

| Referenced Meeting | Date (approx) | Mentioned In | What's Likely Missing |
|-------------------|----------------|--------------|----------------------|
| "sync with eng team about X" | ~15 Feb 2025 | [thread message](https://weightsandbiases.slack.com/archives/CXXX/pYYY) | Decision on fix approach |
| ... | ... | ... | ... |
```

The "Mentioned In" column must link to the **specific Slack message** that references the meeting — not the thread root, not a batch label like "Batch 1 Thread 6." Use the message URL captured by sub-agents. If the exact message URL isn't available, link to the thread root as a fallback.

If the user provides Granola notes or meeting transcripts (as manual context), incorporate them into the synthesis — they often contain the decisions that explain the actions seen in Slack.

**Other Principles:**
- Concise beats comprehensive. If it doesn't help in the meeting, cut it.
- Specific beats general. Dates, versions, settings, names — always.
- Chronological for timeline, thematic for everything else.
- Distinguish facts from impressions. "Customer seems frustrated" only if there's evidence (e.g., explicit statements, escalation patterns, response tone).
- **No unattributed superlatives or hyperbole.** Do not write "most demanding customer," "extreme workload," "massive scale," etc. unless you can cite a specific source (person, date, thread) that used those words or stated the facts that justify them. If Flamarion said "2x larger than largest dedicated cloud deployments" — quote that with attribution. If nobody said it, state the measurable facts (e.g., "~10,000 concurrent models per the 21st August deep-dive call") and let the reader draw their own conclusions. The pre-read is a factual briefing, not a narrative.
- **FE-UPDATE coverage is not relevant** unless the SE explicitly says it is. FE-UPDATE is a new convention rolling out from April 2026 — absence of FE-UPDATE comments on Jira issues is expected, not a gap.
- **No raw Slack channel IDs in the output.** Channel IDs like `C06NX624Q9G` are meaningless to readers. Always use channel names (e.g., `#wandb-g-research`). If the channel name is unknown, resolve it using the Slack skill's `channels.py` script or describe it by its role (e.g., "customer-facing channel," "internal SE channel"). This applies everywhere: header, timeline, source index, inline references.

## Output Format

Write the pre-read to `customers/{customer_name}/pre-reads/{YYYY-MM-DD}-pre-read.md`.

Create directories as needed:
```bash
mkdir -p customers/{customer_name}/pre-reads
```

### Document Structure

The order below is deliberate — it moves from "what do I need to know right now" to "supporting detail I can drill into." The top half (Executive Summary through Issue Themes) is what most readers will actually read. The bottom half (Timeline through Source Index) is reference material.

```markdown
# {Customer Name} — Pre-Read
**Generated:** {date}
**Sources:** {N} Slack threads ({channel names, not IDs — e.g., "#wandb-g-research, #internal-g-research"}), {N} Jira issues, {manual context: yes/no}
**Prepared for:** {meeting context if known}
**Briefing goal:** {goal text, if provided — omit this line if no goal was given}

---

## Executive Summary

3-5 sentences. The "read this if you read nothing else" section. Cover: overall account health, biggest open issue, most important thing to know for the meeting. All claims must be attributed — cite who said it and when.

If a briefing goal was provided, open by addressing it directly.

Must include a one-line Jira health assessment: total open issues, staleness rate, and number of unassigned P0/P1s. Example: "84 open Jira issues; 75% have no update in 30+ days. 2 P0 issues sit in Triage with no Eng owner."

---

## Actions Required

Group blocked items by owner type, not by Jira status. Each item: plain-language ask, owner name, what's blocking progress, date it matters by. Limit to 5-8 genuinely blocking items.

### Engineering — Ship by {deadline}
| Ask | Owner | Blocker | Jira |
|-----|-------|---------|------|

### Product — Confirm timelines
| Ask | Owner | Blocker | Jira |
|-----|-------|---------|------|

### Field Team
| Ask | Blocker |
|-----|---------|

### Customer
| Ask | Blocker |
|-----|---------|

If the pre-read covers a short time window (single incident), this section may have only 1-2 items — that's fine. If there's no renewal or deadline driving urgency, the date column can note "no hard deadline" and the section still serves as a task list.

---

## Key Signals

3-6 direct quotes that represent the strongest sentiment signals: frustration, churn risk, trust loss, or positive momentum. Each quote includes who said it, when, and one line of context for why it matters. Link to the specific Slack message (not the thread root) where the quote appears. When the time period is short, 1-2 quotes is fine.

> **"Quote here"**
> — Person (role), [date](https://weightsandbiases.slack.com/archives/CXXX/pYYY). Context: why this matters.

---

## Issue Themes

Group related issues by theme, not by Jira status. An SE thinks in themes: "the artifact upload problems," "the launch agent instability," "the SSO rollout."

Within each theme, use two clearly labeled subsections:

### {Theme 1: e.g., Artifact Upload Performance}
- **Status:** {resolved / active / stale}
- **Jira:** [WB-123](https://wandb.atlassian.net/browse/WB-123), [WB-456](https://wandb.atlassian.net/browse/WB-456)

**Technical Summary:** What broke, why, what was done, what remains. 2-4 sentences. An engineer or SA can scan just these halves across all themes.

**Account Impact:** Customer sentiment, commercial risk, quotes that signal escalation or churn risk. 2-4 sentences. An account manager or CS lead can scan just these halves.

When the pre-read covers a short window, some themes may only need one or the other — don't force both if there's nothing meaningful to say.

### {Theme 2}
...

---

## Jira Summary

Surface the Jira landscape prominently. This section answers: "How well are we tracking this customer's issues?"

**Health:** {N} open issues. {X}% have no update in 30+ days. {Y} P0/P1 issues in Triage (unassigned).

### P0/P1 Issues (all statuses)
| Key | Summary | Status | Assignee | Last Update | Stale? |
|-----|---------|--------|----------|-------------|--------|
| [WB-123](https://wandb.atlassian.net/browse/WB-123) | ... | Triage | Unassigned | 2025-01-15 | YES |
| ... | ... | ... | ... | ... | ... |

### Stale Issues (no activity 30+ days, any priority)
| Key | Summary | Priority | Status | Last Update |
|-----|---------|----------|--------|-------------|
| ... | ... | ... | ... | ... |

Note: full Jira list is in the Source Index appendix.

---

## Impact Summary

Quantify the cumulative effect of incidents and issues on this customer. This section answers: "How much pain has this customer actually experienced?"

| Incident | Date | Severity | Duration | Affected | Resolution |
|----------|------|----------|----------|----------|------------|
| SDK crash on large uploads | 15 Jan 2025 | Blocked workflow | ~4 hours | ML platform team | Workaround provided, fix in v0.18.3 |
| Launch agent pod failures | 3 Feb 2025 | Degraded | ~8 hours | All GPU training jobs | Config fix applied |
| ... | ... | ... | ... | ... | ... |

**Totals:** {N} incidents, ~{X} hours cumulative impact over {time period}

Severity categories (use the one that best fits — these aren't rigid):
- **Full outage**: Service completely unavailable, work stopped
- **Degraded**: Service running but impaired (slow, errors, partial functionality)
- **Blocked workflow**: Specific workflow broken, other work continues
- **Intermittent**: Sporadic failures, not continuous

If timing is uncertain, use ranges ("2-4 hours") and note the uncertainty. Better to approximate than omit — the meeting needs a sense of scale. If no incidents were found across all sources, omit this section entirely.

---

## Open Items

Things that are unresolved and may come up in the meeting.

| Item | Owner | Status | Last Update |
|------|-------|--------|-------------|
| SDK crash fix (WB-123) | SDK Team | In Review | 2025-03-01 |
| SSO configuration help | SE (you) | Pending customer response | 2025-02-28 |
| ... | ... | ... | ... |

---

## Timeline

Chronological list of key events. Not every message — just the inflection points. Link to the specific Slack message (not thread root) where the event was discussed.

| Date | Event | Source |
|------|-------|--------|
| 2025-01-15 | Customer reported SDK crash on artifact upload >5GB | [#wandb-acme](https://weightsandbiases.slack.com/archives/CXXX/pYYY) |
| 2025-01-17 | W&B eng confirmed bug in v0.18.2, fix targeting v0.18.3 | [eng thread](https://weightsandbiases.slack.com/archives/CXXX/pYYY) |
| ... | ... | ... |

---

## Key People

Who's involved on both sides. Knowing names before a meeting matters.

| Name | Role | Organization | Context |
|------|------|-------------|---------|
| Jane Smith | ML Platform Lead | Customer | Primary technical contact, drives most threads |
| Bob Chen | SDK Engineer | W&B | Assigned to WB-123, active in eng threads |
| ... | ... | ... | ... |

---

## W&B Configuration & Settings

What's enabled, what was changed, what's non-standard. This section is reference material — the reader comes here when they need to check a specific value, not to understand the account narrative.

### Current State

Show the most recently confirmed value for each setting. Flag settings with notable drift.

| Setting/Feature | Value (as of {date}) | Drift | Notes |
|----------------|---------------------|-------|-------|
| `GORILLA_LIMITER` | `redis://...` (as of 26th Aug 2025) | — | Was completely inactive before this date |
| `GRAPHQL` rate limit | `1500` (as of Feb 2026) | Changed 5x | Started at 200 (SaaS default). See drift history |
| ... | ... | ... | ... |

The "as of" date must be the date of the most recent source that explicitly confirms the value — not an inferred date.

### Configuration History (settings with notable drift)

For any setting changed 3+ times, or changed back and forth, or correlated with incidents:

**{Setting name}**
| Date | Value | Changed by | Reason | Source |
|------|-------|------------|--------|--------|
| 25th Apr 2025 | 200 (SaaS default) | W&B eng | First rate limit applied during outage | [message](url) |
| 1st Sep 2025 | 800 | Tim Hailwood | Post bare-metal migration bump | [message](url) |
| ... | ... | ... | ... | ... |

This section surfaces patterns invisible in any single thread — e.g., "rate limits adjusted 8 times in 6 months, always upward, suggesting the baseline is still wrong."

---

## Suggested Additional Context

(Meeting references — see Gaps, Inconsistencies, and Missing Context instructions above)

---

## Source Index

Compact appendix for traceability. Most readers won't need this — the inline links throughout the document point to specific messages. This exists so nothing is lost.

### Slack Threads
| # | Channel | Date | Topic | Link |
|---|---------|------|-------|------|
| 1 | #wandb-acme | 2025-01-15 | SDK crash report | [thread](url) |
| ... | ... | ... | ... | ... |

### Jira Issues (full list)
| Key | Summary | Status | Priority | Last Update |
|-----|---------|--------|----------|-------------|
| [WB-123](https://wandb.atlassian.net/browse/WB-123) | SDK crash on large artifact upload | In Review | P1 | 2025-03-01 |
| ... | ... | ... | ... | ... |
```

### Phase 4: Humanizer Review

After synthesis is complete, run the `/humanizer` skill against the generated pre-read document. This is a tone pass, not a content pass — the humanizer should not change facts, dates, attributions, or structure.

The humanizer catches patterns that undermine a factual briefing:
- Inflated language ("significant," "notably," "importantly")
- AI-typical phrasing ("It's worth noting that," "This highlights the fact that")
- Em dash overuse, rule of three, excessive conjunctive phrases
- Promotional or narrative tone where the document should be stating facts

The humanizer reviews the full document and applies fixes inline. After the humanizer pass, do a quick scan to confirm no factual content was altered — the humanizer works on tone, not substance, but verify.

## Execution Notes

### Parallelization Strategy

- **Phase 1 + Phase 2 run in parallel** — thread fetching and Jira pull are independent
- **Within Phase 1**, spawn up to 5 thread-fetch agents at a time. If there are more than 5 threads, batch them in waves of 5.
- **Phase 1b** (discovered threads) runs after Phase 1 completes, also in waves of 5
- **Phase 3** (synthesis) runs after everything else is done
- **Phase 4** (humanizer) runs after synthesis, before presenting to the user

### Context Window Management

Each thread-fetch sub-agent operates independently and returns only the summary, not the raw thread JSON. This keeps the synthesis agent's context focused on summaries rather than raw Slack data. For a typical pre-read with 15-20 threads + Jira data, the synthesis input should be well within context limits.

### Error Handling

- If a thread fetch fails (channel not found, auth error), log it and continue with remaining threads
- If Jira pull fails, proceed with Slack data only and note the gap in the document
- If fewer than 3 threads are fetched, warn the user that the pre-read may be thin

### User Interaction

- After gathering inputs, show the user a summary of what will be fetched before starting: "{N} threads from {channels}, Jira issues for {customer}, briefing goal: {yes/no}, manual context: {yes/no}"
- After synthesis + humanizer pass, present the pre-read and ask if anything is missing or needs adjustment
- If the user provides feedback, re-run the synthesis (and humanizer) with their notes incorporated

## Limitations

- Thread fetch limit is 200 replies per thread. Very long threads may be truncated.
- Slack search API may not find all relevant threads in a channel — if the user knows specific threads exist, pasting URLs is more reliable.
- Discovered thread following is depth-limited to 2 hops. If thread A links to B which links to C, we fetch all three. But if C links to D, we stop there.
- Private channels require membership — threads from channels you can't access will fail silently.
