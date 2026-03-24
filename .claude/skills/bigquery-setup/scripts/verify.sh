#!/usr/bin/env bash
# BigQuery connectivity verification for wandb-production.
# Checks ADC credentials, BQ access, and dataset availability.
# Exit 0 if core checks pass, exit 1 if gcloud/ADC/BQ/analytics fail.

set -euo pipefail

PASS="\033[0;32mPASS\033[0m"
FAIL="\033[0;31mFAIL\033[0m"
WARN="\033[0;33mWARN\033[0m"

echo "=== BigQuery Setup Verification ==="
echo ""

# 1. Check gcloud CLI installed
echo -n "[1/5] gcloud CLI installed... "
if command -v gcloud &>/dev/null; then
    echo -e "$PASS ($(gcloud --version 2>/dev/null | head -1))"
else
    echo -e "$FAIL"
    echo "  Install: brew install google-cloud-sdk"
    exit 1
fi

# 2. Check ADC token present
echo -n "[2/5] ADC token available... "
if gcloud auth application-default print-access-token &>/dev/null; then
    echo -e "$PASS"
else
    echo -e "$FAIL"
    echo "  Run: gcloud auth application-default login"
    exit 1
fi

# 3. Test BigQuery connectivity to wandb-production
echo -n "[3/5] BigQuery connectivity (wandb-production)... "
if bq query --project_id=wandb-production --use_legacy_sql=false --max_rows=1 "SELECT 1 AS test" &>/dev/null; then
    echo -e "$PASS"
else
    echo -e "$FAIL"
    echo "  Cannot connect to wandb-production BigQuery."
    echo "  Verify you have access: https://console.cloud.google.com/bigquery?project=wandb-production"
    exit 1
fi

# 4. Test analytics dataset access
echo -n "[4/5] analytics dataset access... "
if bq query --project_id=wandb-production --use_legacy_sql=false --max_rows=1 \
    "SELECT COUNT(*) AS cnt FROM \`wandb-production.analytics.stg_salesforce_accounts\` LIMIT 1" &>/dev/null; then
    echo -e "$PASS"
else
    echo -e "$FAIL"
    echo "  Cannot access wandb-production.analytics.stg_salesforce_accounts"
    echo "  Request analytics dataset access from the data team."
    exit 1
fi

# 5. Test landing_development dataset access (non-fatal)
echo -n "[5/5] landing_development dataset access... "
if bq query --project_id=wandb-production --use_legacy_sql=false --max_rows=1 \
    "SELECT COUNT(*) AS cnt FROM \`wandb-production.landing_development.renewal_predictions\` LIMIT 1" &>/dev/null; then
    echo -e "$PASS"
else
    echo -e "$WARN (non-fatal)"
    echo "  Cannot access wandb-production.landing_development.renewal_predictions"
    echo "  Churn probability data will be unavailable. Other metrics still work."
    echo "  Request landing_development access from the data team if churn data is needed."
fi

echo ""
echo "=== Verification Complete ==="
echo "BigQuery is ready for use. Run: uv run --project .claude/skills/bigquery python .claude/skills/bigquery/scripts/usage.py --customer <name>"
