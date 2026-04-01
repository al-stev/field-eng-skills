---
name: customer-snapshot
description: "Generate interactive intelligence dashboards showing a customer's Jira issues, Slack sentiment, trending metrics, and executive summaries. Use this skill whenever the user mentions customer snapshot, customer trackers, customer dashboards, customer issue summaries, preparing for a customer call, QBR prep, tracking customer bugs/feature requests, or wants to visualize Jira issues for a specific customer. Also trigger when the user references /customer-snapshot, asks to 'build a snapshot' or 'build a tracker' for any customer name, or says anything about reviewing a customer's open tickets before a meeting."
argument-hint: "<customer-name> (required)"
---

# Customer Snapshot

Generate professional, interactive intelligence dashboards from W&B Jira data and Slack channel history for customer call prep. The output is a folder-based dashboard with modular panels, ECharts visualizations, pill filters, collapsible theme sections, sentiment analysis, trending metrics, executive summary, internal/external audience toggle, and light/dark mode support.

The dashboard is designed for a Solutions Engineer preparing for customer calls -- professional enough to screen-share or send to colleagues. The internal/external toggle allows hiding candid analysis when screen-sharing.

## Pipeline

### Step 1: Parse customer name

Extract the customer name from the user's input. Common patterns:
- "/customer-tracker GResearch" -> "GResearch"
- "build a tracker for Acme Corp" -> "Acme Corp"
- "customer dashboard for G-Research" -> "G-Research"

### Step 2: Load customer registry

Read `templates/customers.yaml` (project root, NOT inside skill directory) to look up customer configuration:

```bash
# Read the file using Claude's Read tool
# Path: templates/customers.yaml
```

- Find matching customer by `name` field (case-insensitive, ignore hyphens/spaces)
- If found: extract `slack_channels` for Step 4, `jira_customer` for Step 3
- If not found: proceed with Jira-only mode, sentiment will show "Not configured"
- If `slack_channels[].id` is "PLACEHOLDER": warn and skip Slack fetch
- Optional: if customer has `component_normalize` map, use it to override built-in normalization

### Step 3: Fetch Jira data

Use the Jira skill to pull all issues for the customer with comment metadata:

```bash
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py list \
  --customer "<CustomerName>" --max-results 200 --with-comments
```

The `--with-comments` flag includes per-issue comment analysis: comment count, last comment date/author, last eng comment date/author (excluding FE-UPDATE), first comment date, and FE-UPDATE count. This data powers the dashboard's analysis section (staleness, velocity, response cadence). The response also includes `resolutiondate` for accurate time-to-resolution metrics.

Parse the JSON output. If no issues are returned, generate a dashboard with an empty state message rather than failing.

### Step 3.5: Fetch Asana tasks

If the customer has `action_tracker_id` in customers.yaml (and it is not "PLACEHOLDER", and `action_tracker` is `"asana"`):

1. Determine current user GID:
   ```bash
   uv run --project .claude/skills/asana python .claude/skills/asana/scripts/query.py project --gid <action_tracker_id> --pretty
   ```
   (The user GID comes from the PAT owner, resolved during task filtering)

2. Fetch all incomplete tasks in the customer's Asana project:
   ```bash
   uv run --project .claude/skills/asana python .claude/skills/asana/scripts/query.py tasks \
     --project-gid <action_tracker_id> --limit 100 --pretty
   ```

3. Filter to incomplete tasks only (completed=false or null)
4. For each task, compute:
   - `overdue`: true if due_on is before today and task is not completed
   - `stale`: true if (today - modified_at) > 7 days AND section is "To Do" or "In Progress"
   - `stale_days`: days since modified_at
   - `priority`: from custom_fields Priority enum, or parsed from name prefix `[P0]`/`[P1]`/`[P2]`/`[P3]`, or null
   - `linked_jira`: extracted from task name using regex `\(WB-\d+\)`, or from notes field
   - `section`: from memberships[0].section.name
5. Default scope: filter to tasks where assignee matches current user ("my tasks")
6. Build the `actions` object for INTELLIGENCE_DATA (see schema in Step 7)

If `action_tracker_id` is missing or "PLACEHOLDER": set `actions: { available: false, reason: "not_configured" }` and proceed.
If Asana API fails: set `actions: { available: false, reason: "api_error" }` and proceed gracefully.

