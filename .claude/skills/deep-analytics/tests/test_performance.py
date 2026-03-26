"""Tests for PerformanceTransform."""

import pandas as pd
import numpy as np
import pytest
from datetime import date, timedelta


from transforms.performance import PerformanceTransform


@pytest.fixture
def transform():
    return PerformanceTransform()


@pytest.fixture
def perf_df():
    """90 rows (one per day) of synthetic performance data."""
    dates = [date.today() - timedelta(days=i) for i in range(89, -1, -1)]
    np.random.seed(42)
    return pd.DataFrame({
        "date_day": dates,
        "application_performance_index": np.random.normal(70, 5, 90).clip(0, 100),
        "slow_charts": np.random.randint(10, 50, 90),
        "slow_project_search": np.random.randint(5, 20, 90),
        "slow_artifact_creating": np.random.randint(2, 15, 90),
        "slow_run_sidebar": np.random.randint(1, 10, 90),
        "slow_workspace_settings": np.random.randint(0, 5, 90),
        "users_facing_errors_ct": np.random.randint(5, 20, 90),
        "error_count": np.random.randint(20, 100, 90),
    })


@pytest.fixture
def latency_df():
    """500 rows with synthetic latency_ms values centered around 1500ms."""
    np.random.seed(42)
    latencies = np.random.exponential(1500, 500).clip(100, 30000)
    return pd.DataFrame({
        "latency_ms": latencies,
        "universal_user_id": [f"uid-{i % 50}" for i in range(500)],
    })


@pytest.fixture
def slow_users_df():
    """10 rows with synthetic usernames and slow_pct values."""
    return pd.DataFrame({
        "universal_user_id": [f"uid-{i}" for i in range(10)],
        "username": [f"user{i}" for i in range(10)],
        "slow_loads": [50, 40, 35, 30, 25, 20, 15, 10, 5, 2],
        "total_loads": [100, 80, 100, 120, 50, 100, 150, 200, 100, 100],
        "slow_pct": [50.0, 50.0, 35.0, 25.0, 50.0, 20.0, 10.0, 5.0, 5.0, 2.0],
        "last_seen": [date.today() - timedelta(days=i) for i in range(10)],
    })


class TestPerformanceTransformEmptyInput:
    """Test transform with empty perf_df returns empty_result."""

    def test_empty_perf_df_returns_unavailable(self, transform):
        empty_df = pd.DataFrame(columns=[
            "date_day", "application_performance_index",
            "slow_charts", "slow_project_search", "slow_artifact_creating",
            "slow_run_sidebar", "slow_workspace_settings",
            "users_facing_errors_ct", "error_count",
        ])
        result = transform.transform(
            perf_df=empty_df,
            latency_df=pd.DataFrame(),
            slow_users_df=pd.DataFrame(),
            customer_name="TestCorp",
            deployment_type="SaaS",
        )
        assert result["available"] is False
        assert result["reason"] == "performance_data_unavailable"


class TestDescopedState:
    """Test descoped_result returns correct shape."""

    def test_descoped_result_performance_descoped(self, transform):
        result = transform.descoped_result("performance_descoped")
        assert result["available"] is False
        assert result["reason"] == "performance_descoped"
        assert result["page_type"] == "performance"

    def test_descoped_result_schema_error(self, transform):
        result = transform.descoped_result("schema_error")
        assert result["available"] is False
        assert result["reason"] == "schema_error"

    def test_descoped_result_has_kpis_with_dashes(self, transform):
        result = transform.descoped_result("performance_descoped")
        kpis = result["kpis"]
        assert len(kpis) == 4
        for kpi in kpis:
            assert kpi["value"] == "--"

    def test_descoped_result_kpi_labels(self, transform):
        result = transform.descoped_result("performance_descoped")
        labels = [k["label"] for k in result["kpis"]]
        assert labels == ["Performance Index", "Error Count (30d)", "P95 Chart Load", "Slow Chart Users"]


