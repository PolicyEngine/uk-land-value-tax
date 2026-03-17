import React, { useState } from 'react';
import data from './lvt_results.json';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell
} from 'recharts';
import './App.css';

const C = {
  teal500: '#319795',
  teal600: '#2C7A7B',
  teal700: '#285E61',
  blue500: '#0EA5E9',
  blue700: '#026AA2',
  baseline: '#6B7280',
  gray200: '#E2E8F0',
  gray400: '#9CA3AF',
  gray500: '#6B7280',
  gray600: '#4B5563',
  // 10-color palette: alternating teal & blue shades
  decile: [
    '#285E61', '#2C7A7B', '#319795', '#38B2AC', '#4FD1C5',
    '#026AA2', '#0284C7', '#0EA5E9', '#38BDF8', '#7DD3FC',
  ],
};

const fmt = (v) => `£${Number(v).toLocaleString()}`;
const fmtBn = (v) => `£${Number(v).toFixed(1)}bn`;
const fmtTn = (v) => `£${Number(v).toFixed(1)}tn`;
const fmtPct = (v) => `${Number(v).toFixed(1)}%`;

const AXIS_STYLE = { fontFamily: 'Inter', fontSize: 11, fill: '#6B7280' };
const GRID_STYLE = { stroke: '#E2E8F0', strokeDasharray: '3 3' };

/* Custom Tooltip matching student-loan style */
function CustomTooltip({ active, payload, label, formatter }) {
  if (!active || !payload?.length || (label && label.toString().trim() === '')) return null;
  return (
    <div className="custom-tooltip">
      <div className="tooltip-title">{label}</div>
      {payload.map((p, i) => (
        <div className="tooltip-row" key={i}>
          <span className="tooltip-label">
            <span className="tooltip-swatch" style={{ background: p.color }} />
            {p.name}
          </span>
          <span className="tooltip-value">
            {formatter ? formatter(p.value, p.name) : p.value}
          </span>
        </div>
      ))}
    </div>
  );
}

function SectionTitle({ children, prose }) {
  return (
    <div className="section-title">
      <h2>{children}</h2>
      {prose && <div className="prose">{prose}</div>}
    </div>
  );
}

