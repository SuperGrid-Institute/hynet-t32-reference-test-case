# SPDX-License-Identifier: MIT
"""Repository-relative locations of inputs and outputs."""

from dataclasses import dataclass
from pathlib import Path
from typing import Self

from hynet_testcase.ids import VariantId


@dataclass(frozen=True)
class RepoPaths:
    """Locations used by the build, all derived from the repository root."""

    root: Path

    @classmethod
    def discover(cls) -> Self:
        """Returns the paths of the repository this package is installed from.

        The package is installed in editable mode from `src/`, so the repository root
        is two levels above the package directory.
        """
        return cls(Path(__file__).resolve().parents[2])

    @property
    def sources(self) -> Path:
        """Original models, kept unchanged."""
        return self.root / "data" / "sources"

    @property
    def inputs(self) -> Path:
        """Hand-edited inputs."""
        return self.root / "data" / "inputs"

    @property
    def testcase(self) -> Path:
        """Generated test case."""
        return self.root / "testcase"

    def variant_output(self, variant: VariantId) -> Path:
        """Generated directory of one variant."""
        return self.testcase / variant
