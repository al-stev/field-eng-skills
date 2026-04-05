#!/usr/bin/env python3
"""
Jira issue operations tool.

View, create, edit, transition, assign, comment, and link issues in the
W&B Jira instance using the Python jira SDK.

Usage:
    issues.py view --key WB-123
    issues.py list [--assignee EMAIL] [--status STATUS] [--type TYPE] [--customer NAME]
    issues.py search --jql "project = WB ORDER BY updated DESC" [--customer NAME]
    issues.py transitions --key WB-123
    issues.py create --type Bug --summary "..." [--customer NAME] [--eng-team TEAM]
    issues.py create-epic --summary "..." --parent WB-90
    issues.py edit --key WB-123 [--summary "..."] [--description "..."] [--add-labels L1 L2] [--remove-labels L3] [--due-date YYYY-MM-DD]
    issues.py transition --key WB-123 --status "In Progress"
    issues.py assign --key WB-123 --assignee "user@..."
    issues.py comment --key WB-123 --body "..."
    issues.py link --from-key WB-123 --to-key WB-456 --type "Blocks"
    issues.py fe-update --key WB-123 --status waiting-on-prod-eng --next-update 2026-03-20 --notes "Details"
    issues.py fe-updates --key WB-123
"""

import argparse
import json
import sys
from pathlib import Path

# Add current directory to path to import jira_client
sys.path.insert(0, str(Path(__file__).parent))

from jira import JIRAError
from jira_client import (
    get_client,
    handle_api_call,
    serialize_resource,
    output_json,
    output_error,
    escape_jql_string,
    DEFAULT_PROJECT,
    JIRA_SERVER,
    CUSTOMER_FIELD,
    ENG_TEAM_FIELD,
)


def _format_date(value: str) -> str:
    """Normalize a date string to DD-MMM-YYYY format (e.g. 20-MAR-2026).

    Accepts DD-MMM-YYYY (passthrough), YYYY-MM-DD, or DD/MM/YYYY.
    Uses uppercase 3-letter month to avoid US/EU date ambiguity.
    """
    from datetime import datetime
    v = value.strip().upper()
    for fmt in ("%d-%b-%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(v, fmt).strftime("%d-%b-%Y").upper()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date '{value}'. Use DD-MMM-YYYY (e.g. 20-MAR-2026)")


def _customer_jql_clause(name: str) -> str:
    """Build a Customer JQL clause that matches common name variations.

    Jira's Customer field has inconsistent naming (e.g. "GResearch" vs
    "G-Research"). This generates an IN clause covering hyphenated,
    non-hyphenated, and spaced variants.
    """
    variants = {name}
    # If name contains a hyphen, also try without it and with space
    if "-" in name:
        variants.add(name.replace("-", ""))
        variants.add(name.replace("-", " "))
    elif " " in name:
        variants.add(name.replace(" ", "-"))
        variants.add(name.replace(" ", ""))
    else:
        # Try inserting hyphens/spaces at case boundaries
        # Handles both "GResearch" -> "G-Research" and "BigCorp" -> "Big-Corp"
        import re
        split = re.sub(r'([A-Z][a-z])', r'-\1', name).lstrip("-")
        if split != name:
            variants.add(split)                    # G-Research
            variants.add(split.replace("-", " "))  # G Research
            variants.add(split.replace("-", ""))   # GResearch (already in set)
    if len(variants) == 1:
        return f'"Customer (WB)" = "{escape_jql_string(name)}"'
    quoted = ", ".join(f'"{escape_jql_string(v)}"' for v in sorted(variants))
    return f'"Customer (WB)" IN ({quoted})'


def cmd_view(args):
    """View a single issue."""
    client = get_client()
    issue = handle_api_call(client.issue, args.key)

    result = {
        "key": issue.key,
        "url": f"{JIRA_SERVER}/browse/{issue.key}",
        "fields": serialize_resource(issue.raw.get("fields", {})),
    }
    output_json(result, args.pretty)


