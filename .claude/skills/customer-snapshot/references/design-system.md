# Customer Tracker Design System

Authoritative design rules for customer tracker HTML dashboards. These decisions come from a structured bake-off between two approaches and are locked -- do not deviate.

Read this file when modifying templates or debugging visual issues. Every rule here exists because the alternative was tested and rejected.

## Typography

| Role | Font | Notes |
|------|------|-------|
| Display (titles, theme headings) | Instrument Serif | Google Fonts CDN, weight 400 |
| Body (text, UI elements) | Outfit | Google Fonts CDN, weights 300-700 |
| Mono (ticket keys, labels, badges) | JetBrains Mono | Google Fonts CDN, weights 400-600 |
| Micro-labels (chart labels, group labels) | JetBrains Mono, 9-11px, uppercase, letter-spacing 1.5px | |

Google Fonts import URL:
```
Instrument+Serif&family=JetBrains+Mono:wght@400;500;600&family=Outfit:wght@300;400;500;600;700
```

## Colour Palette

### Light Mode (`prefers-color-scheme: light`)

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-primary` | `#f6f4f0` (warm cream) | Page background |
| `--bg-elevated` | `#ffffff` | Elevated surfaces |
| `--bg-surface` | `#eeece8` | Secondary surfaces |
| `--bg-hover` | `#e6e4e0` | Hover states |
| `--border` | `#d4d2ce` | Dividers |
| `--border-subtle` | `#e0ded9` | Subtle dividers |
| `--text-primary` | `#1a1a1a` | Headings, body |
| `--text-secondary` | `#5c5c5c` | Meta text |
| `--text-tertiary` | `#8c8c8c` | Timestamps |
| `--accent` | `#b8922e` | Gold highlights |
| `--accent-dim` | `rgba(184, 146, 46, 0.10)` | Active pill bg |
| `--accent-border` | `rgba(184, 146, 46, 0.25)` | Active pill border |

### Dark Mode (`prefers-color-scheme: dark`) -- default

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-primary` | `#0c0f14` (deep navy) | Page background |
| `--bg-elevated` | `#141820` | Elevated surfaces |
| `--bg-surface` | `#1a1f2b` | Secondary surfaces |
| `--bg-hover` | `#222838` | Hover states |
| `--border` | `#2a3040` | Dividers |
| `--border-subtle` | `#1e2430` | Subtle dividers |
| `--text-primary` | `#e8eaed` | Headings, body |
| `--text-secondary` | `#8b92a0` | Meta text |
| `--text-tertiary` | `#5c6370` | Timestamps |
| `--accent` | `#d4a853` | Gold highlights |

Use tinted neutrals throughout -- never pure gray.

### Noise Texture (dark mode only)

SVG fractalNoise overlay on `body::before`, opacity ~0.025. Adds subtle depth. Skip in light mode.

### Status Colours

| Category | Light | Dark | Maps to |
|----------|-------|------|---------|
| Resolved | `#1a7a4c` | `#4ade80` | Done, Closed, Resolved, Merged |
| Active | `#1565a0` | `#60a5fa` | In Progress, In Review, In Development, Selected for Development |
| Waiting | `#9a6e08` | `#fbbf24` | Open, Backlog, To Do, Waiting, Future |
| Triage | `#6b6a6a` | `#6b7280` | Triage, Won't Fix, Archived |

Each colour has `-dim` (rgba ~10%) and `-border` (rgba ~22%) variants for badge backgrounds and borders.

### Priority Colours

| Priority | Light | Dark |
|----------|-------|------|
| P0 Critical | `#dc2626` | `#f87171` (red) |
| P1 High | `#c2410c` | `#fb923c` (orange) |
| P2 Medium | `#9a6e08` | `#fbbf24` (amber) |
| P3 Low | `#6b6a6a` | `#6b7280` (gray) |

## Layout

- Full-width single column, max-width ~1160px, centered
- `clamp()` for all sizing -- fluid responsive, no breakpoint jank
- Inline header stats (total, open, in progress, resolved) -- NOT KPI cards
- Gold rule separator (2px, accent colour) under the title
- No sidebar, no table of contents

## Header

- Customer name in Instrument Serif, large (`clamp(28px, 4vw, 42px)`)
- Mono micro-label subtitle: "W&B Jira . Customer Tracker"
- Thin gold accent line below title
- Inline stats row: value + label pairs, flex layout with generous gap
- Generation date in meta text

