from abc import ABC, abstractmethod
from typing import Dict, Any, Set
from SetAnubis.core.Common.MultiSet import MultiSet

class IDecayCalculation(ABC):
    """Interface for calculating decay widths for particle decays.

    Provides an abstract method to compute decay width given the mother particle,
    daughter particles, and relevant parameters.
    """
    def __init__(self):
        self._is_br = False
        
    def is_br(self):
        return self._is_br
    
    @abstractmethod
    def calculate(self, 
                  mother: int, 
                  daughters: MultiSet[int], 
                  parameters: Dict[str, float]) -> float:
        """Calculates decay width for a given decay process.

        Args:
            mother (int): PDG code of the mother particle.
            daughters (MultiSet[int]): PDG codes of daughter particles.
            parameters (Dict[str, float]): Parameters needed for the calculation (masses, couplings, etc.).

        Returns:
            float: Calculated decay width.
        """
        pass
