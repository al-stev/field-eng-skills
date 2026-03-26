#!/usr/bin/env python3
"""
Deep Analytics page generator.

CLI orchestrator that routes --customer/--page to the correct query + transform + template
pipeline. Produces self-contained HTML files in customers/<name>/analytics/.

Usage:
    uv run --project .claude/skills/deep-analytics python \
        .claude/skills/deep-analytics/scripts/generate.py \
        --customer GResearch --page user-journey
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
SKILLS_DIR = SKILL_DIR.parent  # .claude/skills/
PROJECT_ROOT = SKILLS_DIR.parents[1]  # project root
TEMPLATES_DIR = SKILL_DIR / "templates"

# Add bigquery scripts to path (same pattern as usage.py)
sys.path.insert(0, str(SKILLS_DIR / "bigquery" / "scripts"))

# Add deep-analytics scripts to path for local imports
sys.path.insert(0, str(SCRIPT_DIR))


# Page type registry -- maps CLI arg to handler function
# Handlers will be added in Phases 2-4 as each page is implemented.
# For now, all entries point to a placeholder that returns sample data.
def _placeholder_handler(client, account_id, customer_name):
    """Placeholder handler for pages not yet implemented."""
    return {
        "customer": customer_name,
        "generated": date.today().isoformat(),
        "period": {"start": "2025-03-24", "end": "2026-03-24"},
        "available": False,
        "reason": "not_implemented",
        "page_type": "placeholder",
        "kpis": [
            {"value": "--", "label": "Total Users"},
            {"value": "--", "label": "Active (30d)"},
            {"value": "--", "label": "Top Product Area"},
            {"value": "--", "label": "Data Period"},
        ],
    }


def _feature_velocity_handler(client, account_id, customer_name):
    """Feature Velocity — real BQ data via product_areas_query()."""
    from queries import product_areas_query, account_health_query
    from bq_client import run_query
    from transforms.feature_velocity import FeatureVelocityTransform

    sql = product_areas_query()
    df = run_query(client, sql, account_id=account_id, maximum_bytes_billed=50_000_000_000)

    # Check if customer has Weave contracted
    health_df = run_query(client, account_health_query(), account_id=account_id, maximum_bytes_billed=50_000_000_000)
    weave_customer = False
    if not health_df.empty and "weave_customer" in health_df.columns:
        weave_customer = bool(health_df.iloc[0].get("weave_customer", False))

    transform = FeatureVelocityTransform()
    return transform.transform(product_areas=df, customer_name=customer_name, weave_customer=weave_customer)


def _user_journey_handler(client, account_id, customer_name):
    """User Journey — adoption funnel Sankey from dim_users first_*_at fields."""
    from queries import user_journey_query, account_health_query
    from bq_client import run_query
    from transforms.user_journey import UserJourneyTransform

    sql = user_journey_query()
    df = run_query(client, sql, account_id=account_id, maximum_bytes_billed=100_000_000_000)

    # Check Weave status
    health_df = run_query(client, account_health_query(), account_id=account_id, maximum_bytes_billed=50_000_000_000)
    weave_customer = False
    if not health_df.empty and "weave_customer" in health_df.columns:
        weave_customer = bool(health_df.iloc[0].get("weave_customer", False))

    transform = UserJourneyTransform()
    return transform.transform(user_journey=df, customer_name=customer_name, weave_customer=weave_customer)


def _engagement_decay_handler(client, account_id, customer_name):
    """Engagement Decay — per-user activity decline detection."""
    from queries import engagement_decay_query, account_health_query
    from bq_client import run_query
    from transforms.engagement_decay import EngagementDecayTransform

    sql = engagement_decay_query()
    df = run_query(client, sql, account_id=account_id, maximum_bytes_billed=50_000_000_000)

    # Get contracted seats for licensed-user filtering
    health_df = run_query(client, account_health_query(), account_id=account_id, maximum_bytes_billed=50_000_000_000)
    contracted_seats = None
    if not health_df.empty:
        contracted_seats = health_df.iloc[0].get("total_contracted_seats")
        if contracted_seats is not None:
            contracted_seats = int(contracted_seats)

    transform = EngagementDecayTransform()
    return transform.transform(engagement=df, customer_name=customer_name, contracted_seats=contracted_seats)


def _sdk_versions_handler(client, account_id, customer_name):
    """SDK Versions — cli_version/local_version distribution and freshness."""
    from queries import sdk_versions_query
    from bq_client import run_query
    from transforms.sdk_versions import SdkVersionsTransform

    sql = sdk_versions_query()
    df = run_query(client, sql, account_id=account_id, maximum_bytes_billed=50_000_000_000)

    transform = SdkVersionsTransform()
    return transform.transform(sdk_versions=df, customer_name=customer_name)


def _team_detection_handler(client, account_id, customer_name):
    """Team Detection -- organizational structure from org_name fields."""
    from queries import team_detection_query, team_champions_query, account_health_query
    from bq_client import run_query
    from transforms.team_detection import TeamDetectionTransform
    from schema_validator import check_data_availability, PHASE3_DATA_CHECKS

    # Check team data availability before running expensive queries
    avail = check_data_availability(client, account_id, {
        "team_org_names": PHASE3_DATA_CHECKS["team_org_names"],
        "team_flags": PHASE3_DATA_CHECKS["team_flags"],
    })

    teams_df = run_query(client, team_detection_query(),
                         account_id=account_id, maximum_bytes_billed=100_000_000_000)

    # Only query champions if we have team data with org names
    champions_df = None
    if avail.get("team_org_names", {}).get("available", False):
        try:
            champions_df = run_query(client, team_champions_query(),
                                     account_id=account_id, maximum_bytes_billed=50_000_000_000)
        except Exception:
            pass

    # Get deployment type for data provenance
    health_df = run_query(client, account_health_query(),
                          account_id=account_id, maximum_bytes_billed=50_000_000_000)
    deployment_type = "Unknown"
    if not health_df.empty and "deployment_type" in health_df.columns:
        deployment_type = str(health_df.iloc[0].get("deployment_type", "Unknown"))

    transform = TeamDetectionTransform()
    return transform.transform(
        teams=teams_df, champions=champions_df,
        customer_name=customer_name, deployment_type=deployment_type
    )


def _cohort_analysis_handler(client, account_id, customer_name):
    """Cohort Analysis -- retention heatmap from user activity data."""
    from queries import cohort_retention_query, user_lifecycle_query, user_journey_query
    from bq_client import run_query
    from transforms.cohort_analysis import CohortAnalysisTransform
    from schema_validator import check_data_availability, PHASE3_DATA_CHECKS

    # Check if preferred retention features table is available
    avail = check_data_availability(client, account_id,
        {"retention_features": PHASE3_DATA_CHECKS["retention_features"]})

    # Always use fallback (activity-based) for now -- safer and always available
    retention_df = run_query(client, cohort_retention_query(),
                             account_id=account_id, maximum_bytes_billed=50_000_000_000)

    # Lifecycle data
    lifecycle_df = None
    try:
        lifecycle_df = run_query(client, user_lifecycle_query(),
                                 account_id=account_id, maximum_bytes_billed=50_000_000_000)
    except Exception:
        pass  # Transform handles None lifecycle gracefully

    # Journey data for behavioral cohorts (reuse existing query)
    journey_df = None
    try:
        journey_df = run_query(client, user_journey_query(),
                               account_id=account_id, maximum_bytes_billed=100_000_000_000)
    except Exception:
        pass

    transform = CohortAnalysisTransform()
    return transform.transform(
        retention=retention_df, lifecycle=lifecycle_df, journey=journey_df,
        customer_name=customer_name,
        data_source="ext_daily_user_event_usage (activity-based cohorts)"
    )


def _risk_scoring_handler(client, account_id, customer_name):
    """Risk Scoring -- composite churn risk from engagement, utilization, churn model."""
    from queries import engagement_trend_query, risk_support_tickets_query, account_health_query, seat_utilization_query
    from bq_client import run_query
    from transforms.risk_scoring import RiskScoringTransform
    from schema_validator import check_data_availability, PHASE3_DATA_CHECKS

    # Check data availability for optional sources
    avail = check_data_availability(client, account_id, {
        "renewal_predictions": PHASE3_DATA_CHECKS["renewal_predictions"],
        "engagement_scores": PHASE3_DATA_CHECKS["engagement_scores"],
    })

    # Account health (includes churn probability if available)
    health_df = run_query(client, account_health_query(),
                          account_id=account_id, maximum_bytes_billed=50_000_000_000)

    # Engagement trend (6 months)
    engagement_df = pd.DataFrame()
    if avail.get("engagement_scores", {}).get("available", False):
        try:
            engagement_df = run_query(client, engagement_trend_query(),
                                      account_id=account_id, maximum_bytes_billed=50_000_000_000)
        except Exception:
            pass

    # Seat utilization
    seats_df = run_query(client, seat_utilization_query(),
                         account_id=account_id, maximum_bytes_billed=50_000_000_000)

    # Support tickets
    tickets_df = pd.DataFrame()
    try:
        tickets_df = run_query(client, risk_support_tickets_query(),
                               account_id=account_id, maximum_bytes_billed=50_000_000_000)
    except Exception:
        pass

    transform = RiskScoringTransform()
    return transform.transform(
        engagement=engagement_df, health=health_df,
        seats=seats_df, tickets=tickets_df,
        customer_name=customer_name
    )


def _performance_handler(client, account_id, customer_name):
    """Performance Deep Dive -- application performance from low-confidence BQ tables.
    Includes go/no-go gate: validates schema + checks data before proceeding."""
    from queries import performance_query, latency_distribution_query, slow_chart_users_query, account_health_query
    from bq_client import run_query
    from transforms.performance import PerformanceTransform
    from schema_validator import (validate_tables, check_data_availability,
                                   PHASE4_SCHEMA_SPECS, PHASE4_DATA_CHECKS)

    transform = PerformanceTransform()

    # --- GO/NO-GO GATE ---
    # Gate 1: Schema validation -- do the tables exist with expected columns?
    perf_table = "`wandb-production.analytics.fct_application_performance`"
    schema_results = validate_tables(client, {
        perf_table: PHASE4_SCHEMA_SPECS[perf_table]
    })
    if not schema_results[perf_table]["valid"]:
        return transform.descoped_result("schema_error")

    # Gate 2: Data availability -- does this account have rows?
    avail = check_data_availability(client, account_id, {
        "perf_index": PHASE4_DATA_CHECKS["perf_index"],
    })
    if not avail.get("perf_index", {}).get("available", False):
        return transform.descoped_result("performance_descoped")

    # --- GATE PASSED: proceed with full pipeline ---
    perf_df = run_query(client, performance_query(),
                        account_id=account_id, maximum_bytes_billed=50_000_000_000)

    if perf_df.empty:
        return transform.descoped_result("performance_descoped")

    # Latency and slow users are best-effort (tables may not exist)
    latency_df = None
    try:
        latency_table = "`wandb-production.analytics.fct_onscreen_loader_latencies`"
        lat_schema = validate_tables(client, {
            latency_table: PHASE4_SCHEMA_SPECS[latency_table]
        })
        if lat_schema[latency_table]["valid"]:
            lat_avail = check_data_availability(client, account_id, {
                "latency_data": PHASE4_DATA_CHECKS["latency_data"],
            })
            if lat_avail.get("latency_data", {}).get("available", False):
                latency_df = run_query(client, latency_distribution_query(),
                                       account_id=account_id, maximum_bytes_billed=50_000_000_000)
    except Exception:
        pass

    slow_users_df = None
    try:
        slow_table = "`wandb-production.analytics.agg_daily_team_members_slow_chart_loads`"
        slow_schema = validate_tables(client, {
            slow_table: PHASE4_SCHEMA_SPECS[slow_table]
        })
        if slow_schema[slow_table]["valid"]:
            slow_avail = check_data_availability(client, account_id, {
                "slow_chart_data": PHASE4_DATA_CHECKS["slow_chart_data"],
            })
            if slow_avail.get("slow_chart_data", {}).get("available", False):
                slow_users_df = run_query(client, slow_chart_users_query(),
                                          account_id=account_id, maximum_bytes_billed=50_000_000_000)
    except Exception:
        pass

    # Get deployment type
    health_df = run_query(client, account_health_query(),
                          account_id=account_id, maximum_bytes_billed=50_000_000_000)
    deployment_type = "Unknown"
    if not health_df.empty and "deployment_type" in health_df.columns:
        deployment_type = str(health_df.iloc[0].get("deployment_type", "Unknown"))

    return transform.transform(
        perf_df=perf_df,
        latency_df=latency_df if latency_df is not None else pd.DataFrame(),
        slow_users_df=slow_users_df if slow_users_df is not None else pd.DataFrame(),
        customer_name=customer_name,
        deployment_type=deployment_type,
    )


PAGE_REGISTRY = {
    "user-journey": _user_journey_handler,
    "cohort-analysis": _cohort_analysis_handler,
    "engagement-decay": _engagement_decay_handler,
    "feature-velocity": _feature_velocity_handler,
    "team-detection": _team_detection_handler,
    "risk-scoring": _risk_scoring_handler,
    "usage-correlation": _placeholder_handler,
    "sdk-versions": _sdk_versions_handler,
    "performance": _performance_handler,
}


def build_output_path(customer_name: str, page_type: str, output_dir: str | None = None) -> Path:
    """
    Build the output file path for a generated analytics page.

    Convention: customers/<kebab-case-name>/analytics/YYYY-MM-DD-<page-type>.html

    Args:
        customer_name: Customer display name
        page_type: Page type slug (e.g., "user-journey")
        output_dir: Override output directory (optional)

    Returns:
        Path to the output HTML file
    """
    from common.data_utils import kebab_case

    if output_dir:
        out = Path(output_dir)
    else:
        slug = kebab_case(customer_name)
        out = PROJECT_ROOT / "customers" / slug / "analytics"

    out.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    return out / f"{today}-{page_type}.html"


def inject_page_data(template: str, data: dict) -> str:
    """
    Replace PAGE_DATA constant in template using sentinel comments.

    Template contains:
        /* PAGE_DATA_START */
        const PAGE_DATA = {...};
        /* PAGE_DATA_END */

    The content between sentinels is replaced with the real data.
    """
    START = "/* PAGE_DATA_START */"
    END = "/* PAGE_DATA_END */"

    start_idx = template.index(START) + len(START)
    end_idx = template.index(END)

    data_json = json.dumps(data, indent=2, default=str)
    return template[:start_idx] + f"\nconst PAGE_DATA = {data_json};\n" + template[end_idx:]


def inject_ai_narrative(template: str, narrative: dict) -> str:
    """
    Replace AI_NARRATIVE constant in template using sentinel comments.

    Template contains:
        /* AI_NARRATIVE_START */
        const AI_NARRATIVE = {...};
        /* AI_NARRATIVE_END */
    """
    START = "/* AI_NARRATIVE_START */"
    END = "/* AI_NARRATIVE_END */"

    start_idx = template.index(START) + len(START)
    end_idx = template.index(END)

    narrative_json = json.dumps(narrative, indent=2, default=str)
    return template[:start_idx] + f"\nconst AI_NARRATIVE = {narrative_json};\n" + template[end_idx:]


def write_output(
    customer_name: str,
    page_type: str,
    page_data: dict,
    ai_narrative: dict | None = None,
    output_dir: str | None = None,
    template_name: str = "base-template.html",
) -> Path:
    """
    Read template, inject data, write output file.

    Args:
        customer_name: Customer display name
        page_type: Page type slug
        page_data: PAGE_DATA dict for injection
        ai_narrative: AI_NARRATIVE dict for injection (optional)
        output_dir: Override output directory
        template_name: Template filename in templates/ dir

    Returns:
        Path to the generated HTML file
    """
    template_path = TEMPLATES_DIR / template_name
    template = template_path.read_text()

    # Inject PAGE_DATA
    template = inject_page_data(template, page_data)

    # Inject AI_NARRATIVE if provided
    if ai_narrative:
        template = inject_ai_narrative(template, ai_narrative)

    # Write output
    output_path = build_output_path(customer_name, page_type, output_dir)
    output_path.write_text(template)
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate deep analytics pages from BigQuery data"
    )
    parser.add_argument(
        "--customer", required=True,
        help="Customer name (must exist in templates/customers.yaml)"
    )
    parser.add_argument(
        "--page", required=True,
        choices=sorted(PAGE_REGISTRY.keys()),
        help="Analytics page type to generate"
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="Override output directory (default: customers/<name>/analytics/)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate schema and estimate cost without generating"
    )
    args = parser.parse_args()

    # Import BQ client (available via sys.path)
    from bq_client import get_client, get_sfdc_account_id

    # 1. Look up customer
    try:
        account_id = get_sfdc_account_id(args.customer)
    except ValueError as e:
        print(json.dumps({"success": False, "error": str(e)}, indent=2))
        sys.exit(1)

    client = get_client()

    # 2. Route to page-specific pipeline
    page_func = PAGE_REGISTRY[args.page]
    result = page_func(client, account_id, args.customer)

    # 3. Extract narrative if present
    narrative = result.pop("narrative", None)

    # 4. Write output
    if args.dry_run:
        print(json.dumps({"success": True, "dry_run": True, "data": result, "narrative": narrative}, indent=2))
    else:
        try:
            output_path = write_output(args.customer, args.page, result, ai_narrative=narrative, output_dir=args.output_dir)
            print(json.dumps({"success": True, "path": str(output_path)}, indent=2))
        except FileNotFoundError:
            print(json.dumps({
                "success": False,
                "error": "Template not found. Run Phase 1 Plan 03 to create base-template.html."
            }, indent=2))
            sys.exit(1)


if __name__ == "__main__":
    main()
