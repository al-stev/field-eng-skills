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
    support_tickets_query,
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


class TestSupportTicketsQuery:
    """Verify support_tickets_query uses correct tables and params."""

    def test_support_tickets_query_contains_account_id_param(self):
        """Support tickets query uses @account_id parameter."""
        sql = support_tickets_query()
        assert "@account_id" in sql

    def test_support_tickets_query_joins_through_sfdc(self):
        """Support tickets query joins dim_helpdesk_tickets to stg_salesforce_accounts."""
        sql = support_tickets_query()
        assert "dim_helpdesk_tickets" in sql
        assert "stg_salesforce_accounts" in sql

    def test_support_tickets_query_excludes_deleted(self):
        """Support tickets query filters out deleted tickets."""
        sql = support_tickets_query()
        assert "deleted" in sql

    def test_support_tickets_query_no_aise_filter(self):
        """Support tickets query has no AISE residue."""
        sql = support_tickets_query()
        assert "_aise_filter" not in sql
        assert "Keisuke Kamata" not in sql

    def test_support_tickets_query_includes_jira_fields(self):
        """Support tickets query selects Jira cross-link fields."""
        sql = support_tickets_query()
        assert "jira_id" in sql
        assert "jira_link" in sql
        assert "escalated_to_jira" in sql


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


class TestIdentityResolutionCte:
    """Tests for identity_resolution_cte() reusable SQL CTE for server deployment identity."""

    def test_returns_cte_named_resolved_users(self):
        """Test 1: identity_resolution_cte() returns SQL string containing 'resolved_users AS ('."""
        from queries import identity_resolution_cte

        sql = identity_resolution_cte()
        assert "resolved_users AS (" in sql

    def test_contains_coalesce_for_username_and_email(self):
        """Test 2: identity_resolution_cte() returns SQL containing COALESCE for both username and email."""
        from queries import identity_resolution_cte

        sql = identity_resolution_cte()
        assert "COALESCE(" in sql
        assert "resolved_username" in sql
        assert "resolved_email" in sql
        assert "local_username" in sql
        assert "local_user_email" in sql

    def test_contains_left_join_dim_users_with_account_id(self):
        """Test 3: identity_resolution_cte() returns SQL containing LEFT JOIN on dim_users with account_id filter."""
        from queries import identity_resolution_cte

        sql = identity_resolution_cte()
        assert "LEFT JOIN" in sql
        assert "dim_users" in sql
        assert "du.account_id = @account_id" in sql

    def test_activity_table_alias(self):
        """Test 4: identity_resolution_cte(table_alias='activity') uses 'activity.' prefix in COALESCE."""
        from queries import identity_resolution_cte

        sql = identity_resolution_cte(table_alias="activity")
        assert "activity.universal_user_id" in sql
        assert "COALESCE(activity.username, du.local_username)" in sql
        assert "COALESCE(activity.email, du.local_user_email)" in sql

    def test_default_src_table_alias(self):
        """Test 5: identity_resolution_cte(table_alias='src') uses 'src.' prefix (default)."""
        from queries import identity_resolution_cte

        sql = identity_resolution_cte(table_alias="src")
        assert "src.universal_user_id" in sql
        assert "COALESCE(src.username, du.local_username)" in sql
        assert "COALESCE(src.email, du.local_user_email)" in sql

        # Also verify default matches explicit "src"
        sql_default = identity_resolution_cte()
        assert sql == sql_default

    def test_contains_fully_qualified_dim_users_ref(self):
        """Test 6: identity_resolution_cte() output contains fully-qualified dim_users table reference via _ref()."""
        from queries import identity_resolution_cte

        sql = identity_resolution_cte()
        expected_ref = _ref("dim_users")  # `wandb-production.analytics.dim_users`
        assert expected_ref in sql
