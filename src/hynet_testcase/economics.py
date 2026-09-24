# SPDX-License-Identifier: MIT
"""Economic assumptions shared by every variant."""

import logging
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Self

import pandas as pd
import yaml

from hynet_testcase.errors import InputError

logger = logging.getLogger(__name__)

# Unit and description of every shipped parameter, in shipping order.
_PARAMETERS: dict[str, tuple[str, str]] = {
    "value_of_lost_load_eur_mwh": ("EUR/MWh", "Cost of energy not served"),
    "battery_cycling_cost_eur_mwh": ("EUR/MWh", "Battery wear cost per MWh discharged"),
    "redispatch_premium_eur_mwh": ("EUR/MWh", "Redispatch price margin around marginal cost"),
    "discount_rate": ("-", "Discount rate for annualising investments"),
    "asset_lifetime_years": ("year", "Economic lifetime of network assets"),
    "capital_recovery_factor": ("1/year", "Annuity factor from discount rate and lifetime"),
    "line_cost_345kv_eur_km": ("EUR/km",
                               "Investment cost of a single-circuit 345 kV overhead line"),
}


@dataclass(frozen=True)
class Economics:
    """Economic assumptions, from `data/inputs/economics/economics.yaml`.

    Attributes:
        value_of_lost_load_eur_mwh: Cost of energy not served (EUR/MWh).
        battery_cycling_cost_eur_mwh: Battery wear cost per MWh discharged (EUR/MWh).
        redispatch_premium_eur_mwh: Margin around marginal cost for redispatch (EUR/MWh).
        discount_rate: Discount rate for annualising investments.
        asset_lifetime_years: Economic lifetime of network assets (years).
        line_cost_345kv_eur_km: Investment cost of a 345 kV overhead line (EUR/km).
    """

    value_of_lost_load_eur_mwh: float
    battery_cycling_cost_eur_mwh: float
    redispatch_premium_eur_mwh: float
    discount_rate: float
    asset_lifetime_years: int
    line_cost_345kv_eur_km: float

    @classmethod
    def load(cls, path: Path) -> Self:
        """Reads the economic assumptions.

        Raises:
            InputError: If the file cannot be read, a key is missing or unknown, or a
                value is not a positive number.
        """
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise InputError(f"cannot read {path}: {exc}") from exc
        expected = {f.name for f in fields(cls)}
        if unknown := set(data) - expected:
            raise InputError(f"{path.name}: unknown keys {sorted(unknown)}")
        if missing := expected - set(data):
            raise InputError(f"{path.name}: missing keys {sorted(missing)}")
        try:
            economics = cls(
                value_of_lost_load_eur_mwh=float(data["value_of_lost_load_eur_mwh"]),
                battery_cycling_cost_eur_mwh=float(data["battery_cycling_cost_eur_mwh"]),
                redispatch_premium_eur_mwh=float(data["redispatch_premium_eur_mwh"]),
                discount_rate=float(data["discount_rate"]),
                asset_lifetime_years=int(data["asset_lifetime_years"]),
                line_cost_345kv_eur_km=float(data["line_cost_345kv_eur_km"]),
            )
        except (TypeError, ValueError) as exc:
            raise InputError(f"{path.name}: {exc}") from exc
        if any(getattr(economics, f.name) <= 0 for f in fields(cls)):
            raise InputError(f"{path.name}: every value must be positive")
        return economics

    @property
    def capital_recovery_factor(self) -> float:
        """Share of an investment paid back each year over the asset lifetime."""
        r, n = self.discount_rate, self.asset_lifetime_years
        return r / (1.0 - (1.0 + r) ** -n)

    def annuity_eur(self, investment_eur: float) -> float:
        """Yearly cost of an investment over the asset lifetime (EUR/year)."""
        return investment_eur * self.capital_recovery_factor

    def parameters(self) -> pd.DataFrame:
        """Returns every parameter with its value, unit and description."""
        return pd.DataFrame([
            {"parameter": name, "value": round(float(getattr(self, name)), 6),
             "unit": unit, "description": description}
            for name, (unit, description) in _PARAMETERS.items()])

    def generator_costs(self, generators: pd.DataFrame) -> pd.DataFrame:
        """Returns marginal and redispatch prices of every generator (EUR/MWh).

        Args:
            generators: Generator metadata with `generator_id` and `price_eur_mwh`.
        """
        price = generators["price_eur_mwh"].astype(float)
        return pd.DataFrame({
            "generator_id": generators["generator_id"],
            "marginal_cost_eur_mwh": price,
            "redispatch_up_eur_mwh": price + self.redispatch_premium_eur_mwh,
            "redispatch_down_eur_mwh": price - self.redispatch_premium_eur_mwh,
        }).sort_values("generator_id", kind="stable")
