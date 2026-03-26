#!/usr/bin/env python3
"""
BigQuery query factory for W&B customer usage data.

Provides parameterized SQL queries for 4 metric categories:
- Seat utilization (contracted vs claimed vs active)
- Weave ingestion (GB ingested, unique users)
- Tracked hours / run count
- Account health / renewal data

Cherry-picked from apac-account-management/adapters/bq_queries.py.
Key adaptation: all AISE name filters replaced with @account_id parameter.
"""

from typing import Optional

import pandas as pd


PROJECT_ID = "wandb-production"


def _ref(table: str, dataset: str = "analytics") -> str:
    """
    Build a fully-qualified BigQuery table reference.

    Args:
        table: Table name
        dataset: Dataset name (default: analytics)

    Returns:
        Fully-qualified reference like `wandb-production.analytics.table_name`
    """
    return f"`{PROJECT_ID}.{dataset}.{table}`"


def identity_resolution_cte(table_alias: str = "src") -> str:
    """
    Returns a SQL CTE that resolves user identity for server deployments.

    Server deployments do not populate username/email in ext_daily_user_event_usage.
    This CTE LEFT JOINs dim_users to resolve local_username and local_user_email.

    The source query must have columns: universal_user_id, username, email.
    The enclosing query must have @account_id parameter bound.

    Args:
        table_alias: Alias for the source table/CTE that has universal_user_id,
                     username, and email columns.

    Returns:
        SQL string for a CTE named 'resolved_users' with columns:
        universal_user_id, resolved_username, resolved_email
    """
    dim_users = _ref("dim_users")
    return f"""
    resolved_users AS (
        SELECT
            {table_alias}.universal_user_id,
            COALESCE({table_alias}.username, du.local_username) AS resolved_username,
            COALESCE({table_alias}.email, du.local_user_email) AS resolved_email
        FROM {table_alias}
        LEFT JOIN {dim_users} du
            ON {table_alias}.universal_user_id = du.universal_user_id
            AND du.account_id = @account_id
    )
    """


def seat_utilization_query() -> str:
    """
    Daily seat utilization query -- contracted vs claimed vs active seats.

    Adapted from BigQueryQueryFactory.cloud_usage_history_query() +
    local_usage_history_query(). Combines cloud and local into a single query
    filtered by @account_id.

    Returns:
        SQL string with @account_id parameter placeholder
    """
    daily_usage = _ref("ext_daily_user_event_usage")
    return f"""
    SELECT
        account_id,
        date_day,
        MAX(COALESCE(active_cloud_enterprise_seats, 0) +
            COALESCE(active_cloud_self_service_seats, 0) +
            COALESCE(active_cloud_trial_seats, 0) +
            COALESCE(active_local_seats, 0)) AS active_seats,
        MAX(COALESCE(claimed_cloud_enterprise_models_full_seats, 0) +
            COALESCE(claimed_local_models_full_seats, 0)) AS claimed_seats,
        MAX(COALESCE(contracted_cloud_models_seats, 0) +
            COALESCE(contracted_local_models_seats, 0)) AS contracted_seats
    FROM {daily_usage}
    WHERE account_id = @account_id
        AND date_day >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
        AND product_type != 'weave'
    GROUP BY account_id, date_day
    ORDER BY date_day
    """


