"""Constant decay-observable adapter for manual values and validation studies."""

from __future__ import annotations

from typing import Dict

from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation
from SetAnubis.core.Common.MultiSet import MultiSet


class ConstantCalculationAdapter(IDecayCalculation):
    """Return one configured partial width or branching ratio for every call."""

    def __init__(self, value: float, is_br: bool = False) -> None:
        """Store a finite, non-negative decay observable."""
        value = float(value)
        if value < 0.0:
            raise ValueError("A decay width or branching ratio cannot be negative")
        self._value = value
        self._is_br = bool(is_br)

    def calculate(
        self,
        mother: int,
        daughters: MultiSet[int],
        parameters: Dict[str, float],
    ) -> float:
        """Return the configured value; arguments are accepted for the common API."""
        del mother, daughters, parameters
        return self._value
