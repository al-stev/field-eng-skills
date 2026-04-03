#!/usr/bin/env python3
"""
Deterministic INTELLIGENCE_DATA assembler for customer-snapshot dashboards.

Accepts --jira, --bq, --asana, --sentiment JSON file arguments, applies
component/parent normalization, theme clustering, trending metrics computation,
and Asana task transformation. Outputs complete INTELLIGENCE_DATA JSON ready
for compose.py consumption.

Usage:
    uv run --project .claude/skills/customer-snapshot python \
        .claude/skills/customer-snapshot/templates/assemble.py \
        --customer "GResearch" \
        --jira /path/to/jira.json \
        --bq /path/to/bq.json \
        --asana /path/to/asana.json \
        --sentiment /path/to/sentiment.json \
        --days 14 --months 6 --audience internal \
        --output /path/to/output.json

All data source args are optional. Output goes to stdout by default,
or to --output file path.
"""

import argparse
import json
import re
import statistics
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# ── Cross-skill path setup (deep-analytics transforms + bigquery client) ──
SKILLS_DIR = Path(__file__).resolve().parent.parent.parent  # .claude/skills/
sys.path.insert(0, str(SKILLS_DIR / "bigquery" / "scripts"))
sys.path.insert(0, str(SKILLS_DIR / "deep-analytics" / "scripts"))


# ── Normalization maps (exact copies from panels/issues.js lines 56-99) ──

COMPONENT_NORMALIZE = {
    "Weave Python SDK": "SDK & Client Libraries",
    "Python SDK": "SDK & Client Libraries",
    "wandb-sdk": "SDK & Client Libraries",
    "wandb SDK": "SDK & Client Libraries",
    "Client": "SDK & Client Libraries",
    "Sweeps": "Sweeps",
    "Sweep": "Sweeps",
    "Launch": "Launch",
    "W&B Launch": "Launch",
    "Artifacts": "Artifacts",
    "Artifact": "Artifacts",
    "Model Registry": "Model Registry",
    "Reports": "Reports",
    "Report": "Reports",
    "Weave": "Weave",
    "Weave Tracing": "Weave",
    "UI": "UI & Dashboard",
    "Dashboard": "UI & Dashboard",
    "App": "UI & Dashboard",
    "Frontend": "UI & Dashboard",
    "Auth": "Auth & Permissions",
    "Authentication": "Auth & Permissions",
    "Permissions": "Auth & Permissions",
    "SSO": "Auth & Permissions",
    "API": "API & Integrations",
    "Public API": "API & Integrations",
    "Integrations": "API & Integrations",
    "Infrastructure": "Infrastructure",
    "Infra": "Infrastructure",
    "Backend": "Infrastructure",
    "Server": "Infrastructure",
}

PARENT_NORMALIZE = {
    "SDK Improvements": "SDK & Client Libraries",
    "Weave SDK Improvements": "SDK & Client Libraries",
    "Sweep Improvements": "Sweeps",
    "Launch Improvements": "Launch",
    "Artifact Improvements": "Artifacts",
    "UI Improvements": "UI & Dashboard",
    "Auth Improvements": "Auth & Permissions",
    "API Improvements": "API & Integrations",
}

# ── Priority name -> P-code mapping ──

PRIORITY_MAP = {
    "Critical": "P0",
    "Highest": "P0",
    "High": "P1",
    "Medium": "P2",
    "Low": "P3",
    "Lowest": "P3",
}

# Passthrough values
_PASSTHROUGH_PRIORITIES = {"P0", "P1", "P2", "P3"}

# Asana priority display_value -> P-code
ASANA_PRIORITY_MAP = {
    "High": "P1",
    "Medium": "P2",
    "Low": "P3",
}

# Sections that are exempt from staleness
_STALE_EXEMPT_SECTIONS = {
    "Waiting on Customer",
    "Waiting on Eng",
    "Scheduled/Future",
    "Done",
}

# Sections counted as stale-eligible
_STALE_ELIGIBLE_SECTIONS = {"To Do", "In Progress"}

# Linked Jira regex
_JIRA_LINK_RE = re.compile(r"\(WB-(\d+)\)")


# ── Helper functions ──


def map_priority(priority):
    """Map a Jira priority name to a P-code.

    Returns P0-P3 for known names, passthrough for existing P-codes,
    None for None input.
    """
    if priority is None:
        return None
    if priority in _PASSTHROUGH_PRIORITIES:
        return priority
    return PRIORITY_MAP.get(priority, priority)


