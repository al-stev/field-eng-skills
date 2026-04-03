# Plan 07-03: Live Validation & Field Discovery — SUMMARY

## Outcome
All Jira skills now work against coreweave.atlassian.net with correct custom field IDs.

## What was done

### Task 1: Credential validation & field discovery
- Authenticated as Al Stevenson (astevenson@coreweave.com) — 198 projects visible
- Discovered Customer field moved: customfield_10083 → customfield_16678 ("Customer (WB)")
- Discovered Eng Team field moved: customfield_10084 → customfield_16680 ("Eng Team")
- Discovered JQL field name changed: "Customer" → "Customer (WB)"
- Root cause of broken filters: API token needed regeneration for coreweave.atlassian.net + field IDs changed during migration

### Task 2: Fix field IDs and JQL
- Updated jira_client.py CUSTOMER_FIELD and ENG_TEAM_FIELD constants
- Updated issues.py JQL construction to use "Customer (WB)" field name
- Updated issues.py help text with correct field IDs
- Updated atlassian.md rules with new field IDs

### Task 3: Worktree cleanup
- Removed 3 stale worktrees: agent-a5746f0b, agent-ab0a21fa, agent-acdfd84c
- Pruned orphaned git worktree entries
- Verified zero wandb.atlassian.net references remain in source code

## Verification
- `issues.py list --customer "Isomorphic"` returns 3 results from coreweave.atlassian.net
- Zero wandb.atlassian.net references in committed source (outside .planning/)

## Key files modified
- `.claude/skills/jira/scripts/jira_client.py` — field ID constants
- `.claude/skills/jira/scripts/issues.py` — JQL field name + help text
- `.claude/rules/atlassian.md` — field ID documentation

## Duration
~15 min (interactive — required user to update API token)
