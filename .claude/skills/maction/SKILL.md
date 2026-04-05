---
name: maction
description: "Extract action items, RAID items, and feedback from meeting notes or transcripts. Creates Asana tasks, publishes meeting notes to Confluence, and captures customer feedback. Use when the user shares meeting notes, Granola output, call transcript, or asks to create actions from a meeting. Trigger for /maction, 'create actions from this meeting', 'extract actions from notes', 'meeting to tasks'."
argument-hint: "<customer-name> <meeting-notes or paste>"
requires-credentials:
  - ASANA_TOKEN
  - ATLASSIAN_EMAIL
  - ATLASSIAN_TOKEN
---

# Meeting Notes to Actions + RAID Pipeline

Turns meeting notes into tracked work. Extracts two types of items:

## Prerequisites

- **Asana** -- `ASANA_TOKEN` in `~/.fe-skills/.env` (run `/asana-setup` if not configured)
- **Customer registry** -- Customer must exist in `templates/customers.yaml` with `action_tracker_id` (for actions) and optionally `raid_tracker_id` (for RAID items)

## Output

- **Action items** -> Asana tasks in the customer's Actions project
- **RAID items** (risks, assumptions, dependencies mentioned in the meeting) -> Asana tasks in the RAID project

Input is typically Granola summary format but can be a full transcript, pasted text, or a file path.

## Pipeline

### Step 1: Parse input

- **Customer name** (required): fuzzy-match against `templates/customers.yaml` names
- **Meeting notes**: the rest of the input. Can be:
  - Pasted text (Granola summary, transcript, bullet points)
  - File path to a `.md` or `.txt` file
  - If notes are very short (< 50 words), ask user if they want to paste more

### Step 2: Extract action items

Analyze the meeting notes and extract action items. For each action item, determine:

| Field | How to Infer |
|-------|-------------|
| **Task name** | Concise, action-oriented (e.g., "Send SDK migration guide to customer") |
| **Owner** | "Allan will..." = me, "Customer will..." = customer, "Eng team will..." = eng |
| **Due date** | "by next week" = 7 days, "before the QBR" = QBR date from customers.yaml. Default: 7 days if no signal. |
| **Priority** | P0-P3 based on urgency signals in the notes (escalation = P1+, routine = P2-P3) |
| **Section** | Default "To Do". "Waiting on Customer" if action is on the customer. "Waiting on Eng" if waiting on eng. |
| **Jira reference** | Detect `WB-XXXX` patterns in the notes context around this action |

### Step 3: Extract RAID items

Analyze the meeting notes for RAID signals:

- **Risks**: mention of churn, competitor, champion leaving, declining usage, renewal concern, "worried about", "risk of"
- **Assumptions**: implicit assumptions ("assuming they'll renew", "expecting migration by Q3", "plan is to...")
- **Dependencies**: "blocked on", "waiting for eng to", "need product to ship", "depends on"
- **Issues**: typically already tracked in Jira -- only flag explicit new issues not yet in Jira

For each RAID item, determine:

| Field | How to Infer |
|-------|-------------|
| **Category** | Risk, Assumption, Issue, or Dependency |
| **Description** | Concise statement of the item |
| **Impact** | High / Medium / Low (infer from context) |
| **Likelihood** | High / Medium / Low (infer from context) |
| **Source** | "Cadence call [date]" or "Meeting notes [date]" |
| **Visibility** | Default Internal (Risks/Assumptions always internal; Dependencies may be Shared) |

### Step 3.5: Extract customer feedback signals

Analyze the meeting notes for customer-originating feedback -- their words, their sentiment, their satisfaction signals. This is NOT your internal assessment of the customer; it's what THEY expressed.

| Signal Type | What to Look For |
|-------------|-----------------|
| **NPS/CSAT** | Any mention of scores, surveys, ratings |
| **Praise** | Customer expressing satisfaction ("this is great", "really happy with", "exactly what we needed") |
| **Complaint** | Customer expressing dissatisfaction ("frustrated", "doesn't work", "been waiting", "considering alternatives") |
| **Feature ask** | Customer requesting something directly ("we really need", "wish you had", "when will you support") |
| **Churn signal** | Customer mentioning competitors, evaluating alternatives, questioning value |

For each feedback item, determine:

| Field | How to Infer |
|-------|-------------|
| **Summary** | One-line description of the feedback |
| **Type** | NPS, Praise, Complaint, Feature Ask, or Churn Signal |
| **Status** | OPEN (needs response/action) or BACKLOG (noted, no action needed) |
| **Direct quote** | The customer's actual words if available (in italics) |
| **Source links** | Gong, Granola, or Slack links if provided in the input |

