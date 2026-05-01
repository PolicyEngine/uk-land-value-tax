from __future__ import annotations

import importlib
import importlib.util
import json
import os
import shutil
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd

from .analysis import (
    DEFAULT_LVT_RATES,
    build_average_land_tables,
    build_baseline_summary,
    build_council_tax_vs_lvt_table,
    build_distribution_by_decile,
    build_impact_scenario_table,
    build_ons_comparison,
    build_revenue_by_rate,
    build_revenue_by_scope,
    classify_family_type,
    format_rate_label,
    make_rate_grid,
)

DEFAULT_YEAR = 2026
DEFAULT_OUTPUT_PATH = Path("data/lvt_results.json")
DEFAULT_DASHBOARD_OUTPUT_PATH = Path("dashboard/public/data/lvt_results.json")
DEFAULT_TARGET_YEAR = 2024
DATASET_URL = "hf://policyengine/policyengine-uk-data-private/enhanced_frs_2023_24.h5"


def _policyengine_classes():
    try:
        from policyengine_uk import Microsimulation, Scenario, Simulation
    except ImportError as exc:
        raise RuntimeError(
            "Running the simulation requires policyengine-uk. "
            "Install the package with the simulation extra first."
        ) from exc
    return Microsimulation, Scenario, Simulation


def _import_uk_data_module(module_name: str, uk_data_root: Path | None = None):
    try:
        return importlib.import_module(module_name)
    except ImportError as import_error:
        candidate_roots: list[Path] = []
        env_root = os.getenv("POLICYENGINE_UK_DATA_ROOT")
        if uk_data_root is not None:
            candidate_roots.append(uk_data_root.expanduser().resolve())
        if env_root:
            candidate_roots.append(Path(env_root).expanduser().resolve())

        for root in candidate_roots:
            if not (root / "policyengine_uk_data").exists():
                continue
            sys.path.insert(0, str(root))
            try:
                return importlib.import_module(module_name)
            except ImportError:
                sys.path.pop(0)
                continue

        if module_name == "policyengine_uk_data.targets.sources.ons_land_values":
            for root in candidate_roots:
                module = _load_uk_data_target_module_from_checkout(module_name, root)
                if module is not None:
                    return module

        raise RuntimeError(
            "Loading land targets requires policyengine-uk-data. "
            "Install the package or pass --uk-data-root / set POLICYENGINE_UK_DATA_ROOT."
        ) from import_error


