#!/usr/bin/env python3
"""
Asana write operations tool.

Create, update, complete, move tasks, set up projects and RAID projects,
manage portfolios, and multi-home tasks across projects.

Usage:
    mutate.py create --project-gid GID --name NAME [--section SECTION] [--assignee GID|me] [--due YYYY-MM-DD] [--priority High|Medium|Low] [--notes TEXT] [--pretty]
    mutate.py update --gid GID [--name NAME] [--due YYYY-MM-DD] [--notes TEXT] [--priority High|Medium|Low] [--assignee GID|me] [--pretty]
    mutate.py complete --gid GID [--pretty]
    mutate.py move --gid GID --section SECTION --project-gid GID [--pretty]
    mutate.py setup-project --name NAME [--team GID] [--pretty]
    mutate.py setup-raid-project --name NAME [--team GID] [--pretty]
    mutate.py add-project --task-gid GID --project-gid GID [--section SECTION] [--pretty]
    mutate.py create-master-portfolio --name NAME [--pretty]
    mutate.py setup-customer --name NAME --master-portfolio-gid GID [--team GID] [--se-owner-gid GID] [--account-exec-gid GID] [--deployment-type TYPE] [--health HEALTH] [--pretty]
    mutate.py delete-portfolio --gid GID [--pretty]
"""

import argparse
import sys
from pathlib import Path

# Add current directory to path to import asana_client
sys.path.insert(0, str(Path(__file__).parent))

import asana

from asana_client import (
    get_client,
    handle_api_call,
    get_workspace_gid,
    serialize_task,
    serialize_project,
    serialize_section,
    output_json,
    output_error,
)


# ---------------------------------------------------------------------------
# Priority custom field configuration
# Enterprise+ plan -- using existing workspace Priority field.
# GIDs discovered from Asana API (workspace field GID: 1208185034501267).
# ---------------------------------------------------------------------------
PRIORITY_FIELD_GID = "1208185034501267"
PRIORITY_OPTION_GIDS = {
    "HIGH": "1208185034501270",
    "MEDIUM": "1208185034501271",
    "LOW": "1208185034501272",
}

# Default team GID for Organization workspace project creation
DEFAULT_TEAM_GID = "1211862347384669"  # W&B EMEA Post-Sales

# ---------------------------------------------------------------------------
# RAID custom field definitions
# These are created at workspace level by setup-raid-project.
# GIDs are populated after first run and cached here for reference.
# Use get_or_create_raid_fields() to resolve GIDs at runtime.
# ---------------------------------------------------------------------------
RAID_FIELD_DEFINITIONS = [
    {
        "name": "Category",
        "resource_subtype": "enum",
        "enum_options": [
            {"name": "Risk", "color": "red"},
            {"name": "Assumption", "color": "yellow-orange"},
            {"name": "Issue", "color": "orange"},
            {"name": "Dependency", "color": "blue"},
        ],
    },
    {
        "name": "Impact",
        "resource_subtype": "enum",
        "enum_options": [
            {"name": "High", "color": "red"},
            {"name": "Medium", "color": "yellow-orange"},
            {"name": "Low", "color": "yellow-green"},
        ],
    },
    {
        "name": "Likelihood",
        "resource_subtype": "enum",
        "enum_options": [
            {"name": "High", "color": "red"},
            {"name": "Medium", "color": "yellow-orange"},
            {"name": "Low", "color": "yellow-green"},
        ],
    },
    {
        "name": "Status",
        "resource_subtype": "enum",
        "enum_options": [
            {"name": "Open", "color": "red"},
            {"name": "Accepted", "color": "yellow-orange"},
            {"name": "Closed", "color": "green"},
        ],
    },
    {
        "name": "Source",
        "resource_subtype": "text",
    },
    {
        "name": "Visibility",
        "resource_subtype": "enum",
        "enum_options": [
            {"name": "Internal", "color": "purple"},
            {"name": "Shared", "color": "blue"},
        ],
    },
]

