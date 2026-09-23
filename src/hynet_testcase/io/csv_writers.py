# SPDX-License-Identifier: MIT
"""CSV writers, one per file family shipped in `testcase/`."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import pandas as pd

from hynet_testcase.ids import ScenarioId
from hynet_testcase.network.zones import ZoneData
from hynet_testcase.scenarios.inputs import ScenarioInputs


@dataclass(frozen=True)
class VariantData:
    """Tabular data of a variant, written next to its networks.

    Attributes:
        scenarios: Scenario inputs.
        zones: Zone tables.
    """

    scenarios: ScenarioInputs
    zones: ZoneData


class CsvWriter(ABC):
    """Writes one CSV file in the shared format (UTF-8, comma, dot, LF)."""

    directory: ClassVar[str]
    filename: ClassVar[str]

    @abstractmethod
    def frame(self, data: VariantData) -> pd.DataFrame:
        """Returns the table to write."""

    def write(self, data: VariantData, output: Path) -> Path:
        """Writes the table under the variant output `output` and returns its path."""
        path = output / self.directory / self.filename
        path.parent.mkdir(parents=True, exist_ok=True)
        self.frame(data).to_csv(path, index=False, lineterminator="\n", encoding="utf-8")
        return path


def _time_series(frame: pd.DataFrame) -> pd.DataFrame:
    """Prefixes a scenario time series with its scenario id and UTC timestamp."""
    out = frame.copy()
    out.insert(1, "scenario_id",
               [str(ScenarioId.from_input_name(name)) for name in out["scenario"]])
    out["timestamp"] = out["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return out.rename(columns={"scenario": "scenario_name"}).sort_values(
        ["timestamp", out.columns[3]], kind="stable")


class GenerationWriter(CsvWriter):
    """Generator active power set points per scenario."""

    directory = "scenarios"
    filename = "generation.csv"

    def frame(self, data: VariantData) -> pd.DataFrame:
        """Returns the generation time series."""
        return _time_series(data.scenarios.generation)


class LoadWriter(CsvWriter):
    """Load consumption per scenario."""

    directory = "scenarios"
    filename = "loads.csv"

    def frame(self, data: VariantData) -> pd.DataFrame:
        """Returns the load time series."""
        return _time_series(data.scenarios.loads)


class HvdcWriter(CsvWriter):
    """HVDC active power set points per scenario."""

    directory = "scenarios"
    filename = "hvdc.csv"

    def frame(self, data: VariantData) -> pd.DataFrame:
        """Returns the HVDC time series."""
        return _time_series(data.scenarios.hvdc)


class GeneratorWriter(CsvWriter):
    """Generator metadata: type, nominal power, marginal price and RES flag."""

    directory = "scenarios"
    filename = "generators.csv"

    def frame(self, data: VariantData) -> pd.DataFrame:
        """Returns the generator metadata, sorted by id."""
        return data.scenarios.generators.sort_values("generator_id", kind="stable")


class BusZoneWriter(CsvWriter):
    """Zone of every bus."""

    directory = "zones"
    filename = "bus_zones.csv"

    def frame(self, data: VariantData) -> pd.DataFrame:
        """Returns the bus → zone mapping."""
        return data.zones.bus_zones


class ElementZoneWriter(CsvWriter):
    """Bus and zone of every generator and load."""

    directory = "zones"
    filename = "element_zones.csv"

    def frame(self, data: VariantData) -> pd.DataFrame:
        """Returns the element → zone mapping."""
        return data.zones.element_zones


class InterconnectionWriter(CsvWriter):
    """Branches and HVDC links between zones, with their capacity."""

    directory = "zones"
    filename = "interconnections.csv"

    def frame(self, data: VariantData) -> pd.DataFrame:
        """Returns the interconnections."""
        return data.zones.interconnections


class ZoneBalanceWriter(CsvWriter):
    """Scheduled generation, load and balance per zone and scenario."""

    directory = "zones"
    filename = "zone_balance.csv"

    def frame(self, data: VariantData) -> pd.DataFrame:
        """Returns the zone balances of every scenario, from the scenario set points."""
        rows = []
        for snapshot in data.scenarios.snapshots():
            balance = data.zones.zone_balance(snapshot.generation, snapshot.loads["p_mw"])
            balance = balance.rename_axis("zone_id").reset_index()
            balance.insert(0, "timestamp", snapshot.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"))
            balance.insert(1, "scenario_id", str(snapshot.scenario))
            rows.append(balance)
        return pd.concat(rows, ignore_index=True).round(3)


CSV_WRITERS: list[CsvWriter] = [
    GenerationWriter(), LoadWriter(), HvdcWriter(), GeneratorWriter(),
    BusZoneWriter(), ElementZoneWriter(), InterconnectionWriter(), ZoneBalanceWriter(),
]
