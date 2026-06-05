"""Build the LVT distributional charts (all quintiles) in PolicyEngine style.

Reads ``data/lvt_results.json`` and writes PNG + SVG charts to
``blog/charts-quintile/`` using plotly and
``policyengine_core.charts.format_fig``, which applies the PolicyEngine style
guide (Roboto Serif, plotly_white) and stamps the PolicyEngine logo in the
bottom-right. The logo is loaded from a local copy so renders are reproducible
offline.

Run:  uv run --no-sync python blog/build_charts.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import plotly.graph_objects as go
from PIL import Image
from policyengine_core.charts import (
    BLUE,
    GRAY,
    MEDIUM_DARK_GRAY,
    format_fig,
)

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data" / "lvt_results.json"
OUT = REPO / "blog" / "charts-quintile"
OUT.mkdir(parents=True, exist_ok=True)
LOGO = Image.open(REPO / "blog" / "assets" / "policyengine-blue.png")

GAIN = BLUE                    # #2C6496 PolicyEngine blue
LOSS = GRAY                    # #808080
UNCHANGED = MEDIUM_DARK_GRAY   # #D2D2D2
QLABELS = ["1 (poorest)", "2", "3", "4", "5 (richest)"]
YEAR = "2026-27"

data = json.loads(DATA.read_text())


def budget_neutral_rate() -> str:
    target = data["council_tax_replacement"]["required_lvt_rate_pct"]
    for key in data["impact_scenarios_quintile"]:
        if abs(float(str(key).rstrip("%")) - target) < 1e-9:
            return key
    return f"{target}%"


RATE = budget_neutral_rate()


def q_rows(table):
    return sorted(table, key=lambda r: r["decile"])


def sym_bound(values, step):
    """Axis bound symmetric about 0, with ~half a tick of clearance below the
    tallest bar so its value label never collides with the axis."""
    b = max(abs(min(values)), abs(max(values)))
    bound = math.ceil(b / step) * step
    if bound - b < step * 0.4:
        bound += step
    return int(bound)


def signed(v):
    return ("+£" if v >= 0 else "−£") + f"{abs(round(v)):,}"


def style(fig, height=520, width=820):
    fig = format_fig(fig)
    # Re-place the PolicyEngine logo fully inside the figure, bottom-right.
    # format_fig pins it at x=1.1 (beyond the plot), which clips on these
    # dimensions. Right-align to the plot edge, drop it into the bottom margin.
    fig.layout.images[0].update(
        source=LOGO,  # local logo -> reproducible kaleido render
        sizing="contain",
        xref="paper",
        yref="paper",
        x=1.0,
        xanchor="right",
        y=-0.26,
        yanchor="bottom",
        sizex=0.16,
        sizey=0.13,
    )
    fig.update_layout(
        height=height,
        width=width,
        margin=dict(t=64, b=98, l=92, r=52),
        font=dict(family="Roboto Serif", size=15, color="black"),
        title=dict(font=dict(size=18), x=0.5, xanchor="center"),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    fig.update_xaxes(
        showgrid=False, linecolor="#9ca3af", ticks="outside", tickcolor="#9ca3af"
    )
    fig.update_yaxes(gridcolor="#e5e7eb", zeroline=False)
    return fig


def save(fig, name):
    fig.write_image(str(OUT / f"{name}.png"), scale=2)
    fig.write_image(str(OUT / f"{name}.svg"))


def value_bar(rows, key, *, title, xtitle, step, name, signed_labels):
    vals = [r[key] for r in rows]
    if signed_labels:
        bound = sym_bound(vals, step)
        ticks = list(range(-bound, bound + 1, step))
        ticktext = ["£0" if t == 0 else signed(t) for t in ticks]
        yrange = [-bound, bound]
        colours = [GAIN if v >= 0 else LOSS for v in vals]
        text = [signed(v) for v in vals]
    else:
        top = math.ceil(max(vals) / step) * step
        ticks = list(range(0, top + 1, step))
        ticktext = [f"£{t / 1000:.0f}k" if t else "£0" for t in ticks]
        yrange = [0, top * 1.10]
        colours = GAIN
        text = [f"£{v / 1000:.0f}k" for v in vals]
    fig = go.Figure(
        go.Bar(
            x=QLABELS,
            y=vals,
            marker_color=colours,
            text=text,
            textposition="outside",
            textfont=dict(size=14, color="black"),
            cliponaxis=False,
        )
    )
    fig.update_layout(title=title, xaxis_title=xtitle)
    fig.update_yaxes(range=yrange, tickvals=ticks, ticktext=ticktext)
    if signed_labels:
        fig.add_hline(y=0, line_color=GRAY, line_width=1)
    save(style(fig), name)


# Fig 1 — average household land value by income quintile
value_bar(
    q_rows(data["distribution_by_quintile"]),
    "avg_land_value",
    title=f"Average household land value by income quintile, {YEAR}",
    xtitle="Income quintile",
    step=100_000,
    name="fig1_land_by_income_quintile",
    signed_labels=False,
)

# Fig 4 — net income change by income quintile
value_bar(
    q_rows(data["impact_scenarios_quintile"][RATE]),
    "avg_net_change",
    title=f"Net income change by income quintile, {RATE} LVT, {YEAR}",
    xtitle="Income quintile",
    step=200,
    name="fig4_netchange_by_income_quintile",
    signed_labels=True,
)

# Fig 5 — net income change by wealth quintile
value_bar(
    q_rows(data["impact_scenarios_by_wealth_quintile"][RATE]),
    "avg_net_change",
    title=f"Net income change by net wealth quintile, {RATE} LVT, {YEAR}",
    xtitle="Net wealth quintile",
    step=1000,
    name="fig5_netchange_by_wealth_quintile",
    signed_labels=True,
)

# Fig 6 — share with higher / unchanged / lower net income by income quintile
rows = q_rows(data["impact_scenarios_quintile"][RATE])
winners = [r["pct_winners"] for r in rows]
unchanged = [r["pct_unchanged"] for r in rows]
losers = [r["pct_losers"] for r in rows]
fig = go.Figure()
fig.add_bar(
    y=QLABELS, x=winners, orientation="h", name="Higher net income",
    marker_color=GAIN, text=[f"{v:.0f}%" for v in winners],
    textposition="inside", insidetextanchor="middle",
    insidetextfont=dict(color="white", size=13),
)
fig.add_bar(
    y=QLABELS, x=unchanged, orientation="h", name="Unchanged", marker_color=UNCHANGED,
)
fig.add_bar(
    y=QLABELS, x=losers, orientation="h", name="Lower net income",
    marker_color=LOSS, text=[f"{v:.0f}%" for v in losers],
    textposition="inside", insidetextanchor="middle",
    insidetextfont=dict(color="white", size=13),
)
fig.update_layout(
    barmode="stack",
    title=f"Share with higher, lower, or unchanged net income, {RATE} LVT",
    xaxis=dict(range=[0, 100], ticksuffix="%", showgrid=False),
    yaxis=dict(title="Income quintile", autorange="reversed"),
    legend=dict(
        orientation="h",
        traceorder="normal",
        yanchor="top",
        y=-0.18,
        xanchor="center",
        x=0.5,
    ),
)
fig6 = style(fig, height=480)
fig6.update_layout(margin=dict(t=64, b=134, l=92, r=52))
save(fig6, "fig6_shares_by_income_quintile")

print(f"charts written to {OUT} (budget-neutral rate {RATE})")
