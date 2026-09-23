# SPDX-License-Identifier: MIT
"""AC load flow used to validate network states before export."""

import logging
from dataclasses import dataclass

import pypowsybl as pp
from pypowsybl.network import Network

from hynet_testcase.errors import LoadFlowError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ComponentResult:
    """Load-flow outcome of one synchronous component.

    Attributes:
        synchronous_component: Number of the synchronous component.
        status: OpenLoadFlow status, e.g. `CONVERGED`.
        iterations: Newton-Raphson iterations.
        slack_mismatch_mw: Active power left on the slack bus after distribution.
    """

    synchronous_component: int
    status: str
    iterations: int
    slack_mismatch_mw: float


def _parameters() -> pp.loadflow.Parameters:
    # Losses are spread over the dispatched units in proportion to their output, so
    # the scenario dispatch is preserved as far as possible.
    return pp.loadflow.Parameters(
        distributed_slack=True,
        balance_type=pp.loadflow.BalanceType.PROPORTIONAL_TO_GENERATION_P,
    )


def run_ac(network: Network, label: str) -> list[ComponentResult]:
    """Runs an AC load flow on the working variant of `network`.

    Args:
        network: Network whose working variant is solved in place.
        label: Name of the state, used in logs and errors.

    Returns:
        One result per synchronous component.

    Raises:
        LoadFlowError: If any synchronous component does not converge.
    """
    results = [
        ComponentResult(
            synchronous_component=r.synchronous_component_num,
            status=r.status.name,
            iterations=r.iteration_count,
            slack_mismatch_mw=sum(s.active_power_mismatch for s in r.slack_bus_results),
        )
        for r in pp.loadflow.run_ac(network, _parameters())
    ]
    failed = [r for r in results if r.status != "CONVERGED"]
    if failed:
        raise LoadFlowError(f"AC load flow of {label} did not converge: {failed}")
    for r in results:
        logger.debug("%s: component %d converged in %d iterations, slack mismatch %.3f MW",
                     label, r.synchronous_component, r.iterations, r.slack_mismatch_mw)
    return results
