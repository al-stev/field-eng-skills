#!/usr/bin/env python3
"""
BigQuery usage pipeline -- fetch and aggregate customer usage data.

CLI entry point that fetches seat utilization, Weave ingestion, tracked hours,
and account health data from BigQuery, then outputs JSON matching the
INTELLIGENCE_DATA.usage schema for dashboard consumption.

Usage:
    python usage.py --customer <name> [--format json|text] [--months 12]
"""

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

# Add scripts directory to path for sibling imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from bq_client import get_client, run_query, get_sfdc_account_id
from queries import (
    seat_utilization_query,
    weave_ingestion_query,
    tracked_hours_query,
    account_health_query,
    product_areas_query,
    power_users_query,
    support_tickets_query,
    weave_activity_query,
    weave_users_query,
    aggregate_weekly,
)




def classify_utilization_zone(percent: float) -> str:
    """
    Classify utilization percentage into health zones.

    Args:
        percent: Utilization percentage (0-100+)

    Returns:
        Zone string: 'healthy' (>=80), 'at_risk' (50-79), 'critical' (<50)
    """
    if percent >= 80:
        return "healthy"
    elif percent >= 50:
        return "at_risk"
    else:
        return "critical"


def _is_empty(df) -> bool:
    """Check if a DataFrame is None or empty."""
    return df is None or (isinstance(df, pd.DataFrame) and df.empty)


def _build_seat_utilization(seat_df: pd.DataFrame) -> Optional[dict]:
    """Build seat_utilization sub-section from daily seat data."""
    if _is_empty(seat_df):
        return None

    # Get latest values for headline
    latest = seat_df.iloc[-1]
    contracted = int(latest.get("contracted_seats", 0))
    active = int(latest.get("active_seats", 0))
    claimed = int(latest.get("claimed_seats", 0))
    utilization_pct = round((active / contracted) * 100, 1) if contracted > 0 else 0.0

    # Aggregate to weekly using "last" (end-of-week snapshot)
    weekly = aggregate_weekly(
        seat_df,
        date_col="date_day",
        value_cols=["active_seats", "contracted_seats", "claimed_seats"],
        method="last",
    )

    history = []
    for _, row in weekly.iterrows():
        history.append({
            "week": row["date_day"].strftime("%Y-%m-%d"),
            "contracted": int(row.get("contracted_seats", 0)),
            "active": int(row.get("active_seats", 0)),
        })

    return {
        "contracted": contracted,
        "claimed": claimed,
        "active": active,
        "utilization_percent": utilization_pct,
        "zone": classify_utilization_zone(utilization_pct),
        "history": history,
    }


def _build_weave(weave_df: pd.DataFrame) -> Optional[dict]:
    """Build weave sub-section from monthly Weave ingestion data."""
    if _is_empty(weave_df):
        return None

    total_ingestion = float(weave_df["total_storage_gb"].sum())

    # Get limit if available
    limit_gb = None
    if "weave_data_ingestion_limit_gb" in weave_df.columns:
        limits = weave_df["weave_data_ingestion_limit_gb"].dropna()
        if not limits.empty:
            limit_gb = float(limits.iloc[0])

    utilization_pct = round((total_ingestion / limit_gb) * 100, 1) if limit_gb else None

    # Get unique users from last 90 days (last 3 months)
    unique_users_90d = None
    if "unique_users" in weave_df.columns:
        recent = weave_df.tail(3)
        unique_users_90d = int(recent["unique_users"].max()) if not recent["unique_users"].isna().all() else None

    history = []
    for _, row in weave_df.iterrows():
        entry = {
            "month": row["created_date"].strftime("%Y-%m"),
            "ingestion_gb": round(float(row.get("total_storage_gb", 0)), 1),
        }
        if "unique_users" in weave_df.columns:
            entry["unique_users"] = int(row.get("unique_users", 0))
        else:
            entry["unique_users"] = 0
        history.append(entry)

    result = {
        "ingestion_gb": round(total_ingestion, 1),
        "history": history,
    }
    if limit_gb is not None:
        result["limit_gb"] = limit_gb
        result["utilization_percent"] = utilization_pct
    if unique_users_90d is not None:
        result["unique_users_last_90d"] = unique_users_90d

    return result


