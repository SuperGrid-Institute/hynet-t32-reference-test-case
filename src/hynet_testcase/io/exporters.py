# SPDX-License-Identifier: MIT
"""Network exporters, one per shipped format."""

import logging
import re
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

import pandas as pd
import pypowsybl as pp
from pypowsybl.network import Network

from hynet_testcase.errors import ExportError
from hynet_testcase.ids import ExportFormat

logger = logging.getLogger(__name__)

ID_MAPPING_FILE = "id_mapping.csv"


class NetworkExporter(ABC):
    """Writes the working variant of a network in one format."""

    format: ClassVar[ExportFormat]

    @abstractmethod
    def export(self, network: Network, directory: Path, basename: str) -> None:
        """Writes `network` into `directory`, which must exist and be empty.

        Args:
            network: Network whose working variant is exported.
            directory: Output directory.
            basename: File name stem of the exported files.
        """


class XiidmExporter(NetworkExporter):
    """IIDM XML, the native pypowsybl format."""

    format = ExportFormat.XIIDM

    def export(self, network: Network, directory: Path, basename: str) -> None:
        """Writes `<basename>.xiidm`."""
        # Sorted output keeps diffs between versions of the test case readable.
        network.save(str(directory / f"{basename}.xiidm"), format="XIIDM",
                     parameters={"iidm.export.xml.sorted": "true"})


