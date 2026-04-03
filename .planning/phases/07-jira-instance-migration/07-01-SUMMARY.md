---
phase: 07-jira-instance-migration
plan: 01
subsystem: infra
tags: [jira, atlassian, migration, credentials, documentation]

# Dependency graph
requires: []
provides:
  - "Jira API client (jira_client.py) connecting to coreweave.atlassian.net"
  - "Credential health check validating against coreweave.atlassian.net"
  - "Agent rules and project documentation pointing to coreweave.atlassian.net"
affects: [07-02, 07-03, jira, jira-check, cadence-prep, customer-snapshot, pre-read]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - ".claude/skills/jira/scripts/jira_client.py"
    - ".claude/skills/credential-status/scripts/check.sh"
    - ".claude/rules/atlassian.md"
    - ".claude/skills/atlassian-setup/SKILL.md"
    - "CLAUDE.md"
    - "README.md"
    - ".claude/skills/jira/SKILL.md"

key-decisions:
  - "Stale __pycache__ bytecache contains old URL but is gitignored and regenerated on next run -- no action needed"

patterns-established: []

requirements-completed: [JIRA-01, JIRA-04]

# Metrics
duration: 3min
completed: 2026-04-03
---

# Phase 7 Plan 1: Core Jira Client, Health Check, and Documentation Migration Summary

**Jira API client, credential health checker, agent rules, and all project documentation migrated from wandb.atlassian.net to coreweave.atlassian.net**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-03T12:46:43Z
- **Completed:** 2026-04-03T12:49:30Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Migrated the JIRA_SERVER constant in jira_client.py -- the single source of truth for all Jira API connectivity
- Updated credential health check (check.sh) to validate against the new instance
- Updated agent rules (atlassian.md) and setup instructions (atlassian-setup SKILL.md) including rewriting the troubleshooting note that previously warned against using coreweave.atlassian.net for Jira
- Updated all project-level documentation (CLAUDE.md, README.md, Jira SKILL.md) credential tables, descriptions, and URLs

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate Jira API client, health checker, and rules** - `10b1543` (feat)
2. **Task 2: Update CLAUDE.md, README.md, and Jira SKILL.md** - `a92952a` (docs)

## Files Created/Modified
- `.claude/skills/jira/scripts/jira_client.py` - JIRA_SERVER constant updated to coreweave.atlassian.net
- `.claude/skills/credential-status/scripts/check.sh` - Jira health check URL and success message updated
- `.claude/rules/atlassian.md` - Jira instance reference updated in Instances section
- `.claude/skills/atlassian-setup/SKILL.md` - Instance table, CLI link, and troubleshooting note rewritten
- `CLAUDE.md` - Header, project structure comment, and credential table updated
- `README.md` - Quick Start comment, data sources table, and credentials table updated
- `.claude/skills/jira/SKILL.md` - Frontmatter service-url, description, defaults table, and browser URL updated

## Decisions Made
- Stale `__pycache__/*.pyc` files contain the old URL string but are gitignored generated artifacts that will be regenerated on next Python invocation -- no manual cleanup needed

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - all changes are complete URL swaps with no placeholder or stub content.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. Existing ATLASSIAN_EMAIL and ATLASSIAN_TOKEN credentials work against the new instance (same Atlassian ID covers both instances).

## Next Phase Readiness
- Core API client and documentation now point to coreweave.atlassian.net
- Plan 02 (downstream skill SKILL.md files and HTML templates) can proceed -- these depend on the API client being correct first
- Plan 03 (custom field discovery and validation) can proceed -- it needs the client connecting to the right instance

## Self-Check: PASSED

All 7 modified files exist. Both task commits (10b1543, a92952a) verified. Key content checks (JIRA_SERVER constant, health check URL) confirmed.

---
*Phase: 07-jira-instance-migration*
*Completed: 2026-04-03*
