#!/usr/bin/env python3
"""
Salesforce Account operations tool.

Read-only queries for Account data: field discovery, account list,
account details with custom fields, and team members.

Usage:
    accounts.py describe [--filter KEYWORD] [--pretty]
    accounts.py my-accounts [--pretty]
    accounts.py account-detail --account-id ID [--pretty]
    accounts.py team-members --account-id ID [--pretty]
"""

import argparse
import sys
from pathlib import Path

# Add current directory to path to import sfdc_client
sys.path.insert(0, str(Path(__file__).resolve().parent))

from simple_salesforce.exceptions import (
    SalesforceMalformedRequest,
)
from sfdc_client import (
    get_client,
    handle_api_call,
    output_json,
    output_error,
)


# Standard Account fields always available
STANDARD_FIELDS = [
    "Id", "Name", "OwnerId", "Type", "Industry",
]

# Custom fields to attempt (W&B SFDC org -- discovered via describe 2026-03-24)
CUSTOM_FIELDS = [
    "Renewal_ARR__c",
    "CS_Renewal_Date__c",
    "Subscription_Plan__c",
    "Opportunity_Deployment_Types__c",
    "CS_Tier__c",
    "Post_Sales_SMLE_TEXT__c",       # Post-Sales AISE (text lookup)
    "Post_Sales_SMLE__c",            # Post-Sales AISE (reference ID)
    "Solutions_Architect__c",         # Solutions Architect (reference ID)
    "Account_Owner_Text__c",         # Account Owner name (text)
]

# Account team role fields -- used to populate account_team in customers.yaml
# These are reference fields on Account that point to User records
TEAM_ROLE_FIELDS = {
    "OwnerId": "Account Owner",
    "Post_Sales_SMLE__c": "Post-Sales AISE",
    "Solutions_Architect__c": "Solutions Architect",
}


def cmd_describe(sf, args):
    """Describe Account object fields, optionally filtered by label keyword."""
    description = handle_api_call(sf.Account.describe)
    fields = description["fields"]

    result_fields = []
    for f in fields:
        entry = {
            "name": f["name"],
            "label": f["label"],
            "type": f["type"],
        }
        if args.filter:
            if args.filter.lower() in f["label"].lower():
                result_fields.append(entry)
        else:
            result_fields.append(entry)

    output_json({
        "object": "Account",
        "field_count": len(result_fields),
        "filter": args.filter,
        "fields": result_fields,
    }, args.pretty)


def cmd_my_accounts(sf, args):
    """List accounts where the current user is on the account team."""
    # Get current user ID via /services/oauth2/userinfo or SOQL
    user_id = _get_current_user_id(sf)

    # Query AccountTeamMember for user's accounts
    try:
        team_records = handle_api_call(
            sf.query_all,
            "SELECT AccountId, Account.Name, Account.Id, TeamMemberRole "
            "FROM AccountTeamMember "
            "WHERE UserId = '{}' "
            "AND Account.Type = 'Customer'".format(user_id),
        )

        accounts = []
        for rec in team_records["records"]:
            accounts.append({
                "name": rec["Account"]["Name"],
                "id": rec["Account"]["Id"],
                "role": rec["TeamMemberRole"],
            })

        output_json({
            "user_id": user_id,
            "count": len(accounts),
            "accounts": accounts,
        }, args.pretty)

    except SalesforceMalformedRequest as e:
        content = str(e.content) if hasattr(e, 'content') else str(e)
        if "INVALID_TYPE" in content:
            output_json({
                "user_id": user_id,
                "count": 0,
                "accounts": [],
                "warning": "AccountTeamMember object not available in this org. "
                           "Use account-detail with a known Account ID instead.",
            }, args.pretty)
        else:
            raise


