"""Adapter for decay functions extracted from a UFO model."""

from __future__ import annotations

from typing import Dict

from SetAnubis.core.BranchingRatio.adapters.output.DecayProvider import DecayProvider
from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation
from SetAnubis.core.Common.MultiSet import MultiSet


class UFOCalculationAdapter(IDecayCalculation):
    """Evaluate a decay function cached from a UFO model."""

    def __init__(self, ufo_path: str, is_br: bool = False) -> None:
        """Load the UFO decay provider from ``ufo_path``."""
        self._provider = DecayProvider(ufo_path)
        self._is_br = bool(is_br)

    def calculate(
        self,
        mother: int,
        daughters: MultiSet[int],
        parameters: Dict[str, float],
    ) -> float:
        """Evaluate the requested UFO decay channel."""
        return float(self._provider.calculate(mother, daughters, parameters))
