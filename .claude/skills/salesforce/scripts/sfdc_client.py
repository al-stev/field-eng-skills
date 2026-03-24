#!/usr/bin/env python3
"""
Salesforce client with ~/.tsm-ai/.env authentication support.

Provides get_client() for authenticated Salesforce API access and handle_api_call()
for structured error handling. Auth uses username/password/security_token from
SFDC_USERNAME, SFDC_PASSWORD, SFDC_SECURITY_TOKEN in ~/.tsm-ai/.env, configured
by /salesforce-setup.
"""

import json
import sys
from pathlib import Path
from typing import Any, Callable

from simple_salesforce import Salesforce
from simple_salesforce.exceptions import (
    SalesforceAuthenticationFailed,
    SalesforceMalformedRequest,
)


# Constants
TSM_ENV = Path.home() / '.tsm-ai' / '.env'

_env_perms_warned = False


def _check_env_permissions() -> None:
    """Warn once if ~/.tsm-ai/.env has permissions more open than 600."""
    global _env_perms_warned
    if _env_perms_warned or not TSM_ENV.exists():
        return
    mode = TSM_ENV.stat().st_mode & 0o777
    if mode & 0o077:  # group or other has any access
        print(
            f"WARNING: {TSM_ENV} has permissions {oct(mode)} (expected 0o600). "
            f"Run: chmod 600 {TSM_ENV}",
            file=sys.stderr,
        )
        _env_perms_warned = True


def _load_credential(key: str) -> str | None:
    """Read a single value from ~/.tsm-ai/.env."""
    if not TSM_ENV.exists():
        return None
    _check_env_permissions()
    for line in TSM_ENV.read_text().splitlines():
        if line.startswith(f'{key}='):
            return line.split('=', 1)[1]
    return None


def get_client() -> Salesforce:
    """
    Create a Salesforce client using ~/.tsm-ai/.env credentials.

    Supports two auth modes (checked in order):
    1. Session-based (SSO/2FA): SFDC_SESSION_ID + SFDC_INSTANCE
    2. Username/password: SFDC_USERNAME + SFDC_PASSWORD + SFDC_SECURITY_TOKEN

    Returns:
        Salesforce client

    Raises:
        FileNotFoundError: If no valid credential set is found
    """
    # Mode 1: Session-based auth (for SSO/2FA environments)
    session_id = _load_credential('SFDC_SESSION_ID')
    instance = _load_credential('SFDC_INSTANCE')

    if session_id and instance:
        return Salesforce(session_id=session_id, instance=instance)

    # Mode 2: Username/password/token auth
    username = _load_credential('SFDC_USERNAME')
    password = _load_credential('SFDC_PASSWORD')
    security_token = _load_credential('SFDC_SECURITY_TOKEN')
    domain = _load_credential('SFDC_DOMAIN') or 'login'

    if all([username, password, security_token]):
        return Salesforce(
            username=username,
            password=password,
            security_token=security_token,
            domain=domain,
        )

    raise FileNotFoundError(
        "SFDC credentials not found in ~/.tsm-ai/.env. "
        "Need either SFDC_SESSION_ID + SFDC_INSTANCE (session auth) "
        "or SFDC_USERNAME + SFDC_PASSWORD + SFDC_SECURITY_TOKEN (password auth). "
        "Run /salesforce-setup first."
    )


def handle_api_call(api_func: Callable, *args, **kwargs) -> Any:
    """
    Wrapper for Salesforce API calls with structured error handling.

    Args:
        api_func: The Salesforce SDK method to call
        *args, **kwargs: Arguments to pass to api_func

    Returns:
        Result from api_func

    Raises:
        SalesforceAuthenticationFailed: Re-raised with setup message
        SalesforceMalformedRequest: Re-raised with describe suggestion for INVALID_FIELD
        Exception: For other errors
    """
    try:
        return api_func(*args, **kwargs)
    except SalesforceAuthenticationFailed:
        raise SalesforceAuthenticationFailed(
            401,
            "Authentication failed. Check credentials in ~/.tsm-ai/.env. "
            "Run /salesforce-setup to reconfigure.",
        )
    except SalesforceMalformedRequest as e:
        # Check if it's an INVALID_FIELD error
        content = str(e.content) if hasattr(e, 'content') else str(e)
        if "INVALID_FIELD" in content:
            raise SalesforceMalformedRequest(
                e.url,
                e.status,
                e.resource_name,
                f"INVALID_FIELD error. Run 'accounts.py describe' to discover "
                f"correct field names. Original: {e.content}",
            )
        raise


def output_json(data: Any, pretty: bool = False) -> None:
    """Print JSON to stdout."""
    if pretty:
        print(json.dumps(data, indent=2, default=str))
    else:
        print(json.dumps(data, default=str))


def output_error(error_type: str, message: str) -> None:
    """Print structured error JSON to stderr."""
    print(json.dumps({
        "ok": False,
        "error": error_type,
        "message": message
    }), file=sys.stderr)
