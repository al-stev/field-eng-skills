#!/usr/bin/env python3
"""
Slack channel operations tool.

List channels, get channel info, and read channel history.

Usage:
    channels.py list [options]           List public/private channels
    channels.py info --channel CHAN_ID   Get channel information
    channels.py history --channel CHAN_ID [options]  Read channel messages

Examples:
    channels.py list --types public_channel,private_channel --limit 200
    channels.py info --channel C01234ABCDE
    channels.py history --channel C01234ABCDE --limit 50
    channels.py history --channel C01234ABCDE --after 1704067200
"""

import argparse
import json
import sys
from pathlib import Path

# Add current directory to path to import slack_client
sys.path.insert(0, str(Path(__file__).parent))

from slack_client import get_client, handle_api_call


def cmd_list(args):
    """List public and/or private channels."""
    client = get_client()

    response = handle_api_call(
        client.conversations_list,
        types=args.types,
        limit=args.limit,
        exclude_archived=args.exclude_archived
    )

    if args.pretty:
        print(json.dumps(response.data, indent=2))
    else:
        print(json.dumps(response.data))


def cmd_info(args):
    """Get information about a specific channel."""
    client = get_client()

    response = handle_api_call(
        client.conversations_info,
        channel=args.channel
    )

    if args.pretty:
        print(json.dumps(response.data, indent=2))
    else:
        print(json.dumps(response.data))


def cmd_history(args):
    """Read message history from a channel."""
    client = get_client()

    kwargs = {
        'channel': args.channel,
        'limit': args.limit
    }

    if args.oldest:
        kwargs['oldest'] = str(args.oldest)
    if args.latest:
        kwargs['latest'] = str(args.latest)
    if args.inclusive is not None:
        kwargs['inclusive'] = args.inclusive

    response = handle_api_call(
        client.conversations_history,
        **kwargs
    )

    if args.pretty:
        print(json.dumps(response.data, indent=2))
    else:
        print(json.dumps(response.data))


def main():
    parser = argparse.ArgumentParser(
        description='Slack channel operations',
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
    list_parser = subparsers.add_parser('list', help='List channels', parents=[pretty_parser])
    list_parser.add_argument(
        '--types',
        default='public_channel,private_channel',
        help='Channel types (comma-separated): public_channel, private_channel (default: both)'
    )
    list_parser.add_argument(
        '--limit',
        type=int,
        default=200,
        help='Maximum number of channels to return (default: 200)'
    )
    list_parser.add_argument(
        '--exclude-archived',
        action='store_true',
        help='Exclude archived channels'
    )

    # Info subcommand
    info_parser = subparsers.add_parser('info', help='Get channel information', parents=[pretty_parser])
    info_parser.add_argument(
        '--channel',
        required=True,
        help='Channel ID (e.g., C01234ABCDE)'
    )

    # History subcommand
    history_parser = subparsers.add_parser('history', help='Read channel message history', parents=[pretty_parser])
    history_parser.add_argument(
        '--channel',
        required=True,
        help='Channel ID (e.g., C01234ABCDE)'
    )
    history_parser.add_argument(
        '--limit',
        type=int,
        default=20,
        help='Number of messages to return (default: 20)'
    )
    history_parser.add_argument(
        '--oldest',
        type=float,
        help='Unix timestamp - only messages after this time'
    )
    history_parser.add_argument(
        '--latest',
        type=float,
        help='Unix timestamp - only messages before this time'
    )
    history_parser.add_argument(
        '--inclusive',
        type=lambda x: x.lower() == 'true',
        help='Include messages with exact oldest/latest timestamps (true/false)'
    )

    args = parser.parse_args()

    try:
        if args.command == 'list':
            cmd_list(args)
        elif args.command == 'info':
            cmd_info(args)
        elif args.command == 'history':
            cmd_history(args)

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
