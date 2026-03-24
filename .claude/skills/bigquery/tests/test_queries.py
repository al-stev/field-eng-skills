"""Tests for queries.py -- query factory with parameterized account_id filtering."""

import sys

import pytest

# Add scripts/ to path for imports
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "scripts"))

from queries import (
    seat_utilization_query,
    weave_ingestion_query,
    tracked_hours_query,
    account_health_query,
    _ref,
)


class TestQueryFactory:
    """Verify all queries use @account_id parameter and have no AISE residue."""

    def test_seat_utilization_query_contains_account_id_param(self):
        """Seat utilization query uses @account_id parameter."""
        sql = seat_utilization_query()
        assert "@account_id" in sql

    def test_seat_utilization_query_no_aise_filter(self):
        """Seat utilization query does NOT contain _aise_filter or hardcoded AISE names."""
        sql = seat_utilization_query()
        assert "_aise_filter" not in sql
        assert "Keisuke Kamata" not in sql
        assert "Yuya Yamamoto" not in sql
        assert "Hyunwoo Oh" not in sql

    def test_weave_ingestion_query_contains_account_id_param(self):
        """Weave ingestion query uses @account_id parameter."""
        sql = weave_ingestion_query()
        assert "@account_id" in sql

    def test_weave_ingestion_query_no_aise_filter(self):
        """Weave ingestion query has no AISE residue."""
        sql = weave_ingestion_query()
        assert "_aise_filter" not in sql
        assert "Keisuke Kamata" not in sql

    def test_tracked_hours_query_contains_account_id_param(self):
        """Tracked hours query uses @account_id parameter."""
        sql = tracked_hours_query()
        assert "@account_id" in sql

    def test_tracked_hours_query_no_aise_filter(self):
        """Tracked hours query has no AISE residue."""
        sql = tracked_hours_query()
        assert "_aise_filter" not in sql
        assert "Keisuke Kamata" not in sql

    def test_account_health_query_references_landing_development(self):
        """Account health query references landing_development.renewal_predictions."""
        sql = account_health_query()
        assert "landing_development" in sql
        assert "renewal_predictions" in sql

    def test_account_health_query_contains_account_id_param(self):
        """Account health query uses @account_id parameter."""
        sql = account_health_query()
        assert "@account_id" in sql

    def test_account_health_query_no_aise_filter(self):
        """Account health query has no AISE residue."""
        sql = account_health_query()
        assert "_aise_filter" not in sql
        assert "Keisuke Kamata" not in sql


class TestRefHelper:
    """Tests for _ref() fully-qualified table name helper."""

    def test_ref_default_dataset(self):
        """_ref('stg_salesforce_accounts') returns fully-qualified analytics reference."""
        result = _ref("stg_salesforce_accounts")
        assert result == "`wandb-production.analytics.stg_salesforce_accounts`"

    def test_ref_custom_dataset(self):
        """_ref('renewal_predictions', dataset='landing_development') uses custom dataset."""
        result = _ref("renewal_predictions", dataset="landing_development")
        assert result == "`wandb-production.landing_development.renewal_predictions`"
