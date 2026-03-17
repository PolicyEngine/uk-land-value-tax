# UK Land Value Tax Analysis

An interactive dashboard modelling the impact of replacing council tax with a land value tax (LVT) in the UK, built with [PolicyEngine UK](https://github.com/PolicyEngine/policyengine-uk).

## Overview

The dashboard estimates UK land values for 2026-27 and simulates what would happen if council tax were abolished and replaced with a flat-rate land value tax. It covers:

- **Land and wealth overview** — total UK land values compared with ONS National Balance Sheet figures, average land value by region and household type, and distribution across income deciles
- **Replacing council tax with LVT** — budgetary impact at various LVT rates, distributional effects by income decile, winners and losers, and changes to poverty and inequality

All estimates are produced by [PolicyEngine UK](https://github.com/PolicyEngine/policyengine-uk) using the [Enhanced FRS 2023-24](https://github.com/PolicyEngine/policyengine-uk-data) microdata, uprated to 2026-27 with OBR per capita nominal GDP growth projections.

## Data sources

| Source | Description |
|--------|-------------|
| [ONS National Balance Sheet 2025](https://www.ons.gov.uk/economy/nationalaccounts/uksectoraccounts/bulletins/nationalbalancesheet/2025) | Official UK land value estimates (AN.211) by sector |
| [OBR Economic and Fiscal Outlook](https://obr.uk/efo/economic-and-fiscal-outlook-march-2025/) | Per capita nominal GDP growth projections used for uprating |
| [Wealth and Assets Survey](https://www.ons.gov.uk/peoplepopulationandcommunity/personalandhouseholdfinances/debt/methodologies/wealthandassetssurveyqmi) | Household-level wealth data used for imputation |
| [PolicyEngine UK Data](https://github.com/PolicyEngine/policyengine-uk-data) | Enhanced FRS 2023-24 microdata |

## Project structure

```
├── dashboard/          # React dashboard (Create React App + Recharts)
│   ├── src/
│   │   ├── App.js      # Main dashboard component
│   │   ├── App.css     # Styles
│   │   └── lvt_results.json  # Simulation results consumed by the dashboard
│   └── package.json
├── simulation/
│   └── land_value_tax_simulation.py  # PolicyEngine UK microsimulation script
├── data/
│   └── lvt_results.json  # Simulation output
└── notebook/
    └── land_value_tax_microsimulation.ipynb
```

## Running locally

### Dashboard

```bash
cd dashboard
npm install
npm start
```

### Simulation

Requires the `python313` conda environment with `policyengine-uk` installed and access to the Enhanced FRS dataset.

```bash
conda activate python313
cd simulation
python land_value_tax_simulation.py
cp ../data/lvt_results.json ../dashboard/src/lvt_results.json
```

## Deployment

The dashboard is deployed on [Vercel](https://vercel.com) and updates automatically on pushes to `main`. The Vercel project is configured with:

- **Root directory**: `dashboard`
- **Framework**: Create React App
- **Build command**: `npm run build`
- **Output directory**: `build`
