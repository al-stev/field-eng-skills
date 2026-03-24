---
name: salesforce
description: "Read-only Salesforce queries for account data. Use when needing SFDC account details, team members, field discovery, or account list. Trigger on 'salesforce', 'sfdc', 'account team', 'account details from salesforce'."
argument-hint: "<subcommand> [options]"
---

# Salesforce Skill

Read-only Salesforce API access for querying account data, team members, and field discovery.

## Prerequisites

- SFDC credentials configured in `~/.tsm-ai/.env` (run `/salesforce-setup` if not configured)
- Auth mode 1 (SSO/2FA -- recommended): `SFDC_SESSION_ID` + `SFDC_INSTANCE` (from `sf org login web` OAuth flow)
- Auth mode 2 (password): `SFDC_USERNAME` + `SFDC_PASSWORD` + `SFDC_SECURITY_TOKEN`
- W&B instance: `wandb.my.salesforce.com`

## Commands

### Describe Account Fields

Discover available fields on the Account object. Use `--filter` to search by label keyword.

```bash
uv run --project .claude/skills/salesforce python .claude/skills/salesforce/scripts/accounts.py describe --pretty
uv run --project .claude/skills/salesforce python .claude/skills/salesforce/scripts/accounts.py describe --filter "ARR" --pretty
uv run --project .claude/skills/salesforce python .claude/skills/salesforce/scripts/accounts.py describe --filter "renewal" --pretty
uv run --project .claude/skills/salesforce python .claude/skills/salesforce/scripts/accounts.py describe --filter "deployment" --pretty
```

### List My Accounts

List accounts where the current user is the Post-Sales AISE. Note: AccountTeamMember is NOT available in W&B's org, so this queries `Post_Sales_SMLE__c` instead.

```bash
uv run --project .claude/skills/salesforce python .claude/skills/salesforce/scripts/accounts.py my-accounts --pretty
```

### Account Detail

Fetch account details by Salesforce Account ID. Includes standard fields + W&B custom fields (ARR, renewal date, subscription plan, deployment types, CS tier, AISE, SA). Falls back to standard fields if custom fields are not available.

```bash
uv run --project .claude/skills/salesforce python .claude/skills/salesforce/scripts/accounts.py account-detail --account-id 0012E00002LLzyLQAT --pretty
```

### Account Team (from Account reference fields)

W&B stores account team as reference fields on Account, NOT in AccountTeamMember:

| SFDC Field | Role |
|---|---|
| `OwnerId` | Account Owner |
| `Post_Sales_SMLE__c` | Post-Sales AISE |
| `Solutions_Architect__c` | Solutions Architect |

Resolve names/emails by querying the User object with the reference IDs from account-detail.

### Team Members (legacy -- returns empty for W&B)

```bash
uv run --project .claude/skills/salesforce python .claude/skills/salesforce/scripts/accounts.py team-members --account-id 0012E00002LLzyLQAT --pretty
```

Returns empty in W&B's org (AccountTeamMember disabled). Use account-detail + User lookup instead.

### W&B Custom Field Mapping (discovered 2026-03-24)

| Registry Field | SFDC API Name |
|---|---|
| arr | `Renewal_ARR__c` |
| contract_end / renewal_date | `CS_Renewal_Date__c` |
| cs_tier | `CS_Tier__c` |
| subscription_plan | `Subscription_Plan__c` |
| deployment_type | `Opportunity_Deployment_Types__c` |

## Output Format

All commands output JSON to stdout. Use `--pretty` for human-readable indented output. Errors are written to stderr as `{"ok": false, "error": "...", "message": "..."}`.

## Error Handling

- **Missing credentials:** Raises error directing to `/salesforce-setup`
- **Authentication failed:** Suggests running `/salesforce-setup` to reconfigure
- **INVALID_FIELD:** Suggests running `describe` to discover correct field names
- **AccountTeamMember unavailable:** Falls back gracefully with empty results and a warning

## Related Skills

- `/salesforce-setup` -- One-time SFDC credential configuration
- `/customer-setup` -- Interactive customer registry onboarding (uses this skill)
- `/credential-status` -- Check health of all configured credentials