def weave_ingestion_query() -> str:
    """
    Monthly Weave ingestion query -- GB ingested per month with unique users.

    Adapted from BigQueryQueryFactory.weave_usage_history_query() +
    weave_monthly_users_query(). Joins through dim_organizations to filter
    by account_id. Keeps the APAC unit normalization CASE statement for
    MB/GB/TB -> GB conversion.

    Returns:
        SQL string with @account_id parameter placeholder
    """
    weave_storage = _ref("fct_weave_project_storage")
    dim_organizations = _ref("dim_organizations")
    dim_opportunities = _ref("dim_opportunities")
    daily_usage = _ref("ext_daily_user_event_usage")
    return f"""
    WITH weave_data AS (
        SELECT
            orgs.account_id,
            DATE_TRUNC(DATE(storage.created_at), MONTH) AS created_date,
            SUM(storage.storage_gb) AS total_storage_gb
        FROM {weave_storage} AS storage
        JOIN {dim_organizations} AS orgs USING (organization_id)
        WHERE orgs.account_id = @account_id
            AND DATE(storage.created_at) >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
            AND storage.storage_type NOT IN ('feedback', 'call_exception')
        GROUP BY 1, 2
    ),
    weave_users AS (
        SELECT
            DATE_TRUNC(date_day, MONTH) AS month,
            COUNT(DISTINCT universal_user_id) AS unique_users
        FROM {daily_usage}
        WHERE product_type = 'weave'
            AND account_id = @account_id
            AND date_day >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
        GROUP BY 1
    ),
    weave_limit AS (
        SELECT
            account_id,
            CASE
                WHEN weave_data_ingestion_uoms[OFFSET(0)] = 'MB'
                    THEN total_weave_data_ingestion_limit / 1000
                WHEN weave_data_ingestion_uoms[OFFSET(0)] = 'TB'
                    THEN total_weave_data_ingestion_limit * 1000
                ELSE total_weave_data_ingestion_limit
            END AS weave_data_ingestion_limit_gb
        FROM {dim_opportunities}
        WHERE account_id = @account_id
            AND total_weave_data_ingestion_limit IS NOT NULL
            AND is_won IS TRUE
            AND service_type = 'Touch'
            AND CURRENT_DATE() BETWEEN DATE(contract_start_date) AND DATE(contract_end_date)
        LIMIT 1
    )
    SELECT
        wd.account_id,
        wd.created_date,
        wd.total_storage_gb,
        COALESCE(wu.unique_users, 0) AS unique_users,
        wl.weave_data_ingestion_limit_gb
    FROM weave_data wd
    LEFT JOIN weave_users wu ON wd.created_date = wu.month
    LEFT JOIN weave_limit wl ON wd.account_id = wl.account_id
    ORDER BY wd.created_date
    """


def tracked_hours_query() -> str:
    """
    Daily tracked hours and run count query.

    Adapted from BigQueryQueryFactory.tracked_hours_history_query().
    Filtered by @account_id parameter.

    Returns:
        SQL string with @account_id parameter placeholder
    """
    company_usage = _ref("agg_daily_company_usage")
    return f"""
    SELECT
        account_id,
        date_day,
        tracked_hours,
        last_30_days_tracked_hours,
        last_30_days_run_count
    FROM {company_usage}
    WHERE account_id = @account_id
        AND date_day >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
        AND tracked_hours > 0
    ORDER BY date_day
    """


def product_areas_query() -> str:
    """
    Product area usage breakdown -- maps event types to W&B marketecture areas.

    Returns monthly event counts and unique users per product area.
    """
    daily_usage = _ref("ext_daily_user_event_usage")
    return f"""
    WITH mapped AS (
        SELECT
            date_day,
            universal_user_id,
            event_count,
            CASE
                WHEN event IN ('run_created', 'run_viewed', 'project_created', 'project_viewed') THEN 'Experiments'
                WHEN event IN ('artifact_created', 'artifact_used', 'artifact_viewed') THEN 'Artifacts'
                WHEN event IN ('model_registry_viewed') THEN 'Model Registry'
                WHEN event IN ('sweep_created', 'sweep_viewed') THEN 'Sweeps'
                WHEN event IN ('report_created', 'report_viewed') THEN 'Reports'
                WHEN event IN ('weave_table_created', 'weave_table_viewed') THEN 'Tables'
                WHEN event IN ('team_or_profile_viewed') THEN 'Collaboration'
                WHEN event IN ('weave_call_created', 'weave_model_created', 'weave_op_created') THEN 'Weave Tracing'
                WHEN event IN ('weave_feedback_created', 'weave_evaluation_created', 'weave_scorer_created') THEN 'Weave Evaluation'
                WHEN event LIKE 'weave_backend%' OR event IN ('weave_object_created', 'weave_file_created', 'weave_dataset_created') THEN 'Weave Data'
                ELSE 'Other'
            END AS product_area
        FROM {daily_usage}
        WHERE account_id = @account_id
            AND date_day >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
            AND event_count > 0
    )
    SELECT
        product_area,
        FORMAT_DATE('%Y-%m', date_day) AS month,
        SUM(event_count) AS event_count,
        COUNT(DISTINCT universal_user_id) AS unique_users
    FROM mapped
    WHERE product_area != 'Other'
    GROUP BY product_area, month
    ORDER BY product_area, month
    """