def assign_theme(issue):
    """Assign a product-area theme to an issue using 3-tier cascade.

    1. First component -> COMPONENT_NORMALIZE
    2. parent_summary -> PARENT_NORMALIZE
    3. "Uncategorized"
    """
    components = issue.get("components") or []
    if components:
        first_component = components[0]
        normalized = COMPONENT_NORMALIZE.get(first_component)
        if normalized:
            return normalized

    parent_summary = issue.get("parent_summary")
    if parent_summary:
        normalized = PARENT_NORMALIZE.get(parent_summary)
        if normalized:
            return normalized

    return "Uncategorized"


def _parse_date(date_str):
    """Parse a date string into a date object.

    Handles ISO formats with and without timezone info:
    - "2026-01-15T10:00:00.000+0000"
    - "2026-01-15"
    - "2026-01-15T10:00:00Z"

    Returns None if parsing fails or input is None.
    """
    if not date_str:
        return None
    try:
        # Try full ISO with milliseconds and timezone
        if "T" in date_str:
            # Strip timezone suffix for simpler parsing
            clean = date_str.split("+")[0].split("Z")[0]
            if "." in clean:
                clean = clean.split(".")[0]
            dt = datetime.strptime(clean, "%Y-%m-%dT%H:%M:%S")
            return dt.date()
        else:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def _parse_datetime(dt_str):
    """Parse a datetime string into a datetime object.

    Returns None if parsing fails or input is None.
    """
    if not dt_str:
        return None
    try:
        clean = dt_str.split("+")[0].split("Z")[0]
        if "." in clean:
            clean = clean.split(".")[0]
        return datetime.strptime(clean, "%Y-%m-%dT%H:%M:%S")
    except (ValueError, AttributeError):
        return None


def transform_jira_issues(raw_issues):
    """Transform raw Jira issues from issues.py format to INTELLIGENCE_DATA format.

    Applies priority mapping and theme assignment to each issue.
    """
    transformed = []
    for issue in raw_issues:
        created_date = _parse_date(issue.get("created"))
        transformed.append(
            {
                "key": issue.get("key"),
                "summary": issue.get("summary"),
                "type": issue.get("type"),
                "priority": map_priority(issue.get("priority")),
                "status": issue.get("status"),
                "assignee": issue.get("assignee"),
                "theme": assign_theme(issue),
                "created": created_date.isoformat() if created_date else None,
                "updated": (
                    _parse_date(issue.get("updated")).isoformat()
                    if _parse_date(issue.get("updated"))
                    else None
                ),
                "resolutiondate": (
                    _parse_date(issue.get("resolutiondate")).isoformat()
                    if _parse_date(issue.get("resolutiondate"))
                    else None
                ),
                "url": issue.get("url"),
                "components": issue.get("components", []),
                "parent": issue.get("parent"),
                "parent_summary": issue.get("parent_summary"),
                "comments": issue.get("comments"),
            }
        )
    return transformed


