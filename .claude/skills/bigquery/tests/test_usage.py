"""Tests for usage.py -- usage pipeline JSON output and helper functions."""

import sys
from pathlib import Path

import pandas as pd
import pytest

# Add scripts/ to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from usage import build_usage_json, classify_utilization_zone, _build_support_tickets


class TestBuildUsageJson:
    """Tests for build_usage_json() output schema and behavior."""

    def test_json_output_matches_schema(
        self,
        sample_seat_usage_df,
        sample_weave_usage_df,
        sample_tracked_hours_df,
        sample_account_health_df,
    ):
        """build_usage_json returns dict with all required top-level keys."""
        result = build_usage_json(
            sample_seat_usage_df,
            sample_weave_usage_df,
            sample_tracked_hours_df,
            sample_account_health_df,
        )
        assert isinstance(result, dict)
        assert result["available"] is True
        assert "period" in result
        assert "seat_utilization" in result
        assert "weave" in result
        assert "tracked_hours" in result
        assert "account_health" in result
        assert "product_areas" in result
        assert "support_tickets" in result

    def test_empty_data_returns_unavailable(self, sample_empty_df):
        """All empty DataFrames produce {"available": false, "reason": "no_data"}."""
        result = build_usage_json(
            sample_empty_df,
            sample_empty_df,
            sample_empty_df,
            sample_empty_df,
        )
        assert result["available"] is False
        assert result["reason"] == "no_data"

    def test_partial_data_independent_sections(
        self,
        sample_seat_usage_df,
        sample_empty_df,
    ):
        """Seat data present but weave empty -> seat_utilization populated, weave is null."""
        result = build_usage_json(
            sample_seat_usage_df,
            sample_empty_df,
            sample_empty_df,
            sample_empty_df,
        )
        assert result["available"] is True
        assert result["seat_utilization"] is not None
        assert result["weave"] is None

    def test_account_health_fields(self, sample_account_health_df, sample_empty_df):
        """account_health sub-object contains all 8 fields."""
        result = build_usage_json(
            sample_empty_df,
            sample_empty_df,
            sample_empty_df,
            sample_account_health_df,
        )
        assert result["available"] is True
        health = result["account_health"]
        assert health is not None
        for field in [
            "renewal_date", "arr", "cs_tier", "customer_health",
            "churn_probability_3mo", "churn_probability_5mo",
            "subscription_plan", "deployment_type",
        ]:
            assert field in health, f"Missing field: {field}"

    def test_history_weekly_format(self, sample_seat_usage_df, sample_empty_df):
        """seat_utilization.history entries have week, contracted, active keys."""
        result = build_usage_json(
            sample_seat_usage_df,
            sample_empty_df,
            sample_empty_df,
            sample_empty_df,
        )
        history = result["seat_utilization"]["history"]
        assert len(history) > 0
        entry = history[0]
        assert "week" in entry
        assert "contracted" in entry
        assert "active" in entry

    def test_weave_history_monthly_format(self, sample_weave_usage_df, sample_empty_df):
        """weave.history entries have month (YYYY-MM), ingestion_gb, unique_users keys."""
        result = build_usage_json(
            sample_empty_df,
            sample_weave_usage_df,
            sample_empty_df,
            sample_empty_df,
        )
        history = result["weave"]["history"]
        assert len(history) > 0
        entry = history[0]
        assert "month" in entry
        assert "ingestion_gb" in entry
        assert "unique_users" in entry
        # Month should be YYYY-MM format
        assert len(entry["month"]) == 7  # "2026-01"

    def test_weave_unit_normalization(self, sample_weave_usage_df, sample_empty_df):
        """Pipeline passes through GB-normalized Weave data from SQL."""
        result = build_usage_json(
            sample_empty_df,
            sample_weave_usage_df,
            sample_empty_df,
            sample_empty_df,
        )
        # Weave data should be present and have ingestion_gb
        weave = result["weave"]
        assert weave is not None
        assert weave["ingestion_gb"] > 0


