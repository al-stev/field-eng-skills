"""Tests for accounts.py — describe, my-accounts, account-detail, team-members subcommands."""

import json
import sys
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


class TestCmdDescribe:
    """Tests for cmd_describe function."""

    def test_filters_fields_by_label_keyword(self, mock_sfdc_client, capsys):
        """cmd_describe parses Account.describe() response, filters by label keyword."""
        from accounts import cmd_describe

        args = Namespace(filter="ARR", pretty=False)
        cmd_describe(mock_sfdc_client, args)

        captured = capsys.readouterr()
        result = json.loads(captured.out)
        # Should only include fields with "ARR" in the label (case-insensitive)
        assert len(result["fields"]) == 1
        assert result["fields"][0]["name"] == "Renewal_ARR__c"

    def test_returns_all_fields_without_filter(self, mock_sfdc_client, capsys):
        """cmd_describe with no filter returns all fields."""
        from accounts import cmd_describe

        args = Namespace(filter=None, pretty=False)
        cmd_describe(mock_sfdc_client, args)

        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert len(result["fields"]) == 12  # all fields from fixture


class TestCmdMyAccounts:
    """Tests for cmd_my_accounts function."""

    def test_queries_account_team_member(self, mock_sfdc_client, capsys):
        """cmd_my_accounts queries AccountTeamMember, returns list of account dicts."""
        from accounts import cmd_my_accounts

        args = Namespace(pretty=False)
        cmd_my_accounts(mock_sfdc_client, args)

        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["count"] == 2
        accounts = result["accounts"]
        assert accounts[0]["name"] == "Acme Corp"
        assert accounts[0]["id"] == "001xx000003DGbY"
        assert accounts[0]["role"] == "Solutions Engineer"
        assert accounts[1]["name"] == "Beta Inc"

    def test_falls_back_on_invalid_type(self, mock_sfdc_client, capsys):
        """cmd_my_accounts falls back gracefully when AccountTeamMember query fails."""
        from simple_salesforce.exceptions import SalesforceMalformedRequest
        from accounts import cmd_my_accounts

        # First query (user ID) succeeds, second (AccountTeamMember) fails
        mock_sfdc_client.query.return_value = {
            "totalSize": 1,
            "done": True,
            "records": [{"Id": "005xx000001Svgh", "Username": "test@example.com"}],
        }
        mock_sfdc_client.query_all.side_effect = SalesforceMalformedRequest(
            "url", 400, "resource",
            [{"message": "INVALID_TYPE: AccountTeamMember", "errorCode": "INVALID_TYPE"}]
        )

        args = Namespace(pretty=False)
        cmd_my_accounts(mock_sfdc_client, args)

        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["count"] == 0
        assert "warning" in result


class TestCmdAccountDetail:
    """Tests for cmd_account_detail function."""

    def test_fetches_account_by_id(self, mock_sfdc_client, mock_account_detail_response, mock_team_members_response, capsys):
        """cmd_account_detail fetches account by ID with standard + custom fields."""
        from accounts import cmd_account_detail

        mock_sfdc_client.query.return_value = mock_account_detail_response
        mock_sfdc_client.query_all.return_value = mock_team_members_response

        args = Namespace(account_id="001xx000003DGbY", pretty=False)
        cmd_account_detail(mock_sfdc_client, args)

        captured = capsys.readouterr()
        result = json.loads(captured.out)
        account = result["account"]
        assert account["Id"] == "001xx000003DGbY"
        assert account["Name"] == "Acme Corp"
        assert account["Renewal_ARR__c"] == 150000.0

    def test_includes_team_members(self, mock_sfdc_client, mock_account_detail_response, mock_team_members_response, capsys):
        """cmd_account_detail includes team members from AccountTeamMember subquery."""
        from accounts import cmd_account_detail

        mock_sfdc_client.query.return_value = mock_account_detail_response
        mock_sfdc_client.query_all.return_value = mock_team_members_response

        args = Namespace(account_id="001xx000003DGbY", pretty=False)
        cmd_account_detail(mock_sfdc_client, args)

        captured = capsys.readouterr()
        result = json.loads(captured.out)
        team = result["team_members"]
        assert len(team) == 3
        assert team[0]["name"] == "Test User"
        assert team[0]["role"] == "Solutions Engineer"


class TestCmdTeamMembers:
    """Tests for cmd_team_members function."""

    def test_returns_structured_team_list(self, mock_sfdc_client, mock_team_members_response, capsys):
        """cmd_team_members returns structured team member list with name/email/role."""
        from accounts import cmd_team_members

        mock_sfdc_client.query_all.return_value = mock_team_members_response

        args = Namespace(account_id="001xx000003DGbY", pretty=False)
        cmd_team_members(mock_sfdc_client, args)

        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["count"] == 3
        members = result["members"]
        assert members[0] == {
            "name": "Test User",
            "email": "test@example.com",
            "role": "Solutions Engineer",
        }
        assert members[1] == {
            "name": "CS Manager",
            "email": "csm@example.com",
            "role": "Customer Success Manager",
        }
        assert members[2] == {
            "name": "AE Person",
            "email": "ae@example.com",
            "role": "Account Executive",
        }
