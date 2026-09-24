# SPDX-License-Identifier: MIT
"""Contingency list: single-element outages analysed on every scenario."""

import logging
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Self

import pandas as pd
from pypowsybl.network import Network

from hynet_testcase.errors import IdResolutionError, InputError, LoadFlowError, TestCaseError
from hynet_testcase.io.readers import read_input_csv
from hynet_testcase.network.loadflow import run_ac
from hynet_testcase.scenarios.report import StateReport, branch_loadings, bus_voltages

logger = logging.getLogger(__name__)

_COLUMNS = ["contingency_id", "element_type", "element_id"]


class ContingencyElementType(StrEnum):
    """Element types a contingency may trip."""

    LINE = "line"
    TWO_WINDINGS_TRANSFORMER = "two_windings_transformer"
    GENERATOR = "generator"


@dataclass(frozen=True)
class Contingency:
    """Outage of one element.

    Attributes:
        contingency_id: Contingency id.
        element_type: Type of the tripped element.
        element_id: IIDM id of the tripped element.
    """

    contingency_id: str
    element_type: ContingencyElementType
    element_id: str

    def apply(self, network: Network) -> None:
        """Disconnects the element on the working variant of `network`."""
        match self.element_type:
            case ContingencyElementType.LINE:
                network.update_lines(id=[self.element_id], connected1=[False], connected2=[False])
            case ContingencyElementType.TWO_WINDINGS_TRANSFORMER:
                network.update_2_windings_transformers(
                    id=[self.element_id], connected1=[False], connected2=[False])
            case ContingencyElementType.GENERATOR:
                network.update_generators(id=[self.element_id], connected=[False])


@dataclass(frozen=True)
class PostContingencyState:
    """Summary of a solved post-contingency state.

    Attributes:
        contingency_id: Contingency id.
        converged: Whether the AC load flow converged.
        max_loading_pct: Highest branch loading (% of the permanent limit).
        min_voltage_pu: Lowest bus voltage (p.u.).
        overloads: Branches above 100 %, with their loading (%).
    """

    contingency_id: str
    converged: bool
    max_loading_pct: float | None = None
    min_voltage_pu: float | None = None
    overloads: dict[str, float] | None = None


@dataclass(frozen=True)
class ContingencyList:
    """The contingencies of a variant, from `data/inputs/contingencies/`.

    Attributes:
        contingencies: Contingencies, in file order.
    """

    contingencies: list[Contingency]

    @classmethod
    def load(cls, path: Path) -> Self:
        """Reads the contingency file of a variant.

        Raises:
            InputError: On another header, a duplicate contingency id or element, or an
                unsupported element type.
        """
        frame = read_input_csv(path, _COLUMNS)
        if frame["contingency_id"].duplicated().any():
            raise InputError(f"{path.name}: duplicate contingency_id")
        if frame["element_id"].duplicated().any():
            raise InputError(f"{path.name}: an element is tripped by two contingencies")
        try:
            contingencies = [
                Contingency(str(cid), ContingencyElementType(str(kind)), str(element))
                for cid, kind, element in zip(frame["contingency_id"], frame["element_type"],
                                              frame["element_id"])]
        except ValueError as exc:
            raise InputError(f"{path.name}: {exc}") from exc
        return cls(contingencies=contingencies)

    def table(self) -> pd.DataFrame:
        """Returns the list as a table (`contingency_id`, `element_type`, `element_id`)."""
        return pd.DataFrame([{"contingency_id": c.contingency_id,
                              "element_type": str(c.element_type),
                              "element_id": c.element_id} for c in self.contingencies])

    def check(self, network: Network) -> None:
        """Checks that every element exists and that no outage splits the network.

        An outage that disconnects buses would make post-contingency results depend on
        how each tool handles islands, so the list only holds non-islanding outages.

        Raises:
            IdResolutionError: If an element is unknown or of another type.
            TestCaseError: If a branch outage disconnects part of the network.
        """
        getters = {
            ContingencyElementType.LINE: network.get_lines,
            ContingencyElementType.TWO_WINDINGS_TRANSFORMER: network.get_2_windings_transformers,
            ContingencyElementType.GENERATOR: network.get_generators,
        }
        unknown = [c.element_id for c in self.contingencies
                   if c.element_id not in getters[c.element_type]().index]
        if unknown:
            raise IdResolutionError(f"contingencies: unknown elements {unknown}")
        edges = _ac_edges(network)
        buses = set(network.get_bus_breaker_view_buses().index)
        intact = _component_count(edges, buses)
        for contingency in self.contingencies:
            if contingency.element_type is ContingencyElementType.GENERATOR:
                continue
            remaining = edges[edges.index != contingency.element_id]
            if _component_count(remaining, buses) > intact:
                raise TestCaseError(f"contingency {contingency.contingency_id} splits the network")
        logger.info("%d contingencies, none splitting the network", len(self.contingencies))

    def analyse(self, network: Network, label: str) -> list[PostContingencyState]:
        """Solves every contingency from the working variant of a solved `network`.

        Each outage is applied on a temporary copy of the working variant, which is
        left unchanged.
        """
        states = []
        source = network.get_working_variant_id()
        for contingency in self.contingencies:
            variant = f"{source}_{contingency.contingency_id}"
            network.clone_variant(source, variant)
            network.set_working_variant(variant)
            contingency.apply(network)
            try:
                run_ac(network, f"{label}/{contingency.contingency_id}")
            except LoadFlowError:
                states.append(PostContingencyState(contingency.contingency_id, converged=False))
            else:
                loadings = branch_loadings(network)
                states.append(PostContingencyState(
                    contingency.contingency_id, converged=True,
                    max_loading_pct=max(loadings.values()),
                    min_voltage_pu=float(bus_voltages(network)["v_pu"].min()),
                    overloads={branch.strip(): value for branch, value in loadings.items()
                               if value > 100.0}))
            network.set_working_variant(source)
            network.remove_variant(variant)
        return states


