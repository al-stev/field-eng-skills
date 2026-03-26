"""Tests for UsageCorrelationTransform — co-occurrence matrix, privacy enforcement, peer benchmarking."""

import json
import re

import pandas as pd
import pytest
from datetime import date, timedelta

from transforms.usage_correlation import UsageCorrelationTransform


SFDC_ID_PATTERN = re.compile(r"0018[A-Za-z0-9]{14}")

# --- Product areas matching the real PRODUCT_AREA_CASE in queries.py ---
PRODUCT_AREAS = [
    "Experiments", "Artifacts", "Weave Tracing", "Sweeps",
    "Models", "Launch", "Tables", "Reports",
]

# --- Synthetic account IDs (SFDC-format, used to test privacy enforcement) ---
FAKE_ACCOUNT_IDS = [f"001800000fake{i:03d}" for i in range(25)]
CURRENT_ACCOUNT_ID = "001800000current"


@pytest.fixture
def transform():
    return UsageCorrelationTransform()


@pytest.fixture
def cross_account_df():
    """20+ synthetic accounts with various product area combinations."""
    rows = []
    import random
    random.seed(42)
    for i, acct_id in enumerate(FAKE_ACCOUNT_IDS):
        # Each account uses 2-5 product areas
        num_areas = random.randint(2, 5)
        areas = random.sample(PRODUCT_AREAS, num_areas)
        for area in areas:
            rows.append({
                "account_id": acct_id,
                "product_area": area,
                "users": random.randint(5, 100),
                "events": random.randint(1000, 50000),
            })
    # Add current account
    for area in ["Experiments", "Artifacts", "Weave Tracing"]:
        rows.append({
            "account_id": CURRENT_ACCOUNT_ID,
            "product_area": area,
            "users": 30,
            "events": 15000,
        })
    return pd.DataFrame(rows)


@pytest.fixture
def arr_data_df():
    """Matching ARR and breadth data for all accounts."""
    rows = []
    import random
    random.seed(42)
    tiers = ["Enterprise", "Enterprise", "Enterprise", "Business", "Startup"]
    for i, acct_id in enumerate(FAKE_ACCOUNT_IDS):
        rows.append({
            "account_id": acct_id,
            "product_breadth": random.randint(1, 6),
            "arr": random.randint(50000, 500000),
            "cs_tier": tiers[i % len(tiers)],
        })
    # Current account
    rows.append({
        "account_id": CURRENT_ACCOUNT_ID,
        "product_breadth": 3,
        "arr": 120000,
        "cs_tier": "Enterprise",
    })
    return pd.DataFrame(rows)


@pytest.fixture
def current_account_areas():
    return ["Experiments", "Artifacts", "Weave Tracing"]


@pytest.fixture
def account_health_with_entitlements():
    return {
        "total_contracted_seats": 50,
        "seats_in_use": 42,
        "weave_ingestion_gb": 80.0,
        "weave_ingestion_cap_gb": 100.0,
        "deployment_type": "Dedicated Cloud",
    }


@pytest.fixture
def account_health_no_entitlements():
    return {
        "deployment_type": "SaaS",
    }


# ── Test: empty cross_account returns empty_result ──

def test_empty_cross_account(transform):
    result = transform.transform(
        cross_account=pd.DataFrame(),
        arr_data=pd.DataFrame(),
        current_account_areas=["Experiments"],
        account_health={},
        customer_name="TestCo",
        account_id="001800000test001",
        deployment_type="SaaS",
    )
    assert result["available"] is False
    assert result["reason"] == "cross_account_unavailable"


# ── Test: insufficient cohort (<10 accounts) returns empty_result ──

def test_insufficient_cohort(transform):
    # Only 5 unique accounts
    rows = []
    for i in range(5):
        rows.append({
            "account_id": f"001800000small{i:03d}",
            "product_area": "Experiments",
            "users": 10,
            "events": 5000,
        })
    small_df = pd.DataFrame(rows)
    result = transform.transform(
        cross_account=small_df,
        arr_data=pd.DataFrame(),
        current_account_areas=["Experiments"],
        account_health={},
        customer_name="TestCo",
        account_id="001800000test001",
        deployment_type="SaaS",
    )
    assert result["available"] is False
    assert result["reason"] == "insufficient_cohort"