class TestTransformFullOutput:
    """Test transform with valid data returns all expected keys."""

    def test_returns_available_true(self, transform, perf_df, latency_df, slow_users_df):
        result = transform.transform(
            perf_df=perf_df, latency_df=latency_df, slow_users_df=slow_users_df,
            customer_name="TestCorp", deployment_type="SaaS",
        )
        assert result["available"] is True

    def test_returns_all_expected_keys(self, transform, perf_df, latency_df, slow_users_df):
        result = transform.transform(
            perf_df=perf_df, latency_df=latency_df, slow_users_df=slow_users_df,
            customer_name="TestCorp", deployment_type="SaaS",
        )
        expected_keys = {
            "available", "reason", "page_type", "customer", "generated",
            "performance_index", "slowness_breakdown", "error_metrics",
            "latency_distribution", "slow_chart_users", "narrative", "kpis",
            "data_source", "deployment_type",
        }
        assert expected_keys.issubset(result.keys()), f"Missing keys: {expected_keys - result.keys()}"

    def test_page_type_is_performance(self, transform, perf_df, latency_df, slow_users_df):
        result = transform.transform(
            perf_df=perf_df, latency_df=latency_df, slow_users_df=slow_users_df,
            customer_name="TestCorp", deployment_type="SaaS",
        )
        assert result["page_type"] == "performance"


class TestPerformanceIndexTiers:
    """Test tier classification: good >= 80, fair >= 50, poor < 50."""

    def _make_perf_df(self, index_value):
        """Create a perf_df with constant performance index."""
        dates = [date.today() - timedelta(days=i) for i in range(30)]
        return pd.DataFrame({
            "date_day": dates,
            "application_performance_index": [index_value] * 30,
            "slow_charts": [10] * 30,
            "slow_project_search": [5] * 30,
            "slow_artifact_creating": [3] * 30,
            "slow_run_sidebar": [2] * 30,
            "slow_workspace_settings": [1] * 30,
            "users_facing_errors_ct": [5] * 30,
            "error_count": [20] * 30,
        })

    def test_tier_good(self, transform):
        result = transform.transform(
            perf_df=self._make_perf_df(85.0),
            latency_df=pd.DataFrame(), slow_users_df=pd.DataFrame(),
            customer_name="TestCorp", deployment_type="SaaS",
        )
        assert result["performance_index"]["tier"] == "good"

    def test_tier_fair(self, transform):
        result = transform.transform(
            perf_df=self._make_perf_df(65.0),
            latency_df=pd.DataFrame(), slow_users_df=pd.DataFrame(),
            customer_name="TestCorp", deployment_type="SaaS",
        )
        assert result["performance_index"]["tier"] == "fair"

    def test_tier_poor(self, transform):
        result = transform.transform(
            perf_df=self._make_perf_df(30.0),
            latency_df=pd.DataFrame(), slow_users_df=pd.DataFrame(),
            customer_name="TestCorp", deployment_type="SaaS",
        )
        assert result["performance_index"]["tier"] == "poor"

    def test_tier_boundary_80_is_good(self, transform):
        result = transform.transform(
            perf_df=self._make_perf_df(80.0),
            latency_df=pd.DataFrame(), slow_users_df=pd.DataFrame(),
            customer_name="TestCorp", deployment_type="SaaS",
        )
        assert result["performance_index"]["tier"] == "good"

    def test_tier_boundary_50_is_fair(self, transform):
        result = transform.transform(
            perf_df=self._make_perf_df(50.0),
            latency_df=pd.DataFrame(), slow_users_df=pd.DataFrame(),
            customer_name="TestCorp", deployment_type="SaaS",
        )
        assert result["performance_index"]["tier"] == "fair"


