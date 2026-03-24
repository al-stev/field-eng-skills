---
name: customer-setup
description: "Interactive customer onboarding -- add customers to the registry from Salesforce data with SE-provided overlays. Run '/customer-setup CustomerName' to add one customer, or '/customer-setup --all' to bulk-import from Salesforce. Trigger on 'add customer', 'onboard customer', 'set up customer', 'populate registry', 'customer-setup'."
argument-hint: "<customer-name> | --all"
---

# Customer Setup

Interactive onboarding skill for adding customers to `templates/customers.yaml`. Queries Salesforce for account-level data and prompts the SE for overlay fields (Slack channels, cadence schedule, Asana project GID) that don't exist in Salesforce.

Partial entries are acceptable -- use PLACEHOLDER markers for any field the SE skips or that cannot be resolved from Salesforce. Consumer skills (customer-snapshot, cadence-prep, jira-check, 3p-update) all handle PLACEHOLDER gracefully.

## Prerequisites

- **Salesforce credentials** configured in `~/.tsm-ai/.env` (run `/salesforce-setup` first). Optional -- if SFDC is unavailable, the skill falls back to manual entry for all fields.
- **Jira credentials** configured (for verifying customer name mapping). Required keys: `ATLASSIAN_EMAIL`, `ATLASSIAN_TOKEN`.
- **Slack credentials** configured (for verifying channel IDs). Required keys: `SLACK_TOKEN`, `SLACK_COOKIE`.

## Schema Reference

| Field | Source | Required for |
|-------|--------|-------------|
| name | SE input | All skills |
| jira_customer | SE confirms from SFDC name | jira-check, customer-snapshot, cadence-prep |
| jira_customer_variants | SE input | jira-check |
| sfdc_account_id | SFDC Account.Id | bigquery, customer-snapshot |
| slack_channels | SE input (Slack search) | customer-snapshot, cadence-prep, 3p-update |
| action_tracker | SE input ("asana" or "sheets") | 3p-update, customer-snapshot, nag, ghosted |
| action_tracker_id | SE input (Asana project GID or Sheets URL) | 3p-update, customer-snapshot |
| raid_tracker | SE input ("asana" or "sheets") | raid, cadence-prep, maction |
| raid_tracker_id | SE input (Asana RAID project GID or Sheets URL) | raid, cadence-prep |
| portfolio_id | SE input (Asana portfolio GID) | asana portfolio views |
| deployment_type | SFDC or SE input | cadence-prep |
| cadence | SE input | cadence-prep |
| contacts | SE-managed | cadence-prep |

---

## Mode 1: Per-Customer (`/customer-setup <CustomerName>`)

### Step 1: Parse Customer Name

Extract the customer name from the user's input. This becomes the `name` field in customers.yaml.

### Step 2: Check Existing Registry

Read `templates/customers.yaml` and check if the customer already exists:

- **If exists:** Show the current entry to the SE. Ask if they want to update any PLACEHOLDER fields with real data. Existing non-PLACEHOLDER values are preserved unless the SE explicitly chooses to overwrite.
- **If new:** Create a new entry skeleton with all fields set to PLACEHOLDER.

### Step 3: Query Salesforce (if credentials available)

First, discover available fields to understand the org's schema:

```bash
uv run --project .claude/skills/salesforce python .claude/skills/salesforce/scripts/accounts.py describe --filter "arr" --pretty
```

Then search for the customer by name:

```bash
uv run --project .claude/skills/salesforce python -c "
import sys
sys.path.insert(0, '.claude/skills/salesforce/scripts')
from sfdc_client import get_client
sf = get_client()
result = sf.query(\"SELECT Id, Name, Type FROM Account WHERE Name LIKE '%<CustomerName>%' AND Type = 'Customer'\")
for r in result['records']:
    print(f'{r[\"Name\"]} | {r[\"Id\"]}')
"
```

If a matching account is found, fetch full details including account team:

