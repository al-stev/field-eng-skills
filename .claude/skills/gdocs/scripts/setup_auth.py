#!/usr/bin/env python3
"""
Google Docs Apps Script setup helper.

Saves the Apps Script web app URL and API key to ~/.fe-skills/.env,
then verifies connectivity via CDP (Chrome debug instance).

Usage:
    setup_auth.py --url "https://script.google.com/.../exec" --key "YOUR_KEY"
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


TSM_ENV = Path.home() / '.fe-skills' / '.env'

# CDP fetch script path (relative to this file)
CDP_FETCH_SCRIPT = Path(__file__).parent.parent.parent.parent.parent / 'scripts' / 'gmail-cdp-fetch.sh'


def _save_credential(key: str, value: str) -> None:
    """Upsert a key=value in ~/.fe-skills/.env."""
    env_dir = TSM_ENV.parent
    env_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(str(env_dir), 0o700)

    lines = TSM_ENV.read_text().splitlines() if TSM_ENV.exists() else []
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f'{key}='):
            lines[i] = f'{key}={value}'
            found = True
            break
    if not found:
        lines.append(f'{key}={value}')
    TSM_ENV.write_text('\n'.join(lines) + '\n')
    os.chmod(str(TSM_ENV), 0o600)


def main():
    parser = argparse.ArgumentParser(
        description='Save Google Docs Apps Script credentials and verify connectivity'
    )
    parser.add_argument(
        '--url',
        required=True,
        help='Apps Script web app URL (https://script.google.com/.../exec)'
    )
    parser.add_argument(
        '--key',
        required=True,
        help='API key configured in the Apps Script'
    )

    args = parser.parse_args()

    # Validate URL format
    if not args.url.startswith('https://script.google.com/'):
        print(json.dumps({
            "ok": False,
            "error": "invalid_url",
            "message": f"URL must start with https://script.google.com/, got: {args.url[:50]}..."
        }), file=sys.stderr)
        sys.exit(1)

    # Save credentials to ~/.fe-skills/.env
    _save_credential('GDOCS_APPSCRIPT_URL', args.url)
    _save_credential('GDOCS_APPSCRIPT_KEY', args.key)

    # Verify via CDP fetch
    if not CDP_FETCH_SCRIPT.exists():
        print(json.dumps({
            "ok": True,
            "message": "Credentials saved (verification skipped — CDP fetch script not found)",
            "env_path": str(TSM_ENV),
        }, indent=2))
        sys.exit(0)

    from urllib.parse import urlencode
    test_url = f"{args.url}?{urlencode({'key': args.key, 'action': 'ping'})}"

    try:
        result = subprocess.run(
            [str(CDP_FETCH_SCRIPT), test_url],
            capture_output=True,
            text=True,
            timeout=90,
            cwd=CDP_FETCH_SCRIPT.parent.parent
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            if 'not running' in stderr:
                print(json.dumps({
                    "ok": True,
                    "message": "Credentials saved. Verification skipped — Chrome debug instance not running. "
                               "Start it with: ./scripts/chrome-debug.sh start",
                    "env_path": str(TSM_ENV),
                }, indent=2))
                sys.exit(0)

            print(json.dumps({
                "ok": False,
                "error": "verification_failed",
                "message": f"Credentials saved but verification failed: {stderr}",
                "env_path": str(TSM_ENV),
            }), file=sys.stderr)
            sys.exit(1)

        body = result.stdout.strip()
        data = json.loads(body)

        if not data.get('ok'):
            error = data.get('error', 'unknown')
            message = data.get('message', 'Unknown error')
            print(json.dumps({
                "ok": False,
                "error": error,
                "message": f"Apps Script returned error: {message}. Check your URL and API key.",
                "env_path": str(TSM_ENV),
            }), file=sys.stderr)
            sys.exit(1)

        print(json.dumps({
            "ok": True,
            "message": "Google Docs Apps Script setup successful",
            "env_path": str(TSM_ENV),
        }, indent=2))

        sys.exit(0)

    except subprocess.TimeoutExpired:
        print(json.dumps({
            "ok": False,
            "error": "timeout",
            "message": "Credentials saved but verification timed out. "
                       "Ensure you are signed into Okta in the Chrome debug instance.",
            "env_path": str(TSM_ENV),
        }), file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(json.dumps({
            "ok": False,
            "error": "setup_failed",
            "message": f"Credentials saved but verification failed: {e}",
            "env_path": str(TSM_ENV),
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
