---
phase: quick
plan: 260401-kd6
subsystem: customer-snapshot
tags: [python, cli, normalization, jira, asana, bigquery, intelligence-data]

# Dependency graph
requires:
  - phase: 05-dashboard-v2
    provides: compose.py pipeline, INTELLIGENCE_DATA schema, panels/issues.js normalization maps
provides:
  - Deterministic INTELLIGENCE_DATA assembly script (assemble.py)
  - Unit tests for normalization, theme assignment, trending, graceful degradation
  - Updated SKILL.md Step 7 referencing assemble.py
affects: [customer-snapshot, customer-snapshot-skill]

# Tech tracking
tech-stack:
  added: [pytest (dev dependency for customer-snapshot)]
  patterns: [deterministic data assembly replacing LLM stitching, 3-tier theme cascade, graceful degradation stubs]

key-files:
  created:
    - .claude/skills/customer-snapshot/templates/assemble.py
    - .claude/skills/customer-snapshot/templates/test_assemble.py
  modified:
    - .claude/skills/customer-snapshot/SKILL.md
    - .claude/skills/customer-snapshot/pyproject.toml

key-decisions:
  - "Normalization maps copied verbatim from issues.js (31 component + 8 parent entries) -- JS remains source of truth"
  - "Asana stale-exempt sections include Waiting on Customer, Waiting on Eng, Scheduled/Future, Done -- matches asana.md rules"
  - "Trending uses calendar month bucketing (not rolling windows) for opened/closed counts"

patterns-established:
  - "assemble.py CLI pattern: --jira/--bq/--asana/--sentiment file args with graceful None handling"
  - "Graceful degradation: missing data sources produce {available: false, reason: 'not_provided'} stubs"

requirements-completed: []

# Metrics
duration: 5min
completed: 2026-04-01
---

# Quick Task 260401-kd6: Build assemble.py for Customer Snapshot Summary

**Deterministic INTELLIGENCE_DATA assembler replacing manual LLM stitching -- component/parent normalization, theme cascade, trending metrics, Asana transformation, and graceful degradation for missing data sources**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-01T13:43:34Z
- **Completed:** 2026-04-01T13:48:34Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Built assemble.py with CLI interface accepting --jira, --bq, --asana, --sentiment JSON file args
- 31 component + 8 parent normalization maps verified identical to issues.js counterparts
- 45 unit tests covering normalization, theme cascade, priority mapping, trending, Asana transformation, graceful degradation, full assembly, and CLI output
- Updated SKILL.md Step 7 from manual Claude assembly to assemble.py invocation

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests** - `5b7750e` (test)
2. **Task 1 GREEN: assemble.py implementation** - `96c66d4` (feat)
3. **Task 2: Update SKILL.md Step 7** - `a8ed293` (docs)

_TDD cycle: RED (failing tests) -> GREEN (implementation passing all 45 tests)_

## Files Created/Modified
- `.claude/skills/customer-snapshot/templates/assemble.py` - Deterministic INTELLIGENCE_DATA assembler (564 lines, stdlib-only)
- `.claude/skills/customer-snapshot/templates/test_assemble.py` - 45 unit tests across 9 test classes
- `.claude/skills/customer-snapshot/SKILL.md` - Step 7 updated to reference assemble.py with CLI usage
- `.claude/skills/customer-snapshot/pyproject.toml` - Added pytest dev dependency group

## Decisions Made
- Normalization maps copied verbatim from issues.js (31 component + 8 parent entries) -- JS remains source of truth; Python must be updated if JS maps change
- Asana stale-exempt sections match asana.md conventions (Waiting on Customer/Eng, Scheduled/Future, Done)
- Trending uses calendar month bucketing for opened/closed counts, consistent with existing dashboard velocity charts
- No new runtime dependencies needed -- stdlib only (json, argparse, datetime, statistics, re, pathlib)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added pytest dev dependency to pyproject.toml**
- **Found during:** Task 1 (test infrastructure check)
- **Issue:** pytest not available in customer-snapshot project venv, cannot run TDD
- **Fix:** Added `[dependency-groups] dev = ["pytest>=8.0"]` to pyproject.toml
- **Files modified:** .claude/skills/customer-snapshot/pyproject.toml
- **Verification:** `uv run --group dev python -m pytest --version` returns pytest 9.0.2
- **Committed in:** 5b7750e (Task 1 RED commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential for TDD execution. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None -- assemble.py is fully functional with all data paths wired.

## Next Phase Readiness
- assemble.py ready for use in customer-snapshot skill pipeline
- compose.py consumes assemble.py output via --data flag (JSON file handoff)
- Future: if issues.js normalization maps are updated, assemble.py maps must be synced manually

---
## Self-Check: PASSED

- All 5 files verified present on disk
- All 3 commit hashes verified in git log (5b7750e, 96c66d4, a8ed293)

---
*Plan: quick-260401-kd6*
*Completed: 2026-04-01*
