"""Interactive UK local-authority map of the LVT reform.

One self-contained script that:
  1. Runs the same PolicyEngine simulations the dashboard uses
     (baseline + abolish council tax + LVT at the budget-neutral rate).
  2. Aggregates per-household results to the 360 UK local authorities
     via policyengine-uk-data's local_authority_weights matrix.
  3. Renders a Scottish-budget-style D3 choropleth HTML with a three-way
     view toggle:
        - Average council tax bill
        - Average LVT bill
        - Average net change after reform (CT abolished + LVT applied)
     Includes search, zoom, tooltip.

Inputs (auto-downloaded from HF when missing):
  - PolicyEngine UK dataset: hf://policyengine/policyengine-uk-data-private/enhanced_frs_2023_24.h5
  - LA weight matrix:        hf://policyengine/policyengine-uk-data-private/local_authority_weights.h5
  - LA codes CSV:            hf://policyengine/policyengine-uk-data-private/local_authorities_2021.csv

Static inputs (committed in repo):
  - blog/data/uk_lad_2025_buc.geojson   (ONS LAD May 2025 boundaries)
  - data/lvt_results.json               (budget-neutral LVT rate from dashboard)

Output:
  - blog/figures/la_lvt_map.html
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

YEAR = 2026
WEIGHTS_YEAR = 2025

ROOT = Path(__file__).resolve().parents[1]
GEO_PATH = ROOT / "blog" / "data" / "uk_lad_2025_buc.geojson"
NATIONAL = ROOT / "data" / "lvt_results.json"
OUT_PATH = ROOT / "blog" / "figures" / "la_lvt_map.html"
CACHE_DIR = ROOT / "blog" / "data" / ".pe_uk_data_cache"

DATASET_URL = "hf://policyengine/policyengine-uk-data-private/enhanced_frs_2023_24.h5"
PE_UK_DATA_REPO = "policyengine/policyengine-uk-data-private"


def _hf_token() -> str | None:
    return os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_TOKEN")


def _ensure(filename: str) -> Path:
    """Download the file from HF if not already cached."""
    target = CACHE_DIR / filename
    if target.exists():
        return target
    from huggingface_hub import hf_hub_download

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  Downloading {filename} from HF...")
    hf_hub_download(
        PE_UK_DATA_REPO,
        filename,
        repo_type="model",
        token=_hf_token(),
        local_dir=str(CACHE_DIR),
    )
    return target


def compute_la_aggregates(rate: float) -> list[dict]:
    """Run baseline + reform simulations and aggregate to LA via the weight matrix.

    Returns list of dicts keyed by LA: {code, name, households, lvt, ct, net}.
    """
    from policyengine_uk import Microsimulation, Scenario

    print("Running baseline simulation...")
    baseline = Microsimulation(dataset=DATASET_URL)
    baseline_ct = np.asarray(
        baseline.calculate("council_tax_less_benefit", YEAR).values, dtype=np.float64
    )
    baseline_net_income = np.asarray(
        baseline.calculate("household_net_income", YEAR).values, dtype=np.float64
    )

    print(f"Running reform simulation (abolish CT + LVT @ {rate*100:.2f}%)...")
    reform = Scenario(parameter_changes={
        "gov.contrib.abolish_council_tax": True,
        "gov.contrib.ubi_center.land_value_tax.rate": rate,
    })
    reformed = Microsimulation(scenario=reform, dataset=DATASET_URL)
    reformed_lvt = np.asarray(
        reformed.calculate("LVT", YEAR).values, dtype=np.float64
    )
    reformed_net_income = np.asarray(
        reformed.calculate("household_net_income", YEAR).values, dtype=np.float64
    )
    income_change = reformed_net_income - baseline_net_income

    print("Aggregating to LAs via weight matrix...")
    weights_path = _ensure("local_authority_weights.h5")
    la_csv_path = _ensure("local_authorities_2021.csv")
    la_df = pd.read_csv(la_csv_path)
    with h5py.File(weights_path, "r") as f:
        weights = np.asarray(f[str(WEIGHTS_YEAR)], dtype=np.float64)

    if weights.shape[1] != baseline_ct.shape[0]:
        raise RuntimeError(
            f"Shape mismatch: weights {weights.shape}, households {baseline_ct.shape[0]}"
        )

    households_la = weights.sum(axis=1)
    safe = np.where(households_la > 0, households_la, np.nan)
    avg_ct_la = (weights @ baseline_ct) / safe
    avg_lvt_la = (weights @ reformed_lvt) / safe
    avg_net_la = (weights @ income_change) / safe

    return [
        {
            "code": row["code"],
            "name": row["name"],
            "households": round(float(households_la[i])),
            "ct": round(float(avg_ct_la[i])),
            "lvt": round(float(avg_lvt_la[i])),
            "net": round(float(avg_net_la[i])),
        }
        for i, row in la_df.iterrows()
    ]


def build_html(records: list[dict], rate_pct: float, geojson: dict) -> str:
    impact = {r["code"]: r for r in records}
    all_names = sorted({r["name"] for r in records})
    return (
        HTML_TEMPLATE
        .replace("__RATE_PCT__", f"{rate_pct:.2f}")
        .replace("__IMPACT_JSON__", json.dumps(impact))
        .replace("__GEO_JSON__", json.dumps(geojson))
        .replace("__NAMES_JSON__", json.dumps(all_names))
    )


def main() -> None:
    rate_pct = float(json.loads(NATIONAL.read_text())["council_tax_replacement"]["required_lvt_rate_pct"])
    rate = rate_pct / 100
    print(f"Budget-neutral LVT rate (from dashboard): {rate_pct}%")

    records = compute_la_aggregates(rate)
    geojson = json.loads(GEO_PATH.read_text())

    html = build_html(records, rate_pct, geojson)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html)
    kb = OUT_PATH.stat().st_size / 1024
    print(f"Wrote {OUT_PATH} ({kb:.0f} KB)")

    cts = sorted(r["ct"] for r in records)
    lvts = sorted(r["lvt"] for r in records)
    nets = sorted(r["net"] for r in records)
    print(f"  LAs: {len(records)}")
    print(f"  Avg CT  median £{cts[len(cts)//2]:,}  range £{cts[0]:,}-£{cts[-1]:,}")
    print(f"  Avg LVT median £{lvts[len(lvts)//2]:,}  range £{lvts[0]:,}-£{lvts[-1]:,}")
    print(f"  Net     median £{nets[len(nets)//2]:,}  range £{nets[0]:,} to £{nets[-1]:,}  (positive = better off)")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Council tax to LVT reform by UK local authority</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Roboto', sans-serif; background: white; }
  .map-wrapper { display: flex; flex-direction: column; gap: 8px; padding: 8px; max-width: 900px; margin: 0 auto; }
  .map-header { padding-bottom: 6px; border-bottom: 1px solid #e5e7eb; }
  .map-header h2 { margin: 0 0 2px 0; color: #374151; font-size: 1rem; font-weight: 600; }
  .map-header p { margin: 0; color: #6b7280; font-size: 0.8rem; }
  .view-toggle { display: inline-flex; border: 1px solid #d1d5db; border-radius: 8px; padding: 3px; background: white; }
  .view-toggle button { padding: 6px 12px; font-size: 0.8rem; font-weight: 500; border: none; background: transparent; cursor: pointer; border-radius: 6px; color: #4b5563; font-family: 'Roboto', sans-serif; }
  .view-toggle button.active { background: #1b1d24; color: white; }
  .map-top-bar { display: flex; gap: 16px; align-items: center; flex-wrap: wrap; }
  .map-search-section { flex: 1; min-width: 200px; max-width: 300px; }
  .map-search-section h3 { font-size: 0.72rem; font-weight: 600; color: #374151; margin: 0 0 4px 0; text-transform: uppercase; letter-spacing: 0.05em; }
  .search-container { position: relative; }
  .la-search { width: 100%; padding: 6px 10px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.8rem; font-family: 'Roboto', sans-serif; }
  .la-search:focus { outline: none; border-color: #2c6e49; box-shadow: 0 0 0 3px rgba(44, 110, 73, 0.12); }
  .search-results { position: absolute; z-index: 100; width: 100%; margin-top: 4px; background: white; border: 1px solid #d1d5db; border-radius: 6px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); max-height: 240px; overflow-y: auto; display: none; }
  .search-result-item { width: 100%; text-align: left; padding: 8px 12px; background: none; border: none; border-bottom: 1px solid #f3f4f6; cursor: pointer; font-family: 'Roboto', sans-serif; }
  .search-result-item:hover { background: #f9fafb; }
  .result-name { font-weight: 500; font-size: 0.85rem; color: #374151; }
  .result-value { font-size: 0.72rem; color: #6b7280; margin-top: 2px; }
  .map-legend { display: flex; flex-direction: column; gap: 4px; margin-left: auto; min-width: 220px; }
  .legend-title { font-size: 0.7rem; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
  .legend-gradient { width: 100%; height: 12px; border-radius: 3px; }
  .legend-labels { display: flex; justify-content: space-between; font-size: 0.72rem; color: #6b7280; }
  .map-canvas { position: relative; width: 100%; display: flex; justify-content: center; }
  .map-canvas svg { background: #fbfaf6; border-radius: 6px; width: 100%; height: auto; max-width: 700px; }
  .la-path { cursor: pointer; transition: opacity 0.1s ease; }
  .la-path:hover { opacity: 0.85; }
  .map-controls { position: absolute; top: 12px; right: 12px; display: flex; gap: 4px; background: white; padding: 4px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1); }
  .zoom-btn { width: 28px; height: 28px; background: transparent; border: none; border-radius: 4px; display: flex; align-items: center; justify-content: center; cursor: pointer; color: #6b7280; font-size: 18px; font-weight: bold; }
  .zoom-btn:hover { background: #f3f4f6; color: #2c6e49; }
  .tooltip { position: absolute; background: white; border: 2px solid #2c6e49; border-radius: 8px; padding: 12px 16px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15); pointer-events: none; min-width: 240px; transform: translate(-50%, -100%); margin-top: -10px; z-index: 100; display: none; }
  .tooltip h4 { font-size: 0.95rem; font-weight: 600; color: #374151; margin: 0 0 8px 0; }
  .tooltip-value { font-size: 1.4rem; font-weight: 700; color: #2c6e49; margin: 4px 0; }
  .tooltip-value.negative { color: #b3261e; }
  .tooltip-row { display: flex; justify-content: space-between; font-size: 0.78rem; color: #6b7280; margin: 4px 0; gap: 12px; }
  .source { font-size: 0.72rem; color: #9ca3af; margin-top: 12px; text-align: center; }
  .source a { color: #2c6e49; text-decoration: none; }
</style>
</head>
<body>
<div class="map-wrapper">
  <div class="map-header">
    <h2 id="title"></h2>
    <p id="subtitle"></p>
  </div>

  <div class="view-toggle" role="tablist" aria-label="Map view">
    <button class="active" data-view="ct">Avg council tax</button>
    <button data-view="lvt">Avg LVT</button>
    <button data-view="net">Avg net change</button>
  </div>

  <div class="map-top-bar">
    <div class="map-search-section">
      <h3>Search local authority</h3>
      <div class="search-container">
        <input type="text" class="la-search" placeholder="Type to search..." id="search-input">
        <div class="search-results" id="search-results"></div>
      </div>
    </div>
    <div class="map-legend">
      <div class="legend-title" id="legend-title"></div>
      <div class="legend-gradient" id="legend-gradient"></div>
      <div class="legend-labels">
        <span id="min-label"></span>
        <span id="mid-label"></span>
        <span id="max-label"></span>
      </div>
    </div>
  </div>

  <div class="map-canvas">
    <svg id="map" viewBox="0 0 600 760" preserveAspectRatio="xMidYMid meet"></svg>
    <div class="map-controls">
      <button class="zoom-btn" id="zoom-in" title="Zoom in">+</button>
      <button class="zoom-btn" id="zoom-out" title="Zoom out">-</button>
      <button class="zoom-btn" id="zoom-reset" title="Reset">↺</button>
    </div>
    <div class="tooltip" id="tooltip"></div>
  </div>

  <div class="source">
    All three views come from the same PolicyEngine UK simulation that powers the dashboard (baseline + abolish council tax + LVT at __RATE_PCT__%). Per-household results are aggregated to LA via policyengine-uk-data's local_authority_weights matrix. Net change uses household_net_income, so it includes council-tax-reduction loss and other benefit interactions just like the dashboard's distributional impact chart. Boundaries: ONS LAD May 2025 (UK BUC). |
    <a href="https://policyengine.org" target="_blank">PolicyEngine</a>
  </div>
</div>

<script>
const impactData = __IMPACT_JSON__;
const geoData = __GEO_JSON__;
const allNames = __NAMES_JSON__;
const ratePct = __RATE_PCT__;

const width = 600, height = 760;
const svg = d3.select('#map');
const g = svg.append('g');
const tooltip = document.getElementById('tooltip');
const titleEl = document.getElementById('title');
const subtitleEl = document.getElementById('subtitle');
const legendTitleEl = document.getElementById('legend-title');
const legendGradient = document.getElementById('legend-gradient');
const minLabel = document.getElementById('min-label');
const midLabel = document.getElementById('mid-label');
const maxLabel = document.getElementById('max-label');

// Project lon/lat to SVG via plate-carrée scaled by cos(mean lat).
let lonMin = Infinity, lonMax = -Infinity, latMin = Infinity, latMax = -Infinity;
geoData.features.forEach(f => {
  const traverse = c => { if (typeof c[0] === 'number') {
    lonMin = Math.min(lonMin, c[0]); lonMax = Math.max(lonMax, c[0]);
    latMin = Math.min(latMin, c[1]); latMax = Math.max(latMax, c[1]);
  } else c.forEach(traverse); };
  traverse(f.geometry.coordinates);
});
const meanLat = (latMin + latMax) / 2;
const xRatio = Math.cos(meanLat * Math.PI / 180);
const padding = 16;
const dataW = (lonMax - lonMin) * xRatio;
const dataH = (latMax - latMin);
const scale = Math.min((width - 2 * padding) / dataW, (height - 2 * padding) / dataH);
const offX = (width - dataW * scale) / 2;
const offY = (height - dataH * scale) / 2;
const projection = d3.geoTransform({ point: function(lon, lat) {
  this.stream.point(offX + (lon - lonMin) * xRatio * scale, offY + (latMax - lat) * scale);
}});
const pathGenerator = d3.geoPath().projection(projection);

const zoom = d3.zoom().scaleExtent([1, 12]).on('zoom', e => g.attr('transform', e.transform));
svg.call(zoom);
document.getElementById('zoom-in').onclick = () => svg.transition().call(zoom.scaleBy, 1.5);
document.getElementById('zoom-out').onclick = () => svg.transition().call(zoom.scaleBy, 0.67);
document.getElementById('zoom-reset').onclick = () => svg.transition().call(zoom.transform, d3.zoomIdentity);

// Sequential green ramp for CT/LVT, diverging red↔green for net change.
const SEQ = ['#f1ede3', '#cfe0cb', '#9cc6a7', '#5ba88f', '#2c6e49'];
const DIV_NEG = ['#7a1f1a', '#b3261e', '#e89c95', '#f4ede4'];
const DIV_POS = ['#f4ede4', '#9cc6a7', '#5ba88f', '#2c6e49'];
const NA = '#e8e6df';

const fmtSigned = v => (v == null || isNaN(v)) ? 'n/a' : (v > 0 ? '+' : (v < 0 ? '−' : '')) + '£' + Math.round(Math.abs(v)).toLocaleString();

const VIEW = {
  ct: {
    title: 'Average council tax bill by UK local authority',
    subtitle: `Average household council tax less benefit, 2026-27. NI households pay domestic rates rather than council tax (£0).`,
    legendTitle: 'Avg council tax (£/yr)',
    accessor: d => (d && d.ct > 0) ? d.ct : null,
    diverging: false,
  },
  lvt: {
    title: 'Average LVT bill by UK local authority',
    subtitle: `Average household LVT bill at the budget-neutral rate of ${ratePct}%, 2026-27.`,
    legendTitle: 'Avg LVT (£/yr)',
    accessor: d => (d && d.lvt > 0) ? d.lvt : null,
    diverging: false,
  },
  net: {
    title: 'Net change after the reform',
    subtitle: `Average household income change from abolishing council tax and applying ${ratePct}% LVT. Same simulation the dashboard uses for its distributional impact chart. Green = better off, red = worse off.`,
    legendTitle: 'Net change (£/household/yr)',
    accessor: d => (d && d.net != null) ? d.net : null,
    diverging: true,
  },
};

function buildSeq(values) {
  const positives = values.filter(v => v != null && v > 0);
  if (!positives.length) return null;
  const minV = Math.max(1, d3.min(positives));
  const maxV = d3.max(positives);
  const log = d3.scaleLog().domain([minV, maxV]).range([0, 1]).clamp(true);
  const stops = SEQ.map((_, i) => i / (SEQ.length - 1));
  return {
    fill: v => {
      if (v == null || v <= 0) return NA;
      const t = log(v);
      for (let i = 1; i < stops.length; i++) {
        if (t <= stops[i]) {
          const lt = (t - stops[i-1]) / (stops[i] - stops[i-1]);
          return d3.interpolate(SEQ[i-1], SEQ[i])(lt);
        }
      }
      return SEQ[SEQ.length - 1];
    },
    minV, maxV, midV: Math.round(Math.exp((Math.log(minV) + Math.log(maxV)) / 2)),
    gradient: `linear-gradient(to right, ${SEQ.join(', ')})`,
  };
}

function buildDiv(values) {
  const valid = values.filter(v => v != null && !isNaN(v));
  if (!valid.length) return null;
  const absMax = Math.max(Math.abs(d3.min(valid)), Math.abs(d3.max(valid)));
  const negStops = DIV_NEG.map((_, i) => i / (DIV_NEG.length - 1));
  const posStops = DIV_POS.map((_, i) => i / (DIV_POS.length - 1));
  return {
    fill: v => {
      if (v == null || isNaN(v)) return NA;
      if (Math.abs(v) < 1) return DIV_POS[0];
      if (v < 0) {
        const u = 1 - Math.min(1, Math.abs(v) / absMax);
        for (let i = 1; i < negStops.length; i++) if (u <= negStops[i]) {
          const lt = (u - negStops[i-1]) / (negStops[i] - negStops[i-1]);
          return d3.interpolate(DIV_NEG[i-1], DIV_NEG[i])(lt);
        }
        return DIV_NEG[DIV_NEG.length - 1];
      } else {
        const t = Math.min(1, v / absMax);
        for (let i = 1; i < posStops.length; i++) if (t <= posStops[i]) {
          const lt = (t - posStops[i-1]) / (posStops[i] - posStops[i-1]);
          return d3.interpolate(DIV_POS[i-1], DIV_POS[i])(lt);
        }
        return DIV_POS[DIV_POS.length - 1];
      }
    },
    minV: -absMax, midV: 0, maxV: absMax,
    gradient: `linear-gradient(to right, ${DIV_NEG.slice().reverse().join(', ')}, ${DIV_POS.slice(1).join(', ')})`,
  };
}

let activeView = 'ct';

function render(view) {
  activeView = view;
  const cfg = VIEW[view];
  titleEl.textContent = cfg.title;
  subtitleEl.textContent = cfg.subtitle;
  legendTitleEl.textContent = cfg.legendTitle;

  const values = Object.values(impactData).map(cfg.accessor);
  const ramp = cfg.diverging ? buildDiv(values) : buildSeq(values);
  if (ramp) {
    legendGradient.style.background = ramp.gradient;
    if (cfg.diverging) {
      minLabel.textContent = fmtSigned(ramp.minV);
      midLabel.textContent = '£0';
      maxLabel.textContent = fmtSigned(ramp.maxV);
    } else {
      minLabel.textContent = '£' + Math.round(ramp.minV).toLocaleString();
      midLabel.textContent = '£' + Math.round(ramp.midV).toLocaleString();
      maxLabel.textContent = '£' + Math.round(ramp.maxV).toLocaleString();
    }
  }
  paths.attr('fill', d => {
    const data = impactData[d.properties.LAD25CD];
    const v = cfg.accessor(data);
    return ramp ? ramp.fill(v) : NA;
  });
}

const paths = g.selectAll('path')
  .data(geoData.features)
  .join('path')
  .attr('class', 'la-path')
  .attr('d', pathGenerator)
  .attr('stroke', 'white')
  .attr('stroke-width', 0.4)
  .attr('opacity', 0.95)
  .on('mouseenter', function(e, d) { showTooltip(d, e); d3.select(this).attr('opacity', 1).attr('stroke-width', 1.5); })
  .on('mousemove', function(e, d) { showTooltip(d, e); })
  .on('mouseleave', function() { d3.select(this).attr('opacity', 0.95).attr('stroke-width', 0.4); tooltip.style.display = 'none'; });

function showTooltip(feature, event) {
  const d = impactData[feature.properties.LAD25CD];
  const name = feature.properties.LAD25NM;
  if (!d) {
    tooltip.innerHTML = `<h4>${name}</h4><div class="tooltip-row"><span>No estimate</span></div>`;
  } else {
    let headline = '', cls = '';
    if (activeView === 'ct') headline = d.ct > 0 ? `£${d.ct.toLocaleString()}` : '£0';
    else if (activeView === 'lvt') headline = `£${d.lvt.toLocaleString()}`;
    else { headline = fmtSigned(d.net); cls = d.net < 0 ? 'negative' : ''; }
    tooltip.innerHTML = `
      <h4>${name}</h4>
      <div class="tooltip-value ${cls}">${headline}</div>
      <div class="tooltip-row"><span>Avg council tax</span><span>£${d.ct.toLocaleString()}</span></div>
      <div class="tooltip-row"><span>Avg LVT</span><span>£${d.lvt.toLocaleString()}</span></div>
      <div class="tooltip-row"><span>Net income change</span><span>${fmtSigned(d.net)}</span></div>
      <div class="tooltip-row"><span>Households</span><span>${d.households.toLocaleString()}</span></div>
    `;
  }
  tooltip.style.display = 'block';
  const rect = document.querySelector('.map-canvas').getBoundingClientRect();
  tooltip.style.left = (event.clientX - rect.left) + 'px';
  tooltip.style.top = (event.clientY - rect.top) + 'px';
}

document.querySelectorAll('.view-toggle button').forEach(btn => {
  btn.onclick = () => {
    document.querySelectorAll('.view-toggle button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    render(btn.dataset.view);
  };
});

const searchInput = document.getElementById('search-input');
const searchResults = document.getElementById('search-results');
searchInput.addEventListener('input', function() {
  const q = this.value.toLowerCase();
  if (q.length < 2) { searchResults.style.display = 'none'; return; }
  const matches = allNames.filter(n => n.toLowerCase().includes(q)).slice(0, 12);
  if (!matches.length) { searchResults.style.display = 'none'; return; }
  searchResults.innerHTML = matches.map(n => {
    const code = Object.keys(impactData).find(c => impactData[c].name === n);
    const d = impactData[code] || { ct: 0, lvt: 0, net: 0 };
    return `<button class="search-result-item" data-code="${code}">
      <div class="result-name">${n}</div>
      <div class="result-value">CT £${d.ct.toLocaleString()} · LVT £${d.lvt.toLocaleString()} · Net ${fmtSigned(d.net)}</div>
    </button>`;
  }).join('');
  searchResults.style.display = 'block';
  searchResults.querySelectorAll('.search-result-item').forEach(item => {
    item.onclick = function() {
      const code = this.dataset.code;
      const feature = geoData.features.find(f => f.properties.LAD25CD === code);
      if (!feature) return;
      searchInput.value = feature.properties.LAD25NM;
      searchResults.style.display = 'none';
      paths.attr('opacity', 0.95).attr('stroke-width', 0.4);
      paths.filter(d => d.properties.LAD25CD === code).attr('opacity', 1).attr('stroke-width', 2);
      const b = pathGenerator.bounds(feature);
      const dx = b[1][0] - b[0][0], dy = b[1][1] - b[0][1];
      const cx = (b[0][0] + b[1][0]) / 2, cy = (b[0][1] + b[1][1]) / 2;
      const k = Math.max(1, Math.min(10, 0.9 / Math.max(dx / width, dy / height)));
      svg.transition().duration(750).call(zoom.transform,
        d3.zoomIdentity.translate(width / 2, height / 2).scale(k).translate(-cx, -cy));
    };
  });
});
document.addEventListener('click', e => {
  if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) searchResults.style.display = 'none';
});

render('ct');
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
