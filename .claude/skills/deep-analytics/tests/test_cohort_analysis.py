"""Tests for CohortAnalysisTransform -- retention heatmap, lifecycle, behavioral cohorts, narrative."""

import pandas as pd
import pytest
from datetime import date


def _make_retention_df():
    """Create a realistic retention DataFrame matching cohort_retention_query() output."""
    # 4 cohorts, each with varying retention over months
    rows = []
    cohorts = ["2025-04", "2025-05", "2025-06", "2025-07"]
    cohort_sizes = [20, 15, 25, 10]

    for i, cohort in enumerate(cohorts):
        base_size = cohort_sizes[i]
        # Each cohort has data for its own month (M+0) plus subsequent months
        for offset in range(12 - i * 2):  # fewer months for later cohorts
            active_month_num = int(cohort.split("-")[1]) + offset
            year = int(cohort.split("-")[0])
            if active_month_num > 12:
                active_month_num -= 12
                year += 1
            active_month = f"{year}-{active_month_num:02d}"
            # Simulate retention decay
            if offset == 0:
                active_users = base_size
            else:
                active_users = max(1, int(base_size * (0.8 ** offset)))
            rows.append({
                "cohort_month": cohort,
                "active_month": active_month,
                "active_users": active_users,
            })

    return pd.DataFrame(rows)


def _make_lifecycle_df():
    """Create a lifecycle DataFrame matching user_lifecycle_query() output."""
    months = ["2025-04", "2025-05", "2025-06", "2025-07", "2025-08", "2025-09"]
    return pd.DataFrame({
        "month": months,
        "new_users": [10, 8, 12, 5, 7, 9],
        "retained": [0, 6, 10, 14, 12, 15],
        "resurrected": [0, 2, 1, 3, 2, 4],
        "churned": [0, 4, 3, 5, 6, 3],
    })


def _make_journey_df():
    """Create a journey DataFrame matching user_journey_query() output."""
    return pd.DataFrame({
        "universal_user_id": [f"user_{i}" for i in range(20)],
        "local_username": [f"user{i}" for i in range(20)],
        "local_user_email": [f"user{i}@test.com" for i in range(20)],
        "first_telemetry_at": pd.to_datetime(["2025-04-01"] * 5 + ["2025-05-01"] * 5 + ["2025-06-01"] * 5 + ["2025-07-01"] * 5),
        "first_run_at": pd.to_datetime(["2025-04-02"] * 10 + [None] * 10),
        "first_sweep_at": pd.to_datetime([None] * 5 + ["2025-05-03"] * 5 + [None] * 10),
        "first_table_created_at": pd.to_datetime([None] * 10 + ["2025-06-04"] * 5 + [None] * 5),
        "first_weave_call_at": pd.to_datetime([None] * 15 + ["2025-07-05"] * 5),
        "first_license_created_at": pd.to_datetime([None] * 20),
    })


class TestCohortAnalysisTransformBasic:
    """Test core transform behavior with valid data."""

    def test_transform_returns_available_true(self):
        """Transform with valid retention data returns available=True."""
        from transforms.cohort_analysis import CohortAnalysisTransform

        transform = CohortAnalysisTransform()
        result = transform.transform(
            retention=_make_retention_df(),
            customer_name="TestCorp",
        )
        assert result["available"] is True

    def test_transform_returns_page_type(self):
        """Transform returns correct page_type."""
        from transforms.cohort_analysis import CohortAnalysisTransform

        transform = CohortAnalysisTransform()
        result = transform.transform(
            retention=_make_retention_df(),
            customer_name="TestCorp",
        )
        assert result["page_type"] == "cohort-analysis"

    def test_transform_returns_all_required_keys(self):
        """Transform output includes all required PAGE_DATA keys."""
        from transforms.cohort_analysis import CohortAnalysisTransform

        transform = CohortAnalysisTransform()
        result = transform.transform(
            retention=_make_retention_df(),
            lifecycle=_make_lifecycle_df(),
            journey=_make_journey_df(),
            customer_name="TestCorp",
        )
        required_keys = {
            "available", "page_type", "customer", "generated", "period",
            "kpis", "cohort_matrix", "retention_curve", "lifecycle",
            "cohort_overlay", "behavioral_cohorts", "narrative", "data_source",
        }
        assert required_keys.issubset(set(result.keys()))

    def test_transform_includes_data_source(self):
        """Transform output includes data_source key for provenance."""
        from transforms.cohort_analysis import CohortAnalysisTransform

        transform = CohortAnalysisTransform()
        result = transform.transform(
            retention=_make_retention_df(),
            customer_name="TestCorp",
            data_source="ext_daily_user_event_usage (activity-based cohorts)",
        )
        assert "data_source" in result
        assert "ext_daily_user_event_usage" in result["data_source"]


