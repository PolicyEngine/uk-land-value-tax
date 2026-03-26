"use client";

import { useState } from "react";
import { colors } from "@policyengine/design-system/tokens/colors";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import SectionHeading from "./SectionHeading";
import { formatCompactCurrency, formatCurrency, formatTn } from "../lib/formatters";
import { getNiceTicks, getTickDomain } from "../lib/chartUtils";
import ChartLogo from "./ChartLogo";

const AXIS_STYLE = {
  fontSize: 12,
  fill: colors.gray[500],
};

const TABLE_VIEW_CONFIG = {
  region: {
    buttonLabel: "Region",
    headingLabel: "Region",
    rowsKey: "avg_land_by_region",
  },
  country: {
    buttonLabel: "Country",
    headingLabel: "Country",
    rowsKey: "avg_land_by_country",
  },
  family: {
    buttonLabel: "Household type",
    headingLabel: "Household type",
    rowsKey: "avg_land_by_family_type",
  },
};

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-lg">
      <div className="mb-2 font-semibold text-slate-800">{label}</div>
      {payload.map((entry) => (
        <div className="flex items-center justify-between gap-4" key={entry.name}>
          <span className="flex items-center gap-2 text-slate-600">
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            {entry.name}
          </span>
          <span className="font-medium text-slate-800">{formatCurrency(entry.value)}</span>
        </div>
      ))}
    </div>
  );
}

export default function BaselineTab({ data }) {
  const [tableView, setTableView] = useState("region");
  const tableConfig = TABLE_VIEW_CONFIG[tableView];
  const tableRows = data[tableConfig.rowsKey];
  const comparison = data.ons_comparison;
  const landValueTicks = getNiceTicks([
    0,
    Math.max(...data.distribution_by_decile.map((row) => Number(row.avg_land_value || 0))),
  ]);

  return (
    <div className="space-y-8">
      <SectionHeading
        title="Land baseline"
        description="Overview of the UK's modelled land base for 2026-27: aggregate land values, comparison with ONS targets, and how household land ownership varies by region, country, and income."
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="metric-card">
          <div className="text-xs font-medium uppercase tracking-[0.08em] text-slate-500">
            Total land value
          </div>
          <div className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
            {formatTn(data.baseline.total_land_tn)}
          </div>
        </div>
        <div className="metric-card">
          <div className="text-xs font-medium uppercase tracking-[0.08em] text-slate-500">
            Household land
          </div>
          <div className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
            {formatTn(data.baseline.household_land_tn)}
          </div>
        </div>
        <div className="metric-card">
          <div className="text-xs font-medium uppercase tracking-[0.08em] text-slate-500">
            Corporate land
          </div>
          <div className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
            {formatTn(data.baseline.corporate_land_tn)}
          </div>
        </div>
        <div className="metric-card">
          <div className="text-xs font-medium uppercase tracking-[0.08em] text-slate-500">
            Model vs target
          </div>
          <div className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
            {comparison.model_vs_target_pct}%
          </div>
          <div className="mt-2 text-sm text-slate-500">
            Modelled 2026-27 total land value as a share of the ONS 2024-25 target.
          </div>
        </div>
      </div>

      <div className="grid gap-8 xl:grid-cols-[1fr_1.15fr]">
        <div className="section-card">
          <SectionHeading
            title="Official comparison"
            description="Modelled 2026-27 land values compared with ONS National Balance Sheet 2024-25 totals for household, corporate, and total land."
          />
          <table className="data-table">
            <thead>
              <tr>
                <th>Source</th>
                <th>Period</th>
                <th>Household</th>
                <th>Corporate</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Upstream target</td>
                <td>{comparison.target_label}</td>
                <td>{formatTn(comparison.target_household_tn)}</td>
                <td>{formatTn(comparison.target_corporate_tn)}</td>
                <td>{formatTn(comparison.target_total_tn)}</td>
              </tr>
              <tr>
                <td>PolicyEngine</td>
                <td>2026-27</td>
                <td>{formatTn(comparison.model_2026_household_tn)}</td>
                <td>{formatTn(comparison.model_2026_corporate_tn)}</td>
                <td>{formatTn(comparison.model_2026_total_tn)}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="section-card">
          <SectionHeading
            title="Average land value by group"
            description="Average household land value (the land component of residential property) by region, country, or household type. Excludes corporate land."
          />
          <div className="mb-5 flex flex-wrap gap-2">
            {Object.entries(TABLE_VIEW_CONFIG).map(([view, config]) => (
              <button
                key={view}
                className={`toggle-button ${tableView === view ? "active" : ""}`}
                onClick={() => setTableView(view)}
              >
                {config.buttonLabel}
              </button>
            ))}
          </div>
          <div className="max-h-[420px] overflow-y-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>{tableConfig.headingLabel}</th>
                  <th>Average land value</th>
                </tr>
              </thead>
              <tbody>
                {[...tableRows].sort((a, b) => b.avg_land_value - a.avg_land_value).map((row) => (
                  <tr key={row.group}>
                    <td>{row.group}</td>
                    <td>{formatCurrency(row.avg_land_value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="section-card">
        <SectionHeading
          title="Land value by income decile"
          description="Average household land value by equivalised household income decile, showing how residential land ownership concentrates toward higher-income households."
        />
        <div className="h-[340px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.distribution_by_decile}>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.border.light} />
              <XAxis
                dataKey="decile"
                tick={AXIS_STYLE}
                tickLine={false}
                label={{
                  value: "Income decile",
                  position: "insideBottom",
                  offset: -12,
                  style: AXIS_STYLE,
                }}
              />
              <YAxis
                ticks={landValueTicks}
                domain={getTickDomain(landValueTicks)}
                tick={AXIS_STYLE}
                tickLine={false}
                axisLine={false}
                tickFormatter={(value) => formatCompactCurrency(value)}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar
                dataKey="avg_land_value"
                name="Average land value"
                fill={colors.primary[600]}
                radius={[6, 6, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <ChartLogo />
      </div>
    </div>
  );
}
