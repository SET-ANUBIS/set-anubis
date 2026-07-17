"""Adapter for decay calculations implemented in a user-provided Python file."""

from __future__ import annotations

from typing import Dict

from SetAnubis.core.BranchingRatio.adapters.output.BRCalculatorLoader import (
    BRCalculatorLoader,
)
from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation
from SetAnubis.core.Common.MultiSet import MultiSet


class PythonCalculationAdapter(IDecayCalculation):
    """Load an :class:`IDecayCalculation` implementation from a Python script."""

    def __init__(self, script_path: str, is_br: bool = False) -> None:
        """Load the calculator and record whether it returns a branching ratio."""
        self._calculator = BRCalculatorLoader.load_calculator(script_path)
        self._is_br = bool(is_br)

    def calculate(
        self,
        mother: int,
        daughters: MultiSet[int],
        parameters: Dict[str, float],
    ) -> float:
        """Delegate the decay calculation to the dynamically loaded calculator."""
        return float(self._calculator.calculate(mother, daughters, parameters))