### Step 3.7: Fetch BigQuery usage data

If the customer has `sfdc_account_id` in customers.yaml (and it is not "PLACEHOLDER"):

```bash
uv run --project .claude/skills/bigquery python .claude/skills/bigquery/scripts/usage.py \
  --customer "<CustomerName>" --format json
```

Parse the JSON output. The output matches the `INTELLIGENCE_DATA.usage` schema (see Step 7).

The usage data powers ECharts time-series and radar charts in the dashboard's Usage panel
(replacing the previous CSS horizontal bars). ECharts is loaded from CDN and themed to
match the design system. The dashboard coexists: Jira/Slack panels use CSS bars, Usage
panel uses ECharts.

If `available: false`: set `usage: { available: false, reason: "<from output>" }` and proceed.
If `sfdc_account_id` is missing or "PLACEHOLDER": set `usage: { available: false, reason: "not_configured" }` and proceed.
If BigQuery skill fails: set `usage: { available: false, reason: "api_error" }` and proceed gracefully.

### Step 4: Fetch Slack channel history

For each channel in `slack_channels` where `id` is not "PLACEHOLDER":

```bash
OLDEST=$(python3 -c "import time; print(time.time() - DAYS*86400)")
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/channels.py history \
  --channel <CHANNEL_ID> --limit 200 --oldest $OLDEST
```

Default DAYS = 14 (configurable via --days flag on skill invocation).
Fetch sequentially, not in parallel (rate limit safety).
If Slack API fails or no channels configured: set sentiment to null, proceed gracefully.

### Step 5: Analyze sentiment

Claude reads the fetched Slack messages and produces a structured sentiment object:

1. Read messages chronologically
2. Score overall channel tone using 5-point categorical scale:
   - positive (happy, grateful, optimistic)
   - neutral (routine communication)
   - cautiously-negative (hints of frustration)
   - negative (clear complaints)
   - critical (anger, threats to leave, executive escalation)
3. Assign supplementary numeric score (-1.0 to 1.0)
4. Identify hot threads: threads where 3+ messages have negative tone, OR executive expressing frustration, OR mentions of evaluating alternatives
5. For each hot thread, fetch full replies via `threads.py replies`
6. Produce the sentiment JSON matching INTELLIGENCE_DATA.sentiment schema (see below)
7. For internal section: note risk signals and recommended actions

Output a JSON object -- do not display to user, inject into INTELLIGENCE_DATA.

### Step 6: Cluster issues by theme + compute trending metrics

Group issues into product-area themes using Jira field data:
1. Use the issue's first **component** if available (apply COMPONENT_NORMALIZE map)
2. Otherwise, use the **parent epic summary** if available (apply PARENT_NORMALIZE map)
3. Otherwise, assign to **"Uncategorized"**

Labels are skipped entirely -- W&B Jira labels are meta/triage labels (fe-reported, vis-triage), not product areas.

**Normalization maps**: The template includes `COMPONENT_NORMALIZE` and `PARENT_NORMALIZE` JavaScript objects that merge variant names into canonical themes (e.g. "Weave Python SDK" and "weave" both map to "Weave"). These maps are customer/project-specific and should be updated when generating dashboards for new customers. If the customer registry has a `component_normalize` map, use it to override or extend the built-in maps.

Additionally compute trending metrics:
- Compute opened/closed by month for last 6 months
- Compute raised-to-resolved ratio
- Compute median time-to-resolution using `resolutiondate` (fall back to `updated` if null)
- Compute top 5 theme recurrence

Aim for 5-10 themes. Theme names should be short, recognizable product areas. Some Uncategorized issues are expected -- the analysis section flags this as a metric.

### Step 7: Assemble INTELLIGENCE_DATA

Save each data source output from prior steps to temporary JSON files, then run assemble.py:

```bash
uv run --project .claude/skills/customer-snapshot python \
    .claude/skills/customer-snapshot/templates/assemble.py \
    --customer "<CustomerName>" \
    --jira /tmp/snapshot-jira.json \
    --bq /tmp/snapshot-bq.json \
    --asana /tmp/snapshot-asana.json \
    --sentiment /tmp/snapshot-sentiment.json \
    --days 14 --months 6 --audience internal \
    --output /tmp/customer-snapshot-data.json
```