def _extract_comment_metadata(issue):
    """Extract comment analysis metadata from an issue's comment field.

    Returns a dict with:
      - comment_count: total comments
      - last_comment_date: most recent comment (any author)
      - last_comment_author: who wrote the most recent comment
      - last_eng_comment_date: most recent non-FE-UPDATE comment
      - last_eng_comment_author: who wrote the most recent non-FE-UPDATE comment
      - first_comment_date: earliest comment (for response time calc)
      - fe_update_count: number of FE-UPDATE comments
    """
    comments = []
    if hasattr(issue.fields, 'comment') and issue.fields.comment:
        comments = getattr(issue.fields.comment, 'comments', [])

    if not comments:
        return {
            "comment_count": 0,
            "last_comment_date": None,
            "last_comment_author": None,
            "last_eng_comment_date": None,
            "last_eng_comment_author": None,
            "first_comment_date": None,
            "fe_update_count": 0,
        }

    fe_update_count = 0
    last_eng = None
    first_comment = comments[0] if comments else None

    for c in comments:
        body = getattr(c, 'body', '') or ''
        if "[FE-UPDATE]" in body:
            fe_update_count += 1
        else:
            last_eng = c  # iterating forward, last assignment wins

    last_comment = comments[-1]

    return {
        "comment_count": len(comments),
        "last_comment_date": str(last_comment.created) if last_comment else None,
        "last_comment_author": str(last_comment.author) if last_comment else None,
        "last_eng_comment_date": str(last_eng.created) if last_eng else None,
        "last_eng_comment_author": str(last_eng.author) if last_eng else None,
        "first_comment_date": str(first_comment.created) if first_comment else None,
        "fe_update_count": fe_update_count,
    }


def cmd_list(args):
    """List issues with filters (builds JQL, adds ORDER BY updated DESC)."""
    client = get_client()

    clauses = []
    project = args.project or DEFAULT_PROJECT
    clauses.append(f'project = "{escape_jql_string(project)}"')

    if args.assignee:
        clauses.append(f'assignee = "{escape_jql_string(args.assignee)}"')
    if args.status:
        clauses.append(f'status = "{escape_jql_string(args.status)}"')
    if args.type:
        clauses.append(f'issuetype = "{escape_jql_string(args.type)}"')
    if args.label:
        clauses.append(f'labels = "{escape_jql_string(args.label)}"')
    if args.customer:
        clauses.append(_customer_jql_clause(args.customer))

    jql = " AND ".join(clauses) + " ORDER BY updated DESC"
    max_results = args.max_results or 50

    # When --with-comments is set, include comment field in the search
    search_kwargs = {"maxResults": max_results}
    if args.with_comments:
        search_kwargs["fields"] = (
            "summary,status,issuetype,priority,assignee,components,"
            f"labels,parent,duedate,created,updated,resolutiondate,comment,{CUSTOMER_FIELD}"
        )

    issues = handle_api_call(client.enhanced_search_issues, jql, **search_kwargs)

    result_issues = []
    for issue in issues:
        entry = {
            "key": issue.key,
            "url": f"{JIRA_SERVER}/browse/{issue.key}",
            "summary": issue.fields.summary,
            "status": str(issue.fields.status),
            "type": str(issue.fields.issuetype),
            "priority": str(issue.fields.priority) if issue.fields.priority else None,
            "assignee": str(issue.fields.assignee) if issue.fields.assignee else None,
            "customer": getattr(issue.fields, CUSTOMER_FIELD, None),
            "components": [c.name for c in (issue.fields.components or [])],
            "labels": list(issue.fields.labels or []),
            "parent": issue.fields.parent.key if getattr(issue.fields, 'parent', None) else None,
            "parent_summary": issue.fields.parent.fields.summary if getattr(issue.fields, 'parent', None) and hasattr(issue.fields.parent, 'fields') else None,
            "duedate": str(issue.fields.duedate) if issue.fields.duedate else None,
            "created": str(issue.fields.created),
            "updated": str(issue.fields.updated),
            "resolutiondate": str(issue.fields.resolutiondate) if getattr(issue.fields, 'resolutiondate', None) else None,
        }
        if args.with_comments:
            entry["comments"] = _extract_comment_metadata(issue)
        result_issues.append(entry)

    result = {
        "jql": jql,
        "total": issues.total,
        "count": len(issues),
        "issues": result_issues,
    }
    output_json(result, args.pretty)


