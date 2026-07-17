"""Adapter for externally supplied MadGraph decay-width calculations."""

from __future__ import annotations

from typing import Callable, Dict, Optional

from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation
from SetAnubis.core.Common.MultiSet import MultiSet

MadGraphCalculator = Callable[[int, MultiSet[int], Dict[str, float]], float]


class MadGraphCalculationAdapter(IDecayCalculation):
    """Delegate a decay calculation to a configured MadGraph result provider."""

    def __init__(
        self,
        calculator: Optional[MadGraphCalculator] = None,
        is_br: bool = False,
    ) -> None:
        """Store an optional callable that extracts a MadGraph result."""
        self._calculator = calculator
        self._is_br = bool(is_br)

    def calculate(
        self,
        mother: int,
        daughters: MultiSet[int],
        parameters: Dict[str, float],
    ) -> float:
        """Return a configured MadGraph result or explain how to provide one."""
        if self._calculator is None:
            raise RuntimeError(
                "MadGraph decay evaluation requires a result-provider callable. "
                "Use the MadGraph preparation example to generate cards, then pass "
                "a callable through config['calculator'] to parse the produced width."
            )
        return float(self._calculator(mother, daughters, parameters))
