from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import (
    DEFAULT_DASHBOARD_OUTPUT_PATH,
    DEFAULT_OUTPUT_PATH,
    DEFAULT_YEAR,
    generate_results_file,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate dashboard-ready land value tax results."
    )
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument(
        "--sync-dashboard",
        action="store_true",
        help="Copy the generated JSON into dashboard/src/lvt_results.json as well.",
    )
    parser.add_argument(
        "--dashboard-output",
        type=Path,
        default=DEFAULT_DASHBOARD_OUTPUT_PATH,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    results = generate_results_file(
        year=args.year,
        output_path=args.output,
        sync_dashboard=args.sync_dashboard,
        dashboard_output_path=args.dashboard_output,
    )
    print(f"Results saved to {args.output}")
    if args.sync_dashboard:
        print(f"Dashboard data synced to {args.dashboard_output}")
    print(
        "Summary: "
        f"total land £{results['baseline']['total_land_tn']}tn, "
        f"budget-neutral LVT rate {results['council_tax_replacement']['required_lvt_rate_pct']}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

