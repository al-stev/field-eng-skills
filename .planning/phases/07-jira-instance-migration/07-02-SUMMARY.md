---
phase: 07-jira-instance-migration
plan: 02
subsystem: templates
tags: [jira, atlassian, url-migration, dashboard, skill-docs]

# Dependency graph
requires:
  - phase: 07-01
    provides: "Core Jira skill config and scripts migrated to coreweave.atlassian.net"
provides:
  - "All dashboard HTML/JS templates construct Jira URLs pointing to coreweave.atlassian.net"
  - "All downstream skill docs reference coreweave.atlassian.net as Jira instance"
  - "Test fixtures use coreweave.atlassian.net URLs"
  - "Cadence review template uses coreweave.atlassian.net URL patterns"
affects: [customer-snapshot, cadence-prep, jira-check, pre-read, gdocs, bigquery, usage-report]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - .claude/skills/customer-snapshot/templates/shell.html
    - .claude/skills/customer-snapshot/templates/panels/support.js
    - .claude/skills/customer-snapshot/templates/panels/actions.js
    - .claude/skills/customer-snapshot/templates/dashboard-v2.html
    - .claude/skills/customer-snapshot/templates/issue-tracker.html
    - .claude/skills/customer-snapshot/templates/intelligence-dashboard.html
    - .claude/skills/customer-snapshot/prototypes/support-tickets/4-ticket-age-scatter.html
    - .claude/skills/customer-snapshot/templates/test_assemble.py
    - .claude/skills/customer-snapshot/references/design-system.md
    - .claude/skills/customer-snapshot/SKILL.md
    - .claude/skills/jira-check/SKILL.md
    - .claude/skills/cadence-prep/SKILL.md
    - .claude/skills/pre-read/SKILL.md
    - .claude/skills/gdocs/SKILL.md
    - .claude/skills/bigquery/tests/conftest.py
    - templates/cadence-review.md

key-decisions:
  - "Mechanical find-and-replace only -- no logic changes needed since URL construction patterns are identical between instances"

patterns-established: []

requirements-completed: [JIRA-03, JIRA-05]

# Metrics
duration: 2min
completed: 2026-04-03
---

# Phase 07 Plan 02: Downstream URL Migration Summary

**Migrated all Jira URL references in 16 dashboard templates, skill docs, test fixtures, and output templates from wandb.atlassian.net to coreweave.atlassian.net**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-03T12:46:41Z
- **Completed:** 2026-04-03T12:49:04Z
- **Tasks:** 2
- **Files modified:** 16

## Accomplishments
- All 10 customer-snapshot files (HTML templates, JS panels, test fixtures, docs) now construct Jira URLs pointing to coreweave.atlassian.net
- All 6 downstream skill files (jira-check, cadence-prep, pre-read, gdocs, bigquery conftest, cadence-review template) reference the new instance
- Zero wandb.atlassian.net references remain in any committed source file outside .planning/ and .claude/worktrees/

## Task Commits

Each task was committed atomically:

1. **Task 1: Update dashboard HTML/JS templates and test fixtures** - `65bb5ba` (fix)
2. **Task 2: Update downstream skill docs and templates** - `42e847c` (fix)

## Files Created/Modified
- `.claude/skills/customer-snapshot/templates/shell.html` - Context menu "Open in Jira" URL
- `.claude/skills/customer-snapshot/templates/panels/support.js` - Jira URL construction for ticket links (2 occurrences)
- `.claude/skills/customer-snapshot/templates/panels/actions.js` - Jira badge href construction
- `.claude/skills/customer-snapshot/templates/dashboard-v2.html` - Inline Jira link in legacy template
- `.claude/skills/customer-snapshot/templates/issue-tracker.html` - Sample data URLs (5 issues)
- `.claude/skills/customer-snapshot/templates/intelligence-dashboard.html` - Sample data URLs (5 issues) + actions badge
- `.claude/skills/customer-snapshot/prototypes/support-tickets/4-ticket-age-scatter.html` - JIRA_BASE constant
- `.claude/skills/customer-snapshot/templates/test_assemble.py` - 4 test fixture issue URLs
- `.claude/skills/customer-snapshot/references/design-system.md` - URL pattern documentation
- `.claude/skills/customer-snapshot/SKILL.md` - Example data URL
- `.claude/skills/jira-check/SKILL.md` - Description, defaults table, URL-based mode (3 occurrences)
- `.claude/skills/cadence-prep/SKILL.md` - Frontmatter service-url, link rules, defaults, URL patterns (8 occurrences)
- `.claude/skills/pre-read/SKILL.md` - Example Jira links in output format tables (3 occurrences)
- `.claude/skills/gdocs/SKILL.md` - Example content with Jira URL (1 occurrence)
- `.claude/skills/bigquery/tests/conftest.py` - Test fixture jira_link URLs (3 occurrences)
- `templates/cadence-review.md` - Comment URL pattern and table row examples (5 occurrences)

## Decisions Made
- Mechanical find-and-replace only -- no logic changes needed since URL construction patterns are identical between instances. The old and new domains use the same `/browse/WB-XXX` path structure.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Known Stubs

None - all URLs are fully wired to the new coreweave.atlassian.net instance.

## Next Phase Readiness
- All downstream consumers of Jira URLs are migrated
- Plan 03 (cleanup of stale worktrees and CLAUDE.md credential table) can proceed
- The only remaining wandb.atlassian.net references are in .planning/ (historical docs) and .claude/worktrees/ (stale copies)

---
## Self-Check: PASSED

- All 16 modified files: FOUND
- Commit 65bb5ba (Task 1): FOUND
- Commit 42e847c (Task 2): FOUND
- Zero wandb.atlassian.net references in source files (excluding .planning/, .claude/worktrees/, __pycache__): VERIFIED

---
*Phase: 07-jira-instance-migration*
*Completed: 2026-04-03*
