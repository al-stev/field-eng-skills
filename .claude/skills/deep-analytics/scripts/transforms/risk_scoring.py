"""Risk Scoring transform -- composite churn risk from engagement, utilization, churn model."""

from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd

from transforms.base import BaseTransform
from common.data_utils import safe_value, format_date


# ---------------------------------------------------------------------------
# Module-level constants (per research: Pitfall 4 asymmetric weighting)
# ---------------------------------------------------------------------------

RISK_WEIGHTS = {
    "churn_model": 0.40,
    "engagement_trend": 0.25,
    "seat_utilization": 0.20,
    "support_velocity": 0.15,
}

CRITICAL_THRESHOLDS = {
    "churn_model": 0.80,        # ML churn probability > 80%
    "engagement_trend": -30,    # Engagement dropped >30% in 3 months
    "seat_utilization": 0.20,   # <20% seat utilization
}


# ---------------------------------------------------------------------------
# Pure function for composite risk computation (testable independently)
# ---------------------------------------------------------------------------

def compute_composite_risk(
    churn_probability: float | None,
    engagement_trend_pct: float,
    seat_utilization_pct: float,
    support_ticket_count_90d: int,
) -> dict:
    """
    Compute weighted composite risk score from 4 factors.

    Each factor is normalized to 0-100 (higher = riskier), then weighted.
    When churn_probability is None, weights are redistributed among remaining factors.
    Veto rule: if churn_probability > 0.80, score is floored at 70.

    Returns:
        Dict with score, factors, veto_applied, churn_model_available.
    """
    # Normalize each factor to 0-100 (higher = riskier)
    if churn_probability is not None:
        churn_normalized = min(100, churn_probability * 100)
    else:
        churn_normalized = None

    engagement_normalized = min(100, max(0, 50 - engagement_trend_pct))
    utilization_normalized = min(100, max(0, 100 - seat_utilization_pct * 100))
    support_normalized = min(100, support_ticket_count_90d * 10)

    # Build factors dict
    factors = {
        "churn_model": {
            "raw": churn_probability,
            "normalized": round(churn_normalized, 1) if churn_normalized is not None else None,
            "weight": RISK_WEIGHTS["churn_model"],
            "contribution": 0.0,
        },
        "engagement_trend": {
            "raw": engagement_trend_pct,
            "normalized": round(engagement_normalized, 1),
            "weight": RISK_WEIGHTS["engagement_trend"],
            "contribution": 0.0,
        },
        "seat_utilization": {
            "raw": seat_utilization_pct,
            "normalized": round(utilization_normalized, 1),
            "weight": RISK_WEIGHTS["seat_utilization"],
            "contribution": 0.0,
        },
        "support_velocity": {
            "raw": support_ticket_count_90d,
            "normalized": round(support_normalized, 1),
            "weight": RISK_WEIGHTS["support_velocity"],
            "contribution": 0.0,
        },
    }

    # Determine active factors and redistribute weights if churn model unavailable
    churn_model_available = churn_probability is not None
    if not churn_model_available:
        # Redistribute churn_model weight proportionally among remaining factors
        remaining = {k: v for k, v in RISK_WEIGHTS.items() if k != "churn_model"}
        remaining_sum = sum(remaining.values())
        for k in remaining:
            factors[k]["weight"] = remaining[k] / remaining_sum
        factors["churn_model"]["weight"] = 0.0
    else:
        # Reset weights to defaults (already set above)
        pass

    # Compute weighted score
    score = 0.0
    for name, f in factors.items():
        if f["normalized"] is not None and f["weight"] > 0:
            contribution = f["normalized"] * f["weight"]
            f["contribution"] = round(contribution, 2)
            score += contribution

    score = round(score, 1)

    # Veto rule: if churn_probability exceeds critical threshold, floor score at 70
    veto_applied = False
    if churn_model_available and churn_probability > CRITICAL_THRESHOLDS["churn_model"]:
        veto_applied = True
        score = max(score, 70.0)

    return {
        "score": score,
        "factors": factors,
        "veto_applied": veto_applied,
        "churn_model_available": churn_model_available,
    }


