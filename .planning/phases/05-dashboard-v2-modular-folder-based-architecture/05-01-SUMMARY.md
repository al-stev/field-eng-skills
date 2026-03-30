---
phase: 05-dashboard-v2-modular-folder-based-architecture
plan: 01
subsystem: ui
tags: [echarts, vanilla-js, css-custom-properties, pyyaml, dashboard, composition-pipeline]

# Dependency graph
requires: []
provides:
  - "Dashboard shell HTML template with sidebar, router, command palette, and complete CSS design system"
  - "PanelRegistry JS library with register/get/getAll/renderPanel/injectCSS API"
  - "ChartHelpers JS library with createChart/resizeAll/tooltipConfig/wandb theme"
  - "panels.yaml declarative manifest with 6 panels in 3 groups"
  - "compose.py pipeline assembling templates + data into working dashboard folder"
affects: [05-02, 05-03, 05-04, 05-05, 05-06]

# Tech tracking
tech-stack:
  added: [pyyaml]
  patterns: [folder-based-dashboard, panel-registration-contract, css-scoping-via-id-prefix, template-placeholder-replacement, dot-path-key-resolution]

key-files:
  created:
    - ".claude/skills/customer-snapshot/templates/shell.html"
    - ".claude/skills/customer-snapshot/templates/lib/panel-registry.js"
    - ".claude/skills/customer-snapshot/templates/lib/chart-helpers.js"
    - ".claude/skills/customer-snapshot/templates/panels.yaml"
    - ".claude/skills/customer-snapshot/templates/compose.py"
    - ".claude/skills/customer-snapshot/pyproject.toml"
  modified: []

key-decisions:
  - "Font weights 400+600 only (per UI-SPEC consolidation, no 300/500/700)"
  - "Nav labels use font-weight 600 (semibold) for scannable anchors"
  - "Badge font-size 11px with weight 600 (per UI-SPEC mono tier)"
  - "Sidebar footer font-size 11px (consolidated from 10px/9px prototype)"
  - "Panel containers created dynamically by JS, not hardcoded in HTML"
  - "compose.py uses Path(__file__).resolve().parent for anchoring (not cwd)"
  - "echarts.min.js graceful skip with warning if not present locally"
  - "Added pyproject.toml to customer-snapshot skill for pyyaml dependency"

patterns-established:
  - "Panel contract: PanelRegistry.register({id, render, getHeadlineStats, getAttentionItems})"
  - "CSS scoping: PanelRegistry.injectCSS(id, cssText) prepends #panel-{id} to selectors"
  - "Template placeholders: {{CUSTOMER_NAME}}, {{GENERATED_DATE}}, {{PANEL_SCRIPTS}}"
  - "Data injection: const INTELLIGENCE_DATA = {...}; in data.js (no ES modules, file:// safe)"
  - "Script load order: echarts -> chart-helpers -> panel-registry -> data.js -> panel scripts"
  - "resolve_key(data, 'a.b.length') for dot-path traversal with .length support"

requirements-completed: [DASH-01, DASH-02, DASH-03, DASH-04, DASH-12]

# Metrics
duration: 10min
completed: 2026-03-30
---

# Phase 05 Plan 01: Dashboard V2 Infrastructure Summary

**Shell HTML template with sidebar/router/command palette, PanelRegistry + ChartHelpers JS libraries, panels.yaml manifest, and compose.py pipeline producing working dashboard folders from templates + data**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-27T16:13:09Z
- **Completed:** 2026-03-30T00:00:00Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- Complete CSS design system with dark/light mode, orange/gray tokens, and 10 semantic chart color aliases
- PanelRegistry with register/get/getAll/renderPanel/injectCSS API, ChartHelpers with createChart/resizeAll/tooltipConfig and wandb ECharts theme
- compose.py pipeline that reads panels.yaml manifest, determines active panels, replaces template placeholders, and assembles a working dashboard folder with index.html, data.js, lib/, panels/, and history/
- End-to-end test verified: compose.py produces correct output with customer name in index.html and INTELLIGENCE_DATA in data.js

## Task Commits

Each task was committed atomically:

1. **Task 1: Panel registry, chart helpers, and panels.yaml manifest** - `d24952e` (feat)
2. **Task 2: Shell HTML template with sidebar, router, and command palette** - `d22b6e7` (feat)
3. **Task 3: compose.py composition pipeline with end-to-end test** - `a9f6238` (feat)

## Files Created/Modified
- `.claude/skills/customer-snapshot/templates/lib/panel-registry.js` - Panel registration contract with register/get/getAll/renderPanel/injectCSS
- `.claude/skills/customer-snapshot/templates/lib/chart-helpers.js` - Shared ECharts utilities with wandb theme, tooltipConfig, axisLabelConfig, resize tracking
- `.claude/skills/customer-snapshot/templates/panels.yaml` - Declarative manifest: 3 groups (intelligence, usage, activity), 6 panels with data_key/badge_key/order
- `.claude/skills/customer-snapshot/templates/shell.html` - Dashboard shell with complete CSS design system, sidebar, hash router, command palette, keyboard shortcuts
- `.claude/skills/customer-snapshot/templates/compose.py` - Composition pipeline: reads manifest, replaces placeholders, writes dashboard folder
- `.claude/skills/customer-snapshot/pyproject.toml` - Skill dependency config with pyyaml

## Decisions Made
- Font weights consolidated to 400+600 only per UI-SPEC checker revision (removed 300/500/700 from Google Fonts URL)
- Nav label weight set to 600 (semibold) for active element hierarchy, per UI-SPEC weight consolidation
- Panel containers created dynamically by buildSidebar() JS rather than hardcoded in HTML, allowing data-driven panel visibility
- compose.py anchors paths via `Path(__file__).resolve().parent`, matching the established pattern from deep-analytics generate.py
- echarts.min.js handled gracefully: compose.py warns to stderr and continues if not found (does not crash)
- Created pyproject.toml for customer-snapshot skill to provide pyyaml dependency for uv run

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created pyproject.toml for customer-snapshot skill**
- **Found during:** Task 3 (compose.py)
- **Issue:** compose.py requires pyyaml but customer-snapshot skill had no pyproject.toml, so `uv run --project` could not install dependencies
- **Fix:** Created minimal pyproject.toml with pyyaml>=6.0 dependency and hatch build config pointing to templates/
- **Files modified:** .claude/skills/customer-snapshot/pyproject.toml
- **Verification:** `uv run --project .claude/skills/customer-snapshot python3 -c "import yaml"` succeeds
- **Committed in:** a9f6238 (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential for compose.py to run via uv. No scope creep.

## Issues Encountered
- Task 1 files (panel-registry.js, chart-helpers.js, panels.yaml) already existed as untracked files from a prior scaffolding session. Verified they matched all acceptance criteria and committed as-is rather than rewriting.

## Known Stubs
None. All infrastructure files are fully functional. Panel JS files (overview.js, issues.js, etc.) do not exist yet -- they are the subject of Plans 02-06 and compose.py correctly skips missing panel source files.

## Next Phase Readiness
- All infrastructure ready for panel development in Plans 02-06
- Panel authors can call `PanelRegistry.register()` with the documented contract
- compose.py can assemble dashboards once panel JS files are created
- echarts.min.js needs to be downloaded and placed in templates/lib/ before charts will render (compose.py warns if missing)

## Self-Check: PASSED

All 6 created files verified present on disk. All 3 task commit hashes verified in git log.

---
*Phase: 05-dashboard-v2-modular-folder-based-architecture*
*Completed: 2026-03-30*
