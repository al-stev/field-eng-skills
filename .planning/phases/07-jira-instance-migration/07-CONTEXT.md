# Phase 7: Jira Instance Migration - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Migrate all Jira integrations from wandb.atlassian.net to coreweave.atlassian.net. The WB project was migrated to the new instance. Confluence was already on coreweave.atlassian.net and is unaffected.

</domain>

<decisions>
## Implementation Decisions

### Migration Approach
- **D-01:** Straightforward URL swap from wandb.atlassian.net to coreweave.atlassian.net across all source files
- **D-02:** After URL swap, run discovery against the new instance to validate custom fields, JQL filters, and project structure
- **D-03:** Fix anything that breaks — expect possible changes in custom field IDs, space names, or filter syntax
- **D-04:** Existing ATLASSIAN_TOKEN and ATLASSIAN_EMAIL credentials should be revalidated against the new instance

### Claude's Discretion
- Validation approach (manual vs automated) — Claude decides based on what's practical
- Order of file updates — Claude decides based on dependency chain
- Whether to clean up stale worktrees (4 exist with old URLs) — can be done as part of this phase or deferred

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Jira Integration
- `.claude/skills/jira/scripts/jira_client.py` — The actual API client, contains base URL
- `.claude/skills/jira/SKILL.md` — Jira skill documentation with instance references
- `.claude/rules/atlassian.md` — Workspace rules referencing wandb.atlassian.net
- `CLAUDE.md` — Project-level instructions with credential table

### Downstream Skills
- `.claude/skills/jira-check/SKILL.md` — Jira triage skill
- `.claude/skills/cadence-prep/SKILL.md` — Meeting prep skill consuming Jira data
- `.claude/skills/pre-read/SKILL.md` — Pre-read skill consuming Jira data
- `.claude/skills/customer-snapshot/SKILL.md` — Dashboard skill consuming Jira data

</canonical_refs>

<code_context>
## Existing Code Insights

### Files Needing URL Update (non-worktree)
- `jira_client.py` — API client, likely has base URL constant
- `CLAUDE.md` — credential table references wandb.atlassian.net
- `.claude/rules/atlassian.md` — instance reference in rules
- `.claude/skills/atlassian-setup/SKILL.md` — setup instructions
- `.claude/skills/credential-status/scripts/check.sh` — health checker
- 6 SKILL.md files across downstream skills
- 6 HTML/JS template files with Jira issue URLs
- `templates/cadence-review.md` — meeting template with Jira links

### Stale Worktrees
- 4 worktree directories under `.claude/worktrees/` contain copies with old URLs
- These are leftover from v1.0 parallel execution and can be cleaned up

### Integration Points
- `jira_client.py` is the single source of truth for Jira API connectivity
- Dashboard templates construct issue URLs client-side (pattern: `https://wandb.atlassian.net/browse/WB-XXXX`)
- credential-status check.sh validates connectivity to the Jira instance

</code_context>

<specifics>
## Specific Ideas

User noted: "Most things should still be valid. There might just be a slight change in the space name or how the filters work, but we're going to have to look at it to discover this."

The approach is: swap URLs first, then discover and fix what breaks. Not a redesign — just a migration.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-jira-instance-migration*
*Context gathered: 2026-04-03*
