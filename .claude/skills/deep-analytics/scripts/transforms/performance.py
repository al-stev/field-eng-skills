"""Performance Deep Dive transform -- application performance intelligence from BQ tables.

Data model notes:
- fct_application_performance is a SNAPSHOT table (one row per team/entity, no date column).
  It provides aggregate performance scores, slowness user counts, and error totals.
- fct_onscreen_loader_latencies is a per-event table with date_measured + duration (ms).
  We alias duration -> latency_ms in the query for downstream consistency.
- agg_daily_team_members_slow_chart_loads is a daily per-user table with string flags
  (user_with_slow_charts IS NOT NULL = had slow charts). We count days in the query.
"""

from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from transforms.base import BaseTransform


class PerformanceTransform(BaseTransform):
    """
    Transforms performance query outputs into Performance Deep Dive PAGE_DATA.

    Input DataFrames:
        perf_df: from performance_query() -- snapshot performance index + slowness + errors per team
        latency_df: from latency_distribution_query() -- raw latency_ms values with component_id (may be empty)
        slow_users_df: from slow_chart_users_query() -- per-user slow chart day counts (may be empty)

    Output: PAGE_DATA with gauge scoring, latency histogram, component breakdown, error summary, slow users table.
    """

    TIER_THRESHOLDS = {"good": 80, "fair": 50}  # >= 80 = good, >= 50 = fair, else poor

    LATENCY_BINS = [
        (0, 1000, "0-1s"),
        (1000, 2000, "1-2s"),
        (2000, 5000, "2-5s"),
        (5000, 10000, "5-10s"),
        (10000, float("inf"), "10s+"),
    ]

    # Maps BQ column name -> display label for all slow_*_user_ct columns
    SLOWNESS_FEATURES = {
        "slow_charts_user_ct": "Slow Charts",
        "slow_project_search_user_ct": "Slow Project Search",
        "slow_artifact_creating_user_ct": "Slow Artifact Creating",
        "slow_adag_lineage_user_ct": "Slow ADAG Lineage",
        "slow_run_groups_query_user_ct": "Slow Run Groups Query",
        "slow_artifact_manifests_user_ct": "Slow Artifact Manifests",
        "slow_project_page_user_ct": "Slow Project Page",
        "slow_report_metadata_user_ct": "Slow Report Metadata",
        "slow_runs_query_user_ct": "Slow Runs Query",
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
                {"value": "--", "label": "Error Count"},
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

        # 1. Performance index (aggregated across all teams/entities)
        performance_index = self._compute_performance_index(perf_df)

        # 2. Slowness breakdown (summed across teams)
        slowness_breakdown = self._compute_slowness_breakdown(perf_df)

        # 3. Error metrics (summed across teams)
        error_metrics = self._compute_error_metrics(perf_df)

        # 4. Latency distribution (from separate latency table)
        latency_distribution = self._compute_latency_distribution(latency_df)

        # 5. Component latency breakdown
        component_latency = self._compute_component_latency(latency_df)

        # 6. Slow chart users
        slow_chart_users = self._compute_slow_chart_users(slow_users_df)

        # 7. Per-team breakdown (if multiple teams)
        team_breakdown = self._compute_team_breakdown(perf_df)

        # 8. Narrative
        narrative = self._build_narrative(
            customer_name, performance_index, slowness_breakdown,
            error_metrics, latency_distribution, slow_chart_users,
        )

        # 9. KPIs
        p95_display = (
            f"{int(round(latency_distribution['p95']))}ms"
            if latency_distribution["p95"] != "--"
            else "--"
        )
        kpis = [
            {"value": str(round(performance_index["score"], 1)), "label": "Performance Index"},
            {"value": str(int(error_metrics["error_count"])), "label": "Error Count"},
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
            "component_latency": component_latency,
            "slow_chart_users": slow_chart_users,
            "team_breakdown": team_breakdown,
            "narrative": narrative,
            "kpis": kpis,
            "data_source": "fct_application_performance (snapshot) + fct_onscreen_loader_latencies",
            "deployment_type": deployment_type,
        }

    def _compute_performance_index(self, perf_df: pd.DataFrame) -> dict:
        """Compute weighted-average performance index across all teams and tier classification.

        The table is a snapshot: one row per team/entity. We weight by total_active_users
        if available, otherwise use a simple mean.
        """
        if "total_active_users" in perf_df.columns:
            weights = perf_df["total_active_users"].fillna(0).astype(float)
            values = perf_df["application_performance_index"].fillna(0).astype(float)
            total_weight = weights.sum()
            if total_weight > 0:
                score = float((values * weights).sum() / total_weight)
            else:
                score = float(values.mean())
        else:
            score = float(perf_df["application_performance_index"].mean())

        if score >= self.TIER_THRESHOLDS["good"]:
            tier = "good"
        elif score >= self.TIER_THRESHOLDS["fair"]:
            tier = "fair"
        else:
            tier = "poor"

        # Performance category from BQ (if consistent across rows)
        categories = perf_df["performance_category"].dropna().unique().tolist() if "performance_category" in perf_df.columns else []
        category = categories[0] if len(categories) == 1 else (categories[0] if categories else tier.capitalize())

        # Component breakdown: sum each slow_*_user_ct, normalize against total_active_users
        total_active = int(perf_df["total_active_users"].sum()) if "total_active_users" in perf_df.columns else 1
        components = {}
        for col, label in self.SLOWNESS_FEATURES.items():
            if col in perf_df.columns:
                slow_count = int(perf_df[col].fillna(0).sum())
                # Normalize: 0 slow users = 100, all users slow = 0
                if total_active > 0:
                    component_score = max(0, min(100, 100 * (1 - slow_count / total_active)))
                else:
                    component_score = 100.0
                components[col] = round(component_score, 1)
            else:
                components[col] = 100.0

        return {
            "score": round(score, 1),
            "tier": tier,
            "category": category,
            "components": components,
            "total_active_users": int(perf_df["total_active_users"].sum()) if "total_active_users" in perf_df.columns else 0,
        }

    def _compute_slowness_breakdown(self, perf_df: pd.DataFrame) -> list[dict]:
        """Sum each slow_*_user_ct column across teams, compute percentages."""
        totals = {}
        for col, label in self.SLOWNESS_FEATURES.items():
            totals[label] = int(perf_df[col].fillna(0).sum()) if col in perf_df.columns else 0

        grand_total = sum(totals.values())
        breakdown = []
        for feature, count in totals.items():
            pct = round(count / grand_total * 100, 1) if grand_total > 0 else 0.0
            breakdown.append({"feature": feature, "count": count, "pct": pct})

        breakdown.sort(key=lambda x: x["count"], reverse=True)
        return breakdown

    def _compute_error_metrics(self, perf_df: pd.DataFrame) -> dict:
        """Compute error metrics from snapshot data (no trend since no time series)."""
        error_count = int(perf_df["error_count"].fillna(0).sum())
        users_facing_errors = int(perf_df["users_facing_errors_ct"].fillna(0).sum())
        total_active = int(perf_df["total_active_users"].fillna(0).sum()) if "total_active_users" in perf_df.columns else 0

        # Slow operations ratio (if available)
        slow_ops_ratio = None
        if "slow_operations_ratio" in perf_df.columns:
            vals = perf_df["slow_operations_ratio"].dropna()
            if not vals.empty:
                slow_ops_ratio = round(float(vals.mean()), 4)

        # Bad experience tickets
        bad_tickets = 0
        if "num_bad_experience_tickets" in perf_df.columns:
            bad_tickets = int(perf_df["num_bad_experience_tickets"].fillna(0).sum())

        return {
            "users_facing_errors": users_facing_errors,
            "error_count": error_count,
            "total_active_users": total_active,
            "error_rate_pct": round(users_facing_errors / max(total_active, 1) * 100, 1),
            "slow_operations_ratio": slow_ops_ratio,
            "bad_experience_tickets": bad_tickets,
        }

    def _compute_latency_distribution(self, latency_df: pd.DataFrame) -> dict:
        """Bin latency_ms values into 5 fixed ranges and compute percentiles."""
        bin_defs = self.LATENCY_BINS

        if latency_df.empty or "latency_ms" not in latency_df.columns:
            empty_bins = [
                {"label": label, "count": 0, "pct": 0.0}
                for _, _, label in bin_defs
            ]
            return {"bins": empty_bins, "p50": "--", "p95": "--", "p99": "--", "total_measurements": 0}

        latency_values = latency_df["latency_ms"].dropna().astype(float)
        total = len(latency_values)

        if total == 0:
            empty_bins = [
                {"label": label, "count": 0, "pct": 0.0}
                for _, _, label in bin_defs
            ]
            return {"bins": empty_bins, "p50": "--", "p95": "--", "p99": "--", "total_measurements": 0}

        # Bin using fixed ranges
        bins = []
        for low, high, label in bin_defs:
            if high == float("inf"):
                count = int((latency_values >= low).sum())
            else:
                count = int(((latency_values >= low) & (latency_values < high)).sum())
            pct = round(count / total * 100, 1)
            bins.append({"label": label, "count": count, "pct": pct})

        # Percentiles
        p50 = round(float(np.percentile(latency_values, 50)), 1)
        p95 = round(float(np.percentile(latency_values, 95)), 1)
        p99 = round(float(np.percentile(latency_values, 99)), 1)

        # Date range
        date_range = {}
        if "date_measured" in latency_df.columns:
            dates = pd.to_datetime(latency_df["date_measured"])
            date_range = {
                "earliest": dates.min().isoformat()[:10],
                "latest": dates.max().isoformat()[:10],
            }

        return {
            "bins": bins, "p50": p50, "p95": p95, "p99": p99,
            "total_measurements": total, "date_range": date_range,
        }

    def _compute_component_latency(self, latency_df: pd.DataFrame) -> list[dict]:
        """Per-component latency breakdown from fct_onscreen_loader_latencies."""
        if latency_df.empty or "component_id" not in latency_df.columns or "latency_ms" not in latency_df.columns:
            return []

        components = []
        for comp_id, group in latency_df.groupby("component_id"):
            vals = group["latency_ms"].dropna().astype(float)
            if len(vals) == 0:
                continue
            components.append({
                "component": str(comp_id),
                "count": len(vals),
                "p50": round(float(np.percentile(vals, 50)), 1),
                "p95": round(float(np.percentile(vals, 95)), 1),
                "max": round(float(vals.max()), 1),
            })

        components.sort(key=lambda c: c["count"], reverse=True)
        return components[:20]  # Top 20 components

    def _compute_slow_chart_users(self, slow_users_df: pd.DataFrame) -> list[dict]:
        """Convert slow users DataFrame to sorted list of dicts.

        Expected columns from query: username, team, total_days, slow_days, slow_pct, last_seen.
        """
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
            team = str(row.get("team", "unknown"))
            users.append({
                "username": username,
                "display_name": username,
                "team": team,
                "total_days": int(row.get("total_days", 0)),
                "slow_days": int(row.get("slow_days", 0)),
                "slow_pct": round(float(row.get("slow_pct", 0)), 1),
                "last_seen": last_seen,
            })

        users.sort(key=lambda u: u["slow_pct"], reverse=True)
        return users

    def _compute_team_breakdown(self, perf_df: pd.DataFrame) -> list[dict]:
        """Per-team performance breakdown (only meaningful if multiple teams)."""
        if len(perf_df) <= 1:
            return []

        teams = []
        for _, row in perf_df.iterrows():
            team_name = str(row.get("team_name", "unknown"))
            teams.append({
                "team": team_name,
                "score": round(float(row.get("application_performance_index", 0)), 1),
                "category": str(row.get("performance_category", "")),
                "active_users": int(row.get("total_active_users", 0)),
                "slow_users": int(row.get("slow_users", 0)),
                "slow_pct": round(float(row.get("slow_users_pct", 0)), 1),
                "error_count": int(row.get("error_count", 0)),
                "users_facing_errors": int(row.get("users_facing_errors_ct", 0)),
            })

        teams.sort(key=lambda t: t["score"])
        return teams

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
        category = perf_index.get("category", tier.capitalize())

        # Performance assessment
        if tier == "good":
            highlights.append(
                f"Application performance is healthy with a score of {score}/100 ({category})."
            )
        elif tier == "fair":
            highlights.append(
                f"Application performance is fair ({score}/100, {category}). Some areas need attention."
            )
        else:
            highlights.append(
                f"Application performance is degraded ({score}/100, {category}). Immediate investigation recommended."
            )

        # Active users context
        total_active = perf_index.get("total_active_users", 0)
        if total_active > 0:
            highlights.append(f"{total_active} total active users across all teams.")

        # Slowest feature
        if slowness:
            # Filter to features with non-zero counts
            nonzero = [s for s in slowness if s["count"] > 0]
            if nonzero:
                worst = nonzero[0]
                highlights.append(
                    f"Top slowness contributor: {worst['feature']} with {worst['count']} affected users "
                    f"({worst['pct']}% of total slow operations)."
                )
                if worst["pct"] > 40:
                    recommendations.append(
                        f"Investigate {worst['feature']} -- accounts for over 40% of all slow operations."
                    )
            else:
                highlights.append("No users experiencing slow operations -- all performance dimensions clean.")

        # Error assessment
        if errors["users_facing_errors"] > 0:
            highlights.append(
                f"{errors['users_facing_errors']} users facing errors "
                f"({errors['error_rate_pct']}% of active users), "
                f"{errors['error_count']} total errors."
            )
            if errors["error_rate_pct"] > 10:
                recommendations.append(
                    "High error rate detected. Review error logs for recurring failure patterns."
                )
        else:
            highlights.append("No users currently facing errors.")

        # Bad experience tickets
        if errors.get("bad_experience_tickets", 0) > 0:
            recommendations.append(
                f"{errors['bad_experience_tickets']} bad experience ticket(s) on record. "
                "Review ticket details for UX improvement opportunities."
            )

        # Latency
        if latency["p95"] != "--" and latency["p95"] > 5000:
            recommendations.append(
                f"P95 chart load latency is {latency['p95']}ms. Consider optimizing chart rendering."
            )

        # Slow users
        slow_with_issues = [u for u in slow_users if u["slow_pct"] > 0]
        if len(slow_with_issues) > 3:
            recommendations.append(
                f"{len(slow_with_issues)} users experiencing slow chart loads. "
                "Check if specific projects or chart configurations are causing performance issues."
            )

        if not recommendations:
            recommendations.append(
                "No immediate performance concerns. Continue monitoring for degradation signals."
            )

        executive_summary = (
            f"{customer} application performance index: {score}/100 ({category}). "
            f"{errors['error_count']} errors affecting "
            f"{errors['users_facing_errors']} users."
        )

        return {
            "executive_summary": executive_summary,
            "highlights": highlights[:5],
            "recommendations": recommendations[:4],
        }
