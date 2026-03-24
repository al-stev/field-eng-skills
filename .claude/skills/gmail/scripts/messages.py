#!/usr/bin/env python3
"""
Gmail message operations tool.

Search messages and read individual messages via Apps Script backend.

Usage:
    messages.py search --query "QUERY" [options]    Search for messages
    messages.py get --id MESSAGE_ID [options]        Get a specific message

Examples:
    messages.py search --query "from:user@example.com" --max-results 20
    messages.py get --id 18d4f2a3b5c6e7f8
    messages.py get --id 18d4f2a3b5c6e7f8 --format metadata
"""

import argparse
import json
import sys
from pathlib import Path

# Add current directory to path to import gmail_client
sys.path.insert(0, str(Path(__file__).parent))

from gmail_client import api_call, handle_api_call


def cmd_search(args):
    """Search for messages."""
    def do_search():
        params = {
            'query': args.query,
            'maxResults': str(args.max_results),
        }
        if args.start:
            params['start'] = str(args.start)
        return api_call('search', **params)

    result = handle_api_call(do_search)

    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


def cmd_get(args):
    """Get a specific message by ID."""
    def do_get():
        return api_call('getMessage', id=args.id, format=args.format)

    result = handle_api_call(do_get)

    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


def main():
    parser = argparse.ArgumentParser(
        description='Gmail message operations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Search query operators (include in --query):
  from:user@example.com    Messages from a sender
  to:me                    Messages sent to you
  subject:meeting          Subject line contains term
  is:unread                Unread messages
  is:starred               Starred messages
  label:INBOX              Messages with a label
  has:attachment            Messages with attachments
  after:2026/01/01         Messages after a date
  before:2026/02/01        Messages before a date
  newer_than:7d            Messages newer than N days
  older_than:30d           Messages older than N days
  filename:pdf             Attachments by filename

Combine operators: "from:user@example.com after:2026/01/01 has:attachment"
        """
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # Search subcommand
    search_parser = subparsers.add_parser('search', help='Search for messages')
    search_parser.add_argument(
        '--query',
        required=True,
        help='Gmail search query (supports Gmail search operators)'
    )
    search_parser.add_argument(
        '--max-results',
        type=int,
        default=20,
        help='Maximum number of results (default: 20)'
    )
    search_parser.add_argument(
        '--start',
        type=int,
        default=0,
        help='Start offset for pagination (default: 0)'
    )
    search_parser.add_argument(
        '--pretty',
        action='store_true',
        help='Pretty-print JSON output'
    )

    # Get subcommand
    get_parser = subparsers.add_parser('get', help='Get a specific message')
    get_parser.add_argument(
        '--id',
        required=True,
        help='Message ID'
    )
    get_parser.add_argument(
        '--format',
        default='full',
        choices=['minimal', 'metadata', 'full'],
        help='Response format (default: full)'
    )
    get_parser.add_argument(
        '--pretty',
        action='store_true',
        help='Pretty-print JSON output'
    )

    args = parser.parse_args()

    try:
        if args.command == 'search':
            cmd_search(args)
        elif args.command == 'get':
            cmd_get(args)

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