def _get_current_user_id(sf):
    """Get the current user's Salesforce ID. Works with both auth modes."""
    import requests
    # Method 1: Use the userinfo endpoint (works with OAuth tokens)
    try:
        resp = requests.get(
            f"https://{sf.sf_instance}/services/oauth2/userinfo",
            headers={"Authorization": f"Bearer {sf.session_id}"},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()["user_id"]
    except Exception:
        pass

    # Method 2: Query User table directly (fallback)
    result = handle_api_call(
        sf.query,
        "SELECT Id FROM User WHERE Username = '{}'".format(
            sf.sf_instance  # Will be overridden below
        ),
    )
    if result["records"]:
        return result["records"][0]["Id"]

    output_error("no_user", "Could not determine current user ID.")
    sys.exit(1)


def cmd_account_detail(sf, args):
    """Fetch account details by ID with standard and custom fields."""
    # Try standard + custom fields first
    all_fields = STANDARD_FIELDS + CUSTOM_FIELDS
    query_fields = ", ".join(all_fields)

    try:
        result = handle_api_call(
            sf.query,
            f"SELECT {query_fields} FROM Account WHERE Id = '{args.account_id}'",
        )
    except SalesforceMalformedRequest:
        # Fall back to standard fields only
        query_fields = ", ".join(STANDARD_FIELDS)
        result = handle_api_call(
            sf.query,
            f"SELECT {query_fields} FROM Account WHERE Id = '{args.account_id}'",
        )

    if not result["records"]:
        output_error("not_found", f"Account {args.account_id} not found.")
        sys.exit(1)

    account = result["records"][0]

    # Fetch team members
    team_members = _fetch_team_members(sf, args.account_id)

    output_json({
        "account": account,
        "team_members": team_members,
    }, args.pretty)


def _fetch_team_members(sf, account_id):
    """Fetch AccountTeamMember records for an account. Returns empty list on failure."""
    try:
        team_result = handle_api_call(
            sf.query_all,
            "SELECT UserId, TeamMemberRole, User.Name, User.Email "
            "FROM AccountTeamMember "
            "WHERE AccountId = '{}'".format(account_id),
        )
        return [
            {
                "name": rec["User"]["Name"],
                "email": rec["User"]["Email"],
                "role": rec["TeamMemberRole"],
            }
            for rec in team_result["records"]
        ]
    except SalesforceMalformedRequest:
        return []


def cmd_team_members(sf, args):
    """List team members for an account."""
    try:
        team_result = handle_api_call(
            sf.query_all,
            "SELECT UserId, TeamMemberRole, User.Name, User.Email "
            "FROM AccountTeamMember "
            "WHERE AccountId = '{}'".format(args.account_id),
        )

        members = [
            {
                "name": rec["User"]["Name"],
                "email": rec["User"]["Email"],
                "role": rec["TeamMemberRole"],
            }
            for rec in team_result["records"]
        ]

        output_json({
            "account_id": args.account_id,
            "count": len(members),
            "members": members,
        }, args.pretty)

    except SalesforceMalformedRequest as e:
        content = str(e.content) if hasattr(e, 'content') else str(e)
        if "INVALID_TYPE" in content:
            output_json({
                "account_id": args.account_id,
                "count": 0,
                "members": [],
                "warning": "AccountTeamMember object not available in this org.",
            }, args.pretty)
        else:
            raise


def main():
    # Shared parent parser for --pretty flag
    pretty_parser = argparse.ArgumentParser(add_help=False)
    pretty_parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON output"
    )

    parser = argparse.ArgumentParser(
        description="Salesforce Account operations (read-only)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[pretty_parser],
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # describe
    describe_parser = subparsers.add_parser(
        "describe", help="Describe Account object fields",
        parents=[pretty_parser],
    )
    describe_parser.add_argument(
        "--filter", help="Filter fields by label keyword (case-insensitive)"
    )

    # my-accounts
    subparsers.add_parser(
        "my-accounts", help="List accounts where you are on the account team",
        parents=[pretty_parser],
    )

    # account-detail
    detail_parser = subparsers.add_parser(
        "account-detail", help="Get account details by ID",
        parents=[pretty_parser],
    )
    detail_parser.add_argument(
        "--account-id", required=True, help="Salesforce Account ID (18-char)"
    )

    # team-members
    team_parser = subparsers.add_parser(
        "team-members", help="List team members for an account",
        parents=[pretty_parser],
    )
    team_parser.add_argument(
        "--account-id", required=True, help="Salesforce Account ID (18-char)"
    )

    args = parser.parse_args()

    try:
        sf = get_client()

        commands = {
            "describe": cmd_describe,
            "my-accounts": cmd_my_accounts,
            "account-detail": cmd_account_detail,
            "team-members": cmd_team_members,
        }
        commands[args.command](sf, args)
        sys.exit(0)

    except FileNotFoundError as e:
        output_error("credentials_not_found", str(e))
        sys.exit(1)

    except Exception as e:
        output_error("unknown", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
