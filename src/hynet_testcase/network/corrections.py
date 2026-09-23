# SPDX-License-Identifier: MIT
"""Corrections applied to a source model, declared in `data/inputs/network/`."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

from pypowsybl.network import Network
import yaml

from hynet_testcase.errors import InputError, TestCaseError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VoltageRescale:
    """Moves voltage levels to another nominal voltage, keeping per-unit values.

    Attributes:
        source_nominal_kv: Nominal voltage of the voltage levels to rescale.
        target_nominal_kv: Nominal voltage after correction.
        expected_voltage_levels: Number of voltage levels the correction must touch.
    """

    source_nominal_kv: float
    target_nominal_kv: float
    expected_voltage_levels: int

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Self:
        """Builds the correction from its YAML mapping.

        Raises:
            InputError: If a field is missing or has the wrong type.
        """
        try:
            return cls(
                source_nominal_kv=float(data["source_nominal_kv"]),
                target_nominal_kv=float(data["target_nominal_kv"]),
                expected_voltage_levels=int(data["expected_voltage_levels"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise InputError(f"invalid voltage_rescale correction: {exc}") from exc

    def apply(self, network: Network) -> None:
        """Rescales the matching voltage levels of `network` in place.

        Raises:
            TestCaseError: If the number of matching voltage levels is not the expected
                one, if a branch straddles rescaled and other voltage levels, or if an
                element type the rescale does not handle is present.
        """
        voltage_levels = network.get_voltage_levels()
        targets = list(voltage_levels.index[voltage_levels["nominal_v"] == self.source_nominal_kv])
        if len(targets) != self.expected_voltage_levels:
            raise TestCaseError(
                f"voltage rescale expects {self.expected_voltage_levels} voltage levels at "
                f"{self.source_nominal_kv} kV, found {len(targets)}")
        ids = set(targets)
        self._check_supported(network, ids)
        k = self.target_nominal_kv / self.source_nominal_kv
        # Impedances scale with the square of the voltage base, admittances inversely.
        z = k * k

        network.update_voltage_levels(id=targets, nominal_v=[self.target_nominal_kv] * len(targets))

        lines = _within(network.get_lines(all_attributes=True), ids, "line")
        network.update_lines(
            id=list(lines.index), r=list(lines["r"] * z), x=list(lines["x"] * z),
            g1=list(lines["g1"] / z), b1=list(lines["b1"] / z),
            g2=list(lines["g2"] / z), b2=list(lines["b2"] / z))

        transformers = _within(network.get_2_windings_transformers(all_attributes=True), ids,
                               "transformer")
        network.update_2_windings_transformers(
            id=list(transformers.index),
            r=list(transformers["r"] * z), x=list(transformers["x"] * z),
            g=list(transformers["g"] / z), b=list(transformers["b"] / z),
            rated_u1=list(transformers["rated_u1"] * k),
            rated_u2=list(transformers["rated_u2"] * k))

        tap_changers = network.get_ratio_tap_changers()
        tap_changers = tap_changers[tap_changers.index.isin(transformers.index)]
        network.update_ratio_tap_changers(
            id=list(tap_changers.index), target_v=list(tap_changers["target_v"] * k))

        shunts = network.get_shunt_compensators()
        shunts = shunts[shunts["voltage_level_id"].isin(ids)]
        sections = network.get_linear_shunt_compensator_sections().loc[shunts.index]
        network.update_linear_shunt_compensator_sections(
            id=list(sections.index),
            b_per_section=list(sections["b_per_section"] / z),
            g_per_section=list(sections["g_per_section"] / z))

        generators = network.get_generators()
        generators = generators[generators["voltage_level_id"].isin(ids)]
        network.update_generators(id=list(generators.index),
                                  target_v=list(generators["target_v"] * k))

        stations = network.get_vsc_converter_stations()
        stations = stations[stations["voltage_level_id"].isin(ids)]
        network.update_vsc_converter_stations(id=list(stations.index),
                                              target_v=list(stations["target_v"] * k))

        logger.info("rescaled %d voltage levels from %g kV to %g kV (%d lines, %d transformers, "
                    "%d shunts, %d generators, %d VSC stations)", len(targets),
                    self.source_nominal_kv, self.target_nominal_kv, len(lines),
                    len(transformers), len(shunts), len(generators), len(stations))

    @staticmethod
    def _check_supported(network: Network, ids: set[str]) -> None:
        # Element types whose voltage-dependent attributes the rescale does not scale.
        # None exists in the source today; fail rather than leave one silently wrong.
        checks = {
            "phase tap changers": network.get_phase_tap_changers(),
            "three-winding transformers": network.get_3_windings_transformers(),
            "static var compensators": network.get_static_var_compensators(),
            "dangling lines": network.get_dangling_lines(),
            "LCC converter stations": network.get_lcc_converter_stations(),
            "non-linear shunt sections": network.get_non_linear_shunt_compensator_sections(),
            "operational limits": network.get_operational_limits(),
        }
        present = [name for name, frame in checks.items() if len(frame) > 0]
        limits = network.get_voltage_levels().loc[sorted(ids),
                                                  ["low_voltage_limit", "high_voltage_limit"]]
        if limits.notna().to_numpy().any():
            present.append("voltage limits")
        if present:
            raise TestCaseError(f"voltage rescale does not handle: {', '.join(present)}")


def _within(branches: Any, ids: set[str], kind: str) -> Any:
    """Returns the branches inside the voltage levels `ids`.

    Raises:
        TestCaseError: If a branch connects a voltage level in `ids` to one outside.
    """
    side1 = branches["voltage_level1_id"].isin(ids)
    side2 = branches["voltage_level2_id"].isin(ids)
    if (side1 ^ side2).any():
        raise TestCaseError(f"a {kind} connects a rescaled and a non-rescaled voltage level")
    return branches[side1 & side2]


@dataclass(frozen=True)
class SourceCorrections:
    """All corrections declared for one source model.

    Attributes:
        voltage_rescale: Nominal-voltage correction, if any.
    """

    voltage_rescale: VoltageRescale | None

    @classmethod
    def load(cls, path: Path) -> Self:
        """Reads the corrections file of a source model.

        Raises:
            InputError: If the file is missing, malformed or has unknown keys.
        """
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise InputError(f"cannot read corrections {path}: {exc}") from exc
        unknown = set(data) - {"voltage_rescale"}
        if unknown:
            raise InputError(f"unknown corrections in {path}: {sorted(unknown)}")
        rescale = data.get("voltage_rescale")
        return cls(voltage_rescale=VoltageRescale.from_mapping(rescale) if rescale else None)

    def apply(self, network: Network) -> None:
        """Applies every declared correction to `network` in place."""
        if self.voltage_rescale is not None:
            self.voltage_rescale.apply(network)
