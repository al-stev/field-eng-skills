# Asana Workspace Rules

## Workspace

- User is a Solutions Engineer at W&B (Weights & Biases), which is by CoreWeave
- Asana tracks SE actions and customer task management -- separate from Jira (which tracks engineering work)
- Use the Asana skill scripts (uv run) for Asana operations
- Never use MCP Asana tools -- use the Asana skill exclusively

## Instance

| Property | Value |
|---|---|
| Workspace GID | `1208076155392173` |
| SE Team project GID | `1213787150415828` |
| Default team GID | `1211862347384669` (W&B EMEA Post-Sales) |
| Web app | https://app.asana.com |

## Authentication

| Property | Value |
|---|---|
| Credential store | `~/.tsm-ai/.env` |
| Token key | `ASANA_TOKEN` |
| Auth method | Personal Access Token (PAT) |

## Standard Sections (6 per project)

All customer projects and the SE Team project use these sections in this order:

1. **To Do** -- Queued work, not yet started
2. **In Progress** -- Actively being worked on
3. **Waiting on Customer** -- Blocked on customer response/action
4. **Waiting on Eng** -- Blocked on engineering work (linked to Jira issue)
5. **Scheduled/Future** -- Planned for later, not yet actionable
6. **Done** -- Completed tasks

## Priority Custom Field

Enterprise+ plan -- using existing workspace Priority field (High/Medium/Low). `PRIORITY_FIELD_GID` in mutate.py is populated.

| Property | Value |
|---|---|
| Field GID | `1208185034501267` |
| High option GID | `1208185034501270` |
| Medium option GID | `1208185034501271` |
| Low option GID | `1208185034501272` |

Legacy P0-P3 names are accepted by mutate.py and mapped: P0/P1 -> High, P2 -> Medium, P3 -> Low.

## RAID (Risks, Assumptions, Issues, Dependencies)

### Two-Project Model

Each customer has TWO Asana projects:

1. **Customer Actions project** (`[Customer] Actions`) -- day-to-day SE work. 6 standard sections (To Do, In Progress, Waiting on Customer, Waiting on Eng, Scheduled/Future, Done). Safe to share with customers.

2. **RAID Portfolio project** (`[Customer] RAID Log`) -- internal strategic view. 4 RAID sections (Risks, Assumptions, Issues, Dependencies). NEVER shared with customers.

**Multi-homing:** Action tasks from the customer project can also appear in the RAID project under Issues or Dependencies via `mutate.py add-project`. Internal-only Risks and Assumptions only live in the RAID project.

**Visibility:**
- Customer sees: their Actions project with statuses and due dates
- SE sees: Actions project PLUS the internal RAID layer
- Management sees: portfolio RAID view across all customers

### RAID Categories

| Category | What it tracks | Examples |
|---|---|---|
| **Risks** | Potential future problems | Churn signals, champion loss, competitive threat, declining usage, renewal risk |
| **Assumptions** | Things assumed true that could blow up | "Customer will renew at ACV", "migration planned for Q3" |
| **Issues** | Active current problems | Product bugs, feature gaps, adoption blockers (maps to Jira) |
| **Dependencies** | Blocked on external factors | Waiting on eng, product roadmap, customer providing access |

### RAID Custom Fields

Created at workspace level by `mutate.py setup-raid-project`. GIDs discovered from live Asana workspace (2026-03-24).

| Field | GID | Type | Values |
|---|---|---|---|
| Category | `1212045998650534` | enum | **Note:** Reused existing workspace field with non-RAID values (General Site Safety, PPE, etc.). RAID values (Risk/Assumption/Issue/Dependency) not yet available as enum options. Use task section placement (Risks/Assumptions/Issues/Dependencies) as the primary categorization. |
| Impact | `1213802950765700` | enum | High (`1213802950765701`) / Medium (`1213802950765702`) / Low (`1213802950765703`) |
| Likelihood | `1213797930646918` | enum | High (`1213797930646919`) / Medium (`1213797930646920`) / Low (`1213797930646921`) |
| Status | `1208249896021493` | enum | **Note:** Reused existing workspace field with project-management values (New, Ready, In Progress, Blocked, Done, In Review, Descoped). Use "In Progress" for Open, "Done" for Closed. No direct "Accepted" mapping. |
| Source | `1213810597892502` | text | Where it came from (Slack thread, cadence call, QBR) |
| Visibility | `1213802950256772` | enum | Internal (`1213802950256773`) / Shared (`1213802950256774`) |

