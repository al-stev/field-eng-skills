# Phase 8: Panel Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-03
**Phase:** 08-panel-integration
**Areas discussed:** Data pipeline wiring, Panel density vs. full pages, Sidebar organization, Empty state strategy

---

## Data Pipeline Wiring

### Q1: How should deep analytics data get into INTELLIGENCE_DATA?

| Option | Description | Selected |
|--------|-------------|----------|
| Extend assemble.py | Add analytics transforms inline in assemble.py. Single skill boundary, single BQ client session. | ✓ |
| New orchestration step | Separate fetch-analytics.py between assemble and compose. Keeps skills independent but adds complexity. | |
| Generate separately, compose merges | Run generate.py per page type, compose.py merges outputs. Reuses existing code but 9 separate invocations. | |
| You decide | Claude picks during planning. | |

**User's choice:** Extend assemble.py (Recommended)
**Notes:** None

### Q2: Should analytics data be fetched on every run or opt-in?

| Option | Description | Selected |
|--------|-------------|----------|
| Always fetch if BQ configured | If customer has sfdc_account_id, run all 9 transforms automatically. | ✓ |
| Opt-in via flag | --analytics flag required. Default is operational-only. | |
| Configurable per-customer | analytics_enabled field in customers.yaml. | |

**User's choice:** Always fetch if BQ configured (Recommended)
**Notes:** None

### Q3: Where should deep analytics transform code live?

| Option | Description | Selected |
|--------|-------------|----------|
| Import from deep-analytics | assemble.py imports from deep-analytics/scripts/transforms/. Single source of truth. | ✓ |
| Copy into customer-snapshot | Duplicate transforms. Each skill self-contained but code in two places. | |
| Extract to shared lib | Move to shared package. Cleanest but bigger refactor. | |

**User's choice:** Import from deep-analytics (Recommended)
**Notes:** None

### Q4: How should INTELLIGENCE_DATA keys be structured?

| Option | Description | Selected |
|--------|-------------|----------|
| Nested under analytics.* | data.analytics.cohort, data.analytics.risk, etc. Clean namespace separation. | ✓ |
| Flat alongside existing keys | data.cohort, data.risk_scoring, etc. Simpler but clutters top-level. | |
| You decide | Claude picks during planning. | |

**User's choice:** Nested under analytics.* (Recommended)
**Notes:** None

---

## Panel Density vs. Full Pages

### Q5: How much of each analytics page becomes a dashboard panel?

| Option | Description | Selected |
|--------|-------------|----------|
| Port everything | All charts from standalone page adapted to panel format. Dashboard IS the analytics tool. | ✓ |
| Pick top 2-3 charts | Lightweight panels, standalone pages for full analysis. | |
| KPI cards only | Ultra-lightweight status board, all viz in standalone pages. | |
| You decide per page | Claude evaluates individually. | |

**User's choice:** Port everything (Recommended)
**Notes:** User initially asked for clarification on what "panel density" meant in context of the v2 dashboard architecture. After clarification that this is about how much of each standalone page's content goes into its panel JS file, user chose to port everything.

### Q6: Should standalone HTML pages still be generated?

| Option | Description | Selected |
|--------|-------------|----------|
| Retire standalone pages | Dashboard panels replace standalone analytics pages entirely. | ✓ |
| Keep both | Both dashboard panels and standalone pages available. | |
| You decide | Claude decides during implementation. | |

**User's choice:** Retire standalone pages (Recommended)
**Notes:** None

---

## Sidebar Organization

### Q7: How should 15 panels be organized in the sidebar?

| Option | Description | Selected |
|--------|-------------|----------|
| Add an Analytics group | 3 existing + 1 new group with all 9 analytics panels. | |
| Spread across themed groups | ~5 groups by theme, breaking existing structure. | |
| Two analytics sub-groups | User Intelligence + Product Intelligence. Balanced without reshuffling. | ✓ |
| You decide | Claude picks during implementation. | |

**User's choice:** Two analytics sub-groups (Recommended)
**Notes:** User asked what the four groups would be under the single Analytics group option. After seeing the lopsided layout (9 items in one group), user agreed the two sub-groups approach was better balanced.

---

## Empty State Strategy

### Q8: How should panels with unavailable data behave in the sidebar?

| Option | Description | Selected |
|--------|-------------|----------|
| Show panel with explanation | Panel always in sidebar. Empty body explains why data is missing. | ✓ |
| Hide from sidebar entirely | Panels with no data don't appear. Cleaner but SE unaware of capability. | |
| Dimmed sidebar entry | Grayed out with tooltip. Clicking shows explanation. | |

**User's choice:** Show panel with explanation (Recommended)
**Notes:** None

### Q9: How should partially available data be handled?

| Option | Description | Selected |
|--------|-------------|----------|
| Show what's available | Render available charts, placeholder for missing sections. | ✓ |
| All-or-nothing | Any missing required source shows full empty state. | |
| You decide per panel | Claude decides threshold per panel. | |

**User's choice:** Show what's available (Recommended)
**Notes:** None

---

## Claude's Discretion

- Panel order within each new sidebar group
- Icon choices for new panels in panels.yaml
- Whether to extract shared CSS patterns into chart-helpers.js
- 800-line limit management — trimming decisions if needed
- Badge key choices for sidebar indicators

## Deferred Ideas

None — discussion stayed within phase scope
