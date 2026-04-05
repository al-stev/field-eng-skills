#!/usr/bin/env python3
"""
Confluence client with ~/.fe-skills/.env authentication support.

Provides get_client() for authenticated Confluence Cloud API access and
handle_api_call() for structured error handling. Auth uses basic_auth from
ATLASSIAN_EMAIL and ATLASSIAN_TOKEN in ~/.fe-skills/.env, configured by /atlassian-setup.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Callable

from atlassian import Confluence
from atlassian.errors import ApiError

# Suppress noisy library logging (e.g. "Can't find 'X' page on ...")
logging.getLogger("atlassian").setLevel(logging.CRITICAL)


# Constants
CONFLUENCE_URL = "https://coreweave.atlassian.net/wiki"
FE_SPACE_KEY = "FE"
FE_SPACE_ID = "681410596"
PERSONAL_SPACE_KEY = "~712020cfd6bd1badc345a895e7bcf488706f05"
PERSONAL_SPACE_ID = "658472966"

ENV_FILE = Path.home() / '.fe-skills' / '.env'

_env_perms_warned = False


def _check_env_permissions() -> None:
    """Warn once if ~/.fe-skills/.env has permissions more open than 600."""
    global _env_perms_warned
    if _env_perms_warned or not ENV_FILE.exists():
        return
    mode = ENV_FILE.stat().st_mode & 0o777
    if mode & 0o077:  # group or other has any access
        print(
            f"WARNING: {ENV_FILE} has permissions {oct(mode)} (expected 0o600). "
            f"Run: chmod 600 {ENV_FILE}",
            file=sys.stderr,
        )
        _env_perms_warned = True


def _load_credential(key: str) -> str | None:
    """Read a single value from ~/.fe-skills/.env."""
    if not ENV_FILE.exists():
        return None
    _check_env_permissions()
    for line in ENV_FILE.read_text().splitlines():
        if line.startswith(f'{key}='):
            return line.split('=', 1)[1]
    return None


def get_client() -> Confluence:
    """
    Create a Confluence client using ~/.fe-skills/.env credentials.

    Reads ATLASSIAN_EMAIL and ATLASSIAN_TOKEN from ~/.fe-skills/.env.
    These are configured by /atlassian-setup.

    Returns:
        Confluence client configured with basic auth for Cloud

    Raises:
        FileNotFoundError: If credentials are missing
        ValueError: If credentials are incomplete
    """
    # Prefer CONFLUENCE_EMAIL/CONFLUENCE_TOKEN (CoreWeave account with full permissions)
    # Fall back to ATLASSIAN_EMAIL/ATLASSIAN_TOKEN (W&B account, guest-level access)
    login = _load_credential('CONFLUENCE_EMAIL') or _load_credential('ATLASSIAN_EMAIL')
    password = _load_credential('CONFLUENCE_TOKEN') or _load_credential('ATLASSIAN_TOKEN')

    if not login or not password:
        raise FileNotFoundError(
            "Confluence credentials not found in ~/.fe-skills/.env. "
            "Set CONFLUENCE_EMAIL/CONFLUENCE_TOKEN (preferred) or ATLASSIAN_EMAIL/ATLASSIAN_TOKEN. "
            "Run /atlassian-setup first."
        )

    return Confluence(
        url=CONFLUENCE_URL,
        username=login,
        password=password,
        cloud=True,
    )


def handle_api_call(api_func: Callable, *args, **kwargs) -> Any:
    """
    Wrapper for Confluence API calls with structured error handling.

    API tokens don't expire, so no credential refresh is needed. This wrapper
    provides clear error messages for common failure modes.

    Args:
        api_func: The Confluence SDK method to call
        *args, **kwargs: Arguments to pass to api_func

    Returns:
        Result from api_func

    Raises:
        Exception: Re-raised with context
    """
    try:
        return api_func(*args, **kwargs)
    except ApiError as e:
        error_str = str(e)
        # Check for HTTP status codes via the response object if available
        status = None
        if hasattr(e, "response") and hasattr(e.response, "status_code"):
            status = e.response.status_code
        if status == 401 or "401" in error_str or "Unauthorized" in error_str:
            raise RuntimeError(
                "Authentication failed. Check ATLASSIAN_EMAIL/ATLASSIAN_TOKEN in ~/.fe-skills/.env. "
                "Run /atlassian-setup to reconfigure."
            ) from e
        elif status == 403 or "403" in error_str or "Forbidden" in error_str:
            raise RuntimeError(f"Permission denied: {error_str}") from e
        elif status == 404 or "no content with the given id" in error_str.lower():
            raise RuntimeError(f"Not found: {error_str}") from e
        elif status == 409 or "409" in error_str or "Conflict" in error_str:
            raise RuntimeError(
                f"Version conflict — re-fetch the page for the latest version: {error_str}"
            ) from e
        raise RuntimeError(f"Confluence API error: {error_str}") from e
    except Exception as e:
        raise


def create_page_v2(
    client: Confluence,
    space_id: str,
    title: str,
    body: str,
    parent_id: str | None = None,
    subtype: str = "live",
) -> dict:
    """
    Create a Confluence page using the v2 API.

    Uses POST /wiki/api/v2/pages which supports the ``subtype`` field for
    creating Live Docs (``subtype="live"``) or traditional pages
    (``subtype="page"``).

    Args:
        client: Authenticated Confluence client (used for session/auth)
        space_id: Numeric space ID (e.g. '282199076' for FE)
        title: Page title
        body: HTML content in Confluence storage format
        parent_id: Optional parent page or folder ID
        subtype: "live" (default) for Live Doc, "page" for traditional page

    Returns:
        Dict with the created page data from the v2 API
    """
    url = f"{CONFLUENCE_URL}/api/v2/pages"
    payload: dict[str, Any] = {
        "spaceId": space_id,
        "status": "current",
        "title": title,
        "body": {
            "representation": "storage",
            "value": body,
        },
    }
    if subtype:
        payload["subtype"] = subtype
    if parent_id:
        payload["parentId"] = str(parent_id)

    response = client._session.post(url, json=payload)
    if not response.ok:
        raise RuntimeError(
            f"Failed to create page (HTTP {response.status_code}): {response.text}"
        )
    return response.json()


def create_folder(client: Confluence, space_id: str, title: str, parent_id: str | None = None) -> dict:
    """
    Create a Confluence folder using the v2 API.

    The atlassian-python-api SDK doesn't support folders natively, so this
    makes a direct REST call to POST /wiki/api/v2/folders.

    Args:
        client: Authenticated Confluence client (used for session/auth)
        space_id: Numeric space ID (e.g. '282199076' for FE)
        title: Folder title
        parent_id: Parent folder or page ID

    Returns:
        Dict with folder id, title, and parentId
    """
    url = f"{CONFLUENCE_URL}/api/v2/folders"
    payload = {"spaceId": space_id, "title": title}
    if parent_id:
        payload["parentId"] = parent_id

    response = client._session.post(url, json=payload)
    if not response.ok:
        raise RuntimeError(
            f"Failed to create folder (HTTP {response.status_code}): {response.text}"
        )
    return response.json()


def move_page(client: Confluence, page_id: str, parent_id: str) -> dict:
    """
    Move a page under a new parent using the v2 API.

    The atlassian-python-api SDK's move_page method silently fails (returns
    None without effect). This uses PUT /wiki/api/v2/pages/{id} to set the
    parentId directly, which works reliably for both pages and folders.

    Args:
        client: Authenticated Confluence client (used for session/auth)
        page_id: Page ID to move
        parent_id: New parent page or folder ID

    Returns:
        Dict with the updated page data from the v2 API
    """
    # Fetch current version via v1 (reliable and fast)
    page = client.get_page_by_id(page_id, expand="version")
    version = page["version"]["number"]

    url = f"{CONFLUENCE_URL}/api/v2/pages/{page_id}"
    payload = {
        "id": str(page_id),
        "status": "current",
        "title": page["title"],
        "parentId": str(parent_id),
        "version": {
            "number": version + 1,
            "message": "Move page",
        },
    }
    response = client._session.put(url, json=payload)
    if not response.ok:
        raise RuntimeError(
            f"Failed to move page (HTTP {response.status_code}): {response.text}"
        )
    return response.json()


def get_children_via_cql(client: Confluence, parent_id: str, limit: int = 25) -> list[dict]:
    """
    List direct children of a page or folder using CQL.

    The v1 get_page_child_by_type only works for pages, not folders.
    CQL ``parent=ID`` returns direct children of both pages and folders.

    Args:
        client: Authenticated Confluence client (used for session/auth)
        parent_id: Parent page or folder ID
        limit: Maximum results to return

    Returns:
        List of CQL result dicts (content wrapped in search results)
    """
    response = client.cql(f"parent={parent_id}", limit=limit)
    results = response.get("results", []) if isinstance(response, dict) else []
    return [
        {
            "id": r.get("content", {}).get("id"),
            "title": r.get("content", {}).get("title"),
            "type": r.get("content", {}).get("type"),
            "status": r.get("content", {}).get("status"),
        }
        for r in results
    ]


def resolve_space(space: str | None) -> tuple[str, str]:
    """
    Resolve a space argument to (space_key, space_id).

    Args:
        space: "fe", "personal", or None (defaults to FE)

    Returns:
        Tuple of (space_key, space_id)
    """
    if space and space.lower() == "personal":
        return PERSONAL_SPACE_KEY, PERSONAL_SPACE_ID
    return FE_SPACE_KEY, FE_SPACE_ID


def output_json(data: Any, pretty: bool = False) -> None:
    """Print JSON to stdout."""
    if pretty:
        print(json.dumps(data, indent=2, default=str))
    else:
        print(json.dumps(data, default=str))


def output_error(error_type: str, message: str) -> None:
    """Print structured error JSON to stderr."""
    print(
        json.dumps({"ok": False, "error": error_type, "message": message}),
        file=sys.stderr,
    )
