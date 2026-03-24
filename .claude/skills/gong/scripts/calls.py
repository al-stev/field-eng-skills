#!/usr/bin/env python3
"""
Gong call operations: list, view, transcript, search, spotlight.

Uses authenticated session cookies to call Gong's internal web app API
endpoints directly. Falls back to CDP fetch for edge cases.

Usage:
    calls.py list [--limit N] [--pretty]
    calls.py view --call-id ID [--pretty]
    calls.py transcript --call-id ID [--pretty]
    calls.py spotlight --call-id ID [--pretty]
    calls.py search --query TEXT [--limit N] [--pretty]
    calls.py explore-cookies [--pretty]
    calls.py explore-api --url URL [--pretty]

Examples:
    calls.py list --limit 10 --pretty
    calls.py transcript --call-id 8714105745982611438 --pretty
    calls.py spotlight --call-id 8714105745982611438 --pretty
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from gong_client import (
    GONG_BASE_URL,
    WORKSPACE_ID,
    cdp_fetch,
    get_session,
    handle_api_call,
)


def cmd_list(args):
    """List recent calls (my calls)."""
    session = get_session()

    def api_call():
        url = f'{GONG_BASE_URL}/ajax/home/calls/my-calls'
        params = {'workspace-id': WORKSPACE_ID}
        response = session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    result = handle_api_call(api_call)

    # The response has a nested structure: { "status_code": { "call_id": {...} } }
    # Flatten into a list of calls sorted by startTime descending
    calls = []
    for status_group in result.values():
        if isinstance(status_group, dict):
            for call_id, call_data in status_group.items():
                if isinstance(call_data, dict) and 'id' in call_data:
                    calls.append(call_data)

    calls.sort(key=lambda c: c.get('startTime', ''), reverse=True)

    if args.limit:
        calls = calls[:args.limit]

    output = {
        'total': len(calls),
        'calls': calls,
    }

    if args.pretty:
        print(json.dumps(output, indent=2))
    else:
        print(json.dumps(output))


def cmd_view(args):
    """View call details (collaborators, shares, metadata)."""
    session = get_session()

    def api_call():
        call_id = args.call_id
        collaborators_url = f'{GONG_BASE_URL}/json/call/get-collaborators'
        collaborators = session.get(collaborators_url, params={'call-id': call_id})
        collaborators.raise_for_status()

        spotlight_url = f'{GONG_BASE_URL}/ajax/get-call-spotlight'
        spotlight = session.get(spotlight_url, params={
            'call-id': call_id,
            'token': '',
            'should-regenerate': 'false',
        })
        spotlight.raise_for_status()

        return {
            'call_id': call_id,
            'collaborators': collaborators.json(),
            'spotlight': spotlight.json(),
        }

    result = handle_api_call(api_call)

    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


def cmd_transcript(args):
    """Get full call transcript with word-level timing."""
    session = get_session()

    def api_call():
        url = f'{GONG_BASE_URL}/call/detailed-transcript'
        response = session.get(url, params={'call-id': args.call_id})
        response.raise_for_status()
        return response.json()

    result = handle_api_call(api_call)

    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


def cmd_transcript_text(args):
    """Get call transcript as plain text (speaker: text format)."""
    session = get_session()

    def api_call():
        url = f'{GONG_BASE_URL}/call/detailed-transcript'
        response = session.get(url, params={'call-id': args.call_id})
        response.raise_for_status()
        return response.json()

    result = handle_api_call(api_call)

    # Format as readable text
    title = result.get('callTitle', 'Untitled')
    when = result.get('when', '')
    organizer = result.get('callOrganizerName', '')
    customers = result.get('callCustomers', '')

    lines = []
    lines.append(f'Title: {title}')
    lines.append(f'Date: {when}')
    lines.append(f'Organizer: {organizer}')
    if customers:
        lines.append(f'Customers: {customers}')
    lines.append('')

    for monologue in result.get('monologues', []):
        speaker = monologue.get('speakerName', 'Unknown')
        text = monologue.get('text', '').strip()
        timestamp = monologue.get('timestampStr', '')
        if text:
            lines.append(f'[{timestamp}] {speaker}: {text}')

    output = '\n'.join(lines)

    if args.pretty:
        # Wrap in JSON for consistency
        print(json.dumps({'transcript': output}, indent=2))
    else:
        print(output)


def cmd_spotlight(args):
    """Get AI-generated call summary (brief, key points, next steps)."""
    session = get_session()

    def api_call():
        url = f'{GONG_BASE_URL}/ajax/get-call-spotlight'
        response = session.get(url, params={
            'call-id': args.call_id,
            'token': '',
            'should-regenerate': 'false',
        })
        response.raise_for_status()
        return response.json()

    result = handle_api_call(api_call)

    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


def cmd_search(args):
    """Search calls (uses the calls list and filters client-side)."""
    session = get_session()

    def api_call():
        url = f'{GONG_BASE_URL}/ajax/home/calls/my-calls'
        params = {'workspace-id': WORKSPACE_ID}
        response = session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    result = handle_api_call(api_call)

    # Flatten and search
    query_lower = args.query.lower()
    matches = []
    for status_group in result.values():
        if isinstance(status_group, dict):
            for call_id, call_data in status_group.items():
                if isinstance(call_data, dict) and 'id' in call_data:
                    title = call_data.get('title', '').lower()
                    owner = call_data.get('owner', '').lower()
                    if query_lower in title or query_lower in owner:
                        matches.append(call_data)

    matches.sort(key=lambda c: c.get('startTime', ''), reverse=True)

    if args.limit:
        matches = matches[:args.limit]

    output = {
        'query': args.query,
        'total': len(matches),
        'calls': matches,
    }

    if args.pretty:
        print(json.dumps(output, indent=2))
    else:
        print(json.dumps(output))


def cmd_explore_cookies(args):
    """List Gong cookies for debugging."""
    session = get_session()

    cookies = []
    for cookie in session.cookies:
        cookies.append({
            'name': cookie.name,
            'domain': cookie.domain,
            'value_preview': cookie.value[:20] + '...' if len(cookie.value) > 20 else cookie.value,
            'value_length': len(cookie.value),
        })

    result = {
        'cookie_count': len(cookies),
        'cookies': cookies,
    }

    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


def cmd_explore_api(args):
    """Fetch a Gong URL via CDP (Chrome navigation) for endpoint discovery."""
    def api_call():
        body = cdp_fetch(args.url)
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {
                'type': 'html',
                'content_length': len(body),
                'content_preview': body[:2000],
            }

    result = handle_api_call(api_call)

    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


def main():
    parser = argparse.ArgumentParser(
        description='Gong call operations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest='command', help='Subcommand')

    # list
    list_parser = subparsers.add_parser('list', help='List recent calls')
    list_parser.add_argument('--limit', type=int, default=25, help='Max results (default: 25)')
    list_parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON')
    list_parser.set_defaults(func=cmd_list)

    # view
    view_parser = subparsers.add_parser('view', help='View call details')
    view_parser.add_argument('--call-id', required=True, help='Gong call ID')
    view_parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON')
    view_parser.set_defaults(func=cmd_view)

    # transcript
    transcript_parser = subparsers.add_parser('transcript', help='Get full call transcript (JSON)')
    transcript_parser.add_argument('--call-id', required=True, help='Gong call ID')
    transcript_parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON')
    transcript_parser.set_defaults(func=cmd_transcript)

    # transcript-text
    text_parser = subparsers.add_parser('transcript-text', help='Get call transcript as plain text')
    text_parser.add_argument('--call-id', required=True, help='Gong call ID')
    text_parser.add_argument('--pretty', action='store_true', help='Wrap output in JSON')
    text_parser.set_defaults(func=cmd_transcript_text)

    # spotlight
    spotlight_parser = subparsers.add_parser('spotlight', help='Get AI-generated call summary')
    spotlight_parser.add_argument('--call-id', required=True, help='Gong call ID')
    spotlight_parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON')
    spotlight_parser.set_defaults(func=cmd_spotlight)

    # search
    search_parser = subparsers.add_parser('search', help='Search calls by keyword')
    search_parser.add_argument('--query', required=True, help='Search query')
    search_parser.add_argument('--limit', type=int, default=25, help='Max results (default: 25)')
    search_parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON')
    search_parser.set_defaults(func=cmd_search)

    # explore-cookies
    cookies_parser = subparsers.add_parser('explore-cookies', help='List Gong cookies for debugging')
    cookies_parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON')
    cookies_parser.set_defaults(func=cmd_explore_cookies)

    # explore-api
    api_parser = subparsers.add_parser('explore-api', help='Fetch a Gong URL via CDP')
    api_parser.add_argument('--url', required=True, help='Full URL to fetch via Chrome CDP')
    api_parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON')
    api_parser.set_defaults(func=cmd_explore_api)

    args = parser.parse_args()

    if not hasattr(args, 'func'):
        parser.print_help()
        sys.exit(1)

    try:
        args.func(args)
    except Exception as e:
        print(json.dumps({'error': str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
