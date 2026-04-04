#!/usr/bin/env python3
"""
Jira client with ~/.fe-skills/.env authentication support.

Provides get_client() for authenticated Jira API access and handle_api_call()
for structured error handling. Auth uses basic_auth from ATLASSIAN_EMAIL and
ATLASSIAN_TOKEN in ~/.fe-skills/.env, configured by /atlassian-setup.
"""

import json
import sys
from pathlib import Path
from typing import Any, Callable

from jira import JIRA, JIRAError
from jira.resources import Resource


# Constants
JIRA_SERVER = "https://coreweave.atlassian.net"
DEFAULT_PROJECT = "WB"
CUSTOMER_FIELD = "customfield_16678"
ENG_TEAM_FIELD = "customfield_16680"

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


def escape_jql_string(value: str) -> str:
    """Escape a value for safe interpolation inside a JQL double-quoted string."""
    return value.replace('\\', '\\\\').replace('"', '\\"')


def get_client() -> JIRA:
    """
    Create a JIRA client using ~/.fe-skills/.env credentials.

    Reads ATLASSIAN_EMAIL and ATLASSIAN_TOKEN from ~/.fe-skills/.env.
    These are configured by /atlassian-setup.

    Returns:
        JIRA client configured with basic auth

    Raises:
        FileNotFoundError: If credentials are missing
        ValueError: If credentials are incomplete
    """
    login = _load_credential('ATLASSIAN_EMAIL')
    password = _load_credential('ATLASSIAN_TOKEN')

    if not login or not password:
        raise FileNotFoundError(
            "ATLASSIAN_EMAIL and/or ATLASSIAN_TOKEN not found in ~/.fe-skills/.env. "
            "Run /atlassian-setup first."
        )

    return JIRA(server=JIRA_SERVER, basic_auth=(login, password))


def handle_api_call(api_func: Callable, *args, **kwargs) -> Any:
    """
    Wrapper for Jira API calls with structured error handling.

    API tokens don't expire, so no credential refresh is needed. This wrapper
    provides clear error messages for common failure modes.

    Args:
        api_func: The Jira SDK method to call
        *args, **kwargs: Arguments to pass to api_func

    Returns:
        Result from api_func

    Raises:
        JIRAError: Re-raised with clear error messages
        Exception: For other errors
    """
    try:
        return api_func(*args, **kwargs)
    except JIRAError as e:
        if e.status_code == 401:
            raise JIRAError(
                status_code=401,
                text="Authentication failed. Check ATLASSIAN_EMAIL/ATLASSIAN_TOKEN in ~/.fe-skills/.env. "
                     "Run /atlassian-setup to reconfigure."
            )
        elif e.status_code == 403:
            raise JIRAError(
                status_code=403,
                text=f"Permission denied: {e.text}"
            )
        elif e.status_code == 404:
            raise JIRAError(
                status_code=404,
                text=f"Not found: {e.text}"
            )
        raise


def serialize_resource(obj: Any) -> Any:
    """
    Recursively convert Jira Resource objects to JSON-serializable dicts.

    The jira library returns Resource objects instead of plain dicts.
    This function uses the .raw property to convert them.

    Args:
        obj: A Resource, dict, list, or primitive value

    Returns:
        JSON-serializable equivalent
    """
    if isinstance(obj, Resource):
        return obj.raw
    elif isinstance(obj, dict):
        return {k: serialize_resource(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_resource(item) for item in obj]
    return obj


def output_json(data: Any, pretty: bool = False) -> None:
    """Print JSON to stdout."""
    if pretty:
        print(json.dumps(data, indent=2, default=str))
    else:
        print(json.dumps(data, default=str))


def output_error(error_type: str, message: str) -> None:
    """Print structured error JSON to stderr."""
    import sys
    print(json.dumps({
        "ok": False,
        "error": error_type,
        "message": message
    }), file=sys.stderr)
