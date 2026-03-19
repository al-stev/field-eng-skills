# Skill Composition Workflows

Named multi-skill workflows for common W&B SE operations. Each workflow lists skills in recommended order. Steps can be skipped or reordered based on context — these are starting patterns, not rigid scripts.

## Issue Triage

Investigate a customer-reported issue from initial report through resolution tracking.

1. **slack** — Search channel history for the complaint or thread context. Read the full thread if referenced.
2. **jira** — Search for related issues in the WB project by customer name or keyword. Check for existing bugs or feature requests.
3. **slack** — Post findings in the customer's channel (internal or external). Reply in the original thread.
4. **jira** — Create or update a Bug/Feature Request with FE-UPDATE comment to track the issue.

## Customer Lookup

Build a picture of a customer's issue landscape and current engagement state.

1. **jira** — Search WB project issues by customer name (`"Customer" = "CustomerName"`). List open bugs and feature requests to understand current workstreams.
2. **slack** — Search `#ext-*` and `#supp-*` channels for recent customer activity. Look for unresolved threads.
3. **confluence** — Check for existing customer documentation or knowledge base articles.

## Customer Snapshot

Generate an intelligence dashboard summarizing a customer's Jira issues, Slack sentiment, trending metrics, and executive summary.

1. **jira** — Pull all open issues for the customer. Include components, labels, priority, and status.
2. **customer-snapshot** — Generate HTML dashboard with intelligence panels, theme clustering, and filter controls.
3. Output saved to `customers/<name>/trackers/YYYY-MM-DD-dashboard.html`.

## Communication Prep

Prepare for a customer meeting or email update by gathering current context.

1. **slack** — Read recent messages in the customer's `#ext-*` and `#supp-*` channels. Look for unresolved threads or new issues since the last meeting.
2. **jira** — Check the customer's open issues for status updates to report. Note any blocked or overdue items. Review recent FE-UPDATE comments.
3. **confluence** — Check for relevant documentation or meeting notes.

## FE-UPDATE Workflow

The "pull view, notice stale, trigger update" pattern for keeping Jira issues current.

1. **jira** — Pull customer issues, identify those with stale or missing FE-UPDATE comments.
2. **slack** — Follow linked Slack thread URLs from Jira issues. Summarize new activity since last update.
3. **jira** — Post FE-UPDATE formatted comments with source citations and updated status/dates.
