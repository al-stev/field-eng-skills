"""Tests for TeamDetectionTransform."""

import pandas as pd
import pytest
from datetime import date


from transforms.team_detection import TeamDetectionTransform


@pytest.fixture
def transform():
    return TeamDetectionTransform()


@pytest.fixture
def valid_teams_df():
    """DataFrame simulating team_detection_query() output with real team data."""
    return pd.DataFrame({
        "team_name": ["ML Platform", "ML Platform", "Data Eng", "Data Eng", "Research"],
        "member_count": [15, 15, 8, 8, 5],
        "total_events": [30000, 15230, 18000, 5100, 9500],
        "first_active": [
            date(2024, 6, 12), date(2024, 6, 12),
            date(2024, 9, 1), date(2024, 9, 1),
            date(2025, 1, 15),
        ],
        "last_active": [
            date(2026, 3, 24), date(2026, 3, 24),
            date(2026, 3, 20), date(2026, 3, 20),
            date(2026, 3, 18),
        ],
        "users_with_team_flag": [12, 12, 6, 6, 4],
        "product_area": ["Experiments", "Artifacts", "Experiments", "Weave Tracing", "Experiments"],
    })


@pytest.fixture
def names_unavailable_df():
    """DataFrame where all org_name is Unknown but team flags exist."""
    return pd.DataFrame({
        "team_name": ["Unknown", "Unknown"],
        "member_count": [20, 20],
        "total_events": [50000, 12000],
        "first_active": [date(2024, 6, 1), date(2024, 6, 1)],
        "last_active": [date(2026, 3, 24), date(2026, 3, 24)],
        "users_with_team_flag": [15, 15],
        "product_area": ["Experiments", "Artifacts"],
    })


@pytest.fixture
def unavailable_df():
    """DataFrame where all org_name is Unknown and no team flags."""
    return pd.DataFrame({
        "team_name": ["Unknown", "Unknown"],
        "member_count": [20, 20],
        "total_events": [50000, 12000],
        "first_active": [date(2024, 6, 1), date(2024, 6, 1)],
        "last_active": [date(2026, 3, 24), date(2026, 3, 24)],
        "users_with_team_flag": [0, 0],
        "product_area": ["Experiments", "Artifacts"],
    })


@pytest.fixture
def champions_df():
    """DataFrame simulating team_champions_query() output."""
    return pd.DataFrame({
        "team_name": ["ML Platform", "Data Eng", "Research"],
        "universal_user_id": ["uid1", "uid2", "uid3"],
        "username": ["jdoe", "asmith", None],
        "email": ["jdoe@test.com", "asmith@test.com", "bwilson@test.com"],
        "total_events": [12450, 8900, 5200],
        "last_active": [date(2026, 3, 24), date(2026, 3, 20), date(2026, 3, 18)],
    })


class TestTeamDetectionAvailableStatus:
    """Test transform with full team data available (team_data_status='available')."""

    def test_transform_returns_available_true(self, transform, valid_teams_df):
        result = transform.transform(teams=valid_teams_df, customer_name="TestCorp")
        assert result["available"] is True

    def test_transform_returns_correct_page_type(self, transform, valid_teams_df):
        result = transform.transform(teams=valid_teams_df, customer_name="TestCorp")
        assert result["page_type"] == "team-detection"

    def test_transform_returns_available_status(self, transform, valid_teams_df):
        result = transform.transform(teams=valid_teams_df, customer_name="TestCorp")
        assert result["team_data_status"] == "available"


class TestTeamDetectionNamesUnavailable:
    """Test transform when org_name is NULL but team flags exist."""

    def test_names_unavailable_status(self, transform, names_unavailable_df):
        result = transform.transform(teams=names_unavailable_df, customer_name="TestCorp")
        assert result["team_data_status"] == "names_unavailable"

    def test_names_unavailable_still_returns_available_true(self, transform, names_unavailable_df):
        result = transform.transform(teams=names_unavailable_df, customer_name="TestCorp")
        assert result["available"] is True


class TestTeamDetectionUnavailable:
    """Test transform when org_name is NULL and no team flags."""

    def test_unavailable_status(self, transform, unavailable_df):
        result = transform.transform(teams=unavailable_df, customer_name="TestCorp")
        assert result["team_data_status"] == "unavailable"

    def test_unavailable_still_returns_available_true(self, transform, unavailable_df):
        result = transform.transform(teams=unavailable_df, customer_name="TestCorp")
        assert result["available"] is True


class TestTeamDetectionTeamBreakdown:
    """Test team breakdown table data (TEAM-01)."""

    def test_teams_sorted_by_total_events_descending(self, transform, valid_teams_df):
        result = transform.transform(teams=valid_teams_df, customer_name="TestCorp")
        teams = result["teams"]
        events = [t["total_events"] for t in teams]
        assert events == sorted(events, reverse=True)

    def test_teams_have_required_keys(self, transform, valid_teams_df):
        result = transform.transform(teams=valid_teams_df, customer_name="TestCorp")
        required_keys = {"name", "member_count", "total_events", "top_product", "first_active", "last_active"}
        for team in result["teams"]:
            assert required_keys.issubset(team.keys()), f"Missing keys in team: {required_keys - team.keys()}"


