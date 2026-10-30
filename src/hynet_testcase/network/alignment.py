# SPDX-License-Identifier: MIT
"""Element data aligned with a reference model, declared in `data/inputs/network/`.

Each table overrides attributes of existing elements of the source model with the
values of a reference model, here the PowerFactory model of `tx-full`. Every row names
the reference element it comes from in a `basis` column.
"""

import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

import pandas as pd
from pypowsybl.network import Network

from hynet_testcase.errors import IdResolutionError, InputError
from hynet_testcase.io.readers import read_input_csv

logger = logging.getLogger(__name__)

_GENERATOR_COLUMNS = ["generator_id", "rated_s_mva", "min_p_mw", "max_p_mw", "target_p_mw",
                      "min_q_mvar", "max_q_mvar", "target_v_pu", "voltage_regulator_on", "basis"]
_TRANSFORMER_COLUMNS = ["transformer_id", "rated_s_mva", "uk_pct", "pcu_kw", "parallel_units",
                        "basis"]
_LOAD_COLUMNS = ["load_id", "p_mw", "q_mvar", "basis"]


def _numbers(frame: pd.DataFrame, columns: list[str], name: str, blank: bool) -> None:
    """Converts `columns` to floats in place; blank cells become NaN if `blank`.

    Raises:
        InputError: On a non-numeric value, or a blank one when `blank` is false.
    """
    for column in columns:
        if not blank and (frame[column] == "").any():
            raise InputError(f"{name}: blank value in {column}")
        try:
            frame[column] = pd.to_numeric(frame[column].replace("", math.nan), errors="raise")
        except ValueError as exc:
            raise InputError(f"{name}: non-numeric value in {column}: {exc}") from exc


def _check_ids(listed: pd.Series, existing: set[str], kind: str, name: str,
               complete: bool) -> None:
    """Checks that `listed` ids are unique, exist and, if `complete`, cover `existing`.

    Raises:
        InputError: On a duplicate id.
        IdResolutionError: On an unknown id, or a missing one when `complete`.
    """
    if duplicated := sorted(listed[listed.duplicated()]):
        raise InputError(f"{name}: {kind} in more than one row: {duplicated}")
    errors = []
    if unknown := sorted(set(listed) - existing):
        errors.append(f"unknown {kind} {unknown}")
    if complete and (missing := sorted(existing - set(listed))):
        errors.append(f"no row for {missing}")
    if errors:
        raise IdResolutionError(f"{name}: " + "; ".join(errors))


