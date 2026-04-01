---
phase: 06-dashboard-v2-ux-polish-data-provenance-split-charts-navigation-improvements
verified: 2026-04-01T13:00:00Z
status: passed
score: 11/11 must-haves verified
re_verification: false
---

# Phase 6: Dashboard V2 UX Polish Verification Report

**Phase Goal:** Polish the v2 modular dashboard based on user testing feedback from Phase 05 verification. Three themes: data transparency (show where every number comes from), chart readability (split overlaid charts, label time periods), and navigation UX (breadcrumb back from metric clicks). Final deliverable: wire compose.py into SKILL.md so /customer-snapshot produces v2 output.

**Verified:** 2026-04-01T13:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | Product adoption shows two separate radar charts (Events and Users) that are independently readable | VERIFIED | `renderEventsRadar()` and `renderUsersRadar()` functions in usage.js (lines 378, 446); DOM IDs `usage-radar-events` and `usage-radar-users`; both wired in render() at lines 857-866 |
| 2  | Sweeps data distinguishes between created and viewed in product adoption | VERIFIED | `PRODUCT_AREA_CASE` in queries.py lines 41-42: `'sweep_created' -> 'Sweeps Created'` and `'sweep_viewed' -> 'Sweeps Viewed'`; also in power_users_query inline CASE at lines 289-290 |
| 3  | Seat utilization chart renders without top label clipping | VERIFIED | `renderSeatChart` grid: `top: 40` (line 305) and markLine label `position: 'insideEndTop'` (line 348) — provides headroom for contracted-seats label |
| 4  | Tracked hours chart renders without bottom x-axis date label clipping | VERIFIED | `renderHoursChart` grid: `bottom: 72` (line 620) — sufficient space for rotated date labels |
| 5  | Every chart section in Usage panel displays its time period | VERIFIED | Four `.time-period` divs in usage.js render(): "Last 12 months (weekly)" for seat, "Last 12 months" for both radars, "Last 12 months (monthly)" for Weave, "Last 12 months (weekly)" for hours |
| 6  | Support panel chart sections display their time period | VERIFIED | Three `.time-period` divs in support.js: "All time" for Volume & Concerns, "Currently open" for Active Tickets, "All time" for Submitter Analysis |
| 7  | Clicking a key metric card on Overview navigates to the panel AND shows a back-to-overview breadcrumb | VERIFIED | overview.js calls `navigateTo(panelId, true)` on card and attention-row clicks; shell.html `navigateTo(panelId, fromOverview)` adds `.visible` class to `.breadcrumb-bar` when `fromOverview=true` |
| 8  | Clicking the breadcrumb returns to Overview | VERIFIED | shell.html line 781: `onclick="navigateTo('overview')"` on breadcrumb link |
| 9  | Each data section has a small SQL icon that copies the BigQuery query to clipboard on click | VERIFIED | `sqlCopyBtn(queryKey)` helper in usage.js and support.js; click handlers use `navigator.clipboard.writeText(queries[key])` wired to `INTELLIGENCE_DATA.usage.bq_queries`; 6 sections covered (seat, product adoption x2, Weave, hours, account health in usage.js; support in support.js) |
| 10 | A toast notification saying "Copied!" appears after clicking the SQL icon | VERIFIED | `showToast('Copied!')` called in SQL click handler; `showToast()` global defined in shell.html with CSS `.toast` / `.toast.visible` transition |
| 11 | Running /customer-snapshot produces a v2 folder-based dashboard via compose.py, not the v1 monolith | VERIFIED | SKILL.md Step 8 explicitly instructs agents to call `compose.py` with `--customer`, `--data`, and `--output` flags; v1 `intelligence-dashboard.html` described as "fallback reference, no longer the default output path" |

**Score:** 11/11 truths verified

---

### Required Artifacts

