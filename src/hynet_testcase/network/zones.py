# SPDX-License-Identifier: MIT
"""Bidding zones: an overlay of the network defined by a bus → zone mapping."""

import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Self

import pandas as pd
from pypowsybl.network import Network

from hynet_testcase.errors import IdResolutionError, InputError, TestCaseError
from hynet_testcase.io.readers import read_input_csv
from hynet_testcase.network.limits import PERMANENT_LIMIT_NAME

logger = logging.getLogger(__name__)

_COLUMNS = ["bus_id", "zone_id"]


@dataclass(frozen=True)
class ZoneMapping:
    """Zone of every bus-breaker bus of a variant.

    Attributes:
        bus_zones: Zone id, indexed by bus id.
    """

    bus_zones: pd.Series

    @classmethod
    def load(cls, path: Path) -> Self:
        """Reads the bus → zone file of a variant.

        Raises:
            InputError: If the file is missing, has another header, lists a bus twice
                or has an empty zone id.
        """
        frame = read_input_csv(path, _COLUMNS)
        if duplicated := sorted(frame.loc[frame["bus_id"].duplicated(), "bus_id"]):
            raise InputError(f"{path.name}: buses in more than one row: {duplicated}")
        if (frame["zone_id"] == "").any():
            raise InputError(f"{path.name}: empty zone_id")
        return cls(bus_zones=frame.set_index("bus_id")["zone_id"])

    def resolve(self, network: Network) -> ZoneData:
        """Checks the mapping against `network` and derives the zone tables.

        Raises:
            IdResolutionError: If a bus is unknown or has no zone.
            TestCaseError: If a zone is not connected through its own AC branches.
        """
        buses = network.get_bus_breaker_view_buses()
        errors = []
        if unknown := set(self.bus_zones.index) - set(buses.index):
            errors.append(f"unknown bus_id {sorted(unknown)}")
        if missing := set(buses.index) - set(self.bus_zones.index):
            errors.append(f"no zone for {sorted(missing)}")
        if errors:
            raise IdResolutionError("zones: " + "; ".join(errors))

        branches = _ac_branches(network)
        self._check_connected(branches)
        elements = pd.concat([
            self._element_zones(network.get_generators(all_attributes=True), "generator"),
            self._element_zones(network.get_loads(all_attributes=True), "load"),
            self._element_zones(network.get_batteries(all_attributes=True), "battery"),
        ], ignore_index=True)
        interconnections = pd.concat([self._ac_ties(branches, network),
                                      self._hvdc_links(network)], ignore_index=True)
        logger.info("%d zones, %d interconnections", self.bus_zones.nunique(),
                    len(interconnections))
        return ZoneData(bus_zones=self.bus_zones.sort_index().rename_axis("bus_id").reset_index(),
                        element_zones=elements, interconnections=interconnections)

    def _check_connected(self, branches: pd.DataFrame) -> None:
        # A zone split into pockets is almost always a typo in the mapping.
        for zone in sorted(set(self.bus_zones)):
            members = set(self.bus_zones.index[self.bus_zones == zone])
            inside = branches[branches["bus1"].isin(members) & branches["bus2"].isin(members)]
            neighbours: dict[str, set[str]] = {bus: set() for bus in members}
            for bus1, bus2 in zip(inside["bus1"], inside["bus2"]):
                neighbours[bus1].add(bus2)
                neighbours[bus2].add(bus1)
            start = min(members)
            reached, frontier = {start}, [start]
            while frontier:
                for neighbour in neighbours[frontier.pop()] - reached:
                    reached.add(neighbour)
                    frontier.append(neighbour)
            if cut_off := members - reached:
                raise TestCaseError(f"zone {zone} is not connected: {sorted(cut_off)} are cut "
                                    f"off from {start}")

    def _element_zones(self, elements: pd.DataFrame, element_type: str) -> pd.DataFrame:
        return pd.DataFrame({
            "element_type": element_type,
            "element_id": elements.index,
            "bus_id": elements["bus_breaker_bus_id"].to_numpy(),
            "zone_id": elements["bus_breaker_bus_id"].map(self.bus_zones).to_numpy(),
        }).sort_values("element_id", kind="stable")

    def _ac_ties(self, branches: pd.DataFrame, network: Network) -> pd.DataFrame:
        ties = branches[branches["bus1"].map(self.bus_zones)
                        != branches["bus2"].map(self.bus_zones)]
        limits = network.get_operational_limits(attributes=["name", "value"]).reset_index()
        limits = limits[(limits["name"] == PERMANENT_LIMIT_NAME) & (limits["side"] == "ONE")]
        limit_a = ties.index.map(limits.set_index("element_id")["value"].to_dict())
        nominal_kv = ties["voltage_level1_id"].map(network.get_voltage_levels()["nominal_v"])
        return pd.DataFrame({
            "interconnection_id": ties.index,
            "type": "ac_branch",
            "zone_from": ties["bus1"].map(self.bus_zones).to_numpy(),
            "zone_to": ties["bus2"].map(self.bus_zones).to_numpy(),
            # Apparent power at nominal voltage matching the permanent current limit.
            "capacity_mw": (math.sqrt(3) * nominal_kv.to_numpy() * limit_a.to_numpy()
                            / 1000.0).round(1),
        }).sort_values("interconnection_id", kind="stable")

    def _zones_of(self, buses: pd.Series) -> list[str]:
        return [str(self.bus_zones[bus]) for bus in buses]

    def _hvdc_links(self, network: Network) -> pd.DataFrame:
        lines = network.get_hvdc_lines()
        stations = network.get_vsc_converter_stations(all_attributes=True)["bus_breaker_bus_id"]
        return pd.DataFrame({
            "interconnection_id": lines.index,
            "type": "hvdc",
            "zone_from": self._zones_of(lines["converter_station1_id"].map(stations)),
            "zone_to": self._zones_of(lines["converter_station2_id"].map(stations)),
            "capacity_mw": lines["max_p"].to_numpy(),
        })


