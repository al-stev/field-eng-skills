"""Tests for bq_client.py -- BigQuery client with ADC auth and parameterized queries."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

# Add scripts/ to path for imports
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "scripts"))

from bq_client import get_client, run_query, get_sfdc_account_id


class TestGetClient:
    """Tests for get_client() ADC setup."""

    @patch("bq_client.bigquery.Client")
    def test_get_client_sets_quota_project(self, mock_client_cls):
        """get_client('wandb-production') sets GOOGLE_CLOUD_QUOTA_PROJECT env var."""
        # Clear env var if set
        os.environ.pop("GOOGLE_CLOUD_QUOTA_PROJECT", None)

        get_client("wandb-production")

        assert os.environ.get("GOOGLE_CLOUD_QUOTA_PROJECT") == "wandb-production"
        mock_client_cls.assert_called_once_with(project="wandb-production")

    @patch("bq_client.bigquery.Client")
    def test_get_client_returns_client_instance(self, mock_client_cls):
        """get_client() returns the Client instance."""
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance

        result = get_client("wandb-production")

        assert result is mock_instance


class TestRunQuery:
    """Tests for run_query() with parameterized and non-parameterized execution."""

    @patch("bq_client.bigquery")
    def test_run_query_with_account_id(self, mock_bq):
        """run_query with account_id builds QueryJobConfig with ScalarQueryParameter."""
        mock_client = MagicMock()
        mock_job = MagicMock()
        mock_client.query.return_value = mock_job
        mock_job.to_dataframe.return_value = MagicMock()

        run_query(mock_client, "SELECT * FROM t WHERE account_id = @account_id", account_id="001ABC")

        # Verify query was called with a job_config
        call_args = mock_client.query.call_args
        assert call_args is not None
        job_config = call_args[1].get("job_config") or call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("job_config")
        assert job_config is not None

        # Verify ScalarQueryParameter was created
        mock_bq.ScalarQueryParameter.assert_called_once_with("account_id", "STRING", "001ABC")

    @patch("bq_client.bigquery")
    def test_run_query_without_account_id(self, mock_bq):
        """run_query without account_id executes query without parameters."""
        mock_client = MagicMock()
        mock_job = MagicMock()
        mock_client.query.return_value = mock_job
        mock_job.to_dataframe.return_value = MagicMock()

        run_query(mock_client, "SELECT 1")

        mock_client.query.assert_called_once()
        # No ScalarQueryParameter should be created
        mock_bq.ScalarQueryParameter.assert_not_called()


class TestSfdcIdLookup:
    """Tests for get_sfdc_account_id() customer registry lookup."""

    def test_sfdc_id_lookup(self, sample_customers_yaml):
        """get_sfdc_account_id('AcmeCorp') returns configured sfdc_account_id."""
        result = get_sfdc_account_id("AcmeCorp", registry_path=sample_customers_yaml)
        assert result == "001ABC"

    def test_sfdc_id_lookup_case_insensitive(self, sample_customers_yaml):
        """get_sfdc_account_id('acmecorp') matches 'AcmeCorp' case-insensitively."""
        result = get_sfdc_account_id("acmecorp", registry_path=sample_customers_yaml)
        assert result == "001ABC"

    def test_sfdc_id_placeholder_raises(self, sample_customers_yaml):
        """Customer with sfdc_account_id='PLACEHOLDER' raises ValueError."""
        with pytest.raises(ValueError, match="PLACEHOLDER"):
            get_sfdc_account_id("No-BQ-Customer", registry_path=sample_customers_yaml)

    def test_sfdc_id_missing_customer_raises(self, sample_customers_yaml):
        """Unknown customer name raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            get_sfdc_account_id("NonExistentCorp", registry_path=sample_customers_yaml)