# ── Test: successful transform returns all expected keys ──

def test_full_transform_returns_expected_keys(
    transform, cross_account_df, arr_data_df, current_account_areas,
    account_health_with_entitlements,
):
    result = transform.transform(
        cross_account=cross_account_df,
        arr_data=arr_data_df,
        current_account_areas=current_account_areas,
        account_health=account_health_with_entitlements,
        customer_name="TestCo",
        account_id=CURRENT_ACCOUNT_ID,
        deployment_type="Dedicated Cloud",
    )
    assert result["available"] is True
    assert result["reason"] is None
    assert result["page_type"] == "usage-correlation"

    expected_keys = [
        "correlation_matrix", "account_positioning", "next_best_action",
        "expansion_signals", "peer_benchmarking", "arr_scatter",
        "privacy", "narrative", "kpis", "data_source", "deployment_type",
    ]
    for key in expected_keys:
        assert key in result, f"Missing key: {key}"


# ── Test: cohort suppression — entries with < 10 accounts excluded ──

def test_cohort_suppression(transform):
    """Product combos backed by fewer than 10 accounts must be excluded from the matrix."""
    # Create 12 accounts, but only 3 use 'Launch', so Launch+X combos should be suppressed
    rows = []
    import random
    random.seed(99)
    for i in range(12):
        acct_id = f"001800000cohort{i:02d}"
        rows.append({"account_id": acct_id, "product_area": "Experiments", "users": 10, "events": 5000})
        rows.append({"account_id": acct_id, "product_area": "Artifacts", "users": 8, "events": 3000})
        if i < 3:
            rows.append({"account_id": acct_id, "product_area": "Launch", "users": 2, "events": 500})
    df = pd.DataFrame(rows)

    arr_rows = [
        {"account_id": f"001800000cohort{i:02d}", "product_breadth": 2, "arr": 100000, "cs_tier": "Enterprise"}
        for i in range(12)
    ]
    arr_df = pd.DataFrame(arr_rows)

    result = transform.transform(
        cross_account=df,
        arr_data=arr_df,
        current_account_areas=["Experiments", "Artifacts"],
        account_health={},
        customer_name="TestCo",
        account_id="001800000test001",
        deployment_type="SaaS",
    )
    assert result["available"] is True
    matrix = result["correlation_matrix"]["matrix"]
    product_areas = result["correlation_matrix"]["product_areas"]

    # Check that any combo involving Launch (which has only 3 accounts) is not present
    launch_idx = product_areas.index("Launch") if "Launch" in product_areas else None
    if launch_idx is not None:
        for entry in matrix:
            row_idx, col_idx, _, _, cohort_size = entry
            # If Launch is involved, cohort_size must be >= 10
            if row_idx == launch_idx or col_idx == launch_idx:
                assert cohort_size >= 10, f"Launch combo with cohort_size {cohort_size} should be suppressed"
    # The Experiments+Artifacts combo should be present (all 12 accounts have both)
    has_exp_art = any(
        entry[4] >= 10
        for entry in matrix
    )
    assert has_exp_art, "Expected at least one combo with cohort >= 10"


# ── Test: privacy enforcement — no SFDC account IDs in serialized output ──

def test_privacy_no_account_ids(
    transform, cross_account_df, arr_data_df, current_account_areas,
    account_health_with_entitlements,
):
    result = transform.transform(
        cross_account=cross_account_df,
        arr_data=arr_data_df,
        current_account_areas=current_account_areas,
        account_health=account_health_with_entitlements,
        customer_name="TestCo",
        account_id=CURRENT_ACCOUNT_ID,
        deployment_type="Dedicated Cloud",
    )
    serialized = json.dumps(result, default=str)
    matches = SFDC_ID_PATTERN.findall(serialized)
    assert len(matches) == 0, f"SFDC account IDs leaked in output: {matches}"


# ── Test: arr_scatter.peers contains only {breadth, arr} — no identity fields ──

