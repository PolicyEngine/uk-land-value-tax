import { formatTn } from "../lib/formatters";

export default function MethodologyTab({ data }) {
  const comparison = data.ons_comparison;

  return (
    <div className="space-y-8">
      <div className="section-card">
        <div className="eyebrow text-slate-500">What this tool is for</div>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">
          First-round analysis of a council-tax-to-LVT swap
        </h2>
        <p className="mt-4 max-w-4xl text-sm leading-7 text-slate-600">
          This tool uses a static microsimulation to replace council tax with
          an annual land value tax. It shows who pays more, who pays less, and
          how revenue, poverty, and inequality change at rates near the
          council-tax-replacement range.
        </p>
      </div>

      <div className="grid gap-8 xl:grid-cols-3">
        <div className="section-card">
          <div className="eyebrow text-slate-500">Included</div>
          <h3 className="mt-2 text-lg font-semibold text-slate-900">
            What the model does
          </h3>
          <ul className="mt-4 space-y-3 text-sm leading-6 text-slate-600">
            <li>Estimates household and corporate land values for UK households.</li>
            <li>Attributes corporate land through household shareholdings.</li>
            <li>Simulates abolishing council tax and replacing it with LVT.</li>
            <li>Reports first-round distributional, poverty, and inequality effects.</li>
          </ul>
        </div>

        <div className="section-card">
          <div className="eyebrow text-slate-500">Excluded</div>
          <h3 className="mt-2 text-lg font-semibold text-slate-900">
            What the model does not do
          </h3>
          <ul className="mt-4 space-y-3 text-sm leading-6 text-slate-600">
            <li>It does not model land-price capitalisation.</li>
            <li>It does not model rent pass-through or landlord responses.</li>
            <li>It does not model local government redesign or local rate-setting.</li>
            <li>It should not be read as a long-run equilibrium forecast for very high annual LVT rates.</li>
          </ul>
        </div>

        <div className="section-card">
          <div className="eyebrow text-slate-500">Sources</div>
          <h3 className="mt-2 text-lg font-semibold text-slate-900">
            Data and calibration
          </h3>
          <ul className="mt-4 space-y-3 text-sm leading-6 text-slate-600">
            <li>Enhanced FRS 2023-24 microdata through PolicyEngine UK.</li>
            <li>Land calibration targets from policyengine-uk-data.</li>
            <li>
              Current upstream target total: {formatTn(comparison.target_total_tn)} for{" "}
              {comparison.target_label}.
            </li>
            <li>Uprating to 2026-27 using OBR per-capita nominal GDP growth projections.</li>
          </ul>
        </div>
      </div>

      <div className="section-card">
        <div className="eyebrow text-slate-500">Replication</div>
        <h3 className="mt-2 text-lg font-semibold text-slate-900">
          Code structure
        </h3>
        <p className="mt-4 max-w-4xl text-sm leading-7 text-slate-600">
          The Python pipeline generates the JSON consumed by this app. The
          dashboard reads <code>public/data/lvt_results.json</code>, and the
          replication code lives in the public repository.
        </p>
      </div>
    </div>
  );
}