# ---------------------------------------------------------------------------
# Transform class
# ---------------------------------------------------------------------------

class RiskScoringTransform(BaseTransform):
    """
    Transforms engagement, health, seats, and tickets data into Risk Scoring PAGE_DATA.

    Computes composite risk score, factor breakdown, trend, renewal context,
    radar with historical comparison, and AI narrative with recommendations.
    """

    def transform(
        self,
        engagement: pd.DataFrame,
        health: pd.DataFrame,
        seats: pd.DataFrame = None,
        tickets: pd.DataFrame = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if engagement.empty and health.empty:
            return self.empty_result("no_data")

        customer_name = kwargs.get("customer_name", "Unknown")

        # ---- Extract risk inputs from DataFrames ----

        # Churn probability from health
        churn_probability = None
        churn_model_stale = False
        churn_model_age_days = 0
        if not health.empty and "churn_probability_3mo" in health.columns:
            raw_val = health.iloc[0].get("churn_probability_3mo")
            churn_probability = safe_value(raw_val)
            if churn_probability is not None:
                churn_probability = float(churn_probability)

        # Churn model staleness detection
        if churn_probability is not None and not health.empty and "inference_timestamp" in health.columns:
            ts_val = health.iloc[0].get("inference_timestamp")
            ts_val = safe_value(ts_val)
            if ts_val is not None:
                if isinstance(ts_val, datetime):
                    inference_dt = ts_val
                elif isinstance(ts_val, date):
                    inference_dt = datetime.combine(ts_val, datetime.min.time())
                else:
                    try:
                        inference_dt = pd.Timestamp(ts_val).to_pydatetime()
                    except Exception:
                        inference_dt = None

                if inference_dt is not None:
                    now = datetime.now()
                    age = (now - inference_dt).days
                    churn_model_age_days = age
                    if age > 30:
                        churn_model_stale = True

        # Engagement trend: % change from first to last month
        engagement_trend_pct = 0.0
        if not engagement.empty and "avg_engagement_score" in engagement.columns:
            sorted_eng = engagement.sort_values("month")
            scores = sorted_eng["avg_engagement_score"].dropna().tolist()
            if len(scores) >= 2 and scores[0] > 0:
                engagement_trend_pct = round(((scores[-1] - scores[0]) / scores[0]) * 100, 1)

        # Seat utilization from health
        seat_utilization_pct = 0.5  # default
        contracted = 0
        active = 0
        if not health.empty:
            contracted = safe_value(health.iloc[0].get("total_contracted_seats"), 0)
            active = safe_value(health.iloc[0].get("total_active_seats"), 0)
            if contracted and int(contracted) > 0:
                contracted = int(contracted)
                active = int(active) if active else 0
                seat_utilization_pct = active / contracted

        # Support tickets
        support_ticket_count = 0
        if tickets is not None and not tickets.empty and "ticket_count_90d" in tickets.columns:
            raw_count = tickets.iloc[0].get("ticket_count_90d", 0)
            support_ticket_count = int(safe_value(raw_count, 0))

        # ---- Compute composite risk ----
        risk_result = compute_composite_risk(
            churn_probability=churn_probability,
            engagement_trend_pct=engagement_trend_pct,
            seat_utilization_pct=seat_utilization_pct,
            support_ticket_count_90d=support_ticket_count,
        )

        score = risk_result["score"]
        # Determine tier
        if score <= 30:
            tier = "low"
        elif score <= 60:
            tier = "medium"
        else:
            tier = "high"

        risk = {
            "score": score,
            "tier": tier,
            "veto_applied": risk_result["veto_applied"],
            "churn_model_available": risk_result["churn_model_available"],
            "churn_model_stale": churn_model_stale,
            "churn_model_age_days": churn_model_age_days,
            "factors": risk_result["factors"],
        }

        # ---- Risk trend (RISK-03) ----
        risk_trend = self._compute_risk_trend(
            engagement, seats, churn_probability, support_ticket_count
        )

        # ---- Renewal context (RISK-04) ----
        renewal_context = self._compute_renewal_context(health, active, contracted, seat_utilization_pct)

        # ---- Risk radar (RISK-06, RISK-08) ----
        risk_radar = self._compute_risk_radar(
            risk_result, engagement, seats, support_ticket_count, churn_probability
        )

        # ---- KPIs ----
        days_to_renewal = renewal_context.get("days_to_renewal", "N/A")
        arr_val = renewal_context.get("arr", 0)
        arr_display = f"${arr_val // 1000}K" if isinstance(arr_val, (int, float)) and arr_val > 0 else "N/A"

        kpis = [
            {"value": str(round(score)), "label": "Risk Score"},
            {"value": tier.upper(), "label": "Risk Tier"},
            {"value": f"{days_to_renewal} days" if isinstance(days_to_renewal, int) else str(days_to_renewal), "label": "To Renewal"},
            {"value": arr_display, "label": "ARR"},
        ]

        # ---- Narrative ----
        narrative = self._build_narrative(
            customer_name, risk, risk_result["factors"],
            engagement_trend_pct, seat_utilization_pct, support_ticket_count,
            renewal_context, tier,
        )

        # ---- Data source ----
        if risk_result["churn_model_available"]:
            data_source = "renewal_predictions + engagement_score + seat_utilization"
        else:
            data_source = "engagement_score + seat_utilization (behavioral only)"

        return {
            "available": True,
            "reason": None,
            "customer": customer_name,
            "generated": date.today().isoformat(),
            "period": {"start": risk_trend["months"][0] if risk_trend["months"] else None,
                       "end": risk_trend["months"][-1] if risk_trend["months"] else None},
            "page_type": "risk-scoring",
            "kpis": kpis,
            "risk": risk,
            "risk_trend": risk_trend,
            "renewal_context": renewal_context,
            "risk_radar": risk_radar,
            "narrative": narrative,
            "data_source": data_source,
        }

    def _compute_risk_trend(
        self,
        engagement: pd.DataFrame,
        seats: pd.DataFrame | None,
        churn_probability: float | None,
        support_ticket_count: int,
    ) -> dict:
        """Compute monthly risk score proxy over 6 months (RISK-03)."""
        months = []
        scores = []
        tiers = []

        if engagement.empty or "avg_engagement_score" not in engagement.columns:
            return {"months": [], "scores": [], "tiers": []}

        sorted_eng = engagement.sort_values("month")
        eng_scores = sorted_eng["avg_engagement_score"].tolist()
        eng_months = sorted_eng["month"].tolist()

        # Build monthly seat utilization map
        seat_util_map = {}
        if seats is not None and not seats.empty and "active_seats" in seats.columns and "contracted_seats" in seats.columns:
            for _, row in seats.iterrows():
                d = row.get("date_day")
                if d is not None:
                    m = pd.Timestamp(d).strftime("%Y-%m")
                    contracted = safe_value(row.get("contracted_seats"), 0)
                    active = safe_value(row.get("active_seats"), 0)
                    if contracted and int(contracted) > 0:
                        seat_util_map[m] = int(active) / int(contracted)

        first_score = eng_scores[0] if eng_scores and eng_scores[0] and eng_scores[0] > 0 else 50

        for i, month in enumerate(eng_months):
            # Engagement trend at this point relative to first month
            if first_score > 0 and eng_scores[i] is not None:
                trend_pct = ((eng_scores[i] - first_score) / first_score) * 100
            else:
                trend_pct = 0.0

            # Seat utilization for this month (or default 0.5)
            util = seat_util_map.get(month, 0.5)

            # Recompute composite at this month
            monthly_risk = compute_composite_risk(
                churn_probability=churn_probability,
                engagement_trend_pct=trend_pct,
                seat_utilization_pct=util,
                support_ticket_count_90d=support_ticket_count,
            )

            ms = monthly_risk["score"]
            if ms <= 30:
                mt = "low"
            elif ms <= 60:
                mt = "medium"
            else:
                mt = "high"

            months.append(month)
            scores.append(round(ms, 1))
            tiers.append(mt)

        return {"months": months, "scores": scores, "tiers": tiers}

    def _compute_renewal_context(
        self,
        health: pd.DataFrame,
        active_seats: int,
        contracted_seats: int,
        seat_utilization_pct: float,
    ) -> dict:
        """Extract renewal context from health data (RISK-04)."""
        if health.empty:
            return {
                "days_to_renewal": "N/A",
                "contract_end": None,
                "arr": 0,
                "contracted_seats": contracted_seats,
                "active_seats": active_seats,
                "seat_utilization": round(seat_utilization_pct * 100, 1),
            }

        row = health.iloc[0]
        renewal_date = safe_value(row.get("renewal_date"))
        arr = safe_value(row.get("arr"), 0)

        if renewal_date is not None:
            if isinstance(renewal_date, str):
                try:
                    renewal_date = date.fromisoformat(renewal_date)
                except ValueError:
                    renewal_date = None
            elif isinstance(renewal_date, datetime):
                renewal_date = renewal_date.date()

        days_to_renewal = "N/A"
        contract_end = None
        if renewal_date is not None and isinstance(renewal_date, date):
            days_to_renewal = (renewal_date - date.today()).days
            contract_end = renewal_date.isoformat()

        return {
            "days_to_renewal": days_to_renewal,
            "contract_end": contract_end,
            "arr": int(arr) if arr else 0,
            "contracted_seats": contracted_seats,
            "active_seats": active_seats,
            "seat_utilization": round(seat_utilization_pct * 100, 1),
        }

    def _compute_risk_radar(
        self,
        risk_result: dict,
        engagement: pd.DataFrame,
        seats: pd.DataFrame | None,
        support_ticket_count: int,
        churn_probability: float | None,
    ) -> dict:
        """Compute radar data with current + historical overlays (RISK-06, RISK-08)."""
        indicators = ["Churn Model", "Engagement", "Utilization", "Support", "Trend"]
        factors = risk_result["factors"]

        # Current values
        churn_norm = factors["churn_model"]["normalized"] if factors["churn_model"]["normalized"] is not None else 0
        eng_norm = factors["engagement_trend"]["normalized"]
        util_norm = factors["seat_utilization"]["normalized"]
        supp_norm = factors["support_velocity"]["normalized"]
        # Trend: use the overall score as a trend proxy
        trend_norm = min(100, max(0, risk_result["score"]))

        current = [round(churn_norm, 1), round(eng_norm, 1), round(util_norm, 1),
                    round(supp_norm, 1), round(trend_norm, 1)]

        # Historical 3mo ago
        historical_3mo = self._compute_historical_radar(
            engagement, seats, support_ticket_count, churn_probability, offset_months=3
        )

        # Historical 6mo ago
        historical_6mo = self._compute_historical_radar(
            engagement, seats, support_ticket_count, churn_probability, offset_months=6
        )

        return {
            "indicators": indicators,
            "current": current,
            "historical_3mo": historical_3mo,
            "historical_6mo": historical_6mo,
        }

    def _compute_historical_radar(
        self,
        engagement: pd.DataFrame,
        seats: pd.DataFrame | None,
        support_ticket_count: int,
        churn_probability: float | None,
        offset_months: int,
    ) -> list | None:
        """Compute radar values at a historical point."""
        if engagement.empty or "avg_engagement_score" not in engagement.columns:
            return None

        sorted_eng = engagement.sort_values("month")
        eng_scores = sorted_eng["avg_engagement_score"].tolist()

        # offset_months from the end: index = len - offset_months
        idx = len(eng_scores) - offset_months
        if idx < 0 or idx >= len(eng_scores):
            return None

        first_score = eng_scores[0] if eng_scores[0] and eng_scores[0] > 0 else 50
        hist_score = eng_scores[idx]
        if first_score > 0 and hist_score is not None:
            hist_trend = ((hist_score - first_score) / first_score) * 100
        else:
            hist_trend = 0.0

        eng_norm = min(100, max(0, 50 - hist_trend))
        churn_norm = min(100, churn_probability * 100) if churn_probability is not None else 0
        util_norm = 50  # Default for historical (no per-month seat data granularity guaranteed)
        supp_norm = min(100, support_ticket_count * 10)

        # Recompute a risk proxy score for trend dimension
        hist_risk = compute_composite_risk(
            churn_probability=churn_probability,
            engagement_trend_pct=hist_trend,
            seat_utilization_pct=0.5,
            support_ticket_count_90d=support_ticket_count,
        )
        trend_norm = min(100, max(0, hist_risk["score"]))

        return [round(churn_norm, 1), round(eng_norm, 1), round(util_norm, 1),
                round(supp_norm, 1), round(trend_norm, 1)]

    def _build_narrative(
        self,
        customer_name: str,
        risk: dict,
        factors: dict,
        engagement_trend_pct: float,
        seat_utilization_pct: float,
        support_ticket_count: int,
        renewal_context: dict,
        tier: str,
    ) -> dict:
        """Build structured risk narrative with recommendations (RISK-05, RISK-07)."""
        score = risk["score"]
        highlights = []
        recommendations = []

        # Executive summary
        tier_desc = {"low": "healthy", "medium": "moderate", "high": "elevated"}
        churn_clause = ""
        if risk["churn_model_available"]:
            churn_val = factors["churn_model"]["raw"]
            churn_clause = f" ML churn probability is {churn_val:.0%}."
        else:
            churn_clause = " ML churn model data is unavailable; score is behavioral-only."

        days = renewal_context.get("days_to_renewal", "N/A")
        renewal_clause = f" Renewal is in {days} days." if isinstance(days, int) else ""

        executive_summary = (
            f"{customer_name} has a {tier_desc.get(tier, tier)} risk posture "
            f"with a composite score of {round(score)}/100.{churn_clause}{renewal_clause}"
        )

        # Highlights: identify elevated factors
        for name, f in factors.items():
            if f["normalized"] is not None and f["normalized"] > 60:
                label = name.replace("_", " ").title()
                highlights.append(
                    f"{label} is elevated at {f['normalized']}/100 "
                    f"(raw: {f['raw']}, weight: {f['weight']:.0%})."
                )

        if risk["churn_model_stale"]:
            highlights.append(
                f"Churn model data is {risk['churn_model_age_days']} days old -- "
                f"interpret ML-based risk factors with caution."
            )

        if risk["veto_applied"]:
            highlights.append(
                "Critical threshold exceeded: churn probability triggered automatic "
                "high-risk floor (score floored at 70)."
            )

        if not risk["churn_model_available"]:
            highlights.append(
                "Risk score excludes ML churn model. Behavioral signals only: "
                "engagement trend, seat utilization, support velocity."
            )

        if engagement_trend_pct < -10:
            highlights.append(
                f"Engagement declining at {engagement_trend_pct:.1f}% over 6 months."
            )

        if not highlights:
            highlights.append("All risk factors are within normal ranges.")

        # Recommendations based on risk profile
        if tier == "high":
            recommendations.append(
                "Schedule executive QBR within 2 weeks to address risk signals."
            )
        if factors["engagement_trend"]["normalized"] is not None and factors["engagement_trend"]["normalized"] > 50:
            recommendations.append(
                "Run targeted enablement workshop to reverse engagement decline."
            )
        if factors["seat_utilization"]["normalized"] is not None and factors["seat_utilization"]["normalized"] > 60:
            recommendations.append(
                f"Seat utilization is {seat_utilization_pct:.0%} -- "
                f"identify adoption blockers and run onboarding for inactive seats."
            )
        if support_ticket_count > 3:
            recommendations.append(
                "Review support ticket backlog with account team -- "
                f"{support_ticket_count} tickets in 90 days is above average."
            )
        if isinstance(days, int) and days < 90:
            recommendations.append(
                f"Renewal in {days} days -- initiate renewal prep and stakeholder alignment."
            )

        if not recommendations:
            recommendations.append(
                "Risk profile is healthy. Continue regular cadence and monitor for changes."
            )

        return {
            "executive_summary": executive_summary,
            "highlights": highlights[:5],
            "recommendations": recommendations[:5],
        }
