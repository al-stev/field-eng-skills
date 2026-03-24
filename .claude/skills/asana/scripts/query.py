#!/usr/bin/env python3
"""
Asana read-only query tool.

Query Asana projects, sections, and tasks using the official Python SDK.

Usage:
    query.py projects [--team-gid GID] [--limit N] [--pretty]
    query.py project --gid GID | --url URL [--pretty]
    query.py sections --project-gid GID | --url URL [--pretty]
    query.py tasks --project-gid GID | --section-gid GID | --url URL [--limit N] [--pretty]
    query.py view --gid GID [--pretty]
    query.py subtasks --gid GID [--limit N] [--pretty]
    query.py search --text TEXT [--project-gid GID] [--assignee GID] [--completed] [--limit N] [--pretty]
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
    parse_asana_url,
    collect_pages,
    get_workspace_gid,
    serialize_project,
    serialize_section,
    serialize_task,
    output_json,
    output_error,
    DEFAULT_LIMIT,
)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_projects(args):
    """List projects in the workspace or a specific team."""
    api_client = get_client()
    projects_api = asana.ProjectsApi(api_client)

    opts = {
        "limit": min(args.limit, 100),
        "opt_fields": "name,archived,created_at,modified_at,due_on,start_on,owner.name,team.name,current_status_update.title,current_status_update.status_type,color",
    }

    if args.archived is not None:
        opts["archived"] = args.archived

    workspace_gid = get_workspace_gid()

    if args.team_gid:
        generator = handle_api_call(
            projects_api.get_projects_for_team,
            args.team_gid,
            opts,
        )
    else:
        generator = handle_api_call(
            projects_api.get_projects_for_workspace,
            workspace_gid,
            opts,
        )

    results = collect_pages(generator, args.limit)
    projects = [serialize_project(p) for p in results]

    output_json({
        "count": len(projects),
        "results": projects,
    }, args.pretty)


def cmd_project(args):
    """Get project details by GID or URL."""
    gid = args.gid
    if args.url:
        parsed = parse_asana_url(args.url)
        gid = parsed["project_gid"]

    if not gid:
        output_error("invalid_input", "Must provide --gid or --url.")
        sys.exit(1)

    api_client = get_client()
    projects_api = asana.ProjectsApi(api_client)

    project = handle_api_call(
        projects_api.get_project,
        gid,
        {
            "opt_fields": "name,archived,color,created_at,modified_at,due_on,start_on,notes,owner.name,team.name,members.name,current_status_update.title,current_status_update.status_type,current_status_update.text,custom_fields,custom_field_settings.custom_field.name,privacy_setting,default_view",
        },
    )

    output_json(serialize_project(project), args.pretty)


def cmd_sections(args):
    """List sections in a project."""
    project_gid = args.project_gid
    if args.url:
        parsed = parse_asana_url(args.url)
        project_gid = parsed["project_gid"]

    if not project_gid:
        output_error("invalid_input", "Must provide --project-gid or --url.")
        sys.exit(1)

    api_client = get_client()
    sections_api = asana.SectionsApi(api_client)

    generator = handle_api_call(
        sections_api.get_sections_for_project,
        project_gid,
        {"opt_fields": "name,created_at"},
    )

    results = collect_pages(generator)
    sections = [serialize_section(s) for s in results]

    output_json({
        "project_gid": project_gid,
        "count": len(sections),
        "sections": sections,
    }, args.pretty)


def cmd_tasks(args):
    """List tasks in a project or section."""
    api_client = get_client()
    tasks_api = asana.TasksApi(api_client)

    opts = {
        "limit": min(args.limit, 100),
        "opt_fields": "name,completed,completed_at,assignee.name,due_on,due_at,start_on,created_at,modified_at,custom_fields,num_subtasks,memberships.section.name,memberships.project.name,resource_subtype",
    }

    if args.section_gid:
        generator = handle_api_call(
            tasks_api.get_tasks_for_section,
            args.section_gid,
            opts,
        )
    elif args.project_gid:
        generator = handle_api_call(
            tasks_api.get_tasks_for_project,
            args.project_gid,
            opts,
        )
    elif args.url:
        parsed = parse_asana_url(args.url)
        generator = handle_api_call(
            tasks_api.get_tasks_for_project,
            parsed["project_gid"],
            opts,
        )
    else:
        output_error("invalid_input", "Must provide --project-gid, --section-gid, or --url.")
        sys.exit(1)

    results = collect_pages(generator, args.limit)
    tasks = [serialize_task(t) for t in results]

    output_json({
        "count": len(tasks),
        "results": tasks,
    }, args.pretty)


def cmd_view(args):
    """Get task details by GID."""
    api_client = get_client()
    tasks_api = asana.TasksApi(api_client)

    task = handle_api_call(
        tasks_api.get_task,
        args.gid,
        {
            "opt_fields": "name,notes,html_notes,completed,completed_at,completed_by.name,assignee.name,created_at,created_by.name,modified_at,due_on,due_at,start_on,start_at,custom_fields,num_subtasks,memberships.project.name,memberships.section.name,dependencies.name,dependents.name,resource_subtype,approval_status",
        },
    )

    output_json(serialize_task(task), args.pretty)


def cmd_subtasks(args):
    """List subtasks of a task."""
    api_client = get_client()
    tasks_api = asana.TasksApi(api_client)

    generator = handle_api_call(
        tasks_api.get_subtasks_for_task,
        args.gid,
        {
            "limit": min(args.limit, 100),
            "opt_fields": "name,completed,assignee.name,due_on,created_at,custom_fields,num_subtasks,resource_subtype",
        },
    )

    results = collect_pages(generator, args.limit)
    tasks = [serialize_task(t) for t in results]

    output_json({
        "parent_gid": args.gid,
        "count": len(tasks),
        "subtasks": tasks,
    }, args.pretty)


def cmd_search(args):
    """Search tasks in the workspace."""
    api_client = get_client()
    tasks_api = asana.TasksApi(api_client)

    workspace_gid = get_workspace_gid()

    opts = {
        "opt_fields": "name,completed,assignee.name,due_on,created_at,modified_at,memberships.project.name,memberships.section.name,custom_fields,resource_subtype",
    }

    if args.text:
        opts["text"] = args.text
    if args.project_gid:
        opts["projects_any"] = args.project_gid
    if args.assignee:
        opts["assignee_any"] = args.assignee
    if args.completed is not None:
        opts["completed"] = args.completed

    generator = handle_api_call(
        tasks_api.search_tasks_for_workspace,
        workspace_gid,
        opts,
    )

    results = collect_pages(generator, args.limit)
    tasks = [serialize_task(t) for t in results]

    output_json({
        "count": len(tasks),
        "results": tasks,
    }, args.pretty)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    # Shared parent parsers
    pretty_parser = argparse.ArgumentParser(add_help=False)
    pretty_parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON output"
    )

    limit_parser = argparse.ArgumentParser(add_help=False)
    limit_parser.add_argument(
        "--limit", type=int, default=DEFAULT_LIMIT,
        help=f"Max results to return (default: {DEFAULT_LIMIT})"
    )

    # Main parser
    parser = argparse.ArgumentParser(
        description="Asana read-only query tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[pretty_parser],
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- projects ---
    projects_parser = subparsers.add_parser(
        "projects", help="List projects in workspace or team",
        parents=[pretty_parser, limit_parser],
    )
    projects_parser.add_argument("--team-gid", help="Filter by team GID")
    projects_parser.add_argument(
        "--archived", type=lambda v: v.lower() == 'true',
        default=None, help="Filter by archived status (true/false)"
    )

    # --- project ---
    project_parser = subparsers.add_parser(
        "project", help="Get project details",
        parents=[pretty_parser],
    )
    project_parser.add_argument("--gid", help="Project GID")
    project_parser.add_argument("--url", help="Asana project URL")

    # --- sections ---
    sections_parser = subparsers.add_parser(
        "sections", help="List sections in a project",
        parents=[pretty_parser],
    )
    sections_parser.add_argument("--project-gid", help="Project GID")
    sections_parser.add_argument("--url", help="Asana project URL")

    # --- tasks ---
    tasks_parser = subparsers.add_parser(
        "tasks", help="List tasks in a project or section",
        parents=[pretty_parser, limit_parser],
    )
    tasks_parser.add_argument("--project-gid", help="Project GID")
    tasks_parser.add_argument("--section-gid", help="Section GID")
    tasks_parser.add_argument("--url", help="Asana project URL")

    # --- view ---
    view_parser = subparsers.add_parser(
        "view", help="Get task details",
        parents=[pretty_parser],
    )
    view_parser.add_argument("--gid", required=True, help="Task GID")

    # --- subtasks ---
    subtasks_parser = subparsers.add_parser(
        "subtasks", help="List subtasks of a task",
        parents=[pretty_parser, limit_parser],
    )
    subtasks_parser.add_argument("--gid", required=True, help="Parent task GID")

    # --- search ---
    search_parser = subparsers.add_parser(
        "search", help="Search tasks in workspace (Premium)",
        parents=[pretty_parser, limit_parser],
    )
    search_parser.add_argument("--text", help="Text search query")
    search_parser.add_argument("--project-gid", help="Filter to a specific project")
    search_parser.add_argument("--assignee", help="Filter by assignee GID")
    search_parser.add_argument(
        "--completed", type=lambda v: v.lower() == 'true',
        default=None, help="Filter by completed status (true/false)"
    )

    # --- Parse and dispatch ---
    args = parser.parse_args()

    commands = {
        "projects": cmd_projects,
        "project": cmd_project,
        "sections": cmd_sections,
        "tasks": cmd_tasks,
        "view": cmd_view,
        "subtasks": cmd_subtasks,
        "search": cmd_search,
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
