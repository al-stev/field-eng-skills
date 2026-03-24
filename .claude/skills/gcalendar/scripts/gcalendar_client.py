#!/usr/bin/env python3
"""
Google Calendar Apps Script client with CDP-based authentication.

Routes requests through the Chrome debug instance via CDP to handle
Okta SSO transparently. Provides api_call() for making requests and
handle_api_call() for automatic retry on transient errors.
"""

import json
import subprocess
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode


TSM_ENV = Path.home() / '.tsm-ai' / '.env'

# CDP fetch script path (relative to this file)
# __file__ = .claude/skills/gcalendar/scripts/gcalendar_client.py
CDP_FETCH_SCRIPT = Path(__file__).parent.parent.parent.parent.parent / 'scripts' / 'gmail-cdp-fetch.sh'


def _load_credential(key: str) -> str | None:
    """Read a single value from ~/.tsm-ai/.env."""
    if not TSM_ENV.exists():
        return None
    for line in TSM_ENV.read_text().splitlines():
        if line.startswith(f'{key}='):
            return line.split('=', 1)[1]
    return None


def get_session() -> tuple:
    """
    Load Apps Script URL and API key from ~/.tsm-ai/.env.

    Returns:
        Tuple of (base_url, api_key)

    Raises:
        FileNotFoundError: If credentials are missing
        ValueError: If credentials are empty or malformed
    """
    url = _load_credential('GCALENDAR_APPSCRIPT_URL')
    key = _load_credential('GCALENDAR_APPSCRIPT_KEY')

    if not url:
        raise FileNotFoundError(
            "GCALENDAR_APPSCRIPT_URL not found in ~/.tsm-ai/.env. Run /gcalendar-setup first."
        )
    if not key:
        raise FileNotFoundError(
            "GCALENDAR_APPSCRIPT_KEY not found in ~/.tsm-ai/.env. Run /gcalendar-setup first."
        )

    if not url.startswith('https://script.google.com/'):
        raise ValueError(
            f"Invalid Apps Script URL format. Expected https://script.google.com/..., "
            f"got: {url[:50]}..."
        )

    return url, key


def api_call(action: str, **params) -> dict:
    """
    Make an authenticated request to the Google Calendar Apps Script web app via CDP.

    Routes the request through the Chrome debug instance so Okta SSO
    is handled transparently by the browser.

    Args:
        action: The action to perform (listCalendars, getEvents, etc.)
        **params: Additional query parameters

    Returns:
        Parsed JSON response dict

    Raises:
        FileNotFoundError: If credential files don't exist
        RuntimeError: If CDP fetch fails
        Exception: If the Apps Script returns an error
    """
    url, key = get_session()

    query_params = {
        'key': key,
        'action': action,
    }
    query_params.update(params)

    full_url = f"{url}?{urlencode(query_params)}"

    if not CDP_FETCH_SCRIPT.exists():
        raise RuntimeError(
            f"CDP fetch script not found at {CDP_FETCH_SCRIPT}. "
            f"Ensure ./scripts/gmail-cdp-fetch.sh exists."
        )

    result = subprocess.run(
        [str(CDP_FETCH_SCRIPT), full_url],
        capture_output=True,
        text=True,
        timeout=90,
        cwd=CDP_FETCH_SCRIPT.parent.parent  # Run from project root
    )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if 'not running' in stderr:
            raise RuntimeError(
                f"Chrome debug instance not running. "
                f"Start it with: ./scripts/chrome-debug.sh start"
            )
        if 'Timeout' in stderr:
            raise RuntimeError(
                f"Timed out waiting for Apps Script response. "
                f"Ensure you are signed into Okta in the Chrome debug instance."
            )
        raise RuntimeError(f"CDP fetch failed: {stderr}")

    body = result.stdout.strip()
    if not body:
        raise RuntimeError("CDP fetch returned empty response.")

    data = json.loads(body)

    if not data.get('ok', False):
        error = data.get('error', 'unknown')
        message = data.get('message', 'Unknown error')
        raise Exception(f"Google Calendar Apps Script error: {error} - {message}")

    return data


def handle_api_call(api_func: Callable, *args, max_retries: int = 1, **kwargs) -> Any:
    """
    Wrapper for API calls with retry on transient errors.

    Args:
        api_func: The function to call
        max_retries: Number of retry attempts (default 1)
        *args, **kwargs: Arguments to pass to api_func

    Returns:
        Result from api_func

    Raises:
        Exception: If API call fails after retries
    """
    retry_count = 0

    while True:
        try:
            result = api_func(*args, **kwargs)
            return result

        except RuntimeError as e:
            # CDP/Chrome errors — retry once in case of transient issue
            if retry_count < max_retries and any(
                keyword in str(e).lower()
                for keyword in ['timeout', 'websocket']
            ):
                retry_count += 1
                continue
            raise

        except Exception as e:
            if retry_count < max_retries and any(
                keyword in str(e).lower()
                for keyword in ['timeout', 'connection', 'temporary']
            ):
                retry_count += 1
                continue
            raise
