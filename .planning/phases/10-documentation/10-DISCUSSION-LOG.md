# Phase 10: Documentation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-04
**Phase:** 10-documentation
**Areas discussed:** Document structure, Audience and depth, Architecture diagrams, Onboarding walkthrough

---

## Document Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Extend README (Recommended) | Keep README.md as the single entry point. Add sections for architecture, onboarding. Avoids scattering docs. | ✓ |
| Separate doc files | Create docs/ folder with standalone files. README stays as hub with links. | |
| Hybrid | README as quick-start hub, separate files for long-form content. | |

**User's choice:** Extend README
**Notes:** User wanted clarity on what DOCS-01 through DOCS-04 meant. After explanation, confirmed single-document approach. Also raised that SKILL-INVENTORY.md overlap was confusing — resolved by keeping SKILL-INVENTORY.md as Phase 9 artifact and README as the summary view with links.

### Skill Reference Overlap (follow-up)

**User's choice:** Discussed in free text — user said "I'm not sure I even understood the question about docs-02" and "I think we should just have one document." Resolved by explaining DOCS-01 = getting started, DOCS-02 = skill reference, and confirming both live as sections in README.md.

### Credential Path Rename (user-initiated)

**User raised:** `~/.tsm-ai/` is a legacy name ("a hangover") that doesn't apply anymore. Needs renaming before docs are written.

| Option | Description | Selected |
|--------|-------------|----------|
| ~/.wandb-se/ | Clear, specific to W&B SE tooling | |
| ~/.field-eng-skills/ | Matches repo name exactly, a bit long | |
| ~/.wandb-tools/ | Broader, could house other W&B tool configs | |
| ~/.fe-skills/ | User's suggestion — short, maps to "field engineering skills" | ✓ |

**User's choice:** ~/.fe-skills/ (user-provided via "Other")
**Notes:** Mechanical find-and-replace across all scripts and docs. Directory structure inside stays identical.

---

## Audience and Depth

| Option | Description | Selected |
|--------|-------------|----------|
| CLI-comfortable (Recommended) | Assume terminal, Python, git. Focus depth on W&B-specific parts. | ✓ |
| Thorough onboarding | Explain uv, Claude Code skills, credential concepts. More hand-holding. | |
| Minimal + links | Bullet points only, link out for anything not repo-specific. | |

**User's choice:** CLI-comfortable
**Notes:** None — straightforward selection.

---

## Architecture Diagrams

| Option | Description | Selected |
|--------|-------------|----------|
| Mermaid diagrams (Recommended) | Renders natively on GitHub. Pipeline flow and panel contract as inline diagrams. | ✓ |
| Prose + code blocks | Plain text explanation, no diagrams. Simpler to maintain. | |
| ASCII art | Hand-drawn box diagrams in code blocks. | |

**User's choice:** Mermaid diagrams
**Notes:** None — straightforward selection.

---

## Onboarding Walkthrough

| Option | Description | Selected |
|--------|-------------|----------|
| Worked example (Recommended) | Walk through adding a fictional customer step by step. Concrete and followable. | ✓ |
| Reference checklist | Numbered checklist with commands. No worked example. | |
| Both | Short checklist first, detailed worked example after. | |

**User's choice:** Worked example
**Notes:** None — straightforward selection.

---

## Claude's Discretion

- Exact section ordering within README.md
- Number of usage examples per skill category
- Level of detail in Mermaid diagrams
- Whether to include a Troubleshooting subsection
- Fictional customer name for the worked example

## Deferred Ideas

None — discussion stayed within phase scope
