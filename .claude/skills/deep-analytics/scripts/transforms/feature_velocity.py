"""Feature Velocity transform — per-product-area time-series with momentum indicators."""

from datetime import date
from typing import Any

import pandas as pd

from transforms.base import BaseTransform


class FeatureVelocityTransform(BaseTransform):
    """
    Transforms product_areas_query() output into Feature Velocity PAGE_DATA.

    Input: DataFrame with columns [product_area, month, event_count, unique_users]
    Output: PAGE_DATA dict with sparkline data, momentum indicators, and KPIs.
    """

    WEAVE_AREAS = {"Weave Tracing", "Weave Evaluation", "Weave Data"}

    def transform(self, product_areas: pd.DataFrame, **kwargs: pd.DataFrame) -> dict[str, Any]:
        if product_areas.empty:
            return self.empty_result("no_data")

        customer_name = kwargs.get("customer_name", "Unknown")
        weave_customer = kwargs.get("weave_customer", True)

        # Filter out Weave areas if customer doesn't have Weave contracted
        if not weave_customer:
            product_areas = product_areas[~product_areas["product_area"].isin(self.WEAVE_AREAS)]
            if product_areas.empty:
                return self.empty_result("no_data")

        # Get all months and product areas
        all_months = sorted(product_areas["month"].unique())
        all_areas = sorted(product_areas["product_area"].unique())

        # Build per-area time series
        area_series = []
        for area in all_areas:
            area_data = product_areas[product_areas["product_area"] == area].sort_values("month")

            # Create a complete month series (fill missing months with 0)
            month_map = dict(zip(area_data["month"], zip(area_data["event_count"], area_data["unique_users"])))
            events = []
            users = []
            for m in all_months:
                ev, us = month_map.get(m, (0, 0))
                events.append(int(ev) if pd.notna(ev) else 0)
                users.append(int(us) if pd.notna(us) else 0)

            # Momentum: compare last 3 months vs prior 3 months
            recent_events = sum(events[-3:]) if len(events) >= 3 else sum(events)
            prior_events = sum(events[-6:-3]) if len(events) >= 6 else sum(events[:max(1, len(events) // 2)])

            if prior_events > 0:
                momentum_pct = round((recent_events - prior_events) / prior_events * 100, 1)
            elif recent_events > 0:
                momentum_pct = 100.0
            else:
                momentum_pct = 0.0

            if momentum_pct > 10:
                momentum = "up"
            elif momentum_pct < -10:
                momentum = "down"
            else:
                momentum = "flat"

            total_events = sum(events)
            latest_users = users[-1] if users else 0
            avg_recent_users = round(sum(users[-3:]) / min(3, len(users))) if users else 0

            area_series.append({
                "area": area,
                "months": all_months,
                "events": events,
                "users": users,
                "total_events": total_events,
                "latest_monthly_users": latest_users,
                "avg_recent_users": avg_recent_users,
                "momentum": momentum,
                "momentum_pct": momentum_pct,
            })

        # Sort by total events descending
        area_series.sort(key=lambda x: x["total_events"], reverse=True)

        # KPIs
        total_events_all = sum(a["total_events"] for a in area_series)
        # Active areas = had events in the most recent 3 months
        active_areas = len([a for a in area_series if sum(a["events"][-3:]) > 0])
        top_area = area_series[0]["area"] if area_series else "None"
        accelerating = len([a for a in area_series if a["momentum"] == "up"])
        decelerating = len([a for a in area_series if a["momentum"] == "down"])

        # Generate AI narrative from data
        narrative = self._build_narrative(area_series, customer_name, active_areas, accelerating, decelerating)

        return {
            "available": True,
            "reason": None,
            "customer": customer_name,
            "generated": date.today().isoformat(),
            "period": {"start": all_months[0], "end": all_months[-1]} if all_months else {},
            "page_type": "feature-velocity",
            "kpis": [
                {"value": f"{total_events_all:,}", "label": "Total Events (12mo)"},
                {"value": str(active_areas), "label": "Active Product Areas"},
                {"value": top_area, "label": "Top Area"},
                {"value": f"{accelerating}↑ {decelerating}↓", "label": "Momentum"},
            ],
            "areas": area_series,
            "months": all_months,
            "narrative": narrative,
        }

    def _build_narrative(self, areas: list, customer: str, active: int, accel: int, decel: int) -> dict:
        """Build structured narrative from velocity data."""
        highlights = []
        recommendations = []

        # Top area by volume
        if areas:
            top = areas[0]
            highlights.append(
                f"{top['area']} dominates with {top['total_events']:,} events "
                f"({top['avg_recent_users']} active users/mo recently)."
            )

        # Accelerating areas
        accel_areas = [a for a in areas if a["momentum"] == "up" and a["total_events"] > 0]
        if accel_areas:
            names = ", ".join(a["area"] for a in accel_areas[:3])
            highlights.append(
                f"Growing areas: {names} — all showing increased activity vs prior 3 months."
            )

        # Decelerating areas
        decel_areas = [a for a in areas if a["momentum"] == "down" and a["total_events"] > 100]
        if decel_areas:
            worst = max(decel_areas, key=lambda a: abs(a["momentum_pct"]))
            highlights.append(
                f"{worst['area']} declining the fastest at {worst['momentum_pct']}% vs prior 3 months "
                f"({worst['avg_recent_users']} active users/mo)."
            )

        # Dead areas (had events historically but none recently)
        dead_areas = [a for a in areas if a["total_events"] > 0 and sum(a["events"][-3:]) == 0]
        if dead_areas:
            names = ", ".join(a["area"] for a in dead_areas)
            highlights.append(
                f"Inactive recently: {names} — had historical usage but no events in last 3 months."
            )

        # Cliff detection: sudden drop (>90%) from one month to the next
        for a in areas:
            events = a["events"]
            for i in range(1, len(events)):
                if events[i - 1] > 100 and events[i] == 0 and i < len(events) - 1 and events[i + 1] <= 5 if i + 1 < len(events) else True:
                    month_label = a["months"][i] if i < len(a["months"]) else "unknown"
                    recommendations.append(
                        f"{a['area']}: Abrupt drop to near-zero in {month_label} "
                        f"(from {events[i-1]:,} events). Likely an instrumentation/tracking change "
                        f"rather than user behavior — verify with product team."
                    )
                    break  # only flag once per area

        # Breadth assessment
        if active <= 3:
            recommendations.append(
                f"Only {active} product areas active recently. Explore expansion into "
                f"underused areas to increase platform stickiness."
            )
        elif active >= 7:
            highlights.append(
                f"Strong platform breadth: {active} product areas active in the last 3 months."
            )

        # Specific recommendations based on patterns
        for a in areas:
            if a["momentum"] == "down" and a["avg_recent_users"] > 20 and a["total_events"] > 1000:
                recommendations.append(
                    f"{a['area']}: {a['avg_recent_users']} users still active but events declining "
                    f"({a['momentum_pct']}%). Investigate whether this is seasonal or a disengagement signal."
                )
            if a["total_events"] > 0 and a["avg_recent_users"] <= 2 and a["avg_recent_users"] > 0:
                recommendations.append(
                    f"{a['area']}: Only {a['avg_recent_users']} user(s) active. "
                    f"Single-user dependency risk — consider enablement to broaden adoption."
                )

        # Enablement opportunities
        unused = [a for a in areas if a["total_events"] == 0]
        if not unused:
            # Check for low-adoption areas
            low = [a for a in areas if 0 < a["total_events"] < 100 and a["avg_recent_users"] <= 3]
            if low:
                names = ", ".join(a["area"] for a in low)
                recommendations.append(
                    f"Low adoption areas ({names}) could benefit from targeted enablement sessions."
                )

        if not recommendations:
            recommendations.append(
                "Usage patterns look healthy across active areas. "
                "Monitor momentum trends for early signals of change."
            )

        return {
            "executive_summary": (
                f"{customer} uses {active} W&B product areas actively. "
                f"{accel} area(s) accelerating, {decel} decelerating."
            ),
            "highlights": highlights[:5],
            "recommendations": recommendations[:4],
        }
