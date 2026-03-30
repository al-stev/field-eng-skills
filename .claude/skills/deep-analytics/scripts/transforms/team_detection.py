"""Team Detection transform -- organizational structure from org_name fields."""

from datetime import date
from typing import Any

import pandas as pd

from transforms.base import BaseTransform
from common.data_utils import safe_value, format_date


class TeamDetectionTransform(BaseTransform):
    """
    Transforms team_detection_query() and team_champions_query() output
    into Team Detection PAGE_DATA.

    Input:
        teams: DataFrame with columns [team_name, member_count, total_events,
               first_active, last_active, users_with_team_flag, product_area]
        champions: Optional DataFrame with columns [team_name, universal_user_id,
                   username, email, total_events, last_active]

    Output:
        PAGE_DATA dict with team breakdown, activity, heatmap, timeline,
        champions, growth, KPIs, and narrative.
    """

    def transform(self, teams: pd.DataFrame, champions: pd.DataFrame = None, members: pd.DataFrame = None, **kwargs: Any) -> dict[str, Any]:
        if teams.empty:
            return self.empty_result("no_data")

        customer_name = kwargs.get("customer_name", "Unknown")
        deployment_type = kwargs.get("deployment_type", "Unknown")

        # --- Three-tier team data status detection (TEAM-04) ---
        team_data_status = self._detect_team_data_status(teams)

        # For "unavailable" or "names_unavailable", return minimal but renderable result
        if team_data_status in ("unavailable", "names_unavailable"):
            total_flagged = int(teams["users_with_team_flag"].sum())
            return {
                "available": True,
                "reason": None,
                "customer": customer_name,
                "generated": date.today().isoformat(),
                "period": self._build_period(teams),
                "page_type": "team-detection",
                "team_data_status": team_data_status,
                "flagged_users": total_flagged,
                "kpis": [
                    {"value": "0", "label": "Teams Detected"},
                    {"value": str(total_flagged) if team_data_status == "names_unavailable" else "0", "label": "Total Members"},
                    {"value": "--", "label": "Most Active Team"},
                    {"value": "0", "label": "Product Areas Used"},
                ],
                "teams": [],
                "team_activity": {"team_names": [], "events": [], "users": []},
                "team_product_heatmap": {"team_names": [], "product_areas": [], "matrix": []},
                "team_timeline": [],
                "team_growth": {"months": [], "teams": []},
                "narrative": self._build_empty_narrative(customer_name, team_data_status, total_flagged),
                "data_source": "bigquery",
                "deployment_type": deployment_type,
            }

        # --- Full team data processing ---
        # Filter out "Unknown" for team analysis
        real_teams = teams[teams["team_name"] != "Unknown"].copy()

        # Team breakdown (TEAM-01): aggregate across product areas
        team_agg = self._aggregate_teams(real_teams)

        # Determine top_product per team
        team_top_product = self._top_product_per_team(real_teams)

        # Build teams list sorted by total_events descending
        teams_list = self._build_teams_list(team_agg, team_top_product, champions, members)

        # Team activity (TEAM-02)
        team_activity = self._build_team_activity(teams_list)

        # Team product heatmap (TEAM-03)
        team_product_heatmap = self._build_heatmap(real_teams)

        # Team timeline (TEAM-06)
        team_timeline = self._build_timeline(team_agg)

        # Team growth (TEAM-08) -- monthly user counts if data supports it
        team_growth = self._build_growth(real_teams)

        # KPIs
        product_areas_used = len(real_teams["product_area"].unique())
        kpis = [
            {"value": str(len(team_agg)), "label": "Teams Detected"},
            {"value": str(int(team_agg["member_count"].sum())), "label": "Total Members"},
            {"value": teams_list[0]["name"] if teams_list else "--", "label": "Most Active Team"},
            {"value": str(product_areas_used), "label": "Product Areas Used"},
        ]

        # Narrative (TEAM-05)
        narrative = self._build_narrative(teams_list, customer_name, product_areas_used, real_teams)

        return {
            "available": True,
            "reason": None,
            "customer": customer_name,
            "generated": date.today().isoformat(),
            "period": self._build_period(teams),
            "page_type": "team-detection",
            "team_data_status": "available",
            "kpis": kpis,
            "teams": teams_list,
            "team_activity": team_activity,
            "team_product_heatmap": team_product_heatmap,
            "team_timeline": team_timeline,
            "team_growth": team_growth,
            "narrative": narrative,
            "data_source": "bigquery",
            "deployment_type": deployment_type,
        }

    # ── Status detection ──

    def _detect_team_data_status(self, teams: pd.DataFrame) -> str:
        """
        Three-tier team data status:
        1. "available" -- real team names present
        2. "names_unavailable" -- no real names but team flags exist
        3. "unavailable" -- no real names and no team flags
        """
        non_unknown = teams[teams["team_name"] != "Unknown"]
        has_real_teams = len(non_unknown) > 0

        if has_real_teams:
            return "available"

        # All team_names are "Unknown" -- check team flags
        total_flagged = int(teams["users_with_team_flag"].sum())
        if total_flagged > 0:
            return "names_unavailable"

        return "unavailable"

    # ── Aggregation helpers ──

    def _aggregate_teams(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate across product areas to get per-team totals."""
        agg = df.groupby("team_name").agg(
            member_count=("member_count", "max"),
            total_events=("total_events", "sum"),
            first_active=("first_active", "min"),
            last_active=("last_active", "max"),
        ).reset_index()
        return agg.sort_values("total_events", ascending=False).reset_index(drop=True)

    def _top_product_per_team(self, df: pd.DataFrame) -> dict[str, str]:
        """Find the product area with most events per team."""
        product_by_team = df.groupby(["team_name", "product_area"])["total_events"].sum().reset_index()
        idx = product_by_team.groupby("team_name")["total_events"].idxmax()
        top = product_by_team.loc[idx]
        return dict(zip(top["team_name"], top["product_area"]))

    def _build_teams_list(
        self,
        team_agg: pd.DataFrame,
        top_product: dict[str, str],
        champions: pd.DataFrame | None,
        members: pd.DataFrame | None = None,
    ) -> list[dict]:
        """Build the teams list with champion and member data merged in."""
        # Build champion lookup
        champion_map: dict[str, dict] = {}
        if champions is not None and not champions.empty:
            for _, row in champions.iterrows():
                name = safe_value(row.get("team_name"))
                if name is None:
                    continue
                username = safe_value(row.get("username"))
                email = safe_value(row.get("email"))
                display_name = username or (email.split("@")[0] if email else "Unknown")
                champion_map[name] = {
                    "username": username or (email.split("@")[0] if email else None),
                    "display_name": display_name,
                    "events": int(row["total_events"]),
                }

        # Build members lookup (team_name -> list of {name, runs} sorted by runs desc)
        members_map: dict[str, list[dict]] = {}
        if members is not None and not members.empty:
            for team_name, group in members.groupby("team_name"):
                team_members = []
                for _, mrow in group.iterrows():
                    member_name = safe_value(mrow.get("member_name"))
                    if member_name is None:
                        continue
                    team_members.append({
                        "name": member_name,
                        "runs": int(mrow.get("run_count", 0)),
                    })
                members_map[str(team_name)] = team_members[:10]  # top 10 per team

        teams_list = []
        for _, row in team_agg.iterrows():
            name = row["team_name"]
            team = {
                "name": name,
                "member_count": int(row["member_count"]),
                "total_events": int(row["total_events"]),
                "top_product": top_product.get(name, "Unknown"),
                "first_active": format_date(row["first_active"]),
                "last_active": format_date(row["last_active"]),
                "champion": champion_map.get(name),
                "members": members_map.get(str(name), []),
            }
            teams_list.append(team)

        return teams_list

    # ── Chart data builders ──

    def _build_team_activity(self, teams_list: list[dict]) -> dict:
        """Build team activity bar chart data (TEAM-02)."""
        return {
            "team_names": [t["name"] for t in teams_list],
            "events": [t["total_events"] for t in teams_list],
            "users": [t["member_count"] for t in teams_list],
        }

    def _build_heatmap(self, df: pd.DataFrame) -> dict:
        """Build team x product area heatmap data (TEAM-03)."""
        pivot = df.groupby(["team_name", "product_area"])["total_events"].sum().reset_index()

        team_names = sorted(pivot["team_name"].unique())
        product_areas = sorted(pivot["product_area"].unique())

        team_idx = {name: i for i, name in enumerate(team_names)}
        area_idx = {area: i for i, area in enumerate(product_areas)}

        matrix = []
        for _, row in pivot.iterrows():
            ti = team_idx[row["team_name"]]
            ai = area_idx[row["product_area"]]
            matrix.append([ti, ai, int(row["total_events"])])

        return {
            "team_names": team_names,
            "product_areas": product_areas,
            "matrix": matrix,
        }

    def _build_timeline(self, team_agg: pd.DataFrame) -> list[dict]:
        """Build team adoption timeline data (TEAM-06)."""
        timeline = []
        for _, row in team_agg.iterrows():
            timeline.append({
                "name": row["team_name"],
                "first_active": format_date(row["first_active"]),
                "last_active": format_date(row["last_active"]),
            })
        return timeline

    def _build_growth(self, df: pd.DataFrame) -> dict:
        """
        Build team growth trend data (TEAM-08).

        Since team_detection_query() aggregates across the full period,
        we cannot derive monthly granularity from it. Return empty growth
        structure -- the handler can supply monthly data if available.
        """
        # The query returns totals, not monthly breakdowns.
        # A future enhancement could add a monthly team query.
        return {"months": [], "teams": []}

    # ── Period ──

    def _build_period(self, df: pd.DataFrame) -> dict:
        """Build period dict from dataframe date ranges."""
        if "first_active" in df.columns and not df.empty:
            return {
                "start": format_date(df["first_active"].min()),
                "end": format_date(df["last_active"].max()),
            }
        return {}

    # ── Narrative ──

    def _build_narrative(
        self,
        teams_list: list[dict],
        customer: str,
        product_areas_used: int,
        raw_df: pd.DataFrame,
    ) -> dict:
        """Build structured narrative from team data (TEAM-05)."""
        highlights = []
        recommendations = []

        num_teams = len(teams_list)

        # Largest team
        if teams_list:
            top = teams_list[0]
            highlights.append(
                f"{top['name']} is the most active team with {top['total_events']:,} events "
                f"and {top['member_count']} members."
            )

        # Product diversity
        if product_areas_used >= 4:
            highlights.append(
                f"Strong product breadth: {product_areas_used} product areas in use across teams."
            )
        elif product_areas_used <= 2 and num_teams > 1:
            recommendations.append(
                f"Only {product_areas_used} product areas in use. Consider enablement sessions "
                f"to expand teams into Artifacts, Sweeps, or Weave."
            )

        # Newest teams (first_active within last 3 months)
        recent_teams = [t for t in teams_list if t.get("first_active") and t["first_active"] >= "2025-12"]
        if recent_teams:
            names = ", ".join(t["name"] for t in recent_teams[:3])
            highlights.append(f"Recently onboarded teams: {names}.")

        # Champion insights
        teams_with_champ = [t for t in teams_list if t.get("champion")]
        if teams_with_champ:
            top_champ_team = max(teams_with_champ, key=lambda t: t["champion"]["events"])
            highlights.append(
                f"Top champion: {top_champ_team['champion']['display_name']} in {top_champ_team['name']} "
                f"with {top_champ_team['champion']['events']:,} events."
            )

        # Teams using only 1 product area -- enablement opportunity
        for team in teams_list:
            team_areas = raw_df[raw_df["team_name"] == team["name"]]["product_area"].nunique()
            if team_areas == 1:
                recommendations.append(
                    f"{team['name']}: Only using {team['top_product']}. "
                    f"Consider cross-product enablement to increase platform stickiness."
                )

        # Small teams
        small_teams = [t for t in teams_list if t["member_count"] <= 2]
        if small_teams:
            names = ", ".join(t["name"] for t in small_teams[:3])
            recommendations.append(
                f"Small teams ({names}) have 1-2 members. "
                f"Single-user dependency risk -- encourage broader team adoption."
            )

        if not recommendations:
            recommendations.append(
                "Team adoption patterns look healthy. "
                "Monitor growth trends for early signals of team contraction."
            )

        return {
            "executive_summary": (
                f"{customer} has {num_teams} active team(s) using {product_areas_used} "
                f"W&B product areas."
            ),
            "highlights": highlights[:5],
            "recommendations": recommendations[:4],
        }

    def _build_empty_narrative(self, customer: str, status: str, flagged_users: int) -> dict:
        """Build narrative for unavailable/names_unavailable states."""
        if status == "names_unavailable":
            return {
                "executive_summary": (
                    f"{customer} has {flagged_users} users flagged as team members, "
                    f"but organization names are not populated in W&B."
                ),
                "highlights": [
                    f"{flagged_users} users have is_part_of_team=True but org_name is NULL."
                ],
                "recommendations": [
                    "Configure organization names in W&B to enable team-level analytics.",
                    "Contact the customer admin to set up organization structure.",
                ],
            }
        return {
            "executive_summary": (
                f"{customer} does not have organization structure configured in W&B. "
                f"Team-level analysis is unavailable."
            ),
            "highlights": [],
            "recommendations": [
                "Team analytics requires org_name to be populated in W&B.",
                "This typically means the account does not use W&B Organizations feature.",
            ],
        }