def cmd_search(args):
    """Full JQL search (supports ORDER BY). Optional --customer adds a Customer filter."""
    client = get_client()
    max_results = args.max_results or 50

    jql = args.jql
    if args.customer:
        # Prepend customer filter to user-provided JQL
        customer_clause = _customer_jql_clause(args.customer)
        # Insert before ORDER BY if present, otherwise append
        jql_upper = jql.upper()
        if "ORDER BY" in jql_upper:
            idx = jql_upper.index("ORDER BY")
            jql = jql[:idx].rstrip() + f" AND {customer_clause} " + jql[idx:]
        else:
            jql = jql + f" AND {customer_clause}"

    issues = handle_api_call(client.enhanced_search_issues, jql, maxResults=max_results)

    result = {
        "jql": args.jql,
        "total": issues.total,
        "count": len(issues),
        "issues": [
            {
                "key": issue.key,
                "url": f"{JIRA_SERVER}/browse/{issue.key}",
                "summary": issue.fields.summary,
                "status": str(issue.fields.status),
                "type": str(issue.fields.issuetype),
                "priority": str(issue.fields.priority) if issue.fields.priority else None,
                "assignee": str(issue.fields.assignee) if issue.fields.assignee else None,
                "duedate": str(issue.fields.duedate) if issue.fields.duedate else None,
                "updated": str(issue.fields.updated),
            }
            for issue in issues
        ],
    }
    output_json(result, args.pretty)


def cmd_transitions(args):
    """List available transitions for an issue."""
    client = get_client()
    transitions = handle_api_call(client.transitions, args.key)

    result = {
        "key": args.key,
        "transitions": [
            {
                "id": t["id"],
                "name": t["name"],
                "to": t.get("to", {}).get("name"),
            }
            for t in transitions
        ],
    }
    output_json(result, args.pretty)


DEFAULT_ENG_TEAM = "🥷 Support Triage"
DEFAULT_LABELS = ["jira_escalated", "fe-reported"]


def cmd_create(args):
    """Create a new issue (Bug, Feature Request, etc.)."""
    client = get_client()

    fields = {
        "project": {"key": args.project or DEFAULT_PROJECT},
        "issuetype": {"name": args.type},
        "summary": args.summary,
    }

    if args.description:
        fields["description"] = args.description
    if args.priority:
        fields["priority"] = {"name": args.priority}

    # Labels: use provided labels, or default to jira_escalated + fe-reported
    fields["labels"] = args.labels if args.labels else DEFAULT_LABELS

    if args.parent:
        fields["parent"] = {"key": args.parent}
    if args.customer:
        # Customer field is label-type: spaces not allowed, use hyphens
        fields[CUSTOMER_FIELD] = [args.customer.replace(" ", "-")]

    # Eng team: use provided value, or default to Support Triage
    eng_team = args.eng_team if args.eng_team else DEFAULT_ENG_TEAM
    fields[ENG_TEAM_FIELD] = {"value": eng_team}

    issue = handle_api_call(client.create_issue, fields=fields)

    result = {
        "key": issue.key,
        "url": f"{JIRA_SERVER}/browse/{issue.key}",
        "summary": issue.fields.summary,
        "type": str(issue.fields.issuetype),
    }
    output_json(result, args.pretty)


