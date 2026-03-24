---
name: usage-report
description: "Generate standalone usage visualization reports from BigQuery data. Two report types: external (customer-facing, shareable on QBR calls) and internal (SE prep with candid risk assessment). Use when the user mentions usage reports, usage charts, usage visualization, seat utilization, Weave ingestion, tracked hours, or wants to see customer BigQuery usage data. Also trigger for QBR usage prep or screen-sharing usage stats."
argument-hint: "<customer-name> [--internal] (required)"
---

# Usage Report

Generate polished, self-contained HTML usage visualizations from BigQuery data with Apache ECharts charts and AI-generated narrative intelligence. Two report types serve different audiences:

- **External** (default) -- Customer-facing report for QBR calls, slide decks, and customer sharing. W&B branded, positive/growth-framed AI narrative, no internal data.
- **Internal** (`--internal`) -- SE prep report with candid risk assessment, power user real names/emails, account health, churn indicators, and actionable SE recommendations.

Both reports use the same design system (Instrument Serif + Outfit + JetBrains Mono, gold accent) with ECharts for time-series, radar, and bar chart visualization.

## Prerequisites

- **ADC configured:** Run `gcloud auth application-default login` (one-time setup)
- **Customer registered:** Customer must have `sfdc_account_id` set in `templates/customers.yaml`
- **Verify setup:** Run `/bigquery-setup` to check connectivity

## Pipeline

### Step 1: Parse customer name

Extract the customer name from the user's input. Common patterns:
- `/usage-report GResearch` -> "GResearch"
- `usage report for Acme Corp` -> "Acme Corp"
- `show me GResearch usage` -> "GResearch"
- `generate usage charts for G-Research` -> "G-Research"
- `internal usage report for GResearch` -> "GResearch" (+ internal flag)

### Step 2: Determine report type

Choose the report type based on the user's input:

- **External** (default): No flag needed. Customer-safe content only.
- **Internal**: Triggered by `--internal` flag or keywords like "internal", "SE prep", "full report", "risk assessment", "candid".

| Feature | External | Internal |
|---------|----------|----------|
| W&B branding header | Yes | Yes |
| Seat utilization chart | Yes | Yes |
| Product adoption radar | Yes | Yes |
| Weave ingestion chart | Yes | Yes |
| Tracked hours chart | Yes | Yes |
| AI narrative | Positive/growth tone | Candid/risk tone |
| Account health section | No | Yes |
| Churn risk data | No | Yes |
| Power user real names | No (username only) | Yes (name + email) |
| Risk signals | No | Yes |
| SE action items | No | Yes |

### Step 3: Fetch usage data from BigQuery

Call the bigquery skill to fetch usage metrics:

```bash
# External report (default)
uv run --project .claude/skills/bigquery python .claude/skills/bigquery/scripts/usage.py \
  --customer "<CustomerName>" --format json

# Internal report (includes real names/emails in power_users)
uv run --project .claude/skills/bigquery python .claude/skills/bigquery/scripts/usage.py \
  --customer "<CustomerName>" --format json --internal
```

Parse the JSON output. Handle the response:
- If `available: true`: proceed to Step 4
- If `available: false` with `reason: "config_error"`: generate report with empty state
- If `available: false` with `reason: "no_data"`: generate report with empty state
- If `available: false` with `reason: "api_error"`: generate report with error state

### Step 4: Generate AI narrative

Analyze the BigQuery usage data and generate an `AI_NARRATIVE` object. The tone and content differ by report type.

**External AI narrative** (positive, growth-opportunity framing):

```javascript
const AI_NARRATIVE = {
  executive_summary: "...",   // 2-3 paragraphs, positive tone
  recommendations: ["..."],   // 3-5 actionable items, growth-framed
  highlights: ["..."]         // 3-5 positive highlights from the data
};
```

Guidelines for external narrative:
- Frame everything as growth opportunity, not deficiency
- Highlight adoption wins and expanding usage
- Suggest expansion areas as "unlocking additional value"
- Never mention churn risk, declining metrics negatively, or internal concerns
- Use language appropriate for customer stakeholders and decision-makers

**Internal AI narrative** (candid risk assessment):

```javascript
const AI_NARRATIVE = {
  executive_summary: "...",   // 2-3 paragraphs, candid tone
  recommendations: ["..."],   // 3-5 actionable items for SE
  highlights: ["..."],        // 3-5 highlights (positive and concerning)
  risk_signals: ["..."],      // 2-4 specific risk indicators
  se_actions: ["..."]         // 3-5 concrete next steps for the SE
};
```

Guidelines for internal narrative:
- Be direct about risks: declining usage, dormant seats, champion loss signals
- Flag churn indicators explicitly with supporting data
- Provide concrete SE actions: "Schedule Model Registry workshop with alice_ml"
- Reference specific users by name when relevant
- Include "what to push on in the next call" recommendations

### Step 5: Build USAGE_DATA and AI_NARRATIVE objects

Wrap the BigQuery JSON output into the template's JavaScript constants:

```javascript
const USAGE_DATA = {
  customer: "<CustomerName>",
  generated: "YYYY-MM-DD",       // today's date
  period: { start: "...", end: "..." },
  available: true,
  seat_utilization: { ... },     // from BigQuery response
  weave: { ... },                // from BigQuery response
  tracked_hours: { ... },        // from BigQuery response
  trends: { ... },               // from BigQuery response
  product_areas: [ ... ],        // from BigQuery response
  power_users: [ ... ]           // from BigQuery response (anonymized for external)
  // account_health: { ... }     // INTERNAL ONLY -- omit for external
};
```