class TestCohortMatrix:
    """Test cohort matrix computation."""

    def test_cohort_matrix_keys(self):
        """Cohort matrix has required keys: cohort_labels, cohort_sizes, period_labels, matrix."""
        from transforms.cohort_analysis import CohortAnalysisTransform

        transform = CohortAnalysisTransform()
        result = transform.transform(
            retention=_make_retention_df(),
            customer_name="TestCorp",
        )
        matrix = result["cohort_matrix"]
        assert "cohort_labels" in matrix
        assert "cohort_sizes" in matrix
        assert "period_labels" in matrix
        assert "matrix" in matrix

    def test_cohort_labels_are_strings(self):
        """Cohort labels are list of strings."""
        from transforms.cohort_analysis import CohortAnalysisTransform

        transform = CohortAnalysisTransform()
        result = transform.transform(
            retention=_make_retention_df(),
            customer_name="TestCorp",
        )
        labels = result["cohort_matrix"]["cohort_labels"]
        assert isinstance(labels, list)
        assert all(isinstance(l, str) for l in labels)
        assert len(labels) == 4  # 4 cohorts in test data

    def test_period_labels_format(self):
        """Period labels are M+N format strings."""
        from transforms.cohort_analysis import CohortAnalysisTransform

        transform = CohortAnalysisTransform()
        result = transform.transform(
            retention=_make_retention_df(),
            customer_name="TestCorp",
        )
        period_labels = result["cohort_matrix"]["period_labels"]
        assert isinstance(period_labels, list)
        assert period_labels[0] == "M+0"
        assert all(l.startswith("M+") for l in period_labels)

    def test_matrix_format(self):
        """Matrix is list of [cohortIdx, periodIdx, retentionPct]."""
        from transforms.cohort_analysis import CohortAnalysisTransform

        transform = CohortAnalysisTransform()
        result = transform.transform(
            retention=_make_retention_df(),
            customer_name="TestCorp",
        )
        matrix = result["cohort_matrix"]["matrix"]
        assert isinstance(matrix, list)
        assert len(matrix) > 0
        # Each entry is [cohortIdx, periodIdx, retentionPct]
        for entry in matrix:
            assert len(entry) == 3
            assert isinstance(entry[0], int)
            assert isinstance(entry[1], int)
            assert isinstance(entry[2], float)

    def test_retention_capped_at_100(self):
        """Retention percentages are capped at 100.0 (safety clamp per research pitfall 3)."""
        from transforms.cohort_analysis import CohortAnalysisTransform

        # Create data where active_users exceeds cohort size (data anomaly)
        df = pd.DataFrame({
            "cohort_month": ["2025-04", "2025-04", "2025-04"],
            "active_month": ["2025-04", "2025-05", "2025-06"],
            "active_users": [10, 15, 5],  # M+1 has 15 users > 10 cohort size
        })

        transform = CohortAnalysisTransform()
        result = transform.transform(retention=df, customer_name="TestCorp")
        matrix = result["cohort_matrix"]["matrix"]
        for entry in matrix:
            assert entry[2] <= 100.0

    def test_cohort_sizes_dict(self):
        """Cohort sizes is dict mapping cohort label to size."""
        from transforms.cohort_analysis import CohortAnalysisTransform

        transform = CohortAnalysisTransform()
        result = transform.transform(
            retention=_make_retention_df(),
            customer_name="TestCorp",
        )
        sizes = result["cohort_matrix"]["cohort_sizes"]
        assert isinstance(sizes, dict)
        assert len(sizes) == 4
        # M+0 values should match the base sizes
        assert sizes["2025-04"] == 20
        assert sizes["2025-05"] == 15


