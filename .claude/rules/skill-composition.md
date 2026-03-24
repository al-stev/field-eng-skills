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

0. **salesforce** — Query SFDC for account-level data (ARR, tier, contract dates, account team). Use `accounts.py account-detail --account-id <ID>` for full account context before diving into issues and channels.
1. **jira** — Search WB project issues by customer name (`"Customer" = "CustomerName"`). List open bugs and feature requests to understand current workstreams.
2. **slack** — Search `#ext-*` and `#supp-*` channels for recent customer activity. Look for unresolved threads.
3. **confluence** — Check for existing customer documentation or knowledge base articles.

## Customer Snapshot

Generate an intelligence dashboard summarizing a customer's Jira issues, Slack sentiment, Asana actions, trending metrics, and executive summary.

1. **jira** — Pull all open issues for the customer. Include components, labels, priority, and status.
2. **asana** — Fetch SE action tasks from the customer's Asana project (if configured).
3. **bigquery** — Fetch usage data from BigQuery if sfdc_account_id is configured. Provides seat utilization, Weave ingestion, tracked hours, account health, product areas. Renders as ECharts charts in the Usage panel.
4. **customer-snapshot** — Generate HTML dashboard with intelligence panels, SE actions, theme clustering, and filter controls.
5. Output saved to `customers/<name>/trackers/YYYY-MM-DD-dashboard.html`.

## Communication Prep

Prepare for a customer meeting or email update by gathering current context.

1. **slack** — Read recent messages in the customer's `#ext-*` and `#supp-*` channels. Look for unresolved threads or new issues since the last meeting.
2. **jira** — Check the customer's open issues for status updates to report. Note any blocked or overdue items. Review recent FE-UPDATE comments.
3. **confluence** — Check for relevant documentation or meeting notes.
4. **bigquery** — Optionally pull usage stats for data-driven talking points (seat adoption trends, Weave ingestion).
5. **gcalendar** — Check upcoming calendar events for the customer (meeting times, attendees, recurrence).
6. **gmail** — Search for recent email threads with the customer for additional context.
7. **gong** — Review recent call recordings and AI summaries for conversation continuity.

## FE-UPDATE Workflow

The "pull view, notice stale, trigger update" pattern for keeping Jira issues current.

1. **jira** — Pull customer issues, identify those with stale or missing FE-UPDATE comments.
2. **slack** — Follow linked Slack thread URLs from Jira issues. Summarize new activity since last update.
3. **jira** — Post FE-UPDATE formatted comments with source citations and updated status/dates.

## Action Tracking

Manage SE actions for a customer -- create tasks from Slack conversations, track progress, update status.

1. **slack** — Read the Slack thread or conversation that needs action tracking.
2. **jira** — Check if there's a related Jira issue (search by keywords or issue key mentioned in thread).
3. **asana** — Create a task in the customer's Asana project with:
   - Description populated from Slack thread context
   - Linked Jira issue key in task name suffix (WB-XXXX)
   - Slack source URL in description
   - Priority and due date based on urgency
4. **asana** — Update task status as work progresses (move between sections).

## Programme Update

Generate a 3P (Progress, Plans, Problems) update for a customer or across all customers.

1. **3p-update** — Run the 3P generation skill which automatically:
   - Fetches Asana tasks (progress/plans)
   - Fetches Jira activity (progress/problems)
   - Fetches Slack signals (problems)
   - Synthesizes a concise 3P update
2. Optional: add `--confluence` flag to publish as a Confluence page.

## RAID Management

Manage RAID logs (Risks, Assumptions, Issues, Dependencies) across customer accounts. RAID is the management-visibility layer that sits above day-to-day SE actions.

1. **raid** — View current RAID log for a customer, scan for new items, or manually add items.
2. **asana** — Base operations: create/update/move/complete RAID tasks, multi-home between customer and RAID projects.
3. **jira** — Scan mode data source: open issues, stale items, FE-UPDATE status for Issue and Dependency detection.
4. **slack** — Scan mode data source: customer channel sentiment for Risk detection.

## Usage Report

Generate a standalone usage visualization for a customer from BigQuery data. Two report types available.

1. **bigquery** — Fetch all usage metrics (seats, Weave, tracked hours, account health, product areas, power users) for the customer.
2. **usage-report** — Generate self-contained HTML usage report with ECharts charts.
   - Default: external report (customer-facing, QBR-ready, W&B branded, positive AI narrative)
   - With `--internal`: full SE prep report (power users with real names, churn risk, candid AI narrative)
3. Output saved to `customers/<name>/usage/YYYY-MM-DD-usage-report.html` (external) or `customers/<name>/usage/YYYY-MM-DD-usage-report-internal.html` (internal).

## Customer Onboarding

Set up a new customer's full Asana structure with portfolio, projects, and metadata.

1. **asana** — Run `setup-customer` to create customer portfolio + Actions project + RAID project + add to master portfolio + populate custom fields (SE Owner, Account Exec, Deployment Type, Customer Health).
2. **salesforce** — Look up SFDC account for ARR, contract dates, account team (if `/customer-setup` available).
3. **jira** — Verify the Jira customer name mapping. Search for issues using the customer name to confirm it matches.
4. **slack** — Look up Slack channel IDs for the customer's ext-* and supp-* channels.
5. Update `templates/customers.yaml` with the new GIDs (action_tracker_id, raid_tracker_id, portfolio_id) and customer metadata.

## Customer Silence Check

Monitor customer responsiveness on tracked threads.

1. **ghosted** — Scan "Waiting on Customer" tasks for unresponsive Slack threads (`/ghosted` or `/ghosted GResearch`).
2. **ghosted** — Track new threads: `/ghosted track <URL>` to start monitoring a thread.
3. **asana** — Move tasks back to active sections when customer responds.

## Meeting Follow-Up

Turn meeting notes into tracked actions and RAID items.

1. **maction** — Extract action items and RAID signals from meeting notes (`/maction GResearch <notes>`).
2. **asana** — Review and adjust created tasks (move sections, update priority, add details).
3. **raid** — Review RAID log after maction additions (`/raid GResearch`).

## Task Hygiene

Keep SE task backlog clean and current.

1. **nag** — Scan for overdue and stale tasks (`/nag`).
2. **asana** — Address flagged items: complete, reschedule, or move sections.
3. **ghosted** — Check customer silence on waiting items (`/ghosted`).