class TestBuildSupportTickets:
    """Tests for _build_support_tickets() output schema and aggregation."""

    def test_support_tickets_output_keys(self, sample_support_tickets_df):
        """_build_support_tickets returns dict with all required keys."""
        result = _build_support_tickets(sample_support_tickets_df)
        assert result is not None
        for key in [
            "total", "by_status", "by_priority", "escalated_to_jira",
            "csat", "top_concerns", "monthly_volume", "recent_tickets",
        ]:
            assert key in result, f"Missing key: {key}"

    def test_support_tickets_total_count(self, sample_support_tickets_df):
        """total equals number of ticket rows."""
        result = _build_support_tickets(sample_support_tickets_df)
        assert result["total"] == 6

    def test_support_tickets_status_distribution(self, sample_support_tickets_df):
        """by_status counts each status correctly."""
        result = _build_support_tickets(sample_support_tickets_df)
        assert result["by_status"]["open"] == 1
        assert result["by_status"]["pending"] == 1
        assert result["by_status"]["closed"] == 1
        assert result["by_status"]["hold"] == 1
        assert result["by_status"]["new"] == 1
        assert result["by_status"]["solved"] == 1

    def test_support_tickets_escalation_count(self, sample_support_tickets_df):
        """escalated_to_jira counts 'yes' values (3 in fixture)."""
        result = _build_support_tickets(sample_support_tickets_df)
        assert result["escalated_to_jira"] == 3

    def test_support_tickets_recent_only_open(self, sample_support_tickets_df):
        """recent_tickets only includes open/pending/new/hold tickets."""
        result = _build_support_tickets(sample_support_tickets_df)
        statuses = {t["status"] for t in result["recent_tickets"]}
        assert statuses <= {"open", "pending", "new", "hold"}
        # closed and solved should NOT be in recent
        assert "closed" not in statuses
        assert "solved" not in statuses

    def test_support_tickets_jira_cross_link(self, sample_support_tickets_df):
        """Tickets with jira_id include jira_id and jira_link in output."""
        result = _build_support_tickets(sample_support_tickets_df)
        linked = [t for t in result["recent_tickets"] if "jira_id" in t]
        assert len(linked) > 0
        for t in linked:
            assert t["jira_id"].startswith("WB-")

    def test_support_tickets_monthly_volume(self, sample_support_tickets_df):
        """monthly_volume has entries sorted by month."""
        result = _build_support_tickets(sample_support_tickets_df)
        months = [m["month"] for m in result["monthly_volume"]]
        assert months == sorted(months)
        assert sum(m["count"] for m in result["monthly_volume"]) == 6

    def test_support_tickets_empty_returns_none(self, sample_empty_df):
        """Empty DataFrame returns None."""
        result = _build_support_tickets(sample_empty_df)
        assert result is None

    def test_support_tickets_in_usage_json(
        self, sample_empty_df, sample_support_tickets_df
    ):
        """support_tickets appears in build_usage_json output."""
        result = build_usage_json(
            sample_empty_df, sample_empty_df, sample_empty_df, sample_empty_df,
            support_tickets_df=sample_support_tickets_df,
        )
        assert result["available"] is True
        assert result["support_tickets"] is not None
        assert result["support_tickets"]["total"] == 6


class TestClassifyUtilizationZone:
    """Tests for zone threshold classification."""

    def test_utilization_zone_healthy(self):
        """80+ = 'healthy'."""
        assert classify_utilization_zone(80.0) == "healthy"
        assert classify_utilization_zone(100.0) == "healthy"

    def test_utilization_zone_at_risk(self):
        """50-79 = 'at_risk'."""
        assert classify_utilization_zone(50.0) == "at_risk"
        assert classify_utilization_zone(79.9) == "at_risk"

    def test_utilization_zone_critical(self):
        """<50 = 'critical'."""
        assert classify_utilization_zone(49.9) == "critical"
        assert classify_utilization_zone(0.0) == "critical"


