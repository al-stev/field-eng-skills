#!/usr/bin/env python3
"""
Dashboard V2 Composition Pipeline.

Assembles template files (shell.html, panel JS, lib/) + INTELLIGENCE_DATA
into a working dashboard folder. Only data.js changes on each refresh —
shell and panel templates are stable.

Usage:
    uv run --project .claude/skills/customer-snapshot python \
        .claude/skills/customer-snapshot/templates/compose.py \
        --customer "Isomorphic Labs" --data /path/to/data.json --output /path/to/output

    Or programmatically:
        from compose import generate_dashboard
        result = generate_dashboard("Customer", data_dict, Path("/output"))
"""

import argparse
import json
import shutil
import sys
from datetime import date
from pathlib import Path

import yaml

# ── Path resolution (anchored to this file's location) ──
SCRIPT_DIR = Path(__file__).resolve().parent  # templates/
SKILL_DIR = SCRIPT_DIR.parent                 # customer-snapshot/
PROJECT_ROOT = SKILL_DIR.parents[2]           # project root


def resolve_key(data, dot_path):
    """Walk a dot-separated path through nested dicts.

    Handles `.length` suffix by returning len(value) if value is a list.
    Returns the value at the path, or None if any key is missing.

    >>> resolve_key({'a': {'b': 1}}, 'a.b')
    1
    >>> resolve_key({'a': {'b': [1, 2, 3]}}, 'a.b.length')
    3
    >>> resolve_key({}, 'missing.key')
    """
    if not data or not dot_path:
        return None
    parts = dot_path.split('.')
    current = data
    for part in parts:
        if part == 'length' and isinstance(current, list):
            return len(current)
        if not isinstance(current, dict):
            return None
        current = current.get(part)
        if current is None:
            return None
    return current


def generate_dashboard(customer_name, data, output_dir, echarts_path=None):
    """Generate a dashboard folder for a customer.

    Parameters:
        customer_name: Display name (e.g., "Isomorphic Labs")
        data: INTELLIGENCE_DATA dictionary
        output_dir: Target directory (e.g., customers/iso-labs/dashboard/)
        echarts_path: Path to echarts.min.js. If None, looks in SCRIPT_DIR/lib/.
                      If not found, logs warning and continues without it.

    Returns:
        Summary dict with output_dir, panels_active, panels_skipped, data_js_size_kb.
    """
    output_dir = Path(output_dir)

    # 1. Read panels.yaml manifest
    manifest_path = SCRIPT_DIR / 'panels.yaml'
    with open(manifest_path, 'r') as f:
        manifest = yaml.safe_load(f)

    # 2. Determine active panels
    active_panels = []
    skipped_panels = []
    for panel in sorted(manifest['panels'], key=lambda p: p.get('order', 99)):
        if panel.get('always_show'):
            active_panels.append(panel)
        elif panel.get('data_key') and resolve_key(data, panel['data_key']):
            active_panels.append(panel)
        else:
            skipped_panels.append(panel)

    # 3. Read shell.html template
    shell_path = SCRIPT_DIR / 'shell.html'
    shell_content = shell_path.read_text(encoding='utf-8')

    # 4. Replace {{CUSTOMER_NAME}}
    shell_content = shell_content.replace('{{CUSTOMER_NAME}}', customer_name)

    # 5. Replace {{GENERATED_DATE}}
    generated_date = date.today().strftime('%d %b %Y')
    shell_content = shell_content.replace('{{GENERATED_DATE}}', generated_date)

    # 6. Replace {{PANEL_SCRIPTS}} with script tags for active panels
    panel_script_tags = '\n'.join(
        f'<script src="panels/{p["id"]}.js"></script>'
        for p in active_panels
    )
    shell_content = shell_content.replace('{{PANEL_SCRIPTS}}', panel_script_tags)

    # 7. Create output directory structure
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'panels').mkdir(exist_ok=True)
    (output_dir / 'lib').mkdir(exist_ok=True)
    (output_dir / 'history').mkdir(exist_ok=True)

    # 12. History snapshot: save old data.js before overwriting
    data_js_path = output_dir / 'data.js'
    if data_js_path.exists():
        history_name = f'data-{date.today().isoformat()}.js'
        history_path = output_dir / 'history' / history_name
        if not history_path.exists():  # don't overwrite same-day snapshot
            shutil.copy2(data_js_path, history_path)

    # 8. Write index.html
    (output_dir / 'index.html').write_text(shell_content, encoding='utf-8')

    # 9. Write data.js
    data_js_content = f'const INTELLIGENCE_DATA = {json.dumps(data, default=str, indent=2)};'
    data_js_path.write_text(data_js_content, encoding='utf-8')

    # 10. Copy active panel JS files (skip if source doesn't exist)
    for panel in active_panels:
        src = SCRIPT_DIR / 'panels' / f'{panel["id"]}.js'
        if src.exists():
            shutil.copy2(src, output_dir / 'panels' / f'{panel["id"]}.js')

    # 11. Copy lib files
    for lib_file in ['chart-helpers.js', 'panel-registry.js']:
        src = SCRIPT_DIR / 'lib' / lib_file
        if src.exists():
            shutil.copy2(src, output_dir / 'lib' / lib_file)

    # Copy echarts.min.js (optional)
    echarts_src = None
    if echarts_path and Path(echarts_path).exists():
        echarts_src = Path(echarts_path)
    else:
        candidate = SCRIPT_DIR / 'lib' / 'echarts.min.js'
        if candidate.exists():
            echarts_src = candidate

    if echarts_src:
        shutil.copy2(echarts_src, output_dir / 'lib' / 'echarts.min.js')
    else:
        print(
            'WARNING: echarts.min.js not found -- skipping. '
            'Download from https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js '
            'and place at .claude/skills/customer-snapshot/templates/lib/echarts.min.js',
            file=sys.stderr
        )

    # 13. Compute summary
    data_js_size = len(data_js_content.encode('utf-8'))
    return {
        'output_dir': str(output_dir),
        'panels_active': [p['id'] for p in active_panels],
        'panels_skipped': [p['id'] for p in skipped_panels],
        'data_js_size_kb': data_js_size // 1024
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Compose v2 dashboard folder')
    parser.add_argument('--customer', required=True, help='Customer display name')
    parser.add_argument('--data', required=True, help='Path to JSON file with INTELLIGENCE_DATA')
    parser.add_argument('--output', required=True, help='Output directory path')
    args = parser.parse_args()

    data = json.loads(Path(args.data).read_text(encoding='utf-8'))
    result = generate_dashboard(args.customer, data, Path(args.output))
    print(json.dumps(result, indent=2))
