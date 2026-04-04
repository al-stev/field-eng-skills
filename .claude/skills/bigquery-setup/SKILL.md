---
name: bigquery-setup
description: "One-time setup verification for BigQuery connectivity. Checks ADC credentials, wandb-production access, and analytics dataset."
argument-hint: ""
allowed-tools: Bash(bash .claude/skills/bigquery-setup/scripts/verify.sh)
---

# BigQuery Setup Verification

Verifies that Application Default Credentials (ADC) are configured and BigQuery connectivity to `wandb-production` is working.

## What It Checks

1. **gcloud CLI** -- Installed and on PATH
2. **ADC token** -- `gcloud auth application-default print-access-token` succeeds
3. **BigQuery connectivity** -- Can execute a simple query against `wandb-production`
4. **analytics dataset** -- Can access `stg_salesforce_accounts` table
5. **landing_development dataset** -- Can access `renewal_predictions` (non-fatal -- churn data optional)

## Usage

```bash
bash .claude/skills/bigquery-setup/scripts/verify.sh
```

## Setup Instructions

If verification fails:

1. Install gcloud CLI: `brew install google-cloud-sdk`
2. Login: `gcloud auth login`
3. Set ADC: `gcloud auth application-default login`
4. Re-run: `bash .claude/skills/bigquery-setup/scripts/verify.sh`

## Notes

- ADC tokens refresh automatically -- no manual token management needed
- No secrets stored in `~/.fe-skills/.env` for BigQuery (unlike Slack/Jira)
- The `landing_development` dataset check is non-fatal: if it fails, churn probability data will be unavailable but all other metrics still work