def cmd_create_epic(args):
    """
    Create an Epic with two-step fallback.

    Some Jira configurations reject Epic creation with certain fields
    (parent, priority, labels) in the initial request. This command creates
    the Epic with only summary/description first, then updates remaining
    fields via issue.update().
    """
    client = get_client()

    # Step 1: Create minimal Epic (summary + description only)
    fields = {
        "project": {"key": args.project or DEFAULT_PROJECT},
        "issuetype": {"name": "Epic"},
        "summary": args.summary,
    }
    if args.description:
        fields["description"] = args.description

    issue = handle_api_call(client.create_issue, fields=fields)

    # Step 2: Update parent, priority, labels via issue.update()
    update_fields = {}
    if args.parent:
        update_fields["parent"] = {"key": args.parent}
    if args.priority:
        update_fields["priority"] = {"name": args.priority}
    if args.labels:
        update_fields["labels"] = args.labels

    if update_fields:
        handle_api_call(issue.update, fields=update_fields)
        # Refresh issue data after update
        issue = handle_api_call(client.issue, issue.key)

    result = {
        "key": issue.key,
        "url": f"{JIRA_SERVER}/browse/{issue.key}",
        "summary": issue.fields.summary,
        "type": str(issue.fields.issuetype),
        "parent": issue.raw.get("fields", {}).get("parent", {}).get("key") if issue.raw.get("fields", {}).get("parent") else None,
    }
    output_json(result, args.pretty)


def cmd_edit(args):
    """Update fields on an existing issue."""
    client = get_client()
    issue = handle_api_call(client.issue, args.key)

    update_fields = {}
    if args.summary:
        update_fields["summary"] = args.summary
    if args.description:
        update_fields["description"] = args.description
    if args.priority:
        update_fields["priority"] = {"name": args.priority}
    if args.labels is not None:
        update_fields["labels"] = args.labels
    if args.due_date is not None:
        update_fields["duedate"] = None if args.due_date.lower() == "none" else args.due_date
    if args.parent:
        update_fields["parent"] = {"key": args.parent}

    # Incremental label operations (--add-labels / --remove-labels)
    label_updates = []
    if args.add_labels:
        for lbl in args.add_labels:
            label_updates.append({"add": lbl})
    if args.remove_labels:
        for lbl in args.remove_labels:
            label_updates.append({"remove": lbl})

    has_field_changes = bool(update_fields)
    has_label_updates = bool(label_updates)

    if not has_field_changes and not has_label_updates:
        output_error("no_changes", "No fields to update. Provide at least one of --summary, --description, --priority, --labels, --add-labels, --remove-labels, --due-date, --parent.")
        sys.exit(1)

    # Build the update call — fields= for replacements, update= for incremental ops
    kwargs = {}
    if has_field_changes:
        kwargs["fields"] = update_fields
    if has_label_updates:
        kwargs["update"] = {"labels": label_updates}

    handle_api_call(issue.update, **kwargs)

    # Refresh issue data
    issue = handle_api_call(client.issue, args.key)

    changed = list(update_fields.keys())
    if has_label_updates:
        changed.append("labels (incremental)")

    result = {
        "key": issue.key,
        "url": f"{JIRA_SERVER}/browse/{issue.key}",
        "updated_fields": changed,
        "labels": issue.fields.labels or [],
        "summary": issue.fields.summary,
    }
    output_json(result, args.pretty)


def cmd_transition(args):
    """Transition an issue to a new status."""
    client = get_client()

    # Find the transition ID matching the requested status
    transitions = handle_api_call(client.transitions, args.key)
    target = None
    for t in transitions:
        if t["name"].lower() == args.status.lower():
            target = t
            break

    if target is None:
        available = [t["name"] for t in transitions]
        output_error(
            "invalid_transition",
            f'Transition "{args.status}" not available for {args.key}. '
            f"Available: {', '.join(available)}"
        )
        sys.exit(1)

    handle_api_call(client.transition_issue, args.key, target["id"])

    result = {
        "key": args.key,
        "url": f"{JIRA_SERVER}/browse/{args.key}",
        "transitioned_to": target["name"],
    }
    output_json(result, args.pretty)


def cmd_assign(args):
    """Assign or unassign an issue."""
    client = get_client()

    if args.unassign:
        handle_api_call(client.assign_issue, args.key, None)
        assignee = None
    else:
        handle_api_call(client.assign_issue, args.key, args.assignee)
        assignee = args.assignee

    result = {
        "key": args.key,
        "url": f"{JIRA_SERVER}/browse/{args.key}",
        "assignee": assignee,
    }
    output_json(result, args.pretty)


