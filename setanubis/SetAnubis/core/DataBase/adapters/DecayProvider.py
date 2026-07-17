"""Decay-function provider backed by a UFO decay manager."""

from __future__ import annotations

from typing import Any, Callable

from SetAnubis.core.Common.MultiSet import MultiSet
from SetAnubis.core.DataBase.domain.UFODecayManager import DecayUFOManager
from SetAnubis.core.DataBase.ports.IDecayProvider import IDecayProvider


class DecayProvider(IDecayProvider):
    """Provide evaluated UFO decay functions and their cached expressions."""

    def __init__(self, ufo_path: str) -> None:
        """Load, evaluate, and cache the decay model at ``ufo_path``."""

        self.decay_manager = DecayUFOManager(ufo_path)
        self.decay_manager.evaluate_with_sm()
        self.decay_manager.create_func_caches()

    def get_function(
        self,
        mother: int,
        daughters: MultiSet[int],
    ) -> Callable[[dict[str, Any]], float]:
        """Return the decay function for a mother and daughter multiset."""

        return self.decay_manager.func[mother][daughters]

    def get_caches(self) -> Any:
        """Return cached symbolic decay-calculation data."""

        return self.decay_manager.get_caches()
