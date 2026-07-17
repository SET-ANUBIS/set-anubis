"""Branching-ratio provider backed by the shared UFO decay manager."""

from __future__ import annotations

from typing import Any, Callable, Dict

from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation
from SetAnubis.core.Common.MultiSet import MultiSet
from SetAnubis.core.DataBase.domain.UFODecayManager import DecayUFOManager


class DecayProvider(IDecayCalculation):
    """Expose evaluated UFO decay functions through the common decay API."""

    def __init__(self, ufo_path: str) -> None:
        """Load, simplify, and cache decay expressions from a trusted UFO model."""
        self.decay_manager = DecayUFOManager(ufo_path)
        self.decay_manager.evaluate_with_sm()
        self.decay_manager.create_func_caches()

    def get_function(
        self,
        mother: int,
        daughters: MultiSet[int],
    ) -> Callable[[Dict[str, Any]], float]:
        """Return the cached function for one decay channel."""
        ordered = tuple(sorted(int(value) for value in daughters))
        channels = self.decay_manager.func.get(mother, {})
        candidates = (MultiSet(ordered), ordered, frozenset(ordered))
        for key in candidates:
            if key in channels:
                return channels[key]
        raise KeyError(
            f"No UFO decay function for mother={mother}, daughters={list(ordered)}"
        )

    def calculate(
        self,
        mother: int,
        daughters: MultiSet[int],
        parameters: Dict[str, float],
    ) -> float:
        """Evaluate a cached UFO decay function with model parameters."""
        return float(self.get_function(mother, daughters)(parameters))

    def get_caches(self) -> Any:
        """Return the function and parameter caches maintained by the UFO manager."""
        return self.decay_manager.get_caches()
