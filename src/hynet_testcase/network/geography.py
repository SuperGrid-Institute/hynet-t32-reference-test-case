# SPDX-License-Identifier: MIT
"""Geographical coordinates of the substations of a variant.

The coordinates are illustrative: they place the network on a map so that tools and
diagrams can show it geographically, not at real substation sites. They are stored in
IIDM as the `substationPosition` extension. The CGMES export of pypowsybl has no
geographical (GL) profile, so they are also shipped as a table, one row per bus.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Self

import pandas as pd
from pypowsybl.network import Network

from hynet_testcase.errors import IdResolutionError, InputError
from hynet_testcase.io.readers import read_input_csv

logger = logging.getLogger(__name__)

_COLUMNS = ["substation_id", "latitude", "longitude"]
_EXTENSION = "substationPosition"


@dataclass(frozen=True)
class SubstationCoordinates:
    """WGS84 coordinates of every substation of a variant.

    Attributes:
        table: Columns of the input file, latitude and longitude as floats.
    """

    table: pd.DataFrame

    @classmethod
    def load(cls, path: Path) -> Self:
        """Reads and checks the substation coordinate file of a variant.

        Raises:
            InputError: On another header, a duplicate substation, a non-numeric value,
                or a latitude outside [-90, 90] or longitude outside [-180, 180].
        """
        table = read_input_csv(path, _COLUMNS)
        if duplicated := sorted(table.loc[table["substation_id"].duplicated(), "substation_id"]):
            raise InputError(f"{path.name}: substations in more than one row: {duplicated}")
        try:
            table[_COLUMNS[1:]] = table[_COLUMNS[1:]].astype(float)
        except ValueError as exc:
            raise InputError(f"{path.name}: non-numeric value: {exc}") from exc
        if not (table["latitude"].abs() <= 90).all() or not (table["longitude"].abs() <= 180).all():
            raise InputError(f"{path.name}: latitude or longitude out of range")
        return cls(table=table)

    def add_to(self, network: Network) -> None:
        """Adds the position of every substation to `network`.

        Raises:
            IdResolutionError: If a substation is unknown or has no coordinates.
        """
        substations = set(network.get_substations().index)
        listed = set(self.table["substation_id"])
        errors = []
        if unknown := sorted(listed - substations):
            errors.append(f"unknown substation_id {unknown}")
        if missing := sorted(substations - listed):
            errors.append(f"no coordinates for {missing}")
        if errors:
            raise IdResolutionError("substation coordinates: " + "; ".join(errors))
        network.create_extensions(_EXTENSION, id=list(self.table["substation_id"]),
                                  latitude=list(self.table["latitude"]),
                                  longitude=list(self.table["longitude"]))
        logger.info("added coordinates to %d substations", len(self.table))


def bus_coordinates(network: Network) -> pd.DataFrame:
    """Returns the coordinates of every bus-breaker bus, those of its substation.

    Raises:
        IdResolutionError: If a substation of the network has no position.
    """
    buses = network.get_bus_breaker_view_buses()
    substations = buses["voltage_level_id"].map(network.get_voltage_levels()["substation_id"])
    positions = network.get_extensions(_EXTENSION)
    if missing := sorted(set(substations) - set(positions.index)):
        raise IdResolutionError(f"substations without coordinates: {missing}")
    table = pd.DataFrame({
        "bus_id": buses.index,
        "substation_id": substations.to_numpy(),
        "latitude": positions.loc[substations, "latitude"].to_numpy(),
        "longitude": positions.loc[substations, "longitude"].to_numpy(),
    })
    return table.sort_values("bus_id", kind="stable", ignore_index=True)