def _load_module_from_path(module_name: str, module_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module spec for {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _ensure_namespace_package(module_name: str, package_path: Path) -> None:
    if module_name in sys.modules:
        return
    package = types.ModuleType(module_name)
    package.__path__ = [str(package_path)]
    sys.modules[module_name] = package


def _load_uk_data_target_module_from_checkout(module_name: str, root: Path):
    package_root = root / "policyengine_uk_data"
    schema_path = package_root / "targets" / "schema.py"
    target_module_path = package_root / "targets" / "sources" / "ons_land_values.py"
    if not schema_path.exists() or not target_module_path.exists():
        return None

    _ensure_namespace_package("policyengine_uk_data", package_root)
    _ensure_namespace_package("policyengine_uk_data.targets", package_root / "targets")
    _ensure_namespace_package(
        "policyengine_uk_data.targets.sources",
        package_root / "targets" / "sources",
    )
    if "policyengine_uk_data.targets.schema" not in sys.modules:
        _load_module_from_path("policyengine_uk_data.targets.schema", schema_path)
    return _load_module_from_path(module_name, target_module_path)


def _load_ons_land_targets(
    target_year: int = DEFAULT_TARGET_YEAR,
    uk_data_root: Path | None = None,
) -> dict:
    ons_land_values = _import_uk_data_module(
        "policyengine_uk_data.targets.sources.ons_land_values",
        uk_data_root=uk_data_root,
    )
    targets = {target.name: target for target in ons_land_values.get_targets()}

    required_names = (
        "ons/household_land_value",
        "ons/corporate_land_value",
        "ons/land_value",
    )
    missing_names = [
        target_name
        for target_name in required_names
        if target_name not in targets or target_year not in targets[target_name].values
    ]
    if missing_names:
        raise RuntimeError(
            "Missing required land targets in policyengine-uk-data for "
            f"{target_year}: {', '.join(missing_names)}"
        )

    household_target = targets["ons/household_land_value"]
    corporate_target = targets["ons/corporate_land_value"]
    total_target = targets["ons/land_value"]
    return {
        "target_year": target_year,
        "target_household_tn": household_target.values[target_year] / 1e12,
        "target_corporate_tn": corporate_target.values[target_year] / 1e12,
        "target_total_tn": total_target.values[target_year] / 1e12,
        "reference_url": total_target.reference_url,
    }


def _values(result) -> np.ndarray:
    return np.asarray(result.values)


def build_results(
    year: int = DEFAULT_YEAR,
    uk_data_root: Path | None = None,
) -> dict:
    Microsimulation, Scenario, Simulation = _policyengine_classes()

    results: dict = {}
    baseline = Microsimulation(dataset=DATASET_URL)

    land_value = baseline.calculate("land_value", year)
    household_land_value = baseline.calculate("household_land_value", year)
    corporate_land_value = baseline.calculate("corporate_land_value", year)
    property_wealth = baseline.calculate("property_wealth", year)
    total_wealth = baseline.calculate("total_wealth", year)
    weights = baseline.calculate("household_weight", year)
    income = baseline.calculate("household_net_income", year)
    income_decile = baseline.calculate("household_income_decile", year)
    wealth_decile = baseline.calculate("household_wealth_decile", year)

    weight_values = _values(weights)
    land_values = _values(land_value)
    baseline_df = pd.DataFrame(
        {
            "land_value": land_values,
            "hh_land": _values(household_land_value),
            "corp_land": _values(corporate_land_value),
            "property_wealth": _values(property_wealth),
            "total_wealth": _values(total_wealth),
            "income": _values(income),
            "income_decile": _values(income_decile),
            "wealth_decile": _values(wealth_decile),
            "weight": weight_values,
        }
    )

    results["baseline"] = build_baseline_summary(baseline_df)

    country = baseline.calculate("country", year)
    region = baseline.calculate("region", year)
    ages = _values(baseline.calculate("age", year))
    is_pension_age = _values(baseline.calculate("is_SP_age", year)).astype(float)
    household_children = np.asarray(
        baseline.map_result((ages < 18).astype(float), "person", "household")
    )
    household_adults = np.asarray(
        baseline.map_result((ages >= 18).astype(float), "person", "household")
    )
    household_pensioners = np.asarray(
        baseline.map_result(is_pension_age, "person", "household")
    )
    family_types = [
        classify_family_type(adults, children, pensioners)
        for adults, children, pensioners in zip(
            household_adults,
            household_children,
            household_pensioners,
        )
    ]
    household_df = pd.DataFrame(
        {
            "land_value": land_values,
            "country": _values(country),
            "region": _values(region),
            "family_type": family_types,
            "weight": weight_values,
        }
    )
    (
        results["avg_land_by_country"],
        results["avg_land_by_region"],
        results["avg_land_by_family_type"],
    ) = build_average_land_tables(household_df)

    results["ons_comparison"] = build_ons_comparison(
        results["baseline"],
        **_load_ons_land_targets(uk_data_root=uk_data_root),
    )
    results["distribution_by_decile"] = build_distribution_by_decile(baseline_df)
    results["distribution_by_wealth_decile"] = build_distribution_by_decile(
        baseline_df, decile_col="wealth_decile"
    )

    council_tax_revenue_bn = float(baseline.calculate("council_tax", year).sum()) / 1e9
    rate_rows = []
    for rate in DEFAULT_LVT_RATES:
        reform = Scenario(
            parameter_changes={"gov.contrib.ubi_center.land_value_tax.rate": rate}
        )
        simulation = Microsimulation(scenario=reform, dataset=DATASET_URL)
        lvt = simulation.calculate("LVT", year)
        rate_rows.append(
            {
                "rate": rate,
                "lvt_revenue_bn": float(lvt.sum()) / 1e9,
                "avg_per_household": float(lvt.mean()),
            }
        )
    results["revenue_by_rate"] = build_revenue_by_rate(
        council_tax_revenue_bn, rate_rows
    )

    baseline_net_income = baseline.calculate("household_net_income", year)
    council_tax_baseline = baseline.calculate("council_tax", year)
    total_land_bn = float(land_value.sum()) / 1e9
    required_rate = council_tax_revenue_bn / total_land_bn
    impact_rates = make_rate_grid(required_rate)

    baseline_poverty_bhc = float(baseline.calculate("in_poverty_bhc", year).mean()) * 100
    baseline_poverty_ahc = float(baseline.calculate("in_poverty_ahc", year).mean()) * 100
    baseline_gini = float(baseline_net_income.gini())
    baseline_net_income_values = _values(baseline_net_income)
    council_tax_baseline_values = _values(council_tax_baseline)

    results["impact_scenarios"] = {}
    results["impact_scenarios_by_wealth"] = {}
    results["poverty_gini"] = {
        "baseline_poverty_bhc": round(baseline_poverty_bhc, 2),
        "baseline_poverty_ahc": round(baseline_poverty_ahc, 2),
        "baseline_gini": round(baseline_gini, 4),
        "scenarios": {},
    }

    for rate in impact_rates:
        rate_label = format_rate_label(rate, required_rate)
        reform = Scenario(
            parameter_changes={
                "gov.contrib.abolish_council_tax": True,
                "gov.contrib.ubi_center.land_value_tax.rate": rate,
            }
        )
        simulation = Microsimulation(scenario=reform, dataset=DATASET_URL)
        reformed_lvt = simulation.calculate("LVT", year)
        reformed_net_income = simulation.calculate("household_net_income", year)
        income_change = _values(reformed_net_income) - baseline_net_income_values

        reform_poverty_rate_bhc = float(
            simulation.calculate("in_poverty_bhc", year).mean()
        ) * 100
        reform_poverty_rate_ahc = float(
            simulation.calculate("in_poverty_ahc", year).mean()
        ) * 100
        reform_gini = float(reformed_net_income.gini())
        results["poverty_gini"]["scenarios"][rate_label] = {
            "poverty_bhc": round(reform_poverty_rate_bhc, 2),
            "poverty_ahc": round(reform_poverty_rate_ahc, 2),
            "poverty_bhc_change": round(
                reform_poverty_rate_bhc - baseline_poverty_bhc,
                2,
            ),
            "poverty_ahc_change": round(
                reform_poverty_rate_ahc - baseline_poverty_ahc,
                2,
            ),
            "gini": round(reform_gini, 4),
            "gini_change": round(reform_gini - baseline_gini, 4),
            "gini_change_pct": round(
                (reform_gini - baseline_gini) / baseline_gini * 100,
                2,
            ),
        }

        impact_df = pd.DataFrame(
            {
                "income_decile": _values(income_decile),
                "wealth_decile": _values(wealth_decile),
                "lvt": _values(reformed_lvt),
                "council_tax_saved": council_tax_baseline_values,
                "income_change": income_change,
                "baseline_income": baseline_net_income_values,
                "land_value": land_values,
                "weight": weight_values,
            }
        )
        results["impact_scenarios"][rate_label] = build_impact_scenario_table(
            impact_df
        )
        results["impact_scenarios_by_wealth"][rate_label] = build_impact_scenario_table(
            impact_df, decile_col="wealth_decile"
        )

    scope_scenarios = {
        "all_land": {"gov.contrib.ubi_center.land_value_tax.rate": 0.01},
        "household_only": {
            "gov.contrib.ubi_center.land_value_tax.household_rate": 0.01
        },
        "corporate_only": {
            "gov.contrib.ubi_center.land_value_tax.corporate_rate": 0.01
        },
    }
    scope_rows = []
    for scope, params in scope_scenarios.items():
        simulation = Microsimulation(
            scenario=Scenario(parameter_changes=params),
            dataset=DATASET_URL,
        )
        lvt = simulation.calculate("LVT", year)
        scope_rows.append(
            {
                "scope": scope,
                "revenue_bn": float(lvt.sum()) / 1e9,
                "avg_per_household": float(lvt.mean()),
            }
        )
    results["revenue_by_scope"] = build_revenue_by_scope(scope_rows)

    results["council_tax_replacement"] = {
        "council_tax_revenue_bn": round(council_tax_revenue_bn, 1),
        "total_land_bn": round(total_land_bn, 1),
        "required_lvt_rate_pct": round(required_rate * 100, 2),
    }

    results["council_tax_vs_lvt_scenarios"] = {}
    results["council_tax_vs_lvt_scenarios_by_wealth"] = {}
    for rate in impact_rates:
        rate_label = format_rate_label(rate, required_rate)
        simulation = Microsimulation(
            scenario=Scenario(
                parameter_changes={"gov.contrib.ubi_center.land_value_tax.rate": rate}
            ),
            dataset=DATASET_URL,
        )
        lvt = simulation.calculate("LVT", year)
        council_tax_vs_lvt_df = pd.DataFrame(
            {
                "income_decile": _values(income_decile),
                "wealth_decile": _values(wealth_decile),
                "council_tax": council_tax_baseline_values,
                "lvt": _values(lvt),
                "weight": weight_values,
            }
        )
        results["council_tax_vs_lvt_scenarios"][rate_label] = (
            build_council_tax_vs_lvt_table(council_tax_vs_lvt_df)
        )
        results["council_tax_vs_lvt_scenarios_by_wealth"][rate_label] = (
            build_council_tax_vs_lvt_table(
                council_tax_vs_lvt_df, decile_col="wealth_decile"
            )
        )

    example_situation = {
        "people": {
            "adult": {
                "age": {year: 40},
                "employment_income": {year: 50_000},
            }
        },
        "benunits": {"benunit": {"members": ["adult"]}},
        "households": {
            "household": {
                "members": ["adult"],
                "main_residence_value": {year: 400_000},
                "corporate_wealth": {year: 50_000},
            }
        },
    }
    no_lvt_simulation = Simulation(situation=example_situation)
    with_lvt_simulation = Simulation(
        situation=example_situation,
        scenario=Scenario(
            parameter_changes={"gov.contrib.ubi_center.land_value_tax.rate": 0.01}
        ),
    )
    results["single_household_example"] = {
        "property_value": 400_000,
        "corporate_wealth": 50_000,
        "property_wealth": round(
            float(no_lvt_simulation.calculate("property_wealth", year)[0])
        ),
        "household_land_value": round(
            float(no_lvt_simulation.calculate("household_land_value", year)[0])
        ),
        "corporate_land_value": round(
            float(no_lvt_simulation.calculate("corporate_land_value", year)[0])
        ),
        "total_land_value": round(
            float(no_lvt_simulation.calculate("land_value", year)[0])
        ),
        "lvt_liability_1pct": round(
            float(with_lvt_simulation.calculate("LVT", year)[0])
        ),
    }

    return results


def write_results(results: dict, output_path: Path = DEFAULT_OUTPUT_PATH) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2) + "\n")
    return output_path


def sync_dashboard_results(
    source_path: Path = DEFAULT_OUTPUT_PATH,
    dashboard_output_path: Path = DEFAULT_DASHBOARD_OUTPUT_PATH,
) -> Path:
    dashboard_output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, dashboard_output_path)
    return dashboard_output_path


def generate_results_file(
    year: int = DEFAULT_YEAR,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    sync_dashboard: bool = False,
    dashboard_output_path: Path = DEFAULT_DASHBOARD_OUTPUT_PATH,
    uk_data_root: Path | None = None,
) -> dict:
    results = build_results(year=year, uk_data_root=uk_data_root)
    written_output = write_results(results, output_path)
    if sync_dashboard:
        sync_dashboard_results(written_output, dashboard_output_path)
    return results
