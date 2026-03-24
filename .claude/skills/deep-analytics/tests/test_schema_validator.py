"""Tests for schema_validator.py -- BigQuery table schema validation via dry-run."""

import pytest
from unittest.mock import MagicMock, patch


class TestValidateTableSchema:
    """Test validate_table_schema() dry-run schema validation."""

    def _make_schema_field(self, name: str) -> MagicMock:
        """Create a mock SchemaField with a .name attribute."""
        field = MagicMock()
        field.name = name
        return field

    def _make_mock_job(self, column_names: list[str], bytes_processed: int = 1000) -> MagicMock:
        """Create a mock dry-run job with schema fields."""
        job = MagicMock()
        job.schema = [self._make_schema_field(name) for name in column_names]
        job.total_bytes_processed = bytes_processed
        return job

    def test_valid_schema_all_columns_present(self, mock_bq_client):
        """Test 1: All required columns present returns valid=True, missing=[]."""
        from schema_validator import validate_table_schema

        mock_job = self._make_mock_job(["user_id", "email", "created_at", "status"])
        mock_bq_client.query.return_value = mock_job

        result = validate_table_schema(
            mock_bq_client,
            "`wandb-production.analytics.dim_users`",
            ["user_id", "email"],
        )

        assert result["valid"] is True
        assert result["missing"] == []
        assert "bytes_estimate" in result

    def test_partial_columns_returns_missing(self, mock_bq_client):
        """Test 2: Partial columns returns valid=False with missing list."""
        from schema_validator import validate_table_schema

        mock_job = self._make_mock_job(["user_id", "created_at"])
        mock_bq_client.query.return_value = mock_job

        result = validate_table_schema(
            mock_bq_client,
            "`wandb-production.analytics.dim_users`",
            ["user_id", "email", "missing_col"],
        )

        assert result["valid"] is False
        assert "email" in result["missing"]
        assert "missing_col" in result["missing"]

    def test_exception_returns_error(self, mock_bq_client):
        """Test 3: Exception during dry-run returns valid=False with error message."""
        from schema_validator import validate_table_schema

        mock_bq_client.query.side_effect = Exception("Table not found: xyz")

        result = validate_table_schema(
            mock_bq_client,
            "`wandb-production.analytics.nonexistent`",
            ["col_a", "col_b"],
        )

        assert result["valid"] is False
        assert "Table not found" in result["error"]

    def test_missing_columns_sorted(self, mock_bq_client):
        """Test 4: Missing columns are returned sorted alphabetically."""
        from schema_validator import validate_table_schema

        mock_job = self._make_mock_job(["id"])
        mock_bq_client.query.return_value = mock_job

        result = validate_table_schema(
            mock_bq_client,
            "`wandb-production.analytics.dim_users`",
            ["zebra", "alpha", "middle"],
        )

        assert result["missing"] == ["alpha", "middle", "zebra"]

    def test_bytes_estimate_in_result(self, mock_bq_client):
        """Test 5: bytes_estimate is included in successful result."""
        from schema_validator import validate_table_schema

        mock_job = self._make_mock_job(["col_a"], bytes_processed=42000)
        mock_bq_client.query.return_value = mock_job

        result = validate_table_schema(
            mock_bq_client,
            "`wandb-production.analytics.dim_users`",
            ["col_a"],
        )

        assert result["bytes_estimate"] == 42000
