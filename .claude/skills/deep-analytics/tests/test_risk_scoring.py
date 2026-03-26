"""Tests for RiskScoringTransform and compute_composite_risk."""

import pandas as pd
import pytest
from datetime import date, datetime, timedelta

from transforms.risk_scoring import (
    RiskScoringTransform,
    compute_composite_risk,
    RISK_WEIGHTS,
    CRITICAL_THRESHOLDS,
)


# ---------------------------------------------------------------------------
# compute_composite_risk() unit tests (pure function)
# ---------------------------------------------------------------------------

class TestCompositeRiskAllFactors:
    """Test compute_composite_risk() with all 4 factors present."""

    def test_returns_score_between_0_and_100(self):
        result = compute_composite_risk(
            churn_probability=0.5,
            engagement_trend_pct=0.0,
            seat_utilization_pct=0.5,
            support_ticket_count_90d=3,
        )
        assert 0 <= result["score"] <= 100

    def test_returns_factors_dict_with_four_entries(self):
        result = compute_composite_risk(
            churn_probability=0.5,
            engagement_trend_pct=0.0,
            seat_utilization_pct=0.5,
            support_ticket_count_90d=3,
        )
        assert len(result["factors"]) == 4

    def test_returns_weights_summing_to_one(self):
        result = compute_composite_risk(
            churn_probability=0.5,
            engagement_trend_pct=0.0,
            seat_utilization_pct=0.5,
            support_ticket_count_90d=3,
        )
        total = sum(f["weight"] for f in result["factors"].values())
        assert abs(total - 1.0) < 0.01

    def test_churn_model_available_true(self):
        result = compute_composite_risk(
            churn_probability=0.5,
            engagement_trend_pct=0.0,
            seat_utilization_pct=0.5,
            support_ticket_count_90d=3,
        )
        assert result["churn_model_available"] is True

    def test_veto_not_applied_for_moderate_churn(self):
        result = compute_composite_risk(
            churn_probability=0.5,
            engagement_trend_pct=0.0,
            seat_utilization_pct=0.5,
            support_ticket_count_90d=3,
        )
        assert result["veto_applied"] is False


class TestCompositeRiskNoChurnModel:
    """Test compute_composite_risk() when churn_probability is None."""

    def test_redistributes_weights_among_three_factors(self):
        result = compute_composite_risk(
            churn_probability=None,
            engagement_trend_pct=-10.0,
            seat_utilization_pct=0.5,
            support_ticket_count_90d=5,
        )
        total = sum(f["weight"] for f in result["factors"].values() if f["normalized"] is not None)
        assert abs(total - 1.0) < 0.01

    def test_churn_model_available_false(self):
        result = compute_composite_risk(
            churn_probability=None,
            engagement_trend_pct=-10.0,
            seat_utilization_pct=0.5,
            support_ticket_count_90d=5,
        )
        assert result["churn_model_available"] is False

    def test_score_still_in_range(self):
        result = compute_composite_risk(
            churn_probability=None,
            engagement_trend_pct=-10.0,
            seat_utilization_pct=0.5,
            support_ticket_count_90d=5,
        )
        assert 0 <= result["score"] <= 100


class TestCompositeRiskVetoRule:
    """Test veto rule when churn_probability exceeds critical threshold."""

    def test_veto_applied_true(self):
        result = compute_composite_risk(
            churn_probability=0.85,
            engagement_trend_pct=10.0,  # positive trend (low risk)
            seat_utilization_pct=0.90,  # high utilization (low risk)
            support_ticket_count_90d=0,  # no tickets (low risk)
        )
        assert result["veto_applied"] is True

    def test_score_at_least_70(self):
        result = compute_composite_risk(
            churn_probability=0.85,
            engagement_trend_pct=10.0,
            seat_utilization_pct=0.90,
            support_ticket_count_90d=0,
        )
        assert result["score"] >= 70


