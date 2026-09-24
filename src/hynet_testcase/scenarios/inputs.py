# SPDX-License-Identifier: MIT
"""Scenario inputs: reading, checking and applying them to a network."""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Self

import pandas as pd
from pypowsybl.network import Network

from hynet_testcase.errors import IdResolutionError, InputError
from hynet_testcase.ids import ScenarioId
from hynet_testcase.io.readers import read_input_csv

logger = logging.getLogger(__name__)

GENERATION_FILE = "generation_scenarios.csv"
LOAD_FILE = "load_scenarios.csv"
HVDC_FILE = "hvdc_setpoints.csv"
BATTERY_FILE = "battery_setpoints.csv"
GENERATOR_FILE = "generators_metadata.csv"

_TIME_SERIES_COLUMNS: dict[str, tuple[str, list[str]]] = {
    GENERATION_FILE: ("generator_id", ["p_mw"]),
    LOAD_FILE: ("load_id", ["p_mw", "q_mvar"]),
    HVDC_FILE: ("hvdc_line_id", ["target_p_mw"]),
    BATTERY_FILE: ("battery_id", ["target_p_mw"]),
}
_GENERATOR_COLUMNS = ["generator_id", "subnetwork", "type", "nominal_p_mw", "price_eur_mwh",
                      "is_res"]


