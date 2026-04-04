#!/usr/bin/env python3
"""
Gong client with dual authentication: cookie-based HTTP and CDP fetch fallback.

Primary approach: Use session cookies extracted from the Chrome debug instance
to call Gong's internal web app API endpoints directly via requests.

Fallback approach: Route requests through the Chrome debug instance via CDP
(gmail-cdp-fetch.sh) which handles Okta SSO transparently.

Provides get_session() for cookie-based HTTP, cdp_fetch() for CDP-routed
requests, and handle_api_call() for automatic retry on auth failures.
"""

import json
import subprocess
from pathlib import Path
from typing import Any, Callable

import requests


TSM_ENV = Path.home() / '.tsm-ai' / '.env'


def _load_credential(key: str) -> str | None:
    """Read a single value from ~/.tsm-ai/.env."""
    if not TSM_ENV.exists():
        return None
    for line in TSM_ENV.read_text().splitlines():
        if line.startswith(f'{key}='):
            return line.split('=', 1)[1]
    return None


# Script paths (relative to this file)
# __file__ = .claude/skills/gong/scripts/gong_client.py
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
COOKIE_REFRESH_SCRIPT = PROJECT_ROOT / 'scripts' / 'gong-cookie-refresh.sh'
CDP_FETCH_SCRIPT = PROJECT_ROOT / 'scripts' / 'gmail-cdp-fetch.sh'

# Gong instance configuration -- loaded from ~/.tsm-ai/.env (no hardcoded fallbacks)
# Set via /gong-setup: GONG_BASE_URL (e.g. https://us-39259.app.gong.io)
#                      GONG_WORKSPACE_ID (found in DevTools network tab workspace-id= param)
GONG_BASE_URL = _load_credential('GONG_BASE_URL')
WORKSPACE_ID = _load_credential('GONG_WORKSPACE_ID')


def _require_gong_config() -> tuple[str, str]:
    """
    Validate that GONG_BASE_URL and GONG_WORKSPACE_ID are configured.

    Returns:
        Tuple of (base_url, workspace_id)

    Raises:
        ValueError: If either credential is missing
    """
    if not GONG_BASE_URL:
        raise ValueError(
            "GONG_BASE_URL not found in ~/.tsm-ai/.env. "
            "Run /gong-setup to configure."
        )
    if not WORKSPACE_ID:
        raise ValueError(
            "GONG_WORKSPACE_ID not found in ~/.tsm-ai/.env. "
            "Run /gong-setup to configure."
        )
    return GONG_BASE_URL, WORKSPACE_ID


def get_session() -> requests.Session:
    """
    Create a requests Session with Gong session cookies.

    Returns:
        requests.Session configured with Gong cookies

    Raises:
        FileNotFoundError: If GONG_COOKIE not found
        ValueError: If GONG_BASE_URL or GONG_WORKSPACE_ID not configured
    """
    base_url, _ = _require_gong_config()

    cookie_header = _load_credential('GONG_COOKIE')

    if not cookie_header:
        raise FileNotFoundError(
            "GONG_COOKIE not found in ~/.tsm-ai/.env. Run /gong-setup first."
        )

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'gong-skill-python/0.1.0',
        'Accept': 'application/json',
    })

    # Parse "name1=value1; name2=value2" cookie header into session cookies
    for pair in cookie_header.split('; '):
        if '=' in pair:
            name, value = pair.split('=', 1)
            # Extract domain from GONG_BASE_URL (e.g. 'us-54638.app.gong.io')
            from urllib.parse import urlparse
            domain = urlparse(base_url).hostname or 'app.gong.io'
            session.cookies.set(name.strip(), value.strip(), domain=domain)

    return session


def cdp_fetch(url: str, timeout: int = 90) -> str:
    """
    Fetch a URL through the Chrome debug instance via CDP.

    Chrome handles Okta SSO transparently. Returns the page body as a string.
    If the response is JSON, caller should parse it.

    Args:
        url: Full URL to fetch
        timeout: Subprocess timeout in seconds

    Returns:
        Page body text (may be JSON or HTML)

    Raises:
        RuntimeError: If CDP fetch fails
    """
    if not CDP_FETCH_SCRIPT.exists():
        raise RuntimeError(
            f"CDP fetch script not found at {CDP_FETCH_SCRIPT}. "
            f"Ensure ./scripts/gmail-cdp-fetch.sh exists."
        )

    result = subprocess.run(
        [str(CDP_FETCH_SCRIPT), url],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(PROJECT_ROOT),
    )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if 'not running' in stderr:
            raise RuntimeError(
                "Chrome debug instance not running. "
                "Start it with: ./scripts/chrome-debug.sh start"
            )
        if 'Timeout' in stderr:
            raise RuntimeError(
                "Timed out waiting for Gong response. "
                "Ensure you are signed into Okta in the Chrome debug instance."
            )
        raise RuntimeError(f"CDP fetch failed: {stderr}")

    body = result.stdout.strip()
    if not body:
        raise RuntimeError("CDP fetch returned empty response.")

    return body


def refresh_credentials() -> None:
    """Refresh Gong cookies by calling the cookie refresh script."""
    if not COOKIE_REFRESH_SCRIPT.exists():
        raise RuntimeError(
            f"Cookie refresh script not found at {COOKIE_REFRESH_SCRIPT}. "
            f"Ensure ./scripts/gong-cookie-refresh.sh exists."
        )

    result = subprocess.run(
        [str(COOKIE_REFRESH_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Cookie refresh failed:\n{result.stderr}\n{result.stdout}"
        )


def handle_api_call(api_func: Callable, *args, max_retries: int = 1, **kwargs) -> Any:
    """
    Wrapper for API calls with automatic credential refresh on auth failure.

    Args:
        api_func: The function to call
        max_retries: Number of refresh attempts (default 1)
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

        except requests.HTTPError as e:
            if e.response.status_code in (401, 403) and retry_count < max_retries:
                refresh_credentials()
                retry_count += 1
                continue
            raise

        except RuntimeError as e:
            # CDP/Chrome errors — retry once in case of transient issue
            if retry_count < max_retries and any(
                keyword in str(e).lower()
                for keyword in ['timeout', 'websocket', 'auth', 'unauthorized']
            ):
                refresh_credentials()
                retry_count += 1
                continue
            raise

        except Exception as e:
            if retry_count < max_retries and any(
                keyword in str(e).lower()
                for keyword in ['timeout', 'connection', 'temporary', 'auth']
            ):
                refresh_credentials()
                retry_count += 1
                continue
            raise
