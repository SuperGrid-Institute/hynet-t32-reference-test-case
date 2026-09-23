# SPDX-License-Identifier: MIT
"""Thermal limits of branches, declared in `data/inputs/network/`."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Self

import pandas as pd
from pypowsybl.network import Network

from hynet_testcase.errors import IdResolutionError, InputError

logger = logging.getLogger(__name__)

PERMANENT_LIMIT_NAME = "permanent_limit"
_COLUMNS = ["branch_id", "permanent_limit_a", "basis"]


@dataclass(frozen=True)
class ThermalLimits:
    """Permanent current limit of every line and two-winding transformer.

    Attributes:
        limits_a: Permanent current limit (A), indexed by branch id. The same limit
            applies to both sides of the branch.
    """

    limits_a: pd.Series

    @classmethod
    def load(cls, path: Path) -> Self:
        """Reads the thermal limits file of a variant.

        Raises:
            InputError: If the file is missing, has another header, a duplicate branch,
                or a limit that is not a positive number.
        """
        try:
            frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        except OSError as exc:
            raise InputError(f"cannot read {path}: {exc}") from exc
        if list(frame.columns) != _COLUMNS:
            raise InputError(f"{path.name}: expected columns {_COLUMNS}, "
                             f"found {list(frame.columns)}")
        if frame["branch_id"].duplicated().any():
            raise InputError(f"{path.name}: duplicate branch_id")
        try:
            limits = frame.set_index("branch_id")["permanent_limit_a"].astype(float)
        except ValueError as exc:
            raise InputError(f"{path.name}: non-numeric permanent_limit_a: {exc}") from exc
        if not (limits > 0).all():
            raise InputError(f"{path.name}: permanent_limit_a must be positive")
        return cls(limits_a=limits)

    def apply(self, network: Network) -> None:
        """Adds the limits to both sides of every branch of `network`.

        Raises:
            IdResolutionError: If a branch id is unknown, or if a line or two-winding
                transformer of the network has no limit.
        """
        branches = set(network.get_lines().index) | set(network.get_2_windings_transformers().index)
        errors = []
        if unknown := set(self.limits_a.index) - branches:
            errors.append(f"unknown branch_id {sorted(unknown)}")
        if missing := branches - set(self.limits_a.index):
            errors.append(f"no thermal limit for {sorted(missing)}")
        if errors:
            raise IdResolutionError("thermal limits: " + "; ".join(errors))
        ids = list(self.limits_a.index)
        for side in ("ONE", "TWO"):
            network.create_loading_limits(
                element_id=ids, name=[PERMANENT_LIMIT_NAME] * len(ids), side=[side] * len(ids),
                type=["CURRENT"] * len(ids), value=list(self.limits_a),
                acceptable_duration=[-1] * len(ids), fictitious=[False] * len(ids))
        logger.info("added permanent current limits to %d branches", len(ids))