def cmd_comment(args):
    """Add a comment to an issue."""
    client = get_client()
    comment = handle_api_call(client.add_comment, args.key, args.body)

    result = {
        "key": args.key,
        "url": f"{JIRA_SERVER}/browse/{args.key}",
        "comment_id": comment.id,
        "body": comment.body,
    }
    output_json(result, args.pretty)


def cmd_link(args):
    """Link two issues."""
    client = get_client()
    handle_api_call(client.create_issue_link, args.type, args.from_key, args.to_key)

    result = {
        "from": args.from_key,
        "to": args.to_key,
        "type": args.type,
    }
    output_json(result, args.pretty)


def cmd_flag(args):
    """Flag or unflag an issue.

    Uses the REST API v2 directly with customfield_10021 because the
    'flagged' field is not on the WB project edit screens, so the
    standard issue.update() path rejects it.
    """
    client = get_client()

    url = f"{client._options['server']}/rest/api/2/issue/{args.key}"
    if args.remove:
        payload = {"fields": {"customfield_10021": []}}
    else:
        payload = {"fields": {"customfield_10021": [{"value": "Impediment"}]}}

    resp = client._session.put(url, json=payload)
    if resp.status_code not in (200, 204):
        output_error(
            f"flag_error_{resp.status_code}",
            resp.text[:500] if resp.text else "Unknown error",
        )
        sys.exit(1)

    result = {
        "key": args.key,
        "url": f"{JIRA_SERVER}/browse/{args.key}",
        "flagged": not args.remove,
    }
    output_json(result, args.pretty)


def cmd_fe_update(args):
    """Add a structured FE-UPDATE comment to an issue (WRITE operation)."""
    client = get_client()

    # Format dates to DD-MMM-YYYY
    next_update = _format_date(args.next_update) if args.next_update else None
    target = _format_date(args.target) if args.target else None

    # Build the structured comment body
    header = f"[FE-UPDATE] [status:{args.status}]"
    if next_update:
        header += f" [next-update:{next_update}]"
    if target:
        header += f" [target:{target}]"
    body = header
    if args.notes:
        body += f"\n{args.notes}"

    comment = handle_api_call(client.add_comment, args.key, body)

    result = {
        "key": args.key,
        "url": f"{JIRA_SERVER}/browse/{args.key}",
        "comment_id": comment.id,
        "fe_update": {
            "status": args.status,
            "next_update": next_update,
            "target": target,
            "notes": args.notes,
        },
        "body": comment.body,
    }
    output_json(result, args.pretty)


def cmd_fe_updates(args):
    """Retrieve all FE-UPDATE comments from an issue (READ operation)."""
    import re

    client = get_client()
    issue = handle_api_call(client.issue, args.key, fields="comment")

    status_re = re.compile(r'\[status:([^\]]+)\]')
    next_update_re = re.compile(r'\[next-update:([^\]]+)\]')
    target_re = re.compile(r'\[target:([^\]]+)\]')

    fe_updates = []
    comments = issue.fields.comment.comments if hasattr(issue.fields.comment, 'comments') else []

    for comment in comments:
        body = comment.body
        if "[FE-UPDATE]" not in body:
            continue

        status_match = status_re.search(body)
        next_update_match = next_update_re.search(body)
        target_match = target_re.search(body)

        # Extract notes: everything after the first line
        lines = body.split("\n", 1)
        notes = lines[1].strip() if len(lines) > 1 else None

        fe_updates.append({
            "comment_id": comment.id,
            "author": str(comment.author),
            "created": str(comment.created),
            "updated": str(comment.updated),
            "status": status_match.group(1) if status_match else None,
            "next_update": next_update_match.group(1) if next_update_match else None,
            "target": target_match.group(1) if target_match else None,
            "notes": notes,
            "raw_body": body,
        })

    # Track target date drift across updates
    targets = [u["target"] for u in fe_updates if u["target"]]

    result = {
        "key": args.key,
        "url": f"{JIRA_SERVER}/browse/{args.key}",
        "total_fe_updates": len(fe_updates),
        "fe_updates": fe_updates,
        "current_status": fe_updates[-1]["status"] if fe_updates else None,
        "current_target": targets[-1] if targets else None,
        "target_history": targets if len(targets) > 1 else None,
    }
    output_json(result, args.pretty)


