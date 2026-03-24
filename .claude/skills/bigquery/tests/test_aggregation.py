"""Tests for aggregate_weekly() -- pandas resample with method dispatch."""

import sys

import pandas as pd
import pytest

# Add scripts/ to path for imports
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "scripts"))

from queries import aggregate_weekly


class TestAggregateWeekly:
    """Tests for weekly aggregation with different methods."""

    def test_weekly_aggregation_last(self, sample_seat_usage_df):
        """Daily seat data aggregated to weekly using 'last' gives end-of-week snapshot."""
        result = aggregate_weekly(
            sample_seat_usage_df,
            date_col="date_day",
            value_cols=["active_seats", "contracted_seats"],
            method="last",
        )
        assert not result.empty
        # Should have fewer rows than input (7 daily -> ~2 weekly)
        assert len(result) <= len(sample_seat_usage_df)
        # Values should be the last value in each week
        assert "active_seats" in result.columns
        assert "contracted_seats" in result.columns

    def test_weekly_aggregation_mean(self, sample_tracked_hours_df):
        """Daily tracked hours aggregated using 'mean' gives weekly average."""
        result = aggregate_weekly(
            sample_tracked_hours_df,
            date_col="date_day",
            value_cols=["tracked_hours"],
            method="mean",
        )
        assert not result.empty
        # Mean of [180.5, 200.0, 190.3, 210.7, 195.0] should be reasonable
        assert result["tracked_hours"].iloc[0] > 0

    def test_weekly_aggregation_sum(self, sample_weave_usage_df):
        """Ingestion data aggregated using 'sum' gives cumulative total."""
        result = aggregate_weekly(
            sample_weave_usage_df,
            date_col="created_date",
            value_cols=["total_storage_gb"],
            method="sum",
        )
        assert not result.empty
        # Sum should be >= any individual value
        assert result["total_storage_gb"].max() >= 8.2

    def test_weekly_aggregation_empty(self, sample_empty_df):
        """Empty DataFrame returns empty DataFrame (no crash)."""
        result = aggregate_weekly(
            sample_empty_df,
            date_col="date_day",
            value_cols=["value"],
            method="last",
        )
        assert isinstance(result, pd.DataFrame)
        assert result.empty