class TestLatencyDistribution:
    """Test latency binning with 5 fixed bins and percentiles."""

    def test_latency_bins_five_entries(self, transform, perf_df, latency_df, slow_users_df):
        result = transform.transform(
            perf_df=perf_df, latency_df=latency_df, slow_users_df=slow_users_df,
            customer_name="TestCorp", deployment_type="SaaS",
        )
        bins = result["latency_distribution"]["bins"]
        assert len(bins) == 5

    def test_latency_bin_labels(self, transform, perf_df, latency_df, slow_users_df):
        result = transform.transform(
            perf_df=perf_df, latency_df=latency_df, slow_users_df=slow_users_df,
            customer_name="TestCorp", deployment_type="SaaS",
        )
        labels = [b["label"] for b in result["latency_distribution"]["bins"]]
        assert labels == ["0-1s", "1-2s", "2-5s", "5-10s", "10s+"]

    def test_latency_bins_sum_equals_total(self, transform, perf_df, latency_df, slow_users_df):
        result = transform.transform(
            perf_df=perf_df, latency_df=latency_df, slow_users_df=slow_users_df,
            customer_name="TestCorp", deployment_type="SaaS",
        )
        bins = result["latency_distribution"]["bins"]
        total_count = sum(b["count"] for b in bins)
        assert total_count == len(latency_df)

    def test_latency_percentiles_computed(self, transform, perf_df, latency_df, slow_users_df):
        result = transform.transform(
            perf_df=perf_df, latency_df=latency_df, slow_users_df=slow_users_df,
            customer_name="TestCorp", deployment_type="SaaS",
        )
        dist = result["latency_distribution"]
        assert "p50" in dist
        assert "p95" in dist
        assert "p99" in dist
        # Verify p50 <= p95 <= p99
        assert dist["p50"] <= dist["p95"] <= dist["p99"]

    def test_latency_percentiles_correct(self, transform, perf_df, latency_df, slow_users_df):
        """Verify percentiles match numpy computation."""
        result = transform.transform(
            perf_df=perf_df, latency_df=latency_df, slow_users_df=slow_users_df,
            customer_name="TestCorp", deployment_type="SaaS",
        )
        expected_p50 = round(float(np.percentile(latency_df["latency_ms"], 50)), 1)
        expected_p95 = round(float(np.percentile(latency_df["latency_ms"], 95)), 1)
        expected_p99 = round(float(np.percentile(latency_df["latency_ms"], 99)), 1)
        assert result["latency_distribution"]["p50"] == expected_p50
        assert result["latency_distribution"]["p95"] == expected_p95
        assert result["latency_distribution"]["p99"] == expected_p99

    def test_empty_latency_returns_empty_bins(self, transform, perf_df):
        result = transform.transform(
            perf_df=perf_df, latency_df=pd.DataFrame(), slow_users_df=pd.DataFrame(),
            customer_name="TestCorp", deployment_type="SaaS",
        )
        bins = result["latency_distribution"]["bins"]
        assert len(bins) == 5
        for b in bins:
            assert b["count"] == 0
        assert result["latency_distribution"]["p50"] == "--"
        assert result["latency_distribution"]["p95"] == "--"
        assert result["latency_distribution"]["p99"] == "--"


class TestSlownessBreakdown:
    """Test slowness breakdown sorted by count descending."""

    def test_slowness_sorted_descending(self, transform, perf_df, latency_df, slow_users_df):
        result = transform.transform(
            perf_df=perf_df, latency_df=latency_df, slow_users_df=slow_users_df,
            customer_name="TestCorp", deployment_type="SaaS",
        )
        breakdown = result["slowness_breakdown"]
        counts = [b["count"] for b in breakdown]
        assert counts == sorted(counts, reverse=True)

    def test_slowness_has_five_features(self, transform, perf_df, latency_df, slow_users_df):
        result = transform.transform(
            perf_df=perf_df, latency_df=latency_df, slow_users_df=slow_users_df,
            customer_name="TestCorp", deployment_type="SaaS",
        )
        breakdown = result["slowness_breakdown"]
        assert len(breakdown) == 5

    def test_slowness_feature_names(self, transform, perf_df, latency_df, slow_users_df):
        result = transform.transform(
            perf_df=perf_df, latency_df=latency_df, slow_users_df=slow_users_df,
            customer_name="TestCorp", deployment_type="SaaS",
        )
        names = {b["feature"] for b in result["slowness_breakdown"]}
        expected = {"Slow Charts", "Slow Project Search", "Slow Artifact Creating",
                    "Slow Run Sidebar", "Slow Workspace Settings"}
        assert names == expected


