"""End-to-end integration tests for template injection pipeline.

These tests use the REAL base-template.html file (not mocked template strings)
to validate that the actual sentinel positions, whitespace, and surrounding
content work with the injection logic in generate.py.
"""

import json
import os
import re
from datetime import date
from pathlib import Path

import pytest

# Path to real template
TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "templates" / "base-template.html"


class TestInjectPageDataRealTemplate:
    """Test 1: inject_page_data() with real base-template.html."""

    def test_inject_page_data_with_real_template(self):
        """Inject custom PAGE_DATA into real template and verify output contains injected data."""
        from generate import inject_page_data

        template = TEMPLATE_PATH.read_text()
        custom_data = {
            "customer": "TestCorp Integration",
            "generated": "2026-03-24",
            "period": {"start": "2025-01-01", "end": "2026-03-24"},
            "available": True,
            "reason": None,
            "page_type": "user-journey",
            "kpis": [
                {"value": "42", "label": "Total Users"},
                {"value": "18", "label": "Active (30d)"},
                {"value": "Experiments", "label": "Top Product Area"},
                {"value": "12 months", "label": "Data Period"},
            ],
        }
        result = inject_page_data(template, custom_data)

        # Injected customer name must appear in output
        assert '"TestCorp Integration"' in result
        # Original sample data must be gone
        assert '"Sample Corp"' not in result.split("PAGE_DATA_END")[0].split("PAGE_DATA_START")[1]
        # KPI data present
        assert '"Total Users"' in result


class TestInjectAINarrativeRealTemplate:
    """Test 2: inject_ai_narrative() with real base-template.html."""

    def test_inject_ai_narrative_with_real_template(self):
        """Inject custom AI_NARRATIVE into real template and verify output contains injected narrative."""
        from generate import inject_ai_narrative

        template = TEMPLATE_PATH.read_text()
        custom_narrative = {
            "executive_summary": "TestCorp shows strong adoption with 42 active users across 3 product areas.",
            "highlights": [
                "User growth accelerated 15% month-over-month",
                "Experiments adoption reached 85% of licensed seats",
            ],
            "recommendations": [
                "Schedule Artifacts workshop for remaining non-adopters",
                "Review Sweeps usage with ML platform team lead",
            ],
        }
        result = inject_ai_narrative(template, custom_narrative)

        # Injected narrative must appear
        assert "TestCorp shows strong adoption" in result
        assert "User growth accelerated" in result
        # Original placeholder must be gone from the narrative section
        narrative_section = result.split("AI_NARRATIVE_START")[1].split("AI_NARRATIVE_END")[0]
        assert "placeholder" not in narrative_section.lower()


class TestWriteOutputEndToEnd:
    """Test 3: write_output() full pipeline with real template."""

    def test_write_output_creates_valid_html(self, tmp_path):
        """write_output reads real template, injects data, writes file with customer name."""
        from generate import write_output

        page_data = {
            "customer": "EndToEnd Corp",
            "generated": "2026-03-24",
            "period": {"start": "2025-01-01", "end": "2026-03-24"},
            "available": True,
            "reason": None,
            "page_type": "cohort-analysis",
            "kpis": [
                {"value": "100", "label": "Total Users"},
            ],
        }
        ai_narrative = {
            "executive_summary": "EndToEnd Corp integration test narrative.",
            "highlights": ["Test highlight"],
            "recommendations": ["Test recommendation"],
        }

        output_path = write_output(
            customer_name="EndToEnd Corp",
            page_type="cohort-analysis",
            page_data=page_data,
            ai_narrative=ai_narrative,
            output_dir=str(tmp_path),
        )

        assert output_path.exists()
        content = output_path.read_text()
        # Valid HTML structure
        assert "<!DOCTYPE html>" in content
        assert "</html>" in content
        # Contains injected customer name
        assert '"EndToEnd Corp"' in content
        # Contains injected narrative
        assert "EndToEnd Corp integration test narrative." in content
        # File is in the expected directory
        assert output_path.parent == tmp_path


class TestWriteOutputEmptyState:
    """Test 4: write_output() with available=false produces renderable empty state."""

    def test_empty_state_html_contains_reason(self, tmp_path):
        """Empty state HTML has renderEmptyState function and reason code in data."""
        from generate import write_output

        page_data = {
            "customer": "EmptyState Corp",
            "generated": "2026-03-24",
            "period": {"start": "2025-01-01", "end": "2026-03-24"},
            "available": False,
            "reason": "no_data",
            "page_type": "engagement-decay",
            "kpis": [
                {"value": "--", "label": "Total Users"},
            ],
        }

        output_path = write_output(
            customer_name="EmptyState Corp",
            page_type="engagement-decay",
            page_data=page_data,
            output_dir=str(tmp_path),
        )

        content = output_path.read_text()
        # The renderEmptyState JS function must exist
        assert "renderEmptyState" in content
        # The reason code must be in the injected data
        assert '"no_data"' in content
        # available must be false in the data
        assert '"available": false' in content


