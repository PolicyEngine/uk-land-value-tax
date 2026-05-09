"""LVT analysis pipeline using the policyengine.py client.

This module orchestrates the baseline / reform microsimulation runs and
shapes the results into the JSON the dashboard and post consume. All
simulation work goes through ``policyengine.py`` (the v4 client), which is
the path PolicyEngine is steering users toward.
"""

from __future__ import annotations

import datetime
import importlib
import importlib.util
import json
import os
import shutil
import sys
import types
from pathlib import Path
from typing import Iterable

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
DATASET_CACHE = Path(os.getenv("PE_UK_DATA_FOLDER", "/tmp/pe_data"))


# ---------------------------------------------------------------------------
# policyengine.py setup helpers
# ---------------------------------------------------------------------------


def _import_pe():
    try:
        import policyengine as pe
        from policyengine.core import (
            Parameter,
            ParameterValue,
            Policy,
            Simulation,
        )
        from policyengine.tax_benefit_models.uk import uk_latest
    except ImportError as exc:
        raise RuntimeError(
            "Running the simulation requires policyengine and policyengine-uk. "
            "Install the package with the simulation extra first."
        ) from exc
    return pe, Simulation, Policy, Parameter, ParameterValue, uk_latest


def _ensure_dataset(year: int):
    pe, *_ = _import_pe()
    DATASET_CACHE.mkdir(parents=True, exist_ok=True)
    ds_map = pe.uk.ensure_datasets(
        datasets=[DATASET_URL],
        years=[year],
        data_folder=str(DATASET_CACHE),
    )
    return next(iter(ds_map.values()))


def _build_policy(year: int, parameter_changes: dict) -> "Policy":
    """Translate a ``{path: value}`` dict into a single-period Policy."""
    _, _, Policy, Parameter, ParameterValue, uk_latest = _import_pe()
    parameter_values = []
    start = datetime.date(year, 1, 1)
    end = datetime.date(year, 12, 31)
    for path, value in parameter_changes.items():
        param = Parameter(
            id=f"{uk_latest.id}-{path}",
            name=path,
            tax_benefit_model_version=uk_latest,
            description=path,
            data_type=type(value) if not isinstance(value, bool) else bool,
        )
        parameter_values.append(
            ParameterValue(
                parameter=param,
                start_date=start,
                end_date=end,
                value=value,
            )
        )
    return Policy(
        name=f"LVT scenario {year}",
        description=", ".join(parameter_changes),
        parameter_values=parameter_values,
    )


HOUSEHOLD_BASE_VARS = (
    "household_id",
    "household_weight",
    "household_net_income",
    "council_tax",
    "council_tax_benefit",
    "council_tax_less_benefit",
    "land_value",
    "household_land_value",
    "corporate_land_value",
    "property_wealth",
    "total_wealth",
    "household_income_decile",
    "household_wealth_decile",
    "in_poverty_bhc",
    "in_poverty_ahc",
    "country",
    "region",
    "LVT",
)
PERSON_BASE_VARS = ("person_id", "household_id", "age", "is_SP_age")


def _run(
    dataset,
    parameter_changes: dict | None = None,
    *,
    year: int,
    extra_household: Iterable[str] = (),
    extra_person: Iterable[str] = (),
):
    """Run a Simulation and return (household_df, person_df).

    ``parameter_changes`` is a flat ``{path: value}`` dict; ``None`` runs
    the baseline.
    """
    pe, Simulation, *_ , uk_latest = _import_pe()
    household_vars = sorted(set(HOUSEHOLD_BASE_VARS) | set(extra_household))
    person_vars = sorted(set(PERSON_BASE_VARS) | set(extra_person))
    kwargs = dict(
        dataset=dataset,
        tax_benefit_model_version=uk_latest,
        extra_variables={"household": household_vars, "person": person_vars},
    )
    if parameter_changes:
        kwargs["policy"] = _build_policy(year, parameter_changes)
    sim = Simulation(**kwargs)
    sim.run()
    out = sim.output_dataset.data
    return out.household, out.person


