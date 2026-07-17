"""Abstract decay-calculation contract."""

from abc import ABC, abstractmethod
from typing import Dict

from SetAnubis.core.Common.MultiSet import MultiSet


class IDecayCalculation(ABC):
    """Calculate a partial width or branching ratio for a decay channel."""

    def __init__(self) -> None:
        self._is_br = False

    def is_br(self) -> bool:
        """Return whether :meth:`calculate` produces a branching ratio."""
        return self._is_br

    @abstractmethod
    def calculate(
        self,
        mother: int,
        daughters: MultiSet[int],
        parameters: Dict[str, float],
    ) -> float:
        """Calculate the configured decay observable.

        Args:
            mother: PDG identifier of the mother particle.
            daughters: Daughter-particle PDG identifiers.
            parameters: Numerical model parameters required by the calculation.

        Returns:
            The calculated partial width or branching ratio.
        """
        raise NotImplementedError
