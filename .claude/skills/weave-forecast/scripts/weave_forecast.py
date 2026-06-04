#!/usr/bin/env python3
"""
Weave ingestion forecast for a customer.

Pulls daily Weave ingestion from BigQuery, projects 365 days forward using
windowed mean-rate scenarios (180d / 90d / 30d), computes contracted-limit
crossing dates, and renders a self-contained HTML page using the wandb-themed
ECharts template.

Why mean rate, not linear fit?
    Daily Weave ingestion is noisy and spiky. Least-squares linear regression
    produces a slope-and-intercept pair whose intercept term amplifies wildly
    when projected forward — small noise yields huge cumulative differences.
    Windowed mean rate ("at your last 30-day average of X GB/day, you hit the
    limit on Y") is more interpretable, harder to misuse in a customer
    conversation, and doesn't pretend to be more precise than the signal
    supports.

Usage (uses the bigquery skill's venv for pandas / google-cloud-bigquery deps):
    uv run --project .claude/skills/bigquery \\
        python .claude/skills/weave-forecast/scripts/weave_forecast.py --customer GSK

Cost: ~90 GB processed per refresh (one daily-grain scan of fct_weave_project_storage,
plus a small monthly aggregation and a tiny dim_opportunities lookup).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# Import the BQ data layer from the bigquery skill — bq_client + queries.py
# live there because they're shared infrastructure (used by usage-report,
# customer-snapshot, deep-analytics). Duplicating them here would invite drift.
_BIGQUERY_SCRIPTS = Path(__file__).resolve().parent.parent.parent / "bigquery" / "scripts"
sys.path.insert(0, str(_BIGQUERY_SCRIPTS))
from bq_client import get_client, get_sfdc_account_id, run_query  # noqa: E402
from queries import (  # noqa: E402
    account_health_query,
    weave_daily_by_project_query,
    weave_limit_query,
    weave_monthly_query,
)


SPIKE_THRESHOLD_GB = 5.0   # project must have contributed at least this much total
SPIKE_STALENESS_DAYS = 7   # project must have been silent at least this long


SCENARIOS = [
    {
        "key": "conservative",
        "label": "Conservative (180-day avg rate)",
        "window_days": 180,
        "window_description": "Average daily ingestion over the last 6 months. Smooths recent spikes.",
    },
    {
        "key": "recent",
        "label": "Recent (90-day avg rate)",
        "window_days": 90,
        "window_description": "Average daily ingestion over the last 90 days. Reflects current trajectory.",
    },
    {
        "key": "aggressive",
        "label": "Aggressive (30-day avg rate)",
        "window_days": 30,
        "window_description": "Average daily ingestion over the last 30 days only. Bullish — assumes recent rate sustains.",
    },
]


def windowed_mean_rate(daily: pd.DataFrame, window_days: int, today: date) -> float:
    """Mean GB/day over the last window_days. Returns 0 if insufficient data."""
    cutoff = pd.Timestamp(today - timedelta(days=window_days))
    sub = daily[daily["day"] >= cutoff]
    if sub.empty:
        return 0.0
    # Divide by window size, not row count — days with zero ingestion may be absent
    return float(sub["day_gb"].sum() / window_days)


def project_constant_rate(rate_gb_per_day: float, horizon_days: int, today: date) -> list[dict]:
    """Project a constant daily rate forward for horizon_days starting tomorrow."""
    future_days = pd.date_range(
        pd.Timestamp(today) + pd.Timedelta(days=1), periods=horizon_days, freq="D"
    )
    return [
        {"day": d.strftime("%Y-%m-%d"), "gb": round(float(rate_gb_per_day), 4)}
        for d in future_days
    ]


def crossing_date(
    starting_cum: float, rate_gb_per_day: float, limit_gb: float | None, today: date
) -> str | None:
    """Date when starting_cum + rate * days_forward first reaches limit_gb.

    Returns None if rate <= 0 (never crosses) or if limit is unknown.
    """
    if limit_gb is None or rate_gb_per_day <= 0:
        return None
    if starting_cum >= limit_gb:
        return today.strftime("%Y-%m-%d")
    days_to_cross = int(np.ceil((limit_gb - starting_cum) / rate_gb_per_day))
    return (today + timedelta(days=days_to_cross)).strftime("%Y-%m-%d")


def horizon_cumulative(starting_cum: float, rate_gb_per_day: float, days: int) -> float:
    """Cumulative ingestion (starting_cum + rate*days) after `days` days."""
    return round(starting_cum + rate_gb_per_day * days, 2)


def cumulative_since(daily: pd.DataFrame, since: date | None) -> float:
    """Sum of day_gb in daily where day >= since. If since is None, returns total."""
    if since is None:
        return float(daily["day_gb"].sum())
    sub = daily[daily["day"] >= pd.Timestamp(since)]
    return float(sub["day_gb"].sum())


def parse_date(val) -> date | None:
    """Best-effort parse of a BigQuery date/timestamp into a Python date."""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    try:
        return pd.to_datetime(val).date()
    except Exception:
        return None


def detect_stale_spike_projects(
    daily_by_project_df: pd.DataFrame,
    today: date,
    threshold_gb: float = SPIKE_THRESHOLD_GB,
    staleness_days: int = SPIKE_STALENESS_DAYS,
) -> list[dict]:
    """Identify projects that contributed a meaningful burst and have since
    gone silent. These are the projects a SE would want to be able to
    exclude when projecting forward.

    A project is a 'stale spike' if:
      - it has contributed at least `threshold_gb` total over the window AND
      - it hasn't been active in the last `staleness_days` days.

    Returns a list of {project_id, total_gb, last_active, days_silent}.
    """
    if daily_by_project_df.empty:
        return []
    df = daily_by_project_df.copy()
    df["day"] = pd.to_datetime(df["day"]).dt.date
    agg = df.groupby("project_id").agg(
        total_gb=("day_gb", "sum"),
        last_active=("day", "max"),
        active_days=("day", "nunique"),
    )
    out = []
    for project_id, row in agg.iterrows():
        days_silent = (today - row["last_active"]).days
        if row["total_gb"] >= threshold_gb and days_silent >= staleness_days:
            out.append(
                {
                    "project_id": int(project_id),
                    "total_gb": round(float(row["total_gb"]), 2),
                    "last_active": row["last_active"].strftime("%Y-%m-%d"),
                    "days_silent": int(days_silent),
                    "active_days": int(row["active_days"]),
                }
            )
    # Sort biggest impact first
    out.sort(key=lambda r: -r["total_gb"])
    return out


def daily_series_from_by_project(
    daily_by_project_df: pd.DataFrame, exclude_project_ids: list[int] = None
) -> pd.DataFrame:
    """Roll up daily-by-project into per-day totals, optionally excluding
    given project_ids. Returns a DataFrame with [day, day_gb]."""
    df = daily_by_project_df.copy()
    df["day"] = pd.to_datetime(df["day"])
    if exclude_project_ids:
        df = df[~df["project_id"].isin(exclude_project_ids)]
    out = df.groupby("day", as_index=False)["day_gb"].sum()
    return out.sort_values("day").reset_index(drop=True)


def compute_scenarios_for_series(
    daily_df: pd.DataFrame,
    starting_cum: float,
    limit_gb: float | None,
    horizon_days: int,
    today: date,
) -> list[dict]:
    """Run the three windowed-mean-rate scenarios on a given daily series.
    Returns a list of scenario dicts matching the SCENARIOS spec."""
    out = []
    for spec in SCENARIOS:
        rate = windowed_mean_rate(daily_df, spec["window_days"], today)
        proj = project_constant_rate(rate, horizon_days, today)
        cross = crossing_date(starting_cum, rate, limit_gb, today)
        out.append(
            {
                **spec,
                "rate_gb_per_day": round(rate, 4),
                "slope_gb_per_day": round(rate, 4),
                "monthly_rate_gb": round(rate * 30.4375, 2),
                "projected_daily": proj,
                "hits_limit_at": cross,
                "total_at_3mo_gb": horizon_cumulative(starting_cum, rate, 90),
                "total_at_6mo_gb": horizon_cumulative(starting_cum, rate, 180),
                "total_at_9mo_gb": horizon_cumulative(starting_cum, rate, 270),
                "total_at_12mo_gb": horizon_cumulative(starting_cum, rate, 365),
            }
        )
    return out


def build_payload(
    customer: str,
    account_id: str,
    daily_by_project_df: pd.DataFrame,
    monthly_df: pd.DataFrame,
    limit_df: pd.DataFrame,
    health_df: pd.DataFrame,
    horizon_days: int,
) -> dict:
    today = date.today()

    # Roll up daily totals (with spikes) from the by-project frame
    daily_df = daily_series_from_by_project(daily_by_project_df)
    daily_df["day_gb"] = daily_df["day_gb"].fillna(0.0)

    # Detect spike projects and build the "no spike" daily series
    spike_projects = detect_stale_spike_projects(daily_by_project_df, today)
    spike_ids = [s["project_id"] for s in spike_projects]
    daily_no_spike_df = (
        daily_series_from_by_project(daily_by_project_df, exclude_project_ids=spike_ids)
        if spike_ids
        else daily_df.copy()
    )
    daily_no_spike_df["day_gb"] = daily_no_spike_df["day_gb"].fillna(0.0)

    # Contract limit + dates
    limit_gb = None
    contract_start = None
    contract_end = None
    if not limit_df.empty:
        row = limit_df.iloc[0]
        if pd.notna(row.get("weave_data_ingestion_limit_gb")):
            limit_gb = float(row["weave_data_ingestion_limit_gb"])
        contract_start = parse_date(row.get("contract_start_date"))
        contract_end = parse_date(row.get("contract_end_date"))

    # Account health (renewal, arr, subscription, deployment)
    renewal_date_str = None
    arr = None
    cs_tier = None
    subscription = None
    deployment_type = None
    if not health_df.empty:
        row = health_df.iloc[0]
        ren = parse_date(row.get("renewal_date"))
        renewal_date_str = ren.strftime("%Y-%m-%d") if ren else None
        if pd.notna(row.get("arr")):
            arr = float(row["arr"])
        cs_tier = row.get("cs_tier") if pd.notna(row.get("cs_tier")) else None
        subscription = row.get("subscription_plan") if pd.notna(row.get("subscription_plan")) else None
        deployment_type = row.get("deployment_type") if pd.notna(row.get("deployment_type")) else None

    contract = {
        "limit_gb": limit_gb,
        "contract_start_date": contract_start.strftime("%Y-%m-%d") if contract_start else None,
        "contract_end_date": contract_end.strftime("%Y-%m-%d") if contract_end else None,
        "renewal_date": renewal_date_str,
        "arr": arr,
        "cs_tier": cs_tier,
        "subscription": subscription,
    }

    # Cumulative ingestion since the start of the current contract period (if
    # known). Computed for both series — with and without stale spike projects.
    cumulative_since_contract = cumulative_since(daily_df, contract_start)
    cumulative_since_contract_no_spike = cumulative_since(daily_no_spike_df, contract_start)
    history_covers_contract = (
        contract_start is not None
        and len(daily_df)
        and daily_df["day"].min().date() <= contract_start
    )

    # Last-12-month total (rolling) — independent of contract anchoring
    last_12mo_total = float(
        sum(r.get("total_storage_gb") or 0.0 for _, r in monthly_df.iterrows())
    )

    # Last 30 days — both series
    cutoff_30d = pd.Timestamp(today - timedelta(days=30))
    last_30d = daily_df[daily_df["day"] >= cutoff_30d]
    last_30d_total = float(last_30d["day_gb"].sum())
    last_30d_no_spike = daily_no_spike_df[daily_no_spike_df["day"] >= cutoff_30d]
    last_30d_total_no_spike = float(last_30d_no_spike["day_gb"].sum())

    last_30d_rate = last_30d_total / 30.0
    last_30d_rate_no_spike = last_30d_total_no_spike / 30.0
    utilization_pct = (last_12mo_total / limit_gb * 100.0) if limit_gb else None
    days_until_renewal = (
        (parse_date(renewal_date_str) - today).days if renewal_date_str else None
    )

    current_state = {
        "last_12mo_gb": round(last_12mo_total, 2),
        "utilization_pct": round(utilization_pct, 1) if utilization_pct is not None else None,
        "last_30d_gb": round(last_30d_total, 2),
        "last_30d_rate_gb_per_day": round(last_30d_rate, 3),
        "annualized_30d_rate_gb": round(last_30d_rate * 365.0, 1),
        "cumulative_since_contract_start": round(cumulative_since_contract, 2),
        # No-spike equivalents
        "last_30d_gb_no_spike": round(last_30d_total_no_spike, 2),
        "last_30d_rate_gb_per_day_no_spike": round(last_30d_rate_no_spike, 3),
        "annualized_30d_rate_gb_no_spike": round(last_30d_rate_no_spike * 365.0, 1),
        "cumulative_since_contract_start_no_spike": round(cumulative_since_contract_no_spike, 2),
        "utilization_pct_no_spike": (
            round(cumulative_since_contract_no_spike / limit_gb * 100.0, 1)
            if (limit_gb and contract_start)
            else None
        ),
        "days_until_renewal": days_until_renewal,
        "history_covers_contract": bool(history_covers_contract),
    }

    # Historical daily series for the chart — both views
    historical_daily = [
        {"day": r["day"].strftime("%Y-%m-%d"), "gb": round(float(r["day_gb"]), 4)}
        for _, r in daily_df.iterrows()
    ]
    historical_daily_no_spike = [
        {"day": r["day"].strftime("%Y-%m-%d"), "gb": round(float(r["day_gb"]), 4)}
        for _, r in daily_no_spike_df.iterrows()
    ]

    # Historical monthly series (just the with-spike total — monthly granularity
    # makes spike detection less meaningful and the de-spiked view is the
    # daily / scenario story)
    historical_monthly = []
    for _, row in monthly_df.iterrows():
        mo = row.get("created_date")
        if pd.isna(mo):
            continue
        historical_monthly.append(
            {
                "month": pd.to_datetime(mo).strftime("%Y-%m"),
                "gb": round(float(row.get("total_storage_gb") or 0.0), 2),
                "users": int(row["unique_users"]) if pd.notna(row.get("unique_users")) else 0,
            }
        )

    # Scenarios — run twice: once on the full daily series, once on the
    # spike-stripped series. Each anchors to its own cumulative baseline.
    starting_cum = (
        cumulative_since_contract if contract_start is not None else last_12mo_total
    )
    starting_cum_no_spike = (
        cumulative_since_contract_no_spike
        if contract_start is not None
        else float(daily_no_spike_df["day_gb"].sum())
    )
    scenarios_with_spike = compute_scenarios_for_series(
        daily_df, starting_cum, limit_gb, horizon_days, today
    )
    scenarios_no_spike = compute_scenarios_for_series(
        daily_no_spike_df, starting_cum_no_spike, limit_gb, horizon_days, today
    )

    return {
        "customer": customer,
        "account_id": account_id,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "deployment_type": deployment_type,
        "contract": contract,
        "current_state": current_state,
        "starting_cumulative_gb": round(starting_cum, 2),
        "starting_cumulative_gb_no_spike": round(starting_cum_no_spike, 2),
        "spike_analysis": {
            "enabled": len(spike_projects) > 0,
            "projects": spike_projects,
            "threshold_gb": SPIKE_THRESHOLD_GB,
            "staleness_days": SPIKE_STALENESS_DAYS,
            "total_excluded_gb": round(
                sum(p["total_gb"] for p in spike_projects), 2
            ),
        },
        "historical": {
            "daily": historical_daily,
            "daily_no_spike": historical_daily_no_spike,
            "monthly": historical_monthly,
        },
        "scenarios": scenarios_with_spike,
        "scenarios_no_spike": scenarios_no_spike,
    }


def render_html(template_path: Path, payload: dict) -> str:
    template = template_path.read_text()
    placeholder = "/*__FORECAST_DATA__*/{}"
    if placeholder not in template:
        raise RuntimeError(f"Template missing placeholder: {placeholder}")
    return template.replace(placeholder, json.dumps(payload, default=str))


def main():
    ap = argparse.ArgumentParser(description="Generate a Weave ingestion forecast HTML page.")
    ap.add_argument("--customer", required=True)
    ap.add_argument("--days", type=int, default=180, help="Daily-history lookback in days (default: 180)")
    ap.add_argument("--horizon-days", type=int, default=365, help="Forecast horizon (default: 365)")
    ap.add_argument("--output", help="Output HTML path (default: customers/<name>/weave/<date>-weave-forecast.html)")
    ap.add_argument("--open", action="store_true", help="Open the result in the default browser")
    args = ap.parse_args()

    account_id = get_sfdc_account_id(args.customer)
    print(f"[forecast] customer={args.customer} account_id={account_id}", file=sys.stderr)

    client = get_client()

    print("[forecast] pulling daily ingestion (by project)…", file=sys.stderr)
    daily_by_project_df = run_query(
        client, weave_daily_by_project_query(args.days), account_id=account_id
    )
    if daily_by_project_df.empty:
        print(f"[forecast] no Weave data for {args.customer}", file=sys.stderr)
        sys.exit(2)

    print("[forecast] pulling monthly history (cheap, no JOIN)…", file=sys.stderr)
    monthly_df = run_query(client, weave_monthly_query(12), account_id=account_id)

    print("[forecast] pulling contract limit + dates…", file=sys.stderr)
    limit_df = run_query(client, weave_limit_query(), account_id=account_id)

    print("[forecast] pulling account health…", file=sys.stderr)
    health_df = run_query(client, account_health_query(), account_id=account_id)

    payload = build_payload(
        args.customer,
        account_id,
        daily_by_project_df,
        monthly_df,
        limit_df,
        health_df,
        args.horizon_days,
    )

    template_path = Path(__file__).parent.parent / "templates" / "weave-forecast.html"
    html = render_html(template_path, payload)

    out_path = (
        Path(args.output)
        if args.output
        else Path(
            f"customers/{args.customer.lower().replace(' ', '-')}/weave/{date.today().isoformat()}-weave-forecast.html"
        )
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html)
    print(f"[forecast] wrote {out_path}", file=sys.stderr)
    print(out_path)

    if args.open:
        import webbrowser
        webbrowser.open(f"file://{out_path.resolve()}")


if __name__ == "__main__":
    main()