If no feedback signals are detected, skip this step silently -- not every meeting has customer feedback.

### Step 3.6: Compose meeting notes entry

Prepare a Confluence meeting notes entry in the standard FE format. The entry is a collapsible section with:

- **Title**: `YYYY-MM-DD -- <Short Title> (<Participants>)`
- **Source Links**: Links to Gong call, Granola notes, Slack threads (from the input)
- **Summary**: 3-5 bullet points covering what was discussed
- **Action Items**: List of actions extracted in Step 2 (with owners)
- **Key Decisions**: Any decisions made during the meeting
- **RAID Signals**: Any risks/dependencies flagged in Step 3

The Confluence storage format for one entry:

```xml
<ac:structured-macro ac:name="expand" ac:schema-version="1">
  <ac:parameter ac:name="title">YYYY-MM-DD -- Short Title (Participants)</ac:parameter>
  <ac:rich-text-body>
    <p><time datetime="YYYY-MM-DD" /></p>
    <p><strong>Source Links:</strong></p>
    <ul>
      <li><p>Gong: <a href="URL">Call title</a> (or "Not recorded")</p></li>
      <li><p>Granola: <a href="URL">Notes title</a> (or "None")</p></li>
      <li><p>Slack: <a href="URL">Thread context</a> (or "None")</p></li>
    </ul>
    <h3>Summary</h3>
    <ul><li><p>Key point 1</p></li>...</ul>
    <h3>Action Items</h3>
    <ul><li><p>[Owner] Action description -- Due: YYYY-MM-DD</p></li>...</ul>
    <h3>Decisions</h3>
    <ul><li><p>Decision made</p></li>...</ul>
  </ac:rich-text-body>
</ac:structured-macro>
```

### Step 4: Present proposals to user

Show all extracted items in a clear format before creation:

```
Actions from [Customer] meeting ([date]):

PROPOSED ACTIONS (for [Customer] Actions project):
1. [P1] Send SDK migration guide to customer -- Due: 2026-04-01 -- Owner: me -- Section: To Do
2. [P2] Follow up on WB-1234 fix status (WB-1234) -- Due: 2026-03-28 -- Owner: me -- Section: Waiting on Eng
3. [P3] Customer to provide access credentials -- Due: 2026-04-05 -- Owner: customer -- Section: Waiting on Customer

PROPOSED RAID ITEMS (for [Customer] RAID Log):
R1. [Risk] Champion VP Eng may be leaving -- Impact: High, Likelihood: Medium -- Source: Cadence call 2026-03-24
D1. [Dependency] Blocked on eng shipping SDK v2.1 hotfix -- Impact: High, Likelihood: High -- Source: Cadence call 2026-03-24

CONFLUENCE MEETING NOTES (will be appended to [Customer] - Meeting Notes):
Title: 2026-03-24 -- Cadence Call (Allan, Customer Lead)
Summary: 3 bullet points
Sources: Granola link, Gong link

[If feedback found:]
CUSTOMER FEEDBACK (will be appended to [Customer] - Feedback):
F1. [Complaint] "We've been waiting three weeks for this fix" -- Status: OPEN

Confirm: create all (y), select items (s), or cancel (n)?
```

### Step 5: Create confirmed items

For user-confirmed **action items**:

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/mutate.py create \
  --project-gid <action_tracker_id> --name "<task name>" \
  --section "<section>" --assignee me --due <YYYY-MM-DD> --priority <P0-P3> \
  --notes "Source: Meeting notes [date]\n\nContext: <relevant excerpt from notes>" \
  --pretty
```

For user-confirmed **RAID items**:

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/mutate.py create \
  --project-gid <raid_tracker_id> --name "<description>" \
  --section "<Risks|Assumptions|Issues|Dependencies>" --assignee me \
  --notes "Source: <source>\n\nContext: <relevant excerpt from notes>" \
  --pretty
```

After creation, set custom fields on RAID items (Category, Impact, Likelihood, Status=Open, Source, Visibility) via `mutate.py update` with `--custom-fields` or through the Asana API directly.

### Step 6: Publish meeting notes to Confluence

Look up `confluence_pages.meeting_notes` from the customer's entry in `templates/customers.yaml`. If configured:

1. **Fetch the current page** to get the existing body:
   ```bash
   uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/pages.py get --id <meeting_notes_page_id> --pretty
   ```

2. **Prepend** the new collapsible entry (from Step 3.6) to the TOP of the existing body, after any intro text. New entries go at the top so the most recent meeting is first.