class TestCompositeRiskNormalization:
    """Test individual factor normalization rules."""

    def test_engagement_trend_minus15_normalized_to_65(self):
        result = compute_composite_risk(
            churn_probability=0.5,
            engagement_trend_pct=-15.0,
            seat_utilization_pct=0.5,
            support_ticket_count_90d=3,
        )
        assert result["factors"]["engagement_trend"]["normalized"] == 65

    def test_seat_utilization_35pct_normalized_to_65(self):
        result = compute_composite_risk(
            churn_probability=0.5,
            engagement_trend_pct=0.0,
            seat_utilization_pct=0.35,
            support_ticket_count_90d=3,
        )
        assert result["factors"]["seat_utilization"]["normalized"] == 65

    def test_support_tickets_7_normalized_to_70(self):
        result = compute_composite_risk(
            churn_probability=0.5,
            engagement_trend_pct=0.0,
            seat_utilization_pct=0.5,
            support_ticket_count_90d=7,
        )
        assert result["factors"]["support_velocity"]["normalized"] == 70


# ---------------------------------------------------------------------------
# RiskScoringTransform.transform() tests
# ---------------------------------------------------------------------------

@pytest.fixture
def transform():
    return RiskScoringTransform()


@pytest.fixture
def valid_engagement_df():
    """6 months of engagement data."""
    return pd.DataFrame({
        "month": ["2025-10", "2025-11", "2025-12", "2026-01", "2026-02", "2026-03"],
        "avg_engagement_score": [70.0, 68.0, 65.0, 60.0, 55.0, 50.0],
        "active_users": [100, 95, 90, 85, 80, 75],
    })


@pytest.fixture
def valid_health_df():
    """Account health with churn model data."""
    return pd.DataFrame({
        "renewal_date": [date(2026, 9, 15)],
        "arr": [250000],
        "cs_tier": ["Enterprise"],
        "churn_probability_3mo": [0.35],
        "churn_probability_5mo": [0.45],
        "total_contracted_seats": [200],
        "total_active_seats": [80],
        "deployment_type": ["SaaS"],
        "weave_customer": [True],
    })


@pytest.fixture
def valid_seats_df():
    """Seat utilization data over 6 months."""
    months = ["2025-10", "2025-11", "2025-12", "2026-01", "2026-02", "2026-03"]
    return pd.DataFrame({
        "date_day": [date(2025, 10, 15), date(2025, 11, 15), date(2025, 12, 15),
                     date(2026, 1, 15), date(2026, 2, 15), date(2026, 3, 15)],
        "active_seats": [90, 85, 80, 75, 80, 80],
        "claimed_seats": [150, 150, 150, 150, 150, 150],
        "contracted_seats": [200, 200, 200, 200, 200, 200],
    })


@pytest.fixture
def valid_tickets_df():
    """Support ticket count."""
    return pd.DataFrame({
        "ticket_count_90d": [5],
    })


class TestTransformValidData:
    """Test transform() with valid data for all inputs."""

    def test_returns_available_true(self, transform, valid_engagement_df, valid_health_df, valid_seats_df, valid_tickets_df):
        result = transform.transform(
            engagement=valid_engagement_df, health=valid_health_df,
            seats=valid_seats_df, tickets=valid_tickets_df,
            customer_name="TestCorp",
        )
        assert result["available"] is True

    def test_returns_correct_page_type(self, transform, valid_engagement_df, valid_health_df, valid_seats_df, valid_tickets_df):
        result = transform.transform(
            engagement=valid_engagement_df, health=valid_health_df,
            seats=valid_seats_df, tickets=valid_tickets_df,
            customer_name="TestCorp",
        )
        assert result["page_type"] == "risk-scoring"

    def test_risk_dict_has_required_keys(self, transform, valid_engagement_df, valid_health_df, valid_seats_df, valid_tickets_df):
        result = transform.transform(
            engagement=valid_engagement_df, health=valid_health_df,
            seats=valid_seats_df, tickets=valid_tickets_df,
            customer_name="TestCorp",
        )
        risk = result["risk"]
        required_keys = {"score", "tier", "veto_applied", "churn_model_available",
                         "churn_model_stale", "churn_model_age_days", "factors"}
        assert required_keys.issubset(risk.keys()), f"Missing: {required_keys - risk.keys()}"

    def test_risk_tier_mapping(self, transform, valid_engagement_df, valid_health_df, valid_seats_df, valid_tickets_df):
        result = transform.transform(
            engagement=valid_engagement_df, health=valid_health_df,
            seats=valid_seats_df, tickets=valid_tickets_df,
            customer_name="TestCorp",
        )
        score = result["risk"]["score"]
        tier = result["risk"]["tier"]
        if score <= 30:
            assert tier == "low"
        elif score <= 60:
            assert tier == "medium"
        else:
            assert tier == "high"