### Step 6: Generate the report

1. Read the appropriate template:
   - External: `templates/usage-report-external.html`
   - Internal: `templates/usage-report-internal.html`
2. Replace the sample `USAGE_DATA` constant with the real data object from Step 5
3. Replace the sample `AI_NARRATIVE` constant with the generated narrative from Step 4
4. Save to the output path (see Output Path Convention below)
5. Create the directory path if it doesn't exist
6. Open the file: `open <path>`

### Step 7: Present to the user

Tell the user:
- Report type (external or internal)
- File path
- Brief summary: seat utilization %, Weave ingestion %, tracked hours, trend directions
- Flag any "critical" utilization zones (< 50%)
- Note if any sections were unavailable (null in the data)
- For internal: note renewal date, health status, and top risk signals

## Output Path Convention

```
customers/<kebab-case-name>/usage/YYYY-MM-DD-usage-report.html          # external
customers/<kebab-case-name>/usage/YYYY-MM-DD-usage-report-internal.html  # internal
```

Examples:
- `customers/g-research/usage/2026-03-24-usage-report.html` (external)
- `customers/g-research/usage/2026-03-24-usage-report-internal.html` (internal)

## AI Narrative Guidelines

### External Tone

The external narrative is written for customer stakeholders. It should feel like a branded W&B deliverable -- professional, encouraging, and actionable.

- **Executive summary**: 2-3 paragraphs highlighting platform adoption, growth areas, and value delivered. Start with the strongest metric.
- **Highlights**: 3-5 concrete data points framed positively (e.g., "Weave adoption grew 228% YoY").
- **Recommendations**: 3-5 suggestions framed as "unlocking additional value" or "accelerating adoption" -- never as fixing problems.

Forbidden in external narrative: "churn", "risk", "declining", "underutilized" (use "growth opportunity" instead), "dormant" (use "available capacity"), internal SE jargon.

### Internal Tone

The internal narrative is written for the SE preparing for calls. It should be direct, data-driven, and actionable.

- **Executive summary**: 2-3 paragraphs with honest assessment. Lead with the most important signal (positive or negative).
- **Risk signals**: 2-4 specific indicators with supporting data (e.g., "4 power users inactive 30+ days").
- **SE actions**: 3-5 concrete next steps with named users/teams where relevant.
- **Highlights**: Mix of positive and concerning data points.
- **Recommendations**: Tactical actions for the next customer interaction.

## Design Rules

- **ECharts from CDN** -- loaded from `https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js`. Not bundled, not Chart.js.
- **Custom 'wandb' ECharts theme** -- registered via `echarts.registerTheme('wandb', ...)` matching the project design system: gold accent for reference lines, blue primary data series, transparent background, JetBrains Mono axis labels, Outfit tooltip font.
- **W&B branding** on both report types: "Weights & Biases by CoreWeave" header, "USAGE REPORT" subtitle.
- **Dark mode default**, light mode via `prefers-color-scheme: light` media query.
- **Same design system tokens** as the intelligence dashboard (Instrument Serif display, Outfit body, JetBrains Mono mono, gold accent #d4a853/#b8922e).
- **Internal report adds**: Account Health section, power user section with real names, risk signal callouts.
- **Responsive**: Max-width 1160px, fluid `clamp()` spacing, single-column for screen-sharing.
- **Animation accessibility**: All animations respect `prefers-reduced-motion: reduce`.

## Template Files

| Template | Path | Audience |
|----------|------|----------|
| External | `templates/usage-report-external.html` | Customer QBR, slide decks |
| Internal | `templates/usage-report-internal.html` | SE prep, account reviews |

Both templates have two injection points:
- `const USAGE_DATA = { ... };` -- replace sample data with real BigQuery data
- `const AI_NARRATIVE = { ... };` -- replace sample narrative with AI-generated content

## Template Injection

The templates contain JavaScript constants at the top of the script block. These are the injection points -- replace the sample data with real data from Steps 4-5.

Each template's JavaScript handles all rendering: ECharts initialization, conditional section display, empty states, and responsive behavior. You only inject the data constants.

## Anti-Patterns

- Chart.js or any non-ECharts charting library
- Horizontal CSS bars for time-series data (use ECharts line/bar charts)
- KPI cards (big number + small label in identical card grid)
- Gradient text, glassmorphism, neon accents
- Inter/Roboto/Arial fonts
- Sidebar navigation
- Churn risk or internal data in external reports
- Bundling ECharts into the HTML file (use CDN)

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Empty report with config message | Add `sfdc_account_id` to `templates/customers.yaml` for this customer |
| Empty report with API error | Run `/bigquery-setup` to verify ADC and BQ connectivity |
| All sections blank | Customer may have no data in BigQuery -- verify account_id is correct |
| Missing specific section | That metric category returned null -- check BigQuery tables for data |
| ECharts not loading | Check internet connectivity (CDN dependency) |
| Report won't open | Check file path exists in `customers/` directory |

## Related Skills

- `/bigquery` -- Base data access skill (called in Step 3)
- `/bigquery-setup` -- Verify ADC and BigQuery connectivity
- `/customer-snapshot` -- Intelligence dashboard (also consumes BigQuery usage data)
