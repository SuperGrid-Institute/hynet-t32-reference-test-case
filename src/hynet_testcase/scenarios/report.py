# SPDX-License-Identifier: MIT
"""Summary of a solved network state, logged by the build."""

import logging
from dataclasses import dataclass

import pandas as pd
from pypowsybl.network import Network

from hynet_testcase.network.loadflow import ComponentResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VoltageRange:
    """Extreme bus voltages at one nominal voltage.

    Attributes:
        nominal_kv: Nominal voltage of the buses.
        min_pu: Lowest bus voltage (p.u. of nominal).
        min_bus: Bus with the lowest voltage.
        max_pu: Highest bus voltage (p.u. of nominal).
        max_bus: Bus with the highest voltage.
    """

    nominal_kv: float
    min_pu: float
    min_bus: str
    max_pu: float
    max_bus: str


@dataclass(frozen=True)
class StateReport:
    """Summary of a solved state.

    Attributes:
        label: Name of the state (case or scenario).
        voltages: Voltage ranges, one per nominal voltage, ascending.
        hvdc_p_mw: Active power at the rectifier side of each HVDC line (MW).
        slack_mismatch_mw: Total active power left on slack buses (MW).
        loadings: Loading of each branch (% of its permanent current limit, worst
            side), in descending order.
    """

    label: str
    voltages: list[VoltageRange]
    hvdc_p_mw: dict[str, float]
    slack_mismatch_mw: float
    loadings: dict[str, float]

    @property
    def overloads(self) -> dict[str, float]:
        """Branches loaded above their permanent current limit, in %."""
        return {branch: loading for branch, loading in self.loadings.items() if loading > 100.0}

    @classmethod
    def of(cls, network: Network, label: str,
           results: list[ComponentResult]) -> StateReport:
        """Summarises the working variant of a solved `network`."""
        buses = bus_voltages(network)
        voltages = []
        for nominal_kv in sorted(buses["nominal_v"].unique()):
            v_pu = buses.loc[buses["nominal_v"] == nominal_kv, "v_pu"]
            voltages.append(VoltageRange(
                nominal_kv=float(nominal_kv), min_pu=float(v_pu.min()), min_bus=str(v_pu.idxmin()),
                max_pu=float(v_pu.max()), max_bus=str(v_pu.idxmax())))
        station_p = network.get_vsc_converter_stations()["p"].astype(float)
        lines = network.get_hvdc_lines()
        rectifiers = lines["converter_station1_id"].where(
            lines["converters_mode"] == "SIDE_1_RECTIFIER_SIDE_2_INVERTER",
            lines["converter_station2_id"])
        hvdc = {str(line_id): float(station_p.to_numpy()[station_p.index.get_loc(station)])
                for line_id, station in rectifiers.items()}
        return cls(label=label, voltages=voltages, hvdc_p_mw=hvdc,
                   slack_mismatch_mw=sum(r.slack_mismatch_mw for r in results),
                   loadings=branch_loadings(network))

    def log(self) -> None:
        """Logs the summary at INFO level."""
        for v in self.voltages:
            logger.info("%s: %g kV buses %.3f p.u. (%s) to %.3f p.u. (%s)", self.label,
                        v.nominal_kv, v.min_pu, v.min_bus, v.max_pu, v.max_bus)
        for line_id, p in self.hvdc_p_mw.items():
            logger.info("%s: HVDC %s carries %.1f MW", self.label, line_id, p)
        branch, loading = next(iter(self.loadings.items()))
        logger.info("%s: highest branch loading %.0f %% (%s)", self.label, loading, branch.strip())
        for branch, loading in self.overloads.items():
            logger.info("%s: overload %s at %.0f %%", self.label, branch.strip(), loading)


def branch_loadings(network: Network) -> dict[str, float]:
    """Loading of every limited branch of a solved network, in % of its permanent
    current limit (worst side), in descending order."""
    limits = network.get_operational_limits().reset_index()
    limits = limits[(limits["type"] == "CURRENT") & (limits["acceptable_duration"] == -1)]
    limit_by_side = limits.pivot_table(index="element_id", columns="side", values="value",
                                       aggfunc="min")
    branches = pd.concat([network.get_lines(attributes=["i1", "i2"]),
                          network.get_2_windings_transformers(attributes=["i1", "i2"])])
    branches = branches.join(limit_by_side, how="inner")
    loading = pd.concat([branches["i1"].abs() / branches["ONE"],
                         branches["i2"].abs() / branches["TWO"]], axis=1).max(axis=1) * 100.0
    loading = loading.sort_values(ascending=False, kind="stable")
    return {str(branch): float(value) for branch, value in zip(loading.index, loading.to_numpy())}


def bus_voltages(network: Network) -> pd.DataFrame:
    """Voltage of every energised bus of a solved network.

    Bus-breaker ids (e.g. `B31`) are used: they are the model's bus ids, whereas
    bus-view ids such as `VL6_0` are generated and not stable across formats.

    Returns:
        Columns `v_mag` (kV), `nominal_v` (kV), `v_pu` and `voltage_level_id`, indexed
        by bus id.
    """
    buses = network.get_bus_breaker_view_buses().join(
        network.get_voltage_levels()[["nominal_v"]], on="voltage_level_id")
    buses = buses[buses["v_mag"].notna()]
    buses["v_pu"] = buses["v_mag"] / buses["nominal_v"]
    return buses[["v_mag", "nominal_v", "v_pu", "voltage_level_id"]]
