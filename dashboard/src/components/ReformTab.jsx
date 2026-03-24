"use client";

import { useMemo, useState } from "react";
import { colors } from "@policyengine/design-system/tokens/colors";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import SectionHeading from "./SectionHeading";
import {
  deriveAggregateOutcomeRows,
  deriveCouncilTaxDistribution,
  deriveScenarioSummary,
  getBudgetNeutralRateLabel,
  getScenarioOptions,
} from "../lib/dataHelpers";
import {
  formatBn,
  formatCompactCurrency,
  formatCurrency,
  formatPct,
  formatPercentagePointChange,
  formatSignedBn,
  formatSignedCurrency,
  formatSignedPct,
} from "../lib/formatters";
import { getNiceTicks, getTickDomain } from "../lib/chartUtils";
import ChartLogo from "./ChartLogo";

const PALETTE = {
  border: colors.border.light,
  grid: colors.border.light,
  text: colors.gray[700],
  muted: colors.gray[500],
  councilTax: colors.gray[700],
  lvt: colors.primary[600],
  gain: colors.primary[700],
  loss: colors.error,
  neutral: colors.gray[300],
};

const AXIS_STYLE = {
  fontSize: 12,
  fill: colors.gray[500],
};

function CustomTooltip({ active, payload, label, formatter }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-lg">
      {label ? <div className="mb-2 font-semibold text-slate-800">{label}</div> : null}
      {payload.map((entry) => (
        <div className="flex items-center justify-between gap-4" key={entry.name}>
          <span className="flex items-center gap-2 text-slate-600">
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            {entry.name}
          </span>
          <span className="font-medium text-slate-800">
            {formatter ? formatter(entry.value, entry.name) : entry.value}
          </span>
        </div>
      ))}
    </div>
  );
}

function getCouncilTaxConfig(view) {
  if (view === "share") {
    return {
      dataKey: "avg_council_tax_pct_of_income",
      name: "Council tax as % of income",
      tooltipFormatter: (value) => formatPct(value),
      yAxisFormatter: (value) => `${value}%`,
    };
  }

  return {
    dataKey: "avg_council_tax",
    name: "Average council tax",
    tooltipFormatter: (value) => formatCurrency(value),
    yAxisFormatter: (value) => formatCompactCurrency(value),
  };
}

function getImpactConfig(view) {
  if (view === "pct") {
    return {
      dataKey: "avg_income_change_pct",
      name: "Income change",
      tooltipFormatter: (value) => formatSignedPct(value),
      yAxisFormatter: (value) => `${value}%`,
      getCellColor: (row) =>
        Number(row.avg_income_change_pct) >= 0 ? PALETTE.gain : PALETTE.loss,
    };
  }

  return {
    dataKey: "avg_net_change",
    name: "Average net change",
    tooltipFormatter: (value) => formatSignedCurrency(value),
    yAxisFormatter: (value) => formatCompactCurrency(value),
    getCellColor: (row) =>
      Number(row.avg_net_change) >= 0 ? PALETTE.gain : PALETTE.loss,
  };
}