class TestTeamDetectionActivity:
    """Test team activity chart data (TEAM-02)."""

    def test_team_activity_has_required_keys(self, transform, valid_teams_df):
        result = transform.transform(teams=valid_teams_df, customer_name="TestCorp")
        activity = result["team_activity"]
        assert "team_names" in activity
        assert "events" in activity
        assert "users" in activity

    def test_team_activity_lists_same_length(self, transform, valid_teams_df):
        result = transform.transform(teams=valid_teams_df, customer_name="TestCorp")
        activity = result["team_activity"]
        assert len(activity["team_names"]) == len(activity["events"]) == len(activity["users"])


class TestTeamDetectionHeatmap:
    """Test team product heatmap data (TEAM-03)."""

    def test_heatmap_has_required_keys(self, transform, valid_teams_df):
        result = transform.transform(teams=valid_teams_df, customer_name="TestCorp")
        heatmap = result["team_product_heatmap"]
        assert "team_names" in heatmap
        assert "product_areas" in heatmap
        assert "matrix" in heatmap

    def test_heatmap_matrix_entries_are_triplets(self, transform, valid_teams_df):
        result = transform.transform(teams=valid_teams_df, customer_name="TestCorp")
        matrix = result["team_product_heatmap"]["matrix"]
        assert len(matrix) > 0
        for entry in matrix:
            assert len(entry) == 3, f"Expected [teamIdx, areaIdx, eventCount], got {entry}"


class TestTeamDetectionTimeline:
    """Test team adoption timeline data (TEAM-06)."""

    def test_timeline_has_entries(self, transform, valid_teams_df):
        result = transform.transform(teams=valid_teams_df, customer_name="TestCorp")
        timeline = result["team_timeline"]
        assert len(timeline) > 0

    def test_timeline_entries_have_required_keys(self, transform, valid_teams_df):
        result = transform.transform(teams=valid_teams_df, customer_name="TestCorp")
        for entry in result["team_timeline"]:
            assert "name" in entry
            assert "first_active" in entry
            assert "last_active" in entry


class TestTeamDetectionChampions:
    """Test champion identification (TEAM-07)."""

    def test_champions_merged_into_teams(self, transform, valid_teams_df, champions_df):
        result = transform.transform(teams=valid_teams_df, champions=champions_df, customer_name="TestCorp")
        teams_with_champion = [t for t in result["teams"] if t.get("champion") is not None]
        assert len(teams_with_champion) >= 1

    def test_champion_has_required_keys(self, transform, valid_teams_df, champions_df):
        result = transform.transform(teams=valid_teams_df, champions=champions_df, customer_name="TestCorp")
        teams_with_champion = [t for t in result["teams"] if t.get("champion") is not None]
        for team in teams_with_champion:
            champ = team["champion"]
            assert "username" in champ
            assert "display_name" in champ
            assert "events" in champ


class TestTeamDetectionGrowth:
    """Test team growth/contraction data (TEAM-08)."""

    def test_growth_has_required_keys(self, transform, valid_teams_df):
        result = transform.transform(teams=valid_teams_df, customer_name="TestCorp")
        growth = result["team_growth"]
        assert "months" in growth
        assert "teams" in growth


class TestTeamDetectionKPIs:
    """Test KPI generation."""

    def test_kpis_has_four_entries(self, transform, valid_teams_df):
        result = transform.transform(teams=valid_teams_df, customer_name="TestCorp")
        assert len(result["kpis"]) == 4

    def test_kpi_labels(self, transform, valid_teams_df):
        result = transform.transform(teams=valid_teams_df, customer_name="TestCorp")
        labels = [k["label"] for k in result["kpis"]]
        assert labels == ["Teams Detected", "Total Members", "Most Active Team", "Product Areas Used"]


class TestTeamDetectionNarrative:
    """Test AI narrative generation (TEAM-05)."""

    def test_narrative_has_required_keys(self, transform, valid_teams_df):
        result = transform.transform(teams=valid_teams_df, customer_name="TestCorp")
        narrative = result["narrative"]
        assert "executive_summary" in narrative
        assert "highlights" in narrative
        assert "recommendations" in narrative


class TestTeamDetectionEmptyInput:
    """Test with empty DataFrame."""

    def test_empty_dataframe_returns_not_available(self, transform):
        empty_df = pd.DataFrame(columns=["team_name", "member_count", "total_events",
                                          "first_active", "last_active", "users_with_team_flag",
                                          "product_area"])
        result = transform.transform(teams=empty_df, customer_name="TestCorp")
        assert result["available"] is False
        assert result["reason"] == "no_data"


class TestTeamDetectionOutputShape:
    """Test the full output shape has all required top-level keys."""

    def test_full_output_keys(self, transform, valid_teams_df):
        result = transform.transform(teams=valid_teams_df, customer_name="TestCorp", deployment_type="SaaS")
        required_keys = {
            "available", "page_type", "customer", "generated", "period",
            "kpis", "team_data_status", "teams", "team_activity",
            "team_product_heatmap", "team_timeline", "team_growth",
            "narrative", "data_source", "deployment_type",
        }
        assert required_keys.issubset(result.keys()), f"Missing keys: {required_keys - result.keys()}"
