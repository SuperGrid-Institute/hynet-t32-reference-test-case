# SPDX-License-Identifier: MIT
"""Inverter-based renewable units added to a variant.

The units are static generators in all but name: IIDM has no separate class for them,
so they are generators with a wind or solar energy source, a reactive range given by a
minimum power factor, and no voltage control.
"""

import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Self

import pandas as pd
from pypowsybl.network import Network

from hynet_testcase.errors import IdResolutionError, InputError
from hynet_testcase.io.readers import read_input_csv

logger = logging.getLogger(__name__)

_COLUMNS = ["generator_id", "bus_id", "energy_source", "max_p_mw", "power_factor", "site"]
_ENERGY_SOURCES = {"WIND", "SOLAR"}


@dataclass(frozen=True)
class ResUnits:
    """Renewable units of a variant, one row per unit.

    Attributes:
        table: Columns of the input file, `max_p_mw` and `power_factor` as floats.
    """

    table: pd.DataFrame

    @classmethod
    def load(cls, path: Path) -> Self:
        """Reads and checks the renewable unit file of a variant.

        Raises:
            InputError: On another header, a duplicate id, an energy source other than
                WIND or SOLAR, a non-positive rating or a power factor outside (0, 1].
        """
        table = read_input_csv(path, _COLUMNS)
        if table["generator_id"].duplicated().any():
            raise InputError(f"{path.name}: duplicate generator_id")
        try:
            table[["max_p_mw", "power_factor"]] = table[["max_p_mw", "power_factor"]].astype(float)
        except ValueError as exc:
            raise InputError(f"{path.name}: non-numeric value: {exc}") from exc
        errors = []
        if unknown := sorted(set(table["energy_source"]) - _ENERGY_SOURCES):
            errors.append(f"energy_source must be WIND or SOLAR, found {unknown}")
        if not (table["max_p_mw"] > 0).all():
            errors.append("max_p_mw must be positive")
        if not (table["power_factor"].gt(0) & table["power_factor"].le(1)).all():
            errors.append("power_factor must be in (0, 1]")
        if errors:
            raise InputError(f"{path.name}: {'; '.join(errors)}")
        return cls(table=table)

    def add_to(self, network: Network) -> None:
        """Adds every unit to `network`, idle (0 MW, 0 Mvar) and without voltage control.

        The rating is `max_p_mw / power_factor` and the reactive range is symmetric,
        ± `max_p_mw · tan(acos(power_factor))`, so that the unit can run at the power
        factor at full output in both directions.

        Raises:
            IdResolutionError: If a bus is not a bus of the network, or an id is
                already used.
        """
        buses = network.get_bus_breaker_view_buses()["voltage_level_id"]
        if unknown := sorted(set(self.table["bus_id"]) - set(buses.index)):
            raise IdResolutionError(f"renewable units: unknown bus_id {unknown}")
        if clash := sorted(set(self.table["generator_id"])
                           & set(network.get_identifiables().index)):
            raise IdResolutionError(f"renewable units: ids already used in the network {clash}")
        ids = list(self.table["generator_id"])
        max_p = list(self.table["max_p_mw"])
        max_q = [p * math.tan(math.acos(pf))
                 for p, pf in zip(max_p, self.table["power_factor"])]
        network.create_generators(
            id=ids, voltage_level_id=[buses[bus] for bus in self.table["bus_id"]],
            bus_id=list(self.table["bus_id"]), energy_source=list(self.table["energy_source"]),
            min_p=[0.0] * len(ids), max_p=max_p, target_p=[0.0] * len(ids),
            target_q=[0.0] * len(ids), voltage_regulator_on=[False] * len(ids),
            rated_s=[p / pf for p, pf in zip(max_p, self.table["power_factor"])])
        network.create_minmax_reactive_limits(id=ids, min_q=[-q for q in max_q], max_q=max_q)
        logger.info("added %d renewable units (%g MW)", len(ids), sum(max_p))