Omit any --flag for data sources that were not fetched (e.g., skip --bq if BigQuery
was unavailable). assemble.py handles missing sources gracefully.

The script applies component/parent normalization, assigns themes, computes trending
metrics, and transforms Asana tasks. Output is the complete INTELLIGENCE_DATA JSON
ready for compose.py in Step 8.

#### Schema Reference

```javascript
const INTELLIGENCE_DATA = {
  customer: "G-Research",
  generated: "2026-03-17",
  config: {
    sentiment_days: 14,       // --days flag, default 14
    trending_months: 6,        // 6-month lookback
    audience: "internal"       // default view mode
  },
  issues: [
    {
      key: "WB-1234",
      summary: "SDK crash on large artifact upload",
      type: "Bug",           // "Bug" or "Feature Request"
      priority: "P1",        // "P0", "P1", "P2", "P3"
      status: "In Progress", // Raw Jira status value
      assignee: "Jane Doe",  // or null if unassigned
      theme: "SDK & Client Libraries",
      created: "2026-01-15",
      updated: "2026-03-08",
      resolutiondate: null,  // or ISO date string for resolved issues
      url: "https://wandb.atlassian.net/browse/WB-1234",
      components: ["Weave Python SDK"],
      parent: "WB-900",
      parent_summary: "Weave SDK Improvements",
      comments: {
        comment_count: 5,
        last_comment_date: "2026-03-01T10:30:00.000+0000",
        last_comment_author: "Jane Doe",
        last_eng_comment_date: "2026-02-28T14:00:00.000+0000",
        last_eng_comment_author: "John Smith",
        first_comment_date: "2026-01-16T09:00:00.000+0000",
        fe_update_count: 2
      }
    }
  ],

  // Sentiment (populated by Step 5, null when Slack unavailable)
  sentiment: {
    available: true,
    channels_analyzed: ["#ext-gresearch"],
    period: { start: "2026-03-03", end: "2026-03-17" },
    overall: {
      score: "cautiously-negative",  // positive | neutral | cautiously-negative | negative | critical
      numeric: -0.3,                 // -1.0 to 1.0
      summary: "Tone shifted negative this week, driven by frustration with SDK stability."
    },
    hot_threads: [
      {
        channel: "#ext-gresearch",
        thread_ts: "1710500000.000000",
        summary: "Frustration about repeated SDK crashes blocking production training",
        sentiment: "negative",
        message_count: 12,
        participants: 4,
        url: "https://coreweave.slack.com/archives/C0XXX/p1710500000000000"
      }
    ],
    internal: {
      raw_analysis: "Detailed sentiment breakdown...",
      risk_signals: ["Repeated mentions of evaluating alternatives"],
      recommended_actions: ["Escalate SDK stability to P0"]
    }
  },

  // Trending (computed client-side from issues data in JS)
  trending: null,

  // Executive summary (computed client-side from issues + sentiment in JS)
  exec_summary: null,

  // SE Actions from Asana (populated by Step 3.5, null/unavailable when Asana not configured)
  actions: {
    available: true,           // false when Asana not configured or fetch failed
    source: "asana",
    current_user: { gid: "12345", name: "Allan Stevenson" },
    scope: "my_tasks",         // or "team"
    project_gid: "98765",
    project_url: "https://app.asana.com/0/98765",
    tasks: [
      {
        gid: "11111",
        name: "Follow up on SDK crash (WB-1234)",
        section: "In Progress",
        due_on: "2026-03-28",
        overdue: false,          // computed: due_on < today
        stale: false,            // computed: 7+ days since modified_at AND section in [To Do, In Progress]
        stale_days: 2,
        priority: "P1",          // from custom field or parsed from name prefix [P1]
        assignee: { gid: "12345", name: "Allan Stevenson" },
        linked_jira: "WB-1234", // extracted from name via regex \(WB-\d+\)
        slack_source: "https://coreweave.slack.com/archives/...",
        url: "https://app.asana.com/0/0/11111",
        modified_at: "2026-03-21T10:00:00Z"
      }
    ],
    summary: {
      total: 8,
      in_progress: 3,
      waiting: 2,
      todo: 2,
      overdue: 1,
      stale: 1
    }
  },

  // Usage data from BigQuery (populated by Step 3.7, null/unavailable when BQ not configured)
  usage: {
    available: true,           // false when BigQuery not configured or fetch failed
    period: { start: "2025-03-24", end: "2026-03-24" },
    seat_utilization: {
      contracted: 50, claimed: 42, active: 35,
      utilization_percent: 70.0,
      history: [{ week: "2025-04-07", contracted: 50, active: 28 }]
    },
    weave: {
      ingestion_gb: 156.3, limit_gb: 500.0, utilization_percent: 31.3,
      unique_users_last_90d: 12,
      history: [{ month: "2025-04", ingestion_gb: 8.2, unique_users: 5 }]
    },
    tracked_hours: {
      last_30d_hours: 1250.0, last_30d_run_count: 342,
      history: [{ week: "2025-04-07", tracked_hours: 180.5 }]
    },
    account_health: {  // internal-only
      renewal_date: "2026-09-15", arr: 250000.0, cs_tier: "Strategic",
      customer_health: "Green", churn_probability_3mo: 0.05,
      churn_probability_5mo: 0.08, subscription_plan: "Enterprise",
      deployment_type: "dedicated-cloud"
    },
    trends: {
      seat_utilization_change: 12.5, weave_ingestion_change: -3.2,
      tracked_hours_change: 8.7, run_count_change: 15.3
    },
    product_areas: [  // NEW - from Plan 01 expansion, powers radar chart
      { area: "Experiments", total_events: 1800, unique_users: 25,
        monthly_events: [{month: "2025-04", count: 150, users: 12}] }
    ],
    power_users: [  // NEW - anonymized by default, real names with --internal
      { username: "alice_ml", total_events: 5000, product_areas: ["Experiments"],
        last_activity: "2026-03-20" }
    ]
  }
};
```