| Artifact | Plan | Expected | Status | Details |
|----------|------|----------|--------|---------|
| `.claude/skills/bigquery/scripts/queries.py` | 06-01 | PRODUCT_AREA_CASE with Sweeps Created/Viewed | VERIFIED | Contains at lines 41-42 and 289-290 |
| `.claude/skills/bigquery/scripts/usage.py` | 06-01, 06-03 | product_areas builder + bq_queries dict | VERIFIED | `bq_queries` dict at lines 486-493 with 6 query keys; `include_queries=True` in main() call |
| `.claude/skills/customer-snapshot/templates/panels/usage.js` | 06-01, 06-02, 06-03 | Dual radar + time periods + SQL buttons; min 850 lines | VERIFIED | 987 lines; contains `renderEventsRadar`, `renderUsersRadar`, `.time-period`, `sql-copy-btn` |
| `.claude/skills/customer-snapshot/templates/panels/support.js` | 06-02, 06-03 | Time period labels + SQL copy button | VERIFIED | Contains `.time-period` CSS and 3 time-period divs; `sqlCopyBtn('support_tickets')` on Volume & Concerns section |
| `.claude/skills/customer-snapshot/templates/panels/overview.js` | 06-02 | Stat cards call navigateTo with fromOverview=true | VERIFIED | Both card click and attention-row click call `navigateTo(panelId, true)` |
| `.claude/skills/customer-snapshot/templates/shell.html` | 06-02, 06-03 | Breadcrumb bar CSS + navigateTo(fromOverview) + toast | VERIFIED | `.breadcrumb-bar`, `.breadcrumb-link`, `.toast` CSS; `showToast()` function; `navigateTo(panelId, fromOverview)` signature |
| `.claude/skills/customer-snapshot/SKILL.md` | 06-03 | Step 8 instructs compose.py for v2 output | VERIFIED | Step 8 contains full compose.py invocation with flags |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `queries.py` | `usage.py` | `product_areas_query()` called by usage.py | VERIFIED | `from queries import ... product_areas_query` at line 31 of usage.py; called at line 550 |
| `usage.js` | `INTELLIGENCE_DATA.usage.product_areas` | Both radar renders read `data.product_areas` | VERIFIED | `var areas = data.product_areas` in `renderEventsRadar` and `renderUsersRadar` |
| `overview.js` | `shell.html navigateTo()` | `navigateTo(panelId, true)` from card/attention clicks | VERIFIED | Two click handlers call `navigateTo(panelId, true)` at overview.js lines 479, 491 |
| `shell.html` | `navigateTo function` | Breadcrumb link calls `navigateTo('overview')` | VERIFIED | `onclick="navigateTo('overview')"` at shell.html line 781 |
| `usage.py` | `usage.js` | `INTELLIGENCE_DATA.usage.bq_queries` consumed by SQL copy handlers | VERIFIED | `data.bq_queries` referenced in SQL click handler at usage.js lines 897-901 |
| `shell.html` | `usage.js` + `support.js` | `showToast()` called by panel SQL button click handlers | VERIFIED | Both panels call `if (typeof showToast === 'function') showToast('Copied!')` |
| `SKILL.md` | `compose.py` | Step 8 instructs agent to call compose.py | VERIFIED | `uv run ... compose.py --customer --data --output` in SKILL.md Step 8 |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `usage.js` SQL copy buttons | `data.bq_queries[key]` | `build_usage_json(include_queries=True)` in usage.py | Yes — each key maps to actual query function output (e.g., `seat_utilization_query().strip()`) | FLOWING |
| `usage.js` radar charts | `data.product_areas` | `_build_product_areas(pa_df)` from live BQ `product_areas_query()` | Yes — aggregated from `ext_daily_user_event_usage` with `PRODUCT_AREA_CASE` applied | FLOWING |
| `support.js` SQL copy button | `INTELLIGENCE_DATA.usage.bq_queries['support_tickets']` | Same `bq_queries` dict from usage.py | Yes — `support_tickets_query().strip()` | FLOWING |

---

### Behavioral Spot-Checks

Step 7b: SKIPPED — the dashboard is a template-rendered HTML output requiring a browser and live BQ credentials to verify end-to-end. No runnable server entry point exists for automated spot-checks. Human verification covers observable behavior.

---

### Requirements Coverage

