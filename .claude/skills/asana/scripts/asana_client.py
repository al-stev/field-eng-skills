#!/usr/bin/env python3
"""
Asana client with Personal Access Token authentication.

Provides get_client() for authenticated Asana API access and helpers
for URL parsing, serialization, and structured output. Auth uses a PAT
from ~/.tsm-ai/.env configured by /asana-setup.
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import asana


# Constants
# Updated during /asana-setup with the user's workspace GID.
# Can also be overridden via ASANA_WORKSPACE_GID environment variable.
_ASANA_WORKSPACE_GID_DEFAULT = "1208076155392173"
WORKSPACE_GID = os.environ.get("ASANA_WORKSPACE_GID", _ASANA_WORKSPACE_GID_DEFAULT)
DEFAULT_TEAM_GID = os.environ.get("ASANA_DEFAULT_TEAM_GID", "1211862347384669")
DEFAULT_LIMIT = 100

TSM_ENV = Path.home() / '.tsm-ai' / '.env'


def get_workspace_gid() -> str:
    """
    Get the Asana workspace GID.

    Resolution order:
      1. ASANA_WORKSPACE_GID environment variable (if set)
      2. Hardcoded default in this file (updated during /asana-setup)

    Returns:
        Workspace GID string

    Raises:
        ValueError: If workspace GID is not configured
    """
    if WORKSPACE_GID and WORKSPACE_GID != "REPLACE_AFTER_SETUP":
        return WORKSPACE_GID
    raise ValueError(
        "Workspace GID not configured. Run /asana-setup to discover and set "
        "your workspace GID, or set ASANA_WORKSPACE_GID environment variable."
    )


def _load_credential(key: str) -> str | None:
    """Read a single value from ~/.tsm-ai/.env."""
    if not TSM_ENV.exists():
        return None
    for line in TSM_ENV.read_text().splitlines():
        if line.startswith(f'{key}='):
            return line.split('=', 1)[1]
    return None


def get_client() -> asana.ApiClient:
    """
    Create an authenticated Asana API client using ~/.tsm-ai/.env credentials.

    Reads ASANA_TOKEN from ~/.tsm-ai/.env.
    Configured by /asana-setup.

    Returns:
        asana.ApiClient configured with PAT authentication

    Raises:
        FileNotFoundError: If credentials are missing
    """
    token = _load_credential('ASANA_TOKEN')

    if not token:
        raise FileNotFoundError(
            "ASANA_TOKEN not found in ~/.tsm-ai/.env. "
            "Run /asana-setup first."
        )

    configuration = asana.Configuration()
    configuration.access_token = token

    return asana.ApiClient(configuration)


def handle_api_call(api_func, *args, **kwargs) -> Any:
    """
    Wrapper for Asana API calls with structured error handling.

    PATs do not expire, so no auto-refresh is needed.
    """
    try:
        return api_func(*args, **kwargs)
    except asana.rest.ApiException as e:
        if e.status == 401:
            raise Exception(
                "Authentication failed. Check ASANA_TOKEN in ~/.tsm-ai/.env. "
                "Run /asana-setup to reconfigure."
            )
        if e.status == 403:
            raise Exception(
                f"Permission denied (403). You may not have access to this resource. "
                f"Details: {e.body}"
            )
        if e.status == 404:
            raise Exception(
                f"Resource not found (404). Check that the GID is correct. "
                f"Details: {e.body}"
            )
        raise


def parse_asana_url(url: str) -> dict:
    """
    Extract GIDs from an Asana URL.

    Supports:
        New: https://app.asana.com/1/<ws_gid>/project/<project_gid>/list/<item_gid>
        Old: https://app.asana.com/0/<project_gid>/<task_gid>

    Returns:
        Dict with keys: project_gid, and optionally workspace_gid, task_gid, view_type

    Raises:
        ValueError: If URL doesn't match expected patterns
    """
    # New format: /1/<ws_gid>/project/<project_gid>/<view>/<item_gid>
    new_pattern = r'app\.asana\.com/1/(\d+)/project/(\d+)(?:/(list|board|timeline|calendar)(?:/(\d+))?)?'
    match = re.search(new_pattern, url)
    if match:
        result = {
            "workspace_gid": match.group(1),
            "project_gid": match.group(2),
        }
        if match.group(3):
            result["view_type"] = match.group(3)
        if match.group(4):
            result["focused_gid"] = match.group(4)
        return result

    # Old format: /0/<project_gid>/<task_gid>
    old_pattern = r'app\.asana\.com/0/(\d+)(?:/(\d+))?'
    match = re.search(old_pattern, url)
    if match:
        result = {"project_gid": match.group(1)}
        if match.group(2):
            result["task_gid"] = match.group(2)
        return result

    raise ValueError(
        f"Cannot parse Asana URL: {url}\n"
        f"Expected: https://app.asana.com/1/<ws>/project/<project>/list/... "
        f"or https://app.asana.com/0/<project>/<task>"
    )


def collect_pages(generator, limit: int | None = None) -> list:
    """
    Collect results from an Asana SDK generator (handles pagination).

    Args:
        generator: Asana SDK paginated generator
        limit: Maximum number of results to collect (None = all)

    Returns:
        List of result dicts
    """
    results = []
    for item in generator:
        results.append(item)
        if limit and len(results) >= limit:
            break
    return results


def serialize_project(project: dict) -> dict:
    """Convert an Asana project response to a clean dict."""
    result = {
        "gid": project.get("gid"),
        "name": project.get("name"),
        "url": f"https://app.asana.com/0/{project.get('gid')}" if project.get("gid") else None,
    }
    # Include optional fields if present
    for field in [
        "archived", "color", "created_at", "modified_at",
        "due_on", "start_on", "notes", "current_status_update",
        "default_view", "privacy_setting",
    ]:
        if field in project and project[field] is not None:
            result[field] = project[field]

    if "owner" in project and project["owner"]:
        result["owner"] = {
            "gid": project["owner"].get("gid"),
            "name": project["owner"].get("name"),
        }

    if "team" in project and project["team"]:
        result["team"] = {
            "gid": project["team"].get("gid"),
            "name": project["team"].get("name"),
        }

    if "custom_fields" in project and project["custom_fields"]:
        result["custom_fields"] = _serialize_custom_fields(project["custom_fields"])

    return result


def serialize_section(section: dict) -> dict:
    """Convert an Asana section response to a clean dict."""
    return {
        "gid": section.get("gid"),
        "name": section.get("name"),
    }


def serialize_task(task: dict) -> dict:
    """Convert an Asana task response to a clean dict."""
    result = {
        "gid": task.get("gid"),
        "name": task.get("name"),
        "url": f"https://app.asana.com/0/0/{task.get('gid')}" if task.get("gid") else None,
    }
    for field in [
        "completed", "completed_at", "created_at", "modified_at",
        "due_on", "due_at", "start_on", "start_at",
        "notes", "num_subtasks", "approval_status", "resource_subtype",
    ]:
        if field in task and task[field] is not None:
            result[field] = task[field]

    if "assignee" in task and task["assignee"]:
        result["assignee"] = {
            "gid": task["assignee"].get("gid"),
            "name": task["assignee"].get("name"),
        }

    if "memberships" in task and task["memberships"]:
        result["memberships"] = [
            {
                "project": {
                    "gid": m.get("project", {}).get("gid"),
                    "name": m.get("project", {}).get("name"),
                } if m.get("project") else None,
                "section": {
                    "gid": m.get("section", {}).get("gid"),
                    "name": m.get("section", {}).get("name"),
                } if m.get("section") else None,
            }
            for m in task["memberships"]
        ]

    if "custom_fields" in task and task["custom_fields"]:
        result["custom_fields"] = _serialize_custom_fields(task["custom_fields"])

    return result


def _serialize_custom_fields(custom_fields: list) -> list:
    """Serialize custom fields to a clean list of dicts."""
    results = []
    for cf in custom_fields:
        entry = {
            "gid": cf.get("gid"),
            "name": cf.get("name"),
            "type": cf.get("type"),
        }
        # Extract display value based on field type
        if cf.get("display_value") is not None:
            entry["display_value"] = cf["display_value"]
        elif cf.get("text_value") is not None:
            entry["value"] = cf["text_value"]
        elif cf.get("number_value") is not None:
            entry["value"] = cf["number_value"]
        elif cf.get("enum_value") is not None:
            entry["value"] = cf["enum_value"].get("name")
        elif cf.get("multi_enum_values"):
            entry["value"] = [v.get("name") for v in cf["multi_enum_values"]]
        elif cf.get("date_value") is not None:
            entry["value"] = cf["date_value"]
        else:
            entry["value"] = None
        results.append(entry)
    return results


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
