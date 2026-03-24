#!/usr/bin/env python3
"""
Google Calendar event operations tool.

Search, view, create, update, and delete events via Apps Script backend.

Usage:
    events.py list --start-date DATE --end-date DATE [options]   List events in range
    events.py get --id EVENT_ID [options]                        Get event details
    events.py today [options]                                    List today's events
    events.py upcoming [--days N] [options]                      List upcoming events
    events.py create --title TITLE --start DATETIME --end DATETIME [options]
    events.py create-all-day --title TITLE --date DATE [options]
    events.py update --id EVENT_ID [options]                     Update an event
    events.py delete --id EVENT_ID [options]                     Delete an event

Examples:
    events.py today --pretty
    events.py upcoming --days 7
    events.py list --start-date 2026-02-13 --end-date 2026-02-20
    events.py get --id EVENT_ID
    events.py create --title "Team Standup" --start "2026-02-14T10:00:00" --end "2026-02-14T10:30:00"
    events.py create-all-day --title "PTO" --date 2026-02-14 --end-date 2026-02-15
    events.py update --id EVENT_ID --title "New Title"
    events.py delete --id EVENT_ID
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add current directory to path to import gcalendar_client
sys.path.insert(0, str(Path(__file__).parent))

from gcalendar_client import api_call, handle_api_call


def cmd_list(args):
    """List events in a date range."""
    def do_list():
        params = {
            'startDate': args.start_date,
            'endDate': args.end_date,
        }
        if args.calendar_id:
            params['calendarId'] = args.calendar_id
        if args.query:
            params['query'] = args.query
        return api_call('getEvents', **params)

    result = handle_api_call(do_list)

    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


def cmd_get(args):
    """Get a specific event by ID."""
    def do_get():
        params = {'id': args.id}
        if args.calendar_id:
            params['calendarId'] = args.calendar_id
        return api_call('getEvent', **params)

    result = handle_api_call(do_get)

    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


def cmd_today(args):
    """List today's events."""
    today = datetime.now().strftime('%Y-%m-%d')
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    def do_today():
        params = {
            'startDate': today,
            'endDate': tomorrow,
        }
        if args.calendar_id:
            params['calendarId'] = args.calendar_id
        return api_call('getEvents', **params)

    result = handle_api_call(do_today)

    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


def cmd_upcoming(args):
    """List upcoming events."""
    today = datetime.now().strftime('%Y-%m-%d')
    end = (datetime.now() + timedelta(days=args.days)).strftime('%Y-%m-%d')

    def do_upcoming():
        params = {
            'startDate': today,
            'endDate': end,
        }
        if args.calendar_id:
            params['calendarId'] = args.calendar_id
        return api_call('getEvents', **params)

    result = handle_api_call(do_upcoming)

    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


def cmd_create(args):
    """Create a new event."""
    def do_create():
        params = {
            'title': args.title,
            'startTime': args.start,
            'endTime': args.end,
        }
        if args.calendar_id:
            params['calendarId'] = args.calendar_id
        if args.description:
            params['description'] = args.description
        if args.location:
            params['location'] = args.location
        if args.guests:
            params['guests'] = args.guests
        return api_call('createEvent', **params)

    result = handle_api_call(do_create)

    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


def cmd_create_all_day(args):
    """Create an all-day event."""
    def do_create():
        params = {
            'title': args.title,
            'date': args.date,
        }
        if args.end_date:
            params['endDate'] = args.end_date
        if args.calendar_id:
            params['calendarId'] = args.calendar_id
        if args.description:
            params['description'] = args.description
        if args.location:
            params['location'] = args.location
        if args.guests:
            params['guests'] = args.guests
        return api_call('createAllDayEvent', **params)

    result = handle_api_call(do_create)

    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


def cmd_update(args):
    """Update an existing event."""
    def do_update():
        params = {'id': args.id}
        if args.calendar_id:
            params['calendarId'] = args.calendar_id
        if args.title:
            params['title'] = args.title
        if args.description is not None:
            params['description'] = args.description
        if args.location is not None:
            params['location'] = args.location
        if args.start:
            params['startTime'] = args.start
        if args.end:
            params['endTime'] = args.end
        return api_call('updateEvent', **params)

    result = handle_api_call(do_update)

    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