@dataclass(frozen=True)
class GeneratorData:
    """Ratings, operating ranges and voltage control of every generator.

    A blank cell keeps the value of the source model.

    Attributes:
        table: Columns of the input file, numbers as floats (NaN when blank) and
            `voltage_regulator_on` as text (`True`, `False` or blank).
        name: Input file name, for messages.
    """

    table: pd.DataFrame
    name: str

    @classmethod
    def load(cls, path: Path) -> Self:
        """Reads and checks the generator data file of a variant.

        Raises:
            InputError: On another header, a non-numeric value, a `voltage_regulator_on`
                other than True, False or blank, only one of the two reactive limits,
                or a minimum above its maximum.
        """
        table = read_input_csv(path, _GENERATOR_COLUMNS)
        _numbers(table, _GENERATOR_COLUMNS[1:8], path.name, blank=True)
        errors = []
        if not table["voltage_regulator_on"].isin(["True", "False", ""]).all():
            errors.append("voltage_regulator_on must be True, False or blank")
        if (table["min_q_mvar"].isna() != table["max_q_mvar"].isna()).any():
            errors.append("min_q_mvar and max_q_mvar must be both set or both blank")
        if (table["min_p_mw"] > table["max_p_mw"]).any() or (
                table["min_q_mvar"] > table["max_q_mvar"]).any():
            errors.append("a minimum is above its maximum")
        if errors:
            raise InputError(f"{path.name}: {'; '.join(errors)}")
        return cls(table=table, name=path.name)

    def apply(self, network: Network) -> None:
        """Sets the declared values on the generators of `network`.

        Voltage set points are converted at the nominal voltage of the generator's
        voltage level, which is also that of its regulated bus in the source.

        Raises:
            InputError: On a duplicate generator.
            IdResolutionError: If a generator is unknown or has no row.
        """
        generators = network.get_generators(all_attributes=True)
        _check_ids(self.table["generator_id"], set(generators.index), "generator_id", self.name,
                   complete=True)
        nominal_v = generators["voltage_level_id"].map(network.get_voltage_levels()["nominal_v"])
        table = self.table.set_index("generator_id")
        updates = {"rated_s": "rated_s_mva", "min_p": "min_p_mw", "max_p": "max_p_mw",
                   "target_p": "target_p_mw"}
        for attribute, column in updates.items():
            values = table[column].dropna()
            if len(values):
                network.update_generators(values.rename(attribute).rename_axis("id").to_frame())
        target_v = table["target_v_pu"].dropna()
        if len(target_v):
            network.update_generators(id=list(target_v.index),
                                      target_v=list(target_v * nominal_v[target_v.index]))
        regulating = table.loc[table["voltage_regulator_on"] != "", "voltage_regulator_on"]
        if len(regulating):
            network.update_generators(id=list(regulating.index),
                                      voltage_regulator_on=list(regulating == "True"))
        limits = table[["min_q_mvar", "max_q_mvar"]].dropna()
        if len(limits):
            network.create_minmax_reactive_limits(id=list(limits.index),
                                                  min_q=list(limits["min_q_mvar"]),
                                                  max_q=list(limits["max_q_mvar"]))
        logger.info("set reference data on %d generators", len(table))


@dataclass(frozen=True)
class TransformerData:
    """Impedance and rating of every two-winding transformer, from nameplate data.

    The series impedance is derived from the short-circuit voltage `uk_pct` and the
    copper losses `pcu_kw` on the rating `rated_s_mva` of one unit, as in PowerFactory;
    `parallel_units` identical units in parallel divide it and multiply the rating.

    Attributes:
        table: Columns of the input file, numbers as floats.
        name: Input file name, for messages.
    """

    table: pd.DataFrame
    name: str

    @classmethod
    def load(cls, path: Path) -> Self:
        """Reads and checks the transformer data file of a variant.

        Raises:
            InputError: On another header, a blank or non-numeric value, a rating,
                `uk_pct` or unit count that is not positive, negative copper losses, or
                copper losses that exceed the short-circuit impedance.
        """
        table = read_input_csv(path, _TRANSFORMER_COLUMNS)
        _numbers(table, _TRANSFORMER_COLUMNS[1:5], path.name, blank=False)
        errors = []
        if not (table[["rated_s_mva", "uk_pct", "parallel_units"]] > 0).all(axis=None):
            errors.append("rated_s_mva, uk_pct and parallel_units must be positive")
        if (table["pcu_kw"] < 0).any():
            errors.append("pcu_kw must not be negative")
        if (table["parallel_units"] % 1 != 0).any():
            errors.append("parallel_units must be an integer")
        if (_resistance_pu(table) >= table["uk_pct"] / 100.0).any():
            errors.append("pcu_kw exceeds the short-circuit impedance")
        if errors:
            raise InputError(f"{path.name}: {'; '.join(errors)}")
        return cls(table=table, name=path.name)

    def apply(self, network: Network) -> None:
        """Sets r, x and the rating of every transformer of `network`.

        IIDM holds the impedance in ohms on side 2. It is computed at the nominal
        voltage of that side, so per-unit values on 100 MVA equal the reference ones
        whatever the nominal voltages of the two models.

        Raises:
            InputError: On a duplicate transformer.
            IdResolutionError: If a transformer is unknown or has no row.
        """
        transformers = network.get_2_windings_transformers(all_attributes=True)
        _check_ids(self.table["transformer_id"], set(transformers.index), "transformer_id",
                   self.name, complete=True)
        table = self.table.set_index("transformer_id")
        nominal_v2 = transformers.loc[table.index, "voltage_level2_id"].map(
            network.get_voltage_levels()["nominal_v"])
        z_base = nominal_v2 ** 2 / table["rated_s_mva"]
        r_pu = _resistance_pu(table)
        x_pu = ((table["uk_pct"] / 100.0) ** 2 - r_pu ** 2) ** 0.5
        units = table["parallel_units"]
        network.update_2_windings_transformers(
            id=list(table.index), r=list(r_pu * z_base / units), x=list(x_pu * z_base / units),
            rated_s=list(table["rated_s_mva"] * units))
        logger.info("set nameplate impedances on %d transformers", len(table))


