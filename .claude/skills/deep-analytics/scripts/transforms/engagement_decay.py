"""Engagement Decay transform — per-user activity decline detection and ranking."""

from datetime import date, timedelta
from typing import Any

import pandas as pd

from transforms.base import BaseTransform


class EngagementDecayTransform(BaseTransform):
    """
    Transforms engagement_decay_query() output into Engagement Decay PAGE_DATA.

    Input: DataFrame with columns [universal_user_id, username, email, week, events]
    Output: PAGE_DATA with per-user decay classification, sparklines, and ranked table.
    """

    # Status thresholds based on recent-vs-peak ratio and weeks since last activity
    STATUS_THRESHOLDS = {
        "hot": {"min_ratio": 0.6, "max_inactive_weeks": 2},
        "warm": {"min_ratio": 0.3, "max_inactive_weeks": 4},
        "cooling": {"min_ratio": 0.1, "max_inactive_weeks": 8},
        # anything else = "cold"
    }

    def transform(self, engagement: pd.DataFrame, **kwargs: Any) -> dict[str, Any]:
        if engagement.empty:
            return self.empty_result("no_data")

        customer_name = kwargs.get("customer_name", "Unknown")
        contracted_seats = kwargs.get("contracted_seats")

        engagement = engagement.copy()
        engagement["week"] = pd.to_datetime(engagement["week"])

        # Build complete week range
        all_weeks = sorted(engagement["week"].unique())
        week_labels = [w.strftime("%Y-%m-%d") for w in all_weeks]
        now = pd.Timestamp.now().normalize()

        # Process per-user
        users = []
        for uid, user_df in engagement.groupby("universal_user_id"):
            user_df = user_df.sort_values("week")

            # Resolve username: prefer real username, then email, then ID fallback
            username = user_df["username"].dropna().iloc[-1] if not user_df["username"].dropna().empty else None
            email = user_df["email"].dropna().iloc[-1] if not user_df["email"].dropna().empty else None
            resolved = True
            if not username or username == "unknown":
                if email and email != "unknown" and "@" in str(email):
                    username = str(email).split("@")[0]
                else:
                    username = f"user-{str(uid)[:8]}" if uid else "unknown"
                    resolved = False

            # Build complete weekly series (fill missing weeks with 0)
            week_map = dict(zip(user_df["week"], user_df["events"]))
            weekly_events = [int(week_map.get(w, 0)) for w in all_weeks]

            total_events = sum(weekly_events)
            if total_events == 0:
                continue

            # Peak activity (best 4-week rolling average)
            if len(weekly_events) >= 4:
                rolling = [
                    sum(weekly_events[i:i+4]) / 4
                    for i in range(len(weekly_events) - 3)
                ]
                peak_avg = max(rolling) if rolling else 0
            else:
                peak_avg = sum(weekly_events) / max(len(weekly_events), 1)

            # Recent activity (last 4 weeks)
            recent_4w = weekly_events[-4:] if len(weekly_events) >= 4 else weekly_events
            recent_avg = sum(recent_4w) / len(recent_4w)

            # Weeks since last activity
            last_active_idx = None
            for i in range(len(weekly_events) - 1, -1, -1):
                if weekly_events[i] > 0:
                    last_active_idx = i
                    break
            if last_active_idx is not None:
                weeks_inactive = len(weekly_events) - 1 - last_active_idx
                last_active_week = week_labels[last_active_idx]
            else:
                weeks_inactive = len(weekly_events)
                last_active_week = None

            # Activity ratio (recent vs peak)
            ratio = recent_avg / peak_avg if peak_avg > 0 else 0

            # Classify status
            status = self._classify_status(ratio, weeks_inactive)

            # Trend: compare last 4 weeks to prior 4 weeks
            if len(weekly_events) >= 8:
                prior_4w = weekly_events[-8:-4]
                prior_avg = sum(prior_4w) / len(prior_4w)
                if prior_avg > 0:
                    trend_pct = round((recent_avg - prior_avg) / prior_avg * 100, 1)
                elif recent_avg > 0:
                    trend_pct = 100.0
                else:
                    trend_pct = 0.0
            else:
                trend_pct = 0.0

            users.append({
                "username": username,
                "email": email or "",
                "resolved": resolved,
                "status": status,
                "total_events": total_events,
                "peak_weekly_avg": round(peak_avg, 1),
                "recent_weekly_avg": round(recent_avg, 1),
                "ratio": round(ratio, 2),
                "trend_pct": trend_pct,
                "weeks_inactive": weeks_inactive,
                "last_active": last_active_week,
                "sparkline": weekly_events,
            })

        if not users:
            return self.empty_result("no_data")

        # Sort: hot first so SE sees full status spectrum, then by activity level
        # Unresolved names pushed to bottom within each status group
        status_order = {"hot": 0, "warm": 1, "cooling": 2, "cold": 3}
        users.sort(key=lambda u: (status_order.get(u["status"], 4), 0 if u["resolved"] else 1, -u["recent_weekly_avg"]))

        # Mark top N users by total activity as "likely licensed"
        # Sort by total_events descending to find top N, then restore original sort
        if contracted_seats and contracted_seats > 0:
            by_activity = sorted(users, key=lambda u: u["total_events"], reverse=True)
            licensed_ids = {u["username"] for u in by_activity[:contracted_seats]}
            for u in users:
                u["licensed"] = u["username"] in licensed_ids
        else:
            # No seat data — mark all as licensed (can't filter)
            for u in users:
                u["licensed"] = True

        # Status counts
        status_counts = {"hot": 0, "warm": 0, "cooling": 0, "cold": 0}
        for u in users:
            status_counts[u["status"]] = status_counts.get(u["status"], 0) + 1

        total_users = len(users)

        # KPIs
        cold_cooling = status_counts["cold"] + status_counts["cooling"]
        at_risk_pct = round(cold_cooling / total_users * 100) if total_users > 0 else 0

        kpis = [
            {"value": str(total_users), "label": "Tracked Users"},
            {"value": f"{status_counts['hot']}", "label": "Hot (Active)"},
            {"value": f"{cold_cooling}", "label": "Cooling + Cold"},
            {"value": f"{at_risk_pct}%", "label": "At Risk"},
        ]

        # Narrative
        narrative = self._build_narrative(
            customer_name, users, status_counts, total_users, at_risk_pct,
        )

        return {
            "available": True,
            "reason": None,
            "customer": customer_name,
            "generated": date.today().isoformat(),
            "period": {"start": week_labels[0], "end": week_labels[-1]} if week_labels else {},
            "page_type": "engagement-decay",
            "kpis": kpis,
            "users": users,
            "weeks": week_labels,
            "status_counts": status_counts,
            "contracted_seats": contracted_seats,
            "narrative": narrative,
        }

    def _classify_status(self, ratio: float, weeks_inactive: int) -> str:
        """Classify user engagement status based on activity ratio and inactivity."""
        if weeks_inactive > self.STATUS_THRESHOLDS["cooling"]["max_inactive_weeks"]:
            return "cold"
        if ratio >= self.STATUS_THRESHOLDS["hot"]["min_ratio"] and weeks_inactive <= self.STATUS_THRESHOLDS["hot"]["max_inactive_weeks"]:
            return "hot"
        if ratio >= self.STATUS_THRESHOLDS["warm"]["min_ratio"] and weeks_inactive <= self.STATUS_THRESHOLDS["warm"]["max_inactive_weeks"]:
            return "warm"
        if ratio >= self.STATUS_THRESHOLDS["cooling"]["min_ratio"] and weeks_inactive <= self.STATUS_THRESHOLDS["cooling"]["max_inactive_weeks"]:
            return "cooling"
        return "cold"

    def _build_narrative(
        self, customer: str, users: list, counts: dict, total: int, at_risk_pct: int,
    ) -> dict:
        """Build structured narrative from engagement decay data."""
        highlights = []
        recommendations = []

        # Overall health
        if at_risk_pct <= 15:
            highlights.append(
                f"Healthy engagement: only {at_risk_pct}% of users showing signs of decline."
            )
        elif at_risk_pct <= 35:
            highlights.append(
                f"Moderate risk: {at_risk_pct}% of users are cooling or cold. Worth monitoring."
            )
        else:
            highlights.append(
                f"High churn risk: {at_risk_pct}% of users ({counts['cooling'] + counts['cold']}) "
                f"are cooling or have gone cold."
            )

        # Status breakdown
        highlights.append(
            f"Status breakdown: {counts['hot']} hot, {counts['warm']} warm, "
            f"{counts['cooling']} cooling, {counts['cold']} cold."
        )

        # Biggest decliners (cooling users with high peak)
        decliners = [u for u in users if u["status"] == "cooling" and u["peak_weekly_avg"] > 50]
        if decliners:
            top = decliners[0]
            recommendations.append(
                f"{top['username']} was highly active (peak {top['peak_weekly_avg']} events/wk) "
                f"but has dropped to {top['recent_weekly_avg']}/wk. Reach out before they go cold."
            )

        # Recently gone cold (< 4 weeks cold)
        recently_cold = [u for u in users if u["status"] == "cold" and u["weeks_inactive"] <= 6]
        if recently_cold:
            names = ", ".join(u["username"] for u in recently_cold[:3])
            recommendations.append(
                f"Recently gone cold: {names}. Still recoverable with timely outreach."
            )

        # Long-term cold (> 8 weeks)
        long_cold = [u for u in users if u["status"] == "cold" and u["weeks_inactive"] > 8]
        if long_cold:
            highlights.append(
                f"{len(long_cold)} users inactive for 8+ weeks — likely churned or moved to a different tool."
            )

        # Hot users with declining trend
        hot_declining = [u for u in users if u["status"] == "hot" and u["trend_pct"] < -20]
        if hot_declining:
            names = ", ".join(u["username"] for u in hot_declining[:3])
            recommendations.append(
                f"Watch list: {names} — currently active but trending down ({hot_declining[0]['trend_pct']}% WoW)."
            )

        if not recommendations:
            recommendations.append(
                "No immediate action needed. Continue monitoring for early signs of disengagement."
            )

        return {
            "executive_summary": (
                f"{customer} has {total} tracked users. "
                f"{counts['hot']} actively engaged, {counts['cooling'] + counts['cold']} at risk of churning."
            ),
            "highlights": highlights[:5],
            "recommendations": recommendations[:4],
        }