def _build_tracked_hours(hours_df: pd.DataFrame) -> Optional[dict]:
    """Build tracked_hours sub-section from daily tracked hours data."""
    if _is_empty(hours_df):
        return None

    # Get latest row for headline stats
    latest = hours_df.iloc[-1]
    last_30d_hours = float(latest.get("last_30_days_tracked_hours", 0))
    if last_30d_hours == 0 and "tracked_hours" in hours_df.columns:
        # Fall back to sum of last 30 days
        thirty_days_ago = hours_df["date_day"].max() - timedelta(days=30)
        recent = hours_df[hours_df["date_day"] >= thirty_days_ago]
        last_30d_hours = float(recent["tracked_hours"].sum())

    last_30d_run_count = int(latest.get("last_30_days_run_count", 0))

    # Aggregate to weekly using "sum" (weekly totals match 30d KPI scale)
    weekly = aggregate_weekly(
        hours_df,
        date_col="date_day",
        value_cols=["tracked_hours"],
        method="sum",
    )

    history = []
    for _, row in weekly.iterrows():
        history.append({
            "week": row["date_day"].strftime("%Y-%m-%d"),
            "tracked_hours": round(float(row.get("tracked_hours", 0)), 1),
        })

    return {
        "last_30d_hours": round(last_30d_hours, 1),
        "last_30d_run_count": last_30d_run_count,
        "history": history,
    }


def _build_account_health(account_df: pd.DataFrame) -> Optional[dict]:
    """Build account_health sub-section from account metadata."""
    if _is_empty(account_df):
        return None

    row = account_df.iloc[0]

    def _val(key, convert=None):
        v = row.get(key)
        if pd.isna(v) if isinstance(v, float) else v is None:
            return None
        if convert:
            return convert(v)
        return v

    return {
        "renewal_date": _val("renewal_date", lambda v: str(v)[:10] if v else None),
        "arr": _val("arr", float),
        "cs_tier": _val("cs_tier", str),
        "customer_health": _val("customer_health", str),
        "churn_probability_3mo": _val("churn_probability_3mo", float),
        "churn_probability_5mo": _val("churn_probability_5mo", float),
        "subscription_plan": _val("subscription_plan", str),
        "deployment_type": _val("deployment_type", str),
        # Entitlement fields for pipeline enrichment
        "product_family_sold": _val("product_family_sold", str),
        "weave_customer": _val("weave_customer", bool),
        "current_weave_arr": _val("current_weave_arr", float),
        "weave_commitment_gb": _val("weave_commitment_gb", float),
        "contracted_cloud_seats": _val("contracted_cloud_seats", int),
        "contracted_local_seats": _val("contracted_local_seats", int),
        "total_contracted_seats": _val("total_contracted_seats", int),
        "active_cloud_seats": _val("active_cloud_seats", int),
        "active_local_seats": _val("active_local_seats", int),
        "total_active_seats": _val("total_active_seats", int),
    }


def _build_product_areas(pa_df: pd.DataFrame) -> Optional[list]:
    """Build product_areas list from monthly product area data."""
    if _is_empty(pa_df):
        return None

    areas = {}
    for _, row in pa_df.iterrows():
        area = row["product_area"]
        if area not in areas:
            areas[area] = {"area": area, "total_events": 0, "unique_users": 0, "monthly_events": []}
        evt = int(row["event_count"]) if pd.notna(row["event_count"]) else 0
        usr = int(row["unique_users"]) if pd.notna(row["unique_users"]) else 0
        areas[area]["total_events"] += evt
        areas[area]["unique_users"] = max(areas[area]["unique_users"], usr)
        areas[area]["monthly_events"].append({
            "month": row["month"],
            "count": evt,
            "users": usr,
        })

    # Remove low-signal categories
    # "Collaboration" is just team_or_profile_viewed — page views, not real collaboration
    noise = {"Collaboration", "Other"}
    result = [a for a in areas.values() if a["area"] not in noise]
    result = sorted(result, key=lambda x: x["unique_users"], reverse=True)

    # Normalize radar values by unique_users (adoption breadth, not raw event volume)
    max_users = max(a["unique_users"] for a in result) if result else 1
    for a in result:
        a["radar_value"] = round((a["unique_users"] / max_users) * 100, 1) if max_users > 0 else 0

    return result


