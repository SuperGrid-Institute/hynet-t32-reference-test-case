# SPDX-License-Identifier: MIT
"""Network-area diagrams coloured by zone, including the network map.

Needs only pypowsybl, so the build can draw the map; the charts are in `plots`.
"""

import json
import logging
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Self

import pandas as pd
from pypowsybl.network import NadLayoutType, NadParameters, NadProfile, Network

from hynet_testcase.errors import ExportError, InputError

logger = logging.getLogger(__name__)

ZONE_COLORS = {"Z0": "#7b3294", "Z1": "#1b7837", "Z2": "#2166ac", "Z3": "#d6604d"}
"""Zone colours, shared by the diagrams and the charts."""

# The geographical layout of pypowsybl places a substation at (lon, -mercator(lat)),
# both in radians, times this factor: a spherical Web Mercator projection.
_MAP_SCALING = 40000
_MAP_MARGIN = 0.12      # space around the network, share of its extent
_MAP_ASPECT = 16 / 9
_MAP_WIDTH_PX = 1600    # nominal size; the SVG scales freely
_SEA, _LAND, _BORDER = "#dce6ee", "#f5f4f0", "#b4b4b4"
_LINE, _HVDC = "#3c3c3c", "#1e1e1e"
_ROOT = re.compile(r'<svg width="[^"]+" height="[^"]+" viewBox="([^"]+)"')


def zone_diagram_profile(network: Network, bus_zones: pd.DataFrame) -> NadProfile:
    """Network-area diagram profile colouring each bus by its zone.

    Args:
        network: Network the diagram is drawn from.
        bus_zones: `bus_zones.csv` of the test case (`bus_id`, `zone_id`).
    """
    zones = bus_zones.set_index("bus_id")["zone_id"]
    # The diagram addresses buses by their bus-view id.
    buses = network.get_bus_breaker_view_buses()[["bus_id"]].join(zones)
    buses = buses.dropna().drop_duplicates("bus_id")
    styles = pd.DataFrame({
        "fill": [ZONE_COLORS[zone] for zone in buses["zone_id"]],
        "edge": "#333333",
        "edge-width": "1",
    }, index=pd.Index(buses["bus_id"], name="id"))
    return NadProfile(bus_node_styles=styles)


def zone_diagram_parameters() -> NadParameters:
    """Diagram parameters showing active power flows without injections."""
    # At the default scale the labels overlap the bus nodes.
    return NadParameters(injections_added=False, edge_info_along_edge=True,
                         power_value_precision=0, voltage_level_details=False,
                         scaling_factor=150000)


def _project(longitude: float, latitude: float) -> tuple[float, float]:
    """WGS84 degrees to diagram coordinates of the geographical layout."""
    phi = math.radians(latitude)
    return (_MAP_SCALING * math.radians(longitude),
            -_MAP_SCALING * math.log(math.tan(math.pi / 4 + phi / 2)))


@dataclass(frozen=True)
class Basemap:
    """Country outlines drawn under the network map.

    Attributes:
        polygons: Rings of every polygon, outer ring first, as (longitude, latitude)
            in WGS84 degrees.
    """

    polygons: list[list[list[tuple[float, float]]]]

    @classmethod
    def load(cls, path: Path) -> Self:
        """Reads the polygons of a GeoJSON feature collection.

        Raises:
            InputError: If the file is not GeoJSON or holds no polygon.
        """
        try:
            features = json.loads(path.read_text(encoding="utf-8"))["features"]
            polygons = []
            for feature in features:
                geometry = feature["geometry"]
                coordinates = geometry["coordinates"]
                parts = coordinates if geometry["type"] == "MultiPolygon" else [coordinates]
                polygons += [[[(float(p[0]), float(p[1])) for p in ring] for ring in polygon]
                             for polygon in parts]
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise InputError(f"{path.name}: not a GeoJSON polygon collection: {exc}") from exc
        if not polygons:
            raise InputError(f"{path.name}: no polygon")
        return cls(polygons=polygons)

    def svg(self, frame: tuple[float, float, float, float]) -> str:
        """SVG group of the land polygons that overlap `frame`, over a sea background.

        Args:
            frame: x, y, width and height of the view, in diagram coordinates.
        """
        x0, y0, width, height = frame
        paths = []
        for polygon in self.polygons:
            rings = [[_project(lon, lat) for lon, lat in ring] for ring in polygon]
            xs, ys = [x for x, _ in rings[0]], [y for _, y in rings[0]]
            if max(xs) < x0 or min(xs) > x0 + width or max(ys) < y0 or min(ys) > y0 + height:
                continue
            paths.append("".join(
                "M" + " ".join(f"{x:.1f} {y:.1f}" for x, y in ring) + "Z" for ring in rings))
        land = "\n".join(f'<path d="{d}"/>' for d in paths)
        return (f'<g class="hynet-basemap">\n'
                f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{width:.1f}" height="{height:.1f}" '
                f'fill="{_SEA}"/>\n'
                f'<g fill="{_LAND}" fill-rule="evenodd" stroke="{_BORDER}" stroke-width="3" '
                f'stroke-linejoin="round">\n{land}\n</g>\n</g>')


