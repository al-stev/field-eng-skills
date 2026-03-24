#!/usr/bin/env python3
"""
BigQuery client with Application Default Credentials (ADC) auth.

Provides get_client() for authenticated BigQuery access and run_query() for
parameterized query execution. Auth uses ADC via `gcloud auth application-default login`
-- no stored secrets needed.

Cherry-picked from apac-account-management/adapters/bq_adapter.py, adapted for
per-customer parameterized queries (replacing AISE name filters).
"""

import os
import re
from pathlib import Path
from typing import Optional

import yaml
from google.cloud import bigquery
import pandas as pd


# Data lives in wandb-production, but jobs run in the sandbox (user may not have
# serviceusage.serviceUsageConsumer on wandb-production itself)
DATA_PROJECT = "wandb-production"
JOB_PROJECT = "wandb-sa-sandbox"

# Default path to customer registry (4 levels up from scripts/ to project root)
# scripts/ -> bigquery/ -> skills/ -> .claude/ -> project root
DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parents[4] / "templates" / "customers.yaml"


def get_client(project_id: str = JOB_PROJECT) -> bigquery.Client:
    """
    Create an authenticated BigQuery client using ADC.

    Jobs run in the sandbox project (where user has serviceUsageConsumer).
    Queries reference wandb-production datasets via fully-qualified table names.

    Args:
        project_id: GCP project ID for running jobs (default: wandb-sa-sandbox)

    Returns:
        bigquery.Client configured for the project
    """
    os.environ.setdefault("GOOGLE_CLOUD_QUOTA_PROJECT", project_id)
    return bigquery.Client(project=project_id)


def run_query(
    client: bigquery.Client,
    query: str,
    account_id: Optional[str] = None,
) -> pd.DataFrame:
    """
    Execute a BigQuery query, optionally with account_id parameter.

    When account_id is provided, builds a QueryJobConfig with a
    ScalarQueryParameter for safe parameterized filtering.

    Args:
        client: Authenticated BigQuery client
        query: SQL query string (may contain @account_id placeholder)
        account_id: Optional SFDC account ID for parameterized filtering

    Returns:
        Query results as a pandas DataFrame
    """
    if account_id is not None:
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("account_id", "STRING", account_id)
            ]
        )
        return client.query(query, job_config=job_config).to_dataframe()
    else:
        return client.query(query).to_dataframe()


def get_sfdc_account_id(
    customer_name: str,
    registry_path: Optional[Path] = None,
) -> str:
    """
    Look up the SFDC account ID for a customer from the registry.

    Matches customer name case-insensitively, ignoring hyphens and spaces.

    Args:
        customer_name: Customer display name (e.g., "GResearch", "g-research")
        registry_path: Path to customers.yaml (default: templates/customers.yaml)

    Returns:
        18-character Salesforce Account ID

    Raises:
        ValueError: If customer not found or sfdc_account_id is PLACEHOLDER
    """
    path = registry_path or DEFAULT_REGISTRY_PATH

    with open(path) as f:
        data = yaml.safe_load(f)

    def normalize(name: str) -> str:
        """Normalize name for matching: lowercase, strip hyphens and spaces."""
        return re.sub(r"[-\s]", "", name.lower())

    target = normalize(customer_name)

    for customer in data.get("customers", []):
        if normalize(customer.get("name", "")) == target:
            sfdc_id = customer.get("sfdc_account_id", "")
            if not sfdc_id or sfdc_id == "PLACEHOLDER":
                raise ValueError(
                    f"Customer '{customer['name']}' has sfdc_account_id=PLACEHOLDER. "
                    f"Look up the 18-char Salesforce Account ID and update "
                    f"templates/customers.yaml."
                )
            return sfdc_id

    raise ValueError(
        f"Customer '{customer_name}' not found in {path}. "
        f"Add the customer to templates/customers.yaml first."
    )
