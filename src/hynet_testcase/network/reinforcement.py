# SPDX-License-Identifier: MIT
"""The `reinforced` network case: the base case plus one new line."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Self

import pandas as pd
import yaml
from pypowsybl.network import Network

from hynet_testcase.economics import Economics
from hynet_testcase.errors import IdResolutionError, InputError
from hynet_testcase.network.limits import PERMANENT_LIMIT_NAME

logger = logging.getLogger(__name__)


def add_parallel_line(network: Network, line_id: str, parallel_to: str) -> None:
    """Adds a line between the buses of `parallel_to`, with the same parameters.

    Operational limits are not copied.

    Raises:
        IdResolutionError: If the copied line is unknown or the new id is taken.
    """
    lines = network.get_lines(all_attributes=True)
    if parallel_to not in lines.index:
        raise IdResolutionError(f"parallel line: unknown line {parallel_to!r}")
    if line_id in network.get_identifiables().index:
        raise IdResolutionError(f"parallel line: id {line_id!r} already used")
    model = lines.loc[parallel_to]
    network.create_lines(
        id=[line_id],
        voltage_level1_id=[model["voltage_level1_id"]], bus1_id=[model["bus_breaker_bus1_id"]],
        voltage_level2_id=[model["voltage_level2_id"]], bus2_id=[model["bus_breaker_bus2_id"]],
        r=[model["r"]], x=[model["x"]], g1=[model["g1"]], b1=[model["b1"]],
        g2=[model["g2"]], b2=[model["b2"]])
    logger.info("added %s parallel to %s", line_id, parallel_to)


@dataclass(frozen=True)
class Reinforcement:
    """A new circuit parallel to an existing line.

    Attributes:
        line_id: Id of the new line.
        parallel_to: Id of the existing line whose parameters and limit are copied.
        length_km: Length of the new line (km), for its investment cost.
    """

    line_id: str
    parallel_to: str
    length_km: float

    @classmethod
    def load(cls, path: Path) -> Self:
        """Reads the reinforcement file of a variant.

        Raises:
            InputError: If the file cannot be read, a key is missing or unknown, or the
                length is not positive.
        """
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise InputError(f"cannot read {path}: {exc}") from exc
        line = data.get("new_line") or {}
        if set(data) != {"new_line"} or set(line) != {"id", "parallel_to", "length_km"}:
            raise InputError(f"{path.name}: expected new_line with id, parallel_to, length_km")
        try:
            reinforcement = cls(line_id=str(line["id"]), parallel_to=str(line["parallel_to"]),
                                length_km=float(line["length_km"]))
        except (TypeError, ValueError) as exc:
            raise InputError(f"{path.name}: {exc}") from exc
        if reinforcement.length_km <= 0:
            raise InputError(f"{path.name}: length_km must be positive")
        return reinforcement

    def apply(self, network: Network) -> None:
        """Adds the new line to `network`, with the parameters and limit it copies.

        Raises:
            IdResolutionError: If the copied line is unknown or the new id is taken.
        """
        add_parallel_line(network, self.line_id, self.parallel_to)
        limits = network.get_operational_limits(attributes=["name", "value"]).reset_index()
        limits = limits[(limits["element_id"] == self.parallel_to)
                        & (limits["name"] == PERMANENT_LIMIT_NAME)]
        for side, value in zip(limits["side"], limits["value"]):
            network.create_loading_limits(
                element_id=self.line_id, name=PERMANENT_LIMIT_NAME, side=side, type="CURRENT",
                value=float(value), acceptable_duration=-1, fictitious=False)
        logger.info("reinforcement %s is %g km long", self.line_id, self.length_km)

    def investment(self, economics: Economics) -> pd.DataFrame:
        """Returns the investment and annuity of the new line (EUR, EUR/year)."""
        investment = self.length_km * economics.line_cost_345kv_eur_km
        return pd.DataFrame([{
            "element_id": self.line_id,
            "length_km": self.length_km,
            "investment_eur": round(investment, 2),
            "annuity_eur_year": round(economics.annuity_eur(investment), 2),
        }])
