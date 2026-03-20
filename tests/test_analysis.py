import pandas as pd

from uk_land_value_tax.analysis import (
    build_average_land_tables,
    build_baseline_summary,
    build_council_tax_vs_lvt_table,
    build_distribution_by_decile,
    build_impact_scenario_table,
    classify_family_type,
    format_rate_label,
    make_rate_grid,
)


def test_classify_family_type_covers_household_shapes():
    assert classify_family_type(1, 0, 0) == "Single, no children"
    assert classify_family_type(2, 0, 0) == "Couple, no children"
    assert classify_family_type(1, 2, 0) == "Lone parent"
    assert classify_family_type(2, 2, 0) == "Couple with children"
    assert classify_family_type(1, 0, 1) == "Single pensioner"
    assert classify_family_type(2, 0, 2) == "Pensioner couple"


def test_build_baseline_summary_uses_weighted_statistics():
    df = pd.DataFrame(
        {
            "land_value": [1e12, 2e12],
            "hh_land": [0.8e12, 1.5e12],
            "corp_land": [0.2e12, 0.5e12],
            "property_wealth": [2e12, 3e12],
            "total_wealth": [4e12, 5e12],
            "weight": [1, 3],
        }
    )

    summary = build_baseline_summary(df)

    assert summary == {
        "total_land_tn": 7.0,
        "household_land_tn": 5.3,
        "corporate_land_tn": 1.7,
        "total_property_wealth_tn": 11.0,
        "total_wealth_tn": 19.0,
        "land_pct_of_property": 48.2,
        "land_pct_of_wealth": 36.8,
        "avg_land_per_household": 1750000000000,
        "median_land_value": 2000000000000,
    }


def test_build_distribution_by_decile_excludes_non_positive_deciles():
    df = pd.DataFrame(
        {
            "income_decile": [1, 1, 2, 0],
            "income": [10, 20, 40, 999],
            "land_value": [100, 200, 400, 999],
            "property_wealth": [70, 90, 120, 999],
            "weight": [1, 3, 2, 10],
        }
    )

    assert build_distribution_by_decile(df) == [
        {
            "decile": 1,
            "avg_income": 18,
            "avg_land_value": 175,
            "avg_property_wealth": 85,
            "share_of_land_pct": 46.7,
        },
        {
            "decile": 2,
            "avg_income": 40,
            "avg_land_value": 400,
            "avg_property_wealth": 120,
            "share_of_land_pct": 53.3,
        },
    ]


def test_build_impact_scenario_table_uses_weighted_winner_shares():
    df = pd.DataFrame(
        {
            "income_decile": [1, 1, 2],
            "lvt": [800, 1400, 900],
            "council_tax_saved": [1200, 1000, 900],
            "income_change": [400, -400, 0],
            "baseline_income": [20000, 30000, 40000],
            "land_value": [160000, 280000, 180000],
            "weight": [1, 3, 2],
        }
    )

    assert build_impact_scenario_table(df) == [
        {
            "decile": 1,
            "avg_lvt": 1250,
            "avg_council_tax_saved": 1050,
            "avg_net_change": -200,
            "avg_income_change_pct": -0.7,
            "avg_land_value": 250000,
            "pct_winners": 25.0,
            "pct_losers": 75.0,
            "pct_unchanged": 0.0,
        },
        {
            "decile": 2,
            "avg_lvt": 900,
            "avg_council_tax_saved": 900,
            "avg_net_change": 0,
            "avg_income_change_pct": 0.0,
            "avg_land_value": 180000,
            "pct_winners": 0.0,
            "pct_losers": 0.0,
            "pct_unchanged": 100.0,
        },
    ]


def test_build_council_tax_vs_lvt_table_reports_weighted_differences():
    df = pd.DataFrame(
        {
            "income_decile": [1, 1, 2],
            "council_tax": [1200, 1000, 900],
            "lvt": [800, 1400, 900],
            "weight": [1, 3, 2],
        }
    )

    assert build_council_tax_vs_lvt_table(df) == [
        {
            "decile": 1,
            "avg_council_tax": 1050,
            "avg_lvt": 1250,
            "difference": 200,
            "change_pct": 19.0,
        },
        {
            "decile": 2,
            "avg_council_tax": 900,
            "avg_lvt": 900,
            "difference": 0,
            "change_pct": 0.0,
        },
    ]


def test_average_land_tables_preserve_expected_labels():
    df = pd.DataFrame(
        {
            "country": ["ENGLAND", "SCOTLAND"],
            "region": ["EAST_OF_ENGLAND", "SCOTLAND"],
            "family_type": ["Couple, no children", "Single pensioner"],
            "land_value": [300000, 100000],
            "weight": [3, 1],
        }
    )

    avg_by_country, avg_by_region, avg_by_family_type = build_average_land_tables(df)

    assert avg_by_country == [
        {"group": "UK", "avg_land_value": 250000},
        {"group": "England", "avg_land_value": 300000},
        {"group": "Scotland", "avg_land_value": 100000},
    ]
    assert avg_by_region == [
        {"group": "East of England", "avg_land_value": 300000},
        {"group": "Scotland", "avg_land_value": 100000},
    ]
    assert avg_by_family_type == [
        {"group": "Couple, no children", "avg_land_value": 300000},
        {"group": "Single pensioner", "avg_land_value": 100000},
    ]


def test_make_rate_grid_deduplicates_and_formats_budget_neutral_rate():
    rates = make_rate_grid(0.01)
    assert rates == [0.005, 0.01, 0.015, 0.02, 0.03, 0.05]
    assert format_rate_label(0.01, 0.01) == "1.00%"
    assert format_rate_label(0.0073, 0.0073) == "0.73%"

