#!/usr/bin/env python3
"""
Confluence page operations tool.

View, search, create, update, and delete pages in the CoreWeave Confluence
instance using the atlassian-python-api SDK.

Usage:
    pages.py get --id 123456
    pages.py search --title "Meeting Notes" [--space fe]
    pages.py cql --query 'space=FE AND title~"weekly"'
    pages.py children --id 123456
    pages.py spaces
    pages.py create --title "New Page" --body "<p>Content</p>" --parent-id 123
    pages.py update --id 123456 --title "Updated" --body "<p>New content</p>"
    pages.py delete --id 123456
    pages.py attach --id 123456 --file /path/to/file.pdf
    pages.py labels --id 123456 [--add label1] [--remove label2]
    pages.py comment --id 123456 --body "Comment text"
"""

import argparse
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).parent))

from confluence_client import (
    get_client,
    create_folder,
    create_page_v2,
    get_children_via_cql,
    move_page,
    handle_api_call,
    resolve_space,
    output_json,
    output_error,
    CONFLUENCE_URL,
)


def page_url(page_id: str | int, space_key: str | None = None, title: str | None = None) -> str:
    """Build a direct URL for a Confluence page."""
    if space_key:
        url = f"{CONFLUENCE_URL}/spaces/{space_key}/pages/{page_id}"
        if title:
            url += f"/{quote(str(title), safe='')}"
        return url
    return f"{CONFLUENCE_URL}/pages/{page_id}"


def summarize_page(page: dict) -> dict:
    """Extract key fields from a page response dict."""
    space_key = None
    space = page.get("space")
    if isinstance(space, dict):
        space_key = space.get("key")

    result = {
        "id": page.get("id"),
        "title": page.get("title"),
        "url": page_url(page.get("id"), space_key=space_key, title=page.get("title")),
        "status": page.get("status"),
        "type": page.get("type"),
    }
    version = page.get("version")
    if isinstance(version, dict):
        result["version"] = version.get("number")
    elif version is not None:
        result["version"] = version
    if space_key:
        result["space_key"] = space_key
    body = page.get("body")
    if isinstance(body, dict):
        storage = body.get("storage") or body.get("view")
        if isinstance(storage, dict):
            result["body"] = storage.get("value")
    return result


def cmd_get(args):
    """Get a single page by ID."""
    client = get_client()
    page = handle_api_call(client.get_page_by_id, args.id, expand="body.storage,version,space")
    output_json(summarize_page(page), args.pretty)


def cmd_search(args):
    """Search for pages by title within a space."""
    client = get_client()
    space_key, _ = resolve_space(args.space)

    pages = handle_api_call(
        client.get_page_by_title,
        space_key,
        args.title,
    )

    if pages is None:
        output_json({"query": args.title, "space": space_key, "count": 0, "pages": []}, args.pretty)
        return

    # get_page_by_title returns a single dict or None
    if isinstance(pages, dict):
        pages = [pages]

    result = {
        "query": args.title,
        "space": space_key,
        "count": len(pages),
        "pages": [summarize_page(p) for p in pages],
    }
    output_json(result, args.pretty)


def cmd_cql(args):
    """Search with CQL (Confluence Query Language)."""
    client = get_client()
    limit = args.limit or 25

    response = handle_api_call(client.cql, args.query, limit=limit)

    results = response.get("results", []) if isinstance(response, dict) else []
    result = {
        "cql": args.query,
        "count": len(results),
        "total": response.get("totalSize", len(results)) if isinstance(response, dict) else len(results),
        "results": [
            {
                "id": (cid := r.get("content", {}).get("id") if "content" in r else r.get("id")),
                "title": (ctitle := r.get("content", {}).get("title") if "content" in r else r.get("title")),
                "type": r.get("content", {}).get("type") if "content" in r else r.get("type"),
                "url": page_url(
                    cid,
                    space_key=(r.get("content", {}).get("space", {}) or {}).get("key") if "content" in r else None,
                    title=ctitle,
                ),
                "excerpt": r.get("excerpt"),
                "lastModified": r.get("lastModified"),
            }
            for r in results
        ],
    }
    output_json(result, args.pretty)


def _summarize_v2_page(page: dict) -> dict:
    """Extract key fields from a v2 API page response."""
    return {
        "id": page.get("id"),
        "title": page.get("title"),
        "url": page_url(page.get("id")),
        "status": page.get("status"),
        "type": page.get("type", "page"),
        "parentId": page.get("parentId"),
    }


