"""Tests for assemble.py -- deterministic INTELLIGENCE_DATA assembly."""

import json
import subprocess
import sys
from datetime import date, datetime, timedelta

import pytest

from assemble import (
    COMPONENT_NORMALIZE,
    PARENT_NORMALIZE,
    assemble_intelligence_data,
    assign_theme,
    compute_trending,
    map_priority,
    transform_asana_tasks,
    transform_jira_issues,
)


# ── Fixtures ──


SAMPLE_JIRA_ISSUE = {
    "key": "WB-1234",
    "url": "https://wandb.atlassian.net/browse/WB-1234",
    "summary": "SDK crash on large artifact upload",
    "status": "In Progress",
    "type": "Bug",
    "priority": "High",
    "assignee": "Jane Doe",
    "customer": "GResearch",
    "components": ["Weave Python SDK"],
    "labels": ["fe-reported"],
    "parent": "WB-900",
    "parent_summary": "Weave SDK Improvements",
    "duedate": None,
    "created": "2026-01-15T10:00:00.000+0000",
    "updated": "2026-03-08T14:00:00.000+0000",
    "resolutiondate": None,
    "comments": {
        "comment_count": 5,
        "last_comment_date": "2026-03-01T10:30:00.000+0000",
        "last_comment_author": "Jane Doe",
        "last_eng_comment_date": "2026-02-28T14:00:00.000+0000",
        "last_eng_comment_author": "John Smith",
        "first_comment_date": "2026-01-16T09:00:00.000+0000",
        "fe_update_count": 2,
    },
}

SAMPLE_JIRA_ISSUE_NO_COMPONENT = {
    "key": "WB-5678",
    "url": "https://wandb.atlassian.net/browse/WB-5678",
    "summary": "Sweep parameter ranges off",
    "status": "Open",
    "type": "Bug",
    "priority": "Medium",
    "assignee": None,
    "customer": "GResearch",
    "components": [],
    "labels": [],
    "parent": "WB-800",
    "parent_summary": "Sweep Improvements",
    "duedate": None,
    "created": "2026-02-10T10:00:00.000+0000",
    "updated": "2026-03-01T14:00:00.000+0000",
    "resolutiondate": None,
    "comments": {
        "comment_count": 0,
        "last_comment_date": None,
        "last_comment_author": None,
        "last_eng_comment_date": None,
        "last_eng_comment_author": None,
        "first_comment_date": None,
        "fe_update_count": 0,
    },
}

SAMPLE_JIRA_ISSUE_UNCATEGORIZED = {
    "key": "WB-9999",
    "url": "https://wandb.atlassian.net/browse/WB-9999",
    "summary": "Random misc issue",
    "status": "Open",
    "type": "Feature Request",
    "priority": "Low",
    "assignee": "Bob",
    "customer": "GResearch",
    "components": [],
    "labels": [],
    "parent": None,
    "parent_summary": None,
    "duedate": None,
    "created": "2026-03-01T10:00:00.000+0000",
    "updated": "2026-03-15T14:00:00.000+0000",
    "resolutiondate": None,
    "comments": {
        "comment_count": 1,
        "last_comment_date": "2026-03-02T10:00:00.000+0000",
        "last_comment_author": "Bob",
        "last_eng_comment_date": None,
        "last_eng_comment_author": None,
        "first_comment_date": "2026-03-02T10:00:00.000+0000",
        "fe_update_count": 0,
    },
}