# ---------------------------------------------------------------------------
# Portfolio custom field definitions
# These are created at workspace level by create-master-portfolio.
# Attached to the master portfolio for filtering/sorting customer rows.
# ---------------------------------------------------------------------------
PORTFOLIO_FIELD_DEFINITIONS = [
    {
        "name": "SE Owner",
        "resource_subtype": "people",
    },
    {
        "name": "Account Exec",
        "resource_subtype": "people",
    },
    {
        "name": "Deployment Type",
        "resource_subtype": "enum",
        "enum_options": [
            {"name": "SaaS", "color": "blue"},
            {"name": "Dedicated Cloud", "color": "purple"},
            {"name": "Server", "color": "orange"},
        ],
    },
    {
        "name": "Customer Health",
        "resource_subtype": "enum",
        "enum_options": [
            {"name": "Green", "color": "green"},
            {"name": "Amber", "color": "yellow-orange"},
            {"name": "Red", "color": "red"},
        ],
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def resolve_section_gid(sections_api, project_gid: str, section_name: str) -> str:
    """
    Look up a section GID by name within a project.

    Args:
        sections_api: Asana SectionsApi instance
        project_gid: Project to search in
        section_name: Section name to find (case-insensitive)

    Returns:
        Section GID string

    Raises:
        ValueError: If section not found
    """
    generator = handle_api_call(
        sections_api.get_sections_for_project,
        project_gid,
        {"opt_fields": "name"},
    )

    sections = []
    for section in generator:
        sections.append(section)
        if section.get("name", "").lower() == section_name.lower():
            return section["gid"]

    available = [s.get("name", "?") for s in sections]
    raise ValueError(
        f"Section '{section_name}' not found in project {project_gid}. "
        f"Available sections: {', '.join(available)}"
    )


def _get_priority_custom_fields(priority_str: str) -> dict | None:
    """
    Get custom_fields dict for priority if GIDs are configured.

    Accepts both legacy names (P0-P3) and workspace names (High/Medium/Low).
    Mapping: P0/P1 -> High, P2 -> Medium, P3 -> Low.

    Args:
        priority_str: Priority string (P0, P1, P2, P3, High, Medium, Low)

    Returns:
        Dict of {field_gid: option_gid} if configured, None otherwise
    """
    if not PRIORITY_FIELD_GID or not PRIORITY_OPTION_GIDS:
        return None

    # Map legacy P0-P3 to workspace High/Medium/Low
    legacy_map = {
        "P0": "HIGH",
        "P1": "HIGH",
        "P2": "MEDIUM",
        "P3": "LOW",
    }

    priority_upper = priority_str.upper()
    mapped = legacy_map.get(priority_upper, priority_upper)

    if mapped not in PRIORITY_OPTION_GIDS:
        return None

    return {PRIORITY_FIELD_GID: PRIORITY_OPTION_GIDS[mapped]}


def _apply_priority_to_name(name: str, priority_str: str) -> str:
    """
    Prepend priority prefix to task name (free plan fallback).
    Not used on Enterprise+ but retained for compatibility.

    Args:
        name: Task name
        priority_str: Priority string

    Returns:
        Name with priority prefix, e.g. "[High] Task name"
    """
    return f"[{priority_str}] {name}"


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_create(args):
    """Create a new task in a project."""
    print(f"Creating task '{args.name}' in project {args.project_gid}...", file=sys.stderr)

    api_client = get_client()
    tasks_api = asana.TasksApi(api_client)

    # Build task data
    task_data = {
        "name": args.name,
        "projects": [args.project_gid],
    }

    if args.assignee:
        task_data["assignee"] = args.assignee

    if args.due:
        task_data["due_on"] = args.due

    if args.notes:
        task_data["notes"] = args.notes

    # Handle priority
    if args.priority:
        custom_fields = _get_priority_custom_fields(args.priority)
        if custom_fields:
            task_data["custom_fields"] = custom_fields
        else:
            # Free plan fallback: prepend priority to name
            task_data["name"] = _apply_priority_to_name(task_data["name"], args.priority)

    task = handle_api_call(tasks_api.create_task, {"data": task_data}, {})

    # Move to specific section if requested
    if args.section:
        sections_api = asana.SectionsApi(api_client)
        section_gid = resolve_section_gid(sections_api, args.project_gid, args.section)
        handle_api_call(
            sections_api.add_task_for_section,
            section_gid,
            {"body": {"data": {"task": task["gid"]}}},
        )
        print(f"Moved to section '{args.section}'", file=sys.stderr)

    print(f"Created task {task['gid']}", file=sys.stderr)
    output_json(serialize_task(task), args.pretty)


def cmd_update(args):
    """Update an existing task."""
    print(f"Updating task {args.gid}...", file=sys.stderr)

    api_client = get_client()
    tasks_api = asana.TasksApi(api_client)

    # Only send fields that are provided
    task_data = {}

    if args.name is not None:
        task_data["name"] = args.name

    if args.due is not None:
        task_data["due_on"] = args.due

    if args.notes is not None:
        task_data["notes"] = args.notes

    if args.assignee is not None:
        task_data["assignee"] = args.assignee

    # Handle priority
    if args.priority is not None:
        custom_fields = _get_priority_custom_fields(args.priority)
        if custom_fields:
            task_data["custom_fields"] = custom_fields
        else:
            # Free plan fallback: need to update the name with priority prefix
            # First fetch current name if not already being updated
            if "name" not in task_data:
                current_task = handle_api_call(
                    tasks_api.get_task,
                    args.gid,
                    {"opt_fields": "name"},
                )
                current_name = current_task.get("name", "")
                # Remove existing priority prefix if present
                import re
                current_name = re.sub(r'^\[P[0-3]\]\s*', '', current_name)
                task_data["name"] = _apply_priority_to_name(current_name, args.priority)
            else:
                task_data["name"] = _apply_priority_to_name(task_data["name"], args.priority)

    if not task_data:
        output_error("invalid_input", "No fields to update. Provide at least one of: --name, --due, --notes, --priority, --assignee")
        sys.exit(1)

    task = handle_api_call(tasks_api.update_task, {"data": task_data}, args.gid, {})

    print(f"Updated task {args.gid}", file=sys.stderr)
    output_json(serialize_task(task), args.pretty)


def cmd_complete(args):
    """Mark a task as completed."""
    print(f"Completing task {args.gid}...", file=sys.stderr)

    api_client = get_client()
    tasks_api = asana.TasksApi(api_client)

    task = handle_api_call(tasks_api.update_task, {"data": {"completed": True}}, args.gid, {})

    print(f"Completed task {args.gid}", file=sys.stderr)
    output_json(serialize_task(task), args.pretty)


def cmd_move(args):
    """Move a task to a different section."""
    print(f"Moving task {args.gid} to section '{args.section}'...", file=sys.stderr)

    api_client = get_client()
    sections_api = asana.SectionsApi(api_client)

    section_gid = resolve_section_gid(sections_api, args.project_gid, args.section)

    handle_api_call(
        sections_api.add_task_for_section,
        section_gid,
        {"body": {"data": {"task": args.gid}}},
    )

    print(f"Moved task {args.gid} to '{args.section}' (section {section_gid})", file=sys.stderr)

    # Fetch and return updated task
    tasks_api = asana.TasksApi(api_client)
    task = handle_api_call(
        tasks_api.get_task,
        args.gid,
        {"opt_fields": "name,completed,assignee.name,due_on,memberships.section.name,memberships.project.name"},
    )
    output_json(serialize_task(task), args.pretty)


def _get_or_create_raid_fields(custom_fields_api, workspace_gid: str) -> dict:
    """
    Find existing RAID custom fields by name, or create them if missing.

    Checks workspace-level custom fields first to avoid duplicates.

    Args:
        custom_fields_api: Asana CustomFieldsApi instance
        workspace_gid: Workspace GID

    Returns:
        Dict mapping field name -> {"gid": str, "enum_options": {name: gid}}
    """
    # Fetch all workspace custom fields to check for existing ones
    existing_fields = {}
    generator = handle_api_call(
        custom_fields_api.get_custom_fields_for_workspace,
        workspace_gid,
        {"opt_fields": "name,type,resource_subtype,enum_options"},
    )
    for field in generator:
        existing_fields[field["name"]] = field

    result = {}
    for field_def in RAID_FIELD_DEFINITIONS:
        name = field_def["name"]

        if name in existing_fields:
            # Reuse existing field
            existing = existing_fields[name]
            field_info = {
                "gid": existing["gid"],
                "name": name,
                "enum_options": {},
            }
            for opt in existing.get("enum_options", []):
                if opt.get("enabled", True):
                    field_info["enum_options"][opt["name"]] = opt["gid"]
            result[name] = field_info
            print(f"  Found existing field: {name} (GID: {existing['gid']})", file=sys.stderr)
        else:
            # Create new field
            create_data = {
                "name": name,
                "resource_subtype": field_def["resource_subtype"],
                "workspace": workspace_gid,
            }
            if "enum_options" in field_def:
                create_data["enum_options"] = field_def["enum_options"]

            field = handle_api_call(
                custom_fields_api.create_custom_field,
                {"data": create_data},
                {},
            )
            field_info = {
                "gid": field["gid"],
                "name": name,
                "enum_options": {},
            }
            for opt in field.get("enum_options", []):
                if opt.get("enabled", True):
                    field_info["enum_options"][opt["name"]] = opt["gid"]
            result[name] = field_info
            print(f"  Created field: {name} (GID: {field['gid']})", file=sys.stderr)

    return result


def _get_or_create_portfolio_fields(custom_fields_api, workspace_gid: str) -> dict:
    """
    Find existing portfolio custom fields by name, or create them if missing.

    Follows same dedup pattern as _get_or_create_raid_fields.

    Args:
        custom_fields_api: Asana CustomFieldsApi instance
        workspace_gid: Workspace GID

    Returns:
        Dict mapping field name -> {"gid": str, "enum_options": {name: gid}}
    """
    # Fetch all workspace custom fields to check for existing ones
    existing_fields = {}
    generator = handle_api_call(
        custom_fields_api.get_custom_fields_for_workspace,
        workspace_gid,
        {"opt_fields": "name,type,resource_subtype,enum_options"},
    )
    for field in generator:
        existing_fields[field["name"]] = field

    result = {}
    for field_def in PORTFOLIO_FIELD_DEFINITIONS:
        name = field_def["name"]

        if name in existing_fields:
            # Reuse existing field
            existing = existing_fields[name]
            field_info = {
                "gid": existing["gid"],
                "name": name,
                "enum_options": {},
            }
            for opt in existing.get("enum_options", []):
                if opt.get("enabled", True):
                    field_info["enum_options"][opt["name"]] = opt["gid"]
            result[name] = field_info
            print(f"  Found existing field: {name} (GID: {existing['gid']})", file=sys.stderr)
        else:
            # Create new field
            create_data = {
                "name": name,
                "resource_subtype": field_def["resource_subtype"],
                "workspace": workspace_gid,
            }
            if "enum_options" in field_def:
                create_data["enum_options"] = field_def["enum_options"]

            field = handle_api_call(
                custom_fields_api.create_custom_field,
                {"data": create_data},
                {},
            )
            field_info = {
                "gid": field["gid"],
                "name": name,
                "enum_options": {},
            }
            for opt in field.get("enum_options", []):
                if opt.get("enabled", True):
                    field_info["enum_options"][opt["name"]] = opt["gid"]
            result[name] = field_info
            print(f"  Created field: {name} (GID: {field['gid']})", file=sys.stderr)

    return result


# ---------------------------------------------------------------------------
# Reusable project creation helpers
# ---------------------------------------------------------------------------

def _create_actions_project(api_client, workspace_gid: str, name: str, team_gid: str | None) -> dict:
    """
    Create a customer Actions project with 6 standard sections.

    Args:
        api_client: Asana ApiClient instance
        workspace_gid: Workspace GID
        name: Customer name (project will be named "{name} Actions")
        team_gid: Team GID (required for Organization workspaces)

    Returns:
        Dict with "project" (serialized), "project_gid", "sections"
    """
    project_name = f"{name} Actions"
    print(f"Creating project '{project_name}' with standard sections...", file=sys.stderr)

    projects_api = asana.ProjectsApi(api_client)
    project_data = {
        "name": project_name,
        "default_view": "list",
        "notes": f"SE action tracking for {name}. Created by Claude Code /asana skill.",
    }
    if team_gid:
        project_data["team"] = team_gid

    project = handle_api_call(projects_api.create_project_for_workspace, {"data": project_data}, workspace_gid, {})
    project_gid = project["gid"]
    print(f"Created project '{project_name}' (GID: {project_gid})", file=sys.stderr)

    # Create 6 standard sections in order
    sections_api = asana.SectionsApi(api_client)
    standard_sections = [
        "To Do",
        "In Progress",
        "Waiting on Customer",
        "Waiting on Eng",
        "Scheduled/Future",
        "Done",
    ]

    section_results = []
    for section_name in standard_sections:
        section = handle_api_call(
            sections_api.create_section_for_project,
            project_gid,
            {"body": {"data": {"name": section_name}}},
        )
        section_results.append(serialize_section(section))
        print(f"  Created section: {section_name} (GID: {section['gid']})", file=sys.stderr)

    return {
        "project": serialize_project(project),
        "project_gid": project_gid,
        "sections": section_results,
    }


def _create_raid_project(api_client, workspace_gid: str, name: str, team_gid: str) -> dict:
    """
    Create a customer RAID Log project with 4 sections and 6 custom fields.

    Args:
        api_client: Asana ApiClient instance
        workspace_gid: Workspace GID
        name: Customer name (project will be named "{name} RAID Log")
        team_gid: Team GID

    Returns:
        Dict with "project" (serialized), "project_gid", "sections", "custom_fields"
    """
    project_name = f"{name} RAID Log"
    print(f"Creating RAID project '{project_name}'...", file=sys.stderr)

    projects_api = asana.ProjectsApi(api_client)
    project_data = {
        "name": project_name,
        "default_view": "list",
        "notes": (
            f"RAID log for {name}. "
            "Tracks Risks, Assumptions, Issues, and Dependencies. "
            "Internal strategic view -- never shared with customers.\n\n"
            "Created by Claude Code /raid skill."
        ),
        "team": team_gid,
    }

    project = handle_api_call(
        projects_api.create_project_for_workspace,
        {"data": project_data},
        workspace_gid,
        {},
    )
    project_gid = project["gid"]
    print(f"Created project '{project_name}' (GID: {project_gid})", file=sys.stderr)

    # Create 4 RAID sections in order
    sections_api = asana.SectionsApi(api_client)
    raid_sections = ["Risks", "Assumptions", "Issues", "Dependencies"]

    section_results = []
    for section_name in raid_sections:
        section = handle_api_call(
            sections_api.create_section_for_project,
            project_gid,
            {"body": {"data": {"name": section_name}}},
        )
        section_results.append(serialize_section(section))
        print(f"  Created section: {section_name} (GID: {section['gid']})", file=sys.stderr)

    # Get or create the 6 RAID custom fields
    custom_fields_api = asana.CustomFieldsApi(api_client)
    raid_fields = _get_or_create_raid_fields(custom_fields_api, workspace_gid)

    # Attach all 6 custom fields + Priority field to the project
    all_field_gids = [info["gid"] for info in raid_fields.values()]
    all_field_gids.append(PRIORITY_FIELD_GID)  # Existing workspace Priority field

    for field_gid in all_field_gids:
        handle_api_call(
            projects_api.add_custom_field_setting_for_project,
            {"data": {"custom_field": field_gid}},
            project_gid,
            {},
        )
    print(f"  Attached {len(all_field_gids)} custom fields to project", file=sys.stderr)

    return {
        "project": serialize_project(project),
        "project_gid": project_gid,
        "sections": section_results,
        "custom_fields": {
            field_name: {"gid": info["gid"], "enum_options": info["enum_options"]}
            for field_name, info in raid_fields.items()
        },
    }


def cmd_setup_project(args):
    """Create a new customer project with standard sections.

    Thin wrapper around _create_actions_project for CLI use.
    """
    api_client = get_client()
    workspace_gid = get_workspace_gid()

    result = _create_actions_project(api_client, workspace_gid, args.name, args.team)

    result["next_steps"] = (
        f"Copy project_gid '{result['project_gid']}' to the appropriate location:\n"
        f"  - For customer project: templates/customers.yaml -> action_tracker_id\n"
        f"  - For SE Team project: .claude/rules/asana.md -> SE Team project GID"
    )

    output_json(result, args.pretty)


def cmd_setup_raid_project(args):
    """Create a RAID log project with 4 RAID sections and 6 custom fields.

    Thin wrapper around _create_raid_project for CLI use.
    """
    api_client = get_client()
    workspace_gid = get_workspace_gid()
    team_gid = args.team or DEFAULT_TEAM_GID

    result = _create_raid_project(api_client, workspace_gid, args.name, team_gid)

    result["priority_field"] = {
        "gid": PRIORITY_FIELD_GID,
        "options": PRIORITY_OPTION_GIDS,
    }
    result["next_steps"] = (
        f"Copy project_gid '{result['project_gid']}' to customers.yaml:\n"
        f"  raid_tracker_id: \"{result['project_gid']}\""
    )

    output_json(result, args.pretty)


def cmd_add_project(args):
    """Add a task to an additional project (multi-homing)."""
    print(f"Multi-homing task {args.task_gid} into project {args.project_gid}...", file=sys.stderr)

    api_client = get_client()
    tasks_api = asana.TasksApi(api_client)

    # Add task to the additional project
    body_data = {"project": args.project_gid}
    if args.section:
        # Need to resolve section GID first
        sections_api = asana.SectionsApi(api_client)
        section_gid = resolve_section_gid(sections_api, args.project_gid, args.section)
        body_data["section"] = section_gid

    handle_api_call(
        tasks_api.add_project_for_task,
        {"body": {"data": body_data}},
        args.task_gid,
        {},
    )

    print(f"Added task {args.task_gid} to project {args.project_gid}", file=sys.stderr)

    # Fetch and return updated task
    task = handle_api_call(
        tasks_api.get_task,
        args.task_gid,
        {"opt_fields": "name,completed,assignee.name,due_on,memberships.section.name,memberships.project.name,custom_fields"},
    )
    output_json(serialize_task(task), args.pretty)


def cmd_create_master_portfolio(args):
    """Create a master portfolio with 4 portfolio-level custom fields."""
    print(f"Creating master portfolio '{args.name}'...", file=sys.stderr)

    api_client = get_client()
    workspace_gid = get_workspace_gid()

    # Step 1: Create the portfolio
    portfolios_api = asana.PortfoliosApi(api_client)
    portfolio = handle_api_call(
        portfolios_api.create_portfolio,
        {"data": {"name": args.name, "workspace": workspace_gid, "color": "light-green"}},
        {},
    )
    portfolio_gid = portfolio["gid"]
    print(f"Created portfolio '{args.name}' (GID: {portfolio_gid})", file=sys.stderr)

    # Step 2: Get or create the 4 portfolio custom fields
    custom_fields_api = asana.CustomFieldsApi(api_client)
    portfolio_fields = _get_or_create_portfolio_fields(custom_fields_api, workspace_gid)

    # Step 3: Attach all 4 custom fields to the portfolio
    for field_name, field_info in portfolio_fields.items():
        handle_api_call(
            portfolios_api.add_custom_field_setting_for_portfolio,
            {"data": {"custom_field": field_info["gid"]}},
            portfolio_gid,
        )
        print(f"  Attached field: {field_name} (GID: {field_info['gid']})", file=sys.stderr)

    # Output result
    result = {
        "portfolio_gid": portfolio_gid,
        "name": args.name,
        "custom_fields": {
            name: {"gid": info["gid"], "enum_options": info["enum_options"]}
            for name, info in portfolio_fields.items()
        },
        "next_steps": (
            f"Master portfolio created. Use this GID with setup-customer:\n"
            f"  mutate.py setup-customer --name <CustomerName> "
            f"--master-portfolio-gid {portfolio_gid}"
        ),
    }

    output_json(result, args.pretty)


def _find_customer_in_master(portfolios_api, master_portfolio_gid, customer_name):
    """Check if a customer portfolio already exists in the master portfolio.

    Returns (portfolio_gid, items) if found, (None, None) if not.
    """
    items = list(portfolios_api.get_items_for_portfolio(
        master_portfolio_gid,
        {"opt_fields": "name,resource_type"},
    ))
    for item in items:
        if item.get("name", "").lower() == customer_name.lower():
            return item["gid"], items
    return None, items


def cmd_setup_customer(args):
    """Set up or update a customer structure: portfolio + Actions + RAID + master portfolio.

    Idempotent — checks master portfolio for existing customer first:
    - New customer: creates portfolio + Actions + RAID + adds to master + sets fields
    - Existing customer: updates custom fields (SE Owner, AE, etc.), skips project creation
    """
    print(f"Setting up customer '{args.name}'...", file=sys.stderr)

    api_client = get_client()
    workspace_gid = get_workspace_gid()
    team_gid = args.team or DEFAULT_TEAM_GID
    portfolios_api = asana.PortfoliosApi(api_client)

    # Step 0: Check if customer already exists in master portfolio
    print("Checking master portfolio for existing customer...", file=sys.stderr)
    existing_gid, _ = _find_customer_in_master(
        portfolios_api, args.master_portfolio_gid, args.name
    )

    if existing_gid:
        print(f"  Customer '{args.name}' already exists (GID: {existing_gid}). Updating fields...", file=sys.stderr)
        customer_portfolio_gid = existing_gid
        mode = "updated"

        # Discover existing projects inside the customer portfolio
        portfolio_items = list(portfolios_api.get_items_for_portfolio(
            customer_portfolio_gid,
            {"opt_fields": "name,resource_type"},
        ))
        actions_project_gid = None
        raid_project_gid = None
        actions_result = {"sections": []}
        raid_result = {"sections": []}
        for item in portfolio_items:
            name = item.get("name", "")
            if "RAID" in name:
                raid_project_gid = item["gid"]
            elif item.get("resource_type") == "project":
                actions_project_gid = item["gid"]

        if not actions_project_gid:
            print("  Actions project missing — creating...", file=sys.stderr)
            actions_result = _create_actions_project(api_client, workspace_gid, args.name, team_gid)
            actions_project_gid = actions_result["project_gid"]
            handle_api_call(
                portfolios_api.add_item_for_portfolio,
                {"data": {"item": actions_project_gid}},
                customer_portfolio_gid,
            )

        if not raid_project_gid:
            print("  RAID project missing — creating...", file=sys.stderr)
            raid_result = _create_raid_project(api_client, workspace_gid, args.name, team_gid)
            raid_project_gid = raid_result["project_gid"]
            handle_api_call(
                portfolios_api.add_item_for_portfolio,
                {"data": {"item": raid_project_gid}},
                customer_portfolio_gid,
            )
    else:
        mode = "created"

        # Step 1: Create customer portfolio
        print("Step 1/7: Creating customer portfolio...", file=sys.stderr)
        customer_portfolio = handle_api_call(
            portfolios_api.create_portfolio,
            {"data": {"name": args.name, "workspace": workspace_gid, "color": "light-green"}},
            {},
        )
        customer_portfolio_gid = customer_portfolio["gid"]
        print(f"  Created customer portfolio '{args.name}' (GID: {customer_portfolio_gid})", file=sys.stderr)

        # Step 2: Create Actions project
        print("Step 2/7: Creating Actions project...", file=sys.stderr)
        actions_result = _create_actions_project(api_client, workspace_gid, args.name, team_gid)
        actions_project_gid = actions_result["project_gid"]

        # Step 3: Create RAID project
        print("Step 3/7: Creating RAID project...", file=sys.stderr)
        raid_result = _create_raid_project(api_client, workspace_gid, args.name, team_gid)
        raid_project_gid = raid_result["project_gid"]

        # Step 4: Add Actions project to customer portfolio
        print("Step 4/7: Adding Actions project to customer portfolio...", file=sys.stderr)
        handle_api_call(
            portfolios_api.add_item_for_portfolio,
            {"data": {"item": actions_project_gid}},
            customer_portfolio_gid,
        )

        # Step 5: Add RAID project to customer portfolio
        print("Step 5/7: Adding RAID project to customer portfolio...", file=sys.stderr)
        handle_api_call(
            portfolios_api.add_item_for_portfolio,
            {"data": {"item": raid_project_gid}},
            customer_portfolio_gid,
        )

        # Step 6: Add customer portfolio to master portfolio
        print("Step 6/7: Adding customer portfolio to master portfolio...", file=sys.stderr)
        handle_api_call(
            portfolios_api.add_item_for_portfolio,
            {"data": {"item": customer_portfolio_gid}},
            args.master_portfolio_gid,
        )

    # Step 7: Set custom field values on customer portfolio (if provided)
    custom_field_values = {}
    if args.se_owner_gid or args.account_exec_gid or args.deployment_type or args.health:
        print("Step 7/7: Setting custom field values...", file=sys.stderr)

        # Need to resolve portfolio field GIDs from the master portfolio
        custom_fields_api = asana.CustomFieldsApi(api_client)
        portfolio_fields = _get_or_create_portfolio_fields(custom_fields_api, workspace_gid)

        fields_to_set = {}

        if args.se_owner_gid:
            se_field = portfolio_fields.get("SE Owner")
            if se_field:
                fields_to_set[se_field["gid"]] = args.se_owner_gid
                custom_field_values["SE Owner"] = args.se_owner_gid

        if args.account_exec_gid:
            ae_field = portfolio_fields.get("Account Exec")
            if ae_field:
                fields_to_set[ae_field["gid"]] = args.account_exec_gid
                custom_field_values["Account Exec"] = args.account_exec_gid

        if args.deployment_type:
            dt_field = portfolio_fields.get("Deployment Type")
            if dt_field:
                # Resolve enum option GID by name
                type_map = {
                    "saas": "SaaS",
                    "dedicated-cloud": "Dedicated Cloud",
                    "server": "Server",
                }
                display_name = type_map.get(args.deployment_type, args.deployment_type)
                option_gid = dt_field["enum_options"].get(display_name)
                if option_gid:
                    fields_to_set[dt_field["gid"]] = option_gid
                    custom_field_values["Deployment Type"] = display_name

        if args.health:
            health_field = portfolio_fields.get("Customer Health")
            if health_field:
                # Resolve enum option GID by name
                health_map = {
                    "green": "Green",
                    "amber": "Amber",
                    "red": "Red",
                }
                display_name = health_map.get(args.health, args.health)
                option_gid = health_field["enum_options"].get(display_name)
                if option_gid:
                    fields_to_set[health_field["gid"]] = option_gid
                    custom_field_values["Customer Health"] = display_name

        if fields_to_set:
            handle_api_call(
                portfolios_api.update_portfolio,
                {"data": {"custom_fields": fields_to_set}},
                customer_portfolio_gid,
                {},
            )
            print(f"  Set {len(fields_to_set)} custom field(s)", file=sys.stderr)
    else:
        print("Step 7/7: No custom field values provided, skipping.", file=sys.stderr)

    print(f"Customer '{args.name}' {mode}!", file=sys.stderr)

    # Gap detection: scan for PLACEHOLDER values in customers.yaml if it exists
    gaps = []
    try:
        import yaml as _yaml
        yaml_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))), "templates", "customers.yaml")
        if os.path.exists(yaml_path):
            with open(yaml_path) as f:
                registry = _yaml.safe_load(f) or {}
            for cust in registry.get("customers", []):
                if cust.get("name", "").lower() == args.name.lower():
                    for key, val in cust.items():
                        if val == "PLACEHOLDER" or val == ["PLACEHOLDER"]:
                            gaps.append(key)
                        elif isinstance(val, dict):
                            for k2, v2 in val.items():
                                if v2 == "PLACEHOLDER":
                                    gaps.append(f"{key}.{k2}")
                        elif isinstance(val, list):
                            for item in val:
                                if isinstance(item, dict):
                                    for k2, v2 in item.items():
                                        if v2 == "PLACEHOLDER":
                                            gaps.append(f"{key}[].{k2}")
                    break
    except Exception:
        pass  # Gap detection is best-effort

    if gaps:
        print(f"\n⚠ {len(gaps)} gap(s) in customers.yaml for {args.name}:", file=sys.stderr)
        for g in gaps:
            print(f"  - {g}", file=sys.stderr)
        print("Run /customer-setup to populate these fields.", file=sys.stderr)

    # Output result
    result = {
        "mode": mode,
        "customer_portfolio_gid": customer_portfolio_gid,
        "actions_project_gid": actions_project_gid,
        "raid_project_gid": raid_project_gid,
        "master_portfolio_gid": args.master_portfolio_gid,
        "custom_field_values": custom_field_values,
        "actions_sections": actions_result.get("sections", []),
        "raid_sections": raid_result.get("sections", []),
        "gaps": gaps,
        "next_steps": (
            f"Update templates/customers.yaml for {args.name}:\n"
            f"  action_tracker_id: \"{actions_project_gid}\"\n"
            f"  raid_tracker_id: \"{raid_project_gid}\"\n"
            f"  portfolio_id: \"{customer_portfolio_gid}\""
        ) if mode == "created" else f"Customer '{args.name}' fields updated. No changes to customers.yaml needed.",
    }

    output_json(result, args.pretty)


