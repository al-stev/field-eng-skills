"""User Journey transform — adoption funnel and Sankey flows from dim_users milestones."""

from datetime import date
from typing import Any

import pandas as pd

from transforms.base import BaseTransform


class UserJourneyTransform(BaseTransform):
    """
    Transforms user_journey_query() output into User Journey PAGE_DATA.

    Input: DataFrame with columns [universal_user_id, first_*_at timestamps]
    Output: PAGE_DATA with Sankey nodes/links, funnel counts, and per-stage stats.
    """

    # Ordered adoption stages (linear funnel, then branching)
    STAGES = [
        ("telemetry", "first_telemetry_at", "SDK Installed"),
        ("run", "first_run_at", "First Run"),
        ("sweep", "first_sweep_at", "First Sweep"),
        ("table", "first_table_created_at", "First Table"),
        ("weave", "first_weave_call_at", "First Weave Call"),
        ("license", "first_license_created_at", "License Created"),
    ]

    def transform(self, user_journey: pd.DataFrame, **kwargs: Any) -> dict[str, Any]:
        if user_journey.empty:
            return self.empty_result("no_data")

        customer_name = kwargs.get("customer_name", "Unknown")
        weave_customer = kwargs.get("weave_customer", True)

        total_users = len(user_journey)

        # Count users at each stage
        stage_counts = {}
        for key, col, label in self.STAGES:
            if col in user_journey.columns:
                count = int(user_journey[col].notna().sum())
                if count > 0:
                    stage_counts[key] = {"key": key, "col": col, "label": label, "count": count}

        # Skip Weave if not contracted and count is 0
        if not weave_customer and "weave" in stage_counts and stage_counts["weave"]["count"] == 0:
            del stage_counts["weave"]

        # Skip license if count is 0 (server deployments)
        if "license" in stage_counts and stage_counts["license"]["count"] == 0:
            del stage_counts["license"]

        if not stage_counts:
            return self.empty_result("no_data")

        # Build funnel: ordered stages by count descending
        funnel = sorted(stage_counts.values(), key=lambda s: s["count"], reverse=True)

        # Build Sankey flows
        # The Sankey shows: total_users -> telemetry -> run -> [sweep, table, weave]
        nodes = []
        links = []
        seen_nodes = set()

        def add_node(name):
            if name not in seen_nodes:
                nodes.append({"name": name})
                seen_nodes.add(name)

        # Entry node
        add_node("All Users")

        # Telemetry as first filter
        has_telemetry = "telemetry" in stage_counts
        has_run = "run" in stage_counts

        if has_telemetry:
            tel_count = stage_counts["telemetry"]["count"]
            no_telemetry = total_users - tel_count
            add_node("SDK Installed")
            links.append({"source": "All Users", "target": "SDK Installed", "value": tel_count})
            if no_telemetry > 0:
                add_node("No SDK")
                links.append({"source": "All Users", "target": "No SDK", "value": no_telemetry})

            if has_run:
                run_count = stage_counts["run"]["count"]
                # Users with telemetry but no run
                tel_only = tel_count - run_count
                add_node("First Run")
                links.append({"source": "SDK Installed", "target": "First Run", "value": run_count})
                if tel_only > 0:
                    add_node("SDK Only")
                    links.append({"source": "SDK Installed", "target": "SDK Only", "value": tel_only})

                # From First Run, branch to advanced features
                # Count users who reached each advanced stage (must also have run)
                advanced_stages = []
                for key in ["sweep", "table", "weave"]:
                    if key in stage_counts:
                        col = stage_counts[key]["col"]
                        label = stage_counts[key]["label"]
                        # Users with both run and this stage
                        both = int((user_journey["first_run_at"].notna() & user_journey[col].notna()).sum())
                        if both > 0:
                            advanced_stages.append({"key": key, "label": label, "count": both})

                advanced_users = set()
                for stage in advanced_stages:
                    col = stage_counts[stage["key"]]["col"]
                    mask = user_journey["first_run_at"].notna() & user_journey[col].notna()
                    advanced_users.update(user_journey[mask]["universal_user_id"].tolist())
                    add_node(stage["label"])
                    links.append({"source": "First Run", "target": stage["label"], "value": stage["count"]})

                # Users with run but no advanced feature
                run_only = run_count - len(advanced_users)
                if run_only > 0:
                    add_node("Runs Only")
                    links.append({"source": "First Run", "target": "Runs Only", "value": run_only})
            else:
                # No run data — all telemetry users stop at SDK
                pass
        else:
            # No telemetry data — unusual, show what we have
            add_node("Active Users")
            links.append({"source": "All Users", "target": "Active Users", "value": total_users})

        # KPIs
        tel = stage_counts.get("telemetry", {}).get("count", 0)
        run = stage_counts.get("run", {}).get("count", 0)
        adoption_pct = round(run / total_users * 100) if total_users > 0 else 0
        deepest_stage = funnel[-1] if funnel else None
        deepest_label = deepest_stage["label"] if deepest_stage else "--"
        deepest_pct = round(deepest_stage["count"] / total_users * 100) if deepest_stage and total_users > 0 else 0

        kpis = [
            {"value": str(total_users), "label": "Total Users"},
            {"value": str(tel), "label": "SDK Installed"},
            {"value": f"{adoption_pct}%", "label": "Run Adoption"},
            {"value": f"{deepest_pct}%", "label": deepest_label},
        ]

        # Narrative
        narrative = self._build_narrative(customer_name, total_users, stage_counts, funnel)

        return {
            "available": True,
            "reason": None,
            "customer": customer_name,
            "generated": date.today().isoformat(),
            "period": {"start": "all-time", "end": date.today().isoformat()},
            "page_type": "user-journey",
            "kpis": kpis,
            "sankey": {"nodes": nodes, "links": links},
            "funnel": [{"label": s["label"], "count": s["count"], "pct": round(s["count"] / total_users * 100, 1)} for s in funnel],
            "total_users": total_users,
            "narrative": narrative,
        }

    def _build_narrative(self, customer: str, total: int, stages: dict, funnel: list) -> dict:
        highlights = []
        recommendations = []

        tel = stages.get("telemetry", {}).get("count", 0)
        run = stages.get("run", {}).get("count", 0)
        sweep = stages.get("sweep", {}).get("count", 0)
        table = stages.get("table", {}).get("count", 0)

        # SDK adoption
        if tel > 0:
            sdk_pct = round(tel / total * 100)
            if sdk_pct >= 80:
                highlights.append(f"Strong SDK penetration: {sdk_pct}% of users ({tel}) have installed the SDK.")
            else:
                highlights.append(f"{sdk_pct}% of users ({tel}/{total}) have the SDK installed.")
                if sdk_pct < 50:
                    recommendations.append(
                        f"{total - tel} users have accounts but never installed the SDK. "
                        f"Consider onboarding sessions or setup guides."
                    )

        # Run conversion
        if tel > 0 and run > 0:
            run_pct = round(run / tel * 100)
            drop = tel - run
            highlights.append(f"SDK-to-Run conversion: {run_pct}% ({run}/{tel}). {drop} users installed but never ran.")
            if run_pct < 60:
                recommendations.append(
                    f"{drop} users have the SDK but never created a run. "
                    f"This is the biggest drop-off — quickstart tutorials or pairing sessions could help."
                )

        # Advanced features
        if run > 0:
            if sweep > 0:
                sweep_pct = round(sweep / run * 100)
                highlights.append(f"{sweep_pct}% of runners ({sweep}) have tried Sweeps.")
                if sweep_pct < 20:
                    recommendations.append(f"Only {sweep_pct}% using Sweeps. Opportunity for hyperparameter optimization enablement.")
            if table > 0:
                table_pct = round(table / run * 100)
                highlights.append(f"{table_pct}% of runners ({table}) have created Tables.")

        if not recommendations:
            recommendations.append("Adoption funnel looks healthy. Monitor for drop-off at each stage over time.")

        return {
            "executive_summary": (
                f"{customer} has {total} users in dim_users. "
                f"{tel} installed the SDK, {run} created runs, "
                f"{sweep} tried Sweeps, {table} created Tables."
            ),
            "highlights": highlights[:5],
            "recommendations": recommendations[:4],
        }
