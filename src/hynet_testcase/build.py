# SPDX-License-Identifier: MIT
"""End-to-end build of `testcase/` and the `hynet-testcase` command."""

import argparse
import logging
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pypowsybl.network import Network

from hynet_testcase.economics import Economics
from hynet_testcase.errors import TestCaseError
from hynet_testcase.ids import CaseId, ScenarioId, VariantId
from hynet_testcase.io.csv_writers import CSV_WRITERS, VariantData
from hynet_testcase.io.exporters import EXPORTERS
from hynet_testcase.network.builders import TxFullBuilder, VariantBuilder
from hynet_testcase.network.contingencies import ContingencyList, log_states
from hynet_testcase.network.loadflow import run_ac
from hynet_testcase.network.zones import ZoneMapping
from hynet_testcase.paths import RepoPaths
from hynet_testcase.scenarios.inputs import ScenarioInputs
from hynet_testcase.scenarios.report import StateReport
from hynet_testcase.scenarios.validation import ScenarioValidation
from hynet_testcase.storage.batteries import Batteries

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SolvedState:
    """A solved network variant waiting for export.

    Attributes:
        variant_id: pypowsybl variant holding the state.
        directory: Output directory, relative to the variant output.
        basename: File name stem of the exported files.
        case_date: Case date written with the state (CGMES scenario time).
        report: Load-flow summary of the state.
    """

    variant_id: str
    directory: Path
    basename: str
    case_date: datetime
    report: StateReport


def _variant_data(variant: VariantId, paths: RepoPaths, network: Network) -> VariantData:
    """Reads the tabular inputs of a variant and checks them against its network.

    Raises:
        TestCaseError: On any invalid input or unresolved id.
    """
    scenarios = ScenarioInputs.load(paths.inputs / "scenarios")
    scenarios.check_ids(network)
    zones = ZoneMapping.load(paths.inputs / "zones" / f"{variant}_bus_zones.csv").resolve(network)
    batteries = Batteries.load(paths.inputs / "storage" / f"{variant}_batteries.csv")
    contingencies = ContingencyList.load(
        paths.inputs / "contingencies" / f"{variant}_contingencies.csv")
    contingencies.check(network)
    return VariantData(scenarios=scenarios, zones=zones, batteries=batteries.with_zones(zones),
                       contingencies=contingencies,
                       economics=Economics.load(paths.inputs / "economics" / "economics.yaml"))


def _analyse_contingencies(network: Network, states: list[SolvedState],
                           contingencies: ContingencyList) -> None:
    """Solves every contingency on every scenario state and logs the outcome.

    Post-contingency violations are reported, not enforced: the list exists to create
    them.
    """
    base_variant = network.get_working_variant_id()
    for state in states:
        network.set_working_variant(state.variant_id)
        log_states(state.report.label, contingencies.analyse(network, state.report.label))
    network.set_working_variant(base_variant)


def _solve_states(network: Network, variant: VariantId,
                  inputs: ScenarioInputs) -> list[SolvedState]:
    """Solves the base case and one pypowsybl variant per scenario, in memory.

    The base case comes first, then one state per scenario whose variant id is the
    scenario id.

    Raises:
        LoadFlowError: If any state does not converge.
    """
    base_variant = network.get_working_variant_id()
    label = f"{variant}/{CaseId.BASE}"
    states = [SolvedState(base_variant, Path("network") / CaseId.BASE, f"{variant}_{CaseId.BASE}",
                          network.case_date,
                          StateReport.of(network, label, run_ac(network, label)))]
    for snapshot in inputs.snapshots():
        network.clone_variant(base_variant, str(snapshot.scenario))
        network.set_working_variant(str(snapshot.scenario))
        snapshot.apply(network)
        label = f"{variant}/{CaseId.BASE}/{snapshot.scenario}"
        states.append(SolvedState(
            str(snapshot.scenario), Path("scenarios") / "snapshots" / snapshot.scenario,
            f"{variant}_{CaseId.BASE}_{snapshot.scenario}", snapshot.timestamp,
            StateReport.of(network, label, run_ac(network, label))))
        network.set_working_variant(base_variant)
    return states


def _export_states(network: Network, states: list[SolvedState], output: Path) -> None:
    base_variant = network.get_working_variant_id()
    for state in states:
        network.set_working_variant(state.variant_id)
        network.case_date = state.case_date
        for exporter in EXPORTERS:
            directory = output / state.directory / exporter.format
            directory.mkdir(parents=True)
            exporter.export(network, directory, state.basename)
        state.report.log()
    network.set_working_variant(base_variant)


def build_variant(builder: VariantBuilder, paths: RepoPaths) -> list[StateReport]:
    """Builds one variant into `testcase/<variant>/`, replacing its previous content.

    All states are computed in memory first; files are written only once every state
    has converged, so a failed build never leaves a partial output behind.

    Returns:
        The report of every exported state.

    Raises:
        TestCaseError: On any invalid input, unresolved id or non-converged state.
    """
    network = builder.build()
    data = _variant_data(builder.variant, paths, network)
    unchanged = builder.unchanged_files()
    states = _solve_states(network, builder.variant, data.scenarios)
    ScenarioValidation.load(paths.inputs / "scenarios" / "validation.yaml").check(
        {ScenarioId(state.variant_id): state.report for state in states[1:]})
    _analyse_contingencies(network, states[1:], data.contingencies)

    output = paths.variant_output(builder.variant)
    if output.exists():
        shutil.rmtree(output)
    _export_states(network, states, output)
    for source in unchanged:
        directory = output / "network" / CaseId.BASE / source.suffix.lstrip(".")
        directory.mkdir(parents=True)
        shutil.copyfile(source, directory / source.name)
    for writer in CSV_WRITERS:
        writer.write(data, output)
    logger.info("wrote %s", output.relative_to(paths.root))
    return [state.report for state in states]


def build(paths: RepoPaths) -> None:
    """Builds every variant of the test case.

    Raises:
        TestCaseError: If any variant fails to build.
    """
    for builder in (TxFullBuilder(paths),):
        build_variant(builder, paths)


def main(argv: list[str] | None = None) -> int:
    """Entry point of the `hynet-testcase` command.

    Returns:
        The process exit code.
    """
    parser = argparse.ArgumentParser(prog="hynet-testcase",
                                     description="HYNET Task 3.2 reference test case tools.")
    parser.add_argument("-v", "--verbose", action="store_true", help="log debug messages")
    commands = parser.add_subparsers(dest="command", required=True)
    build_parser = commands.add_parser("build", help="regenerate testcase/ from data/")
    build_parser.add_argument("--root", type=Path, default=None,
                              help="repository root (default: the installed repository)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    # pypowsybl warns about every element when the build reads its own CGMES export
    # back to map ids; its warnings are only useful when investigating.
    logging.getLogger("powsybl").setLevel(logging.WARNING if args.verbose else logging.ERROR)
    paths = RepoPaths(args.root.resolve()) if args.root else RepoPaths.discover()
    try:
        build(paths)
    except TestCaseError as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
