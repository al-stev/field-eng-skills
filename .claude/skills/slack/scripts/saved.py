#!/usr/bin/env python3
"""
Slack saved items ("Save for later") tool.

Lists items saved via Slack's "Save for later" feature using the internal
saved.list API. Optionally hydrates each item with message content and
channel names.

Usage:
    saved.py list [--hydrate] [--count N] [--pretty]

Examples:
    saved.py list --pretty
    saved.py list --hydrate --pretty
    saved.py list --hydrate --count 5
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add current directory to path to import slack_client
sys.path.insert(0, str(Path(__file__).parent))

from slack_client import get_client, handle_api_call


def fetch_saved_items(client, count=25):
    """Fetch saved items via the internal saved.list API."""
    response = handle_api_call(
        client.api_call,
        "saved.list",
        params={"count": count},
    )
    return response


def hydrate_message(client, channel_id, ts):
    """Fetch message content for a saved item."""
    try:
        response = handle_api_call(
            client.conversations_history,
            channel=channel_id,
            latest=ts,
            inclusive=True,
            limit=1,
        )
        messages = response.get("messages", [])
        if messages:
            return messages[0]
    except Exception:
        pass
    return None


def resolve_channel(client, channel_id, cache):
    """Resolve a channel ID to name, using cache to avoid repeat lookups."""
    if channel_id in cache:
        return cache[channel_id]

    try:
        response = handle_api_call(
            client.conversations_info,
            channel=channel_id,
        )
        ch = response.get("channel", {})
        if ch.get("is_im"):
            # DM — resolve user name
            user_id = ch.get("user", "")
            try:
                user_resp = handle_api_call(client.users_info, user=user_id)
                user = user_resp.get("user", {})
                name = f"DM ({user.get('real_name', user.get('name', user_id))})"
            except Exception:
                name = f"DM ({user_id})"
        else:
            name = f"#{ch.get('name', channel_id)}"
        cache[channel_id] = name
        return name
    except Exception:
        cache[channel_id] = channel_id
        return channel_id


def ts_to_iso(unix_ts):
    """Convert a Unix timestamp to ISO 8601 string."""
    if not unix_ts:
        return None
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc).isoformat()


def cmd_list(args):
    client = get_client()

    response = fetch_saved_items(client, count=args.count)

    items = response.get("saved_items", [])
    counts = response.get("counts", {})

    if not args.hydrate:
        # Raw output with readable timestamps added
        output = {
            "ok": True,
            "counts": counts,
            "saved_items": [],
        }
        for item in items:
            enriched = dict(item)
            enriched["date_created_iso"] = ts_to_iso(item.get("date_created"))
            enriched["date_due_iso"] = ts_to_iso(item.get("date_due")) if item.get("date_due") else None
            output["saved_items"].append(enriched)

        if args.pretty:
            print(json.dumps(output, indent=2))
        else:
            print(json.dumps(output))
        return

    # Hydrated output — fetch message content and channel names
    channel_cache = {}
    hydrated_items = []

    for item in items:
        channel_id = item.get("item_id", "")
        ts = item.get("ts", "")

        channel_name = resolve_channel(client, channel_id, channel_cache)
        message = hydrate_message(client, channel_id, ts)

        entry = {
            "channel_id": channel_id,
            "channel_name": channel_name,
            "ts": ts,
            "date_saved": ts_to_iso(item.get("date_created")),
            "date_due": ts_to_iso(item.get("date_due")) if item.get("date_due") else None,
            "state": item.get("state", "unknown"),
            "is_archived": item.get("is_archived", False),
        }

        if message:
            entry["text"] = message.get("text", "")
            entry["user"] = message.get("user", "")
            profile = message.get("user_profile", {})
            entry["user_name"] = profile.get("display_name") or profile.get("real_name") or ""
            entry["permalink"] = (
                f"https://coreweave.slack.com/archives/{channel_id}/p{ts.replace('.', '')}"
            )

        hydrated_items.append(entry)

    output = {
        "ok": True,
        "counts": counts,
        "items": hydrated_items,
    }

    if args.pretty:
        print(json.dumps(output, indent=2))
    else:
        print(json.dumps(output))


def main():
    # Shared --pretty flag
    pretty_parser = argparse.ArgumentParser(add_help=False)
    pretty_parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON output"
    )

    parser = argparse.ArgumentParser(
        description="Slack saved items (Save for later)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list subcommand
    list_parser = subparsers.add_parser(
        "list",
        parents=[pretty_parser],
        help="List saved items",
    )
    list_parser.add_argument(
        "--count",
        type=int,
        default=25,
        help="Max items to return (default: 25)",
    )
    list_parser.add_argument(
        "--hydrate",
        action="store_true",
        help="Fetch message content and channel names for each item",
    )

    args = parser.parse_args()

    try:
        if args.command == "list":
            cmd_list(args)

        sys.exit(0)

    except FileNotFoundError as e:
        print(
            json.dumps(
                {"ok": False, "error": "credentials_not_found", "message": str(e)}
            ),
            file=sys.stderr,
        )
        sys.exit(1)

    except Exception as e:
        print(
            json.dumps({"ok": False, "error": "unknown", "message": str(e)}),
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