def power_users_query() -> str:
    """
    Top power users by event count with product area breakdown.

    Returns top 20 users with their most-used product areas.
    Joins dim_users to resolve local/server user identities (username, email)
    that are NULL in ext_daily_user_event_usage for server deployments.
    """
    daily_usage = _ref("ext_daily_user_event_usage")
    dim_users = _ref("dim_users")
    return f"""
    WITH activity AS (
        SELECT
            universal_user_id,
            username,
            email,
            SUM(event_count) AS total_events,
            MAX(date_day) AS last_activity,
            COUNT(DISTINCT DATE_TRUNC(date_day, WEEK)) AS active_weeks,
            ARRAY_AGG(DISTINCT
                CASE
                    WHEN event IN ('run_created', 'run_viewed', 'project_created', 'project_viewed') THEN 'Experiments'
                    WHEN event IN ('artifact_created', 'artifact_used', 'artifact_viewed') THEN 'Artifacts'
                    WHEN event IN ('model_registry_viewed') THEN 'Model Registry'
                    WHEN event IN ('sweep_created', 'sweep_viewed') THEN 'Sweeps'
                    WHEN event IN ('report_created', 'report_viewed') THEN 'Reports'
                    WHEN event IN ('weave_table_created', 'weave_table_viewed') THEN 'Tables'
                    WHEN event LIKE 'weave_%' THEN 'Weave'
                    ELSE NULL
                END
                IGNORE NULLS
                LIMIT 5
            ) AS product_areas
        FROM {daily_usage}
        WHERE account_id = @account_id
            AND date_day >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
            AND event_count > 0
        GROUP BY universal_user_id, username, email
        ORDER BY total_events DESC
        LIMIT 20
    )
    SELECT
        a.universal_user_id,
        COALESCE(a.username, du.local_username) AS username,
        COALESCE(a.email, du.local_user_email) AS email,
        a.total_events,
        a.last_activity,
        a.active_weeks,
        a.product_areas
    FROM activity a
    LEFT JOIN {dim_users} du
        ON a.universal_user_id = du.universal_user_id
        AND du.account_id = @account_id
    ORDER BY a.total_events DESC
    """


def support_tickets_query() -> str:
    """
    Support tickets from Zendesk (synced via dim_helpdesk_tickets).

    Joins through stg_salesforce_accounts to filter by @account_id.
    Excludes deleted tickets. Returns per-ticket rows for builder aggregation.

    Returns:
        SQL string with @account_id parameter placeholder
    """
    helpdesk = _ref("dim_helpdesk_tickets")
    salesforce = _ref("stg_salesforce_accounts")
    return f"""
    SELECT
        t.zendesk_ticket_id,
        t.ticket_subject,
        t.ticket_status,
        t.ticket_priority,
        t.ticket_created_at,
        t.ticket_created_date_day,
        t.ticket_last_updated_at,
        t.primary_ticket_concern,
        t.sa_ticket_type,
        t.channel,
        t.jira_id,
        t.jira_link,
        t.jira_status,
        t.escalated_to_jira,
        t.escalated_to_t2,
        t.ticket_satisfaction_score,
        t.submitter_name,
        t.submitter_email,
        t.assignee_name
    FROM {helpdesk} t
    JOIN {salesforce} s
        ON LOWER(t.account_name) = LOWER(s.name)
    WHERE s.account_id = @account_id
        AND t.ticket_status != 'deleted'
        AND t.ticket_created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 365 DAY)
    ORDER BY t.ticket_created_at DESC
    """