export default function ReformTab({ data }) {
  const scenarioOptions = useMemo(() => getScenarioOptions(data), [data]);
  const defaultScenario = useMemo(() => getBudgetNeutralRateLabel(data), [data]);
  const [selectedScenario, setSelectedScenario] = useState(defaultScenario);
  const [councilTaxView, setCouncilTaxView] = useState("amount");
  const [impactView, setImpactView] = useState("net");
  const [taxSwapView, setTaxSwapView] = useState("comparison");

  const selectedSummary = useMemo(
    () => deriveScenarioSummary(data, selectedScenario),
    [data, selectedScenario],
  );
  const councilTaxDistribution = useMemo(
    () => deriveCouncilTaxDistribution(data, selectedScenario),
    [data, selectedScenario],
  );
  const impactRows = data.impact_scenarios[selectedScenario] || [];
  const taxSwapRows = data.council_tax_vs_lvt_scenarios[selectedScenario] || [];
  const aggregateOutcomes = useMemo(
    () => deriveAggregateOutcomeRows(data),
    [data],
  );
  const councilTaxConfig = useMemo(
    () => getCouncilTaxConfig(councilTaxView),
    [councilTaxView],
  );
  const impactConfig = useMemo(() => getImpactConfig(impactView), [impactView]);

  const avgCouncilTaxBill = Math.round(
    councilTaxDistribution.reduce((sum, row) => sum + row.avg_council_tax, 0) /
      Math.max(councilTaxDistribution.length, 1),
  );

  const councilTaxTicks = useMemo(() => {
    const values = councilTaxDistribution.map((row) => Number(row[councilTaxConfig.dataKey] || 0));
    return getNiceTicks([0, Math.max(0, ...values)]);
  }, [councilTaxConfig.dataKey, councilTaxDistribution]);

  const impactTicks = useMemo(() => {
    const values = impactRows.map((row) => Number(row[impactConfig.dataKey] || 0));
    return getNiceTicks([Math.min(0, ...values), Math.max(0, ...values)]);
  }, [impactConfig.dataKey, impactRows]);

  const taxSwapDiffRows = useMemo(
    () =>
      taxSwapRows.map((row) => ({
        ...row,
        tax_diff: Number(row.avg_lvt || 0) - Number(row.avg_council_tax || 0),
      })),
    [taxSwapRows],
  );

  const taxSwapTicks = useMemo(() => {
    if (taxSwapView === "difference") {
      const values = taxSwapDiffRows.map((row) => row.tax_diff);
      return getNiceTicks([Math.min(0, ...values), Math.max(0, ...values)]);
    }
    const values = taxSwapRows.flatMap((row) => [Number(row.avg_council_tax || 0), Number(row.avg_lvt || 0)]);
    return getNiceTicks([0, Math.max(0, ...values)]);
  }, [taxSwapRows, taxSwapDiffRows, taxSwapView]);

  const winnersLosersTicks = useMemo(() => getNiceTicks([0, 100]), []);

  return (
    <div className="space-y-8">
      <SectionHeading
        title="Replace council tax with land value tax"
        description="Estimate how a flat annual land value tax reshapes 2026-27 tax burdens relative to council tax. This static first-round simulation captures immediate distributional effects without modelling equilibrium adjustments in land prices, rents, ownership, or local tax design, so the scenarios shown focus on the council-tax-replacement range rather than treating very high LVT rates as literal policy forecasts."
      />

      <div className="section-card">
          <SectionHeading
            title="Choose a land value tax rate"
            description="Compare the three scenarios closest to a plausible council-tax replacement range. The revenue line on each card shows how much revenue each scenario raises relative to current council tax."
          />
        <div className="grid gap-4 lg:grid-cols-3">
          {scenarioOptions.map((option) => {
            const summary = deriveScenarioSummary(data, option.value);
            return (
              <button
                key={option.value}
                className={`selector-chip ${selectedScenario === option.value ? "active" : ""}`}
                onClick={() => setSelectedScenario(option.value)}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold text-slate-900">{option.title}</div>
                    <div className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
                      {option.value}
                    </div>
                  </div>
                  <div className="selector-chip-status px-3 py-1 text-xs font-medium shadow-sm">
                    {summary.net_revenue_bn === 0 ? "Revenue neutral" : "Revenue change"}
                  </div>
                </div>
                <div className="mt-3 text-sm text-slate-600">{option.description}</div>
                <div className="mt-4 text-sm font-medium text-slate-800">
                  {formatSignedBn(summary.net_revenue_bn)}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <div className="metric-card">
          <div className="text-xs font-medium uppercase tracking-[0.08em] text-slate-500">
            Budget-neutral rate
          </div>
          <div className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
            {data.council_tax_replacement.required_lvt_rate_pct}%
          </div>
          <div className="mt-2 text-sm text-slate-500">
            Annual rate on total land value.
          </div>
        </div>
        <div className="metric-card">
          <div className="text-xs font-medium uppercase tracking-[0.08em] text-slate-500">
            Council tax revenue
          </div>
          <div className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
            {formatBn(data.council_tax_replacement.council_tax_revenue_bn)}
          </div>
          <div className="mt-2 text-sm text-slate-500">
            Annual revenue in 2026-27.
          </div>
        </div>
        <div className="metric-card">
          <div className="text-xs font-medium uppercase tracking-[0.08em] text-slate-500">
            Average council tax bill
          </div>
          <div className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
            {formatCurrency(avgCouncilTaxBill)}
          </div>
          <div className="mt-2 text-sm text-slate-500">
            Approximate 2026-27 decile-average baseline bill.
          </div>
        </div>
        <div className="metric-card">
          <div className="text-xs font-medium uppercase tracking-[0.08em] text-slate-500">
            Selected scenario impact
          </div>
          <div className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
            {formatSignedCurrency(selectedSummary.avg_net_change)}
          </div>
          <div className="mt-2 text-sm text-slate-500">
            Average 2026-27 household net change at {selectedScenario}.
          </div>
        </div>
        <div className="metric-card">
          <div className="text-xs font-medium uppercase tracking-[0.08em] text-slate-500">
            Households gaining
          </div>
          <div className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
            {formatPct(selectedSummary.pct_winners)}
          </div>
          <div className="mt-2 text-sm text-slate-500">
            Better off at {selectedScenario}.
          </div>
        </div>
      </div>

      <div className="grid gap-8 xl:grid-cols-[1.1fr_1fr]">
        <div className="section-card">
          <SectionHeading
            title="Current council tax burden"
            description="If the story is council tax to LVT, the starting point matters. This chart shows how today’s average council tax burden varies across income deciles."
          />
          <div className="mb-5 flex flex-wrap gap-2">
            <button
              className={`toggle-button ${councilTaxView === "amount" ? "active" : ""}`}
              onClick={() => setCouncilTaxView("amount")}
            >
              Average bill
            </button>
            <button
              className={`toggle-button ${councilTaxView === "share" ? "active" : ""}`}
              onClick={() => setCouncilTaxView("share")}
            >
              % of income
            </button>
          </div>
          <div className="h-[320px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={councilTaxDistribution}>
                <CartesianGrid strokeDasharray="3 3" stroke={PALETTE.grid} />
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
                  ticks={councilTaxTicks}
                  domain={getTickDomain(councilTaxTicks)}
                  tick={AXIS_STYLE}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={councilTaxConfig.yAxisFormatter}
                />
                <Tooltip
                  content={<CustomTooltip formatter={councilTaxConfig.tooltipFormatter} />}
                />
                <Bar
                  dataKey={councilTaxConfig.dataKey}
                  name={councilTaxConfig.name}
                  fill={PALETTE.councilTax}
                  radius={[6, 6, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <ChartLogo />
        </div>

        <div className="section-card">
          <SectionHeading
            title="Aggregate outcomes"
            description="These compact indicators keep the public view near the plausible implementation range."
          />
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Scenario</th>
                  <th>Avg impact</th>
                  <th>Gaining</th>
                  <th>BHC poverty</th>
                  <th>AHC poverty</th>
                  <th>Gini</th>
                </tr>
              </thead>
              <tbody>
                {aggregateOutcomes.map((row) => (
                  <tr key={row.rate}>
                    <td>
                      <div className="font-medium text-slate-900">{row.title}</div>
                      <div className="text-xs text-slate-500">{row.rate}</div>
                    </td>
                    <td>{formatSignedCurrency(row.avg_net_change)}</td>
                    <td>{formatPct(row.pct_winners)}</td>
                    <td>{formatPercentagePointChange(row.poverty_bhc_change)}</td>
                    <td>{formatPercentagePointChange(row.poverty_ahc_change)}</td>
                    <td>{formatSignedPct(row.gini_change_pct, 2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="section-card">
        <SectionHeading
          title="Distributional impact of the swap"
          description={`At ${selectedScenario}, the chart below shows the average 2026-27 net change in household income after abolishing council tax and applying the selected LVT rate.`}
        />
        <div className="mb-5 flex flex-wrap gap-2">
          <button
            className={`toggle-button ${impactView === "net" ? "active" : ""}`}
            onClick={() => setImpactView("net")}
          >
            Absolute (£)
          </button>
          <button
            className={`toggle-button ${impactView === "pct" ? "active" : ""}`}
            onClick={() => setImpactView("pct")}
          >
            % of income
          </button>
        </div>
        <div className="h-[340px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={impactRows}>
              <CartesianGrid strokeDasharray="3 3" stroke={PALETTE.grid} />
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
                  ticks={impactTicks}
                  domain={getTickDomain(impactTicks)}
                  tick={AXIS_STYLE}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={impactConfig.yAxisFormatter}
                />
              <ReferenceLine y={0} stroke={colors.gray[400]} strokeWidth={1} />
              <Tooltip
                content={<CustomTooltip formatter={impactConfig.tooltipFormatter} />}
              />
              <Bar
                dataKey={impactConfig.dataKey}
                name={impactConfig.name}
                radius={[6, 6, 0, 0]}
              >
                {impactRows.map((row) => (
                  <Cell
                    key={`${row.decile}-fill`}
                    fill={impactConfig.getCellColor(row)}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <ChartLogo />
      </div>

      <div className="grid gap-8 xl:grid-cols-[1.15fr_1fr]">
        <div className="section-card">
          <SectionHeading
            title="Current council tax versus proposed LVT"
            description="This puts the swap itself in view, by showing the average council tax bill and the average LVT charge under the selected scenario for each income decile."
          />
          <div className="mb-5 flex flex-wrap gap-2">
            <button
              className={`toggle-button ${taxSwapView === "comparison" ? "active" : ""}`}
              onClick={() => setTaxSwapView("comparison")}
            >
              Side by side
            </button>
            <button
              className={`toggle-button ${taxSwapView === "difference" ? "active" : ""}`}
              onClick={() => setTaxSwapView("difference")}
            >
              Difference
            </button>
          </div>
          <div className="h-[360px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              {taxSwapView === "comparison" ? (
                <BarChart data={taxSwapRows} barGap={6}>
                  <CartesianGrid strokeDasharray="3 3" stroke={PALETTE.grid} />
                  <XAxis dataKey="decile" tick={AXIS_STYLE} tickLine={false} />
                  <YAxis
                    ticks={taxSwapTicks}
                    domain={getTickDomain(taxSwapTicks)}
                    tick={AXIS_STYLE}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(value) => formatCompactCurrency(value)}
                  />
                  <Tooltip
                    content={
                      <CustomTooltip formatter={(value) => formatCurrency(value)} />
                    }
                  />
                  <Legend />
                  <Bar
                    dataKey="avg_council_tax"
                    name="Council tax"
                    fill={PALETTE.councilTax}
                    radius={[6, 6, 0, 0]}
                  />
                  <Bar
                    dataKey="avg_lvt"
                    name={`LVT at ${selectedScenario}`}
                    fill={PALETTE.lvt}
                    radius={[6, 6, 0, 0]}
                  />
                </BarChart>
              ) : (
                <BarChart data={taxSwapDiffRows}>
                  <CartesianGrid strokeDasharray="3 3" stroke={PALETTE.grid} />
                  <XAxis dataKey="decile" tick={AXIS_STYLE} tickLine={false} />
                  <YAxis
                    ticks={taxSwapTicks}
                    domain={getTickDomain(taxSwapTicks)}
                    tick={AXIS_STYLE}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(value) => formatCompactCurrency(value)}
                  />
                  <ReferenceLine y={0} stroke={colors.gray[400]} strokeWidth={1} />
                  <Tooltip
                    content={
                      <CustomTooltip formatter={(value) => formatSignedCurrency(value)} />
                    }
                  />
                  <Bar
                    dataKey="tax_diff"
                    name={`LVT minus council tax`}
                    radius={[6, 6, 0, 0]}
                  >
                    {taxSwapDiffRows.map((row) => (
                      <Cell
                        key={`${row.decile}-diff`}
                        fill={row.tax_diff >= 0 ? PALETTE.loss : PALETTE.gain}
                      />
                    ))}
                  </Bar>
                </BarChart>
              )}
            </ResponsiveContainer>
          </div>
          <ChartLogo />
        </div>

        <div className="section-card">
          <SectionHeading
            title="Winners and losers"
            description="Each decile contains the same share of households, so this chart shows who comes out ahead or behind within those groups."
          />
          <div className="h-[360px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={impactRows} margin={{ top: 10, right: 12, left: 4, bottom: 24 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={PALETTE.grid} />
                <XAxis dataKey="decile" tick={AXIS_STYLE} tickLine={false} />
                <YAxis
                  ticks={winnersLosersTicks}
                  tick={AXIS_STYLE}
                  tickLine={false}
                  axisLine={false}
                  domain={[0, 100]}
                  tickFormatter={(value) => `${value}%`}
                />
                <Tooltip
                  content={<CustomTooltip formatter={(value) => formatPct(value)} />}
                />
                <Legend />
                <Bar
                  dataKey="pct_winners"
                  name="Better off"
                  stackId="shares"
                  fill={PALETTE.gain}
                  radius={[0, 0, 6, 6]}
                />
                <Bar
                  dataKey="pct_unchanged"
                  name="No change"
                  stackId="shares"
                  fill={PALETTE.neutral}
                />
                <Bar
                  dataKey="pct_losers"
                  name="Worse off"
                  stackId="shares"
                  fill={PALETTE.loss}
                  radius={[6, 6, 0, 0]}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <ChartLogo />
        </div>
      </div>
    </div>
  );
}