```bash
uv run --project .claude/skills/salesforce python .claude/skills/salesforce/scripts/accounts.py account-detail --account-id <ID> --pretty
```

**Note:** AccountTeamMember is NOT available in W&B's SFDC org. Account team members are stored as reference fields directly on the Account object. Resolve them separately:

```bash
uv run --project .claude/skills/salesforce python -c "
import sys
sys.path.insert(0, '.claude/skills/salesforce/scripts')
from sfdc_client import get_client
sf = get_client()
r = sf.query(\"SELECT OwnerId, Post_Sales_SMLE__c, Solutions_Architect__c FROM Account WHERE Id = '<ACCOUNT_ID>'\")['records'][0]
ids = [v for v in [r.get('OwnerId'), r.get('Post_Sales_SMLE__c'), r.get('Solutions_Architect__c')] if v]
users = sf.query(\"SELECT Id, Name, Email FROM User WHERE Id IN ('{}')\" .format(\"','\".join(ids)))
role_map = {r.get('OwnerId'): 'Account Owner', r.get('Post_Sales_SMLE__c'): 'Post-Sales AISE', r.get('Solutions_Architect__c'): 'Solutions Architect'}
for u in users['records']:
    print(f'{role_map.get(u[\"Id\"],\"?\")} | {u[\"Name\"]} | {u[\"Email\"]}')
"
```

Then look up each team member's Slack user ID. **Do NOT use `users.py search-name`** — it paginates the entire workspace and hits rate limits on large orgs like CoreWeave. Use one of these approaches instead (in priority order):

**Approach 1: Message search by handle** (fastest, most reliable)
```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/search.py --query "from:@<slack-handle>" --count 1
```
Extract `user` field from the first match. Derive handle from email prefix (e.g., `allan.stevenson@wandb.com` → try `@astevenson`, `@allan.stevenson`; `flamarion.jorge@wandb.com` → try `@fjorge`, `@flamarion.jorge`).

**Approach 2: Channel members** — Get members of a small channel the person is known to be in. Match by display name. Good when you don't know their handle.

**Approach 3: Profile URL** — Ask the SE to paste a Slack profile link (e.g., `https://coreweave.enterprise.slack.com/team/U08R4K46ER1`). The user ID is in the URL. Zero API calls.

**Present SFDC data to SE for confirmation before writing.**

Auto-fill from SFDC (W&B field mapping discovered 2026-03-24):
- `sfdc_account_id` -- Account.Id (18-char, also used as BigQuery account ID)
- `deployment_type` -- `Opportunity_Deployment_Types__c` (map to saas/dedicated-cloud/server)

Note: Business data fields (arr, contract_end, renewal_date, cs_tier, subscription_plan, account_team) are pulled from SFDC at runtime via the /salesforce skill -- they are NOT stored in customers.yaml. The routing table only stores pointers to external systems.

**If SFDC unavailable** (credentials not configured, auth fails, or no API permissions): Prompt the SE to enter each field manually. This is the D-05 fallback -- the schema is SFDC-ready even when populated by hand.

### Step 4: Jira Customer Name Mapping

The SFDC Account.Name (e.g., "G-Research Ltd") often differs from the Jira Customer field value (e.g., "GResearch"). The Jira Customer field uses unpredictable formats — hyphenated, parenthesized, abbreviated. **Never guess the Jira name from the SFDC name.**

**Discovery approach (in priority order):**

1. **Search by filter** — Ask the SE if they have a saved Jira filter for this customer. Filters are the most reliable way to find the exact customer field value:
```bash
uv run --project .claude/skills/jira python -c "
import sys; sys.path.insert(0, '.claude/skills/jira/scripts')
from jira_client import get_client; jira = get_client()
result = jira.search_issues('filter=<FILTER_ID>', maxResults=5, fields='customfield_10083')
for i in result:
    raw = i.raw['fields'].get('customfield_10083', [])
    for item in raw:
        val = item.get('value', str(item)) if isinstance(item, dict) else str(item)
        print(f'{i.key} | Customer: {val}')
"
```