def compute_trending(issues, months=6):
    """Compute trending metrics from transformed issues.

    Returns dict with opened_by_month, closed_by_month,
    raised_to_resolved_ratio, median_ttr_days, theme_recurrence.
    """
    today = date.today()
    # Build month range: last N months
    month_labels = []
    for i in range(months - 1, -1, -1):
        # Go back i months from today
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        month_labels.append(f"{y:04d}-{m:02d}")

    # Count opened by month
    opened_counts = {m: 0 for m in month_labels}
    closed_counts = {m: 0 for m in month_labels}

    total_opened_in_period = 0
    total_closed_in_period = 0
    ttr_days_list = []

    for issue in issues:
        # Opened
        created = _parse_date(issue.get("created"))
        if created:
            month_key = f"{created.year:04d}-{created.month:02d}"
            if month_key in opened_counts:
                opened_counts[month_key] += 1
                total_opened_in_period += 1

        # Closed
        resolved = _parse_date(issue.get("resolutiondate"))
        if resolved:
            month_key = f"{resolved.year:04d}-{resolved.month:02d}"
            if month_key in closed_counts:
                closed_counts[month_key] += 1
                total_closed_in_period += 1

            # TTR (time to resolution)
            if created and resolved:
                ttr = (resolved - created).days
                ttr_days_list.append(ttr)

    # Ratio
    ratio = None
    if total_closed_in_period > 0:
        ratio = round(total_opened_in_period / total_closed_in_period, 1)

    # Median TTR
    median_ttr = None
    if ttr_days_list:
        median_ttr = round(statistics.median(ttr_days_list))

    # Theme recurrence (top 5 by count)
    theme_counts = {}
    for issue in issues:
        theme = issue.get("theme", "Uncategorized")
        theme_counts[theme] = theme_counts.get(theme, 0) + 1
    theme_recurrence = sorted(
        [{"theme": t, "count": c} for t, c in theme_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:5]

    return {
        "opened_by_month": [
            {"month": m, "count": opened_counts[m]} for m in month_labels
        ],
        "closed_by_month": [
            {"month": m, "count": closed_counts[m]} for m in month_labels
        ],
        "raised_to_resolved_ratio": ratio,
        "median_ttr_days": median_ttr,
        "theme_recurrence": theme_recurrence,
    }


def transform_asana_tasks(asana_data):
    """Transform raw Asana tasks to INTELLIGENCE_DATA.actions format.

    Computes overdue, stale, stale_days, linked_jira, section, priority,
    and summary counts.
    """
    today = date.today()
    now = datetime.utcnow()
    raw_tasks = asana_data.get("results", [])

    transformed_tasks = []
    summary = {
        "total": 0,
        "in_progress": 0,
        "waiting": 0,
        "todo": 0,
        "overdue": 0,
        "stale": 0,
    }

    for task in raw_tasks:
        # Skip completed tasks
        if task.get("completed"):
            continue

        # Section
        memberships = task.get("memberships") or []
        section = (
            memberships[0]["section"]["name"]
            if memberships and memberships[0].get("section")
            else None
        )

        # Due date and overdue
        due_on = task.get("due_on")
        due_date = _parse_date(due_on) if due_on else None
        overdue = bool(due_date and due_date < today)

        # Modified and stale
        modified_at_str = task.get("modified_at")
        modified_dt = _parse_datetime(modified_at_str)
        stale_days = 0
        if modified_dt:
            stale_days = (now - modified_dt).days

        stale = bool(
            stale_days > 7 and section in _STALE_ELIGIBLE_SECTIONS
        )

        # Linked Jira
        name = task.get("name", "")
        jira_match = _JIRA_LINK_RE.search(name)
        linked_jira = f"WB-{jira_match.group(1)}" if jira_match else None

        # Priority from custom_fields
        priority = None
        for field in task.get("custom_fields") or []:
            if field.get("name") == "Priority" and field.get("display_value"):
                priority = ASANA_PRIORITY_MAP.get(
                    field["display_value"], field["display_value"]
                )
                break

        # Assignee
        assignee = task.get("assignee")

        # URL
        gid = task.get("gid", "")
        url = f"https://app.asana.com/0/0/{gid}" if gid else None

        transformed_tasks.append(
            {
                "gid": gid,
                "name": name,
                "section": section,
                "due_on": due_on,
                "overdue": overdue,
                "stale": stale,
                "stale_days": stale_days,
                "priority": priority,
                "assignee": assignee,
                "linked_jira": linked_jira,
                "url": url,
                "modified_at": modified_at_str,
            }
        )

        # Summary counts
        summary["total"] += 1
        if overdue:
            summary["overdue"] += 1
        if stale:
            summary["stale"] += 1
        if section == "In Progress":
            summary["in_progress"] += 1
        elif section == "To Do":
            summary["todo"] += 1
        elif section and section.startswith("Waiting"):
            summary["waiting"] += 1

    return {
        "available": True,
        "source": "asana",
        "tasks": transformed_tasks,
        "summary": summary,
    }


# ── Analytics key names (all 9 deep-analytics transforms) ──
ANALYTICS_KEYS = [
    "journey", "cohort", "decay", "team", "velocity",
    "sdk_versions", "correlation", "risk", "performance",
]


def _analytics_stubs(reason):
    """Return a dict with all 9 analytics keys set to unavailable stubs.

    Used when analytics cannot be fetched (no account_id, pipeline error, etc.).
    """
    return {key: {"available": False, "reason": reason} for key in ANALYTICS_KEYS}


def _get_deployment_type(client, account_id):
    """Extract deployment type from account_health_query. Returns (health_df, deployment_type)."""
    from queries import account_health_query
    from bq_client import run_query

    health_df = run_query(
        client, account_health_query(),
        account_id=account_id, maximum_bytes_billed=50_000_000_000,
    )
    deployment_type = "cloud"
    if not health_df.empty and "deployment_type" in health_df.columns:
        raw = str(health_df.iloc[0].get("deployment_type", ""))
        if "dedicated" in raw.lower():
            deployment_type = "dedicated-cloud"
        elif raw.lower() in ("server", "local"):
            deployment_type = "server"
    return health_df, deployment_type


def fetch_analytics_data(customer_name, client, account_id):
    """Fetch all 9 deep-analytics transforms and return analytics dict.

    Each key maps to its transform's output dict on success, or
    {"available": False, "reason": <error>} on failure.

    Parameters:
        customer_name: Customer display name
        client: BigQuery client instance
        account_id: SFDC account ID for BQ queries
    """
    if not account_id:
        return _analytics_stubs("No sfdc_account_id configured in customers.yaml")

    import pandas as pd
    from bq_client import run_query

    analytics = {}

    # ── Shared: deployment type + health (reused by several transforms) ──
    try:
        health_df, deployment_type = _get_deployment_type(client, account_id)
        weave_customer = False
        if not health_df.empty and "weave_customer" in health_df.columns:
            weave_customer = bool(health_df.iloc[0].get("weave_customer", False))
        contracted_seats = None
        if not health_df.empty:
            contracted_seats = health_df.iloc[0].get("total_contracted_seats")
            if contracted_seats is not None:
                contracted_seats = int(contracted_seats)
    except Exception as e:
        # If we can't even get health data, stub everything
        return _analytics_stubs(f"Health query failed: {e}")

    # ── 1. User Journey ──
    try:
        from queries import user_journey_query
        from transforms.user_journey import UserJourneyTransform

        sql = user_journey_query(deployment_type=deployment_type)
        df = run_query(client, sql, account_id=account_id, maximum_bytes_billed=100_000_000_000)
        transform = UserJourneyTransform()
        analytics["journey"] = transform.transform(
            user_journey=df, customer_name=customer_name, weave_customer=weave_customer,
        )
    except Exception as e:
        analytics["journey"] = {"available": False, "reason": str(e)}

    # ── 2. Cohort Analysis ──
    try:
        from queries import cohort_retention_query, user_lifecycle_query, user_journey_query as uj_query
        from transforms.cohort_analysis import CohortAnalysisTransform

        retention_df = run_query(
            client, cohort_retention_query(),
            account_id=account_id, maximum_bytes_billed=50_000_000_000,
        )
        lifecycle_df = None
        try:
            lifecycle_df = run_query(
                client, user_lifecycle_query(),
                account_id=account_id, maximum_bytes_billed=50_000_000_000,
            )
        except Exception:
            pass
        journey_df = None
        try:
            journey_df = run_query(
                client, uj_query(),
                account_id=account_id, maximum_bytes_billed=100_000_000_000,
            )
        except Exception:
            pass
        transform = CohortAnalysisTransform()
        analytics["cohort"] = transform.transform(
            retention=retention_df, lifecycle=lifecycle_df, journey=journey_df,
            customer_name=customer_name,
            data_source="ext_daily_user_event_usage (activity-based cohorts)",
        )
    except Exception as e:
        analytics["cohort"] = {"available": False, "reason": str(e)}

    # ── 3. Engagement Decay ──
    try:
        from queries import engagement_decay_query
        from transforms.engagement_decay import EngagementDecayTransform

        sql = engagement_decay_query(deployment_type=deployment_type)
        df = run_query(client, sql, account_id=account_id, maximum_bytes_billed=50_000_000_000)
        transform = EngagementDecayTransform()
        analytics["decay"] = transform.transform(
            engagement=df, customer_name=customer_name, contracted_seats=contracted_seats,
        )
    except Exception as e:
        analytics["decay"] = {"available": False, "reason": str(e)}

    # ── 4. Team Detection ──
    try:
        from queries import (
            team_detection_query, team_detection_query_dedicated,
            team_members_query_dedicated, team_champions_query,
        )
        from transforms.team_detection import TeamDetectionTransform

        display_type = str(health_df.iloc[0].get("deployment_type", "Unknown")) if not health_df.empty else "Unknown"
        members_df = None
        champions_df = None

        if deployment_type in ("dedicated-cloud", "server"):
            teams_df = run_query(
                client, team_detection_query_dedicated(),
                account_id=account_id, maximum_bytes_billed=100_000_000_000,
            )
            try:
                members_df = run_query(
                    client, team_members_query_dedicated(),
                    account_id=account_id, maximum_bytes_billed=100_000_000_000,
                )
            except Exception:
                pass
        else:
            teams_df = run_query(
                client, team_detection_query(),
                account_id=account_id, maximum_bytes_billed=100_000_000_000,
            )
            try:
                from schema_validator import check_data_availability, PHASE3_DATA_CHECKS
                avail = check_data_availability(client, account_id, {
                    "team_org_names": PHASE3_DATA_CHECKS["team_org_names"],
                })
                if avail.get("team_org_names", {}).get("available", False):
                    champions_df = run_query(
                        client, team_champions_query(deployment_type=deployment_type),
                        account_id=account_id, maximum_bytes_billed=50_000_000_000,
                    )
            except Exception:
                pass

        transform = TeamDetectionTransform()
        analytics["team"] = transform.transform(
            teams=teams_df, champions=champions_df, members=members_df,
            customer_name=customer_name, deployment_type=display_type,
        )
    except Exception as e:
        analytics["team"] = {"available": False, "reason": str(e)}

    # ── 5. Feature Velocity ──
    try:
        from queries import product_areas_query
        from transforms.feature_velocity import FeatureVelocityTransform

        sql = product_areas_query()
        df = run_query(client, sql, account_id=account_id, maximum_bytes_billed=50_000_000_000)
        transform = FeatureVelocityTransform()
        analytics["velocity"] = transform.transform(
            product_areas=df, customer_name=customer_name, weave_customer=weave_customer,
        )
    except Exception as e:
        analytics["velocity"] = {"available": False, "reason": str(e)}

    # ── 6. SDK Versions ──
    try:
        from queries import sdk_versions_query
        from transforms.sdk_versions import SdkVersionsTransform

        sql = sdk_versions_query()
        df = run_query(client, sql, account_id=account_id, maximum_bytes_billed=50_000_000_000)
        transform = SdkVersionsTransform()
        analytics["sdk_versions"] = transform.transform(
            sdk_versions=df, customer_name=customer_name,
        )
    except Exception as e:
        analytics["sdk_versions"] = {"available": False, "reason": str(e)}

    # ── 7. Usage Correlation ──
    try:
        from queries import (
            cross_account_product_areas_query, cross_account_arr_breadth_query,
            product_areas_query as pa_query, account_health_query,
        )
        from transforms.usage_correlation import UsageCorrelationTransform

        cross_account_df = run_query(
            client, cross_account_product_areas_query(),
            maximum_bytes_billed=100_000_000_000,
        )
        arr_data_df = run_query(
            client, cross_account_arr_breadth_query(),
            maximum_bytes_billed=100_000_000_000,
        )
        current_areas_df = run_query(
            client, pa_query(),
            account_id=account_id, maximum_bytes_billed=50_000_000_000,
        )
        current_account_areas = (
            current_areas_df["product_area"].unique().tolist()
            if not current_areas_df.empty else []
        )
        account_health = {}
        corr_deployment_type = "Unknown"
        if not health_df.empty:
            row = health_df.iloc[0]
            account_health = row.to_dict()
            corr_deployment_type = str(row.get("deployment_type", "Unknown"))

        transform = UsageCorrelationTransform()
        analytics["correlation"] = transform.transform(
            cross_account=cross_account_df, arr_data=arr_data_df,
            current_account_areas=current_account_areas,
            account_health=account_health, customer_name=customer_name,
            account_id=account_id, deployment_type=corr_deployment_type,
        )
    except Exception as e:
        analytics["correlation"] = {"available": False, "reason": str(e)}

    # ── 8. Risk Scoring ──
    try:
        from queries import (
            engagement_trend_query, risk_support_tickets_query,
            account_health_query as ah_query, seat_utilization_query,
        )
        from transforms.risk_scoring import RiskScoringTransform

        engagement_df = pd.DataFrame()
        try:
            from schema_validator import check_data_availability, PHASE3_DATA_CHECKS
            avail = check_data_availability(client, account_id, {
                "engagement_scores": PHASE3_DATA_CHECKS["engagement_scores"],
            })
            if avail.get("engagement_scores", {}).get("available", False):
                engagement_df = run_query(
                    client, engagement_trend_query(),
                    account_id=account_id, maximum_bytes_billed=50_000_000_000,
                )
        except Exception:
            pass

        seats_df = run_query(
            client, seat_utilization_query(),
            account_id=account_id, maximum_bytes_billed=50_000_000_000,
        )
        tickets_df = pd.DataFrame()
        try:
            tickets_df = run_query(
                client, risk_support_tickets_query(),
                account_id=account_id, maximum_bytes_billed=50_000_000_000,
            )
        except Exception:
            pass

        transform = RiskScoringTransform()
        analytics["risk"] = transform.transform(
            engagement=engagement_df, health=health_df,
            seats=seats_df, tickets=tickets_df,
            customer_name=customer_name,
        )
    except Exception as e:
        analytics["risk"] = {"available": False, "reason": str(e)}

    # ── 9. Performance ──
    try:
        from queries import performance_query, latency_distribution_query, slow_chart_users_query
        from transforms.performance import PerformanceTransform
        from schema_validator import (
            validate_tables, check_data_availability,
            PHASE4_SCHEMA_SPECS, PHASE4_DATA_CHECKS,
        )

        transform = PerformanceTransform()

        # Go/no-go gate: schema validation
        perf_table = "`wandb-production.analytics.fct_application_performance`"
        schema_results = validate_tables(client, {perf_table: PHASE4_SCHEMA_SPECS[perf_table]})
        if not schema_results[perf_table]["valid"]:
            analytics["performance"] = transform.descoped_result("schema_error")
        else:
            avail = check_data_availability(client, account_id, {
                "perf_index": PHASE4_DATA_CHECKS["perf_index"],
            })
            if not avail.get("perf_index", {}).get("available", False):
                analytics["performance"] = transform.descoped_result("performance_descoped")
            else:
                display_type = str(health_df.iloc[0].get("deployment_type", "Unknown")) if not health_df.empty else "Unknown"
                perf_df = run_query(
                    client, performance_query(),
                    account_id=account_id, maximum_bytes_billed=50_000_000_000,
                )
                if perf_df.empty:
                    analytics["performance"] = transform.descoped_result("performance_descoped")
                else:
                    latency_df = None
                    try:
                        latency_table = "`wandb-production.analytics.fct_onscreen_loader_latencies`"
                        lat_schema = validate_tables(client, {latency_table: PHASE4_SCHEMA_SPECS[latency_table]})
                        if lat_schema[latency_table]["valid"]:
                            lat_avail = check_data_availability(client, account_id, {
                                "latency_data": PHASE4_DATA_CHECKS["latency_data"],
                            })
                            if lat_avail.get("latency_data", {}).get("available", False):
                                latency_df = run_query(
                                    client, latency_distribution_query(),
                                    account_id=account_id, maximum_bytes_billed=50_000_000_000,
                                )
                    except Exception:
                        pass

                    slow_users_df = None
                    try:
                        slow_table = "`wandb-production.analytics.agg_daily_team_members_slow_chart_loads`"
                        slow_schema = validate_tables(client, {slow_table: PHASE4_SCHEMA_SPECS[slow_table]})
                        if slow_schema[slow_table]["valid"]:
                            slow_avail = check_data_availability(client, account_id, {
                                "slow_chart_data": PHASE4_DATA_CHECKS["slow_chart_data"],
                            })
                            if slow_avail.get("slow_chart_data", {}).get("available", False):
                                slow_users_df = run_query(
                                    client, slow_chart_users_query(deployment_type=deployment_type),
                                    account_id=account_id, maximum_bytes_billed=50_000_000_000,
                                )
                    except Exception:
                        pass

                    analytics["performance"] = transform.transform(
                        perf_df=perf_df,
                        latency_df=latency_df if latency_df is not None else pd.DataFrame(),
                        slow_users_df=slow_users_df if slow_users_df is not None else pd.DataFrame(),
                        customer_name=customer_name,
                        deployment_type=display_type,
                    )
    except Exception as e:
        analytics["performance"] = {"available": False, "reason": str(e)}

    return analytics


def assemble_intelligence_data(
    customer,
    jira_data,
    bq_data,
    asana_data,
    sentiment_data,
    config=None,
):
    """Assemble complete INTELLIGENCE_DATA from individual data sources.

    Parameters:
        customer: Customer display name
        jira_data: Dict from issues.py list --with-comments, or None
        bq_data: Dict from usage.py --format json, or None
        asana_data: Dict from query.py tasks, or None
        sentiment_data: Dict matching sentiment schema, or None
        config: Optional dict with sentiment_days, trending_months, audience

    Returns:
        Complete INTELLIGENCE_DATA dictionary ready for compose.py.
    """
    config = config or {}
    sentiment_days = config.get("sentiment_days", 14)
    trending_months = config.get("trending_months", 6)
    audience = config.get("audience", "internal")

    # ── Issues ──
    if jira_data and jira_data.get("issues"):
        issues = transform_jira_issues(jira_data["issues"])
    else:
        issues = []

    # ── Trending ──
    trending = compute_trending(issues, months=trending_months) if issues else None

    # ── Usage ──
    if bq_data is not None:
        usage = bq_data
    else:
        usage = {"available": False, "reason": "not_provided"}

    # ── Actions ──
    if asana_data is not None:
        actions = transform_asana_tasks(asana_data)
    else:
        actions = {"available": False, "reason": "not_provided"}

    # ── Sentiment ──
    sentiment = sentiment_data  # None if not provided

    # ── Analytics (deep-analytics transforms) ──
    analytics_enabled = config.get("analytics", True)
    analytics = {}
    if analytics_enabled:
        try:
            from bq_client import get_client, get_sfdc_account_id

            # Reuse BQ data's account_id if available, or look up from customer name
            client = get_client()
            acct_id = bq_data.get("sfdc_account_id") if bq_data else None
            if not acct_id:
                try:
                    acct_id = get_sfdc_account_id(customer)
                except Exception:
                    acct_id = None
            analytics = fetch_analytics_data(customer, client, acct_id)
        except Exception as e:
            analytics = _analytics_stubs(f"Pipeline error: {e}")
    else:
        analytics = _analytics_stubs("Analytics not enabled")

    return {
        "customer": customer,
        "generated": date.today().isoformat(),
        "config": {
            "sentiment_days": sentiment_days,
            "trending_months": trending_months,
            "audience": audience,
        },
        "issues": issues,
        "sentiment": sentiment,
        "trending": trending,
        "exec_summary": None,
        "actions": actions,
        "usage": usage,
        "analytics": analytics,
    }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Assemble INTELLIGENCE_DATA from JSON file inputs"
    )
    parser.add_argument("--customer", required=True, help="Customer display name")
    parser.add_argument("--jira", help="Path to Jira JSON file")
    parser.add_argument("--bq", help="Path to BigQuery JSON file")
    parser.add_argument("--asana", help="Path to Asana JSON file")
    parser.add_argument("--sentiment", help="Path to sentiment JSON file")
    parser.add_argument(
        "--days", type=int, default=14, help="Sentiment lookback days (default: 14)"
    )
    parser.add_argument(
        "--months",
        type=int,
        default=6,
        help="Trending lookback months (default: 6)",
    )
    parser.add_argument(
        "--audience",
        default="internal",
        choices=["internal", "external"],
        help="Audience mode (default: internal)",
    )
    parser.add_argument("--output", help="Output file path (default: stdout)")
    parser.add_argument(
        "--analytics",
        action="store_true",
        default=True,
        dest="analytics",
        help="Enable deep-analytics transforms (default: True)",
    )
    parser.add_argument(
        "--no-analytics",
        action="store_false",
        dest="analytics",
        help="Disable deep-analytics transforms",
    )
    args = parser.parse_args()

    # Load data sources
    jira_data = None
    if args.jira:
        jira_data = json.loads(Path(args.jira).read_text(encoding="utf-8"))

    bq_data = None
    if args.bq:
        bq_data = json.loads(Path(args.bq).read_text(encoding="utf-8"))

    asana_data = None
    if args.asana:
        asana_data = json.loads(Path(args.asana).read_text(encoding="utf-8"))

    sentiment_data = None
    if args.sentiment:
        sentiment_data = json.loads(Path(args.sentiment).read_text(encoding="utf-8"))

    config = {
        "sentiment_days": args.days,
        "trending_months": args.months,
        "audience": args.audience,
        "analytics": args.analytics,
    }

    result = assemble_intelligence_data(
        customer=args.customer,
        jira_data=jira_data,
        bq_data=bq_data,
        asana_data=asana_data,
        sentiment_data=sentiment_data,
        config=config,
    )

    output_json = json.dumps(result, indent=2, default=str)

    if args.output:
        Path(args.output).write_text(output_json, encoding="utf-8")
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
