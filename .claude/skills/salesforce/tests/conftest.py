"""Shared pytest fixtures for Salesforce skill tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


@pytest.fixture
def tmp_env_file(tmp_path):
    """Create a temporary .env file with SFDC credentials."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SFDC_USERNAME=test@example.com\n"
        "SFDC_PASSWORD=testpass123\n"
        "SFDC_SECURITY_TOKEN=abcdef123456\n"
        "OTHER_KEY=other_value\n"
    )
    return env_file


@pytest.fixture
def tmp_env_file_with_domain(tmp_path):
    """Create a temporary .env file with SFDC credentials including custom domain."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SFDC_USERNAME=test@example.com\n"
        "SFDC_PASSWORD=testpass123\n"
        "SFDC_SECURITY_TOKEN=abcdef123456\n"
        "SFDC_DOMAIN=wandb.my\n"
    )
    return env_file


@pytest.fixture
def tmp_env_file_missing_creds(tmp_path):
    """Create a temporary .env file missing SFDC credentials."""
    env_file = tmp_path / ".env"
    env_file.write_text("OTHER_KEY=other_value\n")
    return env_file


@pytest.fixture
def mock_sfdc_client():
    """Create a mock Salesforce client with common methods."""
    client = MagicMock()

    # Mock Account.describe() response
    client.Account.describe.return_value = {
        "fields": [
            {"name": "Id", "label": "Account ID", "type": "id"},
            {"name": "Name", "label": "Account Name", "type": "string"},
            {"name": "OwnerId", "label": "Account Owner", "type": "reference"},
            {"name": "Type", "label": "Account Type", "type": "picklist"},
            {"name": "Industry", "label": "Industry", "type": "picklist"},
            {"name": "Renewal_ARR__c", "label": "Renewal ARR", "type": "currency"},
            {"name": "CS_Renewal_Date__c", "label": "CS Renewal Date", "type": "date"},
            {"name": "Subscription_Plan__c", "label": "Subscription Plan", "type": "picklist"},
            {"name": "Opportunity_Deployment_Types__c", "label": "Deployment Types", "type": "multipicklist"},
            {"name": "CS_Tier__c", "label": "CS Tier", "type": "picklist"},
            {"name": "BillingCity", "label": "Billing City", "type": "string"},
            {"name": "AnnualRevenue", "label": "Annual Revenue", "type": "currency"},
        ]
    }

    # Mock query for current user
    client.query.return_value = {
        "totalSize": 1,
        "done": True,
        "records": [
            {"Id": "005xx000001Svgh", "Username": "test@example.com"}
        ],
    }

    # Mock query_all for AccountTeamMember
    client.query_all.return_value = {
        "totalSize": 2,
        "done": True,
        "records": [
            {
                "AccountId": "001xx000003DGbY",
                "Account": {"Name": "Acme Corp", "Id": "001xx000003DGbY"},
                "TeamMemberRole": "Solutions Engineer",
            },
            {
                "AccountId": "001xx000003DGbZ",
                "Account": {"Name": "Beta Inc", "Id": "001xx000003DGbZ"},
                "TeamMemberRole": "Solutions Engineer",
            },
        ],
    }

    return client


@pytest.fixture
def mock_account_detail_response():
    """Mock response for account detail query."""
    return {
        "totalSize": 1,
        "done": True,
        "records": [
            {
                "Id": "001xx000003DGbY",
                "Name": "Acme Corp",
                "OwnerId": "005xx000001Svgh",
                "Type": "Customer",
                "Industry": "Technology",
                "Renewal_ARR__c": 150000.0,
                "CS_Renewal_Date__c": "2026-06-15",
                "Subscription_Plan__c": "Enterprise",
                "Opportunity_Deployment_Types__c": "Dedicated Cloud",
                "CS_Tier__c": "Tier 1",
            }
        ],
    }


@pytest.fixture
def mock_team_members_response():
    """Mock response for team members query."""
    return {
        "totalSize": 3,
        "done": True,
        "records": [
            {
                "UserId": "005xx000001Svgh",
                "TeamMemberRole": "Solutions Engineer",
                "User": {"Name": "Test User", "Email": "test@example.com"},
            },
            {
                "UserId": "005xx000001Svgi",
                "TeamMemberRole": "Customer Success Manager",
                "User": {"Name": "CS Manager", "Email": "csm@example.com"},
            },
            {
                "UserId": "005xx000001Svgj",
                "TeamMemberRole": "Account Executive",
                "User": {"Name": "AE Person", "Email": "ae@example.com"},
            },
        ],
    }
