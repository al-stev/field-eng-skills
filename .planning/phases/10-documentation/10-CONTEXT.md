# Phase 10: Documentation - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Create documentation so a new W&B SE can go from zero to running their first skill and generating a customer dashboard by following the repo's docs, without needing to ask the original author. All documentation lives in README.md as a single entry point. Also includes renaming the credential storage directory from `~/.tsm-ai/` to `~/.fe-skills/` across all code and docs.

</domain>

<decisions>
## Implementation Decisions

### Document structure
- **D-01:** Single document approach -- README.md is the one front door for all documentation. Enhance existing sections and add new ones. No separate doc files (no docs/ folder).
- **D-02:** README.md sections map to requirements: enhanced Quick Start (DOCS-01), enhanced Skills section with examples linking to SKILL-INVENTORY.md (DOCS-02), new Customer Onboarding section (DOCS-03), new Architecture Overview section (DOCS-04).
- **D-03:** SKILL-INVENTORY.md stays as-is (Phase 9 artifact). README skill tables serve as the summary view and link to SKILL-INVENTORY.md for the full flat inventory and dependency graph.

### Credential path rename
- **D-04:** Rename `~/.tsm-ai/` to `~/.fe-skills/` across the entire codebase. Every Python script, shell script, SKILL.md, CLAUDE.md, rules file, and README that references the old path must be updated.
- **D-05:** This is a mechanical find-and-replace. The directory structure inside (`~/.fe-skills/.env`) stays identical -- only the parent directory name changes.

### Audience and depth
- **D-06:** Target audience is CLI-comfortable. Assume the reader knows terminal basics, Python, git, and can follow shell commands. Don't explain what uv is or how to clone a repo -- just give them the commands.
- **D-07:** Focus depth on W&B-specific parts: credential setup (which systems, which tokens, why separate instances), customers.yaml schema, dashboard pipeline, and skill composition patterns.

### Architecture overview
- **D-08:** Use Mermaid diagrams for the dashboard pipeline flow and panel contract. Mermaid renders natively on GitHub and is easy to update since it's just text in the markdown.
- **D-09:** Cover the full pipeline: data sources (Jira + BQ + Slack + Asana) -> assemble.py -> INTELLIGENCE_DATA JSON -> compose.py -> dashboard folder -> browser. Include how panels work (PanelRegistry contract, panel JS files, data.js).

### Customer onboarding walkthrough
- **D-10:** Worked example with a fictional customer (e.g., "Acme Corp") walking through the complete flow: `/customer-setup` -> verify customers.yaml entry -> Asana portfolio setup -> Slack channel lookup -> SFDC mapping -> first `/customer-snapshot` generation.
- **D-11:** Step-by-step with concrete commands and expected output at each stage. A new SE should be able to follow along literally.

### Writing style
- **D-12:** Run `/humanizer` on the final README content before committing to remove AI writing patterns and make the prose sound natural.

### Claude's Discretion
- Exact section ordering within README.md (logical flow for a new reader)
- How many usage examples per skill category in DOCS-02
- Level of detail in Mermaid diagrams (how many boxes, which intermediate steps)
- Whether to include a "Troubleshooting" subsection or keep it minimal
- Fictional customer name for the worked example

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing documentation (edit targets)
- `README.md` -- Current getting-started content, skill tables, credentials, project structure (225 lines). Primary edit target for all 4 DOCS requirements.
- `CLAUDE.md` -- References `~/.tsm-ai/.env` throughout. Must be updated for credential path rename.

### Skill inventory and composition
- `SKILL-INVENTORY.md` -- Full 35-skill inventory with types, credentials, invocations, dependency graph. README links to this; do not duplicate.
- `.claude/rules/skill-composition.md` -- 12 multi-skill workflow patterns. README Workflow Patterns section references this.

### Rules files (credential path references)
- `.claude/rules/atlassian.md` -- References `~/.tsm-ai/.env` in credential location section
- `.claude/rules/slack.md` -- References `~/.tsm-ai/.env` in credential location section
- `.claude/rules/asana.md` -- References `~/.tsm-ai/.env` in authentication section

### Skill docs (credential path references)
- `.claude/skills/*/SKILL.md` -- Many reference `~/.tsm-ai/.env`. All 35 need scanning for the path rename.

### Dashboard architecture (content sources for DOCS-04)
- `.claude/skills/customer-snapshot/` -- assemble.py, compose.py, panels.yaml, shell.html, panel JS files
- `DASHBOARD-V2-SPEC.md` -- Dashboard architecture spec (reference for architecture section content)

### Customer onboarding (content sources for DOCS-03)
- `templates/customers.yaml` -- Schema documentation in header comments (40 lines)
- `.claude/rules/asana.md` -- Portfolio structure, setup-customer command, two-project model

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **README.md** (225 lines): Already has Quick Start, Skills tables (3 categories), Workflow Patterns, RAID model, Project Structure, Credentials table, Customer Registry, Python Skills sections. Substantial foundation to build on.
- **SKILL-INVENTORY.md** (80 lines): Full inventory with entry-point/building-block/setup classification and dependency graph. Satisfies DOCS-02 as the detailed reference.
- **customers.yaml header** (40 lines): Extensive schema documentation in YAML comments. Good source material for the onboarding section.
- **DASHBOARD-V2-SPEC.md**: Dashboard architecture spec that can inform the architecture overview content.

### Established Patterns
- Documentation is markdown in repo root
- Skill-level docs are SKILL.md per skill directory
- Rules are .claude/rules/*.md (auto-loaded by Claude Code)
- Credential path `~/.tsm-ai/.env` appears across all skills and docs -- mechanical rename target

### Integration Points
- README.md links to SKILL-INVENTORY.md for full skill reference
- README.md links to skill-composition.md for workflow patterns
- Credential path rename touches every skill's Python scripts and SKILL.md files

</code_context>

<specifics>
## Specific Ideas

- The credential path rename (`~/.tsm-ai/` -> `~/.fe-skills/`) should be a separate plan from the documentation writing -- it's a mechanical codebase-wide find-and-replace
- README already has significant content; the work is enhancing and reorganizing, not writing from scratch
- Mermaid diagrams should show the dashboard pipeline at minimum; panel contract diagram is a nice-to-have
- The worked example for customer onboarding should reference `/customer-setup` which automates most of the flow

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 10-documentation*
*Context gathered: 2026-04-04*