2. **Broad search for raw field values** — Query all WB issues with non-empty Customer field, collect distinct values matching a keyword:
```bash
uv run --project .claude/skills/jira python -c "
import sys; sys.path.insert(0, '.claude/skills/jira/scripts')
from jira_client import get_client; jira = get_client()
result = jira.search_issues('project = WB AND \"Customer\" is not EMPTY', maxResults=200, fields='customfield_10083')
vals = set()
for i in result:
    for item in i.raw['fields'].get('customfield_10083', []):
        val = item.get('value', str(item)) if isinstance(item, dict) else str(item)
        if '<keyword>' in val.lower():
            vals.add(val)
for v in sorted(vals): print(v)
"
```

3. **Exact match verification** — Once you have a candidate value, verify:
```bash
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py list --customer "<jira_customer>" --max-results 1 --pretty
```

**CRITICAL:** If a search returns 0 results, the search term is wrong — NOT that the customer has no tickets. Try broader queries before concluding. Examples of format mismatches:
- SFDC: "MOD UK (Mike M/James C org)" → Jira: `MOD-UK-(Mike-M/James-C-org)`
- SFDC: "GResearch" → Jira: `GResearch` (happens to match)
- SFDC: "Isomorphic Labs" → Jira: `Isomorphic` (shorter)

4. After confirming, ask for `jira_customer_variants` — alternative spellings the SE has seen in Jira.

### Step 5: SE-Provided Overlays

These fields don't exist in Salesforce and require SE input:

**Slack channels:**

Ask the SE for channel name(s) (e.g., "ext-gresearch", "supp-gresearch"). Look up the channel ID:

```bash
uv run --project .claude/skills/slack python .claude/skills/slack/scripts/channels.py search "<channel-name>"
```

For each channel, capture:
- `id` -- Slack channel ID (from search results)
- `name` -- Channel name (e.g., ext-gresearch)
- `type` -- external | internal | support (infer from prefix: ext-* = external, supp-* = support, otherwise ask)

**Cadence schedule:**

Ask the SE:
- `type` -- weekly | biweekly | monthly | qbr
- `day` -- Day of week (e.g., Tuesday)
- `time` -- Time with timezone (e.g., "10:00 AM PT")

**Asana project GID:**

