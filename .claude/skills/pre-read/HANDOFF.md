# Pre-Read Skill — Handoff for Execution

## What Was Built

A new skill at `.claude/skills/pre-read/SKILL.md` that generates structured pre-read documents for customer meetings by orchestrating parallel Slack thread fetching, Jira issue pulling, and manual context synthesis.

## How to Use It

The user will provide:
1. **Customer name** (required)
2. **Slack thread URLs** — paste them directly, the skill parses `channel_id` + `thread_ts` from the URL format `https://coreweave.slack.com/archives/CXXXXXX/p1234567890123456`
3. **Optionally**: channel names + date range for broader search, manual context (pasted or file path), Granola meeting notes

## Execution Pipeline

1. **Phase 1**: Spawn parallel sub-agents (waves of 5) to fetch + summarize each Slack thread via `uv run --project .claude/skills/slack python .claude/skills/slack/scripts/threads.py replies --channel CHANNEL_ID --ts THREAD_TS --limit 200`
2. **Phase 1b**: Follow any Slack thread URLs discovered within threads (depth 1)
3. **Phase 1c**: Follow any URLs discovered in depth-1 threads (depth 2, max)
4. **Phase 2** (parallel with Phase 1): Pull Jira issues via `uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py list --customer CUSTOMER_NAME --with-comments --pretty`
5. **Phase 3**: Synthesize all summaries + Jira + manual context into the pre-read markdown

## URL Parsing

Slack URLs look like: `https://coreweave.slack.com/archives/C0ABC1234/p1709123456789012`
- Channel ID: `C0ABC1234` (segment after `/archives/`)
- Thread TS: drop `p`, insert `.` before last 6 digits → `1709123456.789012`

## Output

Markdown file at `customers/{customer_name}/pre-reads/{YYYY-MM-DD}-pre-read.md`

Sections: Executive Summary, Impact Summary, Timeline, W&B Configuration & Settings, Issue Themes, Open Items, Key People, Suggested Additional Context, Source Index.

## Key Design Decisions

- **Channel naming**: W&B customer channels typically include "wandb" in the name, internal channels include "internal". Engineering channels vary — don't assume a pattern, infer from context.
- **Temporal weighting**: Recent events (30-60 days) get the most detail; older events provide supporting context for themes. Timeline density is logarithmic toward the present.
- **Cross-thread correlation**: Multiple threads about the same issue get merged into a single theme. Correlation via shared Jira keys, participants, temporal proximity, and explicit cross-references.
- **Impact quantification**: Incidents tracked with duration, severity (full outage / degraded / blocked workflow / intermittent), cumulative totals.
- **Date format**: Unambiguous format (e.g., "4th March 2025") to avoid US/International confusion.
- **Gaps and contradictions**: Actively flagged. Missing meeting context prompts a request for Granola notes/transcripts.
- **Attribution**: All actions attributed to specific people with dates.

## Prerequisites

- Slack credentials configured (`~/.fe-skills/.env` — SLACK_TOKEN, SLACK_COOKIE)
- Jira credentials configured (`~/.fe-skills/.env` — ATLASSIAN_EMAIL, ATLASSIAN_TOKEN)
- Read the full skill at `.claude/skills/pre-read/SKILL.md` before executing