3. **Update the page** with the combined body:
   ```bash
   uv run --project .claude/skills/confluence python .claude/skills/confluence/scripts/pages.py update \
     --id <meeting_notes_page_id> --title "<existing title>" \
     --body "<intro text><new entry><existing entries>" --pretty
   ```

**If `confluence_pages` is not configured for this customer:** Skip silently and note in the summary that Confluence publishing was skipped.

### Step 6.5: Publish feedback to Confluence

Only run this step if feedback items were extracted in Step 3.5.

Look up `confluence_pages.feedback` from `templates/customers.yaml`. If configured:

1. **Fetch the current page** to get the existing body.

2. For each feedback item, create an expandable entry in the same format as the FE team's existing pages:
   ```xml
   <ac:structured-macro ac:name="expand" ac:schema-version="1">
     <ac:parameter ac:name="title">YYYY-MM-DD [Type] Short description [Updated YYYY-MM-DD]</ac:parameter>
     <ac:rich-text-body>
       <p><time datetime="YYYY-MM-DD" /></p>
       <p>Summary: <em>"Direct customer quote if available"</em></p>
       <p>Context from meeting notes.</p>
       <p><strong>Links:</strong></p>
       <ul>
         <li><p>Gong: <a href="URL">Call</a> (or None)</p></li>
         <li><p>Granola: <a href="URL">Notes</a> (or None)</p></li>
       </ul>
       <p><strong>Status:</strong></p>
       <ul><li><p>Current status and any planned response.</p></li></ul>
     </ac:rich-text-body>
   </ac:structured-macro>
   ```

3. **Insert** the new entry under the appropriate section header (OPEN or BACKLOG) in the existing page body.

4. **Update the page.**

**If no feedback signals found:** Skip this step entirely.
**If `confluence_pages` is not configured:** Skip silently.

### Step 7: Summary

After all items are created, output a summary:

```
Created:
- 3 action items in [Customer] Actions project
- 2 RAID items in [Customer] RAID Log
- Meeting notes published to Confluence (2026-03-24 -- Cadence Call)
- 1 feedback item published to Confluence
Links: [task URLs, Confluence page URLs]
```

## Granola Format Notes

Granola summaries typically have these sections:
- Summary / Key Points
- Action Items (often pre-extracted but may be incomplete)
- Decisions Made
- Discussion Topics

When processing Granola output, use the pre-extracted action items as a starting point but also scan the full summary for missed actions and RAID signals. Granola often misses RAID-type items since it focuses on explicit action items.

## RAID Detection Heuristics

| Category | Keywords / Patterns |
|----------|-------------------|
| **Risk** | "risk", "churn", "competitor", "leaving", "declining", "renewal", "worried", "concerned", "threat" |
| **Assumption** | "assuming", "expecting", "plan is", "should be", "will be", "by Q[1-4]" |
| **Dependency** | "blocked", "waiting for", "depends on", "need [team] to", "can't proceed until" |
| **Issue** | "bug", "broken", "not working", "outage", "escalation" (cross-check with Jira first) |

Context matters: "risk mitigation" is different from "there's a risk of churn". Use surrounding sentences to disambiguate.

## Edge Cases

- **RAID project not configured** (`raid_tracker_id` is `PLACEHOLDER`): extract RAID items and display them but warn that they can't be created in Asana. Suggest running `/asana setup-raid-project` first.
- **Customer Actions project not configured** (`action_tracker_id` is `PLACEHOLDER`): same warning, suggest `/asana setup-project`.
- **Meeting notes are very short** (< 50 words): ask user if they have more context to share before extracting.
- **No action items or RAID items found**: "No actionable items or RAID signals detected in these notes. If you expected items, try providing more context."
- **Ambiguous customer**: if customer name matches multiple entries, ask user to clarify.

## Safety Rules

- **User confirms ALL items before creation.** Never auto-create.
- Show exactly what will be created (name, project, section, fields) before confirmation.
- Never modify existing tasks -- only create new ones.
- RAID items default to Internal visibility.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No actions extracted | Notes may be too vague. Ask user to highlight specific commitments. |
| Wrong customer matched | Specify exact customer name from `templates/customers.yaml` |
| RAID items can't be created | `raid_tracker_id` is `PLACEHOLDER` -- run `/asana setup-raid-project` first |
| Custom fields not set on RAID items | Custom fields must be created first via `setup-raid-project` |
| Due date inference wrong | User can adjust dates during the confirmation step |

## Related Skills

- `/asana` -- base skill for task creation
- `/raid` -- RAID items created here appear in `/raid` view
- `/ghosted` -- tasks created in "Waiting on Customer" are tracked by `/ghosted`
- `/cadence-prep` -- actions and RAID items created here feed into cadence-prep agendas
