---
name: weave-forecast
description: "Generate a self-contained Weave ingestion forecast HTML page for a customer from BigQuery data. Pulls daily ingestion from fct_weave_project_storage, fits three windowed-mean-rate scenarios (180d/90d/30d), auto-detects stale spike projects, and projects cumulative usage 12 months forward with limit-crossing dates and contract/renewal markers. Use this skill whenever the user mentions Weave forecast, Weave projection, Weave ingestion forecast, Weave usage forecast, weave-forecast, projecting Weave consumption, Weave limit crossing date, when will a customer hit their Weave limit, mid-term Weave upsell trigger, Weave headroom, or wants to extrapolate a customer's Weave ingestion 3/6/9/12 months out. Also trigger for questions like 'how is <customer> tracking against their Weave commitment', 'will <customer> need a Weave upsell before renewal', or any variant of forecasting Weave ingestion growth toward a contracted GB limit. Even if the user only says 'forecast' alongside a customer that has Weave on their subscription, prefer this skill over generic forecasting approaches."
argument-hint: "<customer-name> [--days 180] [--horizon-days 365] [--open]"
---

# Weave Forecast

Generates a polished, self-contained HTML page projecting a customer's Weave ingestion forward against their contracted limit. Designed for the conversation that happens when an SE notices a customer's Weave usage accelerating toward (or past) the limit on their current contract, and needs to decide whether a mid-term upsell is justified.

Three projection scenarios are computed on different lookback windows:

| Scenario | Window | What it tells you |
|---|---|---|
| Conservative | 180-day mean rate | Long-run trend. Smooths out recent spikes. |
| Recent | 90-day mean rate | Most-likely sustained trajectory. |
| Aggressive | 30-day mean rate | Bullish — assumes the recent month rate continues. |

Each scenario projects forward 365 days and computes the date cumulative ingestion (anchored to contract start) crosses the contracted limit.

The page also detects **stale spike projects** — projects that contributed a meaningful burst of ingestion and have since gone silent. A toggle in the UI lets you flip between "include all projects" and "exclude stale spikes" to see how much of the projection is being driven by workloads that may not recur.

## Prerequisites

- **BigQuery ADC configured:** Run `gcloud auth application-default login` (one-time, may need periodic refresh)
- **Customer registered:** Customer must have `sfdc_account_id` set in `templates/customers.yaml` (use `/customer-setup <name>` if not already there)
- **bigquery skill venv installed:** This skill reuses `bq_client.py` and the query factory from the bigquery skill, plus its pandas/numpy/google-cloud-bigquery dependencies
- **Customer must actually use Weave:** the forecast is meaningless for customers with no Weave ingestion

## Pipeline

### Step 1: Parse customer name

Extract the customer name from the user's input. Common patterns:
- `/weave-forecast GSK` → "GSK"
- `weave forecast for Acme Corp` → "Acme Corp"
- `when will GResearch hit their weave limit` → "GResearch"
- `show me how GSK is tracking against their weave commitment` → "GSK"
- `should we upsell weave for Acme this quarter` → "Acme"

The customer name must match an entry in `templates/customers.yaml`. If you can't find it there, ask the user — don't guess.

### Step 2: Run the forecast script

The script is the deterministic data pipeline — Claude doesn't reason about the numbers, it just orchestrates.

```bash
uv run --project .claude/skills/bigquery \
  python .claude/skills/weave-forecast/scripts/weave_forecast.py --customer "<CustomerName>"
```

Add `--open` to auto-open the generated HTML in the default browser.

Useful flags:
- `--days N` — daily-history lookback in days (default 180). Going to 365 nearly doubles BQ scan cost.
- `--horizon-days N` — forecast horizon (default 365). Most useful at 365.
- `--output <path>` — override output location (default goes under `customers/<name>/weave/`).

### Step 3: Read the result and tell the user what it says

The script writes to `customers/<kebab-case-name>/weave/YYYY-MM-DD-weave-forecast.html` and prints the path to stdout. After it runs, summarize the headline findings in the chat:

- Current cumulative ingestion this contract year vs limit
- Recent 30-day rate (and what it implies annualized)
- Limit-crossing dates per scenario
- Whether any stale spike projects were detected (if so, the de-spiked toggle is meaningful)
- Whether the in-flight upsell timing matches the projected crossing date (cross-check via `/salesforce` if relevant)

The user has the HTML for the deeper visual story — don't repeat every chart in chat.

## Data sources & cost

| Query | Source table | Bytes scanned (cold) |
|---|---|---|
| Daily ingestion by project | `wandb-production.analytics.fct_weave_project_storage` | ~85 GB |
| Monthly history | same table | ~190 GB |
| Contract limit + dates | `dim_opportunities` | <10 MB |
| Account health | `stg_salesforce_accounts` (+ `renewal_predictions`) | cached |

Total per fresh run: **~280 GB processed (~$1.40)**. Free within BigQuery's 24-hour result cache, so repeat runs the same day are effectively free.

## Output structure

```
customers/<kebab-case-name>/weave/
  YYYY-MM-DD-weave-forecast.html
```

Self-contained: ECharts via CDN, all data inlined as a JS object literal, no server. Open with `open <path>` or share by attaching the file.

## Caveats to flag to the user

These are worth mentioning at least once when first running the forecast for an account:

- **Internal-only.** The page has an "INTERNAL · SE only" badge for a reason — candid framing ("upsell trigger date") isn't customer-friendly. For QBR or screen-share, adapt the framing or sanitize.
- **Linear scenarios, not growth models.** If the customer keeps accelerating, all scenarios under-project. If they plateau, all over-project. Eyeball the daily-history chart yourself — if the bars are still trending up, prefer the Aggressive scenario as the "real" trajectory.
- **Contract dates can lag SFDC.** The skill reads the latest-ending won opportunity from `dim_opportunities`. If a co-term MSA addition was logged recently it may not yet be reflected — sanity-check the contract end date in the chart against SFDC if it matters for the conversation.
- **Project names are not resolvable for dedicated cloud.** The forecast shows aggregate ingestion only — per-project breakdown isn't available from BigQuery for dedicated-cloud customers. See `customers/gsk/weave/data-team-question.md` (one-off artifact from the GSK debugging session) for context on this gap.
- **Stale-spike detection thresholds are fixed.** A project is flagged "stale spike" if it contributed ≥5 GB in the lookback window AND has been silent ≥7 days. Lower limits or rapidly-evolving workloads may not be classified the way an SE would intuitively classify them.

## Related skills

- `/bigquery` — underlying BQ query layer (this skill reuses `bq_client.py` and queries from it)
- `/customer-setup` — required to register a customer's `sfdc_account_id` before this skill can run
- `/salesforce` — cross-check renewal dates and in-flight Weave upsell opportunities
- `/usage-report` — broader usage view (seats, tracked hours, product areas) for the same customer