def main():
    # Shared parent parser for --pretty flag (works in any position)
    pretty_parser = argparse.ArgumentParser(add_help=False)
    pretty_parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON output"
    )

    parser = argparse.ArgumentParser(
        description="Jira issue operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[pretty_parser],
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- Read operations ---

    # view
    view_parser = subparsers.add_parser("view", help="View a single issue", parents=[pretty_parser])
    view_parser.add_argument("--key", required=True, help="Issue key (e.g. WB-123)")

    # list
    list_parser = subparsers.add_parser("list", help="List issues with filters", parents=[pretty_parser])
    list_parser.add_argument("--assignee", help="Filter by assignee email")
    list_parser.add_argument("--status", help="Filter by status (e.g. 'In Progress')")
    list_parser.add_argument("--type", help="Filter by issue type (e.g. Story, Epic)")
    list_parser.add_argument("--label", help="Filter by label")
    list_parser.add_argument("--customer", help="Filter by Customer field (e.g. 'GResearch')")
    list_parser.add_argument("--project", help=f"Project key (default: {DEFAULT_PROJECT})")
    list_parser.add_argument("--max-results", type=int, help="Max results (default: 50)")
    list_parser.add_argument("--with-comments", action="store_true", help="Include comment metadata per issue (for tracker analysis)")

    # search
    search_parser = subparsers.add_parser("search", help="Full JQL search", parents=[pretty_parser])
    search_parser.add_argument("--jql", required=True, help="JQL query (supports ORDER BY)")
    search_parser.add_argument("--customer", help="Add Customer filter to JQL (e.g. 'GResearch')")
    search_parser.add_argument("--max-results", type=int, help="Max results (default: 50)")

    # transitions
    trans_parser = subparsers.add_parser("transitions", help="List available transitions", parents=[pretty_parser])
    trans_parser.add_argument("--key", required=True, help="Issue key")

    # --- Write operations ---

    # create
    create_parser = subparsers.add_parser("create", help="Create an issue", parents=[pretty_parser])
    create_parser.add_argument("--type", required=True, help="Issue type (Bug, 'Feature Request', Story, Sub-task)")
    create_parser.add_argument("--summary", required=True, help="Issue summary")
    create_parser.add_argument("--description", help="Issue description")
    create_parser.add_argument("--priority", help="Priority (P0, P1, P2, P3, P4)")
    create_parser.add_argument("--labels", nargs="+", help="Labels to add")
    create_parser.add_argument("--parent", help="Parent issue key (for Sub-task or child issues)")
    create_parser.add_argument("--customer", help="Customer name (sets customfield_16678)")
    create_parser.add_argument("--eng-team", dest="eng_team", help="Eng Team (sets customfield_16680)")
    create_parser.add_argument("--project", help=f"Project key (default: {DEFAULT_PROJECT})")

    # create-epic
    epic_parser = subparsers.add_parser("create-epic", help="Create an Epic (two-step)", parents=[pretty_parser])
    epic_parser.add_argument("--summary", required=True, help="Epic summary")
    epic_parser.add_argument("--parent", help="Parent issue key (e.g. Project key)")
    epic_parser.add_argument("--description", help="Epic description")
    epic_parser.add_argument("--priority", help="Priority")
    epic_parser.add_argument("--labels", nargs="+", help="Labels to add")
    epic_parser.add_argument("--project", help=f"Project key (default: {DEFAULT_PROJECT})")

    # edit
    edit_parser = subparsers.add_parser("edit", help="Edit an issue", parents=[pretty_parser])
    edit_parser.add_argument("--key", required=True, help="Issue key")
    edit_parser.add_argument("--summary", help="New summary")
    edit_parser.add_argument("--description", help="New description")
    edit_parser.add_argument("--priority", help="New priority")
    edit_parser.add_argument("--labels", nargs="+", help="Replace all labels")
    edit_parser.add_argument("--add-labels", dest="add_labels", nargs="+", help="Add labels (keeps existing)")
    edit_parser.add_argument("--remove-labels", dest="remove_labels", nargs="+", help="Remove specific labels")
    edit_parser.add_argument("--due-date", dest="due_date", help="Due date (YYYY-MM-DD format, or 'none' to clear)")
    edit_parser.add_argument("--parent", help="New parent issue key")

    # transition
    transition_parser = subparsers.add_parser("transition", help="Transition issue status", parents=[pretty_parser])
    transition_parser.add_argument("--key", required=True, help="Issue key")
    transition_parser.add_argument("--status", required=True, help="Target status name")

    # assign
    assign_parser = subparsers.add_parser("assign", help="Assign or unassign an issue", parents=[pretty_parser])
    assign_parser.add_argument("--key", required=True, help="Issue key")
    assign_group = assign_parser.add_mutually_exclusive_group(required=True)
    assign_group.add_argument("--assignee", help="Assignee email")
    assign_group.add_argument("--unassign", action="store_true", help="Remove assignee")

    # comment
    comment_parser = subparsers.add_parser("comment", help="Add a comment", parents=[pretty_parser])
    comment_parser.add_argument("--key", required=True, help="Issue key")
    comment_parser.add_argument("--body", required=True, help="Comment body")

    # link
    link_parser = subparsers.add_parser("link", help="Link two issues", parents=[pretty_parser])
    link_parser.add_argument("--from-key", required=True, help="Source issue key")
    link_parser.add_argument("--to-key", required=True, help="Target issue key")
    link_parser.add_argument("--type", required=True, help='Link type (e.g. "Blocks")')

    # flag
    flag_parser = subparsers.add_parser("flag", help="Flag or unflag an issue", parents=[pretty_parser])
    flag_parser.add_argument("--key", required=True, help="Issue key")
    flag_parser.add_argument("--remove", action="store_true", help="Remove flag instead of adding")

    # --- FE-UPDATE operations ---

    # fe-update (WRITE)
    fe_update_parser = subparsers.add_parser("fe-update", help="Add a structured FE-UPDATE comment (WRITE)", parents=[pretty_parser])
    fe_update_parser.add_argument("--key", required=True, help="Issue key (e.g. WB-123)")
    fe_update_parser.add_argument("--status", required=True, choices=["waiting-on-prod-eng", "waiting-on-customer", "resolved"], help="FE-UPDATE status")
    fe_update_parser.add_argument("--next-update", dest="next_update", help="Next check-in date (DD-MMM-YYYY, e.g. 20-MAR-2026)")
    fe_update_parser.add_argument("--target", help="Expected delivery/resolution date (DD-MMM-YYYY, e.g. 15-APR-2026)")
    fe_update_parser.add_argument("--notes", help="Free text notes")

    # fe-updates (READ)
    fe_updates_parser = subparsers.add_parser("fe-updates", help="Retrieve FE-UPDATE comments from an issue (READ)", parents=[pretty_parser])
    fe_updates_parser.add_argument("--key", required=True, help="Issue key (e.g. WB-123)")

    args = parser.parse_args()

    try:
        commands = {
            "view": cmd_view,
            "list": cmd_list,
            "search": cmd_search,
            "transitions": cmd_transitions,
            "create": cmd_create,
            "create-epic": cmd_create_epic,
            "edit": cmd_edit,
            "transition": cmd_transition,
            "assign": cmd_assign,
            "comment": cmd_comment,
            "link": cmd_link,
            "flag": cmd_flag,
            "fe-update": cmd_fe_update,
            "fe-updates": cmd_fe_updates,
        }
        commands[args.command](args)
        sys.exit(0)

    except FileNotFoundError as e:
        output_error("credentials_not_found", str(e))
        sys.exit(1)

    except KeyError as e:
        output_error("credentials_missing", str(e))
        sys.exit(1)

    except JIRAError as e:
        output_error(f"jira_error_{e.status_code}", e.text)
        sys.exit(1)

    except Exception as e:
        output_error("unknown", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
