"""High-level interface for widths, branching ratios, and lifetimes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from SetAnubis.core.BranchingRatio.domain.BranchingRatioManager import (
    BranchingRatioManager,
    Unit,
)
from SetAnubis.core.BranchingRatio.domain.CalculationStrategy import (
    CalculationDecayStrategy,
)
from SetAnubis.core.BranchingRatio.domain.DecayChecker import DecayChecker
from SetAnubis.core.Common.MultiSet import MultiSet
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface


class DecayInterface:
    """Provide a concise public API for model-dependent decay observables."""

    def __init__(self, model: SetAnubisInterface) -> None:
        """Create a decay manager for ``model``."""
        self.nsa = model
        self.br_manager = BranchingRatioManager(DecayChecker(), model)

    def get_decay(self, mother: int, daughters: MultiSet[int]) -> float:
        """Return a registered partial width or direct branching ratio."""
        return self.br_manager.calculate_decay(mother, daughters)

    def set_decay(
        self,
        mother: int,
        daughters: MultiSet[int],
        value: float,
        *,
        is_br: bool = False,
    ) -> None:
        """Register a manually supplied partial width or branching ratio."""
        self.br_manager.add_constant_decay(mother, daughters, value, is_br=is_br)

    def get_decay_tot(self, mother: int) -> float:
        """Return the sum of registered partial-width providers for ``mother``."""
        return self.br_manager.calculate_total_decay(mother)

    def get_brs(self, mother: int) -> List[Dict[str, Any]]:
        """Return all registered channels and their branching ratios."""
        return self.br_manager.calculate_branching_ratios_for_mother(mother)

    def get_br(self, mother: int, daughters: MultiSet[int]) -> float:
        """Return the branching ratio for one registered decay channel."""
        return self.br_manager.calculate_branching_ratio_for_mother(mother, daughters)

    def add_decays(
        self,
        decays_list: List[Dict[str, Any]],
        strategy: CalculationDecayStrategy,
        config: Dict[str, Any],
    ) -> None:
        """Register several channels using one calculation configuration."""
        self.br_manager.add_decays(decays_list, strategy, config)

    def get_all_decays(
        self,
        mother: Optional[int] = None,
    ) -> Dict[Tuple[int, Tuple[int, ...]], Any] | List[Tuple[int, ...]]:
        """Return all registered decays or the daughter tuples for one mother."""
        return self.br_manager.get_all_decays(mother)

    def add_special_lifetime(self, particle: int, value: float, unit: Unit) -> None:
        """Override the width-derived lifetime of one particle."""
        self.br_manager.add_special_lifetime(particle, value, unit)

    def calculate_lifetime(self, particle: int, unit: Unit) -> float:
        """Return the particle lifetime in the requested unit."""
        return self.br_manager.calculate_lifetime(particle, unit)