def account_health_query() -> str:
    """
    Account health and renewal data query.

    Adapted from BigQueryQueryFactory.account_data_query(). Joins
    stg_salesforce_accounts + dim_opportunities + renewal_predictions.
    Uses landing_development dataset for churn predictions.

    Returns:
        SQL string with @account_id parameter placeholder
    """
    salesforce_accounts = _ref("stg_salesforce_accounts")
    dim_opportunities = _ref("dim_opportunities")
    company_usage = _ref("agg_daily_company_usage")
    renewal_predictions = _ref("renewal_predictions", dataset="landing_development")
    return f"""
    WITH account AS (
        SELECT
            account_id,
            name AS account_name,
            cs_renewal_date AS renewal_date,
            renewal_arr__c AS arr,
            cs_tier,
            customer_health,
            subscription_plan,
            opportunity_deployment_types AS deployment_type,
            -- Entitlement fields for pipeline enrichment
            product_family_sold,
            weave_customer,
            current_weave_arr,
            weave_total_commitment__c AS weave_commitment_gb,
            contracted_cloud_seats__c AS contracted_cloud_seats,
            contracted_local_seats__c AS contracted_local_seats,
            total_contracted_seats__c AS total_contracted_seats,
            active_cloud_seats__c AS active_cloud_seats,
            active_local_seats__c AS active_local_seats,
            total_active_seats__c AS total_active_seats
        FROM {salesforce_accounts}
        WHERE account_id = @account_id
            AND type = 'Customer'
        LIMIT 1
    ),
    churn_latest AS (
        SELECT
            account_id,
            churn_probability,
            horizon
        FROM {renewal_predictions}
        WHERE account_id = @account_id
        QUALIFY ROW_NUMBER() OVER (PARTITION BY account_id, horizon ORDER BY inference_timestamp DESC) = 1
    ),
    churn AS (
        SELECT
            account_id,
            MAX(IF(horizon = '3mo horizon', churn_probability, NULL)) AS churn_probability_3mo,
            MAX(IF(horizon = '5mo horizon', churn_probability, NULL)) AS churn_probability_5mo
        FROM churn_latest
        GROUP BY 1
    )
    SELECT
        a.renewal_date,
        a.arr,
        a.cs_tier,
        a.customer_health,
        COALESCE(c.churn_probability_3mo, NULL) AS churn_probability_3mo,
        COALESCE(c.churn_probability_5mo, NULL) AS churn_probability_5mo,
        a.subscription_plan,
        a.deployment_type,
        a.product_family_sold,
        a.weave_customer,
        a.current_weave_arr,
        a.weave_commitment_gb,
        a.contracted_cloud_seats,
        a.contracted_local_seats,
        a.total_contracted_seats,
        a.active_cloud_seats,
        a.active_local_seats,
        a.total_active_seats
    FROM account a
    LEFT JOIN churn c ON a.account_id = c.account_id
    """


def sdk_versions_query() -> str:
    """
    SDK version distribution over time — cli_version and local_version per user.

    Returns monthly version distribution with user counts. Filters out null/empty
    versions and aggregates to the major.minor level for cleaner grouping.
    """
    daily_usage = _ref("ext_daily_user_event_usage")
    return f"""
    WITH raw_versions AS (
        SELECT
            universal_user_id,
            date_day,
            -- Treat 'N/A' and empty strings as NULL
            NULLIF(NULLIF(cli_version, 'N/A'), '') AS cli_ver,
            NULLIF(NULLIF(local_version, 'N/A'), '') AS local_ver
        FROM {daily_usage}
        WHERE account_id = @account_id
            AND date_day >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
            AND event_count > 0
    ),
    -- Prefer cli_version; for local_version, take the first CSV entry (can be comma-separated)
    resolved AS (
        SELECT
            universal_user_id,
            date_day,
            COALESCE(
                cli_ver,
                SPLIT(local_ver, ',')[SAFE_OFFSET(0)]
            ) AS sdk_version
        FROM raw_versions
    ),
    -- Aggregate to monthly per-user: take the MAX version seen that month
    monthly_user AS (
        SELECT
            universal_user_id,
            FORMAT_DATE('%Y-%m', date_day) AS month,
            MAX(sdk_version) AS sdk_version
        FROM resolved
        WHERE sdk_version IS NOT NULL
            AND REGEXP_CONTAINS(sdk_version, r'^\\d+\\.\\d+')
        GROUP BY universal_user_id, month
    )
    SELECT
        month,
        sdk_version,
        COUNT(DISTINCT universal_user_id) AS user_count
    FROM monthly_user
    GROUP BY month, sdk_version
    ORDER BY month, sdk_version
    """