def _to_float(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    for column in columns:
        try:
            frame[column] = frame[column].astype(float)
        except ValueError as exc:
            raise InputError(f"{name}: non-numeric value in {column}: {exc}") from exc


@dataclass(frozen=True)
class ScenarioSnapshot:
    """Operating point of one scenario.

    Attributes:
        scenario: Scenario id.
        timestamp: UTC timestamp of the scenario.
        generation: Active power set points (MW), indexed by generator id.
        loads: Active and reactive consumption (MW, Mvar), indexed by load id.
        hvdc: Active power set points (MW, rectifier side), indexed by HVDC line id.
        batteries: Active power set points (MW, > 0 discharging), indexed by battery id.
    """

    scenario: ScenarioId
    timestamp: datetime
    generation: pd.Series
    loads: pd.DataFrame
    hvdc: pd.Series
    batteries: pd.Series

    def apply(self, network: Network) -> None:
        """Sets the operating point on the working variant of `network`."""
        network.update_generators(id=list(self.generation.index),
                                  target_p=list(self.generation))
        network.update_loads(id=list(self.loads.index), p0=list(self.loads["p_mw"]),
                             q0=list(self.loads["q_mvar"]))
        network.update_hvdc_lines(id=list(self.hvdc.index), target_p=list(self.hvdc))
        network.update_batteries(id=list(self.batteries.index), target_p=list(self.batteries))


@dataclass(frozen=True)
class ScenarioInputs:
    """The scenario files of `data/inputs/scenarios/`, checked for consistency.

    Attributes:
        generation: Generator dispatch per scenario.
        loads: Load consumption per scenario.
        hvdc: HVDC set points per scenario.
        batteries: Battery set points per scenario.
        generators: Generator metadata (type, nominal power, price, RES flag).
    """

    generation: pd.DataFrame
    loads: pd.DataFrame
    hvdc: pd.DataFrame
    batteries: pd.DataFrame
    generators: pd.DataFrame

    @classmethod
    def load(cls, directory: Path) -> Self:
        """Reads and checks the scenario files.

        Raises:
            InputError: On a wrong header, a non-numeric value, a malformed or
                non-UTC timestamp, an unknown scenario, a duplicate row, a scenario
                with more than one timestamp, or scenarios covering different ids.
        """
        series: dict[str, pd.DataFrame] = {}
        for name, (id_column, values) in _TIME_SERIES_COLUMNS.items():
            frame = read_input_csv(directory / name, ["timestamp", "scenario", id_column, *values])
            _to_float(frame, values, name)
            frame["timestamp"] = _parse_timestamps(frame["timestamp"], name)
            _check_scenarios(frame, id_column, name)
            series[name] = frame
        _check_same_timestamps(series)

        generators = read_input_csv(directory / GENERATOR_FILE, _GENERATOR_COLUMNS)
        _to_float(generators, ["nominal_p_mw", "price_eur_mwh"], GENERATOR_FILE)
        if not generators["is_res"].isin(["True", "False"]).all():
            raise InputError(f"{GENERATOR_FILE}: is_res must be True or False")
        generators["is_res"] = generators["is_res"] == "True"
        if generators["generator_id"].duplicated().any():
            raise InputError(f"{GENERATOR_FILE}: duplicate generator_id")

        return cls(generation=series[GENERATION_FILE], loads=series[LOAD_FILE],
                   hvdc=series[HVDC_FILE], batteries=series[BATTERY_FILE],
                   generators=generators)

    def check_ids(self, network: Network) -> None:
        """Checks that the inputs cover exactly the network's elements.

        Every id must exist in the network, and every generator, load, HVDC line and
        battery of the network must be set by each scenario, so that no element keeps a value from
        the source model by omission.

        Raises:
            IdResolutionError: If an id is unknown or a network element is not covered.
        """
        expected = {
            GENERATION_FILE: ("generator_id", set(network.get_generators().index)),
            LOAD_FILE: ("load_id", set(network.get_loads().index)),
            HVDC_FILE: ("hvdc_line_id", set(network.get_hvdc_lines().index)),
            BATTERY_FILE: ("battery_id", set(network.get_batteries().index)),
        }
        frames = {GENERATION_FILE: self.generation, LOAD_FILE: self.loads, HVDC_FILE: self.hvdc,
                  BATTERY_FILE: self.batteries}
        errors: list[str] = []
        for name, (id_column, network_ids) in expected.items():
            input_ids = set(frames[name][id_column])
            if unknown := input_ids - network_ids:
                errors.append(f"{name}: unknown {id_column} {sorted(unknown)}")
            if missing := network_ids - input_ids:
                errors.append(f"{name}: no value for {sorted(missing)}")
        metadata_ids = set(self.generators["generator_id"])
        if metadata_ids != expected[GENERATION_FILE][1]:
            errors.append(f"{GENERATOR_FILE}: ids differ from the network generators")
        if errors:
            raise IdResolutionError("; ".join(errors))
        logger.info("all scenario ids resolve in the network")

    def snapshots(self) -> list[ScenarioSnapshot]:
        """Returns one snapshot per scenario, ordered by scenario id."""
        result = []
        for scenario in ScenarioId:
            generation = self.generation[self.generation["scenario"] == scenario.input_name]
            loads = self.loads[self.loads["scenario"] == scenario.input_name]
            hvdc = self.hvdc[self.hvdc["scenario"] == scenario.input_name]
            batteries = self.batteries[self.batteries["scenario"] == scenario.input_name]
            result.append(ScenarioSnapshot(
                scenario=scenario,
                timestamp=generation["timestamp"].iloc[0].to_pydatetime(),
                generation=generation.set_index("generator_id")["p_mw"],
                loads=loads.set_index("load_id")[["p_mw", "q_mvar"]],
                hvdc=hvdc.set_index("hvdc_line_id")["target_p_mw"],
                batteries=batteries.set_index("battery_id")["target_p_mw"],
            ))
        return result


def _parse_timestamps(values: pd.Series, name: str) -> pd.Series:
    # Only an explicit UTC designator is accepted; a naive timestamp is ambiguous.
    if not values.str.endswith("Z").all():
        raise InputError(f"{name}: timestamps must be ISO 8601 in UTC, ending with 'Z'")
    try:
        return pd.to_datetime(values, format="%Y-%m-%dT%H:%M:%SZ", utc=True)
    except ValueError as exc:
        raise InputError(f"{name}: malformed timestamp: {exc}") from exc


def _check_scenarios(frame: pd.DataFrame, id_column: str, name: str) -> None:
    names = {s.input_name for s in ScenarioId}
    if unknown := set(frame["scenario"]) - names:
        raise InputError(f"{name}: unknown scenarios {sorted(unknown)}")
    if missing := names - set(frame["scenario"]):
        raise InputError(f"{name}: missing scenarios {sorted(missing)}")
    if frame.duplicated(["scenario", id_column]).any():
        raise InputError(f"{name}: duplicate ({id_column}, scenario) rows")
    if (frame.groupby("scenario")["timestamp"].nunique() != 1).any():
        raise InputError(f"{name}: each scenario must have a single timestamp")
    ids_per_scenario = frame.groupby("scenario")[id_column].apply(frozenset)
    if ids_per_scenario.nunique() != 1:
        raise InputError(f"{name}: scenarios do not cover the same {id_column} set")


def _check_same_timestamps(series: dict[str, pd.DataFrame]) -> None:
    per_file = {name: frame.groupby("scenario")["timestamp"].first().to_dict()
                for name, frame in series.items()}
    reference = next(iter(per_file.values()))
    if any(timestamps != reference for timestamps in per_file.values()):
        raise InputError(f"scenario timestamps differ between files: {per_file}")