def cmd_delete_portfolio(args):
    """Delete a portfolio by GID."""
    print(f"Deleting portfolio {args.gid}...", file=sys.stderr)

    api_client = get_client()
    portfolios_api = asana.PortfoliosApi(api_client)

    handle_api_call(
        portfolios_api.delete_portfolio,
        args.gid,
    )

    print(f"Deleted portfolio {args.gid}", file=sys.stderr)

    result = {
        "deleted_portfolio_gid": args.gid,
        "status": "deleted",
    }

    output_json(result, args.pretty)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    # Shared parent parsers
    pretty_parser = argparse.ArgumentParser(add_help=False)
    pretty_parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON output"
    )

    # Main parser
    parser = argparse.ArgumentParser(
        description="Asana write operations tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[pretty_parser],
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- create ---
    create_parser = subparsers.add_parser(
        "create", help="Create a new task in a project",
        parents=[pretty_parser],
    )
    create_parser.add_argument("--project-gid", required=True, help="Project GID")
    create_parser.add_argument("--name", required=True, help="Task name")
    create_parser.add_argument("--section", help="Section name (e.g., 'In Progress')")
    create_parser.add_argument("--assignee", help="Assignee GID or 'me'")
    create_parser.add_argument("--due", help="Due date (YYYY-MM-DD)")
    create_parser.add_argument("--priority", choices=["High", "Medium", "Low", "high", "medium", "low", "P0", "P1", "P2", "P3", "p0", "p1", "p2", "p3"],
                               help="Priority level (High/Medium/Low or legacy P0-P3)")
    create_parser.add_argument("--notes", help="Task description/notes")

    # --- update ---
    update_parser = subparsers.add_parser(
        "update", help="Update an existing task",
        parents=[pretty_parser],
    )
    update_parser.add_argument("--gid", required=True, help="Task GID")
    update_parser.add_argument("--name", help="New task name")
    update_parser.add_argument("--due", help="New due date (YYYY-MM-DD)")
    update_parser.add_argument("--notes", help="New description/notes")
    update_parser.add_argument("--priority", choices=["High", "Medium", "Low", "high", "medium", "low", "P0", "P1", "P2", "P3", "p0", "p1", "p2", "p3"],
                               help="New priority level (High/Medium/Low or legacy P0-P3)")
    update_parser.add_argument("--assignee", help="New assignee GID or 'me'")

    # --- complete ---
    complete_parser = subparsers.add_parser(
        "complete", help="Mark a task as completed",
        parents=[pretty_parser],
    )
    complete_parser.add_argument("--gid", required=True, help="Task GID")

    # --- move ---
    move_parser = subparsers.add_parser(
        "move", help="Move a task to a different section",
        parents=[pretty_parser],
    )
    move_parser.add_argument("--gid", required=True, help="Task GID")
    move_parser.add_argument("--section", required=True, help="Target section name")
    move_parser.add_argument("--project-gid", required=True, help="Project GID")

    # --- setup-project ---
    setup_parser = subparsers.add_parser(
        "setup-project", help="Create a customer project with standard sections",
        parents=[pretty_parser],
    )
    setup_parser.add_argument("--name", required=True, help="Project name (e.g., customer name)")
    setup_parser.add_argument("--team", help="Team GID (required for Organization workspaces)")

    # --- setup-raid-project ---
    raid_setup_parser = subparsers.add_parser(
        "setup-raid-project", help="Create a RAID log project with 4 sections and custom fields",
        parents=[pretty_parser],
    )
    raid_setup_parser.add_argument("--name", required=True, help="Customer name (project will be named '[Name] RAID Log')")
    raid_setup_parser.add_argument("--team", help="Team GID (default: W&B EMEA Post-Sales)")

    # --- add-project ---
    add_project_parser = subparsers.add_parser(
        "add-project", help="Multi-home a task into an additional project",
        parents=[pretty_parser],
    )
    add_project_parser.add_argument("--task-gid", required=True, help="Task GID to multi-home")
    add_project_parser.add_argument("--project-gid", required=True, help="Target project GID")
    add_project_parser.add_argument("--section", help="Target section name within the project")

    # --- create-master-portfolio ---
    master_portfolio_parser = subparsers.add_parser(
        "create-master-portfolio",
        help="Create a master portfolio with SE Owner, Account Exec, Deployment Type, Customer Health fields",
        parents=[pretty_parser],
    )
    master_portfolio_parser.add_argument("--name", required=True, help="Portfolio name (e.g., 'W&B EMEA Customers')")

    # --- setup-customer ---
    setup_customer_parser = subparsers.add_parser(
        "setup-customer",
        help="Set up a customer: portfolio + Actions project + RAID project + add to master portfolio",
        parents=[pretty_parser],
    )
    setup_customer_parser.add_argument("--name", required=True, help="Customer name (e.g., 'GResearch')")
    setup_customer_parser.add_argument("--master-portfolio-gid", required=True, help="Master portfolio GID to add customer to")
    setup_customer_parser.add_argument("--team", help="Team GID (default: W&B EMEA Post-Sales)")
    setup_customer_parser.add_argument("--se-owner-gid", help="SE Owner user GID (people field)")
    setup_customer_parser.add_argument("--account-exec-gid", help="Account Exec user GID (people field)")
    setup_customer_parser.add_argument(
        "--deployment-type",
        choices=["saas", "dedicated-cloud", "server"],
        help="Deployment type (saas, dedicated-cloud, server)",
    )
    setup_customer_parser.add_argument(
        "--health",
        choices=["green", "amber", "red"],
        help="Customer health (green, amber, red)",
    )

    # --- delete-portfolio ---
    delete_portfolio_parser = subparsers.add_parser(
        "delete-portfolio",
        help="Delete a portfolio by GID",
        parents=[pretty_parser],
    )
    delete_portfolio_parser.add_argument("--gid", required=True, help="Portfolio GID to delete")

    # --- Parse and dispatch ---
    args = parser.parse_args()

    commands = {
        "create": cmd_create,
        "update": cmd_update,
        "complete": cmd_complete,
        "move": cmd_move,
        "setup-project": cmd_setup_project,
        "setup-raid-project": cmd_setup_raid_project,
        "add-project": cmd_add_project,
        "create-master-portfolio": cmd_create_master_portfolio,
        "setup-customer": cmd_setup_customer,
        "delete-portfolio": cmd_delete_portfolio,
    }

    try:
        commands[args.command](args)
        sys.exit(0)

    except FileNotFoundError as e:
        output_error("credentials_not_found", str(e))
        sys.exit(1)

    except asana.rest.ApiException as e:
        output_error("asana_api_error", f"HTTP {e.status}: {e.body}")
        sys.exit(1)

    except ValueError as e:
        output_error("invalid_input", str(e))
        sys.exit(1)

    except Exception as e:
        output_error("unknown", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
