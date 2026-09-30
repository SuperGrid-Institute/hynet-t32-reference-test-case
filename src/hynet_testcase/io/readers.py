# SPDX-License-Identifier: MIT
"""Reading of the hand-edited CSV inputs."""

from pathlib import Path

import pandas as pd

from hynet_testcase.errors import InputError


def read_input_csv(path: Path, columns: list[str]) -> pd.DataFrame:
    """Reads an input CSV whose header must be exactly `columns`.

    Every value is read as text, so that ids are never parsed as numbers.

    Raises:
        InputError: If the file cannot be read or its header differs.
    """
    try:
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    except OSError as exc:
        raise InputError(f"cannot read {path}: {exc}") from exc
    if list(frame.columns) != columns:
        raise InputError(f"{path.name}: expected columns {columns}, found {list(frame.columns)}")
    return frame
