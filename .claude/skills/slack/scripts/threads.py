#!/usr/bin/env python3
"""
Slack thread operations tool.

Read thread replies for a message.

Usage:
    threads.py replies --channel CHAN_ID --ts THREAD_TS [options]

Examples:
    threads.py replies --channel C01234ABCDE --ts 1704067200.123456
    threads.py replies --channel C01234ABCDE --ts 1704067200.123456 --limit 100
"""

import argparse
import json
import sys
from pathlib import Path

# Add current directory to path to import slack_client
sys.path.insert(0, str(Path(__file__).parent))

from slack_client import get_client, handle_api_call


def cmd_replies(args):
    """Get all replies in a thread."""
    client = get_client()

    response = handle_api_call(
        client.conversations_replies,
        channel=args.channel,
        ts=args.ts,
        limit=args.limit
    )

    if args.pretty:
        print(json.dumps(response.data, indent=2))
    else:
        print(json.dumps(response.data))


def main():
    parser = argparse.ArgumentParser(
        description='Slack thread operations',
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

    # Replies subcommand
    replies_parser = subparsers.add_parser('replies', help='Get thread replies', parents=[pretty_parser])
    replies_parser.add_argument(
        '--channel',
        required=True,
        help='Channel ID (e.g., C01234ABCDE)'
    )
    replies_parser.add_argument(
        '--ts',
        required=True,
        help='Thread timestamp (e.g., 1704067200.123456)'
    )
    replies_parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='Maximum number of replies to return (default: 100)'
    )

    args = parser.parse_args()

    try:
        if args.command == 'replies':
            cmd_replies(args)

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