## Analysis Section

The analysis section is the dashboard's primary value -- surfacing insights not visible in Jira. It sits above the issue list and contains:

### Health Summary Bar
- Horizontal stacked bar: Needs Triage (red) / Active (blue) / Stale (amber) / Resolved (green)
- Segments are proportional, with count labels
- Activity-based classification, not raw Jira statuses
- FE-UPDATE comments excluded from eng activity calculations

### Attention Callouts
- 2x2 grid of clickable metric cards
- Each shows: icon, count, label, "View tickets →" on hover
- Cards: Never Commented, No Eng Activity 60+ days, Unassigned, Recently Opened (14 days)
- Clicking filters the issue list, auto-expands matching themes, scrolls to issues
- Active callout gets accent border highlight

### Velocity Chart
- Opened vs Resolved by month (last 6 months)
- Side-by-side horizontal CSS bars per month
- Month labels in JetBrains Mono micro-label style

### Response Cadence
- Three inline metrics: median days to first comment, % responded within 7 days, zero-comment count
- Clean stat display, not cards

## Charts

- Custom HTML/CSS horizontal bars -- NO Chart.js, NO external JS charting libraries
- Theme breakdown: horizontal stacked bars (Bug vs Feature Request per theme), sorted by total count descending
- All charts recalculate and re-render via JS when filters change
- Bar labels in JetBrains Mono micro-label style
- Dynamic height based on number of bars

## Filter Bar

- Pill toggle buttons for Type (All, Bug, FR), Status (All + categories), Priority (All, P0-P3, P0-P1 compound)
- Dropdown `<select>` for Theme (7+ options typical)
- Text search input (searches summary, key, assignee)
- No "Filter Issues" heading -- self-evident
- Vertical separator pipes between filter groups
- Active pill gets gold accent background
- All filters AND-combined
- Filters sit directly below charts, no visual break

## Theme Sections (Issue List)

- Collapsible sections with click-to-toggle
- Theme header: name (Instrument Serif), count (mono), priority mini-badges (coloured pills)
- Arrow rotation on expand/collapse
- Full-bleed hover on theme headers
- Issue rows (not cards) with: key, summary, type badge, priority, status badge, assignee
- Issue key links to `https://wandb.atlassian.net/browse/KEY`
- No zebra stripes -- bottom border dividers only
- Hover-only row feedback
- Default: hide resolved issues. Toggle to show/hide resolved.
- `grid-template-rows` transition for smooth collapse animation

## Resolved Issues Toggle

- Button in filter bar or above issue list
- Default state: resolved issues hidden
- Toggle label: "Show Resolved" / "Hide Resolved"
- When hidden, resolved issues are excluded from both the issue list AND charts
- When shown, everything renders normally

## Motion

| Effect | Value |
|--------|-------|
| Page load | Staggered fadeUp, 50-100ms delays |
| Easing | `ease-out` only |
| Collapsible | `grid-template-rows: 0fr / 1fr` |
| Bars | barGrow on initial render only |
| Reduced motion | Respect `prefers-reduced-motion: reduce` |

## Audience Toggle

Pill toggle in the header area (next to subtitle/generation date) that switches between Internal and External views.

- Two pill buttons: "Internal" (default active) and "External"
- Reuses existing pill button style from filter bar (same border-radius, font, sizing)
- Internal mode: accent colour (`--accent`) active pill background (`--accent-dim` bg, `--accent-border` border)
- External mode: green colour (`--green`) active pill background (`--green-dim` bg, `--green-border` border)
- Toggle sets `external-mode` class on `<body>`
- CSS rule: `.external-mode .internal-only { display: none !important; }`
- Content marked `.internal-only`: sentiment raw analysis, risk signals, recommended actions, hot item internal notes, candid engagement commentary
- External mode shows: overall sentiment (categorical label only), hot issues (factual, no internal notes), trending metrics, engagement dates
- Note: external mode hides content visually but does NOT strip it from HTML source. Do not share the raw HTML file externally. For screen-sharing, the visual toggle is sufficient.

## Sentiment Panel

Displays channel sentiment analysis from Slack data. Sits between the existing Analysis section and the Trending section.

### Overall Score Display
- Categorical label in large text (Instrument Serif): "Positive", "Neutral", "Cautiously Negative", "Negative", "Critical"
- Colour indicator matches sentiment: green (positive), gray (neutral), amber (cautiously-negative), orange (negative), red (critical)
- Numeric score displayed as supplementary detail in mono micro-label style
- One-line summary in body text below the label

