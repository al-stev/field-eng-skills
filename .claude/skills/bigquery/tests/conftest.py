"""Shared test fixtures with sample DataFrames for BigQuery skill tests."""

import pytest
import pandas as pd
from pathlib import Path
import yaml


@pytest.fixture
def sample_seat_usage_df():
    """Daily seat usage data -- 7 rows spanning 2 weeks for aggregation tests."""
    return pd.DataFrame({
        "account_id": ["001ABC"] * 7,
        "date_day": pd.to_datetime([
            "2026-03-10", "2026-03-11", "2026-03-12",
            "2026-03-13", "2026-03-14", "2026-03-17",
            "2026-03-18",
        ]),
        "active_seats": [30, 32, 31, 33, 35, 34, 36],
        "claimed_seats": [40, 40, 40, 42, 42, 42, 42],
        "contracted_seats": [50, 50, 50, 50, 50, 50, 50],
        "deployment": ["cloud"] * 7,
    })


@pytest.fixture
def sample_weave_usage_df():
    """Monthly Weave ingestion data -- 3 months."""
    return pd.DataFrame({
        "organization_name": ["AcmeCorp"] * 3,
        "created_date": pd.to_datetime([
            "2026-01-01", "2026-02-01", "2026-03-01",
        ]),
        "total_storage_gb": [8.2, 11.4, 9.8],
        "unique_users": [5, 8, 12],
    })


@pytest.fixture
def sample_tracked_hours_df():
    """Daily tracked hours data -- 5 rows for aggregation tests."""
    return pd.DataFrame({
        "account_id": ["001ABC"] * 5,
        "date_day": pd.to_datetime([
            "2026-03-10", "2026-03-11", "2026-03-12",
            "2026-03-13", "2026-03-14",
        ]),
        "tracked_hours": [180.5, 200.0, 190.3, 210.7, 195.0],
        "last_30_days_run_count": [342, 342, 342, 342, 342],
    })


@pytest.fixture
def sample_account_health_df():
    """Single-row account health metadata."""
    return pd.DataFrame({
        "renewal_date": [pd.Timestamp("2026-09-15")],
        "arr": [250000.0],
        "cs_tier": ["Strategic"],
        "customer_health": ["Green"],
        "churn_probability_3mo": [0.05],
        "churn_probability_5mo": [0.08],
        "subscription_plan": ["Enterprise"],
        "deployment_type": ["dedicated-cloud"],
    })


@pytest.fixture
def sample_support_tickets_df():
    """Support ticket data -- 6 tickets with mixed statuses and Jira links."""
    return pd.DataFrame({
        "zendesk_ticket_id": [101, 102, 103, 104, 105, 106],
        "ticket_subject": [
            "SDK crash on init",
            "Cannot login to workspace",
            "Weave ingestion slow",
            "Feature request: dark mode",
            "Run fails with OOM",
            "API rate limit hit",
        ],
        "ticket_status": ["open", "pending", "closed", "hold", "new", "solved"],
        "ticket_priority": ["urgent", "high", "low", "low", "urgent", "normal"],
        "ticket_created_at": pd.to_datetime([
            "2026-03-20 10:00:00", "2026-03-18 14:00:00", "2026-02-15 09:00:00",
            "2026-03-01 11:00:00", "2026-03-22 08:00:00", "2026-01-10 16:00:00",
        ]),
        "ticket_created_date_day": pd.to_datetime([
            "2026-03-20", "2026-03-18", "2026-02-15",
            "2026-03-01", "2026-03-22", "2026-01-10",
        ]),
        "ticket_last_updated_at": pd.to_datetime([
            "2026-03-24 12:00:00", "2026-03-24 10:00:00", "2026-02-20 15:00:00",
            "2026-03-05 09:00:00", "2026-03-23 11:00:00", "2026-01-15 14:00:00",
        ]),
        "primary_ticket_concern": [
            "crashed_run", "user_management", "local", "other", "crashed_run", "client__public_api",
        ],
        "sa_ticket_type": [None, None, None, None, None, None],
        "channel": ["email", "web", "api", "email", "chat", "api"],
        "jira_id": ["WB-1234", None, "WB-5678", None, "WB-9012", None],
        "jira_link": [
            "https://wandb.atlassian.net/browse/WB-1234", None,
            "https://wandb.atlassian.net/browse/WB-5678", None,
            "https://wandb.atlassian.net/browse/WB-9012", None,
        ],
        "jira_status": ["In Progress", None, "Done", None, "Open", None],
        "escalated_to_jira": ["yes", "no", "yes", "", "yes", None],
        "escalated_to_t2": [None, None, None, None, None, None],
        "ticket_satisfaction_score": ["good", "bad", None, None, "good", "good"],
        "submitter_name": ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"],
        "submitter_email": ["a@co.com", "b@co.com", "c@co.com", "d@co.com", "e@co.com", "f@co.com"],
        "assignee_name": ["Agent1", "Agent2", "Agent1", "Agent2", "Agent1", "Agent2"],
    })


@pytest.fixture
def sample_empty_df():
    """Empty DataFrame for edge case tests."""
    return pd.DataFrame()


@pytest.fixture
def sample_customers_yaml(tmp_path):
    """Temp customers.yaml with test data for SFDC ID lookup tests."""
    data = {
        "customers": [
            {
                "name": "AcmeCorp",
                "jira_customer": "AcmeCorp",
                "sfdc_account_id": "001ABC",
                "slack_channels": [],
            },
            {
                "name": "No-BQ-Customer",
                "jira_customer": "No-BQ-Customer",
                "sfdc_account_id": "PLACEHOLDER",
                "slack_channels": [],
            },
        ]
    }
    yaml_path = tmp_path / "customers.yaml"
    yaml_path.write_text(yaml.dump(data))
    return yaml_path
