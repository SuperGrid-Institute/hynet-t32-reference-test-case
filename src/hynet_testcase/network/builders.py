# SPDX-License-Identifier: MIT
"""Builders turning source models into the network of each variant."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from pypowsybl.network import Network

from hynet_testcase.errors import InputError
from hynet_testcase.ids import VariantId
from hynet_testcase.network.corrections import SourceCorrections
from hynet_testcase.network.limits import ThermalLimits
from hynet_testcase.paths import RepoPaths
from hynet_testcase.storage.batteries import Batteries

logger = logging.getLogger(__name__)


class VariantBuilder(ABC):
    """Builds the base network of one variant, in memory."""

    variant: ClassVar[VariantId]

    def __init__(self, paths: RepoPaths) -> None:
        self.paths = paths

    @abstractmethod
    def build(self) -> Network:
        """Returns the corrected base network of the variant, not yet solved."""

    @abstractmethod
    def unchanged_files(self) -> list[Path]:
        """Source files shipped as received, next to the exported base network."""


class TxFullBuilder(VariantBuilder):
    """IEEE 39-bus + HVDC link + IEEE 14-bus, from UCY's XIIDM model."""

    variant = VariantId.TX_FULL

    @property
    def _source_dir(self) -> Path:
        return self.paths.sources / "tx-full"

    def build(self) -> Network:
        """Imports `TestCase.xiidm` and applies corrections, thermal limits and batteries.

        Raises:
            InputError: If the source model is missing.
        """
        source = self._source_dir / "TestCase.xiidm"
        if not source.is_file():
            raise InputError(f"missing source model {source}")
        logger.info("importing %s", source.relative_to(self.paths.root))
        inputs = self.paths.inputs / "network"
        network = SourceCorrections.load(inputs / "tx-full_corrections.yaml").import_source(source)
        # Limits are in A, so they are added once voltages are in physical units.
        ThermalLimits.load(inputs / "tx-full_thermal_limits.csv").apply(network)
        Batteries.load(self.paths.inputs / "storage" / "tx-full_batteries.csv").add_to(network)
        return network

    def unchanged_files(self) -> list[Path]:
        """The PowerFactory model, which pypowsybl can neither read nor write.

        Raises:
            InputError: If the file is missing.
        """
        pfd = self._source_dir / "TestCase.pfd"
        if not pfd.is_file():
            raise InputError(f"missing source model {pfd}")
        return [pfd]
