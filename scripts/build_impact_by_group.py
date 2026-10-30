"""Build impact-by-group JSON for the interactive blog chart.

Runs baseline + (abolish council tax + LVT) reforms at several rates and
aggregates average net household income change by several groupings.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from microdf import MicroDataFrame  # noqa: E402

from uk_land_value_tax.pipeline import _ensure_dataset, _run  # noqa: E402
from uk_land_value_tax.pipeline import _household_family_types  # noqa: E402

YEAR = 2026
RATES = [(0.005, "0.5%"), (0.0077, "0.77%"), (0.01, "1.0%"), (0.015, "1.5%"), (0.02, "2.0%")]
OUT = ROOT / "blog" / "data" / "impact_by_group.json"

REGION_LABELS = {
    "NORTH_EAST": "North East",
    "NORTH_WEST": "North West",
    "YORKSHIRE": "Yorkshire and the Humber",
    "EAST_MIDLANDS": "East Midlands",
    "WEST_MIDLANDS": "West Midlands",
    "EAST_OF_ENGLAND": "East of England",
    "LONDON": "London",
    "SOUTH_EAST": "South East",
    "SOUTH_WEST": "South West",
    "WALES": "Wales",
    "SCOTLAND": "Scotland",
    "NORTHERN_IRELAND": "Northern Ireland",
}
REGION_ORDER = list(REGION_LABELS.values())
COUNTRY_LABELS = {
    "ENGLAND": "England",
    "SCOTLAND": "Scotland",
    "WALES": "Wales",
    "NORTHERN_IRELAND": "Northern Ireland",
}
FAMILY_ORDER = [
    "Single, no children",
    "Couple, no children",
    "Lone parent",
    "Couple with children",
    "Single pensioner",
    "Pensioner couple",
]
TENURE_LABELS = {
    "OWNED_OUTRIGHT": "Owned outright",
    "OWNED_WITH_MORTGAGE": "Owned with mortgage",
    "RENT_PRIVATELY": "Private renter",
    "RENT_FROM_COUNCIL": "Council renter",
    "RENT_FROM_HA": "Housing assoc. renter",
}


def aggregate(mdf_df: MicroDataFrame, col: str, order: list | None = None) -> list[dict]:
    rows = []
    groups = order if order is not None else sorted(pd.Series(mdf_df[col]).dropna().unique())
    for g in groups:
        sub = mdf_df[np.asarray(mdf_df[col]) == g]
        if len(sub) == 0:
            continue
        # |change| <= £1 counts as "no change"; MicroSeries .mean()/.count() are weighted
        winners = float((sub.income_change > 1).mean()) * 100
        losers = float((sub.income_change < -1).mean()) * 100
        rows.append(
            {
                "group": g if not isinstance(g, (np.integer, int)) else int(g),
                "avg_net_change": round(float(sub.income_change.mean())),
                "avg_lvt": round(float(sub.lvt.mean())),
                "avg_council_tax_saved": round(float(sub.council_tax_saved.mean())),
                "pct_winners": round(winners, 1),
                "pct_losers": round(losers, 1),
                "pct_no_change": round(100 - winners - losers, 1),
                "n_households": round(float(sub.income_change.count())),
            }
        )
    return rows


def main() -> None:
    dataset = _ensure_dataset(YEAR)
    extra = ["tenure_type"]

    household, person = _run(dataset, None, year=YEAR, extra_household=extra)

    base = pd.DataFrame(
        {
            "weight": np.asarray(household["household_weight"]),
            "baseline_income": np.asarray(household["household_net_income"]),
            "council_tax_saved": np.asarray(household["council_tax_less_benefit"]),
            "income_decile": np.asarray(household["household_income_decile"]),
            "wealth_decile": np.asarray(household["household_wealth_decile"]),
            "region": [REGION_LABELS.get(r, r) for r in np.asarray(household["region"])],
            "country": [COUNTRY_LABELS.get(c, c) for c in np.asarray(household["country"])],
            "tenure": [TENURE_LABELS.get(t, t) for t in np.asarray(household["tenure_type"])],
            "family_type": _household_family_types(person, household["household_id"]),
        }
    )
    is_pensioner = base["family_type"].isin(["Single pensioner", "Pensioner couple"])
    is_owner = base["tenure"].isin(["Owned outright", "Owned with mortgage"])
    base["age_tenure"] = np.select(
        [is_pensioner & is_owner, is_pensioner & ~is_owner, ~is_pensioner & is_owner],
        ["Pensioner homeowners", "Pensioner renters", "Working-age homeowners"],
        default="Working-age renters",
    )
    base["london"] = np.where(base["region"] == "London", "London", "Rest of UK")
    base["london_pensioner"] = np.select(
        [(base["london"] == "London") & is_pensioner & is_owner, is_pensioner & is_owner],
        ["London pensioner homeowners", "Pensioner homeowners elsewhere"],
        default="Other households",
    )

    out = {"year": YEAR, "rates": [label for _, label in RATES], "scenarios": {}}
    for rate, label in RATES:
        print(f"Running reform at {label}...", flush=True)
        hh, _ = _run(
            dataset,
            {
                "gov.contrib.abolish_council_tax": True,
                "gov.contrib.ubi_center.land_value_tax.rate": rate,
            },
            year=YEAR,
        )
        df = base.copy()
        df["income_change"] = np.asarray(hh["household_net_income"]) - df["baseline_income"]
        df["lvt"] = np.asarray(hh["LVT"])
        md = MicroDataFrame(df, weights="weight")

        out["scenarios"][label] = {
            "income_decile": aggregate(md[np.asarray(md.income_decile) > 0], "income_decile", list(range(1, 11))),
            "wealth_decile": aggregate(md[np.asarray(md.wealth_decile) > 0], "wealth_decile", list(range(1, 11))),
            "region": aggregate(md, "region", REGION_ORDER),
            "country": aggregate(md, "country", list(COUNTRY_LABELS.values())),
            "family_type": aggregate(md, "family_type", FAMILY_ORDER),
            "tenure": aggregate(md, "tenure", list(TENURE_LABELS.values())),
            "age_tenure": aggregate(
                md,
                "age_tenure",
                ["Pensioner homeowners", "Pensioner renters", "Working-age homeowners", "Working-age renters"],
            ),
            "london": aggregate(md, "london", ["London", "Rest of UK"]),
            "london_pensioner": aggregate(
                md,
                "london_pensioner",
                ["London pensioner homeowners", "Pensioner homeowners elsewhere"],
            ),
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