def user_journey_query() -> str:
    """
    Per-user adoption stage data from dim_users first_*_at fields.

    Returns one row per user with timestamps for each adoption milestone.
    Used to build Sankey diagrams showing the adoption funnel.
    """
    dim_users = _ref("dim_users")
    return f"""
    SELECT
        universal_user_id,
        local_username,
        local_user_email,
        first_telemetry_at,
        first_run_at,
        first_sweep_at,
        first_table_created_at,
        first_weave_call_at,
        first_license_created_at
    FROM {dim_users}
    WHERE account_id = @account_id
    """


def engagement_decay_query() -> str:
    """
    Per-user weekly activity for engagement decay analysis.

    Returns weekly event counts per user over 12 months, with identity resolution
    for server deployments. Used to detect activity decline (cooling/cold users).
    """
    daily_usage = _ref("ext_daily_user_event_usage")
    dim_users = _ref("dim_users")
    return f"""
    WITH user_weekly AS (
        SELECT
            universal_user_id,
            username,
            email,
            DATE_TRUNC(date_day, WEEK(MONDAY)) AS week,
            SUM(event_count) AS events
        FROM {daily_usage}
        WHERE account_id = @account_id
            AND date_day >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
            AND event_count > 0
        GROUP BY universal_user_id, username, email, week
    ),
    -- Resolve identity for server deployments
    resolved AS (
        SELECT
            uw.universal_user_id,
            COALESCE(uw.username, du.local_username) AS username,
            COALESCE(uw.email, du.local_user_email) AS email,
            uw.week,
            uw.events
        FROM user_weekly uw
        LEFT JOIN {dim_users} du
            ON uw.universal_user_id = du.universal_user_id
            AND du.account_id = @account_id
    )
    SELECT
        universal_user_id,
        MAX(username) AS username,
        MAX(email) AS email,
        week,
        SUM(events) AS events
    FROM resolved
    GROUP BY universal_user_id, week
    ORDER BY universal_user_id, week
    """


def aggregate_weekly(
    df: pd.DataFrame,
    date_col: str = "date_day",
    value_cols: Optional[list] = None,
    method: str = "last",
) -> pd.DataFrame:
    """
    Aggregate daily data to weekly using pandas resample.

    Args:
        df: Input DataFrame with a date column
        date_col: Name of the date column
        value_cols: Columns to aggregate (if None, aggregates all numeric)
        method: Aggregation method -- 'last' (snapshot), 'mean' (average), 'sum' (cumulative)

    Returns:
        Weekly-aggregated DataFrame with date index reset to column
    """
    if df.empty:
        return pd.DataFrame()

    work = df.copy()

    # Ensure date column is datetime
    if date_col in work.columns:
        work[date_col] = pd.to_datetime(work[date_col])
    else:
        return pd.DataFrame()

    work = work.set_index(date_col)

    # Select value columns
    if value_cols:
        cols_present = [c for c in value_cols if c in work.columns]
        if not cols_present:
            return pd.DataFrame()
        work = work[cols_present]
    else:
        work = work.select_dtypes(include="number")

    # Resample to weekly with method dispatch
    resampled = work.resample("W")
    if method == "last":
        result = resampled.last()
    elif method == "mean":
        result = resampled.mean()
    elif method == "sum":
        result = resampled.sum()
    else:
        raise ValueError(f"Unknown aggregation method: {method}. Use 'last', 'mean', or 'sum'.")

    # Drop weeks with all NaN (no data in that week)
    result = result.dropna(how="all")

    # Reset index to get date back as a column
    result = result.reset_index()

    return result