class TestErrorMetrics:
    """Test error metrics trending."""

    def test_error_trend_negative_when_improving(self, transform):
        """Error trend is negative when recent errors < prior errors."""
        dates = [date.today() - timedelta(days=i) for i in range(29, -1, -1)]
        # First 15 days: high errors, last 15 days: low errors
        error_counts = [100] * 15 + [50] * 15
        perf_df = pd.DataFrame({
            "date_day": dates,
            "application_performance_index": [70.0] * 30,
            "slow_charts": [10] * 30,
            "slow_project_search": [5] * 30,
            "slow_artifact_creating": [3] * 30,
            "slow_run_sidebar": [2] * 30,
            "slow_workspace_settings": [1] * 30,
            "users_facing_errors_ct": [5] * 30,
            "error_count": error_counts,
        })
        result = transform.transform(
            perf_df=perf_df, latency_df=pd.DataFrame(), slow_users_df=pd.DataFrame(),
            customer_name="TestCorp", deployment_type="SaaS",
        )
        assert result["error_metrics"]["error_trend"] < 0


class TestSlowChartUsers:
    """Test slow chart users table."""

    def test_slow_users_sorted_by_slow_pct_descending(self, transform, perf_df, latency_df, slow_users_df):
        result = transform.transform(
            perf_df=perf_df, latency_df=latency_df, slow_users_df=slow_users_df,
            customer_name="TestCorp", deployment_type="SaaS",
        )
        users = result["slow_chart_users"]
        pcts = [u["slow_pct"] for u in users]
        assert pcts == sorted(pcts, reverse=True)

    def test_slow_users_have_required_keys(self, transform, perf_df, latency_df, slow_users_df):
        result = transform.transform(
            perf_df=perf_df, latency_df=latency_df, slow_users_df=slow_users_df,
            customer_name="TestCorp", deployment_type="SaaS",
        )
        required_keys = {"username", "slow_loads", "total_loads", "slow_pct", "last_seen"}
        for user in result["slow_chart_users"]:
            assert required_keys.issubset(user.keys()), f"Missing keys: {required_keys - user.keys()}"

    def test_empty_slow_users_returns_empty_list(self, transform, perf_df, latency_df):
        result = transform.transform(
            perf_df=perf_df, latency_df=latency_df, slow_users_df=pd.DataFrame(),
            customer_name="TestCorp", deployment_type="SaaS",
        )
        assert result["slow_chart_users"] == []


class TestNarrative:
    """Test _build_narrative returns correct structure."""

    def test_narrative_has_required_keys(self, transform, perf_df, latency_df, slow_users_df):
        result = transform.transform(
            perf_df=perf_df, latency_df=latency_df, slow_users_df=slow_users_df,
            customer_name="TestCorp", deployment_type="SaaS",
        )
        narrative = result["narrative"]
        assert "executive_summary" in narrative
        assert "highlights" in narrative
        assert "recommendations" in narrative


class TestKPIs:
    """Test KPI generation."""

    def test_kpis_has_four_entries(self, transform, perf_df, latency_df, slow_users_df):
        result = transform.transform(
            perf_df=perf_df, latency_df=latency_df, slow_users_df=slow_users_df,
            customer_name="TestCorp", deployment_type="SaaS",
        )
        assert len(result["kpis"]) == 4

    def test_kpi_labels(self, transform, perf_df, latency_df, slow_users_df):
        result = transform.transform(
            perf_df=perf_df, latency_df=latency_df, slow_users_df=slow_users_df,
            customer_name="TestCorp", deployment_type="SaaS",
        )
        labels = [k["label"] for k in result["kpis"]]
        assert labels == ["Performance Index", "Error Count (30d)", "P95 Chart Load", "Slow Chart Users"]
