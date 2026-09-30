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
    def discover(cls, start: Path | None = None) -> Self:
        """Returns the paths of the repository holding the working directory.

        The repository root is the first of `start` and its parents that holds
        `testcase/`. The distribution branch installs the package from an archive, so
        the package location says nothing about where the test case is; the working
        directory does, for the build as for the notebooks. Otherwise, falls back to
        the repository the package is installed from in editable mode, two levels above
        the package directory.

        Args:
            start: Directory to search from (default: the working directory).
        """
        start = (start or Path.cwd()).resolve()
        for directory in (start, *start.parents):
            if (directory / "testcase").is_dir():
                return cls(directory)
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
