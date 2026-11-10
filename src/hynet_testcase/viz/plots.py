# SPDX-License-Identifier: MIT
"""Charts for the presentation notebook.

Requires the `notebooks` dependency group (matplotlib).
"""

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from hynet_testcase.viz.diagrams import ZONE_COLORS

# Generator types in merit order, from the cheapest.
TYPE_COLORS = {
    "SOLAR": "#f6c141", "WIND": "#7fb8da", "HYDRO": "#2b83ba", "NUCLEAR": "#b15928",
    "COAL": "#595959", "GAS": "#e7864f",
}
SCENARIO_COLORS = {"S1": "#4d4d4d", "S2": "#1a9850", "S3": "#d73027"}


def plot_dispatch(generation: pd.DataFrame, generators: pd.DataFrame) -> Figure:
    """Stacked generation per scenario, by generator type.

    Args:
        generation: `generation.csv` of the test case.
        generators: `generators.csv` of the test case.
    """
    types = generators.set_index("generator_id")["type"]
    table = (generation.assign(type=generation["generator_id"].map(types))
             .pivot_table(index="scenario_id", columns="type", values="p_mw", aggfunc="sum")
             .reindex(columns=[t for t in TYPE_COLORS if t in set(types)]))
    fig, ax = plt.subplots(figsize=(8, 4.5))
    table.plot.bar(stacked=True, ax=ax, color=[TYPE_COLORS[t] for t in table.columns], rot=0)
    ax.set_xlabel("")
    ax.set_ylabel("Generation (MW)")
    ax.set_title("Scheduled generation by type")
    ax.legend(title="Type", bbox_to_anchor=(1.01, 1), loc="upper left")
    fig.tight_layout()
    return fig


def plot_zone_balance(zone_balance: pd.DataFrame) -> Figure:
    """Scheduled generation minus load per zone and scenario.

    Args:
        zone_balance: `zone_balance.csv` of the test case.
    """
    table = zone_balance.pivot_table(index="zone_id", columns="scenario_id", values="balance_mw")
    fig, ax = plt.subplots(figsize=(8, 4))
    table.plot.bar(ax=ax, color=[SCENARIO_COLORS[s] for s in table.columns], rot=0)
    _centre_y_axis(ax, 0.0)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("")
    ax.set_ylabel("Balance (MW, > 0 exporting)")
    ax.set_title("Scheduled zone balance")
    ax.legend(title="Scenario")
    fig.tight_layout()
    return fig


def _centre_y_axis(ax: Axes, centre: float) -> None:
    """Widens the y limits of `ax` to be symmetric about `centre`.

    Deviations above and below the reference (exports and imports, over- and
    undervoltages) then compare at a glance.
    """
    bottom, top = ax.get_ylim()
    half = max(centre - bottom, top - centre)
    ax.set_ylim(centre - half, centre + half)


def _add_y_ticks(ax: Axes, values: tuple[float, ...]) -> None:
    """Adds `values` to the automatic y ticks of `ax`, keeping its limits.

    An automatic tick closer than 3/4 of a tick step to an added value is dropped, so
    labels do not crowd; the margin over half a step absorbs float rounding.
    """
    bottom, top = ax.get_ylim()
    automatic = ax.get_yticks()
    spacing = 0.75 * (automatic[1] - automatic[0])
    ticks = [tick for tick in automatic if bottom <= tick <= top
             and all(abs(tick - value) >= spacing for value in values)]
    ax.set_yticks(sorted([*ticks, *values]))
    ax.set_ylim(bottom, top)


def plot_voltage_profiles(voltages: dict[str, pd.DataFrame], bus_zones: pd.DataFrame,
                          band: tuple[float, float] = (0.95, 1.05)) -> Figure:
    """Bus voltages (p.u.) per scenario, grouped by zone.

    Args:
        voltages: Per scenario, the result of `bus_voltages()`.
        bus_zones: `bus_zones.csv` of the test case.
        band: Voltage band drawn for reference (p.u.).
    """
    zones = bus_zones.set_index("bus_id")["zone_id"]
    order = sorted(zones.index, key=lambda bus: (zones[bus], int(bus[1:])))
    fig, ax = plt.subplots(figsize=(12, 4.5))
    for scenario, frame in voltages.items():
        v_pu = frame["v_pu"].reindex(order)
        ax.plot(range(len(order)), v_pu.to_numpy(), marker="o", markersize=3, linewidth=1,
                color=SCENARIO_COLORS.get(scenario, "grey"), label=scenario)
    for limit in band:
        ax.axhline(limit, color="grey", linestyle="--", linewidth=0.8)
    _centre_y_axis(ax, sum(band) / 2)
    _add_y_ticks(ax, band)
    start = 0
    for zone in sorted(set(zones)):
        count = int((zones == zone).sum())
        ax.axvspan(start - 0.5, start + count - 0.5, color=ZONE_COLORS[zone], alpha=0.08)
        ax.text(start + count / 2 - 0.5, 1.0, zone, transform=ax.get_xaxis_transform(),
                ha="center", va="bottom", color=ZONE_COLORS[zone], fontweight="bold")
        start += count
    ax.set_xticks(range(len(order)), order, rotation=90, fontsize=7)
    ax.set_ylabel("Voltage (p.u.)")
    ax.set_title("Bus voltages", pad=18)
    ax.legend(title="Scenario", bbox_to_anchor=(1.01, 1), loc="upper left")
    fig.tight_layout()
    return fig


def plot_loadings(loadings: dict[str, dict[str, float]], top: int = 15) -> Figure:
    """Most loaded branches, in % of their permanent current limit, per scenario.

    Args:
        loadings: Per scenario, the result of `branch_loadings()`.
        top: Number of branches shown, the most loaded in any scenario.
    """
    table = pd.DataFrame(loadings)
    table = table.loc[table.max(axis=1).sort_values(ascending=False).index[:top]]
    fig, ax = plt.subplots(figsize=(12, 4.5))
    table.plot.bar(ax=ax, color=[SCENARIO_COLORS.get(s, "grey") for s in table.columns], rot=60)
    ax.axhline(100, color="black", linestyle="--", linewidth=0.8)
    ax.set_xlabel("")
    ax.set_ylabel("Loading (% of permanent limit)")
    ax.set_title(f"{top} most loaded branches")
    ax.legend(title="Scenario")
    fig.tight_layout()
    return fig