def cmd_children(args):
    """List child pages of a page or folder."""
    client = get_client()
    limit = args.limit or 25

    # Try v1 API first (works for pages)
    children = handle_api_call(
        client.get_page_child_by_type,
        args.id,
        type="page",
        start=0,
        limit=limit,
    )

    pages = children if isinstance(children, list) else children.get("results", []) if isinstance(children, dict) else []

    if pages:
        result = {
            "parent_id": args.id,
            "count": len(pages),
            "children": [summarize_page(p) for p in pages],
        }
    else:
        # v1 returns empty for folders — fall back to CQL parent= query
        cql_children = get_children_via_cql(client, args.id, limit=limit)
        result = {
            "parent_id": args.id,
            "count": len(cql_children),
            "children": [_summarize_v2_page(p) for p in cql_children],
        }

    output_json(result, args.pretty)


def cmd_spaces(args):
    """List accessible spaces."""
    client = get_client()
    spaces = handle_api_call(client.get_all_spaces, start=0, limit=50)

    items = spaces.get("results", []) if isinstance(spaces, dict) else spaces if isinstance(spaces, list) else []

    result = {
        "count": len(items),
        "spaces": [
            {
                "id": s.get("id"),
                "key": s.get("key"),
                "name": s.get("name"),
                "type": s.get("type"),
            }
            for s in items
        ],
    }
    output_json(result, args.pretty)


def cmd_create(args):
    """Create a new page (Live Doc by default)."""
    client = get_client()
    _, space_id = resolve_space(args.space)

    page = create_page_v2(
        client,
        space_id=space_id,
        title=args.title,
        body=args.body,
        parent_id=args.parent_id,
        subtype=args.subtype,
    )

    output_json(
        {
            "id": page.get("id"),
            "title": page.get("title"),
            "url": page_url(page.get("id")),
            "status": page.get("status"),
            "subtype": page.get("subtype"),
            "parentId": page.get("parentId"),
        },
        args.pretty,
    )


def cmd_create_folder(args):
    """Create a folder using the Confluence v2 API."""
    client = get_client()
    _, space_id = resolve_space(args.space)

    folder = create_folder(
        client,
        space_id=space_id,
        title=args.title,
        parent_id=args.parent_id,
    )

    output_json(
        {
            "id": folder.get("id"),
            "title": folder.get("title"),
            "parentId": folder.get("parentId"),
        },
        args.pretty,
    )


def cmd_move_page(args):
    """Move a page under a new parent page or folder."""
    client = get_client()
    result = move_page(client, page_id=args.id, parent_id=args.parent_id)
    output_json(
        {
            "id": result.get("id"),
            "title": result.get("title"),
            "parentId": result.get("parentId"),
        },
        args.pretty,
    )


def cmd_update(args):
    """Update an existing page."""
    client = get_client()

    page = handle_api_call(
        client.update_page,
        page_id=args.id,
        title=args.title,
        body=args.body,
        representation="storage",
        minor_edit=args.minor,
    )

    output_json(summarize_page(page), args.pretty)


def cmd_delete(args):
    """Delete a page."""
    client = get_client()
    handle_api_call(client.remove_page, args.id)

    output_json({"id": args.id, "deleted": True}, args.pretty)


def cmd_attach(args):
    """Upload an attachment to a page."""
    client = get_client()
    filepath = Path(args.file)

    if not filepath.exists():
        output_error("file_not_found", f"File not found: {filepath}")
        sys.exit(1)

    result = handle_api_call(
        client.attach_file,
        filename=str(filepath),
        page_id=args.id,
    )

    if isinstance(result, dict):
        results = result.get("results", [result])
    elif isinstance(result, list):
        results = result
    else:
        results = []

    output_json(
        {
            "page_id": args.id,
            "attachments": [
                {
                    "id": a.get("id"),
                    "title": a.get("title"),
                    "mediaType": a.get("metadata", {}).get("mediaType") if isinstance(a.get("metadata"), dict) else None,
                }
                for a in results
            ],
        },
        args.pretty,
    )


def cmd_labels(args):
    """Add or remove labels on a page."""
    client = get_client()

    if args.add:
        for label in args.add:
            handle_api_call(client.set_page_label, args.id, label)

    if args.remove:
        for label in args.remove:
            handle_api_call(client.remove_page_label, args.id, label)

    labels = handle_api_call(client.get_page_labels, args.id)
    label_list = labels.get("results", []) if isinstance(labels, dict) else labels if isinstance(labels, list) else []

    output_json(
        {
            "page_id": args.id,
            "labels": [l.get("name") if isinstance(l, dict) else str(l) for l in label_list],
        },
        args.pretty,
    )


def cmd_comment(args):
    """Add a comment to a page."""
    client = get_client()
    comment = handle_api_call(client.add_comment, args.id, args.body)

    comment_data = {"page_id": args.id, "body": args.body}
    if isinstance(comment, dict):
        comment_data["id"] = comment.get("id")
    output_json(comment_data, args.pretty)


