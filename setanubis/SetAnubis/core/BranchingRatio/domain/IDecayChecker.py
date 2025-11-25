from abc import ABC, abstractmethod
from typing import List, Dict, Any
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis.core.Common.MultiSet import MultiSet

class IDecayChecker(ABC):
    """Abstract interface for checking the validity of decay processes.

    Ensures decays comply with physical conservation laws such as charge conservation,
    particle number, etc.
    """
    
    @abstractmethod
    def check_decay_validity(self, 
                             mother_id: int, 
                             daughters_id: MultiSet[int], nsa : SetAnubisInterface) -> bool:
        """Checks if a decay process is physically valid.

        Args:
            mother_id (int): PDG ID of the mother particle.
            daughters_id (MultiSet[int]): PDG IDs of the daughter particles.
            nsa (NeoSetAnubisInterface): Interface to retrieve particle properties.

        Returns:
            bool: True if the decay is valid.

        Raises:
            ValueError: If the decay violates physical conservation laws.
        """
        pass