class TestTransformRiskTierClassification:
    """Test risk tier classification boundaries."""

    def test_low_tier_for_low_score(self, transform, valid_seats_df, valid_tickets_df):
        """Low churn probability and positive engagement = low risk."""
        health = pd.DataFrame({
            "renewal_date": [date(2027, 12, 15)],
            "arr": [500000],
            "churn_probability_3mo": [0.05],
            "total_contracted_seats": [200],
            "total_active_seats": [180],
            "deployment_type": ["SaaS"],
        })
        engagement = pd.DataFrame({
            "month": ["2025-10", "2025-11", "2025-12", "2026-01", "2026-02", "2026-03"],
            "avg_engagement_score": [80.0, 82.0, 85.0, 87.0, 90.0, 92.0],
            "active_users": [170, 172, 175, 178, 180, 182],
        })
        result = transform.transform(
            engagement=engagement, health=health,
            seats=valid_seats_df, tickets=valid_tickets_df,
            customer_name="HealthyCorp",
        )
        assert result["risk"]["tier"] == "low"


class TestTransformRiskTrend:
    """Test risk_trend output (RISK-03)."""

    def test_risk_trend_has_required_keys(self, transform, valid_engagement_df, valid_health_df, valid_seats_df, valid_tickets_df):
        result = transform.transform(
            engagement=valid_engagement_df, health=valid_health_df,
            seats=valid_seats_df, tickets=valid_tickets_df,
            customer_name="TestCorp",
        )
        trend = result["risk_trend"]
        assert "months" in trend
        assert "scores" in trend

    def test_risk_trend_has_six_entries(self, transform, valid_engagement_df, valid_health_df, valid_seats_df, valid_tickets_df):
        result = transform.transform(
            engagement=valid_engagement_df, health=valid_health_df,
            seats=valid_seats_df, tickets=valid_tickets_df,
            customer_name="TestCorp",
        )
        trend = result["risk_trend"]
        assert len(trend["months"]) == 6
        assert len(trend["scores"]) == 6


class TestTransformRenewalContext:
    """Test renewal_context output (RISK-04)."""

    def test_renewal_context_has_required_keys(self, transform, valid_engagement_df, valid_health_df, valid_seats_df, valid_tickets_df):
        result = transform.transform(
            engagement=valid_engagement_df, health=valid_health_df,
            seats=valid_seats_df, tickets=valid_tickets_df,
            customer_name="TestCorp",
        )
        rc = result["renewal_context"]
        required = {"days_to_renewal", "contract_end", "arr", "contracted_seats",
                     "active_seats", "seat_utilization"}
        assert required.issubset(rc.keys()), f"Missing: {required - rc.keys()}"


class TestTransformRiskRadar:
    """Test risk_radar output (RISK-06, RISK-08)."""

    def test_radar_has_required_keys(self, transform, valid_engagement_df, valid_health_df, valid_seats_df, valid_tickets_df):
        result = transform.transform(
            engagement=valid_engagement_df, health=valid_health_df,
            seats=valid_seats_df, tickets=valid_tickets_df,
            customer_name="TestCorp",
        )
        radar = result["risk_radar"]
        required = {"indicators", "current", "historical_3mo", "historical_6mo"}
        assert required.issubset(radar.keys())

    def test_radar_values_are_0_to_100(self, transform, valid_engagement_df, valid_health_df, valid_seats_df, valid_tickets_df):
        result = transform.transform(
            engagement=valid_engagement_df, health=valid_health_df,
            seats=valid_seats_df, tickets=valid_tickets_df,
            customer_name="TestCorp",
        )
        radar = result["risk_radar"]
        for val in radar["current"]:
            assert 0 <= val <= 100