def _build_power_users(pu_df: pd.DataFrame, internal: bool = False) -> Optional[list]:
    """Build power_users list from per-user activity data."""
    if _is_empty(pu_df):
        return None

    users = []
    for _, row in pu_df.iterrows():
        # Handle product_areas which comes as a BQ ARRAY (numpy array in pandas)
        pa_raw = row.get("product_areas")
        if pa_raw is not None:
            try:
                pa_list = list(pa_raw) if hasattr(pa_raw, '__iter__') and not isinstance(pa_raw, str) else []
            except (TypeError, ValueError):
                pa_list = []
        else:
            pa_list = []

        # Resolve username: prefer real username, fall back to universal_user_id prefix
        raw_username = row.get("username")
        if raw_username and raw_username != "unknown" and pd.notna(raw_username):
            username = raw_username
        else:
            uid = row.get("universal_user_id")
            username = f"user-{str(uid)[:8]}" if uid and pd.notna(uid) else "unknown"

        user = {
            "username": username,
            "total_events": int(row["total_events"]) if pd.notna(row["total_events"]) else 0,
            "last_activity": str(row["last_activity"])[:10] if pd.notna(row.get("last_activity")) else None,
            "active_weeks": int(row["active_weeks"]) if pd.notna(row.get("active_weeks")) else 0,
            "product_areas": pa_list,
        }
        if internal:
            user["email"] = row.get("email") or ""
        users.append(user)

    return users


def _build_weave_activity(activity_df: pd.DataFrame) -> Optional[list]:
    """Build weave_activity list (monthly events by sub-area) from raw event data."""
    if _is_empty(activity_df):
        return None

    result = []
    for _, row in activity_df.iterrows():
        result.append({
            "month": str(row["month"]),
            "area": str(row["area"]),
            "events": int(row["events"]) if pd.notna(row.get("events")) else 0,
            "users": int(row["users"]) if pd.notna(row.get("users")) else 0,
        })
    return result


def _build_weave_users(users_df: pd.DataFrame, internal: bool = False) -> Optional[list]:
    """Build weave_users list (per-user Weave totals) from resolved-name data.

    Keeps email in both internal and external output -- the template decides
    whether to display or anonymise it.
    """
    if _is_empty(users_df):
        return None

    result = []
    for _, row in users_df.iterrows():
        result.append({
            "username": str(row["uname"]) if pd.notna(row.get("uname")) else "",
            "email": str(row["email"]) if pd.notna(row.get("email")) else "",
            "events": int(row["events"]) if pd.notna(row.get("events")) else 0,
            "first_day": str(row["first_day"])[:10] if pd.notna(row.get("first_day")) else None,
            "last_day": str(row["last_day"])[:10] if pd.notna(row.get("last_day")) else None,
        })
    return result