def cmd_delete(args):
    """Delete an event."""
    def do_delete():
        params = {'id': args.id}
        if args.calendar_id:
            params['calendarId'] = args.calendar_id
        return api_call('deleteEvent', **params)

    result = handle_api_call(do_delete)

    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


def main():
    parser = argparse.ArgumentParser(
        description='Google Calendar event operations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # List subcommand
    list_parser = subparsers.add_parser('list', help='List events in a date range')
    list_parser.add_argument('--start-date', required=True, help='Start date (ISO format, e.g. 2026-02-13)')
    list_parser.add_argument('--end-date', required=True, help='End date (ISO format, e.g. 2026-02-20)')
    list_parser.add_argument('--calendar-id', help='Calendar ID (default: primary calendar)')
    list_parser.add_argument('--query', help='Search query to filter events')
    list_parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON output')

    # Get subcommand
    get_parser = subparsers.add_parser('get', help='Get a specific event')
    get_parser.add_argument('--id', required=True, help='Event ID')
    get_parser.add_argument('--calendar-id', help='Calendar ID (default: primary calendar)')
    get_parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON output')

    # Today subcommand
    today_parser = subparsers.add_parser('today', help="List today's events")
    today_parser.add_argument('--calendar-id', help='Calendar ID (default: primary calendar)')
    today_parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON output')

    # Upcoming subcommand
    upcoming_parser = subparsers.add_parser('upcoming', help='List upcoming events')
    upcoming_parser.add_argument('--days', type=int, default=7, help='Number of days to look ahead (default: 7)')
    upcoming_parser.add_argument('--calendar-id', help='Calendar ID (default: primary calendar)')
    upcoming_parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON output')

    # Create subcommand
    create_parser = subparsers.add_parser('create', help='Create a new event')
    create_parser.add_argument('--title', required=True, help='Event title')
    create_parser.add_argument('--start', required=True, help='Start time (ISO format, e.g. 2026-02-14T10:00:00)')
    create_parser.add_argument('--end', required=True, help='End time (ISO format, e.g. 2026-02-14T11:00:00)')
    create_parser.add_argument('--calendar-id', help='Calendar ID (default: primary calendar)')
    create_parser.add_argument('--description', help='Event description')
    create_parser.add_argument('--location', help='Event location')
    create_parser.add_argument('--guests', help='Comma-separated guest emails')
    create_parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON output')

    # Create all-day subcommand
    allday_parser = subparsers.add_parser('create-all-day', help='Create an all-day event')
    allday_parser.add_argument('--title', required=True, help='Event title')
    allday_parser.add_argument('--date', required=True, help='Event date (ISO format, e.g. 2026-02-14)')
    allday_parser.add_argument('--end-date', help='End date for multi-day events (ISO format)')
    allday_parser.add_argument('--calendar-id', help='Calendar ID (default: primary calendar)')
    allday_parser.add_argument('--description', help='Event description')
    allday_parser.add_argument('--location', help='Event location')
    allday_parser.add_argument('--guests', help='Comma-separated guest emails')
    allday_parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON output')

    # Update subcommand
    update_parser = subparsers.add_parser('update', help='Update an event')
    update_parser.add_argument('--id', required=True, help='Event ID')
    update_parser.add_argument('--calendar-id', help='Calendar ID (default: primary calendar)')
    update_parser.add_argument('--title', help='New event title')
    update_parser.add_argument('--description', default=None, help='New event description')
    update_parser.add_argument('--location', default=None, help='New event location')
    update_parser.add_argument('--start', help='New start time (ISO format)')
    update_parser.add_argument('--end', help='New end time (ISO format)')
    update_parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON output')

    # Delete subcommand
    delete_parser = subparsers.add_parser('delete', help='Delete an event')
    delete_parser.add_argument('--id', required=True, help='Event ID')
    delete_parser.add_argument('--calendar-id', help='Calendar ID (default: primary calendar)')
    delete_parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON output')

    args = parser.parse_args()

    try:
        if args.command == 'list':
            cmd_list(args)
        elif args.command == 'get':
            cmd_get(args)
        elif args.command == 'today':
            cmd_today(args)
        elif args.command == 'upcoming':
            cmd_upcoming(args)
        elif args.command == 'create':
            cmd_create(args)
        elif args.command == 'create-all-day':
            cmd_create_all_day(args)
        elif args.command == 'update':
            cmd_update(args)
        elif args.command == 'delete':
            cmd_delete(args)

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