def main():
    pretty_parser = argparse.ArgumentParser(add_help=False)
    pretty_parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON output"
    )

    parser = argparse.ArgumentParser(
        description="Confluence page operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[pretty_parser],
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- Read operations ---

    # get
    get_parser = subparsers.add_parser("get", help="Get a page by ID", parents=[pretty_parser])
    get_parser.add_argument("--id", required=True, help="Page ID")

    # search
    search_parser = subparsers.add_parser("search", help="Search pages by title", parents=[pretty_parser])
    search_parser.add_argument("--title", required=True, help="Page title to search for")
    search_parser.add_argument("--space", help="Space: 'fe' (default) or 'personal'")

    # cql
    cql_parser = subparsers.add_parser("cql", help="Search with CQL", parents=[pretty_parser])
    cql_parser.add_argument("--query", required=True, help="CQL query string")
    cql_parser.add_argument("--limit", type=int, help="Max results (default: 25)")

    # children
    children_parser = subparsers.add_parser("children", help="List child pages", parents=[pretty_parser])
    children_parser.add_argument("--id", required=True, help="Parent page ID")
    children_parser.add_argument("--limit", type=int, help="Max results (default: 25)")

    # spaces
    subparsers.add_parser("spaces", help="List accessible spaces", parents=[pretty_parser])

    # --- Write operations ---

    # create
    create_parser = subparsers.add_parser("create", help="Create a page (Live Doc by default)", parents=[pretty_parser])
    create_parser.add_argument("--title", required=True, help="Page title")
    create_parser.add_argument("--body", required=True, help="Page body (HTML storage format)")
    create_parser.add_argument("--parent-id", help="Parent page or folder ID")
    create_parser.add_argument("--space", help="Space: 'fe' (default) or 'personal'")
    create_parser.add_argument("--subtype", default="live", choices=["live", "page"], help="Page subtype: 'live' (default) for Live Doc, 'page' for traditional")

    # create-folder
    create_folder_parser = subparsers.add_parser("create-folder", help="Create a folder", parents=[pretty_parser])
    create_folder_parser.add_argument("--title", required=True, help="Folder title")
    create_folder_parser.add_argument("--parent-id", required=True, help="Parent folder ID")
    create_folder_parser.add_argument("--space", help="Space: 'fe' (default) or 'personal'")

    # move-page
    move_parser = subparsers.add_parser("move-page", help="Move a page under a new parent", parents=[pretty_parser])
    move_parser.add_argument("--id", required=True, help="Page ID to move")
    move_parser.add_argument("--parent-id", required=True, help="New parent page or folder ID")

    # update
    update_parser = subparsers.add_parser("update", help="Update a page", parents=[pretty_parser])
    update_parser.add_argument("--id", required=True, help="Page ID")
    update_parser.add_argument("--title", required=True, help="Page title")
    update_parser.add_argument("--body", required=True, help="Page body (HTML storage format)")
    update_parser.add_argument("--minor", action="store_true", help="Mark as minor edit")

    # delete
    delete_parser = subparsers.add_parser("delete", help="Delete a page", parents=[pretty_parser])
    delete_parser.add_argument("--id", required=True, help="Page ID")

    # attach
    attach_parser = subparsers.add_parser("attach", help="Upload an attachment", parents=[pretty_parser])
    attach_parser.add_argument("--id", required=True, help="Page ID")
    attach_parser.add_argument("--file", required=True, help="Path to file to attach")

    # labels
    labels_parser = subparsers.add_parser("labels", help="Manage page labels", parents=[pretty_parser])
    labels_parser.add_argument("--id", required=True, help="Page ID")
    labels_parser.add_argument("--add", nargs="+", help="Labels to add")
    labels_parser.add_argument("--remove", nargs="+", help="Labels to remove")

    # comment
    comment_parser = subparsers.add_parser("comment", help="Add a comment", parents=[pretty_parser])
    comment_parser.add_argument("--id", required=True, help="Page ID")
    comment_parser.add_argument("--body", required=True, help="Comment text")

    args = parser.parse_args()

    try:
        commands = {
            "get": cmd_get,
            "search": cmd_search,
            "cql": cmd_cql,
            "children": cmd_children,
            "spaces": cmd_spaces,
            "create": cmd_create,
            "create-folder": cmd_create_folder,
            "move-page": cmd_move_page,
            "update": cmd_update,
            "delete": cmd_delete,
            "attach": cmd_attach,
            "labels": cmd_labels,
            "comment": cmd_comment,
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