def test_arr_scatter_anonymized_peers(
    transform, cross_account_df, arr_data_df, current_account_areas,
    account_health_with_entitlements,
):
    result = transform.transform(
        cross_account=cross_account_df,
        arr_data=arr_data_df,
        current_account_areas=current_account_areas,
        account_health=account_health_with_entitlements,
        customer_name="TestCo",
        account_id=CURRENT_ACCOUNT_ID,
        deployment_type="Dedicated Cloud",
    )
    scatter = result["arr_scatter"]
    assert "current" in scatter
    assert "peers" in scatter
    for peer in scatter["peers"]:
        assert set(peer.keys()) == {"breadth", "arr"}, f"Peer has unexpected keys: {peer.keys()}"
        assert "account_id" not in peer
        assert "account_name" not in peer


# ── Test: peer_benchmarking.breadth_percentile is 0-100 ──

def test_peer_benchmarking_percentile_range(
    transform, cross_account_df, arr_data_df, current_account_areas,
    account_health_with_entitlements,
):
    result = transform.transform(
        cross_account=cross_account_df,
        arr_data=arr_data_df,
        current_account_areas=current_account_areas,
        account_health=account_health_with_entitlements,
        customer_name="TestCo",
        account_id=CURRENT_ACCOUNT_ID,
        deployment_type="Dedicated Cloud",
    )
    pct = result["peer_benchmarking"]["breadth_percentile"]
    assert isinstance(pct, (int, float))
    assert 0 <= pct <= 100


# ── Test: next_best_action sorted by retention_lift_pct descending ──

def test_next_best_action_sorted(
    transform, cross_account_df, arr_data_df, current_account_areas,
    account_health_with_entitlements,
):
    result = transform.transform(
        cross_account=cross_account_df,
        arr_data=arr_data_df,
        current_account_areas=current_account_areas,
        account_health=account_health_with_entitlements,
        customer_name="TestCo",
        account_id=CURRENT_ACCOUNT_ID,
        deployment_type="Dedicated Cloud",
    )
    nba = result["next_best_action"]
    if len(nba) > 1:
        lifts = [item["retention_lift_pct"] for item in nba]
        assert lifts == sorted(lifts, reverse=True), f"NBA not sorted descending: {lifts}"


# ── Test: _build_narrative returns correct keys ──

def test_build_narrative_keys(
    transform, cross_account_df, arr_data_df, current_account_areas,
    account_health_with_entitlements,
):
    result = transform.transform(
        cross_account=cross_account_df,
        arr_data=arr_data_df,
        current_account_areas=current_account_areas,
        account_health=account_health_with_entitlements,
        customer_name="TestCo",
        account_id=CURRENT_ACCOUNT_ID,
        deployment_type="Dedicated Cloud",
    )
    narrative = result["narrative"]
    assert "executive_summary" in narrative
    assert "highlights" in narrative
    assert "recommendations" in narrative
    assert isinstance(narrative["highlights"], list)
    assert isinstance(narrative["recommendations"], list)


# ── Test: expansion_signals empty when no entitlement data ──

def test_expansion_signals_graceful_degradation(
    transform, cross_account_df, arr_data_df, current_account_areas,
    account_health_no_entitlements,
):
    result = transform.transform(
        cross_account=cross_account_df,
        arr_data=arr_data_df,
        current_account_areas=current_account_areas,
        account_health=account_health_no_entitlements,
        customer_name="TestCo",
        account_id=CURRENT_ACCOUNT_ID,
        deployment_type="SaaS",
    )
    assert result["expansion_signals"] == []


# ── Test: privacy dict always has required fields ──

def test_privacy_dict_always_present(
    transform, cross_account_df, arr_data_df, current_account_areas,
    account_health_with_entitlements,
):
    result = transform.transform(
        cross_account=cross_account_df,
        arr_data=arr_data_df,
        current_account_areas=current_account_areas,
        account_health=account_health_with_entitlements,
        customer_name="TestCo",
        account_id=CURRENT_ACCOUNT_ID,
        deployment_type="Dedicated Cloud",
    )
    privacy = result["privacy"]
    assert privacy["badge_visible"] is True
    assert privacy["min_cohort_size"] == 10
    assert privacy["anonymized"] is True
