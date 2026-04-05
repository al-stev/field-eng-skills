#!/usr/bin/env python3
"""
Confluence blog post operations tool.

List, view, create, update, and delete blog posts in the CoreWeave Confluence
instance using the atlassian-python-api SDK.

Usage:
    blogs.py list [--space personal] [--limit 10]
    blogs.py get --id 123456
    blogs.py create --title "Post Title" --body "<p>Content</p>" [--space personal]
    blogs.py update --id 123456 --title "Updated" --body "<p>New content</p>"
    blogs.py delete --id 123456
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from confluence_client import (
    get_client,
    handle_api_call,
    resolve_space,
    output_json,
    output_error,
    CONFLUENCE_URL,
)


def blog_url(post: dict) -> str:
    """Build a full URL for a Confluence blog post from API _links."""
    links = post.get("_links", {})
    base = links.get("base", CONFLUENCE_URL)
    webui = links.get("webui")
    if webui:
        return f"{base}{webui}"
    return f"{CONFLUENCE_URL}/pages/{post.get('id')}"


def summarize_blog(post: dict) -> dict:
    """Extract key fields from a blog post response dict."""
    result = {
        "id": post.get("id"),
        "title": post.get("title"),
        "url": blog_url(post),
        "status": post.get("status"),
        "type": post.get("type"),
    }
    version = post.get("version")
    if isinstance(version, dict):
        result["version"] = version.get("number")
    elif version is not None:
        result["version"] = version
    space = post.get("space")
    if isinstance(space, dict):
        result["space_key"] = space.get("key")
    body = post.get("body")
    if isinstance(body, dict):
        storage = body.get("storage") or body.get("view")
        if isinstance(storage, dict):
            result["body"] = storage.get("value")
    return result


def cmd_list(args):
    """List blog posts in a space."""
    client = get_client()
    space_key, _ = resolve_space(args.space)
    limit = args.limit or 10

    posts = handle_api_call(
        client.get_all_pages_from_space,
        space_key,
        start=0,
        limit=limit,
        content_type="blogpost",
        expand="version,space",
    )

    items = posts if isinstance(posts, list) else posts.get("results", []) if isinstance(posts, dict) else []

    result = {
        "space": space_key,
        "count": len(items),
        "posts": [summarize_blog(p) for p in items],
    }
    output_json(result, args.pretty)


def cmd_get(args):
    """Get a single blog post by ID."""
    client = get_client()
    post = handle_api_call(client.get_page_by_id, args.id, expand="body.storage,version,space")
    output_json(summarize_blog(post), args.pretty)


def cmd_create(args):
    """Create a new blog post."""
    client = get_client()
    space_key, _ = resolve_space(args.space)

    post = handle_api_call(
        client.create_page,
        space=space_key,
        title=args.title,
        body=args.body,
        type="blogpost",
        representation="storage",
    )

    post_id = post.get("id")
    if post_id and args.labels:
        for label in args.labels:
            handle_api_call(client.set_page_label, post_id, label)

    output_json(summarize_blog(post), args.pretty)


def cmd_update(args):
    """Update an existing blog post."""
    client = get_client()

    post = handle_api_call(
        client.update_page,
        page_id=args.id,
        title=args.title,
        body=args.body,
        type="blogpost",
        representation="storage",
    )

    output_json(summarize_blog(post), args.pretty)


def cmd_delete(args):
    """Delete a blog post."""
    client = get_client()
    handle_api_call(client.remove_page, args.id)

    output_json({"id": args.id, "deleted": True}, args.pretty)


def main():
    pretty_parser = argparse.ArgumentParser(add_help=False)
    pretty_parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON output"
    )

    parser = argparse.ArgumentParser(
        description="Confluence blog post operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[pretty_parser],
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- Read operations ---

    # list
    list_parser = subparsers.add_parser("list", help="List blog posts", parents=[pretty_parser])
    list_parser.add_argument("--space", help="Space: 'fe' (default) or 'personal'")
    list_parser.add_argument("--limit", type=int, help="Max results (default: 10)")

    # get
    get_parser = subparsers.add_parser("get", help="Get a blog post by ID", parents=[pretty_parser])
    get_parser.add_argument("--id", required=True, help="Blog post ID")

    # --- Write operations ---

    # create
    create_parser = subparsers.add_parser("create", help="Create a blog post", parents=[pretty_parser])
    create_parser.add_argument("--title", required=True, help="Blog post title")
    create_parser.add_argument("--body", required=True, help="Blog post body (HTML storage format)")
    create_parser.add_argument("--space", help="Space: 'fe' (default) or 'personal'")
    create_parser.add_argument("--labels", nargs="+", help="Labels to add after creation")

    # update
    update_parser = subparsers.add_parser("update", help="Update a blog post", parents=[pretty_parser])
    update_parser.add_argument("--id", required=True, help="Blog post ID")
    update_parser.add_argument("--title", required=True, help="Blog post title")
    update_parser.add_argument("--body", required=True, help="Blog post body (HTML storage format)")

    # delete
    delete_parser = subparsers.add_parser("delete", help="Delete a blog post", parents=[pretty_parser])
    delete_parser.add_argument("--id", required=True, help="Blog post ID")

    args = parser.parse_args()

    try:
        commands = {
            "list": cmd_list,
            "get": cmd_get,
            "create": cmd_create,
            "update": cmd_update,
            "delete": cmd_delete,
        }
        commands[args.command](args)
        sys.exit(0)

    except FileNotFoundError as e:
        output_error("credentials_not_found", str(e))
        sys.exit(1)

    except KeyError as e:
        output_error("credentials_missing", str(e))
        sys.exit(1)

    except RuntimeError as e:
        output_error("api_error", str(e))
        sys.exit(1)

    except Exception as e:
        output_error("unknown", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