### Hot Threads List
- Each hot thread: channel name badge, thread summary, sentiment badge (coloured pill), message count, participant count
- Thread summary is the primary text (Outfit body font)
- "View in Slack" link if URL available
- Sorted by severity (most negative first)
- Max 5 hot threads displayed

### Internal-Only Section (`.internal-only`)
- Raw analysis text in a subtle bordered container (`--bg-surface` background, `--border-subtle` border)
- Risk signals as a bulleted list with red dot indicators
- Recommended actions as a bulleted list with accent dot indicators
- JetBrains Mono micro-label header: "INTERNAL ANALYSIS"

### Unavailable State
- When `sentiment` is null or `sentiment.available` is false:
  - Show "Channel Sentiment" label
  - Below it: "Not configured -- add Slack channels to templates/customers.yaml" (tertiary text)
  - No error styling, no red text -- graceful empty state
- When Slack API failed: "Slack data unavailable" (tertiary text)

## Trending Section

Displays issue trending metrics computed from Jira data. Sits after the Sentiment Panel.

### Opened/Closed Bar Chart
- Extends the existing Velocity Chart pattern (side-by-side horizontal CSS bars per month)
- Same bar-track, bar-segment class usage
- Month labels in JetBrains Mono micro-label style
- Two bars per month: opened (amber) and closed (green)
- 6-month lookback window

### Ratio Metric
- Inline metric display (not a card): "Raised-to-Resolved Ratio: 1.78"
- Trend indicator: arrow up (growing), arrow down (shrinking), dash (stable)
- Growing ratio = amber text, shrinking = green text, stable = gray text
- Period label in mono micro-label: "LAST 6 MONTHS"

### Resolution Velocity Metric
- Inline metric: "Median Time to Resolution: 45 days"
- Supplementary detail: P90 value if available
- Uses `resolutiondate` when available, falls back to `updated`

### Theme Recurrence (Top 5)
- Simple ordered list of top 5 recurring themes by issue count
- Each item: theme name, count (mono), optional trend indicator
- Compact display, not a chart -- a ranked list
- JetBrains Mono micro-label header: "TOP RECURRING THEMES"

## Executive Summary

Four-section layout providing a scannable overview for customer call prep. Sits at the top of the dashboard (below header, above analysis).

### Layout
- Four sections in a 2x2 grid on desktop, stacking to single column on mobile
- Each section has a JetBrains Mono micro-label header (uppercase, letter-spacing)
- Sections ordered by attention priority: Health Snapshot, Hot Items, Trending Metrics, Engagement Cadence
- Compact inline metrics, not cards -- follows the existing inline stats pattern from the header

### Health Snapshot
- Sentiment label + colour indicator (reuses Sentiment Panel colour mapping)
- Backlog trajectory: "Growing" / "Shrinking" / "Stable" with directional indicator
- Staleness summary: "N stale, M very stale" with appropriate colour coding

### Hot Items
- Top 3-5 items needing immediate attention
- Each item: type icon (ticket/thread/escalation), title, one-line detail, link
- Types: stale_ticket, negative_thread, escalation
- Internal notes (`.internal-only`) shown as sub-text in tertiary colour
- Sorted by severity/urgency

### Trending Metrics
- Compact summary: "Opened N / Closed M this period"
- Resolution velocity: "Median N days"
- Theme recurrence: top theme name + count
- All in inline metric style, not cards

### Engagement Cadence
- Last Slack activity date
- Days since last FE-UPDATE
- Last call date (null until Granola integration, shows "No data source")
- Clean date display with "N days ago" relative format

## Anti-Patterns (forbidden)

These patterns signal "AI-generated" and destroy credibility:

- KPI cards (big number + small label in identical card grid)
- Coloured top border accents on cards
- Everything-in-cards (flatten the hierarchy)
- Native `<select>` for type/status/priority (use pill buttons)
- Sidebar navigation
- Redundant headings ("Filter Issues")
- Zebra stripes on tables
- Gradient text
- Inter / Roboto / Arial fonts
- Purple-to-blue gradients
- Neon/glowing accents in dark mode
- Bounce/elastic easing
- Sparklines as decoration
- Glassmorphism / frosted glass
- Chart.js or any external charting library
- Emoji section headers