class TestRetentionCurve:
    """Test overall retention curve computation."""

    def test_retention_curve_structure(self):
        """Retention curve has periods and values."""
        from transforms.cohort_analysis import CohortAnalysisTransform

        transform = CohortAnalysisTransform()
        result = transform.transform(
            retention=_make_retention_df(),
            customer_name="TestCorp",
        )
        curve = result["retention_curve"]
        assert "periods" in curve
        assert "values" in curve
        assert curve["periods"] == ["1 Month", "3 Months", "6 Months", "12 Months"]
        assert isinstance(curve["values"], list)
        assert len(curve["values"]) == 4


class TestLifecycle:
    """Test lifecycle stacked area data."""

    def test_lifecycle_with_lifecycle_df(self):
        """Lifecycle data returned when lifecycle DataFrame is provided."""
        from transforms.cohort_analysis import CohortAnalysisTransform

        transform = CohortAnalysisTransform()
        result = transform.transform(
            retention=_make_retention_df(),
            lifecycle=_make_lifecycle_df(),
            customer_name="TestCorp",
        )
        lc = result["lifecycle"]
        assert "months" in lc
        assert "new_users" in lc
        assert "retained" in lc
        assert "resurrected" in lc
        assert "churned" in lc
        assert len(lc["months"]) == 6

    def test_lifecycle_without_lifecycle_df(self):
        """Lifecycle returns empty lists when no lifecycle DataFrame provided."""
        from transforms.cohort_analysis import CohortAnalysisTransform

        transform = CohortAnalysisTransform()
        result = transform.transform(
            retention=_make_retention_df(),
            customer_name="TestCorp",
        )
        lc = result["lifecycle"]
        assert "months" in lc
        # Should have empty or computed-from-retention data
        assert isinstance(lc["months"], list)


class TestCohortOverlay:
    """Test cohort overlay (last 4 cohorts comparison)."""

    def test_cohort_overlay_structure(self):
        """Cohort overlay has periods and cohorts list."""
        from transforms.cohort_analysis import CohortAnalysisTransform

        transform = CohortAnalysisTransform()
        result = transform.transform(
            retention=_make_retention_df(),
            customer_name="TestCorp",
        )
        overlay = result["cohort_overlay"]
        assert "periods" in overlay
        assert "cohorts" in overlay
        assert isinstance(overlay["cohorts"], list)
        # Last 4 cohorts (we have exactly 4 in test data)
        assert len(overlay["cohorts"]) <= 4

    def test_cohort_overlay_entries(self):
        """Each cohort in overlay has label and values."""
        from transforms.cohort_analysis import CohortAnalysisTransform

        transform = CohortAnalysisTransform()
        result = transform.transform(
            retention=_make_retention_df(),
            customer_name="TestCorp",
        )
        for cohort in result["cohort_overlay"]["cohorts"]:
            assert "label" in cohort
            assert "values" in cohort
            assert isinstance(cohort["values"], list)


