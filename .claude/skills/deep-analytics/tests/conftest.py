"""Shared test fixtures for deep-analytics tests."""

import sys
import pytest
from unittest.mock import MagicMock
from pathlib import Path

# Add scripts directory to path so tests can import generate, schema_validator, etc.
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def mock_bq_client():
    """Mock BigQuery client."""
    client = MagicMock()
    return client


@pytest.fixture
def sample_customers_yaml(tmp_path):
    """Create a temporary customers.yaml for testing."""
    yaml_content = """
customers:
  - name: TestCorp
    sfdc_account_id: "001000000000001AAA"
    deployment_type: cloud
  - name: ServerCo
    sfdc_account_id: "001000000000002AAA"
    deployment_type: server
  - name: Placeholder
    sfdc_account_id: PLACEHOLDER
"""
    path = tmp_path / "customers.yaml"
    path.write_text(yaml_content)
    return path


@pytest.fixture
def project_root():
    """Return the project root path."""
    return Path(__file__).resolve().parents[4]