All 7 UX requirements declared in REQUIREMENTS.md for Phase 6 are claimed across the three plans and verified in the codebase.

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| UX-01 | 06-03 | BQ SQL copy buttons with toast notification | SATISFIED | `sqlCopyBtn()` in usage.js and support.js; `showToast()` in shell.html; `bq_queries` dict in usage.py |
| UX-02 | 06-01 | Split product adoption radar into Events and Users charts | SATISFIED | `renderEventsRadar` + `renderUsersRadar` in usage.js; two-column grid layout |
| UX-03 | 06-02 | Time period labels on every chart section | SATISFIED | `.time-period` divs in usage.js (4 sections) and support.js (3 sections) |
| UX-04 | 06-02 | Overview breadcrumb for panel navigation | SATISFIED | `navigateTo(id, true)` in overview.js; breadcrumb-bar in shell.html |
| UX-05 | 06-01 | Sweeps created vs viewed split in product adoption | SATISFIED | `PRODUCT_AREA_CASE` splits `sweep_created` and `sweep_viewed` in queries.py |
| UX-06 | 06-01 | Chart clipping fixes for seat utilization and tracked hours | SATISFIED | Seat: `top: 40`, `insideEndTop`; Hours: `bottom: 72` in usage.js grid configs |
| UX-07 | 06-03 | compose.py wired into SKILL.md for v2 output | SATISFIED | SKILL.md Step 8 updated with full compose.py invocation |

**Orphaned requirements check:** No UX-* requirements mapped to Phase 6 in REQUIREMENTS.md beyond UX-01 through UX-07. None orphaned.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `shell.html` | 329-364 | `.placeholder-panel`, `.placeholder-icon`, `.placeholder-title`, `.placeholder-desc` CSS class names | Info | These are CSS class names for the empty-state panel UI shown when a panel has no data — intentional, not stubs |
| `usage.py` | 562 | Comment: `# Customer not found or PLACEHOLDER` | Info | Refers to a config sentinel value in customers.yaml — not a code stub |
| `SKILL.md` | multiple | "PLACEHOLDER" as sentinel string in customer registry guards | Info | Deliberate config pattern for unconfigured customers — not a code stub |

No blockers or warnings found. All matches are intentional patterns (CSS class names, config sentinels, empty-state UI).

---

### Human Verification Required

The following behaviors require visual/interactive verification in a browser:

#### 1. Split Radar Charts — Visual Readability

**Test:** Generate a dashboard for a customer with product area data. Open the Usage panel.
**Expected:** Two separate radar charts side-by-side — left labeled "PRODUCT ADOPTION — EVENTS", right labeled "PRODUCT ADOPTION — USERS" — each with its own natural scale, independently readable.
**Why human:** Chart layout and readability require visual inspection; automated checks only verify DOM structure and function existence.

#### 2. SQL Copy Button — Click to Clipboard

**Test:** Open the Usage panel. Click the database cylinder icon next to "SEAT UTILIZATION".
**Expected:** A "Copied!" toast appears in the bottom-right corner for ~2 seconds. Pasting from clipboard yields the full BigQuery SQL query string.
**Why human:** `navigator.clipboard.writeText()` requires a live browser context and user interaction to test; toast animation requires visual confirmation.

#### 3. Breadcrumb Navigation Round-Trip

**Test:** On the Overview panel, click a key metric card (e.g., an attention item from the Issues panel). Navigate back by clicking "← Overview" in the breadcrumb bar.
**Expected:** Clicking the card navigates to the correct panel with a breadcrumb bar visible at the top. Clicking "← Overview" returns to Overview and the breadcrumb bar is hidden.
**Why human:** Navigation state and conditional breadcrumb visibility require a live browser with hash routing active.

#### 4. Time Period Labels — Rendering Position

**Test:** Open the Usage and Support panels.
**Expected:** Under each chart title, a smaller grey monospace label shows the time period (e.g., "Last 12 months (weekly)"). Labels appear between the section title and the chart canvas, not overlapping.
**Why human:** CSS positioning and visual hierarchy require inspection; automated checks confirm the HTML element exists but not its rendered placement.

#### 5. compose.py Pipeline — End-to-End

**Test:** Run `/customer-snapshot <CustomerName>` in Claude Code for a configured customer.
**Expected:** Output is a `customers/<name>/dashboard/` folder containing `index.html`, `data.js`, panel JS files, and `lib/` — not a single monolithic HTML file. Dashboard opens correctly from `file://` protocol.
**Why human:** Requires live BQ credentials, customer configuration, and full agent execution to verify the complete pipeline.

---

### Gaps Summary

No gaps. All 11 truths verified, all 7 UX requirements satisfied, all artifacts exist and are substantive (not stubs), all key links confirmed wired end-to-end. The only unverified items are interactive browser behaviors that require human spot-checks (SQL clipboard, toast animation, breadcrumb round-trip, visual chart layout), which are expected limitations of static code analysis.

---

_Verified: 2026-04-01T13:00:00Z_
_Verifier: Claude (gsd-verifier)_
