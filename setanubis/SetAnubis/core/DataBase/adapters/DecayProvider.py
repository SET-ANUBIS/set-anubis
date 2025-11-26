from typing import Set, Callable, Dict, Any
from SetAnubis.core.DataBase.ports.IDecayProvider import IDecayProvider
from SetAnubis.core.DataBase.domain.UFODecayManager import DecayUFOManager
from SetAnubis.core.Common.MultiSet import MultiSet

from enum import Enum

class DecayProvider(IDecayProvider):
    """Provides decay functions and caching mechanisms based on UFO model definitions.

    Attributes:
        decay_manager (DecayUFOManager): Manager handling UFO model-based decay calculations.
    """
    
    def __init__(self, ufo_path: str):
        """Initializes the DecayProvider with UFO model path.

        Args:
            ufo_path (str): Path to the UFO model directory.
        """
        self.decay_manager = DecayUFOManager(ufo_path)
        self.decay_manager.evaluate_with_sm()
        self.decay_manager.create_func_caches()
 

    def get_function(self, mother: int, daughters: MultiSet[int]) -> Callable[[Dict[str, Any]], float]:
        """
        Retrieves the decay function for a given mother particle and its daughter particles.
        
        Args:
            mother (int): PDG code of the mother particle.
            daughters (Set[int]): PDG codes of the daughter particles.
        
        Returns:
            Callable[[Dict[str, Any]], float]: A function that computes the decay rate given parameter values.
        
        Raises:
            KeyError: If the requested function does not exist.
        """
        return self.decay_manager.func[mother][daughters]
    
    def get_caches(self):
        """Retrieves cached decay calculation data.

        Returns:
            Any: Cached data used for decay rate calculations.
        """
        return self.decay_manager.get_caches()