# SPDX-License-Identifier: MIT
"""CSV writers, one per file family shipped in `testcase/`."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

import pandas as pd

from hynet_testcase.ids import ScenarioId
from hynet_testcase.scenarios.inputs import ScenarioInputs


class CsvWriter(ABC):
    """Writes one CSV file in the shared format (UTF-8, comma, dot, LF)."""

    filename: ClassVar[str]

    @abstractmethod
    def frame(self, inputs: ScenarioInputs) -> pd.DataFrame:
        """Returns the table to write."""

    def write(self, inputs: ScenarioInputs, directory: Path) -> Path:
        """Writes the table into `directory` and returns the file path."""
        path = directory / self.filename
        self.frame(inputs).to_csv(path, index=False, lineterminator="\n", encoding="utf-8")
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

    filename = "generation.csv"

    def frame(self, inputs: ScenarioInputs) -> pd.DataFrame:
        """Returns the generation time series."""
        return _time_series(inputs.generation)


class LoadWriter(CsvWriter):
    """Load consumption per scenario."""

    filename = "loads.csv"

    def frame(self, inputs: ScenarioInputs) -> pd.DataFrame:
        """Returns the load time series."""
        return _time_series(inputs.loads)


class HvdcWriter(CsvWriter):
    """HVDC active power set points per scenario."""

    filename = "hvdc.csv"

    def frame(self, inputs: ScenarioInputs) -> pd.DataFrame:
        """Returns the HVDC time series."""
        return _time_series(inputs.hvdc)


class GeneratorWriter(CsvWriter):
    """Generator metadata: type, nominal power, marginal price and RES flag."""

    filename = "generators.csv"

    def frame(self, inputs: ScenarioInputs) -> pd.DataFrame:
        """Returns the generator metadata, sorted by id."""
        return inputs.generators.sort_values("generator_id", kind="stable")


SCENARIO_WRITERS: list[CsvWriter] = [GenerationWriter(), LoadWriter(), HvdcWriter(),
                                     GeneratorWriter()]