class TestBehavioralCohorts:
    """Test behavioral cohort computation."""

    def test_behavioral_cohorts_with_journey_data(self):
        """Behavioral cohorts computed from journey DataFrame."""
        from transforms.cohort_analysis import CohortAnalysisTransform

        transform = CohortAnalysisTransform()
        result = transform.transform(
            retention=_make_retention_df(),
            journey=_make_journey_df(),
            customer_name="TestCorp",
        )
        bc = result["behavioral_cohorts"]
        assert "periods" in bc
        assert "groups" in bc
        assert isinstance(bc["groups"], list)

    def test_behavioral_cohorts_without_journey_data(self):
        """Behavioral cohorts empty when no journey data."""
        from transforms.cohort_analysis import CohortAnalysisTransform

        transform = CohortAnalysisTransform()
        result = transform.transform(
            retention=_make_retention_df(),
            customer_name="TestCorp",
        )
        bc = result["behavioral_cohorts"]
        assert "groups" in bc
        assert len(bc["groups"]) == 0

    def test_behavioral_cohort_group_structure(self):
        """Each behavioral group has first_action and values."""
        from transforms.cohort_analysis import CohortAnalysisTransform

        transform = CohortAnalysisTransform()
        result = transform.transform(
            retention=_make_retention_df(),
            journey=_make_journey_df(),
            customer_name="TestCorp",
        )
        for group in result["behavioral_cohorts"]["groups"]:
            assert "first_action" in group
            assert "values" in group


class TestKPIs:
    """Test KPI generation."""

    def test_kpis_count(self):
        """KPIs list has exactly 4 entries."""
        from transforms.cohort_analysis import CohortAnalysisTransform

        transform = CohortAnalysisTransform()
        result = transform.transform(
            retention=_make_retention_df(),
            customer_name="TestCorp",
        )
        assert len(result["kpis"]) == 4

    def test_kpi_labels(self):
        """KPIs have correct labels."""
        from transforms.cohort_analysis import CohortAnalysisTransform

        transform = CohortAnalysisTransform()
        result = transform.transform(
            retention=_make_retention_df(),
            customer_name="TestCorp",
        )
        labels = [kpi["label"] for kpi in result["kpis"]]
        assert "Total Cohorts" in labels
        assert "3-Month Retention" in labels
        assert "6-Month Retention" in labels
        assert "Active Users (Current)" in labels


class TestNarrative:
    """Test AI narrative generation."""

    def test_narrative_structure(self):
        """Narrative has executive_summary, highlights, recommendations."""
        from transforms.cohort_analysis import CohortAnalysisTransform

        transform = CohortAnalysisTransform()
        result = transform.transform(
            retention=_make_retention_df(),
            customer_name="TestCorp",
        )
        narrative = result["narrative"]
        assert "executive_summary" in narrative
        assert "highlights" in narrative
        assert "recommendations" in narrative
        assert isinstance(narrative["highlights"], list)
        assert isinstance(narrative["recommendations"], list)

    def test_narrative_has_content(self):
        """Narrative fields are non-empty."""
        from transforms.cohort_analysis import CohortAnalysisTransform

        transform = CohortAnalysisTransform()
        result = transform.transform(
            retention=_make_retention_df(),
            customer_name="TestCorp",
        )
        narrative = result["narrative"]
        assert len(narrative["executive_summary"]) > 10
        assert len(narrative["highlights"]) >= 1
        assert len(narrative["recommendations"]) >= 1


class TestEmptyState:
    """Test empty/error handling."""

    def test_empty_dataframe_returns_not_available(self):
        """Transform with empty DataFrame returns available=False."""
        from transforms.cohort_analysis import CohortAnalysisTransform

        transform = CohortAnalysisTransform()
        result = transform.transform(
            retention=pd.DataFrame(),
            customer_name="TestCorp",
        )
        assert result["available"] is False
        assert result["reason"] == "no_data"

    def test_empty_result_method(self):
        """empty_result returns standard empty dict."""
        from transforms.cohort_analysis import CohortAnalysisTransform

        transform = CohortAnalysisTransform()
        result = transform.empty_result("no_data")
        assert result == {"available": False, "reason": "no_data"}