# ---------------------------------------------------------------------------
# ONS land target loader (unchanged dependency on policyengine-uk-data)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def _household_family_types(person_df: pd.DataFrame, household_ids: pd.Series) -> list[str]:
    children = (person_df["age"].astype(float) < 18).astype(float)
    adults = (person_df["age"].astype(float) >= 18).astype(float)
    pensioners = person_df["is_SP_age"].astype(float)

    grouped = pd.DataFrame(
        {
            "household_id": person_df["household_id"].astype(int).values,
            "children": children.values,
            "adults": adults.values,
            "pensioners": pensioners.values,
        }
    ).groupby("household_id").sum()

    aligned = grouped.reindex(household_ids.astype(int).values).fillna(0)
    return [
        classify_family_type(adults, children, pensioners)
        for adults, children, pensioners in zip(
            aligned["adults"].values,
            aligned["children"].values,
            aligned["pensioners"].values,
        )
    ]


def _df_to_pandas(microdf, columns: Iterable[str]) -> pd.DataFrame:
    """Pull selected columns out of a MicroDataFrame as a plain DataFrame."""
    return pd.DataFrame({col: np.asarray(microdf[col]) for col in columns})


def build_results(
    year: int = DEFAULT_YEAR,
    uk_data_root: Path | None = None,
) -> dict:
    dataset = _ensure_dataset(year)

    results: dict = {}

    # Baseline run
    household, person = _run(dataset, None, year=year)

    weight_values = np.asarray(household["household_weight"])
    land_values = np.asarray(household["land_value"])
    income_decile = np.asarray(household["household_income_decile"])
    wealth_decile = np.asarray(household["household_wealth_decile"])

    baseline_df = pd.DataFrame(
        {
            "land_value": land_values,
            "hh_land": np.asarray(household["household_land_value"]),
            "corp_land": np.asarray(household["corporate_land_value"]),
            "property_wealth": np.asarray(household["property_wealth"]),
            "total_wealth": np.asarray(household["total_wealth"]),
            "income": np.asarray(household["household_net_income"]),
            "income_decile": income_decile,
            "wealth_decile": wealth_decile,
            "weight": weight_values,
        }
    )

    results["baseline"] = build_baseline_summary(baseline_df)

    family_types = _household_family_types(person, household["household_id"])
    household_df = pd.DataFrame(
        {
            "land_value": land_values,
            "country": np.asarray(household["country"]),
            "region": np.asarray(household["region"]),
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

    # Use the MicroSeries weights so .gini() / .mean() are weighted correctly.
    baseline_net_income_microseries = household["household_net_income"]
    baseline_total_wealth_microseries = household["total_wealth"]
    baseline_in_poverty_bhc = household["in_poverty_bhc"]
    baseline_in_poverty_ahc = household["in_poverty_ahc"]
    council_tax_baseline_values = np.asarray(household["council_tax_less_benefit"])
    council_tax_revenue_bn = float(household["council_tax_less_benefit"].sum()) / 1e9

    # Revenue by rate (LVT-only, no abolition)
    rate_rows = []
    for rate in DEFAULT_LVT_RATES:
        hh_rate, _ = _run(
            dataset,
            {"gov.contrib.ubi_center.land_value_tax.rate": rate},
            year=year,
        )
        lvt = hh_rate["LVT"]
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

    total_land_bn = float(np.sum(land_values * weight_values)) / 1e9
    required_rate = council_tax_revenue_bn / total_land_bn
    impact_rates = make_rate_grid(required_rate)

    baseline_poverty_bhc = float(baseline_in_poverty_bhc.mean()) * 100
    baseline_poverty_ahc = float(baseline_in_poverty_ahc.mean()) * 100
    baseline_gini = float(baseline_net_income_microseries.gini())
    baseline_wealth_gini = float(baseline_total_wealth_microseries.gini())
    baseline_net_income_values = np.asarray(baseline_net_income_microseries)

    results["impact_scenarios"] = {}
    results["impact_scenarios_by_wealth"] = {}
    results["poverty_gini"] = {
        "baseline_poverty_bhc": round(baseline_poverty_bhc, 2),
        "baseline_poverty_ahc": round(baseline_poverty_ahc, 2),
        "baseline_gini": round(baseline_gini, 4),
        "baseline_wealth_gini": round(baseline_wealth_gini, 4),
        "scenarios": {},
    }

    for rate in impact_rates:
        rate_label = format_rate_label(rate, required_rate)
        hh_reform, _ = _run(
            dataset,
            {
                "gov.contrib.abolish_council_tax": True,
                "gov.contrib.ubi_center.land_value_tax.rate": rate,
            },
            year=year,
        )
        reformed_lvt = hh_reform["LVT"]
        reformed_net_income = hh_reform["household_net_income"]
        reformed_in_poverty_bhc = hh_reform["in_poverty_bhc"]
        reformed_in_poverty_ahc = hh_reform["in_poverty_ahc"]
        reformed_total_wealth = hh_reform["total_wealth"]
        income_change = np.asarray(reformed_net_income) - baseline_net_income_values

        reform_poverty_rate_bhc = float(reformed_in_poverty_bhc.mean()) * 100
        reform_poverty_rate_ahc = float(reformed_in_poverty_ahc.mean()) * 100
        reform_gini = float(reformed_net_income.gini())
        reform_wealth_gini = float(reformed_total_wealth.gini())
        results["poverty_gini"]["scenarios"][rate_label] = {
            "poverty_bhc": round(reform_poverty_rate_bhc, 2),
            "poverty_ahc": round(reform_poverty_rate_ahc, 2),
            "poverty_bhc_change": round(
                reform_poverty_rate_bhc - baseline_poverty_bhc, 2
            ),
            "poverty_ahc_change": round(
                reform_poverty_rate_ahc - baseline_poverty_ahc, 2
            ),
            "gini": round(reform_gini, 4),
            "gini_change": round(reform_gini - baseline_gini, 4),
            "wealth_gini": round(reform_wealth_gini, 4),
            "wealth_gini_change": round(reform_wealth_gini - baseline_wealth_gini, 4),
        }

        impact_df = pd.DataFrame(
            {
                "income_decile": income_decile,
                "wealth_decile": wealth_decile,
                "lvt": np.asarray(reformed_lvt),
                "council_tax_saved": council_tax_baseline_values,
                "income_change": income_change,
                "baseline_income": baseline_net_income_values,
                "land_value": land_values,
                "weight": weight_values,
            }
        )
        results["impact_scenarios"][rate_label] = build_impact_scenario_table(impact_df)
        results["impact_scenarios_by_wealth"][rate_label] = build_impact_scenario_table(
            impact_df, decile_col="wealth_decile"
        )

    # Scope sensitivity at 1% (all / household-only / corporate-only)
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
        hh_scope, _ = _run(dataset, params, year=year)
        lvt = hh_scope["LVT"]
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

    # Council-tax-vs-LVT comparisons by decile (no abolition; LVT layered on top)
    results["council_tax_vs_lvt_scenarios"] = {}
    results["council_tax_vs_lvt_scenarios_by_wealth"] = {}
    for rate in impact_rates:
        rate_label = format_rate_label(rate, required_rate)
        hh_layer, _ = _run(
            dataset,
            {"gov.contrib.ubi_center.land_value_tax.rate": rate},
            year=year,
        )
        lvt = hh_layer["LVT"]
        council_tax_vs_lvt_df = pd.DataFrame(
            {
                "income_decile": income_decile,
                "wealth_decile": wealth_decile,
                "council_tax": council_tax_baseline_values,
                "lvt": np.asarray(lvt),
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

    # Single-household worked example
    pe, *_ = _import_pe()
    extras_hh = [
        "property_wealth",
        "household_land_value",
        "corporate_land_value",
        "land_value",
        "LVT",
    ]
    base_hh = pe.uk.calculate_household(
        people=[{"age": 40, "employment_income": 50_000}],
        household={"main_residence_value": 400_000, "corporate_wealth": 50_000},
        year=year,
        extra_variables=extras_hh,
    )
    lvt_hh = pe.uk.calculate_household(
        people=[{"age": 40, "employment_income": 50_000}],
        household={"main_residence_value": 400_000, "corporate_wealth": 50_000},
        year=year,
        reform={"gov.contrib.ubi_center.land_value_tax.rate": 0.01},
        extra_variables=extras_hh,
    )
    results["single_household_example"] = {
        "property_value": 400_000,
        "corporate_wealth": 50_000,
        "property_wealth": round(float(base_hh.household.property_wealth)),
        "household_land_value": round(float(base_hh.household.household_land_value)),
        "corporate_land_value": round(float(base_hh.household.corporate_land_value)),
        "total_land_value": round(float(base_hh.household.land_value)),
        "lvt_liability_1pct": round(float(lvt_hh.household.LVT)),
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
    write_results(results, output_path)
    if sync_dashboard:
        sync_dashboard_results(output_path, dashboard_output_path)
    return results