function AvgLandTable() {
  const [filter, setFilter] = useState('country');
  const tableData = filter === 'country' ? data.avg_land_by_country
    : filter === 'region' ? data.avg_land_by_region
    : data.avg_land_by_family_type;

  return (
    <div>
      <div style={{ textAlign: 'center', marginBottom: 12 }}>
        <div className="chart-toggle" style={{ display: 'inline-flex' }}>
          <button className={filter === 'country' ? 'active' : ''} onClick={() => setFilter('country')}>Country</button>
          <button className={filter === 'region' ? 'active' : ''} onClick={() => setFilter('region')}>Region</button>
          <button className={filter === 'family' ? 'active' : ''} onClick={() => setFilter('family')}>Household type</button>
        </div>
      </div>
      <table className="ons-table">
        <thead>
          <tr>
            <th>{filter === 'family' ? 'Household type' : filter === 'region' ? 'Region' : 'Country'}</th>
            <th>Avg land value</th>
          </tr>
        </thead>
        <tbody>
          {tableData.map(row => (
            <tr key={row.group}>
              <td>{row.group}</td>
              <td>{fmt(row.avg_land_value)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BaselineSection() {
  return (
    <section className="dashboard-section">
      <SectionTitle prose={<p>PolicyEngine <a href="https://github.com/PolicyEngine/uk-land-value-tax" target="_blank" rel="noopener noreferrer">estimates</a> UK land values and simulates tax reforms. See the <a href="#methodology">methodology note</a> below for details on how land values are derived. The ONS <a href="https://www.ons.gov.uk/economy/nationalaccounts/uksectoraccounts/datasets/thenationalbalancesheetestimates" target="_blank" rel="noopener noreferrer">reports</a> total UK land at £{Number(data.ons_comparison.ons_2024_total_tn).toFixed(1)}tn for 2024, of which £{Number(data.ons_comparison.ons_2024_household_tn).toFixed(1)}tn is household land and £{(data.ons_comparison.ons_2024_corporate_tn + data.ons_comparison.ons_2024_government_tn).toFixed(1)}tn is non-household (corporate and government). The model estimates total UK land at £{Number(data.baseline.total_land_tn).toFixed(1)}tn, and total UK household wealth at £{Number(data.baseline.total_wealth_tn).toFixed(1)}tn, of which land accounts for {Number(data.baseline.land_pct_of_wealth).toFixed(1)}%.</p>}>
        UK land and wealth overview
      </SectionTitle>
      <div className="subsections">
        <div className="subsection-block">
          <SubsectionTitle>Comparison with official statistics</SubsectionTitle>
          <p className="subsection-prose">The ONS measures land value as non-produced assets (<a href="https://www.ons.gov.uk/economy/nationalaccounts/uksectoraccounts/datasets/thenationalbalancesheetestimates" target="_blank" rel="noopener noreferrer">AN.211</a>) across all sectors. Non-household land combines corporate (private and public non-financial corporations, financial corporations) and general government. The model uprates survey-year values using OBR per capita nominal GDP growth <a href="https://obr.uk/efo/economic-and-fiscal-outlook-march-2025/" target="_blank" rel="noopener noreferrer">projections</a>. Table 1 compares the model's estimates with published ONS figures from the National Balance <a href="https://www.ons.gov.uk/economy/nationalaccounts/uksectoraccounts/bulletins/nationalbalancesheet/2025" target="_blank" rel="noopener noreferrer">Sheet</a>.</p>
          <p className="fig-caption">Table 1. <span>Land value estimates by source (2020-27)</span></p>
          <ONSComparisonTable />
          <p className="subsection-prose finding">Table 1 shows that the model's estimate of £{Number(data.ons_comparison.model_2026_total_tn).toFixed(1)}tn exceeds the ONS 2024 figure of £{Number(data.ons_comparison.ons_2024_total_tn).toFixed(1)}tn. The household share accounts for the majority of UK land in both the ONS data and the model.</p>
        </div>
        <div className="subsection-block">
          <SubsectionTitle>Average land value per household</SubsectionTitle>
          <p className="subsection-prose">Average land value per household is the mean of estimated land value across all households in a given group. It includes both the land component of property wealth (residential and non-residential) and corporate land (derived from shareholdings). Household type is derived from the number of adults, dependent children (under 18), and whether adults are above state pension age. Pensioner households are those where all adults are at or above state pension age. Table 2 shows the breakdown by country, region, or household type.</p>
          <p className="fig-caption">Table 2. <span>Average land value per household (2026-27)</span></p>
          <AvgLandTable />
          <p className="subsection-prose finding">Table 2 shows that pensioner couples hold the highest average land value, followed by non-pensioner couples without children. Lone parents hold the lowest average. Regionally, southern England and the East of England show the highest values, whilst Northern Ireland and Scotland show the lowest.</p>
        </div>
        <div className="subsection-block">
          <SubsectionTitle>Land value distribution</SubsectionTitle>
          <p className="subsection-prose">Land ownership in the UK is unevenly distributed. Households in higher income deciles tend to own more valuable property and therefore hold a larger share of total land value. Figure 1 shows average land value by decile and each decile's share of the national total.</p>
          <p className="fig-caption">Figure 1. <span>Land value by income decile (2026-27)</span></p>
          <DistributionChart />
          <p className="subsection-prose finding">Figure 1 shows that the top decile holds the largest share of total land value, whilst the bottom decile holds the smallest. Average land value rises with income, reflecting higher rates of home ownership and more valuable properties amongst higher-income households.</p>
        </div>
      </div>
    </section>
  );
}

function ONSComparisonTable() {
  const c = data.ons_comparison;
  return (
    <table className="ons-table">
      <thead>
        <tr>
          <th>Source</th>
          <th>Year</th>
          <th>Household</th>
          <th>Non-household</th>
          <th>Total</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>ONS</td>
          <td>2020-21</td>
          <td>{fmtTn(c.ons_2020_household_tn)}</td>
          <td>{fmtTn(c.ons_2020_corporate_tn + c.ons_2020_government_tn)}</td>
          <td>{fmtTn(c.ons_2020_total_tn)}</td>
        </tr>
        <tr>
          <td>ONS</td>
          <td>2024-25</td>
          <td>{fmtTn(c.ons_2024_household_tn)}</td>
          <td>{fmtTn(c.ons_2024_corporate_tn + c.ons_2024_government_tn)}</td>
          <td>{fmtTn(c.ons_2024_total_tn)}</td>
        </tr>
        <tr className="model-row">
          <td>PE</td>
          <td>2026-27</td>
          <td>{fmtTn(c.model_2026_household_tn)}</td>
          <td>{fmtTn(c.model_2026_corporate_tn)}</td>
          <td>{fmtTn(c.model_2026_total_tn)}</td>
        </tr>
      </tbody>
    </table>
  );
}

function DistributionChart() {
  const decileData = data.distribution_by_decile;
  const [distView, setDistView] = useState('avgLand');

  return (
    <div>
      <div style={{ textAlign: 'center', marginBottom: 12 }}>
        <div className="chart-toggle" style={{ display: 'inline-flex' }}>
          <button className={distView === 'avgLand' ? 'active' : ''} onClick={() => setDistView('avgLand')}>Avg value</button>
          <button className={distView === 'share' ? 'active' : ''} onClick={() => setDistView('share')}>Share %</button>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={320}>
        {distView === 'avgLand' ? (
          <BarChart data={decileData}>
            <CartesianGrid {...GRID_STYLE} />
            <XAxis dataKey="decile" tick={AXIS_STYLE} label={{ value: 'Income decile', position: 'insideBottom', offset: -5, ...AXIS_STYLE }} />
            <YAxis tick={AXIS_STYLE} tickFormatter={(v) => `£${Math.round(v / 1000)}k`} label={{ value: 'Average land value', angle: -90, position: 'insideLeft', offset: 10, style: { ...AXIS_STYLE, textAnchor: 'middle' } }} />
            <Tooltip content={<CustomTooltip formatter={(v) => fmt(Math.round(v))} />} />
            <Bar dataKey="avg_land_value" name="Avg land value" fill={C.teal500} radius={[4,4,0,0]} />
          </BarChart>
        ) : (
          <BarChart data={decileData}>
            <CartesianGrid {...GRID_STYLE} />
            <XAxis dataKey="decile" tick={AXIS_STYLE} label={{ value: 'Income decile', position: 'insideBottom', offset: -5, ...AXIS_STYLE }} />
            <YAxis tick={AXIS_STYLE} domain={[0, 25]} ticks={[0, 5, 10, 15, 20, 25]} tickFormatter={(v) => `${v}%`} label={{ value: 'Share of total land', angle: -90, position: 'insideLeft', offset: 10, style: { ...AXIS_STYLE, textAnchor: 'middle' } }} />
            <Tooltip content={<CustomTooltip formatter={(v) => fmtPct(v)} />} />
            <Bar dataKey="share_of_land_pct" name="Share of land %" fill={C.teal500} radius={[4,4,0,0]} />
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}

function SubsectionTitle({ children }) {
  return <h3 className="subsection-title">{children}</h3>;
}

function RateSelector({ value, onChange, rates, defaultRate }) {
  return (
    <div className="rate-selector">
      <label className="rate-selector-label">LVT rate</label>
      <select className="rate-select" value={value} onChange={(e) => onChange(e.target.value)}>
        {rates.map(r => (
          <option key={r} value={r}>{r}{r === defaultRate ? ' (budget-neutral)' : ''}</option>
        ))}
      </select>
    </div>
  );
}

function RateSelectorWithAll({ value, onChange, rates, defaultRate }) {
  return (
    <div className="rate-selector">
      <label className="rate-selector-label">LVT rate</label>
      <select className="rate-select" value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="all">All rates</option>
        {rates.map(r => (
          <option key={r} value={r}>{r}{r === defaultRate ? ' (budget-neutral)' : ''}</option>
        ))}
      </select>
    </div>
  );
}

function ReformSection() {
  const revData = data.revenue_by_rate.map(r => ({
    ...r,
    net_label: r.net_revenue_bn >= 0 ? `+${fmtBn(r.net_revenue_bn)}` : fmtBn(r.net_revenue_bn),
  }));
  const ctBn = data.council_tax_replacement.council_tax_revenue_bn;
  const defaultRate = `${data.council_tax_replacement.required_lvt_rate_pct}%`;

  // Impact / poverty / Gini state
  const scenarios = data.impact_scenarios;
  const rates = Object.keys(scenarios);
  const [impactRate, setImpactRate] = useState(defaultRate);
  const impactData = scenarios[impactRate] || scenarios[rates[0]];
  const [impactView, setImpactView] = useState('net');
  const pg = data.poverty_gini;
  const [povertyRate, setPovertyRate] = useState(defaultRate);
  const [giniRate, setGiniRate] = useState(defaultRate);

  return (
    <section className="dashboard-section">
      <SectionTitle prose={`This section models a single reform: abolishing council tax and replacing it with a land value tax (LVT). PolicyEngine UK estimates that council tax raises £${ctBn} billion per year across the UK. The OBR estimates £50.9 billion for England alone in 2025-26. A ${data.council_tax_replacement.required_lvt_rate_pct}% LVT on all land would be budget-neutral for government, meaning it raises the same total revenue as council tax from a different tax base so there is no change to public spending. Higher rates raise additional revenue beyond replacing council tax. The charts below show how revenue and household-level impacts vary with the LVT rate.`}>
        Replacing council tax with LVT
      </SectionTitle>
      <SubsectionTitle>Budgetary impact</SubsectionTitle>
      <p className="subsection-prose">Council tax is a banded property tax that PolicyEngine UK estimates raises £{ctBn} billion annually across the UK. The <a href="https://obr.uk/forecasts-in-depth/tax-by-tax-spend-by-spend/council-tax/" target="_blank" rel="noopener noreferrer">OBR</a> estimates £50.9 billion for England alone in 2025-26. A land value tax levies a flat percentage on land values. At the budget-neutral rate of {data.council_tax_replacement.required_lvt_rate_pct}%, LVT raises the same total revenue for government as council tax, so there is no change to public spending. Figure 2 shows net revenue at each rate.</p>
      <p className="fig-caption">Figure 2. <span>Net revenue change by LVT rate (2026-27)</span></p>
      <div className="chart-row single">
        <div className="chart-card wide">
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={revData}>
              <CartesianGrid {...GRID_STYLE} />
              <XAxis dataKey="rate_pct" tick={AXIS_STYLE} label={{ value: 'LVT rate', position: 'insideBottom', offset: -5, ...AXIS_STYLE }} />
              <YAxis tick={AXIS_STYLE} label={{ value: 'Net revenue (£bn)', angle: -90, position: 'insideLeft', offset: 10, style: { ...AXIS_STYLE, textAnchor: 'middle' } }} />
              <Tooltip content={<CustomTooltip formatter={(v, name) => fmtBn(v)} />} />
              <Bar dataKey="net_revenue_bn" name="Net revenue change" radius={[4,4,0,0]}>
                {revData.map((d, i) => (
                  <Cell key={i} fill={d.net_revenue_bn >= 0 ? C.teal700 : C.gray400} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <p className="subsection-prose finding">Figure 2 shows that at the budget-neutral rate of {data.council_tax_replacement.required_lvt_rate_pct}%, net revenue change is close to zero. Rates above this threshold generate additional revenue for government, whilst lower rates result in a net revenue loss relative to council tax.</p>
      {/* --- Subsection: Distributional impact --- */}
      <SubsectionTitle>Distributional impact</SubsectionTitle>
      <p className="subsection-prose">Replacing council tax with LVT changes the distribution of the tax burden across income deciles. LVT is proportional to land value, whilst council tax is only loosely linked to property prices. The net effect on each household depends on how much council tax they currently pay relative to the LVT they would owe. Figure 3 shows the average net income change by decile.</p>
      <p className="fig-caption">Figure 3. <span>Distributional impact by income decile (2026-27)</span></p>
      <div className="chart-row single">
        <div className="chart-card wide">
          <div className="chart-header-row">
            <RateSelector value={impactRate} onChange={setImpactRate} rates={rates} defaultRate={defaultRate} />
            <div className="chart-toggle">
              <button className={impactView === 'net' ? 'active' : ''} onClick={() => setImpactView('net')}>Absolute (£)</button>
              <button className={impactView === 'pct' ? 'active' : ''} onClick={() => setImpactView('pct')}>% of income</button>
              <button className={impactView === 'table' ? 'active' : ''} onClick={() => setImpactView('table')}>Table</button>
            </div>
          </div>
          {impactView === 'net' && (
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={impactData}>
                <CartesianGrid {...GRID_STYLE} />
                <XAxis dataKey="decile" tick={AXIS_STYLE} label={{ value: 'Income decile', position: 'insideBottom', offset: -5, ...AXIS_STYLE }} />
                <YAxis tick={AXIS_STYLE} label={{ value: 'Net change (£)', angle: -90, position: 'insideLeft', offset: 10, style: { ...AXIS_STYLE, textAnchor: 'middle' } }} />
                <Tooltip content={<CustomTooltip formatter={(v) => `${v > 0 ? '+' : ''}${fmt(v)}`} />} />
                <Bar dataKey="avg_net_change" name="Net change" radius={[4,4,0,0]}>
                  {impactData.map((d, i) => (
                    <Cell key={i} fill={d.avg_net_change >= 0 ? C.teal700 : C.gray400} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
          {impactView === 'pct' && (
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={impactData}>
                <CartesianGrid {...GRID_STYLE} />
                <XAxis dataKey="decile" tick={AXIS_STYLE} label={{ value: 'Income decile', position: 'insideBottom', offset: -5, ...AXIS_STYLE }} />
                <YAxis tick={AXIS_STYLE} label={{ value: 'Income change (%)', angle: -90, position: 'insideLeft', offset: 10, style: { ...AXIS_STYLE, textAnchor: 'middle' } }} />
                <Tooltip content={<CustomTooltip formatter={(v) => `${v > 0 ? '+' : ''}${fmtPct(v)}`} />} />
                <Bar dataKey="avg_income_change_pct" name="Income change %" radius={[4,4,0,0]}>
                  {impactData.map((d, i) => (
                    <Cell key={i} fill={d.avg_income_change_pct >= 0 ? C.teal700 : C.gray400} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
          {impactView === 'table' && (
            <table className="impact-table">
              <thead>
                <tr>
                  <th>Decile</th>
                  <th>Council tax saved</th>
                  <th>LVT paid</th>
                  <th>Net change</th>
                  <th>% of income</th>
                </tr>
              </thead>
              <tbody>
                {impactData.map(d => (
                  <tr key={d.decile}>
                    <td>{d.decile}</td>
                    <td className="positive">+{fmt(d.avg_council_tax_saved)}</td>
                    <td>{fmt(d.avg_lvt)}</td>
                    <td className={d.avg_net_change >= 0 ? 'positive' : 'negative'}>
                      {d.avg_net_change > 0 ? '+' : ''}{fmt(d.avg_net_change)}
                    </td>
                    <td className={d.avg_income_change_pct >= 0 ? 'positive' : 'negative'}>
                      {d.avg_income_change_pct > 0 ? '+' : ''}{fmtPct(d.avg_income_change_pct)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
      <p className="subsection-prose finding">Figure 3 shows that at the budget-neutral rate, lower-income deciles gain on average whilst higher-income deciles lose. The bottom three deciles see average gains of over £600 per year, whilst the top decile sees an average loss of over £1,600.</p>

      {/* --- Subsection: Winners and losers --- */}
      <SubsectionTitle>Winners and losers</SubsectionTitle>
      <p className="subsection-prose">Within each income decile, households are affected differently depending on their land holdings and current council tax bill. Figure 4 shows the share of households that are better off, worse off, or unaffected by the reform within each decile.</p>
      <p className="fig-caption">Figure 4. <span>Winners and losers by income decile (2026-27)</span></p>
      <div className="chart-row single">
        <div className="chart-card wide">
          <RateSelector value={impactRate} onChange={setImpactRate} rates={rates} defaultRate={defaultRate} />
          <ResponsiveContainer width="100%" height={380} style={{ maxWidth: 640, margin: '0 auto' }}>
            <BarChart data={[
              { decile: 'All',
                pct_winners: impactData.reduce((s, d) => s + d.pct_winners, 0) / impactData.length,
                pct_unchanged: impactData.reduce((s, d) => s + d.pct_unchanged, 0) / impactData.length,
                pct_losers: impactData.reduce((s, d) => s + d.pct_losers, 0) / impactData.length },
              { decile: ' ', pct_winners: 100, pct_unchanged: 0, pct_losers: 0, _spacer: true },
              ...[...impactData].reverse(),
            ]} stackOffset="expand" layout="vertical" barCategoryGap="15%">
              <XAxis type="number" tick={AXIS_STYLE} tickFormatter={(v) => `${Math.round(v * 100)}%`} />
              <YAxis type="category" dataKey="decile" tick={AXIS_STYLE} width={30} />
              <Tooltip content={<CustomTooltip formatter={(v) => fmtPct(v)} />} />
              <Bar dataKey="pct_winners" name="Better off" fill={C.teal700} stackId="a">
                {[
                  { decile: 'All' }, { decile: ' ', _spacer: true },
                  ...[...impactData].reverse()
                ].map((d, i) => (
                  <Cell key={i} fill={d._spacer ? 'transparent' : C.teal700} />
                ))}
              </Bar>
              <Bar dataKey="pct_unchanged" name="No change" fill={C.gray200} stackId="a">
                {[
                  { decile: 'All' }, { decile: ' ', _spacer: true },
                  ...[...impactData].reverse()
                ].map((d, i) => (
                  <Cell key={i} fill={d._spacer ? 'transparent' : C.gray200} />
                ))}
              </Bar>
              <Bar dataKey="pct_losers" name="Worse off" fill={C.gray400} stackId="a">
                {[
                  { decile: 'All' }, { decile: ' ', _spacer: true },
                  ...[...impactData].reverse()
                ].map((d, i) => (
                  <Cell key={i} fill={d._spacer ? 'transparent' : C.gray400} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <p className="subsection-prose finding">Figure 4 shows that at the budget-neutral rate, a majority of households in every decile are better off. In the bottom three deciles, around 78-80% of households gain. In the top decile, 40% gain whilst 60% lose.</p>

      {/* --- Subsection: Poverty --- */}
      <SubsectionTitle>Poverty</SubsectionTitle>
      <p className="subsection-prose">Relative poverty is measured as the share of households with equivalised income below 60% of the national median. BHC measures income before housing costs (rent or mortgage payments); AHC subtracts them. Table 3 reports the change in poverty rates under each LVT scenario, with the budget-neutral rate ({data.council_tax_replacement.required_lvt_rate_pct}%) highlighted.</p>
      <div className="chart-row single">
        <div className="chart-card" style={{ textAlign: 'center' }}>
          <p className="fig-caption">Table 3. <span>Change in relative poverty rate (2026-27)</span></p>
          <RateSelectorWithAll value={povertyRate} onChange={setPovertyRate} rates={rates} defaultRate={defaultRate} />
          <table className="impact-table">
            <thead>
              <tr>
                <th>LVT rate</th>
                <th>BHC</th>
                <th>AHC</th>
              </tr>
            </thead>
            <tbody>
              {(povertyRate === 'all' ? rates : [povertyRate]).map(r => {
                const s = pg.scenarios[r];
                return (
                  <tr key={r} className={r === defaultRate ? 'model-row' : ''}>
                    <td>{r}</td>
                    <td className={s.poverty_bhc_change <= 0 ? 'positive' : 'negative'}>{s.poverty_bhc_change > 0 ? '+' : ''}{s.poverty_bhc_change.toFixed(2)}pp</td>
                    <td className={s.poverty_ahc_change <= 0 ? 'positive' : 'negative'}>{s.poverty_ahc_change > 0 ? '+' : ''}{s.poverty_ahc_change.toFixed(2)}pp</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
      <p className="subsection-prose finding">At the budget-neutral rate, BHC poverty falls by 0.08 percentage points and AHC poverty falls by 1.69 percentage points. The larger AHC reduction reflects that lower-income households tend to pay more council tax relative to their after-housing-costs income.</p>
      {/* --- Subsection: Inequality --- */}
      <SubsectionTitle>Inequality</SubsectionTitle>
      <p className="subsection-prose">The Gini coefficient measures income inequality on a 0 to 1 scale, where lower values indicate a more equal distribution. Table 4 reports the percentage change in the Gini coefficient under each LVT scenario, with the budget-neutral rate ({data.council_tax_replacement.required_lvt_rate_pct}%) highlighted.</p>
      <div className="chart-row single">
        <div className="chart-card" style={{ textAlign: 'center' }}>
          <p className="fig-caption">Table 4. <span>Change in Gini coefficient (2026-27)</span></p>
          <RateSelectorWithAll value={giniRate} onChange={setGiniRate} rates={rates} defaultRate={defaultRate} />
          <table className="impact-table">
            <thead>
              <tr>
                <th>LVT rate</th>
                <th>Change</th>
              </tr>
            </thead>
            <tbody>
              {(giniRate === 'all' ? rates : [giniRate]).map(r => {
                const s = pg.scenarios[r];
                return (
                  <tr key={r} className={r === defaultRate ? 'model-row' : ''}>
                    <td>{r}</td>
                    <td className={s.gini_change_pct <= 0 ? 'positive' : 'negative'}>
                      {s.gini_change_pct > 0 ? '+' : ''}{fmtPct(s.gini_change_pct)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
      <p className="subsection-prose finding">At the budget-neutral rate, the Gini coefficient falls by 0.9%, indicating a small reduction in income inequality. Higher LVT rates produce larger reductions as the tax burden shifts further towards land-rich households.</p>
    </section>
  );
}


function App() {
  return (
    <div className="app">
      <header className="header">
        <h1>UK land value tax analysis</h1>
        <p className="header-sub">PolicyEngine models land value taxation and estimates what the impact would be if we replace council tax with a land value tax.</p>
      </header>

      <main className="main">
        <BaselineSection />
        <ReformSection />
        <section id="methodology" className="dashboard-section methodology-section">
          <details className="methodology-note" open={false}>
            <summary><h2 style={{ display: 'inline', fontSize: '22px' }}>Methodology note</h2></summary>
            <div className="methodology-content">
              <p>Land values are estimated in two steps. First, household-level wealth variables are imputed using quantile random forest models trained on the <a href="https://www.ons.gov.uk/peoplepopulationandcommunity/personalandhouseholdfinances/debt/methodologies/wealthandassetssurveyqmi" target="_blank" rel="noopener noreferrer">Wealth and Assets Survey</a> (Round 7) and applied to the <a href="https://github.com/PolicyEngine/policyengine-uk-data" target="_blank" rel="noopener noreferrer">Enhanced FRS</a> 2023-24 microdata. Second, each household's land value is computed by multiplying its property wealth and corporate wealth by national intensity ratios derived from the <a href="https://www.ons.gov.uk/economy/nationalaccounts/uksectoraccounts/bulletins/nationalbalancesheet/2025" target="_blank" rel="noopener noreferrer">ONS</a> National Balance Sheet, then adding any directly held land. These ratios are uniform across regions, so regional variation in land values reflects differences in property and corporate wealth rather than local land prices.</p>
              <p>All values are uprated from the survey year to 2026-27 using <a href="https://obr.uk/efo/economic-and-fiscal-outlook-march-2025/" target="_blank" rel="noopener noreferrer">OBR</a> per capita nominal GDP growth projections. Poverty is measured as the share of households with equivalised income below 60% of the national median, using the modified OECD equivalence scale. The Gini coefficient is weighted by household weight. Council tax revenue and LVT liability are computed directly by PolicyEngine UK's tax-benefit <a href="https://github.com/PolicyEngine/policyengine-uk" target="_blank" rel="noopener noreferrer">model</a>.</p>
            </div>
          </details>
        </section>
      </main>

    </div>
  );
}

export default App;
