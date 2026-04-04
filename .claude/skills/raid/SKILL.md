---
name: raid
description: "View, scan for, or add RAID (Risks, Assumptions, Issues, Dependencies) items for a customer. Manages Asana-native RAID logs that give management portfolio visibility across accounts."
argument-hint: "[view|scan|add] [customer-name]"
allowed-tools: Bash(uv run --project .claude/skills/asana python .claude/skills/asana/scripts/*.py *), Bash(uv run --project .claude/skills/jira python .claude/skills/jira/scripts/*.py *), Bash(uv run --project .claude/skills/slack python .claude/skills/slack/scripts/*.py *)
requires-credentials:
  - ASANA_TOKEN
  - ATLASSIAN_EMAIL
  - ATLASSIAN_TOKEN
  - SLACK_TOKEN
  - SLACK_COOKIE
setup-skill: asana-setup
service-url: https://app.asana.com
auto-refresh: false
---

# RAID Management Skill

Manage RAID logs (Risks, Assumptions, Issues, Dependencies) for customer accounts. RAID logs are the management-visibility layer that makes Asana useful for the whole team, not just the individual SE.

## Prerequisites

- **Asana** -- `ASANA_TOKEN` in `~/.fe-skills/.env` (run `/asana-setup` if not configured)
- **Jira** -- `ATLASSIAN_EMAIL` and `ATLASSIAN_TOKEN` in `~/.fe-skills/.env` (for scan mode)
- **Slack** -- `SLACK_TOKEN` and `SLACK_COOKIE` in `~/.fe-skills/.env` (for scan mode)
- **Customer registry** -- Customer must exist in `templates/customers.yaml` with `raid_tracker_id` set

Not all credentials are required for every mode. View mode needs only Asana. Scan mode needs all three.

Refer to `.claude/rules/asana.md` for shared constants (workspace GID, project GIDs, custom field definitions, section names).

## Two-Project Model

RAID depends on understanding Asana's two-project structure per customer. This is the most important concept for team adoption.

### Customer Actions Project (working view -- safe to share)

```
[Customer] Actions
  |-- To Do
  |-- In Progress
  |-- Waiting on Customer
  |-- Waiting on Eng
  |-- Scheduled/Future
  |-- Done
```

This is the day-to-day SE work tracker. Contains action items, follow-ups, and tasks the SE needs to do. Customers can see this project -- it shows statuses, due dates, and progress. Nothing sensitive lives here.

### RAID Portfolio Project (internal strategic view -- NEVER shown to customers)

```
[Customer] RAID Log
  |-- Risks            <- internal only, honest assessment of threats
  |-- Assumptions      <- internal only, things we're betting on
  |-- Issues           <- multi-homed from Jira/customer project
  |-- Dependencies     <- multi-homed from "Waiting on" sections
```

This is the internal risk register. Risks and Assumptions are honest, sometimes uncomfortable assessments that should never be visible to customers. Issues and Dependencies often originate as action items in the customer project and are multi-homed into RAID.

### Who Sees What

| Audience | What they see | Project |
|---|---|---|
| **Customer** | Actions with statuses, due dates, progress | Customer Actions |
| **SE** | Actions PLUS internal risk/assumption layer | Both projects |
| **Management** | Portfolio RAID view across all customers | All RAID projects |

### Multi-Homing

Action tasks live in the customer Actions project. Through multi-homing (Asana's native feature), relevant ones also appear in the RAID project under Issues or Dependencies. The task is the same object -- changes in one project are reflected in the other.

**When to multi-home:**
- A Jira bug is causing customer pain -> multi-home the tracking task into RAID Issues
- An action is blocked on eng/product -> multi-home into RAID Dependencies
- The task only exists as an internal concern -> create directly in RAID (no multi-homing)

```bash
# Multi-home an existing action task into the RAID project
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/mutate.py add-project \
  --task-gid TASK_GID --project-gid RAID_PROJECT_GID --section "Issues" --pretty
```

## RAID Categories

RAID = Risks, Assumptions, Issues, Dependencies. NOT Actions or Decisions.

| Category | What it tracks | Examples |
|---|---|---|
| **Risks** | Potential future problems that haven't materialized yet | Churn signals, champion leaving, competitive threat, declining usage, renewal risk, loss of executive sponsor |
| **Assumptions** | Things assumed true that could blow up if wrong | "Customer will renew at current ACV", "migration planned for Q3", "new team will adopt Weave", "budget approved for expansion" |
| **Issues** | Active current problems that need resolution | Product bugs blocking adoption, feature gaps vs competitor, training gaps, integration failures, SLA breaches |
| **Dependencies** | External factors blocking progress | Waiting on eng fix, product roadmap delivery, customer providing access/data, procurement approval, legal review |

**Anti-patterns:**
- Do NOT conflate Risks and Issues: Risks are *potential*, Issues are *actual*
- Do NOT include Actions in RAID -- actions live in the customer Actions project
- Do NOT use `[P0]` name prefixes -- use proper custom fields (Enterprise+ plan)

## Custom Fields

Six lean SE-specific fields, created at workspace level by `mutate.py setup-raid-project`. The existing workspace Priority field (High/Medium/Low) is also attached.

| Field | Type | Values | Notes |
|---|---|---|---|
| Category | enum | Risk / Assumption / Issue / Dependency | Determines which section the task lives in |
| Impact | enum | High / Medium / Low | Business impact if this materializes |
| Likelihood | enum | High / Medium / Low | Probability of occurrence |
| Status | enum | Open / Accepted / Closed | Three statuses only |
| Source | text | Free text | Where it came from (Slack thread URL, cadence call, QBR, etc.) |
| Visibility | enum | Internal / Shared | Internal = never show to customer; Shared = can reference in meetings |
| Priority | enum | High / Medium / Low | Existing workspace field (GID: 1208185034501267) |

**Status semantics:**
- **Open** -- actively needs attention or monitoring. Covers both "monitoring" and "mitigating" states; use the task description for nuance.
- **Accepted** -- acknowledged, no further action needed (e.g., accepted risk with mitigation in place, validated assumption).
- **Closed** -- resolved, no longer relevant.

## Three Modes

### View Mode (read-only)

**Invocation:** `/raid GResearch` or `/raid view GResearch`

Shows the current RAID log from Asana. Does NOT do a fresh scan -- that's a separate operation.

**Pipeline:**

1. Parse customer name, resolve from `templates/customers.yaml`
2. Look up the customer's RAID project GID from `raid_tracker_id` field (when `raid_tracker` is `"asana"`)
3. Fetch tasks from all 4 sections:
   ```bash
   uv run --project .claude/skills/asana python .claude/skills/asana/scripts/query.py tasks \
     --project-gid <raid_project_gid> --pretty
   ```
4. Group tasks by section (Risks, Assumptions, Issues, Dependencies)
5. For each item: show name, custom fields (Impact, Likelihood, Status, Priority), assignee, due date, source
6. Format as **Slack-ready text** output (plain text, copy-paste into Slack)
7. Also generate **styled HTML** using design-system.md conventions. Save to `customers/<name>/raid/YYYY-MM-DD-raid.html`
8. Show summary: counts per category, open/accepted/closed breakdown

**Slack-ready text format example:**
```
RAID Log: GResearch (2026-03-24)
================================

RISKS (2 open, 1 accepted)
  [High/High] Champion VP Eng may be leaving -- Source: cadence call Mar 20
  [Medium/Medium] Declining Weave adoption in ML team -- Source: usage data
  [Accepted] Competitive eval with Comet -- mitigated by exec relationship

ASSUMPTIONS (1 open)
  [Open] Customer will renew at current ACV ($180K) -- Source: QBR Jan 15

ISSUES (3 open)
  [High] SDK crash on large artifact uploads (WB-4521) -- 45 days open, no eng activity
  [Medium] Missing RBAC for team workspaces (WB-3892) -- waiting on product roadmap
  [Low] Documentation gaps for custom charts -- Source: supp-gresearch thread

DEPENDENCIES (2 open)
  [High] Blocked on eng fix for WB-4521 -- target: 15-APR-2026
  [Medium] Customer providing BigQuery access for usage integration -- due: 28-MAR-2026

Summary: 8 open, 1 accepted, 0 closed across 4 categories
```

**HTML output:**
- Single-page, self-contained HTML
- Design system: Instrument Serif headings, Outfit body, JetBrains Mono for labels/badges
- Colour: gold accent (`#b8922e`), warm cream/deep navy palette, dark/light mode
- Pill badges for Impact/Likelihood/Status with colour coding
- Category sections with item counts
- Save to: `customers/<name>/raid/YYYY-MM-DD-raid.html`

### Scan Mode (auto-suggest)

**Invocation:** `/raid scan GResearch`

Scans Jira issues and Slack channels for potential RAID items and suggests them. User confirms each before creation.

**Pipeline:**

1. Parse customer name, resolve from `templates/customers.yaml`
2. Gather Jira issues:
   ```bash
   uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py list \
     --customer "<jira_customer_name>" --with-comments --max-results 200
   ```
3. Gather Slack history from customer channels (7-day lookback):
   ```bash
   uv run --project .claude/skills/slack python .claude/skills/slack/scripts/channels.py history \
     --channel-id <channel_id> --limit 200 --pretty
   ```
4. Analyze for potential RAID items:

   **Risk signals:**
   - Overdue Asana tasks (query the Actions project)
   - Jira issues open 30+ days with no eng activity (excluding FE-UPDATE comments -- SE comments don't count as eng activity)
   - Negative sentiment in Slack (complaints, escalation language, frustration)
   - Declining usage signals mentioned in conversations

   **Assumption signals:**
   - Implicit assumptions in recent discussions ("customer expects X by Q3", "they're planning to...", "assuming budget is...")
   - Renewal or expansion assumptions not explicitly confirmed

   **Issue signals:**
   - New Jira bugs/escalations not yet tracked in RAID
   - P0/P1 Jira items (High priority)
   - Jira issues with recent customer activity but no eng response

   **Dependency signals:**
   - Jira issues in "Waiting" states (waiting-on-prod-eng FE-UPDATE status)
   - Asana tasks in "Waiting on Eng" or "Waiting on Customer" sections
   - Items dependent on product roadmap delivery

5. Present suggestions to user with rationale:
   ```
   Suggested RAID items for GResearch:

   1. [Risk] WB-4521 has been open 45 days with no eng activity
      -> Suggest: "SDK crash blocking large artifact uploads" in Risks (Impact: High, Likelihood: High)
      Add? [y/n]

   2. [Issue] WB-5102 new P1 bug filed 3 days ago, not in RAID
      -> Suggest: "RBAC permission error on team workspace creation" in Issues (Impact: Medium)
      Add? [y/n]

   3. [Dependency] WB-4521 has FE-UPDATE status: waiting-on-prod-eng
      -> Suggest: "Blocked on eng fix for SDK crash" in Dependencies (Impact: High)
      Add? [y/n]
   ```

6. User confirms each suggestion before creation

7. For confirmed items:
   - If the item is an existing Asana task from the customer Actions project, **multi-home** it into the RAID project using `mutate.py add-project` (do NOT create a duplicate)
   - If the item is new (e.g., a risk inferred from Jira data), create a new task in the RAID project with:
     ```bash
     uv run --project .claude/skills/asana python .claude/skills/asana/scripts/mutate.py create \
       --project-gid <raid_project_gid> --name "Risk description (WB-XXXX)" \
       --section "Risks" --assignee me --priority High \
       --notes "Source: Jira WB-4521 (open 45 days)\nDetected by /raid scan" --pretty
     ```
   - Set custom fields (Category, Impact, Likelihood, Status=Open, Source, Visibility=Internal) after creation

### Add Mode (manual creation)

**Invocation:** `/raid add GResearch "Champion VP Eng may be leaving"`

Manually add a RAID item with user guidance.

**Pipeline:**

1. Parse customer name and item description
2. Infer category from description (or ask user if ambiguous):
   - "may be leaving", "risk of", "threat" -> Risk
   - "assuming", "expects", "planned for" -> Assumption
   - "bug", "broken", "not working", "blocker" -> Issue
   - "blocked on", "waiting for", "depends on" -> Dependency
3. Ask user for (suggest sensible defaults):
   - **Impact**: High / Medium / Low
   - **Likelihood**: High / Medium / Low (for Risks/Assumptions)
   - **Visibility**: Internal / Shared (default: Internal)
   - **Priority**: High / Medium / Low
4. Create task in RAID project's appropriate section:
   ```bash
   uv run --project .claude/skills/asana python .claude/skills/asana/scripts/mutate.py create \
     --project-gid <raid_project_gid> --name "Champion VP Eng may be leaving" \
     --section "Risks" --assignee me --priority High \
     --notes "Source: cadence call 2026-03-24\nAdded manually via /raid add" --pretty
   ```
5. Set custom fields after creation (Category=Risk, Impact=High, Likelihood=Medium, Status=Open, Source=cadence call, Visibility=Internal)
6. If description contains a Jira reference (WB-XXXX pattern), add cross-link in notes
7. Confirm creation with task URL

## Portfolio Mode

**Invocation:** `/raid` (no customer name)

Loops over all customers in `templates/customers.yaml` where `raid_tracker_id` is not `PLACEHOLDER` and not empty. Shows aggregated RAID summary across all customers.

**Output format:**
```
RAID Portfolio Summary (2026-03-24)
====================================

GResearch:     2 Risks, 1 Assumption, 3 Issues, 2 Dependencies (8 total, 7 open)
Anthropic:     1 Risk, 0 Assumptions, 2 Issues, 1 Dependency (4 total, 3 open)
...

Totals: 3 Risks, 1 Assumption, 5 Issues, 3 Dependencies (12 total, 10 open)
```

## RAID Project Setup

Before using `/raid` with a customer, the RAID project must be created:

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/mutate.py setup-raid-project \
  --name "GResearch" --pretty
```

This creates `GResearch RAID Log` with 4 sections (Risks, Assumptions, Issues, Dependencies), finds or creates 6 custom fields at workspace level, and attaches all fields + Priority to the project.

Copy the output `project_gid` to `templates/customers.yaml` under `raid_tracker_id`.

## Safety Rules

- **View mode is read-only** -- no confirmation needed, no data modified
- **Scan mode: suggestions only** -- user confirms each item before creation
- **Add mode: show what will be created** -- user confirms before creation
- **Never create duplicate RAID items** -- check existing tasks in the RAID project before creating
- **FE-UPDATE comments excluded from staleness calculations** -- SE comments don't count as eng activity (consistent with all other skills)
- **RAID project is NEVER shared with customers** -- Visibility field tracks what can be *referenced* in meetings, not project access

## Troubleshooting

| Problem | Fix |
|---|---|
| `raid_tracker_id` not configured | Run `mutate.py setup-raid-project --name "Customer"` and copy GID to customers.yaml |
| Custom fields not found on project | Re-run `setup-raid-project` -- it finds existing fields by name and attaches them |
| "No RAID project for customer" | Check `templates/customers.yaml` has `raid_tracker_id` set (not PLACEHOLDER) |
| Multi-homing fails with 404 | Verify both the task GID and target project GID are correct |
| Scan mode finds no suggestions | Normal for well-maintained accounts. Try expanding Slack lookback or Jira query scope |
| HTML output not styled | Ensure design-system.md conventions are followed. Check Google Fonts CDN import |

## Related Skills

- `/asana` -- Base skill for task CRUD operations
- `/3p-update` -- Consumes RAID data for the Problems section of 3P updates
- `/cadence-prep` -- Consumes open Risks and Dependencies for meeting agendas
- `/customer-snapshot` -- SE Actions panel shows action tasks from the customer project
- `/jira` -- Data source for scan mode (Issues, stale items, FE-UPDATE status)
- `/slack` -- Data source for scan mode (customer channel sentiment, thread context)
