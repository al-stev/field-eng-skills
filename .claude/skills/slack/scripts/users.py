#!/usr/bin/env python3
"""
Slack user operations tool.

List users, get user info, and search for users by name.

Usage:
    users.py list [options]              List all users
    users.py info --user USER_ID         Get user information
    users.py search-name --name "NAME"   Search for users by display name or real name

Examples:
    users.py list --limit 500
    users.py info --user U01234ABCDE
    users.py search-name --name "David Silverio"
"""

import argparse
import json
import sys
from pathlib import Path

# Add current directory to path to import slack_client
sys.path.insert(0, str(Path(__file__).parent))

from slack_client import get_client, handle_api_call


def cmd_list(args):
    """List all users in the workspace."""
    client = get_client()

    all_users = []
    cursor = None

    while True:
        kwargs = {'limit': args.limit}
        if cursor:
            kwargs['cursor'] = cursor

        response = handle_api_call(
            client.users_list,
            **kwargs
        )

        all_users.extend(response.data.get('members', []))

        # Check for pagination
        next_cursor = response.data.get('response_metadata', {}).get('next_cursor', '')
        if not next_cursor:
            break

        cursor = next_cursor

        # Respect max_pages limit if set
        if args.max_pages and len(all_users) >= args.limit * args.max_pages:
            break

    result = {
        'ok': True,
        'members': all_users,
        'total_count': len(all_users)
    }

    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


def cmd_info(args):
    """Get information about a specific user."""
    client = get_client()

    response = handle_api_call(
        client.users_info,
        user=args.user
    )

    if args.pretty:
        print(json.dumps(response.data, indent=2))
    else:
        print(json.dumps(response.data))


def cmd_whoami(args):
    """Get the authenticated user's identity via auth.test."""
    client = get_client()

    response = handle_api_call(client.auth_test)

    result = {
        'ok': True,
        'user_id': response.data.get('user_id'),
        'user': response.data.get('user'),
        'team': response.data.get('team'),
        'team_id': response.data.get('team_id'),
    }

    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


def cmd_search_name(args):
    """Search for users by display name or real name."""
    client = get_client()

    # First, list all users
    all_users = []
    cursor = None

    while True:
        kwargs = {'limit': 200}
        if cursor:
            kwargs['cursor'] = cursor

        response = handle_api_call(
            client.users_list,
            **kwargs
        )

        all_users.extend(response.data.get('members', []))

        next_cursor = response.data.get('response_metadata', {}).get('next_cursor', '')
        if not next_cursor:
            break

        cursor = next_cursor

    # Search for matching users
    search_term = args.name.lower()
    matches = []

    for user in all_users:
        real_name = user.get('real_name', '').lower()
        display_name = user.get('profile', {}).get('display_name', '').lower()
        name = user.get('name', '').lower()

        if (search_term in real_name or
            search_term in display_name or
            search_term in name):
            matches.append(user)

    result = {
        'ok': True,
        'members': matches,
        'match_count': len(matches)
    }

    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


def main():
    parser = argparse.ArgumentParser(
        description='Slack user operations',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Shared --pretty flag via parent parser so it works in any position
    pretty_parser = argparse.ArgumentParser(add_help=False)
    pretty_parser.add_argument(
        '--pretty',
        action='store_true',
        help='Pretty-print JSON output'
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # List subcommand
    list_parser = subparsers.add_parser('list', help='List users', parents=[pretty_parser])
    list_parser.add_argument(
        '--limit',
        type=int,
        default=200,
        help='Results per page (default: 200)'
    )
    list_parser.add_argument(
        '--max-pages',
        type=int,
        help='Maximum number of pages to fetch (default: all pages)'
    )

    # Info subcommand
    info_parser = subparsers.add_parser('info', help='Get user information', parents=[pretty_parser])
    info_parser.add_argument(
        '--user',
        required=True,
        help='User ID (e.g., U01234ABCDE)'
    )

    # Whoami subcommand
    subparsers.add_parser('whoami', help='Get authenticated user identity', parents=[pretty_parser])

    # Search-name subcommand
    search_parser = subparsers.add_parser('search-name', help='Search for users by name', parents=[pretty_parser])
    search_parser.add_argument(
        '--name',
        required=True,
        help='Name to search for (matches real_name, display_name, or username)'
    )

    args = parser.parse_args()

    try:
        if args.command == 'list':
            cmd_list(args)
        elif args.command == 'info':
            cmd_info(args)
        elif args.command == 'whoami':
            cmd_whoami(args)
        elif args.command == 'search-name':
            cmd_search_name(args)

        sys.exit(0)

    except FileNotFoundError as e:
        print(json.dumps({
            "ok": False,
            "error": "credentials_not_found",
            "message": str(e)
        }), file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(json.dumps({
            "ok": False,
            "error": "unknown",
            "message": str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