class TestTransformChurnModelStaleness:
    """Test churn model staleness detection."""

    def test_stale_churn_model_detected(self, transform, valid_engagement_df, valid_seats_df, valid_tickets_df):
        """Health data with old inference_timestamp triggers stale flag."""
        health = pd.DataFrame({
            "renewal_date": [date(2026, 9, 15)],
            "arr": [250000],
            "churn_probability_3mo": [0.35],
            "total_contracted_seats": [200],
            "total_active_seats": [80],
            "deployment_type": ["SaaS"],
            "inference_timestamp": [datetime(2026, 1, 15)],  # ~70 days old
        })
        result = transform.transform(
            engagement=valid_engagement_df, health=health,
            seats=valid_seats_df, tickets=valid_tickets_df,
            customer_name="TestCorp",
        )
        assert result["risk"]["churn_model_stale"] is True
        assert result["risk"]["churn_model_age_days"] > 30


class TestTransformKPIs:
    """Test KPI output."""

    def test_kpis_has_four_entries(self, transform, valid_engagement_df, valid_health_df, valid_seats_df, valid_tickets_df):
        result = transform.transform(
            engagement=valid_engagement_df, health=valid_health_df,
            seats=valid_seats_df, tickets=valid_tickets_df,
            customer_name="TestCorp",
        )
        assert len(result["kpis"]) == 4

    def test_kpi_labels(self, transform, valid_engagement_df, valid_health_df, valid_seats_df, valid_tickets_df):
        result = transform.transform(
            engagement=valid_engagement_df, health=valid_health_df,
            seats=valid_seats_df, tickets=valid_tickets_df,
            customer_name="TestCorp",
        )
        labels = [k["label"] for k in result["kpis"]]
        assert labels == ["Risk Score", "Risk Tier", "To Renewal", "ARR"]


class TestTransformNarrative:
    """Test narrative output (RISK-05, RISK-07)."""

    def test_narrative_has_required_keys(self, transform, valid_engagement_df, valid_health_df, valid_seats_df, valid_tickets_df):
        result = transform.transform(
            engagement=valid_engagement_df, health=valid_health_df,
            seats=valid_seats_df, tickets=valid_tickets_df,
            customer_name="TestCorp",
        )
        narrative = result["narrative"]
        assert "executive_summary" in narrative
        assert "highlights" in narrative
        assert "recommendations" in narrative

    def test_recommendations_are_nonempty(self, transform, valid_engagement_df, valid_health_df, valid_seats_df, valid_tickets_df):
        result = transform.transform(
            engagement=valid_engagement_df, health=valid_health_df,
            seats=valid_seats_df, tickets=valid_tickets_df,
            customer_name="TestCorp",
        )
        assert len(result["narrative"]["recommendations"]) >= 1


class TestTransformEmptyInput:
    """Test transform() with empty engagement data."""

    def test_empty_engagement_returns_not_available(self, transform, valid_seats_df):
        empty_df = pd.DataFrame()
        empty_health = pd.DataFrame()
        result = transform.transform(
            engagement=empty_df, health=empty_health,
            seats=valid_seats_df,
            customer_name="TestCorp",
        )
        assert result["available"] is False
        assert result["reason"] == "no_data"


class TestRiskWeightsConstants:
    """Test module-level constants."""

    def test_weights_sum_to_one(self):
        assert abs(sum(RISK_WEIGHTS.values()) - 1.0) < 0.01

    def test_weights_has_four_entries(self):
        assert len(RISK_WEIGHTS) == 4

    def test_critical_thresholds_has_churn_model(self):
        assert CRITICAL_THRESHOLDS["churn_model"] == 0.80

    def test_critical_thresholds_has_engagement_trend(self):
        assert CRITICAL_THRESHOLDS["engagement_trend"] == -30

    def test_critical_thresholds_has_seat_utilization(self):
        assert CRITICAL_THRESHOLDS["seat_utilization"] == 0.20
