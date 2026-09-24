# SPDX-License-Identifier: MIT
"""Closed sets of identifiers: variants, network cases, scenarios and formats."""

from enum import StrEnum


class VariantId(StrEnum):
    """Model variants of the test case."""

    TX_FULL = "tx-full"


class CaseId(StrEnum):
    """Network cases of a variant."""

    BASE = "base"
    REINFORCED = "reinforced"


class ScenarioId(StrEnum):
    """Operating scenarios, one timestamp each."""

    S1 = "S1"
    S2 = "S2"
    S3 = "S3"

    @property
    def input_name(self) -> str:
        """Name of the scenario in the `scenario` column of the input CSVs."""
        return _INPUT_NAMES[self]

    @classmethod
    def from_input_name(cls, name: str) -> ScenarioId:
        """Returns the scenario whose input name is `name`.

        Raises:
            ValueError: If no scenario has this input name.
        """
        for scenario, input_name in _INPUT_NAMES.items():
            if input_name == name:
                return scenario
        raise ValueError(f"unknown scenario name {name!r}")


_INPUT_NAMES: dict[ScenarioId, str] = {
    ScenarioId.S1: "baseline",
    ScenarioId.S2: "high_res_low_demand",
    ScenarioId.S3: "low_res_high_demand",
}


class ExportFormat(StrEnum):
    """Network formats shipped in `testcase/`."""

    XIIDM = "xiidm"
    CGMES = "cgmes"
