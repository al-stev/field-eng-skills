#!/usr/bin/env python3
"""
Gmail label operations tool.

List all labels and get label details via Apps Script backend.

Usage:
    labels.py list                    List all labels
    labels.py get --name LABEL_NAME   Get a specific label

Examples:
    labels.py list
    labels.py get --name "Work"
"""

import argparse
import json
import sys
from pathlib import Path

# Add current directory to path to import gmail_client
sys.path.insert(0, str(Path(__file__).parent))

from gmail_client import api_call, handle_api_call


def cmd_list(args):
    """List all labels."""
    def do_list():
        return api_call('listLabels')

    result = handle_api_call(do_list)

    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


def cmd_get(args):
    """Get a specific label by name."""
    def do_get():
        return api_call('getLabel', name=args.name)

    result = handle_api_call(do_get)

    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


def main():
    parser = argparse.ArgumentParser(
        description='Gmail label operations',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # List subcommand
    list_parser = subparsers.add_parser('list', help='List all labels')
    list_parser.add_argument(
        '--pretty',
        action='store_true',
        help='Pretty-print JSON output'
    )

    # Get subcommand
    get_parser = subparsers.add_parser('get', help='Get a specific label')
    get_parser.add_argument(
        '--name',
        required=True,
        help='Label name (e.g., "Work", "Projects/Active")'
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
