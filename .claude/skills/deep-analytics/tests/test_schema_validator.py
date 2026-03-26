"""Tests for schema_validator.py -- BigQuery table schema validation via dry-run."""

import pytest
from unittest.mock import MagicMock, patch, call


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


class TestPhase3SchemaSpecs:
    """Verify PHASE3_SCHEMA_SPECS dict has correct structure and table coverage."""

    def test_has_exactly_5_entries(self):
        """PHASE3_SCHEMA_SPECS has exactly 5 table entries."""
        from schema_validator import PHASE3_SCHEMA_SPECS

        assert len(PHASE3_SCHEMA_SPECS) == 5

    def test_contains_retention_features_table(self):
        """PHASE3_SCHEMA_SPECS includes agg_weekly_user_retention_features."""
        from schema_validator import PHASE3_SCHEMA_SPECS

        key = "`wandb-production.analytics.agg_weekly_user_retention_features`"
        assert key in PHASE3_SCHEMA_SPECS
        assert "universal_user_id" in PHASE3_SCHEMA_SPECS[key]
        assert "recency" in PHASE3_SCHEMA_SPECS[key]

    def test_contains_daily_event_usage_table(self):
        """PHASE3_SCHEMA_SPECS includes ext_daily_user_event_usage with team fields."""
        from schema_validator import PHASE3_SCHEMA_SPECS

        key = "`wandb-production.analytics.ext_daily_user_event_usage`"
        assert key in PHASE3_SCHEMA_SPECS
        assert "org_name" in PHASE3_SCHEMA_SPECS[key]
        assert "is_part_of_team" in PHASE3_SCHEMA_SPECS[key]

    def test_contains_renewal_predictions_table(self):
        """PHASE3_SCHEMA_SPECS includes renewal_predictions from landing_development."""
        from schema_validator import PHASE3_SCHEMA_SPECS

        key = "`wandb-production.landing_development.renewal_predictions`"
        assert key in PHASE3_SCHEMA_SPECS
        assert "churn_probability" in PHASE3_SCHEMA_SPECS[key]

    def test_contains_user_activity_table(self):
        """PHASE3_SCHEMA_SPECS includes agg_daily_user_activity with accounting fields."""
        from schema_validator import PHASE3_SCHEMA_SPECS

        key = "`wandb-production.analytics.agg_daily_user_activity`"
        assert key in PHASE3_SCHEMA_SPECS
        assert "user_has_any_event_accounting" in PHASE3_SCHEMA_SPECS[key]

    def test_contains_engagement_score_table(self):
        """PHASE3_SCHEMA_SPECS includes agg_daily_customer_engagement_score."""
        from schema_validator import PHASE3_SCHEMA_SPECS

        key = "`wandb-production.analytics.agg_daily_customer_engagement_score`"
        assert key in PHASE3_SCHEMA_SPECS
        assert "customer_engagement_score" in PHASE3_SCHEMA_SPECS[key]


class TestPhase3DataChecks:
    """Verify PHASE3_DATA_CHECKS dict has correct structure and SQL content."""

    def test_has_exactly_5_entries(self):
        """PHASE3_DATA_CHECKS has exactly 5 check entries."""
        from schema_validator import PHASE3_DATA_CHECKS

        assert len(PHASE3_DATA_CHECKS) == 5

    def test_all_checks_contain_account_id_param(self):
        """Every SQL check uses @account_id parameter."""
        from schema_validator import PHASE3_DATA_CHECKS

        for name, sql in PHASE3_DATA_CHECKS.items():
            assert "@account_id" in sql, f"Check '{name}' missing @account_id"

    def test_check_names(self):
        """PHASE3_DATA_CHECKS has the expected check names."""
        from schema_validator import PHASE3_DATA_CHECKS

        expected = {"team_org_names", "team_flags", "retention_features",
                    "renewal_predictions", "engagement_scores"}
        assert set(PHASE3_DATA_CHECKS.keys()) == expected


class TestCheckDataAvailability:
    """Verify check_data_availability() runs count queries and reports results."""

    def _make_mock_result_rows(self, count: int):
        """Create mock query result rows returning a count."""
        row = MagicMock()
        row.__getitem__ = MagicMock(return_value=count)
        return [row]

    def test_available_when_count_positive(self, mock_bq_client):
        """check_data_availability returns available=True when count > 0."""
        from schema_validator import check_data_availability

        mock_job = MagicMock()
        mock_job.result.return_value = self._make_mock_result_rows(5)
        mock_bq_client.query.return_value = mock_job

        result = check_data_availability(
            mock_bq_client,
            "001ABC",
            {"test_check": "SELECT COUNT(*) AS cnt FROM t WHERE account_id = @account_id"},
        )

        assert result["test_check"]["available"] is True
        assert result["test_check"]["count"] == 5
        assert result["test_check"]["error"] is None

    def test_unavailable_when_count_zero(self, mock_bq_client):
        """check_data_availability returns available=False when count == 0."""
        from schema_validator import check_data_availability

        mock_job = MagicMock()
        mock_job.result.return_value = self._make_mock_result_rows(0)
        mock_bq_client.query.return_value = mock_job

        result = check_data_availability(
            mock_bq_client,
            "001ABC",
            {"test_check": "SELECT COUNT(*) AS cnt FROM t WHERE account_id = @account_id"},
        )

        assert result["test_check"]["available"] is False
        assert result["test_check"]["count"] == 0
        assert result["test_check"]["error"] is None

    def test_error_on_exception(self, mock_bq_client):
        """check_data_availability returns available=False with error on exception."""
        from schema_validator import check_data_availability

        mock_bq_client.query.side_effect = Exception("Access Denied: 403")

        result = check_data_availability(
            mock_bq_client,
            "001ABC",
            {"test_check": "SELECT COUNT(*) AS cnt FROM t WHERE account_id = @account_id"},
        )

        assert result["test_check"]["available"] is False
        assert result["test_check"]["count"] == 0
        assert "Access Denied" in result["test_check"]["error"]

    def test_multiple_checks(self, mock_bq_client):
        """check_data_availability handles multiple checks in one call."""
        from schema_validator import check_data_availability

        mock_job_ok = MagicMock()
        mock_job_ok.result.return_value = self._make_mock_result_rows(10)

        mock_job_empty = MagicMock()
        mock_job_empty.result.return_value = self._make_mock_result_rows(0)

        mock_bq_client.query.side_effect = [mock_job_ok, mock_job_empty]

        result = check_data_availability(
            mock_bq_client,
            "001ABC",
            {
                "check_a": "SELECT COUNT(*) AS cnt FROM a WHERE account_id = @account_id",
                "check_b": "SELECT COUNT(*) AS cnt FROM b WHERE account_id = @account_id",
            },
        )

        assert result["check_a"]["available"] is True
        assert result["check_a"]["count"] == 10
        assert result["check_b"]["available"] is False
        assert result["check_b"]["count"] == 0