def _resistance_pu(table: pd.DataFrame) -> pd.Series:
    """Series resistance in p.u. of the unit rating, from the copper losses."""
    return table["pcu_kw"] / 1000.0 / table["rated_s_mva"]


@dataclass(frozen=True)
class LoadData:
    """Base-case consumption of selected loads.

    Attributes:
        table: Columns of the input file, numbers as floats.
        name: Input file name, for messages.
    """

    table: pd.DataFrame
    name: str

    @classmethod
    def load(cls, path: Path) -> Self:
        """Reads and checks the load data file of a variant.

        Raises:
            InputError: On another header or a blank or non-numeric value.
        """
        table = read_input_csv(path, _LOAD_COLUMNS)
        _numbers(table, ["p_mw", "q_mvar"], path.name, blank=False)
        return cls(table=table, name=path.name)

    def apply(self, network: Network) -> None:
        """Sets the declared consumption on the loads of `network`.

        Raises:
            InputError: On a duplicate load.
            IdResolutionError: If a load is unknown.
        """
        _check_ids(self.table["load_id"], set(network.get_loads().index), "load_id", self.name,
                   complete=False)
        network.update_loads(id=list(self.table["load_id"]), p0=list(self.table["p_mw"]),
                             q0=list(self.table["q_mvar"]))
        logger.info("set reference consumption on %d loads", len(self.table))


@dataclass(frozen=True)
class HvdcLineData:
    """DC data of one HVDC line.

    Attributes:
        nominal_v_kv: Nominal DC voltage (kV).
        r_ohm: DC resistance (Ω).
        max_p_mw: Maximum active power (MW).
    """

    nominal_v_kv: float
    r_ohm: float
    max_p_mw: float


@dataclass(frozen=True)
class ConverterStationData:
    """Control of one VSC converter station.

    Attributes:
        voltage_regulator_on: Whether the station regulates its AC voltage.
        target_v_pu: AC voltage set point (p.u. of nominal), if it regulates.
        target_q_mvar: Reactive power set point (Mvar), if it does not.
        min_q_mvar: Lower reactive limit (Mvar).
        max_q_mvar: Upper reactive limit (Mvar).
    """

    voltage_regulator_on: bool
    target_v_pu: float | None
    target_q_mvar: float | None
    min_q_mvar: float
    max_q_mvar: float