class TestBuildOutputPathCreatesDirectory:
    """Test 5: build_output_path() creates directory structure."""

    def test_output_path_creates_directory(self, tmp_path):
        """build_output_path creates customers/<name>/analytics/ in a temp dir."""
        from generate import build_output_path

        nested_dir = tmp_path / "nested" / "output"
        path = build_output_path("Test Customer", "user-journey", str(nested_dir))

        # Directory was created
        assert nested_dir.exists()
        assert nested_dir.is_dir()
        # Path has correct filename format
        today = date.today().isoformat()
        assert path.name == f"{today}-user-journey.html"
        assert path.parent == nested_dir


class TestGeneratedFileSizeLimit:
    """Test 6: Generated HTML file size under 200KB."""

    def test_generated_html_under_200kb(self, tmp_path):
        """Template plus sample data should be well under 200KB."""
        from generate import write_output

        page_data = {
            "customer": "SizeCheck Corp",
            "generated": "2026-03-24",
            "period": {"start": "2025-01-01", "end": "2026-03-24"},
            "available": True,
            "reason": None,
            "page_type": "feature-velocity",
            "kpis": [
                {"value": "50", "label": "Total Users"},
                {"value": "30", "label": "Active (30d)"},
                {"value": "Runs", "label": "Top Product Area"},
                {"value": "6 months", "label": "Data Period"},
            ],
        }
        ai_narrative = {
            "executive_summary": "Size check narrative for file size validation.",
            "highlights": ["Highlight A", "Highlight B", "Highlight C"],
            "recommendations": ["Rec A", "Rec B"],
        }

        output_path = write_output(
            customer_name="SizeCheck Corp",
            page_type="feature-velocity",
            page_data=page_data,
            ai_narrative=ai_narrative,
            output_dir=str(tmp_path),
        )

        file_size = output_path.stat().st_size
        assert file_size < 200 * 1024, f"File size {file_size} bytes exceeds 200KB limit"


class TestPageTypesMatchRegistry:
    """Test 7: PAGE_TYPES JS array matches PAGE_REGISTRY Python dict."""

    def test_page_types_match_registry(self):
        """All 9 page type slugs in PAGE_REGISTRY match the PAGE_TYPES array in base-template.html."""
        from generate import PAGE_REGISTRY

        template = TEMPLATE_PATH.read_text()
        # Extract slugs from PAGE_TYPES JS array: { slug: 'user-journey', ... }
        slugs = re.findall(r"slug:\s*'([^']+)'", template)

        assert len(slugs) == 9, f"Expected 9 page types in template, found {len(slugs)}: {slugs}"
        assert set(slugs) == set(PAGE_REGISTRY.keys()), (
            f"Mismatch between template PAGE_TYPES {set(slugs)} "
            f"and Python PAGE_REGISTRY {set(PAGE_REGISTRY.keys())}"
        )


class TestSentinelPairsIntactAfterInjection:
    """Test 8: Sentinel pairs remain intact after injection."""

    def test_sentinels_intact_after_both_injections(self):
        """Both START and END markers present in output after PAGE_DATA and AI_NARRATIVE injection."""
        from generate import inject_page_data, inject_ai_narrative

        template = TEMPLATE_PATH.read_text()

        page_data = {
            "customer": "Sentinel Test Corp",
            "generated": "2026-03-24",
            "period": {"start": "2025-01-01", "end": "2026-03-24"},
            "available": True,
            "reason": None,
            "page_type": "sdk-versions",
            "kpis": [],
        }
        narrative = {
            "executive_summary": "Sentinel integrity test.",
            "highlights": [],
            "recommendations": [],
        }

        # Apply both injections
        result = inject_page_data(template, page_data)
        result = inject_ai_narrative(result, narrative)

        # All four sentinel markers must be present
        assert "/* PAGE_DATA_START */" in result
        assert "/* PAGE_DATA_END */" in result
        assert "/* AI_NARRATIVE_START */" in result
        assert "/* AI_NARRATIVE_END */" in result

        # Verify the injected data is between the correct sentinels
        page_section = result.split("/* PAGE_DATA_START */")[1].split("/* PAGE_DATA_END */")[0]
        assert '"Sentinel Test Corp"' in page_section

        narrative_section = result.split("/* AI_NARRATIVE_START */")[1].split("/* AI_NARRATIVE_END */")[0]
        assert "Sentinel integrity test." in narrative_section
