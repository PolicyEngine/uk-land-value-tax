# UK Land Value Tax Analysis

An interactive dashboard modelling the impact of replacing council tax with a land value tax (LVT) in the UK, built with [PolicyEngine UK](https://github.com/PolicyEngine/policyengine-uk).

## Overview

The dashboard estimates UK land values for 2026-27 and simulates what would happen if council tax were abolished and replaced with a flat-rate land value tax. It covers:

- **Council tax to LVT** — a tool-first view of how replacing council tax shifts the tax burden, with scenarios near the budget-neutral rate
- **Land baseline** — enough context to interpret the reform, including upstream ONS target comparisons and average land values across groups
- **Methodology** — a short explanation of what the static microsimulation does and does not capture

All estimates are produced by [PolicyEngine UK](https://github.com/PolicyEngine/policyengine-uk) using the [Enhanced FRS 2023-24](https://github.com/PolicyEngine/policyengine-uk-data) microdata, uprated to 2026-27 with OBR per capita nominal GDP growth projections.

The comparison figures in this repo should come from two sources only: upstream land targets from `policyengine-uk-data`, and generated model outputs from the microsimulation script in this repo.

## Data sources

| Source | Description |
|--------|-------------|
| [ONS National Balance Sheet 2025](https://www.ons.gov.uk/economy/nationalaccounts/uksectoraccounts/bulletins/nationalbalancesheet/2025) | Official UK land value estimates (AN.211) by sector |
| [OBR Economic and Fiscal Outlook](https://obr.uk/efo/economic-and-fiscal-outlook-march-2025/) | Per capita nominal GDP growth projections used for uprating |
| [Wealth and Assets Survey](https://www.ons.gov.uk/peoplepopulationandcommunity/personalandhouseholdfinances/debt/methodologies/wealthandassetssurveyqmi) | Household-level wealth data used for imputation |
| [PolicyEngine UK Data](https://github.com/PolicyEngine/policyengine-uk-data) | Enhanced FRS 2023-24 microdata |

## Project structure

```
├── dashboard/          # Next.js + Tailwind dashboard
│   ├── app/           # App Router entrypoints and global styles
│   ├── public/data/   # Generated JSON consumed by the dashboard
│   ├── src/components/
│   └── package.json
├── src/uk_land_value_tax/
│   ├── analysis.py     # Pure, testable data-processing logic
│   ├── pipeline.py     # PolicyEngine orchestration and JSON generation
│   └── cli.py          # CLI entrypoint
├── tests/
│   └── test_analysis.py
├── simulation/
│   └── land_value_tax_simulation.py  # Thin wrapper around the package CLI
├── data/
│   └── lvt_results.json  # Simulation output
└── pyproject.toml
```

## Running locally

### Dashboard

```bash
cd dashboard
npm install
npm run dev
```

### Simulation

The data pipeline now lives in a regular Python package with unit tests. The full simulation still requires access to the Enhanced FRS dataset through `policyengine-uk`, currently requires Python 3.13+ because of the `policyengine-uk` dependency, and expects access to a `policyengine-uk-data` checkout or installed package to load the upstream land targets.

```bash
uv sync --extra simulation --extra dev
uv run pytest
POLICYENGINE_UK_DATA_ROOT=/path/to/policyengine-uk-data \
  uv run uk-land-value-tax-build --sync-dashboard
```

If you prefer the legacy entrypoint, this wrapper still works:

```bash
POLICYENGINE_UK_DATA_ROOT=/path/to/policyengine-uk-data \
  python simulation/land_value_tax_simulation.py --sync-dashboard
```

The Python pipeline writes `data/lvt_results.json`, and `--sync-dashboard` also updates `dashboard/public/data/lvt_results.json`.

## Deployment

The dashboard is deployed on [Vercel](https://vercel.com) and updates automatically on pushes to `main`. The Vercel project is configured with:

- **Root directory**: `dashboard`
- **Framework**: Next.js
- **Build command**: `npm run build`

## Development notes

- The dashboard repo should not use notebooks for production data processing.
- Keep transformation logic in `src/uk_land_value_tax/analysis.py` so it can be tested without the full microsimulation environment.
- Treat `data/lvt_results.json` as a generated artifact from the Python package, not as hand-edited analysis output.
- Pull land targets from `policyengine-uk-data` at build time rather than duplicating ONS constants in this repo.
- Keep the public UI focused on plausible council-tax-replacement scenarios rather than very high annual LVT rates that the static model cannot interpret well.
