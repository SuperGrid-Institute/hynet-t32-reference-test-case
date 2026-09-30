# SPDX-License-Identifier: MIT
"""Corrections applied to a source model, declared in `data/inputs/network/`."""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

import pypowsybl as pp
from pypowsybl.network import Network
import yaml

from hynet_testcase.errors import InputError, TestCaseError

logger = logging.getLogger(__name__)

# Identifier-carrying parts of an XIIDM file. Element references (bus, connectableBus,
# voltage level ids) never contain whitespace in the source, so they need no rewrite.
_ID_ATTRIBUTE = re.compile(r'\b(id|controlId)="([^"]*)"')
_NAME_ATTRIBUTE = re.compile(r'\bname="([^"]*)"')
_ALIAS = re.compile(r"(<iidm:alias\b[^>]*>)([^<]*)(</iidm:alias>)")
# CGMES ids kept as properties by the CGMES import that produced the source.
# CGMES.regionName is a name, not an id, and is left as is.
_CGMES_ID_PROPERTY = re.compile(
    r'(<iidm:property name="CGMES\.(?:GeneratingUnit|RegulatingControl|regionId|subRegionId)"'
    r' value=")([^"]*)(")')
_WHITESPACE = re.compile(r"\s")


def normalise_id(value: str) -> str:
    """Returns `value` without whitespace, as used for the ids of the test case.

    Leading and trailing whitespace is removed, whitespace next to a `-`, `_` or `+`
    separator is removed, and any other run of whitespace becomes `-`. For example
    `"B101-G1 "` → `"B101-G1"`, `"B4-SH 1"` → `"B4-SH-1"` and
    `"T-31-6-1 _PT_RTC_1"` → `"T-31-6-1_PT_RTC_1"`.
    """
    value = re.sub(r"\s*([-_+])\s*", r"\1", value.strip())
    return re.sub(r"\s+", "-", value)


@dataclass(frozen=True)
class IdNormalisation:
    """Removes whitespace from the ids of an XIIDM source, before it is imported.

    IIDM ids cannot be changed once a network is loaded, so the correction rewrites
    the XIIDM text. Ids, id aliases and CGMES id properties are normalised with
    `normalise_id`; names only lose their leading and trailing whitespace.

    Attributes:
        expected_ids: Number of distinct ids the correction must change.
    """

    expected_ids: int

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Self:
        """Builds the correction from its YAML mapping.

        Raises:
            InputError: If a field is missing or has the wrong type.
        """
        try:
            return cls(expected_ids=int(data["expected_ids"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise InputError(f"invalid id_normalisation correction: {exc}") from exc

    def apply(self, xiidm: str) -> str:
        """Returns the XIIDM text `xiidm` with normalised ids.

        Raises:
            TestCaseError: If the number of changed ids is not the expected one, or if
                two distinct ids would become the same.
        """
        ids = {match.group(2) for match in _ID_ATTRIBUTE.finditer(xiidm)}
        renamed = {old: normalise_id(old) for old in ids if normalise_id(old) != old}
        if len(renamed) != self.expected_ids:
            raise TestCaseError(f"id normalisation expects {self.expected_ids} ids to change, "
                                f"found {len(renamed)}")
        if len({normalise_id(old) for old in ids}) != len(ids):
            raise TestCaseError("id normalisation would merge distinct ids")

        xiidm = _ID_ATTRIBUTE.sub(lambda m: f'{m.group(1)}="{normalise_id(m.group(2))}"', xiidm)
        xiidm = _NAME_ATTRIBUTE.sub(lambda m: f'name="{m.group(1).strip()}"', xiidm)
        xiidm = _ALIAS.sub(lambda m: m.group(1) + normalise_id(m.group(2)) + m.group(3), xiidm)
        xiidm = _CGMES_ID_PROPERTY.sub(
            lambda m: m.group(1) + normalise_id(m.group(2)) + m.group(3), xiidm)
        logger.info("removed whitespace from %d ids", len(renamed))
        return xiidm


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
        id_normalisation: Id correction applied to the source text, if any.
        voltage_rescale: Nominal-voltage correction, if any.
    """

    id_normalisation: IdNormalisation | None
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
        unknown = set(data) - {"id_normalisation", "voltage_rescale"}
        if unknown:
            raise InputError(f"unknown corrections in {path}: {sorted(unknown)}")
        ids = data.get("id_normalisation")
        rescale = data.get("voltage_rescale")
        return cls(id_normalisation=IdNormalisation.from_mapping(ids) if ids else None,
                   voltage_rescale=VoltageRescale.from_mapping(rescale) if rescale else None)

    def import_source(self, source: Path) -> Network:
        """Imports the XIIDM `source` and applies every declared correction.

        Raises:
            InputError: If the source cannot be read.
        """
        try:
            xiidm = source.read_text(encoding="utf-8")
        except OSError as exc:
            raise InputError(f"cannot read source model {source}: {exc}") from exc
        if self.id_normalisation is not None:
            xiidm = self.id_normalisation.apply(xiidm)
        network = pp.network.load_from_string(source.name, xiidm)
        if self.voltage_rescale is not None:
            self.voltage_rescale.apply(network)
        return network
