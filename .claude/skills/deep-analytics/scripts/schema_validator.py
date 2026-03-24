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
