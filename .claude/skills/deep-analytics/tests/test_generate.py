"""Tests for generate.py -- CLI orchestrator, page routing, data injection."""

import json
import pytest
from datetime import date
from unittest.mock import patch


class TestPageRegistry:
    """Test PAGE_REGISTRY contains all expected page types."""

    def test_registry_has_9_keys(self):
        """Test 6: PAGE_REGISTRY contains exactly 9 page type keys."""
        from generate import PAGE_REGISTRY

        assert len(PAGE_REGISTRY) == 9

    def test_registry_keys_match_expected(self):
        """Test 6b: PAGE_REGISTRY keys match the 9 expected page types."""
        from generate import PAGE_REGISTRY

        expected = {
            "user-journey",
            "cohort-analysis",
            "engagement-decay",
            "feature-velocity",
            "team-detection",
            "risk-scoring",
            "usage-correlation",
            "sdk-versions",
            "performance",
        }
        assert set(PAGE_REGISTRY.keys()) == expected


class TestArgparse:
    """Test CLI argument parsing."""

    def test_accepts_customer_and_page(self):
        """Test 7: argparse accepts --customer and --page and --output-dir."""
        import argparse
        from generate import PAGE_REGISTRY

        parser = argparse.ArgumentParser()
        parser.add_argument("--customer", required=True)
        parser.add_argument("--page", required=True, choices=sorted(PAGE_REGISTRY.keys()))
        parser.add_argument("--output-dir", default=None)

        args = parser.parse_args(["--customer", "TestCorp", "--page", "user-journey", "--output-dir", "/tmp/out"])

        assert args.customer == "TestCorp"
        assert args.page == "user-journey"
        assert args.output_dir == "/tmp/out"


class TestBuildOutputPath:
    """Test output path generation."""

    def test_output_path_format(self, tmp_path):
        """Test 8: build_output_path produces correct path format."""
        from generate import build_output_path

        path = build_output_path("G-Research", "user-journey", str(tmp_path))
        today = date.today().isoformat()

        assert path.parent == tmp_path
        assert path.name == f"{today}-user-journey.html"

    def test_output_path_default_convention(self):
        """Test 8b: Default path follows customers/<kebab>/analytics/ convention."""
        from generate import build_output_path, PROJECT_ROOT

        path = build_output_path("G-Research", "cohort-analysis")
        today = date.today().isoformat()

        expected_dir = PROJECT_ROOT / "customers" / "g-research" / "analytics"
        assert path.parent == expected_dir
        assert path.name == f"{today}-cohort-analysis.html"


class TestInjectPageData:
    """Test PAGE_DATA sentinel injection."""

    TEMPLATE = """<script>
/* PAGE_DATA_START */
const PAGE_DATA = {"sample": true};
/* PAGE_DATA_END */
/* AI_NARRATIVE_START */
const AI_NARRATIVE = {"sample": true};
/* AI_NARRATIVE_END */
</script>"""

    def test_inject_page_data_replaces_between_sentinels(self):
        """Test 9: inject_page_data replaces content between PAGE_DATA_START and PAGE_DATA_END."""
        from generate import inject_page_data

        data = {"customer": "TestCorp", "available": True}
        result = inject_page_data(self.TEMPLATE, data)

        assert "PAGE_DATA_START" in result
        assert "PAGE_DATA_END" in result
        assert '"customer": "TestCorp"' in result
        assert '"sample": true' not in result.split("PAGE_DATA_END")[0].split("PAGE_DATA_START")[1]

    def test_inject_ai_narrative_replaces_between_sentinels(self):
        """Test 10: inject_ai_narrative replaces content between AI_NARRATIVE_START and AI_NARRATIVE_END."""
        from generate import inject_ai_narrative

        narrative = {"executive_summary": "Test narrative"}
        result = inject_ai_narrative(self.TEMPLATE, narrative)

        assert "AI_NARRATIVE_START" in result
        assert "AI_NARRATIVE_END" in result
        assert '"executive_summary": "Test narrative"' in result
        assert '"sample": true' not in result.split("AI_NARRATIVE_END")[0].split("AI_NARRATIVE_START")[1]
