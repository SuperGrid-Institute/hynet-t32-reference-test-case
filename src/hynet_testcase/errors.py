# SPDX-License-Identifier: MIT
"""Exception hierarchy of the test-case build."""


class TestCaseError(Exception):
    """Root of every error raised by the test-case build."""

    # Not a test class, despite the name pytest would collect.
    __test__ = False


class InputError(TestCaseError):
    """A hand-edited input file is missing, malformed or inconsistent."""


class IdResolutionError(TestCaseError):
    """An identifier used in an input does not resolve in the network."""


class LoadFlowError(TestCaseError):
    """An AC load flow did not converge."""


class ExportError(TestCaseError):
    """A network or CSV export failed or produced unexpected output."""
