"""Tests for bq_client.py -- BigQuery client with ADC auth and parameterized queries."""

import io
import os
import sys
from unittest.mock import patch, MagicMock

import pandas as pd
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
        mock_job.total_bytes_processed = 0
        mock_job.total_bytes_billed = 0
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
        mock_job.total_bytes_processed = 0
        mock_job.total_bytes_billed = 0
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


class TestRunQueryCostGuardrails:
    """Tests for run_query() cost guardrail parameters (maximum_bytes_billed, dry_run, bytes logging)."""

    def _make_mock_client(self, bytes_processed=0, bytes_billed=0):
        """Helper: create a mock BQ client with configurable job stats."""
        mock_client = MagicMock()
        mock_job = MagicMock()
        mock_job.total_bytes_processed = bytes_processed
        mock_job.total_bytes_billed = bytes_billed
        mock_job.to_dataframe.return_value = pd.DataFrame({"col": [1, 2, 3]})
        mock_client.query.return_value = mock_job
        return mock_client

    def test_run_query_default_args_returns_dataframe(self):
        """Test 1: run_query() with default args still returns a DataFrame (backwards compat)."""
        mock_client = self._make_mock_client()

        result = run_query(mock_client, "SELECT 1")

        assert isinstance(result, pd.DataFrame)
        mock_client.query.assert_called_once()
        # Verify no maximum_bytes_billed when param is None
        call_args = mock_client.query.call_args
        job_config = call_args[1].get("job_config")
        assert job_config is not None  # Always creates config now
        assert job_config.maximum_bytes_billed is None

    @patch("bq_client.bigquery.QueryJobConfig")
    def test_run_query_with_maximum_bytes_billed(self, mock_config_cls):
        """Test 2: run_query() with maximum_bytes_billed=1_000_000_000 passes it to QueryJobConfig."""
        mock_config = MagicMock()
        mock_config_cls.return_value = mock_config
        mock_client = self._make_mock_client()

        run_query(mock_client, "SELECT 1", maximum_bytes_billed=1_000_000_000)

        # Verify maximum_bytes_billed was set on the config
        assert mock_config.maximum_bytes_billed == 1_000_000_000

    def test_run_query_dry_run_returns_empty_dataframe(self):
        """Test 3: run_query() with dry_run=True returns empty DataFrame."""
        mock_client = MagicMock()
        mock_job = MagicMock()
        mock_client.query.return_value = mock_job

        result = run_query(mock_client, "SELECT 1", dry_run=True)

        assert isinstance(result, pd.DataFrame)
        assert result.empty
        # to_dataframe should NOT be called for dry run
        mock_job.to_dataframe.assert_not_called()
        # Verify dry_run was set on config
        call_args = mock_client.query.call_args
        job_config = call_args[1].get("job_config")
        assert job_config.dry_run is True

    @patch("bq_client.bigquery.QueryJobConfig")
    @patch("bq_client.bigquery.ScalarQueryParameter")
    def test_run_query_account_id_and_bytes_billed_on_same_config(self, mock_param, mock_config_cls):
        """Test 4: run_query() with account_id sets ScalarQueryParameter AND maximum_bytes_billed on same config."""
        mock_config = MagicMock()
        mock_config_cls.return_value = mock_config
        mock_client = self._make_mock_client()

        run_query(mock_client, "SELECT 1", account_id="001ABC", maximum_bytes_billed=1_000_000_000)

        # Both should be set on the same config object
        assert mock_config.maximum_bytes_billed == 1_000_000_000
        mock_param.assert_called_once_with("account_id", "STRING", "001ABC")
        assert mock_config.query_parameters is not None

    def test_run_query_logs_warning_when_bytes_over_threshold(self):
        """Test 5: run_query() logs warning to stderr when bytes_processed > 500_000_000."""
        mock_client = self._make_mock_client(
            bytes_processed=600_000_000,
            bytes_billed=500_000_000,
        )

        captured = io.StringIO()
        with patch("sys.stderr", captured):
            run_query(mock_client, "SELECT 1")

        output = captured.getvalue()
        assert "[BQ COST]" in output
        assert "0.60 GB processed" in output

    def test_run_query_no_warning_when_bytes_under_threshold(self):
        """Test 6: run_query() does NOT log cost warning when bytes_processed < 500_000_000."""
        mock_client = self._make_mock_client(
            bytes_processed=100_000_000,
            bytes_billed=100_000_000,
        )

        captured = io.StringIO()
        with patch("sys.stderr", captured):
            run_query(mock_client, "SELECT 1")

        output = captured.getvalue()
        assert "[BQ COST]" not in output
        # But should still have the info-level log
        assert "[BQ]" in output