def _build_support_tickets(tickets_df: pd.DataFrame) -> Optional[dict]:
    """Build support_tickets sub-section from per-ticket helpdesk data."""
    if _is_empty(tickets_df):
        return None

    total = len(tickets_df)

    # Status distribution
    by_status = {}
    if "ticket_status" in tickets_df.columns:
        counts = tickets_df["ticket_status"].value_counts()
        by_status = {str(k): int(v) for k, v in counts.items()}

    # Priority distribution
    by_priority = {}
    if "ticket_priority" in tickets_df.columns:
        counts = tickets_df["ticket_priority"].dropna().value_counts()
        by_priority = {str(k): int(v) for k, v in counts.items()}

    # Escalation count
    escalated_count = 0
    if "escalated_to_jira" in tickets_df.columns:
        escalated_count = int(
            tickets_df["escalated_to_jira"]
            .fillna("")
            .apply(lambda v: str(v).lower() not in ("", "no", "false", "nan", "none"))
            .sum()
        )

    # CSAT distribution
    csat = {}
    if "ticket_satisfaction_score" in tickets_df.columns:
        scores = tickets_df["ticket_satisfaction_score"].dropna()
        scores = scores[scores != ""]
        if not scores.empty:
            csat_counts = scores.value_counts()
            csat = {str(k): int(v) for k, v in csat_counts.items()}

    # Top concerns
    top_concerns = []
    if "primary_ticket_concern" in tickets_df.columns:
        concerns = tickets_df["primary_ticket_concern"].dropna()
        concerns = concerns[concerns != ""]
        if not concerns.empty:
            concern_counts = concerns.value_counts().head(10)
            top_concerns = [
                {"concern": str(k), "count": int(v)}
                for k, v in concern_counts.items()
            ]

    # Monthly volume trend
    monthly_volume = []
    if "ticket_created_date_day" in tickets_df.columns:
        work = tickets_df.copy()
        work["month"] = pd.to_datetime(work["ticket_created_date_day"]).dt.to_period("M")
        monthly = work.groupby("month").size().sort_index()
        monthly_volume = [
            {"month": str(m), "count": int(c)}
            for m, c in monthly.items()
        ]

    # Recent non-closed tickets (most useful for dashboard detail view)
    recent_tickets = []
    open_mask = tickets_df["ticket_status"].isin(["new", "open", "pending", "hold"])
    open_df = tickets_df[open_mask].head(25)
    for _, row in open_df.iterrows():
        ticket = {
            "id": int(row["zendesk_ticket_id"]) if pd.notna(row.get("zendesk_ticket_id")) else None,
            "subject": str(row.get("ticket_subject", ""))[:120],
            "status": str(row.get("ticket_status", "")),
            "priority": str(row.get("ticket_priority", "")) if pd.notna(row.get("ticket_priority")) else None,
            "created_at": str(row["ticket_created_at"])[:10] if pd.notna(row.get("ticket_created_at")) else None,
            "updated_at": str(row["ticket_last_updated_at"])[:10] if pd.notna(row.get("ticket_last_updated_at")) else None,
            "concern": str(row.get("primary_ticket_concern", "")) if pd.notna(row.get("primary_ticket_concern")) else None,
            "channel": str(row.get("channel", "")) if pd.notna(row.get("channel")) else None,
        }
        jira_id = row.get("jira_id")
        if jira_id and pd.notna(jira_id) and str(jira_id).strip():
            ticket["jira_id"] = str(jira_id).strip()
            jira_link = row.get("jira_link")
            if jira_link and pd.notna(jira_link):
                ticket["jira_link"] = str(jira_link).strip()
        recent_tickets.append(ticket)

    # Top submitters
    top_submitters = []
    if "submitter_name" in tickets_df.columns:
        submitters = tickets_df.copy()
        submitters["submitter"] = submitters["submitter_name"].fillna("Unknown")
        grouped = submitters.groupby("submitter")
        sub_counts = grouped.size().sort_values(ascending=False).head(10)
        for name, count in sub_counts.items():
            sub_data = submitters[submitters["submitter"] == name]
            concerns = []
            if "primary_ticket_concern" in sub_data.columns:
                concern_counts = sub_data["primary_ticket_concern"].dropna().value_counts()
                concerns = [
                    {"concern": str(k), "count": int(v)}
                    for k, v in concern_counts.head(5).items()
                ]
            top_submitters.append({
                "name": str(name),
                "count": int(count),
                "concerns": concerns,
            })

    return {
        "total": total,
        "by_status": by_status,
        "by_priority": by_priority,
        "escalated_to_jira": escalated_count,
        "csat": csat,
        "top_concerns": top_concerns,
        "monthly_volume": monthly_volume,
        "recent_tickets": recent_tickets,
        "top_submitters": top_submitters,
    }


