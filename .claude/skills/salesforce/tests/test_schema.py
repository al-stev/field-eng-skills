"""Tests for customers.yaml schema validation and SFDC field extensions.

Validates:
- YAML parsing and round-trip stability
- GResearch entry preserves all existing fields
- New SFDC-sourced fields (arr, contract_end, renewal_date, cs_tier, subscription_plan, account_team)
- Schema header documentation for new fields
- Backward compatibility (no bigquery_id field, existing data unchanged)
"""

from pathlib import Path

import yaml


# Path to the real customers.yaml (4 levels up from tests/ to project root)
CUSTOMERS_YAML = Path(__file__).resolve().parents[4] / "templates" / "customers.yaml"


def _load_yaml():
    """Load and return the parsed customers.yaml data."""
    with open(CUSTOMERS_YAML) as f:
        return yaml.safe_load(f)


def _read_raw():
    """Read the raw text of customers.yaml."""
    return CUSTOMERS_YAML.read_text()


def _get_gresearch(data):
    """Find the GResearch entry in the customers list."""
    for customer in data["customers"]:
        if customer["name"] == "GResearch":
            return customer
    raise AssertionError("GResearch entry not found in customers.yaml")


# --- YAML parsing ---


class TestYAMLParsing:
    def test_yaml_parses_without_errors(self):
        """YAML file should parse without errors via yaml.safe_load."""
        data = _load_yaml()
        assert data is not None

    def test_customers_list_has_entries(self):
        """customers list should have at least 1 entry."""
        data = _load_yaml()
        assert len(data["customers"]) >= 1


# --- Existing fields preserved ---


class TestExistingFieldsPreserved:
    def test_gresearch_has_name(self):
        gr = _get_gresearch(_load_yaml())
        assert gr["name"] == "GResearch"

    def test_gresearch_has_jira_customer(self):
        gr = _get_gresearch(_load_yaml())
        assert gr["jira_customer"] == "GResearch"

    def test_gresearch_has_jira_customer_variants(self):
        gr = _get_gresearch(_load_yaml())
        assert "G-Research" in gr["jira_customer_variants"]

    def test_gresearch_has_sfdc_account_id(self):
        gr = _get_gresearch(_load_yaml())
        assert "sfdc_account_id" in gr

    def test_gresearch_has_slack_channels(self):
        gr = _get_gresearch(_load_yaml())
        assert isinstance(gr["slack_channels"], list)
        assert len(gr["slack_channels"]) >= 1

    def test_gresearch_has_action_tracker_id(self):
        gr = _get_gresearch(_load_yaml())
        assert "action_tracker_id" in gr

    def test_gresearch_has_deployment_type(self):
        gr = _get_gresearch(_load_yaml())
        assert gr["deployment_type"] == "server"

    def test_gresearch_has_cadence(self):
        gr = _get_gresearch(_load_yaml())
        assert gr["cadence"]["type"] == "weekly"
        assert gr["cadence"]["day"] == "Monday"

    def test_gresearch_has_contacts(self):
        gr = _get_gresearch(_load_yaml())
        assert isinstance(gr["contacts"], list)
        names = [c["name"] for c in gr["contacts"]]
        assert "Allan Stevenson" in names


# --- New SFDC-sourced fields ---


class TestNewSFDCFields:
    def test_gresearch_has_arr(self):
        """GResearch entry should have 'arr' field (PLACEHOLDER or numeric)."""
        gr = _get_gresearch(_load_yaml())
        assert "arr" in gr
        assert gr["arr"] == "PLACEHOLDER" or isinstance(gr["arr"], (int, float))

    def test_gresearch_has_contract_end(self):
        """GResearch entry should have 'contract_end' field (PLACEHOLDER or date string)."""
        gr = _get_gresearch(_load_yaml())
        assert "contract_end" in gr
        assert gr["contract_end"] == "PLACEHOLDER" or isinstance(gr["contract_end"], str)

    def test_gresearch_has_renewal_date(self):
        """GResearch entry should have 'renewal_date' field (PLACEHOLDER or date string)."""
        gr = _get_gresearch(_load_yaml())
        assert "renewal_date" in gr
        assert gr["renewal_date"] == "PLACEHOLDER" or isinstance(gr["renewal_date"], str)

    def test_gresearch_has_cs_tier(self):
        """GResearch entry should have 'cs_tier' field (PLACEHOLDER string)."""
        gr = _get_gresearch(_load_yaml())
        assert "cs_tier" in gr
        assert gr["cs_tier"] == "PLACEHOLDER" or isinstance(gr["cs_tier"], str)

    def test_gresearch_has_subscription_plan(self):
        """GResearch entry should have 'subscription_plan' field (PLACEHOLDER string)."""
        gr = _get_gresearch(_load_yaml())
        assert "subscription_plan" in gr
        assert gr["subscription_plan"] == "PLACEHOLDER" or isinstance(gr["subscription_plan"], str)

    def test_gresearch_has_account_team(self):
        """GResearch entry should have 'account_team' field (PLACEHOLDER or list of dicts)."""
        gr = _get_gresearch(_load_yaml())
        assert "account_team" in gr
        val = gr["account_team"]
        if val != "PLACEHOLDER":
            assert isinstance(val, list)
            for member in val:
                assert "name" in member
                assert "role" in member
                assert "email" in member


# --- Schema header documentation ---


class TestSchemaHeaderDocs:
    def test_header_documents_arr(self):
        raw = _read_raw()
        assert "#   arr:" in raw

    def test_header_documents_contract_end(self):
        raw = _read_raw()
        assert "#   contract_end:" in raw

    def test_header_documents_renewal_date(self):
        raw = _read_raw()
        assert "#   renewal_date:" in raw

    def test_header_documents_account_team(self):
        raw = _read_raw()
        assert "#   account_team:" in raw

    def test_header_documents_cs_tier(self):
        raw = _read_raw()
        assert "#   cs_tier:" in raw

    def test_header_documents_subscription_plan(self):
        raw = _read_raw()
        assert "#   subscription_plan:" in raw


# --- Backward compatibility ---


class TestBackwardCompatibility:
    def test_no_bigquery_id_field(self):
        """No separate bigquery_id field -- sfdc_account_id IS the BigQuery ID."""
        gr = _get_gresearch(_load_yaml())
        assert "bigquery_id" not in gr

    def test_existing_jira_customer_unchanged(self):
        gr = _get_gresearch(_load_yaml())
        assert gr["jira_customer"] == "GResearch"

    def test_existing_deployment_type_unchanged(self):
        gr = _get_gresearch(_load_yaml())
        assert gr["deployment_type"] == "server"

    def test_existing_cadence_type_unchanged(self):
        gr = _get_gresearch(_load_yaml())
        assert gr["cadence"]["type"] == "weekly"

    def test_existing_contacts_preserved(self):
        gr = _get_gresearch(_load_yaml())
        names = [c["name"] for c in gr["contacts"]]
        assert "Allan Stevenson" in names


# --- YAML round-trip ---


class TestYAMLRoundTrip:
    def test_round_trip_preserves_data(self):
        """Load -> dump -> load should produce identical data structure."""
        data1 = _load_yaml()
        dumped = yaml.dump(data1, default_flow_style=False)
        data2 = yaml.safe_load(dumped)
        assert data1 == data2
