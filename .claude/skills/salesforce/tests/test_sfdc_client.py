"""Tests for sfdc_client.py — credential loading, client creation, error handling, output."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


class TestLoadCredential:
    """Tests for _load_credential function."""

    def test_reads_value_from_env_file(self, tmp_env_file):
        """_load_credential reads SFDC_USERNAME from mock env file, returns value after '='."""
        from sfdc_client import _load_credential

        with patch("sfdc_client.FE_ENV", tmp_env_file):
            result = _load_credential("SFDC_USERNAME")
        assert result == "test@example.com"

    def test_returns_none_when_key_not_found(self, tmp_env_file):
        """_load_credential returns None when key not found."""
        from sfdc_client import _load_credential

        with patch("sfdc_client.FE_ENV", tmp_env_file):
            result = _load_credential("NONEXISTENT_KEY")
        assert result is None

    def test_returns_none_when_env_file_missing(self, tmp_path):
        """_load_credential returns None when env file does not exist."""
        from sfdc_client import _load_credential

        missing = tmp_path / "nonexistent" / ".env"
        with patch("sfdc_client.FE_ENV", missing):
            result = _load_credential("SFDC_USERNAME")
        assert result is None


class TestGetClient:
    """Tests for get_client function."""

    def test_raises_when_credentials_missing(self, tmp_env_file_missing_creds):
        """get_client raises FileNotFoundError when credentials missing, message contains 'Run /salesforce-setup first'."""
        from sfdc_client import get_client

        with patch("sfdc_client.FE_ENV", tmp_env_file_missing_creds):
            with pytest.raises(FileNotFoundError, match="Run /salesforce-setup first"):
                get_client()

    def test_returns_salesforce_instance(self, tmp_env_file):
        """get_client returns Salesforce instance when all 3 credentials present."""
        from sfdc_client import get_client

        mock_sf = MagicMock()
        with (
            patch("sfdc_client.FE_ENV", tmp_env_file),
            patch("sfdc_client.Salesforce", return_value=mock_sf) as mock_cls,
        ):
            client = get_client()

        assert client is mock_sf
        mock_cls.assert_called_once_with(
            username="test@example.com",
            password="testpass123",
            security_token="abcdef123456",
            domain="login",
        )

    def test_passes_custom_domain(self, tmp_env_file_with_domain):
        """get_client passes optional SFDC_DOMAIN to Salesforce constructor when present in env."""
        from sfdc_client import get_client

        mock_sf = MagicMock()
        with (
            patch("sfdc_client.FE_ENV", tmp_env_file_with_domain),
            patch("sfdc_client.Salesforce", return_value=mock_sf) as mock_cls,
        ):
            client = get_client()

        assert client is mock_sf
        mock_cls.assert_called_once_with(
            username="test@example.com",
            password="testpass123",
            security_token="abcdef123456",
            domain="wandb.my",
        )

    def test_defaults_domain_to_login(self, tmp_env_file):
        """get_client defaults domain to 'login' when SFDC_DOMAIN not in env."""
        from sfdc_client import get_client

        with (
            patch("sfdc_client.FE_ENV", tmp_env_file),
            patch("sfdc_client.Salesforce") as mock_cls,
        ):
            get_client()

        _, kwargs = mock_cls.call_args
        assert kwargs["domain"] == "login"


class TestHandleApiCall:
    """Tests for handle_api_call function."""

    def test_returns_result_on_success(self):
        """handle_api_call returns result on success."""
        from sfdc_client import handle_api_call

        mock_func = MagicMock(return_value={"records": []})
        result = handle_api_call(mock_func, "arg1", key="val")
        assert result == {"records": []}
        mock_func.assert_called_once_with("arg1", key="val")

    def test_catches_auth_failed(self):
        """handle_api_call catches SalesforceAuthenticationFailed and raises with setup message."""
        from simple_salesforce.exceptions import SalesforceAuthenticationFailed
        from sfdc_client import handle_api_call

        mock_func = MagicMock(
            side_effect=SalesforceAuthenticationFailed(401, "Bad credentials")
        )
        with pytest.raises(SalesforceAuthenticationFailed, match="/salesforce-setup"):
            handle_api_call(mock_func)

    def test_catches_invalid_field(self):
        """handle_api_call catches INVALID_FIELD errors and suggests describe command."""
        from simple_salesforce.exceptions import SalesforceMalformedRequest
        from sfdc_client import handle_api_call

        mock_func = MagicMock(
            side_effect=SalesforceMalformedRequest(
                "url", 400, "resource",
                [{"message": "INVALID_FIELD: No such column 'Bad_Field__c'", "errorCode": "INVALID_FIELD"}]
            )
        )
        with pytest.raises(SalesforceMalformedRequest, match="describe"):
            handle_api_call(mock_func)


class TestOutputJson:
    """Tests for output_json function."""

    def test_prints_compact_json(self, capsys):
        """output_json prints compact JSON to stdout."""
        from sfdc_client import output_json

        output_json({"key": "value", "count": 42})
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed == {"key": "value", "count": 42}
        assert "\n" not in captured.out.strip()

    def test_prints_pretty_json(self, capsys):
        """output_json prints pretty JSON with indent=2 when pretty=True."""
        from sfdc_client import output_json

        output_json({"key": "value"}, pretty=True)
        captured = capsys.readouterr()
        assert "  " in captured.out  # indented
        parsed = json.loads(captured.out)
        assert parsed == {"key": "value"}


class TestOutputError:
    """Tests for output_error function."""

    def test_prints_error_to_stderr(self, capsys):
        """output_error prints error JSON to stderr with ok=False."""
        from sfdc_client import output_error

        output_error("auth_failed", "Bad credentials")
        captured = capsys.readouterr()
        assert captured.out == ""  # nothing on stdout
        parsed = json.loads(captured.err)
        assert parsed == {
            "ok": False,
            "error": "auth_failed",
            "message": "Bad credentials",
        }
