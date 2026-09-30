# SPDX-License-Identifier: MIT
"""Checks that each scenario exhibits the phenomena it is designed for."""

import logging
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Self

import yaml

from hynet_testcase.errors import InputError, TestCaseError
from hynet_testcase.ids import ScenarioId
from hynet_testcase.scenarios.report import StateReport

logger = logging.getLogger(__name__)

# Voltage rises and drops are measured against this scenario.
REFERENCE = ScenarioId.S1
_HVDC_TOLERANCE_MW = 1e-3


class ValidationError(TestCaseError):
    """A scenario does not exhibit the phenomena it is designed for."""


@dataclass(frozen=True)
class ScenarioRules:
    """Rules one scenario must satisfy; `None` disables a rule.

    Attributes:
        max_branch_loading_pct: No branch may be loaded above this (%).
        voltage_band_pu: Every bus voltage must lie in this band (p.u.).
        hvdc_at_max: Every HVDC line must carry its maximum power.
        min_voltage_rise_pu: Some bus must be at least this much above the reference.
        min_voltage_drop_pu: Some bus must be at least this much below the reference.
        min_overloaded_branches: At least this many branches above 100 %.
    """

    max_branch_loading_pct: float | None = None
    voltage_band_pu: tuple[float, float] | None = None
    hvdc_at_max: bool = False
    min_voltage_rise_pu: float | None = None
    min_voltage_drop_pu: float | None = None
    min_overloaded_branches: int | None = None

    @classmethod
    def from_mapping(cls, scenario: str, data: dict[str, Any]) -> Self:
        """Builds the rules of `scenario` from their YAML mapping.

        Raises:
            InputError: On an unknown rule or a value of the wrong type.
        """
        known = {f.name for f in fields(cls)}
        if unknown := set(data) - known:
            raise InputError(f"validation {scenario}: unknown rules {sorted(unknown)}")
        try:
            band = data.get("voltage_band_pu")
            return cls(
                max_branch_loading_pct=_optional(data, "max_branch_loading_pct", float),
                voltage_band_pu=None if band is None else (float(band[0]), float(band[1])),
                hvdc_at_max=bool(data.get("hvdc_at_max", False)),
                min_voltage_rise_pu=_optional(data, "min_voltage_rise_pu", float),
                min_voltage_drop_pu=_optional(data, "min_voltage_drop_pu", float),
                min_overloaded_branches=_optional(data, "min_overloaded_branches", int),
            )
        except (TypeError, ValueError, IndexError) as exc:
            raise InputError(f"validation {scenario}: {exc}") from exc

    def failures(self, report: StateReport, reference: StateReport) -> list[str]:
        """Returns a description of every rule `report` breaks."""
        failed = []
        highest = max(report.loadings.values())
        if self.max_branch_loading_pct is not None and highest > self.max_branch_loading_pct:
            failed.append(f"a branch is loaded at {highest:.0f} % "
                          f"(max {self.max_branch_loading_pct:g} %)")
        if self.voltage_band_pu is not None:
            low, high = self.voltage_band_pu
            outside = {bus: v for bus, v in report.bus_v_pu.items() if not low <= v <= high}
            if outside:
                failed.append(f"voltages outside {low:g}-{high:g} p.u.: {_rounded(outside)}")
        if self.hvdc_at_max:
            below = {line: p for line, p in report.hvdc_p_mw.items()
                     if abs(p - report.hvdc_max_p_mw[line]) > _HVDC_TOLERANCE_MW}
            if below:
                failed.append(f"HVDC lines below their maximum: {_rounded(below)}")
        rise, drop = _deviation(report, reference)
        if self.min_voltage_rise_pu is not None and rise < self.min_voltage_rise_pu:
            failed.append(f"largest voltage rise vs {REFERENCE} is {rise:.3f} p.u. "
                          f"(min {self.min_voltage_rise_pu:g})")
        if self.min_voltage_drop_pu is not None and drop < self.min_voltage_drop_pu:
            failed.append(f"largest voltage drop vs {REFERENCE} is {drop:.3f} p.u. "
                          f"(min {self.min_voltage_drop_pu:g})")
        if (self.min_overloaded_branches is not None
                and len(report.overloads) < self.min_overloaded_branches):
            failed.append(f"{len(report.overloads)} overloaded branches "
                          f"(min {self.min_overloaded_branches})")
        return failed


@dataclass(frozen=True)
class ScenarioValidation:
    """Rules of every scenario, from `data/inputs/scenarios/validation.yaml`.

    Attributes:
        rules: Rules per scenario; a scenario without rules is not checked.
    """

    rules: dict[ScenarioId, ScenarioRules]

    @classmethod
    def load(cls, path: Path) -> Self:
        """Reads the validation file.

        Raises:
            InputError: If the file cannot be read, names an unknown scenario or holds
                an invalid rule.
        """
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise InputError(f"cannot read {path}: {exc}") from exc
        rules = {}
        for name, mapping in data.items():
            try:
                scenario = ScenarioId(name)
            except ValueError as exc:
                raise InputError(f"{path.name}: unknown scenario {name!r}") from exc
            rules[scenario] = ScenarioRules.from_mapping(name, mapping or {})
        return cls(rules=rules)

    def check(self, reports: dict[ScenarioId, StateReport]) -> None:
        """Checks every scenario with rules against its solved state.

        Raises:
            ValidationError: Listing every broken rule of every scenario.
        """
        failed: list[str] = []
        for scenario, rules in self.rules.items():
            problems = rules.failures(reports[scenario], reports[REFERENCE])
            failed.extend(f"{scenario}: {problem}" for problem in problems)
            if not problems:
                logger.info("%s exhibits its intended phenomena", scenario)
        if failed:
            raise ValidationError("scenario validation failed: " + "; ".join(failed))


def _optional(data: dict[str, Any], key: str, kind: type) -> Any:
    return None if data.get(key) is None else kind(data[key])


def _deviation(report: StateReport, reference: StateReport) -> tuple[float, float]:
    """Largest voltage rise and largest drop of `report` against `reference` (p.u.)."""
    deltas = [v - reference.bus_v_pu[bus] for bus, v in report.bus_v_pu.items()
              if bus in reference.bus_v_pu]
    return max(deltas, default=0.0), -min(deltas, default=0.0)


def _rounded(values: dict[str, float]) -> dict[str, float]:
    return {key: round(value, 3) for key, value in values.items()}