def _ac_branches(network: Network) -> pd.DataFrame:
    """Lines and two-winding transformers with their bus-breaker end buses."""
    columns = ["bus_breaker_bus1_id", "bus_breaker_bus2_id", "voltage_level1_id"]
    branches = pd.concat([network.get_lines(all_attributes=True)[columns],
                          network.get_2_windings_transformers(all_attributes=True)[columns]])
    return branches.rename(columns={"bus_breaker_bus1_id": "bus1", "bus_breaker_bus2_id": "bus2"})


@dataclass(frozen=True)
class ZoneData:
    """Zone tables shipped in `testcase/<variant>/zones/`.

    Attributes:
        bus_zones: Zone of every bus (`bus_id`, `zone_id`).
        element_zones: Bus and zone of every generator, load and battery.
        interconnections: AC branches between zones and HVDC links, with capacity.
    """

    bus_zones: pd.DataFrame
    element_zones: pd.DataFrame
    interconnections: pd.DataFrame

    def zone_balance(self, generation: pd.Series, loads: pd.Series,
                     batteries: pd.Series) -> pd.DataFrame:
        """Generation, storage, load and the resulting balance per zone for one scenario.

        Args:
            generation: Active power per generator id (MW).
            loads: Active power per load id (MW).
            batteries: Active power per battery id (MW, > 0 discharging).
        """
        zones = self.element_zones.set_index("element_id")["zone_id"].to_dict()
        frame = pd.DataFrame({
            "generation_mw": generation.groupby(generation.index.map(zones)).sum(),
            "storage_mw": batteries.groupby(batteries.index.map(zones)).sum(),
            "load_mw": loads.groupby(loads.index.map(zones)).sum(),
        }).fillna(0.0)
        frame["balance_mw"] = frame["generation_mw"] + frame["storage_mw"] - frame["load_mw"]
        return frame