def build_usage_json(
    seat_df: pd.DataFrame,
    weave_df: pd.DataFrame,
    hours_df: pd.DataFrame,
    account_df: pd.DataFrame,
    product_areas_df: pd.DataFrame = None,
    power_users_df: pd.DataFrame = None,
    support_tickets_df: pd.DataFrame = None,
    weave_activity_df: pd.DataFrame = None,
    weave_users_df: pd.DataFrame = None,
    internal: bool = False,
    include_queries: bool = False,
) -> dict:
    """
    Build the INTELLIGENCE_DATA.usage JSON from 4 DataFrames.

    Each sub-section independently degrades when its DataFrame is empty/None.
    If ALL sub-sections are null, returns {"available": false, "reason": "no_data"}.

    Args:
        seat_df: Daily seat utilization data
        weave_df: Monthly Weave ingestion data
        hours_df: Daily tracked hours data
        account_df: Account health metadata

    Returns:
        Dict matching INTELLIGENCE_DATA.usage schema
    """
    seat_util = _build_seat_utilization(seat_df)
    weave = _build_weave(weave_df)
    tracked = _build_tracked_hours(hours_df)
    health = _build_account_health(account_df)
    product_areas = _build_product_areas(product_areas_df)
    power_users = _build_power_users(power_users_df, internal=internal)
    support_tickets = _build_support_tickets(support_tickets_df)
    # Weave activity/users are computed independently of the weave_customer
    # suppression below -- trial/unpaid Weave customers (e.g. RBR) still get these.
    weave_activity = _build_weave_activity(weave_activity_df)
    weave_users = _build_weave_users(weave_users_df, internal=internal)

    # Enrich with SFDC entitlement data if available
    if health:
        # Override seat headline with SFDC contracted/active (more reliable than BQ latest snapshot)
        sfdc_contracted = health.get("total_contracted_seats") or 0
        sfdc_active = health.get("total_active_seats") or 0
        if seat_util and sfdc_contracted > 0:
            seat_util["contracted"] = sfdc_contracted
            seat_util["active"] = sfdc_active
            seat_util["utilization_percent"] = round((sfdc_active / sfdc_contracted) * 100, 1)
            seat_util["zone"] = classify_utilization_zone(seat_util["utilization_percent"])
            # Tag deployment type so template knows cloud vs local
            seat_util["deployment_type"] = health.get("deployment_type")

        # Suppress Weave section if customer is not a Weave customer
        if not health.get("weave_customer"):
            weave = None
            # Also filter Weave areas from product adoption radar
            if product_areas:
                product_areas = [a for a in product_areas if not a["area"].startswith("Weave")]

        # Enrich Weave with SFDC commitment as limit_gb if contracted
        if weave and health.get("weave_commitment_gb"):
            weave["limit_gb"] = health["weave_commitment_gb"]
            if weave["ingestion_gb"] > 0:
                weave["utilization_percent"] = round(
                    (weave["ingestion_gb"] / weave["limit_gb"]) * 100, 1
                )

    # If all sections are None, no data available
    if all(s is None for s in [seat_util, weave, tracked, health, support_tickets]):
        return {"available": False, "reason": "no_data"}

    # Build BQ query strings for data provenance (SQL copy buttons in dashboard)
    bq_queries = None
    if include_queries:
        bq_queries = {
            "seat_utilization": seat_utilization_query().strip(),
            "weave_ingestion": weave_ingestion_query().strip(),
            "tracked_hours": tracked_hours_query().strip(),
            "product_areas": product_areas_query().strip(),
            "support_tickets": support_tickets_query().strip(),
            "account_health": account_health_query().strip(),
        }

    # Compute period from available data
    today = date.today()
    period_start = today - timedelta(days=365)

    return {
        "available": True,
        "period": {
            "start": period_start.isoformat(),
            "end": today.isoformat(),
        },
        "seat_utilization": seat_util,
        "weave": weave,
        "weave_activity": weave_activity,
        "weave_users": weave_users,
        "tracked_hours": tracked,
        "account_health": health,
        "product_areas": product_areas,
        "power_users": power_users,
        "support_tickets": support_tickets,
        "bq_queries": bq_queries,
    }


