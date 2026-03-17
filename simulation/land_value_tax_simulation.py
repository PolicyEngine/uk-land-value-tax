"""
Land Value Tax (LVT) Microsimulation with PolicyEngine UK
Runs the simulation and saves results to JSON for dashboard consumption.
"""

import json
import numpy as np
import microdf as mdf
from policyengine_uk import Microsimulation, Simulation, Scenario

YEAR = 2026
OUTPUT_FILE = "data/lvt_results.json"

def run():
    results = {}

    # Load data
    print("Loading dataset...")
    print("Creating baseline microsimulation...")
    baseline = Microsimulation()

    # === Section 1: Baseline Land Values ===
    land_value = baseline.calculate("land_value", YEAR)
    hh_land = baseline.calculate("household_land_value", YEAR)
    corp_land = baseline.calculate("corporate_land_value", YEAR)
    property_wealth = baseline.calculate("property_wealth", YEAR)
    total_wealth = baseline.calculate("total_wealth", YEAR)
    weights = baseline.calculate("household_weight", YEAR)
    income = baseline.calculate("household_net_income", YEAR)
    income_decile = baseline.calculate("household_income_decile", YEAR)

    # Build main MicroDataFrame with all household-level variables
    df_all = mdf.MicroDataFrame({
        "land_value": land_value.values,
        "hh_land": hh_land.values,
        "corp_land": corp_land.values,
        "property_wealth": property_wealth.values,
        "total_wealth": total_wealth.values,
        "income": income.values,
        "income_decile": income_decile.values,
    }, weights=weights.values)

    results["baseline"] = {
        "total_land_tn": round(float(df_all.land_value.sum()) / 1e12, 2),
        "household_land_tn": round(float(df_all.hh_land.sum()) / 1e12, 2),
        "corporate_land_tn": round(float(df_all.corp_land.sum()) / 1e12, 2),
        "total_property_wealth_tn": round(float(df_all.property_wealth.sum()) / 1e12, 2),
        "total_wealth_tn": round(float(df_all.total_wealth.sum()) / 1e12, 2),
        "land_pct_of_property": round(float(df_all.hh_land.sum()) / float(df_all.property_wealth.sum()) * 100, 1),
        "land_pct_of_wealth": round(float(df_all.land_value.sum()) / float(df_all.total_wealth.sum()) * 100, 1),
        "avg_land_per_household": round(float(df_all.land_value.mean())),
        "median_land_value": round(float(df_all.land_value.median())),
    }
    print(f"  Total land: £{results['baseline']['total_land_tn']}tn")

    # === Section 1b: Avg land value by country and family type ===
    print("  Computing avg land value breakdowns...")
    country = baseline.calculate("country", YEAR)
    region = baseline.calculate("region", YEAR)
    # Derive household type from person-level age and pension status
    is_child = (baseline.calculate("age", YEAR).values < 18).astype(float)
    is_adult = (baseline.calculate("age", YEAR).values >= 18).astype(float)
    is_pension_age = baseline.calculate("is_SP_age", YEAR).values.astype(float)
    hh_children = np.array(baseline.map_result(is_child, "person", "household"))
    hh_adults = np.array(baseline.map_result(is_adult, "person", "household"))
    hh_pensioners = np.array(baseline.map_result(is_pension_age, "person", "household"))
    # All adults at or above state pension age
    all_pensioner = (hh_adults > 0) & (hh_pensioners >= hh_adults) & (hh_children == 0)
    family_type_hh = np.where(
        all_pensioner,
        np.where(hh_adults <= 1, "Single pensioner", "Pensioner couple"),
        np.where(
            hh_adults <= 1,
            np.where(hh_children > 0, "Lone parent", "Single, no children"),
            np.where(hh_children > 0, "Couple with children", "Couple, no children"),
        ),
    )

    df_hh = mdf.MicroDataFrame({
        "land_value": land_value.values,
        "country": country.values,
        "region": region.values,
        "family_type": family_type_hh,
    }, weights=weights.values)

    # By country
    avg_by_country = [{"group": "UK", "avg_land_value": round(float(df_hh.land_value.mean()))}]
    for c in ["ENGLAND", "SCOTLAND", "WALES", "NORTHERN_IRELAND"]:
        subset = df_hh[df_hh["country"] == c]
        if len(subset) > 0:
            avg_val = float(subset.land_value.mean())
            avg_by_country.append({"group": c.replace("_", " ").title(), "avg_land_value": round(avg_val)})

    # By region (England regions + devolved nations)
    avg_by_region = []
    for r in ["NORTH_EAST", "NORTH_WEST", "YORKSHIRE", "EAST_MIDLANDS", "WEST_MIDLANDS",
              "EAST_OF_ENGLAND", "LONDON", "SOUTH_EAST", "SOUTH_WEST",
              "WALES", "SCOTLAND", "NORTHERN_IRELAND"]:
        subset = df_hh[df_hh["region"] == r]
        if len(subset) > 0:
            avg_val = float(subset.land_value.mean())
            label = r.replace("_", " ").title()
            if label == "East Of England":
                label = "East of England"
            if label == "Yorkshire":
                label = "Yorkshire and the Humber"
            avg_by_region.append({"group": label, "avg_land_value": round(avg_val)})

    # By family type
    avg_by_family = []
    family_labels = ["Single, no children", "Couple, no children", "Lone parent", "Couple with children", "Single pensioner", "Pensioner couple"]
    for label in family_labels:
        subset = df_hh[df_hh["family_type"] == label]
        if len(subset) > 0:
            avg_val = float(subset.land_value.mean())
            avg_by_family.append({"group": label, "avg_land_value": round(avg_val)})

    results["avg_land_by_country"] = avg_by_country
    results["avg_land_by_region"] = avg_by_region
    results["avg_land_by_family_type"] = avg_by_family

    # === Section 2: ONS Comparison ===
    # Source: ONS National Balance Sheet 2025, Table 2 (by asset) & Table 11 (Households)
    # Corporate = Private NFC + Public NFC + Financial corporations
    results["ons_comparison"] = {
        "ons_2020_household_tn": 4.11,
        "ons_2020_corporate_tn": 1.94,
        "ons_2020_government_tn": 0.39,
        "ons_2020_total_tn": 6.5,
        "ons_2024_household_tn": 4.56,
        "ons_2024_corporate_tn": 2.12,
        "ons_2024_government_tn": 0.38,
        "ons_2024_total_tn": 7.12,
        "model_2026_total_tn": results["baseline"]["total_land_tn"],
        "model_2026_household_tn": results["baseline"]["household_land_tn"],
        "model_2026_corporate_tn": results["baseline"]["corporate_land_tn"],
        "model_vs_ons_2024_pct": round(results["baseline"]["total_land_tn"] / 7.12 * 100, 1),
        "ons_time_series": [
            {"year": y, "household": h, "corporate": c, "government": g, "total": t}
            for y, h, c, g, t in [
                (2015, 3.24, 1.58, 0.29, 5.15), (2016, 3.47, 1.64, 0.30, 5.44),
                (2017, 3.65, 1.71, 0.33, 5.73), (2018, 3.70, 1.83, 0.39, 5.97),
                (2019, 3.74, 1.84, 0.38, 6.02), (2020, 4.11, 1.94, 0.39, 6.50),
                (2021, 4.37, 2.18, 0.48, 7.11), (2022, 4.67, 2.06, 0.35, 7.14),
                (2023, 4.38, 2.00, 0.33, 6.76), (2024, 4.56, 2.12, 0.38, 7.12),
            ]
        ],
    }

    # === Section 3: Distribution by Income Decile ===
    df = df_all[df_all["income_decile"] > 0]

    by_decile = df.groupby("income_decile")
    decile_stats = by_decile[["land_value", "hh_land", "corp_land", "property_wealth", "income"]].mean()
    decile_totals = by_decile[["land_value"]].sum()
    total_land_all = float(decile_totals["land_value"].sum())

    results["distribution_by_decile"] = []
    for d in decile_stats.index:
        results["distribution_by_decile"].append({
            "decile": int(d),
            "avg_income": round(float(decile_stats.loc[d, "income"])),
            "avg_land_value": round(float(decile_stats.loc[d, "land_value"])),
            "avg_property_wealth": round(float(decile_stats.loc[d, "property_wealth"])),
            "share_of_land_pct": round(float(decile_totals.loc[d, "land_value"]) / total_land_all * 100, 1),
        })
    print("  Distribution by decile computed.")

    # === Section 4: Revenue at Various Rates (reform: abolish CT + add LVT) ===
    ct_rev_bn = float(baseline.calculate("council_tax", YEAR).sum()) / 1e9
    lvt_rates = [0.005, 0.01, 0.015, 0.02, 0.03, 0.05]
    results["revenue_by_rate"] = []

    for rate in lvt_rates:
        print(f"  Simulating LVT rate {rate:.1%}...")
        reform = Scenario(parameter_changes={
            "gov.contrib.ubi_center.land_value_tax.rate": rate
        })
        sim = Microsimulation(scenario=reform)
        lvt_rev = float(sim.calculate("LVT", YEAR).sum()) / 1e9
        avg_lvt = float(sim.calculate("LVT", YEAR).mean())
        net_rev = lvt_rev - ct_rev_bn

        results["revenue_by_rate"].append({
            "rate": rate,
            "rate_pct": f"{rate:.1%}",
            "lvt_revenue_bn": round(lvt_rev, 1),
            "council_tax_bn": round(ct_rev_bn, 1),
            "net_revenue_bn": round(net_rev, 1),
            "avg_per_household": round(avg_lvt),
        })

    # === Section 5: Full reform analysis — Replace Council Tax with LVT ===
    baseline_net_income = baseline.calculate("household_net_income", YEAR)
    council_tax_baseline = baseline.calculate("council_tax", YEAR)
    council_tax_rev = float(council_tax_baseline.sum()) / 1e9
    total_land_bn = float(land_value.sum()) / 1e9
    required_rate = council_tax_rev / total_land_bn
    impact_rates = [required_rate] + [r for r in [0.005, 0.01, 0.015, 0.02, 0.03, 0.05] if abs(r - required_rate) > 0.0001]
    impact_rates.sort()

    # Poverty and Gini helpers using microdf
    # NOTE: We compute poverty directly from household_net_income rather
    # than using in_poverty_bhc, because the HBAI poverty definition only
    # subtracts official taxes and does not include LVT.
    # We use the modified OECD equivalence scale: 1 for the first adult,
    # 0.5 for each additional adult, 0.3 for each child.
    equiv_factor = 1.0 + (hh_adults - 1) * 0.5 + hh_children * 0.3
    equiv_factor = np.where(equiv_factor > 0, equiv_factor, 1.0)

    def poverty_rate(hh_income, wts, equiv):
        """Relative poverty rate: % of households with equiv income < 60% of median."""
        eq_inc = mdf.MicroSeries(hh_income / equiv, weights=wts)
        med = float(eq_inc.median())
        in_poverty = mdf.MicroSeries((hh_income / equiv < 0.6 * med).astype(float), weights=wts)
        return float(in_poverty.mean()) * 100

    wts = weights.values
    baseline_poverty_bhc = poverty_rate(baseline_net_income.values, wts, equiv_factor)
    # AHC: subtract housing costs
    housing_costs = baseline.calculate("housing_costs", YEAR).values
    baseline_poverty_ahc = poverty_rate(baseline_net_income.values - housing_costs, wts, equiv_factor)
    baseline_gini = float(mdf.MicroSeries(baseline_net_income.values, weights=wts).gini())

    results["impact_scenarios"] = {}
    results["poverty_gini"] = {"baseline_poverty_bhc": round(baseline_poverty_bhc, 2),
                                "baseline_poverty_ahc": round(baseline_poverty_ahc, 2),
                                "baseline_gini": round(baseline_gini, 4),
                                "scenarios": {}}

    for rate in impact_rates:
        rate_label = f"{rate * 100:.2f}%" if rate == required_rate else f"{rate * 100:.1f}%"
        print(f"  Computing impact of replacing council tax with {rate_label} LVT...")
        reform = Scenario(parameter_changes={
            "gov.contrib.abolish_council_tax": True,
            "gov.contrib.ubi_center.land_value_tax.rate": rate,
        })
        sim_reform = Microsimulation(scenario=reform)

        lvt_liability = sim_reform.calculate("LVT", YEAR)
        reformed_net_income = sim_reform.calculate("household_net_income", YEAR)
        income_change = reformed_net_income.values - baseline_net_income.values

        # Poverty rates under reform (computed from household_net_income)
        reform_poverty_rate_bhc = poverty_rate(reformed_net_income.values, wts, equiv_factor)
        reform_housing_costs = sim_reform.calculate("housing_costs", YEAR).values
        reform_poverty_rate_ahc = poverty_rate(reformed_net_income.values - reform_housing_costs, wts, equiv_factor)

        # Gini under reform
        reform_gini = float(mdf.MicroSeries(reformed_net_income.values, weights=wts).gini())

        results["poverty_gini"]["scenarios"][rate_label] = {
            "poverty_bhc": round(reform_poverty_rate_bhc, 2),
            "poverty_ahc": round(reform_poverty_rate_ahc, 2),
            "poverty_bhc_change": round(reform_poverty_rate_bhc - baseline_poverty_bhc, 2),
            "poverty_ahc_change": round(reform_poverty_rate_ahc - baseline_poverty_ahc, 2),
            "gini": round(reform_gini, 4),
            "gini_change": round(reform_gini - baseline_gini, 4),
            "gini_change_pct": round((reform_gini - baseline_gini) / baseline_gini * 100, 2),
        }

        # Distributional impact by decile
        df_impact = mdf.MicroDataFrame({
            "income_decile": income_decile.values,
            "lvt": lvt_liability.values,
            "council_tax_saved": council_tax_baseline.values,
            "income_change": income_change,
            "baseline_income": baseline_net_income.values,
            "land_value": land_value.values,
        }, weights=weights.values)
        df_impact = df_impact[df_impact["income_decile"] > 0]

        impact_gb = df_impact.groupby("income_decile")
        impact_means = impact_gb[["lvt", "council_tax_saved", "income_change", "baseline_income", "land_value"]].mean()

        # Winners/losers/unchanged per decile
        df_impact["is_winner"] = (df_impact["income_change"] > 0).astype(float)
        df_impact["is_loser"] = (df_impact["income_change"] < 0).astype(float)
        df_impact["is_unchanged"] = (df_impact["income_change"] == 0).astype(float)
        wl_means = df_impact.groupby("income_decile")[["is_winner", "is_loser", "is_unchanged"]].mean()

        scenario_data = []
        for d in impact_means.index:
            avg_inc_change = float(impact_means.loc[d, "income_change"])
            avg_base_inc = float(impact_means.loc[d, "baseline_income"])
            scenario_data.append({
                "decile": int(d),
                "avg_lvt": round(float(impact_means.loc[d, "lvt"])),
                "avg_council_tax_saved": round(float(impact_means.loc[d, "council_tax_saved"])),
                "avg_net_change": round(avg_inc_change),
                "avg_income_change_pct": round(avg_inc_change / max(avg_base_inc, 1) * 100, 1),
                "avg_land_value": round(float(impact_means.loc[d, "land_value"])),
                "pct_winners": round(float(wl_means.loc[d, "is_winner"]) * 100, 1),
                "pct_losers": round(float(wl_means.loc[d, "is_loser"]) * 100, 1),
                "pct_unchanged": round(float(wl_means.loc[d, "is_unchanged"]) * 100, 1),
            })
        results["impact_scenarios"][rate_label] = scenario_data

    # === Section 6: Household vs Corporate LVT ===
    print("  Comparing household vs corporate LVT...")
    scope_scenarios = {
        "all_land": {"gov.contrib.ubi_center.land_value_tax.rate": 0.01},
        "household_only": {"gov.contrib.ubi_center.land_value_tax.household_rate": 0.01},
        "corporate_only": {"gov.contrib.ubi_center.land_value_tax.corporate_rate": 0.01},
    }

    results["revenue_by_scope"] = []
    for name, params in scope_scenarios.items():
        reform = Scenario(parameter_changes=params)
        sim = Microsimulation(scenario=reform)
        rev = float(sim.calculate("LVT", YEAR).sum()) / 1e9
        avg = float(sim.calculate("LVT", YEAR).mean())
        results["revenue_by_scope"].append({
            "scope": name,
            "revenue_bn": round(rev, 1),
            "avg_per_household": round(avg),
        })

    # === Section 7: Council Tax Replacement ===
    results["council_tax_replacement"] = {
        "council_tax_revenue_bn": round(council_tax_rev, 1),
        "total_land_bn": round(total_land_bn, 1),
        "required_lvt_rate_pct": round(required_rate * 100, 2),
    }

    # === Section 7b: Council Tax vs LVT by Decile (multiple rates) ===
    council_tax = baseline.calculate("council_tax", YEAR)
    ct_rates = [required_rate] + [r for r in [0.005, 0.01, 0.015, 0.02, 0.03, 0.05] if abs(r - required_rate) > 0.0001]
    ct_rates.sort()

    results["council_tax_vs_lvt_scenarios"] = {}
    for rate in ct_rates:
        rate_label = f"{rate * 100:.2f}%" if rate == required_rate else f"{rate * 100:.1f}%"
        print(f"  Computing council tax vs LVT at {rate_label}...")
        reform = Scenario(parameter_changes={
            "gov.contrib.ubi_center.land_value_tax.rate": rate
        })
        sim_ct = Microsimulation(scenario=reform)
        lvt_vals = sim_ct.calculate("LVT", YEAR)

        df_ct = mdf.MicroDataFrame({
            "income_decile": income_decile.values,
            "council_tax": council_tax.values,
            "lvt": lvt_vals.values,
        }, weights=weights.values)
        df_ct = df_ct[df_ct["income_decile"] > 0]

        ct_means = df_ct.groupby("income_decile")[["council_tax", "lvt"]].mean()

        scenario_data = []
        for d in ct_means.index:
            avg_ct = float(ct_means.loc[d, "council_tax"])
            avg_lvt = float(ct_means.loc[d, "lvt"])
            diff = avg_lvt - avg_ct
            scenario_data.append({
                "decile": int(d),
                "avg_council_tax": round(avg_ct),
                "avg_lvt": round(avg_lvt),
                "difference": round(diff),
                "change_pct": round(diff / max(avg_ct, 1) * 100, 1),
            })
        results["council_tax_vs_lvt_scenarios"][rate_label] = scenario_data

    # === Section 8: Single Household Example ===
    situation = {
        "people": {
            "adult": {
                "age": {YEAR: 40},
                "employment_income": {YEAR: 50_000},
            }
        },
        "benunits": {
            "benunit": {"members": ["adult"]}
        },
        "households": {
            "household": {
                "members": ["adult"],
                "main_residence_value": {YEAR: 400_000},
                "corporate_wealth": {YEAR: 50_000},
            }
        }
    }

    sim_no_lvt = Simulation(situation=situation)
    sim_with_lvt = Simulation(
        situation=situation,
        scenario=Scenario(parameter_changes={
            "gov.contrib.ubi_center.land_value_tax.rate": 0.01
        })
    )

    results["single_household_example"] = {
        "property_value": 400_000,
        "corporate_wealth": 50_000,
        "property_wealth": round(float(sim_no_lvt.calculate("property_wealth", YEAR)[0])),
        "household_land_value": round(float(sim_no_lvt.calculate("household_land_value", YEAR)[0])),
        "corporate_land_value": round(float(sim_no_lvt.calculate("corporate_land_value", YEAR)[0])),
        "total_land_value": round(float(sim_no_lvt.calculate("land_value", YEAR)[0])),
        "lvt_liability_1pct": round(float(sim_with_lvt.calculate("LVT", YEAR)[0])),
    }

    # Save results
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {OUTPUT_FILE}")
    return results

if __name__ == "__main__":
    results = run()
    print("\n=== Summary ===")
    print(f"Total UK land value: £{results['baseline']['total_land_tn']}tn")
    print(f"1% LVT revenue: £{results['revenue_by_rate'][1]['lvt_revenue_bn']}bn")
    print(f"Council Tax replacement rate: {results['council_tax_replacement']['required_lvt_rate_pct']}%")
