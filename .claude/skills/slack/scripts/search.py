#!/usr/bin/env python3
"""
Slack message search tool.

Search across all channels you have access to with support for modifiers like
in:#channel, from:@user, after:YYYY-MM-DD, etc.

Usage:
    search.py --query "SEARCH_TERMS" [options]

Examples:
    search.py --query "error in:#tsm-team after:2026-01-01" --count 20
    search.py --query "customer-name from:@dsilverio" --sort score
    search.py --query "deployment" --page 2
"""

import argparse
import json
import sys
from pathlib import Path

# Add current directory to path to import slack_client
sys.path.insert(0, str(Path(__file__).parent))

from slack_client import get_client, handle_api_call


def main():
    parser = argparse.ArgumentParser(
        description='Search Slack messages across all accessible channels',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Search modifiers (include in --query):
  in:#channel        Limit to a specific channel
  from:@user         Messages from a specific user
  before:YYYY-MM-DD  Messages before a date
  after:YYYY-MM-DD   Messages after a date
  during:YYYY-MM     Messages during a month
  has:link           Messages containing a URL
  has:reaction       Messages with emoji reactions

Examples:
  %(prog)s --query "error in:#tsm-team after:2026-01-01"
  %(prog)s --query "customer-name from:@dsilverio" --sort score
  %(prog)s --query "deployment has:reaction" --count 50
        """
    )

    parser.add_argument(
        '--query',
        required=True,
        help='Search query with optional modifiers'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=20,
        help='Number of results per page (default: 20)'
    )
    parser.add_argument(
        '--sort',
        default='timestamp',
        choices=['timestamp', 'score'],
        help='Sort by timestamp or relevance score (default: timestamp)'
    )
    parser.add_argument(
        '--sort-dir',
        default='desc',
        choices=['asc', 'desc'],
        help='Sort direction (default: desc)'
    )
    parser.add_argument(
        '--page',
        type=int,
        default=1,
        help='Page number, 1-indexed (default: 1)'
    )
    parser.add_argument(
        '--pretty',
        action='store_true',
        help='Pretty-print JSON output'
    )

    args = parser.parse_args()

    try:
        client = get_client()

        # Use the auth wrapper for automatic refresh
        response = handle_api_call(
            client.search_messages,
            query=args.query,
            count=args.count,
            sort=args.sort,
            sort_dir=args.sort_dir,
            page=args.page
        )

        # Output JSON to stdout
        if args.pretty:
            print(json.dumps(response.data, indent=2))
        else:
            print(json.dumps(response.data))

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