class TestPhase4SchemaSpecs:
    """Verify PHASE4_SCHEMA_SPECS dict has correct structure and table coverage."""

    def test_has_exactly_3_entries(self):
        """PHASE4_SCHEMA_SPECS has exactly 3 table entries."""
        from schema_validator import PHASE4_SCHEMA_SPECS

        assert len(PHASE4_SCHEMA_SPECS) == 3

    def test_contains_fct_application_performance(self):
        """PHASE4_SCHEMA_SPECS includes fct_application_performance with required columns."""
        from schema_validator import PHASE4_SCHEMA_SPECS

        key = "`wandb-production.analytics.fct_application_performance`"
        assert key in PHASE4_SCHEMA_SPECS
        cols = PHASE4_SCHEMA_SPECS[key]
        assert "account_id" in cols
        assert "date_day" in cols
        assert "application_performance_index" in cols
        assert "slow_charts" in cols
        assert "users_facing_errors_ct" in cols
        assert "error_count" in cols

    def test_contains_fct_onscreen_loader_latencies(self):
        """PHASE4_SCHEMA_SPECS includes fct_onscreen_loader_latencies with required columns."""
        from schema_validator import PHASE4_SCHEMA_SPECS

        key = "`wandb-production.analytics.fct_onscreen_loader_latencies`"
        assert key in PHASE4_SCHEMA_SPECS
        cols = PHASE4_SCHEMA_SPECS[key]
        assert "account_id" in cols
        assert "date_day" in cols
        assert "latency_ms" in cols

    def test_contains_agg_daily_team_members_slow_chart_loads(self):
        """PHASE4_SCHEMA_SPECS includes agg_daily_team_members_slow_chart_loads."""
        from schema_validator import PHASE4_SCHEMA_SPECS

        key = "`wandb-production.analytics.agg_daily_team_members_slow_chart_loads`"
        assert key in PHASE4_SCHEMA_SPECS
        cols = PHASE4_SCHEMA_SPECS[key]
        assert "account_id" in cols
        assert "date_day" in cols
        assert "universal_user_id" in cols
        assert "slow_chart_loads" in cols
        assert "total_chart_loads" in cols


class TestPhase4DataChecks:
    """Verify PHASE4_DATA_CHECKS dict has correct structure and SQL content."""

    def test_has_exactly_3_entries(self):
        """PHASE4_DATA_CHECKS has exactly 3 check entries."""
        from schema_validator import PHASE4_DATA_CHECKS

        assert len(PHASE4_DATA_CHECKS) == 3

    def test_check_names(self):
        """PHASE4_DATA_CHECKS has the expected check names."""
        from schema_validator import PHASE4_DATA_CHECKS

        expected = {"perf_index", "latency_data", "slow_chart_data"}
        assert set(PHASE4_DATA_CHECKS.keys()) == expected

    def test_all_checks_contain_account_id_param(self):
        """Every SQL check uses @account_id parameter."""
        from schema_validator import PHASE4_DATA_CHECKS

        for name, sql in PHASE4_DATA_CHECKS.items():
            assert "@account_id" in sql, f"Check '{name}' missing @account_id"

    def test_all_checks_contain_count_and_limit(self):
        """Every SQL check contains COUNT and LIMIT 1."""
        from schema_validator import PHASE4_DATA_CHECKS

        for name, sql in PHASE4_DATA_CHECKS.items():
            assert "COUNT" in sql, f"Check '{name}' missing COUNT"
            assert "LIMIT 1" in sql, f"Check '{name}' missing LIMIT 1"

    def test_perf_index_references_correct_table(self):
        """perf_index check references fct_application_performance and filters 90 days."""
        from schema_validator import PHASE4_DATA_CHECKS

        sql = PHASE4_DATA_CHECKS["perf_index"]
        assert "fct_application_performance" in sql
        assert "90 DAY" in sql

    def test_latency_data_references_correct_table(self):
        """latency_data check references fct_onscreen_loader_latencies and filters 30 days."""
        from schema_validator import PHASE4_DATA_CHECKS

        sql = PHASE4_DATA_CHECKS["latency_data"]
        assert "fct_onscreen_loader_latencies" in sql
        assert "30 DAY" in sql

    def test_slow_chart_data_references_correct_table(self):
        """slow_chart_data check references agg_daily_team_members_slow_chart_loads and filters 30 days."""
        from schema_validator import PHASE4_DATA_CHECKS

        sql = PHASE4_DATA_CHECKS["slow_chart_data"]
        assert "agg_daily_team_members_slow_chart_loads" in sql
        assert "30 DAY" in sql
