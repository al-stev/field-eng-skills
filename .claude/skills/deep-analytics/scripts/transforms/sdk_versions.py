"""SDK Versions transform — version distribution, freshness classification, migration tracking."""

import re
from datetime import date
from typing import Any

import pandas as pd

from transforms.base import BaseTransform


class SdkVersionsTransform(BaseTransform):
    """
    Transforms sdk_versions_query() output into SDK Versions PAGE_DATA.

    Input: DataFrame with columns [month, sdk_version, user_count]
    Output: PAGE_DATA dict with version distribution, freshness, migration timeline.
    """

    # Semver regex: captures major.minor.patch (ignores pre-release suffixes)
    SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)")

    # Freshness thresholds (minor versions behind latest)
    FRESHNESS_THRESHOLDS = {
        "current": 0,   # latest minor
        "recent": 2,    # within 2 minor versions
        "stale": 5,     # within 5 minor versions
        # anything beyond 5 = "ancient"
    }

    def transform(self, sdk_versions: pd.DataFrame, **kwargs: Any) -> dict[str, Any]:
        if sdk_versions.empty:
            return self.empty_result("no_data")

        customer_name = kwargs.get("customer_name", "Unknown")

        # Parse versions and filter valid semver
        sdk_versions = sdk_versions.copy()
        parsed = sdk_versions["sdk_version"].apply(self._parse_version)
        sdk_versions["major"] = parsed.apply(lambda x: x[0] if x else None)
        sdk_versions["minor"] = parsed.apply(lambda x: x[1] if x else None)
        sdk_versions["patch"] = parsed.apply(lambda x: x[2] if x else None)
        sdk_versions = sdk_versions.dropna(subset=["major"])
        sdk_versions["major"] = sdk_versions["major"].astype(int)
        sdk_versions["minor"] = sdk_versions["minor"].astype(int)
        sdk_versions["patch"] = sdk_versions["patch"].astype(int)

        if sdk_versions.empty:
            return self.empty_result("no_data")

        # Determine latest version (highest semver seen across all months)
        latest_major = sdk_versions["major"].max()
        latest_subset = sdk_versions[sdk_versions["major"] == latest_major]
        latest_minor = latest_subset["minor"].max()

        # Classify freshness per version
        sdk_versions["freshness"] = sdk_versions.apply(
            lambda row: self._classify_freshness(row["major"], row["minor"], latest_major, latest_minor),
            axis=1,
        )

        # Use full semver (major.minor.patch) for display — dropping patch
        # makes versions like 0.78.0 look like the float 0.78
        sdk_versions["version_label"] = sdk_versions["sdk_version"].str.strip()

        all_months = sorted(sdk_versions["month"].unique())

        # --- Current snapshot: latest month's distribution ---
        latest_month = all_months[-1]
        snapshot = sdk_versions[sdk_versions["month"] == latest_month]
        snapshot_agg = (
            snapshot.groupby(["version_label", "freshness"])
            .agg(users=("user_count", "sum"))
            .reset_index()
            .sort_values("users", ascending=False)
        )

        total_users_latest = int(snapshot_agg["users"].sum())

        # Build donut data (top versions + "other" bucket)
        donut_data = []
        other_users = 0
        for _, row in snapshot_agg.iterrows():
            if len(donut_data) < 8:
                donut_data.append({
                    "version": row["version_label"],
                    "users": int(row["users"]),
                    "freshness": row["freshness"],
                    "pct": round(int(row["users"]) / total_users_latest * 100, 1) if total_users_latest > 0 else 0,
                })
            else:
                other_users += int(row["users"])
        if other_users > 0:
            donut_data.append({
                "version": "Other",
                "users": other_users,
                "freshness": "ancient",
                "pct": round(other_users / total_users_latest * 100, 1) if total_users_latest > 0 else 0,
            })

        # --- Timeline: monthly version distribution (stacked bar) ---
        timeline = []
        # Get unique version labels sorted by semver
        unique_versions = sorted(
            sdk_versions["version_label"].unique(),
            key=lambda v: tuple(int(x) for x in v.split(".") if x.isdigit()),
        )
        for month in all_months:
            month_data = sdk_versions[sdk_versions["month"] == month]
            month_agg = month_data.groupby("version_label")["user_count"].sum()
            entry = {"month": month}
            for v in unique_versions:
                entry[v] = int(month_agg.get(v, 0))
            timeline.append(entry)

        # --- Version table: all versions with details ---
        version_table = []
        for v in unique_versions:
            v_data = sdk_versions[sdk_versions["version_label"] == v]
            freshness = v_data["freshness"].iloc[0]
            # First seen / last seen
            months_present = sorted(v_data["month"].unique())
            total_users_ever = int(v_data["user_count"].sum())
            latest_month_users = int(
                v_data[v_data["month"] == latest_month]["user_count"].sum()
            ) if latest_month in v_data["month"].values else 0

            version_table.append({
                "version": v,
                "freshness": freshness,
                "first_seen": months_present[0],
                "last_seen": months_present[-1],
                "current_users": latest_month_users,
                "total_user_months": total_users_ever,
            })

        # Sort table: current users descending
        version_table.sort(key=lambda x: x["current_users"], reverse=True)

        # --- Freshness summary ---
        freshness_counts = {"current": 0, "recent": 0, "stale": 0, "ancient": 0}
        for d in donut_data:
            if d["version"] != "Other":
                freshness_counts[d["freshness"]] = freshness_counts.get(d["freshness"], 0) + d["users"]
            else:
                freshness_counts["ancient"] += d["users"]

        # --- KPIs ---
        unique_versions_count = len(unique_versions)
        current_pct = round(freshness_counts["current"] / total_users_latest * 100) if total_users_latest > 0 else 0
        # Find the highest full version string for the latest major.minor
        latest_subset_full = sdk_versions[
            (sdk_versions["major"] == latest_major) & (sdk_versions["minor"] == latest_minor)
        ]
        latest_patch = latest_subset_full["patch"].max()
        latest_version_str = f"{latest_major}.{latest_minor}.{latest_patch}"

        kpis = [
            {"value": latest_version_str, "label": "Latest CLI Version"},
            {"value": f"{current_pct}%", "label": "On Latest Minor"},
            {"value": str(unique_versions_count), "label": "Versions in Use"},
            {"value": str(total_users_latest), "label": f"Users ({latest_month})"},
        ]

        # --- Narrative ---
        narrative = self._build_narrative(
            customer_name, latest_version_str, unique_versions_count,
            freshness_counts, total_users_latest, version_table, donut_data,
        )

        return {
            "available": True,
            "reason": None,
            "customer": customer_name,
            "generated": date.today().isoformat(),
            "period": {"start": all_months[0], "end": all_months[-1]} if all_months else {},
            "page_type": "sdk-versions",
            "kpis": kpis,
            "donut": donut_data,
            "timeline": timeline,
            "versions": unique_versions,
            "version_table": version_table,
            "freshness_summary": freshness_counts,
            "latest_version": latest_version_str,
            "snapshot_month": latest_month,
            "narrative": narrative,
        }

    def _parse_version(self, version_str: str) -> tuple | None:
        """Parse a version string into (major, minor, patch) or None."""
        if not version_str or not isinstance(version_str, str):
            return None
        m = self.SEMVER_RE.match(version_str.strip())
        if m:
            return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return None

    def _classify_freshness(self, major: int, minor: int, latest_major: int, latest_minor: int) -> str:
        """Classify a version's freshness relative to the latest."""
        if major < latest_major:
            return "ancient"

        minor_behind = latest_minor - minor
        if minor_behind <= self.FRESHNESS_THRESHOLDS["current"]:
            return "current"
        elif minor_behind <= self.FRESHNESS_THRESHOLDS["recent"]:
            return "recent"
        elif minor_behind <= self.FRESHNESS_THRESHOLDS["stale"]:
            return "stale"
        else:
            return "ancient"

    def _build_narrative(
        self, customer: str, latest: str, version_count: int,
        freshness: dict, total_users: int, table: list, donut: list,
    ) -> dict:
        """Build structured narrative from SDK version data."""
        highlights = []
        recommendations = []

        current_pct = round(freshness["current"] / total_users * 100) if total_users > 0 else 0
        stale_ancient = freshness["stale"] + freshness["ancient"]
        stale_pct = round(stale_ancient / total_users * 100) if total_users > 0 else 0

        # Version spread
        if version_count <= 3:
            highlights.append(
                f"Clean version landscape: only {version_count} SDK versions in use across the account."
            )
        elif version_count >= 8:
            highlights.append(
                f"Fragmented SDK landscape: {version_count} different versions in use. "
                f"This increases support complexity and may mask version-specific bugs."
            )
        else:
            highlights.append(
                f"{version_count} SDK versions in use across {total_users} active users."
            )

        # Current version adoption
        if current_pct >= 80:
            highlights.append(
                f"{current_pct}% of users on the latest SDK version ({latest}) — excellent adoption."
            )
        elif current_pct >= 50:
            highlights.append(
                f"{current_pct}% of users on the latest version ({latest}). Good, but {100 - current_pct}% remain on older versions."
            )
        else:
            recommendations.append(
                f"Only {current_pct}% on the latest SDK ({latest}). "
                f"Consider a coordinated upgrade push — newer versions include performance improvements and bug fixes."
            )

        # Stale/ancient users
        if stale_pct > 20:
            recommendations.append(
                f"{stale_pct}% of users ({stale_ancient}) on stale or ancient SDK versions. "
                f"These users may hit known bugs and miss out on new features."
            )

        # Top version if not latest
        if donut and donut[0]["version"] != latest and donut[0]["freshness"] != "current":
            top = donut[0]
            recommendations.append(
                f"Most popular version is {top['version']} ({top['users']} users, {top['pct']}%), "
                f"not the latest. Investigate if there's a blocker preventing upgrade."
            )

        # Single-version dominance
        if donut and donut[0]["pct"] >= 90:
            highlights.append(
                f"Strong standardization: {donut[0]['version']} accounts for {donut[0]['pct']}% of all users."
            )

        # Migration momentum: check if latest version is growing
        latest_in_table = next((v for v in table if v["version"] == latest), None)
        if latest_in_table and latest_in_table["first_seen"] == latest_in_table["last_seen"]:
            highlights.append(
                f"Latest version {latest} just appeared in {latest_in_table['first_seen']} — migration just starting."
            )

        if not recommendations:
            recommendations.append(
                "SDK version health looks good. Continue monitoring for version fragmentation as the team scales."
            )

        return {
            "executive_summary": (
                f"{customer} has {total_users} users across {version_count} SDK versions. "
                f"{current_pct}% on the latest ({latest}), {stale_pct}% on stale/ancient versions."
            ),
            "highlights": highlights[:5],
            "recommendations": recommendations[:4],
        }
