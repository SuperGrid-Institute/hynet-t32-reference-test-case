# SPDX-License-Identifier: MIT
"""Batteries for adequacy studies.

They are shipped as data only and never added to the network models, so security and
dynamic studies, and the PowerFactory model, are unaffected.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Self

import pandas as pd

from hynet_testcase.errors import IdResolutionError, InputError
from hynet_testcase.io.readers import read_input_csv
from hynet_testcase.network.zones import ZoneData

logger = logging.getLogger(__name__)

_COLUMNS = ["battery_id", "bus_id", "power_mw", "energy_mwh", "charge_efficiency",
            "discharge_efficiency", "initial_soc", "final_soc"]
_NUMERIC = _COLUMNS[2:]


@dataclass(frozen=True)
class Batteries:
    """Batteries of a variant, one row per battery.

    Attributes:
        table: Columns of the input file, numeric columns as floats.
    """

    table: pd.DataFrame

    @classmethod
    def load(cls, path: Path) -> Self:
        """Reads and checks the battery file of a variant.

        Raises:
            InputError: On another header, a duplicate id, a non-numeric value, a
                non-positive power or energy, an efficiency outside (0, 1] or a state
                of charge outside [0, 1].
        """
        table = read_input_csv(path, _COLUMNS)
        if table["battery_id"].duplicated().any():
            raise InputError(f"{path.name}: duplicate battery_id")
        try:
            table[_NUMERIC] = table[_NUMERIC].astype(float)
        except ValueError as exc:
            raise InputError(f"{path.name}: non-numeric value: {exc}") from exc
        checks = {
            "power_mw and energy_mwh must be positive":
                (table[["power_mw", "energy_mwh"]] > 0).all(axis=None),
            "efficiencies must be in (0, 1]":
                table[["charge_efficiency", "discharge_efficiency"]].gt(0).all(axis=None)
                and table[["charge_efficiency", "discharge_efficiency"]].le(1).all(axis=None),
            "states of charge must be in [0, 1]":
                table[["initial_soc", "final_soc"]].ge(0).all(axis=None)
                and table[["initial_soc", "final_soc"]].le(1).all(axis=None),
        }
        if failed := [message for message, ok in checks.items() if not ok]:
            raise InputError(f"{path.name}: {'; '.join(failed)}")
        return cls(table=table)

    def with_zones(self, zones: ZoneData) -> pd.DataFrame:
        """Returns the battery table with the zone of each connection bus.

        Raises:
            IdResolutionError: If a battery bus is not a bus of the network.
        """
        bus_zones = zones.bus_zones.set_index("bus_id")["zone_id"].to_dict()
        if unknown := sorted(set(self.table["bus_id"]) - set(bus_zones)):
            raise IdResolutionError(f"batteries: unknown bus_id {unknown}")
        table = self.table.copy()
        table.insert(2, "zone_id", [bus_zones[bus] for bus in table["bus_id"]])
        for row in table.itertuples():
            logger.info("battery %s at %s (%s): %g MW, %g MWh", row.battery_id, row.bus_id,
                        row.zone_id, row.power_mw, row.energy_mwh)
        return table.sort_values("battery_id", kind="stable")