def main():
    """CLI entry point for usage data pipeline."""
    parser = argparse.ArgumentParser(
        description="Fetch and aggregate customer usage data from BigQuery"
    )
    parser.add_argument(
        "--customer", required=True, help="Customer name (matched against customers.yaml)"
    )
    parser.add_argument(
        "--format", choices=["json", "text"], default="json",
        help="Output format (default: json)"
    )
    parser.add_argument(
        "--months", type=int, default=12,
        help="Lookback months (default: 12)"
    )
    parser.add_argument(
        "--internal", action="store_true",
        help="Include internal-only data (power user real names/emails)"
    )
    args = parser.parse_args()

    try:
        # Look up SFDC account ID
        account_id = get_sfdc_account_id(args.customer)

        # Create BigQuery client
        client = get_client()

        # Run all 7 queries
        seat_df = run_query(client, seat_utilization_query(), account_id=account_id)
        weave_df = run_query(client, weave_ingestion_query(), account_id=account_id)
        hours_df = run_query(client, tracked_hours_query(), account_id=account_id)
        account_df = run_query(client, account_health_query(), account_id=account_id)
        # months=0 (or negative) -> full history; reveals multi-year adoption shifts
        pa_months = args.months if args.months and args.months > 0 else None
        pa_df = run_query(client, product_areas_query(months=pa_months), account_id=account_id)
        pu_df = run_query(client, power_users_query(), account_id=account_id)
        tickets_df = run_query(client, support_tickets_query(), account_id=account_id)
        weave_activity_df = run_query(client, weave_activity_query(), account_id=account_id)
        weave_users_df = run_query(client, weave_users_query(), account_id=account_id)

        # Build JSON output
        result = build_usage_json(
            seat_df, weave_df, hours_df, account_df, pa_df, pu_df, tickets_df,
            weave_activity_df=weave_activity_df,
            weave_users_df=weave_users_df,
            internal=getattr(args, 'internal', False),
            include_queries=True,
        )

    except ValueError as e:
        # Customer not found or PLACEHOLDER
        result = {"available": False, "reason": "config_error", "detail": str(e)}
    except Exception as e:
        # BigQuery connection or query error
        result = {"available": False, "reason": "api_error", "detail": str(e)}

    # Output
    if args.format == "json":
        print(json.dumps(result, indent=2, default=str))
    else:
        if result.get("available"):
            print(f"Usage data for {args.customer}:")
            if result.get("seat_utilization"):
                su = result["seat_utilization"]
                print(f"  Seats: {su['active']}/{su['contracted']} ({su['utilization_percent']}%)")
            if result.get("weave"):
                w = result["weave"]
                print(f"  Weave: {w['ingestion_gb']} GB ingested")
            if result.get("tracked_hours"):
                th = result["tracked_hours"]
                print(f"  Hours: {th['last_30d_hours']}h last 30d ({th['last_30d_run_count']} runs)")
            if result.get("account_health"):
                ah = result["account_health"]
                print(f"  Health: {ah['customer_health']} | Tier: {ah['cs_tier']}")
            if result.get("support_tickets"):
                st = result["support_tickets"]
                open_count = st["by_status"].get("open", 0) + st["by_status"].get("pending", 0) + st["by_status"].get("new", 0) + st["by_status"].get("hold", 0)
                print(f"  Support: {st['total']} tickets (12mo), {open_count} open, {st['escalated_to_jira']} escalated")
        else:
            print(f"No usage data: {result.get('reason', 'unknown')}")
            if result.get("detail"):
                print(f"  Detail: {result['detail']}")


if __name__ == "__main__":
    main()
