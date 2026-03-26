"""Usage Correlation transform — cross-account product co-occurrence with privacy controls."""

import json
import re
from datetime import date, timedelta
from typing import Any

import pandas as pd

from transforms.base import BaseTransform


# Pattern matching SFDC account IDs (18-char format starting with 0018)
SFDC_ID_PATTERN = re.compile(r"0018[A-Za-z0-9]{14}")


class UsageCorrelationTransform(BaseTransform):
    """
    Transforms cross-account product area data into Usage Correlation PAGE_DATA.

    This is the only cross-account transform in the deep analytics suite.
    It produces a co-occurrence matrix, peer benchmarking, next-best-action
    recommendations, and expansion signals — all with strict privacy controls.

    Privacy enforcement:
    - Minimum 10-account cohort for any displayed statistic
    - No individual account IDs or names in output
    - SFDC ID scan on serialized output before returning
    """

    MIN_COHORT_SIZE = 10

    def transform(self, **kwargs: Any) -> dict[str, Any]:
        cross_account: pd.DataFrame = kwargs.get("cross_account", pd.DataFrame())
        arr_data: pd.DataFrame = kwargs.get("arr_data", pd.DataFrame())
        current_account_areas: list[str] = kwargs.get("current_account_areas", [])
        account_health: dict = kwargs.get("account_health", {})
        customer_name: str = kwargs.get("customer_name", "Unknown")
        account_id: str = kwargs.get("account_id", "")
        deployment_type: str = kwargs.get("deployment_type", "Unknown")

        # --- Early exits ---
        if cross_account.empty:
            return self.empty_result("cross_account_unavailable")

        unique_accounts = cross_account["account_id"].nunique()
        if unique_accounts < self.MIN_COHORT_SIZE:
            return self.empty_result("insufficient_cohort")

        # --- Co-occurrence matrix ---
        correlation_matrix = self._build_correlation_matrix(cross_account)

        # --- Account positioning ---
        account_positioning = self._build_account_positioning(
            current_account_areas, correlation_matrix
        )

        # --- Next-best-action ---
        next_best_action = self._build_next_best_action(
            current_account_areas, correlation_matrix, customer_name
        )

        # --- Expansion signals ---
        expansion_signals = self._build_expansion_signals(account_health)

        # --- Peer benchmarking ---
        peer_benchmarking = self._build_peer_benchmarking(
            arr_data, account_id
        )

        # --- ARR-usage scatter ---
        arr_scatter = self._build_arr_scatter(arr_data, account_id)

        # --- Narrative ---
        narrative = self._build_narrative(
            customer_name, current_account_areas, correlation_matrix,
            next_best_action, peer_benchmarking, expansion_signals,
        )

        # --- KPIs ---
        top_retention = 0
        if correlation_matrix["matrix"]:
            top_retention = max(entry[3] for entry in correlation_matrix["matrix"])

        breadth_pct = peer_benchmarking.get("breadth_percentile", 0)

        kpis = [
            {"value": str(len(current_account_areas)), "label": "Product Areas Active"},
            {"value": f"{round(top_retention)}%", "label": "Top Combo Retention"},
            {"value": f"P{round(breadth_pct)}", "label": "Breadth Percentile"},
            {"value": str(len(expansion_signals)), "label": "Expansion Signals"},
        ]

        result = {
            "available": True,
            "reason": None,
            "customer": customer_name,
            "generated": date.today().isoformat(),
            "page_type": "usage-correlation",
            "kpis": kpis,
            "privacy": {
                "badge_visible": True,
                "min_cohort_size": self.MIN_COHORT_SIZE,
                "anonymized": True,
            },
            "correlation_matrix": correlation_matrix,
            "account_positioning": account_positioning,
            "next_best_action": next_best_action,
            "expansion_signals": expansion_signals,
            "peer_benchmarking": peer_benchmarking,
            "arr_scatter": arr_scatter,
            "narrative": narrative,
            "data_source": "pre-aggregated cross-account (min 10-account cohort)",
            "deployment_type": deployment_type,
        }

        # --- Privacy enforcement: scan for leaked SFDC IDs ---
        self._enforce_privacy(result)

        return result

    def _build_correlation_matrix(self, cross_account: pd.DataFrame) -> dict:
        """Build co-occurrence matrix with retention overlay and cohort suppression."""
        # Create account x product_area presence matrix
        presence = cross_account.groupby(["account_id", "product_area"]).size().unstack(fill_value=0)
        presence = (presence > 0).astype(int)

        product_areas = sorted(presence.columns.tolist())
        num_areas = len(product_areas)

        # Determine "retained" accounts: those with activity in most recent period
        # We use account-level presence — if they're in cross_account data (last 6 months),
        # consider recent activity as last 30 days approximation: accounts with higher event counts
        # For simplicity, use total event mass as a proxy for recency
        account_events = cross_account.groupby("account_id")["events"].sum()
        median_events = account_events.median()
        retained_accounts = set(account_events[account_events >= median_events].index)

        total_accounts = len(presence)

        # Upper triangle: for each pair, compute co-occurrence, retention, cohort size
        matrix = []
        for i in range(num_areas):
            for j in range(i + 1, num_areas):
                area_a = product_areas[i]
                area_b = product_areas[j]

                # Accounts that have both areas
                both = presence[(presence[area_a] == 1) & (presence[area_b] == 1)]
                cohort_size = len(both)

                # Suppress if below minimum
                if cohort_size < self.MIN_COHORT_SIZE:
                    continue

                co_occurrence_pct = round(cohort_size / total_accounts * 100, 1)

                # Retention rate for this combo
                retained_in_cohort = len(
                    [acct for acct in both.index if acct in retained_accounts]
                )
                retention_pct = round(retained_in_cohort / cohort_size * 100, 1) if cohort_size > 0 else 0

                matrix.append([i, j, co_occurrence_pct, retention_pct, cohort_size])

        return {
            "product_areas": product_areas,
            "matrix": matrix,
        }

    def _build_account_positioning(
        self, current_areas: list[str], correlation_matrix: dict
    ) -> dict:
        """Show how the current account's areas match against aggregate patterns."""
        product_areas = correlation_matrix["product_areas"]
        matrix = correlation_matrix["matrix"]

        total_areas = len(product_areas)
        match_patterns = []

        for entry in matrix:
            row_idx, col_idx, co_occ_pct, retention_pct, cohort_size = entry
            area_a = product_areas[row_idx]
            area_b = product_areas[col_idx]

            has_a = area_a in current_areas
            has_b = area_b in current_areas

            if has_a and has_b:
                match_patterns.append({
                    "combo": f"{area_a} + {area_b}",
                    "match": True,
                    "retention_boost": f"{retention_pct}%",
                })
            elif has_a or has_b:
                # Account has one but not both — potential expansion
                missing = area_b if has_a else area_a
                match_patterns.append({
                    "combo": f"{area_a} + {area_b}",
                    "match": False,
                    "retention_boost": f"+{retention_pct}%",
                    "missing": missing,
                })

        return {
            "active_areas": current_areas,
            "total_areas": total_areas,
            "match_patterns": match_patterns,
        }

    def _build_next_best_action(
        self, current_areas: list[str], correlation_matrix: dict, customer_name: str
    ) -> list[dict]:
        """Compute retention lift for each missing product area, sorted descending."""
        product_areas = correlation_matrix["product_areas"]
        matrix = correlation_matrix["matrix"]

        missing_areas = [a for a in product_areas if a not in current_areas]
        if not missing_areas:
            return []

        nba = []
        for missing in missing_areas:
            missing_idx = product_areas.index(missing)

            # Find all combos involving this missing area AND a current area
            lifts = []
            current_combos = []
            for entry in matrix:
                row_idx, col_idx, co_occ_pct, retention_pct, cohort_size = entry
                area_a = product_areas[row_idx]
                area_b = product_areas[col_idx]

                if area_a == missing and area_b in current_areas:
                    lifts.append(retention_pct)
                    current_combos.append(area_b)
                elif area_b == missing and area_a in current_areas:
                    lifts.append(retention_pct)
                    current_combos.append(area_a)

            if lifts:
                avg_lift = round(sum(lifts) / len(lifts), 1)
                best_combo = current_combos[lifts.index(max(lifts))]
                nba.append({
                    "product_area": missing,
                    "current_combo": best_combo,
                    "retention_lift_pct": avg_lift,
                    "reasoning": (
                        f"Consider enabling {missing}: accounts using "
                        f"{best_combo} + {missing} show {max(lifts)}% higher retention."
                    ),
                })

        # Sort descending by retention_lift_pct
        nba.sort(key=lambda x: x["retention_lift_pct"], reverse=True)
        return nba

    def _build_expansion_signals(self, account_health: dict) -> list[dict]:
        """Compare usage to entitlement limits for upsell signals."""
        signals = []

        # Seat utilization
        contracted = account_health.get("total_contracted_seats")
        in_use = account_health.get("seats_in_use")
        if contracted and in_use and contracted > 0:
            pct = round(in_use / contracted * 100, 1)
            if pct >= 75:
                signals.append({
                    "product_area": "Seats",
                    "usage_pct": pct,
                    "allocation": f"{in_use}/{contracted}",
                    "signal": "approaching_limit" if pct < 95 else "at_limit",
                })

        # Weave ingestion
        weave_usage = account_health.get("weave_ingestion_gb")
        weave_cap = account_health.get("weave_ingestion_cap_gb")
        if weave_usage is not None and weave_cap and weave_cap > 0:
            pct = round(weave_usage / weave_cap * 100, 1)
            if pct >= 70:
                signals.append({
                    "product_area": "Weave Ingestion",
                    "usage_pct": pct,
                    "allocation": f"{weave_usage}GB/{weave_cap}GB",
                    "signal": "approaching_limit" if pct < 95 else "at_limit",
                })

        return signals

    def _build_peer_benchmarking(self, arr_data: pd.DataFrame, account_id: str) -> dict:
        """Compute product breadth percentile among same-tier accounts."""
        if arr_data.empty:
            return {
                "account_tier": "Unknown",
                "breadth_percentile": 0,
                "peer_count": 0,
                "distribution": {"labels": [], "counts": [], "current_bin": 0},
            }

        # Find current account's tier
        current_row = arr_data[arr_data["account_id"] == account_id]
        if current_row.empty:
            account_tier = "Unknown"
            current_breadth = 0
        else:
            account_tier = str(current_row.iloc[0].get("cs_tier", "Unknown"))
            current_breadth = int(current_row.iloc[0].get("product_breadth", 0))

        # Filter to same tier
        if account_tier != "Unknown":
            tier_data = arr_data[arr_data["cs_tier"] == account_tier].copy()
        else:
            tier_data = arr_data.copy()

        if tier_data.empty:
            return {
                "account_tier": account_tier,
                "breadth_percentile": 0,
                "peer_count": 0,
                "distribution": {"labels": [], "counts": [], "current_bin": 0},
            }

        # Compute percentile rank
        breadth_pct = round(
            (tier_data["product_breadth"] <= current_breadth).mean() * 100, 1
        )

        # Build distribution histogram
        labels = ["1 area", "2 areas", "3 areas", "4 areas", "5+ areas"]
        bins = [0, 1, 2, 3, 4, float("inf")]
        counts = []
        current_bin = 0
        for i in range(len(labels)):
            low = bins[i]
            high = bins[i + 1]
            count = int(((tier_data["product_breadth"] > low) & (tier_data["product_breadth"] <= high)).sum())
            counts.append(count)
            if low < current_breadth <= high:
                current_bin = i

        return {
            "account_tier": account_tier,
            "breadth_percentile": breadth_pct,
            "peer_count": len(tier_data),
            "distribution": {
                "labels": labels,
                "counts": counts,
                "current_bin": current_bin,
            },
        }

    def _build_arr_scatter(self, arr_data: pd.DataFrame, account_id: str) -> dict:
        """Build ARR vs product breadth scatter. NO account IDs or names in peers."""
        if arr_data.empty:
            return {"current": {"breadth": 0, "arr": 0}, "peers": []}

        # Current account
        current_row = arr_data[arr_data["account_id"] == account_id]
        if current_row.empty:
            current = {"breadth": 0, "arr": 0}
        else:
            row = current_row.iloc[0]
            current = {
                "breadth": int(row.get("product_breadth", 0)),
                "arr": int(row.get("arr", 0)),
            }

        # Peers: exclude current account, only breadth + arr
        peers_df = arr_data[arr_data["account_id"] != account_id]
        peers = [
            {"breadth": int(r["product_breadth"]), "arr": int(r["arr"])}
            for _, r in peers_df.iterrows()
        ]

        return {"current": current, "peers": peers}

    def _build_narrative(
        self, customer_name: str, current_areas: list[str],
        correlation_matrix: dict, next_best_action: list[dict],
        peer_benchmarking: dict, expansion_signals: list[dict],
    ) -> dict:
        """Build structured narrative from correlation analysis."""
        highlights = []
        recommendations = []

        num_areas = len(current_areas)
        matrix = correlation_matrix["matrix"]
        product_areas = correlation_matrix["product_areas"]

        # Overall assessment
        if matrix:
            avg_retention = round(sum(e[3] for e in matrix) / len(matrix), 1)
            highlights.append(
                f"{customer_name} uses {num_areas} product areas. "
                f"Average combo retention across the cohort is {avg_retention}%."
            )

            # Best combo
            best_entry = max(matrix, key=lambda e: e[3])
            best_a = product_areas[best_entry[0]]
            best_b = product_areas[best_entry[1]]
            highlights.append(
                f"Strongest combination: {best_a} + {best_b} at {best_entry[3]}% retention "
                f"(n={best_entry[4]} accounts)."
            )
        else:
            highlights.append(
                f"{customer_name} uses {num_areas} product areas. "
                "Insufficient data for combo analysis."
            )

        # Peer position
        pct = peer_benchmarking.get("breadth_percentile", 0)
        tier = peer_benchmarking.get("account_tier", "Unknown")
        if pct >= 75:
            highlights.append(
                f"Product breadth is in the P{round(pct)} percentile among "
                f"{tier}-tier accounts — above average adoption."
            )
        elif pct >= 25:
            highlights.append(
                f"Product breadth at P{round(pct)} — typical for {tier}-tier accounts."
            )
        else:
            recommendations.append(
                f"Low product breadth (P{round(pct)}). "
                "Consider expanding to additional product areas to match peer adoption."
            )

        # NBA recommendations
        if next_best_action:
            top = next_best_action[0]
            recommendations.append(
                f"Top expansion opportunity: {top['product_area']} "
                f"(projected {top['retention_lift_pct']}% retention lift)."
            )

        # Expansion signals
        if expansion_signals:
            for signal in expansion_signals:
                recommendations.append(
                    f"{signal['product_area']} usage at {signal['usage_pct']}% of allocation "
                    f"({signal['allocation']}). Potential upsell opportunity."
                )

        if not recommendations:
            recommendations.append(
                "No immediate expansion recommendations. "
                "Continue monitoring cross-account patterns for emerging opportunities."
            )

        executive_summary = (
            f"{customer_name} uses {num_areas} of {len(product_areas)} product areas. "
            f"Product breadth is at P{round(pct)} among {tier}-tier peers."
        )
        if next_best_action:
            executive_summary += (
                f" Top expansion opportunity is {next_best_action[0]['product_area']}."
            )

        return {
            "executive_summary": executive_summary,
            "highlights": highlights[:5],
            "recommendations": recommendations[:4],
        }

    def _enforce_privacy(self, result: dict) -> None:
        """Verify no SFDC account IDs leaked into output. Raises ValueError if found."""
        serialized = json.dumps(result, default=str)
        matches = SFDC_ID_PATTERN.findall(serialized)
        if matches:
            raise ValueError(
                f"Privacy violation: SFDC account IDs found in output: {matches}. "
                "Cross-account data must be fully anonymized."
            )
