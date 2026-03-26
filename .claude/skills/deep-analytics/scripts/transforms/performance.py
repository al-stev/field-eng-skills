"""Performance Deep Dive transform -- application performance intelligence from BQ tables."""

from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from transforms.base import BaseTransform


class PerformanceTransform(BaseTransform):
    """
    Transforms performance query outputs into Performance Deep Dive PAGE_DATA.

    Input DataFrames:
        perf_df: from performance_query() -- daily performance index + slowness + errors
        latency_df: from latency_distribution_query() -- raw latency_ms values (may be empty)
        slow_users_df: from slow_chart_users_query() -- per-user slow chart loads (may be empty)

    Output: PAGE_DATA with gauge scoring, latency histogram, error trending, slow users table.
    """

    TIER_THRESHOLDS = {"good": 80, "fair": 50}  # >= 80 = good, >= 50 = fair, else poor

    LATENCY_BINS = [
        (0, 1000, "0-1s"),
        (1000, 2000, "1-2s"),
        (2000, 5000, "2-5s"),
        (5000, 10000, "5-10s"),
        (10000, float("inf"), "10s+"),
    ]

    SLOWNESS_FEATURES = {
        "slow_charts": "Slow Charts",
        "slow_project_search": "Slow Project Search",
        "slow_artifact_creating": "Slow Artifact Creating",
        "slow_run_sidebar": "Slow Run Sidebar",
        "slow_workspace_settings": "Slow Workspace Settings",
    }

    @classmethod
    def descoped_result(cls, reason: str) -> dict[str, Any]:
        """Return the descoped PAGE_DATA shape when data is insufficient or schema fails."""
        return {
            "available": False,
            "reason": reason,
            "page_type": "performance",
            "kpis": [
                {"value": "--", "label": "Performance Index"},
                {"value": "--", "label": "Error Count (30d)"},
                {"value": "--", "label": "P95 Chart Load"},
                {"value": "--", "label": "Slow Chart Users"},
            ],
            "narrative": {
                "executive_summary": f"Performance Deep Dive descoped: {reason}.",
                "highlights": [
                    "The performance data tables do not contain sufficient data for this account."
                ],
                "recommendations": [
                    "Re-run generation when performance data becomes available in BigQuery."
                ],
            },
        }

    def transform(self, **kwargs: Any) -> dict[str, Any]:
        perf_df: pd.DataFrame = kwargs.get("perf_df", pd.DataFrame())
        latency_df: pd.DataFrame = kwargs.get("latency_df", pd.DataFrame())
        slow_users_df: pd.DataFrame = kwargs.get("slow_users_df", pd.DataFrame())
        customer_name: str = kwargs.get("customer_name", "Unknown")
        deployment_type: str = kwargs.get("deployment_type", "Unknown")

        if perf_df.empty:
            return self.empty_result("performance_data_unavailable")

        perf_df = perf_df.copy()
        perf_df["date_day"] = pd.to_datetime(perf_df["date_day"])
        perf_df = perf_df.sort_values("date_day")

        # 1. Performance index
        performance_index = self._compute_performance_index(perf_df)

        # 2. Slowness breakdown
        slowness_breakdown = self._compute_slowness_breakdown(perf_df)

        # 3. Error metrics
        error_metrics = self._compute_error_metrics(perf_df)

        # 4. Latency distribution
        latency_distribution = self._compute_latency_distribution(latency_df)

        # 5. Slow chart users
        slow_chart_users = self._compute_slow_chart_users(slow_users_df)

        # 6. Narrative
        narrative = self._build_narrative(
            customer_name, performance_index, slowness_breakdown,
            error_metrics, latency_distribution, slow_chart_users,
        )

        # 7. KPIs
        p95_display = (
            f"{int(round(latency_distribution['p95']))}ms"
            if latency_distribution["p95"] != "--"
            else "--"
        )
        kpis = [
            {"value": str(round(performance_index["score"], 1)), "label": "Performance Index"},
            {"value": str(int(error_metrics["error_count_30d"])), "label": "Error Count (30d)"},
            {"value": p95_display, "label": "P95 Chart Load"},
            {"value": str(len(slow_chart_users)), "label": "Slow Chart Users"},
        ]

        return {
            "available": True,
            "reason": None,
            "page_type": "performance",
            "customer": customer_name,
            "generated": date.today().isoformat(),
            "performance_index": performance_index,
            "slowness_breakdown": slowness_breakdown,
            "error_metrics": error_metrics,
            "latency_distribution": latency_distribution,
            "slow_chart_users": slow_chart_users,
            "narrative": narrative,
            "kpis": kpis,
            "data_source": "fct_application_performance + fct_onscreen_loader_latencies",
            "deployment_type": deployment_type,
        }

    def _compute_performance_index(self, perf_df: pd.DataFrame) -> dict:
        """Compute average performance index and tier classification."""
        score = float(perf_df["application_performance_index"].mean())

        if score >= self.TIER_THRESHOLDS["good"]:
            tier = "good"
        elif score >= self.TIER_THRESHOLDS["fair"]:
            tier = "fair"
        else:
            tier = "poor"

        # Component breakdown: average the last 7 days of each slow_* column
        # and normalize to 0-100 scale (lower slow counts = higher component score)
        last_7d = perf_df.tail(7)
        components = {}
        for col, label in self.SLOWNESS_FEATURES.items():
            avg_slow = float(last_7d[col].mean()) if col in last_7d.columns else 0
            # Normalize: 0 slow = 100 score, 100+ slow = 0 score
            component_score = max(0, min(100, 100 - avg_slow))
            components[col] = round(component_score, 1)

        return {
            "score": round(score, 1),
            "tier": tier,
            "components": components,
        }

    def _compute_slowness_breakdown(self, perf_df: pd.DataFrame) -> list[dict]:
        """Sum each slow_* column and compute percentages, sorted by count descending."""
        totals = {}
        for col, label in self.SLOWNESS_FEATURES.items():
            totals[label] = int(perf_df[col].sum()) if col in perf_df.columns else 0

        grand_total = sum(totals.values())
        breakdown = []
        for feature, count in totals.items():
            pct = round(count / grand_total * 100, 1) if grand_total > 0 else 0.0
            breakdown.append({"feature": feature, "count": count, "pct": pct})

        breakdown.sort(key=lambda x: x["count"], reverse=True)
        return breakdown

    def _compute_error_metrics(self, perf_df: pd.DataFrame) -> dict:
        """Compute error metrics with trend (last 15d vs prior 15d)."""
        latest = perf_df.iloc[-1]
        users_facing_errors = int(latest["users_facing_errors_ct"])

        # 30-day error count
        last_30d = perf_df.tail(30)
        error_count_30d = int(last_30d["error_count"].sum())

        # Trend: last 15 days vs prior 15 days
        if len(perf_df) >= 30:
            recent_15d = perf_df.tail(15)["error_count"].sum()
            prior_15d = perf_df.iloc[-30:-15]["error_count"].sum()
        else:
            half = len(perf_df) // 2
            if half > 0:
                recent_15d = perf_df.tail(half)["error_count"].sum()
                prior_15d = perf_df.head(half)["error_count"].sum()
            else:
                recent_15d = error_count_30d
                prior_15d = error_count_30d

        error_trend = round(
            ((recent_15d - prior_15d) / max(prior_15d, 1)) * 100, 1
        )

        return {
            "users_facing_errors": users_facing_errors,
            "error_count": int(latest["error_count"]),
            "error_count_30d": error_count_30d,
            "error_trend": error_trend,
            "trend_period": "30d",
        }

    def _compute_latency_distribution(self, latency_df: pd.DataFrame) -> dict:
        """Bin latency_ms values into 5 fixed ranges and compute percentiles."""
        bin_defs = self.LATENCY_BINS

        if latency_df.empty or "latency_ms" not in latency_df.columns:
            empty_bins = [
                {"label": label, "count": 0, "pct": 0.0}
                for _, _, label in bin_defs
            ]
            return {"bins": empty_bins, "p50": "--", "p95": "--", "p99": "--"}

        latency_values = latency_df["latency_ms"].dropna().astype(float)
        total = len(latency_values)

        if total == 0:
            empty_bins = [
                {"label": label, "count": 0, "pct": 0.0}
                for _, _, label in bin_defs
            ]
            return {"bins": empty_bins, "p50": "--", "p95": "--", "p99": "--"}

        # Bin using fixed ranges
        bins = []
        for low, high, label in bin_defs:
            if high == float("inf"):
                count = int(((latency_values >= low)).sum())
            else:
                count = int(((latency_values >= low) & (latency_values < high)).sum())
            pct = round(count / total * 100, 1)
            bins.append({"label": label, "count": count, "pct": pct})

        # Percentiles
        p50 = round(float(np.percentile(latency_values, 50)), 1)
        p95 = round(float(np.percentile(latency_values, 95)), 1)
        p99 = round(float(np.percentile(latency_values, 99)), 1)

        return {"bins": bins, "p50": p50, "p95": p95, "p99": p99}

    def _compute_slow_chart_users(self, slow_users_df: pd.DataFrame) -> list[dict]:
        """Convert slow users DataFrame to sorted list of dicts."""
        if slow_users_df.empty:
            return []

        users = []
        for _, row in slow_users_df.iterrows():
            last_seen = row.get("last_seen", "")
            if hasattr(last_seen, "isoformat"):
                last_seen = last_seen.isoformat()
            elif hasattr(last_seen, "strftime"):
                last_seen = last_seen.strftime("%Y-%m-%d")
            else:
                last_seen = str(last_seen)

            username = str(row.get("username", "unknown"))
            users.append({
                "username": username,
                "display_name": username,
                "slow_loads": int(row.get("slow_loads", 0)),
                "total_loads": int(row.get("total_loads", 0)),
                "slow_pct": round(float(row.get("slow_pct", 0)), 1),
                "last_seen": last_seen,
            })

        users.sort(key=lambda u: u["slow_pct"], reverse=True)
        return users

    def _build_narrative(
        self,
        customer: str,
        perf_index: dict,
        slowness: list,
        errors: dict,
        latency: dict,
        slow_users: list,
    ) -> dict:
        """Build structured narrative from performance data."""
        highlights = []
        recommendations = []

        score = perf_index["score"]
        tier = perf_index["tier"]

        # Performance assessment
        if tier == "good":
            highlights.append(
                f"Application performance is healthy with a score of {score}/100."
            )
        elif tier == "fair":
            highlights.append(
                f"Application performance is fair ({score}/100). Some areas need attention."
            )
        else:
            highlights.append(
                f"Application performance is degraded ({score}/100). Immediate investigation recommended."
            )

        # Slowest feature
        if slowness:
            worst = slowness[0]
            highlights.append(
                f"Top slowness contributor: {worst['feature']} with {worst['count']} slow loads "
                f"({worst['pct']}% of total)."
            )
            if worst["pct"] > 40:
                recommendations.append(
                    f"Investigate {worst['feature']} -- accounts for over 40% of all slow loads."
                )

        # Error trend
        if errors["error_trend"] > 20:
            highlights.append(
                f"Error count is increasing: {errors['error_trend']}% change over 30 days."
            )
            recommendations.append(
                "Rising error count detected. Review error logs for new failure patterns."
            )
        elif errors["error_trend"] < -20:
            highlights.append(
                f"Error count is improving: {errors['error_trend']}% change over 30 days."
            )

        # Latency
        if latency["p95"] != "--" and latency["p95"] > 5000:
            recommendations.append(
                f"P95 chart load latency is {latency['p95']}ms. Consider optimizing chart rendering."
            )

        # Slow users
        if len(slow_users) > 5:
            recommendations.append(
                f"{len(slow_users)} users experiencing slow chart loads. "
                "Check if specific projects or chart configurations are causing performance issues."
            )

        if not recommendations:
            recommendations.append(
                "No immediate performance concerns. Continue monitoring for degradation signals."
            )

        executive_summary = (
            f"{customer} application performance index: {score}/100 ({tier}). "
            f"{errors['error_count_30d']} errors in the last 30 days affecting "
            f"{errors['users_facing_errors']} users."
        )

        return {
            "executive_summary": executive_summary,
            "highlights": highlights[:5],
            "recommendations": recommendations[:4],
        }
