# Phase 9: Skill Audit and Consolidation - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning
**Source:** Auto mode (recommended defaults selected)

<domain>
## Phase Boundary

Audit and consolidate all 35 skills so any W&B SE can discover, understand, and use the full skill suite without tribal knowledge. Publish a skill inventory, remove hardcoded user-specific values from committed code, update all SKILL.md files to reflect current behavior, and complete skill-composition.md with all multi-skill workflows.

</domain>

<decisions>
## Implementation Decisions

### Inventory format
- **D-01:** Publish skill inventory as `SKILL-INVENTORY.md` in the repo root — single markdown file with a table listing all 35 skills, one-line descriptions, entry-point vs building-block classification, required credentials, and a dependency graph section showing which skills consume which.
- **D-02:** Classification scheme: "entry-point" = SE invokes directly via `/skill-name`; "building-block" = consumed by other skills or composition workflows only (e.g., bigquery consumed by customer-snapshot, usage-report, deep-analytics).

### Hardcoded value scope
- **D-03:** "User-specific" means Asana GIDs, Slack channel IDs, email addresses, and user-specific URLs found in committed `.py` and `.sh` source code. These must move to `customers.yaml` or `~/.tsm-ai/.env`.
- **D-04:** GIDs in SKILL.md files are documentation/examples and are NOT hardcoded violations — they show users what values look like. Test fixtures with example GIDs are also acceptable.
- **D-05:** The known files with GIDs in source code (from scout: `gong_client.py` and test `conftest.py`) need investigation — gong_client.py likely has a hardcoded org ID that should be configurable.

### SKILL.md audit depth
- **D-06:** Every SKILL.md must accurately describe: current behavior, parameters, output format, and example usage. Fix stale content (e.g., old Jira instance references, outdated pipeline descriptions).
- **D-07:** Standardize SKILL.md format across all 35 skills — consistent sections (Purpose, Usage, Parameters, Output, Dependencies, Credentials).
- **D-08:** Success criteria requires spot-checking 5+ skills against actual behavior. Run the skill and verify SKILL.md matches.

### Composition rules update
- **D-09:** Add the v2 dashboard generation pipeline to skill-composition.md: assemble.py (Jira + BQ + Slack + Asana + deep-analytics transforms) → compose.py → dashboard folder.
- **D-10:** Update Jira references throughout skill-composition.md from wandb.atlassian.net to coreweave.atlassian.net (Phase 7 migration).
- **D-11:** Verify all existing workflows in skill-composition.md still work correctly after Phase 7-8 changes.

### Claude's Discretion
- Exact table format and column ordering in SKILL-INVENTORY.md
- Dependency graph visualization approach (ASCII, mermaid, or descriptive list)
- Order of skill auditing (alphabetical, by dependency, by usage frequency)
- Which 5+ skills to spot-check for accuracy verification
- Whether to add new composition workflows discovered during the audit

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Skill structure
- `.claude/rules/skill-composition.md` — Existing composition workflows (128 lines). Must be updated, not replaced.
- `CLAUDE.md` — Project structure section lists all skill directories with descriptions
- `templates/customers.yaml` — Customer registry where user-specific values should live

### Credentials
- `.claude/skills/credential-reference/SKILL.md` — Reference table for all API credential keys
- `.claude/skills/credential-status/scripts/check.sh` — Health checker for all credentials

### Existing skill docs (audit targets)
- `.claude/skills/*/SKILL.md` — All 35 SKILL.md files need accuracy verification
- `.claude/rules/atlassian.md` — Jira/Confluence workspace conventions (updated in Phase 7)
- `.claude/rules/slack.md` — Slack workspace conventions
- `.claude/rules/asana.md` — Asana workspace conventions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- All 35 skills already have SKILL.md files — this is an update/accuracy pass, not creation from scratch
- skill-composition.md already has 128 lines covering 10 workflows — needs expansion, not rewrite
- credential-reference already documents all API keys — can be cross-referenced for inventory

### Established Patterns
- Skills use `uv run --project .claude/skills/<skill>` for Python dependency isolation
- Entry-point skills are listed in CLAUDE.md skill-composition section
- Customer-specific config lives in `templates/customers.yaml`
- Credentials live in `~/.tsm-ai/.env`

### Integration Points
- SKILL-INVENTORY.md is a new file in repo root — needs to be discoverable
- skill-composition.md updates affect how Claude routes multi-skill workflows
- SKILL.md updates may surface outdated behavior that needs code fixes (scope creep risk — defer code fixes to backlog)

</code_context>

<specifics>
## Specific Ideas

- The hardcoded GID scan found 10 files — most are SKILL.md examples (acceptable) but `gong_client.py` likely has a real hardcoded value
- All 35 skills already have SKILL.md — the gap is accuracy and standardization, not existence
- Phase 7 Jira migration and Phase 8 dashboard pipeline are the two biggest composition changes to document

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-skill-audit-and-consolidation*
*Context gathered: 2026-04-04 via auto mode*