SAMPLE_RESOLVED_ISSUE = {
    "key": "WB-1111",
    "url": "https://wandb.atlassian.net/browse/WB-1111",
    "summary": "Launch config validation",
    "status": "Done",
    "type": "Bug",
    "priority": "Critical",
    "assignee": "Alice",
    "customer": "GResearch",
    "components": ["Launch"],
    "labels": [],
    "parent": None,
    "parent_summary": None,
    "duedate": None,
    "created": "2026-01-01T10:00:00.000+0000",
    "updated": "2026-02-15T14:00:00.000+0000",
    "resolutiondate": "2026-02-15T14:00:00.000+0000",
    "comments": {
        "comment_count": 3,
        "last_comment_date": "2026-02-15T14:00:00.000+0000",
        "last_comment_author": "Alice",
        "last_eng_comment_date": "2026-02-14T10:00:00.000+0000",
        "last_eng_comment_author": "DevTeam",
        "first_comment_date": "2026-01-02T09:00:00.000+0000",
        "fe_update_count": 1,
    },
}


SAMPLE_ASANA_TASKS = {
    "count": 3,
    "results": [
        {
            "gid": "11111",
            "name": "Follow up on SDK crash (WB-1234)",
            "completed": False,
            "assignee": {"gid": "12345", "name": "Allan Stevenson"},
            "due_on": "2026-03-28",
            "modified_at": "2026-03-21T10:00:00Z",
            "memberships": [
                {
                    "section": {"name": "In Progress"},
                    "project": {"name": "GResearch Actions"},
                }
            ],
            "custom_fields": [{"name": "Priority", "display_value": "High"}],
        },
        {
            "gid": "22222",
            "name": "Review sweep config",
            "completed": False,
            "assignee": {"gid": "12345", "name": "Allan Stevenson"},
            "due_on": (date.today() - timedelta(days=3)).isoformat(),
            "modified_at": (
                datetime.utcnow() - timedelta(days=10)
            ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "memberships": [
                {
                    "section": {"name": "To Do"},
                    "project": {"name": "GResearch Actions"},
                }
            ],
            "custom_fields": [{"name": "Priority", "display_value": "Medium"}],
        },
        {
            "gid": "33333",
            "name": "Waiting on customer response",
            "completed": False,
            "assignee": {"gid": "12345", "name": "Allan Stevenson"},
            "due_on": (date.today() - timedelta(days=1)).isoformat(),
            "modified_at": (
                datetime.utcnow() - timedelta(days=15)
            ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "memberships": [
                {
                    "section": {"name": "Waiting on Customer"},
                    "project": {"name": "GResearch Actions"},
                }
            ],
            "custom_fields": [{"name": "Priority", "display_value": "Low"}],
        },
    ],
}


SAMPLE_BQ_DATA = {
    "available": True,
    "period": {"start": "2025-03-24", "end": "2026-03-24"},
    "seat_utilization": {
        "contracted": 50,
        "claimed": 42,
        "active": 35,
        "utilization_percent": 70.0,
        "history": [],
    },
    "weave": {
        "ingestion_gb": 156.3,
        "limit_gb": 500.0,
        "utilization_percent": 31.3,
        "unique_users_last_90d": 12,
        "history": [],
    },
    "tracked_hours": {
        "last_30d_hours": 1250.0,
        "last_30d_run_count": 342,
        "history": [],
    },
    "account_health": {
        "renewal_date": "2026-09-15",
        "arr": 250000.0,
        "cs_tier": "Strategic",
    },
    "trends": {
        "seat_utilization_change": 12.5,
        "weave_ingestion_change": -3.2,
        "tracked_hours_change": 8.7,
        "run_count_change": 15.3,
    },
    "product_areas": [],
    "power_users": [],
}

SAMPLE_SENTIMENT = {
    "available": True,
    "channels_analyzed": ["#ext-gresearch"],
    "period": {"start": "2026-03-03", "end": "2026-03-17"},
    "overall": {
        "score": "cautiously-negative",
        "numeric": -0.3,
        "summary": "Tone shifted negative.",
    },
    "hot_threads": [],
    "internal": {
        "raw_analysis": "Detailed analysis...",
        "risk_signals": [],
        "recommended_actions": [],
    },
}


# ── Theme assignment tests ──


class TestComponentNormalization:
    def test_weave_python_sdk_maps_to_sdk(self):
        issue = {"components": ["Weave Python SDK"], "parent_summary": None}
        assert assign_theme(issue) == "SDK & Client Libraries"

    def test_sweeps_maps_to_sweeps(self):
        issue = {"components": ["Sweeps"], "parent_summary": None}
        assert assign_theme(issue) == "Sweeps"

    def test_launch_maps_to_launch(self):
        issue = {"components": ["Launch"], "parent_summary": None}
        assert assign_theme(issue) == "Launch"

    def test_weave_maps_to_weave(self):
        issue = {"components": ["Weave"], "parent_summary": None}
        assert assign_theme(issue) == "Weave"

    def test_ui_maps_to_ui_dashboard(self):
        issue = {"components": ["UI"], "parent_summary": None}
        assert assign_theme(issue) == "UI & Dashboard"


class TestParentNormalization:
    def test_sweep_improvements_maps_via_parent(self):
        issue = {"components": [], "parent_summary": "Sweep Improvements"}
        assert assign_theme(issue) == "Sweeps"

    def test_sdk_improvements_maps_via_parent(self):
        issue = {"components": [], "parent_summary": "SDK Improvements"}
        assert assign_theme(issue) == "SDK & Client Libraries"

    def test_launch_improvements_maps_via_parent(self):
        issue = {"components": [], "parent_summary": "Launch Improvements"}
        assert assign_theme(issue) == "Launch"


class TestUncategorized:
    def test_no_component_no_parent(self):
        issue = {"components": [], "parent_summary": None}
        assert assign_theme(issue) == "Uncategorized"

    def test_no_component_unrecognized_parent(self):
        issue = {"components": [], "parent_summary": "Random Epic"}
        assert assign_theme(issue) == "Uncategorized"

    def test_component_takes_priority_over_parent(self):
        """When both component and parent exist, component wins."""
        issue = {
            "components": ["Weave Python SDK"],
            "parent_summary": "Sweep Improvements",
        }
        assert assign_theme(issue) == "SDK & Client Libraries"


# ── Priority mapping tests ──


class TestPriorityMapping:
    def test_critical_to_p0(self):
        assert map_priority("Critical") == "P0"

    def test_highest_to_p0(self):
        assert map_priority("Highest") == "P0"

    def test_high_to_p1(self):
        assert map_priority("High") == "P1"

    def test_medium_to_p2(self):
        assert map_priority("Medium") == "P2"

    def test_low_to_p3(self):
        assert map_priority("Low") == "P3"

    def test_lowest_to_p3(self):
        assert map_priority("Lowest") == "P3"

    def test_passthrough_p0(self):
        assert map_priority("P0") == "P0"

    def test_passthrough_p1(self):
        assert map_priority("P1") == "P1"

    def test_passthrough_p2(self):
        assert map_priority("P2") == "P2"

    def test_passthrough_p3(self):
        assert map_priority("P3") == "P3"

    def test_none_stays_none(self):
        assert map_priority(None) is None


# ── Trending computation tests ──


class TestTrendingComputation:
    def test_opened_by_month(self):
        issues = transform_jira_issues(
            [SAMPLE_JIRA_ISSUE, SAMPLE_JIRA_ISSUE_NO_COMPONENT, SAMPLE_RESOLVED_ISSUE]
        )
        trending = compute_trending(issues, months=6)
        # Issues created in Jan and Feb 2026 and Mar 2026
        assert isinstance(trending["opened_by_month"], list)
        assert len(trending["opened_by_month"]) == 6
        # Find the Jan entry
        jan_entry = [
            m for m in trending["opened_by_month"] if m["month"] == "2026-01"
        ]
        assert len(jan_entry) == 1
        assert jan_entry[0]["count"] == 2  # WB-1234 and WB-1111 both created Jan

    def test_closed_by_month(self):
        issues = transform_jira_issues(
            [SAMPLE_JIRA_ISSUE, SAMPLE_RESOLVED_ISSUE]
        )
        trending = compute_trending(issues, months=6)
        assert isinstance(trending["closed_by_month"], list)
        # WB-1111 resolved in Feb
        feb_entry = [
            m for m in trending["closed_by_month"] if m["month"] == "2026-02"
        ]
        assert len(feb_entry) == 1
        assert feb_entry[0]["count"] == 1

    def test_median_ttr_days(self):
        issues = transform_jira_issues([SAMPLE_RESOLVED_ISSUE])
        trending = compute_trending(issues, months=6)
        # Created Jan 1, resolved Feb 15 = 45 days
        assert trending["median_ttr_days"] == 45

    def test_theme_recurrence_top_5(self):
        issues = transform_jira_issues(
            [
                SAMPLE_JIRA_ISSUE,
                SAMPLE_JIRA_ISSUE_NO_COMPONENT,
                SAMPLE_JIRA_ISSUE_UNCATEGORIZED,
                SAMPLE_RESOLVED_ISSUE,
            ]
        )
        trending = compute_trending(issues, months=6)
        assert isinstance(trending["theme_recurrence"], list)
        assert len(trending["theme_recurrence"]) <= 5
        # SDK & Client Libraries should appear (WB-1234)
        themes = [t["theme"] for t in trending["theme_recurrence"]]
        assert "SDK & Client Libraries" in themes

    def test_ratio_with_zero_closed(self):
        issues = transform_jira_issues([SAMPLE_JIRA_ISSUE])
        trending = compute_trending(issues, months=6)
        assert trending["raised_to_resolved_ratio"] is None

    def test_ratio_with_closed(self):
        issues = transform_jira_issues(
            [SAMPLE_JIRA_ISSUE, SAMPLE_RESOLVED_ISSUE]
        )
        trending = compute_trending(issues, months=6)
        # 2 opened, 1 closed = 2.0
        assert trending["raised_to_resolved_ratio"] == 2.0


# ── Graceful degradation tests ──


class TestGracefulDegradation:
    def test_missing_jira(self):
        result = assemble_intelligence_data("TestCo", None, None, None, None)
        assert result["issues"] == []
        assert result["trending"] is None

    def test_missing_bq(self):
        result = assemble_intelligence_data("TestCo", None, None, None, None)
        assert result["usage"]["available"] is False
        assert result["usage"]["reason"] == "not_provided"

    def test_missing_asana(self):
        result = assemble_intelligence_data("TestCo", None, None, None, None)
        assert result["actions"]["available"] is False
        assert result["actions"]["reason"] == "not_provided"

    def test_missing_sentiment(self):
        result = assemble_intelligence_data("TestCo", None, None, None, None)
        assert result["sentiment"] is None


# ── Asana task transformation tests ──


class TestAsanaTransformation:
    def test_overdue_detection(self):
        tasks = transform_asana_tasks(SAMPLE_ASANA_TASKS)
        # Task 22222 has due_on in the past and is incomplete
        overdue_task = [t for t in tasks["tasks"] if t["gid"] == "22222"][0]
        assert overdue_task["overdue"] is True

    def test_stale_detection(self):
        tasks = transform_asana_tasks(SAMPLE_ASANA_TASKS)
        # Task 22222 is in "To Do", modified 10 days ago -> stale
        stale_task = [t for t in tasks["tasks"] if t["gid"] == "22222"][0]
        assert stale_task["stale"] is True
        assert stale_task["stale_days"] >= 10

    def test_waiting_section_not_stale(self):
        tasks = transform_asana_tasks(SAMPLE_ASANA_TASKS)
        # Task 33333 is in "Waiting on Customer" -> NOT stale even though old
        waiting_task = [t for t in tasks["tasks"] if t["gid"] == "33333"][0]
        assert waiting_task["stale"] is False

    def test_linked_jira_extracted(self):
        tasks = transform_asana_tasks(SAMPLE_ASANA_TASKS)
        linked = [t for t in tasks["tasks"] if t["gid"] == "11111"][0]
        assert linked["linked_jira"] == "WB-1234"

    def test_no_linked_jira(self):
        tasks = transform_asana_tasks(SAMPLE_ASANA_TASKS)
        no_link = [t for t in tasks["tasks"] if t["gid"] == "22222"][0]
        assert no_link["linked_jira"] is None

    def test_section_extracted(self):
        tasks = transform_asana_tasks(SAMPLE_ASANA_TASKS)
        task = [t for t in tasks["tasks"] if t["gid"] == "11111"][0]
        assert task["section"] == "In Progress"

    def test_priority_mapping(self):
        tasks = transform_asana_tasks(SAMPLE_ASANA_TASKS)
        high = [t for t in tasks["tasks"] if t["gid"] == "11111"][0]
        assert high["priority"] == "P1"
        med = [t for t in tasks["tasks"] if t["gid"] == "22222"][0]
        assert med["priority"] == "P2"
        low = [t for t in tasks["tasks"] if t["gid"] == "33333"][0]
        assert low["priority"] == "P3"

    def test_summary_counts(self):
        tasks = transform_asana_tasks(SAMPLE_ASANA_TASKS)
        s = tasks["summary"]
        assert s["total"] == 3
        assert s["in_progress"] == 1
        assert s["todo"] == 1
        assert s["overdue"] >= 1  # At least task 22222
        assert s["stale"] >= 1  # At least task 22222


# ── Full assembly tests ──


class TestFullAssembly:
    def test_all_inputs_produces_valid_structure(self):
        jira_data = {
            "issues": [SAMPLE_JIRA_ISSUE, SAMPLE_RESOLVED_ISSUE],
            "total": 2,
            "count": 2,
        }
        result = assemble_intelligence_data(
            customer="GResearch",
            jira_data=jira_data,
            bq_data=SAMPLE_BQ_DATA,
            asana_data=SAMPLE_ASANA_TASKS,
            sentiment_data=SAMPLE_SENTIMENT,
        )
        # Top-level keys
        assert result["customer"] == "GResearch"
        assert result["generated"] == date.today().isoformat()
        assert "config" in result
        assert isinstance(result["issues"], list)
        assert len(result["issues"]) == 2
        assert result["sentiment"] == SAMPLE_SENTIMENT
        assert result["trending"] is not None
        assert result["exec_summary"] is None
        assert result["actions"]["available"] is True
        assert result["usage"]["available"] is True

    def test_issues_have_theme_field(self):
        jira_data = {"issues": [SAMPLE_JIRA_ISSUE], "total": 1, "count": 1}
        result = assemble_intelligence_data(
            "TestCo", jira_data, None, None, None
        )
        assert result["issues"][0]["theme"] == "SDK & Client Libraries"

    def test_issues_have_mapped_priority(self):
        jira_data = {"issues": [SAMPLE_JIRA_ISSUE], "total": 1, "count": 1}
        result = assemble_intelligence_data(
            "TestCo", jira_data, None, None, None
        )
        assert result["issues"][0]["priority"] == "P1"  # High -> P1

    def test_config_defaults(self):
        result = assemble_intelligence_data("TestCo", None, None, None, None)
        assert result["config"]["sentiment_days"] == 14
        assert result["config"]["trending_months"] == 6
        assert result["config"]["audience"] == "internal"


# ── CLI smoke test ──


class TestCLI:
    def test_cli_outputs_valid_json(self, tmp_path):
        jira_file = tmp_path / "jira.json"
        jira_file.write_text(json.dumps({"issues": [], "total": 0, "count": 0}))

        result = subprocess.run(
            [
                sys.executable,
                str(
                    (
                        __import__("pathlib").Path(__file__).resolve().parent
                        / "assemble.py"
                    )
                ),
                "--customer",
                "TestCo",
                "--jira",
                str(jira_file),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["customer"] == "TestCo"
        assert data["issues"] == []