def summary_table(states: dict[str, list[PostContingencyState]]) -> pd.DataFrame:
    """Highest post-contingency loading (%) per contingency and scenario.

    Args:
        states: Post-contingency states per scenario, as returned by `analyse`.

    Returns:
        One row per contingency, one column per scenario; `NaN` where the load flow
        does not converge.
    """
    return pd.DataFrame({
        scenario: {s.contingency_id: s.max_loading_pct for s in scenario_states}
        for scenario, scenario_states in states.items()
    })


def log_states(label: str, states: list[PostContingencyState]) -> None:
    """Logs post-contingency results at INFO level."""
    for state in states:
        if not state.converged:
            logger.info("%s/%s: load flow does not converge", label, state.contingency_id)
        elif state.overloads:
            worst = ", ".join(f"{b} {v:.0f} %" for b, v in state.overloads.items())
            logger.info("%s/%s: overloads %s", label, state.contingency_id, worst)


def log_case_change(base: StateReport, other: StateReport,
                    base_states: list[PostContingencyState],
                    other_states: list[PostContingencyState]) -> None:
    """Logs how N and N-1 violations of a scenario change from one network case to another.

    Args:
        base: Report of the scenario on the base case.
        other: Report of the same scenario on the other case.
        base_states: Post-contingency states on the base case.
        other_states: Post-contingency states on the other case.
    """
    logger.info("%s: N: highest loading %.0f %% -> %.0f %%, overloads %d -> %d", other.label,
                max(base.loadings.values()), max(other.loadings.values()),
                len(base.overloads), len(other.overloads))
    logger.info("%s: N-1: overloads %d -> %d, non-converged %d -> %d", other.label,
                _violation_count(base_states), _violation_count(other_states),
                sum(not s.converged for s in base_states),
                sum(not s.converged for s in other_states))
    for before, after in zip(base_states, other_states):
        if before.converged and after.converged and before.max_loading_pct is not None \
                and after.max_loading_pct is not None \
                and abs(after.max_loading_pct - before.max_loading_pct) >= 5.0:
            logger.info("%s/%s: highest loading %.0f %% -> %.0f %%", other.label,
                        after.contingency_id, before.max_loading_pct, after.max_loading_pct)


def _violation_count(states: list[PostContingencyState]) -> int:
    """Number of (contingency, overloaded branch) pairs."""
    return sum(len(s.overloads or {}) for s in states)


def _ac_edges(network: Network) -> pd.DataFrame:
    columns = ["bus_breaker_bus1_id", "bus_breaker_bus2_id"]
    return pd.concat([network.get_lines(all_attributes=True)[columns],
                      network.get_2_windings_transformers(all_attributes=True)[columns]])


def _component_count(edges: pd.DataFrame, buses: set[str]) -> int:
    """Number of connected components of the AC graph of `buses` and `edges`.

    Every bus counts, so a bus left without any branch is a component of its own.
    """
    neighbours: dict[str, set[str]] = {bus: set() for bus in buses}
    for bus1, bus2 in zip(edges["bus_breaker_bus1_id"], edges["bus_breaker_bus2_id"]):
        neighbours[bus1].add(bus2)
        neighbours[bus2].add(bus1)
    seen: set[str] = set()
    count = 0
    for start in neighbours:
        if start in seen:
            continue
        count += 1
        frontier = [start]
        seen.add(start)
        while frontier:
            for neighbour in neighbours[frontier.pop()] - seen:
                seen.add(neighbour)
                frontier.append(neighbour)
    return count
