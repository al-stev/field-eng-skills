#!/usr/bin/env python3
"""
Google Calendar listing tool.

List all calendars (owned + subscribed) via Apps Script backend.

Usage:
    calendars.py list    List all calendars

Examples:
    calendars.py list
    calendars.py list --pretty
"""

import argparse
import json
import sys
from pathlib import Path

# Add current directory to path to import gcalendar_client
sys.path.insert(0, str(Path(__file__).parent))

from gcalendar_client import api_call, handle_api_call


def cmd_list(args):
    """List all calendars."""
    def do_list():
        return api_call('listCalendars')

    result = handle_api_call(do_list)

    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


def main():
    parser = argparse.ArgumentParser(
        description='Google Calendar listing operations',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # List subcommand
    list_parser = subparsers.add_parser('list', help='List all calendars')
    list_parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON output')

    args = parser.parse_args()

    try:
        if args.command == 'list':
            cmd_list(args)

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
