#!/usr/bin/env python3
"""
Gmail thread operations tool.

List threads matching a query and read full thread conversations via Apps Script backend.

Usage:
    threads.py list --query "QUERY" [options]   List threads matching a query
    threads.py get --id THREAD_ID [options]      Get all messages in a thread

Examples:
    threads.py list --query "is:unread" --max-results 10
    threads.py get --id 18d4f2a3b5c6e7f8
"""

import argparse
import json
import sys
from pathlib import Path

# Add current directory to path to import gmail_client
sys.path.insert(0, str(Path(__file__).parent))

from gmail_client import api_call, handle_api_call


def cmd_list(args):
    """List threads matching a query."""
    def do_list():
        params = {
            'query': args.query,
            'maxResults': str(args.max_results),
        }
        if args.start:
            params['start'] = str(args.start)
        return api_call('listThreads', **params)

    result = handle_api_call(do_list)

    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


def cmd_get(args):
    """Get all messages in a thread."""
    def do_get():
        return api_call('getThread', id=args.id, format=args.format)

    result = handle_api_call(do_get)

    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


def main():
    parser = argparse.ArgumentParser(
        description='Gmail thread operations',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # List subcommand
    list_parser = subparsers.add_parser('list', help='List threads matching a query')
    list_parser.add_argument(
        '--query',
        required=True,
        help='Gmail search query'
    )
    list_parser.add_argument(
        '--max-results',
        type=int,
        default=20,
        help='Maximum number of results (default: 20)'
    )
    list_parser.add_argument(
        '--start',
        type=int,
        default=0,
        help='Start offset for pagination (default: 0)'
    )
    list_parser.add_argument(
        '--pretty',
        action='store_true',
        help='Pretty-print JSON output'
    )

    # Get subcommand
    get_parser = subparsers.add_parser('get', help='Get all messages in a thread')
    get_parser.add_argument(
        '--id',
        required=True,
        help='Thread ID'
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
        if args.command == 'list':
            cmd_list(args)
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
