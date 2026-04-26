export function parseRateLabel(label) {
  return Number(String(label).replace("%", ""));
}

export function formatRateLabel(rate) {
  return `${rate.toFixed(rate >= 1 ? 1 : 2)}%`;
}

export function getBudgetNeutralRateLabel(data) {
  const rawRate = data.council_tax_replacement.required_lvt_rate_pct;
  return (
    Object.keys(data.impact_scenarios).find((label) => parseRateLabel(label) === rawRate) ||
    Object.keys(data.impact_scenarios).find(
      (label) => Math.abs(parseRateLabel(label) - rawRate) < 0.001,
    ) ||
    Object.keys(data.impact_scenarios)[0]
  );
}

export function getScenarioOptions(data) {
  const labels = Object.keys(data.impact_scenarios).sort(
    (a, b) => parseRateLabel(a) - parseRateLabel(b),
  );
  const neutral = getBudgetNeutralRateLabel(data);
  const neutralRate = parseRateLabel(neutral);
  const lower = [...labels]
    .reverse()
    .find((label) => parseRateLabel(label) < neutralRate);
  const higher = labels.find((label) => parseRateLabel(label) > neutralRate);

  return [
    lower
      ? {
          value: lower,
          title: "Below neutral",
          description: "Raises less than council tax",
        }
      : null,
    {
      value: neutral,
      title: "Budget-neutral",
      description: "Raises the same revenue as council tax",
    },
    higher
      ? {
          value: higher,
          title: "Above neutral",
          description: "Raises more than council tax",
        }
      : null,
  ].filter(Boolean);
}

function averageAcrossDeciles(rows, key) {
  if (!rows?.length) return 0;
  return rows.reduce((sum, row) => sum + Number(row[key] || 0), 0) / rows.length;
}

function findRevenueRow(data, scenarioLabel) {
  const rate = parseRateLabel(scenarioLabel) / 100;
  return data.revenue_by_rate.find((row) => Math.abs(Number(row.rate) - rate) < 1e-9);
}

export function deriveScenarioSummary(data, scenarioLabel) {
  const impactRows = data.impact_scenarios[scenarioLabel] || [];
  const taxRows = data.council_tax_vs_lvt_scenarios[scenarioLabel] || [];
  const neutralLabel = getBudgetNeutralRateLabel(data);
  const revenueRow =
    scenarioLabel === neutralLabel
      ? {
          lvt_revenue_bn: data.council_tax_replacement.council_tax_revenue_bn,
          net_revenue_bn: 0,
        }
      : findRevenueRow(data, scenarioLabel);

  return {
    avg_net_change: Math.round(averageAcrossDeciles(impactRows, "avg_net_change")),
    avg_income_change_pct: Number(
      averageAcrossDeciles(impactRows, "avg_income_change_pct").toFixed(1),
    ),
    pct_winners: Number(
      averageAcrossDeciles(impactRows, "pct_winners").toFixed(1),
    ),
    pct_losers: Number(averageAcrossDeciles(impactRows, "pct_losers").toFixed(1)),
    pct_unchanged: Number(
      averageAcrossDeciles(impactRows, "pct_unchanged").toFixed(1),
    ),
    avg_council_tax: Math.round(
      averageAcrossDeciles(taxRows, "avg_council_tax"),
    ),
    avg_lvt: Math.round(averageAcrossDeciles(taxRows, "avg_lvt")),
    net_revenue_bn: Number((revenueRow?.net_revenue_bn ?? 0).toFixed(1)),
    lvt_revenue_bn: Number((revenueRow?.lvt_revenue_bn ?? 0).toFixed(1)),
  };
}

export function deriveCouncilTaxDistribution(data, scenarioLabel) {
  const referenceLabel = scenarioLabel || getBudgetNeutralRateLabel(data);
  const impactRows = new Map(
    (data.impact_scenarios[referenceLabel] || []).map((row) => [row.decile, row]),
  );

  return (data.distribution_by_decile || []).map((row) => {
    const avgCouncilTax = impactRows.get(row.decile)?.avg_council_tax_saved ?? 0;
    return {
      decile: row.decile,
      avg_income: row.avg_income,
      avg_land_value: row.avg_land_value,
      avg_council_tax: avgCouncilTax,
      avg_council_tax_pct_of_income:
        row.avg_income > 0 ? Number(((avgCouncilTax / row.avg_income) * 100).toFixed(1)) : 0,
    };
  });
}

export function deriveAggregateOutcomeRows(data) {
  return getScenarioOptions(data).map((option) => {
    const summary = deriveScenarioSummary(data, option.value);
    const poverty = data.poverty_gini.scenarios[option.value];
    return {
      ...option,
      rate: option.value,
      avg_net_change: summary.avg_net_change,
      pct_winners: summary.pct_winners,
      poverty_bhc_change: poverty.poverty_bhc_change,
      poverty_ahc_change: poverty.poverty_ahc_change,
      gini_change: poverty.gini_change,
    };
  });
}