@dataclass(frozen=True)
class HvdcData:
    """DC data of HVDC lines and control of their converter stations.

    Attributes:
        lines: Data per HVDC line id.
        stations: Data per converter station id.
    """

    lines: dict[str, HvdcLineData]
    stations: dict[str, ConverterStationData]

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Self:
        """Builds the correction from its YAML mapping (`lines`, `converter_stations`).

        Raises:
            InputError: If a key is missing or unknown, a value has the wrong type, a
                regulating station has no voltage set point, a non-regulating one has no
                reactive set point, or a limit or rating is inconsistent.
        """
        try:
            if set(data) != {"lines", "converter_stations"}:
                raise ValueError("expected lines and converter_stations")
            lines = {}
            for line_id, line in data["lines"].items():
                if set(line) != {"nominal_v_kv", "r_ohm", "max_p_mw"}:
                    raise ValueError(f"{line_id}: expected nominal_v_kv, r_ohm, max_p_mw")
                lines[str(line_id)] = HvdcLineData(float(line["nominal_v_kv"]),
                                                   float(line["r_ohm"]), float(line["max_p_mw"]))
                if min(lines[str(line_id)].nominal_v_kv, lines[str(line_id)].max_p_mw) <= 0:
                    raise ValueError(f"{line_id}: nominal_v_kv and max_p_mw must be positive")
            stations = {}
            for station_id, station in data["converter_stations"].items():
                if unknown := set(station) - {"voltage_regulator_on", "target_v_pu",
                                              "target_q_mvar", "min_q_mvar", "max_q_mvar"}:
                    raise ValueError(f"{station_id}: unknown keys {sorted(unknown)}")
                regulating = station["voltage_regulator_on"]
                if not isinstance(regulating, bool):
                    raise ValueError(f"{station_id}: voltage_regulator_on must be true or false")
                target_v, target_q = station.get("target_v_pu"), station.get("target_q_mvar")
                if (target_v is None) == regulating or (target_q is None) != regulating:
                    raise ValueError(f"{station_id}: give target_v_pu if it regulates its "
                                     f"voltage, target_q_mvar otherwise")
                stations[str(station_id)] = ConverterStationData(
                    voltage_regulator_on=regulating,
                    target_v_pu=None if target_v is None else float(target_v),
                    target_q_mvar=None if target_q is None else float(target_q),
                    min_q_mvar=float(station["min_q_mvar"]),
                    max_q_mvar=float(station["max_q_mvar"]))
                if stations[str(station_id)].min_q_mvar > stations[str(station_id)].max_q_mvar:
                    raise ValueError(f"{station_id}: min_q_mvar above max_q_mvar")
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise InputError(f"invalid hvdc correction: {exc}") from exc
        return cls(lines=lines, stations=stations)

    def apply(self, network: Network) -> None:
        """Sets the declared data on the HVDC lines and converter stations of `network`.

        Raises:
            IdResolutionError: If a line or station is unknown, or a line of the network
                or one of its stations has no data.
        """
        lines = network.get_hvdc_lines()
        stations = network.get_vsc_converter_stations(all_attributes=True)
        errors = []
        if unknown := sorted(set(self.lines) - set(lines.index)):
            errors.append(f"unknown HVDC lines {unknown}")
        if unknown := sorted(set(self.stations) - set(stations.index)):
            errors.append(f"unknown converter stations {unknown}")
        if missing := sorted(set(lines.index) - set(self.lines)):
            errors.append(f"no data for HVDC lines {missing}")
        if missing := sorted(set(stations.index) - set(self.stations)):
            errors.append(f"no data for converter stations {missing}")
        if errors:
            raise IdResolutionError("hvdc correction: " + "; ".join(errors))

        network.update_hvdc_lines(
            id=list(self.lines), nominal_v=[line.nominal_v_kv for line in self.lines.values()],
            r=[line.r_ohm for line in self.lines.values()],
            max_p=[line.max_p_mw for line in self.lines.values()])
        nominal_v = stations["voltage_level_id"].map(network.get_voltage_levels()["nominal_v"])
        for station_id, station in self.stations.items():
            if station.target_v_pu is not None:
                network.update_vsc_converter_stations(
                    id=station_id, target_v=station.target_v_pu * nominal_v[station_id])
            if station.target_q_mvar is not None:
                network.update_vsc_converter_stations(id=station_id,
                                                      target_q=station.target_q_mvar)
            network.update_vsc_converter_stations(
                id=station_id, voltage_regulator_on=station.voltage_regulator_on)
        network.create_minmax_reactive_limits(
            id=list(self.stations), min_q=[s.min_q_mvar for s in self.stations.values()],
            max_q=[s.max_q_mvar for s in self.stations.values()])
        logger.info("set DC data on %d HVDC lines and control of %d converter stations",
                    len(self.lines), len(self.stations))
