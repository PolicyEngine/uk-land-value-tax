import { formatTn } from "../lib/formatters";

export default function MethodologyTab({ data }) {
  const comparison = data.ons_comparison;

  return (
    <div className="space-y-8">
      <div className="section-card">
        <div className="eyebrow text-slate-500">Overview</div>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">
          How the model works
        </h2>
        <p className="mt-4 text-sm leading-7 text-slate-600">
          This dashboard uses PolicyEngine UK, a static microsimulation model,
          to estimate the first-round effects of replacing council tax with a
          flat annual land value tax. It shows who pays more, who pays less,
          and how aggregate revenue, poverty, and inequality shift at rates
          near the budget-neutral range. All figures are for the 2026-27
          fiscal year.
        </p>
      </div>

      <div className="grid gap-8 xl:grid-cols-3">
        <div className="section-card">
          <div className="eyebrow text-slate-500">Included</div>
          <h3 className="mt-2 text-lg font-semibold text-slate-900">
            What the model captures
          </h3>
          <p className="mt-4 text-sm leading-7 text-slate-600">
            The model estimates household and corporate land values for every
            UK household, attributing corporate land to households through
            shareholdings. It simulates full council tax abolition replaced by
            a flat-rate LVT and reports first-round distributional, poverty,
            and inequality effects by income decile.
          </p>
        </div>

        <div className="section-card">
          <div className="eyebrow text-slate-500">Excluded</div>
          <h3 className="mt-2 text-lg font-semibold text-slate-900">
            What the model omits
          </h3>
          <p className="mt-4 text-sm leading-7 text-slate-600">
            The model does not capture land-price capitalisation in response
            to the tax, rent pass-through or landlord behavioural responses,
            or local government redesign and devolved rate-setting. Long-run
            equilibrium effects are excluded — results should not be read as
            forecasts at very high LVT rates.
          </p>
        </div>

        <div className="section-card">
          <div className="eyebrow text-slate-500">Sources</div>
          <h3 className="mt-2 text-lg font-semibold text-slate-900">
            Data and calibration
          </h3>
          <p className="mt-4 text-sm leading-7 text-slate-600">
            Household microdata comes from the Enhanced Family Resources
            Survey 2023-24 via PolicyEngine UK, with land calibration targets
            from policyengine-uk-data. The ONS {comparison.target_label} aggregate
            land value target is {formatTn(comparison.target_total_tn)}, uprated
            to 2026-27 using OBR per-capita nominal GDP growth projections.
          </p>
        </div>
      </div>

      <div className="section-card">
        <div className="eyebrow text-slate-500">Replication</div>
        <h3 className="mt-2 text-lg font-semibold text-slate-900">
          Code and data pipeline
        </h3>
        <p className="mt-4 text-sm leading-7 text-slate-600">
          A Python pipeline generates <code>lvt_results.json</code>, which
          the dashboard consumes at build time. All source code, data
          processing scripts, and configuration are available in the{" "}
          <a
            href="https://github.com/PolicyEngine/uk-land-value-tax"
            target="_blank"
            rel="noreferrer"
            className="text-blue-600 underline hover:text-blue-800"
          >
            public repository
          </a>.
        </p>
      </div>
    </div>
  );
}
