#!/usr/bin/env python3
"""
BigQuery account metadata -- fetch account health data for a customer.

Lighter-weight alternative to usage.py when only account health data is needed
(renewal date, ARR, CS tier, health status, churn probability).

Usage:
    python account.py --customer <name> [--format json|text]
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

# Add scripts directory to path for sibling imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from bq_client import get_client, run_query, get_sfdc_account_id
from queries import account_health_query


def main():
    """CLI entry point for account metadata lookup."""
    parser = argparse.ArgumentParser(
        description="Fetch account health metadata from BigQuery"
    )
    parser.add_argument(
        "--customer", required=True, help="Customer name (matched against customers.yaml)"
    )
    parser.add_argument(
        "--format", choices=["json", "text"], default="json",
        help="Output format (default: json)"
    )
    args = parser.parse_args()

    try:
        # Look up SFDC account ID
        account_id = get_sfdc_account_id(args.customer)

        # Create BigQuery client and run query
        client = get_client()
        account_df = run_query(client, account_health_query(), account_id=account_id)

        if account_df.empty:
            result = {"available": False, "reason": "no_data"}
        else:
            row = account_df.iloc[0]

            def _val(key, convert=None):
                v = row.get(key)
                if pd.isna(v) if isinstance(v, float) else v is None:
                    return None
                if convert:
                    return convert(v)
                return v

            result = {
                "available": True,
                "renewal_date": _val("renewal_date", lambda v: str(v)[:10] if v else None),
                "arr": _val("arr", float),
                "cs_tier": _val("cs_tier", str),
                "customer_health": _val("customer_health", str),
                "churn_probability_3mo": _val("churn_probability_3mo", float),
                "churn_probability_5mo": _val("churn_probability_5mo", float),
                "subscription_plan": _val("subscription_plan", str),
                "deployment_type": _val("deployment_type", str),
            }

    except ValueError as e:
        result = {"available": False, "reason": "config_error", "detail": str(e)}
    except Exception as e:
        result = {"available": False, "reason": "api_error", "detail": str(e)}

    # Output
    if args.format == "json":
        print(json.dumps(result, indent=2, default=str))
    else:
        if result.get("available"):
            print(f"Account health for {args.customer}:")
            print(f"  Renewal: {result.get('renewal_date', 'N/A')}")
            print(f"  ARR: ${result.get('arr', 0):,.0f}" if result.get('arr') else "  ARR: N/A")
            print(f"  CS Tier: {result.get('cs_tier', 'N/A')}")
            print(f"  Health: {result.get('customer_health', 'N/A')}")
            print(f"  Churn: {result.get('churn_probability_3mo', 'N/A')} (3mo) / {result.get('churn_probability_5mo', 'N/A')} (5mo)")
            print(f"  Plan: {result.get('subscription_plan', 'N/A')}")
            print(f"  Deployment: {result.get('deployment_type', 'N/A')}")
        else:
            print(f"No account data: {result.get('reason', 'unknown')}")
            if result.get("detail"):
                print(f"  Detail: {result['detail']}")


if __name__ == "__main__":
    main()