**Known limitation:** Category and Status fields were reused from existing workspace-level fields with non-RAID enum options. The RAID project's section names (Risks, Assumptions, Issues, Dependencies) serve as the primary categorization. A future improvement would create SE-specific "RAID Category" and "RAID Status" fields with correct enum values.

### RAID Project Setup

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/mutate.py setup-raid-project --name "GResearch" --pretty
```

Creates `[CustomerName] RAID Log` project with 4 sections, finds or creates 6 custom fields, attaches all fields + Priority. Copy the output `project_gid` to `customers.yaml` under `asana_raid_project_gid`.

### Multi-Homing Tasks

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/mutate.py add-project \
  --task-gid TASK_GID --project-gid RAID_PROJECT_GID --section "Issues" --pretty
```

Adds an existing task to the RAID project without removing it from the customer Actions project. Use for Issues and Dependencies that originate as action items.

## Conventions

### Jira Cross-Linking

Task name suffix `(WB-1234)` links an Asana task to a Jira issue. Parsed with regex `\(WB-\d+\)`.

Example: `Follow up on SDK crash (WB-1234)`

This enables bidirectional cross-linking in the customer dashboard:
- Asana task references Jira issue in its name
- Dashboard shows a badge on the Jira issue linking to the Asana task

### Staleness Rules

| Condition | Threshold | Signal |
|---|---|---|
| **Overdue** | Past due date | Red flag |
| **Stale** | No updates 7+ days in To Do or In Progress | Amber flag |
| **Waiting sections exempt** | Waiting on Customer, Waiting on Eng | No staleness (you're waiting on someone else) |
| **Scheduled exempt** | Scheduled/Future | No staleness (not yet actionable) |

Staleness is measured by `modified_at` from the Asana API.

### Task Assignment

- All tasks assigned to individual SEs
- Asana's native "My Tasks" view gives each SE their cross-customer view
- Multiple SEs can share the same customer projects, filtered by assignee
- `--assignee me` resolves to the PAT owner

## Cross-Reference

Asana and Jira serve different purposes:

| System | Tracks | Audience |
|---|---|---|
| **Asana** | SE actions, customer task management, follow-ups | Solutions Engineers |
| **Jira** | Engineering bugs, feature requests, product work | Product & Engineering |

Asana tasks may reference Jira issues (via name suffix), but Asana is NOT a mirror of Jira. Asana tracks what the SE needs to do about a Jira issue, not the Jira issue itself.

## Project Structure

- **One Actions project per customer** -- all SEs can see all projects. GID stored in `templates/customers.yaml` under `asana_project_gid`
- **One RAID project per customer** -- internal strategic view. GID stored in `templates/customers.yaml` under `asana_raid_project_gid`
- **SE Team project** -- shared project for internal/cross-cutting work (GID in table above)
- Actions projects have 6 standard sections; RAID projects have 4 RAID sections (see Two-Project Model above)
- Each customer's Actions and RAID projects live inside a customer portfolio within the master portfolio. See Portfolio Structure below.

## Portfolio Structure

### Nested Hierarchy

```
Portfolio: "W&B EMEA Customers"              <- master portfolio
  |-- Portfolio: "GResearch"                 <- one per customer
  |    |-- GResearch Actions (project)
  |    |-- GResearch RAID Log (project)
  |-- Portfolio: "GSK"
  |    |-- GSK Actions (project)
  |    |-- GSK RAID Log (project)
  |-- ... more customers
```

### Portfolio Custom Fields (on master portfolio)

| Field | Type | Values |
|---|---|---|
| SE Owner | people | Workspace members dropdown |
| Account Exec | people | Workspace members dropdown |
| Deployment Type | enum | SaaS / Dedicated Cloud / Server |
| Customer Health | enum | Green / Amber / Red |

### Setup Commands

One-time master portfolio creation:
```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/mutate.py create-master-portfolio --name "W&B EMEA Customers" --pretty
```

Per-customer setup (creates portfolio + Actions + RAID + adds to master):
```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/mutate.py setup-customer \
  --name "GResearch" --master-portfolio-gid MASTER_GID \
  --se-owner-gid USER_GID --deployment-type dedicated-cloud --health green --pretty
```

Delete a portfolio:
```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/mutate.py delete-portfolio --gid 1211862347976624 --pretty
```

### Views (all native Asana, filtered from master portfolio)

| Persona | View | How |
|---|---|---|
| SE -- my customers | Filter: SE Owner = me | See only your customers |
| SE -- single customer | Click customer row | See Actions + RAID projects |
| Manager -- all customers | No filter | All customers, sort by health |
| Manager -- one SE's book | Filter: SE Owner = [name] | One SE's customers |