class CgmesExporter(NetworkExporter):
    """CGMES 2.4.15 (EQ, TP, SSH, SV) with an IIDM → CGMES id mapping."""

    format = ExportFormat.CGMES

    # Some IIDM ids contain characters invalid in a CGMES rdf:ID (such as the `+` of
    # the network id), which make the files unreadable. The `cgmes` naming strategy
    # replaces every id by a UUID derived from it, so ids are valid and stable between
    # builds.
    _PARAMETERS = {
        "iidm.export.cgmes.naming-strategy": "cgmes",
        # Otherwise the exporter adds fictitious slack injections with random UUIDs.
        "iidm.export.cgmes.export-sv-injections-for-slacks": "false",
    }
    _CREATED = re.compile(r"<md:Model\.created>[^<]*</md:Model\.created>")
    _SCENARIO_TIME = re.compile(r"<md:Model\.scenarioTime>([^<]*)</md:Model\.scenarioTime>")
    _FULL_MODEL = re.compile(r'<md:FullModel rdf:about="([^"]+)"')
    _SV_OBJECT = re.compile(
        r'<cim:(?P<cls>Sv(?:Voltage|PowerFlow|TapStep|ShuntCompensatorSections)) '
        r'rdf:ID="_[0-9a-f-]{36}">(?P<body>.*?)</cim:(?P=cls)>', re.DOTALL)
    _REFERENCE = re.compile(r'rdf:resource="#([^"]+)"')
    _SV_NAMESPACE = uuid.UUID("6f3d1a52-9a0e-5f2b-8c47-0d5b7e1c2a90")
    # Element type → (getter in the IIDM network, getter in the re-imported CGMES).
    _ELEMENT_TYPES = {
        "substation": ("get_substations", "get_substations"),
        "voltage_level": ("get_voltage_levels", "get_voltage_levels"),
        "generator": ("get_generators", "get_generators"),
        "load": ("get_loads", "get_loads"),
        "line": ("get_lines", "get_lines"),
        "two_windings_transformer": ("get_2_windings_transformers",
                                     "get_2_windings_transformers"),
        "shunt_compensator": ("get_shunt_compensators", "get_shunt_compensators"),
        "hvdc_line": ("get_hvdc_lines", "get_hvdc_lines"),
        "vsc_converter_station": ("get_vsc_converter_stations", "get_vsc_converter_stations"),
        # CGMES 2.4.15 has no battery class: batteries are exported as synchronous
        # machines and read back as generators.
        "battery": ("get_batteries", "get_generators"),
    }

    def export(self, network: Network, directory: Path, basename: str) -> None:
        """Writes `<basename>_{EQ,TP,SSH,SV}.xml` and `id_mapping.csv`.

        Raises:
            ExportError: If the files cannot be read back or an id cannot be mapped.
        """
        network.save(str(directory / basename), format="CGMES", parameters=self._PARAMETERS)
        files = sorted(directory.glob(f"{basename}_*.xml"))
        if len(files) != 4:
            raise ExportError(f"expected 4 CGMES profiles in {directory}, found {len(files)}")
        for path in files:
            text = self._pin_creation_time(path.read_text(encoding="utf-8"), path)
            if path.name.endswith("_SV.xml"):
                text = self._stable_state_variable_ids(text, path)
            path.write_text(text, encoding="utf-8", newline="\n")
        self._id_mapping(network, directory).to_csv(directory / ID_MAPPING_FILE, index=False,
                                                    lineterminator="\n")

    def _pin_creation_time(self, text: str, path: Path) -> str:
        # Model.created is the export wall-clock time; replacing it by the scenario
        # time makes rebuilding from an unchanged commit byte-identical.
        match = self._SCENARIO_TIME.search(text)
        if match is None:
            raise ExportError(f"no Model.scenarioTime in {path}")
        pinned = f"<md:Model.created>{match.group(1)}</md:Model.created>"
        text, count = self._CREATED.subn(pinned, text, count=1)
        if count != 1:
            raise ExportError(f"no Model.created in {path}")
        return text

    def _stable_state_variable_ids(self, text: str, path: Path) -> str:
        """Replaces the random ids of SV objects by ids derived from their content.

        pypowsybl gives SvVoltage, SvPowerFlow, SvTapStep and SvShuntCompensatorSections
        random UUIDs whatever the naming strategy. Each describes exactly one object and
        is referenced by no other object, so its id can be derived from the SV model and
        the object it describes.

        Raises:
            ExportError: If the SV model id is missing or two SV objects would share an id.
        """
        model = self._FULL_MODEL.search(text)
        if model is None:
            raise ExportError(f"no FullModel in {path}")
        seen: set[str] = set()

        def replace(match: re.Match[str]) -> str:
            cls, body = match.group("cls"), match.group("body")
            references = self._REFERENCE.findall(body)
            if len(references) != 1:
                raise ExportError(f"{cls} with {len(references)} references in {path}")
            key = f"{model.group(1)}|{cls}|{references[0]}"
            if key in seen:
                raise ExportError(f"two {cls} describe {references[0]} in {path}")
            seen.add(key)
            stable = uuid.uuid5(self._SV_NAMESPACE, key)
            return f'<cim:{cls} rdf:ID="_{stable}">{body}</cim:{cls}>'

        text, count = self._SV_OBJECT.subn(replace, text)
        logger.debug("%s: %d SV objects given stable ids", path.name, count)
        return text

    def _id_mapping(self, network: Network, directory: Path) -> pd.DataFrame:
        """Maps IIDM ids to CGMES mRIDs by reading the export back.

        The CGMES exporter writes each IIDM id as the element's IdentifiedObject.name.

        Raises:
            ExportError: If an element is missing or ambiguous in the export.
        """
        exported = pp.network.load(str(directory))
        rows: list[pd.DataFrame] = []
        for element_type, (iidm_getter, cgmes_getter) in self._ELEMENT_TYPES.items():
            iidm_ids = list(getattr(network, iidm_getter)().index)
            names = getattr(exported, cgmes_getter)(attributes=["name"])["name"]
            by_name = pd.Series(names.index, index=names.values)
            if by_name.index.duplicated().any():
                raise ExportError(f"ambiguous CGMES names for {element_type}")
            if missing := set(iidm_ids) - set(by_name.index):
                raise ExportError(f"{element_type} not found in CGMES export: {sorted(missing)}")
            rows.append(pd.DataFrame({"element_type": element_type, "iidm_id": iidm_ids,
                                      "cgmes_id": list(by_name.loc[iidm_ids])}))
        return pd.concat(rows, ignore_index=True)


EXPORTERS: list[NetworkExporter] = [XiidmExporter(), CgmesExporter()]