The `comments` object is present when data is fetched with `--with-comments`. The template uses it for:
- **Health buckets**: Activity-based classification (Needs Triage / Active / Stale / Resolved)
- **Attention callouts**: Never commented, no eng activity 60+ days, unassigned, recently opened
- **Response cadence**: Median days to first comment, % within 7 days, zero-comment count
- **FE-UPDATE badges**: Gold "SE:N" badge in the Last Activity column

FE-UPDATE comments are excluded from eng activity calculations -- SE posting an update doesn't reset the staleness clock.

Note: trending and exec_summary are computed client-side in the template JS, not server-side. The data they need (issues with dates, sentiment object) is already in INTELLIGENCE_DATA.

For priority mapping: use P0/P1/P2/P3 directly from Jira. If priority uses names like "Critical"/"High"/"Medium"/"Low", map to P0/P1/P2/P3 respectively.

### Step 8: Generate the v2 intelligence dashboard

1. Write the INTELLIGENCE_DATA object to a temporary JSON file:
   ```bash
   # Write the full INTELLIGENCE_DATA dict as JSON to a temp file
   # e.g., /tmp/customer-snapshot-data.json
   ```

2. Call compose.py to generate the v2 folder-based dashboard:
   ```bash
   uv run --project .claude/skills/customer-snapshot python \
       .claude/skills/customer-snapshot/templates/compose.py \
       --customer "<CustomerName>" \
       --data /tmp/customer-snapshot-data.json \
       --output customers/<kebab-case-name>/dashboard/
   ```

3. The output directory will contain:
   - `index.html` -- shell with sidebar navigation
   - `data.js` -- INTELLIGENCE_DATA with all panel data
   - `panels/` -- individual panel JS files (only panels with data)
   - `lib/` -- echarts.min.js, chart-helpers.js, panel-registry.js
   - `history/` -- previous data.js snapshots for diff computation

4. Open the dashboard: `open customers/<kebab-case-name>/dashboard/index.html`

The v1 monolithic template (`templates/intelligence-dashboard.html`) remains as a fallback reference but is no longer the default output path.

### Step 9: Present to the user

Tell the user:
- Dashboard folder path (e.g., `customers/<name>/dashboard/`)
- Brief summary: total issues, sentiment score (or "not configured"), backlog trajectory
- Usage stats if available (seat utilization %, Weave ingestion %, trend direction)
- Asana action counts if available (e.g., "8 open actions, 1 overdue")
- Hot issues or threads needing attention
- Flag any P0/P1 stale issues

## Design Rules

Read `references/design-system.md` for the complete visual specification. Key principles:

- Custom HTML/CSS horizontal bars for Jira/Slack panels -- no external charting libraries for those
- Instrument Serif + Outfit + JetBrains Mono typography
- Gold accent (#d4a853), warm cream light mode (#f6f4f0), deep navy dark mode (#0c0f14)
- Inline header stats, not KPI cards
- Pill toggle filters with "All" default
- Collapsible theme sections with priority mini-badges
- Resolved issues hidden by default with toggle to show
- Both light and dark mode via prefers-color-scheme
- Internal/External audience toggle in header area

## Visualization

- All chart panels use Apache ECharts v5 via the modular panel architecture (usage, support, overview)
- ECharts loaded from locally bundled `lib/echarts.min.js` (not CDN) for offline reliability
- Custom 'wandb' theme registered via `lib/chart-helpers.js` matching design system colors (dark/light mode aware)
- Jira/Slack panels: Custom CSS bars (unchanged from Phase 3/6)
- Each data section has a SQL copy icon button for BQ query provenance (copies query to clipboard with toast notification)

## Status Mapping

The template maps Jira statuses to display categories for filter pills and issue badges:

| Category | Jira Statuses | Colour |
|----------|--------------|--------|
| Resolved | Done, Closed, Resolved, Merged | Green |
| Active | In Progress, In Review, In Development, Selected for Development | Blue |
| Waiting | Open, Backlog, To Do, Waiting, Future | Amber |
| Triage | Triage, Won't Fix, Archived | Gray |

## Health Buckets (Analysis Section)

The analysis section uses activity-based health classification layered on top of raw statuses:

| Bucket | Logic | Colour |
|--------|-------|--------|
| Needs Triage | Open/Backlog/To Do/Triage with no eng comments | Red |
| Active | Non-resolved with eng comment in last STALE_DAYS (30) | Blue |
| Stale | Non-resolved with no eng comment in STALE_DAYS+ | Amber |
| Resolved | Done/Closed/Resolved/Merged | Green |

FE-UPDATE comments are excluded from eng activity -- only non-FE-UPDATE comments count. This prevents SE updates from gaming the staleness metric.

## Analysis Section

The dashboard's primary value is the analysis section above the issue list:

1. **Health summary**: Horizontal bar showing bucket distribution (Needs Triage / Active / Stale / Resolved)
2. **Attention callouts**: Clickable cards that filter the issue list:
   - Never Commented (zero comments)
   - No Eng Activity 60+ days (VERY_STALE_DAYS)
   - Unassigned (no assignee)
   - Recently Opened (last 14 days)
3. **Velocity chart**: Opened vs resolved by month (last 6 months), custom CSS bars
4. **Response cadence**: Median days to first comment, % responded within 7 days, zero-comment count

Callouts are interactive -- clicking one filters the issue list, auto-expands matching themes, and scrolls to the issue section.

## Anti-Patterns

When generating or modifying dashboards, never introduce these patterns:
- KPI cards (big number + small label in identical card grid)
- Gradient text, glassmorphism, neon accents
- Inter/Roboto/Arial fonts
- Copying from the prototype at `.claude/skills/customer-tracker/` in older commits
- LLM-based theme clustering (use Jira components/labels only)
- Generating v1 monolithic intelligence-dashboard.html (use compose.py for v2)
- Loading ECharts from CDN in v2 dashboards (use locally bundled lib/echarts.min.js)

## Future View Types

The skill is structured for multiple view modes of the same data. The Intelligence Dashboard is the primary view:

1. **Intelligence Dashboard** (current) -- filterable dashboard with theme groupings, sentiment, trending, exec summary
2. **Timeline** (planned) -- issues plotted against target dates
3. **Slide Deck** (planned) -- presentation mode for QBRs
4. **Confluence Page** (planned) -- XHTML for publishing

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No issues returned | Check customer name spelling; try variants (GResearch vs G-Research) |
| Too few themes | Customer may have issues without components/labels; "Uncategorized" is fine |
| Too many themes | Consider if the Jira project uses granular labels; the dashboard handles 10+ themes well |
| Missing fields | Template handles null assignees and missing dates gracefully |
| Sentiment shows "Not configured" | Customer not in `templates/customers.yaml` or channels have PLACEHOLDER IDs |
| Sentiment shows "Unavailable" | Slack API failed or returned no messages; dashboard still works without it |
| Empty trending charts | Customer has very few issues or all issues are very old (outside 6-month window) |
