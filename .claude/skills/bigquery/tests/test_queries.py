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
    cohort_retention_query,
    user_lifecycle_query,
    team_detection_query,
    team_champions_query,
    engagement_trend_query,
    risk_support_tickets_query,
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


class TestCohortRetentionQuery:
    """Verify cohort_retention_query() builds correct SQL for cohort analysis."""

    def test_contains_account_id_param(self):
        """Query uses @account_id parameter."""
        sql = cohort_retention_query()
        assert "@account_id" in sql

    def test_uses_ref_for_table(self):
        """Query uses _ref() for ext_daily_user_event_usage (no hardcoded paths)."""
        sql = cohort_retention_query()
        assert _ref("ext_daily_user_event_usage") in sql

    def test_contains_format_date(self):
        """Query contains FORMAT_DATE for month bucketing."""
        sql = cohort_retention_query()
        assert "FORMAT_DATE('%Y-%m'" in sql

    def test_contains_universal_user_id(self):
        """Query groups by universal_user_id."""
        sql = cohort_retention_query()
        assert "universal_user_id" in sql

    def test_contains_event_count_filter(self):
        """Query filters on event_count > 0."""
        sql = cohort_retention_query()
        assert "event_count > 0" in sql

    def test_contains_18_month_lookback(self):
        """Query looks back 18 months for cohort computation."""
        sql = cohort_retention_query()
        assert "INTERVAL 18 MONTH" in sql

    def test_no_select_star(self):
        """Query does NOT use SELECT *."""
        sql = cohort_retention_query()
        assert "SELECT *" not in sql


class TestUserLifecycleQuery:
    """Verify user_lifecycle_query() builds correct SQL for lifecycle states."""

    def test_contains_account_id_param(self):
        """Query uses @account_id parameter."""
        sql = user_lifecycle_query()
        assert "@account_id" in sql

    def test_uses_ref_for_table(self):
        """Query uses _ref() for agg_daily_user_activity."""
        sql = user_lifecycle_query()
        assert _ref("agg_daily_user_activity") in sql

    def test_contains_accounting_field(self):
        """Query references user_has_any_event_accounting for lifecycle states."""
        sql = user_lifecycle_query()
        assert "user_has_any_event_accounting" in sql

    def test_contains_18_month_lookback(self):
        """Query looks back 18 months."""
        sql = user_lifecycle_query()
        assert "INTERVAL 18 MONTH" in sql

    def test_no_select_star(self):
        """Query does NOT use SELECT *."""
        sql = user_lifecycle_query()
        assert "SELECT *" not in sql


class TestTeamDetectionQuery:
    """Verify team_detection_query() builds correct SQL for team breakdown."""

    def test_contains_account_id_param(self):
        """Query uses @account_id parameter."""
        sql = team_detection_query()
        assert "@account_id" in sql

    def test_uses_ref_for_table(self):
        """Query uses _ref() for ext_daily_user_event_usage."""
        sql = team_detection_query()
        assert _ref("ext_daily_user_event_usage") in sql

    def test_contains_org_name(self):
        """Query references org_name for team grouping."""
        sql = team_detection_query()
        assert "org_name" in sql

    def test_contains_coalesce_org_name(self):
        """Query COALESCEs org_name for NULL handling."""
        sql = team_detection_query()
        assert "COALESCE(org_name" in sql

    def test_contains_is_part_of_team(self):
        """Query references is_part_of_team flag."""
        sql = team_detection_query()
        assert "is_part_of_team" in sql

    def test_contains_event_count(self):
        """Query uses event_count for activity aggregation."""
        sql = team_detection_query()
        assert "event_count" in sql

    def test_no_select_star(self):
        """Query does NOT use SELECT *."""
        sql = team_detection_query()
        assert "SELECT *" not in sql


class TestTeamChampionsQuery:
    """Verify team_champions_query() builds correct SQL for per-team top users."""

    def test_contains_account_id_param(self):
        """Query uses @account_id parameter."""
        sql = team_champions_query()
        assert "@account_id" in sql

    def test_uses_ref_for_table(self):
        """Query uses _ref() for ext_daily_user_event_usage."""
        sql = team_champions_query()
        assert _ref("ext_daily_user_event_usage") in sql

    def test_contains_org_name(self):
        """Query references org_name for team identification."""
        sql = team_champions_query()
        assert "org_name" in sql

    def test_contains_universal_user_id(self):
        """Query tracks per-user activity."""
        sql = team_champions_query()
        assert "universal_user_id" in sql

    def test_contains_row_number(self):
        """Query uses ROW_NUMBER() to pick top user per team."""
        sql = team_champions_query()
        assert "ROW_NUMBER()" in sql

    def test_no_select_star(self):
        """Query does NOT use SELECT *."""
        sql = team_champions_query()
        assert "SELECT *" not in sql


class TestEngagementTrendQuery:
    """Verify engagement_trend_query() builds correct SQL for risk scoring input."""

    def test_contains_account_id_param(self):
        """Query uses @account_id parameter."""
        sql = engagement_trend_query()
        assert "@account_id" in sql

    def test_uses_ref_for_table(self):
        """Query uses _ref() for agg_daily_customer_engagement_score."""
        sql = engagement_trend_query()
        assert _ref("agg_daily_customer_engagement_score") in sql

    def test_contains_engagement_score(self):
        """Query references customer_engagement_score column."""
        sql = engagement_trend_query()
        assert "customer_engagement_score" in sql

    def test_contains_6_month_lookback(self):
        """Query looks back 6 months for engagement trend."""
        sql = engagement_trend_query()
        assert "INTERVAL 6 MONTH" in sql

    def test_no_select_star(self):
        """Query does NOT use SELECT *."""
        sql = engagement_trend_query()
        assert "SELECT *" not in sql


class TestRiskSupportTicketsQuery:
    """Verify risk_support_tickets_query() builds correct SQL for risk scoring input."""

    def test_contains_account_id_param(self):
        """Query uses @account_id parameter."""
        sql = risk_support_tickets_query()
        assert "@account_id" in sql

    def test_uses_ref_for_table(self):
        """Query uses _ref() for dim_helpdesk_tickets."""
        sql = risk_support_tickets_query()
        assert _ref("dim_helpdesk_tickets") in sql

    def test_contains_90_day_lookback(self):
        """Query looks back 90 days for support ticket count."""
        sql = risk_support_tickets_query()
        assert "INTERVAL 90 DAY" in sql

    def test_no_select_star(self):
        """Query does NOT use SELECT *."""
        sql = risk_support_tickets_query()
        assert "SELECT *" not in sql
