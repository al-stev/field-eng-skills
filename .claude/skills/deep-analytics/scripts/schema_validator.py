#!/usr/bin/env python3
"""
Schema validation utility for BigQuery tables.

Uses dry-run queries (SELECT * FROM table LIMIT 0) instead of INFORMATION_SCHEMA
to avoid cross-project permission issues. The sandbox project (wandb-sa-sandbox)
can query data in wandb-production but may not have bigquery.tables.list permission
needed for INFORMATION_SCHEMA access.
"""

import sys
from pathlib import Path
from typing import Optional

# Add bigquery scripts to path for bq_client import
SKILLS_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILLS_DIR / "bigquery" / "scripts"))

from google.cloud import bigquery


PHASE3_SCHEMA_SPECS = {
    "`wandb-production.analytics.agg_weekly_user_retention_features`": [
        "universal_user_id", "account_id", "study_period",
        "prediction_period", "recency", "frequency", "age",
    ],
    "`wandb-production.analytics.ext_daily_user_event_usage`": [
        "org_name", "is_part_of_team", "count_teams",
        "organization_id", "universal_user_id", "event_count", "date_day",
    ],
    "`wandb-production.landing_development.renewal_predictions`": [
        "account_id", "churn_probability", "horizon", "inference_timestamp",
    ],
    "`wandb-production.analytics.agg_daily_user_activity`": [
        "universal_user_id", "account_id", "date_day",
        "user_run_created_accounting", "user_has_any_event_accounting",
    ],
    "`wandb-production.analytics.agg_daily_customer_engagement_score`": [
        "universal_user_id", "account_id", "date_day",
        "customer_engagement_score",
    ],
}

PHASE3_DATA_CHECKS = {
    "team_org_names": (
        "SELECT COUNT(DISTINCT org_name) AS cnt "
        "FROM `wandb-production.analytics.ext_daily_user_event_usage` "
        "WHERE account_id = @account_id AND org_name IS NOT NULL "
        "AND date_day >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH) LIMIT 1"
    ),
    "team_flags": (
        "SELECT COUNT(DISTINCT universal_user_id) AS cnt "
        "FROM `wandb-production.analytics.ext_daily_user_event_usage` "
        "WHERE account_id = @account_id AND is_part_of_team = TRUE "
        "AND date_day >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH) LIMIT 1"
    ),
    "retention_features": (
        "SELECT COUNT(*) AS cnt "
        "FROM `wandb-production.analytics.agg_weekly_user_retention_features` "
        "WHERE account_id = @account_id LIMIT 1"
    ),
    "renewal_predictions": (
        "SELECT COUNT(*) AS cnt "
        "FROM `wandb-production.landing_development.renewal_predictions` "
        "WHERE account_id = @account_id LIMIT 1"
    ),
    "engagement_scores": (
        "SELECT COUNT(*) AS cnt "
        "FROM `wandb-production.analytics.agg_daily_customer_engagement_score` "
        "WHERE account_id = @account_id "
        "AND date_day >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH) LIMIT 1"
    ),
}


def check_data_availability(
    client: bigquery.Client,
    account_id: str,
    checks: dict[str, str],
) -> dict[str, dict]:
    """
    Check data availability per account after schema validation passes.

    Runs lightweight count queries to verify that data actually exists for a
    given account_id, addressing the pitfall where schema columns exist but
    data is NULL or empty for specific accounts.

    Args:
        client: Authenticated BigQuery client
        account_id: SFDC account ID
        checks: Dict of {check_name: SQL_with_@account_id_returning_count}

    Returns:
        Dict of {check_name: {"available": bool, "count": int, "error": str|None}}
    """
    from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter

    results = {}
    for check_name, sql in checks.items():
        try:
            job_config = QueryJobConfig(
                query_parameters=[
                    ScalarQueryParameter("account_id", "STRING", account_id),
                ],
                maximum_bytes_billed=1_000_000_000,
            )
            query_job = client.query(sql, job_config=job_config)
            rows = list(query_job.result())
            count = rows[0][0] if rows else 0
            results[check_name] = {
                "available": count > 0,
                "count": count,
                "error": None,
            }
        except Exception as e:
            results[check_name] = {
                "available": False,
                "count": 0,
                "error": str(e),
            }
    return results


def validate_table_schema(
    client: bigquery.Client,
    table_ref: str,
    required_columns: list[str],
) -> dict:
    """
    Validate table exists and has required columns using dry-run.

    Args:
        client: Authenticated BigQuery client
        table_ref: Fully-qualified table reference (e.g., `wandb-production.analytics.dim_users`)
        required_columns: List of column names that must exist

    Returns:
        {
            "valid": bool,
            "missing": list[str],  -- sorted list of missing column names
            "available_columns": list[str],  -- sorted list of all columns (on success)
            "bytes_estimate": int,  -- estimated bytes for full scan (on success)
            "error": str  -- error message (on failure)
        }
    """
    query = f"SELECT * FROM {table_ref} LIMIT 0"
    job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    try:
        job = client.query(query, job_config=job_config)
        available_cols = {f.name for f in job.schema}
        missing = sorted(set(required_columns) - available_cols)
        return {
            "valid": len(missing) == 0,
            "missing": missing,
            "available_columns": sorted(available_cols),
            "bytes_estimate": job.total_bytes_processed,
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
            "missing": sorted(required_columns),
        }


def validate_tables(
    client: bigquery.Client,
    table_specs: dict[str, list[str]],
) -> dict[str, dict]:
    """
    Validate multiple tables at once.

    Args:
        client: Authenticated BigQuery client
        table_specs: Dict of {table_ref: [required_columns]}

    Returns:
        Dict of {table_ref: validation_result}
    """
    results = {}
    for table_ref, columns in table_specs.items():
        results[table_ref] = validate_table_schema(client, table_ref, columns)
    return results
