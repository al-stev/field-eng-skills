#!/usr/bin/env python3
"""
Slack WebClient with xoxc token and d cookie support.

Provides get_client() for authenticated Slack API access and handle_api_call()
for automatic credential refresh on auth failures.
"""

import subprocess
from pathlib import Path
from typing import Any, Callable

from slack_sdk import WebClient
from slack_sdk.http_retry import RetryHandler
from slack_sdk.http_retry.builtin_interval_calculators import BackoffRetryIntervalCalculator
from slack_sdk.http_retry.request import HttpRequest
from slack_sdk.http_retry.response import HttpResponse
from slack_sdk.http_retry.state import RetryState


TSM_ENV = Path.home() / '.tsm-ai' / '.env'


def _load_credential(key: str) -> str | None:
    """Read a single value from ~/.tsm-ai/.env."""
    if not TSM_ENV.exists():
        return None
    for line in TSM_ENV.read_text().splitlines():
        if line.startswith(f'{key}='):
            return line.split('=', 1)[1]
    return None


def get_client() -> WebClient:
    """
    Create a Slack WebClient with xoxc token and d cookie support.

    Reads credentials from ~/.tsm-ai/.env (SLACK_TOKEN, SLACK_COOKIE).

    Returns:
        WebClient configured with cookie header injection

    Raises:
        FileNotFoundError: If credentials are missing
        ValueError: If credentials are empty or malformed
    """
    token = _load_credential('SLACK_TOKEN')
    cookie = _load_credential('SLACK_COOKIE')

    if not token:
        raise FileNotFoundError(
            "SLACK_TOKEN not found in ~/.tsm-ai/.env. Run /slack-setup first."
        )
    if not cookie:
        raise FileNotFoundError(
            "SLACK_COOKIE not found in ~/.tsm-ai/.env. Run /slack-setup first."
        )

    if not token.startswith('xoxc-'):
        raise ValueError(
            f"Invalid token format. Expected xoxc- prefix, got: {token[:10]}..."
        )
    if not cookie.startswith('xoxd-'):
        raise ValueError(
            f"Invalid cookie format. Expected xoxd- prefix, got: {cookie[:10]}..."
        )

    # Create WebClient with cookie header
    # The 'd' cookie is required for xoxc- tokens to work
    headers = {
        'Cookie': f'd={cookie}'
    }

    return WebClient(token=token, headers=headers)


def refresh_credentials() -> None:
    """
    Refresh Slack credentials by calling the credential refresh script.

    Raises:
        RuntimeError: If refresh script fails
    """
    # Find the refresh script relative to the skill root
    # Path: scripts/ -> slack/ -> skills/ -> .claude/ -> project_root/ -> scripts/
    script_path = Path(__file__).parent.parent.parent.parent.parent / 'scripts' / 'slack-credential-refresh.sh'

    if not script_path.exists():
        raise RuntimeError(
            f"Credential refresh script not found at {script_path}. "
            f"Ensure ./scripts/slack-credential-refresh.sh exists."
        )

    result = subprocess.run(
        [str(script_path)],
        capture_output=True,
        text=True,
        cwd=script_path.parent.parent  # Run from project root
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Credential refresh failed:\n{result.stderr}\n{result.stdout}"
        )


def handle_api_call(api_func: Callable, *args, max_retries: int = 1, **kwargs) -> Any:
    """
    Wrapper for Slack API calls with automatic credential refresh on auth failure.

    Args:
        api_func: The Slack SDK method to call (e.g., client.search_messages)
        max_retries: Number of refresh attempts on auth failure (default 1)
        *args, **kwargs: Arguments to pass to api_func

    Returns:
        API response dict

    Raises:
        Exception: If API call fails after refresh or for non-auth errors
    """
    retry_count = 0

    while True:
        try:
            response = api_func(*args, **kwargs)

            # Slack always returns HTTP 200, check ok field
            if not response.get('ok', False):
                error = response.get('error', 'unknown')

                # Auth errors trigger refresh
                if error in ('invalid_auth', 'token_expired', 'not_authed'):
                    if retry_count < max_retries:
                        refresh_credentials()
                        retry_count += 1
                        # Recreate client with fresh credentials and retry
                        # Note: The caller will need to get a new client
                        # For now, just raise to let the tool handle it
                        raise Exception(f"Credentials expired. Please retry - credentials have been refreshed.")

                # Other errors or max retries reached
                raise Exception(f"Slack API error: {error}")

            return response

        except Exception as e:
            # Catch SDK exceptions that might indicate auth issues
            if retry_count < max_retries and any(
                keyword in str(e).lower()
                for keyword in ['auth', 'token', 'unauthorized', 'forbidden']
            ):
                refresh_credentials()
                retry_count += 1
                # Recreate client - caller needs to retry
                raise Exception(f"Credentials expired. Please retry - credentials have been refreshed.")
            raise
