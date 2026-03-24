---
name: salesforce-setup
description: "One-time Salesforce credential setup. Run before first use of /salesforce, when SFDC credentials are missing or expired, or on 'set up Salesforce' or 'configure Salesforce'."
disable-model-invocation: true
allowed-tools: Bash(chmod *), Bash(uv run --project .claude/skills/salesforce *), Bash(sf *), Bash(npm install -g @salesforce/cli *)
---

# Salesforce Setup

One-time setup for Salesforce API access used by the `/salesforce` and `/customer-setup` skills.

## Prerequisites

- A Salesforce account (W&B uses SSO -- you log in via your identity provider)
- Salesforce CLI (`sf`) installed: `npm install -g @salesforce/cli`
- Signed in to Salesforce in your browser

## Auth Method: Salesforce CLI OAuth (Recommended for SSO/2FA)

W&B's Salesforce org uses SSO, so username/password auth doesn't work. Instead, use the Salesforce CLI which handles OAuth via browser redirect.

### Step 1: Install Salesforce CLI

```bash
npm install -g @salesforce/cli
```

### Step 2: Authenticate via Browser

```bash
sf org login web --instance-url https://wandb.my.salesforce.com --alias wandb
```

This opens a browser window. Click **Allow** to authorize. No password needed -- uses your existing SSO session.

### Step 3: Extract Access Token

After successful login:

```bash
sf org display --target-org wandb --json
```

Copy the `accessToken` and `instanceUrl` values from the output.

### Step 4: Save Credentials

Ensure the credential directory exists:

```bash
mkdir -p ~/.tsm-ai && chmod 700 ~/.tsm-ai
```

Use the **Edit tool** to add to `~/.tsm-ai/.env`:

- `SFDC_SESSION_ID=<accessToken from sf org display>`
- `SFDC_INSTANCE=wandb.my.salesforce.com`

Do **NOT** use `echo`, `printf`, or any bash command to write credentials -- these leak into shell history.

Then lock file permissions:

```bash
chmod 600 ~/.tsm-ai/.env
```

### Step 5: Install Python Dependencies

```bash
cd .claude/skills/salesforce && uv sync
```

### Step 6: Verify Connectivity

```bash
uv run --project .claude/skills/salesforce python -c "
import sys
sys.path.insert(0, '.claude/skills/salesforce/scripts')
from sfdc_client import get_client
sf = get_client()
print('Connected to Salesforce!')
print(f'Instance: {sf.sf_instance}')
result = sf.query('SELECT Id, Name FROM Account LIMIT 3')
for r in result['records']:
    print(f'  {r[\"Name\"]} ({r[\"Id\"]})')
"
```

### Step 7: Discover Custom Fields (First time only)

```bash
uv run --project .claude/skills/salesforce python .claude/skills/salesforce/scripts/accounts.py describe --filter "arr" --pretty
uv run --project .claude/skills/salesforce python .claude/skills/salesforce/scripts/accounts.py describe --filter "renewal" --pretty
uv run --project .claude/skills/salesforce python .claude/skills/salesforce/scripts/accounts.py describe --filter "tier" --pretty
uv run --project .claude/skills/salesforce python .claude/skills/salesforce/scripts/accounts.py describe --filter "AISE" --pretty
uv run --project .claude/skills/salesforce python .claude/skills/salesforce/scripts/accounts.py describe --filter "architect" --pretty
```

### W&B SFDC Field Mapping (discovered 2026-03-24)

| Registry Field | SFDC Field | Type |
|---|---|---|
| arr | `Renewal_ARR__c` | currency |
| contract_end | `CS_Renewal_Date__c` | date |
| cs_tier | `CS_Tier__c` | picklist |
| subscription_plan | `Subscription_Plan__c` | text |
| deployment_type | `Opportunity_Deployment_Types__c` | text |
| account_team: Account Owner | `OwnerId` → User lookup | reference |
| account_team: Post-Sales AISE | `Post_Sales_SMLE__c` → User lookup | reference |
| account_team: Solutions Architect | `Solutions_Architect__c` → User lookup | reference |

Account team members are NOT in AccountTeamMember (disabled in W&B org). They are reference fields directly on the Account object.

## Alternative: Session-Based Auth (Legacy)

If Salesforce CLI isn't available, you can grab a session from the browser:

1. Navigate to `https://wandb.my.salesforce.com/` in your browser (must be the classic domain, not Lightning)
2. The `sid` cookie from the Lightning domain (`wandb.lightning.force.com`) does NOT work for REST API
3. Use `sf org login web` instead -- it handles the OAuth flow correctly

## Token Refresh

The `sf` CLI access token expires periodically. To refresh:

```bash
sf org login web --instance-url https://wandb.my.salesforce.com --alias wandb
sf org display --target-org wandb --json
```

Then update `SFDC_SESSION_ID` in `~/.tsm-ai/.env` with the new `accessToken`.

## Troubleshooting

### INVALID_SESSION_ID

- Token has expired. Re-run `sf org login web` and update `SFDC_SESSION_ID`.

### INVALID_FIELD

- Run `accounts.py describe` to find correct field API names
- Custom field names are org-specific and end in `__c`
- Update `CUSTOM_FIELDS` in `accounts.py` if your org uses different names

### sf: command not found

- Run `npm install -g @salesforce/cli`

### Browser doesn't open during sf login

- Run the command interactively: `! sf org login web --instance-url https://wandb.my.salesforce.com --alias wandb`

### AccountTeamMember not available

- This is expected for W&B's org. Account team roles are stored as reference fields on the Account object (OwnerId, Post_Sales_SMLE__c, Solutions_Architect__c), not in AccountTeamMember.

## Fallback: Manual Population

If SFDC API access is blocked entirely, the `/customer-setup` skill can still populate the customer registry manually. SFDC credentials are optional -- having them makes population faster and more accurate, but all registry fields can be entered by hand.