Ask if the customer has an Asana project for SE action tracking. If yes, look up existing projects:

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/query.py projects --pretty
```

If the project exists, use its GID. If not, offer to create one:

```bash
uv run --project .claude/skills/asana python .claude/skills/asana/scripts/mutate.py setup-project --name "<CustomerName>" --pretty
```

**Deployment type:**

If not already resolved from SFDC in Step 3, ask the SE:
- `saas` -- Multi-tenant SaaS (app.wandb.ai)
- `dedicated-cloud` -- Customer-specific cloud instance, managed by W&B
- `server` -- Self-hosted by customer (on-prem or customer cloud)

**Contacts:**

Build contacts list from SE input (account team data is pulled from SFDC at runtime, not stored in customers.yaml). Each contact has:
- `name` -- Contact name
- `org` -- Organization (e.g., W&B, G-Research)
- `role` -- Contact role

### Step 6: Write to Registry

Use Claude's Read tool to read the current `templates/customers.yaml`, then use Claude's Edit tool to add or update the customer entry.

**For new customers:** Append a new entry at the end of the `customers:` list, following the same YAML structure as the GResearch entry.

**For existing customers:** Update only the fields that changed (PLACEHOLDER -> real value, or SE-confirmed overwrites). Preserve all existing entries, comments, and formatting.

Use PLACEHOLDER for any field the SE skips or that could not be resolved.

### Step 7: Verify

1. Read back the entry from `templates/customers.yaml` and show it to the SE for final confirmation.
2. Run a quick Jira test to verify the customer name mapping works:

```bash
uv run --project .claude/skills/jira python .claude/skills/jira/scripts/issues.py list --customer "<jira_customer>" --max-results 3 --pretty
```

3. Confirm: "Customer `<name>` has been added to the registry. Run `/customer-snapshot <name>` or `/jira-check` to verify full integration."

---

## Mode 2: Batch (`/customer-setup --all`)

### Step 1: Query SFDC for SE's Accounts

AccountTeamMember is NOT available in W&B's org. Instead, find accounts where the current user is the Post-Sales AISE:

```bash
uv run --project .claude/skills/salesforce python -c "
import sys
sys.path.insert(0, '.claude/skills/salesforce/scripts')
from sfdc_client import get_client
import requests
sf = get_client()
# Get current user ID
resp = requests.get(f'https://{sf.sf_instance}/services/oauth2/userinfo', headers={'Authorization': f'Bearer {sf.session_id}'}, timeout=10)
user_id = resp.json()['user_id']
# Find accounts where user is AISE
result = sf.query_all(f\"SELECT Id, Name, Type FROM Account WHERE Post_Sales_SMLE__c = '{user_id}' AND Type = 'Customer'\")
for r in result['records']:
    print(f'{r[\"Name\"]} | {r[\"Id\"]}')
"
```

### Step 2: Present Account List

Show the SE the list of accounts found in SFDC. Ask which accounts to onboard -- not all accounts may be actively managed (per D-01, only actively managed accounts belong in the registry).

For each account, show: Account Name and Account ID.

### Step 3: Onboard Each Selected Account

For each selected account, run the per-customer flow (Mode 1, Steps 3-7). The SFDC data is already available from the batch query, so Step 3 (Query Salesforce) can use the cached data rather than re-querying.

### Step 4: Summary

After all selected accounts are processed, show a summary:

- Accounts added: list with names
- Accounts updated: list with names and fields updated
- PLACEHOLDER fields remaining: list per account (these can be filled later by running `/customer-setup <name>` again)

---

## Idempotency

This skill is idempotent -- designed to be run repeatedly without causing data loss:

- Running `/customer-setup GResearch` when GResearch already exists updates PLACEHOLDER fields only. Existing non-PLACEHOLDER values are preserved unless the SE explicitly chooses to overwrite.
- Running `/customer-setup --all` skips accounts already in the registry (unless the SE opts to refresh them).
- Running the skill when SFDC credentials are not configured gracefully falls back to manual entry -- no errors, just prompts.
- Re-running after partial completion fills in any remaining PLACEHOLDER fields.

## Troubleshooting

### SFDC query returns no accounts

- Verify SFDC credentials with `/salesforce-setup`
- The user may not be listed as an AccountTeamMember in SFDC -- ask the SE to check their account assignments
- Fall back to manual entry: the SE can provide all field values directly

### Jira customer name mismatch

- The SFDC Account.Name often differs from the Jira Customer field (e.g., "G-Research Ltd" vs "GResearch")
- Try different spellings in the Jira test query
- Add all known variants to `jira_customer_variants`

### Slack channel not found

- Verify the channel name spelling
- The bot may not have access to the channel -- check with `/slack-setup`
- Enter the channel ID manually if known (find it in Slack channel settings)

### Missing SFDC fields

- Some custom fields (Renewal_ARR__c, CS_Tier__c, etc.) may not exist in every SFDC org
- Run `accounts.py describe --filter "<field>"` to check available fields
- Use PLACEHOLDER for unavailable fields -- they can be populated later

## Related Skills

- `/salesforce-setup` -- Configure SFDC credentials (prerequisite)
- `/salesforce` -- Direct SFDC queries (account details, team members, field discovery)
- `/credential-status` -- Check health of all configured credentials
- `/jira-check` -- Verify Jira integration works for registered customers
- `/customer-snapshot` -- Generate customer intelligence dashboard
- `/cadence-prep` -- Prepare cadence meeting materials