def _check_layout(network: Network, metadata: str) -> None:
    """Checks that the diagram places every voltage level where `_project` does.

    Raises:
        ExportError: If pypowsybl changed its geographical projection, which would
            shift the network against the basemap.
    """
    positions = network.get_extensions("substationPosition")
    substations = network.get_voltage_levels()["substation_id"]
    for node in json.loads(metadata)["nodes"]:
        position = positions.loc[substations[node["equipmentId"]]]
        x, y = _project(position["longitude"], position["latitude"])
        if abs(x - node["x"]) > 1 or abs(y - node["y"]) > 1:
            raise ExportError(f"network map: {node['equipmentId']} drawn at "
                              f"({node['x']}, {node['y']}), expected ({x:.2f}, {y:.2f})")


def _frame(view_box: str) -> tuple[float, float, float, float]:
    """The diagram view box, padded and widened to the map aspect ratio."""
    x0, y0, width, height = map(float, view_box.split())
    cx, cy = x0 + width / 2, y0 + height / 2
    width, height = width * (1 + 2 * _MAP_MARGIN), height * (1 + 2 * _MAP_MARGIN)
    width, height = max(width, height * _MAP_ASPECT), max(height, width / _MAP_ASPECT)
    return cx - width / 2, cy - height / 2, width, height


def _legend(x0: float, y0: float, unit: float) -> str:
    """Zone and HVDC legend in the top-left corner; `unit` is one nominal pixel."""
    left, top, row = x0 + 30 * unit, y0 + 30 * unit, 30 * unit
    font = f'font-size="{18 * unit:.1f}" font-family="sans-serif" dominant-baseline="central"'
    items = [f'<rect x="{left:.1f}" y="{top:.1f}" width="{140 * unit:.1f}" '
             f'height="{(len(ZONE_COLORS) + 1) * row + 20 * unit:.1f}" rx="{6 * unit:.1f}" '
             f'fill="white" fill-opacity="0.9" stroke="{_BORDER}" stroke-width="{unit:.1f}"/>']
    for k, label in enumerate([*ZONE_COLORS, "HVDC link"]):
        y = top + 10 * unit + (k + 0.5) * row
        if label in ZONE_COLORS:
            items.append(f'<circle cx="{left + 25 * unit:.1f}" cy="{y:.1f}" r="{8 * unit:.1f}" '
                         f'fill="{ZONE_COLORS[label]}" stroke="#333333" '
                         f'stroke-width="{unit:.1f}"/>')
        else:
            items.append(f'<line x1="{left + 12 * unit:.1f}" y1="{y:.1f}" '
                         f'x2="{left + 38 * unit:.1f}" y2="{y:.1f}" stroke="{_HVDC}" '
                         f'stroke-width="{4 * unit:.1f}" '
                         f'stroke-dasharray="{7 * unit:.1f},{4 * unit:.1f}"/>')
        items.append(f'<text x="{left + 50 * unit:.1f}" y="{y:.1f}" {font}>{label}</text>')
    return '<g class="hynet-legend">\n' + "\n".join(items) + "\n</g>"


def network_map(network: Network, bus_zones: pd.DataFrame, basemap: Basemap) -> str:
    """Geographical network-area diagram of `network` over a basemap, as SVG.

    Buses sit at the coordinates of their substation and are coloured by zone; the
    diagram carries no name, flow or voltage value: it shows where the network is,
    not a state of it.

    Args:
        network: Network with the `substationPosition` extension.
        bus_zones: `bus_zones.csv` of the test case (`bus_id`, `zone_id`).
        basemap: Land drawn under the network.

    Raises:
        ExportError: If the diagram does not have the expected layout or structure.
    """
    diagram = network.get_network_area_diagram(
        nad_parameters=NadParameters(
            layout_type=NadLayoutType.GEOGRAPHICAL, scaling_factor=_MAP_SCALING,
            injections_added=False, voltage_level_details=False, bus_legend=False,
            edge_info_included=False, voltage_level_legends_included=False),
        nad_profile=zone_diagram_profile(network, bus_zones))
    if diagram.metadata is None:
        raise ExportError("network map: pypowsybl returned no diagram metadata")
    _check_layout(network, diagram.metadata)
    svg: str = diagram.svg
    if not (root := _ROOT.search(svg)) or svg.count("]]></style>") != 1:
        raise ExportError("network map: unexpected SVG structure from pypowsybl")
    x0, y0, width, height = _frame(root.group(1))
    unit = width / _MAP_WIDTH_PX

    style = (f".nad-branch-edges .nad-edge-path, .nad-branch-edges .nad-winding "
             f"{{stroke: {_LINE}; stroke-width: 7}}\n"
             f".nad-hvdc-edge .nad-edge-path {{stroke: {_HVDC}; stroke-width: 10; "
             f"stroke-dasharray: 24,14}}\n"
             f".nad-hvdc-edge polyline.nad-hvdc {{stroke: {_HVDC}; stroke-width: 30}}\n")
    credit = (f'<text x="{x0 + width - 10 * unit:.1f}" y="{y0 + height - 10 * unit:.1f}" '
              f'text-anchor="end" font-size="{12 * unit:.1f}" font-family="sans-serif" '
              f'fill="#666666">Basemap: Natural Earth</text>')
    svg = svg[:root.start()] + (
        f'<svg width="{_MAP_WIDTH_PX}" height="{round(_MAP_WIDTH_PX / _MAP_ASPECT)}" '
        f'viewBox="{x0:.2f} {y0:.2f} {width:.2f} {height:.2f}"') + svg[root.end():]
    svg = svg.replace("]]></style>", style + "]]></style>\n" + basemap.svg(
        (x0, y0, width, height)).rstrip("\n"), 1)
    head, _, tail = svg.rpartition("</svg>")
    return head + _legend(x0, y0, unit) + "\n" + credit + "\n</svg>" + tail
